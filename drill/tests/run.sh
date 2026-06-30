#!/usr/bin/env bash
# C-020 formalized test runner.
#
# Backend  : pytest over the backend tests (logic + db + http + generator)
# Frontend : node over the *.test.js jsdom suites (real index.html)
#
# Both tiers read drill.py / index.html by RELATIVE path, so this runner cd's
# to the project root and exports PROJECT_ROOT for the integration test.
#
# Layout-agnostic: it finds the python test files and the frontend/ dir
# relative to its own location, whether run.sh lives in tests/ or beside it.
#
# Requires from the project root:
#   - python3 with: bottle, pytest, hypothesis
#   - node with jsdom resolvable (npm install jsdom --no-save)
set -u

RUN_DIR="$(cd "$(dirname "$0")" && pwd)"

# Where the python tests + frontend/ live. If run.sh sits in tests/, that is
# RUN_DIR; if it sits beside a tests/ dir, that is RUN_DIR/tests.
if [ -f "$RUN_DIR/test_logic.py" ]; then
  TESTS_DIR="$RUN_DIR"
elif [ -f "$RUN_DIR/tests/test_logic.py" ]; then
  TESTS_DIR="$RUN_DIR/tests"
else
  echo "ERROR: cannot find test_logic.py near $RUN_DIR" >&2
  exit 2
fi

# Project root = where drill.py + index.html live. Walk up from TESTS_DIR.
find_root() {
  local d="$1"
  for _ in 1 2 3 4 5; do
    if [ -f "$d/drill.py" ] && [ -f "$d/index.html" ]; then echo "$d"; return 0; fi
    d="$(cd "$d/.." && pwd)"
  done
  return 1
}
PROJECT_ROOT="${PROJECT_ROOT:-$(find_root "$TESTS_DIR")}"
if [ -z "${PROJECT_ROOT:-}" ] || [ ! -f "$PROJECT_ROOT/drill.py" ]; then
  echo "ERROR: could not locate drill.py; set PROJECT_ROOT explicitly" >&2
  exit 2
fi
export PROJECT_ROOT
echo "TESTS_DIR=$TESTS_DIR"
echo "PROJECT_ROOT=$PROJECT_ROOT"
cd "$PROJECT_ROOT"

fail=0

# Prefer `uv run` so pytest resolves from the project venv (where the test
# dependency-group is installed) rather than the system python3, which on some
# machines has no pytest even after `uv sync --group test`. Fall back to a bare
# python3 invocation if uv is not on PATH (e.g. CI images without uv).
echo
echo "== Backend (pytest: logic, db, http, generator property) =="
if command -v uv >/dev/null 2>&1; then
  if ! uv run python3 -c "import pytest" >/dev/null 2>&1; then
    echo "  test deps missing -- run: uv sync --group test" >&2
    exit 2
  fi
  uv run pytest "$TESTS_DIR" -q || fail=1
else
  python3 -m pytest "$TESTS_DIR" -q || fail=1
fi

# jsdom 24+ and the harnesses use optional chaining (?.), which Node < 18
# cannot parse -- an old node fails with a cryptic "Unexpected token '.'" deep
# inside tough-cookie. Check the major version up front and say so plainly.
# (npm's version is irrelevant here; only the Node runtime matters.)
# The integration test shells out to Python; route it through the venv the
# same way the backend pytest run is, so the child process sees bottle. Mirror
# the uv-preferred / system-fallback choice used for pytest above.
echo
echo "== Frontend (node + jsdom, real index.html) =="
if command -v uv >/dev/null 2>&1; then
  export PYTHON_CMD="uv run python3"
else
  export PYTHON_CMD="python3"
fi
NODE_MAJOR="$(node -p 'process.versions.node.split(".")[0]' 2>/dev/null || echo 0)"
if [ "$NODE_MAJOR" -lt 18 ]; then
  echo "  SKIP: Node 18+ required for jsdom (found $(node --version 2>/dev/null || echo 'no node'))."
  echo "        Install via nvm: nvm install 20 && nvm use 20, then: npm install jsdom --no-save"
  fail=1
else
  for t in drill.test.js speech.test.js timing.test.js stats.test.js stats.integration.test.js difficulty.test.js; do
    echo "-- $t"
    node "$TESTS_DIR/frontend/$t" || fail=1
  done
fi

echo
if [ "$fail" -eq 0 ]; then echo "ALL GREEN"; else echo "FAILURES ABOVE"; fi
exit $fail
