"""tools/week_report.py (PLAN.md D56) on a small, complete week."""

import json
import os
import subprocess
import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

from rep.events import scheduling_day

TOOLS_DIRECTORY = Path(__file__).resolve().parent.parent / "tools"


def build_week(home_directory: Path) -> tuple[Path, str]:
    config_directory = home_directory / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text('device_id = "6a2ah35zhe"\n', encoding="utf-8")
    data_root = home_directory / "learning"
    (data_root / "library").mkdir(parents=True)
    (data_root / "library" / "permit.md").write_text(
        "### Q: Road test fee? (in dollars)\nid: road-test-fee-7q2m\nA: 35\ncheck: numeric\n\n"
        "### Q: What does a flashing red mean?\nid: flashing-red-7q2m\nA: Stop, then go when safe.\n",
        encoding="utf-8",
    )
    now = datetime.now(UTC)
    today = scheduling_day(now, 4)
    two_days_ago = (date.fromisoformat(today) - timedelta(days=2)).isoformat()
    at_now = now.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    at_later = (now + timedelta(minutes=12)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    at_earlier = (now - timedelta(days=2)).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    base = {"format_version": 1, "device": "6a2ah35zhe"}
    events = [
        {**base, "id": "aaaaaaaaaaaa", "at": at_earlier, "kind": "item_stamped", "item": "road-test-fee-7q2m"},
        {**base, "id": "aaaaaaaaaaab", "at": at_earlier, "kind": "attempt", "session": "s", "item": "road-test-fee-7q2m", "rating": 3,
         "latency_milliseconds": 4000, "typed_answer": "35", "fingerprint": "f", "day": two_days_ago},
        {**base, "id": "bbbbbbbbbbbb", "at": at_now, "kind": "item_stamped", "item": "flashing-red-7q2m"},
        {**base, "id": "cccccccccccc", "at": at_now, "kind": "session_start", "preset": {"session_budget": 60}, "utc_offset": "-04:00",
         "plan": [{"item": "road-test-fee-7q2m", "reason": "due"}, {"item": "flashing-red-7q2m", "reason": "new"}], "rep_source": "0123456789ab"},
        # A review two days after its last grade, graded by rep, corrected on the sheet.
        {**base, "id": "dddddddddddd", "at": at_now, "kind": "attempt", "session": "cccccccccccc", "item": "road-test-fee-7q2m", "rating": 1,
         "latency_milliseconds": 9000, "typed_answer": "53", "fingerprint": "f", "day": today},
        {**base, "id": "eeeeeeeeeeee", "at": at_now, "kind": "amend", "target": "dddddddddddd", "rating": 3},
        # Self-graded, left without a grade.
        {**base, "id": "ffffffffffff", "at": at_now, "kind": "attempt", "session": "cccccccccccc", "item": "flashing-red-7q2m", "rating": None,
         "latency_milliseconds": 3000, "typed_answer": "stop", "fingerprint": "f", "day": today},
        {**base, "id": "gggggggggggg", "at": at_later, "kind": "session_end", "session": "cccccccccccc", "reason": "completed"},
    ]  # fmt: skip
    (data_root / "events").mkdir()
    (data_root / "events" / "6a2ah35zhe.jsonl").write_text("".join(json.dumps(event) + "\n" for event in events), encoding="utf-8")
    (data_root / "body").mkdir()
    (data_root / "body" / f"{today}.md").write_text(
        "# notes\nbed: 12:00\nwake: 07:47\nquality: 4\ndrink: 21:30 12 5 beer\ndrink: 01:30 5 wine\ndrink: 3:00 .5\ncoffee: 08:15 8 brewed\nnote:\n",
        encoding="utf-8",
    )
    (data_root / "notes.md").write_text(f"# rep notes\n\n## 2020-01-01\n- old\n\n## {today}\n- QoL: the retest is unclear\n", encoding="utf-8")
    state_directory = home_directory / ".local" / "state" / "rep"
    state_directory.mkdir(parents=True)
    (state_directory / "runs.jsonl").write_text(
        json.dumps({"at": now.isoformat(), "command": "stamp", "duration_milliseconds": 61.0, "exit_code": 0, "error": None,
                    "phases": {"read_library": 12.5, "stamp": 3.0}, "counts": {}, "arguments": ["stamp"]}) + "\n"
        + json.dumps({"at": now.isoformat(), "command": "status", "duration_milliseconds": 40.0, "exit_code": None,
                      "error": "Traceback (most recent call last):\nRuntimeError: planted", "phases": {}, "counts": {}, "arguments": ["status"]}) + "\n"
        + "{not json\n",
        encoding="utf-8",
    )  # fmt: skip
    return data_root, today


def run_report(home_directory: Path, arguments: list[str], answers: str = "") -> subprocess.CompletedProcess[str]:
    environment = {**os.environ, "HOME": str(home_directory)}
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        environment.pop(variable, None)
    return subprocess.run(
        [sys.executable, str(TOOLS_DIRECTORY / "week_report.py"), *arguments],
        env=environment, input=answers, capture_output=True, text=True, check=False,
    )  # fmt: skip


def test_before_the_weeks_end_it_says_which_day_and_writes_nothing(tmp_path: Path) -> None:
    # PLAN.md D61: run on day one, the report covered the seven days before.
    # The week starts on the first day practised: two days ago here.
    data_root, today = build_week(tmp_path)
    two_days_ago = (date.fromisoformat(today) - timedelta(days=2)).isoformat()
    result = run_report(tmp_path, [])
    assert result.returncode == 2 and result.stdout == ""
    assert f"today is day 3 of 7 of week 1 ({two_days_ago} to " in result.stderr and "--partial" in result.stderr
    assert not (data_root / "reports").exists()
    # --start names another first day; nine days back makes this week 2.
    nine_days_ago = (date.fromisoformat(today) - timedelta(days=9)).isoformat()
    result = run_report(tmp_path, ["--start", nine_days_ago])
    assert result.returncode == 2 and f"day 3 of 7 of week 2 ({two_days_ago} to " in result.stderr


def test_the_report_computes_each_card_and_keeps_the_notes(tmp_path: Path) -> None:
    data_root, today = build_week(tmp_path)
    two_days_ago = (date.fromisoformat(today) - timedelta(days=2)).isoformat()
    result = run_report(tmp_path, ["--partial"])
    assert result.returncode == 0, result.stderr
    report_path = data_root / "reports" / f"week-{two_days_ago}.md"
    assert result.stdout.strip() == str(report_path)
    report = report_path.read_text(encoding="utf-8")
    assert "(day 3 of 7, partial)" in report.splitlines()[0]
    assert f"| {today} | 1 |" in report  # E1: one capture today
    # Both road-test attempts fall in the week; one was corrected.
    assert "graded by rep (exact, numeric): 2, of which corrected on a sheet: 1 (50%)" in report
    assert "left without a grade: 1" in report
    assert "| 2-3 | 1 | 100% |" in report  # E4: corrected to good, two days after
    assert "#### E3 consistency: 1 of 3 days with a completed scheduled session" in report
    assert "| 6.5 | road-test-fee-7q2m | permit | yes |" in report  # E5: median of 4.0 and 9.0 s
    assert "median minutes: 12 min (n=1)" in report
    # Body: 12:00 flagged; beer at 5% (1.0), wine at its usual 12% (1.0), and
    # the first template's count (0.5); 3:00 is after midnight, so last.
    body_row = next(line for line in report.splitlines() if line.startswith(f"| {today} | 12:00 |"))
    assert "| 19.8 | 4 | 2.5 | 3:00 | 96 | 08:15 |" in body_row, body_row
    assert "drink at 3:00: after midnight? 3 p.m. is 15:00" in body_row and "drink at 01:30: after midnight?" in body_row
    assert "bed 12:00: daytime? midnight is 00:00" in body_row and "wine strength estimated" in body_row
    assert "| stamp | 1 | 0 | 61 | 61 |" in report and "| status | 1 | 1 | 40 | 40 |" in report
    assert "RuntimeError: planted" in report
    assert "- QoL: the retest is unclear" in report and "- old" not in report


def test_the_form_has_an_answer_line_per_question_and_a_rerun_keeps_answers(tmp_path: Path) -> None:
    # PLAN.md D61: a form filled in nvim, not questions asked one at a time.
    data_root, today = build_week(tmp_path)
    two_days_ago = (date.fromisoformat(today) - timedelta(days=2)).isoformat()
    assert run_report(tmp_path, ["--partial"]).returncode == 0
    report_path = data_root / "reports" / f"week-{two_days_ago}.md"
    report_lines = report_path.read_text(encoding="utf-8").splitlines()
    assert report_lines.count("answer: ") == 5 + 7  # the five cards, then seven questions
    # The person answers the first card on two lines and the fifth question.
    first_card = report_lines.index("answer: ")
    report_lines[first_card : first_card + 1] = ["answer: capture was hard", "  only read on Tuesday"]
    readiness = next(index for index, line in enumerate(report_lines) if line.startswith("#### 5. Permit test readiness"))
    report_lines[readiness + 1] = "answer: 4, the drills helped"
    report_path.write_text("\n".join(report_lines) + "\n", encoding="utf-8")
    assert run_report(tmp_path, ["--partial"]).returncode == 0
    report = report_path.read_text(encoding="utf-8")
    assert "answer: capture was hard\n  only read on Tuesday\n" in report
    assert "Permit test readiness, 1 to 5. Did the drills change it, and how?\nanswer: 4, the drills helped\n" in report
    assert report.count("answer: \n") == 5 + 7 - 2
