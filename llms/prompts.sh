# =============================================================================
# PROMPT LIBRARY
# =============================================================================
#
# PMT_PROMPTS_DIR: absolute path to the prompts directory.
# Update this when the prompts location changes.
#
PMT_PROMPTS_DIR="$HOME/personal_repos/explorations-proj-llms/llms/prompts"

# --- internal: verify prompts directory exists ---------------------------
_pmt_ensure_dir() {
    if [ ! -d "$PMT_PROMPTS_DIR" ]; then
        echo "pmt: error: prompts directory not found: $PMT_PROMPTS_DIR"
        echo "update PMT_PROMPTS_DIR in .bashrc"
        return 1
    fi
    return 0
}

# --- pnew: create a new prompt file from clipboard and open it -----------
pnew() {
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        cat <<'EOF'
pnew - create a new prompt file from clipboard contents

Usage:
  pnew <filename>

Arguments:
  filename    Name of the prompt file. .md appended if missing.

Behavior:
  Writes clipboard contents to PMT_PROMPTS_DIR/<filename>.md
  Opens the new file in $EDITOR.
  Errors if the file already exists.
EOF
        return 0
    fi

    _pmt_ensure_dir || return 1

    if [ -z "$1" ]; then
        echo "pmt: error: filename required"
        echo "usage: pnew <filename>"
        return 1
    fi

    if ! command -v powershell.exe &>/dev/null; then
        echo "pmt: error: powershell.exe not found - clipboard paste unavailable"
        return 1
    fi

    local filename="$1"
    if [ "${filename%.md}" = "$filename" ]; then
        filename="${filename}.md"
    fi

    local filepath="$PMT_PROMPTS_DIR/$filename"

    if [ -f "$filepath" ]; then
        echo "pmt: error: file already exists: $filename"
        return 1
    fi

    powershell.exe -NoProfile -Command Get-Clipboard > "$filepath"
    echo "pmt: clipboard pasted into $filename"

    "${EDITOR:-nvim}" "$filepath"
}

# --- popen: open a prompt file by name -----------------------------------
popen() {
    if [ "$1" = "-h" ] || [ "$1" = "--help" ]; then
        cat <<'EOF'
popen - open a prompt file for editing

Usage:
  popen [filename]

Arguments:
  filename    Name of the prompt file. .md appended if missing.
              If omitted, lists available prompt files and exits.

Behavior:
  Opens PMT_PROMPTS_DIR/<filename>.md in $EDITOR.
  No side effects.
EOF
        return 0
    fi

    _pmt_ensure_dir || return 1

    if [ -z "$1" ]; then
        local found=0
        for filepath in "$PMT_PROMPTS_DIR"/*.md; do
            if [ -f "$filepath" ]; then
                basename "$filepath" .md
                found=1
            fi
        done
        if [ "$found" -eq 0 ]; then
            echo "pmt: no prompt files found in $PMT_PROMPTS_DIR"
        fi
        return 0
    fi

    local filename="$1"
    if [ "${filename%.md}" = "$filename" ]; then
        filename="${filename}.md"
    fi

    local filepath="$PMT_PROMPTS_DIR/$filename"

    if [ ! -f "$filepath" ]; then
        echo "pmt: error: file not found: $filename"
        echo "use pnew $1 to create it"
        return 1
    fi

    "${EDITOR:-nvim}" "$filepath"
}
