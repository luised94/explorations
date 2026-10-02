"""Command-line shell: parse arguments, call the core, print, return an exit code.

REPRESENTATION
  The parsed arguments (argparse.Namespace) live only inside main. Every
  command is one branch of main, so the whole control flow reads top to
  bottom in one place (typer-style decorator dispatch was rejected in
  PLAN.md D13 for hiding it).

EXIT CODES (PLAN.md D30)
  0  success (for lint: no errors; warnings may have been printed)
  1  the input has problems the person must fix; nothing was written, and
     each problem is on stderr as path:line:col: severity: message (the
     quickfix format, PLAN.md D12). For lint: at least one error, listed
     on stdout in the same format.
  2  rep cannot run (bad setup, bad arguments, the writer lock is held,
     a session without a terminal or with a non-UTF-8 one); message on
     stderr, prefixed "rep: "

SESSION
  Plain `rep` (no command) runs today's session: session.py decides what
  to show, this branch reads keys, shows text and writes one event per
  action, under the lock for that append only (PLAN.md D32, D35, D40).

INVARIANTS
  Output meant for the person goes to stdout; warnings and errors go to
  stderr, so `rep ... > file` captures only results.
"""

import argparse
import codecs
import importlib.metadata
import os
# Imported for its effect on input(): line editing for typed answers
# (PLAN.md D34). libedit in uv's CPython; 0.4 ms to import.
import readline
import secrets
import shlex
import subprocess
import sys
import termios
import time
import tty
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

from rep.events import (
    EVENT_FORMAT_VERSION,
    AmendEvent,
    AttemptEvent,
    Event,
    SessionEndEvent,
    SessionStartEvent,
    SuspendEvent,
    UndoEvent,
    fold_events,
    format_canonical_time,
    new_event_id,
    new_item_stamped_events,
    scheduling_day,
)
from rep.library import (
    ITEM_ID_PATTERN,
    Item,
    LocatedItem,
    check_library_files,
    check_source_item,
    grade_typed_answer,
    item_fingerprint,
    parse_library_text,
    plan_library_append,
    stamp_library_text,
)
from rep.machine import MachineContextError, resolve_machine_context
from rep.memory_model import AGAIN, GOOD
from rep.session import DEFAULT_PRESET, plan_session, session_queue
from rep.storage import (
    LIBRARY_FILE_SUFFIX,
    WriterLockBusy,
    acquire_writer_lock,
    append_events,
    append_library_text,
    load_events,
    read_bib_citekeys,
    read_library_files,
)


def main(argument_list: list[str] | None = None) -> int:
    """Entry point for the `rep` console script.

    PRE   argument_list is None (use sys.argv) or the arguments after "rep".
    POST  returns an exit code from the table in the module docstring.
    """
    argument_parser = argparse.ArgumentParser(
        prog="rep",
        description="Retrieval practice from your readings. With no command, runs today's session. "
        "See PLAN.md and CONVENTIONS.md.",
    )
    argument_parser.add_argument(
        "--version", action="version", version=f"rep {importlib.metadata.version('rep')}"
    )
    argument_parser.add_argument(
        "--data-root",
        metavar="PATH",
        help="data folder for this run (default: $REP_DATA_ROOT, else ~/learning)",
    )
    subcommand_parsers = argument_parser.add_subparsers(dest="command", metavar="COMMAND")
    subcommand_parsers.add_parser(
        "where",
        help="show where rep keeps its files on this machine, and this device's id",
    )
    stamp_parser = subcommand_parsers.add_parser(
        "stamp",
        help="read a library file on stdin and write it to stdout with an id on every item (nvim runs this on save)",
    )
    # stdin has no name; nvim passes the buffer's, so problems land in quickfix
    # on the right file.
    stamp_parser.add_argument("--path", metavar="PATH", default="<stdin>", help="file name to use in problem messages")
    add_parser = subcommand_parsers.add_parser(
        "add",
        help="append new items to the library, with ids (the nvim capture key sends them here)",
    )
    # Required and alone for now: plain `rep add` is left free for a future
    # editor-template mode, and PLAN.md D12 names this form.
    add_parser.add_argument("--stdin", action="store_true", required=True, help="read the items from standard input")
    add_parser.add_argument(
        "--to",
        metavar="NAME",
        help="library file to append to (default: <citekey>.md from the items' source)",
    )
    subcommand_parsers.add_parser(
        "lint",
        help="check the whole library and the events; print problems as path:line:col for quickfix",
    )

    parsed_arguments = argument_parser.parse_args(argument_list)
    command: str | None = parsed_arguments.command
    data_root_flag: str | None = parsed_arguments.data_root

    try:
        machine_context = resolve_machine_context(
            data_root_flag=data_root_flag,
            environment=os.environ,
            home_directory=Path.home(),
        )
    except MachineContextError as setup_error:
        print(f"rep: {setup_error}", file=sys.stderr)
        return 2
    for warning in machine_context["warnings"]:
        print(f"rep: warning: {warning}", file=sys.stderr)

    if command == "where":
        # Inspectability: every path rep will read or write, in one place,
        # with the rule that chose the data root.
        data_root_note = machine_context["data_root_source"]
        if not machine_context["data_root_exists"]:
            data_root_note += "; does not exist yet"
        bib_path = machine_context["bib_path"]
        kbd_root = machine_context["kbd_root"]
        print(f"data_root        {machine_context['data_root']}  ({data_root_note})")
        print(f"device_id        {machine_context['device_id']}")
        print(f"local_config     {machine_context['local_config_path']}")
        print(f"state_directory  {machine_context['state_directory']}")
        print(f"bib_path         {bib_path if bib_path is not None else '(not set)'}")
        print(f"kbd_root         {kbd_root if kbd_root is not None else '(not set)'}")
        return 0

    if command is None:
        # PLAN.md D9: plain `rep` runs today's session. Every decision about
        # what to show is in session.py, pure; this branch reads keys, shows
        # text and writes events.
        data_root = machine_context["data_root"]
        if not machine_context["data_root_exists"]:
            # PLAN.md D28: rep never creates the data root.
            print(f"rep: data root {data_root} does not exist; create it with: mkdir -p {data_root}", file=sys.stderr)
            return 2
        if not sys.stdin.isatty() or not sys.stdout.isatty():
            print("rep: a session needs a terminal on standard input and output", file=sys.stderr)
            return 2
        # PLAN.md D34: under a non-UTF-8 locale stdin decodes with
        # surrogateescape, and an answer could not be written after the
        # person had typed it.
        if codecs.lookup(sys.stdin.encoding or "ascii").name != "utf-8":
            print(
                f"rep: the terminal's encoding is {sys.stdin.encoding}; a session needs UTF-8 (export LANG=C.UTF-8)",
                file=sys.stderr,
            )
            return 2
        # PLAN.md D34: the up arrow must not bring back an earlier answer.
        readline.set_auto_history(False)

        preset = DEFAULT_PRESET
        library_read = read_library_files(data_root / "library")
        library_check = check_library_files(
            [(library_file["path"], library_file["text"]) for library_file in library_read["files"]]
        )
        events_load = load_events(data_root / "events")
        fold_result = fold_events(events_load["events"], desired_retention=preset["desired_retention"])
        excluded_item_count = library_check["item_count"] - len(library_check["located_items"])
        if excluded_item_count > 0:
            print(f"rep: {excluded_item_count} items are left out by errors; `rep lint` lists them", file=sys.stderr)
        file_problem_count = len(library_read["problems"]) + len(events_load["problems"]) + len(fold_result["problems"])
        if file_problem_count > 0:
            print(f"rep: {file_problem_count} problems in library or event files; `rep lint` lists them", file=sys.stderr)
        started_at = datetime.now(UTC)
        newest_event_at = max((event["at"] for event in events_load["events"]), default=None)
        # PLAN.md D40: WSL2's clock can fall behind after the host sleeps,
        # and a time behind the log sorts new events before old ones.
        if newest_event_at is not None and format_canonical_time(started_at) < newest_event_at:
            print(
                f"rep: warning: this machine's clock ({format_canonical_time(started_at)}) is behind the newest "
                f"event ({newest_event_at}); check `date` before practising",
                file=sys.stderr,
            )
        today = scheduling_day(started_at, preset["day_start_hour"])
        plan = plan_session(library_check["located_items"], fold_result["items"], events_load["events"], today, preset)
        if plan == []:
            print(f"Nothing to practise today ({today}).")
            return 0
        located_items_by_id: dict[str, LocatedItem] = {
            located_item["item"]["id"]: located_item for located_item in library_check["located_items"]
        }
        due_count = sum(1 for slot in plan if slot["reason"] == "due")
        device_id = machine_context["device_id"]
        terminal_descriptor = sys.stdin.fileno()
        cooked_attributes = termios.tcgetattr(terminal_descriptor)
        session_events: list[Event] = []
        grade_names = {None: "?", AGAIN: "Again", 2: "Hard", GOOD: "Good", 4: "Easy"}

        def read_key(prompt: str) -> str:
            """Show prompt, then read one key press, no Enter. Keys pressed
            before the prompt was shown are discarded (PLAN.md D35): a key
            counts only once what it answers is on screen, so a grade cannot
            precede the answer and a latency cannot be zero. The flush comes
            before the prompt: after it, a key pressed in the moment between
            seeing the prompt and the flush would be lost (found by the
            terminal smoke test)."""
            termios.tcflush(terminal_descriptor, termios.TCIFLUSH)
            print(prompt, flush=True)
            # TCSANOW: tty.setcbreak's default, TCSAFLUSH, would also discard
            # input; the flush above is the deliberate one (spike, PLAN.md
            # section 3).
            tty.setcbreak(terminal_descriptor, termios.TCSANOW)
            try:
                return os.read(terminal_descriptor, 16).decode("utf-8", "replace")
            finally:
                termios.tcsetattr(terminal_descriptor, termios.TCSADRAIN, cooked_attributes)

        def write_events(new_events: list[Event]) -> None:
            """Append under the writer lock, held for this append only, waiting
            for it rather than refusing (PLAN.md D32)."""
            lock_wait_started_at = time.monotonic()
            person_was_told = False
            while True:
                try:
                    lock_descriptor = acquire_writer_lock(machine_context["state_directory"])
                    break
                except WriterLockBusy as lock_busy:
                    if not person_was_told and time.monotonic() - lock_wait_started_at > 2.0:
                        print(f"rep: {lock_busy}; waiting (Ctrl-C ends the session)", file=sys.stderr)
                        person_was_told = True
                    time.sleep(0.05)
            try:
                append_events(data_root / "events", device_id, new_events)
            finally:
                os.close(lock_descriptor)
            session_events.extend(new_events)

        if read_key(f"{due_count} due, {len(plan) - due_count} new. Any key starts; q stops.") == "q":
            return 0
        session_start: SessionStartEvent = {
            "format_version": EVENT_FORMAT_VERSION,
            "id": new_event_id(secrets.token_bytes),
            "at": format_canonical_time(datetime.now(UTC)),
            "device": device_id,
            "kind": "session_start",
            # PLAN.md D40: the values used, so the history describes itself.
            "preset": {
                "session_budget": preset["session_budget"],
                "new_per_day": preset["new_per_day"],
                "new_item_cost": preset["new_item_cost"],
                "relearn_gap": preset["relearn_gap"],
                "day_start_hour": preset["day_start_hour"],
                "desired_retention": preset["desired_retention"],
            },
        }
        # The last attempt or suspend: what `u` corrects (PLAN.md D35).
        last_correctable_event: AttemptEvent | SuspendEvent | None = None

        def correct_last_action() -> None:
            """`u`: a grade is corrected with an amend, a suspend with an undo;
            the attempt itself stays in the history (PLAN.md D35)."""
            nonlocal last_correctable_event
            if last_correctable_event is None:
                print("Nothing to correct.")
                return
            if last_correctable_event["kind"] == "suspend":
                undo: UndoEvent = {
                    "format_version": EVENT_FORMAT_VERSION,
                    "id": new_event_id(secrets.token_bytes),
                    "at": format_canonical_time(datetime.now(UTC)),
                    "device": device_id,
                    "kind": "undo",
                    "target": last_correctable_event["id"],
                }
                write_events([undo])
                print(f"Suspend of {last_correctable_event['item']} undone.")
                last_correctable_event = None
                return
            corrected_question = located_items_by_id[last_correctable_event["item"]]["item"]["question"]
            print(f"Correct the grade of: {corrected_question.splitlines()[0]}")
            correction_key = read_key("y good  n again  any other key keeps it")
            if correction_key != "y" and correction_key != "n":
                print("Kept.")
                return
            amend: AmendEvent = {
                "format_version": EVENT_FORMAT_VERSION,
                "id": new_event_id(secrets.token_bytes),
                "at": format_canonical_time(datetime.now(UTC)),
                "device": device_id,
                "kind": "amend",
                "target": last_correctable_event["id"],
                "rating": GOOD if correction_key == "y" else AGAIN,
            }
            write_events([amend])
            print(f"Now {grade_names[amend['rating']]}.")

        end_reason: Literal["completed", "quit", "interrupted"] = "interrupted"
        attempt_count = 0
        session_was_started = False
        try:
            write_events([session_start])
            session_was_started = True
            while True:
                queue = session_queue(plan, session_events, preset)
                if queue == []:
                    if last_correctable_event is not None:
                        if read_key("\nSession complete. u corrects the last grade; any other key ends.") == "u":
                            correct_last_action()
                            continue  # an amend to Again can bring the item back
                    end_reason = "completed"
                    break

                # --- show the question; the person commits before the reveal ---
                slot = queue[0]
                located_item = located_items_by_id[slot["item_id"]]
                item = located_item["item"]
                print(f"\n[{len(queue)} to go] {slot['reason']}  {item['id']}")
                print(item["question"])
                shown_at = time.monotonic()
                typed_answer: str | None = None
                if item["attempt"] == "typed":
                    termios.tcflush(terminal_descriptor, termios.TCIFLUSH)
                    while True:
                        typed_answer = input("> ")
                        # PLAN.md D34: a lone surrogate is a byte that is not
                        # UTF-8; it could not be written to the events file.
                        if not any("\ud800" <= character <= "\udfff" for character in typed_answer):
                            break
                        print("That was not valid UTF-8; type it again.")
                else:
                    key = read_key("(any key reveals; u corrects the last grade, q quits)")
                    if key == "q":
                        end_reason = "quit"
                        break
                    if key == "u":
                        correct_last_action()
                        continue  # the question is shown again, its latency restarts
                latency_milliseconds = round((time.monotonic() - shown_at) * 1000)
                committed_at = datetime.now(UTC)

                # --- the reveal ---
                if item["answer"] is not None:
                    print("A: " + item["answer"].replace("\n", "\n   "))
                if item["criteria"] is not None:
                    print("grade against:")
                    for criterion in item["criteria"]:
                        print(f"  - {criterion}")
                automatic_rating: int | None = None
                if item["check"] != "self":
                    assert typed_answer is not None, "check_source_item makes exact and numeric typed"
                    automatic_rating = GOOD if grade_typed_answer(item, typed_answer) else AGAIN
                    print(f"you typed: {typed_answer}  ->  {'matches' if automatic_rating == GOOD else 'does not match'}")
                elif typed_answer is not None:
                    print(f"you typed: {typed_answer}")

                # --- the grade ---
                while True:
                    if automatic_rating is None:
                        key = read_key("y good  n again  ? grade later  s suspend  e edit  u correct last  q quit")
                    else:
                        key = read_key("any key next  e edit  s suspend  u correct last  q quit")
                    if key == "u":
                        correct_last_action()
                        continue
                    if automatic_rating is not None or key in ("y", "n", "?", "s", "e", "q"):
                        break
                if key == "q":
                    end_reason = "quit"
                    break
                if key == "s":
                    suspend: SuspendEvent = {
                        "format_version": EVENT_FORMAT_VERSION,
                        "id": new_event_id(secrets.token_bytes),
                        "at": format_canonical_time(datetime.now(UTC)),
                        "device": device_id,
                        "kind": "suspend",
                        "item": item["id"],
                    }
                    write_events([suspend])
                    last_correctable_event = suspend
                    print("Suspended.")
                    continue
                # PLAN.md D35: `e` records the attempt ungraded, an automatic
                # grade too: `e` says the item is wrong, so a grade against
                # its key is suspect; the typed answer is kept for review.
                rating: int | None = automatic_rating
                if key == "y":
                    rating = GOOD
                elif key == "n":
                    rating = AGAIN
                elif key == "?" or key == "e":
                    rating = None
                attempt: AttemptEvent = {
                    "format_version": EVENT_FORMAT_VERSION,
                    "id": new_event_id(secrets.token_bytes),
                    "at": format_canonical_time(committed_at),
                    "device": device_id,
                    "kind": "attempt",
                    "session": session_start["id"],
                    "item": item["id"],
                    "rating": rating,
                    "latency_milliseconds": latency_milliseconds,
                    # PLAN.md D20 constraint 1: the text as typed.
                    "typed_answer": typed_answer,
                    "fingerprint": item_fingerprint(item),
                    "day": scheduling_day(committed_at, preset["day_start_hour"]),
                }
                write_events([attempt])
                attempt_count += 1
                last_correctable_event = attempt
                if key == "e":
                    editor_command = shlex.split(os.environ.get("EDITOR", "")) or ["vi"]
                    subprocess.run([*editor_command, f"+{item['line']}", located_item["path"]], check=False)
                    print("Edited; the item returns next session.")
        except (KeyboardInterrupt, EOFError):
            end_reason = "interrupted"
            print()
        finally:
            termios.tcsetattr(terminal_descriptor, termios.TCSADRAIN, cooked_attributes)
            if session_was_started:
                session_end: SessionEndEvent = {
                    "format_version": EVENT_FORMAT_VERSION,
                    "id": new_event_id(secrets.token_bytes),
                    "at": format_canonical_time(datetime.now(UTC)),
                    "device": device_id,
                    "kind": "session_end",
                    "session": session_start["id"],
                    "reason": end_reason,
                }
                write_events([session_end])
        print(f"{attempt_count} attempts; session {end_reason}.")
        return 0

    if command == "stamp":
        # PLAN.md D24. Bytes, not text: text-mode stdin decodes by the locale, and under
        # the C locale with surrogateescape (measured), so invalid UTF-8
        # would be stamped instead of refused; and a refusal must hand back
        # the exact bytes it was given (PLAN.md I9). On every refusal the
        # input goes back unchanged, so `rep stamp < file > copy` never
        # loses the file.
        input_bytes = sys.stdin.buffer.read()
        message_path: str = parsed_arguments.path
        try:
            input_text = input_bytes.decode("utf-8")
        except UnicodeDecodeError as utf8_error:
            sys.stdout.buffer.write(input_bytes)
            print(
                f"{message_path}: not UTF-8 ({utf8_error.reason} at byte {utf8_error.start}); nothing stamped",
                file=sys.stderr,
            )
            return 1
        data_root = machine_context["data_root"]
        if not machine_context["data_root_exists"]:
            sys.stdout.buffer.write(input_bytes)
            # PLAN.md D28: rep never creates the data root.
            print(f"rep: data root {data_root} does not exist; create it with: mkdir -p {data_root}", file=sys.stderr)
            return 2

        # I1 is library-wide, so new ids must avoid every id in every file.
        # Problems in other files are lint's to report; their ids still count.
        existing_item_ids: set[str] = set()
        library_read = read_library_files(data_root / "library")
        for file_problem in library_read["problems"]:
            print(f"rep: warning: {file_problem['path']}: {file_problem['message']}", file=sys.stderr)
        for library_file in library_read["files"]:
            for source_item in parse_library_text(library_file["text"]):
                id_field = source_item["fields"].get("id")
                if id_field is not None:
                    existing_item_ids.add(id_field["value"])

        stamp_result = stamp_library_text(input_text, existing_item_ids, secrets.token_bytes)
        if stamp_result["problems"] != []:
            sys.stdout.buffer.write(input_bytes)
            for problem in stamp_result["problems"]:
                print(
                    f"{message_path}:{problem['line']}:{problem['column']}: {problem['severity']}: {problem['message']}",
                    file=sys.stderr,
                )
            return 1

        # Only a stamp that adds ids writes history, so saving a file whose
        # items all have ids never touches the lock or the events file.
        if stamp_result["stamped_item_ids"] != []:
            # PLAN.md D24. Ids and their item_stamped events go out together or not at
            # all: ids without events would silently drop captures from E1.
            try:
                lock_descriptor = acquire_writer_lock(machine_context["state_directory"])
            except WriterLockBusy as lock_busy:
                sys.stdout.buffer.write(input_bytes)
                print(f"rep: {lock_busy}; nothing stamped, save again to retry", file=sys.stderr)
                return 2
            try:
                stamped_events = new_item_stamped_events(
                    stamp_result["stamped_item_ids"], machine_context["device_id"], datetime.now(UTC), secrets.token_bytes
                )
                append_events(data_root / "events", machine_context["device_id"], stamped_events)
            finally:
                os.close(lock_descriptor)

        sys.stdout.buffer.write(stamp_result["text"].encode("utf-8"))
        return 0

    if command == "add":
        input_bytes = sys.stdin.buffer.read()
        try:
            input_text = input_bytes.decode("utf-8")
        except UnicodeDecodeError as utf8_error:
            print(f"<stdin>: not UTF-8 ({utf8_error.reason} at byte {utf8_error.start}); nothing added", file=sys.stderr)
            return 1
        data_root = machine_context["data_root"]
        if not machine_context["data_root_exists"]:
            # PLAN.md D28: rep never creates the data root.
            print(f"rep: data root {data_root} does not exist; create it with: mkdir -p {data_root}", file=sys.stderr)
            return 2
        target_name_argument: str | None = parsed_arguments.to

        # PLAN.md D27, D29. The lock is held from the library read to the last write: the ids
        # drawn, the file appended to and the events recorded then all see
        # one state of the library, with no other writer between them.
        try:
            lock_descriptor = acquire_writer_lock(machine_context["state_directory"])
        except WriterLockBusy as lock_busy:
            print(f"rep: {lock_busy}; nothing added", file=sys.stderr)
            return 2
        try:
            library_directory = data_root / "library"
            library_read = read_library_files(library_directory)
            for file_problem in library_read["problems"]:
                print(f"rep: warning: {file_problem['path']}: {file_problem['message']}", file=sys.stderr)
            existing_item_ids: set[str] = set()
            for library_file in library_read["files"]:
                for source_item in parse_library_text(library_file["text"]):
                    id_field = source_item["fields"].get("id")
                    if id_field is not None:
                        existing_item_ids.add(id_field["value"])

            # --- stamp, then check every item as it will be written (D14) ---
            stamp_result = stamp_library_text(input_text, existing_item_ids, secrets.token_bytes)
            refusals: list[str] = [
                f"<stdin>:{problem['line']}:{problem['column']}: {problem['severity']}: {problem['message']}"
                for problem in stamp_result["problems"]
            ]
            added_items: list[Item] = []
            if refusals == []:
                for source_item in parse_library_text(stamp_result["text"]):
                    checked_item, item_problems = check_source_item(source_item)
                    for problem in item_problems:
                        if problem["severity"] == "error":
                            refusals.append(
                                f"<stdin>:{problem['line']}:{problem['column']}: error: {problem['message']}"
                            )
                    if checked_item is None:
                        continue
                    # I1: an id the person wrote into the input must be new
                    # to the library, and must be one rep can have written.
                    if checked_item["id"] in existing_item_ids and checked_item["id"] not in stamp_result["stamped_item_ids"]:
                        refusals.append(
                            f"<stdin>:{checked_item['line']}:1: error: id {checked_item['id']} is already in the library"
                        )
                    elif checked_item["id"] in {added_item["id"] for added_item in added_items}:
                        refusals.append(
                            f"<stdin>:{checked_item['line']}:1: error: id {checked_item['id']} appears twice in the input"
                        )
                    elif ITEM_ID_PATTERN.match(checked_item["id"]) is None:
                        refusals.append(
                            f"<stdin>:{checked_item['line']}:1: error: id {checked_item['id']} is not in the form "
                            "rep writes; remove the 'id:' line and rep will write one"
                        )
                    added_items.append(checked_item)
                if refusals == [] and added_items == []:
                    refusals.append("<stdin>: no '### Q:' item to add")

            # --- which file: --to, else the one citekey all items share (PLAN.md D29) ---
            target_name = ""
            if refusals == []:
                if target_name_argument is not None:
                    target_name = target_name_argument
                    if not target_name.endswith(LIBRARY_FILE_SUFFIX):
                        target_name += LIBRARY_FILE_SUFFIX
                else:
                    item_citekeys = {added_item["citekey"] for added_item in added_items}
                    if len(item_citekeys) != 1 or None in item_citekeys:
                        refusals.append(
                            "rep add: the items do not share one source citekey "
                            f"({', '.join(sorted(str(citekey) for citekey in item_citekeys))}); "
                            "name the file with --to"
                        )
                    else:
                        target_name = f"{item_citekeys.pop()}{LIBRARY_FILE_SUFFIX}"
                # A citekey may hold "/" (BibTeX allows it), which would name a
                # path outside the library; a leading "." would hide the file.
                if refusals == [] and ("/" in target_name or target_name.startswith(".")):
                    refusals.append(
                        f"rep add: '{target_name}' cannot be a library file name (no '/', no leading '.'); "
                        "name the file with --to"
                    )

            # --- the exact text to append, verified to change no meaning ---
            text_to_append = ""
            if refusals == []:
                existing_text: str | None = None
                for library_file in library_read["files"]:
                    if library_file["name"] == target_name:
                        existing_text = library_file["text"]
                if existing_text is None and (library_directory / target_name).exists():
                    refusals.append(f"rep add: {library_directory / target_name} could not be read; nothing added")
                else:
                    text_to_append, append_problems = plan_library_append(
                        existing_text, stamp_result["text"], target_name
                    )
                    refusals.extend(f"rep add: {problem}" for problem in append_problems)

            if refusals != []:
                for refusal in refusals:
                    print(refusal, file=sys.stderr)
                return 1

            # The person's text goes first: if rep stops between the two
            # writes, an item without its capture event costs one E1 count,
            # while an event without its item would be history for nothing.
            append_library_text(library_directory, target_name, text_to_append)
            stamped_events = new_item_stamped_events(
                stamp_result["stamped_item_ids"], machine_context["device_id"], datetime.now(UTC), secrets.token_bytes
            )
            append_events(data_root / "events", machine_context["device_id"], stamped_events)
        finally:
            os.close(lock_descriptor)

        print(f"added {len(added_items)} to library/{target_name}: {', '.join(item['id'] for item in added_items)}")
        return 0

    if command == "lint":
        # PLAN.md D30. Read-only: no lock, so lint can run while a session writes. It may
        # then see a last events line still being written, which the loader
        # reports and skips (storage.py S2).
        data_root = machine_context["data_root"]
        if not machine_context["data_root_exists"]:
            # PLAN.md D28: rep never creates the data root.
            print(f"rep: data root {data_root} does not exist; create it with: mkdir -p {data_root}", file=sys.stderr)
            return 2
        # (path, line, column, severity, message); severity is error,
        # warning, or note (an open question: listed, never a problem).
        lint_lines: list[tuple[str, int, int, str, str]] = []

        library_read = read_library_files(data_root / "library")
        for file_problem in library_read["problems"]:
            lint_lines.append((file_problem["path"], 1, 1, file_problem["severity"], file_problem["message"]))

        # --- every item, and ids across the library: the same check a
        # session applies, so both leave out the same items (library.py L11) ---
        library_check = check_library_files(
            [(library_file["path"], library_file["text"]) for library_file in library_read["files"]]
        )
        for located_problem in library_check["problems"]:
            lint_lines.append(
                (located_problem["path"], located_problem["line"], located_problem["column"],
                 located_problem["severity"], located_problem["message"])
            )  # fmt: skip
        library_item_ids = library_check["written_item_ids"]
        item_count = library_check["item_count"]
        # path, line, citekey, unverified
        cited_items: list[tuple[str, int, str, bool]] = [
            (located_item["path"], located_item["item"]["line"], located_item["item"]["citekey"], located_item["item"]["citekey_is_unverified"])
            for located_item in library_check["located_items"]
            if located_item["item"]["citekey"] is not None
        ]

        # --- citekeys against the bib (PLAN.md D16: kbd is read, never written) ---
        bib_path = machine_context["bib_path"]
        # PLAN.md D25. "@llm:<id>" sources are an open hole (section 9): their
        # meaning is undecided, so they are exempt rather than reported.
        verifiable_cited_items = [cited_item for cited_item in cited_items if cited_item[2] != "llm"]
        if verifiable_cited_items != []:
            if bib_path is None:
                print(
                    "rep: warning: bib_path is not set in local.toml; citekeys were not checked",
                    file=sys.stderr,
                )
            elif not bib_path.is_file():
                print(f"rep: warning: bib {bib_path} not found; citekeys were not checked", file=sys.stderr)
            else:
                bib_citekeys = read_bib_citekeys(bib_path)
                for cited_path, cited_line, citekey, citekey_is_unverified in verifiable_cited_items:
                    if not citekey_is_unverified and citekey not in bib_citekeys:
                        lint_lines.append(
                            (
                                cited_path,
                                cited_line,
                                1,
                                "warning",
                                f"citekey {citekey} is not in the bib; fix it, or mark it unverified as @{citekey}??",
                            )
                        )
                    elif citekey_is_unverified and citekey in bib_citekeys:
                        lint_lines.append(
                            (cited_path, cited_line, 1, "warning", f"citekey {citekey} is in the bib now; drop the '??'")
                        )

        # --- events: unreadable lines, and history with no item (I2) ---
        events_load = load_events(data_root / "events")
        for file_problem in events_load["problems"]:
            # Line 0 means the whole file; quickfix wants a real line.
            lint_lines.append(
                (file_problem["path"], max(file_problem["line"], 1), 1, file_problem["severity"], file_problem["message"])
            )
        fold_result = fold_events(events_load["events"])
        for fold_problem in fold_result["problems"]:
            print(f"rep: warning: events: {fold_problem}", file=sys.stderr)
        last_location_by_item: dict[str, tuple[str, int]] = {}
        for event, event_location in zip(events_load["events"], events_load["event_locations"], strict=True):
            if (
                event["kind"] == "attempt"
                or event["kind"] == "suspend"
                or event["kind"] == "unsuspend"
                or event["kind"] == "item_stamped"
            ):
                last_location_by_item[event["item"]] = (event_location["path"], event_location["line"])
        for orphan_item_id in sorted(set(fold_result["items"]) - library_item_ids):
            orphan_path, orphan_line = last_location_by_item[orphan_item_id]
            lint_lines.append(
                (
                    orphan_path,
                    orphan_line,
                    1,
                    "warning",
                    f"item {orphan_item_id} has review history but is in no library file "
                    "(deleted on purpose, or its id line was changed; I2)",
                )
            )

        for lint_path, lint_line, lint_column, severity, message in sorted(lint_lines):
            print(f"{lint_path}:{lint_line}:{lint_column}: {severity}: {message}")
        error_count = sum(1 for lint_line in lint_lines if lint_line[3] == "error")
        warning_count = sum(1 for lint_line in lint_lines if lint_line[3] == "warning")
        note_count = sum(1 for lint_line in lint_lines if lint_line[3] == "note")
        print(
            f"rep lint: {error_count} errors, {warning_count} warnings, {note_count} open questions; "
            f"{item_count} items in {len(library_read['files'])} files, {len(events_load['events'])} events",
            file=sys.stderr,
        )
        return 1 if error_count > 0 else 0

    raise AssertionError(f"command {command!r} is registered but not handled")
