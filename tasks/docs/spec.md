# tsk -- Task, Calendar & Habit Tracker Spec v3

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
- Single script file for phase 0 and phase 1
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

### 2.1 Entity type convention

Entity types are identified by ID prefix, not by the `type` field. The ID
prefix is the canonical discriminator throughout the codebase:

| Prefix | Entity | File | type field holds |
|--------|--------|------|------------------|
| T | task | active.txt | "task" (by convention) |
| G | goal | active.txt | "goal" (by convention) |
| H | habit | active.txt | "habit" (by convention) |
| E | event | calendar.txt | event subtype: meeting, personal, deadline, block (open set) |

For T/G/H records, the `type` field matches the entity name by convention but
is not used for dispatch. For E records, the `type` field holds the event
subtype (free-text, defaults to "meeting"). Code identifies entity types by
prefix; the `type` field is never the discriminator.

> **Decision: entity type = ID prefix, not type field**
> Why: this was already the codebase pattern in phase 0 (done branches on H prefix, edit selects file by prefix disjointness). Formalizing it avoids a schema migration and eliminates the dual-semantics confusion around the type field.
> Rejected: schema change to add an entity_type field (unnecessary migration for existing data).

### 2.2 Task

A unit of work with a lifecycle: created -> active -> done.

| Field    | Required | Default        | Type   | Notes |
|----------|----------|----------------|--------|-------|
| id       | auto     | T{MMDD}{a-z}   | string | auto-generated on add |
| type     | auto     | task           | string | literal "task" |
| summary  | yes      | --             | string | one-line description, must not be whitespace-only |
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

### 2.3 Goal

A goal is a task with `type = goal`. Same fields, same file (active.txt). Goals are parents that tasks reference via the `parent` field.

Additional field:

| Field    | Required | Default  | Type   | Notes |
|----------|----------|----------|--------|-------|
| review   | no       | --       | string | review cadence: weekly, monthly, quarterly |

Lifecycle: same as task. `tsk today` surfaces review reminders when a goal's `updated` date exceeds its review cadence.

> **Decision: goals live in active.txt with type = goal, not in a separate file**
> Why: uniform parser, uniform data layer, one file to read for task/goal views. Goals are just long-lived tasks that other tasks reference.
> Rejected: separate goals.txt (adds cross-file reads, more complex `tsk today`).

### 2.4 Event

A time-bound calendar entry.

| Field      | Required | Default  | Type   | Notes |
|------------|----------|----------|--------|-------|
| id         | auto     | E{MMDD}{a-z} | string | auto-generated |
| type       | no       | meeting  | string | event subtype: meeting, personal, deadline, block (open set, not validated) |
| summary    | yes      | --       | string | one-line description, must not be whitespace-only |
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

Lifecycle: `tsk add event` -> record in calendar.txt. Events are not individually
completed. Past events (date < today) are batch-archived via `tsk done --cleanup-events`,
which moves them to done.txt with status=done and completed=today. Today's events
remain visible until tomorrow.

> **Decision: event type is an open set**
> Why: the field-agnostic parser philosophy extends to field values. Users may invent types (workshop, travel, errand) without needing code changes. No validation on type values.
> Rejected: closed enum with validation (unnecessary rigidity for a solo tool).

> **Decision: prep is a separate field from notes**
> Why: notes = context you read during the event. prep = actions you take before the event. `tsk today` can show "prep for tomorrow" by reading tomorrow's prep fields. Different read-times, different purposes.
> Rejected: single notes field covering both.

> **Decision: event subtype flag is --label/-y, not --type/-y**
> Why: --type/-y collided with entity type selection after creation consolidation. --label/-y maps to the type field in the record (backward compatible with existing data). Default: "meeting".
> Rejected: keeping --type/-y (ambiguity between entity type and event subtype).

> **Decision: batch event archival, not per-ID done**
> Why: events are not "accomplished" -- they pass. Batch archival via `done --cleanup-events` forces the user to review what is being archived and matches the mental model of "clearing past entries." Per-ID event done was a source of confusion (done E0602a failed because done searches active.txt only).
> Rejected: per-ID event done (would require done to search calendar.txt, complicating the done/active.txt contract).
> Rejected: auto-cleanup on any tsk invocation (manual trigger forces review).

### 2.5 Habit

An ongoing recurring behavior tracked by daily completion.

| Field     | Required | Default  | Type   | Notes |
|-----------|----------|----------|--------|-------|
| id        | auto     | H{MMDD}{a-z} | string | auto-generated |
| type      | auto     | habit    | string | literal "habit" |
| summary   | yes      | --       | string | one-line description, must not be whitespace-only |
| frequency | no       | daily    | string | daily, weekdays, weekly |
| tags      | no       | --       | string | space-separated #tag values |
| project   | no       | --       | string | project or life area |
| notes     | no       | --       | string | multi-line |
| created   | auto     | today    | date   | YYYY-MM-DD |
| updated   | auto     | today    | date   | YYYY-MM-DD |

Lifecycle: `tsk add habit "summary"` -> record in active.txt (persists indefinitely). `tsk done H...` logs a completion line to habit_log.txt but does NOT move the record. Retire a habit with `tsk retire H...` (moves to done.txt with status=retired).

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
  done.txt          -- completed tasks, retired entities, and archived events
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
| calendar.txt   | rewrite-compacted  | moderate diffs    | slow growth, archived via --cleanup-events |
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
YYYY-MM-DDTHH:MM:SS <command> <primary_arg_or_dash> <duration_seconds> <outcome>
```

Example:
```
2026-05-22T14:30:22 add T0522a 0.03s ok
2026-05-22T14:31:05 today - 0.08s ok
2026-05-22T18:00:12 done T0522a 0.02s ok
2026-06-04T09:15:33 add:goal G0604a 0.01s ok
```

Compound command names (add:goal, add:event, add:task, add:habit) are logged
for creation commands to distinguish entity type in usage analysis.

---

## 5. Commands

### Dispatch

Top-level dictionary mapping command names to handler functions. No main() function. Dispatch logic runs at module level at the bottom of the script.

Default command (no arguments): `today`.

ID prefix matching: commands accepting an ID (`done`, `edit`, `retire`) match the shortest unambiguous prefix. If ambiguous, print matching IDs and exit with error.

Each handler that is implemented replaces its placeholder in the dispatch table directly in the same commit. No separate wiring commit needed.

### Error flow

Utility functions (generate_id, find_records_by_prefix, parse_flags, etc.) do not call sys.exit. They return data that callers inspect. Handlers (dispatch targets) may call sys.exit on validation errors. The dispatch level wraps the handler call in try/finally to ensure usage logging fires regardless.

### Summary validation

Whitespace-only and empty summaries are rejected with an error. The missing-summary
error path prints the full type-aware flag list (same output as `tsk help add`)
so the user does not need a separate help call before retrying.

### ID generation

IDs are unique across all data files. generate_id collects existing IDs from
active.txt, done.txt, and calendar.txt before selecting the next available
suffix. Completing or retiring a record does not free its ID for reuse on
the same day.

### 5.1 `tsk add [task|goal|habit|event] <summary> [flags]`

Creates a new record in the appropriate file. Entity type is determined by
an optional positional subcommand; defaults to task.

```
tsk add "buy milk"                              # task (default)
tsk add task "goal setting workshop"            # explicit task
tsk add goal "ship v2" --review monthly         # goal
tsk add habit "morning walk"                    # habit
tsk add event "standup" --date 2026-06-10       # event
```

If the first word of the summary matches a known entity type (task, goal, habit,
event), it is consumed as the type selector. To keep it as part of the summary,
use the explicit `task` subcommand.

All flags are accepted for all entity types (field-agnostic philosophy). One
exception: `--date` is required for events. Flag values are validated per
entity type where applicable (priority 1-3, date format, review cadence,
frequency values).

ENTITY_CONFIG maps each entity type to its ID prefix, target file, flag set,
defaults, validations, and usage string. This is the single source of truth
for per-type creation behavior.

| Flag       | Short | Field     | Type annotation |
|------------|-------|-----------|-----------------|
| --project  | -p    | project   | all |
| --due      | -d    | due       | all |
| --priority | -r    | priority  | all |
| --tags     | -t    | tags      | all |
| --parent   | -g    | parent    | all |
| --source   | -s    | source    | all |
| --review   | -v    | review    | goal |
| --frequency| -f    | frequency | habit |
| --date     |       | date      | event (required) |
| --time     | -m    | time_start/end | event |
| --label    | -y    | type      | event |
| --recur    |       | recur     | event |
| --location | -l    | location  | event |
| --energy   | -e    | energy    | event |
| --linked   | -k    | linked    | event, task |

Auto-populated: id ({prefix}{MMDD}{a-z}), type (entity type or event subtype),
status (active, for non-events), created, updated. Habits default frequency
to daily.

> **Decision: one handle_add replaces four creation handlers**
> Why: friction log showed users wanted `tsk add goal` not `tsk goal`. Four handlers shared 80% of their logic. ENTITY_CONFIG data-drives the differences. Old top-level commands (goal, habit, event) removed from dispatch entirely.
> Rejected: keeping separate top-level commands (code duplication, dispatch clutter, user confusion about whether `tsk goal` or `tsk add goal` is correct).

> **Decision: all flags accepted for all entity types**
> Why: field-agnostic philosophy. A user who passes --priority to a habit gets a priority field on the record. The tool stores it; the user decides if it is meaningful. One exception: --date is required for events because an event without a date is not schedulable.
> Rejected: per-type flag rejection (adds validation code for no user benefit in a solo tool).

> **Decision: positional subcommand, not --type flag, for entity type**
> Why: `tsk add goal "x"` reads naturally. The --type flag is available as fallback but the positional form is primary. The first positional arg is checked against {task, goal, habit, event}; if it matches, it is consumed.
> Rejected: --type as primary (verbose, requires flag before summary).

### 5.2 `tsk edit <id>`

Opens a record in $EDITOR for detailed editing.

Behavior:
1. Find the record by ID (prefix match) across active.txt and calendar.txt.
2. Extract the record text to a temp file.
3. Open temp file in $EDITOR (default: nvim).
4. On save and quit, parse the edited record.
5. Validate: ID must not have changed, required fields present.
6. Write back to the source file at the same position, rewrite-compacted.
7. Auto-update the `updated` field.

handle_edit does not search done.txt. Archived records are not editable.

### 5.3 `tsk done <id>` / `tsk done --cleanup-events`

Completes a task/goal, logs a habit completion, or batch-archives past events.

**`tsk done --cleanup-events` (batch event archival):**
1. Read calendar.txt.
2. Move all events with date < today to done.txt (status=done, completed=today).
3. Events with unparseable dates are skipped with a warning to stderr.
4. Events without a date field are skipped silently.
5. Today's events remain in calendar.txt (date < today, not <=).
6. Print count and IDs of archived events.
7. If no past events found, print "no past events to archive" and exit 0.

**If the ID is a task or goal (T... or G...):**
1. Find record in active.txt by prefix match.
2. Set status = done, completed = today's date, updated = today.
3. Remove from active.txt, append to done.txt.
4. Rewrite active.txt compacted.

**If the ID is a habit (H...):**
1. Verify habit exists in active.txt.
2. Check habit_log.txt for duplicate (same habit + same date). If already logged today, print notice and exit 0.
3. Append `YYYY-MM-DD <habit_id>` to habit_log.txt.
4. Do NOT move the habit from active.txt.

**If the ID matches an event (E...):**
done searches active.txt only. Event IDs are not found. Use `--cleanup-events`
for event archival.

### 5.4 `tsk retire <id>`

Permanently deactivates a habit, goal, or task.

Behavior: find record in active.txt by prefix match, set status = retired and completed = today's date, updated = today, move from active.txt to done.txt. Distinct command name and status value to signal intent: "this is not finished, it is discontinued."

> **Decision: status=retired is distinct from status=done**
> Why: a retired habit/goal was discontinued, not accomplished. The distinction matters for metrics (completion rate vs churn rate) and for review ("what did I stop doing and why?"). done.txt holds both, distinguishable by status field.
> Rejected: reusing status=done for both (loses semantic information).

### 5.5 `tsk today`

The daily dashboard. Default command when `tsk` is run with no arguments.

Data sources: active.txt, calendar.txt, habit_log.txt.

Output: see section 6 (Display Formats).

### 5.6 `tsk list [flags]`

Shows all active records (from active.txt) and events (from calendar.txt),
grouped by entity type.

| Flag       | Short | Effect |
|------------|-------|--------|
| --project  | -p    | filter by project (exact match) |
| --tags     | -t    | filter by tag (substring match) |
| --priority | -r    | filter by priority (exact match) |
| --type     | -y    | filter by entity type: task, goal, habit, event (matches by ID prefix) |
| --sort     |       | sort order within groups: priority (default), date, project |

Filters are AND-combined. Output is grouped by entity type in fixed order:
GOALS, TASKS, HABITS, EVENTS. Sorted within each group by the active --sort
mode. Sections with no matching records are skipped.

> **Decision: --type filter matches by ID prefix, not type field value**
> Why: consistent with the "entity type = ID prefix" convention. `--type event` selects E-prefix records. The type field holds event subtypes, not entity types.
> Rejected: filtering by type field value (would match event subtypes like "meeting" instead of entity types).

> **Decision: list reads both active.txt and calendar.txt**
> Why: events were invisible to list in phase 0 (friction entry 06-02). list is the primary orientation command (26% of invocations); it should show everything.
> Rejected: separate `tsk events` command (redundant; `list --type event` suffices).

### 5.7 `tsk week`

Seven-day forward view of events and task deadlines.

Shows today through today+6. Each day prints a header with weekday name, date,
and "(today)" suffix for the current day. Under each header: events sorted by
start time, then tasks due that day sorted by priority. Days with no entries
show a `--` placeholder to preserve the calendar rhythm.

Data sources: calendar.txt (events), active.txt (tasks with due dates).

### 5.8 `tsk help [command]`

With no argument: lists all commands with one-line descriptions.

With a command name: prints usage line, description, and flags grouped by field
name with descriptions from FIELD_HELP and type annotations from
FLAG_TYPE_ANNOTATIONS (e.g. "(event)", "(goal)", "(event (required))").

The same help output is printed on missing-summary errors in handle_add, so the
user gets the full flag list inline with the error without needing a separate
help call.

### 5.9 `tsk init`

Creates the data directory, data files, and docs directory. Idempotent. Prints
the resolved path so the user can confirm it is the intended target.

### 5.10 Deferred commands (placeholder entries in dispatch, print "not implemented")

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
GOALS
  G0501a [--] kbd v2 [kbd] review:monthly
TASKS
  T0522a [P2] implement Samsung Notes export [kbd] due:2026-05-25
  T0522b [P1] build tasks module [tasks] due:--
HABITS
  H0522a [--] morning exercise due:--
EVENTS
  E0523a [--] team standup date:2026-05-23
```

Grouped by entity type in fixed order: GOALS, TASKS, HABITS, EVENTS. One line
per record within each group. Fields: id, priority (or --), summary, project
(if present), then due/review/date depending on entity type. Goals show review
cadence; events show event date; tasks and habits show due date.

### `tsk week` output

```
Thu 2026-06-04 (today)
  09:00-09:30  morning standup [meeting]
  [due] [P1] submit report [work]
Fri 2026-06-05
  --
Sat 2026-06-06
  14:00-15:00  dentist [personal] @ 123 Main St
Sun 2026-06-07
  --
Mon 2026-06-08
  --
Tue 2026-06-09
  --
Wed 2026-06-10
  --
```

Seven days, today through today+6. Events show time range, summary, type, and
location. Tasks show [due] marker, priority, summary, and project. Empty days
show `--` placeholder.

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
| Entity type distribution | usage_log.txt: add:task vs add:goal vs add:event vs add:habit | what entity types are actually used? |

### Scaffolding

Usage logging is captured at the dispatch level via try/finally. The dispatch block records start time before calling the handler, and appends the log line after the handler completes (or fails). This is inline at the dispatch level, not a separate function. The logging write is wrapped in a silent try/except so it never breaks the tool.

Compound command names (add:goal, add:event, add:task, add:habit) are logged
by peeking at the first argument at dispatch level. This mirrors the entity
type detection in handle_add but is kept at dispatch level to maintain logging
independence from the handler.

---

## 8. Commit Plan

### Phase 0 -- Foundation (complete)

| #  | Level  | Summary | Status |
|----|--------|---------|--------|
| 01 | haiku  | Create directory structure and empty data files | complete |
| 02 | sonnet | Implement record parser (read) | complete |
| 03 | haiku  | Implement record writer (write) | complete |
| 04 | haiku  | Implement round-trip fidelity test | complete |
| 05 | haiku  | Implement ID generation | complete |
| 06 | haiku  | Implement prefix matching | complete |
| 07 | haiku  | Implement usage logging | complete |
| 08 | sonnet | Implement `tsk add` command (exemplar) | complete |
| 09 | haiku  | Implement `tsk goal` command | complete |
| 10 | haiku  | Implement `tsk habit` command | complete |
| 11 | sonnet | Implement `tsk event` command | complete |
| 12 | sonnet | Implement `tsk done` command | complete |
| 13 | haiku  | Implement `tsk retire` command | complete |
| 14 | sonnet | Implement `tsk edit` command | complete |
| 15 | sonnet | Implement `tsk today` command | complete |
| 16 | haiku  | Implement `tsk list` command | complete |
| 17 | haiku  | Create bash alias file (tsk.sh) + hardening (17a-17e) | complete |

### Phase 1 -- Depth (complete)

| #   | Level  | Summary | Status |
|-----|--------|---------|--------|
| 17f | haiku  | Fix ID reuse: collect IDs from all files | complete |
| 18  | sonnet | Consolidate creation into handle_add with ENTITY_CONFIG | complete |
| 19  | sonnet | Extend list: grouped output, calendar.txt, --sort, prefix --type | complete |
| 20  | haiku  | Add --cleanup-events to done | complete |
| 21  | haiku  | Help refinement: full type-aware help on errors | complete |
| 23  | haiku  | Whitespace-only summary guard, spec v3 | complete |
| 22  | sonnet | Implement tsk week -- 7-day forward view | complete |

### Phase 2 -- Integration (planned)

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

### Archived event in done.txt

```
id = E0602a
type = meeting
summary = NEB presentation
status = done
date = 2026-06-02
time_start = 10:00
time_end = 11:00
project = work
created = 2026-06-02
updated = 2026-06-04
completed = 2026-06-04
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

### Usage log entries in usage_log.txt

```
2026-05-22T14:30:22 add T0522a 0.03s ok
2026-05-22T18:00:12 done T0522a 0.02s ok
2026-06-04T09:15:33 add:goal G0604a 0.01s ok
2026-06-04T09:16:01 add:event E0604a 0.01s ok
```

---

## Appendix C: Reconciled Decisions

These decisions were made during implementation and are now part of the spec.

### From phase 0 (commits 01-17e)

| Decision | Chosen | Rejected | Why |
|----------|--------|----------|-----|
| Flag parsing | Hand-rolled parse_flags | argparse | Simpler, transparent, fits procedural style, 15 lines vs 50+ |
| Error flow | Utilities return data, handlers exit | Utilities call sys.exit | Testability, logging integrity via dispatch try/finally |
| Round-trip fidelity | Semantic: parse(write(parse(x))) == parse(x) | Byte-identical | Normalizing indentation is simpler, no formatting metadata needed |
| Field ordering | FIELD_ORDER constant, multi-line fields last | Alphabetical or insertion order | Readable output, prep/notes at end avoid dangling compact fields |
| Usage logging | Inline at dispatch level | Extracted log_usage function | One call site in phase 0, extraction rule says inline |
| Event type validation | Open set, no validation | Closed enum | Field-agnostic philosophy, solo tool flexibility |
| Retire status | status=retired distinct from status=done | Reuse status=done | Semantic distinction for metrics and review |
| Usage log outcome | Append ok/error per invocation | Duration only | Distinguishes validation failures from successes for metrics |
| validate_priority reuse | Shared by add and goal | Inline per handler | Second caller materialized; extraction rule satisfied |
| done/retire updated field | Refresh updated = today | Leave updated unchanged | "Updated on any modification"; Appendix B retired-record example confirms |
| Habit / extra flags | Fall through to summary | Reject unknown flags | Visible and self-correcting; no second caller justifies rejection logic |
| Edit prefix ambiguity | Per-file check, active then calendar | Combined cross-file check | T/G/H (active) and E (calendar) IDs are prefix-disjoint; collision impossible |
| Duplicate habit done | Exit 0 (idempotent) | Exit 1 error | Logging the same habit twice in a day is a no-op, not an error |
| File writes | Temp sibling + atomic replace | Direct write_text | A crash or yanked USB drive cannot truncate a data file |
| Preflight exit codes | 2 = Python, 3 = dir, 4 = writable; shell 127 | Single exit 1 | Distinct codes aid scripting and diagnosis |
| Data dir bootstrap | Explicit tsk init command | Auto-create on any run | Auto-create risks a local shadow dir when the USB drive is unmounted |
| Per-command help | tsk help <command>, flags from flag dicts | --help in every handler | One site, no per-handler boilerplate, no flag duplication or drift |
| ensure_data_files | Extracted | Inline twice | Two callers: module load and handle_init |
| validate_time_of_day | Extracted | Inline twice | Two call sites within handle_event (start and end) |
| Tags multi-value | Document quoting; no runtime guard | Warn on stray #token | "#" is valid inside a summary, so the heuristic false-positives |
| uv invocation (shell) | uv run --no-project | Bare uv run | Ignores a pyproject.toml in the current working directory |

### From phase 1 (commits 17f-22)

| Decision | Chosen | Rejected | Why |
|----------|--------|----------|-----|
| Entity type identification | ID prefix (T/G/H/E) | type field value | Already the codebase pattern; avoids schema migration |
| Creation consolidation | One handle_add with positional subcommand | Four separate handlers | 80% shared logic; ENTITY_CONFIG data-drives differences |
| Entity type selection | Positional subcommand (`tsk add goal`) | --type flag as primary | Reads naturally; --type available as fallback |
| Old commands (goal, habit, event) | Removed from dispatch | Kept as aliases | Clean break; no deprecation period needed for solo tool |
| Flag acceptance | All flags for all types, one exception | Per-type flag rejection | Field-agnostic philosophy; --date required for events |
| Event subtype flag | --label/-y | --type/-y | Avoids collision with entity type; maps to type field in record |
| ID reuse prevention | Collect IDs from all files | Check target file only | Prevents duplicate IDs after done/retire moves records |
| Event lifecycle | Batch archival via --cleanup-events | Per-ID event done | Events pass, not accomplished; batch forces review |
| Auto-cleanup of events | Rejected | On every tsk invocation | Manual trigger forces review of what is archived |
| list data sources | active.txt + calendar.txt | active.txt only | Events were invisible; list is primary orientation command |
| list output format | Grouped by entity type | Flat sorted list | Clear visual separation; entity types have different display fields |
| --type filter | Matches by ID prefix | Matches by type field | Consistent with entity type = ID prefix convention |
| --sort flag | date, project, priority (default) | No sort control | Different users want different orderings |
| list and today | Separate commands, separate display | Unified with flags | Different purposes: data query vs curated dashboard |
| Help on error | Full flag list on missing summary | Bare usage line | Eliminates help-before-action round-trip observed in usage data |
| Flag type annotations | Shown in help output | Hidden, flags unlabeled | Helps user know which flags are relevant per entity type |
| print_command_help extraction | Extracted (2 callers) | Inline in both | handle_help and handle_add error path both need it |
| Whitespace-only summary | Rejected with error | Accepted silently | Creates invisible records in list/today output |
| Compound usage logging | add:goal, add:event, etc. | Plain "add" for all | Enables per-entity-type usage analysis |
| Week view scope | Today + 6 days, no flags | Configurable range | Simple first; extend if usage warrants |
| Week view content | Events + task deadlines | Include habits, goals | Habits are daily (shown in today); goals have no date dimension |
| Edit scope | active.txt + calendar.txt only | Include done.txt | Archived records should not be edited; retire is one-way |
| parse_flags syntax | --flag value only | Also --flag=value | Document limitation; no usage demand for = syntax |
