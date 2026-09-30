"""Events files, library files and the writer lock at their contract (storage.py S1-S5)."""

import os
import signal
import subprocess
import sys
import tempfile
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from hypothesis import given, settings
from hypothesis import strategies as strategies

from rep.events import EVENT_FORMAT_VERSION, EventDecodeError, ItemStampedEvent, format_canonical_time
from rep.machine import DEVICE_ID_ALPHABET
from rep.storage import (
    WriterLockBusy,
    acquire_writer_lock,
    append_events,
    append_library_text,
    load_events,
    read_library_files,
)

DEVICE = "6a2ah35zhe"
OTHER_DEVICE = "7b3bj46ajf"
START = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def stamped_event(position: int, device: str = DEVICE) -> ItemStampedEvent:
    # Distinct valid ids: the position written in the id alphabet.
    event_id = ""
    remaining = position
    while len(event_id) < 12:
        event_id = DEVICE_ID_ALPHABET[remaining % 32] + event_id
        remaining //= 32
    return {
        "format_version": EVENT_FORMAT_VERSION,
        "id": event_id,
        "at": format_canonical_time(START + timedelta(seconds=position)),
        "device": device,
        "kind": "item_stamped",
        "item": f"item-{position}-7q2m",
    }


def events_directory_in(tmp_path: Path) -> Path:
    # The data root exists; its events/ directory does not yet.
    return tmp_path / "events"


# --- load (S1, S2) -----------------------------------------------------------


def test_missing_directory_is_an_empty_history(tmp_path: Path) -> None:
    assert load_events(tmp_path / "events") == {"events": [], "problems": []}


def test_append_then_load_returns_the_events(tmp_path: Path) -> None:
    events_directory = events_directory_in(tmp_path)
    append_events(events_directory, DEVICE, [stamped_event(0), stamped_event(1)])
    append_events(events_directory, DEVICE, [stamped_event(2)])
    append_events(events_directory, OTHER_DEVICE, [stamped_event(3, OTHER_DEVICE)])
    loaded = load_events(events_directory)
    assert loaded["problems"] == []
    assert loaded["events"] == [stamped_event(0), stamped_event(1), stamped_event(2), stamped_event(3, OTHER_DEVICE)]


def test_bad_lines_cost_only_themselves(tmp_path: Path) -> None:
    events_directory = events_directory_in(tmp_path)
    append_events(events_directory, DEVICE, [stamped_event(0)])
    events_path = events_directory / f"{DEVICE}.jsonl"
    with events_path.open("ab") as events_file:
        events_file.write(b"{not json}\n")
        events_file.write(b'{"format_version": 1, "id": "x"}\xff\n')
    append_events(events_directory, DEVICE, [stamped_event(1)])
    with events_path.open("ab") as events_file:
        events_file.write(b'{"format_version": 1, "id": "cut off by a cra')
    loaded = load_events(events_directory)
    assert loaded["events"] == [stamped_event(0), stamped_event(1)]
    assert [(problem["line"], problem["message"].split(";")[0][:25]) for problem in loaded["problems"]] == [
        (5, "last line has no line end"),
        (2, "not JSON: Expecting prope"),
        (3, "not UTF-8"),
    ]


def test_foreign_files_are_reported_not_read(tmp_path: Path) -> None:
    events_directory = events_directory_in(tmp_path)
    append_events(events_directory, DEVICE, [stamped_event(0)])
    conflict_copy = events_directory / f"{DEVICE}.sync-conflict-20260930-120000-ABCDEFG.jsonl"
    conflict_copy.write_bytes((events_directory / f"{DEVICE}.jsonl").read_bytes())
    (events_directory / "notes.txt").write_text("hello\n")
    loaded = load_events(events_directory)
    assert loaded["events"] == [stamped_event(0)]
    assert sorted(Path(problem["path"]).name for problem in loaded["problems"]) == [conflict_copy.name, "notes.txt"]


def test_an_event_in_another_devices_file_is_kept_and_reported(tmp_path: Path) -> None:
    events_directory = events_directory_in(tmp_path)
    append_events(events_directory, OTHER_DEVICE, [stamped_event(0, OTHER_DEVICE)])
    (events_directory / f"{DEVICE}.jsonl").write_bytes((events_directory / f"{OTHER_DEVICE}.jsonl").read_bytes())
    loaded = load_events(events_directory)
    assert loaded["events"] == [stamped_event(0, OTHER_DEVICE), stamped_event(0, OTHER_DEVICE)]
    assert len(loaded["problems"]) == 1 and "is in this device's file" in loaded["problems"][0]["message"]


# --- append (S3, S4) ---------------------------------------------------------


def test_append_after_a_crash_keeps_the_fragment_on_its_own_line(tmp_path: Path) -> None:
    events_directory = events_directory_in(tmp_path)
    append_events(events_directory, DEVICE, [stamped_event(0)])
    events_path = events_directory / f"{DEVICE}.jsonl"
    with events_path.open("ab") as events_file:
        events_file.write(b'{"format_version": 1, "id": "cut')
    append_events(events_directory, DEVICE, [stamped_event(1)])
    loaded = load_events(events_directory)
    # The fragment is now a whole, invalid line 2; the new event is intact.
    assert loaded["events"] == [stamped_event(0), stamped_event(1)]
    assert [problem["line"] for problem in loaded["problems"]] == [2]


def test_append_refuses_to_create_a_missing_data_root(tmp_path: Path) -> None:
    missing_data_root = tmp_path / "mistyped"
    with pytest.raises(FileNotFoundError):
        append_events(missing_data_root / "events", DEVICE, [stamped_event(0)])
    assert not missing_data_root.exists()


def test_nothing_to_append_creates_nothing(tmp_path: Path) -> None:
    append_events(events_directory_in(tmp_path), DEVICE, [])
    assert not events_directory_in(tmp_path).exists()


def test_an_event_that_would_not_read_back_is_never_written(tmp_path: Path) -> None:
    broken_event = stamped_event(0)
    broken_event["at"] = "2026-01-01 09:00"  # not canonical: decode would reject it
    with pytest.raises((EventDecodeError, AssertionError)):
        append_events(events_directory_in(tmp_path), DEVICE, [stamped_event(1), broken_event])
    assert not (events_directory_in(tmp_path) / f"{DEVICE}.jsonl").exists()


@settings(max_examples=50)
@given(strategies.lists(strategies.integers(min_value=0, max_value=4), max_size=8))
def test_any_sequence_of_batches_loads_back_in_order(batch_sizes: list[int]) -> None:
    # tempfile, not tmp_path: a function-scoped fixture is shared by every
    # Hypothesis example, so files would leak from one example to the next.
    with tempfile.TemporaryDirectory() as temporary_directory:
        events_directory = Path(temporary_directory) / "events"
        expected_events: list[ItemStampedEvent] = []
        for batch_size in batch_sizes:
            batch = [stamped_event(len(expected_events) + offset) for offset in range(batch_size)]
            append_events(events_directory, DEVICE, list(batch))
            expected_events.extend(batch)
        loaded = load_events(events_directory)
        assert loaded["problems"] == []
        assert loaded["events"] == expected_events


# --- writer lock (S5) --------------------------------------------------------


def test_a_second_writer_is_refused_until_the_first_releases(tmp_path: Path) -> None:
    first_lock = acquire_writer_lock(tmp_path / "state")
    # flock conflicts between two open file descriptions even in one process,
    # so this stands in for a second rep process.
    with pytest.raises(WriterLockBusy, match=f"process {os.getpid()} is writing"):
        acquire_writer_lock(tmp_path / "state")
    os.close(first_lock)
    second_lock = acquire_writer_lock(tmp_path / "state")
    os.close(second_lock)


def test_a_killed_holder_leaves_no_stale_lock(tmp_path: Path) -> None:
    state_directory = tmp_path / "state"
    holder = subprocess.Popen(
        [
            sys.executable,
            "-c",
            "import sys, pathlib\n"
            "from rep.storage import acquire_writer_lock\n"
            f"acquire_writer_lock(pathlib.Path({str(state_directory)!r}))\n"
            "print('held', flush=True)\n"
            "sys.stdin.read()\n",
        ],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        text=True,
    )
    try:
        assert holder.stdout is not None and holder.stdout.readline() == "held\n"
        with pytest.raises(WriterLockBusy, match=f"process {holder.pid} is writing"):
            acquire_writer_lock(state_directory)
        # SIGKILL: no cleanup code runs, as in a crash or a closed terminal.
        holder.send_signal(signal.SIGKILL)
        holder.wait(timeout=10)
        os.close(acquire_writer_lock(state_directory))
    finally:
        if holder.poll() is None:
            holder.kill()
            holder.wait(timeout=10)


# --- library files -----------------------------------------------------------


def test_library_reader_skips_conflict_copies_and_non_utf8(tmp_path: Path) -> None:
    library_directory = tmp_path / "library"
    library_directory.mkdir()
    (library_directory / "b.md").write_text("### Q: b\n", encoding="utf-8")
    (library_directory / "a.md").write_text("### Q: a\n", encoding="utf-8")
    (library_directory / "a.sync-conflict-20260930-120000-ABCDEFG.md").write_text("### Q: a\n", encoding="utf-8")
    (library_directory / "latin.md").write_bytes("### Q: caf\u00e9\n".encode("latin-1"))
    (library_directory / "notes.txt").write_text("not a library file\n", encoding="utf-8")
    library_read = read_library_files(library_directory)
    assert [library_file["name"] for library_file in library_read["files"]] == ["a.md", "b.md"]
    assert sorted(Path(problem["path"]).name for problem in library_read["problems"]) == [
        "a.sync-conflict-20260930-120000-ABCDEFG.md",
        "latin.md",
    ]
    assert read_library_files(tmp_path / "missing") == {"files": [], "problems": []}


def test_library_append_creates_then_only_appends(tmp_path: Path) -> None:
    library_directory = tmp_path / "library"
    append_library_text(library_directory, "lehninger.md", "### Q: one\n")
    first_bytes = (library_directory / "lehninger.md").read_bytes()
    append_library_text(library_directory, "lehninger.md", "\n### Q: two\n")
    second_bytes = (library_directory / "lehninger.md").read_bytes()
    assert second_bytes.startswith(first_bytes)  # I3: create or append, never rewrite
    assert second_bytes == b"### Q: one\n\n### Q: two\n"
    with pytest.raises(FileNotFoundError):
        append_library_text(tmp_path / "mistyped" / "library", "x.md", "### Q: x\n")
