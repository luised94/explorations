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
from datetime import date, datetime

# ============================================================================
# PATHS
# ============================================================================

env_path = os.environ.get("TASKS_LOCAL_DIR")
if env_path:
    DATA_DIR = Path(env_path).expanduser()
else:
    DATA_DIR = Path.home() / "personal_repos" / "tasks"

if not DATA_DIR.is_dir():
    print(
        f"error: data directory not found: {DATA_DIR}\n"
        f"set TASKS_LOCAL_DIR or create the directory",
        file=sys.stderr,
    )
    sys.exit(1)

ACTIVE_FILE = DATA_DIR / "active.txt"
CALENDAR_FILE = DATA_DIR / "calendar.txt"
DONE_FILE = DATA_DIR / "done.txt"
HABIT_LOG_FILE = DATA_DIR / "habit_log.txt"
USAGE_LOG_FILE = DATA_DIR / "usage_log.txt"

# Ensure data files exist
for filepath in [ACTIVE_FILE, CALENDAR_FILE, DONE_FILE, HABIT_LOG_FILE, USAGE_LOG_FILE]:
    filepath.touch(exist_ok=True)

# Ensure docs directory exists
(DATA_DIR / "docs").mkdir(exist_ok=True)

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
                    current_record[current_field_name] = existing_content + "\n" + line_content
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
                current_record[current_field_name] = existing_content + "\n" + line_content

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
    "id", "type", "summary", "status",
    "project", "priority", "due", "frequency", "review",
    "date", "time_start", "time_end", "recur", "end_recur",
    "tags", "parent", "source", "linked", "location", "energy",
    "created", "updated", "completed",
    "prep", "notes",
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
    """Write a list of record dicts to a CCL-style file.

    Formats each record via format_record, joins with blank line
    separators, writes to filepath. Empty records list writes empty file.
    """
    file_path = Path(filepath)
    if not records:
        file_path.write_text("", encoding="utf-8")
        return

    formatted_records = []
    for record in records:
        if not record:
            continue
        formatted_records.append(format_record(record))

    file_path.write_text("\n\n".join(formatted_records) + "\n", encoding="utf-8")


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
        ("simple record",
         "id = T0522a\n"
         "type = task\n"
         "summary = test task\n"),

        ("multi-line values",
         "id = T0522a\n"
         "type = task\n"
         "summary = test task\n"
         "notes =\n"
         "  line one of notes\n"
         "  line two of notes\n"),

        ("duplicate keys (list)",
         "id = T0522b\n"
         "type = task\n"
         "summary = test\n"
         "tags = #test\n"
         "tags = #example\n"),

        ("empty values",
         "id = T0522c\n"
         "type = task\n"
         "summary = test\n"
         "notes =\n"
         "  content after empty first line\n"),

        ("all entity types",
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
         "updated = 2026-05-22\n"),

        ("multiple records",
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
         "tags = #b\n"),
    ]

    tests_passed = 0
    tests_failed = 0

    for test_name, input_text in test_cases:
        label = f"parser round-trip: {test_name}"
        tmp_path = None
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp_file:
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


# ============================================================================
# COMMANDS
# ============================================================================

def handle_not_implemented(command_name: str, arguments: list[str]) -> None:
    """Print a not-implemented notice for placeholder commands."""
    print(f"not implemented: {command_name}")


def handle_help(arguments: list[str]) -> None:
    """Print available commands with short descriptions to stdout."""
    descriptions = {
        "add":      "create a new task",
        "goal":     "create a new goal",
        "habit":    "create a new habit",
        "event":    "create a new calendar event",
        "edit":     "edit a record in $EDITOR",
        "done":     "complete a task or log a habit",
        "retire":   "deactivate a habit or goal",
        "today":    "daily dashboard (default)",
        "list":     "list active tasks",
        "week":     "(not implemented)",
        "review":   "(not implemented)",
        "stale":    "(not implemented)",
        "search":   "(not implemented)",
        "tomorrow": "(not implemented)",
        "goals":    "(not implemented)",
        "help":     "show this help",
    }
    print("available commands:")
    for command_name, description in descriptions.items():
        print(f"  {command_name:<10}{description}")


# ============================================================================
# DISPATCH
# ============================================================================

COMMANDS = {
    "add":      lambda args: handle_not_implemented("add", args),
    "goal":     lambda args: handle_not_implemented("goal", args),
    "habit":    lambda args: handle_not_implemented("habit", args),
    "event":    lambda args: handle_not_implemented("event", args),
    "edit":     lambda args: handle_not_implemented("edit", args),
    "done":     lambda args: handle_not_implemented("done", args),
    "retire":   lambda args: handle_not_implemented("retire", args),
    "today":    lambda args: handle_not_implemented("today", args),
    "list":     lambda args: handle_not_implemented("list", args),
    "week":     lambda args: handle_not_implemented("week", args),
    "review":   lambda args: handle_not_implemented("review", args),
    "stale":    lambda args: handle_not_implemented("stale", args),
    "search":   lambda args: handle_not_implemented("search", args),
    "tomorrow": lambda args: handle_not_implemented("tomorrow", args),
    "goals":    lambda args: handle_not_implemented("goals", args),
    "help":     handle_help,
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
try:
    COMMANDS[command_name](arguments)
finally:
    elapsed_seconds = time.time() - dispatch_start_time
    primary_arg = arguments[0] if arguments else "-"
    log_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    log_line = f"{log_timestamp} {command_name} {primary_arg} {elapsed_seconds:.2f}s\n"
    try:
        with open(USAGE_LOG_FILE, "a", encoding="utf-8") as usage_log:
            usage_log.write(log_line)
    except OSError:
        pass
