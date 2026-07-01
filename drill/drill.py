"""Drill -- a local, single-user practice tool with cross-session tracking.

This module is the entire backend. It is organized into clearly separated
sections that follow a data-oriented procedural style:

    CONFIG    -- constants and scalar configuration; no callables
    DATABASE  -- functions over a sqlite3.Connection; IO only, no logic
    LOGIC     -- pure functions; no IO, no DB, no HTTP
    HTTP      -- thin Bottle route handlers
    MAIN      -- server startup (added with C-013a)

Boundary invariant (spec section 5): DATABASE never calls LOGIC or HTTP;
LOGIC never calls DATABASE or HTTP; HTTP calls both. Data crosses
boundaries as plain dicts, lists, strings, and numbers.

Status: backend complete through C-019a. Every API endpoint in spec section 6
is implemented, including GET /api/stats (C-019a): the DATABASE stats reader
(get_responses_for_stats), the pure LOGIC summary (summarize_stats), and the
handler that computes the day-window cutoff and returns the summary. The
frontend (index.html) is built in C-013 onward; the stats VIEW that consumes
this endpoint is C-019b.

C-018b note: build_question_payload and the bank-question handler carry a
comment-block scaffold for the deferred per-question-language TTS path; that
remains comment-only (no executable backend code from C-018b).

Error-handling contract for the HTTP layer: handlers return the standard
{"error": message} envelope with a 4xx status for bad input (missing or
non-integer fields, malformed uploads) and for database integrity conflicts
(referencing an id that does not exist, e.g. a row deleted in another open
tab). Pure LOGIC functions raise ValueError on violated preconditions, which
indicate programming errors rather than user input and are intended to fail
loudly during development rather than emit silently wrong output.
"""

from __future__ import annotations

import os
import sqlite3
from datetime import datetime, timedelta

try:
    import bottle
except ImportError:  # pragma: no cover - environment setup guard
    raise SystemExit(
        "The 'bottle' package is required but not installed. "
        "Run 'uv sync' (or 'pip install bottle') and try again."
    )


# --- CONFIG ---

# Constants and scalar configuration now live in config.py (D1 extraction).
# config is the leaf of the backend DAG (config <- db <- logic <- http; main
# wires); importing it here runs its import-time consistency guard
# (_check_difficulty_rungs_consistency) as a side effect, exactly as before the
# split. The migration functions + MIGRATIONS registry below stay in this file
# for now; they relocate to db.py in D3 (they are DATABASE operations -- S10a).
from config import (
    BASELINE_SCHEMA_VERSION,
    DEFAULT_DATABASE_PATH,
    DIFFICULTY_RUNGS,
    OPERATOR_SYMBOLS,
    QTYPE_ARITHMETIC,
    QTYPE_FREE_RESPONSE,
    QTYPE_IDENTIFY,
    QTYPE_MULTIPLE_CHOICE,
    QTYPE_TRANSLATE,
    QTYPES,
    SCHEMA_STATEMENTS,
    SCHEMA_VERSION,
    SEED_CATEGORIES,
    _DEFAULT_OPERAND_RANGE,
    _EXPONENT_POWER_RANGE,
    _MAX_GENERATION_ATTEMPTS,
    _MAX_OPERATOR_DEPTH,
    _MAX_RESULT_VALUE,
    _MULTIPLICATIVE_OPERAND_RANGE,
    _RECURSE_PROBABILITY,
)


# The DATABASE layer now lives in db.py (D2 extraction), together with the
# migration unit that historically sat in the CONFIG region (S10a: the v2/v3
# migrations run DDL, so they are DATABASE operations). db imports config
# (down-stack); importing it here runs its version-consistency guard-weld as a
# side effect, exactly as before the split.
from db import (
    connect,
    end_session,
    get_responses_for_stats,
    get_session_correctness,
    init_db,
    insert_bank,
    insert_questions_bulk,
    insert_response,
    list_banks,
    list_categories,
    list_questions,
    run_migrations,
    start_session,
    utc_now_iso,
)

# The LOGIC layer now lives in logic.py (D3): the arithmetic ENGINE (operator
# table -- callable-bearing, so logic not config, S10b -- plus expression
# generate/evaluate/render + rung application) and the GENERAL LOGIC utilities
# (validation, import parsing, stats, next-question selection, payload build).
# logic imports config (down-stack). drill.py keeps only HTTP + MAIN.
from logic import (
    ImportParseError,
    OPERATORS,
    build_question_payload,
    evaluate_expression,
    generate_expression,
    leaf_count,
    parse_import,
    pick_next_question,
    render_expression,
    summarize_correctness,
    summarize_stats,
    validate_answer,
)


# --- HTTP ---
# Thin Bottle route handlers. Each handler parses the request, calls into
# DATABASE and LOGIC, and formats the JSON response. No business logic lives
# here: an if-statement that is not about request parsing or response
# formatting belongs in LOGIC. HTTP is the only layer that reads the clock
# and the only glue between DATABASE output and LOGIC input.
#
# All endpoints from spec section 6 are implemented, including GET /api/stats
# (C-019a). Handlers open a SQLite connection per request and close it in a
# finally block. Integer fields from the request are parsed through _require_int / _optional_int so malformed values yield a
# 400 rather than an unhandled exception, and database integrity conflicts
# (e.g. a referenced id deleted in another tab) are caught and returned as a
# 400 with a clear message.

# Directory of this module, used to locate the index.html served at root.
_MODULE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# The Bottle application. Routes are attached to this app object rather than
# the module-global default, so the server is explicit and testable.
app = bottle.Bottle()

# Database path the handlers open per request. MAIN may override this at
# startup; handlers read it here so tests can point at a temporary database.
DATABASE_PATH = DEFAULT_DATABASE_PATH


# The stateless request-parsing/error helpers moved to http_layer.py (D4a) --
# _json_error, _integrity_message, _request_json, _BadParameter, _require_int,
# _optional_int. (Module named http_layer, not http, to avoid shadowing the
# stdlib http package that bottle imports.) The app object, DATABASE_PATH, and
# the route handlers below stay here until D4b, which moves them as one unit.
from http_layer import (
    _BadParameter,
    _integrity_message,
    _json_error,
    _optional_int,
    _request_json,
    _require_int,
)


@app.get("/")
def serve_index():
    """Serve the single-page frontend (index.html). [stub -> C-013]"""
    return bottle.static_file("index.html", root=_MODULE_DIRECTORY)


@app.get("/api/categories")
def get_categories():
    """List all categories as JSON.

    C-010: opens a connection, reads categories via DATABASE.list_categories,
    returns them under a "categories" key.
    """
    connection = connect(DATABASE_PATH)
    try:
        categories = list_categories(connection)
    finally:
        connection.close()
    return {"categories": categories}


@app.get("/api/banks")
def get_banks():
    """List banks as JSON, optionally filtered by category_id.

    C-010: reads the optional category_id query parameter, validates it as an
    integer when present, and returns matching banks via DATABASE.list_banks.
    """
    category_id_raw = bottle.request.query.get("category_id")
    category_id = None
    if category_id_raw is not None and category_id_raw != "":
        try:
            category_id = int(category_id_raw)
        except ValueError:
            return _json_error("category_id must be an integer", status=400)
    connection = connect(DATABASE_PATH)
    try:
        banks = list_banks(connection, category_id)
    finally:
        connection.close()
    return {"banks": banks}


@app.get("/api/question")
def get_question_endpoint():
    """Get the next question. Branches on category: arithmetic vs bank.

    C-011 implements the arithmetic branch. The bank branch is C-012.

    Arithmetic (category=arithmetic): generates an expression, evaluates it,
    and returns a question payload the client echoes back to /api/answer.
    Optional query parameter operators is a comma-separated list of operator
    symbols to restrict generation (e.g. operators=+,-); absent means all
    enabled operators. Optional query parameter difficulty is a scalar rung
    (see DIFFICULTY_RUNGS); absent means the no-rung default path (byte-
    identical to pre-#2). The payload's qtype is the validator-level
    "arithmetic" so /api/answer takes the numeric-comparison branch, and
    question_id is null because generated questions are never stored.

    C-D2c: the arithmetic payload now also carries the SERVED difficulty rung
    and the generated expression's leaf_count, so the client can echo both back
    on /api/answer for recording (the capture side is C-D2g, gated on the v3
    migration C-D2f). difficulty is null on the no-rung path; leaf_count is
    always present (it is a fact about the served tree regardless of rung).
    """
    category = bottle.request.query.get("category")
    if not category:
        return _json_error("missing required parameter: category", status=400)

    if category == "arithmetic":
        # Optional operator restriction from the query string.
        operators_raw = bottle.request.query.get("operators")
        enabled_symbols = None
        if operators_raw:
            requested = [
                symbol.strip()
                for symbol in operators_raw.split(",")
                if symbol.strip() != ""
            ]
            # operators= present but containing only separators/whitespace
            # parses to an empty set. That is a malformed restriction, not
            # "use all operators" -- report it rather than silently widening.
            if not requested:
                return _json_error(
                    "operators parameter is empty; omit it for all operators "
                    "or list one or more symbols",
                    status=400,
                )
            unknown = [s for s in requested if s not in OPERATORS]
            if unknown:
                return _json_error(
                    "unknown operator symbols: " + ", ".join(unknown),
                    status=400,
                )
            enabled_symbols = requested

        # Optional difficulty rung. Absent/empty -> None (the default path).
        # Present -> must parse to an int that is a KNOWN rung label. We
        # validate here (user input) and 400 on a bad value, mirroring the
        # operators= unknown-symbol 400; generate_expression's own ValueError
        # guard then only ever fires on an internal programming error.
        difficulty_raw = bottle.request.query.get("difficulty")
        difficulty = None
        if difficulty_raw is not None and difficulty_raw != "":
            try:
                difficulty = int(difficulty_raw)
            except ValueError:
                return _json_error("difficulty must be an integer", status=400)
            known_rungs = [record["rung"] for record in DIFFICULTY_RUNGS]
            if difficulty not in known_rungs:
                return _json_error(
                    "unknown difficulty rung "
                    + str(difficulty)
                    + "; known rungs are "
                    + ", ".join(str(rung) for rung in known_rungs),
                    status=400,
                )

        expression = generate_expression(enabled_symbols, difficulty=difficulty)
        rendered = render_expression(expression)
        result = evaluate_expression(expression)
        return {
            "qtype": QTYPE_ARITHMETIC,
            "question_text": rendered,
            "expected": str(result),
            "question_id": None,
            "alternatives": None,
            "media_url": None,
            # C-D2c echo carriers: the served rung (null on the default path)
            # and the tree's structural leaf_count. The client returns both on
            # /api/answer; capture into responses is C-D2g (needs the v3 cols).
            "difficulty": difficulty,
            "leaf_count": leaf_count(expression),
        }

    # Bank-based question path (C-012). For any non-arithmetic category, draw
    # from a specific bank identified by the required bank_id parameter.
    bank_id_raw = bottle.request.query.get("bank_id")
    if bank_id_raw is None or bank_id_raw == "":
        return _json_error("missing required parameter: bank_id", status=400)
    try:
        bank_id = int(bank_id_raw)
    except ValueError:
        return _json_error("bank_id must be an integer", status=400)

    # Optional recent-history to softly avoid immediate repeats. Accepts a
    # comma-separated list of recently served question ids from the client.
    history_raw = bottle.request.query.get("recent")
    history: list[int] = []
    if history_raw:
        for piece in history_raw.split(","):
            piece = piece.strip()
            if piece == "":
                continue
            try:
                history.append(int(piece))
            except ValueError:
                return _json_error(
                    "recent must be a comma-separated list of integer ids",
                    status=400,
                )

    connection = connect(DATABASE_PATH)
    try:
        candidates = list_questions(connection, bank_id)
    finally:
        connection.close()

    chosen = pick_next_question(candidates, history)
    if chosen is None:
        return _json_error("bank " + str(bank_id) + " has no questions", status=404)
    # C-018b scaffold (deferred Option A): if per-question-language TTS is ever
    # built, this is where the bank's language enters the request. We already
    # have bank_id; the handler would fetch the bank row (get_bank / a
    # language lookup in DATABASE) and pass it down, e.g.
    #     bank = get_bank(connection, bank_id)   # inside the try above
    #     return build_question_payload(chosen, bank_language=bank["language"])
    # Not done now: it touches the frozen backend and the section-6 payload
    # contract, so it is its own future commit + spec amendment. C-018a sources
    # language on the client from the already-fetched bank instead. See the
    # longer note in build_question_payload and DECISIONS C-018b.
    return build_question_payload(chosen)


@app.post("/api/answer")
def post_answer():
    """Validate a submitted answer, log the response, return feedback.

    C-010: the request body echoes back the question context the client was
    served, so the server can validate and log without server-side per-
    question state. Expected JSON fields:
        session_id    (int, required)   the active session
        qtype         (str, required)   drives validation dispatch
        question_text (str, required)   rendered question, stored verbatim
        expected      (str, required)   the correct answer to compare against
        user_input    (str, required)   what the user submitted
        alternatives  (list, optional)  also-acceptable answers (text qtypes)
        question_id   (int, optional)   NULL for generated arithmetic
        elapsed_ms    (int, optional)   reserved for future timed rounds
        difficulty    (int, optional)   served rung echoed from the question
                                        payload; NULL for bank/no-rung (C-D2g)
        leaf_count    (int, optional)   expression leaf_count echoed from the
                                        question payload; NULL for non-arithmetic
        tolerance     (float, optional) numeric tolerance for arithmetic
    Returns {"correct": bool, "expected": str, "user_input": str,
    "session_stats": {total, correct, accuracy, streak}} so the client can
    show feedback (including the right answer on a miss) and refresh the
    stats bar without a separate GET /api/stats call.
    """
    body = _request_json()
    required_fields = ("session_id", "qtype", "question_text", "expected", "user_input")
    for field in required_fields:
        if field not in body:
            return _json_error("missing required field: " + field, status=400)

    try:
        session_id = _require_int(body.get("session_id"), "session_id")
        question_id = _optional_int(body.get("question_id"), "question_id")
        elapsed_ms = _optional_int(body.get("elapsed_ms"), "elapsed_ms")
        # C-D2g: capture the rung + leaf_count the client echoes from the served
        # question payload (C-D2c). Type-checked as optional ints (malformed ->
        # 400), then recorded verbatim. We do NOT reject an out-of-range rung
        # here: the question endpoint already validated ?difficulty= on the way
        # out, and this field is recording-only (the C-D2i breakdown groups by
        # leaf_count, not the rung label). Honestly storing what the client
        # claimed is the right behavior for this single-user local tool; over-
        # policing the echo would add a second rung-range source of truth.
        difficulty = _optional_int(body.get("difficulty"), "difficulty")
        leaf_count = _optional_int(body.get("leaf_count"), "leaf_count")
    except _BadParameter as bad:
        return _json_error(bad.message, status=400)

    # Trust assumption: this single-user local tool trusts the client-supplied
    # question context (expected, qtype, alternatives). The server re-runs
    # validation rather than trusting a client verdict, but it does not verify
    # that "expected" matches a stored question. A future multi-user version
    # should look the question up by question_id and grade against the DB's
    # stored answer, ignoring the client's "expected" field.
    correct = validate_answer(
        expected=str(body["expected"]),
        given=str(body["user_input"]),
        qtype=str(body["qtype"]),
        alternatives=body.get("alternatives"),
        tolerance=body.get("tolerance"),
    )

    connection = connect(DATABASE_PATH)
    try:
        insert_response(
            connection,
            session_id=session_id,
            question_text=str(body["question_text"]),
            answer_text=str(body["expected"]),
            user_input=str(body["user_input"]),
            correct=correct,
            answered=utc_now_iso(),
            question_id=question_id,
            elapsed_ms=elapsed_ms,
            difficulty=difficulty,
            leaf_count=leaf_count,
        )
        # Tack the running session stats onto the response so the UI updates
        # its stats bar without a separate GET /api/stats call per question
        # (keeps the drill hot path to two calls: POST answer, GET question).
        correctness = get_session_correctness(connection, session_id)
    except sqlite3.IntegrityError as error:
        # e.g. session_id (or a non-null question_id) does not exist, perhaps
        # because the session/bank was deleted in another tab. Report cleanly.
        return _json_error(_integrity_message(error), status=400)
    finally:
        connection.close()
    session_stats = summarize_correctness(correctness)
    return {
        "correct": correct,
        "expected": str(body["expected"]),
        "user_input": str(body["user_input"]),
        "session_stats": session_stats,
    }


@app.post("/api/session/start")
def post_session_start():
    """Begin a session and return its id.

    C-010: required field category_id; optional bank_id and config. The
    started timestamp is read from the clock here (HTTP is the clock-reader).
    Returns {"session_id": int}.
    """
    body = _request_json()
    if "category_id" not in body:
        return _json_error("missing required field: category_id", status=400)
    try:
        category_id = _require_int(body.get("category_id"), "category_id")
        bank_id = _optional_int(body.get("bank_id"), "bank_id")
    except _BadParameter as bad:
        return _json_error(bad.message, status=400)
    connection = connect(DATABASE_PATH)
    try:
        session_id = start_session(
            connection,
            category_id=category_id,
            started=utc_now_iso(),
            bank_id=bank_id,
            config=body.get("config"),
        )
    except sqlite3.IntegrityError as error:
        # category_id or bank_id does not reference an existing row.
        return _json_error(_integrity_message(error), status=400)
    finally:
        connection.close()
    return {"session_id": session_id}


@app.post("/api/session/end")
def post_session_end():
    """End a session by stamping its ended timestamp.

    C-010: required field session_id. The ended timestamp is read here.
    Returns {"ended": bool} indicating whether a session row was updated.
    A session_id that does not exist updates no row and returns ended=false
    (not an error -- ending an unknown or already-cleaned-up session is a
    harmless no-op for this tool).
    """
    body = _request_json()
    if "session_id" not in body:
        return _json_error("missing required field: session_id", status=400)
    try:
        session_id = _require_int(body.get("session_id"), "session_id")
    except _BadParameter as bad:
        return _json_error(bad.message, status=400)
    connection = connect(DATABASE_PATH)
    try:
        updated = end_session(
            connection,
            session_id=session_id,
            ended=utc_now_iso(),
        )
    finally:
        connection.close()
    return {"ended": updated > 0}


@app.get("/api/stats")
def get_stats():
    """Durable cross-session stats, optionally filtered by category and window.

    C-019a (spec section 6, the one sanctioned post-freeze backend addition).
    Query parameters (both optional):
        category_id -- restrict to one category; omitted means all categories.
        days        -- a positive integer window; only responses answered
                       within the last N days are counted. Omitted means all
                       time. days <= 0 is a 400 (a zero/negative window is a
                       malformed request, not "all time" -- omit the param for
                       all time).

    The day-window cutoff is computed HERE from the clock (HTTP is the only
    clock-reader alongside init_db); the cutoff is passed to DATABASE as an ISO
    string so neither DATABASE nor LOGIC reads the clock. Rows come from
    get_responses_for_stats; the summary is the pure summarize_stats. Returns:
        {total, correct, accuracy, categories:[{category_id, category_name,
         total, correct, accuracy}], window:{category_id, days, since}}
    where window echoes the effective filter (since is the ISO cutoff or null).
    """
    query = bottle.request.query
    try:
        category_id = _optional_int(query.get("category_id"), "category_id")
        days = _optional_int(query.get("days"), "days")
    except _BadParameter as bad:
        return _json_error(bad.message, status=400)

    since = None
    if days is not None:
        if days <= 0:
            return _json_error(
                "days must be a positive integer (omit it for all time)",
                status=400,
            )
        # Cutoff = now - days, emitted in the same ISO 8601 UTC format as
        # responses.answered so the DATABASE comparison is string-vs-string in
        # one consistent format. utc_now_iso() is the shared clock helper.
        cutoff = datetime.fromisoformat(utc_now_iso()) - timedelta(days=days)
        since = cutoff.isoformat()

    connection = connect(DATABASE_PATH)
    try:
        rows = get_responses_for_stats(
            connection,
            category_id=category_id,
            since=since,
        )
    finally:
        connection.close()

    summary = summarize_stats(rows)
    summary["window"] = {
        "category_id": category_id,
        "days": days,
        "since": since,
    }
    return summary


@app.get("/api/difficulty-rungs")
def get_difficulty_rungs():
    """List the arithmetic difficulty rungs the client can offer (C-2U-a).

    A pure read of the DIFFICULTY_RUNGS config: no query params, no DB, no
    writes. It exists so the UI selector populates from the server's rung
    table rather than re-encoding the rung set in the client -- if the table
    grows or a rung's shape changes, the selector tracks it automatically
    (the D-UI-1 decision).

    Each entry carries the rung's STRUCTURAL FACTS, not a human label: the
    server owns what rungs exist and their shape; the client composes the
    user-facing descriptor from these fields. max_result_value is the
    per-rung result ceiling (null when a rung leaves the ceiling dark,
    ADR-039/044). Returns:
        {"rungs": [{"rung", "operator_depth", "recurse_probability",
                    "max_result_value"}, ...]}
    in ascending rung order (DIFFICULTY_RUNGS is validated gap-free ascending
    at import by _check_difficulty_rungs_consistency).
    """
    rungs = [
        {
            "rung": record["rung"],
            "operator_depth": record["operator_depth"],
            "recurse_probability": record["recurse_probability"],
            "max_result_value": record["max_result_value"],
        }
        for record in DIFFICULTY_RUNGS
    ]
    return {"rungs": rungs}


@app.post("/api/banks/import")
def post_banks_import():
    """Import a JSONL or CSV question bank into a new bank.

    C-010 (item 6): wires the import route by combining LOGIC.parse_import
    (C-008) with DATABASE.insert_bank and insert_questions_bulk (C-003).

    Accepts a multipart upload with a "file" part, plus form fields:
        category_id (int, required)  the category the new bank belongs to
        name        (str, optional)  bank name; defaults to the upload's
                                      filename without extension
        format      (str, optional)  "jsonl" or "csv"; if absent, inferred
                                      from the upload's file extension
        language    (str, optional)  ISO 639-1 code stored on the bank
    The bank's source is recorded as "import". The created timestamp is read
    here. On a parse failure, returns 400 with the row-naming message from
    ImportParseError and creates no bank. Returns
    {"bank_id": int, "imported": int} on success.
    """
    upload = bottle.request.files.get("file")
    if upload is None:
        return _json_error("missing uploaded file part 'file'", status=400)

    form = bottle.request.forms
    category_id_raw = form.get("category_id")
    if category_id_raw is None or category_id_raw == "":
        return _json_error("missing required field: category_id", status=400)
    try:
        category_id = int(category_id_raw)
    except ValueError:
        return _json_error("category_id must be an integer", status=400)

    # Infer format from the explicit field or the filename extension.
    file_format = form.get("format")
    if not file_format:
        _, extension = os.path.splitext(upload.filename or "")
        file_format = extension.lstrip(".").lower()

    # Default the bank name to the uploaded filename without its extension.
    bank_name = form.get("name")
    if not bank_name:
        base = os.path.basename(upload.filename or "imported")
        bank_name = os.path.splitext(base)[0] or "imported"

    language = form.get("language") or None

    # Read and decode the upload, then parse via LOGIC. Parsing happens
    # before any DB write so a bad file creates no empty bank.
    raw_bytes = upload.file.read()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return _json_error("uploaded file must be UTF-8 encoded", status=400)
    try:
        questions = parse_import(text, file_format)
    except ImportParseError as error:
        return _json_error(str(error), status=400)

    connection = connect(DATABASE_PATH)
    try:
        created = utc_now_iso()
        bank_id = insert_bank(
            connection,
            category_id=category_id,
            name=bank_name,
            source="import",
            created=created,
            language=language,
        )
        imported = insert_questions_bulk(connection, bank_id, questions, created)
    except sqlite3.IntegrityError as error:
        # category_id does not reference an existing category.
        return _json_error(_integrity_message(error), status=400)
    finally:
        connection.close()
    return {"bank_id": bank_id, "imported": imported}


# =============================================================================
# --- MAIN ---
#
# Server entry point. Pulled forward to C-013a (originally bundled with the
# C-019 stats work) so the app is runnable while the frontend is built.
#
# Spec section 5 (# --- MAIN ---) defines this block as exactly three things:
# the init_db call, bottle.run, and the __main__ guard. As of C-019a the stats
# endpoint (GET /api/stats) and its DB query are implemented in their proper
# sections above; the only remaining stats work is the frontend view (C-019b),
# which adds nothing here. This block stays the minimum that makes the app
# runnable end to end.
#
# This block is meant to be appended to the END of drill.py (after the
# /api/banks/import handler). It is kept in a separate file here only so the
# verification thread stays clean; reinject it into drill.py's MAIN section.
#
# Design notes:
#   - Runs the explicit `app` object (app.run), not bottle's module-global
#     default, matching how routes are attached.
#   - Rebinds the module global DATABASE_PATH before serving, because the
#     per-request handlers read that global (the spec says "MAIN may override
#     this at startup"). Overriding a local would not reach the handlers.
#   - init_db is idempotent (schema IF NOT EXISTS, version stamp once, seed
#     via INSERT OR IGNORE), so calling it on every startup is safe and is
#     what creates + seeds drill.db the first time -- no separate init step.
#   - No argparse/CLI flags (the spec does not specify any); host/port/db are
#     overridable via environment variables for convenience (notably under
#     WSL), defaulting to 127.0.0.1:8080 and the standard drill.db. Adds no
#     new dependencies (os is already imported).


def main() -> None:
    """Initialize the database and start the drill server.

    Reads optional overrides from the environment:
      DRILL_HOST  (default 127.0.0.1)
      DRILL_PORT  (default 8080)
      DRILL_DB    (default DEFAULT_DATABASE_PATH, i.e. drill.db)

    Calls init_db once at startup (creating and seeding the database on first
    run) and then serves the app. The database path is published to the module
    global DATABASE_PATH so the per-request handlers open the same file.
    """
    global DATABASE_PATH

    host = os.environ.get("DRILL_HOST", "127.0.0.1")
    database_path = os.environ.get("DRILL_DB", DEFAULT_DATABASE_PATH)

    port_raw = os.environ.get("DRILL_PORT", "8080")
    try:
        port = int(port_raw)
    except ValueError:
        raise SystemExit("DRILL_PORT must be an integer (got: " + repr(port_raw) + ")")

    # Publish the chosen path so request handlers (which read the module
    # global) open the same database this startup initialized.
    DATABASE_PATH = database_path

    # Create the schema and seed categories if needed, then apply any pending
    # schema migrations. Reconciliation (decisions.md ADR): init_db stays the
    # version-1 baseline -- it builds today's schema and stamps v1 -- and the
    # migration runner layers versions 2..N on top. Both fresh and existing
    # databases reach the current version by this one path: a fresh DB is built
    # to v1 by init_db then advanced by the runner; an existing DB is left as-is
    # by init_db's IF NOT EXISTS / stamp-once and advanced from its current
    # version by the runner. With an empty MIGRATIONS (T2) the runner is a
    # no-op. Idempotent and safe on every startup. One connection here.
    #
    # The clock is read HERE (MAIN boundary) and injected into the runner, so
    # the DATABASE layer stays clock-free.
    connection = connect(DATABASE_PATH)
    try:
        init_db(connection)
        connection.commit()
        result = run_migrations(connection, utc_now_iso())
    finally:
        connection.close()

    # Operator-facing migration report: what ran and the resulting version.
    if result["applied"]:
        for version, description in result["applied"]:
            print("drill: applied migration " + str(version) + " (" + description + ")")
        print(
            "drill: schema migrated "
            + str(result["from_version"])
            + " -> "
            + str(result["to_version"])
        )
    else:
        print("drill: schema up to date (version " + str(result["to_version"]) + ")")

    # Friendly startup line so the operator knows the exact URL to open.
    # (Bottle also prints its own banner.)
    print(
        "drill: serving on http://" + host + ":" + str(port) + "/"
        " (database: " + DATABASE_PATH + ")"
    )

    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
