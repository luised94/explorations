# tsk -- Task, Calendar & Habit Tracker Spec v2
## 1. Constraints
### Environment
- Python 3.x, run via `uv run tasks.py`
- Alias: `tsk` (defined in bash, points to `uv run ~/personal_repos/explorations/tasks/tasks.py`)
- Code location: `~/personal_repos/explorations/tasks/` (subdirectory of explorations git repo)
- Data location: `~/personal_repos/tasks/` (separate git repo, synced via USB)
- Environment variable: `TASKS_LOCAL_DIR` -> `~/personal_repos/tasks/`
- Single-writer model -- one machine writes at a time
- Sync via USB module (git-based, amend-per-day commits, rebase default) -- data repo only
- No cloud sync, no SSH, no git integration within the tool itself
- No pyproject.toml -- `uv run tasks.py` without project configuration
### Coding style
- Strict procedural -- no classes, no OOP, no main() function pattern
- Data-oriented programming: define data shapes, write functions that transform them
- Libraries with class-based APIs (argparse, pathlib, etc.) are fine to use
- Flat control flow, full descriptive names (abbreviations only when they've become nouns: usb, cli, nvim)
- Single script file for phase 0
- No git calls from within the tool
- Standard ASCII only in all code, comments, output, and documentation
> **Function extraction rule:** a function earns its definition by having 2+ call sites in the current phase, or by being a dispatch target. Length alone does not justify extraction -- a long inline block that runs once is clearer than a named function the reader has to jump to. A 200-line function that performs one irreducible top-to-bottom sequence is not a problem. I/O boundaries do not justify extraction on their own. Default: inline. Extract only when the second caller appears.
>
> **No functions as arguments to higher-order functions:** do not write a function (named, nested, or lambda) solely to pass to `sorted()`, `map()`, `filter()`, or similar. Build the result directly with a list comprehension, explicit loop, or direct construction. Exception: genuine comparison-based sorting on data where the order is not already known (sorting tasks by due date). The test: if you already have the ordering defined somewhere (a list, a known sequence), walk it directly -- do not convert it into sort keys.
>
> **Variable naming:** use domain vocabulary combined with structural role. `field_name` not `key`, `field_value` not `value`, `formatted_records` not `blocks`. If the name would make sense in any program regardless of domain, it is too generic. The name should tell you this is a task tracker, not a generic dict processor. Structural hints (`_name`, `_value`, `_list`, `_path`) are fine as suffixes when they clarify which side of a pair or what shape the data has.
>
> **Intermediate variables over direct returns:** prefer naming a computed result before returning or using it. `position_in_order = FIELD_ORDER.index(field_name)` over a bare expression inside a return or function call. The variable name documents intent.
>
> **Function docstrings:** when a function modifies state or produces side effects rather than returning a value, say what it reads, what it transforms, and what it changes. "Reads active.txt, filters records by project field, prints matching records to stdout." For pure functions, say what goes in and what comes out in domain terms.
> **Decision: no git integration in tsk**
> Why: git is the transport layer managed by the USB sync module (amend-per-day). tsk reads/writes files. Coupling tsk to git would create noisy commit history, remove user control over commit granularity, and bind the tool to one sync mechanism.
> Rejected: auto-commit on every tsk operation.
### Interfaces
- Primary: CLI (`tsk <command> [args]`)
- Secondary: nvim (direct file editing, keybindings for capture -- deferred to phase 2)
- Tertiary: phone capture via Samsung Notes text export (deferred)
---
## 2. Entities
### 2.1 Task
A unit of work with a lifecycle: created -> active -> done.
| Field    | Required | Default        | Type   | Notes |
|----------|----------|----------------|--------|-------|
| id       | auto     | T{MMDD}{a-z}   | string | auto-generated on add |
| type     | auto     | task           | string | literal "task" |
| summary  | yes      | --             | string | one-line description |
| status   | auto     | active         | string | active, done, or retired |
| project  | no       | --             | string | project name |
| priority | no       | --             | int    | 1 (highest) to 3 |
| due      | no       | --             | date   | YYYY-MM-DD |
| tags     | no       | --             | string | space-separated #tag values |
| parent   | no       | --             | string | ID of parent goal |
| source   | no       | --             | string | origin reference (journal:YYYY-MM-DD, meeting:name, lw:experiment) |
| linked   | no       | --             | string | ID of related event |
| notes    | no       | --             | string | multi-line, indented continuation |
| created  | auto     | today          | date   | YYYY-MM-DD |
| updated  | auto     | today          | date   | YYYY-MM-DD, refreshed on any modification |
| completed| auto     | --             | date   | YYYY-MM-DD, set by `tsk done` or `tsk retire` |
Lifecycle: `tsk add` -> record in active.txt (status=active) -> `tsk done` -> record moved to done.txt (status=done, completed set). Alternatively: `tsk retire` -> record moved to done.txt (status=retired, completed set).
### 2.2 Goal
A goal is a task with `type = goal`. Same fields, same file (active.txt). Goals are parents that tasks reference via the `parent` field.
Additional field:
| Field    | Required | Default  | Type   | Notes |
|----------|----------|----------|--------|-------|
| review   | no       | --       | string | review cadence: weekly, monthly, quarterly |
Lifecycle: same as task. `tsk today` surfaces review reminders when a goal's `updated` date exceeds its review cadence.
> **Decision: goals live in active.txt with type = goal, not in a separate file**
> Why: uniform parser, uniform data layer, one file to read for task/goal views. Goals are just long-lived tasks that other tasks reference.
> Rejected: separate goals.txt (adds cross-file reads, more complex `tsk today`).
### 2.3 Event
A time-bound calendar entry.
| Field      | Required | Default  | Type   | Notes |
|------------|----------|----------|--------|-------|
| id         | auto     | E{MMDD}{a-z} | string | auto-generated |
| type       | no       | meeting  | string | meeting, personal, deadline, block (open set, not validated) |
| summary    | yes      | --       | string | one-line description |
| date       | yes      | --       | date   | YYYY-MM-DD |
| time_start | no       | --       | time   | HH:MM (24hr) |
| time_end   | no       | --       | time   | HH:MM (24hr) |
| recur      | no       | --       | string | daily, weekly, biweekly, monthly (deferred logic) |
| end_recur  | no       | --       | date   | YYYY-MM-DD, when recurrence stops (deferred logic) |
| location   | no       | --       | string | physical address or virtual link |
| prep       | no       | --       | string | multi-line, what to do/read before the event |
| notes      | no       | --       | string | multi-line, agenda or context |
| energy     | no       | --       | string | deep, admin, social, creative |
| linked     | no       | --       | string | ID of related task |
| project    | no       | --       | string | project or life area |
| created    | auto     | today    | date   | YYYY-MM-DD |
| updated    | auto     | today    | date   | YYYY-MM-DD |
Lifecycle: `tsk event` -> record in calendar.txt. Events are not "completed" -- they pass. Old non-recurring events accumulate; archiving is deferred.
> **Decision: event type is an open set**
> Why: the field-agnostic parser philosophy extends to field values. Users may invent types (workshop, travel, errand) without needing code changes. No validation on type values.
> Rejected: closed enum with validation (unnecessary rigidity for a solo tool).
> **Decision: prep is a separate field from notes**
> Why: notes = context you read during the event. prep = actions you take before the event. `tsk today` can show "prep for tomorrow" by reading tomorrow's prep fields. Different read-times, different purposes.
> Rejected: single notes field covering both.
### 2.4 Habit
An ongoing recurring behavior tracked by daily completion.
| Field     | Required | Default  | Type   | Notes |
|-----------|----------|----------|--------|-------|
| id        | auto     | H{MMDD}{a-z} | string | auto-generated |
| type      | auto     | habit    | string | literal "habit" |
| summary   | yes      | --       | string | one-line description |
| frequency | no       | daily    | string | daily, weekdays, MWF, weekly |
| tags      | no       | --       | string | space-separated #tag values |
| project   | no       | --       | string | project or life area |
| notes     | no       | --       | string | multi-line |
| created   | auto     | today    | date   | YYYY-MM-DD |
| updated   | auto     | today    | date   | YYYY-MM-DD |
Lifecycle: `tsk habit "summary"` -> record in active.txt (persists indefinitely). `tsk done H...` logs a completion line to habit_log.txt but does NOT move the record. Retire a habit with `tsk retire H...` (moves to done.txt with status=retired).
> **Decision: habit completions go to habit_log.txt, not done.txt**
> Why: done.txt tracks accomplishments (tasks finished, goals reached). Habit completions are high-volume repetitive data (365 entries/year/habit) with different query patterns (streaks, frequency analysis). Mixing them makes done.txt noisy and queries slow.
> Rejected: recurring tasks that re-create daily (floods done.txt, wrong lifecycle semantics).
---
## 3. Files
### Layout
Code (~/personal_repos/explorations/tasks/):
```
explorations/tasks/
  tasks.py          -- the tsk script
  tsk.sh            -- bash alias/function definition (sourced by my_config)
  tsk.vim           -- nvim keybindings and commands (deferred, phase 2)
```
Data (~/personal_repos/tasks/ -- separate git repo, USB-synced):
```
tasks/
  active.txt        -- tasks, goals, and habits (all active entities)
  calendar.txt      -- events (time-bound entries)
  done.txt          -- completed tasks and retired habits (append-mostly)
  habit_log.txt     -- habit completion log (append-only)
  usage_log.txt     -- command invocation log (append-only, metrics)
  docs/             -- task-linked documents (specs, plans, notes, resources)
```
### Task-linked documents convention
Documents associated with a task or goal live in `docs/{id}/`:
```
docs/
  shared/                   -- cross-cutting resources not tied to a specific task
  {task_or_goal_id}/        -- documents for a specific task or goal
```
Examples:
```
docs/shared/coding_style.md
docs/G0501a/design_notes.md
docs/T0525a/spec_v1.md
docs/T0525a/commit_plan_v1.md
```
Discovery is filesystem-based: `ls docs/T0525a/` shows all documents for a task. No metadata field needed on the task record -- the directory name IS the link. Removal is deletion (`rm -r docs/T0525a/`); git history provides recovery. A `tsk docs <id>` command is deferred to phase 2.
### File characteristics
| File           | Write pattern      | Git diff behavior | Growth |
|----------------|--------------------|-------------------|--------|
| active.txt     | rewrite-compacted  | moderate diffs    | bounded (active items only) |
| calendar.txt   | rewrite-compacted  | moderate diffs    | slow growth, archive later |
| done.txt       | append + occasional rewrite on move | small diffs | unbounded, archive later |
| habit_log.txt  | append-only        | one-line diffs    | proportional to habits x days |
| usage_log.txt  | append-only        | one-line diffs    | proportional to invocations |
---
## 4. Record Format
### Syntax
Records are blocks of `key = value` lines separated by one or more blank lines.
```
key = value
another_key = another value
notes =
  this is a continuation line
  so is this
next_record_key = starts here
```
### Parsing rules
1. A line with no leading whitespace containing `=` starts a new key-value pair. Split on the first `=` only. Strip leading/trailing whitespace from both key and value.
2. A line with leading whitespace (spaces or tabs) is a continuation of the previous value. Append to the previous value with a newline. Preserve internal indentation relative to the first continuation line.
3. A blank line (empty or whitespace-only) ends the current record.
4. Lines before the first key-value pair in a file are ignored (allows a file header comment).
5. All values are strings. Type interpretation (dates, integers) happens in command logic, not in the parser.
### Writing rules
1. Continuation lines are normalized to 2-space indentation on write.
2. Fields are ordered per FIELD_ORDER constant: id, type, summary, status, then domain fields, then created/updated/completed, then multi-line fields (prep, notes) last.
3. Unknown fields (not in FIELD_ORDER) are written after known fields, alphabetically.
4. Round-trip fidelity is semantic: parse(write(parse(x))) == parse(x). Byte-identical output is not guaranteed.
### Duplicate keys within a record
If a key appears more than once in a single record, collect values into a list. Single-occurrence keys remain scalar strings. This supports multi-valued fields without special syntax.
> **Decision: field-agnostic parser**
> Why: the parser reads any key = value pairs without knowing what entity type the record represents. This means deferred fields (recur, blocked_by, estimate, etc.) can be written into files today and will parse correctly. Adding new fields never requires parser changes.
> Rejected: schema-aware parser that validates during parse (validation is a separate pass).
### Habit log format (habit_log.txt)
Not key-value. Simple one-line-per-entry format:
```
YYYY-MM-DD <habit_id>
```
Example:
```
2026-05-22 H0522a
2026-05-23 H0522a
2026-05-23 H0522b
```
Parsed by splitting each line on whitespace into (date_string, habit_id). This is a separate parse path from the CCL record parser. Functions that read habit_log.txt (handle_done for duplicate checking, handle_today for streak calculation) share a common parse function.
### Usage log format (usage_log.txt)
One-line-per-invocation:
```
YYYY-MM-DDTHH:MM:SS <command> <primary_arg_or_dash> <duration_seconds>
```
Example:
```
2026-05-22T14:30:22 add T0522a 0.03s
2026-05-22T14:31:05 today - 0.08s
2026-05-22T18:00:12 done T0522a 0.02s
```
---
## 5. Commands
### Dispatch
Top-level dictionary mapping command names to handler functions. No main() function. Dispatch logic runs at module level at the bottom of the script.
Default command (no arguments): `today`.
ID prefix matching: commands accepting an ID (`done`, `edit`, `retire`) match the shortest unambiguous prefix. If ambiguous, print matching IDs and exit with error.
Each handler that is implemented replaces its placeholder in the dispatch table directly in the same commit. No separate wiring commit needed.
### Error flow
Utility functions (generate_id, find_records_by_prefix, parse_flags, etc.) do not call sys.exit. They return data that callers inspect. Handlers (dispatch targets) may call sys.exit on validation errors. The dispatch level wraps the handler call in try/finally to ensure usage logging fires regardless.
### 5.1 `tsk add <summary> [flags]`
Creates a new task in active.txt.
| Flag       | Short | Effect |
|------------|-------|--------|
| --project  | -p    | set project field |
| --due      | -d    | set due date (YYYY-MM-DD) |
| --priority | -r    | set priority (1-3) |
| --tags     | -t    | set tags (space-separated in quotes) |
| --parent   | -g    | set parent goal ID |
| --source   | -s    | set source reference |
Auto-populated: id (T{MMDD}{a-z}), type (task), status (active), created, updated.
Behavior: generate ID, build record dict, append formatted record to active.txt, log to usage_log.txt.
This is the exemplar mutation command. All creation commands (goal, habit, event) follow this pattern.
### 5.2 `tsk goal <summary> [flags]`
Same as `tsk add` but sets `type = goal`. Accepts all add flags plus:
| Flag     | Short | Effect |
|----------|-------|--------|
| --review | -v    | review cadence: weekly, monthly, quarterly |
### 5.3 `tsk habit <summary> [flags]`
Creates a new habit in active.txt.
| Flag        | Short | Effect |
|-------------|-------|--------|
| --frequency | -f    | daily (default), weekdays, weekly |
| --tags      | -t    | set tags |
| --project   | -p    | set project |
Auto-populated: id (H{MMDD}{a-z}), type (habit), created, updated.
Does not accept --due, --priority, or --parent (not applicable to habits).
### 5.4 `tsk event <summary> --date YYYY-MM-DD [flags]`
Creates a new event in calendar.txt.
| Flag       | Short | Effect |
|------------|-------|--------|
| --date     | -d    | event date (required) |
| --time     | -m    | time range HH:MM-HH:MM |
| --type     | -y    | event type (open set, not validated) |
| --recur    | -r    | daily, weekly, biweekly, monthly (stored, logic deferred) |
| --location | -l    | location string |
| --energy   | -e    | deep, admin, social, creative |
| --project  | -p    | project or life area |
| --linked   | -k    | related task ID |
Auto-populated: id (E{MMDD}{a-z}), created, updated.
### 5.5 `tsk edit <id>`
Opens a record in $EDITOR for detailed editing (speed 2 capture).
Behavior:
1. Find the record by ID (prefix match) across active.txt and calendar.txt.
2. Extract the record text to a temp file.
3. Open temp file in $EDITOR (default: nvim).
4. On save and quit, parse the edited record.
5. Validate: ID must not have changed, required fields present.
6. Write back to the source file at the same position, rewrite-compacted.
7. Auto-update the `updated` field.
### 5.6 `tsk done <id>`
Completes a task/goal or logs a habit completion.
**If the ID is a task or goal (T... or G...):**
1. Find record in active.txt by prefix match.
2. Set status = done, completed = today's date.
3. Remove from active.txt, append to done.txt.
4. Rewrite active.txt compacted.
**If the ID is a habit (H...):**
1. Verify habit exists in active.txt.
2. Check habit_log.txt for duplicate (same habit + same date). If already logged today, print notice and exit.
3. Append `YYYY-MM-DD <habit_id>` to habit_log.txt.
4. Do NOT move the habit from active.txt.
### 5.7 `tsk retire <id>`
Permanently deactivates a habit, goal, or task.
Behavior: find record in active.txt by prefix match, set status = retired and completed = today's date, move from active.txt to done.txt. Distinct command name and status value to signal intent: "this is not finished, it is discontinued."
> **Decision: status=retired is distinct from status=done**
> Why: a retired habit/goal was discontinued, not accomplished. The distinction matters for metrics (completion rate vs churn rate) and for review ("what did I stop doing and why?"). done.txt holds both, distinguishable by status field.
> Rejected: reusing status=done for both (loses semantic information).
### 5.8 `tsk today`
The daily dashboard. Default command when `tsk` is run with no arguments.
Data sources: active.txt, calendar.txt, habit_log.txt.
Output: see section 6 (Display Formats).
### 5.9 `tsk list [flags]`
Shows all active tasks (not events, not habits unless --type is specified).
| Flag       | Short | Effect |
|------------|-------|--------|
| --project  | -p    | filter by project |
| --tags     | -t    | filter by tag |
| --priority | -r    | filter by priority |
| --type     | -y    | filter by type (task, goal, habit) |
Default sort: priority (ascending, 1 first), then due date (soonest first), then created.
Sort defaults for missing fields: records without priority sort after P3 (lowest priority). Records without due date sort after all dated records (no deadline = not urgent).
### 5.10 `tsk help`
Lists all available commands with one-line descriptions. Deferred commands are marked as "(not implemented)". Also triggered by unrecognized commands or `tsk --help`.
### 5.11 Deferred commands (placeholder entries in dispatch, print "not implemented")
- `tsk week` -- seven-day calendar + task view
- `tsk review` -- guided weekly review workflow
- `tsk stale` -- tasks with updated older than N days
- `tsk search <term>` -- full-text search across all files
- `tsk tomorrow` -- tomorrow's events with prep fields
- `tsk goals` -- goal hierarchy view with child task counts
---
## 6. Display Formats
### `tsk today` output
```
EVENTS -- 2026-05-22
  14:00-15:30  team standup [meeting]
  18:00-19:00  dentist [personal] @ 123 Main St
HABITS
  ( ) morning exercise (streak: 5)
  ( ) read 20 min (streak: 0)
DEADLINES
  due today:  implement Samsung Notes export [kbd]
  due +2d:    submit quarterly report [work]
ACTIVE TASKS
  [P1] build tasks module first iteration [tasks]
  [P2] implement Samsung Notes export [kbd]
  [P2] refactor friction module [friction]
GOALS -- review due
  G0501a kbd v2 (last reviewed: 28 days ago, cadence: monthly)
```
Formatting rules:
- Sections only appear if they have content (no empty headers).
- Events sorted by time_start.
- Habits show ( ) if not yet completed today, (x) if completed. Streak calculated from habit_log.txt.
- Deadlines: tasks with due date = today or within 3 days.
- Active tasks sorted by priority then due date. Records without priority sort after P3. Records without due date sort after all dated records.
- Goals section only appears when a goal exceeds its review cadence.
### `tsk list` output
```
T0522a [P2] implement Samsung Notes export [kbd] due:2026-05-25
T0522b [P1] build tasks module [tasks] due:--
G0501a [--] kbd v2 [kbd] review:monthly
```
One line per record. Fields: id, priority (or -- for none), summary, project, due or review cadence.
---
## 7. Metrics
### Raw data
All metrics derive from two log files:
**usage_log.txt** -- one line per command invocation (format in section 4).
**habit_log.txt** -- one line per habit completion (format in section 4).
Plus point-in-time analysis of active.txt and done.txt.
### Derived metrics (analysis deferred, data collected from day one)
| Metric | Source | What it tells you |
|--------|--------|-------------------|
| Command frequency distribution | usage_log.txt | which commands you actually use vs. which you built for nothing |
| Capture-to-completion time | active.txt created vs done.txt completed | are tasks actionable (days) or aspirational (months)? |
| Stale task rate | active.txt: count where (today - updated) > 30 days | graveyard detector -- the metric that kills task systems |
| Habit adherence rate | habit_log.txt: completions / expected by frequency | per-habit, per-week trend |
| Habit streak lengths | habit_log.txt: consecutive days per habit | motivation/consistency signal |
| Edit frequency | usage_log.txt: count of edit commands / count of add commands | is speed-2 capture being used? |
| File growth rate | file sizes over time (sample weekly) | when to build archiving |
| Peak usage time | usage_log.txt: hour-of-day distribution | is this a morning tool or an all-day tool? |
| Goal review compliance | active.txt: goals where (today - updated) > review cadence | are you actually reviewing goals? |
### Scaffolding
Usage logging is captured at the dispatch level via try/finally. The dispatch block records start time before calling the handler, and appends the log line after the handler completes (or fails). This is inline at the dispatch level, not a separate function. The logging write is wrapped in a silent try/except so it never breaks the tool.
---
## 8. Commit Plan
All commits are haiku (mechanical, minimal judgment) or sonnet (moderate judgment, bounded scope). No opus commits. Dependencies noted.
Each handler commit wires itself into the dispatch table directly -- no separate wiring commit.
### Phase 0 -- Foundation
| #  | Level  | Summary | Dependencies | Notes |
|----|--------|---------|--------------|-------|
| 01 | haiku  | Create directory structure and empty data files | none | Create $TASKS_LOCAL_DIR, empty data files. Create tasks.py with dispatch table, placeholders, help. |
| 02 | sonnet | Implement record parser (read) | 01 | parse_records, parse_file |
| 03 | haiku  | Implement record writer (write) | 02 | format_record, write_file, FIELD_ORDER constant |
| 04 | haiku  | Implement round-trip fidelity test | 02, 03 | --verify-parser flag, data-driven test cases |
| 05 | haiku  | Implement ID generation | 01 | generate_id, returns None on exhaustion |
| 06 | haiku  | Implement prefix matching | 05 | find_records_by_prefix, returns list of matches |
| 07 | haiku  | Implement usage logging | 01 | Inline try/finally at dispatch level |
| 08 | sonnet | Implement `tsk add` command (exemplar) | 02, 03, 05, 07 | parse_flags shared utility, validation helpers, exemplar mutation pattern |
| 09 | haiku  | Implement `tsk goal` command | 08 | Reuse creation pattern with type=goal, --review flag |
| 10 | haiku  | Implement `tsk habit` command | 08 | Reuse creation pattern with type=habit, --frequency flag |
| 11 | sonnet | Implement `tsk event` command | 02, 03, 05, 07 | calendar.txt, required --date, time range parsing |
| 12 | sonnet | Implement `tsk done` command | 02, 03, 06, 07 | Branch on ID prefix, habit_log parsing (shared with 15) |
| 13 | haiku  | Implement `tsk retire` command | 12 | status=retired, same move-to-done mechanics |
| 14 | sonnet | Implement `tsk edit` command | 02, 03, 06, 07 | $EDITOR, temp file, search active.txt then calendar.txt |
| 15 | sonnet | Implement `tsk today` command | 02, 07 | Exemplar view command, inline all single-caller logic |
| 16 | haiku  | Implement `tsk list` command | 02, 07 | Filter flags, sort with missing-field defaults |
| 17 | haiku  | Create bash alias file (tsk.sh) | 08 | Export TASKS_LOCAL_DIR, define tsk function |
### Phase 0 parallelization
```
01 --+-- 02 -- 03 -- 04
     |    |
     +-- 05 -- 06
     |
     +-- 07
08 -- 09, 10 (parallel)
11 (parallel to 08)
12 -- 13
14 (parallel to 12)
15 (parallel to 14)
16 (parallel to 15)
17 (after 08, can be done anytime)
```
### Phase 1 -- Depth (after phase 0 is lived-in)
| #  | Level  | Summary | Dependencies |
|----|--------|---------|--------------|
| 18 | sonnet | Implement `tsk goals` -- goal hierarchy view | 02, phase 0 |
| 19 | sonnet | Implement `tsk week` -- 7-day view | 15 |
| 20 | sonnet | Implement `tsk review` -- guided weekly review | 15, 18 |
| 21 | sonnet | Implement `tsk stale` -- aged task report | 02 |
| 22 | sonnet | Implement `tsk tomorrow` -- next-day prep view | 15 |
| 23 | sonnet | Implement recurrence logic for events | 15, 11 |
### Phase 2 -- Integration (after phase 1 is stable)
| #  | Level  | Summary | Dependencies |
|----|--------|---------|--------------|
| 24 | sonnet | Nvim keybindings (tsk.vim) -- add from context, today in split | 08, 15 |
| 25 | sonnet | Samsung Notes import script | 02, 03 |
| 26 | haiku  | Implement `tsk search` -- full-text grep across all files | 02 |
| 27 | haiku  | Syntax highlighting file for nvim | none |
### Phase 3 -- Polish (when warranted by usage data)
| #  | Level  | Summary | Dependencies |
|----|--------|---------|--------------|
| 28 | haiku  | Color output (opt-in --color flag) | 15, 16 |
| 29 | sonnet | `tsk archive` -- move old done.txt entries to yearly files | 02, 03 |
| 30 | sonnet | Metrics analysis script -- derive metrics from logs | 07, usage_log.txt |
| 31 | haiku  | Cross-reference view: show linked tasks <-> events | 02, 15 |
---
## Appendix A: Deferred Fields
These fields are mentioned in design discussions but have no command logic yet. The field-agnostic parser will handle them if manually added to records.
| Field      | Entity  | Purpose | Deferred because |
|------------|---------|---------|------------------|
| blocked_by | task    | dependency on another task ID | requires dependency graph logic |
| estimate   | task    | rough time estimate (hours or S/M/L) | only useful if consistently filled in |
| buffer     | event   | travel/transition time in minutes | display logic not yet designed |
| alert      | event   | reminder lead time | requires cron daemon or background process |
| end_recur  | event   | when recurrence stops | recurrence logic itself is deferred |
| attendees  | event   | who else is involved | display-only, low priority for solo user |
| cancel     | event   | skip specific dates of recurring event | recurrence logic deferred |
| actual     | event   | did event occur, actual duration | review/retrospective workflow deferred |
| area       | task    | life area vs project distinction | tags serve this purpose for now |
## Appendix B: Example Records
### Task in active.txt
```
id = T0522a
type = task
summary = implement Samsung Notes export
status = active
project = kbd
priority = 2
due = 2026-05-25
tags = #phone #kbd
source = journal:2026-05-21
linked = E0523a
created = 2026-05-22
updated = 2026-05-22
notes =
  export format is .sdoc
  can convert with plain text extraction
  see journal entry 2026-05-19
```
### Goal in active.txt
```
id = G0501a
type = goal
summary = kbd v2 with full search and tagging
status = active
project = kbd
priority = 1
review = monthly
tags = #kbd #infrastructure
created = 2026-05-01
updated = 2026-05-15
notes =
  milestone 1: tag extraction from journal
  milestone 2: full-text search
  milestone 3: cross-reference with source-notes
```
### Habit in active.txt
```
id = H0522a
type = habit
summary = morning exercise
frequency = daily
tags = #health
created = 2026-05-22
updated = 2026-05-22
```
### Event in calendar.txt
```
id = E0523a
type = meeting
summary = team standup
date = 2026-05-23
time_start = 14:00
time_end = 15:30
recur = weekly
location = zoom.us/j/123456
energy = social
project = work
linked = T0522a
prep =
  review sprint board
  check deploy status from yesterday
notes =
  recurring weekly sync with engineering team
created = 2026-05-20
updated = 2026-05-22
```
### Retired record in done.txt
```
id = H0522a
type = habit
summary = morning exercise
status = retired
frequency = daily
tags = #health
created = 2026-05-22
updated = 2026-06-15
completed = 2026-06-15
```
### Habit log entry in habit_log.txt
```
2026-05-22 H0522a
2026-05-23 H0522a
```
### Usage log entry in usage_log.txt
```
2026-05-22T14:30:22 add T0522a 0.03s
2026-05-22T18:00:12 done T0522a 0.02s
```
---

## Appendix C: Reconciled Decisions (from design/implementation threads)

These decisions were made during implementation and are now part of the spec. The first table covers commits 01-08; the second covers phase-0 completion and hardening (commits 09-17e).

### From commits 01-08

| Decision | Chosen | Rejected | Why |
|----------|--------|----------|-----|
| Flag parsing | Hand-rolled parse_flags | argparse | Simpler, transparent, fits procedural style, 15 lines vs 50+ |
| Error flow | Utilities return data, handlers exit | Utilities call sys.exit | Testability, logging integrity via dispatch try/finally |
| Round-trip fidelity | Semantic: parse(write(parse(x))) == parse(x) | Byte-identical | Normalizing indentation is simpler, no formatting metadata needed |
| Field ordering | FIELD_ORDER constant, multi-line fields last | Alphabetical or insertion order | Readable output, prep/notes at end avoid dangling compact fields |
| Usage logging | Inline at dispatch level | Extracted log_usage function | One call site in phase 0, extraction rule says inline |
| Event type validation | Open set, no validation | Closed enum | Field-agnostic philosophy, solo tool flexibility |
| Retire status | status=retired distinct from status=done | Reuse status=done | Semantic distinction for metrics and review |

### From commits 09-17e (phase 0 completion and hardening)

| Decision | Chosen | Rejected | Why |
|----------|--------|----------|-----|
| Usage log outcome | Append ok/error per invocation | Duration only | Distinguishes validation failures from successes for metrics |
| validate_priority reuse | Shared by add and goal | Inline per handler | Second caller materialized (goal validates priority); resolves the prior ASSUME |
| done/retire updated field | Refresh updated = today | Leave updated unchanged | "Updated on any modification"; Appendix B retired-record example confirms |
| Habit / extra flags | Fall through to summary | Reject unknown flags | Visible and self-correcting; no second caller justifies rejection logic |
| Edit prefix ambiguity | Per-file check, active then calendar | Combined cross-file check | T/G/H (active) and E (calendar) IDs are prefix-disjoint; collision impossible |
| Duplicate habit done | Exit 0 (idempotent) | Exit 1 error | Logging the same habit twice in a day is a no-op, not an error |
| File writes | Temp sibling + atomic replace | Direct write_text | A crash or yanked USB drive cannot truncate a data file |
| Preflight exit codes | 2 = Python too old, 3 = dir missing, 4 = not writable; shell 127 = uv/script missing | Single exit 1 | Distinct codes aid scripting and diagnosis |
| Data dir bootstrap | Explicit tsk init command | Auto-create on any run | Auto-create risks a local shadow dir when the USB drive is unmounted |
| Per-command help | tsk help &lt;command&gt;, flags read from the flag dicts | --help in every handler | One site, no per-handler boilerplate, no flag duplication or drift |
| ensure_data_files | Extracted | Inline twice | Two callers: module load and handle_init |
| validate_time_of_day | Extracted | Inline try/except twice | Two call sites within handle_event (start and end) |
| Event creation | Inline, no shared creation helper | Shared add/goal/habit/event helper | Different target file, required --date, time-range parsing |
| Tags multi-value | Document quoting; no runtime guard | Warn on a stray #token | "#" is valid inside a summary, so the heuristic false-positives |
| uv invocation (shell) | uv run --no-project | Bare uv run | Ignores a pyproject.toml in the current working directory |
| Task-linked docs (planned, phase 2) | Copy or move the file into the repo | Symlink an external file into the repo | Git stores the link text, not contents; external targets dangle after USB sync |

---
