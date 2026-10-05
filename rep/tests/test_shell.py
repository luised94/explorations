"""rep/shell (PLAN.md D56): the functions are defined safely and do what
their comments say. A stub nvim logs how it was called."""

import os
import shutil
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

SHELL_DIRECTORY = Path(__file__).resolve().parent.parent / "shell"
REPOSITORY = SHELL_DIRECTORY.parent


def run_bash(home_directory: Path, script: str) -> subprocess.CompletedProcess[str]:
    """script in bash, with a stub nvim first on PATH and rep's own after it."""
    stub_directory = home_directory / "stub"
    stub_directory.mkdir(exist_ok=True)
    (stub_directory / "nvim").write_text('#!/bin/sh\nprintf "%s\\n" "$@" >> "$HOME/nvim-calls.txt"\n', encoding="utf-8")
    (stub_directory / "nvim").chmod(0o755)
    rep_executable = shutil.which("rep")
    assert rep_executable is not None, "rep is not on PATH; run the tests with `uv run pytest`"
    environment = {**os.environ, "HOME": str(home_directory), "PATH": f"{stub_directory}:{Path(rep_executable).parent}:{os.environ['PATH']}"}
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        environment.pop(variable, None)
    return subprocess.run(["bash", "-c", script], env=environment, capture_output=True, text=True, check=False)


def test_the_files_parse_and_an_alias_of_the_same_name_cannot_break_them(tmp_path: Path) -> None:
    for shell_file in ("rep.sh", "body.sh"):
        assert subprocess.run(["bash", "-n", str(SHELL_DIRECTORY / shell_file)], check=False).returncode == 0
    # The person's .bashrc broke on `body() {` after `alias body=...`.
    result = run_bash(tmp_path, f"shopt -s expand_aliases\nalias body='echo old'\nalias rep-notes='echo old'\nsource {SHELL_DIRECTORY / 'body.sh'}\nsource {SHELL_DIRECTORY / 'rep.sh'}\ndeclare -F body rep-notes rep-screen rep-nvim rep-week rep-tour")
    assert result.returncode == 0, result.stderr
    assert result.stdout.split() == ["body", "rep-notes", "rep-screen", "rep-nvim", "rep-week", "rep-tour"]


def test_body_opens_todays_form_with_the_loader(tmp_path: Path) -> None:
    (tmp_path / "learning").mkdir()
    result = run_bash(tmp_path, f"source {SHELL_DIRECTORY / 'body.sh'}\nbody")
    assert result.returncode == 0, result.stderr
    today = (datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d")
    assert (tmp_path / "nvim-calls.txt").read_text(encoding="utf-8").splitlines() == [
        "--cmd", f"luafile {REPOSITORY / 'nvim' / 'body.lua'}", str(tmp_path / "learning" / "body" / f"{today}.md"),
    ]  # fmt: skip
    assert (tmp_path / "learning" / "body").is_dir()


def test_rep_notes_starts_the_file_once_and_each_day_once(tmp_path: Path) -> None:
    (tmp_path / "learning").mkdir()
    result = run_bash(tmp_path, f"source {SHELL_DIRECTORY / 'rep.sh'}\nrep-notes\nrep-notes")
    assert result.returncode == 0, result.stderr
    notes_text = (tmp_path / "learning" / "notes.md").read_text(encoding="utf-8")
    today = (datetime.now() - timedelta(hours=4)).strftime("%Y-%m-%d")
    assert notes_text.startswith("# rep notes\n") and notes_text.count(f"\n## {today}\n- \n") == 1
    assert (tmp_path / "nvim-calls.txt").read_text(encoding="utf-8").splitlines() == ["+", str(tmp_path / "learning" / "notes.md")] * 2
