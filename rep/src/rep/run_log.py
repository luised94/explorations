"""Run log: one JSON line per run of a command-line program, to measure the
program itself (PLAN.md D55).

Self-contained on purpose: this module imports only the standard library and
nothing from the program that uses it, so it can be copied into another
project unchanged (a test in rep enforces this).

REPRESENTATION
  A run record is a plain dict, filled in during one run and appended as one
  line when the run ends:
    at                     start time, UTC, ISO 8601 with microseconds
    program                the program's name
    arguments              the argument list as given
    command                the subcommand, set by the program once parsed
    phases                 phase name -> milliseconds, in the order measured
    counts                 name -> number, set by the program (sizes it saw)
    duration_milliseconds  start to finish, wall clock
    exit_code              the exit code, or null when an exception ended the run
    error                  the traceback text, or null
    source                 the program's own source hash, set by the program
    python                 the interpreter's version

INVARIANTS
  L1  Logging never changes the run: a failure to write the line is reported
      on stderr once and otherwise ignored.
  L2  One line per run, written with a single append; a reader skips a line
      that does not parse (a run killed mid-write).
  L3  Nothing the person typed is logged unless it is in the arguments.
"""

import json
import sys
import time
from collections.abc import Generator
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def start_run(program: str, arguments: list[str]) -> dict[str, Any]:
    """PRE nothing. POST a record with the start time taken now."""
    return {
        "at": datetime.now(UTC).isoformat(timespec="microseconds"),
        "program": program,
        "arguments": list(arguments),
        "command": None,
        "phases": {},
        "counts": {},
        "duration_milliseconds": None,
        "exit_code": None,
        "error": None,
        "source": None,
        "python": sys.version.split()[0],
        # Not written: the monotonic start, for the duration.
        "_started": time.perf_counter(),
    }


@contextmanager
def phase(run_record: dict[str, Any], phase_name: str) -> Generator[None]:
    """Time the block under phase_name, even when it raises. A name used
    twice adds up, so a phase inside a loop reports its total."""
    phase_started = time.perf_counter()
    try:
        yield
    finally:
        elapsed_milliseconds = (time.perf_counter() - phase_started) * 1000
        run_record["phases"][phase_name] = round(run_record["phases"].get(phase_name, 0.0) + elapsed_milliseconds, 3)


def finish_run(run_record: dict[str, Any], log_path: Path | None, exit_code: int | None, error_text: str | None) -> None:
    """PRE run_record came from start_run. POST one line appended to
    log_path (its directory created), unless log_path is None or the write
    fails (L1)."""
    run_record["duration_milliseconds"] = round((time.perf_counter() - run_record["_started"]) * 1000, 3)
    run_record["exit_code"] = exit_code
    run_record["error"] = error_text
    if log_path is None:
        return
    line = json.dumps({key: value for key, value in run_record.items() if not key.startswith("_")}, ensure_ascii=False, sort_keys=True)
    try:
        log_path.parent.mkdir(parents=True, exist_ok=True)
        # One write of the whole line (L2): appends of a line this size land
        # whole on a local Linux filesystem.
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(line + "\n")
    except OSError as write_error:
        print(f"{run_record['program']}: warning: run log not written ({write_error.strerror}): {log_path}", file=sys.stderr)


def read_runs(log_path: Path) -> list[dict[str, Any]]:
    """Every run record in the file, oldest first; lines that do not parse
    are skipped (L2). A missing file has no runs."""
    if not log_path.exists():
        return []
    run_records: list[dict[str, Any]] = []
    for line in log_path.read_text(encoding="utf-8", errors="replace").splitlines():
        try:
            parsed: object = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            run_records.append(parsed)  # pyright: ignore[reportUnknownArgumentType]  (JSON: checked by the reader's use)
    return run_records
