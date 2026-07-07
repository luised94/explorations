"""One-off: migrate sm2/exercises/*.md content into drill banks.

Written for the A3 close of the SM2 consolidation (implementation-plan.md)
and committed AS A CONTINGENCY: the human decided not to run it immediately
(the sm2 content may be re-authored fresh instead), but with it committed
the old content is one command away from living in drill at any later date.
sm2/ itself is retired in the commit after this script lands; the exercise
files remain recoverable from git at the SHA recorded in ADR-059
(git checkout <sha> -- sm2/exercises), which is what the directory argument
below would then point at.

Usage:
    python3 tools/migrate_sm2_exercises.py <exercises_directory>
    (database from DRILL_DB, default drill.db, same as every drill command)

Mapping (consolidation-findings.md section 14, amended by the human at the
Phase 0 / A2 stops of the authoring thread):
    content  -> question
    criteria -> answer          (self-assessment text; imperfect free_response
                                 until a recall-style self-graded qtype exists
                                 -- the named follow-up in ADR-058/backlog)
    tags     -> tags, plus "sm2-import" appended to every row
    item_id  -> DISCARDED       (identity moves to drill integer ids; no
                                 uuid/hash reintroduced, per the human's
                                 decision at the A1 stop)
    source   -> DISCARDED       (no exercise file carries one; the
                                 questions.metadata funnel extension was
                                 deliberately skipped -- provenance is the
                                 sm2-import tag plus the bank name)
    file     -> one bank per exercise file, named by the file stem, in the
                seeded category from SM2_CATEGORY_BY_BANK_NAME below.

Every record goes through the standard import funnel (parse_jsonl ->
_normalize_question_dict inside it), exactly like an HTTP JSONL upload, so
this script adds no second validation authority. The whole run is
fail-fast: all files are parsed and all target bank names checked BEFORE
the first database write, so a bad file or a name collision writes nothing.

The parser below is a deliberate ~30-line inlining of sm2's @@@ block
format (delimiter "@@@ id: <id>"; "criteria:"/"tags:"/"source:" prefixed
lines; "after:" lines discarded with a warning; remaining lines are
content). Inlined rather than imported so the script stays runnable after
sm2/ is deleted. Style contract applies: flat, pure parse, IO in main only.
"""

from __future__ import annotations

import json
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from config import DEFAULT_DATABASE_PATH  # noqa: E402
from db import (  # noqa: E402
    connect,
    init_db,
    insert_bank,
    insert_questions_bulk,
    list_banks,
    list_categories,
    run_migrations,
    utc_now_iso,
)
from logic import parse_jsonl  # noqa: E402

SM2_ITEM_DELIMITER_PREFIX = "@@@ id:"
SM2_DISCARDED_KEY_PREFIXES = ("after:",)
SM2_IMPORT_TAG = "sm2-import"

# One bank per exercise file, named by the file stem, in a seeded category.
# The mapping was decided at the authoring-thread stops: subject lives in
# tags and the bank name; categories stay the coarse seeded set.
SM2_CATEGORY_BY_BANK_NAME = {
    "biochem": "trivia",
    "c": "code",
    "driving": "trivia",
}
DEFAULT_SM2_CATEGORY = "trivia"


def parse_sm2_exercise_text(filename: str, text: str) -> tuple[list[dict], list[str]]:
    """Parse one sm2 exercise file's text into plain exercise dicts. Pure.

    Returns (exercises, warnings). Each exercise dict has content, criteria,
    and tags keys (item ids are consumed as delimiters and discarded; source
    lines are discarded -- no exercise file carries one, and provenance is
    the sm2-import tag). "after:" lines are discarded with a warning, as the
    original parser did.
    """
    exercises: list[dict] = []
    warnings: list[str] = []
    inside_block = False
    content_lines: list[str] = []
    criteria = ""
    tags: list[str] = []

    for line in text.splitlines():
        if line.startswith(SM2_ITEM_DELIMITER_PREFIX):
            if inside_block:
                exercises.append(
                    {
                        "content": "\n".join(content_lines).strip(),
                        "criteria": criteria,
                        "tags": list(tags),
                    }
                )
            inside_block = True
            content_lines = []
            criteria = ""
            tags = []
            continue
        if not inside_block:
            continue
        if line.startswith("criteria:"):
            criteria = line[len("criteria:"):].strip()
        elif line.startswith("tags:"):
            raw_tags = line[len("tags:"):].strip()
            tags = [tag.strip() for tag in raw_tags.split(",") if tag.strip() != ""]
        elif line.startswith("source:"):
            continue
        elif line.startswith(SM2_DISCARDED_KEY_PREFIXES):
            discarded_key = line.split(":", 1)[0]
            warnings.append(
                filename + ": '" + discarded_key
                + ":' is no longer supported; line discarded"
            )
        else:
            content_lines.append(line)
    if inside_block:
        exercises.append(
            {
                "content": "\n".join(content_lines).strip(),
                "criteria": criteria,
                "tags": list(tags),
            }
        )
    return exercises, warnings


def build_question_records(exercises: list[dict]) -> list[dict]:
    """Map exercise dicts to canonical question dicts THROUGH the funnel.

    Pure. Serializes the mapped records as JSONL and parses them back with
    logic.parse_jsonl -- byte-for-byte the HTTP import path -- so validation
    authority stays single. An exercise with empty content or criteria fails
    inside the funnel with its line named, which is the loud failure a
    one-off migration wants.
    """
    raw_records = []
    for exercise in exercises:
        raw_records.append(
            {
                "question": exercise["content"],
                "answer": exercise["criteria"],
                "tags": exercise["tags"] + [SM2_IMPORT_TAG],
            }
        )
    jsonl_text = "\n".join(json.dumps(record) for record in raw_records)
    return parse_jsonl(jsonl_text)


def run_sm2_content_migration(exercises_directory: str, database_path: str) -> str:
    """Parse every .md exercise file and import each as one drill bank.

    Fail-fast contract: every file is parsed and every target bank name is
    checked against existing banks BEFORE any write; a parse failure or a
    bank-name collision raises SystemExit(1) having written nothing. Returns
    a human-readable summary string; the caller prints it.
    """
    markdown_filenames = sorted(
        name for name in os.listdir(exercises_directory) if name.endswith(".md")
    )
    if not markdown_filenames:
        print("no .md exercise files in " + exercises_directory, file=sys.stderr)
        raise SystemExit(1)

    records_by_bank_name: dict = {}
    all_warnings: list[str] = []
    for filename in markdown_filenames:
        file_path = os.path.join(exercises_directory, filename)
        with open(file_path, "r", encoding="utf-8") as handle:
            text = handle.read()
        exercises, warnings = parse_sm2_exercise_text(filename, text)
        all_warnings.extend(warnings)
        bank_name = os.path.splitext(filename)[0]
        records_by_bank_name[bank_name] = build_question_records(exercises)

    connection = connect(database_path)
    try:
        init_db(connection)
        connection.commit()
        run_migrations(connection, utc_now_iso())

        existing_bank_names = {bank["name"] for bank in list_banks(connection)}
        colliding = sorted(
            name for name in records_by_bank_name if name in existing_bank_names
        )
        if colliding:
            print(
                "bank name(s) already exist (already migrated?): "
                + ", ".join(colliding) + "; nothing written",
                file=sys.stderr,
            )
            raise SystemExit(1)

        category_id_by_name = {
            category["name"]: category["id"]
            for category in list_categories(connection)
        }
        summary_lines = []
        for warning in all_warnings:
            summary_lines.append("warning: " + warning)
        created = utc_now_iso()
        for bank_name in sorted(records_by_bank_name):
            category_name = SM2_CATEGORY_BY_BANK_NAME.get(
                bank_name, DEFAULT_SM2_CATEGORY
            )
            bank_id = insert_bank(
                connection,
                category_id=category_id_by_name[category_name],
                name=bank_name,
                source="import",
                created=created,
            )
            inserted = insert_questions_bulk(
                connection, bank_id, records_by_bank_name[bank_name], created
            )
            summary_lines.append(
                "bank " + repr(bank_name) + " (category " + category_name + "): "
                + str(inserted) + " question(s)"
            )
    finally:
        connection.close()
    return "\n".join(summary_lines)


def main() -> None:
    if len(sys.argv) != 2:
        print(
            "usage: python3 tools/migrate_sm2_exercises.py <exercises_directory>",
            file=sys.stderr,
        )
        raise SystemExit(2)
    database_path = os.environ.get("DRILL_DB", DEFAULT_DATABASE_PATH)
    print(run_sm2_content_migration(sys.argv[1], database_path))


if __name__ == "__main__":
    main()
