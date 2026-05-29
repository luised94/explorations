# ============================================================================
# tsk - task, calendar & habit tracker
#
# Usage: uv run tasks.py <command> [args]
# Alias: tsk (defined in tsk.sh)
#
# Code:  ~/personal_repos/explorations/tasks/tasks.py
# Data:  ~/personal_repos/tasks/ (set via TASKS_LOCAL_DIR)
# ============================================================================

import sys
import os
from pathlib import Path
from datetime import date, datetime

# ============================================================================
# PATHS
# ============================================================================

def resolve_data_directory() -> Path:
    """Resolve the data directory from TASKS_LOCAL_DIR or default path.

    Returns the Path if it exists, prints error and exits if not.
    """
    env_path = os.environ.get("TASKS_LOCAL_DIR")
    if env_path:
        data_dir = Path(env_path).expanduser()
    else:
        data_dir = Path.home() / "personal_repos" / "tasks"

    if not data_dir.is_dir():
        print(
            f"error: data directory not found: {data_dir}\n"
            f"set TASKS_LOCAL_DIR or create the directory",
            file=sys.stderr,
        )
        sys.exit(1)

    return data_dir


DATA_DIR = resolve_data_directory()
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
    """Parse CCL-style key=value text into a list of record dicts.

    Handles continuation lines (leading whitespace), blank-line record
    separation, and duplicate keys (collected into lists).
    """
    records = []
    current_record: dict[str, str | list[str]] = {}
    current_key = None

    for raw_line in text.splitlines():
        stripped = raw_line.strip()

        # blank line ends the current record
        if not stripped:
            if current_record:
                records.append(current_record)
                current_record = {}
                current_key = None
            continue

        # continuation line (leading whitespace, and we have an active key)
        if raw_line[0] in (" ", "\t") and current_key is not None:
            continuation = stripped
            val = current_record[current_key]
            if isinstance(val, list):
                val[-1] = val[-1] + "\n" + continuation
            else:
                current_record[current_key] = val + "\n" + continuation if val else continuation
            continue

        # key = value line
        if "=" in raw_line:
            key, _, value = raw_line.partition("=")
            key = key.strip()
            value = value.strip()
            if key in current_record:
                existing = current_record[key]
                if isinstance(existing, list):
                    existing.append(value)
                else:
                    current_record[key] = [existing, value]
            else:
                current_record[key] = value
            current_key = key
            continue

        # line with no = and no leading whitespace - treat as continuation
        # of previous key if one exists, otherwise skip
        if current_key is not None:
            val = current_record[current_key]
            if isinstance(val, list):
                val[-1] = val[-1] + "\n" + stripped
            else:
                current_record[current_key] = val + "\n" + stripped

    # finalize last record
    if current_record:
        records.append(current_record)

    return records


def parse_file(filepath: str | Path) -> list[dict[str, str | list[str]]]:
    """Read a CCL-style file and return a list of record dicts.

    Returns empty list if file is missing or empty.
    """
    path = Path(filepath)
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
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


def _field_sort_key(key: str) -> tuple[int, str]:
    """Return sort key placing known fields in FIELD_ORDER, unknowns after."""
    try:
        return (FIELD_ORDER.index(key), key)
    except ValueError:
        return (len(FIELD_ORDER), key)


def format_record(record: dict[str, str | list[str]]) -> str:
    """Serialize a record dict to CCL-style key=value text.

    Multi-line values get 2-space indented continuation lines.
    List-valued keys are written as repeated key = value lines.
    Fields are ordered per FIELD_ORDER; unknowns go after, alphabetically.
    """
    lines = []
    sorted_keys = sorted(record.keys(), key=_field_sort_key)

    for key in sorted_keys:
        value = record[key]
        if isinstance(value, list):
            for item in value:
                lines.extend(_format_single_value(key, item))
        else:
            lines.extend(_format_single_value(key, value))

    return "\n".join(lines)


def _format_single_value(key: str, value: str) -> list[str]:
    """Format one key=value pair, handling multi-line values."""
    if "\n" in value:
        parts = value.split("\n")
        first = parts[0]
        rest = parts[1:]
        result = [f"{key} = {first}" if first else f"{key} ="]
        for continuation in rest:
            result.append(f"  {continuation}")
        return result
    return [f"{key} = {value}"]


def write_file(filepath: str | Path, records: list[dict[str, str | list[str]]]) -> None:
    """Write a list of record dicts to a CCL-style file.

    Records are separated by blank lines. File ends with trailing newline.
    """
    path = Path(filepath)
    if not records:
        path.write_text("", encoding="utf-8")
        return

    blocks = []
    for record in records:
        if not record:
            continue
        blocks.append(format_record(record))

    path.write_text("\n\n".join(blocks) + "\n", encoding="utf-8")


# ============================================================================
# VERIFICATION
# ============================================================================

def verify_parser() -> None:
    """Run round-trip tests on the parser and writer.

    Semantic round-trip: parse(write(parse(x))) == parse(x).
    Exits 1 on any failure.
    """
    import tempfile

    tests_passed = 0
    tests_failed = 0

    def run_test(name: str, input_text: str) -> None:
        nonlocal tests_passed, tests_failed
        label = f"parser round-trip: {name}"
        try:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as f:
                f.write(input_text)
                tmp_path = f.name

            # first parse
            records_1 = parse_file(tmp_path)
            # write back
            write_file(tmp_path, records_1)
            # second parse
            records_2 = parse_file(tmp_path)

            if records_1 != records_2:
                print(f"{label} {'.' * (42 - len(label))} FAIL", file=sys.stderr)
                print(f"  first parse:  {records_1}", file=sys.stderr)
                print(f"  second parse: {records_2}", file=sys.stderr)
                tests_failed += 1
            else:
                print(f"{label} {'.' * (42 - len(label))} ok")
                tests_passed += 1
        finally:
            os.unlink(tmp_path)

    # --- test cases ---

    run_test("simple record", (
        "id = T0522a\n"
        "type = task\n"
        "summary = test task\n"
    ))

    run_test("multi-line values", (
        "id = T0522a\n"
        "type = task\n"
        "summary = test task\n"
        "notes =\n"
        "  line one of notes\n"
        "  line two of notes\n"
    ))

    run_test("duplicate keys (list)", (
        "id = T0522b\n"
        "type = task\n"
        "summary = test\n"
        "tags = #test\n"
        "tags = #example\n"
    ))

    run_test("empty values", (
        "id = T0522c\n"
        "type = task\n"
        "summary = test\n"
        "notes =\n"
        "  content after empty first line\n"
    ))

    run_test("all entity types", (
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
        "updated = 2026-05-22\n"
    ))

    run_test("multiple records", (
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
        "tags = #b\n"
    ))

    # --- summary ---

    total = tests_passed + tests_failed
    if tests_failed > 0:
        print(f"\n{tests_failed} of {total} tests FAILED", file=sys.stderr)
        sys.exit(1)
    else:
        print(f"all {total} tests passed")


# ============================================================================
# DATA UTILITIES
# ============================================================================


# ============================================================================
# COMMANDS
# ============================================================================

def handle_not_implemented(command_name: str, arguments: list[str]) -> None:
    """Placeholder handler for commands not yet implemented."""
    print(f"not implemented: {command_name}")


def handle_help(arguments: list[str]) -> None:
    """Print available commands with short descriptions."""
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
    for name, desc in descriptions.items():
        print(f"  {name:<10}{desc}")


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

COMMANDS[command_name](arguments)
