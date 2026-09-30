"""Command-line shell: parse arguments, call the core, print, return an exit code.

REPRESENTATION
  The parsed arguments (argparse.Namespace) live only inside main. Every
  command is one branch of main, so the whole control flow reads top to
  bottom in one place (typer-style decorator dispatch was rejected in
  PLAN.md D13 for hiding it).

EXIT CODES
  0  success
  2  a problem the person must fix (bad setup, bad arguments); message on
     stderr, prefixed "rep: "

INVARIANTS
  Output meant for the person goes to stdout; warnings and errors go to
  stderr, so `rep ... > file` captures only results.
"""

import argparse
import importlib.metadata
import os
import sys
from pathlib import Path

from rep.machine import MachineContextError, resolve_machine_context


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

    raise AssertionError(f"command {command!r} is registered but not handled")
