# Prompt library shell functions.
# Source this file from your bashrc: source /home/luis/personal_repos/explorations-proj-llms/llms/prompts/_pmt.sh

PROMPTS_DIRECTORY="$HOME/personal_repos/explorations-proj-llms/llms/prompts"
FRICTION_FILEPATH="$HOME/personal_repos/explorations-proj-llms/llms/FRICTION.md"

_pmt_warn_if_environment_invalid() {
    local red='\033[0;31m'
    local reset='\033[0m'
    [[ ! -d "$PROMPTS_DIRECTORY" ]] && \
        printf "${red}pmt: warning: PROMPTS_DIRECTORY does not exist: %s${reset}\n" "$PROMPTS_DIRECTORY"
    [[ ! -f "$FRICTION_FILEPATH" ]] && \
        printf "${red}pmt: warning: FRICTION_FILEPATH does not exist: %s${reset}\n" "$FRICTION_FILEPATH"
    ! command -v "${EDITOR:-nvim}" &>/dev/null && \
        printf "${red}pmt: warning: editor not found: %s${reset}\n" "${EDITOR:-nvim}"
    ! command -v powershell.exe &>/dev/null && \
        printf "${red}pmt: warning: powershell.exe not found - pnew clipboard paste will fail${reset}\n"
}
_pmt_warn_if_environment_invalid

pnew() {
    [[ "$1" == "-h" || "$1" == "--help" ]] && {
        cat <<'EOF'
pnew - create a new prompt file from clipboard contents

Usage:
  pnew <filename>

Arguments:
  filename    (required) Name of the prompt file. .md appended if missing.

Side effects:
  Writes clipboard contents to PROMPTS_DIRECTORY/<filename>.md
  Opens the new file in $EDITOR
EOF
        return 0
    }
    [[ ! -d "$PROMPTS_DIRECTORY" ]] && { echo "pmt: error: PROMPTS_DIRECTORY does not exist: $PROMPTS_DIRECTORY"; return 1; }
    local prompt_file_name="${1}"
    [[ -z "$prompt_file_name" ]] && { echo "pmt: usage: pnew <filename>"; return 1; }
    [[ "$prompt_file_name" != *.md ]] && prompt_file_name="${prompt_file_name}.md"
    local prompt_target_path="$PROMPTS_DIRECTORY/$prompt_file_name"
    [[ -f "$prompt_target_path" ]] && { echo "pmt: error: $prompt_file_name already exists"; return 1; }
    powershell.exe -NoProfile -Command Get-Clipboard > "$prompt_target_path"
    echo "pmt: clipboard pasted into $prompt_file_name"
    "${EDITOR:-nvim}" "$prompt_target_path"
}

plog() {
    [[ "$1" == "-h" || "$1" == "--help" ]] && {
        cat <<'EOF'
plog - append a friction entry stub to the friction log and open it

Usage:
  plog

Arguments:
  none

Side effects:
  Appends a timestamped stub to FRICTION_FILEPATH
  Opens FRICTION_FILEPATH in $EDITOR at the last line
EOF
        return 0
    }
    [[ ! -f "$FRICTION_FILEPATH" ]] && { echo "pmt: error: FRICTION_FILEPATH does not exist: $FRICTION_FILEPATH"; return 1; }
    local friction_entry_stub
    friction_entry_stub="$(printf '\n## %s  [severity]\nWhat I was trying to do.\nWhat actually happened or what annoyed me.\n?: idea or fix if one comes to mind\n' "$(date '+%Y-%m-%d %H:%M')")"
    echo "$friction_entry_stub" >> "$FRICTION_FILEPATH"
    "${EDITOR:-nvim}" + "$FRICTION_FILEPATH"
}
