"""SM-2 spaced repetition review tool.

Single-file, banner-sectioned topology. Section order is binding and purity
decreases monotonically downward:

    TYPES AND CONSTANTS   plain data definitions, defaults (read only in ENTRY)
    ALGORITHM             pure: SM-2 math, grading, domain derivation
    PARSER                pure core (parse_text) + thin file wrapper
    SCHEDULER             pure: due-queue throttling
    VIEWS                 pure: strings/rows in, strings out          [phase 3]
    STORE                 DB edge: conn in, plain data out; no print/exit
    SHELL                 all terminal IO, input(), clock capture
    ENTRY POINT           argparse, composition root, sys.exit

Purity fence (grep-enforced): input(, sys.exit, print(, date.today,
time.monotonic, sqlite3, terminal_output. may not appear above the STORE
banner (sqlite3) / SHELL banner (everything else).

Deliberate denormalizations (A2 boundary, named protocol):
  review_log.domain     derived from item_id at insert, never updated.
  review_log.sm2_grade  derived from grade at insert, never updated.
  items.source          copied from file at first insert, never updated;
                        the exercise file remains the source of truth.
"""

import argparse
import datetime
import os
import re
import sqlite3
import sys
import time
from typing import NamedTuple

import terminal_output

# =============================================================================
# TYPES AND CONSTANTS
# =============================================================================
# Defaults only. Nothing below ENTRY POINT may read these as ambient config;
# they flow downward as parameters from main().

DEFAULT_DATABASE_PATH: str = "data/sm2.db"
DEFAULT_EXERCISES_DIR: str = "exercises"
LEECH_THRESHOLD: int = 3
TOTAL_NEW_MAX: int = 9
MIN_PER_DOMAIN: int = 1
MAX_REVIEWS: int = 100
BUSY_TIMEOUT_MS: int = 5000


class Exercise(NamedTuple):
    """One parsed exercise item. Immutable per-run value; files own it."""

    item_id: str
    content: str
    criteria: str
    tags: tuple[str, ...]
    source: str


class ItemState(NamedTuple):
    """One row of the items table: the SM-2 state vector."""

    item_id: str
    easiness_factor: float
    interval_days: float
    repetition_count: int
    due_date: int
    last_review: int
    lapse_count: int


class DueItem(NamedTuple):
    """Queue entry: the minimum the scheduler needs to order and throttle."""

    item_id: str
    repetition_count: int
    due_date: int


class ReviewOutcome(NamedTuple):
    """Complete result of grading one item: the new state plus the log row.

    This is the unit commit_review() executes atomically. Building it is
    pure (grade_item); executing it is the store's job.
    """

    item_id: str
    domain: str
    grade: int
    sm2_grade: int
    review_date: int
    elapsed_days: int
    easiness_factor_before: float
    easiness_factor_after: float
    interval_days_before: float
    interval_days_after: float
    repetition_count_before: int
    repetition_count_after: int
    lapse_count_after: int
    due_date: int
    error_note: str | None
    answer_text: str | None
    response_seconds: float | None


# =============================================================================
# ALGORITHM (pure)
# =============================================================================

USER_GRADE_TO_SM2_GRADE: dict[int, int] = {0: 1, 1: 3, 2: 5}


def domain_of(item_id: str) -> str:
    """Derive the domain from an item id: the segment before the first dash."""
    return item_id.split("-")[0]


def sm2_update(
    grade: int,
    easiness_factor: float,
    interval_days: float,
    repetition_count: int,
    lapse_count: int,
    review_date: int,
) -> dict[str, float | int]:
    sm2_grade: int = USER_GRADE_TO_SM2_GRADE[grade]
    ef_delta_inner: float = 0.08 + (5 - sm2_grade) * 0.02
    ef_delta: float = 0.1 - (5 - sm2_grade) * ef_delta_inner
    raw_easiness_factor: float = easiness_factor + ef_delta
    new_easiness_factor: float = max(1.3, min(3.0, raw_easiness_factor))
    if sm2_grade < 3:
        new_repetition_count: int = 0
        new_interval_days: float = 1.0
        new_lapse_count: int = lapse_count + 1
    else:
        new_lapse_count = lapse_count
        if repetition_count == 0:
            new_interval_days = 1.0
        elif repetition_count == 1:
            new_interval_days = 6.0
        else:
            new_interval_days = interval_days * new_easiness_factor
        new_repetition_count = repetition_count + 1
    new_due_date: int = review_date + round(new_interval_days)
    return {
        "easiness_factor": new_easiness_factor,
        "repetition_count": new_repetition_count,
        "interval_days": new_interval_days,
        "lapse_count": new_lapse_count,
        "due_date": new_due_date,
    }


def grade_item(
    state: ItemState,
    grade: int,
    today: int,
    error_note: str | None = None,
    answer_text: str | None = None,
    response_seconds: float | None = None,
) -> ReviewOutcome:
    """Pure apply step: current state + grade -> the full review outcome."""
    if state.last_review > 0:
        elapsed_days: int = today - state.last_review
    else:
        elapsed_days = 0
    update = sm2_update(
        grade,
        state.easiness_factor,
        state.interval_days,
        state.repetition_count,
        state.lapse_count,
        today,
    )
    return ReviewOutcome(
        item_id=state.item_id,
        domain=domain_of(state.item_id),
        grade=grade,
        sm2_grade=USER_GRADE_TO_SM2_GRADE[grade],
        review_date=today,
        elapsed_days=elapsed_days,
        easiness_factor_before=state.easiness_factor,
        easiness_factor_after=float(update["easiness_factor"]),
        interval_days_before=state.interval_days,
        interval_days_after=float(update["interval_days"]),
        repetition_count_before=state.repetition_count,
        repetition_count_after=int(update["repetition_count"]),
        lapse_count_after=int(update["lapse_count"]),
        due_date=int(update["due_date"]),
        error_note=error_note,
        answer_text=answer_text,
        response_seconds=response_seconds,
    )


# =============================================================================
# PARSER (pure core + thin file wrapper)
# =============================================================================

ITEM_DELIMITER_PATTERN: re.Pattern[str] = re.compile(r"^@@@ id:\s*(.+)$")

# 'after:' (prerequisite gating) was removed; lines using it are discarded
# with a warning so stale files surface instead of silently feeding content.
DISCARDED_KEY_PREFIXES: tuple[str, ...] = ("after:",)


def parse_text(filename: str, text: str) -> tuple[list[Exercise], list[str]]:
    """Parse one exercise file's text. Pure: no IO, no duplicate-id policy
    across files (the wrapper owns that).

    Returns (exercises, warnings). Raises ValueError on a duplicate id
    within the same text.
    """
    warnings: list[str] = []
    blocks: list[tuple[str, list[str]]] = []
    current_id: str = ""
    current_lines: list[str] = []
    for line in text.splitlines():
        delimiter_match = ITEM_DELIMITER_PATTERN.match(line)
        if delimiter_match is not None:
            if current_id != "":
                blocks.append((current_id, current_lines))
            current_id = delimiter_match.group(1).strip()
            current_lines = []
        elif current_id != "":
            current_lines.append(line)
    if current_id != "":
        blocks.append((current_id, current_lines))

    exercises: list[Exercise] = []
    seen_ids: set[str] = set()
    for item_id, block_lines in blocks:
        if item_id in seen_ids:
            raise ValueError(f"duplicate item id '{item_id}' in '{filename}'")
        seen_ids.add(item_id)
        criteria: str = ""
        tags: list[str] = []
        source: str = ""
        content_lines: list[str] = []
        for line in block_lines:
            if line.startswith("criteria:"):
                criteria = line[len("criteria:") :].strip()
            elif line.startswith("tags:"):
                raw_tags = line[len("tags:") :].strip()
                tags = [t.strip() for t in raw_tags.split(",") if t.strip() != ""]
            elif line.startswith("source:"):
                source = line[len("source:") :].strip()
            elif line.startswith(DISCARDED_KEY_PREFIXES):
                key = line.split(":", 1)[0]
                warnings.append(
                    f"{filename}: item '{item_id}': '{key}:' is no longer supported; line discarded"
                )
            else:
                content_lines.append(line)
        exercises.append(
            Exercise(
                item_id=item_id,
                content="\n".join(content_lines).strip(),
                criteria=criteria,
                tags=tuple(tags),
                source=source,
            )
        )
    return exercises, warnings


def parse_exercises(directory_path: str) -> tuple[dict[str, Exercise], list[str]]:
    """Read every *.md file in directory_path and parse it.

    The only file IO in the parser section. Cross-file duplicate ids raise
    ValueError naming both files.
    """
    markdown_filenames = sorted(f for f in os.listdir(directory_path) if f.endswith(".md"))
    exercises: dict[str, Exercise] = {}
    seen_in: dict[str, str] = {}
    all_warnings: list[str] = []
    for filename in markdown_filenames:
        filepath = os.path.join(directory_path, filename)
        with open(filepath, "r", encoding="utf-8") as file_handle:
            raw_text = file_handle.read()
        file_exercises, warnings = parse_text(filepath, raw_text)
        all_warnings.extend(warnings)
        for exercise in file_exercises:
            if exercise.item_id in seen_in:
                raise ValueError(
                    f"duplicate item id '{exercise.item_id}' in "
                    f"'{filepath}' and '{seen_in[exercise.item_id]}'"
                )
            seen_in[exercise.item_id] = filepath
            exercises[exercise.item_id] = exercise
    return exercises, all_warnings


# =============================================================================
# SCHEDULER (pure)
# =============================================================================


def apply_throttle_and_cap(
    due_queue: list[DueItem],
    today_new_by_domain: dict[str, int],
    total_new_max: int,
    min_per_domain: int,
    max_reviews: int,
) -> list[str]:
    """Order-preserving throttle: all due reviews pass through; new items are
    capped at total_new_max with a min_per_domain floor reserved first.
    """
    # pass 1: reserve floor items per domain
    reserved_item_ids: set[str] = set()
    reserved_count_by_domain: dict[str, int] = {}
    for due_item in due_queue:
        if due_item.repetition_count == 0:
            domain = domain_of(due_item.item_id)
            already_reviewed = today_new_by_domain.get(domain, 0)
            already_reserved = reserved_count_by_domain.get(domain, 0)
            if min_per_domain - already_reviewed - already_reserved > 0:
                reserved_item_ids.add(due_item.item_id)
                reserved_count_by_domain[domain] = already_reserved + 1
    # pass 2: build result - reserved slots pre-allocated from budget
    already_new_today: int = sum(today_new_by_domain.values())
    non_reserved_budget: int = max(0, total_new_max - len(reserved_item_ids) - already_new_today)
    non_reserved_added: int = 0
    result: list[str] = []
    for due_item in due_queue:
        if due_item.repetition_count > 0:
            result.append(due_item.item_id)
        elif due_item.item_id in reserved_item_ids:
            result.append(due_item.item_id)
        elif non_reserved_added < non_reserved_budget:
            result.append(due_item.item_id)
            non_reserved_added += 1
    return result[:max_reviews]


# =============================================================================
# VIEWS (pure)  -- placeholder; table row-builders land in Phase 3
# =============================================================================
# Phase 3 extracts the four inline table printers in SHELL into
# (headers, rows) builders plus one render_table(). Until then the shell
# carries the old inline rendering, adapted only for NamedTuple access.


# =============================================================================
# STORE (DB edge: conn in, plain data out; no printing, no exits)
# =============================================================================


def connect(database_path: str) -> sqlite3.Connection:
    """Open the database in explicit-transaction mode with concurrency
    protection: WAL + busy timeout; writes use BEGIN IMMEDIATE.
    """
    conn = sqlite3.connect(database_path, isolation_level=None)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute(f"PRAGMA busy_timeout={BUSY_TIMEOUT_MS}")
    return conn


def init_schema(conn: sqlite3.Connection) -> None:
    """Create tables if absent. Schema is frozen: byte-compatible with
    databases created by the pre-refactor tool."""
    conn.execute("""
        CREATE TABLE IF NOT EXISTS items (
            item_id           TEXT PRIMARY KEY,
            easiness_factor   REAL DEFAULT 2.5,
            interval_days     REAL DEFAULT 0.0,
            repetition_count  INTEGER DEFAULT 0,
            due_date          INTEGER,
            last_review       INTEGER DEFAULT 0,
            lapse_count       INTEGER DEFAULT 0,
            source            TEXT DEFAULT ''
        )
    """)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS review_log (
            id                        INTEGER PRIMARY KEY AUTOINCREMENT,
            item_id                   TEXT,
            grade                     INTEGER,
            sm2_grade                 INTEGER,
            review_date               INTEGER,
            elapsed_days              INTEGER,
            easiness_factor_before    REAL,
            easiness_factor_after     REAL,
            interval_days_before      REAL,
            interval_days_after       REAL,
            repetition_count_before   INTEGER,
            domain                    TEXT,
            error_note                TEXT,
            answer_text               TEXT,
            response_seconds          REAL
        )
    """)
    conn.execute("CREATE INDEX IF NOT EXISTS idx_due_date ON items(due_date)")


def reconcile(conn: sqlite3.Connection, exercises: dict[str, Exercise], today: int) -> set[str]:
    """Insert items present in files but absent from the DB. Returns the
    inserted ids. source is copied at insert (write-once denormalization)."""
    database_ids = {row[0] for row in conn.execute("SELECT item_id FROM items")}
    new_item_ids = set(exercises) - database_ids
    if new_item_ids:
        conn.execute("BEGIN IMMEDIATE")
        for item_id in sorted(new_item_ids):
            conn.execute(
                "INSERT INTO items (item_id, due_date, source) VALUES (?, ?, ?)",
                (item_id, today, exercises[item_id].source),
            )
        conn.execute("COMMIT")
    return new_item_ids


def fetch_due_queue(conn: sqlite3.Connection, item_ids: set[str], today: int) -> list[DueItem]:
    """Items from item_ids due on or before today, ordered by due date."""
    if not item_ids:
        return []
    ids = sorted(item_ids)
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT item_id, repetition_count, due_date FROM items "
        f"WHERE item_id IN ({placeholders}) AND due_date <= ? "
        f"ORDER BY due_date ASC",
        ids + [today],
    ).fetchall()
    return [DueItem(*row) for row in rows]


def fetch_today_new_by_domain(conn: sqlite3.Connection, today: int) -> dict[str, int]:
    """How many first-time items were already reviewed today, per domain."""
    rows = conn.execute(
        "SELECT domain, COUNT(*) FROM review_log "
        "WHERE review_date = ? AND repetition_count_before = 0 "
        "GROUP BY domain",
        (today,),
    ).fetchall()
    return {row[0]: row[1] for row in rows}


def fetch_item_state(conn: sqlite3.Connection, item_id: str) -> ItemState:
    row = conn.execute(
        "SELECT item_id, easiness_factor, interval_days, repetition_count, "
        "due_date, last_review, lapse_count FROM items WHERE item_id = ?",
        (item_id,),
    ).fetchone()
    if row is None:
        raise KeyError(f"item '{item_id}' not found in items table")
    return ItemState(*row)


def fetch_reviews_today_count(conn: sqlite3.Connection, today: int) -> int:
    return conn.execute(
        "SELECT COUNT(*) FROM review_log WHERE review_date = ?", (today,)
    ).fetchone()[0]


def commit_review(conn: sqlite3.Connection, outcome: ReviewOutcome) -> None:
    """Execute one ReviewOutcome atomically: state update + log insert in a
    single transaction. Crash-state analysis: with one transaction the only
    partial state is 'nothing happened', which is detectable (item still due)
    and self-healing (review it again). The pre-refactor two-commit sequence
    could advance an item without logging it -- silent history loss."""
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute(
            "UPDATE items SET easiness_factor=?, interval_days=?, "
            "repetition_count=?, due_date=?, last_review=?, lapse_count=? "
            "WHERE item_id=?",
            (
                outcome.easiness_factor_after,
                outcome.interval_days_after,
                outcome.repetition_count_after,
                outcome.due_date,
                outcome.review_date,
                outcome.lapse_count_after,
                outcome.item_id,
            ),
        )
        conn.execute(
            "INSERT INTO review_log ("
            "item_id, grade, sm2_grade, review_date, elapsed_days, "
            "easiness_factor_before, easiness_factor_after, "
            "interval_days_before, interval_days_after, "
            "repetition_count_before, domain, error_note, answer_text, "
            "response_seconds"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                outcome.item_id,
                outcome.grade,
                outcome.sm2_grade,
                outcome.review_date,
                outcome.elapsed_days,
                outcome.easiness_factor_before,
                outcome.easiness_factor_after,
                outcome.interval_days_before,
                outcome.interval_days_after,
                outcome.repetition_count_before,
                outcome.domain,
                outcome.error_note,
                outcome.answer_text,
                outcome.response_seconds,
            ),
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise


# =============================================================================
# SHELL (all terminal IO, input(), clock capture)
# =============================================================================
# Carried over from the monolith in Phase 1, adapted to NamedTuples and the
# store functions. Phase 3 replaces the inline table printing with VIEWS;
# Phase 4 finishes the T5 sandwich restructuring of the review loop.


def show_failures(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT r.item_id, r.domain, r.review_date, r.error_note, "
        "       i.lapse_count "
        "FROM review_log r "
        "JOIN items i ON r.item_id = i.item_id "
        "WHERE r.grade = 0 "
        "  AND r.error_note IS NOT NULL "
        "  AND r.id = ( "
        "      SELECT MAX(id) FROM review_log "
        "      WHERE item_id = r.item_id "
        "        AND grade = 0 "
        "        AND error_note IS NOT NULL "
        "  ) "
        "ORDER BY r.review_date DESC"
    ).fetchall()
    if len(rows) == 0:
        print("no recorded failures with notes.")
        return
    id_width = max(len("item_id"), max(len(r[0]) for r in rows))
    print(f"{'item_id':<{id_width}}  {'domain':<6}  {'date':<10}  {'lapses':>6}  error_note")
    for item_id, domain, review_date, error_note, lapse_count in rows:
        date_string = datetime.date.fromordinal(review_date).isoformat()
        print(
            f"{item_id:<{id_width}}  {domain:<6}  {date_string:<10}  {lapse_count:>6}  {error_note}"
        )


def show_leeches(conn: sqlite3.Connection, today: int) -> None:
    rows = conn.execute(
        "SELECT item_id, lapse_count, easiness_factor, last_review "
        "FROM items WHERE lapse_count >= ? "
        "ORDER BY lapse_count DESC, easiness_factor ASC",
        (LEECH_THRESHOLD,),
    ).fetchall()
    if len(rows) == 0:
        print(f"no leeches found (lapse_count < {LEECH_THRESHOLD} for all items).")
        return
    id_width = max(len("item_id"), max(len(r[0]) for r in rows))
    print(f"{'item_id':<{id_width}}  {'domain':<6}  {'lapses':>6}  {'EF':>5}  days_since")
    for item_id, lapse_count, easiness_factor, last_review in rows:
        days_since = "never" if last_review == 0 else str(today - last_review)
        print(
            f"{item_id:<{id_width}}  {domain_of(item_id):<6}  "
            f"{lapse_count:>6}  {easiness_factor:>5.2f}  {days_since}"
        )


def show_preview(conn: sqlite3.Connection, item_ids: set[str], today: int) -> None:
    if not item_ids:
        print("no upcoming items found.")
        return
    ids = sorted(item_ids)
    placeholders = ",".join("?" * len(ids))
    rows = conn.execute(
        f"SELECT item_id, easiness_factor, interval_days, "
        f"repetition_count, due_date FROM items "
        f"WHERE item_id IN ({placeholders}) AND due_date > ? "
        f"ORDER BY due_date ASC LIMIT 20",
        ids + [today],
    ).fetchall()
    if len(rows) == 0:
        print("no upcoming items found.")
        return
    id_width = max(len("item_id"), max(len(r[0]) for r in rows))
    print(f"{'item_id':<{id_width}}  {'domain':<6}  {'due_in':>6}  {'rep':>3}  {'EF':>5}")
    for item_id, easiness_factor, _interval, repetition_count, due_date in rows:
        print(
            f"{item_id:<{id_width}}  {domain_of(item_id):<6}  "
            f"{due_date - today:>6}  {repetition_count:>3}  {easiness_factor:>5.2f}"
        )


def show_dry_run(conn: sqlite3.Connection, review_queue: list[str], today: int) -> None:
    print(f"dry run: {len(review_queue)} item(s) in review queue")
    if len(review_queue) == 0:
        return
    placeholders = ",".join("?" * len(review_queue))
    rows = conn.execute(
        f"SELECT item_id, easiness_factor, interval_days, "
        f"repetition_count, due_date FROM items "
        f"WHERE item_id IN ({placeholders})",
        review_queue,
    ).fetchall()
    state = {row[0]: row for row in rows}
    id_width = max(len("item_id"), max(len(i) for i in review_queue))
    print(
        f"{'item_id':<{id_width}}  "
        f"{'domain':<6}  {'rep':>3}  {'EF':>5}  "
        f"{'interval':>8}  days_overdue"
    )
    for item_id in review_queue:
        _, ef, interval, rep, due_date = state[item_id]
        print(
            f"{item_id:<{id_width}}  {domain_of(item_id):<6}  {rep:>3}  "
            f"{ef:>5.2f}  {interval:>8.1f}  {today - due_date}"
        )


def prompt_answer() -> str | None:
    """Tiny labeled-impure IO (T7): read the free-form answer."""
    terminal_output.emit("Your answer (enter to skip):")
    raw = input("").strip()
    return raw if raw != "" else None


def prompt_grade() -> int:
    """Tiny labeled-impure IO (T7): loop until a legal grade is entered."""
    while True:
        terminal_output.emit("Grade (0/1/2):")
        raw = input("").strip()
        if raw in ("0", "1", "2"):
            return int(raw)
        terminal_output.emit("Invalid grade. Enter 0, 1, or 2.")


def prompt_error_note() -> str | None:
    """Tiny labeled-impure IO (T7): optional what-went-wrong note."""
    terminal_output.emit("What went wrong? (enter to skip):")
    raw = input("").strip()
    return raw if raw != "" else None


def run_review_session(
    conn: sqlite3.Connection,
    exercises: dict[str, Exercise],
    review_queue: list[str],
    today: int,
    rehearse: bool,
) -> None:
    review_count = 0
    pass_count = 0
    fail_count = 0
    new_count = 0
    try:
        for item_id in review_queue:
            exercise = exercises[item_id]
            if rehearse:
                progress = (
                    f"{review_count + 1} / {len(review_queue)}  "
                    + terminal_output.format_label("rehearse")
                )
            else:
                progress = f"{review_count + 1} / {len(review_queue)}"
            terminal_output.clear_screen()
            terminal_output.emit(
                terminal_output.format_card(
                    header_left=progress,
                    header_right=domain_of(item_id),
                    body=exercise.content,
                    footer=None,
                )
            )
            response_start = time.monotonic()
            answer_text = prompt_answer()
            if exercise.criteria != "":
                terminal_output.emit(terminal_output.format_separator())
                terminal_output.emit(terminal_output.format_label("criteria"))
                terminal_output.emit(terminal_output.wrap_text(exercise.criteria))
            terminal_output.emit(
                terminal_output.format_choices(
                    [("0", "failed"), ("1", "passed with effort"), ("2", "easy, fluent")]
                )
            )
            grade = prompt_grade()
            response_seconds = round(time.monotonic() - response_start, 2)
            error_note = prompt_error_note() if grade == 0 else None

            state = fetch_item_state(conn, item_id)
            outcome = grade_item(state, grade, today, error_note, answer_text, response_seconds)
            if not rehearse:
                commit_review(conn, outcome)

            duration_string = terminal_output.format_duration(outcome.due_date - today)
            if rehearse:
                if grade == 0:
                    terminal_output.emit(f"Would fail. Would return in {duration_string}.")
                else:
                    terminal_output.emit(f"Would pass. Next review in {duration_string}.")
            else:
                if grade == 0:
                    terminal_output.emit(f"Failed. Returns in {duration_string}.")
                else:
                    terminal_output.emit(f"Passed. Next review in {duration_string}.")
            review_count += 1
            if grade == 0:
                fail_count += 1
            else:
                pass_count += 1
            if state.repetition_count == 0:
                new_count += 1
    except KeyboardInterrupt:
        print("")
        print("Session interrupted.")
    finally:
        terminal_output.msg_info(
            f"Reviewed: {review_count}  "
            f"Passed: {pass_count}  "
            f"Failed: {fail_count}  "
            f"New: {new_count}"
        )
        if rehearse:
            terminal_output.msg_success("session complete (rehearse - nothing written)")
        else:
            terminal_output.msg_success("session complete")
        if fail_count > 0:
            terminal_output.msg_info(f"{fail_count} item(s) return tomorrow")


# =============================================================================
# ENTRY POINT
# =============================================================================


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="SM-2 spaced repetition review tool.")
    parser.add_argument(
        "--new-max",
        type=int,
        default=TOTAL_NEW_MAX,
        help="maximum new items per session (default: 9)",
    )
    parser.add_argument(
        "--min-per-domain",
        type=int,
        default=MIN_PER_DOMAIN,
        help="minimum new items guaranteed per domain (default: 1)",
    )
    parser.add_argument(
        "--max-reviews",
        type=int,
        default=MAX_REVIEWS,
        help="hard session cap on total items reviewed (default: 100)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the review queue and exit without reviewing",
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="show upcoming items not yet due and exit",
    )
    parser.add_argument(
        "--rehearse",
        action="store_true",
        help="run review session without writing to database",
    )
    parser.add_argument(
        "--show-failures",
        action="store_true",
        help="show most recent grade-0 rows with error notes and exit",
    )
    parser.add_argument(
        "--show-leeches",
        action="store_true",
        help="show items with lapse_count >= LEECH_THRESHOLD and exit",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_argument_parser().parse_args(argv)

    terminal_output.set_verbosity(3)
    terminal_output.set_layout(max_width=76, align="center")

    # Ambient inputs captured once, here, and only here.
    today: int = datetime.date.today().toordinal()
    database_path: str = DEFAULT_DATABASE_PATH
    exercises_dir: str = DEFAULT_EXERCISES_DIR

    if not os.path.isdir(os.path.dirname(database_path)):
        print(f"error: {os.path.dirname(database_path)}/ directory not found")
        return 1

    if args.show_failures or args.show_leeches:
        conn = connect(database_path)
        init_schema(conn)
        if args.show_failures:
            show_failures(conn)
        if args.show_leeches:
            show_leeches(conn, today)
        return 0

    if not os.path.isdir(exercises_dir):
        print(f"error: {exercises_dir}/ directory not found")
        return 1

    conn = connect(database_path)
    init_schema(conn)

    exercises, parse_warnings = parse_exercises(exercises_dir)
    for warning in parse_warnings:
        terminal_output.msg_warn(warning)
    item_ids = set(exercises)

    reconcile(conn, exercises, today)

    if args.preview:
        show_preview(conn, item_ids, today)
        return 0

    due_queue = fetch_due_queue(conn, item_ids, today)
    today_new = fetch_today_new_by_domain(conn, today)
    review_queue = apply_throttle_and_cap(
        due_queue, today_new, args.new_max, args.min_per_domain, args.max_reviews
    )

    if args.dry_run:
        show_dry_run(conn, review_queue, today)
        return 0

    if not args.rehearse:
        reviewed_today = fetch_reviews_today_count(conn, today)
        if len(review_queue) == 0 and len(item_ids) == 0:
            terminal_output.msg_warn(f"no items found in {exercises_dir}/")
            return 0
        if len(review_queue) == 0 and reviewed_today > 0:
            terminal_output.msg_info(
                "all due items reviewed today - next session recommended tomorrow"
            )
            return 0
        if len(review_queue) == 0:
            terminal_output.msg_info("no items due today")
            return 0

    run_review_session(conn, exercises, review_queue, today, args.rehearse)
    return 0


if __name__ == "__main__":
    sys.exit(main())
