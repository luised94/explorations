#!/bin/bash
# kbd.sh - shell tooling for kbd (knowledge base desk)
# usb.sh is loaded by infrastructure (bash/06_usb.sh) before extensions.
# This module does not source usb.sh. It reads variables usb.sh set
# during shell initialization. If usb.sh has not run, USB features
# degrade gracefully via variable fallbacks.
#
# This check is a runtime safety net, not dead code. It fires when:
#   - usb-sh repo is not cloned on this machine
#   - bash/ chain load order changed and usb.sh loads after extensions
#   - usb.sh was removed from the infrastructure chain
# See: ~/personal_repos/usb-sh/docs/usb-setup.md (Loading Architecture)
if [[ "${USB_INITIALIZED:-}" != true ]]; then
    if [[ -f "$HOME/personal_repos/usb-sh/usb.sh" ]]; then
        echo "kbd[WARN]: usb.sh found but not loaded (check bash/ chain load order)"
    else
        echo "kbd[WARN]: usb.sh not found, USB features unavailable"
        echo "kbd[WARN]: clone luised94/usb-sh github repo."
    fi
    export USB_CONNECTED=false
fi

# =============================================================================
# SECTION 1: LOCAL CONFIGURATION (always available, no USB dependency)
# =============================================================================
# Used as fallback source for KBD_DIR. Not referenced directly in functions or aliases.
KBD_DIR="${USB_KBD_LOCAL_DIR:-$HOME/personal_repos/kbd}"

_kvim_usage() {
  cat <<EOF
Usage: kvim [OPTIONS]
Open kbd files for editing.
Options:
  -a, --all      All files in KBD_DIR (uses vimall if available)
  -c, --core     Core files only: journal, tasks, notes (default)
  -d, --dir DIR  Specific subdirectory
  -h, --help     Show this help
EOF
}

kvim() {
  local mode="core"
  local subdir=""
  while [[ $# -gt 0 ]]; do
    case "$1" in
      -h|--help)  _kvim_usage; return 0 ;;
      -a|--all)   mode="all"; shift ;;
      -c|--core)  mode="core"; shift ;;
      -d|--dir)
        [[ -z "$2" || "$2" == -* ]] && { echo "kvim: -d requires argument" >&2; return 1; }
        mode="subdir"; subdir="$2"; shift 2
        ;;
      *)          echo "kvim: unknown option: $1" >&2; return 1 ;;
    esac
  done
  case "$mode" in
    core)
      # Deterministic, no dependency needed
      "${EDITOR:-nvim}" "$KBD_DIR"/{journal,source-notes}.txt
      ;;
    all)
      if declare -f vimall &>/dev/null; then
        vimall -d "$KBD_DIR"
      else
        echo "Note: vimall unavailable, opening core files only" >&2
        "${EDITOR:-nvim}" "$KBD_DIR"/{journal,source-notes}.txt
      fi
      ;;
    subdir)
      local target="$KBD_DIR/$subdir"
      [[ -d "$target" ]] || { echo "kvim: not a directory: $target" >&2; return 1; }
      if declare -f vimall &>/dev/null; then
        vimall -d "$target"
      else
        find "$target" -type f | head -50 | xargs "${EDITOR:-nvim}"
      fi
      ;;
  esac
}

kbd_questions() {
    local source_notes_file="$KBD_DIR/source-notes.txt"
    local journal_file="$KBD_DIR/journal.txt"
    local found_any=false
    for target_file in "$journal_file" "$source_notes_file"; do
        if [[ ! -f "$target_file" ]]; then
            echo "kbd[WARN]: not found: $target_file" >&2
            continue
        fi
        awk '
            /^## @/ || /^## [0-9]{4}-[0-9]{2}-[0-9]{2}/ { current_header = $0 }
            /\?:/ { printf "%s | %s:%d | %s\n", current_header, FILENAME, NR, $0 }
        ' "$target_file"
        found_any=true
    done
    if [[ "$found_any" != true ]]; then
        echo "kbd[ERROR]: no searchable files found" >&2
        return 1
    fi
}

kbd_usage_stats() {
  local hist="${HISTFILE:-$HOME/.bash_history}"
  echo "kbd command usage (from history):"
  grep -oE '\bk(j|t|n|vim|st|sync|pull)\b' "$hist" 2>/dev/null | sort | uniq -c | sort -rn
}

# =============================================================================
# SECTION 3: Aliases
# =============================================================================
# All aliases use KBD_DIR. They work whether USB is connected or not.
alias kj='nvim "$KBD_DIR/journal.txt"'
alias kn='nvim "$KBD_DIR/source-notes.txt"'
alias kva='kvim -a'
alias kst='cd "$KBD_DIR" && git status && cd - > /dev/null'


# =============================================================================
# SECTION 4: Code dojo functions
# =============================================================================
# Requires: git, nvim, shuf, find, sort, uniq, head, awk

CODE_DOJO_DIR="${CODE_DOJO_DIR:-$HOME/code-dojo}"


dojo_open_most_edited_files() {
    local project_name="${1:-}"
    local file_count="${2:-20}"

    if [[ -z "$project_name" ]]; then
        echo "usage: dojo_open_most_edited_files <project_name> [file_count]" >&2
        return 1
    fi

    local project_directory="$CODE_DOJO_DIR/$project_name"

    if [[ ! -d "$project_directory" ]]; then
        echo "error: project directory does not exist: $project_directory" >&2
        return 1
    fi

    local most_edited_raw
    most_edited_raw="$(git -C "$project_directory" log --format='' --name-only \
        | sort \
        | uniq -c \
        | sort -rn \
        | head -n "$file_count" \
        | awk '{print $2}')"

    local most_edited_existing_paths=""
    local existing_count=0

    while IFS= read -r candidate_path; do
        if [[ -z "$candidate_path" ]]; then
            continue
        fi
        if [[ -f "$project_directory/$candidate_path" ]]; then
            most_edited_existing_paths="$most_edited_existing_paths $project_directory/$candidate_path"
            existing_count=$((existing_count + 1))
        fi
    done <<< "$most_edited_raw"

    if [[ $existing_count -eq 0 ]]; then
        echo "no existing files found in most-edited results for $project_name" >&2
        return 1
    fi

    echo "opening $existing_count most-edited files in $project_name"
    # word splitting on most_edited_existing_paths is intentional here
    # shellcheck disable=SC2086
    nvim -c "cd $project_directory" $most_edited_existing_paths
}

dojo_open_random_source_file() {
    local project_name="${1:-}"

    if [[ -z "$project_name" ]]; then
        echo "usage: dojo_open_random_source_file <project_name>" >&2
        return 1
    fi

    local project_directory="$CODE_DOJO_DIR/$project_name"

    if [[ ! -d "$project_directory" ]]; then
        echo "error: project directory does not exist: $project_directory" >&2
        return 1
    fi

    local source_extensions="*.c *.h *.lua *.py *.sh *.md *.rb *.rs *.go"

    local find_expression=""
    local first_extension=true
    for extension_pattern in $source_extensions; do
        if [[ "$first_extension" == true ]]; then
            find_expression="-name $extension_pattern"
            first_extension=false
        else
            find_expression="$find_expression -o -name $extension_pattern"
        fi
    done

    local random_source_file
    random_source_file="$(find "$project_directory" \
        -path "$project_directory/.git" -prune \
        -o -type f \( $find_expression \) -print \
        | shuf -n 1)"

    if [[ -z "$random_source_file" ]]; then
        echo "no source files found in $project_name" >&2
        return 1
    fi

    echo "opening $random_source_file"
    nvim -c "cd $project_directory" "$random_source_file"
}

# Suggested aliases (add to .bashrc or .zshrc):
alias dme='dojo_open_most_edited_files'
alias drf='dojo_open_random_source_file'
