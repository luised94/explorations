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

if command_name.startswith("--"):
    # Reserved for special flags like --verify-parser (commit 04)
    print(f"unknown flag: {command_name}", file=sys.stderr)
    print("run 'tsk help' for available commands", file=sys.stderr)
    sys.exit(1)

if command_name not in COMMANDS:
    print(f"unknown command: {command_name}", file=sys.stderr)
    print("run 'tsk help' for available commands", file=sys.stderr)
    sys.exit(1)

COMMANDS[command_name](arguments)
