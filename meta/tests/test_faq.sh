#!/usr/bin/env bash
# The faq function (meta/shell/meta.sh), run in a throwaway git repository
# with a stub nvim that records how it was called. Run from anywhere:
#   bash meta/tests/test_faq.sh
# Prints one line per failed check, then "ok: N checks" or exits 1.
# A planted bug in meta.sh must make at least one check fail.

set -u
META_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
WORK_DIRECTORY="$(mktemp -d)"
trap 'rm -rf "$WORK_DIRECTORY"' EXIT
CHECK_COUNT=0
FAILURE_COUNT=0

function expect {
  # expect DESCRIPTION ACTUAL EXPECTED_SUBSTRING
  CHECK_COUNT=$((CHECK_COUNT + 1))
  case "$2" in
    *"$3"*) ;;
    *) FAILURE_COUNT=$((FAILURE_COUNT + 1)); printf 'FAIL %s\n  wanted: %s\n  got:    %s\n' "$1" "$3" "$2" ;;
  esac
}

function expect_absent {
  CHECK_COUNT=$((CHECK_COUNT + 1))
  case "$2" in
    *"$3"*) FAILURE_COUNT=$((FAILURE_COUNT + 1)); printf 'FAIL %s\n  unwanted: %s\n  got:      %s\n' "$1" "$3" "$2" ;;
  esac
}

# shellcheck source=../shell/meta.sh
source "$META_DIRECTORY/shell/meta.sh"
NVIM_CALLS="$WORK_DIRECTORY/nvim-calls.txt"
# A function wins over any nvim on PATH; it records one call per line.
function nvim { printf '%s|' "$@" >> "$NVIM_CALLS"; printf '\n' >> "$NVIM_CALLS"; }

REPOSITORY="$WORK_DIRECTORY/explorations"
mkdir -p "$REPOSITORY/project/src/deep"
git -C "$REPOSITORY" init -q

# --- nothing yet: says how to start one ---
cd "$REPOSITORY/project/src/deep" || exit 1
output="$(faq 2>&1)"; status=$?
expect "no file: exit 1" "$status" "1"
expect "no file: says how to start" "$output" 'faq --add "QUESTION" starts one'

# --- --add from deep inside a project starts the project's file ---
output="$(faq --add "Why only 8 due?" 2>&1)"
expect "add: starts the file in the project directory" "$output" "started $REPOSITORY/project/FAQ.md"
expect "add: the template's title names the project" "$(head -1 "$REPOSITORY/project/FAQ.md")" "# FAQ: project"
answer_line="$(grep -n '^answer: $' "$REPOSITORY/project/FAQ.md" | cut -d: -f1)"
expect "add: nvim opens at the answer line" "$(tail -1 "$NVIM_CALLS")" "+$answer_line|"
expect "add: nvim loads the fold view" "$(tail -1 "$NVIM_CALLS")" "luafile $META_DIRECTORY/nvim/faq.lua|"

# --- an answered entry, an open one, a duplicate, one with no pointer ---
cat >> "$REPOSITORY/project/FAQ.md" <<'ENTRIES'

## How many items does a session hold, and why that many?
asked: Why three new?
answer: Due items first, then new ones up to the day's allowance;
  drills count toward it.
see: rep status
rule: PLAN.md D36

## why only 8 due?
asked: again, in other words
answer: Asked twice.
ENTRIES
printf '# FAQ: explorations\n\n## How are threads started?\nanswer: From a kickoff file.\nsee: meta/THREADS.md\n' > "$REPOSITORY/FAQ.md"

output="$(faq --questions)"
expect "questions: the open one is marked" "$output" "Why only 8 due?   (open)"
expect "questions: the answered one is not" "$output" "why that many?"
expect_absent "questions: answered not marked open" "$output" "why that many?   (open)"
expect "questions: the repository's file is in scope too" "$output" "$REPOSITORY/FAQ.md:3  How are threads started?"

output="$(faq --open)"
expect "open: lists the open one" "$output" "Why only 8 due?"
expect_absent "open: not the answered one" "$output" "why that many"

output="$(faq session allowance)"
expect "search: all words, across lines" "$output" "## How many items does a session hold, and why that many?"
expect "search: prints the entry body" "$output" "  drills count toward it."
expect_absent "search: not the others" "$output" "How are threads started?"
output="$(faq three NEW)"
expect "search: finds the asked: words, any case" "$output" "why that many?"
faq nothing-like-this > /dev/null 2>&1; status=$?
expect "search: no match exits 1" "$status" "1"

output="$(faq --check)"; status=$?
expect "check: duplicate question named" "$output" "the same question as $REPOSITORY/project/FAQ.md:"
expect "check: answer without see or rule named" "$output" "answered, but no see: or rule:"
expect "check: problems exit 1" "$status" "1"

# --- plain faq opens the nearest file, folded ---
: > "$NVIM_CALLS"
faq
expect "open: the nearest file" "$(cat "$NVIM_CALLS")" "luafile $META_DIRECTORY/nvim/faq.lua|$REPOSITORY/project/FAQ.md|"

# --- at the repository root only its own file is in scope ---
cd "$REPOSITORY" || exit 1
output="$(faq --questions)"
expect_absent "root: the project's file is not in scope" "$output" "project/FAQ.md"

output="$(faq --help)"
expect "help: lists the modes" "$output" 'faq --add "QUESTION"'

if [ "$FAILURE_COUNT" -gt 0 ]; then
  echo "$FAILURE_COUNT of $CHECK_COUNT checks failed"
  exit 1
fi
echo "ok: $CHECK_COUNT checks"
