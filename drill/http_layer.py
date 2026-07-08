"""HTTP layer -- Bottle request/response glue (D4 extraction), module http_layer.

Named http_layer (not http) because a top-level http.py shadows the stdlib http
package that bottle imports (http.client) -- the findings' S4 prototype used this
name for the same reason.

Thin route handlers over the DATABASE and LOGIC layers: each parses the request,
calls down the stack, and formats the JSON response. No business logic lives
here -- an if-statement that is not about request parsing or response formatting
belongs in LOGIC. HTTP is the top data-flow layer (config <- db <- logic <-
http); nothing imports http except main, which wires it. It is the only layer
that reads the clock (per-request timestamps handed to the DB writes).

D4a landed the request-helper preamble; D4b adds the app object, the
DATABASE_PATH request-path global, and all route handlers, so the whole HTTP
layer now lives here. DATABASE_PATH is a module global that main (drill.py)
rebinds at startup via `http_layer.DATABASE_PATH = ...`; the per-request
handlers read it from this module's namespace, so the rebind is visible to them.

Behavior-preserving: every symbol is identical to its pre-split definition.
"""

from __future__ import annotations

import os
import random
import sqlite3
from datetime import date, datetime, timedelta

import bottle

from config import (
    DEFAULT_DATABASE_PATH,
    DIFFICULTY_RUNGS,
    NEW_QUESTIONS_PER_BANK_MINIMUM,
    NEW_QUESTIONS_PER_DAY_MAXIMUM,
    QTYPE_ARITHMETIC,
    REVIEWS_PER_SESSION_MAXIMUM,
)
from db import (
    connect,
    end_session,
    get_new_introduced_today_by_bank,
    get_response_stats_for_bank,
    get_responses_for_stats,
    get_schedule_for_bank,
    get_schedule_for_question,
    get_session,
    get_session_correctness,
    insert_bank,
    insert_questions_bulk,
    insert_response,
    list_banks,
    list_categories,
    list_questions,
    start_session,
    upsert_schedule_row,
    utc_now_iso,
)
from logic import (
    EASINESS_FACTOR_INITIAL,
    ImportParseError,
    OPERATORS,
    advance_schedule_state,
    apply_interval_fuzz,
    apply_new_question_throttle,
    build_question_payload,
    derive_recall_quality,
    evaluate_expression,
    generate_expression,
    leaf_count,
    parse_import,
    partition_candidates_by_schedule,
    pick_next_question,
    render_expression,
    schedule_update_allowed_today,
    select_weighted_by_miss_rate,
    summarize_correctness,
    summarize_stats,
    validate_answer,
)


def _json_error(message: str, status: int = 400) -> dict:
    """Set the response status and return the standard error body.

    The error envelope is {"error": message} with the given HTTP status, per
    spec section 6. Returning the dict lets Bottle serialize it as JSON while
    the status is applied as a side effect on the response object.
    """
    bottle.response.status = status
    return {"error": message}


def _integrity_message(error: sqlite3.IntegrityError) -> str:
    """Translate a SQLite IntegrityError into a user-facing 400 message.

    The common cause in this app is a foreign-key violation: a request
    references a category, bank, session, or question id that does not exist
    (or was deleted in another browser tab between being served and being
    answered -- a real time-gradient case for a single user with multiple
    tabs open). The raw SQLite text is terse; this gives a clearer hint
    without leaking schema internals.
    """
    raw = str(error).lower()
    if "foreign key" in raw:
        return (
            "request references an id that does not exist "
            "(it may have been deleted in another tab)"
        )
    return "the request conflicts with the database state: " + str(error)


def _request_json() -> dict:
    """Return the parsed JSON body of the current request as a dict.

    Bottle's request.json is None when the body is absent or not JSON, and
    can be a non-dict (list, string, number) when the client sends valid JSON
    that is not an object. This helper normalizes both cases to an empty dict
    so handlers can use .get without a None check and without an
    AttributeError on a non-dict body. A client that sends a JSON array or
    scalar is treated as having sent no fields; required-field checks in the
    handler then produce the standard 400, rather than a 500 from .get on a
    list. Malformed JSON (not parseable at all) raises bottle.HTTPError 400
    inside bottle.request.json; handlers need not catch it -- Bottle renders
    it as a 400.
    """
    try:
        parsed = bottle.request.json
    except (ValueError, TypeError):
        # Body present but not parseable as JSON. Treat as no fields; the
        # handler's required-field check will return a descriptive 400.
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


class _BadParameter(Exception):
    """Internal signal that a request parameter failed integer parsing.

    Carries the 400-ready message. Used by _require_int / _optional_int so
    handlers can convert client-supplied strings to integers in one place
    with one consistent error shape, instead of scattering try/except int()
    (a previously unguarded path that turned bad input into 500s).
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _require_int(value: object, field_name: str) -> int:
    """Parse a required value as an int, raising _BadParameter on failure.

    Accepts an int directly or a string of digits. None, empty string, or a
    non-integer string raises _BadParameter with a message naming the field,
    which the handler turns into a 400. This guards the JSON-body integer
    fields (session_id, category_id) that were previously passed straight to
    int() and could raise an unhandled ValueError -> 500.
    """
    if value is None or value == "":
        raise _BadParameter("missing required field: " + field_name)
    try:
        return int(value)
    except (ValueError, TypeError):
        raise _BadParameter(field_name + " must be an integer")


def _optional_int(value: object, field_name: str) -> int | None:
    """Parse an optional value as an int, or None when absent.

    None or empty string yields None. A present but non-integer value raises
    _BadParameter (named) for a 400. Used for optional body fields such as
    bank_id and question_id so a malformed optional value is reported
    cleanly rather than crashing a later int() or DB insert.
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        raise _BadParameter(field_name + " must be an integer")


# === APP + ROUTES (D4b) ======================================================
# The Bottle application, the per-request DATABASE_PATH (rebound by main at
# startup), and the route handlers. Each handler parses the request, calls into
# DATABASE and LOGIC, and formats the JSON response -- no business logic here.

# Directory of this module, used to locate the index.html served at root.
_MODULE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# The Bottle application. Routes are attached to this app object rather than
# the module-global default, so the server is explicit and testable.
app = bottle.Bottle()

# Database path the handlers open per request. MAIN may override this at
# startup; handlers read it here so tests can point at a temporary database.
DATABASE_PATH = DEFAULT_DATABASE_PATH


@app.get("/")
def serve_index():
    """Serve the single-page frontend (index.html). [stub -> C-013]"""
    print("drill: serving index.html (browser will now fetch the ES modules)")
    return bottle.static_file("index.html", root=_MODULE_DIRECTORY)


# The frontend ES modules loaded by index.html's <script type="module"
# src="boot.js">. Before the E10 cutover all JS was inline in index.html and
# needed no route; after the split the browser fetches each module over HTTP, so
# they must be served with a JavaScript MIME type (browsers reject type=module
# scripts served as anything else). Scoped to the known module set so nothing
# else in the module directory is ever served; static_file also guards against
# path traversal via its root check. C-MOD-E10.
_FRONTEND_MODULES = frozenset([
    "state.js", "el.js", "api.js", "timing.js", "stage.js",
    "speech.js", "stats.js", "session.js", "drill.js", "boot.js",
])


@app.get("/<filename:re:[A-Za-z0-9_-]+\\.js>")
def serve_module(filename):
    """Serve a frontend ES module by filename (E10 cutover).

    Only the ten known modules are served, with a JavaScript content type so the
    browser will evaluate them as ES modules. Anything else -> 404.
    """
    if filename not in _FRONTEND_MODULES:
        return bottle.HTTPError(404, "Not found")
    print("drill: serving module " + filename)
    return bottle.static_file(filename, root=_MODULE_DIRECTORY,
                              mimetype="text/javascript")


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

    # B3 (adaptive selection, roadmap #7 / ADR-005): optional strategy
    # parameter selects the picking policy. Absent or "random" keeps the
    # existing pick_next_question path byte-identical; "weighted" draws by
    # smoothed miss rate. C4 adds "scheduled": SM2 review mode -- partition
    # against the schedule, throttle new questions, serve due-then-new.
    # Context (candidates, schedules, response stats, the today ordinal, the
    # uniform random sample) is assembled entirely here at the HTTP edge --
    # LOGIC never queries, never reads the clock, never reads random.
    strategy = bottle.request.query.get("strategy") or "random"
    if strategy not in ("random", "weighted", "scheduled"):
        return _json_error(
            "unknown strategy: " + strategy
            + " (expected random, weighted, or scheduled)",
            status=400,
        )

    # C4: the day is stamped ONCE per request, here at the top, and threaded
    # through partition/throttle/new-today so one request cannot straddle a
    # day boundary mid-computation. date.today() is the LOCAL calendar day:
    # for this single-user local tool the user's own midnight is the honest
    # day boundary (a 23:59 review and its 00:01 retry are different days).
    # Note responses.answered is stored in UTC; the rebuild derives ordinals
    # from those timestamps, so rebuild == stored parity assumes the local
    # and UTC date agree at review time (documented limit, findings s8/s11).
    today_ordinal = date.today().toordinal()

    connection = connect(DATABASE_PATH)
    try:
        candidates = list_questions(connection, bank_id)
        if strategy == "weighted":
            response_stats_by_question_id = get_response_stats_for_bank(
                connection, bank_id
            )
        if strategy == "scheduled":
            response_stats_by_question_id = get_response_stats_for_bank(
                connection, bank_id
            )
            schedule_by_question_id = get_schedule_for_bank(connection, bank_id)
            new_introduced_today_by_bank = get_new_introduced_today_by_bank(
                connection, today_ordinal
            )
    finally:
        connection.close()

    if strategy == "weighted":
        chosen = select_weighted_by_miss_rate(
            candidates, response_stats_by_question_id, history, random.random()
        )
    elif strategy == "scheduled":
        if not candidates:
            return _json_error(
                "bank " + str(bank_id) + " has no questions", status=404
            )
        due, new, not_due = partition_candidates_by_schedule(
            candidates, schedule_by_question_id, today_ordinal
        )
        # The session cap keeps a huge backlog from swamping one sitting;
        # partition already ordered due by relative overdueness so the capped
        # subset is the most at-risk one. Within that due set the pick is
        # weighted by miss rate (findings section 12), not strict order, so
        # a struggling due question surfaces sooner.
        due_within_session_cap = due[:REVIEWS_PER_SESSION_MAXIMUM]
        admitted_new = apply_new_question_throttle(
            new,
            new_introduced_today_by_bank,
            NEW_QUESTIONS_PER_DAY_MAXIMUM,
            NEW_QUESTIONS_PER_BANK_MINIMUM,
        )
        if due_within_session_cap:
            chosen = select_weighted_by_miss_rate(
                due_within_session_cap,
                response_stats_by_question_id,
                history,
                random.random(),
            )
        elif admitted_new:
            chosen = admitted_new[0]
        else:
            return _json_error(
                "nothing due for review in bank " + str(bank_id)
                + " and no new-question budget left today",
                status=404,
            )
    else:
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
        mode          (str, optional)   "practice" (default) or "review".
                                        Review mode (C4) advances the SM2
                                        schedule for stored questions; the
                                        practice path never touches it.
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

    # C4: mode is a REQUEST property (findings section 11) -- the review path
    # updates schedules, the practice path never does; no schema, no flag
    # column. Absent means practice, so every pre-C4 client is untouched.
    mode = body.get("mode") or "practice"
    if mode not in ("practice", "review"):
        return _json_error(
            "unknown mode: " + str(mode) + " (expected practice or review)",
            status=400,
        )

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
        # C4: the schedule write path. The response row above is ALWAYS
        # inserted (the log is complete); the schedule advances only in
        # review mode, only for stored questions (generated arithmetic has
        # question_id None and is never scheduled), and only on the FIRST
        # graded attempt of the day (schedule_update_allowed_today) --
        # same-day retries are logged history that must not advance the
        # interval again off one day of memory. The day is stamped ONCE per
        # request; date.today() is the LOCAL calendar day, the honest
        # boundary for a single-user local tool (a 23:59 review and a 00:01
        # retry are different days). responses.answered is UTC, so the
        # rebuild's ordinal derivation matches this stamp only while the
        # local and UTC date agree at review time (documented limit).
        if mode == "review" and question_id is not None:
            today_ordinal = date.today().toordinal()
            existing_schedule = get_schedule_for_question(connection, question_id)
            if schedule_update_allowed_today(existing_schedule, today_ordinal):
                if existing_schedule is None:
                    easiness_factor = EASINESS_FACTOR_INITIAL
                    interval_days = 0.0
                    repetition_count = 0
                    lapse_count_value = 0
                else:
                    easiness_factor = existing_schedule["easiness_factor"]
                    interval_days = existing_schedule["interval_days"]
                    repetition_count = existing_schedule["repetition_count"]
                    lapse_count_value = existing_schedule["lapse_count"]
                recall_quality = derive_recall_quality(correct, elapsed_ms)
                advanced_schedule = advance_schedule_state(
                    recall_quality,
                    easiness_factor,
                    interval_days,
                    repetition_count,
                    lapse_count_value,
                    today_ordinal,
                )
                fuzzed_interval = apply_interval_fuzz(
                    advanced_schedule["interval_days"], question_id
                )
                advanced_schedule["interval_days"] = fuzzed_interval
                advanced_schedule["due_date"] = today_ordinal + int(
                    round(fuzzed_interval)
                )
                advanced_schedule["question_id"] = question_id
                upsert_schedule_row(connection, advanced_schedule)
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
    """End a session by stamping its ended timestamp, returning a summary.

    C-010: required field session_id. The ended timestamp is read here.
    Returns {"ended": bool, "summary": dict | None}. ended indicates whether
    a session row was updated; a session_id that does not exist updates no
    row and returns ended=false with summary=null (not an error -- ending an
    unknown or already-cleaned-up session is a harmless no-op for this
    tool).

    Q4 (QoL thread): summary closes the session loop in one response
    instead of requiring separate report calls. Fields:
        total, correct, accuracy, streak -- summarize_correctness over the
            session's ordered answers (same numbers the stats bar showed).
        new_introduced_today -- questions that entered the schedule today,
            summed across all banks (the throttle budget is global).
        due_remaining -- due-today count for the SESSION'S bank via the
            same partition the scheduled strategy uses; null for sessions
            without a bank (category-only sessions, generated arithmetic).
    """
    body = _request_json()
    if "session_id" not in body:
        return _json_error("missing required field: session_id", status=400)
    try:
        session_id = _require_int(body.get("session_id"), "session_id")
    except _BadParameter as bad:
        return _json_error(bad.message, status=400)
    today_ordinal = date.today().toordinal()
    connection = connect(DATABASE_PATH)
    try:
        updated = end_session(
            connection,
            session_id=session_id,
            ended=utc_now_iso(),
        )
        summary = None
        if updated > 0:
            correctness = get_session_correctness(connection, session_id)
            summary = summarize_correctness(correctness)
            new_introduced_today_by_bank = get_new_introduced_today_by_bank(
                connection, today_ordinal
            )
            summary["new_introduced_today"] = sum(
                new_introduced_today_by_bank.values()
            )
            session = get_session(connection, session_id)
            summary["due_remaining"] = None
            if session is not None and session.get("bank_id") is not None:
                bank_id = session["bank_id"]
                candidates = list_questions(connection, bank_id)
                schedule_by_question_id = get_schedule_for_bank(
                    connection, bank_id
                )
                due, _new, _not_due = partition_candidates_by_schedule(
                    candidates, schedule_by_question_id, today_ordinal
                )
                summary["due_remaining"] = len(due)
    finally:
        connection.close()
    return {"ended": updated > 0, "summary": summary}


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
