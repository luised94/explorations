"""A3: the one-off sm2 exercise migration script.

Pins the parse mapping (content->question, criteria->answer, tags fold +
sm2-import), the single-funnel guarantee (records go through parse_jsonl),
and the fail-fast contract (a name collision writes nothing). One test runs
against the REAL sm2/exercises fixtures if they are present, so this file is
also part of the verify-before-delete evidence for the retirement commit; it
skips cleanly once sm2/ is gone, keeping the suite green post-retirement.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from _support import current_db, load_db  # noqa: E402

TOOLS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools"
)
sys.path.insert(0, TOOLS_DIR)
import migrate_sm2_exercises as migrate  # noqa: E402

_SAMPLE_EXERCISE_FILE = """\
@@@ id: sample-one
tags: alpha, beta
after: sample-zero
First question content
spanning two lines.
criteria: The first answer.

@@@ id: sample-two
tags: gamma
Second question content.
criteria: The second answer.
"""


def test_parse_maps_fields_and_folds_after_with_warning():
    exercises, warnings = migrate.parse_sm2_exercise_text(
        "sample.md", _SAMPLE_EXERCISE_FILE
    )
    assert len(exercises) == 2
    assert exercises[0]["content"] == "First question content\nspanning two lines."
    assert exercises[0]["criteria"] == "The first answer."
    assert exercises[0]["tags"] == ["alpha", "beta"]
    assert exercises[1]["content"] == "Second question content."
    assert exercises[1]["tags"] == ["gamma"]
    # 'after:' is discarded with a warning, as the original parser did.
    assert any("after:" in warning for warning in warnings)


def test_parse_ignores_preamble_before_first_delimiter():
    text = "junk line\nnot in any block\n" + _SAMPLE_EXERCISE_FILE
    exercises, _warnings = migrate.parse_sm2_exercise_text("x.md", text)
    assert len(exercises) == 2
    assert "junk line" not in exercises[0]["content"]


def test_build_records_go_through_the_funnel_and_tag():
    exercises, _warnings = migrate.parse_sm2_exercise_text(
        "sample.md", _SAMPLE_EXERCISE_FILE
    )
    records = migrate.build_question_records(exercises)
    assert records[0]["question"] == "First question content\nspanning two lines."
    assert records[0]["answer"] == "The first answer."
    assert migrate.SM2_IMPORT_TAG in records[0]["tags"]
    assert "alpha" in records[0]["tags"]
    # The funnel filled canonical defaults, proving it ran (not a hand dict).
    assert records[0]["qtype"] == "free_response"
    assert records[0]["distractors"] == []
    assert records[0]["media_url"] is None


def test_build_records_empty_criteria_fails_in_funnel():
    # criteria maps to answer; an empty answer must fail loudly (the funnel's
    # required-field check), which is what a one-off migration wants.
    exercises = [{"content": "has content", "criteria": "", "tags": []}]
    from logic import ImportParseError

    with pytest.raises(ImportParseError):
        migrate.build_question_records(exercises)


def test_migration_end_to_end_into_temp_database(tmp_path):
    dbm = load_db()
    conn = current_db(dbm, tmp_path)
    conn.close()
    database_path = str(tmp_path / "drill.db")

    exercises_dir = tmp_path / "exercises"
    exercises_dir.mkdir()
    (exercises_dir / "biochem.md").write_text(_SAMPLE_EXERCISE_FILE, encoding="utf-8")
    (exercises_dir / "c.md").write_text(
        "@@@ id: c-one\ntags: pointers\nWhat is a pointer?\ncriteria: An address.\n",
        encoding="utf-8",
    )

    summary = migrate.run_sm2_content_migration(str(exercises_dir), database_path)
    assert "biochem" in summary and "c" in summary

    conn = dbm.connect(database_path)
    banks = {bank["name"]: bank for bank in dbm.list_banks(conn)}
    assert set(banks) == {"biochem", "c"}
    categories = {c["id"]: c["name"] for c in dbm.list_categories(conn)}
    # The decided mapping: c -> code, biochem -> trivia.
    assert categories[banks["c"]["category_id"]] == "code"
    assert categories[banks["biochem"]["category_id"]] == "trivia"

    biochem_questions = dbm.list_questions(conn, banks["biochem"]["id"])
    assert len(biochem_questions) == 2
    assert all(
        migrate.SM2_IMPORT_TAG in question["tags"] for question in biochem_questions
    )
    conn.close()


def test_migration_is_fail_fast_on_bank_name_collision(tmp_path):
    dbm = load_db()
    conn = current_db(dbm, tmp_path)
    database_path = str(tmp_path / "drill.db")
    cats = {c["name"]: c["id"] for c in dbm.list_categories(conn)}
    # Pre-create a 'biochem' bank so the migration must refuse.
    dbm.insert_bank(
        conn, category_id=cats["trivia"], name="biochem", source="manual",
        created=dbm.utc_now_iso(),
    )
    conn.commit()
    conn.close()

    exercises_dir = tmp_path / "exercises"
    exercises_dir.mkdir()
    (exercises_dir / "biochem.md").write_text(_SAMPLE_EXERCISE_FILE, encoding="utf-8")
    (exercises_dir / "c.md").write_text(
        "@@@ id: c-one\nWhat is a pointer?\ncriteria: An address.\n",
        encoding="utf-8",
    )

    with pytest.raises(SystemExit) as caught:
        migrate.run_sm2_content_migration(str(exercises_dir), database_path)
    assert caught.value.code == 1

    # Nothing written: the pre-existing biochem bank is untouched and no 'c'
    # bank was created (the collision was detected before any insert).
    conn = dbm.connect(database_path)
    banks = {bank["name"] for bank in dbm.list_banks(conn)}
    assert "c" not in banks
    biochem_banks = [b for b in dbm.list_banks(conn) if b["name"] == "biochem"]
    assert len(biochem_banks) == 1
    assert dbm.list_questions(conn, biochem_banks[0]["id"]) == []
    conn.close()


@pytest.mark.skipif(
    not os.path.isdir(
        os.path.join(
            os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))),
            "sm2",
            "exercises",
        )
    ),
    reason="sm2/exercises removed at retirement; script pinned by synthetic fixtures",
)
def test_real_sm2_exercises_parse_and_import_cleanly(tmp_path):
    # Verify-before-delete: the real content migrates without error while
    # sm2/ still exists. Skips once sm2/ is retired, keeping the suite green.
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    real_exercises = os.path.join(repo_root, "sm2", "exercises")
    dbm = load_db()
    conn = current_db(dbm, tmp_path)
    conn.close()
    database_path = str(tmp_path / "drill.db")

    summary = migrate.run_sm2_content_migration(real_exercises, database_path)
    assert "question(s)" in summary

    conn = dbm.connect(database_path)
    total = sum(
        len(dbm.list_questions(conn, bank["id"])) for bank in dbm.list_banks(conn)
    )
    # The shipped fixtures are three files of five items each.
    assert total == 15
    conn.close()
