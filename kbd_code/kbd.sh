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
        echo "kbd[WARN]: usb.sh found but not loaded (check bash/ chain load order)" >&2
    else
        echo "kbd[WARN]: usb.sh not found, USB features unavailable" >&2
        echo "kbd[WARN]: clone luised94/usb-sh github repo." >&2
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
  if [[ ! -f "$hist" ]]; then
    echo "kbd[ERROR]: history file not found: $hist" >&2
    return 1
  fi
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
    nvim $most_edited_existing_paths
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

# =============================================================================
# SECTION 5: LLM thread log
# =============================================================================
# Requires: KBD_DIR (set in SECTION 1 above).

# _threadlog_parse_line LINE -> sets reply array TL_FIELDS
# The single parser for a thread-log record. Splits on '|' into the seven
# schema fields (id status date provider tags summary url). Empty trailing
# fields are preserved. Both `new` and `close` paths read records through
# this; the format lives in exactly one place. A caller may use any subset
# of the fields, so all seven are set even when unread here.
# shellcheck disable=SC2034
_threadlog_parse_line() {
    IFS='|' read -r \
        TL_FIELDS_id \
        TL_FIELDS_status \
        TL_FIELDS_date \
        TL_FIELDS_provider \
        TL_FIELDS_tags \
        TL_FIELDS_summary \
        TL_FIELDS_url \
        <<< "$1"
}

# _threadlog_format_line id status date provider tags summary url -> stdout
# The single formatter for a thread-log record. The inverse of the parser;
# the '|' layout exists only here. Both `new` and `close` emit through it.
_threadlog_format_line() {
    printf '%s|%s|%s|%s|%s|%s|%s\n' "$1" "$2" "$3" "$4" "$5" "$6" "$7"
}

# kbd_llm_threadlog <new|close> [args]
#
# Boundary (known, not fixed): the `new` path computes the next per-project
# sequence number by scanning the log, then appends. Two `new` calls racing
# (concurrent shells) can read the same highest sequence and mint duplicate
# ids. Safe for the single-human, one-shell-at-a-time use this tool is for.
# If that assumption ever breaks, the fix is an O_APPEND + flock around the
# scan-and-append, or moving the counter to a separate locked file.
kbd_llm_threadlog() {
    if [[ -z "$KBD_DIR" ]]; then
        echo "error: KBD_DIR is not set" >&2
        return 1
    fi

    local threads_directory="$KBD_DIR/threads"
    local log_file="$threads_directory/thread-log.txt"

    # -- ensure directory and file exist ------------------------------------

    if [[ ! -d "$threads_directory" ]]; then
        mkdir -p "$threads_directory"
    fi

    if [[ ! -f "$log_file" ]]; then
        echo "# project-sequence|status|date|provider|tags|summary|url" > "$log_file"
        echo "# status: active, complete, abandoned" >> "$log_file"
        echo "# tags: comma-separated, no spaces" >> "$log_file"
    fi

    # -- route subcommand ---------------------------------------------------

    local subcommand="${1:-}"

    if [[ -z "$subcommand" ]]; then
        echo "usage: kbd_llm_threadlog <new|close> [arguments]" >&2
        echo "" >&2
        echo "  new   <project> <provider> <summary> [tags] [url]" >&2
        echo "  close <thread_id> [complete|abandoned]" >&2
        return 1
    fi

    shift

    if [[ "$subcommand" == "new" ]]; then

        # -- subcommand: new ------------------------------------------------

        local project_name="${1:-}"
        local provider_name="${2:-}"
        local thread_summary="${3:-}"
        local thread_tags="${4:-}"
        local thread_url="${5:-}"

        if [[ -z "$project_name" ]] || [[ -z "$provider_name" ]] || [[ -z "$thread_summary" ]]; then
            echo "usage: kbd_llm_threadlog new <project> <provider> <summary> [tags] [url]" >&2
            return 1
        fi

        # -- determine next sequence number ---------------------------------

        local highest_sequence=0

        while IFS='|' read -r existing_thread_id _ _ _ _ _ _; do
            if [[ "$existing_thread_id" =~ ^#  ]]; then
                continue
            fi
            if [[ -z "$existing_thread_id" ]]; then
                continue
            fi

            local existing_project="${existing_thread_id%-*}"
            local existing_sequence_raw="${existing_thread_id##*-}"

            if [[ "$existing_project" == "$project_name" ]]; then
                local existing_sequence_number=$((10#$existing_sequence_raw))
                if [[ $existing_sequence_number -gt $highest_sequence ]]; then
                    highest_sequence=$existing_sequence_number
                fi
            fi
        done < "$log_file"

        local next_sequence=$((highest_sequence + 1))
        local padded_sequence
        padded_sequence=$(printf "%02d" "$next_sequence")

        local thread_id="${project_name}-${padded_sequence}"
        local today_date
        today_date=$(date +%Y-%m-%d)

        # -- append to log --------------------------------------------------

        _threadlog_format_line \
            "$thread_id" active "$today_date" \
            "$provider_name" "$thread_tags" "$thread_summary" "$thread_url" \
            >> "$log_file"

        echo "$thread_id"

    elif [[ "$subcommand" == "close" ]]; then

        # -- subcommand: close ----------------------------------------------

        local target_thread_id="${1:-}"
        local close_status="${2:-complete}"

        if [[ -z "$target_thread_id" ]]; then
            echo "usage: kbd_llm_threadlog close <thread_id> [complete|abandoned]" >&2
            return 1
        fi

        if [[ "$close_status" != "complete" ]] && [[ "$close_status" != "abandoned" ]]; then
            echo "error: status must be 'complete' or 'abandoned', got '$close_status'" >&2
            return 1
        fi

        # -- find the matching line -----------------------------------------

        local found_line=""
        local found_line_number=0
        local current_line_number=0

        while IFS= read -r scan_line; do
            current_line_number=$((current_line_number + 1))

            if [[ "$scan_line" =~ ^# ]] || [[ -z "$scan_line" ]]; then
                continue
            fi

            local scan_thread_id="${scan_line%%|*}"

            if [[ "$scan_thread_id" == "$target_thread_id" ]]; then
                found_line="$scan_line"
                found_line_number=$current_line_number
            fi
        done < "$log_file"

        if [[ -z "$found_line" ]]; then
            echo "error: thread '$target_thread_id' not found in log" >&2
            return 1
        fi

        # -- display current entry ------------------------------------------

        echo "current entry:"
        echo "  $found_line"
        echo ""

        # -- extract current fields -----------------------------------------

        _threadlog_parse_line "$found_line"
        local entry_date="$TL_FIELDS_date"
        local entry_provider="$TL_FIELDS_provider"
        local entry_tags="$TL_FIELDS_tags"
        local entry_summary="$TL_FIELDS_summary"
        local entry_url="$TL_FIELDS_url"

        # -- prompt for summary revision ------------------------------------

        echo "current summary: $entry_summary"
        read -r -p "update summary? (enter to keep, or type new): " revised_summary

        if [[ -n "$revised_summary" ]]; then
            entry_summary="$revised_summary"
        fi

        # -- rewrite log with updated line ----------------------------------
        #
        # Commit is rewrite-to-tmp then atomic mv. Crash-state analysis:
        # a death between the redirect opening $temp_file and the mv leaves
        # the ORIGINAL $log_file intact (mv is atomic on the same filesystem)
        # and an orphaned .tmp on disk. Nothing reads .tmp, so the orphan is
        # inert -- the worst crash state is a stale temp file, not data loss.
        # We clear any prior orphan before writing, and refuse to mv if the
        # rewrite itself failed, so a partial .tmp never replaces a good log.

        local temp_file="$log_file.tmp"
        local rewrite_line_number=0

        rm -f "$temp_file"

        if ! while IFS= read -r rewrite_line; do
            rewrite_line_number=$((rewrite_line_number + 1))

            if [[ $rewrite_line_number -eq $found_line_number ]]; then
                _threadlog_format_line \
                    "$target_thread_id" "$close_status" "$entry_date" \
                    "$entry_provider" "$entry_tags" "$entry_summary" "$entry_url"
            else
                echo "$rewrite_line"
            fi
        done < "$log_file" > "$temp_file"; then
            echo "error: failed to rewrite log; original left untouched" >&2
            rm -f "$temp_file"
            return 1
        fi

        if ! mv "$temp_file" "$log_file"; then
            echo "error: failed to commit log; original left untouched" >&2
            rm -f "$temp_file"
            return 1
        fi

        echo "closed $target_thread_id ($close_status)"

    else
        echo "error: unknown subcommand '$subcommand'" >&2
        echo "usage: kbd_llm_threadlog <new|close> [arguments]" >&2
        return 1
    fi
}

# Suggested alias (add to .bashrc or .zshrc):
alias klt='kbd_llm_threadlog'
