# ============================================================================
# tsk -- task, calendar & habit tracker
#
# Usage: uv run tasks.py <command> [args]
# Alias: tsk (defined in tsk.sh)
#
# Code:  ~/personal_repos/explorations/tasks/tasks.py
# Data:  ~/personal_repos/tasks/ (set via TASKS_LOCAL_DIR)
#
# ----------------------------------------------------------------------------
# TOPOLOGY (data-oriented refactor, phases 0-2)
#
#   argv parse command name + args        (pure)
#   files load_store? Store                (IO, edge)
#   (Store, args, Clock) transform_*? Effects   (pure: ALL logic)
#   Effects execute_effects? commit + prints + exit code  (IO, edge)
#
#   Store   = {"active": [recs], "calendar": [recs], "done": [recs],
#              "habit_log": [(date_str, habit_id)]}
#   Clock   = {"today": date, "now": datetime}   -- time enters ONCE, in main()
#   Effects = {"store": Store|None, "stdout": [str], "stderr": [str],
#              "exit": int}                      -- a transform's complete answer
#
#   State-of-record rule: the `status` field is the single source of truth.
#   Which file a record lives in is COMPUTED by partition_file(), never
#   remembered. Transforms set status; commit() repartitions. "Moving a
#   record between files" is no longer an operation, only a consequence.
#   (Corollary: hand-moving a record between files without editing its
#   status will be reverted on the next commit. Edit the status field.)
#
#   Pure transforms: add, done, retire, today, list, week.
#   edit is the interactive sandwich: pure prepare / editor IO / pure apply.
#   Shell-native (own IO/print/exit): help, init, not-implemented stubs.
#
#   Transforms may mutate the Store they are given in place and return it
#   as effects["store"]; the shell loads a fresh Store per invocation, so
#   this is confined aliasing, not shared state. effects["store"] = None
#   means "nothing to write".
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

# Version gate must run at import, before any 3.10+ union annotations are
# evaluated. It is the one side effect allowed at module level (it cannot
# corrupt data and protects everything below it).
#   exit 2 = unsupported Python   exit 3 = data dir missing   exit 4 = not writable
if sys.version_info < REQUIRED_PYTHON:
    print(
        f"error: tsk requires Python {REQUIRED_PYTHON[0]}.{REQUIRED_PYTHON[1]}+, "
        f"found {sys.version_info[0]}.{sys.version_info[1]}",
        file=sys.stderr,
    )
    sys.exit(2)

BOOTSTRAP_COMMANDS = ("init",)


def preflight(command_name: str) -> None:
    """Fail fast with distinct exit codes before any logic or file writes.

    Skipped for bootstrap commands whose job is to create the data dir.
    Runs only from main() -- importing this module performs no IO.
    """
    if command_name in BOOTSTRAP_COMMANDS:
        return
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


def ensure_data_files() -> None:
    """Create the data files and docs directory inside DATA_DIR.

    Touches each path in DATA_FILES and makes DOCS_DIR. Assumes DATA_DIR
    already exists; safe to call repeatedly (exist_ok throughout).
    """
    for data_file_path in DATA_FILES:
        data_file_path.touch(exist_ok=True)
    DOCS_DIR.mkdir(exist_ok=True)


# ============================================================================
# PARSER  (pure: text -> records)
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


def parse_habit_log_text(text: str) -> list[tuple[str, str]]:
    """Parse habit log text into a list of (date_string, habit_id) tuples.

    Splits each non-empty line on whitespace into a date and a habit ID.
    Lines that do not split into at least two fields are skipped. Pure.
    """
    log_entries = []
    for raw_line in text.splitlines():
        line_fields = raw_line.split()
        if len(line_fields) >= 2:
            log_entries.append((line_fields[0], line_fields[1]))
    return log_entries


def parse_habit_log(filepath: str | Path) -> list[tuple[str, str]]:
    """Read habit_log.txt and return a list of (date_string, habit_id) tuples.

    Returns empty list if the file is missing or empty.
    """
    file_path = Path(filepath)
    if not file_path.exists():
        return []
    return parse_habit_log_text(file_path.read_text(encoding="utf-8"))


# ============================================================================
# WRITER  (records -> text; one atomic write per file)
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


def write_habit_log(filepath: str | Path, entries: list[tuple[str, str]]) -> None:
    """Write the habit log atomically as date<space>habit_id lines."""
    file_path = Path(filepath)
    file_content = "".join(f"{d} {h}\n" for d, h in entries)
    temp_file_path = file_path.with_name(file_path.name + ".tmp")
    temp_file_path.write_text(file_content, encoding="utf-8")
    temp_file_path.replace(file_path)


# ============================================================================
# STORE  (the entire world as one value; the ONLY data-file IO besides legacy)
# ============================================================================
STORE_BUCKETS = ("active", "calendar", "done")


def data_paths(base_dir: Path) -> dict:
    """Build the path table for a data directory. Pure.

    Paths are configuration, and configuration is an input: load_store and
    commit take this table as a parameter (defaulting to DATA_PATHS) so the
    IO seam itself is testable against a temp directory. The same move we
    made for the clock -- ambient reads become arguments.
    """
    return {
        "active": base_dir / "active.txt",
        "calendar": base_dir / "calendar.txt",
        "done": base_dir / "done.txt",
        "habit_log": base_dir / "habit_log.txt",
    }


DATA_PATHS = data_paths(DATA_DIR)


def load_store(paths: dict = DATA_PATHS) -> dict:
    """Read every data file into one Store value. IO edge: reads only."""
    return {
        "active": parse_file(paths["active"]),
        "calendar": parse_file(paths["calendar"]),
        "done": parse_file(paths["done"]),
        "habit_log": parse_habit_log(paths["habit_log"]),
    }


def flat_records(store: dict) -> list[dict]:
    """All records across buckets as one list. Pure."""
    return store["active"] + store["calendar"] + store["done"]


def partition_file(record: dict) -> str:
    """Which bucket a record belongs in, computed from the record itself.

    status done/retired -> done bucket; E-prefix ids -> calendar; else active.
    Pure. The single answer to "where does this record live" -- file location
    is derived state, never authoritative.
    """
    if record.get("status") in ("done", "retired"):
        return "done"
    if record.get("id", "").startswith("E"):
        return "calendar"
    return "active"


def commit(store: dict, paths: dict = DATA_PATHS) -> None:
    """Repartition the Store by partition_file and write every data file.

    The ONLY function that writes data files in the transform pipeline.
    Write-order policy: done.txt is written FIRST. If the process dies
    mid-commit, a completed record may briefly exist in both its old file
    and done.txt (visible, self-healing on next commit) rather than in
    neither (silent data loss). Each individual write is atomic.
    IO edge: writes only.
    """
    buckets: dict[str, list[dict]] = {name: [] for name in STORE_BUCKETS}
    for record in flat_records(store):
        buckets[partition_file(record)].append(record)
    write_file(paths["done"], buckets["done"])
    write_file(paths["active"], buckets["active"])
    write_file(paths["calendar"], buckets["calendar"])
    write_habit_log(paths["habit_log"], store["habit_log"])


# ============================================================================
# EFFECTS  (a transform's complete answer, as data)
# ============================================================================
def effects_ok(store: dict | None = None, stdout: list[str] | None = None) -> dict:
    """Build a success Effects value. store=None means nothing to write."""
    return {"store": store, "stdout": stdout or [], "stderr": [], "exit": 0}


def effects_fail(*messages: str) -> dict:
    """Build a failure Effects value: stderr lines, exit 1, no writes."""
    return {"store": None, "stdout": [], "stderr": list(messages), "exit": 1}


def resolve_prefix(records: list[dict], search_prefix: str):
    """Resolve an ID prefix against records. Pure; errors are data.

    Returns a tagged tuple:
      ("ok", record)          unique match
      ("not_found",)          no match
      ("ambiguous", [ids])    multiple matches
    Replaces three copy-pasted resolve blocks in done/retire/edit.
    """
    matches = [
        record for record in records if record.get("id", "").startswith(search_prefix)
    ]
    if len(matches) == 0:
        return ("not_found",)
    if len(matches) > 1:
        return ("ambiguous", [record["id"] for record in matches])
    return ("ok", matches[0])


def resolution_error(tag_tuple, search_prefix: str) -> dict:
    """Map a failed resolve_prefix result to failure Effects. Pure."""
    if tag_tuple[0] == "not_found":
        return effects_fail(f"error: no record found matching: {search_prefix}")
    return effects_fail(
        f"error: ambiguous prefix '{search_prefix}', matches: {', '.join(tag_tuple[1])}"
    )


# ============================================================================
# DATA UTILITIES  (pure)
# ============================================================================
def generate_id(
    type_prefix: str, existing_record_ids: list[str], today: date
) -> str | None:
    """Generate the next available ID for a given type prefix and date.

    Reads existing_record_ids to find used suffixes for this prefix + date
    combination. Returns the next available ID in format {prefix}{MMDD}{a-z},
    or None if all 26 suffix letters are exhausted. Pure: the date is a
    parameter, not an ambient read.
    """
    id_stem = type_prefix + today.strftime("%m%d")
    used_suffixes = set()
    for record_id in existing_record_ids:
        if record_id.startswith(id_stem) and len(record_id) == len(id_stem) + 1:
            used_suffixes.add(record_id[-1])
    for suffix_letter in "abcdefghijklmnopqrstuvwxyz":
        if suffix_letter not in used_suffixes:
            return id_stem + suffix_letter
    return None


def parse_flags(arguments: list[str], flag_definitions: dict[str, str]):
    """Split CLI arguments into positionals and flag values. Pure.

    flag_definitions maps flag strings (--project, -p) to canonical field
    names (project). Each flag consumes the next argument as its value.
    Returns a tagged tuple:
      ("ok", positional_args, flags_dict)
      ("error", message)
    Errors are data, not exits: this function sits under transforms, and
    a helper that prints-and-exits makes every caller above it impure.
    """
    positional_args = []
    parsed_flags = {}
    arg_index = 0
    while arg_index < len(arguments):
        arg = arguments[arg_index]
        if arg in flag_definitions:
            canonical_name = flag_definitions[arg]
            if arg_index + 1 >= len(arguments):
                return ("error", f"error: {arg} requires a value")
            parsed_flags[canonical_name] = arguments[arg_index + 1]
            arg_index += 2
        else:
            positional_args.append(arg)
            arg_index += 1
    return ("ok", positional_args, parsed_flags)


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


def validate_time_of_day(time_string: str) -> bool:
    """Check that a time string matches HH:MM in 24-hour format."""
    try:
        datetime.strptime(time_string, "%H:%M")
        return True
    except ValueError:
        return False


def parse_iso_date(date_string: str) -> date | None:
    """Parse YYYY-MM-DD into a date, or None if malformed. Pure."""
    try:
        return datetime.strptime(date_string, "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


# ============================================================================
# FORMATTERS  (pure: record -> display line; shared by today/week/list)
# ============================================================================
def format_event_line(event_record: dict) -> str:
    """One display line for a calendar event: time range, summary, type, location."""
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
    return event_line


def habit_streak(
    habit_id: str, habit_log: list[tuple[str, str]], today: date
) -> tuple[bool, int]:
    """Compute (completed_today, streak_count) for one habit. Pure.

    Streak counts consecutive logged days backward from today, or from
    yesterday if today is not yet logged.
    """
    logged_dates = {
        entry_date for entry_date, entry_id in habit_log if entry_id == habit_id
    }
    completed_today = today.isoformat() in logged_dates
    streak_count = 0
    cursor_date = today
    if cursor_date.isoformat() not in logged_dates:
        cursor_date = cursor_date - timedelta(days=1)
    while cursor_date.isoformat() in logged_dates:
        streak_count += 1
        cursor_date = cursor_date - timedelta(days=1)
    return completed_today, streak_count


# ============================================================================
# PURE TRANSFORMS  (pure: (Store, args, Clock) -> Effects; no IO, no prints,
#                   no exits, no clock reads anywhere below this line)
# ============================================================================
def transform_done(store: dict, arguments: list[str], clock: dict) -> dict:
    """Complete a task/goal, log a habit, or batch-archive past events.

    --cleanup-events: stamps status=done on every calendar event dated
    before today. Repartitioning into done.txt is commit's job, not ours.
    T/G id: stamps status=done, completed, updated. H id: appends one
    habit_log entry unless already logged today. Pure.
    """
    today = clock["today"]
    today_date = today.isoformat()

    if not arguments:
        return effects_fail("error: ID required", "usage: tsk done <id>")

    if arguments[0] == "--cleanup-events":
        archived_event_ids = []
        warnings = []
        for event_record in store["calendar"]:
            event_date_value = event_record.get("date")
            if not event_date_value:
                continue
            event_date = parse_iso_date(event_date_value)
            if event_date is None:
                event_id = event_record.get("id", "???")
                warnings.append(
                    f"warning: skipping {event_id}, unparseable date: {event_date_value}"
                )
                continue
            if event_date < today:
                event_record["status"] = "done"
                event_record["completed"] = today_date
                event_record["updated"] = today_date
                archived_event_ids.append(event_record.get("id", "???"))
        if not archived_event_ids:
            return {
                "store": None,
                "stdout": ["no past events to archive"],
                "stderr": warnings,
                "exit": 0,
            }
        ids_display = ", ".join(archived_event_ids)
        return {
            "store": store,
            "stdout": [
                f"archived {len(archived_event_ids)} event(s): {ids_display} -> done.txt"
            ],
            "stderr": warnings,
            "exit": 0,
        }

    search_prefix = arguments[0]
    # done <id> resolves against active records only. Events are batch-
    # archived via --cleanup-events, not individually completed. By design.
    resolution = resolve_prefix(store["active"], search_prefix)
    if resolution[0] != "ok":
        return resolution_error(resolution, search_prefix)
    target_record = resolution[1]
    target_id = target_record["id"]
    target_summary = target_record.get("summary", "")

    # habit branch: append a log entry, leave the record where it is
    if target_id.startswith("H"):
        for entry_date, entry_habit_id in store["habit_log"]:
            if entry_date == today_date and entry_habit_id == target_id:
                return effects_ok(
                    stdout=[f"already logged: {target_id} for {today_date}"]
                )
        store["habit_log"].append((today_date, target_id))
        return effects_ok(
            store=store,
            stdout=[f"logged: {target_id} {target_summary} for {today_date}"],
        )

    # task/goal branch: stamp status; commit will repartition into done.txt
    target_record["status"] = "done"
    target_record["completed"] = today_date
    target_record["updated"] = today_date
    return effects_ok(
        store=store,
        stdout=[f"completed: {target_id} {target_summary} -> done.txt"],
    )


def transform_retire(store: dict, arguments: list[str], clock: dict) -> dict:
    """Discontinue a task, goal, habit, or event: stamp status=retired.

    Resolves the prefix against active and calendar records together
    (the old active-then-calendar search cascade existed only because
    reads were scattered; with one Store it is a single resolve). Pure.
    """
    if not arguments:
        return effects_fail("error: ID required", "usage: tsk retire <id>")
    search_prefix = arguments[0]
    resolution = resolve_prefix(store["active"] + store["calendar"], search_prefix)
    if resolution[0] != "ok":
        return resolution_error(resolution, search_prefix)
    target_record = resolution[1]
    today_date = clock["today"].isoformat()
    target_record["status"] = "retired"
    target_record["completed"] = today_date
    target_record["updated"] = today_date
    return effects_ok(
        store=store,
        stdout=[
            f"retired: {target_record['id']} {target_record.get('summary', '')} -> done.txt"
        ],
    )


def transform_today(store: dict, arguments: list[str], clock: dict) -> dict:
    """Build the daily dashboard as Effects. Read-only: store is never written.

    Sections: today's events by start time, habit checkboxes with streaks,
    deadlines within three days, active tasks by priority, goals past their
    review cadence, and a past-events cleanup reminder. Sections with no
    content are skipped. Malformed dates skip a record in that section. Pure.
    """
    today = clock["today"]
    today_date = today.isoformat()
    output_lines: list[str] = []

    task_records = [r for r in store["active"] if r.get("type") == "task"]
    goal_records = [r for r in store["active"] if r.get("type") == "goal"]
    habit_records = [r for r in store["active"] if r.get("type") == "habit"]

    # EVENTS -- today's calendar entries, sorted by start time
    today_events = sorted(
        (r for r in store["calendar"] if r.get("date") == today_date),
        key=lambda r: r.get("time_start", "99:99"),
    )
    if today_events:
        output_lines.append(f"EVENTS -- {today_date}")
        for event_record in today_events:
            output_lines.append(format_event_line(event_record))

    # HABITS -- completion state and streak
    if habit_records:
        output_lines.append("HABITS")
        for habit_record in habit_records:
            completed_today, streak_count = habit_streak(
                habit_record.get("id", ""), store["habit_log"], today
            )
            checkbox = "(x)" if completed_today else "( )"
            output_lines.append(
                f"  {checkbox} {habit_record.get('summary', '')} (streak: {streak_count})"
            )

    # DEADLINES -- tasks due today or within three days
    upcoming_deadlines = []
    for task_record in task_records:
        due_date = parse_iso_date(task_record.get("due", ""))
        if due_date is None:
            continue
        days_until_due = (due_date - today).days
        if 0 <= days_until_due <= 3:
            upcoming_deadlines.append((days_until_due, task_record))
    if upcoming_deadlines:
        output_lines.append("DEADLINES")
        for days_until_due, task_record in sorted(
            upcoming_deadlines, key=lambda pair: pair[0]
        ):
            relative_label = (
                "due today:" if days_until_due == 0 else f"due +{days_until_due}d:"
            )
            output_lines.append(
                f"  {relative_label}  {task_record.get('summary', '')} "
                f"[{task_record.get('project', '--')}]"
            )

    # ACTIVE TASKS -- all tasks, priority then due, missing fields last
    if task_records:
        output_lines.append("ACTIVE TASKS")
        for task_record in sorted(
            task_records,
            key=lambda r: (r.get("priority", "4"), r.get("due", "9999-99-99")),
        ):
            priority_value = task_record.get("priority")
            priority_label = f"P{priority_value}" if priority_value else "--"
            output_lines.append(
                f"  [{priority_label}] {task_record.get('summary', '')} "
                f"[{task_record.get('project', '--')}]"
            )

    # GOALS -- only those past their review cadence
    cadence_days = {"weekly": 7, "monthly": 30, "quarterly": 90}
    goals_to_review = []
    for goal_record in goal_records:
        review_cadence = goal_record.get("review")
        if review_cadence not in cadence_days:
            continue
        updated_date = parse_iso_date(goal_record.get("updated", ""))
        if updated_date is None:
            continue
        days_since_update = (today - updated_date).days
        if days_since_update > cadence_days[review_cadence]:
            goals_to_review.append((goal_record, days_since_update, review_cadence))
    if goals_to_review:
        output_lines.append("GOALS -- review due")
        for goal_record, days_since_update, review_cadence in goals_to_review:
            output_lines.append(
                f"  {goal_record.get('id', '')} {goal_record.get('summary', '')} "
                f"(last reviewed: {days_since_update} days ago, cadence: {review_cadence})"
            )

    # Cleanup reminder for past events still in the calendar bucket
    past_event_count = 0
    for calendar_record in store["calendar"]:
        event_date = parse_iso_date(calendar_record.get("date", ""))
        if event_date is not None and event_date < today:
            past_event_count += 1
    if past_event_count > 0:
        output_lines.append(
            f"\n{past_event_count} past event(s) in calendar -- "
            f"run 'tsk done --cleanup-events' to archive"
        )

    return effects_ok(stdout=output_lines)


# ============================================================================
# LEGACY COMMANDS  (Phase 3 targets: own their IO, prints, and exits)
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
    if arguments:
        requested_command = arguments[0]
        if requested_command not in COMMANDS:
            print(f"unknown command: {requested_command}", file=sys.stderr)
            print("run 'tsk help' for available commands", file=sys.stderr)
            sys.exit(1)
        print_command_help(requested_command)
        return
    print("available commands:")
    for command_name, command_entry in COMMANDS.items():
        print(f"  {command_name:<10}{command_entry['description']}")
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
# CREATION (tsk add) -- legacy
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
        "type_field": "task",
        "defaults": {"status": "active"},
        "validations": {
            "priority": validate_priority,
            "due": validate_date_format,
        },
        "usage": "tsk add task <summary> [flags]",
    },
    "goal": {
        "prefix": "G",
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
        "type_field": "habit",
        "defaults": {"status": "active", "frequency": "daily"},
        "validations": {
            "frequency": lambda v: v in ("daily", "weekdays", "weekly"),
        },
        "usage": "tsk add habit <summary> [flags]",
    },
    "event": {
        "prefix": "E",
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


# Confirmation messages as a table, not a four-way if/elif. Adding a fifth
# entity type means adding a row here and in ENTITY_CONFIG -- no logic edits.
ADD_CONFIRMATIONS = {
    "task": "added: {id} {summary}",
    "goal": "added goal: {id} {summary}",
    "habit": "added habit: {id} {summary}",
    "event": "added event: {id} {summary} on {date}",
}
# Fields consumed by special handling in transform_add, never copied
# verbatim into the record.
ADD_HANDLED_FIELDS = {"label", "time"}


def transform_add(store: dict, arguments: list[str], clock: dict) -> dict:
    """Create a new record (task, goal, habit, or event). Pure.

    Entity type is the required first positional. ENTITY_CONFIG supplies
    per-type prefix, defaults, validations, and required fields. The new
    record is appended to the bucket partition_file selects; commit
    repartitions anyway, so the append target is a courtesy to readers,
    not a correctness requirement.
    """
    parse_result = parse_flags(arguments, CREATION_FLAGS)
    if parse_result[0] == "error":
        return effects_fail(parse_result[1])
    _, positional_args, flags = parse_result

    # Entity type is required as first positional argument. Explicit type
    # eliminates ambiguity when a summary starts with a type name (e.g.,
    # "goal setting workshop" no longer silently creates a goal).
    if not positional_args or positional_args[0] not in ENTITY_TYPES:
        return effects_fail(
            "error: entity type required (task, goal, habit, or event)",
            *render_command_help("add"),
        )
    entity_type = positional_args[0]
    config = ENTITY_CONFIG[entity_type]
    record_summary = " ".join(positional_args[1:])
    if not record_summary.strip():
        return effects_fail("error: summary required", *render_command_help("add"))

    # Validate flag values per entity config (errors are data)
    for field_name, validator in config.get("validations", {}).items():
        if field_name in flags and not validator(flags[field_name]):
            return effects_fail(
                VALIDATION_ERRORS.get(
                    field_name, f"error: invalid value for {field_name}"
                )
            )
    for required_field in config.get("required", set()):
        if required_field not in flags:
            return effects_fail(
                f"error: --{required_field} is required for {entity_type}s"
            )

    # Parse --time HH:MM-HH:MM into start and end (events)
    event_time_start = None
    event_time_end = None
    if "time" in flags:
        time_range = flags["time"]
        start_text, dash, end_text = time_range.partition("-")
        if (
            time_range.count("-") != 1
            or not validate_time_of_day(start_text)
            or not validate_time_of_day(end_text)
        ):
            return effects_fail("error: time must be HH:MM-HH:MM (24hr)")
        event_time_start = start_text
        event_time_end = end_text

    today = clock["today"]
    existing_record_ids = [r["id"] for r in flat_records(store) if "id" in r]
    new_record_id = generate_id(config["prefix"], existing_record_ids, today)
    if new_record_id is None:
        return effects_fail("error: too many records created today")

    # Build the new record: identity first, then type, then flags, then
    # defaults for anything still missing -- so flags always override
    # defaults (e.g., --frequency weekdays beats the habit default of daily).
    today_date = today.isoformat()
    new_record = {
        "id": new_record_id,
        "summary": record_summary,
        "created": today_date,
        "updated": today_date,
    }
    # type field: for events, --label value or default "meeting"; for others,
    # the entity type name. The type field holds dual semantics: entity type
    # for T/G/H, event subtype for E. Read, don't pop: mutating the flags
    # dict mid-build creates order-dependence between this block and the
    # copy loop below; ADD_HANDLED_FIELDS makes the exclusion explicit.
    if config["type_field"] is not None:
        new_record["type"] = config["type_field"]
    else:
        new_record["type"] = flags.get("label", "meeting")
    if event_time_start is not None:
        new_record["time_start"] = event_time_start
        new_record["time_end"] = event_time_end
    for field_name, field_value in flags.items():
        if field_name not in ADD_HANDLED_FIELDS:
            new_record[field_name] = field_value
    for default_field, default_value in config.get("defaults", {}).items():
        if default_field not in new_record:
            new_record[default_field] = default_value

    store[partition_file(new_record)].append(new_record)
    confirmation = ADD_CONFIRMATIONS[entity_type].format(
        id=new_record_id, summary=record_summary, date=flags.get("date", "")
    )
    return effects_ok(store=store, stdout=[confirmation])


def transform_edit_prepare(store: dict, arguments: list[str]) -> dict:
    """Resolve which record to edit and serialize it for the editor. Pure.

    Returns ordinary failure Effects on bad input, or success Effects
    carrying an extra "editor" key: {"id": original_id, "text": serialized
    record}. The shell sees that key, runs the (inherently impure) editor
    session, and hands the result to apply_edit. The interactive command
    is a sandwich: pure prepare / IO in the shell / pure apply.
    """
    if not arguments:
        return effects_fail("error: ID required", "usage: tsk edit <id>")
    search_prefix = arguments[0]
    resolution = resolve_prefix(store["active"] + store["calendar"], search_prefix)
    if resolution[0] != "ok":
        return resolution_error(resolution, search_prefix)
    target_record = resolution[1]
    effects = effects_ok(
        stdout=[f"editing: {target_record['id']} {target_record.get('summary', '')}"]
    )
    effects["editor"] = {
        "id": target_record["id"],
        "text": format_record(target_record) + "\n",
    }
    return effects


def apply_edit(store: dict, original_id: str, edited_text: str, clock: dict) -> dict:
    """Validate edited record text and splice it back into the Store. Pure.

    Rules: exactly one record; ID unchanged; updated refreshed to today.
    The record is replaced in whichever bucket holds it; commit repartitions,
    so editing status to done legitimately moves the record to done.txt.
    Every discard rule here is a five-line golden test now -- this logic
    was untestable when it lived between a tempfile and an os.system call.
    """
    edited_records = parse_records(edited_text)
    if len(edited_records) != 1:
        return effects_fail("edit discarded: expected exactly one record")
    edited_record = edited_records[0]
    if edited_record.get("id") != original_id:
        return effects_fail("edit discarded: ID cannot be changed")
    edited_record["updated"] = clock["today"].isoformat()
    for bucket_name in STORE_BUCKETS:
        bucket = store[bucket_name]
        for record_index, record in enumerate(bucket):
            if record.get("id") == original_id:
                bucket[record_index] = edited_record
    return effects_ok(store=store, stdout=[f"updated: {original_id}"])


def run_editor_session(initial_text: str) -> str | None:
    """IO edge: temp file in, $EDITOR, edited text out. None on editor failure.

    Owned by the shell layer. subprocess with an argument list -- no shell
    interpolation, no quoting hazards. The temp file is removed on every path.
    """
    import tempfile
    import subprocess

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tmp_file:
        tmp_file.write(initial_text)
        tmp_path = tmp_file.name
    try:
        editor_command = os.environ.get("EDITOR", "nvim")
        if subprocess.call([editor_command, tmp_path]) != 0:
            return None
        return Path(tmp_path).read_text(encoding="utf-8")
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def transform_week(store: dict, arguments: list[str], clock: dict) -> dict:
    """Build the 7-day forward view of events and task deadlines. Pure.

    Each day: date and weekday header, events sorted by start time, tasks
    due that day sorted by priority. Empty days print a dash placeholder
    to preserve the calendar rhythm. Read-only: store is never written.
    """
    today = clock["today"]
    day_names = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
    output_lines: list[str] = []
    for day_offset in range(7):
        current_date = today + timedelta(days=day_offset)
        current_date_str = current_date.isoformat()
        day_name = day_names[current_date.weekday()]
        day_events = sorted(
            (r for r in store["calendar"] if r.get("date") == current_date_str),
            key=lambda r: r.get("time_start", "99:99"),
        )
        day_tasks = sorted(
            (r for r in store["active"] if r.get("due") == current_date_str),
            key=lambda r: (r.get("priority", "4"), r.get("created", "9999-99-99")),
        )
        suffix = " (today)" if day_offset == 0 else ""
        output_lines.append(f"{day_name} {current_date_str}{suffix}")
        if not (day_events or day_tasks):
            output_lines.append("  --")
            continue
        for event_record in day_events:
            output_lines.append(format_event_line(event_record))
        for task_record in day_tasks:
            priority_value = task_record.get("priority")
            priority_label = f"P{priority_value}" if priority_value else "--"
            task_line = f"  [due] [{priority_label}] {task_record.get('summary', '')}"
            if task_record.get("project"):
                task_line = task_line + f" [{task_record['project']}]"
            output_lines.append(task_line)
    return effects_ok(stdout=output_lines)


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
        record_line = record_line + f" review:{record.get('review', '--')}"
    elif record_id.startswith("E"):
        record_line = record_line + f" date:{record.get('date', '--')}"
    else:
        record_line = record_line + f" due:{record.get('due', '--')}"
    return record_line


def transform_list(store: dict, arguments: list[str], clock: dict) -> dict:
    """Build a filtered, sorted, type-grouped listing of active records. Pure.

    Applies AND-combined filters from flags (project, priority exact;
    tags substring; type by ID prefix). Groups by entity type in display
    order GOALS, TASKS, HABITS, EVENTS; sorts within each group by --sort
    mode (priority default, date, project). Read-only.
    """
    parse_result = parse_flags(arguments, LIST_FLAGS)
    if parse_result[0] == "error":
        return effects_fail(parse_result[1])
    _, positional_args, flags = parse_result
    sort_mode = flags.get("sort", "priority")
    if sort_mode not in SORT_FIELDS:
        return effects_fail(
            f"error: --sort must be one of: {', '.join(sorted(SORT_FIELDS))}"
        )
    all_records = store["active"] + store["calendar"]
    if not all_records:
        return effects_ok(stdout=["no active records"])
    type_prefix_filter = None
    if "type" in flags:
        type_value = flags["type"]
        if type_value not in TYPE_PREFIX_MAP:
            return effects_fail(
                f"error: --type must be one of: {', '.join(sorted(TYPE_PREFIX_MAP))}"
            )
        type_prefix_filter = TYPE_PREFIX_MAP[type_value]
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
        return effects_ok(stdout=["no matching records"])
    group_order = [
        ("GOALS", "G"),
        ("TASKS", "T"),
        ("HABITS", "H"),
        ("EVENTS", "E"),
    ]
    output_lines: list[str] = []
    for group_label, prefix in group_order:
        group_records = [
            r for r in matching_records if r.get("id", "").startswith(prefix)
        ]
        if not group_records:
            continue
        output_lines.append(group_label)
        for record in sorted(
            group_records, key=lambda r: _sort_key_for_record(r, sort_mode)
        ):
            output_lines.append(f"  {_format_list_line(record)}")
    if not output_lines:
        return effects_ok(stdout=["no matching records"])
    return effects_ok(stdout=output_lines)


# ============================================================================
# HELP REGISTRIES
# ============================================================================
# Per-command usage strings, descriptions, and flag dicts live in COMMANDS
# (defined in the SHELL section, after all transforms and handlers exist).
# Field descriptions below are genuinely shared across commands and stay
# separate. Flag names are NOT duplicated here -- help reads them from the
# flag dict referenced by each COMMANDS entry, so the set of flags has a
# single source of truth.
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
# Annotations for which entity types a flag is most relevant to.
# Flags not listed here apply to all types. Displayed in help output.
FLAG_TYPE_ANNOTATIONS = {
    "review": "goal",
    "frequency": "habit",
    "date": "event (required)",
    "time": "event",
    "label": "event",
    "recur": "event",
    "location": "event",
    "energy": "event",
    "linked": "event, task",
}


def render_command_help(command_name: str) -> list[str]:
    """Build usage, description, and annotated flags for one command. Pure.

    Reads usage, description, and the flag dict from the command's COMMANDS
    entry, field descriptions from FIELD_HELP, and type annotations from
    FLAG_TYPE_ANNOTATIONS. Returns display lines so transforms can embed
    help text in Effects; print_command_help is the thin printing wrapper.
    """
    command_entry = COMMANDS.get(command_name, {})
    output_lines = [
        f"usage: {command_entry.get('usage', f'tsk {command_name}')}"
    ]
    output_lines.append(
        f"  {command_entry.get('description', command_name)}"
    )
    command_flags = command_entry.get("flags")
    if not command_flags:
        return output_lines
    field_to_flags = {}
    for flag_string, field_name in command_flags.items():
        if field_name not in field_to_flags:
            field_to_flags[field_name] = []
        field_to_flags[field_name].append(flag_string)
    output_lines.append("flags:")
    for field_name, flag_strings in field_to_flags.items():
        flag_label = ", ".join(flag_strings)
        field_description = FIELD_HELP.get(field_name, field_name)
        type_annotation = FLAG_TYPE_ANNOTATIONS.get(field_name)
        if type_annotation:
            field_description = f"{field_description} ({type_annotation})"
        output_lines.append(f"  {flag_label:<22}{field_description}")
    return output_lines


def print_command_help(command_name: str) -> None:
    """Print render_command_help lines to stdout. Shell-side wrapper."""
    for line in render_command_help(command_name):
        print(line)


# ============================================================================
# VERIFICATION
# ============================================================================
def verify_parser() -> int:
    """Run round-trip tests on the parser and writer.

    Defines test cases as (name, input_text) pairs, runs each through
    parse_file -> write_file -> parse_file and checks semantic equality.
    Prints results to stdout, returns count of failures.
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
        print(f"\n{tests_failed} of {total} parser tests FAILED", file=sys.stderr)
    else:
        print(f"all {total} parser tests passed")

    # Semantic assertions: a round-trip proves parse/write are mutually
    # stable, not that either is RIGHT. A parser that read every line as
    # garbage and a writer that wrote the same garbage would round-trip
    # perfectly. These pin the actual parse rules.
    semantic_failures = 0

    def sem(label: str, condition: bool, detail: str = "") -> None:
        nonlocal semantic_failures
        if condition:
            print(f"parser semantics: {label} {'.' * max(1, 30 - len(label))} ok")
        else:
            print(
                f"parser semantics: {label} {'.' * max(1, 30 - len(label))} FAIL",
                file=sys.stderr,
            )
            if detail:
                print(f"  {detail}", file=sys.stderr)
            semantic_failures += 1

    parsed = parse_records("url = http://x?a=b&c=d\n")
    sem(
        "split on FIRST equals only",
        parsed == [{"url": "http://x?a=b&c=d"}],
        f"got {parsed}",
    )
    parsed = parse_records("notes = first\n\tsecond via tab\n")
    sem(
        "tab continuation joins",
        parsed == [{"notes": "first\nsecond via tab"}],
        f"got {parsed}",
    )
    parsed = parse_records("summary = hello\nworld no equals\n")
    sem(
        "bare line continues previous field",
        parsed == [{"summary": "hello\nworld no equals"}],
        f"got {parsed}",
    )
    parsed = parse_records("id = T1\n\n\n\nid = T2")
    sem(
        "multiple blanks, no trailing newline",
        parsed == [{"id": "T1"}, {"id": "T2"}],
        f"got {parsed}",
    )
    if semantic_failures == 0:
        print("all parser semantic checks passed")
    return tests_failed + semantic_failures


def verify_units() -> int:
    """Unit tests over the pure helpers under the transform layer.

    These are the functions whose bugs would surface as mysterious
    transform failures: ID generation, prefix resolution, flag parsing,
    streak math, partitioning. All pure; all tested with literal values.
    Returns count of failures.
    """
    failures = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"unit: {label} {'.' * max(1, 47 - len(label))} ok")
        else:
            print(
                f"unit: {label} {'.' * max(1, 47 - len(label))} FAIL", file=sys.stderr
            )
            if detail:
                print(f"  {detail}", file=sys.stderr)
            failures += 1

    fixed_day = date(2026, 6, 9)

    # generate_id: skips used suffixes, exhausts at 26, ignores other stems
    check(
        "generate_id picks first free suffix",
        generate_id("T", ["T0609a", "T0609b", "T0608z"], fixed_day) == "T0609c",
    )
    check(
        "generate_id skips holes",
        generate_id("T", ["T0609a", "T0609c"], fixed_day) == "T0609b",
    )
    all_26 = [f"T0609{c}" for c in "abcdefghijklmnopqrstuvwxyz"]
    check("generate_id exhausts at 26", generate_id("T", all_26, fixed_day) is None)
    check(
        "generate_id ignores longer ids sharing the stem",
        generate_id("T", ["T0609ab"], fixed_day) == "T0609a",
    )

    # resolve_prefix: all three tags
    records = [{"id": "T0609a"}, {"id": "T0609b"}, {"id": "G0609a"}]
    check("resolve_prefix unique", resolve_prefix(records, "G")[0] == "ok")
    check("resolve_prefix not_found", resolve_prefix(records, "X")[0] == "not_found")
    ambiguous = resolve_prefix(records, "T")
    check(
        "resolve_prefix ambiguous lists ids",
        ambiguous[0] == "ambiguous" and ambiguous[1] == ["T0609a", "T0609b"],
    )

    # parse_flags: ok and error tags, flag consumes next arg
    result = parse_flags(["task", "buy milk", "-p", "home"], CREATION_FLAGS)
    check(
        "parse_flags splits positionals and flags",
        result == ("ok", ["task", "buy milk"], {"project": "home"}),
        f"got {result}",
    )
    result = parse_flags(["-p"], CREATION_FLAGS)
    check(
        "parse_flags dangling flag is error data",
        result[0] == "error" and "requires a value" in result[1],
    )

    # habit_streak: today counted, gap breaks, empty log
    log = [("2026-06-07", "H1"), ("2026-06-08", "H1"), ("2026-06-09", "H1")]
    check(
        "streak counts through today", habit_streak("H1", log, fixed_day) == (True, 3)
    )
    log = [("2026-06-06", "H1"), ("2026-06-08", "H1")]
    check(
        "streak broken by gap counts back from yesterday",
        habit_streak("H1", log, fixed_day) == (False, 1),
    )
    check("streak on empty log", habit_streak("H1", [], fixed_day) == (False, 0))
    log = [("2026-06-09", "H2")]
    check(
        "streak ignores other habits",
        habit_streak("H1", log, fixed_day) == (False, 0),
    )

    # partition_file: full decision table
    check(
        "partition: retired beats E-prefix",
        partition_file({"id": "E1", "status": "retired"}) == "done",
    )
    check(
        "partition: event",
        partition_file({"id": "E1", "status": "active"}) == "calendar",
    )
    check("partition: default active", partition_file({"id": "T1"}) == "active")

    # parse_iso_date: real, fake, garbage, None
    check("parse_iso_date valid", parse_iso_date("2026-02-28") == date(2026, 2, 28))
    check(
        "parse_iso_date rejects impossible date",
        parse_iso_date("2026-02-30") is None
        and parse_iso_date("nope") is None
        and parse_iso_date(None) is None,
    )

    if failures > 0:
        print(f"\n{failures} unit test(s) FAILED", file=sys.stderr)
    else:
        print("all unit tests passed")
    return failures


def verify_store() -> int:
    """Integration tests of the IO seam: load_store/commit against a temp dir.

    This is the one suite that touches a filesystem, and it exists to test
    exactly the code the pure suites cannot: that commit + load_store are
    mutually faithful, that partitioning self-heals on disk, and that the
    habit log survives the trip. Possible only because paths are a
    parameter -- the suite never goes near the user's real data directory.
    Returns count of failures.
    """
    import tempfile

    failures = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"store: {label} {'.' * max(1, 46 - len(label))} ok")
        else:
            print(
                f"store: {label} {'.' * max(1, 46 - len(label))} FAIL", file=sys.stderr
            )
            if detail:
                print(f"  {detail}", file=sys.stderr)
            failures += 1

    with tempfile.TemporaryDirectory() as temp_dir:
        paths = data_paths(Path(temp_dir))

        # load from nothing: empty store, no crash
        store = load_store(paths)
        check(
            "load on missing files yields empty store",
            store == {"active": [], "calendar": [], "done": [], "habit_log": []},
        )

        # commit -> load round trip with repartitioning
        store = {
            "active": [
                {
                    "id": "T0609a",
                    "type": "task",
                    "summary": "alpha",
                    "status": "active",
                },
                # misplaced on purpose: status says done, bucket says active
                {"id": "T0609b", "type": "task", "summary": "beta", "status": "done"},
            ],
            "calendar": [
                {
                    "id": "E0609a",
                    "type": "meeting",
                    "summary": "sync",
                    "date": "2026-06-09",
                },
            ],
            "done": [],
            "habit_log": [("2026-06-09", "H0609a")],
        }
        commit(store, paths)
        loaded = load_store(paths)
        check(
            "commit repartitions: misplaced record lands in done",
            [r["id"] for r in loaded["done"]] == ["T0609b"]
            and [r["id"] for r in loaded["active"]] == ["T0609a"]
            and [r["id"] for r in loaded["calendar"]] == ["E0609a"],
        )
        check(
            "records survive the trip field-for-field",
            loaded["active"][0] == store["active"][0],
            f"loaded={loaded['active'][0]}",
        )
        check(
            "habit log round-trips", loaded["habit_log"] == [("2026-06-09", "H0609a")]
        )

        # idempotence: committing what was loaded changes nothing
        commit(loaded, paths)
        check("commit is idempotent on its own output", load_store(paths) == loaded)

        # done-path write guarantee (field report 2026-06-01): a task marked
        # done must leave active.txt and land in done.txt, exactly once, in
        # one transform_done -> commit -> load_store trip against real files.
        done_clock = {"today": date(2026, 6, 1), "now": None}
        commit(
            {
                "active": [
                    {
                        "id": "T0601a",
                        "type": "task",
                        "summary": "gamma",
                        "status": "active",
                    },
                ],
                "calendar": [],
                "done": [],
                "habit_log": [],
            },
            paths,
        )
        done_store = load_store(paths)
        done_effects = transform_done(done_store, ["T0601a"], done_clock)
        check(
            "done transform reports success and a store to write",
            done_effects["exit"] == 0 and done_effects["store"] is not None,
        )
        commit(done_effects["store"], paths)
        done_reloaded = load_store(paths)
        active_copies = [
            r for r in done_reloaded["active"] if r.get("id") == "T0601a"
        ]
        done_copies = [r for r in done_reloaded["done"] if r.get("id") == "T0601a"]
        check(
            "done task absent from active after round trip",
            active_copies == [],
            f"still in active: {active_copies}",
        )
        check(
            "done task present exactly once in done with stamps",
            len(done_copies) == 1
            and done_copies[0].get("status") == "done"
            and done_copies[0].get("completed") == "2026-06-01"
            and done_copies[0].get("updated") == "2026-06-01",
            f"done bucket: {done_copies}",
        )

        # no temp droppings left behind
        leftovers = [
            p.name for p in Path(temp_dir).iterdir() if p.name.endswith(".tmp")
        ]
        check(
            "atomic writes leave no .tmp files", leftovers == [], f"found {leftovers}"
        )

        # malformed habit log lines are skipped, not fatal
        paths["habit_log"].write_text(
            "2026-06-09 H0609a\ngarbage\n2026-06-08 H0609a\n", encoding="utf-8"
        )
        check(
            "malformed habit log lines skipped on load",
            load_store(paths)["habit_log"]
            == [("2026-06-09", "H0609a"), ("2026-06-08", "H0609a")],
        )

    if failures > 0:
        print(f"\n{failures} store test(s) FAILED", file=sys.stderr)
    else:
        print("all store tests passed")
    return failures


def verify_transforms() -> int:
    """Golden tests over pure transforms: (store, args, clock) -> effects.

    No filesystem, no real clock -- store fixtures in, effects dicts out,
    plain comparisons. This is the payoff of Effects-as-data: business
    rules (streaks, cleanup boundaries, duplicate guards, partition policy)
    are testable as dict equality. Returns count of failures.
    """
    fixed_clock = {"today": date(2026, 6, 9), "now": datetime(2026, 6, 9, 12, 0, 0)}

    def make_store():
        return {
            "active": [
                {
                    "id": "T0601a",
                    "type": "task",
                    "summary": "ship report",
                    "status": "active",
                    "priority": "1",
                    "due": "2026-06-10",
                },
                {
                    "id": "T0601b",
                    "type": "task",
                    "summary": "other task",
                    "status": "active",
                },
                {
                    "id": "H0601a",
                    "type": "habit",
                    "summary": "morning run",
                    "status": "active",
                    "frequency": "daily",
                },
            ],
            "calendar": [
                {
                    "id": "E0601a",
                    "type": "meeting",
                    "summary": "old standup",
                    "date": "2026-06-08",
                },
                {
                    "id": "E0601b",
                    "type": "meeting",
                    "summary": "today standup",
                    "date": "2026-06-09",
                },
            ],
            "done": [],
            "habit_log": [("2026-06-07", "H0601a"), ("2026-06-08", "H0601a")],
        }

    failures = 0

    def check(label: str, condition: bool, detail: str = "") -> None:
        nonlocal failures
        if condition:
            print(f"transform: {label} {'.' * max(1, 42 - len(label))} ok")
        else:
            print(
                f"transform: {label} {'.' * max(1, 42 - len(label))} FAIL",
                file=sys.stderr,
            )
            if detail:
                print(f"  {detail}", file=sys.stderr)
            failures += 1

    # done on a task: stamps status; partition_file routes it to done bucket
    store = make_store()
    effects = transform_done(store, ["T0601a"], fixed_clock)
    record = store["active"][0]
    check(
        "done task stamps status+dates",
        effects["exit"] == 0
        and record["status"] == "done"
        and record["completed"] == "2026-06-09"
        and effects["store"] is store,
        f"effects={effects}",
    )
    check(
        "done task repartitions to done.txt",
        partition_file(record) == "done",
    )

    # done with ambiguous prefix: error as data, no store mutation
    store = make_store()
    effects = transform_done(store, ["T"], fixed_clock)
    check(
        "done ambiguous prefix -> exit 1, no write",
        effects["exit"] == 1
        and effects["store"] is None
        and "ambiguous" in effects["stderr"][0]
        and store["active"][0].get("status") == "active",
        f"effects={effects}",
    )

    # done on a habit: appends one log entry
    store = make_store()
    effects = transform_done(store, ["H0601a"], fixed_clock)
    check(
        "done habit appends log entry",
        effects["exit"] == 0
        and ("2026-06-09", "H0601a") in store["habit_log"]
        and len(store["habit_log"]) == 3,
        f"habit_log={store['habit_log']}",
    )

    # done on an already-logged habit: success, no second entry, no write
    store = make_store()
    store["habit_log"].append(("2026-06-09", "H0601a"))
    effects = transform_done(store, ["H0601a"], fixed_clock)
    check(
        "done habit duplicate guard",
        effects["exit"] == 0
        and effects["store"] is None
        and store["habit_log"].count(("2026-06-09", "H0601a")) == 1,
        f"effects={effects}",
    )

    # cleanup-events: yesterday archived, today NOT archived (boundary)
    store = make_store()
    effects = transform_done(store, ["--cleanup-events"], fixed_clock)
    old_event, today_event = store["calendar"][0], store["calendar"][1]
    check(
        "cleanup archives past, keeps today",
        effects["exit"] == 0
        and partition_file(old_event) == "done"
        and partition_file(today_event) == "calendar"
        and "E0601a" in effects["stdout"][0]
        and "E0601b" not in effects["stdout"][0],
        f"effects={effects}",
    )

    # retire resolves across active + calendar in one pass
    store = make_store()
    effects = transform_retire(store, ["E0601b"], fixed_clock)
    check(
        "retire reaches calendar records",
        effects["exit"] == 0
        and store["calendar"][1]["status"] == "retired"
        and partition_file(store["calendar"][1]) == "done",
        f"effects={effects}",
    )

    # today: read-only, streak math, cleanup reminder
    store = make_store()
    effects = transform_today(store, [], fixed_clock)
    output_text = "\n".join(effects["stdout"])
    check(
        "today is read-only",
        effects["store"] is None and effects["exit"] == 0,
    )
    check(
        "today streak counts back from yesterday",
        "( ) morning run (streak: 2)" in output_text,
        f"output:\n{output_text}",
    )
    check(
        "today shows deadline within 3 days",
        "due +1d:" in output_text and "ship report" in output_text,
        f"output:\n{output_text}",
    )
    check(
        "today reminds about past events",
        "1 past event(s) in calendar" in output_text,
        f"output:\n{output_text}",
    )

    # commit/partition invariant: a hand-mislabeled record self-heals
    misplaced = {"id": "T0101z", "type": "task", "summary": "x", "status": "done"}
    check(
        "partition_file overrides file location",
        partition_file(misplaced) == "done",
    )

    # --- Phase 3 transforms ---

    # add task: id generated from clock (not wall clock), defaults applied
    store = make_store()
    effects = transform_add(
        store, ["task", "write tests", "--priority", "2"], fixed_clock
    )
    new_task = store["active"][-1]
    check(
        "add task: clock-derived id, defaults, confirmation",
        effects["exit"] == 0
        and new_task["id"] == "T0609a"
        and new_task["status"] == "active"
        and new_task["priority"] == "2"
        and effects["stdout"] == ["added: T0609a write tests"],
        f"record={new_task} effects={effects}",
    )

    # add habit: flag overrides default frequency
    store = make_store()
    transform_add(store, ["habit", "stretch", "-f", "weekdays"], fixed_clock)
    check(
        "add habit: flag beats default",
        store["active"][-1]["frequency"] == "weekdays",
        f"record={store['active'][-1]}",
    )

    # add event without --date: required-field error as data, no append
    store = make_store()
    before_count = len(store["calendar"])
    effects = transform_add(store, ["event", "standup"], fixed_clock)
    check(
        "add event: missing --date is a data error",
        effects["exit"] == 1
        and effects["store"] is None
        and len(store["calendar"]) == before_count,
        f"effects={effects}",
    )

    # add with dangling flag: purified parse_flags error surfaces as effects
    store = make_store()
    effects = transform_add(store, ["task", "x", "--priority"], fixed_clock)
    check(
        "add: dangling flag value is a data error",
        effects["exit"] == 1 and "requires a value" in effects["stderr"][0],
        f"effects={effects}",
    )

    # list: project filter and grouping
    store = make_store()
    effects = transform_list(store, ["-y", "task"], fixed_clock)
    output_text = "\n".join(effects["stdout"])
    check(
        "list: type filter groups tasks only",
        effects["exit"] == 0
        and output_text.startswith("TASKS")
        and "GOALS" not in output_text
        and "ship report" in output_text,
        f"output:\n{output_text}",
    )

    # week: 7 headers, event appears on its day, read-only
    store = make_store()
    effects = transform_week(store, [], fixed_clock)
    headers = [l for l in effects["stdout"] if not l.startswith(" ")]
    check(
        "week: seven day headers, today marked, read-only",
        effects["store"] is None
        and len(headers) == 7
        and headers[0].endswith("(today)")
        and any("today standup" in l for l in effects["stdout"]),
        f"output:\n" + "\n".join(effects["stdout"]),
    )

    # apply_edit: ID change is rejected, store untouched
    store = make_store()
    effects = apply_edit(
        store, "T0601a", "id = T9999z\nsummary = hijacked\n", fixed_clock
    )
    check(
        "apply_edit: ID change rejected",
        effects["exit"] == 1
        and effects["store"] is None
        and store["active"][0]["summary"] == "ship report",
        f"effects={effects}",
    )

    # apply_edit: status edit moves the record via partition, updated refreshed
    store = make_store()
    effects = apply_edit(
        store,
        "T0601a",
        "id = T0601a\ntype = task\nsummary = ship report\nstatus = done\n",
        fixed_clock,
    )
    edited = store["active"][0]
    check(
        "apply_edit: valid edit splices, repartitions on status",
        effects["exit"] == 0
        and edited["updated"] == "2026-06-09"
        and partition_file(edited) == "done",
        f"record={edited} effects={effects}",
    )

    # --- Phase 4 gap coverage ---

    # missing-argument errors across mutating transforms
    store = make_store()
    check(
        "done/retire with no args fail as data",
        transform_done(store, [], fixed_clock)["exit"] == 1
        and transform_retire(store, [], fixed_clock)["exit"] == 1,
    )

    # cleanup-events: malformed date warns to stderr, record stays, others archive
    store = make_store()
    store["calendar"].append(
        {"id": "E0601x", "type": "meeting", "summary": "bad", "date": "not-a-date"}
    )
    effects = transform_done(store, ["--cleanup-events"], fixed_clock)
    bad_event = store["calendar"][2]
    check(
        "cleanup warns on malformed date, keeps record",
        effects["exit"] == 0
        and any("unparseable" in line for line in effects["stderr"])
        and partition_file(bad_event) == "calendar"
        and "E0601a" in effects["stdout"][0],
        f"effects={effects}",
    )

    # add: 26-id exhaustion is a data error, store not grown
    store = make_store()
    store["done"] = [
        {"id": f"T0609{c}", "type": "task", "summary": "x", "status": "done"}
        for c in "abcdefghijklmnopqrstuvwxyz"
    ]
    before = len(store["active"])
    effects = transform_add(store, ["task", "one too many"], fixed_clock)
    check(
        "add: id exhaustion fails cleanly",
        effects["exit"] == 1
        and "too many records" in effects["stderr"][0]
        and len(store["active"]) == before,
        f"effects={effects}",
    )

    # add: invalid --time formats rejected
    store = make_store()
    check(
        "add: malformed --time rejected",
        transform_add(
            store,
            ["event", "x", "--date", "2026-06-10", "--time", "25:00-26:00"],
            fixed_clock,
        )["exit"]
        == 1
        and transform_add(
            store, ["event", "x", "--date", "2026-06-10", "--time", "0900"], fixed_clock
        )["exit"]
        == 1,
    )

    # empty store: views degrade gracefully
    empty = {"active": [], "calendar": [], "done": [], "habit_log": []}
    check(
        "today on empty store is silent success",
        transform_today(empty, [], fixed_clock) == effects_ok(stdout=[]),
    )
    check(
        "list on empty store says so",
        transform_list(empty, [], fixed_clock)["stdout"] == ["no active records"],
    )

    # week shows a due task on its day with priority tag
    store = make_store()
    effects = transform_week(store, [], fixed_clock)
    check(
        "week shows due task with [due] [P1] tag",
        any("[due] [P1] ship report" in line for line in effects["stdout"]),
        "\n".join(effects["stdout"]),
    )

    if failures > 0:
        print(f"\n{failures} transform test(s) FAILED", file=sys.stderr)
    else:
        print("all transform tests passed")
    return failures


# ============================================================================
# SHELL  (the only place that sequences IO, prints Effects, and exits)
# ============================================================================
def handle_edit_sandwich(arguments: list[str]) -> int:
    """Run the one interactive command: pure prepare / editor IO / pure apply.

    Returns the exit code. The only handler that touches the Store; kept as
    a handler (not a transform) because the editor session in the middle is
    irreducibly IO.
    """
    clock = {"today": date.today(), "now": datetime.now()}
    store = load_store()
    prepared = transform_edit_prepare(store, arguments)
    if "editor" not in prepared:
        return execute_effects(prepared)
    for line in prepared["stdout"]:
        print(line)
    edited_text = run_editor_session(prepared["editor"]["text"])
    if edited_text is None:
        print("edit discarded: editor exited with error", file=sys.stderr)
        return 1
    return execute_effects(apply_edit(store, prepared["editor"]["id"], edited_text, clock))


# One entry per command; the single source of truth for dispatch, the
# unknown-command check, the help list, and per-command help. Entry keys:
#   transform    pure (Store, args, Clock) -> Effects, run via the
#                load -> transform -> execute_effects pipeline
#   handler      shell-native (own IO/prints); returns an exit code or None
#   usage        usage line for help output
#   description  one-line description for help output
#   flags        flag dict for per-command help (only where flags exist)
# Exactly one of transform/handler per entry. Dict order is the display
# order of the tsk help command list.
COMMANDS = {
    "help": {
        "handler": handle_help,
        "usage": "tsk help [command]",
        "description": "show this help",
    },
    "init": {
        "handler": handle_init,
        "usage": "tsk init",
        "description": "create the data directory and files",
    },
    "add": {
        "transform": transform_add,
        "usage": "tsk add <task|goal|habit|event> <summary> [flags]",
        "description": "create a new record (task, goal, habit, or event)",
        "flags": CREATION_FLAGS,
    },
    "edit": {
        "handler": handle_edit_sandwich,
        "usage": "tsk edit <id>",
        "description": "edit a record in $EDITOR",
    },
    "done": {
        "transform": transform_done,
        "usage": "tsk done <id>",
        "description": "complete a task or log a habit",
    },
    "retire": {
        "transform": transform_retire,
        "usage": "tsk retire <id>",
        "description": "deactivate a habit or goal",
    },
    "today": {
        "transform": transform_today,
        "usage": "tsk today",
        "description": "daily dashboard (default)",
    },
    "list": {
        "transform": transform_list,
        "usage": "tsk list [flags]",
        "description": "list active records",
        "flags": LIST_FLAGS,
    },
    "week": {
        "transform": transform_week,
        "usage": "tsk week",
        "description": "7-day forward view of events and deadlines",
    },
    "review": {
        "handler": lambda args: handle_not_implemented("review", args),
        "usage": "tsk review",
        "description": "(not implemented)",
    },
    "stale": {
        "handler": lambda args: handle_not_implemented("stale", args),
        "usage": "tsk stale",
        "description": "(not implemented)",
    },
    "search": {
        "handler": lambda args: handle_not_implemented("search", args),
        "usage": "tsk search",
        "description": "(not implemented)",
    },
    "tomorrow": {
        "handler": lambda args: handle_not_implemented("tomorrow", args),
        "usage": "tsk tomorrow",
        "description": "(not implemented)",
    },
    "goals": {
        "handler": lambda args: handle_not_implemented("goals", args),
        "usage": "tsk goals",
        "description": "(not implemented)",
    },
}
DEFAULT_COMMAND = "today"


def execute_effects(effects: dict) -> int:
    """Realize an Effects value: commit writes, print lines, return exit code.

    Deliberately dumb. All decisions were made in the transform; this
    function never needs to change when commands change.
    """
    if effects["store"] is not None:
        commit(effects["store"])
    for line in effects["stdout"]:
        print(line)
    for line in effects["stderr"]:
        print(line, file=sys.stderr)
    return effects["exit"]


def log_usage(logged_command: str, primary_arg: str, elapsed: float, exit_code) -> None:
    """Append one line to the usage log. Failures to log never fail the run."""
    log_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    # SystemExit.code may be None (success) or a string (message); normalize.
    outcome = "ok" if (exit_code == 0 or exit_code is None) else "error"
    log_line = (
        f"{log_timestamp} {logged_command} {primary_arg} {elapsed:.2f}s {outcome}\n"
    )
    try:
        with open(USAGE_LOG_FILE, "a", encoding="utf-8") as usage_log:
            usage_log.write(log_line)
    except OSError:
        pass


def main(argv: list[str]) -> int:
    """Parse argv, run preflight, dispatch, realize effects, log usage.

    The single composition point: this is the only function that knows
    the pipeline order (parse -> load -> transform -> execute) and the
    only place the real clock is read for command logic.
    """
    command_name = argv[1] if len(argv) > 1 else DEFAULT_COMMAND
    arguments = argv[2:] if len(argv) > 2 else []

    # Verification suites, ordered bottom-up: each layer assumes the one
    # below it. parser -> units -> store (the IO seam) -> transforms.
    VERIFY_SUITES = {
        "--verify-parser": (verify_parser,),
        "--verify-units": (verify_units,),
        "--verify-store": (verify_store,),
        "--verify-transforms": (verify_transforms,),
        "--verify": (verify_parser, verify_units, verify_store, verify_transforms),
    }
    if command_name in VERIFY_SUITES:
        total_failures = 0
        for suite in VERIFY_SUITES[command_name]:
            total_failures += suite()
            print()
        if total_failures:
            print(f"VERIFY FAILED: {total_failures} failure(s)", file=sys.stderr)
            return 1
        print("VERIFY OK: all suites passed")
        return 0
    if command_name.startswith("--"):
        print(f"unknown flag: {command_name}", file=sys.stderr)
        print("run 'tsk help' for available commands", file=sys.stderr)
        return 1
    if command_name not in COMMANDS:
        print(f"unknown command: {command_name}", file=sys.stderr)
        print("run 'tsk help' for available commands", file=sys.stderr)
        return 1

    preflight(command_name)
    if DATA_DIR.is_dir():
        ensure_data_files()

    # Compound usage-log labels (add:goal) without argv peeking inside
    # finally blocks: computed here, once, from the same parse the
    # handlers will see.
    logged_command = command_name
    if command_name == "add" and arguments and arguments[0] in ENTITY_TYPES:
        logged_command = f"add:{arguments[0]}"
    primary_arg = arguments[0] if arguments else "-"

    dispatch_start_time = time.time()
    exit_code = 0
    try:
        command_entry = COMMANDS[command_name]
        if "transform" in command_entry:
            # Time enters the program exactly once, here.
            clock = {"today": date.today(), "now": datetime.now()}
            store = load_store()
            effects = command_entry["transform"](store, arguments, clock)
            exit_code = execute_effects(effects)
        else:
            # Shell-native handlers own their IO; a returned int is the
            # exit code, None means 0 (edit returns its sandwich result).
            exit_code = command_entry["handler"](arguments) or 0
    except SystemExit as exit_error:
        exit_code = exit_error.code if exit_error.code is not None else 0
        raise
    except BrokenPipeError:
        # Downstream pipe closed early (tsk week | head). Normal termination,
        # not a data error; mute stderr so the interpreter's flush doesn't whine.
        sys.stderr.close()
        exit_code = 0
        return 0
    except OSError as os_error:
        exit_code = 1
        print(
            f"error: {os_error.strerror} -- your data is safe (atomic writes)",
            file=sys.stderr,
        )
        return 1
    except Exception:
        exit_code = 1
        raise
    finally:
        log_usage(
            logged_command, primary_arg, time.time() - dispatch_start_time, exit_code
        )
    return exit_code


if __name__ == "__main__":
    sys.exit(main(sys.argv))
