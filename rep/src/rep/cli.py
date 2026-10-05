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

SESSION AND REVIEW
  Plain `rep` (no command) runs today's session in rounds: session.py
  decides what to show; this branch shows each question, reads one typed
  answer, writes it as an attempt, and at the end of each round opens the
  round's grading sheet in $EDITOR (PLAN.md D45). `rep review` opens the
  same sheet for answers still ungraded (D41). The two share the only
  functions outside main: append_events_waiting and grade_on_a_sheet.
  Each append holds the writer lock for that append only (D32).

INVARIANTS
  Output meant for the person goes to stdout; warnings and errors go to
  stderr, so `rep ... > file` captures only results.
"""

import argparse
import codecs
import traceback
from collections import Counter
import hashlib
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
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from rep.events import (
    EVENT_FORMAT_VERSION,
    AmendEvent,
    AttemptEvent,
    Event,
    SessionEndEvent,
    SessionStartEvent,
    SuspendEvent,
    UnsuspendEvent,
    effective_events,
    fold_events,
    format_canonical_time,
    new_event_id,
    new_item_stamped_events,
    parse_canonical_time,
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
from rep import run_log
from rep.machine import MachineContextError, resolve_machine_context
from rep.memory_model import AGAIN, DEFAULT_PARAMETERS, GOOD, retrievability
from rep.session import (
    DEFAULT_PRESET,
    GRADE_WORDS,
    PlanSlot,
    SessionPlan,
    SheetEntry,
    grading_sheet_entries,
    plan_session,
    read_grading_sheet,
    render_grading_sheet,
    review_attempt_ids,
    session_rounds,
)
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


def append_events_waiting(state_directory: Path, events_directory: Path, device_id: str, new_events: list[Event]) -> None:
    """Append under the writer lock, held for this append only, waiting for
    it rather than refusing (PLAN.md D32): what is being written is the
    person's answers or grades, which a refusal would throw away.

    PRE   events_directory's parent, the data root, exists.
    POST  the events are on disk; or KeyboardInterrupt, with nothing written.
    """
    lock_wait_started_at = time.monotonic()
    person_was_told = False
    while True:
        try:
            lock_descriptor = acquire_writer_lock(state_directory)
            break
        except WriterLockBusy as lock_busy:
            if not person_was_told and time.monotonic() - lock_wait_started_at > 2.0:
                print(f"rep: {lock_busy}; waiting (Ctrl-C stops)", file=sys.stderr)
                person_was_told = True
            time.sleep(0.05)
    try:
        append_events(events_directory, device_id, new_events)
    finally:
        os.close(lock_descriptor)


SHEET_PROBLEM_PREFIX = "# problem: "
# PLAN.md D59: screen limits, named so they are found and changed in one
# place. A drill over DRILL_SIZE_WARNING items says so before Enter (the
# person's 251-item drill: 30 to 50 was their limit); SECONDS_PER_ANSWER is
# the estimate for its length; DECKS_LISTED names at most that many decks.
DRILL_SIZE_WARNING = 50
SECONDS_PER_ANSWER = 10
DECKS_LISTED = 3


def grade_on_a_sheet(entries: list[SheetEntry], title: str, sheet_path: Path, device_id: str) -> list[Event]:
    """Open the grading sheet in $EDITOR until it reads cleanly (PLAN.md D41, D45).

    PRE   entries is not empty; sheet_path is in the machine-local state
          directory, which exists.
    POST  the sheet file is gone. Returns the amends and suspends the sheet
          asks for, to be written by the caller; none when the editor exits
          non-zero (the person's way to apply nothing) or cannot be run.
          Either way, answers left ungraded wait for `rep review`.
    """
    sheet_path.write_text(render_grading_sheet(entries, title), encoding="utf-8")
    editor_command = shlex.split(os.environ.get("EDITOR", "")) or ["vi"]
    try:
        while True:
            try:
                editor_exit_code = subprocess.run([*editor_command, str(sheet_path)], check=False).returncode
            except OSError as editor_error:
                print(f"rep: cannot run the editor {editor_command[0]!r}: {editor_error.strerror}", file=sys.stderr)
                print("No grade applied; ungraded answers wait for `rep review`.")
                return []
            if editor_exit_code != 0:
                print("The editor exited with an error: no grade applied; ungraded answers wait for `rep review`.")
                return []
            # The read words are ASCII; a stray invalid byte elsewhere must
            # not lose the sheet.
            sheet_text = sheet_path.read_text(encoding="utf-8", errors="replace")
            sheet_result = read_grading_sheet(sheet_text, entries)
            if sheet_result["problems"] == []:
                break
            # Each problem goes right above its line, and the last pass's
            # problems are dropped, so the person sees them where they are;
            # their own edits stay. The sheet is rep's file, not the
            # person's library, so rewriting it does not break I3.
            problem_messages_by_line: dict[int, list[str]] = {}
            for problem_line_number, problem_message in sheet_result["problems"]:
                problem_messages_by_line.setdefault(problem_line_number, []).append(problem_message)
            rewritten_lines: list[str] = []
            for line_index, sheet_line in enumerate(sheet_text.split("\n")):
                if sheet_line.startswith(SHEET_PROBLEM_PREFIX):
                    continue
                rewritten_lines.extend(
                    SHEET_PROBLEM_PREFIX + problem_message for problem_message in problem_messages_by_line.get(line_index + 1, [])
                )
                rewritten_lines.append(sheet_line)
            sheet_path.write_text("\n".join(rewritten_lines), encoding="utf-8")
    finally:
        sheet_path.unlink(missing_ok=True)
    graded_at = format_canonical_time(datetime.now(UTC))
    sheet_events: list[Event] = []
    for attempt_id, new_rating in sheet_result["amends"]:
        amend: AmendEvent = {
            "format_version": EVENT_FORMAT_VERSION,
            "id": new_event_id(secrets.token_bytes),
            "at": graded_at,
            "device": device_id,
            "kind": "amend",
            "target": attempt_id,
            "rating": new_rating,
        }
        sheet_events.append(amend)
    for suspended_item_id in sheet_result["suspended_item_ids"]:
        suspend: SuspendEvent = {
            "format_version": EVENT_FORMAT_VERSION,
            "id": new_event_id(secrets.token_bytes),
            "at": graded_at,
            "device": device_id,
            "kind": "suspend",
            "item": suspended_item_id,
        }
        sheet_events.append(suspend)
    return sheet_events


def main(argument_list: list[str] | None = None) -> int:
    """Entry point for the `rep` console script: runs the command and logs
    the run (PLAN.md D55), however it ends.

    PRE   argument_list is None (use sys.argv) or the arguments after "rep".
    POST  returns an exit code from the table in the module docstring; one
          line in the run log, once the state directory is known.
    """
    arguments = sys.argv[1:] if argument_list is None else argument_list
    run_record = run_log.start_run("rep", arguments)
    # PLAN.md D49, D55: exactly which code ran, with no version number
    # anyone must remember to bump (1 ms, measured).
    source_digest = hashlib.sha256()
    for source_path in sorted(Path(__file__).parent.glob("*.py")):
        source_digest.update(source_path.name.encode() + b"\0" + source_path.read_bytes())
    run_record["source"] = source_digest.hexdigest()[:12]
    exit_code: int | None = None
    error_text: str | None = None
    try:
        exit_code = run_command(arguments, run_record)
        return exit_code
    except SystemExit as system_exit:
        # argparse ends --help and bad arguments this way.
        exit_code = system_exit.code if isinstance(system_exit.code, int) else (0 if system_exit.code is None else 2)
        raise
    except BaseException:
        error_text = traceback.format_exc()
        raise
    finally:
        run_log.finish_run(run_record, run_record.get("_log_path"), exit_code, error_text)


def run_command(argument_list: list[str], run_record: dict[str, Any]) -> int:
    """One command, from its arguments to its exit code (main logs it).

    PRE   argument_list holds the arguments after "rep"; run_record came
          from run_log.start_run.
    POST  returns an exit code from the table in the module docstring;
          run_record holds the command, its phases and counts.
    """
    # PLAN.md D58: the help is where a first-time person starts, so it says
    # the daily loop, in the loop's order, with an example per command.
    argument_parser = argparse.ArgumentParser(
        prog="rep",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        description="Retrieval practice: you answer from memory, grade yourself against the key,\n"
        "and rep schedules each item to come back just before you would forget it.",
        epilog="the daily loop:\n"
        "  rep                  today's session (same as `rep today`): answer, then grade in your editor\n"
        "  rep drill permit     practise a deck now, as often as you like (--count 10, --tag jol)\n"
        "  rep review           grade answers left without a grade; regrade your last session\n"
        "  rep status           what is due by deck, what waits, which data root\n"
        "first time:\n"
        "  write items in a file, a question and its answer each:\n"
        "      ### Q: What is the capital of Peru?\n"
        "      A: Lima\n"
        "  then: rep add --stdin --to capitals < capitals.md   (CONVENTIONS.md has the rest)",
    )
    # PLAN.md D42: a flag, not action="version", which needs the version
    # string, and so importlib.metadata, while the parser is built: 39 of 57
    # ms of import on every command, and nvim runs `rep stamp` on every save.
    argument_parser.add_argument("--version", action="store_true", help="show program's version number and exit")
    argument_parser.add_argument(
        "--data-root",
        metavar="PATH",
        help="data folder for this run (default: $REP_DATA_ROOT, else ~/learning)",
    )
    subcommand_parsers = argument_parser.add_subparsers(dest="command", metavar="COMMAND")
    subcommand_parsers.add_parser("today", help="today's session: what is due, then new items (plain `rep` does the same)")
    drill_parser = subcommand_parsers.add_parser(
        "drill", help="practise items you choose, as often as you like: a deck (a library file), a tag, or both"
    )
    drill_parser.add_argument("deck", nargs="?", metavar="DECK", help="a library file's name, without .md (default: every deck)")
    drill_parser.add_argument("--tag", metavar="TAG", help="only items with this tag (with or without #)")
    drill_parser.add_argument("--count", type=int, metavar="N", help="at most N of them, drawn at random")
    subcommand_parsers.add_parser(
        "review", help="grade, in $EDITOR, answers left without a grade, and your last session's answers again"
    )
    subcommand_parsers.add_parser(
        "status", help="which data root, each deck's items, new and due, answers waiting for review, today so far"
    )
    add_parser = subcommand_parsers.add_parser(
        "add",
        help="add items from a file to a deck: rep add --stdin --to DECK < file.md",
        description="Add items to a deck (a library file), with ids. The items are read from standard\n"
        "input, so a file, a pipe and nvim's capture all work the same way.",
        epilog="example: rep add --stdin --to capitals < capitals.md",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    add_parser.add_argument("--stdin", action="store_true", help="read the items from standard input (needed; see the example)")
    add_parser.add_argument(
        "--to",
        metavar="DECK",
        help="the deck (library file) to add to (default: <citekey>.md from the items' source)",
    )
    item_help = "an item's id (the `id:` line under its question), or words from its question"
    why_parser = subcommand_parsers.add_parser(
        "why", help="show an item's place, memory state, attempts and whether today's plan has it",
        epilog='example: rep why "capital of Palau"',
    )  # fmt: skip
    why_parser.add_argument("item_id", metavar="ITEM", help=item_help)
    unsuspend_parser = subcommand_parsers.add_parser(
        "unsuspend", help="return a suspended item to sessions", epilog='example: rep unsuspend "capital of Palau"'
    )
    unsuspend_parser.add_argument("item_id", metavar="ITEM", help=item_help)
    where_parser = subcommand_parsers.add_parser(
        "where", help="where rep keeps its files, its helpers, and this device's id"
    )
    # PLAN.md D43: the nvim plugin asks for the data root this way. Its own
    # dest: the default, data_root, is the global --data-root PATH, which a
    # subcommand's value would overwrite in the shared namespace.
    where_parser.add_argument(
        "--data-root", dest="print_data_root_only", action="store_true", help="print only the data root's path"
    )
    subcommand_parsers.add_parser(
        "lint",
        help="check the whole library and the events; print problems as path:line:col for quickfix",
    )
    stamp_parser = subcommand_parsers.add_parser(
        "stamp",
        help="give ids to the items of a library file: rep stamp < file.md > stamped.md (nvim does it on save)",
    )
    # stdin has no name; nvim passes the buffer's, so problems land in quickfix
    # on the right file.
    stamp_parser.add_argument("--path", metavar="PATH", default="<stdin>", help="file name to use in problem messages")

    parsed_arguments = argument_parser.parse_args(argument_list)
    run_record["command"] = "session" if parsed_arguments.command in (None, "today") else parsed_arguments.command
    version_requested: bool = parsed_arguments.version
    if version_requested:
        # Before the machine context, as action="version" was: the version
        # prints even where rep cannot run.
        import importlib.metadata

        print(f"rep {importlib.metadata.version('rep')}")
        return 0
    # `rep today` is plain `rep` by name (D58): the person reached for it.
    command: str | None = None if parsed_arguments.command == "today" else parsed_arguments.command
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
    # PLAN.md D55: machine-local, beside the writer lock; never synced.
    run_record["_log_path"] = machine_context["state_directory"] / "runs.jsonl"
    for warning in machine_context["warnings"]:
        print(f"rep: warning: {warning}", file=sys.stderr)

    if command == "where":
        print_data_root_only: bool = parsed_arguments.print_data_root_only
        if print_data_root_only:
            # Printed whether or not it exists: the caller only matches
            # paths against it.
            print(machine_context["data_root"])
            return 0
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
        print(f"run_log          {machine_context['state_directory'] / 'runs.jsonl'}  (each run's timings; machine-local)")
        # PLAN.md D60: what each thing under the data root is for, and who
        # writes it, so the folder explains itself (the person could not
        # tell ~/learning was rep's, nor what each part held).
        data_root = machine_context["data_root"]
        print("in the data root:")
        for entry_name, purpose in (
            ("library/", "decks: one .md file per deck; yours to edit (rep add appends, nvim stamps ids)"),
            ("events/", "the history: one .jsonl per device; rep appends, never edit by hand"),
            ("body/", "the body form, one file a day (body)"),
            ("notes.md", "the week's notes (rep-notes)"),
            ("reports/", "week reports and code tours (rep-week, rep-tour)"),
            ("screens/", "saved terminal screens (rep-screen); may hold anything on screen, keep private"),
        ):
            entry_path = data_root / entry_name
            if not entry_path.exists():
                presence = "not yet"
            elif entry_path.is_dir():
                presence = f"{sum(1 for _ in entry_path.iterdir())} files"
            else:
                presence = "exists"
            print(f"  {entry_name:<15}{presence:<10}{purpose}")
        # The checkout this code runs from, found from this file: an
        # editable install keeps it there, and the helpers live beside it.
        repository = Path(__file__).resolve().parents[2]
        if (repository / "shell" / "rep.sh").exists():
            print(f"repository       {repository}  (this code)")
            # Whole paths, to copy into a bashrc or an nvim config as they are.
            print(f"  source {repository / 'shell' / 'rep.sh'}    rep-notes, rep-screen, rep-nvim, rep-week, rep-tour")
            print(f"  source {repository / 'shell' / 'body.sh'}   body")
            print(f"  nvim --cmd 'luafile {repository / 'nvim' / 'load.lua'}'   rep's nvim plugin (or rep-nvim)")
            print(f"  {repository / 'templates'}/   the body form and notes templates the helpers copy")
        else:
            print(f"repository       not found beside {Path(__file__).resolve()}  (installed without its checkout)")
        return 0

    if command is None or command in ("review", "why", "unsuspend", "drill", "status"):
        data_root = machine_context["data_root"]
        if not machine_context["data_root_exists"]:
            # PLAN.md D28: rep never creates the data root. D53: say which
            # rule chose it, since a forgotten REP_DATA_ROOT looks like data loss.
            print(
                f"rep: data root {data_root} ({machine_context['data_root_source']}) does not exist; "
                f"create it with: mkdir -p {data_root}, or choose another with REP_DATA_ROOT=... or --data-root",
                file=sys.stderr,
            )
            return 2
        # The session reads answers from the terminal; both run $EDITOR on it.
        if (command is None or command == "review") and (not sys.stdin.isatty() or not sys.stdout.isatty()):
            print(f"rep: {'a session' if command is None else 'review'} needs a terminal on standard input and output", file=sys.stderr)
            return 2
        preset = DEFAULT_PRESET
        device_id = machine_context["device_id"]
        state_directory = machine_context["state_directory"]
        with run_log.phase(run_record, "read_library"):
            library_read = read_library_files(data_root / "library")
            library_check = check_library_files(
                [(library_file["path"], library_file["text"]) for library_file in library_read["files"]]
            )
        located_items_by_id: dict[str, LocatedItem] = {
            located_item["item"]["id"]: located_item for located_item in library_check["located_items"]
        }
        with run_log.phase(run_record, "load_events"):
            events_load = load_events(data_root / "events")
        run_record["counts"].update({"library_items": library_check["item_count"], "events": len(events_load["events"])})
        excluded_item_count = library_check["item_count"] - len(library_check["located_items"])
        if excluded_item_count > 0:
            print(f"rep: {excluded_item_count} items are left out by errors; `rep lint` lists them", file=sys.stderr)

        if command == "status":
            # PLAN.md D53: the state of everything in one screen, read-only.
            fold_result = fold_events(events_load["events"], desired_retention=preset["desired_retention"])
            now = datetime.now(UTC)
            today = scheduling_day(now, preset["day_start_hour"])
            print(f"data root   {data_root}  ({machine_context['data_root_source']})")
            # PLAN.md D60: the clock and what is left of the day, since the
            # day's end (04:00) is not midnight and "today" alone hid both.
            local_now = now.astimezone()
            day_end = datetime.combine(date.fromisoformat(today) + timedelta(days=1), datetime.min.time(), local_now.tzinfo).replace(
                hour=preset["day_start_hour"]
            )
            minutes_left = max(int((day_end - local_now).total_seconds()) // 60, 0)
            print(
                f"today       {today}, now {local_now:%H:%M}, {minutes_left // 60} h {minutes_left % 60:02d} min left"
                f"  (a day runs {preset['day_start_hour']:02d}:00 to {preset['day_start_hour']:02d}:00)"
            )
            # deck -> [items, new, due now, suspended, earliest future due day]
            deck_rows: dict[str, list[int | str]] = {}
            for located_item in library_check["located_items"]:
                deck_name = Path(located_item["path"]).name.removesuffix(LIBRARY_FILE_SUFFIX)
                deck_row = deck_rows.setdefault(deck_name, [0, 0, 0, 0, ""])
                deck_row[0] = int(deck_row[0]) + 1
                item_state = fold_result["items"].get(located_item["item"]["id"])
                if item_state is not None and item_state["suspended"]:
                    deck_row[3] = int(deck_row[3]) + 1
                elif item_state is None or item_state["memory"] is None:
                    deck_row[1] = int(deck_row[1]) + 1
                elif item_state["due_day"] is not None and item_state["due_day"] <= today:
                    deck_row[2] = int(deck_row[2]) + 1
                elif item_state["due_day"] is not None and (deck_row[4] == "" or item_state["due_day"] < str(deck_row[4])):
                    deck_row[4] = item_state["due_day"]
            print(f"decks       {'deck':<16}{'items':>6}{'new':>6}{'due now':>9}{'suspended':>11}  next due")
            for deck_name, deck_row in sorted(deck_rows.items()):
                print(f"            {deck_name:<16}{deck_row[0]:>6}{deck_row[1]:>6}{deck_row[2]:>9}{deck_row[3]:>11}  {deck_row[4] or '-'}")
            if deck_rows == {}:
                print("            none yet: rep add --stdin --to NAME < file.md")
            effective = effective_events(events_load["events"])
            waiting_count = sum(
                1 for event in effective["ordered_events"]
                if event["kind"] == "attempt" and event["id"] not in effective["undone_event_ids"]
                and effective["amended_ratings"].get(event["id"], event["rating"]) is None
            )  # fmt: skip
            print(f"waiting     {waiting_count} answers without a grade" + (": rep review" if waiting_count > 0 else ""))
            sessions_today = 0
            drills_today = 0
            for event in effective["ordered_events"]:
                if event["kind"] == "session_start" and scheduling_day(parse_canonical_time(event["at"]), preset["day_start_hour"]) == today:
                    if "selection" in event:
                        drills_today += 1
                    else:
                        sessions_today += 1
            print(f"today did   {sessions_today} sessions, {drills_today} drills")
            # PLAN.md D60: what plain `rep` would do now, from the planner
            # itself, and the day's new-item allowance it draws on.
            session_plan = plan_session(library_check["located_items"], fold_result["items"], events_load["events"], today, preset)
            completed_session_ids = {
                event["session"] for event in effective["ordered_events"]
                if event["kind"] == "session_end" and event["reason"] == "completed"
            }  # fmt: skip
            session_done_today = any(
                event["kind"] == "session_start" and "selection" not in event and event["id"] in completed_session_ids
                and scheduling_day(parse_canonical_time(event["at"]), preset["day_start_hour"]) == today
                for event in effective["ordered_events"]
            )  # fmt: skip
            planned_due = sum(1 for slot in session_plan["slots"] if slot["reason"] == "due")
            planned_new = len(session_plan["slots"]) - planned_due
            if session_plan["slots"] != []:
                session_text = f"{planned_due} due and {planned_new} new waiting: rep"
                if session_done_today:
                    session_text = "done once; " + session_text
            else:
                session_text = "done" if session_done_today else "nothing planned"
            print(f"session     {session_text}")
            print(
                f"new items   up to {preset['new_per_day']} a day: {session_plan['introduced_today']} started today "
                f"(drills count), {session_plan['new_left_today']} left; {session_plan['new_waiting'] + planned_new} not yet seen"
            )
            return 0

        if command == "why" or command == "unsuspend":
            requested_item_id: str = parsed_arguments.item_id
            fold_result = fold_events(events_load["events"], desired_retention=preset["desired_retention"])
            # PLAN.md D58: words from the question find the item, so no id
            # has to be looked up first.
            if requested_item_id not in library_check["written_item_ids"] and requested_item_id not in fold_result["items"]:
                search_text = " ".join(requested_item_id.split()).casefold()
                question_matches = [
                    located_item for located_item in library_check["located_items"]
                    if search_text in " ".join(located_item["item"]["question"].split()).casefold()
                ]  # fmt: skip
                if len(question_matches) == 1:
                    requested_item_id = question_matches[0]["item"]["id"]
                elif len(question_matches) > 1:
                    print(f"rep: {len(question_matches)} items match {requested_item_id!r}; add words, or use an id:", file=sys.stderr)
                    for located_item in question_matches[:10]:
                        print(f"  {located_item['item']['id']:<34} {' / '.join(located_item['item']['question'].splitlines())}", file=sys.stderr)
                    if len(question_matches) > 10:
                        print(f"  and {len(question_matches) - 10} more", file=sys.stderr)
                    return 2
            item_state = fold_result["items"].get(requested_item_id)
            located_item = located_items_by_id.get(requested_item_id)
            if item_state is None and requested_item_id not in library_check["written_item_ids"]:
                print(f"rep: no item {requested_item_id} in the library or its history; give its id, or words from its question", file=sys.stderr)
                return 2

            if command == "unsuspend":
                # PLAN.md D42. Nothing is written for an item that is not
                # suspended: the event would change nothing.
                if item_state is None or not item_state["suspended"]:
                    print(f"Item {requested_item_id} is not suspended; nothing written.")
                    return 0
                unsuspend: UnsuspendEvent = {
                    "format_version": EVENT_FORMAT_VERSION,
                    "id": new_event_id(secrets.token_bytes),
                    "at": format_canonical_time(datetime.now(UTC)),
                    "device": device_id,
                    "kind": "unsuspend",
                    "item": requested_item_id,
                }
                append_events_waiting(state_directory, data_root / "events", device_id, [unsuspend])
                print(f"Item {requested_item_id} is back in sessions.")
                return 0

            # --- rep why (PLAN.md D42): facts only, so the reasons stay the
            # plan's; a second copy of its rules here could disagree ---
            today = scheduling_day(datetime.now(UTC), preset["day_start_hour"])
            print(f"item        {requested_item_id}")
            if located_item is not None:
                print(f"question    {' / '.join(located_item['item']['question'].splitlines())}")
                print(f"where       {located_item['path']}:{located_item['item']['line']}")
            elif requested_item_id in library_check["written_item_ids"]:
                print("where       in the library, left out by errors (`rep lint` lists them)")
            else:
                print("where       in no library file: deleted, or its id line changed (I2)")
            if item_state is None or item_state["memory"] is None:
                print("memory      none yet: no graded review")
            else:
                last_review_day = item_state["last_review_day"]
                assert last_review_day is not None, "a memory state has a last review day"
                elapsed_days = max((date.fromisoformat(today) - date.fromisoformat(last_review_day)).days, 0)
                recall_now = retrievability(item_state["memory"]["stability"], elapsed_days, DEFAULT_PARAMETERS)
                print(f"stability   {item_state['memory']['stability']:.2f} days")
                print(f"difficulty  {item_state['memory']['difficulty']:.2f} (1 to 10)")
                print(f"recall now  {recall_now:.2f} (today {today}; last graded review {last_review_day})")
                print(f"due         {item_state['due_day']}")
            if item_state is not None:
                print(f"reviews     {item_state['graded_review_count']} graded, {item_state['lapse_count']} lapses")
                print(f"suspended   {'yes (rep unsuspend ' + requested_item_id + ')' if item_state['suspended'] else 'no'}")
            plan = plan_session(library_check["located_items"], fold_result["items"], events_load["events"], today, preset)["slots"]
            plan_reasons = [slot["reason"] for slot in plan if slot["item_id"] == requested_item_id]
            print(f"today       {'in the plan, ' + plan_reasons[0] if plan_reasons != [] else 'not in the plan'}")
            effective = effective_events(events_load["events"])
            grade_word_by_rating = {rating: word for word, rating in GRADE_WORDS.items() if rating is not None}
            item_attempts = [
                event for event in effective["ordered_events"]
                if event["kind"] == "attempt" and event["item"] == requested_item_id
                and event["id"] not in effective["undone_event_ids"]
            ]  # fmt: skip
            print(f"attempts    {len(item_attempts)}")
            current_fingerprint = item_fingerprint(located_item["item"]) if located_item is not None else None
            for attempt in item_attempts:
                attempt_rating = effective["amended_ratings"].get(attempt["id"], attempt["rating"])
                grade_word = "?" if attempt_rating is None else grade_word_by_rating[attempt_rating]
                typed_answer = attempt["typed_answer"] or ""
                # PLAN.md D33: stored on the attempt, so an edit since shows.
                changed_note = "  (item changed since)" if attempt["fingerprint"] != current_fingerprint else ""
                print(f"  {attempt['day']}  {grade_word:<6} {typed_answer}{changed_note}")
            return 0

        if command == "review":
            # PLAN.md D41: this device's last session, then every answer
            # still ungraded; the sheet is the whole interface.
            review_entries = grading_sheet_entries(
                events_load["events"], review_attempt_ids(events_load["events"], device_id), located_items_by_id
            )
            if review_entries == []:
                # PLAN.md D58: say why, and what to do instead.
                print(
                    "Nothing to review: no answer waits for a grade, and this device has no session yet.\n"
                    "Review shows your last session's answers to regrade, and any answer left without a grade.\n"
                    "Start with a session: rep (or rep drill DECK)."
                )
                return 0
            sheet_events = grade_on_a_sheet(
                review_entries,
                f"rep review: {len(review_entries)} answers",
                state_directory / f"review-{new_event_id(secrets.token_bytes)}.txt",
                device_id,
            )
            if sheet_events != []:
                append_events_waiting(state_directory, data_root / "events", device_id, sheet_events)
            amend_count = sum(1 for event in sheet_events if event["kind"] == "amend")
            print(f"{amend_count} grades written, {len(sheet_events) - amend_count} items suspended.")
            return 0

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
        # PLAN.md D47: vi-mode editing at the answer prompt, and Esc v opens
        # the answer in $EDITOR. libedit (uv's CPython) and GNU readline
        # spell it differently. libedit cannot keep the arrow keys in insert
        # mode as well: its Esc cannot be both the mode switch and the start
        # of a key sequence (measured), so the session shows the vi keys.
        readline.parse_and_bind("bind -v" if "libedit" in (readline.__doc__ or "") else "set editing-mode vi")
        with run_log.phase(run_record, "fold"):
            fold_result = fold_events(events_load["events"], desired_retention=preset["desired_retention"])
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
        # Drawn now, not at session_start: a drill's order and sample come from it (D50).
        session_id = new_event_id(secrets.token_bytes)
        drill_selection = ""
        drill_notes: list[str] = []
        session_plan: SessionPlan | None = None  # a session's plan facts; a drill has none
        if command == "drill":
            # PLAN.md D50: the person chooses the items; the schedule does
            # not. A deck is a library file (one file per item, so no item
            # is in two decks by mistake); a tag narrows it.
            deck_argument: str | None = parsed_arguments.deck
            tag_argument: str | None = parsed_arguments.tag
            count_argument: int | None = parsed_arguments.count
            if count_argument is not None and count_argument < 1:
                print("rep: --count must be 1 or more", file=sys.stderr)
                return 2
            deck_file_name = None if deck_argument is None else deck_argument.removesuffix(LIBRARY_FILE_SUFFIX) + LIBRARY_FILE_SUFFIX
            wanted_tag = None if tag_argument is None else "#" + tag_argument.lstrip("#")
            deck_counts = Counter(Path(located_item["path"]).name for located_item in library_check["located_items"])
            deck_items = [
                located_item for located_item in library_check["located_items"]
                if deck_file_name is None or Path(located_item["path"]).name == deck_file_name
            ]  # fmt: skip
            # Nothing to remember: a name that matches nothing lists what does.
            if deck_items == []:
                deck_list = ", ".join(f"{name.removesuffix(LIBRARY_FILE_SUFFIX)} ({count})" for name, count in sorted(deck_counts.items()))
                print(f"rep: no deck {deck_argument!r}; decks: {deck_list or 'none yet'}", file=sys.stderr)
                return 2
            deck_label = "every deck" if deck_file_name is None else deck_file_name.removesuffix(LIBRARY_FILE_SUFFIX)
            tagged_items = [located_item for located_item in deck_items if wanted_tag is None or wanted_tag in located_item["item"]["tags"]]
            if tagged_items == []:
                tag_counts = Counter(tag for located_item in deck_items for tag in located_item["item"]["tags"])
                tag_list = ", ".join(f"{tag} ({count})" for tag, count in sorted(tag_counts.items(), key=lambda pair: (-pair[1], pair[0])))
                print(f"rep: no item in {deck_label} is tagged {wanted_tag}; its tags: {tag_list or 'none'}", file=sys.stderr)
                return 2
            selectable_items = [
                located_item for located_item in tagged_items
                if not (located_item["item"]["id"] in fold_result["items"] and fold_result["items"][located_item["item"]["id"]]["suspended"])
            ]  # fmt: skip
            # Shuffled by hash, as later rounds are (D48): the same order on replay.
            selectable_items.sort(
                key=lambda located_item: hashlib.sha256(f"{session_id}\n1\n{located_item['item']['id']}".encode()).digest()
            )
            plan: list[PlanSlot] = []
            for located_item in selectable_items[:count_argument]:
                item_state = fold_result["items"].get(located_item["item"]["id"])
                seen_before = item_state is not None and item_state["memory"] is not None
                plan.append({"item_id": located_item["item"]["id"], "reason": "drill" if seen_before else "new"})
            drill_selection = " ".join(
                part for part in (deck_label, wanted_tag, None if count_argument is None else f"count={count_argument}") if part is not None
            )
            new_in_drill = sum(1 for slot in plan if slot["reason"] == "new")
            drill_notes.append(
                f"{len(plan)} of the {len(tagged_items)} items in {deck_label}"
                + ("" if wanted_tag is None else f" tagged {wanted_tag}")
                + ("" if count_argument is None else ", drawn at random")
                + "."
            )
            if len(tagged_items) > len(selectable_items):
                drill_notes.append(f"{len(tagged_items) - len(selectable_items)} suspended, left out (`rep unsuspend ID`).")
            if deck_file_name is None and plan != []:
                # PLAN.md D59: "every deck" hides which decks; say them.
                plan_deck_counts = Counter(
                    Path(located_items_by_id[slot["item_id"]]["path"]).name.removesuffix(LIBRARY_FILE_SUFFIX) for slot in plan
                )
                drill_notes.append("From " + ", ".join(f"{name} {count}" for name, count in sorted(plan_deck_counts.items())) + ".")
            if new_in_drill > 0:
                drill_notes.append(f"{new_in_drill} never seen before: from today they are on your schedule, and count")
                drill_notes.append(f"toward today's {preset['new_per_day']} new items, so today's session brings fewer.")
            if len(plan) > DRILL_SIZE_WARNING:
                # PLAN.md D59: a drill of every item in a big deck was started
                # by accident, with no sign of its length until it ran.
                drill_notes.append(
                    f"That is a long drill: {len(plan)} items, over {len(plan) * SECONDS_PER_ANSWER // 60} minutes. "
                    f"Ctrl-D here, then add --count 20 for a smaller set."
                )
            drill_notes.append("Grades update the schedule as a session's do; stopping early loses nothing.")
            if plan == []:
                print(f"Every item in {deck_label} is suspended.")
                return 0
            if not sys.stdin.isatty() or not sys.stdout.isatty():
                print("rep: a drill needs a terminal on standard input and output", file=sys.stderr)
                return 2
        else:
            with run_log.phase(run_record, "plan"):
                session_plan = plan_session(library_check["located_items"], fold_result["items"], events_load["events"], today, preset)
            plan = session_plan["slots"]
        run_record["counts"]["planned_items"] = len(plan)
        if plan == []:
            # PLAN.md D51: say what comes next and what can be done now,
            # instead of leaving the person to remember drills and deck names.
            upcoming_due_days = sorted(
                item_state["due_day"] for item_state in fold_result["items"].values()
                if item_state["due_day"] is not None and not item_state["suspended"] and item_state["due_day"] > today
            )  # fmt: skip
            # PLAN.md D59: a finished day is not an empty one; say which it is.
            effective_so_far = effective_events(events_load["events"])
            completed_session_ids = {
                event["session"] for event in effective_so_far["ordered_events"]
                if event["kind"] == "session_end" and event["reason"] == "completed"
            }  # fmt: skip
            session_done_today = any(
                event["kind"] == "session_start" and "selection" not in event and event["id"] in completed_session_ids
                and scheduling_day(parse_canonical_time(event["at"]), preset["day_start_hour"]) == today
                for event in effective_so_far["ordered_events"]
            )  # fmt: skip
            print(f"Today's session is done ({today})." if session_done_today else f"Nothing due today ({today}).")
            assert session_plan is not None, "an empty drill returned earlier"
            if session_plan["new_waiting"] > 0 and session_plan["new_left_today"] == 0:
                print(
                    f"New items: today's {preset['new_per_day']} are started ({session_plan['introduced_today']} today, drills included); "
                    f"{session_plan['new_waiting']} more wait for the next days."
                )
            elif session_plan["new_waiting"] == 0:
                print("New items: none left; add some with `rep add --help`.")
            if upcoming_due_days != []:
                print(f"Next due: {upcoming_due_days.count(upcoming_due_days[0])} on {upcoming_due_days[0]}.")
            deck_counts = Counter(Path(located_item["path"]).name.removesuffix(LIBRARY_FILE_SUFFIX) for located_item in library_check["located_items"])
            if deck_counts:
                deck_list = ", ".join(f"{name} ({count})" for name, count in sorted(deck_counts.items())[:DECKS_LISTED])
                if len(deck_counts) > DECKS_LISTED:
                    deck_list += f", +{len(deck_counts) - DECKS_LISTED} more (rep status)"
                print(f"To practise more now: rep drill DECK --count 20   (decks: {deck_list})")
            return 0
        reason_by_item_id = {slot["item_id"]: slot["reason"] for slot in plan}
        due_count = sum(1 for slot in plan if slot["reason"] == "due")

        # PLAN.md D46: imported here, so the commands nvim runs on save never
        # load it. Styling follows NO_COLOR and whether both streams are
        # terminals.
        from pyutils import terminal_output  # pyright: ignore[reportMissingTypeStubs]  (no py.typed yet: FINDINGS.md F22)

        terminal_output.set_color(None)
        terminal_output.set_layout(max_width=76, align="center")
        # input() writes its own prompt, so prompts and plain lines start at
        # the column emit() gives the content block, found by the same
        # function rather than by repeating its arithmetic.
        aligned_rule = terminal_output.align_text(terminal_output.format_separator(), align="center")
        block_indent = aligned_rule[: len(aligned_rule) - len(aligned_rule.lstrip(" "))]
        terminal_descriptor = sys.stdin.fileno()

        if command == "drill":
            terminal_output.emit(terminal_output.format_labeled_separator(f"{today}: drill {drill_selection}"))
            for drill_note in drill_notes:
                print(f"{block_indent}{drill_note}")
        else:
            terminal_output.emit(terminal_output.format_labeled_separator(f"{today}: {due_count} due, {len(plan) - due_count} new"))
        # PLAN.md D51: what the session holds, how long it is, and the keys,
        # on screen, so none of it has to be remembered.
        if command != "drill":
            planned_by_deck_and_reason = Counter(
                (Path(located_items_by_id[slot["item_id"]]["path"]).name.removesuffix(LIBRARY_FILE_SUFFIX), slot["reason"])
                for slot in plan
            )
            deck_summaries: list[str] = []
            for deck_name in sorted({deck_and_reason[0] for deck_and_reason in planned_by_deck_and_reason}):
                reason_counts = [
                    f"{planned_by_deck_and_reason[(deck_name, reason)]} {reason}" for reason in ("due", "new")
                    if planned_by_deck_and_reason[(deck_name, reason)] > 0
                ]  # fmt: skip
                deck_summaries.append(f"{deck_name}: {', '.join(reason_counts)}")
            print(f"{block_indent}From {'; '.join(deck_summaries)}.")
        new_slot_count = sum(1 for slot in plan if slot["reason"] == "new")
        if session_plan is not None:
            # PLAN.md D59: why this many new items, from the plan's own terms,
            # so the limit and what used it up are on screen.
            new_reason = f"up to {preset['new_per_day']} new a day"
            if session_plan["introduced_today"] > 0:
                new_reason += f", {session_plan['introduced_today']} started earlier today (drills count)"
            if session_plan["new_room_in_budget"] < session_plan["new_left_today"]:
                new_reason += f"; {due_count} due leave room for {session_plan['new_room_in_budget']} in a {preset['session_budget']}-answer session"
            waiting_text = f"; {session_plan['new_waiting']} more wait, deck by deck in the order added" if session_plan["new_waiting"] > 0 else ""
            print(f"{block_indent}{new_slot_count} new: {new_reason}{waiting_text}.")
        print(f"{block_indent}About {len(plan) + new_slot_count} answers if each is recalled (a new item comes back once).")
        # PLAN.md D59: "a cue is enough" was wrong for arithmetic and names.
        print(f"{block_indent}At > type your answer and press Enter. Cards marked \"a number\" or \"as written\"")
        print(f"{block_indent}are checked as typed; on the others a cue is enough, and you grade it.")
        print(f"{block_indent}Esc: vi keys (h l w b 0 $ x cw u; i to type). Esc v: use your editor.")
        print(f"{block_indent}Each round ends with its answers and the keys in your editor, to grade.")
        print(f"{block_indent}Stopping is fine: Ctrl-D grades what you answered; the rest wait for next time.")
        # PLAN.md D35, kept by D45: a line counts only once its prompt is on
        # screen. The flush comes before the prompt: after it, a key typed in
        # the instant between seeing the prompt and the flush would be lost.
        termios.tcflush(terminal_descriptor, termios.TCIFLUSH)
        try:
            input(f"{block_indent}Enter starts; Ctrl-D stops. ")
        except (EOFError, KeyboardInterrupt):
            print()
            return 0
        session_start: SessionStartEvent = {
            "format_version": EVENT_FORMAT_VERSION,
            "id": session_id,
            "at": format_canonical_time(datetime.now(UTC)),
            "device": device_id,
            "kind": "session_start",
            # PLAN.md D40: the values used, so the history describes itself.
            "preset": {
                "session_budget": preset["session_budget"],
                "new_per_day": preset["new_per_day"],
                "new_item_cost": preset["new_item_cost"],
                "day_start_hour": preset["day_start_hour"],
                "desired_retention": preset["desired_retention"],
            },
            # PLAN.md D49. The offset: `at` is UTC, so without it the local
            # hour of a session is a guess. The plan: once the library
            # changes it cannot be recomputed. The source hash: exactly which
            # code ran, with no version number anyone must remember to bump.
            "utc_offset": datetime.now(UTC).astimezone().isoformat(timespec="seconds")[-6:],
            "plan": [{"item": slot["item_id"], "reason": slot["reason"]} for slot in plan],
            "rep_source": run_record["source"],
        }
        if drill_selection != "":
            session_start["selection"] = drill_selection
        session_events: list[Event] = []
        end_reason: Literal["completed", "quit", "interrupted"] = "interrupted"
        # The events cannot tell an answered round from a graded one (a
        # sheet saved unchanged writes nothing), so the loop counts graded
        # rounds and the fold looks no further than the next (session.py R5).
        graded_round_number = 0
        stop_requested = False
        session_was_started = False
        # PLAN.md D54, D59: why each item of a later round is back, decided
        # once at the round's start from the grades so far.
        retest_reason_by_item_id: dict[str, str] = {}
        try:
            append_events_waiting(state_directory, data_root / "events", device_id, [session_start])
            session_events.append(session_start)
            session_was_started = True
            while True:
                round_state = session_rounds(plan, session_events, graded_round_number + 1, session_start["id"])
                round_number = round_state["round_number"]
                round_is_answered = round_state["unanswered_item_ids"] == []
                if round_is_answered and graded_round_number == round_number:
                    end_reason = "completed"  # D45: no round follows
                    break

                # --- the round's sheet: when it is answered, or on Ctrl-D for what was answered ---
                if round_is_answered or stop_requested:
                    sheet_attempt_ids = round_state["round_attempt_ids"]
                    sheet_title = f"rep {today}, round {round_number}: {len(sheet_attempt_ids)} answers"
                    sheet_pass = 1
                    while sheet_attempt_ids != []:
                        sheet_entries = grading_sheet_entries(session_events, sheet_attempt_ids, located_items_by_id)
                        if sheet_entries == []:
                            break
                        sheet_events = grade_on_a_sheet(
                            sheet_entries, sheet_title,
                            state_directory / f"sheet-{session_start['id']}-{round_number}-{sheet_pass}.txt", device_id,
                        )  # fmt: skip
                        if sheet_events != []:
                            append_events_waiting(state_directory, data_root / "events", device_id, sheet_events)
                            session_events.extend(sheet_events)
                        # PLAN.md D54: an answer left ? leaves the session (R3);
                        # the trial showed that is easy to do by accident, so say
                        # so and offer the sheet again before it happens.
                        sheet_attempt_ids = [
                            entry["attempt_id"] for entry in grading_sheet_entries(session_events, sheet_attempt_ids, located_items_by_id)
                            if entry["rating"] is None
                        ]  # fmt: skip
                        if sheet_attempt_ids == [] or stop_requested:
                            break
                        print(f"{block_indent}{len(sheet_attempt_ids)} answers left ?: an answer without a grade leaves this session, no retest.")
                        termios.tcflush(terminal_descriptor, termios.TCIFLUSH)
                        try:
                            reply = input(f"{block_indent}Enter: grade them now.   n, Enter: leave them for `rep review`. ")
                        except EOFError:
                            print()
                            break
                        if reply.strip().lower().startswith("n"):
                            break
                        sheet_pass += 1
                        sheet_title = f"rep {today}, round {round_number}: {len(sheet_attempt_ids)} still without a grade"
                    graded_round_number = round_number
                    if stop_requested:
                        end_reason = "quit"
                        break
                    continue

                # --- one question; the answer is written, nothing is revealed (D45) ---
                if round_state["round_attempt_ids"] == []:
                    round_size = len(round_state["round_item_ids"])
                    round_label = f"round {round_number}: {round_size} {'items' if round_number == 1 else 'to retest'}"
                    terminal_output.emit(terminal_output.format_labeled_separator(round_label))
                    print(f"{block_indent}Esc: vi keys   Esc v: editor   Ctrl-D: grade, then stop   Ctrl-C: stop now")
                    if round_number > 1:
                        effective_so_far = effective_events(session_events)
                        for round_item_id in round_state["round_item_ids"]:
                            previous_ratings = [
                                effective_so_far["amended_ratings"].get(event["id"], event["rating"])
                                for event in effective_so_far["ordered_events"]
                                if event["kind"] == "attempt" and event["item"] == round_item_id
                            ]  # fmt: skip
                            retest_reason_by_item_id[round_item_id] = "missed" if previous_ratings[-1] == AGAIN else "second look"
                        missed_count = sum(1 for round_item_id in round_state["round_item_ids"] if retest_reason_by_item_id[round_item_id] == "missed")
                        second_look_count = round_size - missed_count
                        # PLAN.md D59: counts and the reason, without a decision number.
                        if missed_count > 0:
                            print(f"{block_indent}{missed_count} missed: each comes back until you recall it once.")
                        if second_look_count > 0:
                            print(
                                f"{block_indent}{second_look_count} new, for a second look: recalling a new item again after"
                            )
                            print(f"{block_indent}others came between is what makes it last past today.")
                item_id = round_state["unanswered_item_ids"][0]
                located_item = located_items_by_id[item_id]
                item = located_item["item"]
                round_position = len(round_state["round_attempt_ids"]) + 1
                # Not "again": that is a grade word, and an item graded Easy
                # that returns (a new item always does, D36) read as a miss.
                card_label = Path(located_item["path"]).name.removesuffix(LIBRARY_FILE_SUFFIX) + ", "
                if round_number == 1:
                    card_label += reason_by_item_id[item_id]
                else:
                    # PLAN.md D54: missed, or a new item's second look (D36).
                    card_label += "retest, " + retest_reason_by_item_id[item_id]
                # D20 compares these as typed; say how, in words (D51).
                if item["check"] == "exact":
                    card_label += ", as written"
                elif item["check"] == "numeric":
                    card_label += ", a number"
                terminal_output.emit(
                    terminal_output.format_card(f"{round_position} of {len(round_state['round_item_ids'])}", card_label, item["question"])
                )
                shown_at = time.monotonic()
                termios.tcflush(terminal_descriptor, termios.TCIFLUSH)
                try:
                    while True:
                        typed_answer = input(f"{block_indent}> ")
                        # PLAN.md D34: a lone surrogate is a byte that is not
                        # UTF-8; it could not be written to the events file.
                        if not any("\ud800" <= character <= "\udfff" for character in typed_answer):
                            break
                        print(f"{block_indent}That was not valid UTF-8; type it again.")
                except EOFError:
                    print()
                    stop_requested = True
                    continue
                latency_milliseconds = round((time.monotonic() - shown_at) * 1000)
                committed_at = datetime.now(UTC)
                # PLAN.md D45: an exact or numeric answer carries its D20
                # grade, unseen until the sheet, where changing it is a
                # recorded correction; a self-graded one is graded there.
                automatic_rating: int | None = None
                if item["check"] != "self":
                    automatic_rating = GOOD if grade_typed_answer(item, typed_answer) else AGAIN
                attempt: AttemptEvent = {
                    "format_version": EVENT_FORMAT_VERSION,
                    "id": new_event_id(secrets.token_bytes),
                    "at": format_canonical_time(committed_at),
                    "device": device_id,
                    "kind": "attempt",
                    "session": session_start["id"],
                    "item": item_id,
                    "rating": automatic_rating,
                    "latency_milliseconds": latency_milliseconds,
                    # PLAN.md D20 constraint 1: the text as typed.
                    "typed_answer": typed_answer,
                    "fingerprint": item_fingerprint(item),
                    "day": scheduling_day(committed_at, preset["day_start_hour"]),
                }
                append_events_waiting(state_directory, data_root / "events", device_id, [attempt])
                session_events.append(attempt)
                print()
        except KeyboardInterrupt:
            # D45: ends at once; this round's answers wait for `rep review`.
            end_reason = "interrupted"
            print()
        finally:
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
                append_events_waiting(state_directory, data_root / "events", device_id, [session_end])
        effective_session = effective_events(session_events)
        session_attempts = [event for event in effective_session["ordered_events"] if event["kind"] == "attempt"]
        ungraded_count = sum(
            1 for attempt in session_attempts if effective_session["amended_ratings"].get(attempt["id"], attempt["rating"]) is None
        )
        terminal_output.emit(terminal_output.format_labeled_separator(f"session {end_reason}"))
        print(f"{block_indent}{len(session_attempts)} answers; {ungraded_count} wait for `rep review`.")
        # PLAN.md D51: when these come back, from the history as it now stands.
        fold_after_session = fold_events([*events_load["events"], *session_events], desired_retention=preset["desired_retention"])
        next_review_counts: Counter[str] = Counter()
        for slot in plan:
            item_state_after = fold_after_session["items"].get(slot["item_id"])
            if item_state_after is not None and item_state_after["due_day"] is not None:
                next_review_counts[item_state_after["due_day"]] += 1
        if next_review_counts:
            next_review_days = sorted(next_review_counts.items())
            next_review_text = ", ".join(f"{count} on {day}" for day, count in next_review_days[:4])
            print(f"{block_indent}Next reviews: {next_review_text}{', and later' if len(next_review_days) > 4 else ''}.")
        # PLAN.md D54: the next step is offered, not remembered.
        deck_names = sorted({Path(located_item["path"]).name.removesuffix(LIBRARY_FILE_SUFFIX) for located_item in library_check["located_items"]})
        # PLAN.md D59: a few names, not every deck; status lists them all.
        deck_list = ", ".join(deck_names[:DECKS_LISTED])
        if len(deck_names) > DECKS_LISTED:
            deck_list += f", +{len(deck_names) - DECKS_LISTED} more"
        print(f"{block_indent}What next:")
        if ungraded_count > 0:
            print(f"{block_indent}  rep review         grade the {ungraded_count} answers still waiting")
        print(f"{block_indent}  rep drill DECK     practise more now ({deck_list})")
        print(f"{block_indent}  rep status         what is due, by deck")
        return 0

    if command == "stamp":
        # PLAN.md D58: a terminal on stdin means nothing was piped in, and
        # reading would wait in silence (the person met exactly that).
        if sys.stdin.isatty():
            print(
                "rep stamp gives ids to the items of a library file read on standard input:\n"
                "  rep stamp < file.md > stamped.md\n"
                "nvim does this on save. To add items to a deck: rep add --stdin --to DECK < file.md",
                file=sys.stderr,
            )
            return 2
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
        with run_log.phase(run_record, "read_library"):
            library_read = read_library_files(data_root / "library")
        for file_problem in library_read["problems"]:
            print(f"rep: warning: {file_problem['path']}: {file_problem['message']}", file=sys.stderr)
        for library_file in library_read["files"]:
            for source_item in parse_library_text(library_file["text"]):
                id_field = source_item["fields"].get("id")
                if id_field is not None:
                    existing_item_ids.add(id_field["value"])

        with run_log.phase(run_record, "stamp"):
            stamp_result = stamp_library_text(input_text, existing_item_ids, secrets.token_bytes)
        run_record["counts"]["stamped_items"] = len(stamp_result["stamped_item_ids"])
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
        # PLAN.md D58: without --stdin, or with nothing piped in, say how
        # instead of an argparse error or a silent wait.
        add_reads_stdin: bool = parsed_arguments.stdin
        if not add_reads_stdin or sys.stdin.isatty():
            print(
                "rep add reads items on standard input, so give it a file:\n"
                "  rep add --stdin --to DECK < file.md\n"
                "Each item is a question and its answer:\n"
                "  ### Q: What is the capital of Peru?\n"
                "  A: Lima\n"
                "CONVENTIONS.md has the rest: checks, sources, tags.",
                file=sys.stderr,
            )
            return 2
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
            # PLAN.md D52: where each question already is, spaces and case
            # folded; running the same add twice must not double a deck.
            existing_question_locations: dict[str, str] = {}
            for library_file in library_read["files"]:
                for source_item in parse_library_text(library_file["text"]):
                    id_field = source_item["fields"].get("id")
                    if id_field is not None:
                        existing_item_ids.add(id_field["value"])
                    existing_question_locations.setdefault(
                        " ".join(source_item["question"].split()).casefold(), f"library/{library_file['name']}:{source_item['line']}"
                    )

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
                    elif " ".join(checked_item["question"].split()).casefold() in existing_question_locations:
                        refusals.append(
                            f"<stdin>:{checked_item['line']}:1: error: this question is already in the library at "
                            f"{existing_question_locations[' '.join(checked_item['question'].split()).casefold()]}; "
                            "nothing added (was this file added before?)"
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
