# Prompt library shell functions.
# Source this file from your bashrc: source /home/luis/personal_repos/explorations-proj-llms/prompts/_pmt.sh

PROMPTS_DIR="$HOME/personal_repos/explorations-proj-llms/llms/prompts"
FRICTION_FILEPATH="$HOME/personal_repos/explorations-proj-llms/llms/FRICTION.md"

_pmt_check_dir() {
    [[ -d "$PROMPTS_DIR" ]] && return 0
    echo "pmt: error: PROMPTS_DIR does not exist: $PROMPTS_DIR"
    return 1
}

pnew() {
    _pmt_check_dir || return 1
    local name="${1}"
    [[ -z "$name" ]] && { echo "pmt: usage: pnew <filename>"; return 1; }
    [[ "$name" != *.md ]] && name="${name}.md"
    local target="$PROMPTS_DIR/$name"
    [[ -f "$target" ]] && { echo "pmt: error: $name already exists"; return 1; }
    powershell.exe -NoProfile -Command Get-Clipboard > "$target"
    echo "pmt: clipboard pasted into $name"
    "${EDITOR:-nvim}" "$target"
}

plog() {
    _pmt_check_dir || return 1
    local friction_filepath="$FRICTION_FILEPATH"
    local stub
    stub="$(printf '\n## %s  [severity]\nWhat I was trying to do.\nWhat actually happened or what annoyed me.\n?: idea or fix if one comes to mind\n' "$(date '+%Y-%m-%d %H:%M')")"
    echo "$stub" >> "$friction_filepath"
    "${EDITOR:-nvim}" + "$friction_filepath"
}
