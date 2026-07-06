"""C5: the drill.py report subcommands.

The dispatch is a data table (REPORT_COMMANDS); these tests pin the table's
contents, the usage text staying generated from it, and each builder running
end to end against a real temp database (via DRILL_DB just like the real
process would -- the builders take the path as a parameter, which is what
makes them testable without spawning a subprocess or a server).
"""

import pytest

from _support import current_db, load_db, load_drill


@pytest.fixture
def populated_database(tmp_path):
    """A temp db file with one bank, one overdue schedule row, one leech,
    one failure, and one timed response. Returns (database_path, ids)."""
    dbm = load_db()
    conn = current_db(dbm, tmp_path)
    database_path = tmp_path / "drill.db"  # temp_db's filename

    cats = {c["name"]: c["id"] for c in dbm.list_categories(conn)}
    cat_id = next(cid for n, cid in cats.items() if n != "arithmetic")
    now = dbm.utc_now_iso()
    bank_id = dbm.insert_bank(
        conn, category_id=cat_id, name="cli-bank", source="manual", created=now
    )
    dbm.insert_questions_bulk(
        conn,
        bank_id,
        [
            {"question": "uno", "answer": "one"},
            {"question": "dos", "answer": "two"},
        ],
        now,
    )
    question_ids = [q["id"] for q in dbm.list_questions(conn, bank_id)]
    session_id = dbm.start_session(conn, cat_id, now, bank_id=bank_id)
    dbm.insert_response(
        conn, session_id, "uno", "one", "wrong-typed", False, now,
        question_id=question_ids[0], elapsed_ms=2100,
    )
    from datetime import date

    today = date.today().toordinal()
    # question 1: overdue and a leech (lapse_count over threshold).
    dbm.upsert_schedule_row(
        conn,
        {
            "question_id": question_ids[0],
            "easiness_factor": 1.3,
            "interval_days": 1.0,
            "repetition_count": 0,
            "due_date": today - 1,
            "last_review": today - 2,
            "lapse_count": 4,
        },
    )
    # question 2: scheduled for the future (preview material).
    dbm.upsert_schedule_row(
        conn,
        {
            "question_id": question_ids[1],
            "easiness_factor": 2.6,
            "interval_days": 6.0,
            "repetition_count": 2,
            "due_date": today + 4,
            "last_review": today - 2,
            "lapse_count": 0,
        },
    )
    conn.commit()
    conn.close()
    return str(database_path), question_ids


def test_report_commands_table_shape():
    drill = load_drill()
    assert set(drill.REPORT_COMMANDS.keys()) == {
        "stats",
        "failures",
        "leeches",
        "preview",
        "dry-run",
    }
    for command_name, entry in drill.REPORT_COMMANDS.items():
        builder, help_text = entry
        assert callable(builder)
        assert isinstance(help_text, str) and help_text


def test_usage_text_generated_from_the_table():
    drill = load_drill()
    usage = drill.build_usage_text()
    assert "serve" in usage
    for command_name in drill.REPORT_COMMANDS:
        assert command_name in usage
    for line in usage.split("\n"):
        assert line == line.rstrip()


def test_stats_report_end_to_end(populated_database):
    database_path, question_ids = populated_database
    drill = load_drill()
    report = drill.build_stats_report(database_path)
    # One graded first-attempt, wrong -> 0.0% retention over 1.
    assert "0.0%" in report
    assert "1 first-attempts-of-day" in report
    assert "free_response" in report  # default qtype of the timed response
    assert "cli-bank" in report


def test_failures_report_end_to_end(populated_database):
    database_path, question_ids = populated_database
    drill = load_drill()
    report = drill.build_failures_report(database_path)
    assert "wrong-typed" in report
    assert "cli-bank" in report


def test_leeches_report_end_to_end(populated_database):
    database_path, question_ids = populated_database
    drill = load_drill()
    report = drill.build_leeches_report(database_path)
    lines = report.split("\n")
    assert len(lines) == 2  # header plus exactly the one leech
    assert str(question_ids[0]) in lines[1]
    assert " 1.30" in lines[1]


def test_preview_report_end_to_end(populated_database):
    database_path, question_ids = populated_database
    drill = load_drill()
    report = drill.build_preview_report(database_path)
    lines = report.split("\n")
    assert len(lines) == 2  # only the future row; the overdue one is not upcoming
    assert str(question_ids[1]) in lines[1]


def test_dry_run_report_end_to_end(populated_database):
    database_path, question_ids = populated_database
    drill = load_drill()
    report = drill.build_dry_run_report(database_path)
    # question 1 is due; question 2 is scheduled for the future; there are
    # no new questions (both have schedule rows), so: 1 due, 0 new.
    assert "1 due, 0 new" in report
    lines = report.split("\n")
    assert str(question_ids[0]) in lines[2]
    assert "due" in lines[2]


def test_reporting_connection_migrates_a_fresh_file(tmp_path):
    # A report against a path that does not exist yet: open_reporting_connection
    # builds and migrates it instead of crashing on a missing table.
    drill = load_drill()
    database_path = str(tmp_path / "brand-new.db")
    report = drill.build_stats_report(database_path)
    assert "no graded reviews yet" in report
