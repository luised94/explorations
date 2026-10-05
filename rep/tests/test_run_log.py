"""The run log (run_log.py, PLAN.md D55): what one line holds, that logging
never breaks a run, and that the module stays copyable to other projects."""

import ast
import io
import json
import os
import sys
from pathlib import Path

import pytest

from rep import cli, run_log


def test_the_module_imports_only_the_standard_library() -> None:
    # D55: cut and paste into another project unchanged.
    tree = ast.parse(Path(run_log.__file__).read_text(encoding="utf-8"))
    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module is not None:
            imported_modules.add(node.module.split(".")[0])
    assert imported_modules != set() and imported_modules <= set(sys.stdlib_module_names), imported_modules


def test_a_run_is_one_line_with_its_phases_counts_and_outcome(tmp_path: Path) -> None:
    log_path = tmp_path / "state" / "runs.jsonl"
    run_record = run_log.start_run("tool", ["status", "--x"])
    run_record["command"] = "status"
    with run_log.phase(run_record, "read"):
        pass
    with run_log.phase(run_record, "read"):  # a name used twice adds up
        pass
    run_record["counts"]["items"] = 3
    run_log.finish_run(run_record, log_path, 0, None)
    lines = log_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    written = json.loads(lines[0])
    assert set(written) == {
        "at", "program", "arguments", "command", "phases", "counts", "duration_milliseconds", "exit_code", "error", "source", "python",
    }  # fmt: skip
    assert (written["program"], written["arguments"], written["command"], written["exit_code"], written["error"]) == (
        "tool", ["status", "--x"], "status", 0, None,
    )  # fmt: skip
    assert list(written["phases"]) == ["read"] and written["phases"]["read"] >= 0
    assert written["counts"] == {"items": 3} and written["duration_milliseconds"] >= 0
    assert run_log.read_runs(log_path) == [written]


def test_a_log_that_cannot_be_written_does_not_change_the_run(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    # L1: a file where the directory should be makes the write fail.
    (tmp_path / "state").write_text("not a directory", encoding="utf-8")
    run_log.finish_run(run_log.start_run("tool", []), tmp_path / "state" / "runs.jsonl", 0, None)
    assert "tool: warning: run log not written" in capsys.readouterr().err


def test_a_crash_is_logged_with_its_traceback_and_still_raised(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "learning").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        monkeypatch.delenv(variable, raising=False)

    def failing_load(events_directory: Path) -> object:
        raise RuntimeError("planted failure in load_events")

    monkeypatch.setattr(cli, "load_events", failing_load)
    with pytest.raises(RuntimeError, match="planted failure"):
        cli.main(["status"])
    last_run = run_log.read_runs(tmp_path / ".local" / "state" / "rep" / "runs.jsonl")[-1]
    assert (last_run["command"], last_run["exit_code"]) == ("status", None)
    assert "RuntimeError: planted failure in load_events" in last_run["error"]
    assert "read_library" in last_run["phases"] and "load_events" in last_run["phases"]


def test_stamp_through_main_logs_its_phases_and_the_source_hash(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / "learning").mkdir()
    monkeypatch.setenv("HOME", str(tmp_path))
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        monkeypatch.delenv(variable, raising=False)
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"### Q: q\nid: q-free-7q2m\nA: x\n")))
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(io.BytesIO()))
    assert cli.main(["stamp"]) == 0
    last_run = run_log.read_runs(tmp_path / ".local" / "state" / "rep" / "runs.jsonl")[-1]
    assert (last_run["command"], last_run["exit_code"], last_run["counts"]) == ("stamp", 0, {"stamped_items": 0})
    assert list(last_run["phases"]) == ["read_library", "stamp"]
    assert len(last_run["source"]) == 12 and os.path.basename(last_run["python"]) == last_run["python"]
