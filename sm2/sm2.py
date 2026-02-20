import argparse
import datetime
import os
import re
import sqlite3
import sys
from typing import TypeAlias


# =============================================================================
# TYPES AND CONSTANTS
# =============================================================================
ParsedItem: TypeAlias = tuple[str, str, str, list[str], list[str]]
# positions:                  id   content  criteria  tags     prerequisites

ContentMap: TypeAlias = dict[str, tuple[str, str, list[str], list[str]]]
# positions:                                   content  criteria  tags     prerequisites

DATABASE_PATH: str = "data/sm2.db"

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
        file_handle = open(filepath, "r", encoding="ascii")
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
                else:
                    content_lines.append(line)

            content: str = "\n".join(content_lines).strip()
            parsed_item: ParsedItem = (item_id, content, criteria, tags, prerequisites)
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
            lapse_count       INTEGER DEFAULT 0
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
            error_note                TEXT
        )
    """)
    database_connection.execute(
        "CREATE INDEX IF NOT EXISTS idx_due_date ON items(due_date)"
    )
    database_connection.commit()
    return database_connection


# =============================================================================
# OUTPUT HELPERS
# =============================================================================


# =============================================================================
# THROTTLE
# =============================================================================


# =============================================================================
# VALIDATION
# =============================================================================


# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    today: int = datetime.date.today().toordinal()

    database_connection: sqlite3.Connection = initialize_database(DATABASE_PATH)

    # --- parse
    parsed_items: list[ParsedItem] = parse_exercises("exercises/")

    parsed_ids: set[str] = set()
    content_map: ContentMap = {}
    for item_id, content, criteria, tags, prerequisites in parsed_items:
        parsed_ids.add(item_id)
        content_map[item_id] = (content, criteria, tags, prerequisites)

    # --- reconcile
    existing_rows: list[tuple] = database_connection.execute(
        "SELECT item_id FROM items"
    ).fetchall()
    database_ids: set[str] = set()
    for row in existing_rows:
        database_ids.add(row[0])

    new_item_ids: set[str] = parsed_ids - database_ids
    for new_item_id in new_item_ids:
        database_connection.execute(
            "INSERT INTO items (item_id, due_date) VALUES (?, ?)",
            (new_item_id, today),
        )
    database_connection.commit()
