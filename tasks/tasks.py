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


def parse_flags(arguments: list[str], flag_definitions: dict[str, str]) -> tuple[list[str], dict[str, str]]:
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


ADD_FLAGS = {
    "--project": "project", "-p": "project",
    "--due": "due", "-d": "due",
    "--priority": "priority", "-r": "priority",
    "--tags": "tags", "-t": "tags",
    "--parent": "parent", "-g": "parent",
    "--source": "source", "-s": "source",
}


def handle_add(arguments: list[str]) -> None:
    """Create a new task record in active.txt.

    Reads active.txt for existing IDs, generates next available ID,
    builds record from summary + flags, appends to active.txt, writes file.
    Prints confirmation with new ID and summary to stdout.
    """
    positional_args, flags = parse_flags(arguments, ADD_FLAGS)

    if not positional_args:
        print("error: summary required", file=sys.stderr)
        print("usage: tsk add <summary> [flags]", file=sys.stderr)
        sys.exit(1)
    task_summary = " ".join(positional_args)

    # validate flag values
    if "priority" in flags and not validate_priority(flags["priority"]):
        print("error: priority must be 1, 2, or 3", file=sys.stderr)
        sys.exit(1)
    if "due" in flags and not validate_date_format(flags["due"]):
        print("error: due date must be YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    # read existing records and generate ID
    active_records = parse_file(ACTIVE_FILE)
    existing_record_ids = [record["id"] for record in active_records if "id" in record]
    new_task_id = generate_id("T", existing_record_ids)
    if new_task_id is None:
        print("error: too many records created today", file=sys.stderr)
        sys.exit(1)

    # build the new record
    today_date = date.today().isoformat()
    new_record = {
        "id": new_task_id,
        "type": "task",
        "summary": task_summary,
        "status": "active",
        "created": today_date,
        "updated": today_date,
    }

    # add optional fields from flags
    for field_name in ("project", "priority", "due", "tags", "parent", "source"):
        if field_name in flags:
            new_record[field_name] = flags[field_name]

    active_records.append(new_record)
    write_file(ACTIVE_FILE, active_records)
    print(f"added: {new_task_id} {task_summary}")


GOAL_FLAGS = {
    "--project": "project", "-p": "project",
    "--due": "due", "-d": "due",
    "--priority": "priority", "-r": "priority",
    "--tags": "tags", "-t": "tags",
    "--parent": "parent", "-g": "parent",
    "--source": "source", "-s": "source",
    "--review": "review", "-v": "review",
}


def handle_goal(arguments: list[str]) -> None:
    """Create a new goal record in active.txt.

    Reads active.txt for existing IDs, generates next available G-prefix
    ID, builds record (type=goal) from summary + flags including --review,
    appends to active.txt, writes file. Prints confirmation to stdout.
    """
    positional_args, flags = parse_flags(arguments, GOAL_FLAGS)

    if not positional_args:
        print("error: summary required", file=sys.stderr)
        print("usage: tsk goal <summary> [flags]", file=sys.stderr)
        sys.exit(1)
    goal_summary = " ".join(positional_args)

    # validate flag values
    if "review" in flags and flags["review"] not in ("weekly", "monthly", "quarterly"):
        print("error: review must be weekly, monthly, or quarterly", file=sys.stderr)
        sys.exit(1)
    if "priority" in flags and not validate_priority(flags["priority"]):
        print("error: priority must be 1, 2, or 3", file=sys.stderr)
        sys.exit(1)
    if "due" in flags and not validate_date_format(flags["due"]):
        print("error: due date must be YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    # read existing records and generate ID
    active_records = parse_file(ACTIVE_FILE)
    existing_record_ids = [record["id"] for record in active_records if "id" in record]
    new_goal_id = generate_id("G", existing_record_ids)
    if new_goal_id is None:
        print("error: too many records created today", file=sys.stderr)
        sys.exit(1)

    # build the new record
    today_date = date.today().isoformat()
    new_record = {
        "id": new_goal_id,
        "type": "goal",
        "summary": goal_summary,
        "status": "active",
        "created": today_date,
        "updated": today_date,
    }

    # add optional fields from flags
    for field_name in ("project", "priority", "due", "review", "tags", "parent", "source"):
        if field_name in flags:
            new_record[field_name] = flags[field_name]

    active_records.append(new_record)
    write_file(ACTIVE_FILE, active_records)
    print(f"added goal: {new_goal_id} {goal_summary}")


HABIT_FLAGS = {
    "--frequency": "frequency", "-f": "frequency",
    "--tags": "tags", "-t": "tags",
    "--project": "project", "-p": "project",
}


def handle_habit(arguments: list[str]) -> None:
    """Create a new habit record in active.txt.

    Reads active.txt for existing IDs, generates next available H-prefix
    ID, builds record (type=habit) from summary + restricted flag set,
    defaulting frequency to daily, appends to active.txt, writes file.
    Prints confirmation to stdout.
    """
    positional_args, flags = parse_flags(arguments, HABIT_FLAGS)

    if not positional_args:
        print("error: summary required", file=sys.stderr)
        print("usage: tsk habit <summary> [flags]", file=sys.stderr)
        sys.exit(1)
    habit_summary = " ".join(positional_args)

    # validate flag values
    if "frequency" in flags and flags["frequency"] not in ("daily", "weekdays", "weekly"):
        print("error: frequency must be daily, weekdays, or weekly", file=sys.stderr)
        sys.exit(1)

    # read existing records and generate ID
    active_records = parse_file(ACTIVE_FILE)
    existing_record_ids = [record["id"] for record in active_records if "id" in record]
    new_habit_id = generate_id("H", existing_record_ids)
    if new_habit_id is None:
        print("error: too many records created today", file=sys.stderr)
        sys.exit(1)

    # build the new record
    today_date = date.today().isoformat()
    habit_frequency = flags["frequency"] if "frequency" in flags else "daily"
    new_record = {
        "id": new_habit_id,
        "type": "habit",
        "summary": habit_summary,
        "status": "active",
        "frequency": habit_frequency,
        "created": today_date,
        "updated": today_date,
    }

    # add optional fields from flags
    for field_name in ("tags", "project"):
        if field_name in flags:
            new_record[field_name] = flags[field_name]

    active_records.append(new_record)
    write_file(ACTIVE_FILE, active_records)
    print(f"added habit: {new_habit_id} {habit_summary}")


EVENT_FLAGS = {
    "--date": "date", "-d": "date",
    "--time": "time", "-m": "time",
    "--type": "type", "-y": "type",
    "--recur": "recur", "-r": "recur",
    "--location": "location", "-l": "location",
    "--energy": "energy", "-e": "energy",
    "--project": "project", "-p": "project",
    "--linked": "linked", "-k": "linked",
}


def handle_event(arguments: list[str]) -> None:
    """Create a new event record in calendar.txt.

    Reads calendar.txt for existing IDs, generates next available
    E-prefix ID, requires --date, parses --time HH:MM-HH:MM into
    time_start and time_end, defaults type to meeting, appends to
    calendar.txt, writes file. Prints confirmation to stdout.
    """
    positional_args, flags = parse_flags(arguments, EVENT_FLAGS)

    if not positional_args:
        print("error: summary required", file=sys.stderr)
        print("usage: tsk event <summary> --date YYYY-MM-DD [flags]", file=sys.stderr)
        sys.exit(1)
    event_summary = " ".join(positional_args)

    # --date is required
    if "date" not in flags:
        print("error: --date is required for events", file=sys.stderr)
        sys.exit(1)
    event_date = flags["date"]
    if not validate_date_format(event_date):
        print("error: date must be YYYY-MM-DD", file=sys.stderr)
        sys.exit(1)

    # parse --time HH:MM-HH:MM into start and end
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

    # read existing records and generate ID
    calendar_records = parse_file(CALENDAR_FILE)
    existing_record_ids = [record["id"] for record in calendar_records if "id" in record]
    new_event_id = generate_id("E", existing_record_ids)
    if new_event_id is None:
        print("error: too many records created today", file=sys.stderr)
        sys.exit(1)

    # build the new record; type defaults to meeting (open set, no validation)
    today_date = date.today().isoformat()
    event_type = flags["type"] if "type" in flags else "meeting"
    new_record = {
        "id": new_event_id,
        "type": event_type,
        "summary": event_summary,
        "date": event_date,
        "created": today_date,
        "updated": today_date,
    }
    if event_time_start is not None:
        new_record["time_start"] = event_time_start
        new_record["time_end"] = event_time_end

    # add optional fields from flags
    for field_name in ("recur", "location", "energy", "project", "linked"):
        if field_name in flags:
            new_record[field_name] = flags[field_name]

    calendar_records.append(new_record)
    write_file(CALENDAR_FILE, calendar_records)
    print(f"added event: {new_event_id} {event_summary} on {event_date}")


def validate_time_of_day(time_string: str) -> bool:
    """Check that a time string matches HH:MM in 24-hour format."""
    try:
        datetime.strptime(time_string, "%H:%M")
        return True
    except ValueError:
        return False


def handle_done(arguments: list[str]) -> None:
    """Complete a task/goal or log a habit completion.

    For T/G IDs: reads active.txt, sets status=done and completed=today,
    removes the record, appends it to done.txt, rewrites both files.
    For H IDs: verifies the habit exists in active.txt, checks
    habit_log.txt for a same-day entry, and appends one log line unless
    already logged. Prints a confirmation to stdout.
    """
    if not arguments:
        print("error: ID required", file=sys.stderr)
        print("usage: tsk done <id>", file=sys.stderr)
        sys.exit(1)
    search_prefix = arguments[0]

    active_records = parse_file(ACTIVE_FILE)
    matches = find_records_by_prefix(active_records, search_prefix)
    if len(matches) == 0:
        print(f"error: no record found matching: {search_prefix}", file=sys.stderr)
        sys.exit(1)
    if len(matches) > 1:
        matching_ids = ", ".join(record["id"] for record in matches)
        print(f"error: ambiguous prefix '{search_prefix}', matches: {matching_ids}", file=sys.stderr)
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

    remaining_active_records = [record for record in active_records if record["id"] != target_id]
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
        print(f"error: ambiguous prefix '{search_prefix}', matches: {matching_ids}", file=sys.stderr)
        sys.exit(1)
    target_record = matches[0]

    target_id = target_record["id"]
    target_summary = target_record.get("summary", "")
    today_date = date.today().isoformat()

    target_record["status"] = "retired"
    target_record["completed"] = today_date
    target_record["updated"] = today_date

    remaining_active_records = [record for record in active_records if record["id"] != target_id]
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
        print(f"error: ambiguous prefix '{search_prefix}', matches: {matching_ids}", file=sys.stderr)
        sys.exit(1)
    target_record = matches[0]

    original_id = target_record["id"]
    target_summary = target_record.get("summary", "")
    record_index = source_records.index(target_record)

    # write the record to a temp file for editing
    with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, encoding="utf-8") as tmp_file:
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

# ============================================================================
# DISPATCH
# ============================================================================

COMMANDS = {
    "add":      handle_add,
    "goal":     handle_goal,
    "habit":    handle_habit,
    "event":    handle_event,
    "edit":     handle_edit,
    "done":     handle_done,
    "retire":   handle_retire,
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
    log_line = f"{log_timestamp} {command_name} {primary_arg} {elapsed_seconds:.2f}s {outcome}\n"
    try:
        with open(USAGE_LOG_FILE, "a", encoding="utf-8") as usage_log:
            usage_log.write(log_line)
    except OSError:
        pass
