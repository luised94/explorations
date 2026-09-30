"""Files under the data root and the machine-local writer lock.

REPRESENTATION
  events directory   <data root>/events/, one file per device:
                     <device id>.jsonl, one encoded event per line, each
                     line ended by "\\n" (PLAN.md D2). Only the device named
                     in the file name writes to it, so folder sync never
                     merges two writers into one file.
  writer lock        <state directory>/lock, machine-local and never synced
                     (PLAN.md D2, I7). Held with flock by the one process
                     allowed to write; the file's content is the holder's
                     pid, for the refusal message only.
  EventFileProblem   a line or file the loader had to skip: path, 1-based
                     line (0 for a whole file), message. Lint prints it as
                     path:line:col.

INVARIANTS
  S1  load_events never raises for file content: every line it cannot use
      becomes a problem, and every other line becomes an event.
  S2  A last line without "\\n" is reported and skipped: it is either being
      written now or was cut off by a crash, and in neither case is it known
      to be the whole event (D2).
  S3  append_events writes whole lines only, in one write per call, and
      returns after fsync. If the file does not end in "\\n" (a line cut off
      by a crash), a "\\n" is written first, so the fragment stays a line of
      its own and the new events are not glued onto it.
  S4  Every appended line decodes back to the event it encodes (I11,
      checked on write), and ids are unique within a batch. Uniqueness
      across the whole log rests on 60 random bits per id (events.py) and
      is reported by the fold, not checked here: checking would mean
      reading the device's whole file on every append.
  S5  At most one process per machine holds the writer lock (I7). It is
      released by closing its descriptor or by the process ending in any
      way, including a crash, so no stale lock can remain.
"""

import errno
import fcntl
import os
from pathlib import Path
from typing import TypedDict

from rep.events import Event, EventDecodeError, decode_event, encode_event
from rep.machine import DEVICE_ID_PATTERN

EVENTS_FILE_SUFFIX = ".jsonl"


class EventFileProblem(TypedDict):
    path: str
    line: int
    message: str


class EventLoadResult(TypedDict):
    events: list[Event]
    problems: list[EventFileProblem]


class WriterLockBusy(Exception):
    """Another rep process on this machine holds the writer lock."""


def load_events(events_directory: Path) -> EventLoadResult:
    """Read every device's events file (S1, S2).

    PRE   events_directory is absolute; it may not exist yet.
    POST  events holds every line that decoded, file by file in name order
          and line order within a file (the fold sorts them itself, E2);
          problems holds every line and file that was skipped. A missing
          directory gives no events and no problems: no device has written.
    """
    events: list[Event] = []
    problems: list[EventFileProblem] = []
    if not events_directory.is_dir():
        return {"events": events, "problems": problems}

    for events_path in sorted(events_directory.iterdir()):
        device_from_name = events_path.name.removesuffix(EVENTS_FILE_SUFFIX)
        # Anything else is reported rather than read: a Syncthing
        # "*.sync-conflict-*" copy would replay events already in the real
        # file (PLAN.md D18), and a stray file is not history.
        if (
            not events_path.is_file()
            or not events_path.name.endswith(EVENTS_FILE_SUFFIX)
            or DEVICE_ID_PATTERN.match(device_from_name) is None
        ):
            problems.append(
                {
                    "path": str(events_path),
                    "line": 0,
                    "message": "not a <device id>.jsonl events file; ignored (a sync conflict copy?)",
                }
            )
            continue

        # Bytes, split on b"\n", decoded line by line: one bad byte then
        # costs one line, not the whole file.
        file_bytes = events_path.read_bytes()
        byte_lines = file_bytes.split(b"\n")
        # split leaves b"" after a final "\n"; anything else there is a line
        # with no ending (S2).
        final_fragment = byte_lines.pop()
        if final_fragment != b"":
            problems.append(
                {
                    "path": str(events_path),
                    "line": len(byte_lines) + 1,
                    "message": "last line has no line ending (being written, or cut off by a crash); skipped",
                }
            )

        for line_index, byte_line in enumerate(byte_lines):
            line_number = line_index + 1
            try:
                line_text = byte_line.decode("utf-8")
                event = decode_event(line_text)
            except UnicodeDecodeError:
                problems.append({"path": str(events_path), "line": line_number, "message": "not UTF-8; skipped"})
                continue
            except EventDecodeError as decode_error:
                problems.append({"path": str(events_path), "line": line_number, "message": f"{decode_error}; skipped"})
                continue
            if event["device"] != device_from_name:
                # Kept: the event describes itself and is valid history; only
                # where it sits is wrong. If it is also in its own device's
                # file, the fold reports the duplicate id.
                problems.append(
                    {
                        "path": str(events_path),
                        "line": line_number,
                        "message": f"event written by device {event['device']} is in this device's file; kept",
                    }
                )
            events.append(event)

    return {"events": events, "problems": problems}


def append_events(events_directory: Path, device_id: str, new_events: list[Event]) -> None:
    """Append events to this device's file and make them durable (S3, S4).

    PRE   the caller holds the writer lock (I7). events_directory's parent,
          the data root, exists: creating it here would hide a mistyped
          REP_DATA_ROOT behind a new, never-synced folder. Every event was
          written by device_id.
    POST  every event is one line at the end of <device_id>.jsonl, on disk.
    """
    batch_event_ids = [event["id"] for event in new_events]
    assert len(set(batch_event_ids)) == len(batch_event_ids), "duplicate event id in one batch"
    encoded_lines: list[str] = []
    for event in new_events:
        assert event["device"] == device_id, "an event from another device must not enter this file"
        encoded_line = encode_event(event)
        # I11, checked on write: what is written is exactly what will be read.
        assert decode_event(encoded_line) == event, f"event {event['id']} does not survive its own encoding"
        encoded_lines.append(encoded_line + "\n")
    if encoded_lines == []:
        return

    # mkdir without parents: FileNotFoundError when the data root is missing.
    directory_was_created = not events_directory.exists()
    events_directory.mkdir(exist_ok=True)
    events_path = events_directory / f"{device_id}{EVENTS_FILE_SUFFIX}"
    file_descriptor = os.open(events_path, os.O_WRONLY | os.O_APPEND | os.O_CREAT, 0o644)
    try:
        file_size = os.fstat(file_descriptor).st_size
        payload = "".join(encoded_lines).encode("utf-8")
        if file_size > 0:
            # O_APPEND does not allow reading, so the last byte comes through
            # a second, read-only descriptor.
            read_descriptor = os.open(events_path, os.O_RDONLY)
            try:
                last_byte = os.pread(read_descriptor, 1, file_size - 1)
            finally:
                os.close(read_descriptor)
            if last_byte != b"\n":
                payload = b"\n" + payload
        # os.write may write less than asked (a full disk, a signal); loop
        # until all of it is written or an error is raised.
        written_byte_count = 0
        while written_byte_count < len(payload):
            written_byte_count += os.write(file_descriptor, payload[written_byte_count:])
        os.fsync(file_descriptor)
    finally:
        os.close(file_descriptor)

    # A new file's name lives in its directory; without this fsync a crash
    # can lose the file even though its content was flushed.
    directory_to_flush = events_directory.parent if directory_was_created else events_directory
    directory_descriptor = os.open(directory_to_flush, os.O_RDONLY)
    try:
        os.fsync(directory_descriptor)
    finally:
        os.close(directory_descriptor)


def acquire_writer_lock(state_directory: Path) -> int:
    """Take the machine's writer lock without waiting (S5).

    PRE   state_directory is machine-local (machine.py M3).
    POST  returns an open descriptor that holds the lock; close it to
          release. Raises WriterLockBusy, naming the holder's pid when it is
          known, if another process holds it.
    """
    state_directory.mkdir(parents=True, exist_ok=True)
    lock_path = state_directory / "lock"
    lock_descriptor = os.open(lock_path, os.O_RDWR | os.O_CREAT, 0o644)
    try:
        fcntl.flock(lock_descriptor, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as lock_error:
        holder_pid_text = os.pread(lock_descriptor, 32, 0).decode("ascii", "replace").strip()
        os.close(lock_descriptor)
        if lock_error.errno not in (errno.EWOULDBLOCK, errno.EAGAIN):
            raise
        holder = f"process {holder_pid_text}" if holder_pid_text.isdigit() else "another process"
        raise WriterLockBusy(
            f"{holder} is writing rep data on this machine (lock {lock_path}); "
            "wait for it to finish, or close the session it belongs to"
        ) from lock_error
    # The pid is only for the message above; the lock itself is the flock.
    os.ftruncate(lock_descriptor, 0)
    os.pwrite(lock_descriptor, f"{os.getpid()}\n".encode("ascii"), 0)
    return lock_descriptor
