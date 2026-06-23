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

echo
echo "== Backend (pytest: logic, db, http, generator property) =="
python3 -m pytest "$TESTS_DIR" -q || fail=1

echo
echo "== Frontend (node + jsdom, real index.html) =="
for t in drill.test.js speech.test.js timing.test.js stats.test.js stats.integration.test.js; do
  echo "-- $t"
  node "$TESTS_DIR/frontend/$t" || fail=1
done

echo
if [ "$fail" -eq 0 ]; then echo "ALL GREEN"; else echo "FAILURES ABOVE"; fi
exit $fail
