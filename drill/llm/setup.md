# C-020 local setup

Drop the `tests/` directory at your project root (next to `drill.py` and
`index.html`):

    drill/
      drill.py
      index.html
      tests/            <- this suite
      pyproject.toml

## Python test deps

Add a test dependency group to `pyproject.toml`:

    [dependency-groups]
    test = ["pytest>=8", "hypothesis>=6"]

(bottle is already your runtime dep.) Then:

    uv sync --group test

## Node test dep (frontend, jsdom)

From the project root:

    npm install jsdom --no-save

## Run

    uv run pytest tests            # backend only
    bash tests/run.sh              # backend + frontend (everything)

Note: open the app through the server (`uv run drill`), not by double-clicking
index.html -- `file://` blocks the ES-module split planned in phase0 Section A.
