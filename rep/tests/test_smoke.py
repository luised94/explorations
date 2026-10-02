"""Smoke test through the installed `rep` console script.

Unit tests import functions directly and never exercise the path a user
takes: the console script uv installs, the package metadata behind
--version, the exit code the shell sees. This test runs that path in a
subprocess with its own HOME, so it cannot touch the real machine setup.
"""

import json
import os
import pty
import select
import shutil
import subprocess
import time
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


# --- plain `rep`: a session under a real terminal (PLAN.md D9, D34, D35) ------

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


def session_home(tmp_path: Path, library_text: str) -> Path:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text('device_id = "6a2ah35zhe"\n', encoding="utf-8")
    (tmp_path / "learning" / "library").mkdir(parents=True)
    (tmp_path / "learning" / "library" / "a.md").write_text(library_text, encoding="utf-8")
    return tmp_path / "learning"


def run_rep_on_a_terminal(home_directory: Path, script: list[tuple[str, bytes]]) -> tuple[int, str]:
    """Run plain `rep` on a pseudo-terminal. For each (text, keys): wait until
    text appears in the output, then type keys (none for a step that only
    waits). Waiting for text, not for a time, keeps the test independent of
    machine speed. Keys go only after their own prompt: the session discards
    keys typed before its prompt (PLAN.md D35), so a script that types on
    seeing earlier text loses keys at random, as a person would."""
    rep_executable = shutil.which("rep")
    assert rep_executable is not None, "rep is not on PATH; run the tests with `uv run pytest`"
    environment = dict(os.environ)
    environment["HOME"] = str(home_directory)
    environment["LANG"] = environment["LC_ALL"] = "C.UTF-8"
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "EDITOR"):
        environment.pop(variable, None)
    controller_descriptor, terminal_descriptor = pty.openpty()
    process = subprocess.Popen(
        [rep_executable], env=environment, stdin=terminal_descriptor, stdout=terminal_descriptor,
        stderr=terminal_descriptor, close_fds=True,
    )  # fmt: skip
    os.close(terminal_descriptor)
    output = b""
    try:
        for expected_text, keys in script:
            deadline = time.monotonic() + 15
            while expected_text.encode() not in output:
                assert time.monotonic() < deadline, f"never saw {expected_text!r}; output so far:\n{output.decode(errors='replace')}"
                if select.select([controller_descriptor], [], [], 0.1)[0]:
                    output += os.read(controller_descriptor, 4096)
            # Only what follows a match is searched next, so one prompt
            # shown twice is waited for twice.
            output = output[output.index(expected_text.encode()) + len(expected_text.encode()):]
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
    return exit_code, output.decode(errors="replace")


def read_session_events(data_root: Path) -> list[dict[str, object]]:
    events_text = (data_root / "events" / "6a2ah35zhe.jsonl").read_text(encoding="utf-8")
    return [json.loads(line) for line in events_text.splitlines()]


def test_a_session_end_to_end_on_a_terminal(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, SESSION_LIBRARY)
    exit_code, output = run_rep_on_a_terminal(
        tmp_path,
        [
            ("0 due, 2 new. Any key starts", b" "),
            # Typed and graded by rep. "Pars", left arrow, "i": line editing
            # must give "Paris", not escape bytes in the answer (D34).
            ("Capital of France?", b""),
            ("> ", b"Pars\x1b[Di\r"),
            ("matches", b""),
            ("any key next", b" "),
            ("What does Km measure?", b""),
            ("any key reveals", b" "),
            ("y good", b"y"),
            # A new item's first showing always returns (D36); this time a
            # case slip, which exact grading counts as a miss (D20).
            ("Capital of France?", b""),
            ("> ", b"paris\r"),
            ("does not match", b""),
            ("any key next", b" "),
            ("What does Km measure?", b""),
            ("any key reveals", b" "),
            ("y good", b"y"),
            ("Capital of France?", b""),
            ("> ", b"Paris\r"),
            ("matches", b""),
            ("any key next", b" "),
            ("Session complete", b" "),
        ],
    )
    assert exit_code == 0, output
    assert "5 attempts; session completed." in output
    session_events = read_session_events(data_root)
    assert [event["kind"] for event in session_events] == ["session_start", *["attempt"] * 5, "session_end"]
    session_start, *attempts, session_end = session_events
    assert session_start["preset"] == {
        "session_budget": 60, "new_per_day": 10, "new_item_cost": 3, "relearn_gap": 3,
        "day_start_hour": 4, "desired_retention": 0.9,
    }  # fmt: skip
    assert [(attempt["item"], attempt["rating"], attempt["typed_answer"]) for attempt in attempts] == [
        ("capital-france-7q2m", 3, "Paris"),
        ("km-measure-7q2m", 3, None),
        ("capital-france-7q2m", 1, "paris"),
        ("km-measure-7q2m", 3, None),
        ("capital-france-7q2m", 3, "Paris"),
    ]
    assert all(attempt["session"] == session_start["id"] for attempt in attempts)
    assert len({attempt["day"] for attempt in attempts}) == 1
    assert all(str(attempt["fingerprint"]).startswith("f1:") for attempt in attempts)
    assert (session_end["session"], session_end["reason"]) == (session_start["id"], "completed")


def test_quitting_a_session_writes_its_end_and_no_attempt(tmp_path: Path) -> None:
    data_root = session_home(tmp_path, "### Q: What does Km measure?\nid: km-measure-7q2m\nA: half of Vmax\n")
    exit_code, output = run_rep_on_a_terminal(
        tmp_path, [("0 due, 1 new. Any key starts", b" "), ("any key reveals", b"q")]
    )
    assert exit_code == 0 and "0 attempts; session quit." in output
    assert [(event["kind"], event.get("reason")) for event in read_session_events(data_root)] == [
        ("session_start", None),
        ("session_end", "quit"),
    ]


def test_u_corrects_the_last_grade_with_an_amend(tmp_path: Path) -> None:
    data_root = session_home(
        tmp_path, SESSION_LIBRARY.replace("A: Paris\ncheck: exact\n", "A: Paris\n")
    )
    exit_code, output = run_rep_on_a_terminal(
        tmp_path,
        [
            ("Any key starts", b" "),
            ("Capital of France?", b""),
            ("any key reveals", b" "),
            ("y good", b"n"),  # a slip: meant Good
            ("What does Km measure?", b""),
            ("any key reveals", b"u"),
            ("y good  n again  any other key keeps it", b"y"),
            ("Now Good.", b""),
            ("any key reveals", b"q"),
        ],
    )
    assert exit_code == 0, output
    session_events = read_session_events(data_root)
    attempt = session_events[1]
    amend = session_events[2]
    assert (attempt["kind"], attempt["rating"]) == ("attempt", 1)
    assert (amend["kind"], amend["target"], amend["rating"]) == ("amend", attempt["id"], 3)


def test_a_session_needs_a_terminal(tmp_path: Path) -> None:
    session_home(tmp_path, SESSION_LIBRARY)
    result = run_rep([], tmp_path)
    assert result.returncode == 2 and b"a session needs a terminal" in result.stderr
