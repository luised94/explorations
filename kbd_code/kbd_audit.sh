#!/usr/bin/env bash
# kbd-audit.sh -- consolidated metrics for kbd plain-text note system
# Usage: bash kbd-audit.sh [output_file]
set -u

# -- CONFIGURATION -------------------------------------------------
KBD_DIR="${KBD_LOCAL_DIR:-$HOME/personal_repos/kbd}"

if [[ ! -d "$KBD_DIR" ]]; then
  echo "kbd[ERROR]: directory not found: $KBD_DIR" >&2
  echo "  Set KBD_LOCAL_DIR or check the default path." >&2
  exit 1
fi

JOURNAL_FILE="$KBD_DIR/journal.txt"
SOURCE_NOTES_FILE="$KBD_DIR/source-notes.txt"
AUDIT_DIR="$KBD_DIR/audit_logs"
OUTPUT_FILE="${1:-${AUDIT_DIR}/audit_$(date +%Y-%m-%d).txt}"

# -- PREPROCESSING -------------------------------------------------
for file in "$JOURNAL_FILE" "$SOURCE_NOTES_FILE"; do
  [[ -f "$file" ]] || { echo "kbd[ERROR]: missing $(basename "$file") in $KBD_DIR" >&2; exit 1; }
done

mkdir -p "$AUDIT_DIR"

PROJECT_FILES=()
if ls "$KBD_DIR"/projects/*.txt 1>/dev/null 2>&1; then
  PROJECT_FILES=("$KBD_DIR"/projects/*.txt)
fi

ALL_TEXT_FILES=("$JOURNAL_FILE" "$SOURCE_NOTES_FILE" "${PROJECT_FILES[@]}")

# -- MAIN LOGIC ----------------------------------------------------
{
cat <<EOF
================================================================
  kbd audit -- $(date +%Y-%m-%d\ %H:%M)
================================================================
EOF

# -- 1. SUMMARY ------------------------------------------------
echo "-- 1. SUMMARY --"
printf "  Journal entries:  %d\n" "$(grep -c '^## [0-9]' "$JOURNAL_FILE")"
printf "  Note sections:    %d\n" "$(grep -c '^## @' "$SOURCE_NOTES_FILE")"
printf "  Project files:    %d\n" "${#PROJECT_FILES[@]}"
printf "  Unique citekeys:  %d\n" "$(grep -rohP '@\w+' "${ALL_TEXT_FILES[@]}" 2>/dev/null | grep -v '@{' | sort -u | wc -l)"
printf "  Unique tags:      %d\n" "$(grep -rohP '#\w+' "${ALL_TEXT_FILES[@]}" 2>/dev/null | sort -u | wc -l)"
printf "  Open questions:   %d\n" "$(grep -rc '\?:' "$JOURNAL_FILE" "$SOURCE_NOTES_FILE" "${PROJECT_FILES[@]}" 2>/dev/null | awk -F: '{s+=$NF}END{print s+0}')"
printf "  Forward links:    %d\n" "$(grep -rc '^-> ' "${ALL_TEXT_FILES[@]}" 2>/dev/null | awk -F: '{s+=$NF}END{print s+0}')"
printf "  Git commits:      %d\n" "$(git -C "$KBD_DIR" rev-list --count HEAD 2>/dev/null || true)"
echo

# -- 2. CONVENTION FREQUENCY -----------------------------------
echo "-- 2. CONVENTION FREQUENCY --"
echo "  Marker type counts across all files:"
grep -rohP '@\{|@\w+:\w+|@\w+\?\?|@\w+|#\w+|\?\:|\!\:|->|\[\[' "${ALL_TEXT_FILES[@]}" 2>/dev/null \
  | sort | uniq -c | sort -rn | sed 's/^/    /'
echo

echo "  Zero-use conventions (comment-out candidates):"
found_unused=0
for pattern in '@{' '!:' ':pp' ':ch' ':S' ':fig' ':t[0-9]'; do
  match_count=$(grep -rl "$pattern" "${ALL_TEXT_FILES[@]}" 2>/dev/null | wc -l)
  if (( match_count == 0 )); then
    printf "    %-12s  UNUSED\n" "$pattern"
    found_unused=1
  fi
done
(( found_unused == 0 )) && echo "    (all conventions in use)"
echo

# -- 3. JOURNAL METRICS ----------------------------------------
echo "-- 3. JOURNAL METRICS --"
active_days=$(grep -oP '^\#\# \K\d{4}-\d{2}-\d{2}' "$JOURNAL_FILE" | sort -u | wc -l)
printf "  Active days: %d\n" "$active_days"

echo "  Avg lines per entry:"
awk '/^## [0-9]{4}-/{if(line_count)print line_count; line_count=0; next}{line_count++} END{if(line_count)print line_count}' "$JOURNAL_FILE" \
  | awk '{sum+=$1; entries++}END{if(entries)printf "    %.1f lines\n", sum/entries; else print "    n/a"}'

echo "  Top citekeys in journal:"
grep -ohP '@\w+' "$JOURNAL_FILE" | grep -v '^@{' | sort | uniq -c | sort -rn | head -10 | sed 's/^/    /'
echo

echo "  Tags by frequency (all files):"
grep -rohP '#\w+' "${ALL_TEXT_FILES[@]}" 2>/dev/null | sort | uniq -c | sort -rn | sed 's/^/    /'
echo

# -- 4. SOURCE NOTES METRICS -----------------------------------
echo "-- 4. SOURCE NOTES METRICS --"
printf "  Note sections:        %d\n" "$(grep -c '^## @' "$SOURCE_NOTES_FILE")"
printf "  Forward links:        %d\n" "$(grep -c '^-> @' "$SOURCE_NOTES_FILE" 2>/dev/null || true)"
printf "  Block content lines:  %d\n" "$(grep -c '^\s*>' "$SOURCE_NOTES_FILE" 2>/dev/null || true)"
printf "  Open questions:       %d\n" "$(grep -c '\?:' "$SOURCE_NOTES_FILE" 2>/dev/null || true)"
printf "  Total lines:          %d\n" "$(wc -l < "$SOURCE_NOTES_FILE")"
echo

echo "  Location specifier types used:"
grep -ohP '@\w+:(p|pp|ch|S|P|fig|t)\w*' "$SOURCE_NOTES_FILE" 2>/dev/null \
  | sed 's/@\w*://' | grep -oP '^[a-zA-Z]+' | sort | uniq -c | sort -rn | sed 's/^/    /'
echo

echo "  Depth per citekey (subsection count):"
awk '/^## @/{if(citekey)print subsection_count,citekey; citekey=$2; subsection_count=0} /^- /{subsection_count++} END{if(citekey)print subsection_count,citekey}' "$SOURCE_NOTES_FILE" \
  | sort -rn | head -10 | sed 's/^/    /'
echo

# -- 5. PROJECTS -----------------------------------------------
echo "-- 5. PROJECTS --"
if (( ${#PROJECT_FILES[@]} > 0 )); then
  echo "  Active projects:"
  for project_file in "${PROJECT_FILES[@]}"; do
    project_name=$(basename "$project_file" .txt)
    line_count=$(wc -l < "$project_file")
    citekey_count=$(grep -ohP '@\w+' "$project_file" 2>/dev/null | grep -v '@{' | sort -u | wc -l)
    question_count=$(grep -c '\?:' "$project_file" 2>/dev/null || true)
    printf "    %-25s %4d lines, %2d citekeys, %2d open questions\n" "$project_name" "$line_count" "$citekey_count" "$question_count"
  done
else
  echo "  (no project files yet)"
fi
echo

# -- 6. DAILY LOG ----------------------------------------------
echo "-- 6. DAILY LOG --"
if ls "$KBD_DIR"/daily_log/*.txt 1>/dev/null 2>&1; then
  entry_count=$(cat "$KBD_DIR"/daily_log/*.txt 2>/dev/null | grep -c '^- ' || true)
  file_count=$(ls "$KBD_DIR"/daily_log/*.txt | wc -l)
  printf "  Log files: %d, total entries: %d\n" "$file_count" "$entry_count"
else
  echo "  (no daily log files yet)"
fi
echo

# -- 7. ROUTING DISCIPLINE -------------------------------------
echo "-- 7. ROUTING DISCIPLINE --"
echo "  Citekeys in journal with no notes section:"
comm -23 \
  <(grep -ohP '@\w+' "$JOURNAL_FILE" 2>/dev/null | grep -v '@{' | sort -u) \
  <(grep -oP '^## @\K\w+' "$SOURCE_NOTES_FILE" 2>/dev/null | sort -u) \
  | sed 's/^/    /'
echo

# -- 8. ORPHANS & DEAD ENDS ------------------------------------
echo "-- 8. ORPHANS & DEAD ENDS --"
echo "  Dangling forward links (target note section missing):"
grep -rohP '^-> @\K\w+' "$JOURNAL_FILE" "$SOURCE_NOTES_FILE" "${PROJECT_FILES[@]}" 2>/dev/null | sort -u | while read -r citekey; do
  if ! grep -q "^## @$citekey" "$SOURCE_NOTES_FILE" 2>/dev/null; then
    echo "    -> @$citekey"
  fi
done
echo

echo "  Single-reference citekeys (shallow engagement):"
grep -rohP '@\w+' "$JOURNAL_FILE" "$SOURCE_NOTES_FILE" "${PROJECT_FILES[@]}" 2>/dev/null | grep -v '@{' \
  | sort | uniq -c | awk '$1==1{print "    "$2}'
echo

# -- 9. GIT HISTORY -------------------------------------------
echo "-- 9. GIT HISTORY --"
if git -C "$KBD_DIR" rev-parse --is-inside-work-tree &>/dev/null; then
  echo "  Commits per day:"
  git -C "$KBD_DIR" log --format='%ad' --date=short | sort | uniq -c | sort -k2 | sed 's/^/    /'
  echo

  echo "  Lines added per file (total):"
  git -C "$KBD_DIR" log --numstat --pretty=format: | awk 'NF==3{added[$3]+=$1}END{for(file in added)print added[file],file}' \
    | sort -rn | sed 's/^/    /'
  echo

  echo "  Files by change frequency:"
  git -C "$KBD_DIR" log --name-only --pretty=format: | grep -v '^$' | sort | uniq -c | sort -rn | sed 's/^/    /'
  echo

  echo "  Daily word count trajectory (journal.txt):"
  git -C "$KBD_DIR" log --reverse --format='%H %ad' --date=short | while read -r commit_hash commit_date; do
    word_count=$(git -C "$KBD_DIR" show "$commit_hash:journal.txt" 2>/dev/null | wc -w)
    printf "    %s  %d words\n" "$commit_date" "$word_count"
  done
else
  echo "  (not a git repo)"
fi
echo

# -- 10. DECISION TRIGGER FLAGS --------------------------------
echo "-- 10. DECISION TRIGGER FLAGS --"
question_total=$(grep -rc '\?:' "$JOURNAL_FILE" "$SOURCE_NOTES_FILE" "${PROJECT_FILES[@]}" 2>/dev/null | awk -F: '{s+=$NF}END{print s+0}')
printf "  Open questions (?:): %d\n" "$question_total"
(( question_total > 10 )) && echo "    FLAG: >10 unresolved -- review and resolve or drop"
echo

# -- OUTPUT --------------------------------------------------------
echo "================================================================"
echo "  Report saved to: $OUTPUT_FILE"
echo "  Reviewed: $(date +%Y-%m-%d)"
echo "================================================================"
} > "$OUTPUT_FILE" 2>&1

echo "Audit complete -> $OUTPUT_FILE"
