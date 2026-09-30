"""Smoke test through the installed `rep` console script.

Unit tests import functions directly and never exercise the path a user
takes: the console script uv installs, the package metadata behind
--version, the exit code the shell sees. This test runs that path in a
subprocess with its own HOME, so it cannot touch the real machine setup.
"""

import os
import shutil
import subprocess
from pathlib import Path


def run_rep(arguments: list[str], home_directory: Path) -> subprocess.CompletedProcess[str]:
    rep_executable = shutil.which("rep")
    assert rep_executable is not None, "rep is not on PATH; run the tests with `uv run pytest`"
    environment = dict(os.environ)
    environment["HOME"] = str(home_directory)
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        environment.pop(variable, None)
    return subprocess.run(
        [rep_executable, *arguments],
        env=environment,
        capture_output=True,
        text=True,
        check=False,
    )


def test_help_and_version(tmp_path: Path) -> None:
    help_result = run_rep(["--help"], tmp_path)
    assert help_result.returncode == 0
    assert "where" in help_result.stdout
    version_result = run_rep(["--version"], tmp_path)
    assert version_result.returncode == 0
    assert version_result.stdout.startswith("rep ")


def test_where_reports_stable_identity_and_default_root(tmp_path: Path) -> None:
    first_result = run_rep(["where"], tmp_path)
    assert first_result.returncode == 0, first_result.stderr
    assert first_result.stderr == ""
    first_lines = dict(line.split(None, 1) for line in first_result.stdout.splitlines())
    assert first_lines["data_root"] == f"{tmp_path / 'learning'}  (default; does not exist yet)"
    assert first_lines["local_config"] == str(tmp_path / ".config" / "rep" / "local.toml")
    second_result = run_rep(["where"], tmp_path)
    second_lines = dict(line.split(None, 1) for line in second_result.stdout.splitlines())
    assert second_lines["device_id"] == first_lines["device_id"]


def test_setup_problem_exits_2_with_message_on_stderr(tmp_path: Path) -> None:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text('device_id = "bad"\n', encoding="utf-8")
    result = run_rep(["where"], tmp_path)
    assert result.returncode == 2
    assert result.stdout == ""
    assert result.stderr.startswith("rep: ")
    assert "device_id" in result.stderr
