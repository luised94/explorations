# =============================================================================
# SM-2 EXERCISE AUTHORING
# =============================================================================
#
# EX_EXERCISES_DIR: absolute path to the exercises directory.
# Update this when the exercises location changes (worktree -> USB, etc.).
#
EX_EXERCISES_DIR="$HOME/personal_repos/explorations/sm2/exercises"

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

Behavior:
  Creates exercises/{domain}.md if it does not exist.
  Appends a formatted stub with id prefix pre-filled.
  Opens the file in $EDITOR at the last line.
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
    local filepath="$EX_EXERCISES_DIR/${domain}.md"

    local stub
    local stub_marker="!!!"
    stub="$(printf '\n@@@ id: %s-%s\ncriteria: \ntags: \nsource: \n' "$domain" "$stub_marker")"
    echo "$stub" >> "$filepath"

    # +/pattern: open nvim with cursor on first search match
    "${EDITOR:-nvim}" "+/${stub_marker}" "$filepath"
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
