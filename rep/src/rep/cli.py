"""Command-line shell: parse arguments, call the core, print, return an exit code.

REPRESENTATION
  The parsed arguments (argparse.Namespace) live only inside main. Every
  command is one branch of main, so the whole control flow reads top to
  bottom in one place (typer-style decorator dispatch was rejected in
  PLAN.md D13 for hiding it).

EXIT CODES
  0  success
  1  the input has problems the person must fix; nothing was written, and
     each problem is on stderr as path:line:col: severity: message (the
     quickfix format, PLAN.md D12)
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

from rep.events import EVENT_FORMAT_VERSION, EVENT_ID_LENGTH, Event, format_canonical_time
from rep.library import parse_library_text, stamp_library_text
from rep.machine import DEVICE_ID_ALPHABET, MachineContextError, resolve_machine_context
from rep.storage import WriterLockBusy, acquire_writer_lock, append_events


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
        # Bytes, not text: text-mode stdin decodes by the locale, and under
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
            print(f"rep: data root {data_root} does not exist; create it with: mkdir -p {data_root}", file=sys.stderr)
            return 2

        # I1 is library-wide, so new ids must avoid every id in every file.
        # Problems in other files are lint's to report; their ids still count.
        existing_item_ids: set[str] = set()
        library_directory = data_root / "library"
        if library_directory.is_dir():
            for library_path in sorted(library_directory.glob("*.md")):
                try:
                    library_text = library_path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    print(
                        f"rep: warning: {library_path} is not UTF-8; its ids were not checked for collisions",
                        file=sys.stderr,
                    )
                    continue
                for source_item in parse_library_text(library_text):
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
            # Ids and their item_stamped events go out together or not at
            # all: ids without events would silently drop captures from E1.
            try:
                lock_descriptor = acquire_writer_lock(machine_context["state_directory"])
            except WriterLockBusy as lock_busy:
                sys.stdout.buffer.write(input_bytes)
                print(f"rep: {lock_busy}; nothing stamped, save again to retry", file=sys.stderr)
                return 2
            try:
                stamped_at = format_canonical_time(datetime.now(UTC))
                stamped_events: list[Event] = []
                for stamped_item_id in stamp_result["stamped_item_ids"]:
                    # One random byte per character; 256 is a multiple of 32.
                    event_id = "".join(
                        DEVICE_ID_ALPHABET[random_byte % len(DEVICE_ID_ALPHABET)]
                        for random_byte in secrets.token_bytes(EVENT_ID_LENGTH)
                    )
                    stamped_events.append(
                        {
                            "format_version": EVENT_FORMAT_VERSION,
                            "id": event_id,
                            "at": stamped_at,
                            "device": machine_context["device_id"],
                            "kind": "item_stamped",
                            "item": stamped_item_id,
                        }
                    )
                append_events(data_root / "events", machine_context["device_id"], stamped_events)
            finally:
                os.close(lock_descriptor)

        sys.stdout.buffer.write(stamp_result["text"].encode("utf-8"))
        return 0

    raise AssertionError(f"command {command!r} is registered but not handled")
