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


# --------------------------------------------------------------------------
# A2: authoring shells. The editor loop is tested headlessly with a SCRIPTED
# $EDITOR (a python script standing in for nvim) -- the port of the spike
# demonstration in llm/spike/author_shell.py: pass 1 writes a broken buffer,
# pass 2 must see the reinserted #! error banner and fix it in place. The
# push face pins the nvim quickfix contract: exactly `file:line: message` on
# stderr, exit 1, and NO rows written on failure. Both faces append through
# the same funnel; the end-to-end tests assert the rows landed.
# --------------------------------------------------------------------------
import json as _json
import os as _os
import sys as _sys


def _write_scripted_editor(tmp_path, script_body):
    """Write a python script used as $EDITOR; returns the command list."""
    editor_path = tmp_path / "scripted_editor.py"
    editor_path.write_text(script_body, encoding="utf-8")
    return [_sys.executable, str(editor_path)]


_FIX_RETRY_EDITOR = """\
import sys
path = sys.argv[1]
text = open(path, encoding="utf-8").read()
if "#! ERROR" not in text:
    out = "q: Capital of France?\\na: Paris\\ntype: essay\\n"
else:
    assert "qtype" in text, "error banner missing from reopened buffer"
    out = text.replace("type: essay", "type: free_response")
open(path, "w", encoding="utf-8").write(out)
"""


def test_author_session_error_banner_fix_retry(tmp_path):
    drill = load_drill()
    editor_command = _write_scripted_editor(tmp_path, _FIX_RETRY_EDITOR)
    records = drill.author_session("q: \na: \n", editor_command)
    assert records is not None
    assert records[0]["answer"] == "Paris"
    assert records[0]["qtype"] == "free_response"


def test_author_session_untouched_buffer_aborts(tmp_path):
    drill = load_drill()
    do_nothing_editor = [_sys.executable, "-c", "pass"]
    assert drill.author_session("q: \na: \n", do_nothing_editor) is None


def test_author_session_emptied_buffer_aborts(tmp_path):
    drill = load_drill()
    empty_the_buffer = _write_scripted_editor(
        tmp_path,
        'import sys\nopen(sys.argv[1], "w", encoding="utf-8").write("")\n',
    )
    assert drill.author_session("q: \na: \n", empty_the_buffer) is None


def test_author_session_gives_up_after_max_attempts(tmp_path):
    drill = load_drill()
    always_broken = _write_scripted_editor(
        tmp_path,
        'import sys\n'
        'open(sys.argv[1], "w", encoding="utf-8").write("q: x\\na: y\\ntype: essay\\n")\n',
    )
    assert drill.author_session("q: \na: \n", always_broken, max_attempts=2) is None


def test_parse_author_arguments_shapes():
    drill = load_drill()
    parsed = drill.parse_author_arguments(["--bank", "biochem"])
    assert parsed == {"bank": "biochem", "category": None, "file_path": None}
    parsed = drill.parse_author_arguments(
        ["--bank", "biochem", "--category", "trivia", "notes.drill"]
    )
    assert parsed["category"] == "trivia" and parsed["file_path"] == "notes.drill"


def test_parse_author_arguments_rejects_bad_input(capsys):
    drill = load_drill()
    for bad in (
        [],
        ["--bank"],
        ["--bogus", "x"],
        ["--bank", "b", "one.drill", "two.drill"],
    ):
        with pytest.raises(SystemExit) as caught:
            drill.parse_author_arguments(bad)
        assert caught.value.code == 2
    capsys.readouterr()


def test_resolve_author_bank_option_ii_contract(tmp_path, capsys):
    # (ii) decided by the human: existing name resolves; missing name with
    # --category creates; missing name WITHOUT --category refuses (exit 2,
    # nothing created); an unknown category also refuses.
    dbm = load_db()
    drill = load_drill()
    conn = current_db(dbm, tmp_path)
    cats = {c["name"]: c["id"] for c in dbm.list_categories(conn)}
    now = dbm.utc_now_iso()
    existing_id = dbm.insert_bank(
        conn, category_id=cats["trivia"], name="existing", source="manual",
        created=now,
    )

    assert drill.resolve_author_bank(conn, "existing", None) == existing_id
    assert drill.resolve_author_bank(conn, "existing", "geography") == existing_id

    created_id = drill.resolve_author_bank(conn, "brand-new", "trivia")
    created_names = [bank["name"] for bank in dbm.list_banks(conn)]
    assert "brand-new" in created_names and created_id != existing_id

    with pytest.raises(SystemExit) as caught:
        drill.resolve_author_bank(conn, "typo-bank", None)
    assert caught.value.code == 2
    with pytest.raises(SystemExit) as caught:
        drill.resolve_author_bank(conn, "other-new", "no-such-category")
    assert caught.value.code == 2
    surviving = [bank["name"] for bank in dbm.list_banks(conn)]
    assert "typo-bank" not in surviving and "other-new" not in surviving
    conn.close()
    capsys.readouterr()


def test_push_file_end_to_end_appends_rows(tmp_path, monkeypatch, capsys):
    dbm = load_db()
    drill = load_drill()
    conn = current_db(dbm, tmp_path)
    conn.close()
    database_path = str(tmp_path / "drill.db")
    monkeypatch.setenv("DRILL_DB", database_path)

    buffer_path = tmp_path / "cards.drill"
    buffer_path.write_text(
        "q: Capital of France?\na: Paris\n\nq: Capital of Peru?\na: Lima\n",
        encoding="utf-8",
    )
    drill.run_push_command(
        ["--bank", "capitals", "--category", "geography", str(buffer_path)]
    )
    output = capsys.readouterr()
    assert "added 2 question(s)" in output.out

    conn = dbm.connect(database_path)
    bank = [b for b in dbm.list_banks(conn) if b["name"] == "capitals"][0]
    questions = dbm.list_questions(conn, bank["id"])
    assert sorted(q["answer"] for q in questions) == ["Lima", "Paris"]
    conn.close()


def test_push_stdin_end_to_end(tmp_path, monkeypatch, capsys):
    import io

    dbm = load_db()
    drill = load_drill()
    conn = current_db(dbm, tmp_path)
    conn.close()
    monkeypatch.setenv("DRILL_DB", str(tmp_path / "drill.db"))
    monkeypatch.setattr("sys.stdin", io.StringIO("q: 2+2?\na: 4\n"))
    drill.run_push_command(["--bank", "sums", "--category", "logic"])
    assert "added 1 question(s)" in capsys.readouterr().out


def test_push_parse_error_is_quickfix_shaped_and_writes_nothing(
    tmp_path, monkeypatch, capsys
):
    dbm = load_db()
    drill = load_drill()
    conn = current_db(dbm, tmp_path)
    conn.close()
    database_path = str(tmp_path / "drill.db")
    monkeypatch.setenv("DRILL_DB", database_path)

    buffer_path = tmp_path / "broken.drill"
    buffer_path.write_text("q: x\na: y\nbogus: z\n", encoding="utf-8")
    with pytest.raises(SystemExit) as caught:
        drill.run_push_command(
            ["--bank", "never-created", "--category", "trivia", str(buffer_path)]
        )
    assert caught.value.code == 1
    captured = capsys.readouterr()
    # THE quickfix contract: file:line: message, line 3 for the bogus key.
    assert captured.err.startswith(str(buffer_path) + ":3: ")
    conn = dbm.connect(database_path)
    assert all(b["name"] != "never-created" for b in dbm.list_banks(conn))
    conn.close()


def test_push_empty_buffer_refuses(tmp_path, monkeypatch, capsys):
    import io

    dbm = load_db()
    drill = load_drill()
    conn = current_db(dbm, tmp_path)
    conn.close()
    monkeypatch.setenv("DRILL_DB", str(tmp_path / "drill.db"))
    monkeypatch.setattr("sys.stdin", io.StringIO("# only a comment\n"))
    with pytest.raises(SystemExit) as caught:
        drill.run_push_command(["--bank", "sums", "--category", "logic"])
    assert caught.value.code == 1
    assert "no question blocks" in capsys.readouterr().err


def test_add_end_to_end_with_scripted_editor(tmp_path, monkeypatch, capsys):
    dbm = load_db()
    drill = load_drill()
    conn = current_db(dbm, tmp_path)
    conn.close()
    database_path = str(tmp_path / "drill.db")
    monkeypatch.setenv("DRILL_DB", database_path)

    write_two_blocks = (
        "import sys\n"
        'out = "q: Largest planet?\\na: Jupiter\\n\\nq: Smallest planet?\\na: Mercury\\n"\n'
        'open(sys.argv[1], "w", encoding="utf-8").write(out)\n'
    )
    editor_path = tmp_path / "editor.py"
    editor_path.write_text(write_two_blocks, encoding="utf-8")
    monkeypatch.setenv("EDITOR", _sys.executable + " " + str(editor_path))

    drill.run_add_command(["--bank", "planets", "--category", "trivia"])
    assert "added 2 question(s)" in capsys.readouterr().out

    conn = dbm.connect(database_path)
    bank = [b for b in dbm.list_banks(conn) if b["name"] == "planets"][0]
    answers = sorted(q["answer"] for q in dbm.list_questions(conn, bank["id"]))
    assert answers == ["Jupiter", "Mercury"]
    conn.close()


def test_add_aborted_editor_exits_one_and_writes_nothing(
    tmp_path, monkeypatch, capsys
):
    dbm = load_db()
    drill = load_drill()
    conn = current_db(dbm, tmp_path)
    conn.close()
    database_path = str(tmp_path / "drill.db")
    monkeypatch.setenv("DRILL_DB", database_path)
    monkeypatch.setenv("EDITOR", _sys.executable + " -c pass")

    with pytest.raises(SystemExit) as caught:
        drill.run_add_command(["--bank", "planets", "--category", "trivia"])
    assert caught.value.code == 1
    assert "aborted" in capsys.readouterr().err
    conn = dbm.connect(database_path)
    bank = [b for b in dbm.list_banks(conn) if b["name"] == "planets"][0]
    assert dbm.list_questions(conn, bank["id"]) == []
    conn.close()


def test_usage_lists_authoring_commands():
    drill = load_drill()
    usage = drill.build_usage_text()
    assert "add" in usage and "push" in usage
    assert set(drill.AUTHORING_COMMANDS.keys()) == {"add", "push"}
