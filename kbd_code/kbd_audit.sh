#!/usr/bin/env bash
# kbd-audit.sh -- consolidated metrics for kbd plain-text note system
# Run from the root of your kbd repo.
# Usage: bash kbd-audit.sh [output_file]

set -u

#KBD_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KBD_DIR=$KBD_LOCAL_DIR
CURRENT_DIR=$(pwd)

OUT="${1:-_audit_$(date +%Y-%m-%d).txt}"
J="journal.txt" N="notes.txt" T="tasks.txt" TL="tasks_log.txt" F="_friction.txt"

cd "$KBD_DIR"

# ensure core files exist
for f in "$J" "$N" "$T"; do
  [[ -f "$f" ]] || { echo "Missing $f -- run from kbd root." >&2; exit 1; }
done

{
cat <<EOF
================================================================
  kbd audit -- $(date +%Y-%m-%d\ %H:%M)
================================================================

EOF

# -- 1. SUMMARY ------------------------------------------------
echo "-- 1. SUMMARY --"
printf "  Journal entries:  %d\n" "$(grep -c '^## [0-9]' "$J")"
printf "  Note sections:    %d\n" "$(grep -c '^## @' "$N")"
printf "  Open tasks:       %d\n" "$(grep -c '^\[ \]' "$T")"
printf "  In-progress:      %d\n" "$(grep -c '^\[>\]' "$T" 2>/dev/null || true)"
printf "  Blocked:          %d\n" "$(grep -c '^\[-\]' "$T" 2>/dev/null || true)"
printf "  Completed tasks:  %d\n" "$( [[ -f "$TL" ]] && { grep -c '^\[x\]' "$TL" || true; } || true )"
printf "  Unique citekeys:  %d\n" "$(grep -rohP '@\w+' *.txt | grep -v '@{' | sort -u | wc -l)"
printf "  Unique tags:      %d\n" "$(grep -rohP '#\w+' *.txt | sort -u | wc -l)"
printf "  Open questions:   %d\n" "$(grep -c 'Question:' "$J" 2>/dev/null || true)"
printf "  Forward links:    %d\n" "$(grep -rc '^-> ' *.txt 2>/dev/null | awk -F: '{s+=$NF}END{print s+0}')"
printf "  Git commits:      %d\n" "$(git rev-list --count HEAD 2>/dev/null || true)"
echo

# -- 2. CONVENTION FREQUENCY -----------------------------------
echo "-- 2. CONVENTION FREQUENCY --"
echo "  Marker type counts across all files:"
grep -rohP '@\{|@\w+:\w+|@\w+\?\?|@\w+|#\w+|\?\:|\!\:|->|\[\[' *.txt 2>/dev/null \
  | sort | uniq -c | sort -rn | sed 's/^/    /'
echo
echo "  Zero-use conventions (comment-out candidates):"
found_unused=0
for pat in '@{' '[[j:' '!:' ':pp' ':ch' ':S' ':fig' ':t[0-9]'; do
  c=$(grep -rl "$pat" *.txt 2>/dev/null | wc -l)
  if (( c == 0 )); then
    printf "    %-12s  UNUSED\n" "$pat"
    found_unused=1
  fi
done
(( found_unused == 0 )) && echo "    (all conventions in use)"
echo

# -- 3. DAILY PRACTICE ADHERENCE -------------------------------
echo "-- 3. DAILY PRACTICE ADHERENCE --"
echo "  Marker totals:"
for m in "Intent:" "Done:" "Noticed:" "Question:" "Connection:"; do
  printf "    %-14s %d\n" "$m" "$(grep -c "$m" "$J" 2>/dev/null || true)"
done
echo
echo "  Per-date marker presence:"
awk '/^## [0-9]{4}-/{date=$2}
     /Intent:/{i[date]++} /Done:/{d[date]++}
     /Noticed:/{n[date]++} /Question:/{q[date]++}
     END{for(dt in i)
       printf "    %s  Intent:%d  Done:%d  Noticed:%d  Question:%d\n",
         dt, i[dt]+0, d[dt]+0, n[dt]+0, q[dt]+0
     }' "$J" | sort
echo

# -- 4. JOURNAL METRICS ----------------------------------------
echo "-- 4. JOURNAL METRICS --"
active=$(grep -oP '^\#\# \K\d{4}-\d{2}-\d{2}' "$J" | sort -u | wc -l)
printf "  Active days: %d\n" "$active"
echo "  Avg lines per entry:"
awk '/^## [0-9]{4}-/{if(n)print n; n=0; next}{n++} END{if(n)print n}' "$J" \
  | awk '{s+=$1;c++}END{if(c)printf "    %.1f lines\n", s/c; else print "    n/a"}'
echo "  Top citekeys in journal:"
grep -ohP '@\w+' "$J" | grep -v '^@{' | sort | uniq -c | sort -rn | head -10 | sed 's/^/    /'
echo
echo "  Tags by frequency:"
grep -rohP '#\w+' *.txt | sort | uniq -c | sort -rn | sed 's/^/    /'
echo

# -- 5. NOTES METRICS ------------------------------------------
echo "-- 5. NOTES METRICS --"
printf "  Note sections:        %d\n" "$(grep -c '^## @' "$N")"
printf "  Forward links:        %d\n" "$(grep -c '^-> @' "$N" 2>/dev/null || true)"
printf "  Block content lines:  %d\n" "$(grep -c '^\s*>' "$N" 2>/dev/null || true)"
printf "  Total lines:          %d\n" "$(wc -l < "$N")"
echo
echo "  Location specifier types used:"
grep -ohP '@\w+:(p|pp|ch|S|P|fig|t)\w*' "$N" 2>/dev/null \
  | sed 's/@\w*://' | grep -oP '^[a-zA-Z]+' | sort | uniq -c | sort -rn | sed 's/^/    /'
echo
echo "  Depth per citekey (subsection count):"
awk '/^## @/{if(k)print c,k; k=$2; c=0} /^- /{c++} END{if(k)print c,k}' "$N" \
  | sort -rn | head -10 | sed 's/^/    /'
echo

# -- 6. TASK METRICS -------------------------------------------
echo "-- 6. TASK METRICS --"
echo "  Status breakdown:"
grep -rohP '^\[.\]' "$T" "$TL" 2>/dev/null | sort | uniq -c | sort -rn | sed 's/^/    /'
echo
echo "  Categories:"
grep -ohP '^\[.\] \d{4}-\d{2}-\d{2} \K\w+' "$T" "$TL" 2>/dev/null \
  | sort | uniq -c | sort -rn | sed 's/^/    /'
echo
echo "  Open task ages:"
while IFS= read -r d; do
  age=$(( ( $(date +%s) - $(date -d "$d" +%s) ) / 86400 ))
  line=$(grep "^\[ \] $d" "$T" | head -1)
  printf "    %3d days  %s\n" "$age" "$line"
done < <(grep -oP '^\[ \] \K\d{4}-\d{2}-\d{2}' "$T" | sort)
echo

# -- 7. FRICTION LOG -------------------------------------------
echo "-- 7. FRICTION LOG --"
if [[ -f "$F" ]]; then
  printf "  Total entries: %d\n" "$(grep -c . "$F")"
  echo "  Categories:"
  grep -oP '^\d{4}-\d{2}-\d{2}: \K\w+' "$F" | sort | uniq -c | sort -rn | sed 's/^/    /'
  echo
  echo "  Recurring (3+, trigger: build a solution):"
  result=$(grep -oP '^\d{4}-\d{2}-\d{2}: \K\w+' "$F" | sort | uniq -c | awk '$1>=3')
  if [[ -n "$result" ]]; then
    echo "$result" | sed 's/^/    /'
  else
    echo "    (none)"
  fi
else
  echo "  _friction.txt not found (guide says log friction daily)"
fi
echo

# -- 8. ROUTING DISCIPLINE -------------------------------------
echo "-- 8. ROUTING DISCIPLINE --"
cb=$(grep -c '^\[.\]' "$J" 2>/dev/null || true)
printf "  Checkboxes in journal.txt: %d" "$cb"
(( cb > 0 )) && echo "  <- should be in tasks.txt" || echo ""
echo "  Citekeys in journal with no notes section:"
comm -23 \
  <(grep -ohP '@\w+' "$J" 2>/dev/null | grep -v '@{' | sort -u) \
  <(grep -oP '^## @\K\w+' "$N" 2>/dev/null | sort -u) \
  | sed 's/^/    /'
echo

# -- 9. ORPHANS & DEAD ENDS ------------------------------------
echo "-- 9. ORPHANS & DEAD ENDS --"
echo "  Dangling forward links (target note section missing):"
dangling=0
grep -rohP '^-> @\K\w+' "$J" "$N" 2>/dev/null | sort -u | while read -r k; do
  if ! grep -q "^## @$k" "$N" 2>/dev/null; then
    echo "    -> @$k"
  fi
done
echo
echo "  Single-reference citekeys (shallow engagement):"
grep -rohP '@\w+' "$J" "$N" 2>/dev/null | grep -v '@{' \
  | sort | uniq -c | awk '$1==1{print "    "$2}'
echo

# -- 10. GIT HISTORY -------------------------------------------
echo "-- 10. GIT HISTORY --"
if git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "  Commits per day:"
  git log --format='%ad' --date=short | sort | uniq -c | sort -k2 | sed 's/^/    /'
  echo
  echo "  Lines added per file (total):"
  git log --numstat --pretty=format: | awk 'NF==3{a[$3]+=$1}END{for(f in a)print a[f],f}' \
    | sort -rn | sed 's/^/    /'
  echo
  echo "  Files by change frequency:"
  git log --name-only --pretty=format: | grep -v '^$' | sort | uniq -c | sort -rn | sed 's/^/    /'
  echo
  echo "  Daily word count trajectory (journal.txt):"
  git log --reverse --format='%H %ad' --date=short | while read -r h d; do
    wc=$(git show "$h:$J" 2>/dev/null | wc -w)
    printf "    %s  %d words\n" "$d" "$wc"
  done
else
  echo "  (not a git repo)"
fi
echo

# -- 11. DECISION TRIGGER FLAGS --------------------------------
echo "-- 11. DECISION TRIGGER FLAGS --"
# Intent completion
intent_c=$(grep -c 'Intent:' "$J" 2>/dev/null || true)
done_c=$(grep -c 'Done:' "$J" 2>/dev/null || true)
if (( intent_c > 0 )); then
  pct=$(( done_c * 100 / intent_c ))
  printf "  Intent->Done rate: %d%% (%d/%d)\n" "$pct" "$done_c" "$intent_c"
  (( pct < 50 )) && echo "    WARNING: Below 50% -- consider simplifying"
else
  echo "  Intent->Done rate: n/a (no Intent: markers found)"
fi

q_c=$(grep -c 'Question:' "$J" 2>/dev/null || true)
printf "  Open questions captured: %d" "$q_c"
(( q_c == 0 )) && echo "  (none -- drop Question: or start using it)" || echo ""

conn_c=$(grep -c 'Connection:' "$J" 2>/dev/null || true)
printf "  Connections captured: %d" "$conn_c"
(( conn_c == 0 )) && echo "  (none -- let emerge naturally)" || echo ""

echo
echo "================================================================"
echo "  Report saved to: $OUT"
echo "  Reviewed: $(date +%Y-%m-%d)"
echo "================================================================"

} > "$OUT" 2>&1

echo "Audit complete -> $OUT"
