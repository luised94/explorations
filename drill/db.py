"""DATABASE layer -- IO over a sqlite3 connection (D2 extraction).

Extracted verbatim from drill.py's DATABASE section plus the migration unit that
historically sat in the CONFIG region (S10a: the v2/v3 migration functions run
DDL, so they are DATABASE operations, not config). This layer sits one above the
leaf: config <- db <- logic <- http; main wires. db imports ONLY config
(down-stack, legal) plus stdlib.

Layering contract (CODING_CONVENTIONS): IO over a connection, no business logic.
The clock is read only by utc_now_iso (the primitive) and init_db (baseline
stamp); every other write takes an injected `now` timestamp so the layer stays
otherwise clock-free and deterministic under test.

The guard-weld: _check_migration_version_consistency reads SCHEMA_VERSION (from
config) and runs at import time, so importing db raises immediately if the
MIGRATIONS registry and the version constant drift. This is why db imports a
config scalar -- a legal down-stack edge, not a layering smell.

Behavior-preserving: every symbol is identical to its pre-split definition;
drill.py now imports these from here. The suite is the proof.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone

from config import (
    BASELINE_SCHEMA_VERSION,
    DEFAULT_DATABASE_PATH,
    QTYPE_FREE_RESPONSE,
    SCHEMA_STATEMENTS,
    SCHEMA_VERSION,
    SEED_CATEGORIES,
)


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


def run_migrations(
    connection: sqlite3.Connection,
    now: str,
    target_version: int = None,
    migrations: list = None,
) -> dict:
    """Apply every pending migration in order, each in its own transaction.

    Forward-only and idempotent: applies the registry entries whose version is
    greater than the database's current version and not greater than the
    target, in ascending order, via _apply_one (which owns each transaction so
    a failure rolls that step back and stops the walk at the last good version).
    Running this against an already-current database selects nothing and is a
    safe no-op.

    Parameters:
      now             -- ISO timestamp string stamped into each applied
                         migration's schema_version row. Injected by the caller
                         (MAIN reads the clock; DATABASE does not) so this layer
                         stays clock-free and tests are deterministic.
      target_version  -- highest version to migrate to; defaults to
                         SCHEMA_VERSION. Lets a caller stop short of the latest.
      migrations      -- the (version, description, migrate) registry; defaults
                         to the module MIGRATIONS. Injectable so a test can run
                         the real loop over a deliberately-failing migration
                         without touching the shipped registry.

    Returns an operator-facing dict the caller can report from:
      {"from_version": int, "to_version": int, "applied": [(version, desc), ...]}
    "from_version" is the version before this run (0 when the database is not
    yet baselined, i.e. get_schema_version returned None); "to_version" is the
    version after; "applied" lists what ran, in order. On a no-op, "applied" is
    empty and from_version == to_version.

    This function reads and selects but performs no commit/rollback itself: all
    transactional writes happen inside _apply_one, one per migration.
    """
    if target_version is None:
        target_version = SCHEMA_VERSION
    if migrations is None:
        migrations = MIGRATIONS

    current_raw = get_schema_version(connection)
    # None means no baseline is stamped yet (table absent or empty). The wired
    # path always runs init_db first (which stamps the version-1 baseline), so
    # this layer treats a missing baseline as 0 purely to compute the selection;
    # with migrations layered on version 1, that still skips nothing it should
    # not, and an empty registry makes it a no-op regardless.
    current = 0 if current_raw is None else current_raw

    pending = [
        (version, description, migrate)
        for version, description, migrate in migrations
        if current < version <= target_version
    ]
    pending.sort(key=lambda entry: entry[0])

    applied = []
    for version, description, migrate in pending:
        # On failure _apply_one rolls back this step and re-raises; the loop
        # stops here, leaving the database at the last successfully applied
        # version. The partial "applied" list reflects what did commit.
        _apply_one(connection, version, description, migrate, now)
        applied.append((version, description))

    to_version = applied[-1][0] if applied else current
    return {
        "from_version": current,
        "to_version": to_version,
        "applied": applied,
    }


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


def get_bank_and_question_counts_by_category(
    connection: sqlite3.Connection,
) -> list[dict]:
    """Per-category bank and question counts for the status report (Q2).

    Returns one dict per category in seed (id) order:
        {"category_name": str, "bank_count": int, "question_count": int}
    LEFT JOINs so categories with no banks (and banks with no questions)
    still appear with zero counts -- the status view must show the empty
    categories, not hide them.
    """
    cursor = connection.execute(
        "SELECT c.name AS category_name, "
        "COUNT(DISTINCT b.id) AS bank_count, "
        "COUNT(q.id) AS question_count "
        "FROM categories c "
        "LEFT JOIN banks b ON b.category_id = c.id "
        "LEFT JOIN questions q ON q.bank_id = b.id "
        "GROUP BY c.id "
        "ORDER BY c.id"
    )
    return [
        {
            "category_name": row["category_name"],
            "bank_count": row["bank_count"],
            "question_count": row["question_count"],
        }
        for row in cursor.fetchall()
    ]


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
    IF NOT EXISTS, stamps the BASELINE_SCHEMA_VERSION (1) the first time the
    database is initialized, and seeds any missing categories. init_db builds
    only the baseline; the migration runner advances it to SCHEMA_VERSION. If
    the database already has a version row, it is left untouched (stamp-once).
    """
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)

    existing_version = get_schema_version(connection)
    if existing_version is None:
        connection.execute(
            "INSERT INTO schema_version (version, applied) VALUES (?, ?)",
            (BASELINE_SCHEMA_VERSION, utc_now_iso()),
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

    The four array columns become Python lists; metadata becomes a dict; other
    scalar and nullable columns pass through unchanged. The result is the
    canonical question dict shape that LOGIC and HTTP operate on.

    metadata (added in v2/D1) is the per-question structured-extras object,
    parsed from its JSON text to a dict (default {} for the backfilled rows).
    It is surfaced at the READER level here so get_question/list_questions
    return it; it is deliberately NOT forwarded into build_question_payload's
    client payload (that allowlist guards the frozen section-6 contract). When
    a real consumer needs it client-side or at grading time -- e.g. SM2 /
    adaptive selection, roadmap #7 -- that thread threads it through the
    payload and validation seam. See llm/decisions.md ADR-D1.
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
        "metadata": _load_json(row["metadata"], {}),
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
    difficulty: int | None = None,
    leaf_count: int | None = None,
) -> int:
    """Insert a response row and return its new id.

    question_id is NULL for generated arithmetic questions, which are not
    persisted to the questions table; question_text always carries the
    rendered question so the response is self-describing regardless. The
    correct bool is stored as INTEGER 0/1. answered is an ISO 8601 string
    supplied by the caller. elapsed_ms is optional (column reserved for the
    future timed-rounds feature).

    C-D2g: difficulty and leaf_count are optional (the v3 columns, C-D2f). Both
    default to None -- the honest "not applicable / not recorded" value for bank
    responses, the no-rung arithmetic path, and any caller that does not supply
    them. They are written verbatim; the HTTP layer (post_answer) is responsible
    for validating the echoed values before passing them here.
    """
    cursor = connection.execute(
        "INSERT INTO responses "
        "(session_id, question_id, question_text, answer_text, user_input, "
        "correct, elapsed_ms, answered, difficulty, leaf_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            question_id,
            question_text,
            answer_text,
            user_input,
            1 if correct else 0,
            elapsed_ms,
            answered,
            difficulty,
            leaf_count,
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
    answered (str), category_id (int), category_name (str), difficulty
    (int|None), leaf_count (int|None). elapsed_ms is SELECTed so the data is
    available to a future timing feature; v1's summarize_stats ignores it.
    difficulty and leaf_count (the v3 columns, C-D2f/g) are likewise surfaced
    here so the per-difficulty breakdown (C-D2i) can group on them; summarize_stats
    does not consume them until that commit. Both are NULL for bank responses,
    the no-rung arithmetic path, and any row recorded before #2. Ordered by
    answered DESC, id DESC so the most recent activity leads (the view renders
    newest-first).
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
        "r.answered AS answered, r.difficulty AS difficulty, "
        "r.leaf_count AS leaf_count, c.id AS category_id, c.name AS category_name "
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
            "difficulty": row["difficulty"],
            "leaf_count": row["leaf_count"],
            "category_id": row["category_id"],
            "category_name": row["category_name"],
        }
        for row in cursor.fetchall()
    ]


def get_response_stats_for_bank(
    connection: sqlite3.Connection,
    bank_id: int,
) -> dict:
    """Return per-question response aggregates for one bank.

    B1 (adaptive selection, roadmap #7): the reader feeding
    select_weighted_by_miss_rate. Returns a dict keyed by question_id, each
    value a dict with attempt_count (int), correct_count (int), and
    last_answered (str, the max responses.answered ISO 8601 timestamp).
    Questions with no responses simply have no entry ("absence means never
    attempted", the same semantics the weighted selector's Laplace smoothing
    expects).

    The inner join through questions restricts rows to the requested bank and
    inherently excludes generated-arithmetic responses (their question_id is
    NULL and joins nothing). Pure SQL aggregation, no LOGIC import; the
    weighting math lives in LOGIC and consumes this dict.
    """
    cursor = connection.execute(
        "SELECT r.question_id AS question_id, "
        "COUNT(*) AS attempt_count, "
        "SUM(r.correct) AS correct_count, "
        "MAX(r.answered) AS last_answered "
        "FROM responses r "
        "JOIN questions q ON r.question_id = q.id "
        "WHERE q.bank_id = ? "
        "GROUP BY r.question_id",
        (bank_id,),
    )
    stats_by_question_id = {}
    for row in cursor.fetchall():
        stats_by_question_id[row["question_id"]] = {
            "attempt_count": int(row["attempt_count"]),
            "correct_count": int(row["correct_count"]),
            "last_answered": row["last_answered"],
        }
    return stats_by_question_id


def get_schedule_for_bank(
    connection: sqlite3.Connection,
    bank_id: int,
) -> dict:
    """Return all question_schedule rows for one bank, keyed by question_id.

    C1 (SM2 scheduling, roadmap #7): the reader feeding
    partition_candidates_by_schedule. Each value is a plain dict carrying the
    six schedule fields verbatim (easiness_factor, interval_days,
    repetition_count, due_date, last_review, lapse_count). A question with no
    row is simply absent -- "absence means never scheduled", the semantics the
    partition function keys on. Pure reader; all scheduling math is LOGIC.
    """
    cursor = connection.execute(
        "SELECT qs.question_id AS question_id, "
        "qs.easiness_factor AS easiness_factor, "
        "qs.interval_days AS interval_days, "
        "qs.repetition_count AS repetition_count, "
        "qs.due_date AS due_date, "
        "qs.last_review AS last_review, "
        "qs.lapse_count AS lapse_count "
        "FROM question_schedule qs "
        "JOIN questions q ON qs.question_id = q.id "
        "WHERE q.bank_id = ?",
        (bank_id,),
    )
    schedule_by_question_id = {}
    for row in cursor.fetchall():
        schedule_by_question_id[row["question_id"]] = {
            "question_id": row["question_id"],
            "easiness_factor": row["easiness_factor"],
            "interval_days": row["interval_days"],
            "repetition_count": row["repetition_count"],
            "due_date": row["due_date"],
            "last_review": row["last_review"],
            "lapse_count": row["lapse_count"],
        }
    return schedule_by_question_id


def upsert_schedule_row(
    connection: sqlite3.Connection,
    state_dict: dict,
) -> None:
    """Insert or update one question_schedule row from a schedule state dict.

    C1: the writer the review answer path (C4) and the rebuild use. state_dict
    carries the seven keys of the table (question_id plus the six schedule
    fields), exactly the dict shape advance_schedule_state produces and
    get_schedule_for_bank returns -- one shape end to end, no translation
    layer. The spike's WRITE_SCHEDULE_ROW statement: INSERT with
    ON CONFLICT(question_id) DO UPDATE so first review and every later review
    go through the same statement. Commits, matching the file's writer
    convention (insert_response et al.).
    """
    connection.execute(
        "INSERT INTO question_schedule "
        "(question_id, easiness_factor, interval_days, repetition_count, "
        "due_date, last_review, lapse_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(question_id) DO UPDATE SET "
        "easiness_factor = excluded.easiness_factor, "
        "interval_days = excluded.interval_days, "
        "repetition_count = excluded.repetition_count, "
        "due_date = excluded.due_date, "
        "last_review = excluded.last_review, "
        "lapse_count = excluded.lapse_count",
        (
            state_dict["question_id"],
            state_dict["easiness_factor"],
            state_dict["interval_days"],
            state_dict["repetition_count"],
            state_dict["due_date"],
            state_dict["last_review"],
            state_dict["lapse_count"],
        ),
    )
    connection.commit()


def get_schedule_for_question(
    connection: sqlite3.Connection,
    question_id: int,
) -> dict | None:
    """Return one question_schedule row as a dict, or None if never scheduled.

    C4: the answer path's read -- post_answer holds a question_id but no
    bank_id, so the write path needs a direct single-row reader to feed
    schedule_update_allowed_today and advance_schedule_state. Same dict shape
    as get_schedule_for_bank's values; None reproduces the "absence means
    never scheduled" semantics.
    """
    cursor = connection.execute(
        "SELECT question_id, easiness_factor, interval_days, repetition_count, "
        "due_date, last_review, lapse_count "
        "FROM question_schedule WHERE question_id = ?",
        (question_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return {
        "question_id": row["question_id"],
        "easiness_factor": row["easiness_factor"],
        "interval_days": row["interval_days"],
        "repetition_count": row["repetition_count"],
        "due_date": row["due_date"],
        "last_review": row["last_review"],
        "lapse_count": row["lapse_count"],
    }


def get_new_introduced_today_by_bank(
    connection: sqlite3.Connection,
    today: int,
) -> dict:
    """Count questions that ENTERED the schedule today, grouped by bank.

    C4: the aggregate feeding apply_new_question_throttle's daily budget. A
    question was introduced today exactly when its schedule row shows its
    first-ever graded review happened today with no prior history:
    repetition_count = 1 AND lapse_count = 0 AND last_review = today (the
    spike's verified predicate). today is an ordinal-day integer stamped by
    the caller at the HTTP edge -- DATABASE never reads the clock. Returns
    {bank_id: count}; banks with nothing introduced today are simply absent.
    """
    cursor = connection.execute(
        "SELECT q.bank_id AS bank_id, COUNT(*) AS introduced_count "
        "FROM question_schedule qs "
        "JOIN questions q ON qs.question_id = q.id "
        "WHERE qs.repetition_count = 1 "
        "AND qs.lapse_count = 0 "
        "AND qs.last_review = ? "
        "GROUP BY q.bank_id",
        (today,),
    )
    introduced_by_bank = {}
    for row in cursor.fetchall():
        introduced_by_bank[row["bank_id"]] = int(row["introduced_count"])
    return introduced_by_bank


def get_true_retention(connection: sqlite3.Connection) -> dict:
    """True retention: accuracy over the FIRST graded attempt of each
    question-day (S1). Retries after a miss inflate plain accuracy; the
    scheduling decision only ever sees the first attempt (the once-per-day
    rule), so this is the number that says whether intervals are working.
    The CTE is the spike-verified query (test_migration_and_simulation.py).
    Returns {"retention": float | None, "graded_reviews": int}; retention is
    None when there are no graded reviews at all.
    """
    row = connection.execute(
        "WITH first_attempt_per_day AS ("
        "    SELECT question_id, substr(answered, 1, 10) AS day_text, "
        "           MIN(id) AS first_response_id "
        "    FROM responses "
        "    WHERE question_id IS NOT NULL "
        "    GROUP BY question_id, day_text"
        ") "
        "SELECT AVG(responses.correct) AS retention, "
        "       COUNT(*) AS graded_reviews "
        "FROM first_attempt_per_day "
        "JOIN responses ON responses.id = first_attempt_per_day.first_response_id"
    ).fetchone()
    return {
        "retention": row["retention"],
        "graded_reviews": int(row["graded_reviews"]),
    }


def get_elapsed_ms_samples(connection: sqlite3.Connection) -> list[dict]:
    """All timed responses as (qtype, bank_name, elapsed_ms) sample dicts (S2).

    Feeds summarize_elapsed_percentiles in LOGIC, which computes the per-qtype
    and per-bank median/p90 -- the same trailing medians the future
    timing-derived derive_recall_quality needs as baselines. NULL elapsed_ms
    rows are excluded here (untimed responses carry no signal). qtype lives on
    the question row; responses with question_id NULL are, by construction,
    generated arithmetic, so they group under qtype 'arithmetic' with
    bank_name None.
    """
    cursor = connection.execute(
        "SELECT COALESCE(q.qtype, 'arithmetic') AS qtype, "
        "       b.name AS bank_name, r.elapsed_ms AS elapsed_ms "
        "FROM responses r "
        "LEFT JOIN questions q ON r.question_id = q.id "
        "LEFT JOIN banks b ON q.bank_id = b.id "
        "WHERE r.elapsed_ms IS NOT NULL "
        "ORDER BY r.id"
    )
    samples = []
    for row in cursor.fetchall():
        samples.append(
            {
                "qtype": row["qtype"],
                "bank_name": row["bank_name"],
                "elapsed_ms": int(row["elapsed_ms"]),
            }
        )
    return samples


def get_failure_rows(connection: sqlite3.Connection) -> list[dict]:
    """Wrong answers with what the user ACTUALLY typed (C5 failures view).

    sm2's failures view showed a manually written error note; drill stores
    the real wrong answer on every response, so user_input replaces the note
    -- the actual confusion, recorded for free. One row per incorrect graded
    response on a stored question, newest first; lapse_count joins in from
    the schedule when the question has one (0 when never scheduled).
    """
    cursor = connection.execute(
        "SELECT r.question_id AS question_id, b.name AS bank_name, "
        "       substr(r.answered, 1, 10) AS answered_day, "
        "       r.user_input AS user_input, "
        "       COALESCE(qs.lapse_count, 0) AS lapse_count "
        "FROM responses r "
        "JOIN questions q ON r.question_id = q.id "
        "JOIN banks b ON q.bank_id = b.id "
        "LEFT JOIN question_schedule qs ON qs.question_id = r.question_id "
        "WHERE r.correct = 0 "
        "ORDER BY r.id DESC"
    )
    return [dict(row) for row in cursor.fetchall()]


def get_leech_rows(
    connection: sqlite3.Connection,
    leech_threshold: int,
) -> list[dict]:
    """Questions that keep lapsing (C5 leeches view): schedule rows with
    lapse_count >= leech_threshold, worst first. bank_name replaces sm2's
    domain_of prefix parsing -- the bank is a real column here.
    """
    cursor = connection.execute(
        "SELECT qs.question_id AS question_id, b.name AS bank_name, "
        "       qs.lapse_count AS lapse_count, "
        "       qs.easiness_factor AS easiness_factor, "
        "       qs.last_review AS last_review "
        "FROM question_schedule qs "
        "JOIN questions q ON qs.question_id = q.id "
        "JOIN banks b ON q.bank_id = b.id "
        "WHERE qs.lapse_count >= ? "
        "ORDER BY qs.lapse_count DESC, qs.question_id",
        (leech_threshold,),
    )
    return [dict(row) for row in cursor.fetchall()]


def get_upcoming_schedule_rows(
    connection: sqlite3.Connection,
    today: int,
) -> list[dict]:
    """Schedule rows due strictly after today, soonest first (C5 preview
    view). today is an ordinal stamped by the caller.
    """
    cursor = connection.execute(
        "SELECT qs.question_id AS question_id, b.name AS bank_name, "
        "       qs.easiness_factor AS easiness_factor, "
        "       qs.interval_days AS interval_days, "
        "       qs.repetition_count AS repetition_count, "
        "       qs.due_date AS due_date "
        "FROM question_schedule qs "
        "JOIN questions q ON qs.question_id = q.id "
        "JOIN banks b ON q.bank_id = b.id "
        "WHERE qs.due_date > ? "
        "ORDER BY qs.due_date, qs.question_id",
        (today,),
    )
    return [dict(row) for row in cursor.fetchall()]


# --- migrations (moved from the CONFIG region in D2 -- these run DDL, so they
# are DATABASE operations; S10a). run_migrations above walks this registry. The
# consistency guard reads SCHEMA_VERSION (config) and fires at import time. ---
def _migrate_2_add_questions_metadata(connection: sqlite3.Connection) -> None:
    """v2 (D1): add questions.metadata, a per-question structured-extras column.

    Additive, NOT NULL DEFAULT '{}' so every pre-existing row backfills to an
    empty JSON object with no data loss (the .db file is the user's only copy).
    The runner owns the transaction and stamps schema_version: this fn performs
    ONLY the schema change and must not commit, rollback, or touch the version.

    banks.metadata already exists in the v1 baseline; questions had no metadata
    column, so this fills that gap (ADR-D1). It is a deliberately uncommitted
    extras hatch: later threads (difficulty tuning, SM2 scheduling state, new
    drill types) can prototype per-question state here before any of them earns
    a dedicated, typed column.

    DEFERRED -- grading_kind: the original D1 brief paired a grading_kind column
    with this one. It is intentionally NOT added here. grading_kind would be a
    persisted *grading-policy* axis, but its only real consumer is adaptive
    selection / SM2 (roadmap #7 -> Phase 4), which consumes grading *results*,
    not policy, and whose own shape is still open ("two notions of a review").
    Forward-only migrations make a wrong guess unrollable, so the column waits
    for that real caller. RECONSIDER when #7 lands: decide then whether a
    grading axis belongs on questions, and fold it in with the SM2 scheduling
    fields as a single later migration. See llm/decisions.md ADR-D1.
    """
    connection.execute(
        "ALTER TABLE questions ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'"
    )


def _migrate_3_add_response_difficulty(connection: sqlite3.Connection) -> None:
    """v3 (#2): add responses.difficulty and responses.leaf_count.

    Two NULLABLE INTEGER columns recording, per answered arithmetic question,
    the difficulty rung served and the generated expression's leaf_count. Both
    follow the elapsed_ms precedent (a nullable collected-but-optional column on
    responses): additive, NULL-by-default, so every pre-existing row backfills to
    NULL with no data loss (the .db file is the user's only copy). The runner
    owns the transaction and stamps schema_version; this fn performs ONLY the
    schema change and must not commit, rollback, or touch the version.

    Why NULLABLE and not NOT NULL DEFAULT: these facts only exist for arithmetic
    responses generated under the #2 difficulty path. Bank-question responses and
    every response recorded before this migration have no rung and no expression
    tree, so NULL is the honest "not applicable / not recorded" value -- a numeric
    default (e.g. 0) would be a fake rung and a fake leaf count that the stats
    breakdown (C-D2i) would then have to special-case anyway.

    Why TWO columns (the questions.metadata hatch is NOT used): arithmetic
    responses carry question_id NULL (generated questions are never stored), so
    there is no questions row to hang metadata on -- the uncommitted extras hatch
    is unreachable for exactly the rows that need these facts. Honest recording
    therefore requires real columns on responses (ADR-040). difficulty is the
    served rung (mutable label -- re-means if a later thread retunes the rung
    table); leaf_count is the NON-DRIFTING structural fact (recomputable from
    question_text by re-parsing), which is why the C-D2i breakdown groups by it
    (ADR-038 S11 resolution) rather than by the rung.
    """
    connection.execute("ALTER TABLE responses ADD COLUMN difficulty INTEGER")
    connection.execute("ALTER TABLE responses ADD COLUMN leaf_count INTEGER")


def _migrate_4_add_question_schedule(connection: sqlite3.Connection) -> None:
    """v4 (C1): add question_schedule, the SM2 per-question scheduling state.

    Scheduling state is mutable review state, not content (findings section 2,
    resolving ADR-025 to a separate table): a 1:1 side table keyed on
    question_id keeps the import pipeline (parse_import ->
    _normalize_question_dict -> insert_questions_bulk) entirely ignorant of
    scheduling, makes this migration a single idempotent CREATE TABLE, and
    reproduces sm2's proven "absence of row means never scheduled" semantics.

    All columns NOT NULL: a row exists only after a first graded review,
    created whole with values computed by the pure core (C2), so no schedule
    field is ever NULL and the scheduler needs no NULL handling. due_date and
    last_review are ordinal-day integers (datetime.date.toordinal) -- day
    granularity is the SM2 contract; the timezone/midnight policy lives at the
    HTTP edge where the ordinal is stamped (C4), never here. No backfill: rows
    appear lazily on the write path or via rebuild_schedule_from_response_log.

    The runner owns the transaction and stamps schema_version; this fn performs
    ONLY the schema change and must not commit, rollback, or touch the version.
    """
    connection.execute(
        "CREATE TABLE IF NOT EXISTS question_schedule ("
        "question_id      INTEGER PRIMARY KEY REFERENCES questions(id), "
        "easiness_factor  REAL    NOT NULL, "
        "interval_days    REAL    NOT NULL, "
        "repetition_count INTEGER NOT NULL, "
        "due_date         INTEGER NOT NULL, "
        "last_review      INTEGER NOT NULL, "
        "lapse_count      INTEGER NOT NULL"
        ")"
    )


# Forward-only schema migrations, in ascending version order. Each entry is
# (version, description, migrate) where migrate(connection) performs the schema
# change for that version. The runner (run_migrations) applies every entry whose
# version is greater than the database's current version, each inside its own
# all-or-nothing transaction (see _apply_one).
#
# This list is the ONE place a schema change is expressed from now on. To add a
# migration, a later thread appends a single (version, description, migrate)
# tuple here and bumps SCHEMA_VERSION to match -- it does NOT edit the runner.
#
# v2 (D1) is the first real entry: questions.metadata. Version 1 (today's
# baseline) is produced by init_db, not by an entry here. v3 (#2) adds the
# responses difficulty + leaf_count columns; it is added together with the
# SCHEMA_VERSION bump to 3 so the import-time consistency guard stays satisfied
# (adding one without the other raises -- the guard-weld).
MIGRATIONS: list[tuple[int, str, object]] = [
    (2, "add questions.metadata", _migrate_2_add_questions_metadata),
    (3, "add responses.difficulty and leaf_count", _migrate_3_add_response_difficulty),
    (4, "add question_schedule (SM2 scheduling state, ADR-025)",
     _migrate_4_add_question_schedule),
]


# Consistency guard, checked at import: the highest migration version must equal
# SCHEMA_VERSION, so the constant and the registry cannot silently drift. With
# an empty MIGRATIONS this holds only when SCHEMA_VERSION is the init_db baseline
# (1); once migrations exist, the top entry's version IS the current version.
def _check_migration_version_consistency() -> None:
    """Raise at import if MIGRATIONS and SCHEMA_VERSION disagree.

    Two ways they can drift, both caught here:
      - a migration is added without bumping SCHEMA_VERSION (top > constant), or
        SCHEMA_VERSION is bumped without adding the migration (constant > top);
      - migration versions are not the strictly ascending 2..N that the runner's
        ordered, gap-free forward walk assumes.
    """
    versions = [version for version, _description, _migrate in MIGRATIONS]
    if versions != sorted(versions) or len(set(versions)) != len(versions):
        raise RuntimeError(
            "MIGRATIONS versions must be strictly ascending and unique: "
            + repr(versions)
        )
    # Migrations layer on top of the init_db baseline (version 1): an empty
    # registry means the DB never advances past 1, so SCHEMA_VERSION must be 1;
    # a non-empty registry must be the gap-free sequence 2..SCHEMA_VERSION with
    # its top entry equal to SCHEMA_VERSION. Both arms reduce to: versions ==
    # range(2, SCHEMA_VERSION + 1). Checking that single equality also catches a
    # constant bumped without a matching migration (and vice versa), including
    # the empty-registry case the earlier per-arm form let slip through.
    expected = list(range(2, SCHEMA_VERSION + 1))
    if versions != expected:
        raise RuntimeError(
            "SCHEMA_VERSION ("
            + str(SCHEMA_VERSION)
            + ") and MIGRATIONS disagree: migrations layer on the version-1 "
            + "init_db baseline, so MIGRATIONS versions must be the gap-free "
            + "sequence "
            + repr(expected)
            + "; got "
            + repr(versions)
            + " (bump SCHEMA_VERSION and add the migration together)"
        )


_check_migration_version_consistency()
