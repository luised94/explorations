#!/bin/bash
# kbd-import-phone-notes - import phone capture files into kbd daily_log
# Usage: kbd-import-phone-notes FILE [FILE...]
# See kbd_code/kbd-import-phone-notes.md for full spec.
set -u

# -- Configuration --
KBD_DIR="${KBD_LOCAL_DIR:-$HOME/personal_repos/kbd}"
DAILY_LOG_DIR="$KBD_DIR/daily_log"

# -- Usage --
print_usage() {
    cat <<'EOF'
Usage: kbd-import-phone-notes FILE [FILE...]

Import dated phone capture files into kbd daily_log.
Files must match pattern: YYMMDD_*.txt

Examples:
  kbd-import-phone-notes ~/Downloads/250115_daily.txt
  kbd-import-phone-notes /tmp/phone/*.txt
EOF
}

# -- Guards --
if [[ $# -eq 0 ]]; then
    print_usage
    exit 1
fi

if [[ "$1" == "-h" || "$1" == "--help" ]]; then
    print_usage
    exit 0
fi

if [[ ! -d "$KBD_DIR" ]]; then
    echo "kbd-import-phone-notes[ERROR]: KBD_DIR not a directory: $KBD_DIR" >&2
    exit 1
fi

if [[ ! -d "$DAILY_LOG_DIR" ]]; then
    mkdir -p "$DAILY_LOG_DIR"
    echo "kbd-import-phone-notes: created $DAILY_LOG_DIR"
fi

# -- Counters --
count_imported=0
count_skipped=0
count_errors=0

# -- Process each file --
for input_file in "$@"; do
    input_basename=$(basename "$input_file")

    # Validate filename pattern: YYMMDD_*.txt
    if [[ ! "$input_basename" =~ ^[0-9]{6}_.+\.txt$ ]]; then
        echo "error:    $input_basename -> filename does not match YYMMDD_*.txt" >&2
        count_errors=$((count_errors + 1))
        continue
    fi

    # Validate file is readable
    if [[ ! -r "$input_file" ]]; then
        echo "error:    $input_basename -> file not readable" >&2
        count_errors=$((count_errors + 1))
        continue
    fi

    # Extract date components from filename
    date_prefix="${input_basename:0:6}"
    year_short="${date_prefix:0:2}"
    month="${date_prefix:2:2}"
    day="${date_prefix:4:2}"
    year_full="20${year_short}"

    # Validate date components are reasonable
    if [[ "$month" -lt 1 || "$month" -gt 12 || "$day" -lt 1 || "$day" -gt 31 ]]; then
        echo "error:    $input_basename -> invalid date in filename (${year_full}-${month}-${day})" >&2
        count_errors=$((count_errors + 1))
        continue
    fi

    # Extract slug (portion between YYMMDD_ and .txt)
    slug="${input_basename:7}"
    slug="${slug%.txt}"

    # Build target path and separator
    monthly_file="$DAILY_LOG_DIR/${year_short}${month}.txt"
    date_separator="## ${year_full}-${month}-${day} ${slug}"

    # Check for duplicate import (idempotent guard)
    if [[ -f "$monthly_file" ]]; then
        if grep -qFx "$date_separator" "$monthly_file"; then
            echo "skipped:  $input_basename -> already in daily_log/${year_short}${month}.txt"
            count_skipped=$((count_skipped + 1))
            continue
        fi
    fi

    # Read content and strip Windows line endings
    file_content=$(tr -d '\r' < "$input_file")
    line_count=$(echo "$file_content" | wc -l)

    # Append: separator + blank line + content + trailing newline
    {
        echo "$date_separator"
        echo ""
        echo "$file_content"
        echo ""
    } >> "$monthly_file"

    echo "imported: $input_basename -> daily_log/${year_short}${month}.txt ($line_count lines)"
    count_imported=$((count_imported + 1))
done

# -- Summary --
echo "---"
echo "done: $count_imported imported, $count_skipped skipped, $count_errors errors"

# Exit status: 0 if any succeeded, 1 if all failed
if [[ $count_imported -eq 0 && $count_skipped -eq 0 ]]; then
    exit 1
fi
exit 0
