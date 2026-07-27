#!/bin/sh
# check.sh -- automation ruler for the playbook. Pre-commit hook.
#
# TWO SEVERITIES, and the distinction is the point of this script:
#   FAIL   blocks the commit. Reserved for correctness: containment
#          (which keeps promotion to a standalone repository cheap,
#          ADR-002) and the ASCII rule. Both are objectively checkable
#          and neither rests on a number anyone guessed.
#   WARN   prints and does not block. Every line ceiling and token
#          budget below was hand-set without measured data (ADR-028)
#          and nothing has been benchmarked since. They are a real
#          accretion countermeasure, so they are kept; they are not
#          calibrated, so they do not gate. Recalibrate when there is
#          data, then promote the ones that earn it.
#
# ASCII only. POSIX sh.

set -u

WORKTREE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "check.sh: not inside a git repository" >&2; exit 1; }
PLAYBOOK_DIRECTORY="$WORKTREE_ROOT/llm_playbook"
[ -d "$PLAYBOOK_DIRECTORY" ] || {
  echo "check.sh: $PLAYBOOK_DIRECTORY missing" >&2; exit 1; }

# A file rather than a shell variable, because the checks below run
# inside pipelines and a subshell cannot set a variable in its parent.
FAILURE_FLAG_FILE="$PLAYBOOK_DIRECTORY/.check-failed"
rm -f "$FAILURE_FLAG_FILE"

# ---- (1) line ceilings -- WARN ----------------------------------------
# Glob pattern relative to the playbook directory, TAB, ceiling.
# entry/ENTRY.md arrives at T-014; until then its pattern matches
# nothing and is skipped, so the table may name a file before it exists.
LINE_CEILING_TABLE='
protocol/*.md	200
preferences/*.md	200
entry/ENTRY.md	150
'

echo "$LINE_CEILING_TABLE" \
| while IFS="$(printf '\t')" read -r CEILING_GLOB_PATTERN CEILING_LINE_COUNT; do
  [ -n "$CEILING_GLOB_PATTERN" ] || continue
  for CANDIDATE_FILE_PATH in $PLAYBOOK_DIRECTORY/$CEILING_GLOB_PATTERN; do
    [ -f "$CANDIDATE_FILE_PATH" ] || continue
    case "$CANDIDATE_FILE_PATH" in
      */entry/ENTRY.md)
        # ENTRY.md is read one role at a time, so its effective size is
        # the common core plus the LARGEST role section, not the whole
        # file. Role sections begin with a line "## ROLE:".
        MEASURED_LINE_COUNT=$(awk '
          BEGIN { core_lines = 0; current_role_lines = 0
                  largest_role_lines = 0; inside_role = 0 }
          /^## ROLE:/ {
            if (inside_role && current_role_lines > largest_role_lines)
              largest_role_lines = current_role_lines
            inside_role = 1; current_role_lines = 1; next }
          { if (inside_role) current_role_lines++; else core_lines++ }
          END {
            if (inside_role && current_role_lines > largest_role_lines)
              largest_role_lines = current_role_lines
            print core_lines + largest_role_lines }' "$CANDIDATE_FILE_PATH")
        ;;
      *)
        MEASURED_LINE_COUNT=$(wc -l < "$CANDIDATE_FILE_PATH")
        ;;
    esac
    if [ "$MEASURED_LINE_COUNT" -gt "$CEILING_LINE_COUNT" ]; then
      echo "check.sh WARN: ${CANDIDATE_FILE_PATH#$WORKTREE_ROOT/} has $MEASURED_LINE_COUNT effective lines (uncalibrated ceiling $CEILING_LINE_COUNT)" >&2
    fi
  done
done

# ---- (2) render ceiling -- WARN ---------------------------------------
# ADR-031 made this ceiling TIER-DEPENDENT: binding for paste delivery,
# advisory for archive delivery. This hook cannot implement that. The
# tier is a property of how a render is SENT, and that is not known at
# commit time. The obvious fix -- a tier: line in the render header --
# is blocked because render.md fixes the hashed body as line 3 onward,
# so inserting a header line invalidates every stamp already issued.
# Until that is resolved the ceiling warns in both tiers and the human
# decides. Recorded here rather than silently dropped.
for STAGED_RENDER_PATH in $(git diff --cached --name-only --diff-filter=ACM 2>/dev/null \
                            | grep -E '(^|/)CONTEXT\.md$' || true); do
  [ -f "$WORKTREE_ROOT/$STAGED_RENDER_PATH" ] || continue
  RENDER_LINE_COUNT=$(wc -l < "$WORKTREE_ROOT/$STAGED_RENDER_PATH")
  if [ "$RENDER_LINE_COUNT" -gt 250 ]; then
    echo "check.sh WARN: $STAGED_RENDER_PATH has $RENDER_LINE_COUNT lines (render ceiling 250, binding for paste delivery only -- ADR-031)" >&2
  fi
done

# ---- (3) required-read lists ------------------------------------------
# A missing file is a FAIL: the list points at something that is not
# there, which is wrong whatever the budget says. The token budget
# itself is a WARN, on the same grounds as the line ceilings.
if [ -f "$PLAYBOOK_DIRECTORY/MANIFEST.md" ]; then
  grep '^REQREAD ' "$PLAYBOOK_DIRECTORY/MANIFEST.md" \
  | while read -r _ REQUIRED_READ_ROLE ROLE_TOKEN_BUDGET REMAINDER_OF_LINE; do
    ROLE_TOKEN_BUDGET="${ROLE_TOKEN_BUDGET%:}"
    LISTED_PATHS="${REMAINDER_OF_LINE#*: }"
    [ "$LISTED_PATHS" = "$REMAINDER_OF_LINE" ] && LISTED_PATHS="$REMAINDER_OF_LINE"
    TOTAL_CHARACTER_COUNT=0
    for LISTED_PATH in $LISTED_PATHS; do
      if [ -f "$WORKTREE_ROOT/$LISTED_PATH" ]; then
        FILE_CHARACTER_COUNT=$(wc -c < "$WORKTREE_ROOT/$LISTED_PATH")
        TOTAL_CHARACTER_COUNT=$((TOTAL_CHARACTER_COUNT + FILE_CHARACTER_COUNT))
      else
        echo "CHECK FAIL: REQREAD $REQUIRED_READ_ROLE lists missing file $LISTED_PATH" >&2
        touch "$FAILURE_FLAG_FILE"
      fi
    done
    # The estimate MANIFEST.md documents: total characters divided by 4.
    ESTIMATED_TOKEN_COUNT=$((TOTAL_CHARACTER_COUNT / 4))
    if [ "$ESTIMATED_TOKEN_COUNT" -gt "$ROLE_TOKEN_BUDGET" ]; then
      echo "check.sh WARN: REQREAD $REQUIRED_READ_ROLE estimated $ESTIMATED_TOKEN_COUNT tokens (uncalibrated budget $ROLE_TOKEN_BUDGET)" >&2
    fi
  done
fi

# ---- (4) containment -- FAIL ------------------------------------------
# Why this exists: ADR-002 keeps the playbook promotable to a standalone
# repository by copy or filter-repo, and one upward path reference or
# one mention of the parent repository would fail silently until
# promotion day.
#
# Why llm/ is exempt: containment protects the TOOLKIT layer, which is
# what travels at promotion. llm/ is this project's own thread history
# -- close artifacts, handoffs, plans -- and it travels with the project
# under either arrangement. Those documents legitimately name the parent
# repository, because they describe work done inside it.
#
# MANIFEST.md is exempt from the parent-name check only: its raw URLs
# must contain the repository name, and rewriting them is the sole
# designated content change at promotion.
PARENT_REPOSITORY_NAME="$(basename "$WORKTREE_ROOT")"
UPWARD_PATH_PATTERN="..""/"

find "$PLAYBOOK_DIRECTORY" -name '*.md' -type f \
| while read -r MARKDOWN_FILE_PATH; do
  REPOSITORY_RELATIVE_PATH="${MARKDOWN_FILE_PATH#$WORKTREE_ROOT/}"
  case "$REPOSITORY_RELATIVE_PATH" in
    llm_playbook/llm/*) continue ;;
  esac
  if grep -Fq "$UPWARD_PATH_PATTERN" "$MARKDOWN_FILE_PATH"; then
    echo "CHECK FAIL: $REPOSITORY_RELATIVE_PATH contains an upward path reference" >&2
    touch "$FAILURE_FLAG_FILE"
  fi
  case "$REPOSITORY_RELATIVE_PATH" in
    llm_playbook/MANIFEST.md) : ;;
    *)
      if grep -iq "$PARENT_REPOSITORY_NAME" "$MARKDOWN_FILE_PATH"; then
        echo "CHECK FAIL: $REPOSITORY_RELATIVE_PATH names the parent repository ($PARENT_REPOSITORY_NAME) in prose" >&2
        touch "$FAILURE_FLAG_FILE"
      fi ;;
  esac
done

# ---- (5) ASCII rule -- FAIL -------------------------------------------
TAB_CHARACTER="$(printf '\t')"
find "$PLAYBOOK_DIRECTORY" -type f ! -path '*/.git/*' ! -name '.check-failed' \
| while read -r ANY_PLAYBOOK_FILE_PATH; do
  if LC_ALL=C grep -q "[^ -~$TAB_CHARACTER]" "$ANY_PLAYBOOK_FILE_PATH" 2>/dev/null; then
    echo "CHECK FAIL: ${ANY_PLAYBOOK_FILE_PATH#$WORKTREE_ROOT/} contains non-ASCII bytes" >&2
    touch "$FAILURE_FLAG_FILE"
  fi
done

if [ -f "$FAILURE_FLAG_FILE" ]; then
  rm -f "$FAILURE_FLAG_FILE"
  echo "check.sh: violations found; commit blocked" >&2
  exit 1
fi
echo "check.sh: clean"
exit 0
