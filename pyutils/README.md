# pyutils

Small, general, dependency-free Python utilities, kept in one installable
package so any local project can import them instead of copying files or
fighting with sys.path. Standard-library only.

## Modules

- `terminal_output` -- terminal formatting: width-aware alignment and
  wrapping, color/style application (with a global on/off so output is
  deterministic in tests and pipes), cards, tables, separators, tree
  rendering, duration/cost/token formatting, and leveled message emit
  (error/warn/info/debug/success) routed to stderr. Extracted from the
  retired sm2 project (see the drill repo, ADR-059).

## Install (editable, recommended)

From this directory:

    pip install -e .

Editable means edits to the source are live with no reinstall. After this,
every Python project on the machine can:

    from pyutils import terminal_output
    from pyutils.terminal_output import emit, format_card

Run the tests:

    pip install -e ".[test]"
    python -m pytest tests/ -q

## Layout

    pyutils/
      pyproject.toml         packaging (setuptools, src layout)
      README.md
      src/pyutils/
        __init__.py          exposes the modules
        terminal_output.py
      tests/
        test_terminal_output.py

The `src/` layout is deliberate: it prevents importing the package by
accident from the working directory before it is installed, so the tests
exercise the installed package exactly as other projects will import it.

## Planned: extracting into its own repository (preserving history)

This package currently lives inside the `explorations` monorepo. It is
structured so the entire `pyutils/` directory can become a standalone repo
root unchanged (nothing above `pyutils/` is referenced). When you want to
split it out with history preserved, use `git subtree` from the monorepo
root:

    # 1. Create a new branch containing ONLY pyutils/ history, with
    #    pyutils/ rewritten to the repo root.
    git subtree split --prefix=pyutils -b pyutils-only

    # 2. Make the new repo and pull that branch in as its main.
    mkdir ../pyutils-repo && cd ../pyutils-repo
    git init
    git pull ../explorations pyutils-only

    # 3. Point it at a remote and push.
    git remote add origin <new-remote-url>
    git push -u origin main

`git subtree split` walks history and keeps only the commits that touched
`pyutils/`, rewriting paths so `pyutils/src/...` becomes `src/...` at the
new root. History for these files is preserved (authorship, dates,
messages) for every commit that is present in the clone.

IMPORTANT caveat for this specific clone: it was created with
`--depth 1` (a shallow clone), so it does NOT contain full history. A
subtree split here would only carry the commits present locally. To get
COMPLETE history into the split, first deepen the clone:

    git fetch --unshallow

then run the split. If you would rather not preserve pre-extraction
history at all, the simplest alternative is to copy the `pyutils/`
directory into a fresh `git init` and make one initial commit -- clean
slate, no shared history. Both are valid; `subtree split` after
`--unshallow` is the history-preserving one.

After extraction, consumers install from the new repo the same way
(`pip install -e path/to/pyutils-repo`, or from a git URL), and the
monorepo copy can be removed.
