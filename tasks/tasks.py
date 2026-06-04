# ============================================================================
# tsk -- task, calendar & habit tracker
#
# Usage: uv run tasks.py <command> [args]
# Alias: tsk (defined in tsk.sh)
#
# Code:  ~/personal_repos/explorations/tasks/tasks.py
# Data:  ~/personal_repos/tasks/ (set via TASKS_LOCAL_DIR)
# ============================================================================

import sys
import os
import time
from pathlib import Path
from datetime import date, datetime, timedelta

# ============================================================================
# CONFIGURATION
# ============================================================================

REQUIRED_PYTHON = (3, 10)

env_path = os.environ.get("TASKS_LOCAL_DIR")
if env_path:
    DATA_DIR = Path(env_path).expanduser()
    DATA_DIR_FROM_ENV = True
else:
    DATA_DIR = Path.home() / "personal_repos" / "tasks"
    DATA_DIR_FROM_ENV = False

ACTIVE_FILE = DATA_DIR / "active.txt"
CALENDAR_FILE = DATA_DIR / "calendar.txt"
DONE_FILE = DATA_DIR / "done.txt"
HABIT_LOG_FILE = DATA_DIR / "habit_log.txt"
USAGE_LOG_FILE = DATA_DIR / "usage_log.txt"
DATA_FILES = [ACTIVE_FILE, CALENDAR_FILE, DONE_FILE, HABIT_LOG_FILE, USAGE_LOG_FILE]
DOCS_DIR = DATA_DIR / "docs"

# ============================================================================
# PREFLIGHT CHECKS
# ============================================================================
# Fail fast with distinct exit codes before any logic or file writes.
# These run above every def, so the version gate fires before the 3.10+
# union-type annotations below are ever evaluated.
#   exit 2 = unsupported Python   exit 3 = data dir missing   exit 4 = not writable

if sys.version_info < REQUIRED_PYTHON:
    print(
        f"error: tsk requires Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+, "
        f"found {sys.version_info[0]}.{sys.version_info[1]}",
        file=sys.stderr,
    )
    sys.exit(2)

# Commands that must run even when the data directory is absent, because
# their job is to create it. These skip the directory gate below.
BOOTSTRAP_COMMANDS = ("init",)
peeked_command = sys.argv[1] if len(sys.argv) > 1 else ""

if peeked_command not in BOOTSTRAP_COMMANDS:
    if not DATA_DIR.is_dir():
        if DATA_DIR_FROM_ENV:
            print(
                f"error: data directory not found: {DATA_DIR}\n"
                f"TASKS_LOCAL_DIR points here but the directory does not exist\n"
                f"run 'tsk init' to create it, or fix the path / mount the drive",
                file=sys.stderr,
            )
        else:
            print(
                f"error: data directory not found: {DATA_DIR}\n"
                f"run 'tsk init' to create it, or set TASKS_LOCAL_DIR to an existing directory",
                file=sys.stderr,
            )
        sys.exit(3)

    if not os.access(DATA_DIR, os.W_OK):
        print(f"error: data directory not writable: {DATA_DIR}", file=sys.stderr)
        sys.exit(4)

# ============================================================================
# PREPROCESSING / DERIVED VALUES
# ============================================================================


def ensure_data_files() -> None:
    """Create the data files and docs directory inside DATA_DIR.

    Touches each path in DATA_FILES and makes DOCS_DIR. Assumes DATA_DIR
    already exists; safe to call repeatedly (exist_ok throughout).
    """
    for data_file_path in DATA_FILES:
        data_file_path.touch(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)


# On a normal run the data dir exists (gated above), so ensure its files are
# present. On a bootstrap command the dir may not exist yet; init creates it.
if DATA_DIR.is_dir():
    ensure_data_files()

# Blueprint sections 5 (main-loop metrics) and 6 (post-run summary report)
# are N/A for a CLI dispatcher: per-command confirmation prints serve as the
# summary, and the dispatch-level usage log serves as the metrics layer.

# ============================================================================
# PARSER
# ============================================================================


def parse_records(text: str) -> list[dict[str, str | list[str]]]:
    """Parse CCL-style text into a list of record dicts.

    Reads raw text, splits on blank lines into record blocks, handles
    continuation lines (leading whitespace) and duplicate field names
    (collected into lists). Returns list of dicts with string field
    names and string or list-of-string field values.
    """
    records = []
    current_record: dict[str, str | list[str]] = {}
    current_field_name = None

    for raw_line in text.splitlines():
        line_content = raw_line.strip()

        # blank line ends the current record
        if not line_content:
            if current_record:
                records.append(current_record)
                current_record = {}
                current_field_name = None
            continue

        # continuation line (leading whitespace, and we have an active field)
        if raw_line[0] in (" ", "\t") and current_field_name is not None:
            existing_content = current_record[current_field_name]
            if isinstance(existing_content, list):
                existing_content[-1] = existing_content[-1] + "\n" + line_content
            else:
                if existing_content:
                    current_record[current_field_name] = (
                        existing_content + "\n" + line_content
                    )
                else:
                    current_record[current_field_name] = line_content
            continue

        # field_name = field_value line
        if "=" in raw_line:
            field_name, _, field_value = raw_line.partition("=")
            field_name = field_name.strip()
            field_value = field_value.strip()
            if field_name in current_record:
                prior_content = current_record[field_name]
                if isinstance(prior_content, list):
                    prior_content.append(field_value)
                else:
                    current_record[field_name] = [prior_content, field_value]
            else:
                current_record[field_name] = field_value
            current_field_name = field_name
            continue

        # line with no = and no leading whitespace -- treat as continuation
        # of previous field if one exists, otherwise skip
        if current_field_name is not None:
            existing_content = current_record[current_field_name]
            if isinstance(existing_content, list):
                existing_content[-1] = existing_content[-1] + "\n" + line_content
            else:
                current_record[current_field_name] = (
                    existing_content + "\n" + line_content
                )

    # finalize last record
    if current_record:
        records.append(current_record)

    return records


def parse_file(filepath: str | Path) -> list[dict[str, str | list[str]]]:
    """Read a CCL-style file and return a list of record dicts.

    Reads the file at filepath, passes contents to parse_records.
    Returns empty list if file is missing or empty.
    """
    file_path = Path(filepath)
    if not file_path.exists():
        return []
    text = file_path.read_text(encoding="utf-8")
    if not text.strip():
        return []
    return parse_records(text)


# ============================================================================
# WRITER
# ============================================================================

FIELD_ORDER = [
    "id",
    "type",
    "summary",
    "status",
    "project",
    "priority",
    "due",
    "frequency",
    "review",
    "date",
    "time_start",
    "time_end",
    "recur",
    "end_recur",
    "tags",
    "parent",
    "source",
    "linked",
    "location",
    "energy",
    "created",
    "updated",
    "completed",
    "prep",
    "notes",
]


def format_record(record: dict[str, str | list[str]]) -> str:
    """Serialize a record dict to CCL-style field_name = field_value text.

    Orders fields per FIELD_ORDER with unknowns appended alphabetically.
    Writes multi-line field values with 2-space indented continuation.
    Writes list-valued fields as repeated field_name = field_value lines.
    """
    output_lines = []
    known_field_names = [name for name in FIELD_ORDER if name in record]
    unknown_field_names = sorted(name for name in record if name not in FIELD_ORDER)
    all_field_names = known_field_names + unknown_field_names

    for field_name in all_field_names:
        raw_field = record[field_name]
        values_to_write = raw_field if isinstance(raw_field, list) else [raw_field]
        for field_value in values_to_write:
            if "\n" in field_value:
                content_lines = field_value.split("\n")
                first_line = content_lines[0]
                if first_line:
                    output_lines.append(f"{field_name} = {first_line}")
                else:
                    output_lines.append(f"{field_name} =")
                for continuation in content_lines[1:]:
                    output_lines.append(f"  {continuation}")
            else:
                output_lines.append(f"{field_name} = {field_value}")

    return "\n".join(output_lines)


def write_file(filepath: str | Path, records: list[dict[str, str | list[str]]]) -> None:
    """Write a list of record dicts to a CCL-style file atomically.

    Formats each record via format_record, joins with blank line separators,
    writes the content to a temp sibling file, then atomically replaces the
    target. A crash or interrupted write cannot truncate the existing file.
    Empty records list writes an empty file.
    """
    file_path = Path(filepath)
    if not records:
        file_content = ""
    else:
        formatted_records = []
        for record in records:
            if not record:
                continue
            formatted_records.append(format_record(record))
        file_content = "\n\n".join(formatted_records) + "\n"

    temp_file_path = file_path.with_name(file_path.name + ".tmp")
    temp_file_path.write_text(file_content, encoding="utf-8")
    temp_file_path.replace(file_path)


# ============================================================================
# VERIFICATION
# ============================================================================


def verify_parser() -> None:
    """Run round-trip tests on the parser and writer.

    Defines test cases as (name, input_text) pairs, runs each through
    parse_file -> write_file -> parse_file and checks semantic equality.
    Prints results to stdout, exits 1 on any failure.
    """
    import tempfile

    test_cases = [
        ("simple record", "id = T0522a\ntype = task\nsummary = test task\n"),
        (
            "multi-line values",
            "id = T0522a\n"
            "type = task\n"
            "summary = test task\n"
            "notes =\n"
            "  line one of notes\n"
            "  line two of notes\n",
        ),
        (
            "duplicate keys (list)",
            "id = T0522b\ntype = task\nsummary = test\ntags = #test\ntags = #example\n",
        ),
        (
            "empty values",
            "id = T0522c\n"
            "type = task\n"
            "summary = test\n"
            "notes =\n"
            "  content after empty first line\n",
        ),
        (
            "all entity types",
            "id = T0522a\n"
            "type = task\n"
            "summary = a task\n"
            "status = active\n"
            "priority = 2\n"
            "created = 2026-05-22\n"
            "updated = 2026-05-22\n"
            "\n"
            "id = G0501a\n"
            "type = goal\n"
            "summary = a goal\n"
            "review = monthly\n"
            "created = 2026-05-01\n"
            "updated = 2026-05-15\n"
            "\n"
            "id = H0522a\n"
            "type = habit\n"
            "summary = morning exercise\n"
            "frequency = daily\n"
            "created = 2026-05-22\n"
            "updated = 2026-05-22\n",
        ),
        (
            "multiple records",
            "id = T0522a\n"
            "summary = first\n"
            "\n"
            "id = T0522b\n"
            "summary = second\n"
            "notes =\n"
            "  multi-line\n"
            "  value here\n"
            "\n"
            "id = T0522c\n"
            "summary = third\n"
            "tags = #a\n"
            "tags = #b\n",
        ),
    ]

    tests_passed = 0
    tests_failed = 0

    for test_name, input_text in test_cases:
        label = f"parser round-trip: {test_name}"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".txt", delete=False, encoding="utf-8"
            ) as tmp_file:
                tmp_file.write(input_text)
                tmp_path = tmp_file.name
            first_parse = parse_file(tmp_path)
            write_file(tmp_path, first_parse)
            second_parse = parse_file(tmp_path)
            if first_parse != second_parse:
                print(f"{label} {'.' * (42 - len(label))} FAIL", file=sys.stderr)
                print(f"  first parse:  {first_parse}", file=sys.stderr)
                print(f"  second parse: {second_parse}", file=sys.stderr)
                tests_failed += 1
            else:
                print(f"{label} {'.' * (42 - len(label))} ok")
                tests_passed += 1
        finally:
            if tmp_path:
                os.unlink(tmp_path)

    total = tests_passed + tests_failed
    if tests_failed > 0:
        print(f"\n{tests_failed} of {total} tests FAILED", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"all {total} tests passed")


# ============================================================================
# DATA UTILITIES
# ============================================================================


def generate_id(type_prefix: str, existing_record_ids: list[str]) -> str | None:
    """Generate the next available ID for a given type prefix and today's date.

    Reads existing_record_ids to find used suffixes for this prefix + date
    combination. Returns the next available ID in format {prefix}{MMDD}{a-z},
    or None if all 26 suffix letters are exhausted.
    """
    today_mmdd = date.today().strftime("%m%d")
    id_stem = type_prefix + today_mmdd

    used_suffixes = set()
    for record_id in existing_record_ids:
        if record_id.startswith(id_stem) and len(record_id) == len(id_stem) + 1:
            used_suffixes.add(record_id[-1])

    for suffix_letter in "abcdefghijklmnopqrstuvwxyz":
        if suffix_letter not in used_suffixes:
            return id_stem + suffix_letter

    return None


def find_records_by_prefix(records: list[dict], search_prefix: str) -> list[dict]:
    """Find all records whose id field starts with search_prefix.

    Returns list of matching records. Caller interprets length:
    0 = not found, 1 = unique match, 2+ = ambiguous prefix.
    """
    matching_records = []
    for record in records:
        record_id = record.get("id", "")
        if record_id.startswith(search_prefix):
            matching_records.append(record)
    return matching_records


def parse_flags(
    arguments: list[str], flag_definitions: dict[str, str]
) -> tuple[list[str], dict[str, str]]:
    """Split a list of CLI arguments into positional args and flag values.

    flag_definitions maps flag strings (--project, -p) to canonical field
    names (project). Each flag consumes the next argument as its value.
    Returns (positional_args, flags_dict).
    """
    positional_args = []
    parsed_flags = {}
    arg_index = 0
    while arg_index < len(arguments):
        arg = arguments[arg_index]
        if arg in flag_definitions:
            canonical_name = flag_definitions[arg]
            if arg_index + 1 >= len(arguments):
                print(f"error: {arg} requires a value", file=sys.stderr)
                sys.exit(1)
            parsed_flags[canonical_name] = arguments[arg_index + 1]
            arg_index += 2
        else:
            positional_args.append(arg)
            arg_index += 1
    return positional_args, parsed_flags


def validate_priority(priority_value: str) -> bool:
    """Check that a priority string is 1, 2, or 3."""
    return priority_value in ("1", "2", "3")


def validate_date_format(date_string: str) -> bool:
    """Check that a date string matches YYYY-MM-DD format and is a real date."""
    try:
        datetime.strptime(date_string, "%Y-%m-%d")
        return True
    except ValueError:
        return False


def parse_habit_log(filepath: str | Path) -> list[tuple[str, str]]:
    """Read habit_log.txt and return a list of (date_string, habit_id) tuples.

    Splits each non-empty line on whitespace into a date and a habit ID.
    Returns empty list if the file is missing or empty. Lines that do not
    split into at least two whitespace-separated fields are skipped.
    """
    file_path = Path(filepath)
    if not file_path.exists():
        return []
    text = file_path.read_text(encoding="utf-8")
    log_entries = []
    for raw_line in text.splitlines():
        line_fields = raw_line.split()
        if len(line_fields) >= 2:
            entry_date = line_fields[0]
            entry_habit_id = line_fields[1]
            log_entries.append((entry_date, entry_habit_id))
    return log_entries


# ============================================================================
# COMMANDS
# ============================================================================


def handle_not_implemented(command_name: str, arguments: list[str]) -> None:
    """Print a not-implemented notice for placeholder commands."""
    print(f"not implemented: {command_name}")


def handle_help(arguments: list[str]) -> None:
    """Print command help to stdout.

    With no argument, lists every command with a one-line description and a
    pointer to per-command help. With a command name, prints that command's
    usage line, description, and flags grouped by field (flag names read from
    the command's flag dict, descriptions from FIELD_HELP).
    """

    descriptions = {
        "help": "show this help",
        "init": "create the data directory and files",
        "add": "create a new record (task, goal, habit, or event)",
        "edit": "edit a record in $EDITOR",
        "done": "complete a task or log a habit",
        "retire": "deactivate a habit or goal",
        "today": "daily dashboard (default)",
        "list": "list active records",
        "week": "(not implemented)",
        "review": "(not implemented)",
        "stale": "(not implemented)",
        "search": "(not implemented)",
        "tomorrow": "(not implemented)",
        "goals": "(not implemented)",
    }

    if arguments:
        requested_command = arguments[0]
        if requested_command not in descriptions:
            print(f"unknown command: {requested_command}", file=sys.stderr)
            print("run 'tsk help' for available commands", file=sys.stderr)
            sys.exit(1)
        usage_line = COMMAND_USAGE.get(requested_command, f"tsk {requested_command}")
        print(f"usage: {usage_line}")
        print(f"  {descriptions[requested_command]}")
        command_flags = COMMAND_FLAG_SETS.get(requested_command)
        if command_flags:
            field_to_flags = {}
            for flag_string, field_name in command_flags.items():
                if field_name not in field_to_flags:
                    field_to_flags[field_name] = []
                field_to_flags[field_name].append(flag_string)
            print("flags:")
            for field_name, flag_strings in field_to_flags.items():
                flag_label = ", ".join(flag_strings)
                field_description = FIELD_HELP.get(field_name, field_name)
                print(f"  {flag_label:<22}{field_description}")
        return

    print("available commands:")
    for command_name, description in descriptions.items():
        print(f"  {command_name:<10}{description}")
    print("run 'tsk help <command>' for usage and flags")


def handle_init(arguments: list[str]) -> None:
    """Create the data directory, data files, and docs directory.

    Makes DATA_DIR (with parents) then calls ensure_data_files. Idempotent:
    safe to run on an existing directory. Prints the resolved path so the
    user can confirm it is the intended target (e.g. a mounted drive, not a
    local shadow directory). Reads DATA_DIR; creates directories and files.
    """
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ensure_data_files()
    print(f"initialized: {DATA_DIR}")


# ============================================================================
# CREATION (tsk add)
# ============================================================================

# Entity type is determined by ID prefix (T/G/H/E), not by the type field.
# For events, the type field holds the event subtype (meeting, personal).
# For tasks/goals/habits, the type field matches the entity type by convention.

# All flags accepted for all entity types (field-agnostic philosophy).
# Exception: --date is required for events. No flags are rejected by type.
# Event subtype flag is --label/-y (not --type/-y) to avoid collision with
# entity type selection. --label maps to the type field in the record.
CREATION_FLAGS = {
    "--project": "project",
    "-p": "project",
    "--due": "due",
    "-d": "due",
    "--priority": "priority",
    "-r": "priority",
    "--tags": "tags",
    "-t": "tags",
    "--parent": "parent",
    "-g": "parent",
    "--source": "source",
    "-s": "source",
    "--review": "review",
    "-v": "review",
    "--frequency": "frequency",
    "-f": "frequency",
    "--date": "date",
    "--time": "time",
    "-m": "time",
    "--label": "label",
    "-y": "label",
    "--recur": "recur",
    "--location": "location",
    "-l": "location",
    "--energy": "energy",
    "-e": "energy",
    "--linked": "linked",
    "-k": "linked",
}

ENTITY_TYPES = {"task", "goal", "habit", "event"}

ENTITY_CONFIG = {
    "task": {
        "prefix": "T",
        "file": ACTIVE_FILE,
        "type_field": "task",
        "defaults": {"status": "active"},
        "validations": {
            "priority": validate_priority,
            "due": validate_date_format,
        },
        "usage": "tsk add [task] <summary> [flags]",
    },
    "goal": {
        "prefix": "G",
        "file": ACTIVE_FILE,
        "type_field": "goal",
        "defaults": {"status": "active"},
        "validations": {
            "priority": validate_priority,
            "due": validate_date_format,
            "review": lambda v: v in ("weekly", "monthly", "quarterly"),
        },
        "usage": "tsk add goal <summary> [flags]",
    },
    "habit": {
        "prefix": "H",
        "file": ACTIVE_FILE,
        "type_field": "habit",
        "defaults": {"status": "active", "frequency": "daily"},
        "validations": {
            "frequency": lambda v: v in ("daily", "weekdays", "weekly"),
        },
        "usage": "tsk add habit <summary> [flags]",
    },
    "event": {
        "prefix": "E",
        "file": CALENDAR_FILE,
        "type_field": None,
        "defaults": {},
        "validations": {
            "date": validate_date_format,
        },
        "required": {"date"},
        "usage": "tsk add event <summary> --date YYYY-MM-DD [flags]",
    },
}

VALIDATION_ERRORS = {
    "priority": "error: priority must be 1, 2, or 3",
    "due": "error: due date must be YYYY-MM-DD",
    "date": "error: date must be YYYY-MM-DD",
    "review": "error: review must be weekly, monthly, or quarterly",
    "frequency": "error: frequency must be daily, weekdays, or weekly",
}


def handle_add(arguments: list[str]) -> None:
    """Create a new record (task, goal, habit, or event) in the appropriate file.

    Determines entity type from first positional arg if it matches a known type,
    otherwise defaults to task. Reads all data files for existing IDs to prevent
    reuse. Builds record from summary + flags using ENTITY_CONFIG for per-type
    prefix, target file, defaults, and validations. Validates required fields
    and flag values. Appends to target file, writes file. Prints confirmation
    with new ID and summary to stdout.
    """
    positional_args, flags = parse_flags(arguments, CREATION_FLAGS)

    # Determine entity type from positional subcommand or default to task
    entity_type = "task"
    if positional_args and positional_args[0] in ENTITY_TYPES:
        entity_type = positional_args.pop(0)

    config = ENTITY_CONFIG[entity_type]

    if not positional_args:
        print("error: summary required", file=sys.stderr)
        print(f"usage: {config['usage']}", file=sys.stderr)
        sys.exit(1)

    record_summary = " ".join(positional_args)

    # Whitespace-only summary guard (commit 23 moves this earlier; here for safety)
    if not record_summary.strip():
        print("error: summary required", file=sys.stderr)
        print(f"usage: {config['usage']}", file=sys.stderr)
        sys.exit(1)

    # Validate flag values per entity config
    for field_name, validator in config.get("validations", {}).items():
        if field_name in flags and not validator(flags[field_name]):
            error_message = VALIDATION_ERRORS.get(
                field_name, f"error: invalid value for {field_name}"
            )
            print(error_message, file=sys.stderr)
            sys.exit(1)

    # Check required fields
    for required_field in config.get("required", set()):
        if required_field not in flags:
            print(
                f"error: --{required_field} is required for {entity_type}s",
                file=sys.stderr,
            )
            sys.exit(1)

    # Parse --time HH:MM-HH:MM into start and end (events)
    event_time_start = None
    event_time_end = None
    if "time" in flags:
        time_range = flags["time"]
        if time_range.count("-") != 1:
            print("error: time must be HH:MM-HH:MM (24hr)", file=sys.stderr)
            sys.exit(1)
        start_text, _, end_text = time_range.partition("-")
        start_valid = validate_time_of_day(start_text)
        end_valid = validate_time_of_day(end_text)
        if not (start_valid and end_valid):
            print("error: time must be HH:MM-HH:MM (24hr)", file=sys.stderr)
            sys.exit(1)
        event_time_start = start_text
        event_time_end = end_text

    # Collect IDs from all files to prevent reuse after done/retire moves records out.
    existing_record_ids = (
        [record["id"] for record in parse_file(ACTIVE_FILE) if "id" in record]
        + [record["id"] for record in parse_file(DONE_FILE) if "id" in record]
        + [record["id"] for record in parse_file(CALENDAR_FILE) if "id" in record]
    )

    type_prefix = config["prefix"]
    new_record_id = generate_id(type_prefix, existing_record_ids)
    if new_record_id is None:
        print("error: too many records created today", file=sys.stderr)
        sys.exit(1)

    # Build the new record
    today_date = date.today().isoformat()
    new_record = {
        "id": new_record_id,
        "summary": record_summary,
        "created": today_date,
        "updated": today_date,
    }

    # type field: for events, --label value or default "meeting";
    # for others, the entity type name (task, goal, habit).
    # The type field holds dual semantics: entity type for T/G/H, event subtype for E.
    if config["type_field"] is not None:
        new_record["type"] = config["type_field"]
    else:
        new_record["type"] = flags.pop("label", "meeting")

    # Apply defaults from config (status, frequency, etc.)
    for default_field, default_value in config.get("defaults", {}).items():
        new_record[default_field] = default_value

    # Apply defaults that can be overridden by flags
    if entity_type == "habit" and "frequency" in flags:
        new_record["frequency"] = flags["frequency"]

    # Add time fields if parsed
    if event_time_start is not None:
        new_record["time_start"] = event_time_start
        new_record["time_end"] = event_time_end

    # Add all remaining flag values as record fields.
    # Skip fields already handled (label consumed above, time parsed above,
    # date goes in directly, frequency handled via defaults).
    skip_fields = {"label", "time"}
    for field_name, field_value in flags.items():
        if field_name not in skip_fields and field_name not in new_record:
            new_record[field_name] = field_value

    # Read target file records and append
    target_file = config["file"]
    target_records = parse_file(target_file)
    target_records.append(new_record)
    write_file(target_file, target_records)

    # Confirmation output
    if entity_type == "event":
        event_date = flags.get("date", "")
        print(f"added event: {new_record_id} {record_summary} on {event_date}")
    elif entity_type == "goal":
        print(f"added goal: {new_record_id} {record_summary}")
    elif entity_type == "habit":
        print(f"added habit: {new_record_id} {record_summary}")
    else:
        print(f"added: {new_record_id} {record_summary}")


def validate_time_of_day(time_string: str) -> bool:
    """Check that a time string matches HH:MM in 24-hour format."""
    try:
        datetime.strptime(time_string, "%H:%M")
        return True
    except ValueError:
        return False


def handle_done(arguments: list[str]) -> None:
    """Complete a task/goal, log a habit, or batch-archive past events.

    With --cleanup-events: reads calendar.txt, moves all events with
    date < today to done.txt (status=done, completed=today). Events with
    unparseable dates are skipped with a warning. Prints count and IDs.

    With a T/G ID: reads active.txt, sets status=done and completed=today,
    removes the record, appends it to done.txt, rewrites both files.

    With an H ID: verifies the habit exists in active.txt, checks
    habit_log.txt for a same-day entry, and appends one log line unless
    already logged. Prints a confirmation to stdout.
    """
    if not arguments:
        print("error: ID required", file=sys.stderr)
        print("usage: tsk done <id>", file=sys.stderr)
        sys.exit(1)

    # done --cleanup-events: batch-move past events from calendar.txt to done.txt.
    # done <id> searches active.txt only. Events archived via --cleanup-events,
    # not per-ID. By design: events are batch-archived, not individually completed.
    if arguments[0] == "--cleanup-events":
        today = date.today()
        today_date = today.isoformat()
        calendar_records = parse_file(CALENDAR_FILE)
        done_records = parse_file(DONE_FILE)

        remaining_calendar_records = []
        archived_event_ids = []

        for event_record in calendar_records:
            event_date_value = event_record.get("date")
            if not event_date_value:
                remaining_calendar_records.append(event_record)
                continue
            try:
                event_date = datetime.strptime(event_date_value, "%Y-%m-%d").date()
            except ValueError:
                event_id = event_record.get("id", "???")
                print(
                    f"warning: skipping {event_id}, unparseable date: {event_date_value}",
                    file=sys.stderr,
                )
                remaining_calendar_records.append(event_record)
                continue

            if event_date < today:
                event_record["status"] = "done"
                event_record["completed"] = today_date
                event_record["updated"] = today_date
                done_records.append(event_record)
                archived_event_ids.append(event_record.get("id", "???"))
            else:
                remaining_calendar_records.append(event_record)

        if not archived_event_ids:
            print("no past events to archive")
            return

        write_file(DONE_FILE, done_records)
        write_file(CALENDAR_FILE, remaining_calendar_records)

        archived_count = len(archived_event_ids)
        ids_display = ", ".join(archived_event_ids)
        print(f"archived {archived_count} event(s): {ids_display} -> done.txt")
        return

    search_prefix = arguments[0]

    active_records = parse_file(ACTIVE_FILE)
    matches = find_records_by_prefix(active_records, search_prefix)
    if len(matches) == 0:
        print(f"error: no record found matching: {search_prefix}", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        matching_ids = ", ".join(record["id"] for record in matches)
        print(
            f"error: ambiguous prefix '{search_prefix}', matches: {matching_ids}",
            file=sys.stderr,
        )
        sys.exit(1)
    target_record = matches[0]

    target_id = target_record["id"]
    target_summary = target_record.get("summary", "")
    today_date = date.today().isoformat()

    # habit branch: log a completion, do not move the record
    if target_id.startswith("H"):
        habit_log_entries = parse_habit_log(HABIT_LOG_FILE)
        already_logged_today = False
        for entry_date, entry_habit_id in habit_log_entries:
            if entry_date == today_date and entry_habit_id == target_id:
                already_logged_today = True
        if already_logged_today:
            print(f"already logged: {target_id} for {today_date}")
            sys.exit(0)
        try:
            with open(HABIT_LOG_FILE, "a", encoding="utf-8") as habit_log:
                habit_log.write(f"{today_date} {target_id}\n")
        except OSError:
            print("error: could not write habit_log.txt", file=sys.stderr)
            sys.exit(1)
        print(f"logged: {target_id} {target_summary} for {today_date}")
        return

    # task/goal branch: move the record to done.txt
    target_record["status"] = "done"
    target_record["completed"] = today_date
    target_record["updated"] = today_date

    remaining_active_records = [
        record for record in active_records if record["id"] != target_id
    ]
    done_records = parse_file(DONE_FILE)
    done_records.append(target_record)

    write_file(DONE_FILE, done_records)
    write_file(ACTIVE_FILE, remaining_active_records)
    print(f"completed: {target_id} {target_summary} -> done.txt")


def handle_retire(arguments: list[str]) -> None:
    """Discontinue a task, goal, or habit by moving it to done.txt.

    Reads active.txt, sets status=retired and completed=today on the
    matched record, removes it from active.txt, appends it to done.txt,
    rewrites both files. Prints a confirmation to stdout.
    """
    if not arguments:
        print("error: ID required", file=sys.stderr)
        print("usage: tsk retire <id>", file=sys.stderr)
        sys.exit(1)
    search_prefix = arguments[0]

    active_records = parse_file(ACTIVE_FILE)
    matches = find_records_by_prefix(active_records, search_prefix)
    if len(matches) == 0:
        print(f"error: no record found matching: {search_prefix}", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        matching_ids = ", ".join(record["id"] for record in matches)
        print(
            f"error: ambiguous prefix '{search_prefix}', matches: {matching_ids}",
            file=sys.stderr,
        )
        sys.exit(1)
    target_record = matches[0]

    target_id = target_record["id"]
    target_summary = target_record.get("summary", "")
    today_date = date.today().isoformat()

    target_record["status"] = "retired"
    target_record["completed"] = today_date
    target_record["updated"] = today_date

    remaining_active_records = [
        record for record in active_records if record["id"] != target_id
    ]
    done_records = parse_file(DONE_FILE)
    done_records.append(target_record)

    write_file(DONE_FILE, done_records)
    write_file(ACTIVE_FILE, remaining_active_records)
    print(f"retired: {target_id} {target_summary} -> done.txt")


def handle_edit(arguments: list[str]) -> None:
    """Open a record in $EDITOR and write the edited version back to source.

    Searches active.txt then calendar.txt for a prefix match, tracking the
    source file. Writes the matched record to a temp file, opens it in
    $EDITOR, then parses, validates (single record, ID unchanged), refreshes
    updated=today, and rewrites the source file in place. Removes the temp
    file on success and failure. Prints status to stdout, discards to stderr.
    """
    import tempfile

    if not arguments:
        print("error: ID required", file=sys.stderr)
        print("usage: tsk edit <id>", file=sys.stderr)
        sys.exit(1)
    search_prefix = arguments[0]

    # search active.txt first, then calendar.txt
    source_file_path = ACTIVE_FILE
    source_records = parse_file(ACTIVE_FILE)
    matches = find_records_by_prefix(source_records, search_prefix)
    if len(matches) == 0:
        source_file_path = CALENDAR_FILE
        source_records = parse_file(CALENDAR_FILE)
        matches = find_records_by_prefix(source_records, search_prefix)

    if len(matches) == 0:
        print(f"error: no record found matching: {search_prefix}", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        matching_ids = ", ".join(record["id"] for record in matches)
        print(
            f"error: ambiguous prefix '{search_prefix}', matches: {matching_ids}",
            file=sys.stderr,
        )
        sys.exit(1)
    target_record = matches[0]

    original_id = target_record["id"]
    target_summary = target_record.get("summary", "")
    record_index = source_records.index(target_record)

    # write the record to a temp file for editing
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tmp_file:
        tmp_file.write(format_record(target_record) + "\n")
        tmp_path = tmp_file.name

    try:
        editor_command = os.environ.get("EDITOR", "nvim")
        print(f"editing: {original_id} {target_summary}")
        editor_exit_status = os.system(f"{editor_command} {tmp_path}")
        if editor_exit_status != 0:
            print("edit discarded: editor exited with error", file=sys.stderr)
            sys.exit(1)

        edited_records = parse_file(tmp_path)
        if len(edited_records) != 1:
            print("edit discarded: expected exactly one record", file=sys.stderr)
            sys.exit(1)
        edited_record = edited_records[0]
        if edited_record.get("id") != original_id:
            print("edit discarded: ID cannot be changed", file=sys.stderr)
            sys.exit(1)

        edited_record["updated"] = date.today().isoformat()
        source_records[record_index] = edited_record
        write_file(source_file_path, source_records)
        print(f"updated: {original_id}")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def handle_today(arguments: list[str]) -> None:
    """Print the daily dashboard to stdout.

    Reads active.txt, calendar.txt, and habit_log.txt. Separates active
    records by type, then prints events for today, habit completion state
    with streaks, deadlines within three days, active tasks by priority,
    and goals past their review cadence. Sections with no content are
    skipped. Malformed dates cause a record to be skipped in that section.
    """
    active_records = parse_file(ACTIVE_FILE)
    calendar_records = parse_file(CALENDAR_FILE)
    habit_log_entries = parse_habit_log(HABIT_LOG_FILE)
    today = date.today()
    today_date = today.isoformat()

    task_records = [record for record in active_records if record.get("type") == "task"]
    goal_records = [record for record in active_records if record.get("type") == "goal"]
    habit_records = [
        record for record in active_records if record.get("type") == "habit"
    ]

    # EVENTS -- today's calendar entries, sorted by start time
    today_events = [
        record for record in calendar_records if record.get("date") == today_date
    ]
    today_events = sorted(today_events, key=lambda r: r.get("time_start", "99:99"))
    if today_events:
        print(f"EVENTS -- {today_date}")
        for event_record in today_events:
            event_summary = event_record.get("summary", "")
            event_type = event_record.get("type", "")
            time_start = event_record.get("time_start")
            time_end = event_record.get("time_end")
            if time_start and time_end:
                time_part = f"{time_start}-{time_end}"
            elif time_start:
                time_part = time_start
            else:
                time_part = "--"
            event_line = f"  {time_part}  {event_summary} [{event_type}]"
            if "location" in event_record:
                event_line = event_line + f" @ {event_record['location']}"
            print(event_line)

    # HABITS -- completion state and streak
    if habit_records:
        print("HABITS")
        for habit_record in habit_records:
            habit_id = habit_record.get("id", "")
            habit_summary = habit_record.get("summary", "")
            logged_dates_for_habit = {
                entry_date
                for entry_date, entry_habit_id in habit_log_entries
                if entry_habit_id == habit_id
            }
            completed_today = today_date in logged_dates_for_habit
            # streak: consecutive days backward from today (or yesterday if not yet done)
            streak_count = 0
            cursor_date = today
            if cursor_date.isoformat() not in logged_dates_for_habit:
                cursor_date = cursor_date - timedelta(days=1)
            while cursor_date.isoformat() in logged_dates_for_habit:
                streak_count += 1
                cursor_date = cursor_date - timedelta(days=1)
            checkbox = "(x)" if completed_today else "( )"
            print(f"  {checkbox} {habit_summary} (streak: {streak_count})")

    # DEADLINES -- tasks due today or within three days
    upcoming_deadlines = []
    for task_record in task_records:
        due_value = task_record.get("due")
        if not due_value:
            continue
        try:
            due_date = datetime.strptime(due_value, "%Y-%m-%d").date()
        except ValueError:
            continue
        days_until_due = (due_date - today).days
        if 0 <= days_until_due <= 3:
            upcoming_deadlines.append((days_until_due, task_record))
    upcoming_deadlines = sorted(upcoming_deadlines, key=lambda pair: pair[0])
    if upcoming_deadlines:
        print("DEADLINES")
        for days_until_due, task_record in upcoming_deadlines:
            task_summary = task_record.get("summary", "")
            task_project = task_record.get("project", "--")
            if days_until_due == 0:
                relative_label = "due today:"
            else:
                relative_label = f"due +{days_until_due}d:"
            print(f"  {relative_label}  {task_summary} [{task_project}]")

    # ACTIVE TASKS -- all tasks, priority then due, missing fields last
    if task_records:
        sorted_task_records = sorted(
            task_records,
            key=lambda r: (r.get("priority", "4"), r.get("due", "9999-99-99")),
        )
        print("ACTIVE TASKS")
        for task_record in sorted_task_records:
            task_summary = task_record.get("summary", "")
            task_project = task_record.get("project", "--")
            priority_value = task_record.get("priority")
            priority_label = f"P{priority_value}" if priority_value else "--"
            print(f"  [{priority_label}] {task_summary} [{task_project}]")

    # GOALS -- only those past their review cadence
    cadence_days = {"weekly": 7, "monthly": 30, "quarterly": 90}
    goals_to_review = []
    for goal_record in goal_records:
        review_cadence = goal_record.get("review")
        if review_cadence not in cadence_days:
            continue
        updated_value = goal_record.get("updated")
        if not updated_value:
            continue
        try:
            updated_date = datetime.strptime(updated_value, "%Y-%m-%d").date()
        except ValueError:
            continue
        days_since_update = (today - updated_date).days
        if days_since_update > cadence_days[review_cadence]:
            goals_to_review.append((goal_record, days_since_update, review_cadence))
    if goals_to_review:
        print("GOALS -- review due")
        for goal_record, days_since_update, review_cadence in goals_to_review:
            goal_id = goal_record.get("id", "")
            goal_summary = goal_record.get("summary", "")
            print(
                f"  {goal_id} {goal_summary} (last reviewed: {days_since_update} days ago, cadence: {review_cadence})"
            )


LIST_FLAGS = {
    "--project": "project",
    "-p": "project",
    "--tags": "tags",
    "-t": "tags",
    "--priority": "priority",
    "-r": "priority",
    "--type": "type",
    "-y": "type",
    "--sort": "sort",
}


# --type filter matches entity type by ID prefix (T=task, G=goal, H=habit,
# E=event), not by the type field value. This aligns with the "entity type =
# ID prefix" convention used throughout the codebase.
TYPE_PREFIX_MAP = {
    "task": "T",
    "goal": "G",
    "habit": "H",
    "event": "E",
}

SORT_FIELDS = {"date", "project", "priority"}


def _sort_key_for_record(record: dict, sort_mode: str) -> tuple:
    """Build a sort key tuple for a record based on the active sort mode.

    Returns a tuple that sorts missing values last within each field.
    Used only by handle_list; extracted because sorted() requires a key
    function for genuine comparison-based ordering on runtime data.
    """
    if sort_mode == "date":
        return (
            record.get("due", record.get("date", "9999-99-99")),
            record.get("priority", "4"),
            record.get("created", "9999-99-99"),
        )
    elif sort_mode == "project":
        # Records without project sort after all projects (~ sorts after z)
        return (
            record.get("project", "~~~"),
            record.get("priority", "4"),
            record.get("due", record.get("date", "9999-99-99")),
        )
    else:  # priority (default)
        return (
            record.get("priority", "4"),
            record.get("due", record.get("date", "9999-99-99")),
            record.get("created", "9999-99-99"),
        )


def _format_list_line(record: dict) -> str:
    """Format a single record as a one-line string for list output.

    Goals show review cadence instead of due date. Events show event date.
    All records show ID, priority, summary, and project if present.
    """
    record_id = record.get("id", "")
    record_summary = record.get("summary", "")
    priority_value = record.get("priority")
    priority_label = f"P{priority_value}" if priority_value else "--"
    record_line = f"{record_id} [{priority_label}] {record_summary}"

    if "project" in record:
        record_line = record_line + f" [{record['project']}]"

    if record_id.startswith("G"):
        review_cadence = record.get("review", "--")
        record_line = record_line + f" review:{review_cadence}"
    elif record_id.startswith("E"):
        event_date = record.get("date", "--")
        record_line = record_line + f" date:{event_date}"
    else:
        due_value = record.get("due", "--")
        record_line = record_line + f" due:{due_value}"

    return record_line


def handle_list(arguments: list[str]) -> None:
    """Print a filtered, sorted, type-grouped list of active records and events.

    Reads active.txt and calendar.txt. Applies AND-combined filters from flags
    (project, priority as exact match; tags as substring; type by ID prefix).
    Groups output by entity type: GOALS, TASKS, HABITS, EVENTS. Sorts within
    each group by --sort mode (priority default, date, project). Sections with
    no matching records are skipped. Prints to stdout.
    """
    positional_args, flags = parse_flags(arguments, LIST_FLAGS)

    # Validate --sort if provided
    sort_mode = flags.get("sort", "priority")
    if sort_mode not in SORT_FIELDS:
        print(
            f"error: --sort must be one of: {', '.join(sorted(SORT_FIELDS))}",
            file=sys.stderr,
        )
        sys.exit(1)

    # Read both data sources
    active_records = parse_file(ACTIVE_FILE)
    calendar_records = parse_file(CALENDAR_FILE)
    all_records = active_records + calendar_records

    if not all_records:
        print("no active records")
        return

    # Resolve --type filter to ID prefix
    type_prefix_filter = None
    if "type" in flags:
        type_value = flags["type"]
        if type_value in TYPE_PREFIX_MAP:
            type_prefix_filter = TYPE_PREFIX_MAP[type_value]
        else:
            print(
                f"error: --type must be one of: {', '.join(sorted(TYPE_PREFIX_MAP))}",
                file=sys.stderr,
            )
            sys.exit(1)

    # Apply filters (AND-combined)
    matching_records = []
    for record in all_records:
        keep_record = True
        record_id = record.get("id", "")

        if type_prefix_filter and not record_id.startswith(type_prefix_filter):
            keep_record = False
        if "project" in flags and record.get("project") != flags["project"]:
            keep_record = False
        if "priority" in flags and record.get("priority") != flags["priority"]:
            keep_record = False
        if "tags" in flags and flags["tags"] not in record.get("tags", ""):
            keep_record = False

        if keep_record:
            matching_records.append(record)

    if not matching_records:
        print("no matching records")
        return

    # Group by entity type using ID prefix, in display order
    group_order = [
        ("GOALS", "G"),
        ("TASKS", "T"),
        ("HABITS", "H"),
        ("EVENTS", "E"),
    ]

    any_printed = False
    for group_label, prefix in group_order:
        group_records = [
            record
            for record in matching_records
            if record.get("id", "").startswith(prefix)
        ]
        if not group_records:
            continue

        sorted_group = sorted(
            group_records,
            key=lambda record: _sort_key_for_record(record, sort_mode),
        )

        print(group_label)
        for record in sorted_group:
            print(f"  {_format_list_line(record)}")
        any_printed = True

    if not any_printed:
        print("no matching records")


# ============================================================================
# HELP REGISTRIES
# ============================================================================
# Usage strings and field descriptions for per-command help. Flag names are
# NOT duplicated here -- handle_help reads them from the flag dicts below via
# COMMAND_FLAG_SETS, so the set of flags has a single source of truth.


COMMAND_USAGE = {
    "add": "tsk add [task|goal|habit|event] <summary> [flags]",
    "edit": "tsk edit <id>",
    "done": "tsk done <id>",
    "retire": "tsk retire <id>",
    "today": "tsk today",
    "list": "tsk list [flags]",
    "init": "tsk init",
    "help": "tsk help [command]",
}

COMMAND_FLAG_SETS = {
    "add": CREATION_FLAGS,
    "list": LIST_FLAGS,
}

FIELD_HELP = {
    "date": "event date, YYYY-MM-DD (required)",
    "due": "due date, YYYY-MM-DD",
    "energy": "energy type: deep, admin, social, creative",
    "frequency": "how often: daily (default), weekdays, weekly",
    "label": "event subtype: meeting (default), personal, deadline, block (free-text)",
    "linked": "id of a related record (task <-> event)",
    "location": "where, e.g. an address or meeting link",
    "parent": "id of a parent goal (G-prefix, from a prior tsk goal)",
    "priority": "priority 1 (highest) to 3",
    "project": "project or life area (free-text string, your choice)",
    "recur": "recurrence: daily, weekly, biweekly, monthly (stored, not yet active)",
    "review": "review cadence: weekly, monthly, quarterly",
    "sort": "sort order: priority (default), date, project",
    "source": "where this came from, e.g. journal:2026-05-21, meeting:standup, lw:exp3",
    "tags": 'tags in one quoted string, e.g. "#health #home"',
    "time": "time range, HH:MM-HH:MM (24hr)",
}

# ============================================================================
# DISPATCH
# ============================================================================


COMMANDS = {
    "help": handle_help,
    "init": handle_init,
    "add": handle_add,
    "edit": handle_edit,
    "done": handle_done,
    "retire": handle_retire,
    "today": handle_today,
    "list": handle_list,
    "week": lambda args: handle_not_implemented("week", args),
    "review": lambda args: handle_not_implemented("review", args),
    "stale": lambda args: handle_not_implemented("stale", args),
    "search": lambda args: handle_not_implemented("search", args),
    "tomorrow": lambda args: handle_not_implemented("tomorrow", args),
    "goals": lambda args: handle_not_implemented("goals", args),
}

DEFAULT_COMMAND = "today"

command_name = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_COMMAND
arguments = sys.argv[2:] if len(sys.argv) > 2 else []

if command_name == "--verify-parser":
    verify_parser()
    sys.exit(0)

if command_name.startswith("--"):
    print(f"unknown flag: {command_name}", file=sys.stderr)
    print("run 'tsk help' for available commands", file=sys.stderr)
    sys.exit(1)

if command_name not in COMMANDS:
    print(f"unknown command: {command_name}", file=sys.stderr)
    print("run 'tsk help' for available commands", file=sys.stderr)
    sys.exit(1)

dispatch_start_time = time.time()
dispatch_exit_code = 0
try:
    COMMANDS[command_name](arguments)
except SystemExit as exit_error:
    dispatch_exit_code = exit_error.code
    raise
except Exception:
    dispatch_exit_code = 1
    raise
finally:
    outcome = "ok" if dispatch_exit_code == 0 else "error"
    elapsed_seconds = time.time() - dispatch_start_time
    primary_arg = arguments[0] if arguments else "-"
    log_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    # Peek at entity type for compound logging (add:goal, add:event).
    # Mirrors type detection in handle_add; kept here to maintain
    # dispatch-level logging without handler cooperation.
    logged_command = command_name
    if command_name == "add" and arguments:
        first_arg = arguments[0]
        if first_arg in {"task", "goal", "habit", "event"}:
            logged_command = f"add:{first_arg}"
    log_line = f"{log_timestamp} {logged_command} {primary_arg} {elapsed_seconds:.2f}s {outcome}\n"
    try:
        with open(USAGE_LOG_FILE, "a", encoding="utf-8") as usage_log:
            usage_log.write(log_line)
    except OSError:
        pass
