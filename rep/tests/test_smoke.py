"""Smoke test through the installed `rep` console script.

Unit tests import functions directly and never exercise the path a user
takes: the console script uv installs, the package metadata behind
--version, the exit code the shell sees. This test runs that path in a
subprocess with its own HOME, so it cannot touch the real machine setup.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

from rep.storage import acquire_writer_lock


# Bytes in and out, not text: subprocess text mode turns "\r\n" into "\n"
# when reading the output (measured), which would hide exactly the byte
# changes stamp must not make.
def run_rep(
    arguments: list[str], home_directory: Path, input_bytes: bytes = b""
) -> subprocess.CompletedProcess[bytes]:
    rep_executable = shutil.which("rep")
    assert rep_executable is not None, "rep is not on PATH; run the tests with `uv run pytest`"
    environment = dict(os.environ)
    environment["HOME"] = str(home_directory)
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        environment.pop(variable, None)
    return subprocess.run(
        [rep_executable, *arguments],
        env=environment,
        input=input_bytes,
        capture_output=True,
        check=False,
    )


def test_help_and_version(tmp_path: Path) -> None:
    help_result = run_rep(["--help"], tmp_path)
    assert help_result.returncode == 0
    assert "where" in help_result.stdout.decode()
    assert "stamp" in help_result.stdout.decode()
    version_result = run_rep(["--version"], tmp_path)
    assert version_result.returncode == 0
    assert version_result.stdout.decode().startswith("rep ")


def test_where_reports_stable_identity_and_default_root(tmp_path: Path) -> None:
    first_result = run_rep(["where"], tmp_path)
    assert first_result.returncode == 0, first_result.stderr
    assert first_result.stderr == b""
    first_lines = dict(line.split(None, 1) for line in first_result.stdout.decode().splitlines())
    assert first_lines["data_root"] == f"{tmp_path / 'learning'}  (default; does not exist yet)"
    assert first_lines["local_config"] == str(tmp_path / ".config" / "rep" / "local.toml")
    second_result = run_rep(["where"], tmp_path)
    second_lines = dict(line.split(None, 1) for line in second_result.stdout.decode().splitlines())
    assert second_lines["device_id"] == first_lines["device_id"]


def test_setup_problem_exits_2_with_message_on_stderr(tmp_path: Path) -> None:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text('device_id = "bad"\n', encoding="utf-8")
    result = run_rep(["where"], tmp_path)
    assert result.returncode == 2
    assert result.stdout == b""
    assert result.stderr.decode().startswith("rep: ")
    assert "device_id" in result.stderr.decode()


# --- rep stamp -----------------------------------------------------------------

CAPTURED_ITEMS = (
    "## @Lehninger2021\r\n"
    "\r\n"
    "### Q: What does Km measure?\r\n"
    "A: half of Vmax\r\n"
    "\r\n"
    "### Q: How does the proton gradient drive ATP synthesis?\r\n"
    "criteria: rotor turns\r\n"
).encode("utf-8")


def events_in(home_directory: Path) -> list[dict[str, object]]:
    events_directory = home_directory / "learning" / "events"
    lines: list[dict[str, object]] = []
    for events_path in sorted(events_directory.glob("*.jsonl")):
        lines.extend(json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines())
    return lines


def test_stamp_adds_ids_records_captures_and_is_idempotent(tmp_path: Path) -> None:
    (tmp_path / "learning").mkdir()
    first_result = run_rep(["stamp", "--path", "library/lehninger.md"], tmp_path, CAPTURED_ITEMS)
    assert first_result.returncode == 0, first_result.stderr
    stamped_text = first_result.stdout.decode("utf-8")
    # CRLF survives the round trip through the installed command.
    assert "\r\n" in stamped_text and "\n" not in stamped_text.replace("\r\n", "")
    stamped_ids = [line.removeprefix("id: ") for line in stamped_text.split("\r\n") if line.startswith("id: ")]
    assert [stamped_id.rsplit("-", 1)[0] for stamped_id in stamped_ids] == ["km-measure", "proton-gradient-drive"]
    events = events_in(tmp_path)
    assert [(event["kind"], event["item"]) for event in events] == [
        ("item_stamped", stamped_ids[0]),
        ("item_stamped", stamped_ids[1]),
    ]
    # A second save changes nothing and records nothing.
    second_result = run_rep(["stamp"], tmp_path, first_result.stdout)
    assert (second_result.returncode, second_result.stdout) == (0, first_result.stdout)
    assert len(events_in(tmp_path)) == 2


def test_stamp_refusals_return_the_input_unchanged(tmp_path: Path) -> None:
    broken = b"### Q: fine\nA: x\n### Q: broken\nA: y\nstray line\n"
    # No data root yet: cannot run.
    no_root = run_rep(["stamp"], tmp_path, broken)
    assert (no_root.returncode, no_root.stdout) == (2, broken)
    assert b"mkdir -p" in no_root.stderr
    (tmp_path / "learning").mkdir()
    # A parse error: problems in quickfix form, input unchanged, no events.
    parse_error = run_rep(["stamp", "--path", "library/x.md"], tmp_path, broken)
    assert (parse_error.returncode, parse_error.stdout) == (1, broken)
    assert parse_error.stderr.decode().startswith("library/x.md:5:1: error: ")
    # Not UTF-8.
    latin1 = "### Q: caf\u00e9\n".encode("latin-1")
    not_utf8 = run_rep(["stamp"], tmp_path, latin1)
    assert (not_utf8.returncode, not_utf8.stdout) == (1, latin1)
    # Another process holds the writer lock: nothing stamped, nothing recorded.
    lock_descriptor = acquire_writer_lock(tmp_path / ".local" / "state" / "rep")
    try:
        busy = run_rep(["stamp"], tmp_path, CAPTURED_ITEMS)
    finally:
        os.close(lock_descriptor)
    assert (busy.returncode, busy.stdout) == (2, CAPTURED_ITEMS)
    assert b"is writing rep data" in busy.stderr
    assert not (tmp_path / "learning" / "events").exists()


# --- rep add -------------------------------------------------------------------

CAPTURED_ITEM = b"### Q: What does Km measure?\nsource: @Lehninger2021:p80\nA: half of Vmax\n"


def library_snapshot(home_directory: Path) -> dict[str, bytes]:
    data_root = home_directory / "learning"
    return {
        str(path.relative_to(data_root)): path.read_bytes()
        for path in sorted(data_root.rglob("*"))
        if path.is_file()
    }


def test_add_files_by_citekey_stamps_records_and_only_appends(tmp_path: Path) -> None:
    (tmp_path / "learning").mkdir()
    first_result = run_rep(["add", "--stdin"], tmp_path, CAPTURED_ITEM)
    assert first_result.returncode == 0, first_result.stderr
    assert first_result.stdout.decode().startswith("added 1 to library/Lehninger2021.md: km-measure-")
    library_path = tmp_path / "learning" / "library" / "Lehninger2021.md"
    first_bytes = library_path.read_bytes()
    assert first_bytes.startswith(b"### Q: What does Km measure?\nid: km-measure-")
    second_result = run_rep(["add", "--stdin"], tmp_path, CAPTURED_ITEM.replace(b"Km", b"Vmax"))
    assert second_result.returncode == 0, second_result.stderr
    second_bytes = library_path.read_bytes()
    assert second_bytes.startswith(first_bytes + b"\n### Q: What does Vmax measure?\nid: vmax-measure-")
    assert [event["kind"] for event in events_in(tmp_path)] == ["item_stamped", "item_stamped"]


def test_add_to_a_named_topic_file(tmp_path: Path) -> None:
    (tmp_path / "learning").mkdir()
    result = run_rep(["add", "--stdin", "--to", "enzymes"], tmp_path, b"### Q: What is an enzyme?\nA: a catalyst\n")
    assert result.returncode == 0, result.stderr
    assert (tmp_path / "learning" / "library" / "enzymes.md").read_bytes().startswith(b"### Q: What is an enzyme?\nid: ")


@pytest.mark.parametrize(
    ("arguments", "input_bytes", "expected_code", "stderr_fragment"),
    [
        (["add", "--stdin"], b"### Q: no source\nA: x\n", 1, b"do not share one source citekey"),
        (["add", "--stdin"], CAPTURED_ITEM + b"### Q: other\nsource: @Other2020\nA: y\n", 1, b"do not share one source"),
        (["add", "--stdin"], b"### Q: q\nsource: @Rancourt02/22/2021\nA: x\n", 1, b"cannot be a library file name"),
        (["add", "--stdin"], CAPTURED_ITEM + b"check: fuzzy\n", 1, b"check must be"),
        (["add", "--stdin"], b"### Q: q\nsource: @Lehninger2021\n", 1, b"no answer"),
        (["add", "--stdin"], b"### Q: q\nsource: @Lehninger2021\nA: x\nstray\n", 1, b"<stdin>:4:1: error:"),
        (["add", "--stdin"], b"just notes, no item\n", 1, b"no '### Q:' item to add"),
        (["add", "--stdin"], CAPTURED_ITEM.replace(b"source", b"id: km-measure-aaaa\nsource") * 2, 1, b"appears twice"),
        (["add", "--stdin"], CAPTURED_ITEM.replace(b"source", b"id: my-own-id\nsource"), 1, b"not in the form rep writes"),
        (["add"], CAPTURED_ITEM, 2, b"--stdin"),
    ],
)
def test_add_refusals_write_nothing(
    tmp_path: Path, arguments: list[str], input_bytes: bytes, expected_code: int, stderr_fragment: bytes
) -> None:
    (tmp_path / "learning").mkdir()
    result = run_rep(arguments, tmp_path, input_bytes)
    assert result.returncode == expected_code, result.stderr
    assert stderr_fragment in result.stderr
    assert result.stdout == b""
    assert library_snapshot(tmp_path) == {}


def test_add_refuses_an_id_already_in_the_library_and_a_source_the_file_would_change(tmp_path: Path) -> None:
    library_directory = tmp_path / "learning" / "library"
    library_directory.mkdir(parents=True)
    (library_directory / "Lehninger2021.md").write_bytes(b"## @Other2020\n\n### Q: a\nid: km-measure-aaaa\nA: x\n")
    before = library_snapshot(tmp_path)
    duplicate = run_rep(["add", "--stdin"], tmp_path, CAPTURED_ITEM.replace(b"source", b"id: km-measure-aaaa\nsource"))
    assert duplicate.returncode == 1 and b"already in the library" in duplicate.stderr
    sourceless = run_rep(["add", "--stdin", "--to", "Lehninger2021"], tmp_path, b"### Q: q\nA: x\n")
    assert sourceless.returncode == 1 and b"would take its source from the heading '## @Other2020'" in sourceless.stderr
    assert library_snapshot(tmp_path) == before


def test_add_is_refused_while_another_process_writes(tmp_path: Path) -> None:
    (tmp_path / "learning").mkdir()
    lock_descriptor = acquire_writer_lock(tmp_path / ".local" / "state" / "rep")
    try:
        result = run_rep(["add", "--stdin"], tmp_path, CAPTURED_ITEM)
    finally:
        os.close(lock_descriptor)
    assert result.returncode == 2 and b"is writing rep data" in result.stderr
    assert library_snapshot(tmp_path) == {}
