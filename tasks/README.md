# tsk -- task, calendar & habit tracker

A single-file, plain-text CLI for tracking tasks, goals, habits, and calendar
events. Data lives in human-readable `key = value` text files; the tool reads
and writes those files and does nothing else. Sync, backup, and version history
are handled outside the tool (a separate git repo, synced via USB).

## Requirements

- Python 3.10 or newer (the code uses `X | Y` union type syntax)
- [uv](https://docs.astral.sh/uv/) on your `PATH`

The tool itself has no third-party dependencies -- it imports only the Python
standard library. uv is used purely as the runner.

## Setup

The code and the data live in two separate repositories:

- **Code:** `~/personal_repos/explorations/tasks/`
- **Data:** `~/personal_repos/tasks/` (set via the `TASKS_LOCAL_DIR` environment variable)

To install the `tsk` command, source the alias file from your shell config (or
symlink it into your config's extensions directory):

```bash
source ~/personal_repos/explorations/tasks/tsk.sh
```

This defines a `tsk` shell function and exports `TASKS_LOCAL_DIR`. The alias
file checks for uv and for the script itself at startup, warning if either is
missing, and stays silent when everything is healthy.

`TASKS_LOCAL_DIR` defaults to `~/personal_repos/tasks` but respects an existing
value, so you can point tsk at an alternate data directory by exporting it
before sourcing.

## Layout

```
explorations/tasks/        (code repo)
  tasks.py                 the tsk script
  tsk.sh                   shell alias / function definition
  README.md                this file

personal_repos/tasks/      (data repo, USB-synced)
  active.txt               tasks, goals, and habits (all active entities)
  calendar.txt             events (time-bound entries)
  done.txt                 completed tasks, retired entities, and archived events
  habit_log.txt            habit completion log (append-only)
  usage_log.txt            command invocation log (append-only, metrics)
  docs/                    task-linked documents, one folder per id
```

## Entity types and ID prefixes

Entity types are identified by their ID prefix, not by the `type` field:

| Prefix | Entity | File | Notes |
|--------|--------|------|-------|
| T | task | active.txt | unit of work with a lifecycle |
| G | goal | active.txt | long-lived task that other tasks reference via `parent` |
| H | habit | active.txt | recurring behavior tracked by daily completion |
| E | event | calendar.txt | time-bound calendar entry |

For events, the `type` field holds the event subtype (meeting, personal,
deadline, block). For tasks, goals, and habits, `type` matches the entity name
by convention. The ID prefix is the canonical discriminator throughout the
codebase.

IDs are auto-generated as `{prefix}{MMDD}{letter}` (e.g. `T0529a`). IDs are
unique across all files -- completing or retiring a record does not free its ID
for reuse on the same day.

## Commands

Run `tsk` with no arguments for the daily dashboard (the default command), or
`tsk help` for the full list. For a single command's usage and flags, run
`tsk help <command>` (e.g. `tsk help add`) -- the flag list is generated from
the command itself, so it is always current.

| Command | Syntax | What it does |
|---------|--------|--------------|
| `add`    | `tsk add [task\|goal\|habit\|event] <summary> [flags]` | create a record (task by default) |
| `edit`   | `tsk edit <id>` | open a record in `$EDITOR` |
| `done`   | `tsk done <id>` | complete a task/goal, or log a habit for today |
| `done`   | `tsk done --cleanup-events` | archive all past events to done.txt |
| `retire` | `tsk retire <id>` | discontinue any entity (status=retired) |
| `today`  | `tsk today` (or just `tsk`) | daily dashboard |
| `list`   | `tsk list [flags]` | filtered, grouped list of active records and events |
| `week`   | `tsk week` | 7-day forward view of events and deadlines |
| `init`   | `tsk init` | create the data directory and files |
| `help`   | `tsk help [command]` | list commands, or show one command's usage and flags |

Commands that take an id accept the shortest unambiguous prefix.

### Creating records: `tsk add`

All records are created through `tsk add`. The entity type is determined by an
optional positional subcommand:

```bash
tsk add "buy milk"                              # task (default)
tsk add task "goal setting workshop"            # explicit task
tsk add goal "ship v2" --review monthly         # goal
tsk add habit "morning walk"                    # habit (frequency defaults to daily)
tsk add event "standup" --date 2026-06-10       # event (--date required)
```

If the first word of the summary matches a known entity type (task, goal, habit,
event), it is consumed as the type selector. To keep it in the summary, use the
explicit `task` subcommand: `tsk add task "goal setting workshop"`.

### Flags

All flags are accepted for all entity types (field-agnostic philosophy). The
tool does not reject a flag because of entity type -- it simply stores the
value. One exception: `--date` is required for events.

| Flag | Short | Field | Notes |
|------|-------|-------|-------|
| `--project` | `-p` | project | project or life area |
| `--due` | `-d` | due | due date, YYYY-MM-DD |
| `--priority` | `-r` | priority | 1 (highest) to 3 |
| `--tags` | `-t` | tags | space-separated #tags in one quoted string |
| `--parent` | `-g` | parent | ID of a parent goal |
| `--source` | `-s` | source | origin reference (journal:2026-05-21, meeting:standup) |
| `--review` | `-v` | review | review cadence: weekly, monthly, quarterly (goal) |
| `--frequency` | `-f` | frequency | daily (default), weekdays, weekly (habit) |
| `--date` | | date | event date, YYYY-MM-DD (event, required) |
| `--time` | `-m` | time_start/end | time range HH:MM-HH:MM in 24hr (event) |
| `--label` | `-y` | type | event subtype: meeting (default), personal, deadline, block (event) |
| `--recur` | | recur | daily, weekly, biweekly, monthly (stored, not yet active) |
| `--location` | `-l` | location | address or meeting link (event) |
| `--energy` | `-e` | energy | deep, admin, social, creative (event) |
| `--linked` | `-k` | linked | ID of a related record |

Multi-value flags like `--tags` take a single argument, so quote the whole
value: `--tags "#health #home"`. Unquoted extra words (`--tags #health #home`)
are not grouped -- only the first is captured as the tag and the rest fall
into the summary.

### Listing records: `tsk list`

Shows all active records (from active.txt) and events (from calendar.txt),
grouped by entity type: GOALS, TASKS, HABITS, EVENTS.

| Flag | Short | Effect |
|------|-------|--------|
| `--project` | `-p` | filter by project (exact match) |
| `--tags` | `-t` | filter by tag (substring match) |
| `--priority` | `-r` | filter by priority (exact match) |
| `--type` | `-y` | filter by entity type: task, goal, habit, event (matches by ID prefix) |
| `--sort` | | sort order within groups: priority (default), date, project |

Filters are AND-combined. Sections with no matching records are skipped.

### Completing and archiving

`tsk done <id>` works differently depending on entity type:

- **Tasks and goals (T/G):** moves the record from active.txt to done.txt with
  status=done and completed=today.
- **Habits (H):** logs a completion line to habit_log.txt for today. The habit
  record stays in active.txt. Logging the same habit twice in a day is a
  no-op (exit 0).
- **Events (E):** `done <id>` does not work on events. Use
  `tsk done --cleanup-events` to batch-archive all events with a date before
  today from calendar.txt to done.txt. Today's events remain visible until
  tomorrow.

`tsk retire <id>` discontinues any entity by moving it to done.txt with
status=retired.

### Week view: `tsk week`

Shows a 7-day forward calendar starting from today. Each day lists events
(sorted by start time) and tasks due that day (sorted by priority). Days
with no entries show a placeholder.

```
Thu 2026-06-04 (today)
  09:00-09:30  morning standup [meeting]
Fri 2026-06-05
  [due] [P1] submit report [work]
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

### Not yet implemented

`review`, `stale`, `search`, `tomorrow`, `goals` are registered but
print a not-implemented notice. They are planned for later phases.

## Record format

Records are blocks of `key = value` lines separated by blank lines. Indented
lines continue the previous value; a repeated key collects into a list.

```
id = T0529a
type = task
summary = write the README
status = active
project = tsk
priority = 2
due = 2026-06-01
notes =
  this is a continuation line
  so is this
```

The parser is field-agnostic: it reads any keys without knowing the entity
type, so new fields can be added to records by hand and will round-trip
correctly. Writes are atomic (temp file + rename), so an interrupted write
cannot truncate a data file.

## Examples

```bash
tsk add "draft quarterly report" --project work --priority 1 --due 2026-06-15
tsk add goal "ship v2" --project tsk --review monthly --priority 1
tsk add habit "morning walk" --frequency daily --tags "#health"
tsk add event "team standup" --date 2026-06-02 --time 09:00-09:30 --project work
tsk done T0529a            # complete a task
tsk done H0529a            # log today's habit completion
tsk done --cleanup-events  # archive past events
tsk retire G0501a          # discontinue a goal
tsk list --project work
tsk list --type event
tsk list --sort date
tsk week                   # 7-day forward view
tsk                        # daily dashboard
```

## Exit codes

| Code | Meaning |
|------|---------|
| 0 | success (including idempotent no-ops, e.g. habit already logged today) |
| 1 | command-level validation error (bad argument, no match, ambiguous prefix) |
| 2 | unsupported Python version (requires 3.10+) |
| 3 | data directory not found |
| 4 | data directory not writable |
| 127 | (shell) uv or the script not found |

## Sync

tsk assumes a **single writer** -- one machine edits at a time. There is no
locking, no cloud sync, and no git integration inside the tool itself; tsk only
reads and writes the plain-text files.

Syncing the data repository across machines is handled externally by the USB
sync module ([luised94/usb-sh](https://github.com/luised94/usb-sh)), which uses
git with amend-per-day commits over a USB drive. tsk deliberately stays out of
that: it does not commit, push, or pull, so you keep full control over commit
granularity and the tool is not bound to one sync mechanism.

If you only ever use tsk on a single machine, the git repository in the data
directory is optional -- you can leave it uninitialized or remove it entirely.
The tool does not depend on git in any way; it just needs a writable directory.

## Using tsk from nvim

`tsk` is a bash *function* (defined in `integrations/tsk.sh`, sourced from
your interactive shell config). nvim's `:!cmd` spawns a **non-interactive**
shell, which does not source that config -- so `:!tsk ...` fails with
`command not found` and exit 127. There are three ways to drive tsk from
nvim, in increasing order of integration; pick per use.

**1. A terminal split (works immediately, no setup).** `:terminal` -- or
`:split | terminal` for a persistent dashboard beside your notes -- starts
an interactive shell that *does* source your config, so the `tsk` function
is present. Run `tsk today` after each capture to keep the dashboard
current. Editor capture (`tsk add ... --edit`) must happen here: it opens
$EDITOR as a child, and inside a `:terminal` that is a normal nested nvim
(`:wq` applies the capture, `:cq` aborts and nothing is created). This is
the only place `--edit` works from within nvim.

**2. Call the script directly in `:!` (one-offs, no shell function).**
Because tsk is just argv in, files and stdout out, you can bypass the
function and run the script the way the function does:

```
:!uv run --no-project ~/personal_repos/explorations/tasks/tasks.py today
:r !uv run --no-project ~/personal_repos/explorations/tasks/tasks.py week
```

The second reads the week view into the current buffer at the cursor -- a
planning workflow: pull the week in, annotate it, keep it as a note. tsk's
exit codes (0 ok, 1 validation, 3 data dir missing -- see Exit codes) show
up in `:!` output, so a bad field tells you at once. This form is verbose
but has zero dependency on shell config and cannot 127.

**3. The nvim module (real integration).** `integrations/tsk.lua` is a
plugin-free module that wraps the direct-script call in `:Tsk` and
`:TskRead` commands plus `<leader>t` maps, using `vim.system` (no shell,
no quoting hazards). See that file's header for the loader contract and
`docs/nvim-integration-strategy.md` for the design and alternatives. Note
that `:Tsk add ... --edit` cannot open an interactive editor (no
controlling TTY); use the terminal split from option 1 for capture.

Concurrency: tsk reads and writes files atomically per invocation, so nvim
commands and a shell on the same machine interleave safely. The
single-writer rule in the Sync section is about machines, not processes
started at different times -- just do not run two writing commands at the
same instant.

## Notes

Writes are atomic (temp file + rename), so an interrupted write or a yanked USB
drive cannot truncate a data file. On exFAT volumes, atomicity of rename is not
guaranteed by the filesystem; the temp-file approach is still strictly better
than a direct write.

On first setup, run `tsk init` and confirm the printed path is your intended
data directory (the mounted drive, not a local path created while the drive was
unmounted).
