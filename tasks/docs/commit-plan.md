# tsk -- Commit Plan v2 (Phase 0)
## Thread Map
```
COMPLETED (commits 01-08):
  Thread A (data layer):    01 -> 02 -> 03 -> 04
  Thread B (identity):      01 -> 05 -> 06
  Thread C (observability): 01 -> 07
  Thread D (exemplar):      08
                            |
REMAINING (commits 09-17):  v
  Thread D (creation):      09, 10 (parallel), 11 (parallel)
  Thread E (lifecycle):     12 -> 13, 14 (parallel to 12)
  Thread F (views):         15, 16 (parallel)
  Thread G (shell):         17 (anytime after 08)
```
---
## Completed Commits (01-08) -- Reference Summary
### What was built
| #  | Summary | Key output |
|----|---------|------------|
| 01 | Scaffold | tasks.py skeleton, dispatch table with placeholders, handle_help, data file creation, DATA_DIR resolution |
| 02 | Parser | parse_records(text), parse_file(filepath) -- CCL key=value into list[dict] |
| 03 | Writer | format_record(record), write_file(filepath, records), FIELD_ORDER constant |
| 04 | Verification | --verify-parser flag, 6 data-driven round-trip test cases |
| 05 | ID generation | generate_id(type_prefix, existing_record_ids) -> str or None |
| 06 | Prefix matching | find_records_by_prefix(records, search_prefix) -> list[dict] |
| 07 | Usage logging | Inline try/finally at dispatch level, silent OSError catch |
| 08 | tsk add (exemplar) | handle_add, parse_flags, validate_priority, validate_date_format, ADD_FLAGS dict |
### Shared functions and signatures
| Function | Signature | Returns | Call sites (phase 0) |
|----------|-----------|---------|---------------------|
| parse_records | (text: str) -> list[dict] | list of record dicts | parse_file |
| parse_file | (filepath: str or Path) -> list[dict] | [] if missing/empty | add, goal, habit, event, done, edit, today, list |
| format_record | (record: dict) -> str | CCL-formatted text block | write_file |
| write_file | (filepath: str or Path, records: list[dict]) -> None | writes file | add, goal, habit, event, done, edit |
| generate_id | (type_prefix: str, existing_record_ids: list[str]) -> str or None | None = exhausted | add, goal, habit, event |
| find_records_by_prefix | (records: list[dict], search_prefix: str) -> list[dict] | 0=miss, 1=match, 2+=ambiguous | done, retire, edit |
| parse_flags | (arguments: list[str], flag_definitions: dict[str,str]) -> tuple[list[str], dict[str,str]] | (positional, flags) | add, goal, habit, event, list |
| validate_priority | (priority_value: str) -> bool | True if 1-3 | add, goal |
| validate_date_format | (date_string: str) -> bool | True if valid YYYY-MM-DD | add, event |
### Established patterns
**Mutation command (handle_add exemplar):**
1. Define FLAG_DICT constant above handler
2. parse_flags(arguments, FLAG_DICT)
3. Validate positional args (summary required)
4. Validate flag values
5. parse_file(target_file) -> existing records
6. Collect IDs: `[r["id"] for r in records if "id" in r]`
7. generate_id(prefix, ids) -> check for None
8. Build record dict: auto fields + flag fields
9. Append record, write_file
10. Print: `"added: {id} {summary}"`
**Error output:** `"error: {description}"` to stderr, then optional `"usage: tsk ..."` line, then sys.exit(1).
**Dispatch wiring:** each handler commit replaces its lambda placeholder with a direct function reference in the COMMANDS dict.
**Prefix match consumption pattern (for commits 12-14):**
```python
matches = find_records_by_prefix(records, search_prefix)
if len(matches) == 0:
    print(f"error: no record found matching: {search_prefix}", file=sys.stderr)
    sys.exit(1)
if len(matches) > 1:
    matching_ids = ", ".join(r["id"] for r in matches)
    print(f"error: ambiguous prefix '{search_prefix}', matches: {matching_ids}", file=sys.stderr)
    sys.exit(1)
target_record = matches[0]
```
### Deviations from original plan (now canonical)
1. Usage logging inlined at dispatch, not extracted as function
2. find_records_by_prefix returns list, caller checks length
3. generate_id returns None on exhaustion, caller checks
4. parse_flags calls sys.exit(1) on missing flag value (pre-state-read, logging still fires)
5. Continuation indentation normalized to 2 spaces, semantic round-trip
6. FIELD_ORDER constant orders output, multi-line fields last
---
## Remaining Commits (09-17)
### COMMIT 09: feat(tsk): implement tsk goal command
LEVEL: haiku
THREAD: D
DEPENDS ON: 08
PURPOSE: Add goal creation, following the handle_add exemplar with type=goal and --review flag.
CONTEXT: Spec section 5.2. Follow handle_add pattern exactly. Goals accept all task flags plus --review. Goals write to active.txt with type=goal, G-prefix IDs.
IMPLEMENTATION OUTLINE:
1. Define GOAL_FLAGS dict above handler: all ADD_FLAGS entries plus `"--review": "review", "-v": "review"`
2. Implement handle_goal(arguments) following the mutation command pattern
3. Type prefix: "G", type value: "goal"
4. Validate --review if present: must be weekly, monthly, or quarterly
5. Validate --priority if present via validate_priority (confirms 2nd caller)
6. Validate --due if present via validate_date_format
7. Confirmation: `"added goal: {id} {summary}"`
8. Wire into COMMANDS dict: `"goal": handle_goal`
INVARIANTS:
- assert: new record has type = goal, id starts with G
- assert: --review value stored in review field
- assert: all add flags work for goals
ERROR HANDLING:
- no summary -> "error: summary required", usage line, exit 1
- invalid review cadence -> "error: review must be weekly, monthly, or quarterly", exit 1
- same priority/due validation as add
STRATEGIC PRINTS:
- success -> "added goal: {id} {summary}" to stdout
VERIFICATION:
```
$ uv run tasks.py goal "kbd v2 with full search" --project kbd --review monthly --priority 1
added goal: G0528a kbd v2 with full search
$ uv run tasks.py goal "bad review" --review biannual
error: review must be weekly, monthly, or quarterly
$ grep "type = goal" ~/personal_repos/tasks/active.txt
type = goal
```
COMMIT MESSAGE:
```
feat(tsk): implement tsk goal command
- follow add exemplar with type=goal and G-prefix IDs
- accept --review flag for weekly/monthly/quarterly cadence
- validate review cadence values
```
---
### COMMIT 10: feat(tsk): implement tsk habit command
LEVEL: haiku
THREAD: D
DEPENDS ON: 08
PURPOSE: Add habit creation with type=habit, --frequency flag, and restricted flag set.
CONTEXT: Spec section 5.3. Habits do not accept --due, --priority, or --parent. Default frequency is daily.
IMPLEMENTATION OUTLINE:
1. Define HABIT_FLAGS dict: only `--frequency/-f`, `--tags/-t`, `--project/-p`
2. Implement handle_habit(arguments) following mutation command pattern
3. Type prefix: "H", type value: "habit"
4. If --frequency provided, validate: must be daily, weekdays, or weekly
5. If --frequency not provided, set frequency = "daily" in record
6. Confirmation: `"added habit: {id} {summary}"`
7. Wire into COMMANDS dict
INVARIANTS:
- assert: new record has type = habit, id starts with H
- assert: frequency field always present (defaults to daily)
- assert: --due, --priority, --parent are not recognized (go to positional args, cause noise in summary -- acceptable, or reject unknown flags)
ERROR HANDLING:
- no summary -> error, exit 1
- invalid frequency -> "error: frequency must be daily, weekdays, or weekly", exit 1
STRATEGIC PRINTS:
- success -> "added habit: {id} {summary}" to stdout
VERIFICATION:
```
$ uv run tasks.py habit "morning exercise" --tags "#health"
added habit: H0528a morning exercise
$ uv run tasks.py habit "read 20 min" --frequency weekdays --project growth
added habit: H0528b read 20 min
$ uv run tasks.py habit "bad freq" --frequency biweekly
error: frequency must be daily, weekdays, or weekly
```
COMMIT MESSAGE:
```
feat(tsk): implement tsk habit command
- follow add exemplar with type=habit and H-prefix IDs
- accept --frequency flag, default to daily
- restricted flag set: no --due, --priority, --parent
```
---
### COMMIT 11: feat(tsk): implement tsk event command
LEVEL: sonnet
THREAD: D
DEPENDS ON: 02, 03, 05, 07
PURPOSE: Add event creation in calendar.txt with required --date, time range parsing, and event-specific flags.
CONTEXT: Spec section 5.4. Events write to calendar.txt (not active.txt). --date is required. --time is a single flag parsed into time_start and time_end. Event type is an open set (no validation). This handler does NOT share a creation helper with add/goal/habit due to different target file, required --date, and time parsing.
IMPLEMENTATION OUTLINE:
1. Define EVENT_FLAGS dict:
   `--date/-d`, `--time/-m`, `--type/-y`, `--recur/-r`, `--location/-l`, `--energy/-e`, `--project/-p`, `--linked/-k`
2. Implement handle_event(arguments) following mutation command pattern but targeting calendar.txt
3. Type prefix: "E"
4. Require --date flag: if missing, error and exit
5. Validate --date via validate_date_format
6. If --time provided, parse "HH:MM-HH:MM" format:
   - Split on "-" into time_start and time_end
   - Validate both are HH:MM (24hr)
   - Store as separate time_start and time_end fields in record
7. --type is stored as-is (open set, no validation per spec)
8. Set default type = "meeting" if --type not provided
9. Read calendar.txt for existing IDs, generate E-prefix ID
10. Build record, append, write calendar.txt
11. Confirmation: `"added event: {id} {summary} on {date}"`
12. Wire into COMMANDS dict
INVARIANTS:
- assert: event written to calendar.txt, not active.txt
- assert: --date is required, error if missing
- assert: --time "14:00-15:30" becomes time_start = 14:00, time_end = 15:30
- assert: --type stores any value without validation
- assert: default type is meeting when --type not provided
ERROR HANDLING:
- no summary -> error, exit 1
- no --date -> "error: --date is required for events", exit 1
- invalid date format -> "error: date must be YYYY-MM-DD", exit 1
- invalid time format -> "error: time must be HH:MM-HH:MM (24hr)", exit 1
STRATEGIC PRINTS:
- success -> "added event: {id} {summary} on {date}" to stdout
VERIFICATION:
```
$ uv run tasks.py event "team standup" --date 2026-05-29 --time 14:00-15:30 --type meeting --project work
added event: E0528a team standup on 2026-05-29
$ cat ~/personal_repos/tasks/calendar.txt
id = E0528a
type = meeting
summary = team standup
date = 2026-05-29
time_start = 14:00
time_end = 15:30
project = work
created = 2026-05-28
updated = 2026-05-28
$ uv run tasks.py event "no date event"
error: --date is required for events
$ uv run tasks.py event "bad time" --date 2026-05-29 --time 2pm-3pm
error: time must be HH:MM-HH:MM (24hr)
```
COMMIT MESSAGE:
```
feat(tsk): implement tsk event command
- create events in calendar.txt with E-prefix IDs
- require --date flag, validate YYYY-MM-DD format
- parse --time HH:MM-HH:MM into time_start and time_end fields
- event type is open set, defaults to meeting
```
---
### COMMIT 12: feat(tsk): implement tsk done command
LEVEL: sonnet
THREAD: E
DEPENDS ON: 02, 03, 06, 07
PURPOSE: Implement completion with branching behavior: tasks/goals move to done.txt, habits log to habit_log.txt.
CONTEXT: Spec section 5.6. Uses find_records_by_prefix (prefix match consumption pattern from handoff). Introduces parse_habit_log as a shared function (also called by handle_today in commit 15 -- 2 callers, extraction justified).
IMPLEMENTATION OUTLINE:
1. Implement parse_habit_log(filepath) -> list[tuple[str, str]]
   - Read file as text lines
   - Split each non-empty line on whitespace into (date_string, habit_id)
   - Return list of (date_string, habit_id) tuples
   - Missing or empty file -> return []
2. Implement handle_done(arguments):
   - Require one positional arg (ID or prefix)
   - Detect entity type from first character of resolved ID (T/G vs H)
   - **For T or G (task/goal completion):**
     a. Read active.txt, apply prefix match consumption pattern
     b. Set status = "done", completed = today
     c. Remove matched record from active_records list
     d. Read done.txt, append completed record
     e. Write both active.txt and done.txt
     f. Print: "completed: {id} {summary} -> done.txt"
   - **For H (habit logging):**
     a. Read active.txt, verify habit exists via prefix match
     b. Parse habit_log.txt via parse_habit_log
     c. Check for duplicate: any entry with today's date + this habit_id
     d. If duplicate: print "already logged: {id} for {today}", exit 0
     e. Append one line "YYYY-MM-DD {habit_id}\n" to habit_log.txt
     f. Print: "logged: {id} {summary} for {today}"
3. Wire into COMMANDS dict
INVARIANTS:
- assert: after task done, record in done.txt with status=done and completed date
- assert: after task done, record removed from active.txt
- assert: after habit done, habit still in active.txt
- assert: after habit done, one new line in habit_log.txt
- assert: duplicate habit done on same day prints notice, does not add line
- assert: parse_habit_log on empty file returns []
ERROR HANDLING:
- no ID argument -> "error: ID required", "usage: tsk done <id>", exit 1
- ID not found -> "error: no record found matching: {prefix}", exit 1
- ambiguous prefix -> "error: ambiguous prefix ..., matches: ...", exit 1
STRATEGIC PRINTS:
- task/goal done -> "completed: {id} {summary} -> done.txt" to stdout
- habit logged -> "logged: {id} {summary} for {today}" to stdout
- habit duplicate -> "already logged: {id} for {today}" to stdout
VERIFICATION:
```
$ uv run tasks.py add "test completion" --project test
added: T0528a test completion
$ uv run tasks.py done T0528a
completed: T0528a test completion -> done.txt
$ grep "status = done" ~/personal_repos/tasks/done.txt
status = done
$ grep "T0528a" ~/personal_repos/tasks/active.txt
(no output -- record moved)
$ uv run tasks.py habit "test habit"
added habit: H0528a test habit
$ uv run tasks.py done H0528a
logged: H0528a test habit for 2026-05-28
$ uv run tasks.py done H0528a
already logged: H0528a for 2026-05-28
$ cat ~/personal_repos/tasks/habit_log.txt
2026-05-28 H0528a
```
COMMIT MESSAGE:
```
feat(tsk): implement tsk done command
- branch on ID prefix: T/G moves to done.txt, H logs to habit_log.txt
- introduce parse_habit_log shared with handle_today
- set status=done and completed date on task/goal completion
- prevent duplicate habit logging for same day
```
---
### COMMIT 13: feat(tsk): implement tsk retire command
LEVEL: haiku
THREAD: E
DEPENDS ON: 12
PURPOSE: Add retire command for discontinuing any entity with status=retired.
CONTEXT: Spec section 5.7. Same move-to-done mechanics as handle_done for T/G, but sets status=retired. Works for any entity type (T, G, H). For habits, retire moves the record out of active.txt (unlike done which only logs).
IMPLEMENTATION OUTLINE:
1. Implement handle_retire(arguments):
   - Require one positional arg (ID or prefix)
   - Read active.txt, apply prefix match consumption pattern
   - Set status = "retired", completed = today
   - Remove from active_records
   - Read done.txt, append retired record
   - Write both files
   - Print: "retired: {id} {summary} -> done.txt"
2. Wire into COMMANDS dict
INVARIANTS:
- assert: retired record in done.txt has status = retired (not done)
- assert: retired record has completed date
- assert: record removed from active.txt regardless of type
ERROR HANDLING:
- same as done: no ID, not found, ambiguous
STRATEGIC PRINTS:
- success -> "retired: {id} {summary} -> done.txt" to stdout
VERIFICATION:
```
$ uv run tasks.py habit "temporary habit"
added habit: H0528b temporary habit
$ uv run tasks.py retire H0528b
retired: H0528b temporary habit -> done.txt
$ grep "status = retired" ~/personal_repos/tasks/done.txt
status = retired
```
COMMIT MESSAGE:
```
feat(tsk): implement tsk retire command
- move record to done.txt with status=retired
- works for any entity type (task, goal, habit)
- semantic distinction from done (discontinued vs completed)
```
---
### COMMIT 14: feat(tsk): implement tsk edit command
LEVEL: sonnet
THREAD: E
DEPENDS ON: 02, 03, 06, 07
PURPOSE: Implement speed-2 editing via $EDITOR for detailed record modification.
CONTEXT: Spec section 5.5. Searches active.txt then calendar.txt. Must track which file the match came from to write back correctly. Uses temp file for editor interaction.
IMPLEMENTATION OUTLINE:
1. Implement handle_edit(arguments):
   - Require one positional arg (ID or prefix)
   - Search active.txt first:
     a. active_records = parse_file(ACTIVE_FILE)
     b. active_matches = find_records_by_prefix(active_records, search_prefix)
   - If no active match, search calendar.txt:
     a. calendar_records = parse_file(CALENDAR_FILE)
     b. calendar_matches = find_records_by_prefix(calendar_records, search_prefix)
   - If still no match -> error, exit 1
   - If ambiguous (combined matches > 1) -> error with all matching IDs, exit 1
   - Track source: source_file_path, source_records, record_index in list
   - Format matched record to temp file via format_record
   - Determine editor: os.environ.get("EDITOR", "nvim")
   - Print: "editing: {id} {summary}"
   - Run editor via os.system(f"{editor} {tmp_path}")
     - If editor returns non-zero -> "edit discarded: editor exited with error", exit 1
   - Parse temp file: edited_records = parse_file(tmp_path)
   - Validate:
     - Exactly one record in parsed result
     - ID field unchanged from original
     - If validation fails -> "edit discarded: {reason}", exit 1
   - Set updated = today on edited record
   - Replace record at record_index in source_records
   - write_file(source_file_path, source_records)
   - Print: "updated: {id}"
   - Clean up temp file in finally block
2. Wire into COMMANDS dict
INVARIANTS:
- assert: after edit, record count in source file unchanged
- assert: after edit, updated field is today
- assert: ID cannot be changed via edit
- assert: temp file cleaned up on success and failure
- assert: editor failure discards changes
ERROR HANDLING:
- no ID argument -> error, exit 1
- ID not found in either file -> "error: no record found matching: {prefix}", exit 1
- ambiguous across both files -> error with all matches, exit 1
- editor non-zero exit -> "edit discarded: editor exited with error", exit 1
- ID changed in editor -> "edit discarded: ID cannot be changed", exit 1
- parse failure on edited file -> "edit discarded: could not parse edited record", exit 1
STRATEGIC PRINTS:
- before editor -> "editing: {id} {summary}" to stdout
- after success -> "updated: {id}" to stdout
- on discard -> "edit discarded: {reason}" to stderr
VERIFICATION:
```
$ uv run tasks.py add "editable task" --project test
added: T0528a editable task
$ uv run tasks.py edit T0528a
editing: T0528a editable task
(editor opens, make a change, save, quit)
updated: T0528a
$ uv run tasks.py edit nonexistent
error: no record found matching: nonexistent
```
COMMIT MESSAGE:
```
feat(tsk): implement tsk edit command
- open record in $EDITOR for detailed modification
- search active.txt then calendar.txt
- validate ID unchanged, auto-update timestamp
- clean up temp file on success and failure
```
---
### COMMIT 15: feat(tsk): implement tsk today command
LEVEL: sonnet
THREAD: F
DEPENDS ON: 02, 07
PURPOSE: Implement the daily dashboard as the exemplar view command. All filtering, calculation, and formatting logic is inline in handle_today -- no single-caller helper functions extracted.
CONTEXT: Spec sections 5.8 and 6. Reads active.txt, calendar.txt, habit_log.txt. Uses parse_habit_log (from commit 12, 2 callers). All other logic is one irreducible top-to-bottom sequence: read data, separate by type, filter, compute, format, print. Each section only prints if it has content.
IMPLEMENTATION OUTLINE:
1. Implement handle_today(arguments) as one top-to-bottom function:
   - **Read phase:**
     a. active_records = parse_file(ACTIVE_FILE)
     b. calendar_records = parse_file(CALENDAR_FILE)
     c. habit_log_entries = parse_habit_log(HABIT_LOG_FILE)
     d. today_date = date.today().isoformat()
   - **Separate by type:**
     a. Walk active_records, separate into task_records, goal_records, habit_records by type field
   - **Events section:**
     a. Filter calendar_records where date == today_date
     b. Sort by time_start (records without time_start sort last)
     c. If any: print "EVENTS -- {today_date}" header, then each event formatted as "  {time_start}-{time_end}  {summary} [{type}]" with optional "@ {location}"
   - **Habits section:**
     a. For each habit_record, check if today_date + habit_id appears in habit_log_entries
     b. Calculate streak: count consecutive days backward from today (or yesterday) where habit_id appears in log
     c. If any habits: print "HABITS" header, then each as "  (x) {summary} (streak: N)" or "  ( ) {summary} (streak: N)"
   - **Deadlines section:**
     a. Filter task_records where due field exists and due date is today or within 3 days
     b. Sort by due date ascending
     c. Format relative: "due today:", "due +1d:", "due +2d:", "due +3d:"
     d. If any: print "DEADLINES" header, then each as "  {relative}  {summary} [{project}]"
   - **Active tasks section:**
     a. All task_records (not goals, not habits)
     b. Sort by priority ascending (missing priority after P3), then due date ascending (missing due last)
     c. If any: print "ACTIVE TASKS" header, then each as "  [P{priority}] {summary} [{project}]" or "  [--] {summary} [{project}]"
   - **Goals review section:**
     a. Filter goal_records where review cadence is set and updated date exceeds cadence
     b. Calculate days since last update
     c. If any: print "GOALS -- review due" header, then each as "  {id} {summary} (last reviewed: {N} days ago, cadence: {review})"
2. Wire into COMMANDS dict (replaces "today" placeholder -- this is the default command)
INVARIANTS:
- assert: empty files produce no output (no empty section headers)
- assert: events sorted by time_start
- assert: tasks sorted by priority then due, missing fields sort last
- assert: habit (x) vs ( ) reflects today's log entries
- assert: streak counts consecutive days backward
- assert: deadlines only show tasks due within 3 days
- assert: goals section only shows goals past review cadence
ERROR HANDLING:
- missing fields on records (no time_start, no priority, no project) -> display with defaults ("--" for missing priority, no location line, etc.), never crash
- malformed dates in due or updated fields -> skip record in relevant section
- all errors are display-graceful, not fatal
STRATEGIC PRINTS:
- the formatted dashboard IS the output
VERIFICATION:
```
$ uv run tasks.py event "standup" --date 2026-05-28 --time 14:00-15:30 --type meeting
$ uv run tasks.py add "urgent thing" --priority 1 --due 2026-05-28
$ uv run tasks.py add "less urgent" --priority 2 --project work
$ uv run tasks.py habit "morning exercise"
$ uv run tasks.py done H0528a
$ uv run tasks.py today
EVENTS -- 2026-05-28
  14:00-15:30  standup [meeting]
HABITS
  (x) morning exercise (streak: 1)
DEADLINES
  due today:  urgent thing
ACTIVE TASKS
  [P2] less urgent [work]
$ uv run tasks.py
(same output -- today is the default command)
```
COMMIT MESSAGE:
```
feat(tsk): implement tsk today command
- daily dashboard: events, habits, deadlines, active tasks, goal reviews
- all logic inline as one top-to-bottom sequence
- skip empty sections, sort by priority and date
- resilient to missing fields and malformed dates
```
---
### COMMIT 16: feat(tsk): implement tsk list command
LEVEL: haiku
THREAD: F
DEPENDS ON: 02, 07
PURPOSE: Show filtered, sorted list of all active records.
CONTEXT: Spec section 5.9. Uses parse_flags for filter flags. Sort defaults: missing priority sorts after P3, missing due sorts after all dated records.
IMPLEMENTATION OUTLINE:
1. Define LIST_FLAGS dict: `--project/-p`, `--tags/-t`, `--priority/-r`, `--type/-y`
2. Implement handle_list(arguments):
   - parse_flags(arguments, LIST_FLAGS) -- no positional args expected
   - Read active.txt
   - Filter: for each flag present, keep only records where that field matches
     - --tags filter: check if filter value appears in record's tags string (substring match for #tag)
     - filters are AND-combined
   - Sort: by priority ascending (missing = 4, sorts after P3), then due ascending (missing = "9999-99-99", sorts last), then created ascending
   - Format one line per record: `"{id} [{priority}] {summary} [{project}] due:{due}"`
     - priority missing -> "[--]"
     - project missing -> omit bracket section
     - due missing -> "due:--"
     - For goals: show "review:{cadence}" instead of "due:{due}"
   - If no records match -> "no matching records"
3. Wire into COMMANDS dict
INVARIANTS:
- assert: no flags shows all active records
- assert: --project filters to exact project match
- assert: --type habit shows only habits
- assert: records without priority sort after P3
- assert: records without due sort after dated records
ERROR HANDLING:
- no matching records -> "no matching records" to stdout (not an error)
- active.txt empty -> "no active records" to stdout
STRATEGIC PRINTS:
- the list IS the output
VERIFICATION:
```
$ uv run tasks.py list
T0528a [P1] urgent thing due:2026-05-28
T0528b [P2] less urgent [work] due:--
H0528a [--] morning exercise due:--
$ uv run tasks.py list --project work
T0528b [P2] less urgent [work] due:--
$ uv run tasks.py list --type habit
H0528a [--] morning exercise due:--
$ uv run tasks.py list --priority 1
T0528a [P1] urgent thing due:2026-05-28
```
COMMIT MESSAGE:
```
feat(tsk): implement tsk list command
- filter by project, tags, priority, type (AND-combined)
- sort by priority then due date, missing fields sort last
- one-line-per-record output format
```
---
### COMMIT 17: feat(tsk): create bash alias file
LEVEL: haiku
THREAD: G
DEPENDS ON: 08
PURPOSE: Create tsk.sh for sourcing by my_config.
CONTEXT: Spec section 3 (layout). This is a shell file, not a Python change. Designed to be symlinked into my_config extensions directory.
IMPLEMENTATION OUTLINE:
1. Create file: ~/personal_repos/explorations/tasks/tsk.sh
2. Contents:
   ```bash
   # tsk -- task, calendar & habit tracker
   # Source this file or symlink into my_config extensions.
   export TASKS_LOCAL_DIR="$HOME/personal_repos/tasks"
   tsk() { uv run "$HOME/personal_repos/explorations/tasks/tasks.py" "$@"; }
   ```
3. No changes to tasks.py
INVARIANTS:
- assert: after sourcing, `tsk help` works from any directory
- assert: TASKS_LOCAL_DIR is exported
ERROR HANDLING:
- none in shell file -- tasks.py handles missing env var
STRATEGIC PRINTS:
- none
VERIFICATION:
```
$ source ~/personal_repos/explorations/tasks/tsk.sh
$ tsk help
available commands:
  add       create a new task
  ...
$ echo $TASKS_LOCAL_DIR
/home/user/personal_repos/tasks
```
COMMIT MESSAGE:
```
feat(tsk): create bash alias file
- export TASKS_LOCAL_DIR and define tsk function
- designed for symlink into my_config extensions
```
---
## Next Thread Grouping (recommendation)
| Batch | Commits | Level combined | Notes |
|-------|---------|---------------|-------|
| 1 | 09, 10, 11 | sonnet | Three creation commands, 09-10 are thin wrappers, 11 is independent |
| 2 | 12, 13 | sonnet | Lifecycle commands, 13 depends on 12 |
| 3 | 14 | sonnet | Edit is standalone, $EDITOR interaction needs care |
| 4 | 15, 16 | sonnet | View commands, parallel, can batch if thread has room |
| 5 | 17 | haiku | Bash alias, can attach to any batch |
---
## Phase 0 -- Status (updated 2026-05-30)

All planned commits **01-17 complete.** Commits 17a-17e below were added during the 09-17 implementation thread in response to setup/usability findings; they are part of phase 0, not phase 1.

### Planned commits 09-17 -- complete

| #  | Level  | Thread | Summary | Notes |
|----|--------|--------|---------|-------|
| 09 | haiku  | D | `tsk goal` | type=goal, G-prefix, --review |
| 10 | haiku  | D | `tsk habit` | type=habit, H-prefix, --frequency, restricted flags |
| 11 | sonnet | D | `tsk event` | calendar.txt, required --date, --time -> time_start/time_end |
| 12 | sonnet | E | `tsk done` | branch T/G (move) vs H (log); introduced parse_habit_log |
| 13 | haiku  | E | `tsk retire` | move to done.txt, status=retired, any type |
| 14 | sonnet | E | `tsk edit` | $EDITOR + temp file, search active then calendar |
| 15 | sonnet | F | `tsk today` | dashboard, all logic inline; 2nd caller of parse_habit_log |
| 16 | haiku  | F | `tsk list` | filter + sort, missing-field defaults |
| 17 | haiku  | G | `tsk.sh` | TASKS_LOCAL_DIR export, tsk function, uv --no-project |

### Phase 0 hardening / refinement (17a-17e)

| #   | Level  | Type  | Summary | Touches | Depends |
|-----|--------|-------|---------|---------|---------|
| 17a | haiku  | fix   | Harden tsk.sh: TSK_SCRIPT config var, uv source-warn + per-call fail-fast (127), silent on healthy startup | tsk.sh | 17 |
| 17b | sonnet | chore | Section tasks.py into CONFIGURATION/PREFLIGHT/DERIVED; fail-fast on python version + missing/unwritable data dir (exit 2/3/4); atomic write_file (temp + rename) | tasks.py | 03, 07 |
| 17c | haiku  | fix   | Verify TSK_SCRIPT exists at source time (warn) and call time (fail-fast 127) | tsk.sh | 17a |
| 17d | sonnet | feat  | Add `tsk init` (explicit data-dir bootstrap); skip dir gate for bootstrap commands; data-dir error messages distinguish env-set vs default; extract ensure_data_files | tasks.py | 17b |
| 17e | sonnet | feat  | Per-command help: `tsk help <command>` shows usage + flags, flag names derived from the flag dicts (single source of truth) | tasks.py | 08 |

### New shared functions / constants (this thread)

| Name | Introduced | Callers |
|------|-----------|---------|
| `parse_habit_log` | 12 | handle_done, handle_today |
| `validate_time_of_day` | 11 | handle_event (start + end) |
| `ensure_data_files` | 17d | module load, handle_init |
| `COMMAND_USAGE` / `COMMAND_FLAG_SETS` / `FIELD_HELP` | 17e | handle_help |

### Decisions made during 09-17e (canonical; fold into spec Appendix C)

- Atomic writes (temp + rename) to survive interrupted writes / yanked USB.
- Preflight exit codes: 2 = unsupported Python, 3 = data dir missing, 4 = not writable, 127 = (shell) uv/script missing; 1 = command validation.
- `updated` refreshed on `done` and `retire` (per Appendix B retired-record example).
- `edit` ambiguity checked per file (T/G/H vs E prefixes are disjoint).
- `tsk init` over auto-create: auto-create rejected to avoid creating a local shadow directory when the USB drive is unmounted.
- Per-command help via `tsk help <command>`, not per-command `--help` (avoids per-handler boilerplate and parse_flags pollution).
- Habit/tags unrecognized-token fall-through accepted (visible, self-correcting); tags-quoting documented rather than guarded (`#` is valid in summaries).
- Document-linking mechanism (deferred to phase 2): copy/move file into `docs/{id}/`; symlinks rejected for sync-portability (git stores the link, external targets dangle after sync).

### Thread map -- phase 0 closed

```
01-08  (prior thread)  complete
09, 10, 11  thread D   complete
12 -> 13, 14  thread E   complete
15, 16  thread F   complete
17 -> 17a -> 17c  thread G   complete
17b -> 17d  (tasks.py hardening)  complete
17e  (help)  complete
```

---
