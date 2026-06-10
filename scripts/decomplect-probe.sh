#!/usr/bin/env bash
# decomplect-probe.sh -- Diagnostic probe for the Decomplection Playbook
# Gathers impurity map, handler inventory, hidden inputs, duplication,
# and structure metrics into a plain-text report.
#
# Usage: bash decomplect-probe.sh <filepath>
# Output: <filepath>.probe-report.txt
#
# Design: linear procedural script. Each section is a pure-ish gather
# (read file, emit lines to stdout) piped into the report. No mutation
# of the source file. No dependencies beyond coreutils + awk + grep.

set -euo pipefail

# -- ARGUMENTS ----------------------------------------------------------------

if [[ $# -lt 1 ]]; then
    echo "Usage: $0 <python-file>" >&2
    exit 1
fi

src="$1"

if [[ ! -f "$src" ]]; then
    echo "Error: file not found: $src" >&2
    exit 1
fi

today=$(date +%F)
report="${src}.probe-report.txt"

# -- HELPERS (pure: stdin/args -> stdout, no side effects) --------------------

# Impurity patterns used throughout -- defined once, used as data
IMPURITY_PATTERN='print\(|sys\.exit|date\.today|datetime\.now|os\.environ|os\.getenv|open\(|random\.|input\('

section() {
    # section TITLE -- emit a section header
    printf '\n%s\n%s\n' "## $1" "$(printf '=%.0s' {1..70})"
}

separator() {
    printf '%s\n' "$(printf '%.0s-' {1..70})"
}

# -- REPORT ASSEMBLY ----------------------------------------------------------
# Each block: section header, then the gathered data. Written sequentially
# to the report file. No intermediate state between sections.

{
    printf '%s\n' "# Decomplection Probe Report"
    printf '%s\n' "# Source: $src"
    printf '%s\n' "# Generated: $today"
    printf '%s\n' "# Playbook ref: v1.1"

    # -- 1. SIZE AND STRUCTURE ------------------------------------------------
    section "1. Size and Structure"

    total=$(wc -l < "$src")
    blank=$(grep -c "^$" "$src" || true)
    comments=$(grep -c "^ *#" "$src" || true)
    code=$((total - blank - comments))
    functions=$(grep -c "^def " "$src" || true)
    nested_functions=$(grep -c "^    def " "$src" || true)
    classes=$(grep -c "^class " "$src" || true)
    imports=$(grep -c "^import \|^from " "$src" || true)

    printf 'Total lines:      %d\n' "$total"
    printf 'Code lines:       %d  (blank: %d, comment: %d)\n' "$code" "$blank" "$comments"
    printf 'Top-level defs:   %d\n' "$functions"
    printf 'Nested defs:      %d\n' "$nested_functions"
    printf 'Classes:          %d\n' "$classes"
    printf 'Imports:          %d\n' "$imports"

    # -- 2. FUNCTION MAP (line number + name) ---------------------------------
    section "2. Function Map"
    printf '(top-level functions with line numbers)\n\n'
    grep -n "^def " "$src" | sed 's/def //' | sed 's/(.*/:/' || printf '(none)\n'

    # -- 3. TOTAL IMPURITY COUNT ---------------------------------------------
    section "3. Impurity Summary"

    total_hits=$(grep -cE "$IMPURITY_PATTERN" "$src" || true)
    prints=$(grep -c "print(" "$src" || true)
    exits=$(grep -c "sys\.exit" "$src" || true)
    clocks=$(grep -cE "date\.today|datetime\.now" "$src" || true)
    opens=$(grep -c "open(" "$src" || true)
    envs=$(grep -cE "os\.environ|os\.getenv" "$src" || true)
    randoms=$(grep -c "random\." "$src" || true)
    inputs=$(grep -c "input(" "$src" || true)

    printf 'Total impurity hits: %d\n\n' "$total_hits"
    printf '  print(        %4d\n' "$prints"
    printf '  sys.exit      %4d\n' "$exits"
    printf '  date/time     %4d\n' "$clocks"
    printf '  open(         %4d\n' "$opens"
    printf '  os.environ    %4d\n' "$envs"
    printf '  random.       %4d\n' "$randoms"
    printf '  input(        %4d\n' "$inputs"

    # -- 4. IMPURITY DENSITY PER FUNCTION ------------------------------------
    section "4. Impurity Density per Function (ranked)"
    printf '(count of impure calls per top-level function, highest first)\n\n'

    awk '
    /^def / { fn = $0; sub(/[(].*/, "", fn); sub(/^def /, "", fn); current_fn = fn }
    /^[^ \t]/ && !/^def / { current_fn = "(module-level)" }
    {
        if (current_fn && match($0, /print[(]|sys[.]exit|date[.]today|datetime[.]now|os[.]environ|os[.]getenv|open[(]|random[.]|input[(]/)) {
            counts[current_fn]++
        }
    }
    END {
        for (f in counts) print counts[f] "\t" f
    }
    ' "$src" | sort -rn || printf '(none)\n'

    # -- 5. IMPURITY DETAIL PER FUNCTION -------------------------------------
    section "5. Impurity Detail (per function, with line numbers)"
    printf '(each impure call with its enclosing function)\n\n'

    awk -v pat="print[(]|sys[.]exit|date[.]today|datetime[.]now|os[.]environ|os[.]getenv|open[(]|random[.]|input[(]" '
    /^def / {
        fn = $0; sub(/\(.*/, "", fn); sub(/^def /, "", fn)
        current_fn = fn
    }
    /^[^ \t]/ && !/^def / && !/^class / { current_fn = "(module-level)" }
    {
        if (match($0, pat)) {
            line = $0; sub(/^[ \t]+/, "", line)
            printf "%5d  %-30s  %s\n", NR, current_fn, line
        }
    }
    ' "$src" || printf '(none)\n'

    # -- 6. HANDLER / DISPATCH DETECTION (H1) --------------------------------
    section "6. Handler / Dispatch Detection (H1)"
    printf '(functions matching handle_/cmd_/do_ patterns + dispatch structures)\n\n'

    printf "=== Handler-shaped functions ===\n"
    grep -n "^def handle_\|^def cmd_\|^def do_\|^def run_" "$src" || printf '(none)\n'

    printf '\n--- Dispatch structures (if/elif chains, dicts) ---\n'
    grep -n "elif.*==\|dispatch\|COMMANDS\|command_map\|CMD_" "$src" | head -30 || printf '(none)\n'

    # -- 7. MODULE-LEVEL SIDE EFFECTS (Phase 0 targets) ----------------------
    section "7. Module-Level Side Effects (Phase 0 targets)"
    printf '(non-import, non-def, non-constant code at indent 0)\n\n'

    grep -n "^[a-z]" "$src" | grep -vE "^[0-9]+:(def |class |import |from |#)" || printf '(none -- clean for Phase 0)\n'

    # -- 8. HIDDEN CLOCK CALLS -----------------------------------------------
    section "8. Hidden Clock Calls (P3)"
    printf '(every date/time/sleep access with line number)\n\n'

    grep -n "date\.today\|datetime\.now\|time\.time\|time\.sleep\|time\.strftime" "$src" || printf '(none)\n'

    # -- 9. FILE IO CALLS ----------------------------------------------------
    section "9. File IO Calls"
    printf '(every open() and file-adjacent call with line number)\n\n'

    grep -n "open(\|\.read()\|\.write(\|\.readlines\|json\.load\|json\.dump\|yaml\.\|toml\.\|csv\." "$src" || printf '(none)\n'

    # -- 10. STATE ENCODING SMELLS (H4, P5) ----------------------------------
    section "10. State Encoding Smells (H4, P5)"
    printf '(status fields, filename assignments, bucket/category references)\n\n'

    grep -n "status\|bucket\|category\|\.txt\|\.json\|filename\|filepath\|active\|done\|archive\|completed" "$src" | head -40 || printf '(none)\n'

    # -- 11. DUPLICATE LINE DETECTION (H2) -----------------------------------
    section "11. Duplicate Lines (H2 -- copy-paste smell)"
    printf '(non-trivial lines appearing 3+ times)\n\n'

    awk 'length > 35 { gsub(/^[ \t]+/, ""); counts[$0]++; lines[$0] = lines[$0] " " NR }
    END { for (l in counts) if (counts[l] >= 3) printf "%3dx  %s\n      lines:%s\n", counts[l], l, lines[l] }
    ' "$src" | sort -rn | head -30 || printf '%s\n' '(none)'

    # -- 12. CLASS INVENTORY -------------------------------------------------
    section "12. Class Inventory"
    printf '(all class definitions -- R2 targets for removal)\n\n'

    grep -n "^class " "$src" || printf '(none)\n'

    # -- 13. CALLER MAP FOR SHARED HELPERS (T1) ------------------------------
    section "13. Shared Helper Caller Counts (T1)"
    printf '(top-level functions sorted by how many other functions call them)\n'
    printf '(high counts = shared helpers that couple migration order)\n\n'

    # Extract function names, then count references to each
    grep -oP "^def \K[a-zA-Z_][a-zA-Z0-9_]*" "$src" | while read -r fname; do
        count=$(grep -c "$fname" "$src" || true)
        # subtract 1 for the def line itself
        refs=$((count - 1))
        if [[ $refs -gt 1 ]]; then
            printf '%4d refs  %s\n' "$refs" "$fname"
        fi
    done | sort -rn | head -30 || printf '(none)\n'

    # -- 14. PLAYBOOK APPLICABILITY CHECK ------------------------------------
    section "14. Playbook Applicability Check"

    printf 'Scope conditions (Decomplection Playbook v1.1):\n\n'

    if [[ $total -lt 100 ]]; then
        printf '[!] File is only %d lines -- may be too small for full playbook.\n' "$total"
    elif [[ $total -gt 3500 ]]; then
        printf '[!] File is %d lines -- exceeds typical 1-3k range. Consider splitting probe.\n' "$total"
    else
        printf '[ok] File size (%d lines) within playbook range.\n' "$total"
    fi

    if [[ $classes -gt 0 ]]; then
        printf '[!] %d class(es) found -- playbook targets plain functions/dicts (R2).\n' "$classes"
    else
        printf '[ok] No classes.\n'
    fi

    if [[ $total_hits -gt 0 ]]; then
        printf '[ok] %d impurity hits -- the disease is present; playbook applies.\n' "$total_hits"
    else
        printf '[?] Zero impurity hits -- file may already be clean. Verify manually.\n'
    fi

    if grep -qE "async def |await |asyncio\." "$src"; then
        printf '[!] Async/await detected -- concurrency is out of playbook scope.\n'
    else
        printf '[ok] No async patterns.\n'
    fi

    if grep -qE "Thread\(|threading\.|multiprocessing\." "$src"; then
        printf '[!] Threading/multiprocessing detected -- out of playbook scope.\n'
    else
        printf '[ok] No threading/multiprocessing.\n'
    fi

    section "END OF REPORT"

} > "$report"

echo "Report written to: $report" >&2
echo "$(wc -l < "$report") lines" >&2
