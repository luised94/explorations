# Drill

A local, single-user drill/practice tool for self-study with persistent
cross-session tracking. Categories include arithmetic (generated on the
fly), vocabulary, trivia, geography, logic, typing, and code snippets.

The tool is a Python backend serving one HTML page and a small JSON API.
You run it locally, open a browser, and drill. All progress is tracked in
a single SQLite file across sessions.

## Stack

- Python 3.10+, managed with [uv](https://docs.astral.sh/uv/)
- [Bottle](https://bottlepy.org/) -- the one external Python dependency
- SQLite via the standard-library `sqlite3` module for persistence
- Vanilla JS, HTML, and CSS for the frontend -- no frameworks, no build step

## Layout

    drill.py        all backend: config, database, logic, http, main
    index.html      all frontend: drill UI, single page
    pyproject.toml  project metadata and dependencies
    drill.db        SQLite database (created on first run; not committed)

The backend is organized into clearly separated sections -- CONFIG,
DATABASE, LOGIC, HTTP, MAIN -- following a data-oriented procedural style
where data crosses boundaries as plain dicts, lists, and primitives.

## Setup

Install uv if you do not have it, then sync the environment:

    uv sync

This creates a virtual environment and installs Bottle.

## Running

    uv run drill

By default the server starts on http://localhost:8080. Open that URL in a
browser to start drilling. The SQLite database is created automatically on
first run.

## Importing content

Question banks import as JSON Lines (`.jsonl`), the canonical format: one
JSON object per line, with required fields `question` and `answer` and
optional fields for tags, alternatives, distractors, hints, and media.
CSV is also accepted as a convenience and converted internally to the same
format.

## Backup

The database is a single file. To back it up, copy `drill.db`. To restore,
copy it back. There is no separate export step.

## Status

v1, in development. See the design spec for architecture decisions, the
data model, the API surface, and the commit-by-commit implementation plan.
Notable exclusions from v1 (the schema already accommodates them): AI
content generation, speech recognition, handwriting input, timed rounds,
adaptive difficulty, multi-user access, and chart rendering in stats.
