"""Smoke test through the installed `rep` console script.

Unit tests import functions directly and never exercise the path a user
takes: the console script uv installs, the package metadata behind
--version, the exit code the shell sees. This test runs that path in a
subprocess with its own HOME, so it cannot touch the real machine setup.
"""

import fcntl
import hashlib
import importlib.metadata
import json
import os
import pty
import re
import select
import shutil
import struct
import subprocess
import sys
import termios
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest

from rep import cli
from rep.events import scheduling_day
from rep.session import DEFAULT_PRESET
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
    assert version_result.stdout.decode() == f"rep {importlib.metadata.version('rep')}\n"


def test_where_data_root_prints_only_the_path_and_keeps_the_global_flag(tmp_path: Path) -> None:
    # PLAN.md D43: what the nvim plugin reads. The global --data-root PATH and
    # where's --data-root flag share a name; argparse would let the flag's
    # False overwrite the path if they shared a destination.
    default_result = run_rep(["where", "--data-root"], tmp_path)
    assert default_result.stdout == f"{tmp_path / 'learning'}\n".encode(), default_result.stderr
    chosen_root = tmp_path / "elsewhere"
    flagged_result = run_rep(["--data-root", str(chosen_root), "where", "--data-root"], tmp_path)
    assert flagged_result.stdout == f"{chosen_root}\n".encode(), flagged_result.stderr


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


# --- rep lint ------------------------------------------------------------------

LINT_BIB = b"@book{Lehninger2021,\n}\n@article{Matsui1980,\n}\n"
ATTEMPT_LINE = (
    '{"at":"2026-09-01T10:00:00.000000Z","day":"2026-09-01","device":"6a2ah35zhe","fingerprint":"f","format_version":1,'
    '"id":"aaaaaaaaaaaa","item":"renamed-7q2m","kind":"attempt","latency_milliseconds":900,'
    '"rating":3,"session":"s","typed_answer":null}\n'
)


def lint_home(tmp_path: Path, with_bib_path: bool) -> Path:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (tmp_path / "zotero_library.bib").write_bytes(LINT_BIB)
    bib_line = f'bib_path = "{tmp_path / "zotero_library.bib"}"\n' if with_bib_path else ""
    (config_directory / "local.toml").write_text(f'device_id = "6a2ah35zhe"\n{bib_line}', encoding="utf-8")
    (tmp_path / "learning" / "library").mkdir(parents=True)
    return tmp_path / "learning"


def test_lint_reports_every_kind_of_problem_in_quickfix_form(tmp_path: Path) -> None:
    data_root = lint_home(tmp_path, with_bib_path=True)
    library_directory = data_root / "library"
    (library_directory / "a.md").write_text(
        "## @Lehninger2021\n"  # 1
        "\n"  # 2
        "### Q: fine\n"  # 3
        "id: fine-7q2m\n"  # 4
        "A: x\n"  # 5
        "?: worth its own item?\n"  # 6
        "### Q: broken\n"  # 7
        "id: broken-7q2m\n"  # 8
        "A: x\n"  # 9
        "check: fuzzy\n"  # 10
        "### Q: missing citekey\n"  # 11
        "id: missing-7q2m\n"  # 12
        "A: x\n"  # 13
        "source: @Missing2020:p3\n"  # 14
        "### Q: verified now\n"  # 15
        "id: verified-7q2m\n"  # 16
        "A: x\n"  # 17
        "source: @Matsui1980??\n"  # 18
        "### Q: from a model thread\n"  # 19
        "id: thread-7q2m\n"  # 20
        "A: x\n"  # 21
        "source: @llm:867:p15\n"  # 22
        "tags: #Bad_Tag\n",  # 23
        encoding="utf-8",
    )
    (library_directory / "b.md").write_text("### Q: twin\nid: fine-7q2m\nA: y\n", encoding="utf-8")
    (library_directory / "a.sync-conflict-20260930-120000-ABCDEFG.md").write_text("### Q: x\n", encoding="utf-8")
    events_directory = data_root / "events"
    events_directory.mkdir()
    (events_directory / "6a2ah35zhe.jsonl").write_text(ATTEMPT_LINE + "{not json}\n" + '{"cut', encoding="utf-8")

    result = run_rep(["lint"], tmp_path)
    assert result.returncode == 1, result.stderr
    library_a = library_directory / "a.md"
    library_b = library_directory / "b.md"
    conflict = library_directory / "a.sync-conflict-20260930-120000-ABCDEFG.md"
    events_file = events_directory / "6a2ah35zhe.jsonl"
    # Lint orders by path, then by line as a number (6 before 10), the
    # order a person reads a file in.
    expected_lines = sorted(
        [
            (str(library_a), 6, "note: ?: worth its own item?"),
            (str(library_a), 10, "error: check must be self, exact or numeric"),
            (str(library_a), 11, "warning: citekey Missing2020 is not in the bib"),
            (str(library_a), 15, "warning: citekey Matsui1980 is in the bib now"),
            (str(library_a), 23, "warning: tag '#Bad_Tag' is not kbd form"),
            (str(conflict), 1, "error: sync conflict copy"),
            (str(library_b), 2, f"error: id fine-7q2m is already used at {library_a}:4"),
            (str(events_file), 1, "warning: item renamed-7q2m has review history but is in no library file"),
            (str(events_file), 2, "error: not JSON"),
            (str(events_file), 3, "warning: last line has no line ending"),
        ]
    )
    output_lines = result.stdout.decode().splitlines()
    assert len(output_lines) == len(expected_lines), output_lines
    for output_line, (expected_path, expected_line, expected_text) in zip(output_lines, expected_lines, strict=True):
        assert output_line.startswith(f"{expected_path}:{expected_line}:1: {expected_text}"), output_line
    assert b"rep lint: 4 errors, 5 warnings, 1 open questions; 6 items in 2 files, 1 events" in result.stderr


def test_lint_of_a_clean_library_exits_0_and_says_when_citekeys_went_unchecked(tmp_path: Path) -> None:
    data_root = lint_home(tmp_path, with_bib_path=False)
    (data_root / "library" / "a.md").write_text("### Q: q\nid: q-7q2m3x\nA: x\nsource: @Anything\n", encoding="utf-8")
    result = run_rep(["lint"], tmp_path)
    assert (result.returncode, result.stdout) == (0, b"")
    assert b"bib_path is not set in local.toml; citekeys were not checked" in result.stderr


# --- plain `rep` and `rep review` under a real terminal (PLAN.md D34, D41, D45) ---

SESSION_LIBRARY = (
    "### Q: Capital of France?\n"
    "id: capital-france-7q2m\n"
    "A: Paris\n"
    "check: exact\n"
    "\n"
    "### Q: What does Km measure?\n"
    "id: km-measure-7q2m\n"
    "A: half of Vmax\n"
)

# The editor a test runs as $EDITOR. Each call is one pass of the sheet: it
# logs the sheet as it found it, sets the first word of every read line that
# contains one of the pass's fragments, and exits with the pass's code.
EDITOR_SCRIPT = """
import json, pathlib, sys
passes_path = pathlib.Path(sys.argv[1])
sheet_path = pathlib.Path(sys.argv[2])
log_path = passes_path.with_suffix(".log")
seen = json.loads(log_path.read_text()) if log_path.exists() else []
this_pass = json.loads(passes_path.read_text())[len(seen)]
sheet_text = sheet_path.read_text()
log_path.write_text(json.dumps([*seen, sheet_text]))
sheet_lines = sheet_text.split("\\n")
for index, line in enumerate(sheet_lines):
    for fragment, word in this_pass["words"].items():
        if line.strip() != "" and not line.startswith("#") and fragment in line:
            sheet_lines[index] = word + line[len(line.split()[0]):]
sheet_path.write_text("\\n".join(sheet_lines))
sys.exit(this_pass["exit"])
"""


def scripted_editor(tmp_path: Path, passes: list[dict[str, object]]) -> tuple[str, Path]:
    """$EDITOR for a run, and the log of the sheets it was given."""
    (tmp_path / "editor.py").write_text(EDITOR_SCRIPT, encoding="utf-8")
    (tmp_path / "passes.json").write_text(json.dumps(passes), encoding="utf-8")
    return f"{sys.executable} {tmp_path / 'editor.py'} {tmp_path / 'passes.json'}", tmp_path / "passes.log"


def session_home(tmp_path: Path, library_text: str) -> Path:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text('device_id = "6a2ah35zhe"\n', encoding="utf-8")
    (tmp_path / "learning" / "library").mkdir(parents=True)
    (tmp_path / "learning" / "library" / "a.md").write_text(library_text, encoding="utf-8")
    return tmp_path / "learning"


def run_rep_on_a_terminal(
    home_directory: Path,
    script: list[tuple[str, bytes] | dict[str, bytes]],
    editor: str = "false",
    arguments: list[str] | None = None,
) -> tuple[int, str]:
    """Run `rep` on a pseudo-terminal of 30 rows and 100 columns. For each
    (text, keys): wait until text appears in the output, then type keys
    (none for a step that only waits). Waiting for text, not for a time,
    keeps the test independent of machine speed. Keys go only after their
    own prompt: the session discards keys typed before its prompt (PLAN.md
    D35), so a script that types on seeing earlier text loses keys at
    random, as a person would. A dict step is questions shown in any order
    (later rounds, PLAN.md D48): each question's keys are typed at the
    prompt that follows it, whichever comes first."""
    rep_executable = shutil.which("rep")
    assert rep_executable is not None, "rep is not on PATH; run the tests with `uv run pytest`"
    environment = dict(os.environ)
    environment["HOME"] = str(home_directory)
    environment["LANG"] = environment["LC_ALL"] = "C.UTF-8"
    # Plain text to search; pyutils turns styling off for NO_COLOR (D46).
    environment["NO_COLOR"] = "1"
    environment["EDITOR"] = editor
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        environment.pop(variable, None)
    controller_descriptor, terminal_descriptor = pty.openpty()
    # A new pseudo-terminal reports 0 columns (measured), unlike any real
    # terminal, and pyutils would lay out to that width (FINDINGS.md F21).
    fcntl.ioctl(terminal_descriptor, termios.TIOCSWINSZ, struct.pack("HHHH", 30, 100, 0, 0))
    # As in a person's terminal, the pseudo-terminal is rep's controlling
    # terminal, so Ctrl-C reaches it as SIGINT; without this, nothing was
    # delivered (measured). preexec_fn runs after the new session is made
    # and standard input is in place.
    process = subprocess.Popen(
        [rep_executable, *(arguments or [])], env=environment, stdin=terminal_descriptor,
        stdout=terminal_descriptor, stderr=terminal_descriptor, close_fds=True, start_new_session=True,
        preexec_fn=lambda: fcntl.ioctl(0, termios.TIOCSCTTY, 0),
    )  # fmt: skip
    os.close(terminal_descriptor)
    output = b""
    seen_output = b""
    try:
        # A dict step becomes, question by question as each appears, the
        # same (question, no keys) then (prompt, keys) pair as a fixed step.
        pending_steps: list[tuple[str, bytes] | dict[str, bytes]] = list(script)
        while pending_steps != []:
            step = pending_steps.pop(0)
            if isinstance(step, dict):
                deadline = time.monotonic() + 15
                while not any(question.encode() in output for question in step):
                    assert time.monotonic() < deadline, f"never saw any of {list(step)}; output so far:\n{(seen_output + output).decode(errors='replace')}"
                    if select.select([controller_descriptor], [], [], 0.1)[0]:
                        output += os.read(controller_descriptor, 4096)
                first_question = min(
                    (question for question in step if question.encode() in output),
                    key=lambda question: output.index(question.encode()),
                )
                remaining = {question: keys for question, keys in step.items() if question != first_question}
                pending_steps[:0] = [(first_question, b""), ("> ", step[first_question])] + ([remaining] if remaining else [])
                continue
            expected_text, keys = step
            deadline = time.monotonic() + 15
            while expected_text.encode() not in output:
                assert time.monotonic() < deadline, f"never saw {expected_text!r}; output so far:\n{(seen_output + output).decode(errors='replace')}"
                if select.select([controller_descriptor], [], [], 0.1)[0]:
                    output += os.read(controller_descriptor, 4096)
            # Only what follows a match is searched next, so one prompt
            # shown twice is waited for twice.
            match_end = output.index(expected_text.encode()) + len(expected_text.encode())
            seen_output += output[:match_end]
            output = output[match_end:]
            os.write(controller_descriptor, keys)
        exit_code = process.wait(timeout=15)
        while select.select([controller_descriptor], [], [], 0.1)[0]:
            try:
                output += os.read(controller_descriptor, 4096)
            except OSError:
                break
    finally:
        process.kill()
        os.close(controller_descriptor)
    return exit_code, (seen_output + output).decode(errors="replace")


def read_session_events(data_root: Path) -> list[dict[str, object]]:
    events_text = (data_root / "events" / "6a2ah35zhe.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in events_text.splitlines()]


def test_a_session_in_rounds_end_to_end_on_a_terminal(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, SESSION_LIBRARY)
    editor, sheet_log = scripted_editor(
        tmp_path,
        [
            {"words": {"Km measure": "good"}, "exit": 0},  # round 1
            {"words": {"Km measure": "good"}, "exit": 0},  # round 2: the case slip stays Again
            {"words": {}, "exit": 0},  # round 3: saved unchanged
        ],
    )
    exit_code, output = run_rep_on_a_terminal(
        tmp_path,
        [
            ("Enter starts; Ctrl-D stops. ", b"\r"),
            # "Pars", Esc, i, "i": vi-mode editing must give "Paris", not
            # escape bytes in the answer (D34, D47).
            ("Capital of France?", b""),
            ("> ", b"Pars\x1bii\r"),
            ("What does Km measure?", b""),
            ("> ", b"half vmax\r"),
            # A new item's first showing always returns (D36), in an order
            # drawn from the session id (D48).
            ("round 2", b""),
            {"Capital of France?": b"paris\r", "What does Km measure?": b"half of Vmax\r"},
            ("round 3", b""),
            ("Capital of France?", b""),
            ("> ", b"Paris\r"),
            ("session completed", b""),
        ],
        editor=editor,
    )
    assert exit_code == 0, output
    assert "5 answers; 0 wait for `rep review`." in output
    # A 76-column card centered on 100 columns: 12 spaces before each border.
    assert "\n" + " " * 12 + "+" + "-" * 74 + "+" in output.replace("\r\n", "\n")
    assert "1 of 2" in output and "a, new, as written" in output
    # PLAN.md D51: what the session holds, its length, the keys, what comes next.
    assert "From a: 2 new." in output and "About 4 answers if each is recalled" in output
    assert "round 1: 2 items" in output and "round 2: 2 to retest" in output and "Esc v: editor" in output
    # D54: why each comes back, and what to do next.
    # France (the one exact item): Good in round 1, so round 2 is its second
    # look; Again in round 2 ("paris"), so round 3 says missed.
    assert 0 <= output.index("a, retest, second look, as written") < output.index("a, retest, missed, as written")
    # D59: the retest round says how many of each and why; the start says
    # why this many new; exact cards are flagged as checked as typed.
    assert "2 new, for a second look" in output and "1 missed: each comes back" in output
    assert "2 new: up to 10 new a day." in output and "are checked as typed" in output
    assert "Ctrl-D grades what you answered" in output
    assert "What next:" in output and "rep drill DECK     practise more now (a)" in output
    assert re.search(r"Next reviews: \d+ on \d{4}-\d{2}-\d{2}", output)
    # Nothing is revealed before the sheet (D45).
    assert "half of Vmax" not in output.replace("half of Vmax\r", "")
    session_events = read_session_events(data_root)
    assert [event["kind"] for event in session_events] == [
        "session_start", "attempt", "attempt", "amend", "attempt", "attempt", "amend", "attempt", "session_end",
    ]  # fmt: skip
    session_start, *middle, session_end = session_events
    assert session_start["preset"] == {
        "session_budget": 60, "new_per_day": 10, "new_item_cost": 3, "day_start_hour": 4, "desired_retention": 0.9,
    }  # fmt: skip
    # PLAN.md D49: the local offset, the plan as served, the code that ran.
    assert re.fullmatch(r"[+-][0-9]{2}:[0-9]{2}", str(session_start["utc_offset"]))
    assert session_start["plan"] == [
        {"item": "capital-france-7q2m", "reason": "new"}, {"item": "km-measure-7q2m", "reason": "new"},
    ]  # fmt: skip
    source_digest = hashlib.sha256()
    for source_path in sorted(Path(cli.__file__).parent.glob("*.py")):
        source_digest.update(source_path.name.encode() + b"\0" + source_path.read_bytes())
    assert session_start["rep_source"] == source_digest.hexdigest()[:12]
    attempts = [event for event in middle if event["kind"] == "attempt"]
    # Round 2's order is the session's own (D48); compare it by item.
    attempts = attempts[:2] + sorted(attempts[2:4], key=lambda attempt: str(attempt["item"])) + attempts[4:]
    assert [(attempt["item"], attempt["rating"], attempt["typed_answer"]) for attempt in attempts] == [
        ("capital-france-7q2m", 3, "Paris"),
        ("km-measure-7q2m", None, "half vmax"),
        ("capital-france-7q2m", 1, "paris"),
        ("km-measure-7q2m", None, "half of Vmax"),
        ("capital-france-7q2m", 3, "Paris"),
    ]
    amends = [event for event in middle if event["kind"] == "amend"]
    assert [(amend["target"], amend["rating"]) for amend in amends] == [(attempts[1]["id"], 3), (attempts[3]["id"], 3)]
    assert all(attempt["session"] == session_start["id"] for attempt in attempts)
    assert len({attempt["day"] for attempt in attempts}) == 1
    assert all(str(attempt["fingerprint"]).startswith("f1:") for attempt in attempts)
    assert (session_end["session"], session_end["reason"]) == (session_start["id"], "completed")
    # Each round's sheet held that round's answers, the automatic grade as
    # rep wrote it, the typed text beside the key; no sheet is left behind.
    sheets: list[str] = json.loads(sheet_log.read_text(encoding="utf-8"))
    assert len(sheets) == 3
    assert f"good    {attempts[0]['id']}  Capital of France?" in sheets[0]
    assert f"?       {attempts[1]['id']}  What does Km measure?\n#         typed:  half vmax\n#         key:    half of Vmax" in sheets[0]
    assert f"again   {attempts[2]['id']}  Capital of France?" in sheets[1]
    assert f"?       {attempts[3]['id']}  What does Km measure?" in sheets[1]
    assert str(attempts[4]["id"]) in sheets[2] and str(attempts[3]["id"]) not in sheets[2]
    assert list((tmp_path / ".local" / "state" / "rep").glob("*.txt")) == []


def test_ctrl_d_grades_what_was_answered_then_quits(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, SESSION_LIBRARY.replace("check: exact\n", ""))
    editor, sheet_log = scripted_editor(tmp_path, [{"words": {"Capital": "easy"}, "exit": 0}])
    exit_code, output = run_rep_on_a_terminal(
        tmp_path,
        [
            ("Enter starts; Ctrl-D stops. ", b"\r"),
            ("Capital of France?", b""),
            ("> ", b"Paris\r"),
            ("What does Km measure?", b""),
            ("> ", b"\x04"),
            ("session quit", b""),
        ],
        editor=editor,
    )
    assert exit_code == 0, output
    assert "1 answers; 0 wait for `rep review`." in output
    session_events = read_session_events(data_root)
    assert [(event["kind"], event.get("rating"), event.get("reason")) for event in session_events] == [
        ("session_start", None, None), ("attempt", None, None), ("amend", 4, None), ("session_end", None, "quit"),
    ]  # fmt: skip
    assert "What does Km measure?" not in json.loads(sheet_log.read_text(encoding="utf-8"))[0]


def test_ctrl_c_ends_the_session_at_once_and_leaves_the_round_for_review(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, SESSION_LIBRARY.replace("check: exact\n", ""))
    exit_code, output = run_rep_on_a_terminal(
        tmp_path,
        [
            ("Enter starts; Ctrl-D stops. ", b"\r"),
            ("Capital of France?", b""),
            ("> ", b"Paris\r"),
            ("What does Km measure?", b""),
            ("> ", b"\x03"),
            ("session interrupted", b""),
        ],
    )
    assert exit_code == 0, output
    assert "1 answers; 1 wait for `rep review`." in output and "no grade applied" not in output
    assert [(event["kind"], event.get("rating"), event.get("reason")) for event in read_session_events(data_root)] == [
        ("session_start", None, None), ("attempt", None, None), ("session_end", None, "interrupted"),
    ]  # fmt: skip


def test_stopping_before_the_first_question_writes_nothing(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, SESSION_LIBRARY)
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Enter starts; Ctrl-D stops. ", b"\x04")])
    assert exit_code == 0, output
    assert not (data_root / "events").exists()


def test_an_editor_error_applies_nothing_and_review_grades_later(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, SESSION_LIBRARY.replace("check: exact\n", ""))
    editor, _ = scripted_editor(tmp_path, [{"words": {"Km measure": "good"}, "exit": 1}])
    exit_code, output = run_rep_on_a_terminal(
        tmp_path,
        [
            ("Enter starts; Ctrl-D stops. ", b"\r"),
            ("Capital of France?", b""),
            ("> ", b"Paris\r"),
            ("What does Km measure?", b""),
            ("> ", b"\r"),  # nothing came to mind
            # D54: both left ?, so rep offers the sheet again; n leaves them.
            ("leave them for `rep review`. ", b"n\r"),
            ("session completed", b""),
        ],
        editor=editor,
    )
    assert exit_code == 0, output
    assert "no grade applied" in output and "2 answers; 2 wait for `rep review`." in output
    attempts = [event for event in read_session_events(data_root) if event["kind"] == "attempt"]
    assert [event["kind"] for event in read_session_events(data_root)].count("amend") == 0

    (tmp_path / "passes.log").unlink()
    review_editor, sheet_log = scripted_editor(
        tmp_path,
        [
            {"words": {"Km measure": "goood", "Capital": "suspend"}, "exit": 0},  # a typo: reopened
            {"words": {"Km measure": "agin"}, "exit": 0},  # another: reopened
            {"words": {"Km measure": "again"}, "exit": 0},
        ],
    )
    exit_code, output = run_rep_on_a_terminal(
        tmp_path, [("items suspended.", b"")], editor=review_editor, arguments=["review"]
    )
    assert exit_code == 0, output
    assert "1 grades written, 1 items suspended." in output
    review_events = read_session_events(data_root)[len(attempts) + 2:]
    assert [(event["kind"], event.get("target"), event.get("rating"), event.get("item")) for event in review_events] == [
        ("amend", attempts[1]["id"], 1, None), ("suspend", None, None, "capital-france-7q2m"),
    ]  # fmt: skip
    # The problem is shown right above its line; the person's other edit stays.
    second_sheet = json.loads(sheet_log.read_text(encoding="utf-8"))[1]
    problem_line = "# problem: 'goood' is not a grade (again, hard, good, easy, ?, suspend)"
    sheet_lines = second_sheet.split("\n")
    assert sheet_lines[sheet_lines.index(problem_line) + 1].split()[:2] == ["goood", attempts[1]["id"]]
    assert [attempts[0]["id"]] == [line.split()[1] for line in sheet_lines if line.startswith("suspend ")]
    assert "#         typed:  (nothing typed)" in second_sheet
    # The last pass's problem is replaced, not added to.
    third_sheet = json.loads(sheet_log.read_text(encoding="utf-8"))[2]
    assert [line for line in third_sheet.split("\n") if line.startswith("# problem: ")] == [
        "# problem: 'agin' is not a grade (again, hard, good, easy, ?, suspend)"
    ]


def test_a_session_and_review_need_a_terminal(tmp_path: Path) -> None:
    session_home(tmp_path, SESSION_LIBRARY)
    result = run_rep([], tmp_path)
    assert result.returncode == 2 and b"a session needs a terminal" in result.stderr
    result = run_rep(["review"], tmp_path)
    assert result.returncode == 2 and b"review needs a terminal" in result.stderr


# --- rep why and rep unsuspend (PLAN.md D42) -----------------------------------


def test_why_shows_the_facts_and_unsuspend_returns_a_suspended_item(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, SESSION_LIBRARY)
    (data_root / "events").mkdir()
    # An Easy a month ago, against a fingerprint that is not the item's now,
    # then a suspend.
    events_path = data_root / "events" / "6a2ah35zhe.jsonl"
    events_path.write_text(
        '{"at":"2026-09-01T10:00:00.000000Z","day":"2026-09-01","device":"6a2ah35zhe","fingerprint":"f","format_version":1,'
        '"id":"aaaaaaaaaaaa","item":"km-measure-7q2m","kind":"attempt","latency_milliseconds":900,'
        '"rating":4,"session":"s","typed_answer":"half Vmax"}\n'
        '{"at":"2026-09-01T10:01:00.000000Z","device":"6a2ah35zhe","format_version":1,'
        '"id":"bbbbbbbbbbbb","item":"km-measure-7q2m","kind":"suspend"}\n',
        encoding="utf-8",
    )
    why_result = run_rep(["why", "km-measure-7q2m"], tmp_path)
    assert why_result.returncode == 0, why_result.stderr
    why_lines = why_result.stdout.decode().splitlines()
    assert f"where       {data_root / 'library' / 'a.md'}:6" in why_lines
    assert "reviews     1 graded, 0 lapses" in why_lines
    assert "suspended   yes (rep unsuspend km-measure-7q2m)" in why_lines
    assert "today       not in the plan" in why_lines
    assert "  2026-09-01  easy   half Vmax  (item changed since)" in why_lines
    assert any(line.startswith("stability   ") for line in why_lines)

    new_item_lines = run_rep(["why", "capital-france-7q2m"], tmp_path).stdout.decode().splitlines()
    assert "memory      none yet: no graded review" in new_item_lines
    assert "today       in the plan, new" in new_item_lines

    unsuspend_result = run_rep(["unsuspend", "km-measure-7q2m"], tmp_path)
    assert unsuspend_result.stdout == b"Item km-measure-7q2m is back in sessions.\n", unsuspend_result.stderr
    assert json.loads(events_path.read_text(encoding="utf-8").splitlines()[-1])["kind"] == "unsuspend"
    # Due since early September, it is a review today.
    after_lines = run_rep(["why", "km-measure-7q2m"], tmp_path).stdout.decode().splitlines()
    assert "suspended   no" in after_lines and "today       in the plan, due" in after_lines

    event_count = len(events_path.read_text(encoding="utf-8").splitlines())
    again_result = run_rep(["unsuspend", "km-measure-7q2m"], tmp_path)
    assert again_result.stdout == b"Item km-measure-7q2m is not suspended; nothing written.\n"
    assert len(events_path.read_text(encoding="utf-8").splitlines()) == event_count

    unknown_result = run_rep(["why", "nope-0000"], tmp_path)
    assert unknown_result.returncode == 2 and b"no item nope-0000" in unknown_result.stderr


# --- rep drill (PLAN.md D50) -----------------------------------------------------

DRILL_LIBRARY = SESSION_LIBRARY.replace("A: half of Vmax\n", "A: half of Vmax\ntags: #enzymes\n")


def test_drill_names_what_exists_when_a_deck_or_tag_matches_nothing(tmp_path: Path) -> None:
    session_home(tmp_path, DRILL_LIBRARY)
    unknown_deck = run_rep(["drill", "nosuch"], tmp_path)
    assert unknown_deck.returncode == 2 and b"no deck 'nosuch'; decks: a (2)" in unknown_deck.stderr
    unknown_tag = run_rep(["drill", "a", "--tag", "zzz"], tmp_path)
    assert unknown_tag.returncode == 2 and b"no item in a is tagged #zzz; its tags: #enzymes (1)" in unknown_tag.stderr
    zero_count = run_rep(["drill", "a", "--count", "0"], tmp_path)
    assert zero_count.returncode == 2 and b"--count must be 1 or more" in zero_count.stderr


def test_a_deck_can_be_drilled_twice_in_a_day(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, DRILL_LIBRARY)
    editor, _ = scripted_editor(
        tmp_path,
        [
            {"words": {"Km measure": "good"}, "exit": 0},  # first drill, round 1
            {"words": {"Km measure": "good"}, "exit": 0},  # first drill, round 2
            {"words": {"Km measure": "good"}, "exit": 0},  # second drill, its one round
        ],
    )
    answers = {"Capital of France?": b"Paris\r", "What does Km measure?": b"half of Vmax\r"}
    exit_code, output = run_rep_on_a_terminal(
        tmp_path,
        [("Enter starts; Ctrl-D stops. ", b"\r"), answers, ("round 2", b""), answers, ("session completed", b"")],
        editor=editor, arguments=["drill", "a"],
    )  # fmt: skip
    assert exit_code == 0, output
    assert "drill a" in output and "2 of the 2 items in a." in output
    assert "2 never seen before: from today they are on your schedule, and count" in output
    assert "Grades update the schedule as a session's do" in output
    # Again the same day: both are now seen, both recalled, so one round.
    exit_code, output = run_rep_on_a_terminal(
        tmp_path, [("Enter starts; Ctrl-D stops. ", b"\r"), answers, ("session completed", b"")],
        editor=editor, arguments=["drill", "a"],
    )  # fmt: skip
    assert exit_code == 0, output
    assert "never seen before" not in output and "round 2" not in output
    starts = [event for event in read_session_events(data_root) if event["kind"] == "session_start"]
    assert [start["selection"] for start in starts] == ["a", "a"]
    assert [sorted((planned["item"], planned["reason"]) for planned in start["plan"]) for start in starts] == [  # type: ignore[union-attr]
        [("capital-france-7q2m", "new"), ("km-measure-7q2m", "new")],
        [("capital-france-7q2m", "drill"), ("km-measure-7q2m", "drill")],
    ]


def test_drill_count_and_tag_narrow_the_selection_and_say_so(tmp_path: Path) -> None:
    session_home(tmp_path, DRILL_LIBRARY)
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Enter starts; Ctrl-D stops. ", b"\x04")], arguments=["drill", "a", "--count", "1"])
    assert exit_code == 0 and "1 of the 2 items in a, drawn at random." in output, output
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Enter starts; Ctrl-D stops. ", b"\x04")], arguments=["drill", "--tag", "enzymes"])
    assert exit_code == 0 and "drill every deck #enzymes" in output and "1 of the 1 items in every deck tagged #enzymes." in output, output


def test_a_long_drill_of_every_deck_names_its_decks_and_its_length(tmp_path: Path) -> None:
    # PLAN.md D59: the person's first drill was 251 items with no sign of it.
    data_root = session_home(
        tmp_path, "".join(f"### Q: Question number {index}?\nid: question-{index}-7q2m\nA: {index}\n\n" for index in range(51))
    )
    (data_root / "library" / "b.md").write_text("### Q: Alone in b?\nid: alone-b-7q2m\nA: yes\n", encoding="utf-8")
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Enter starts; Ctrl-D stops. ", b"\x04")], arguments=["drill"])
    assert exit_code == 0, output
    assert "52 of the 52 items in every deck." in output and "From a 51, b 1." in output, output
    assert "That is a long drill: 52 items, over 8 minutes." in output and "--count 20" in output, output


def test_drill_leaves_suspended_items_out_and_says_how_many(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, DRILL_LIBRARY)
    (data_root / "events").mkdir()
    (data_root / "events" / "6a2ah35zhe.jsonl").write_text(
        '{"at":"2026-09-01T10:01:00.000000Z","device":"6a2ah35zhe","format_version":1,'
        '"id":"bbbbbbbbbbbb","item":"km-measure-7q2m","kind":"suspend"}\n',
        encoding="utf-8",
    )
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Enter starts; Ctrl-D stops. ", b"\x04")], arguments=["drill", "a"])
    assert exit_code == 0 and "1 of the 2 items in a." in output and "1 suspended, left out (`rep unsuspend ID`)." in output, output


def test_nothing_due_says_when_and_offers_a_drill(tmp_path: Path) -> None:
    # PLAN.md D51. Reviewed far in the future, so nothing is due and nothing
    # is new, whatever today's date (the clock warning is expected).
    data_root = session_home(tmp_path, SESSION_LIBRARY)
    (data_root / "events").mkdir()
    (data_root / "events" / "6a2ah35zhe.jsonl").write_text(
        "".join(
            f'{{"at":"2099-01-01T10:0{index}:00.000000Z","day":"2099-01-01","device":"6a2ah35zhe","fingerprint":"f","format_version":1,'
            f'"id":"{letter * 12}","item":"{item_id}","kind":"attempt","latency_milliseconds":900,'
            f'"rating":3,"session":"s","typed_answer":"x"}}\n'
            for index, (letter, item_id) in enumerate([("a", "capital-france-7q2m"), ("b", "km-measure-7q2m")])
        ),
        encoding="utf-8",
    )
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Nothing due today", b"")])
    assert exit_code == 0, output
    assert re.search(r"Next due: [12] on 2099-01-0\d\.", output), output
    assert "To practise more now: rep drill DECK --count 20   (decks: a (2))" in output


def test_a_finished_day_says_the_session_is_done_not_that_nothing_is_due(tmp_path: Path) -> None:
    # PLAN.md D59: after today's scheduled session completed, the empty plan
    # says so, and why no new items come: the day's allowance is used.
    data_root = session_home(tmp_path, SESSION_LIBRARY)
    (data_root / "events").mkdir()
    # Now, written as the session would: today's scheduling day, whatever
    # the hour the test runs (a day starts at 04:00 local).
    now_text = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.%fZ")
    today = scheduling_day(datetime.now(UTC), DEFAULT_PRESET["day_start_hour"])
    event_lines = [
        f'{{"at":"{now_text}","device":"6a2ah35zhe","format_version":1,"id":"ssssssssssss","kind":"session_start",'
        f'"preset":{json.dumps(DEFAULT_PRESET, sort_keys=True)}}}',
        *(
            f'{{"at":"{now_text}","day":"{today}","device":"6a2ah35zhe","fingerprint":"f","format_version":1,'
            f'"id":"{letter * 12}","item":"{item_id}","kind":"attempt","latency_milliseconds":900,'
            f'"rating":3,"session":"ssssssssssss","typed_answer":"x"}}'
            for letter, item_id in [("a", "capital-france-7q2m"), ("b", "km-measure-7q2m")]
        ),
        f'{{"at":"{now_text}","device":"6a2ah35zhe","format_version":1,"id":"eeeeeeeeeeee","kind":"session_end",'
        f'"reason":"completed","session":"ssssssssssss"}}',
    ]
    events_path = data_root / "events" / "6a2ah35zhe.jsonl"
    # Stopped early, the day is not done: the plain message.
    events_path.write_text("".join(line + "\n" for line in event_lines).replace('"completed"', '"quit"'), encoding="utf-8")
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Nothing due today", b"")])
    assert exit_code == 0 and "session is done" not in output, output
    events_path.write_text("".join(line + "\n" for line in event_lines), encoding="utf-8")
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Today's session is done", b"")])
    assert exit_code == 0, output
    assert "New items: none left" in output and "Next due:" in output, output


# --- the same items added twice (PLAN.md D52) ----------------------------------


def test_adding_the_same_file_twice_is_refused_and_lint_names_duplicates(tmp_path: Path) -> None:
    # The person's trial root grew to five copies of each deck by re-running
    # one command block; the second add must change nothing.
    (tmp_path / "learning").mkdir()
    deck = b"### Q: Capital of Chad?\nA: N'Djamena\n\n### Q: Capital of Peru?\nA: Lima\n"
    assert run_rep(["add", "--stdin", "--to", "capitals"], tmp_path, deck).returncode == 0
    before = library_snapshot(tmp_path)
    # Spacing and case do not make a question new.
    second = run_rep(["add", "--stdin", "--to", "capitals"], tmp_path, deck.replace(b"of Chad", b"of  chad").replace(b"Peru?", b"PERU?  "))
    assert second.returncode == 1
    assert b"error: this question is already in the library at library/capitals.md:1;" in second.stderr, second.stderr
    assert b"error: this question is already in the library at library/capitals.md:5;" in second.stderr, second.stderr
    assert library_snapshot(tmp_path) == before
    # Duplicates written by hand, or by an older rep: lint warns, both stay.
    (tmp_path / "learning" / "library" / "copy.md").write_text("### Q: Capital of  Peru?\nid: copy-peru-7q2m\nA: Lima\n", encoding="utf-8")
    lint = run_rep(["lint"], tmp_path)
    assert lint.returncode == 0
    assert "copy.md:1:1: warning: same question as " in lint.stdout.decode() and "capitals.md:5; added twice?" in lint.stdout.decode()


# --- rep status (PLAN.md D53) ---------------------------------------------------


def test_status_shows_the_root_each_deck_what_waits_and_today(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, SESSION_LIBRARY + "\n### Q: Capital of Peru?\nid: capital-peru-7q2m\nA: Lima\n")
    (data_root / "events").mkdir()
    now_text = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%S.000000Z")
    (data_root / "events" / "6a2ah35zhe.jsonl").write_text(
        # France reviewed long ago (due now), Peru suspended, Km answered
        # today without a grade, inside a session and a drill started today.
        '{"at":"2026-01-01T10:00:00.000000Z","day":"2026-01-01","device":"6a2ah35zhe","fingerprint":"f","format_version":1,'
        '"id":"aaaaaaaaaaaa","item":"capital-france-7q2m","kind":"attempt","latency_milliseconds":900,"rating":3,"session":"s","typed_answer":"Paris"}\n'
        '{"at":"2026-01-01T10:01:00.000000Z","device":"6a2ah35zhe","format_version":1,"id":"bbbbbbbbbbbb","item":"capital-peru-7q2m","kind":"suspend"}\n'
        f'{{"at":"{now_text}","device":"6a2ah35zhe","format_version":1,"id":"cccccccccccc","kind":"session_start","preset":{{"session_budget":60}}}}\n'
        f'{{"at":"{now_text}","device":"6a2ah35zhe","format_version":1,"id":"dddddddddddd","kind":"session_start","preset":{{"session_budget":60}},"selection":"a"}}\n'
        f'{{"at":"{now_text}","day":"2026-10-05","device":"6a2ah35zhe","fingerprint":"f","format_version":1,'
        '"id":"eeeeeeeeeeee","item":"km-measure-7q2m","kind":"attempt","latency_milliseconds":900,"rating":null,"session":"cccccccccccc","typed_answer":"x"}\n',
        encoding="utf-8",
    )
    result = run_rep(["status"], tmp_path)
    assert result.returncode == 0, result.stderr
    status_lines = result.stdout.decode().splitlines()
    assert status_lines[0] == f"data root   {data_root}  (default)"
    assert status_lines[1].startswith("today       ") and status_lines[1].endswith("(a day runs 04:00 to 04:00)")
    assert "            a                    3     1        1          1  -" in status_lines, status_lines
    assert "waiting     1 answers without a grade: rep review" in status_lines
    assert "today did   1 sessions, 1 drills" in status_lines
    missing_root = run_rep(["--data-root", str(tmp_path / "nowhere"), "status"], tmp_path)
    assert missing_root.returncode == 2 and b"(flag) does not exist" in missing_root.stderr and b"REP_DATA_ROOT" in missing_root.stderr


def test_answers_left_ungraded_are_offered_again_before_they_leave(tmp_path: Path) -> None:
    # PLAN.md D54: in the trial, seven answers left ? quietly dropped out.
    data_root = session_home(tmp_path, "### Q: What does Km measure?\nid: km-measure-7q2m\nA: half of Vmax\n")
    editor, sheet_log = scripted_editor(
        tmp_path,
        [
            {"words": {}, "exit": 0},  # saved without grading
            {"words": {"Km measure": "good"}, "exit": 0},  # offered again: graded
            {"words": {"Km measure": "good"}, "exit": 0},  # round 2, the second look
        ],
    )
    exit_code, output = run_rep_on_a_terminal(
        tmp_path,
        [
            ("Enter starts; Ctrl-D stops. ", b"\r"), ("> ", b"half\r"),
            ("1 answers left ?: an answer without a grade leaves this session", b""),
            ("leave them for `rep review`. ", b"\r"),
            ("round 2", b""), ("> ", b"half of Vmax\r"), ("session completed", b""),
        ],
        editor=editor,
    )  # fmt: skip
    assert exit_code == 0, output
    sheets: list[str] = json.loads(sheet_log.read_text(encoding="utf-8"))
    assert len(sheets) == 3 and "round 1: 1 still without a grade" in sheets[1]
    assert [event["kind"] for event in read_session_events(data_root)].count("amend") == 2


# --- explaining before acting (PLAN.md D58) -------------------------------------


def test_commands_explain_themselves_instead_of_waiting_or_failing_bare(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, SESSION_LIBRARY)
    help_text = run_rep(["--help"], tmp_path).stdout.decode()
    assert "the daily loop:" in help_text and "rep add --stdin --to capitals < capitals.md" in help_text
    assert help_text.index("today") < help_text.index("drill") < help_text.index("stamp")  # the loop's order
    # Nothing piped in: an explanation and exit 2, not a silent wait.
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("rep stamp < file.md > stamped.md", b"")], arguments=["stamp"])
    assert exit_code == 2, output
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("rep add --stdin --to DECK < file.md", b"")], arguments=["add", "--stdin"])
    assert exit_code == 2 and "### Q: What is the capital of Peru?" in output, output
    # Words from the question find an item; several matches list their ids.
    found = run_rep(["why", "km MEASURE"], tmp_path)
    assert found.returncode == 0 and b"item        km-measure-7q2m" in found.stdout, found.stderr
    several = run_rep(["unsuspend", "a"], tmp_path)  # in both questions
    assert several.returncode == 2 and b"2 items match 'a'; add words, or use an id:" in several.stderr
    assert b"capital-france-7q2m" in several.stderr and b"km-measure-7q2m" in several.stderr
    # An empty review says why and what to do.
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Start with a session", b"")], arguments=["review"])
    assert exit_code == 0 and "no answer waits for a grade, and this device has no session yet" in output, output
    # `rep today` is the session.
    exit_code, output = run_rep_on_a_terminal(tmp_path, [("Enter starts; Ctrl-D stops. ", b"\x04")], arguments=["today"])
    assert exit_code == 0 and "0 due, 2 new" in output, output
    assert not (data_root / "events").exists() or "session_start" not in (data_root / "events" / "6a2ah35zhe.jsonl").read_text(encoding="utf-8")
