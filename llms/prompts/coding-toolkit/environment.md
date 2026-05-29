# Environment
VERSION: 2
UPDATED: 2026-05-27

Development environment, tools, directory structure, and constraints.
Paste into LLM threads when the model needs to understand where code
lives and how it runs.

---

## Glossary

| Term | What it is | Example |
|------|-----------|---------|
| module | A self-contained project directory with its own data and purpose | kbd module, lw module |
| repo | A git repository, either GitHub-synced or USB-synced | explorations repo, tasks repo |
| my_config repo | Central git repo for shell/editor environment configuration | ~/personal_repos/my_config/ |
| extensions directory | Directory inside my_config repo where symlinked config files are auto-loaded | my_config/extensions/ |
| USB sync module | Infrastructure for syncing private repos between machines via USB drive | handles push/pull/amend |

---

## Tools

### Editor
- nvim as primary editor
- Extensions/config managed via my_config extensions directory
  (files symlinked into a location my_config reads on load)
- Fold navigation via `# ====` section headers
- File access from anywhere via custom commands/functions

### Shell
- bash as primary shell
- Aliases and functions defined in files sourced by my_config
- Convention: short memorable aliases for frequently used tools

### Language
- Python 3.x as primary scripting language
- Run via `uv run script.py` (no virtualenv management, no
  pyproject.toml required for single scripts)
- bash for thin wrappers, aliases, environment setup
- Lua only for nvim configuration

### Version Control
- git for all repositories
- **Public/code repos**: synced via GitHub (explorations repo, etc.)
- **Private/data repos**: synced via USB sync module (tasks repo,
  kbd module, lw module - anything containing personal data)
- USB sync convention: amend-per-day commits, rebase as default,
  pull required before push, safeguards against accidental overwrites
- Single-writer model: only one machine writes to a private repo at
  a time; conflicts rare but handled via rebase
- No SSH configured (out of scope for now)

---

## Directory Structure

### Code repositories (GitHub-synced)
```
~/personal_repos/
  explorations/           git repo, GitHub-synced, project code
    tasks/                tsk project code directory
      tasks.py
      tsk.sh
      tsk.vim (deferred)
    friction/             friction tracking project directory
    [other projects]/
```

### Private repositories (USB-synced)
```
~/personal_repos/
  my_config/              git repo, USB-synced, environment config
    extensions/           symlinked config files (bash, nvim)
  kbd/                    git repo, USB-synced, knowledge base module
    journal.txt
    source-notes.txt
    projects/
  lw/                     git repo, USB-synced, lab work module
  tasks/                  git repo, USB-synced, tsk data
    active.txt
    calendar.txt
    done.txt
    habit_log.txt
    usage_log.txt
    docs/
      shared/
      {task_id}/
  [other private modules]/
```

### Convention
- Code and data are always in separate repositories
- Data is precious and USB-synced; code is replaceable
- Each module (kbd, lw, tasks) is a sibling, not nested
- Modules connect through conventions (tags, references, file
  naming), not code imports or shared dependencies

---

## my_config

Central environment configuration. Always loaded on shell startup.

### What it does
- Sources bash files from extensions directory
- Loads nvim config files from extensions directory
- Sets environment variables
- Defines aliases and functions

### How projects integrate
- Project creates a shell file (e.g., `tsk.sh`) defining aliases,
  env vars, and functions
- File is symlinked into my_config's extensions directory
- my_config picks it up automatically on next shell startup

### Example integration (tsk)
```bash
# tsk.sh - symlinked into my_config/extensions/
export TASKS_LOCAL_DIR="$HOME/personal_repos/tasks"
tsk() { uv run "$HOME/personal_repos/explorations/tasks/tasks.py" "$@"; }
```

---

## Module Ecosystem

### Current modules
| Module   | Purpose | Data location | Code location | Sync |
|----------|---------|---------------|---------------|------|
| kbd module | Knowledge base, journal, source notes | ~/personal_repos/kbd/ | same | USB |
| lw module | Lab work, job-related experiment notes | ~/personal_repos/lw/ | same | USB |
| tasks repo | Task/calendar/habit tracker data | ~/personal_repos/tasks/ | explorations/tasks/ | USB (data), GitHub (code) |
| friction project | Friction tracking across projects | varies | explorations/friction/ | GitHub |
| my_config repo | Shell/editor environment config | ~/personal_repos/my_config/ | same | USB |

### Module relationships
- Modules are siblings, never nested
- No code imports between modules
- Connection via lightweight conventions:
  - Tags: `#kbd`, `#lw` in task records
  - Source references: `source = journal:2026-05-21`
  - Project field: `project = kbd` on tasks
  - File naming: task IDs in docs/ directories

### Planned but not yet built
- Samsung Notes import (phone  kbd/tasks)
- SM2 spaced repetition system
- Personal LLM interaction library (prompt storage, thread management)
- Centralized config language library (CCL-style parser)
- Shared personal libraries (terminal output, logging, metrics)

---

## Constraints

- Solo developer, personal tooling
- No cloud services, no SSH (for now)
- No external dependencies unless unavoidable (prefer stdlib)
- No internet-connected features in tools
- USB sync is the only data transport between machines
- Phone capture (Samsung Notes) exists but export/import not yet built
- Work context: salaried job tasks tracked alongside personal projects,
  no integration with employer's systems (Jira, etc.)
