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

import csv
import io
import json
import os
import random
import re
import sqlite3
from datetime import datetime, timedelta, timezone

try:
    import bottle
except ImportError:  # pragma: no cover - environment setup guard
    raise SystemExit(
        "The 'bottle' package is required but not installed. "
        "Run 'uv sync' (or 'pip install bottle') and try again."
    )


# --- CONFIG ---
# Constants and scalar configuration only. No callables (resolution to the
# operator-table layering tension: the operator table is built in LOGIC in
# C-006, not here). Operator definitions are intentionally absent from C-002.

# Current schema version. Stamped once into the schema_version table at init.
# No migration logic runs in v1 (ADR / spec section 5, item 5); the table
# exists so a future version can detect the schema and apply migrations.
SCHEMA_VERSION: int = 1

# Seed categories (spec section 4.1). Inserted once at init if absent.
# Each entry is (name, description). Config defaults to an empty JSON object
# at seed time; per-category config is populated by later commits as needed.
SEED_CATEGORIES: list[tuple[str, str]] = [
    ("arithmetic", "Generated arithmetic expressions to evaluate"),
    ("vocabulary", "Vocabulary terms and translations"),
    ("trivia", "General trivia and history questions"),
    ("geography", "Places, capitals, and map knowledge"),
    ("logic", "Logic and reasoning puzzles"),
    ("typing", "Typing accuracy and speed drills"),
    ("code", "Code snippet recall and comprehension"),
]

# Question types (qtype enum). free_response is the default for trivia and
# arithmetic; translate is for vocabulary (show term, type translation);
# identify is for "what is this" media questions; multiple_choice is the
# only type that uses the distractors field.
QTYPE_FREE_RESPONSE: str = "free_response"
QTYPE_MULTIPLE_CHOICE: str = "multiple_choice"
QTYPE_TRANSLATE: str = "translate"
QTYPE_IDENTIFY: str = "identify"

QTYPES: list[str] = [
    QTYPE_FREE_RESPONSE,
    QTYPE_MULTIPLE_CHOICE,
    QTYPE_TRANSLATE,
    QTYPE_IDENTIFY,
]

# Validator-level qtype for generated arithmetic. Deliberately NOT part of
# QTYPES: that enum describes stored bank questions, whereas arithmetic is
# ephemeral and never persisted to the questions table. validate_answer
# (C-007) recognizes this string to take the numeric-comparison branch.
QTYPE_ARITHMETIC: str = "arithmetic"

# C-005: Operator scalar configuration.
# Per the layering resolution, CONFIG holds only the scalar data describing
# arithmetic operators. The callables (eval, display, operand generation)
# and the assembled operator table live in LOGIC (C-006), which reads these
# constants. Nothing here is a callable.
#
# Each operator's scalar config is a dict of plain data:
#   symbol     -- the rendered operator string (also the join key that
#                 LOGIC uses to attach functions and that the enabled list
#                 references)
#   name       -- human-readable operator name
#   arity      -- number of operands (all v1 operators are binary)
#   operand_min, operand_max -- inclusive range for generated operands;
#                 interpreted per operator by the C-006 generator (e.g.
#                 division treats this range as the divisor/quotient range
#                 and derives the dividend, guaranteeing integer results
#                 per ADR-007)
#   forbid_identity -- list of operand values that would make the operation
#                 a trivial identity and must be rejected at generation time
#                 (ADR-007: no x+0, x*1, x/1, 0*x, etc.); enforcement is in
#                 C-006, the values to forbid are scalar config here
#
# OPERATOR_SYMBOLS lists which operators are enabled by default. Every
# symbol here must exist in OPERATOR_CONFIG; C-006 validates this at the
# time it builds the operator table.

OPERATOR_CONFIG: list[dict] = [
    {
        "symbol": "+",
        "name": "addition",
        "arity": 2,
        "operand_min": 1,
        "operand_max": 20,
        "forbid_identity": [0],
    },
    {
        "symbol": "-",
        "name": "subtraction",
        "arity": 2,
        "operand_min": 1,
        "operand_max": 20,
        "forbid_identity": [0],
    },
    {
        "symbol": "*",
        "name": "multiplication",
        "arity": 2,
        "operand_min": 2,
        "operand_max": 12,
        "forbid_identity": [0, 1],
    },
    {
        "symbol": "/",
        "name": "division",
        "arity": 2,
        # For division the range bounds the divisor and quotient; the
        # dividend is derived as divisor * quotient (ADR-007). Divisor range
        # [2..12] matches the spec; quotient shares the same range.
        "operand_min": 2,
        "operand_max": 12,
        "forbid_identity": [1],
    },
]

# Operators enabled by default, by symbol. Used when a session config does
# not specify a custom operator set. Every entry must match a symbol in
# OPERATOR_CONFIG (validated in C-006).
OPERATOR_SYMBOLS: list[str] = ["+", "-", "*", "/"]

# Default on-disk database filename. The server may override this at startup.
DEFAULT_DATABASE_PATH: str = "drill.db"

# Data definition language for every table in the schema (spec section 4.1).
# All timestamp columns are TEXT storing ISO 8601 strings (item 8). Foreign
# keys are declared; PRAGMA foreign_keys is enabled per connection.
SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER NOT NULL,
        applied TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS categories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        description TEXT,
        config      TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS banks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        name        TEXT NOT NULL,
        language    TEXT,
        source      TEXT NOT NULL,
        metadata    TEXT NOT NULL DEFAULT '{}',
        created     TEXT NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS questions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        bank_id      INTEGER NOT NULL,
        qtype        TEXT NOT NULL,
        question     TEXT NOT NULL,
        answer       TEXT NOT NULL,
        alternatives TEXT NOT NULL DEFAULT '[]',
        distractors  TEXT NOT NULL DEFAULT '[]',
        hints        TEXT NOT NULL DEFAULT '[]',
        media_url    TEXT,
        tags         TEXT NOT NULL DEFAULT '[]',
        difficulty   INTEGER,
        created      TEXT NOT NULL,
        FOREIGN KEY (bank_id) REFERENCES banks (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        bank_id     INTEGER,
        config      TEXT NOT NULL DEFAULT '{}',
        started     TEXT NOT NULL,
        ended       TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (bank_id) REFERENCES banks (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS responses (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id    INTEGER NOT NULL,
        question_id   INTEGER,
        question_text TEXT NOT NULL,
        answer_text   TEXT NOT NULL,
        user_input    TEXT NOT NULL,
        correct       INTEGER NOT NULL,
        elapsed_ms    INTEGER,
        answered      TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (id),
        FOREIGN KEY (question_id) REFERENCES questions (id)
    )
    """,
]


# --- DATABASE ---
# Functions that take a sqlite3.Connection and return dicts or lists. IO
# only: no business logic, no HTTP. init_db is the one place in this section
# allowed to read the clock, because it must stamp the schema_version row
# and the seed timestamps (item 8).


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    This is the single clock-reading helper for the DATABASE layer. Only
    init_db (here) and the HTTP layer (later commits) may call it; LOGIC
    receives timestamps as string parameters and never reads the clock.
    """
    return datetime.now(timezone.utc).isoformat()


def connect(database_path: str = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with row access by name and FKs enforced.

    The connection uses sqlite3.Row so that DATABASE functions can convert
    rows to plain dicts before returning them across the layer boundary.
    Foreign key enforcement is enabled per connection (SQLite defaults off).
    """
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_schema_version(connection: sqlite3.Connection) -> int | None:
    """Return the highest recorded schema version, or None if unstamped.

    Returns None when the schema_version table does not yet exist or holds
    no rows, which indicates a fresh, uninitialized database.
    """
    try:
        cursor = connection.execute(
            "SELECT MAX(version) AS version FROM schema_version"
        )
    except sqlite3.OperationalError:
        # schema_version table does not exist yet.
        return None
    row = cursor.fetchone()
    if row is None or row["version"] is None:
        return None
    return int(row["version"])


def _apply_one(
    connection: sqlite3.Connection,
    version: int,
    description: str,
    migrate,
    now: str,
) -> None:
    """Apply a single migration inside one explicit, all-or-nothing transaction.

    migrate -- a callable taking the connection; it performs the schema change
               (DDL and/or data backfill) for this version. It MUST NOT commit,
               rollback, or stamp schema_version itself: this function owns the
               transaction boundary and records the version row on success.

    Why an explicit BEGIN/COMMIT/ROLLBACK rather than relying on the
    connection's implicit handling: Python's legacy sqlite3 isolation mode
    (the default for connect()) does NOT open a transaction before a DDL
    statement such as ALTER TABLE, so a DDL change autocommits and SURVIVES a
    later rollback(). That would make a half-finished migration permanent --
    the opposite of the forward-only, last-good-version guarantee. Issuing
    BEGIN ourselves puts the DDL inside a transaction we control, so any
    failure (in the migrate callable or the version stamp) rolls the whole
    step back and leaves the database at its prior version, not half-migrated.

    On failure the original exception is re-raised unchanged after rollback,
    so the caller sees the real error; the caller is responsible for the
    operator-facing "migration N failed" framing.
    """
    connection.execute("BEGIN")
    try:
        migrate(connection)
        connection.execute(
            "INSERT INTO schema_version (version, applied) VALUES (?, ?)",
            (version, now),
        )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def seed_categories(connection: sqlite3.Connection) -> None:
    """Insert the seed categories that are not already present.

    Idempotent: uses INSERT OR IGNORE against the UNIQUE name constraint, so
    running it repeatedly never duplicates a category and never overwrites a
    category whose description or config was later edited.
    """
    connection.executemany(
        "INSERT OR IGNORE INTO categories (name, description, config) "
        "VALUES (?, ?, '{}')",
        SEED_CATEGORIES,
    )


# C-010 support: category readers. The commit plan defines no dedicated
# category-CRUD commit (categories are seeded in C-002 and otherwise fixed in
# v1), but the GET /api/categories handler needs to read them, so the minimal
# read functions live here. Same plain-dict-out pattern as the other readers.


def _category_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a categories row to a plain dict with config parsed."""
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "config": _load_json(row["config"], {}),
    }


def list_categories(connection: sqlite3.Connection) -> list[dict]:
    """Return all categories as a list of dicts, ordered by id (seed order)."""
    cursor = connection.execute("SELECT * FROM categories ORDER BY id")
    return [_category_row_to_dict(row) for row in cursor.fetchall()]


def get_category(connection: sqlite3.Connection, category_id: int) -> dict | None:
    """Return a single category dict by id, or None if no such category."""
    cursor = connection.execute(
        "SELECT * FROM categories WHERE id = ?",
        (category_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _category_row_to_dict(row)


def init_db(connection: sqlite3.Connection) -> None:
    """Create the schema if needed, stamp the version, and seed categories.

    Idempotent and safe to call on every startup. Creates all tables with
    IF NOT EXISTS, stamps the current SCHEMA_VERSION the first time the
    database is initialized, and seeds any missing categories. No migration
    logic runs in v1 (item 5): if the database is already at the current
    version, the version row is left untouched.
    """
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)

    existing_version = get_schema_version(connection)
    if existing_version is None:
        connection.execute(
            "INSERT INTO schema_version (version, applied) VALUES (?, ?)",
            (SCHEMA_VERSION, utc_now_iso()),
        )

    seed_categories(connection)
    connection.commit()


# C-003: Bank and question CRUD.
# These functions accept and return plain Python structures. The JSON-typed
# columns (config/metadata as objects; alternatives/distractors/hints/tags
# as arrays) are serialized to text on write and parsed back to Python lists
# and dicts on read, so callers never handle raw JSON strings. This
# marshalling is IO at the layer edge, not business logic.


def _dump_json(value: object) -> str:
    """Serialize a Python value to a compact JSON string for storage.

    Used to write the JSON-typed columns. Compact separators keep the
    stored text small and stable for inspection.
    """
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _load_json(text: str | None, default: object) -> object:
    """Parse a JSON string from a column, returning default when empty.

    The schema defaults JSON columns to '[]' or '{}' and marks them NOT
    NULL, so text is normally present; default guards the None case
    defensively without raising at the layer boundary.

    If a stored value is present but not valid JSON -- which should not happen
    through this application's writes, but can occur if the .db file is
    hand-edited (the spec encourages direct SQLite inspection and file-copy
    backups) -- this raises ValueError with a clear message rather than
    letting an opaque JSONDecodeError surface from inside row conversion.
    """
    if text is None or text == "":
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "stored JSON column is corrupt (not valid JSON): "
            + repr(text[:80])
            + " ("
            + str(error)
            + ")"
        )


def _bank_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a banks row to a plain dict with metadata parsed to an object."""
    return {
        "id": row["id"],
        "category_id": row["category_id"],
        "name": row["name"],
        "language": row["language"],
        "source": row["source"],
        "metadata": _load_json(row["metadata"], {}),
        "created": row["created"],
    }


def _question_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a questions row to a plain dict with JSON columns parsed.

    The four array columns become Python lists; scalar and nullable columns
    pass through unchanged. The result is the canonical question dict shape
    that LOGIC and HTTP operate on.
    """
    return {
        "id": row["id"],
        "bank_id": row["bank_id"],
        "qtype": row["qtype"],
        "question": row["question"],
        "answer": row["answer"],
        "alternatives": _load_json(row["alternatives"], []),
        "distractors": _load_json(row["distractors"], []),
        "hints": _load_json(row["hints"], []),
        "media_url": row["media_url"],
        "tags": _load_json(row["tags"], []),
        "difficulty": row["difficulty"],
        "created": row["created"],
    }


def list_banks(
    connection: sqlite3.Connection,
    category_id: int | None = None,
) -> list[dict]:
    """Return banks as a list of dicts, optionally filtered by category.

    When category_id is None, all banks are returned. Results are ordered by
    name for stable, predictable listing in the bank selector UI.
    """
    if category_id is None:
        cursor = connection.execute("SELECT * FROM banks ORDER BY name")
    else:
        cursor = connection.execute(
            "SELECT * FROM banks WHERE category_id = ? ORDER BY name",
            (category_id,),
        )
    return [_bank_row_to_dict(row) for row in cursor.fetchall()]


def get_bank(connection: sqlite3.Connection, bank_id: int) -> dict | None:
    """Return a single bank dict by id, or None if no such bank exists."""
    cursor = connection.execute(
        "SELECT * FROM banks WHERE id = ?",
        (bank_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _bank_row_to_dict(row)


def insert_bank(
    connection: sqlite3.Connection,
    category_id: int,
    name: str,
    source: str,
    created: str,
    language: str | None = None,
    metadata: dict | None = None,
) -> int:
    """Insert a bank and return its new id.

    The caller supplies the created timestamp as an ISO 8601 string (the
    HTTP layer reads the clock; this layer does not). metadata defaults to
    an empty object. source is one of "manual", "import", or "ai_generated"
    per the data model; this layer stores it verbatim without validating.
    """
    cursor = connection.execute(
        "INSERT INTO banks "
        "(category_id, name, language, source, metadata, created) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            category_id,
            name,
            language,
            source,
            _dump_json(metadata if metadata is not None else {}),
            created,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def delete_bank(connection: sqlite3.Connection, bank_id: int) -> int:
    """Delete a bank and its questions, returning the number of banks removed.

    Questions reference banks by foreign key, so the bank's questions are
    deleted first to satisfy referential integrity. Returns 0 when the bank
    does not exist.
    """
    connection.execute(
        "DELETE FROM questions WHERE bank_id = ?",
        (bank_id,),
    )
    cursor = connection.execute(
        "DELETE FROM banks WHERE id = ?",
        (bank_id,),
    )
    connection.commit()
    return cursor.rowcount


def list_questions(
    connection: sqlite3.Connection,
    bank_id: int,
) -> list[dict]:
    """Return all questions in a bank as a list of dicts, ordered by id."""
    cursor = connection.execute(
        "SELECT * FROM questions WHERE bank_id = ? ORDER BY id",
        (bank_id,),
    )
    return [_question_row_to_dict(row) for row in cursor.fetchall()]


def get_question(
    connection: sqlite3.Connection,
    question_id: int,
) -> dict | None:
    """Return a single question dict by id, or None if no such question."""
    cursor = connection.execute(
        "SELECT * FROM questions WHERE id = ?",
        (question_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _question_row_to_dict(row)


def insert_questions_bulk(
    connection: sqlite3.Connection,
    bank_id: int,
    questions: list[dict],
    created: str,
) -> int:
    """Insert many questions into one bank, returning the count inserted.

    Each question dict supplies the required keys question and answer and
    may supply qtype and the optional fields; missing optional fields fall
    back to sensible defaults (free_response qtype, empty arrays, null media
    and difficulty). All rows share the one created timestamp passed in.
    This is the bulk path used by the import endpoint (parse in C-008 feeds
    this in C-010). Inserts run in a single transaction.
    """
    rows = []
    for question in questions:
        rows.append(
            (
                bank_id,
                question.get("qtype", QTYPE_FREE_RESPONSE),
                question["question"],
                question["answer"],
                _dump_json(question.get("alternatives", [])),
                _dump_json(question.get("distractors", [])),
                _dump_json(question.get("hints", [])),
                question.get("media_url"),
                _dump_json(question.get("tags", [])),
                question.get("difficulty"),
                created,
            )
        )
    connection.executemany(
        "INSERT INTO questions "
        "(bank_id, qtype, question, answer, alternatives, distractors, "
        "hints, media_url, tags, difficulty, created) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    connection.commit()
    return len(rows)


# C-004: Session and response tracking.
# Sessions bracket a run of drilling; responses record each answered
# question within a session. As with C-003, these functions accept and
# return plain Python structures and read no clock -- timestamps arrive as
# ISO 8601 string parameters from the HTTP layer. The responses.correct
# column is stored as INTEGER 0/1 but exposed to callers as a Python bool;
# the correct/incorrect judgment itself is a LOGIC output (C-007) that this
# layer only stores.


def _session_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sessions row to a plain dict with config parsed to an object."""
    return {
        "id": row["id"],
        "category_id": row["category_id"],
        "bank_id": row["bank_id"],
        "config": _load_json(row["config"], {}),
        "started": row["started"],
        "ended": row["ended"],
    }


def _response_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a responses row to a plain dict with correct as a bool.

    The stored INTEGER 0/1 becomes a Python bool; elapsed_ms and question_id
    remain nullable and pass through unchanged.
    """
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "question_id": row["question_id"],
        "question_text": row["question_text"],
        "answer_text": row["answer_text"],
        "user_input": row["user_input"],
        "correct": bool(row["correct"]),
        "elapsed_ms": row["elapsed_ms"],
        "answered": row["answered"],
    }


def start_session(
    connection: sqlite3.Connection,
    category_id: int,
    started: str,
    bank_id: int | None = None,
    config: dict | None = None,
) -> int:
    """Insert a session row and return its new id.

    The caller supplies the started timestamp as an ISO 8601 string. bank_id
    is optional (a category-wide session, e.g. generated arithmetic, has no
    bank). ended is left NULL until end_session is called. config defaults
    to an empty object.
    """
    cursor = connection.execute(
        "INSERT INTO sessions (category_id, bank_id, config, started, ended) "
        "VALUES (?, ?, ?, ?, NULL)",
        (
            category_id,
            bank_id,
            _dump_json(config if config is not None else {}),
            started,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def end_session(
    connection: sqlite3.Connection,
    session_id: int,
    ended: str,
) -> int:
    """Stamp a session's ended timestamp, returning the number of rows updated.

    The caller supplies the ended timestamp as an ISO 8601 string. Returns 0
    when the session does not exist. Already-ended sessions are overwritten
    with the new timestamp; guarding against re-ending is a logic concern,
    not enforced here.
    """
    cursor = connection.execute(
        "UPDATE sessions SET ended = ? WHERE id = ?",
        (ended, session_id),
    )
    connection.commit()
    return cursor.rowcount


def get_session(
    connection: sqlite3.Connection,
    session_id: int,
) -> dict | None:
    """Return a single session dict by id, or None if no such session."""
    cursor = connection.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _session_row_to_dict(row)


def insert_response(
    connection: sqlite3.Connection,
    session_id: int,
    question_text: str,
    answer_text: str,
    user_input: str,
    correct: bool,
    answered: str,
    question_id: int | None = None,
    elapsed_ms: int | None = None,
) -> int:
    """Insert a response row and return its new id.

    question_id is NULL for generated arithmetic questions, which are not
    persisted to the questions table; question_text always carries the
    rendered question so the response is self-describing regardless. The
    correct bool is stored as INTEGER 0/1. answered is an ISO 8601 string
    supplied by the caller. elapsed_ms is optional (column reserved for the
    future timed-rounds feature).
    """
    cursor = connection.execute(
        "INSERT INTO responses "
        "(session_id, question_id, question_text, answer_text, user_input, "
        "correct, elapsed_ms, answered) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            question_id,
            question_text,
            answer_text,
            user_input,
            1 if correct else 0,
            elapsed_ms,
            answered,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def list_responses(
    connection: sqlite3.Connection,
    session_id: int,
) -> list[dict]:
    """Return all responses in a session as a list of dicts, ordered by id."""
    cursor = connection.execute(
        "SELECT * FROM responses WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    return [_response_row_to_dict(row) for row in cursor.fetchall()]


def get_session_correctness(
    connection: sqlite3.Connection,
    session_id: int,
) -> list[bool]:
    """Return the ordered sequence of correct/incorrect for a session.

    C-011 support (pulled forward from the C-019 stats work): returns just
    the correct flags in answer order, as a list of bools. Computing the
    summary (total, accuracy, streak) from this sequence is a LOGIC concern
    (summarize_correctness), keeping the streak logic out of SQL. The broader
    category- and time-windowed stats query is get_responses_for_stats below
    (added in C-019a), summarized by summarize_stats.
    """
    cursor = connection.execute(
        "SELECT correct FROM responses WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    return [bool(row["correct"]) for row in cursor.fetchall()]


def get_responses_for_stats(
    connection: sqlite3.Connection,
    category_id: int | None = None,
    since: str | None = None,
) -> list[dict]:
    """Return response rows for the durable stats view, newest-first.

    C-019a: the broad, cross-session counterpart to get_session_correctness.
    Joins responses -> sessions -> categories so each row carries the owning
    category (the stats view groups by category). This is a pure reader: it
    only filters and returns rows; all aggregation (totals, accuracy, the
    per-category breakdown) is a LOGIC concern (summarize_stats), keeping
    computation out of SQL exactly as the C-011 correctness split does.

    Filters (both optional, AND-combined):
        category_id -- restrict to responses whose session belongs to this
                       category; None means all categories.
        since       -- an ISO 8601 timestamp lower bound (inclusive) compared
                       against responses.answered; None means all time. The
                       caller (HTTP) computes this cutoff from the clock and
                       the requested day window; DATABASE never reads the clock.

    Each returned dict carries: correct (bool), elapsed_ms (int|None),
    answered (str), category_id (int), category_name (str). elapsed_ms is
    SELECTed so the data is available to a future timing feature; v1's
    summarize_stats ignores it. Ordered by answered DESC, id DESC so the most
    recent activity leads (the view renders newest-first).
    """
    clauses = []
    params: list[object] = []
    if category_id is not None:
        clauses.append("s.category_id = ?")
        params.append(category_id)
    if since is not None:
        clauses.append("r.answered >= ?")
        params.append(since)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    cursor = connection.execute(
        "SELECT r.correct AS correct, r.elapsed_ms AS elapsed_ms, "
        "r.answered AS answered, c.id AS category_id, c.name AS category_name "
        "FROM responses r "
        "JOIN sessions s ON r.session_id = s.id "
        "JOIN categories c ON s.category_id = c.id"
        + where
        + " ORDER BY r.answered DESC, r.id DESC",
        params,
    )
    return [
        {
            "correct": bool(row["correct"]),
            "elapsed_ms": row["elapsed_ms"],
            "answered": row["answered"],
            "category_id": row["category_id"],
            "category_name": row["category_name"],
        }
        for row in cursor.fetchall()
    ]


# --- LOGIC ---
# Pure functions only. No IO, no DB access, no HTTP. Functions take plain
# data (numbers, strings, dicts, lists) and return plain data. Randomness
# is the one impurity tolerated here: generation draws from the random
# module, which the spec's generator inherently requires.


# C-006: Operator table, expression generation, evaluation, rendering.
#
# The operator table combines the scalar config from CONFIG (C-005) with the
# callables defined here. Per the layering resolution, the callables live in
# LOGIC and the table is assembled here, once, as a module-level constant.
#
# Expression tree shape (spec section 4.3, runtime only -- never stored):
#   internal node: {"op": str, "left": node, "right": node}
#   leaf:          a plain int
# A node's "op" is an operator symbol; left and right are themselves nodes
# or int leaves, allowing nested expressions.


def _add(left_value: int, right_value: int) -> int:
    """Return the sum of two integers."""
    return left_value + right_value


def _subtract(left_value: int, right_value: int) -> int:
    """Return the difference of two integers."""
    return left_value - right_value


def _multiply(left_value: int, right_value: int) -> int:
    """Return the product of two integers."""
    return left_value * right_value


def _divide(left_value: int, right_value: int) -> int:
    """Return the integer quotient of two integers.

    Generation guarantees the dividend is an exact multiple of the divisor
    (ADR-007), so floor division here is always exact. The divisor is never
    zero because operand generation draws divisors from a positive range.
    """
    return left_value // right_value


# Maps an operator symbol to the function that evaluates it. Defined in
# LOGIC; attached to the operator table below. Keyed by the same symbol
# string that CONFIG uses, which is the join key between the two layers.
_OPERATOR_EVAL_FUNCTIONS = {
    "+": _add,
    "-": _subtract,
    "*": _multiply,
    "/": _divide,
}


def _generate_operands_standard(
    operator: dict,
) -> tuple[int, int]:
    """Generate a (left, right) operand pair for a non-division operator.

    Draws both operands from the operator's inclusive [operand_min,
    operand_max] range and rejects pairs that would form a trivial identity
    (per the operator's forbid_identity list, ADR-007). For subtraction the
    left operand is forced to be at least the right so the result is never
    negative. Rejection-resamples until a valid pair is found.
    """
    minimum = operator["operand_min"]
    maximum = operator["operand_max"]
    forbidden = operator["forbid_identity"]
    while True:
        left_value = random.randint(minimum, maximum)
        right_value = random.randint(minimum, maximum)
        if operator["symbol"] == "-" and left_value < right_value:
            left_value, right_value = right_value, left_value
        # Reject if either operand is a forbidden identity value, or if the
        # two operands are equal in a way that trivializes the result
        # (e.g. x - x = 0). Equal-operand subtraction is treated as trivial.
        if left_value in forbidden or right_value in forbidden:
            continue
        if operator["symbol"] == "-" and left_value == right_value:
            continue
        return left_value, right_value


def _generate_operands_division(
    operator: dict,
) -> tuple[int, int]:
    """Generate a (dividend, divisor) pair guaranteeing an integer quotient.

    Picks the divisor and quotient from the operator's range, then derives
    the dividend as divisor * quotient (ADR-007). This guarantees exact
    division without post-hoc filtering. Rejects quotients in the operator's
    forbid_identity list (a quotient of 1 makes x / x, a trivial identity).
    """
    minimum = operator["operand_min"]
    maximum = operator["operand_max"]
    forbidden = operator["forbid_identity"]
    while True:
        divisor = random.randint(minimum, maximum)
        quotient = random.randint(minimum, maximum)
        if quotient in forbidden:
            continue
        dividend = divisor * quotient
        return dividend, divisor


# Maps an operator symbol to the function that generates its operands.
# Division has its own derivation; all others share the standard generator.
_OPERATOR_OPERAND_GENERATORS = {
    "+": _generate_operands_standard,
    "-": _generate_operands_standard,
    "*": _generate_operands_standard,
    "/": _generate_operands_division,
}


def _build_operator_table() -> dict:
    """Assemble the operator table from CONFIG scalars and LOGIC callables.

    Returns a dict mapping each operator symbol to a dict that merges the
    scalar config (symbol, name, arity, ranges, forbid_identity) with the
    operator's eval and operand-generation functions. Validates that every
    symbol enabled in CONFIG.OPERATOR_SYMBOLS has a corresponding entry in
    CONFIG.OPERATOR_CONFIG and a registered eval and generator function,
    raising ValueError at import time if not -- catching typos early rather
    than at request time.
    """
    config_by_symbol = {entry["symbol"]: entry for entry in OPERATOR_CONFIG}

    for symbol in OPERATOR_SYMBOLS:
        if symbol not in config_by_symbol:
            raise ValueError(
                "enabled operator symbol "
                + repr(symbol)
                + " has no entry in OPERATOR_CONFIG"
            )
        if symbol not in _OPERATOR_EVAL_FUNCTIONS:
            raise ValueError(
                "operator symbol " + repr(symbol) + " has no eval function"
            )
        if symbol not in _OPERATOR_OPERAND_GENERATORS:
            raise ValueError(
                "operator symbol " + repr(symbol) + " has no operand generator"
            )

    table = {}
    for symbol, entry in config_by_symbol.items():
        table[symbol] = {
            "symbol": entry["symbol"],
            "name": entry["name"],
            "arity": entry["arity"],
            "operand_min": entry["operand_min"],
            "operand_max": entry["operand_max"],
            "forbid_identity": entry["forbid_identity"],
            "eval_fn": _OPERATOR_EVAL_FUNCTIONS[symbol],
            "generate_operands": _OPERATOR_OPERAND_GENERATORS[symbol],
        }
    return table


# Built once at import. Module-level constant; not rebuilt per request.
OPERATORS: dict = _build_operator_table()


def generate_expression(
    enabled_symbols: list[str] | None = None,
) -> dict:
    """Generate a single-operator arithmetic expression tree.

    Picks one operator at random from enabled_symbols (defaulting to
    CONFIG.OPERATOR_SYMBOLS), generates a valid operand pair for it, and
    returns an expression tree node. v1 generates flat single-operator
    expressions (two int leaves); the tree shape supports nesting for a
    future enhancement without changing the evaluator or renderer.
    """
    # Distinguish "omitted" (None -> use the default set) from "given but
    # empty" ([] -> an error). Treating [] as falsy and silently falling back
    # to all operators would mask a caller that meant to restrict generation
    # and produced an empty set (e.g. a query string that parsed to no valid
    # symbols).
    symbols = OPERATOR_SYMBOLS if enabled_symbols is None else enabled_symbols
    if not symbols:
        raise ValueError("generate_expression requires at least one operator symbol")
    unknown = [symbol for symbol in symbols if symbol not in OPERATORS]
    if unknown:
        # A caller passed a symbol with no operator-table entry. HTTP already
        # validates ?operators= against OPERATORS, so reaching here means a
        # programming error rather than bad user input -- fail loudly.
        raise ValueError(
            "generate_expression got unknown operator symbols: "
            + ", ".join(repr(symbol) for symbol in unknown)
        )
    symbol = random.choice(symbols)
    operator = OPERATORS[symbol]
    left_value, right_value = operator["generate_operands"](operator)
    return {"op": symbol, "left": left_value, "right": right_value}


def evaluate_expression(node: dict | int) -> int:
    """Evaluate an expression tree to an integer result.

    Recursively evaluates internal nodes by applying the operator's eval
    function to its evaluated operands; integer leaves return themselves.
    Pure and deterministic: the same tree always evaluates to the same
    result.
    """
    if isinstance(node, int):
        return node
    if not isinstance(node, dict) or "op" not in node:
        raise ValueError(
            "evaluate_expression expected an int leaf or an {op,left,right} "
            "node, got " + repr(node)
        )
    if node["op"] not in OPERATORS:
        raise ValueError("evaluate_expression got unknown operator " + repr(node["op"]))
    operator = OPERATORS[node["op"]]
    left_value = evaluate_expression(node["left"])
    right_value = evaluate_expression(node["right"])
    return operator["eval_fn"](left_value, right_value)


def render_expression(node: dict | int) -> str:
    """Render an expression tree as a human-readable infix string.

    Integer leaves render as their digits. Internal nodes render as
    "left symbol right". Nested internal operands are parenthesized to keep
    the rendering unambiguous; flat single-operator expressions (the v1
    case) produce no parentheses. The rendered string is what gets stored
    in responses.question_text.
    """
    if isinstance(node, int):
        return str(node)
    left_text = render_expression(node["left"])
    right_text = render_expression(node["right"])
    if isinstance(node["left"], dict):
        left_text = "(" + left_text + ")"
    if isinstance(node["right"], dict):
        right_text = "(" + right_text + ")"
    return left_text + " " + node["op"] + " " + right_text


# C-007: Answer validation.
# Pure functions. Two public functions: normalize_text (the text
# normalization pipeline) and validate_answer (the dispatcher across qtypes).
# free_response, translate, and identify share one normalized-text path;
# multiple_choice does an exact comparison of server-generated strings;
# arithmetic parses the input as a number and compares within a tolerance.


# Punctuation stripped during normalization. Deliberately excludes hyphens
# and apostrophes: "well-known" vs "wellknown" and "don't" vs "dont" are
# real distinctions in vocabulary drills (decision in C-007 feedback).
_STRIP_PUNCTUATION = ",.!?:;"

# Quote and bracket characters stripped only from the outer edges of the
# text (surrounding quotes and parentheses), not from the interior.
_STRIP_OUTER_CHARACTERS = "\"'()"

# Matches any run of whitespace, for collapsing internal whitespace to a
# single space.
_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalize free-text for lenient answer comparison.

    Pipeline: lowercase; remove the defined interior punctuation set
    (commas, periods, exclamation/question marks, colons, semicolons);
    collapse internal whitespace runs to single spaces; trim outer
    whitespace; strip surrounding quotes and parentheses from the ends.

    Does NOT strip hyphens, apostrophes, or Unicode accents -- these carry
    meaning in language drills (decision in C-007 feedback). Accent
    sensitivity means an answer written with accents must be typed with
    them; a per-bank accent_insensitive flag is a possible future addition.
    """
    lowered = text.lower()
    without_punctuation = "".join(
        character for character in lowered if character not in _STRIP_PUNCTUATION
    )
    collapsed = _WHITESPACE_RUN.sub(" ", without_punctuation).strip()
    return collapsed.strip(_STRIP_OUTER_CHARACTERS).strip()


def _validate_numeric(given: str, expected: str, tolerance: float | None) -> bool:
    """Compare a numeric answer to the expected value within a tolerance.

    Parses both sides as floats. A tolerance of None (or 0) requires exact
    equality; a positive tolerance accepts answers within that absolute
    difference (for future float-producing operators). Non-numeric input
    (e.g. letters typed for a math question) is simply an incorrect answer,
    returning False rather than raising.

    A non-numeric tolerance (e.g. a stray string from a client) is treated as
    no tolerance (exact match) rather than raising, so a malformed optional
    field cannot crash the validator.
    """
    try:
        given_value = float(given.strip())
        expected_value = float(str(expected).strip())
    except (ValueError, AttributeError):
        return False

    numeric_tolerance: float | None
    try:
        numeric_tolerance = None if tolerance is None else float(tolerance)
    except (ValueError, TypeError):
        numeric_tolerance = None

    if numeric_tolerance is None or numeric_tolerance == 0:
        return given_value == expected_value
    return abs(given_value - expected_value) <= numeric_tolerance


def validate_answer(
    expected: str,
    given: str,
    qtype: str,
    alternatives: list[str] | None = None,
    tolerance: float | None = None,
) -> bool:
    """Return whether the user's answer is correct for the given qtype.

    Dispatch by qtype:
      free_response / translate / identify -- normalize both sides and check
        given against [expected] + alternatives, returning True on the first
        normalized match. These three share one path in v1; identify and
        free_response are presently identical, with qtype kept in the
        signature so the paths can diverge later without a signature change.
      multiple_choice -- exact string comparison of given against expected.
        Both strings are server-generated (the server builds the shuffled
        options and the user submits the chosen option's text), so no
        normalization is needed.
      arithmetic -- parse given as a number and compare to expected within
        tolerance.

    An unrecognized qtype returns False rather than raising, so a bad qtype
    can never be silently scored correct.
    """
    if qtype == QTYPE_ARITHMETIC:
        return _validate_numeric(given, expected, tolerance)

    if qtype == QTYPE_MULTIPLE_CHOICE:
        return given == expected

    if qtype in (QTYPE_FREE_RESPONSE, QTYPE_TRANSLATE, QTYPE_IDENTIFY):
        normalized_given = normalize_text(given)
        acceptable = [expected] + (alternatives or [])
        for candidate in acceptable:
            if normalize_text(candidate) == normalized_given:
                return True
        return False

    return False


# C-008: Import parsing (JSON Lines and CSV).
# Pure functions that turn raw uploaded text into a list of canonical
# question dicts ready for DATABASE.insert_questions_bulk (C-003). JSONL is
# the canonical format (ADR-004); CSV is a convenience adapter that produces
# the identical dict shape. Both routes converge through
# _normalize_question_dict, which is the single place that validates required
# fields and fills optional defaults -- so the bulk insert can assume valid
# dicts (decision in C-003).

# Within a CSV cell, array-valued fields (alternatives, distractors, hints,
# tags) are pipe-separated, because the comma is the CSV column delimiter and
# would collide. Example: a tags cell "capital|europe|france" becomes
# ["capital", "europe", "france"].
_CSV_ARRAY_SEPARATOR = "|"

# The array-valued optional fields, handled uniformly by both parsers.
_ARRAY_FIELDS = ("alternatives", "distractors", "hints", "tags")


class ImportParseError(ValueError):
    """Raised when import text cannot be parsed into valid question dicts.

    Carries a human-readable message naming the offending line or field so
    the HTTP layer can report which row of an upload failed.
    """


def _coerce_difficulty(value: object) -> int | None:
    """Coerce a difficulty value to an int in 1..5, or None.

    Accepts None, empty string, or a parseable integer. Returns None for
    absent/empty input. Raises ImportParseError for a present but invalid
    value (non-integer, or out of the 1..5 range from the data model).
    """
    if value is None or value == "":
        return None
    try:
        difficulty = int(value)
    except (ValueError, TypeError):
        raise ImportParseError("difficulty must be an integer 1-5, got " + repr(value))
    if difficulty < 1 or difficulty > 5:
        raise ImportParseError(
            "difficulty must be between 1 and 5, got " + repr(difficulty)
        )
    return difficulty


def _normalize_question_dict(raw: dict) -> dict:
    """Validate and normalize one raw record into a canonical question dict.

    Required fields: question and answer, both non-empty after stripping.
    qtype defaults to free_response and, if present, must be one of QTYPES.
    The four array fields default to empty lists. media_url defaults to None.
    difficulty is coerced to an int 1..5 or None. The returned dict has
    exactly the keys insert_questions_bulk consumes.

    Raises ImportParseError naming the problem when a record is invalid.
    """
    question = raw.get("question")
    answer = raw.get("answer")
    if question is None or str(question).strip() == "":
        raise ImportParseError("record is missing a non-empty 'question'")
    if answer is None or str(answer).strip() == "":
        raise ImportParseError("record is missing a non-empty 'answer'")

    qtype = raw.get("qtype") or QTYPE_FREE_RESPONSE
    if qtype not in QTYPES:
        raise ImportParseError(
            "qtype must be one of " + repr(QTYPES) + ", got " + repr(qtype)
        )

    normalized = {
        "qtype": qtype,
        "question": str(question),
        "answer": str(answer),
        "media_url": raw.get("media_url") or None,
        "difficulty": _coerce_difficulty(raw.get("difficulty")),
    }
    for field in _ARRAY_FIELDS:
        value = raw.get(field)
        if value is None or value == "":
            normalized[field] = []
        elif isinstance(value, list):
            normalized[field] = [str(item) for item in value]
        else:
            raise ImportParseError(
                "field " + repr(field) + " must be a list, got " + repr(value)
            )
    return normalized


def parse_jsonl(text: str) -> list[dict]:
    """Parse JSON Lines import text into a list of canonical question dicts.

    One JSON object per line (ADR-004). Blank lines and lines that are only
    whitespace are skipped, so trailing newlines are harmless. Each object is
    normalized and validated. Raises ImportParseError naming the line number
    (1-based) when a line is not valid JSON or fails validation.
    """
    questions = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "":
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise ImportParseError(
                "line " + str(line_number) + " is not valid JSON: " + str(error)
            )
        if not isinstance(raw, dict):
            raise ImportParseError("line " + str(line_number) + " is not a JSON object")
        try:
            questions.append(_normalize_question_dict(raw))
        except ImportParseError as error:
            raise ImportParseError("line " + str(line_number) + ": " + str(error))
    return questions


def parse_csv(text: str) -> list[dict]:
    """Parse CSV import text into a list of canonical question dicts.

    Expects a header row naming columns; question and answer columns are
    required, the rest optional. Array-valued columns (alternatives,
    distractors, hints, tags) hold pipe-separated values within a single
    cell, since the comma is the column delimiter. Empty cells become absent
    fields (handled as defaults by normalization). Produces the same dict
    shape as parse_jsonl. Raises ImportParseError naming the row number
    (1-based, excluding the header) when a row fails validation.
    """
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return []

    questions = []
    for row_number, row in enumerate(reader, start=1):
        # Split pipe-separated array cells into lists before normalizing.
        prepared: dict = {}
        for key, value in row.items():
            if key is None:
                continue
            if key in _ARRAY_FIELDS:
                if value is None or value.strip() == "":
                    prepared[key] = []
                else:
                    prepared[key] = [
                        item.strip()
                        for item in value.split(_CSV_ARRAY_SEPARATOR)
                        if item.strip() != ""
                    ]
            else:
                prepared[key] = value
        try:
            questions.append(_normalize_question_dict(prepared))
        except ImportParseError as error:
            raise ImportParseError("row " + str(row_number) + ": " + str(error))
    return questions


def parse_import(text: str, file_format: str) -> list[dict]:
    """Dispatch import parsing by format string ("jsonl" or "csv").

    The HTTP layer determines the format from the upload's file extension or
    an explicit format parameter and passes it here. Both formats yield the
    same canonical list of question dicts. Raises ImportParseError for an
    unrecognized format.
    """
    if file_format == "jsonl":
        return parse_jsonl(text)
    if file_format == "csv":
        return parse_csv(text)
    raise ImportParseError(
        "unknown import format " + repr(file_format) + "; expected 'jsonl' or 'csv'"
    )


# C-011 support: session stats summary (pure). Takes the ordered correctness
# sequence from DATABASE.get_session_correctness and computes the summary the
# UI stats bar shows. Streak is the count of consecutive correct answers
# ending at the most recent response (a current run), which is natural in
# Python and awkward in SQL -- hence the split.


def summarize_correctness(correctness: list[bool]) -> dict:
    """Summarize an ordered correct/incorrect sequence for the stats bar.

    Returns a dict with:
        total    -- number of answers
        correct  -- number marked correct
        accuracy -- correct / total as a float, or 0.0 when total is 0
        streak   -- length of the current run of consecutive correct answers
                    counting backward from the most recent answer (0 if the
                    most recent answer was incorrect or there are none)
    Pure and deterministic.
    """
    total = len(correctness)
    # An empty sequence (a session with no answers yet -- the very first
    # question, or a freshly started session) yields zeros and a 0.0 accuracy
    # rather than a division error. This is the time-zero case for every new
    # session and must be handled, not asserted away.
    correct_count = sum(1 for is_correct in correctness if is_correct)
    accuracy = (correct_count / total) if total > 0 else 0.0

    streak = 0
    for is_correct in reversed(correctness):
        if not is_correct:
            break
        streak += 1

    return {
        "total": total,
        "correct": correct_count,
        "accuracy": accuracy,
        "streak": streak,
    }


def summarize_stats(rows: list[dict]) -> dict:
    """Summarize durable cross-session stats for the stats view (C-019a).

    Pure counterpart to the DATABASE reader get_responses_for_stats. Takes the
    response rows it returns (each with at least `correct` and the owning
    `category_id`/`category_name`) and produces the text-only summary the view
    renders (section 9 -- no charts in v1):

        total      -- number of responses in the window/filter
        correct    -- number marked correct
        accuracy   -- correct / total as a float, or 0.0 when total is 0
        categories -- per-category breakdown, a list of
                      {category_id, category_name, total, correct, accuracy},
                      ordered by descending total then category name, so the
                      most-practiced category leads

    The empty case (a fresh database, or a window/filter with no responses)
    yields total 0, accuracy 0.0, and an empty categories list rather than a
    division error -- the time-zero case, handled like summarize_correctness.

    elapsed_ms is deliberately IGNORED in v1: timing collection began at C-018c
    but the timing FEATURE (any per-answer or aggregate timing metric) is a
    deferred future commit. The rows carry elapsed_ms so that feature can use
    it later without a new query; this summary simply does not read it.

    Pure and deterministic (the category ordering is total/name, not input
    order, so the same rows always summarize identically).
    """
    total = len(rows)
    correct_count = sum(1 for row in rows if row.get("correct"))
    accuracy = (correct_count / total) if total > 0 else 0.0

    # Group by category, preserving each category's id and display name.
    grouped: dict[int, dict] = {}
    for row in rows:
        category_id = row.get("category_id")
        bucket = grouped.get(category_id)
        if bucket is None:
            bucket = {
                "category_id": category_id,
                "category_name": row.get("category_name"),
                "total": 0,
                "correct": 0,
            }
            grouped[category_id] = bucket
        bucket["total"] += 1
        if row.get("correct"):
            bucket["correct"] += 1

    categories = []
    for bucket in grouped.values():
        bucket_total = bucket["total"]
        bucket["accuracy"] = (
            (bucket["correct"] / bucket_total) if bucket_total > 0 else 0.0
        )
        categories.append(bucket)

    # Most-practiced first; name as a stable tiebreak so the order is
    # deterministic regardless of dict/input ordering. (name may be None only
    # for malformed data; coerce to "" for a total-safe sort key.)
    categories.sort(key=lambda entry: (-entry["total"], entry["category_name"] or ""))

    return {
        "total": total,
        "correct": correct_count,
        "accuracy": accuracy,
        "categories": categories,
    }


# C-012: bank question selection and payload assembly (pure LOGIC).
# pick_next_question chooses one question dict from a list of candidates
# (fetched by HTTP from DATABASE -- LOGIC never queries the DB). v1 uses
# simple random selection with a soft avoid-recent rule; adaptive selection
# is explicitly out of scope (ADR-005, section 9). build_question_payload
# turns a stored question dict into the client-facing payload, including the
# shuffled options list for multiple_choice (the C-007 options contract).


def pick_next_question(
    candidates: list[dict],
    history: list[int] | None = None,
) -> dict | None:
    """Choose the next question from candidates, softly avoiding recent ids.

    candidates is a list of question dicts (as returned by DATABASE). history
    is a list of recently served question ids, most-recent-last. Returns one
    chosen question dict, or None when candidates is empty.

    Policy (v1, non-adaptive): prefer a uniformly random pick from the
    candidates whose id is not in the recent-history window; if that filtered
    set is empty (e.g. the bank is smaller than the window, or every
    candidate was recently seen), fall back to a uniformly random pick from
    all candidates. This avoids immediate repeats when the bank is large
    enough without ever failing to return a question.
    """
    if not candidates:
        return None

    recent = set(history or [])
    fresh = [question for question in candidates if question.get("id") not in recent]
    pool = fresh if fresh else candidates
    return random.choice(pool)


def build_question_payload(question: dict) -> dict:
    """Build the client-facing question payload from a stored question dict.

    The payload mirrors the shape the arithmetic branch returns, so the
    client handles both uniformly and echoes it back to /api/answer:
        qtype, question_text, expected, question_id, alternatives, media_url
    For multiple_choice, an additional "options" list is included: the
    correct answer plus the question's distractors, shuffled, so the UI can
    render choices. The user submits the chosen option's text, which
    validate_answer exact-matches against expected (C-007 contract). For
    non-multiple_choice types, alternatives carries the also-acceptable
    answers and no options list is present.
    """
    required_keys = ("qtype", "question", "answer", "id")
    missing = [key for key in required_keys if key not in question]
    if missing:
        # A question dict reaching here always comes from DATABASE row
        # conversion, which always supplies these keys. Missing keys mean a
        # programming error upstream, so fail loudly rather than emitting a
        # payload with null question_text/expected that the client would
        # silently mis-grade against.
        raise ValueError(
            "build_question_payload got a question missing required keys: "
            + ", ".join(missing)
        )
    payload = {
        "qtype": question["qtype"],
        "question_text": question["question"],
        "expected": question["answer"],
        "question_id": question["id"],
        "alternatives": question.get("alternatives") or [],
        "media_url": question.get("media_url"),
    }
    # ---- C-018b scaffold: deferred "Option A" (per-question language) -------
    # TTS (C-018a) needs a language code to pronounce a prompt. It currently
    # resolves one CLIENT-SIDE from the selected bank (banks.language, already
    # sent by GET /api/banks), so this payload deliberately carries NO
    # "language" field and the backend stays frozen.
    #
    # The future, more general path ("Option A") is to thread language THROUGH
    # this payload instead. That would matter when language is a property of
    # the QUESTION rather than the bank -- e.g. a single mixed-language bank,
    # or per-row language overrides -- which the client's bank-level lookup
    # cannot express. Shipping it would mean, in rough order:
    #   1. carry a language up to here -- either as question["language"] (new
    #      per-question column or metadata key, a schema/import change) or by
    #      passing the owning bank's language in as a parameter, e.g.
    #          def build_question_payload(question, *, bank_language=None)
    #      and setting payload["language"] = question.get("language")
    #      or bank_language;
    #   2. have the bank-question handler below fetch the bank row (it already
    #      has bank_id) and pass bank_language=bank["language"] (see the
    #      matching comment at the call site);
    #   3. update the section-6 payload contract + the frontend to prefer
    #      payload.language over the client bank lookup when present.
    #
    # This is intentionally NOT built here: it changes the frozen backend and
    # the API contract, so per the working agreement it needs its own spec
    # amendment and commit. Until then, build_question_payload stays a pure
    # function of the question dict alone. See DECISIONS C-018b.
    # -------------------------------------------------------------------------
    if question["qtype"] == QTYPE_MULTIPLE_CHOICE:
        options = [question["answer"]] + list(question.get("distractors") or [])
        random.shuffle(options)
        payload["options"] = options
    return payload


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
    enabled operators. The payload's qtype is the validator-level
    "arithmetic" so /api/answer takes the numeric-comparison branch, and
    question_id is null because generated questions are never stored.
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

        expression = generate_expression(enabled_symbols)
        rendered = render_expression(expression)
        result = evaluate_expression(expression)
        return {
            "qtype": QTYPE_ARITHMETIC,
            "question_text": rendered,
            "expected": str(result),
            "question_id": None,
            "alternatives": None,
            "media_url": None,
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

    # Create the schema and seed categories if needed. Idempotent: safe on
    # every startup. One connection, opened and closed here.
    connection = connect(DATABASE_PATH)
    try:
        init_db(connection)
        connection.commit()
    finally:
        connection.close()

    # Friendly startup line so the operator knows the exact URL to open.
    # (Bottle also prints its own banner.)
    print(
        "drill: serving on http://" + host + ":" + str(port) + "/"
        " (database: " + DATABASE_PATH + ")"
    )

    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
