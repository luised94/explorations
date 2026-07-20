#!/bin/sh
# check.sh -- automation ruler for the playbook. Pre-commit hook.
# Enforces: (1) per-file line ceilings from the budgets table below,
# (2) chars/4 token estimates for MANIFEST REQREAD lists,
# (3) containment: no upward path references and no parent-repository
#     name in prose within playbook markdown files,
# (4) the ASCII rule for every playbook file.
# Exception (plan-sanctioned): MANIFEST.md is excluded from the
# parent-name grep because its raw URLs must contain the repository
# name; those URLs are the sole designated change at promotion.
# ASCII only. POSIX sh.

set -u

ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "check.sh: not inside a git repository" >&2; exit 1; }
PB="$ROOT/llm_playbook"
[ -d "$PB" ] || { echo "check.sh: $PB missing" >&2; exit 1; }

FLAG="$PB/.check-failed"
rm -f "$FLAG"
err() { echo "CHECK FAIL: $*" >&2; touch "$FLAG"; }

# ---- (1) line ceilings ------------------------------------------------
# budgets table: glob pattern (relative to playbook dir) TAB ceiling
BUDGETS='
protocol/*.md	200
preferences/*.md	200
entry/ENTRY.md	150
'
# entry/ENTRY.md ceiling applies to common core plus the largest role
# section; role sections are delimited by lines beginning "## ROLE:".

count_entry_effective() {
  awk 'BEGIN{core=0; cur=0; max=0; inrole=0}
    /^## ROLE:/ {if(inrole && cur>max)max=cur; inrole=1; cur=1; next}
    { if(inrole) cur++; else core++ }
    END{ if(inrole && cur>max)max=cur; print core+max }' "$1"
}

echo "$BUDGETS" | while IFS="$(printf '\t')" read -r pat ceil; do
  [ -n "$pat" ] || continue
  for f in $PB/$pat; do
    [ -f "$f" ] || continue
    case "$f" in
      */entry/ENTRY.md) n=$(count_entry_effective "$f") ;;
      *) n=$(wc -l < "$f") ;;
    esac
    if [ "$n" -gt "$ceil" ]; then
      echo "CHECK FAIL: ${f#$ROOT/} has $n effective lines (ceiling $ceil)" >&2
      touch "$FLAG"
    fi
  done
done

# renders anywhere in the repo: any staged CONTEXT.md <= 250 lines
for f in $(git diff --cached --name-only --diff-filter=ACM 2>/dev/null \
           | grep -E '(^|/)CONTEXT\.md$' || true); do
  [ -f "$ROOT/$f" ] || continue
  n=$(wc -l < "$ROOT/$f")
  [ "$n" -le 250 ] || err "$f has $n lines (render ceiling 250)"
done

# ---- (2) token estimates for REQREAD lists ----------------------------
if [ -f "$PB/MANIFEST.md" ]; then
  grep '^REQREAD ' "$PB/MANIFEST.md" | while read -r _ role budget rest; do
    budget="${budget%:}"
    paths="${rest#*: }"
    [ "$paths" = "$rest" ] && paths="$rest"
    total=0
    for p in $paths; do
      if [ -f "$ROOT/$p" ]; then
        c=$(wc -c < "$ROOT/$p"); total=$((total + c))
      else
        echo "CHECK FAIL: REQREAD $role lists missing file $p" >&2
        touch "$FLAG"
      fi
    done
    tokens=$((total / 4))
    if [ "$tokens" -gt "$budget" ]; then
      echo "CHECK FAIL: REQREAD $role estimated $tokens tokens (budget $budget)" >&2
      touch "$FLAG"
    fi
  done
fi

# ---- (3) containment --------------------------------------------------
PARENT="$(basename "$ROOT")"
UP="..""/"
for f in $(find "$PB" -name '*.md' -type f); do
  rel="${f#$ROOT/}"
  if grep -Fq "$UP" "$f"; then
    err "$rel contains an upward path reference"
  fi
  case "$rel" in
    llm_playbook/MANIFEST.md) : ;;   # sanctioned raw-URL exception
    *)
      if grep -iq "$PARENT" "$f"; then
        err "$rel names the parent repository ($PARENT) in prose"
      fi ;;
  esac
done

# ---- (4) ASCII rule ---------------------------------------------------
TAB="$(printf '\t')"
for f in $(find "$PB" -type f ! -path '*/.git/*' ! -name '.check-failed'); do
  if LC_ALL=C grep -q "[^ -~$TAB]" "$f" 2>/dev/null; then
    err "${f#$ROOT/} contains non-ASCII bytes"
  fi
done

if [ -f "$FLAG" ]; then
  rm -f "$FLAG"
  echo "check.sh: violations found; commit blocked" >&2
  exit 1
fi
echo "check.sh: clean"
exit 0
