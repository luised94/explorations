# =============================================================================
# SM-2 EXERCISE AUTHORING
# =============================================================================
#
# EX_EXERCISES_DIR: absolute path to the exercises directory.
# Update this when the exercises location changes (worktree -> USB, etc.).
#
EX_EXERCISES_DIR="$KBD_DIR/recall"

# --- internal: verify exercises directory exists -------------------------
_ex_ensure_dir() {
    if [ ! -d "$EX_EXERCISES_DIR" ]; then
        echo "error: exercises directory not found: $EX_EXERCISES_DIR"
        echo "update EX_EXERCISES_DIR in .bashrc"
        return 1
    fi
    return 0
}

# --- exnew: append stub to domain file and open --------------------------
exnew() {
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        cat <<'EOF'
exnew - append a new item stub to a domain exercise file and open it
Usage:
  exnew [domain]
Arguments:
  domain    Exercise domain (e.g. c, bio, drive). Required.
            Must be one word: lowercase alphanumeric, no dashes.
Behavior:
  Creates exercises/{domain}.md if it does not exist.
  Appends a formatted stub with id prefix pre-filled.
  Opens the file in $EDITOR at the last line.
  Warns if the stub marker is left unfilled on exit.
EOF
        return 0
    fi
    if [ -z "$1" ]; then
        echo "error: domain required"
        echo "usage: exnew [domain]"
        return 1
    fi
    _ex_ensure_dir || return 1
    local domain="$1"
    if ! [[ "$domain" =~ ^[a-z0-9]+$ ]]; then
        echo "error: domain must be one word, lowercase alphanumeric, no dashes"
        return 1
    fi
    local filepath="$EX_EXERCISES_DIR/${domain}.md"
    local stub
    local stub_marker="!!!"
    stub="$(printf '\n@@@ id: %s-%s\ncriteria: \ntags: \nsource: \n' "$domain" "$stub_marker")"
    echo "$stub" >> "$filepath" || {
        echo "error: failed to append to $filepath"
        return 1
    }
    # +/pattern: open nvim with cursor on first search match
    "${EDITOR:-nvim}" "+/${stub_marker}" "$filepath"
    if grep -q "id: ${domain}-${stub_marker}" "$filepath"; then
        echo "warning: unfilled stub remains in $filepath"
    fi
}

# --- exopen: open a domain exercise file without appending ---------------
exopen() {
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        cat <<'EOF'
exopen - open a domain exercise file for editing
Usage:
  exopen [domain]
Arguments:
  domain    Exercise domain (e.g. c, bio, drive).
            If omitted, lists available domains and exits.
Behavior:
  Opens exercises/{domain}.md in $EDITOR.
  No stub is appended. No side effects.
EOF
        return 0
    fi
    _ex_ensure_dir || return 1
    if [ -z "$1" ]; then
        local found=0
        for filepath in "$EX_EXERCISES_DIR"/*.md; do
            if [ -f "$filepath" ]; then
                basename "$filepath" .md
                found=1
            fi
        done
        if [ "$found" -eq 0 ]; then
            echo "no domain files found in $EX_EXERCISES_DIR"
        fi
        return 0
    fi
    local domain="$1"
    local filepath="$EX_EXERCISES_DIR/${domain}.md"
    if [ ! -f "$filepath" ]; then
        echo "error: no exercise file for domain '${domain}': $filepath"
        echo "use exnew ${domain} to create it"
        return 1
    fi
    "${EDITOR:-nvim}" + "$filepath"
}

# --- exfind: search item ids across all domain files ---------------------
exfind() {
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        cat <<'EOF'
exfind - search item ids across all domain files
Usage:
  exfind [fragment]
Arguments:
  fragment  Substring to match against item ids. Required.
            Matching is case-insensitive.
Behavior:
  Greps '@@@ id:' lines across all exercises/*.md files.
  Prints matching file, line number, and id line.
EOF
        return 0
    fi
    _ex_ensure_dir || return 1
    if [ -z "$1" ]; then
        echo "error: id fragment required"
        echo "usage: exfind [fragment]"
        return 1
    fi
    grep -rin "@@@ id:.*$1" "$EX_EXERCISES_DIR"/*.md
}
