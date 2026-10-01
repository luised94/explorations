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
  2  rep cannot run (bad setup, bad arguments, the writer lock is held);
     message on stderr, prefixed "rep: "

INVARIANTS
  Output meant for the person goes to stdout; warnings and errors go to
  stderr, so `rep ... > file` captures only results.
"""

import argparse
import importlib.metadata
import os
import secrets
import sys
from datetime import UTC, datetime
from pathlib import Path

from rep.events import fold_events, new_item_stamped_events
from rep.library import (
    ITEM_ID_PATTERN,
    Item,
    check_source_item,
    parse_library_text,
    plan_library_append,
    stamp_library_text,
)
from rep.machine import MachineContextError, resolve_machine_context
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
        description="Retrieval practice from your readings. See PLAN.md and CONVENTIONS.md.",
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

    # With no command, M3 will start today's session (PLAN.md D9). Until the
    # session exists, the honest affordance is the help text.
    if command is None:
        argument_parser.print_help()
        return 0

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

        # --- every item on its own (parser and checks) ---
        # first location of each id, for I1; citekeys to check against the bib
        id_first_locations: dict[str, tuple[str, int]] = {}
        library_item_ids: set[str] = set()
        cited_items: list[tuple[str, int, str, bool]] = []  # path, line, citekey, unverified
        item_count = 0
        for library_file in library_read["files"]:
            for source_item in parse_library_text(library_file["text"]):
                item_count += 1
                checked_item, item_problems = check_source_item(source_item)
                for problem in item_problems:
                    lint_lines.append(
                        (library_file["path"], problem["line"], problem["column"], problem["severity"], problem["message"])
                    )
                for open_question in source_item["open_questions"]:
                    lint_lines.append((library_file["path"], open_question["line"], 1, "note", f"?: {open_question['value']}"))
                # I1 counts every id that is written down, even on an item
                # with other errors: the id is still claimed in the file.
                id_field = source_item["fields"].get("id")
                if id_field is not None:
                    item_id = id_field["value"]
                    library_item_ids.add(item_id)
                    first_location = id_first_locations.get(item_id)
                    if first_location is None:
                        id_first_locations[item_id] = (library_file["path"], id_field["line"])
                    else:
                        lint_lines.append(
                            (
                                library_file["path"],
                                id_field["line"],
                                1,
                                "error",
                                f"id {item_id} is already used at {first_location[0]}:{first_location[1]}; "
                                "a session cannot tell these items apart (delete this id line to get a new one)",
                            )
                        )
                if checked_item is not None and checked_item["citekey"] is not None:
                    cited_items.append(
                        (library_file["path"], checked_item["line"], checked_item["citekey"], checked_item["citekey_is_unverified"])
                    )

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
            if event["kind"] != "undo" and event["kind"] != "amend":
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
