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
  done.txt                 completed tasks and retired entities
  habit_log.txt            habit completion log (append-only)
  usage_log.txt            command invocation log (append-only, metrics)
  docs/                    task-linked documents, one folder per id
```

## Commands

Run `tsk` with no arguments for the daily dashboard (the default command), or
`tsk help` for the full list. For a single command's usage and flags, run
`tsk help <command>` (e.g. `tsk help add`) -- the flag list is generated from
the command itself, so it is always current.

| Command | Syntax | What it does |
|---------|--------|--------------|
| `add`    | `tsk add <summary> [flags]` | create a task in active.txt |
| `goal`   | `tsk goal <summary> [flags]` | create a goal (task with type=goal) |
| `habit`  | `tsk habit <summary> [flags]` | create a habit |
| `event`  | `tsk event <summary> --date YYYY-MM-DD [flags]` | create a calendar event |
| `edit`   | `tsk edit <id>` | open a record in `$EDITOR` |
| `done`   | `tsk done <id>` | complete a task/goal, or log a habit for today |
| `retire` | `tsk retire <id>` | discontinue any entity (status=retired) |
| `today`  | `tsk today` (or just `tsk`) | daily dashboard |
| `list`   | `tsk list [flags]` | filtered, sorted list of active records |
| `init`   | `tsk init` | create the data directory and files |
| `help`   | `tsk help [command]` | list commands, or show one command's usage and flags |

IDs are auto-generated as `{prefix}{MMDD}{letter}` -- `T` for tasks, `G` for
goals, `H` for habits, `E` for events (e.g. `T0529a`). Commands that take an id
accept the shortest unambiguous prefix.

### Common flags

`add` and `goal`: `--project/-p`, `--due/-d`, `--priority/-r` (1-3),
`--tags/-t`, `--parent/-g`, `--source/-s`. `goal` adds `--review/-v`
(weekly, monthly, quarterly).

`habit`: `--frequency/-f` (daily, weekdays, weekly; default daily),
`--tags/-t`, `--project/-p`.

`event`: `--date/-d` (required), `--time/-m` (`HH:MM-HH:MM`), `--type/-y`,
`--recur/-r`, `--location/-l`, `--energy/-e`, `--project/-p`, `--linked/-k`.

`list`: `--project/-p`, `--tags/-t`, `--priority/-r`, `--type/-y`
(filters are AND-combined).

Multi-value flags like `--tags` take a single argument, so quote the whole
value: `--tags "#health #home"`. Unquoted extra words (`--tags #health #home`)
are not grouped -- only the first is captured as the tag and the rest fall
into the summary.

### Not yet implemented

`week`, `review`, `stale`, `search`, `tomorrow`, `goals` are registered but
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
tsk goal "ship v2" --project tsk --review monthly --priority 1
tsk habit "morning walk" --frequency daily --tags "#health"
tsk event "team standup" --date 2026-06-02 --time 09:00-09:30 --project work
tsk done T0529a            # complete a task
tsk done H0529a            # log today's habit completion
tsk retire G0501a          # discontinue a goal
tsk list --project work
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

## Notes

Writes are atomic (temp file + rename), so an interrupted write or a yanked USB
drive cannot truncate a data file. On first setup, run `tsk init` and confirm
the printed path is your intended data directory (the mounted drive, not a
local path created while the drive was unmounted).
