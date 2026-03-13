import argparse
import datetime
import os
import re
import sqlite3
import sys
import time
from typing import TypeAlias
import terminal_output


# =============================================================================
# TYPES AND CONSTANTS
# =============================================================================
ParsedItem: TypeAlias = tuple[str, str, str, list[str], list[str]]
# positions:                  id   content  criteria  tags     prerequisites

ContentMap: TypeAlias = dict[str, tuple[str, str, list[str], list[str], str]]
# positions:                                   content  criteria  tags     prerequisites  source

DueItem: TypeAlias = tuple[str, int, int]
# positions:               item_id  repetition_count  due_date

DATABASE_PATH: str = "data/sm2.db"
LEECH_THRESHOLD: int = 3
TOTAL_NEW_MAX: int = 9
MIN_PER_DOMAIN: int = 1
MAX_REVIEWS: int = 100

# =============================================================================
# PARSER
# =============================================================================
ITEM_DELIMITER_PATTERN: re.Pattern[str] = re.compile(r"^@@@ id:\s*(.+)$")


def parse_exercises(directory_path: str) -> list[ParsedItem]:
    all_filenames: list[str] = os.listdir(directory_path)
    markdown_filenames: list[str] = []
    for filename in all_filenames:
        if filename.endswith(".md"):
            markdown_filenames.append(filename)

    parsed_items: list[ParsedItem] = []
    seen_ids: dict[str, str] = {}  # item_id -> source filepath

    for filename in sorted(markdown_filenames):
        filepath: str = os.path.join(directory_path, filename)
        file_handle = open(filepath, "r", encoding="utf-8")
        raw_text: str = file_handle.read()
        file_handle.close()

        lines: list[str] = raw_text.splitlines()

        blocks: list[tuple[str, list[str]]] = []
        current_id: str = ""
        current_lines: list[str] = []

        for line in lines:
            delimiter_match: re.Match[str] | None = ITEM_DELIMITER_PATTERN.match(line)
            if delimiter_match is not None:
                if current_id != "":
                    blocks.append((current_id, current_lines))
                current_id = delimiter_match.group(1).strip()
                current_lines = []
            else:
                if current_id != "":
                    current_lines.append(line)

        if current_id != "":
            blocks.append((current_id, current_lines))

        for item_id, block_lines in blocks:
            if item_id in seen_ids:
                raise ValueError(
                    f"duplicate item id '{item_id}' in '{filepath}'"
                    f" and '{seen_ids[item_id]}'"
                )
            seen_ids[item_id] = filepath

            criteria: str = ""
            tags: list[str] = []
            prerequisites: list[str] = []
            source: str = ""
            content_lines: list[str] = []

            for line in block_lines:
                if line.startswith("criteria:"):
                    criteria = line[len("criteria:"):].strip()
                elif line.startswith("tags:"):
                    raw_tags: str = line[len("tags:"):].strip()
                    for raw_tag in raw_tags.split(","):
                        stripped_tag: str = raw_tag.strip()
                        if stripped_tag != "":
                            tags.append(stripped_tag)
                elif line.startswith("after:"):
                    raw_prerequisites: str = line[len("after:"):].strip()
                    for raw_prerequisite in raw_prerequisites.split(","):
                        stripped_prerequisite: str = raw_prerequisite.strip()
                        if stripped_prerequisite != "":
                            prerequisites.append(stripped_prerequisite)
                elif line.startswith("source:"):
                    source = line[len("source:"):].strip()
                else:
                    content_lines.append(line)

            content: str = "\n".join(content_lines).strip()
            parsed_item: ParsedItem = (item_id, content, criteria, tags, prerequisites, source)
            parsed_items.append(parsed_item)

    return parsed_items


# =============================================================================
# SM-2 ALGORITHM
# =============================================================================
USER_GRADE_TO_SM2_GRADE: dict[int, int] = {0: 1, 1: 3, 2: 5}

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


# =============================================================================
# DATABASE SCHEMA
# =============================================================================

def initialize_database(database_path: str) -> sqlite3.Connection:
    database_connection: sqlite3.Connection = sqlite3.connect(database_path)
    database_connection.execute("PRAGMA journal_mode=WAL")
    database_connection.execute("""
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
    database_connection.execute("""
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

    database_connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_due_date ON items(due_date)"
    )
    database_connection.commit()
    existing_columns: list[tuple] = database_connection.execute(
        "PRAGMA table_info(review_log)"
    ).fetchall()
    column_names: set[str] = set()
    for column_row in existing_columns:
        column_names.add(column_row[1])
    if "answer_text" not in column_names:
        database_connection.execute(
            "ALTER TABLE review_log ADD COLUMN answer_text TEXT"
        )
        database_connection.commit()
    if "response_seconds" not in column_names:
        database_connection.execute(
            "ALTER TABLE review_log ADD COLUMN response_seconds REAL"
        )
        database_connection.commit()
    existing_items_columns: list[tuple] = database_connection.execute(
        "PRAGMA table_info(items)"
    ).fetchall()
    items_column_names: set[str] = set()
    for items_column_row in existing_items_columns:
        items_column_names.add(items_column_row[1])
    if "source" not in items_column_names:
        database_connection.execute(
            "ALTER TABLE items ADD COLUMN source TEXT DEFAULT ''"
        )
        database_connection.commit()
    return database_connection

# =============================================================================
# THROTTLE
# =============================================================================
def apply_throttle_and_cap(
    due_queue: list[DueItem],
    today_new_by_domain: dict[str, int],
    total_new_max: int,
    min_per_domain: int,
    max_reviews: int,
    blocked_set: set[str],
) -> list[str]:
    # pass 1: reserve floor items per domain
    reserved_item_ids: set[str] = set()
    reserved_count_by_domain: dict[str, int] = {}
    for due_item in due_queue:
        item_id: str = due_item[0]
        repetition_count: int = due_item[1]
        if item_id in blocked_set:
            continue
        if repetition_count == 0:
            identifier_parts: list[str] = item_id.split("-")
            domain: str = identifier_parts[0]
            already_reviewed_in_domain: int = today_new_by_domain.get(domain, 0)
            already_reserved_in_domain: int = reserved_count_by_domain.get(domain, 0)
            floor_remaining: int = (
                min_per_domain - already_reviewed_in_domain - already_reserved_in_domain
            )
            if floor_remaining > 0:
                reserved_item_ids.add(item_id)
                reserved_count_by_domain[domain] = already_reserved_in_domain + 1
    # pass 2: build result - reserved slots pre-allocated from budget
    already_new_today: int = 0
    for domain_count in today_new_by_domain.values():
        already_new_today = already_new_today + domain_count
    total_reserved: int = len(reserved_item_ids)
    non_reserved_budget: int = max(0, total_new_max - total_reserved - already_new_today)
    non_reserved_added: int = 0
    result: list[str] = []
    for due_item in due_queue:
        item_id: str = due_item[0]
        repetition_count: int = due_item[1]
        if item_id in blocked_set:
            continue
        if repetition_count > 0:
            result.append(item_id)
        else:
            if item_id in reserved_item_ids:
                result.append(item_id)
            elif non_reserved_added < non_reserved_budget:
                result.append(item_id)
                non_reserved_added = non_reserved_added + 1
    if len(result) > max_reviews:
        result = result[:max_reviews]
    return result
# =============================================================================
# PREREQUISITE ENFORCEMENT
# =============================================================================
def build_blocked_set(
    content_map: ContentMap,
    database_connection: sqlite3.Connection,
) -> set[str]:
    # Prerequisite chains are assumed acyclic by authoring convention.
    # No runtime cycle detection.
    blocked_item_ids: set[str] = set()
    for item_id in content_map:
        prerequisites: list[str] = content_map[item_id][3]
        for prerequisite_id in prerequisites:
            prerequisite_in_db: int = database_connection.execute(
                "SELECT COUNT(*) FROM items WHERE item_id = ?",
                (prerequisite_id,),
            ).fetchone()[0]
            if prerequisite_in_db == 0:
                continue
            passing_grades: int = database_connection.execute(
                "SELECT COUNT(*) FROM review_log "
                "WHERE item_id = ? AND grade > 0",
                (prerequisite_id,),
            ).fetchone()[0]
            if passing_grades == 0:
                blocked_item_ids.add(item_id)
                break
    return blocked_item_ids
# =============================================================================
# VALIDATION
# =============================================================================
def run_validation() -> None:
    failure_count: int = 0
    FLOAT_TOLERANCE: float = 0.0001
    validation_today: int = datetime.date.today().toordinal()

    # sanity check: ordinal is a plausible current date
    if validation_today <= datetime.date(2024, 1, 1).toordinal():
        print("FAIL: today ordinal is not a plausible current date")
        failure_count = failure_count + 1

    # build 15 synthetic parsed items: 5 per domain
    synthetic_items: list[ParsedItem] = []
    for domain_prefix in ["drive", "c", "bio"]:
        for index in range(1, 6):
            synthetic_id: str = f"{domain_prefix}-val-{index}"
            synthetic_source: str = "wozniak1999" if synthetic_id == "drive-val-1" else ""
            synthetic_item: ParsedItem = (
                synthetic_id,
                f"validation content for {synthetic_id}",
                "",
                [],
                [],
                synthetic_source,
            )
            synthetic_items.append(synthetic_item)

# init in-memory database
    validation_connection: sqlite3.Connection = initialize_database(":memory:")
    pragma_rows: list[tuple] = validation_connection.execute(
        "PRAGMA table_info(review_log)"
    ).fetchall()
    pragma_column_names: set[str] = set()
    for pragma_row in pragma_rows:
        pragma_column_names.add(pragma_row[1])

    if "answer_text" not in pragma_column_names:
        print("FAIL: answer_text column missing from review_log after initialize_database")
        failure_count = failure_count + 1

    if "response_seconds" not in pragma_column_names:
        print("FAIL: response_seconds column missing from review_log after initialize_database")
        failure_count = failure_count + 1
    items_pragma_rows: list[tuple] = validation_connection.execute(
        "PRAGMA table_info(items)"
    ).fetchall()
    items_column_names: set[str] = set()
    for items_pragma_row in items_pragma_rows:
        items_column_names.add(items_pragma_row[1])
    if "source" not in items_column_names:
        print("FAIL: source column missing from items after initialize_database")
        failure_count = failure_count + 1
    # build parsed_ids and content_map
    validation_parsed_ids: set[str] = set()
    validation_content_map: ContentMap = {}
    for item_id, content, criteria, tags, prerequisites, source in synthetic_items:
        validation_parsed_ids.add(item_id)
        validation_content_map[item_id] = (content, criteria, tags, prerequisites, source)

    # reconcile
    existing_rows: list[tuple] = validation_connection.execute(
        "SELECT item_id FROM items"
    ).fetchall()
    validation_database_ids: set[str] = set()
    for row in existing_rows:
        validation_database_ids.add(row[0])
    new_item_ids: set[str] = validation_parsed_ids - validation_database_ids

    for new_item_id in new_item_ids:
        new_item_source: str = validation_content_map[new_item_id][4]
        validation_connection.execute(
            "INSERT INTO items (item_id, due_date, source) VALUES (?, ?, ?)",
            (new_item_id, validation_today, new_item_source),
        )
    validation_connection.commit()
    # assert 15 items in table
    item_count_row: tuple = validation_connection.execute(
        "SELECT COUNT(*) FROM items"
    ).fetchone()
    item_count: int = item_count_row[0]

    if item_count != 15:
        print(f"FAIL: expected 15 items in table, got {item_count}")
        failure_count = failure_count + 1
    source_check_row: tuple | None = validation_connection.execute(
        "SELECT source FROM items WHERE item_id = ?",
        ("drive-val-1",),
    ).fetchone()
    if source_check_row is None or source_check_row[0] != "wozniak1999":
        print("FAIL: source value did not round-trip through reconcile")
        failure_count = failure_count + 1
    empty_source_check_row: tuple | None = validation_connection.execute(
        "SELECT source FROM items WHERE item_id = ?",
        ("drive-val-2",),
    ).fetchone()
    if empty_source_check_row is None or empty_source_check_row[0] != "":
        print("FAIL: item without source: field did not get empty string default")
        failure_count = failure_count + 1

    # build due queue
    validation_due_queue: list[DueItem] = []
    validation_parsed_ids_list: list[str] = list(validation_parsed_ids)
    in_placeholders: str = ",".join("?" * len(validation_parsed_ids_list))
    due_queue_query: str = (
        f"SELECT item_id, repetition_count, due_date FROM items "
        f"WHERE item_id IN ({in_placeholders}) AND due_date <= ? "
        f"ORDER BY due_date ASC"
    )
    due_queue_parameters: list[str | int] = validation_parsed_ids_list + [validation_today]
    due_queue_rows: list[tuple] = validation_connection.execute(
        due_queue_query, due_queue_parameters
    ).fetchall()
    for row in due_queue_rows:
        validation_due_item: DueItem = (row[0], row[1], row[2])
        validation_due_queue.append(validation_due_item)

    # query today new by domain (empty on fresh db)
    validation_today_new_rows: list[tuple] = validation_connection.execute(
        "SELECT domain, COUNT(*) FROM review_log "
        "WHERE review_date = ? AND repetition_count_before = 0 "
        "GROUP BY domain",
        (validation_today,),
    ).fetchall()
    validation_today_new_by_domain: dict[str, int] = {}
    for row in validation_today_new_rows:
        validation_today_new_by_domain[row[0]] = row[1]

    # apply throttle
    validation_review_queue: list[str] = apply_throttle_and_cap(
        validation_due_queue,
        validation_today_new_by_domain,
        TOTAL_NEW_MAX,
        MIN_PER_DOMAIN,
        MAX_REVIEWS,
        set(),
    )

    # assert 9 items in review queue
    if len(validation_review_queue) != 9:
        print(f"FAIL: expected 9 in review queue, got {len(validation_review_queue)}")
        failure_count = failure_count + 1

    # simulate reviews: grades cycle 0, 1, 2
    simulated_grades: list[int] = [0, 1, 2, 0, 1, 2, 0, 1, 2]

    for queue_index, item_id in enumerate(validation_review_queue):
        grade: int = simulated_grades[queue_index]
        sim_sm2_grade: int = USER_GRADE_TO_SM2_GRADE[grade]

        sim_state_row: tuple = validation_connection.execute(
            "SELECT easiness_factor, interval_days, repetition_count, "
            "due_date, last_review, lapse_count "
            "FROM items WHERE item_id = ?",
            (item_id,),
        ).fetchone()

        sim_easiness_factor_before: float = sim_state_row[0]
        sim_interval_days_before: float = sim_state_row[1]
        sim_repetition_count_before: int = sim_state_row[2]
        sim_last_review: int = sim_state_row[4]
        sim_lapse_count_before: int = sim_state_row[5]

        if sim_last_review > 0:
            sim_elapsed_days: int = validation_today - sim_last_review
        else:
            sim_elapsed_days = 0

        sim_update_result: dict[str, float | int] = sm2_update(
            grade,
            sim_easiness_factor_before,
            sim_interval_days_before,
            sim_repetition_count_before,
            sim_lapse_count_before,
            validation_today,
        )

        sim_new_easiness_factor: float = float(sim_update_result["easiness_factor"])
        sim_new_repetition_count: int = int(sim_update_result["repetition_count"])
        sim_new_interval_days: float = float(sim_update_result["interval_days"])
        sim_new_lapse_count: int = int(sim_update_result["lapse_count"])
        sim_new_due_date: int = int(sim_update_result["due_date"])

        identifier_parts: list[str] = item_id.split("-")
        domain: str = identifier_parts[0]

        validation_connection.execute(
            "UPDATE items SET easiness_factor=?, interval_days=?, "
            "repetition_count=?, due_date=?, last_review=?, lapse_count=? "
            "WHERE item_id=?",
            (
                sim_new_easiness_factor,
                sim_new_interval_days,
                sim_new_repetition_count,
                sim_new_due_date,
                validation_today,
                sim_new_lapse_count,
                item_id,
            ),
        )
        validation_connection.commit()

        validation_connection.execute(
            "INSERT INTO review_log ("
            "item_id, grade, sm2_grade, review_date, elapsed_days, "
            "easiness_factor_before, easiness_factor_after, "
            "interval_days_before, interval_days_after, "
            "repetition_count_before, domain, error_note, answer_text, "
            "response_seconds"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                item_id,
                grade,
                sim_sm2_grade,
                validation_today,
                sim_elapsed_days,
                sim_easiness_factor_before,
                sim_new_easiness_factor,
                sim_interval_days_before,
                sim_new_interval_days,
                sim_repetition_count_before,
                domain,
                None,
                None,
                None,
            ),
        )
        validation_connection.commit()

    # assert 9 review_log rows
    log_count_row: tuple = validation_connection.execute(
        "SELECT COUNT(*) FROM review_log"
    ).fetchone()
    log_count: int = log_count_row[0]
    if log_count != 9:
        print(f"FAIL: expected 9 review_log rows, got {log_count}")
        failure_count = failure_count + 1

    # assert state transitions per grade
    for queue_index, item_id in enumerate(validation_review_queue):
        grade = simulated_grades[queue_index]

        post_state_row: tuple = validation_connection.execute(
            "SELECT easiness_factor, interval_days, repetition_count, "
            "lapse_count, due_date "
            "FROM items WHERE item_id = ?",
            (item_id,),
        ).fetchone()

        post_easiness_factor: float = post_state_row[0]
        post_interval_days: float = post_state_row[1]
        post_repetition_count: int = post_state_row[2]
        post_lapse_count: int = post_state_row[3]
        post_due_date: int = post_state_row[4]

        if grade == 0:
            if post_repetition_count != 0:
                print(
                    f"FAIL: {item_id} grade 0 expected repetition_count 0, "
                    f"got {post_repetition_count}"
                )
                failure_count = failure_count + 1
            if post_lapse_count != 1:
                print(
                    f"FAIL: {item_id} grade 0 expected lapse_count 1, "
                    f"got {post_lapse_count}"
                )
                failure_count = failure_count + 1
            if abs(post_easiness_factor - 1.96) > FLOAT_TOLERANCE:
                print(
                    f"FAIL: {item_id} grade 0 expected easiness_factor 1.96, "
                    f"got {post_easiness_factor}"
                )
                failure_count = failure_count + 1
        elif grade == 1:
            if post_repetition_count != 1:
                print(
                    f"FAIL: {item_id} grade 1 expected repetition_count 1, "
                    f"got {post_repetition_count}"
                )
                failure_count = failure_count + 1
            if abs(post_easiness_factor - 2.36) > FLOAT_TOLERANCE:
                print(
                    f"FAIL: {item_id} grade 1 expected easiness_factor 2.36, "
                    f"got {post_easiness_factor}"
                )
                failure_count = failure_count + 1
        elif grade == 2:
            if post_repetition_count != 1:
                print(
                    f"FAIL: {item_id} grade 2 expected repetition_count 1, "
                    f"got {post_repetition_count}"
                )
                failure_count = failure_count + 1
            if abs(post_easiness_factor - 2.60) > FLOAT_TOLERANCE:
                print(
                    f"FAIL: {item_id} grade 2 expected easiness_factor 2.60, "
                    f"got {post_easiness_factor}"
                )
                failure_count = failure_count + 1

        if abs(post_interval_days - 1.0) > FLOAT_TOLERANCE:
            print(
                f"FAIL: {item_id} expected interval_days 1.0, "
                f"got {post_interval_days}"
            )
            failure_count = failure_count + 1

        if post_due_date != validation_today + 1:
            print(
                f"FAIL: {item_id} expected due_date {validation_today + 1}, "
                f"got {post_due_date}"
            )
            failure_count = failure_count + 1

    validation_connection.close()

    if failure_count == 0:
        print("validation passed: all checks ok")
    else:
        print(f"validation failed: {failure_count} check(s) failed")
        sys.exit(1)


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    argument_parser: argparse.ArgumentParser = argparse.ArgumentParser(
        description="SM-2 spaced repetition review tool."
    )
    argument_parser.add_argument(
        "--new-max",
        type=int,
        default=TOTAL_NEW_MAX,
        help="maximum new items per session (default: 9)",
    )
    argument_parser.add_argument(
        "--min-per-domain",
        type=int,
        default=MIN_PER_DOMAIN,
        help="minimum new items guaranteed per domain (default: 1)",
    )
    argument_parser.add_argument(
        "--max-reviews",
        type=int,
        default=MAX_REVIEWS,
        help="hard session cap on total items reviewed (default: 100)",
    )
    argument_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="print the review queue and exit without reviewing",
    )
    argument_parser.add_argument(
        "--preview",
        action="store_true",
        help="show upcoming items not yet due and exit",
    )
    argument_parser.add_argument(
        "--validate",
        action="store_true",
        help="run internal validation suite and exit",
    )
    argument_parser.add_argument(
        "--rehearse",
        action="store_true",
        help="run review session without writing to database",
    )
    argument_parser.add_argument(
        "--show_failures",
        action="store_true",
        help="show most recent grade-0 rows with error notes and exit",
    )
    argument_parser.add_argument(
        "--show_leeches",
        action="store_true",
        help="show items with lapse_count >= LEECH_THRESHOLD and exit",
    )
    parsed_args: argparse.Namespace = argument_parser.parse_args()
    rehearse_mode: bool = parsed_args.rehearse
    terminal_output.set_verbosity(3)
    terminal_output.set_layout(max_width=76, align="center")
    if parsed_args.validate:
        run_validation()
        sys.exit(0)

    TOTAL_NEW_MAX = parsed_args.new_max
    MIN_PER_DOMAIN = parsed_args.min_per_domain
    MAX_REVIEWS = parsed_args.max_reviews

    today: int = datetime.date.today().toordinal()
    if parsed_args.show_failures or parsed_args.show_leeches:
        if not os.path.isdir("data"):
            print("error: data/ directory not found")
            sys.exit(1)
        flags_connection: sqlite3.Connection = initialize_database(DATABASE_PATH)
        if parsed_args.show_failures:
            failures_rows: list[tuple] = flags_connection.execute(
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
            if len(failures_rows) == 0:
                print("no recorded failures with notes.")
            else:
                failures_id_width: int = len("item_id")
                for failures_row in failures_rows:
                    if len(failures_row[0]) > failures_id_width:
                        failures_id_width = len(failures_row[0])
                print(
                    f"{'item_id':<{failures_id_width}}  "
                    f"{'domain':<6}  {'date':<10}  {'lapses':>6}  error_note"
                )
                for failures_row in failures_rows:
                    failure_item_id: str = failures_row[0]
                    failure_domain: str = failures_row[1]
                    failure_date: str = datetime.date.fromordinal(failures_row[2]).isoformat()
                    failure_error_note: str = failures_row[3]
                    failure_lapse_count: int = failures_row[4]
                    print(
                        f"{failure_item_id:<{failures_id_width}}  "
                        f"{failure_domain:<6}  {failure_date:<10}  "
                        f"{failure_lapse_count:>6}  {failure_error_note}"
                    )
        if parsed_args.show_leeches:
            leeches_rows: list[tuple] = flags_connection.execute(
                "SELECT item_id, lapse_count, easiness_factor, last_review "
                "FROM items "
                "WHERE lapse_count >= ? "
                "ORDER BY lapse_count DESC, easiness_factor ASC",
                (LEECH_THRESHOLD,),
            ).fetchall()
            if len(leeches_rows) == 0:
                print(
                    f"no show_leeches found (lapse_count < {LEECH_THRESHOLD} for all items)."
                )
            else:
                leeches_id_width: int = len("item_id")
                for leeches_row in leeches_rows:
                    if len(leeches_row[0]) > leeches_id_width:
                        leeches_id_width = len(leeches_row[0])
                print(
                    f"{'item_id':<{leeches_id_width}}  "
                    f"{'domain':<6}  {'lapses':>6}  {'EF':>5}  days_since"
                )
                for leeches_row in leeches_rows:
                    leech_item_id: str = leeches_row[0]
                    leech_lapse_count: int = leeches_row[1]
                    leech_easiness_factor: float = leeches_row[2]
                    leech_last_review: int = leeches_row[3]
                    leech_domain: str = leech_item_id.split("-")[0]
                    if leech_last_review == 0:
                        leech_days_since: str = "never"
                    else:
                        leech_days_since = str(today - leech_last_review)
                    print(
                        f"{leech_item_id:<{leeches_id_width}}  "
                        f"{leech_domain:<6}  {leech_lapse_count:>6}  "
                        f"{leech_easiness_factor:>5.2f}  {leech_days_since}"
                    )
        sys.exit(0)
    if not os.path.isdir("data"):
        print("error: data/ directory not found")
        sys.exit(1)
    if not os.path.isdir("exercises"):
        print("error: exercises/ directory not found")
        sys.exit(1)
    database_connection: sqlite3.Connection = initialize_database(DATABASE_PATH)
    # --- parse
    parsed_items: list[ParsedItem] = parse_exercises("exercises/")

    parsed_ids: set[str] = set()
    content_map: ContentMap = {}
    for item_id, content, criteria, tags, prerequisites, source in parsed_items:
        parsed_ids.add(item_id)
        content_map[item_id] = (content, criteria, tags, prerequisites, source)

    # --- reconcile
    existing_rows: list[tuple] = database_connection.execute(
        "SELECT item_id FROM items"
    ).fetchall()
    database_ids: set[str] = set()
    for row in existing_rows:
        database_ids.add(row[0])

    new_item_ids: set[str] = parsed_ids - database_ids

    for new_item_id in new_item_ids:
        new_item_source: str = content_map[new_item_id][4]
        database_connection.execute(
            "INSERT INTO items (item_id, due_date, source) VALUES (?, ?, ?)",
            (new_item_id, today, new_item_source),
        )
    database_connection.commit()
    # --- preview upcoming items
    if parsed_args.preview:
        if len(parsed_ids) == 0:
            print("no upcoming items found.")
            sys.exit(0)
        preview_parsed_ids_list: list[str] = list(parsed_ids)
        preview_placeholders: str = ",".join("?" * len(preview_parsed_ids_list))
        preview_rows: list[tuple] = database_connection.execute(
            f"SELECT item_id, easiness_factor, interval_days, "
            f"repetition_count, due_date "
            f"FROM items "
            f"WHERE item_id IN ({preview_placeholders}) "
            f"  AND due_date > ? "
            f"ORDER BY due_date ASC "
            f"LIMIT 20",
            preview_parsed_ids_list + [today],
        ).fetchall()
        if len(preview_rows) == 0:
            print("no upcoming items found.")
            sys.exit(0)
        preview_id_width: int = len("item_id")
        for preview_row in preview_rows:
            if len(preview_row[0]) > preview_id_width:
                preview_id_width = len(preview_row[0])
        print(
            f"{'item_id':<{preview_id_width}}  "
            f"{'domain':<6}  {'due_in':>6}  {'rep':>3}  {'EF':>5}"
        )
        for preview_row in preview_rows:
            preview_item_id: str = preview_row[0]
            preview_easiness_factor: float = preview_row[1]
            preview_repetition_count: int = preview_row[3]
            preview_due_date: int = preview_row[4]
            preview_domain: str = preview_item_id.split("-")[0]
            preview_due_in: int = preview_due_date - today
            print(
                f"{preview_item_id:<{preview_id_width}}  "
                f"{preview_domain:<6}  {preview_due_in:>6}  "
                f"{preview_repetition_count:>3}  {preview_easiness_factor:>5.2f}"
            )
        sys.exit(0)
    # --- build due queue
    due_queue: list[DueItem] = []
    if len(parsed_ids) > 0:
        parsed_ids_list: list[str] = list(parsed_ids)
        in_placeholders: str = ",".join("?" * len(parsed_ids_list))
        due_queue_query: str = (
            f"SELECT item_id, repetition_count, due_date FROM items "
            f"WHERE item_id IN ({in_placeholders}) AND due_date <= ? "
            f"ORDER BY due_date ASC"
        )
        due_queue_parameters: list[str | int] = parsed_ids_list + [today]
        due_queue_rows: list[tuple] = database_connection.execute(
            due_queue_query, due_queue_parameters
        ).fetchall()
        for row in due_queue_rows:
            due_item: DueItem = (row[0], row[1], row[2])
            due_queue.append(due_item)

    # --- query today new counts
    today_new_rows: list[tuple] = database_connection.execute(
        "SELECT domain, COUNT(*) FROM review_log "
        "WHERE review_date = ? AND repetition_count_before = 0 "
        "GROUP BY domain",
        (today,),
    ).fetchall()
    today_new_by_domain: dict[str, int] = {}
    for row in today_new_rows:
        today_new_by_domain[row[0]] = row[1]

    # --- build blocked set
    blocked_set: set[str] = set()

    # --- apply throttle and cap
    review_queue: list[str] = apply_throttle_and_cap(
        due_queue,
        today_new_by_domain,
        TOTAL_NEW_MAX,
        MIN_PER_DOMAIN,
        MAX_REVIEWS,
        blocked_set,
    )

    if parsed_args.dry_run:
        print(f"dry run: {len(review_queue)} item(s) in review queue")
        if len(review_queue) > 0:
            dry_run_placeholders: str = ",".join("?" * len(review_queue))
            dry_run_rows: list[tuple] = database_connection.execute(
                f"SELECT item_id, easiness_factor, interval_days, "
                f"repetition_count, due_date "
                f"FROM items WHERE item_id IN ({dry_run_placeholders})",
                review_queue,
            ).fetchall()
            dry_run_state: dict[str, tuple] = {}
            for row in dry_run_rows:
                dry_run_state[row[0]] = row
            id_column_width: int = len("item_id")
            for queued_item_id in review_queue:
                if len(queued_item_id) > id_column_width:
                    id_column_width = len(queued_item_id)
            print(
                f"{'item_id':<{id_column_width}}  "
                f"{'domain':<6}  {'rep':>3}  {'EF':>5}  "
                f"{'interval':>8}  days_overdue"
            )
            for queued_item_id in review_queue:
                dry_run_row: tuple = dry_run_state[queued_item_id]
                item_domain: str = queued_item_id.split("-")[0]
                item_ef: float = dry_run_row[1]
                item_interval: float = dry_run_row[2]
                item_rep: int = dry_run_row[3]
                item_due_date: int = dry_run_row[4]
                item_days_overdue: int = today - item_due_date
                print(
                    f"{queued_item_id:<{id_column_width}}  "
                    f"{item_domain:<6}  {item_rep:>3}  {item_ef:>5.2f}  "
                    f"{item_interval:>8.1f}  {item_days_overdue}"
                )
        sys.exit(0)
    if not rehearse_mode:
        items_reviewed_today: int = database_connection.execute(
            "SELECT COUNT(*) FROM review_log WHERE review_date = ?",
            (today,),
        ).fetchone()[0]
        if len(review_queue) == 0 and len(parsed_ids) == 0:
            terminal_output.msg_warn("no items found in exercises/")
            sys.exit(0)
        if len(review_queue) == 0 and items_reviewed_today > 0:
            terminal_output.msg_info(
                "all due items reviewed today - "
                "next session recommended tomorrow"
            )
            sys.exit(0)
        if len(review_queue) == 0 and items_reviewed_today == 0 and len(parsed_ids) > 0:
            terminal_output.msg_info("no items due today")
            sys.exit(0)

    # --- review loop
    review_count: int = 0
    pass_count: int = 0
    fail_count: int = 0
    new_count: int = 0
    try:
        for item_id in review_queue:

            content_entry: tuple[str, str, list[str], list[str], str] = content_map[item_id]
            content: str = content_entry[0]
            criteria: str = content_entry[1]

            identifier_parts: list[str] = item_id.split("-")
            domain: str = identifier_parts[0]

            if rehearse_mode:
                progress_string: str = (
                    f"{review_count + 1} / {len(review_queue)}  "
                    + terminal_output.format_label("rehearse")
                )
            else:
                progress_string: str = f"{review_count + 1} / {len(review_queue)}"

            terminal_output.clear_screen()
            terminal_output.emit(terminal_output.format_card(
                header_left=progress_string,
                header_right=domain,
                body=content,
                footer=None,
            ))


            response_start: float = time.monotonic()
            terminal_output.emit("Your answer (enter to skip):")
            raw_answer: str = input("").strip()
            answer_text: str | None = raw_answer if raw_answer != "" else None
            if criteria != "":
                terminal_output.emit(terminal_output.format_separator())
                terminal_output.emit(terminal_output.format_label("criteria"))
                terminal_output.emit(terminal_output.wrap_text(criteria))
            terminal_output.emit(terminal_output.format_choices([
                ("0", "failed"),
                ("1", "passed with effort"),
                ("2", "easy, fluent"),
            ]))
            grade: int = -1
            while grade == -1:
                terminal_output.emit("Grade (0/1/2):")
                raw_grade: str = input("").strip()
                if raw_grade == "0":
                    grade = 0
                elif raw_grade == "1":
                    grade = 1
                elif raw_grade == "2":
                    grade = 2
                else:
                    terminal_output.emit("Invalid grade. Enter 0, 1, or 2.")

            response_seconds: float = round(time.monotonic() - response_start, 2)
            error_note: str | None = None
            if grade == 0:
                terminal_output.emit("What went wrong? (enter to skip):")
                raw_error_note: str = input("").strip()
                if raw_error_note != "":
                    error_note = raw_error_note

            state_row: tuple = database_connection.execute(
                "SELECT easiness_factor, interval_days, repetition_count, "
                "due_date, last_review, lapse_count "
                "FROM items WHERE item_id = ?",
                (item_id,),
            ).fetchone()

            easiness_factor_before: float = state_row[0]
            interval_days_before: float = state_row[1]
            repetition_count_before: int = state_row[2]
            last_review: int = state_row[4]
            lapse_count_before: int = state_row[5]

            if last_review > 0:
                elapsed_days = today - last_review
            else:
                elapsed_days = 0

            sm2_grade: int = USER_GRADE_TO_SM2_GRADE[grade]

            update_result: dict[str, float | int] = sm2_update(
                grade,
                easiness_factor_before,
                interval_days_before,
                repetition_count_before,
                lapse_count_before,
                today,
            )

            new_easiness_factor: float = float(update_result["easiness_factor"])
            new_repetition_count: int = int(update_result["repetition_count"])
            new_interval_days: float = float(update_result["interval_days"])
            new_lapse_count: int = int(update_result["lapse_count"])
            new_due_date: int = int(update_result["due_date"])


            if not rehearse_mode:
                database_connection.execute(
                    "UPDATE items SET easiness_factor=?, interval_days=?, "
                    "repetition_count=?, due_date=?, last_review=?, lapse_count=? "
                    "WHERE item_id=?",
                    (
                        new_easiness_factor,
                        new_interval_days,
                        new_repetition_count,
                        new_due_date,
                        today,
                        new_lapse_count,
                        item_id,
                    ),
                )
                database_connection.commit()
                database_connection.execute(
                    "INSERT INTO review_log ("
                    "item_id, grade, sm2_grade, review_date, elapsed_days, "
                    "easiness_factor_before, easiness_factor_after, "
                    "interval_days_before, interval_days_after, "
                    "repetition_count_before, domain, error_note, answer_text, "
                    "response_seconds"
                    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        item_id,
                        grade,
                        sm2_grade,
                        today,
                        elapsed_days,
                        easiness_factor_before,
                        new_easiness_factor,
                        interval_days_before,
                        new_interval_days,
                        repetition_count_before,
                        domain,
                        error_note,
                        answer_text,
                        response_seconds,
                    ),
                )
                database_connection.commit()

            days_until: int = new_due_date - today
            duration_string: str = terminal_output.format_duration(days_until)

            if rehearse_mode:
                if grade == 0:
                    terminal_output.emit(f"Would fail. Would return in {duration_string}.")
                else:
                    terminal_output.emit(f"Would pass. Next review in {duration_string}.")
            else:
                if grade == 0:
                    terminal_output.emit(f"Failed. Returns in {duration_string}.")
                else:
                    terminal_output.emit(f"Passed. Next review in {duration_string}.")

            review_count = review_count + 1
            if grade == 0:
                fail_count = fail_count + 1
            else:
                pass_count = pass_count + 1
            if repetition_count_before == 0:
                new_count = new_count + 1

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
        if rehearse_mode:
            terminal_output.msg_success("session complete (rehearse - nothing written)")
        else:
            terminal_output.msg_success("session complete")

        if fail_count > 0:
            terminal_output.msg_info(f"{fail_count} item(s) return tomorrow")
