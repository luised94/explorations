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
# All aliases and functions in this section use KBD_DIR. They work whether
# USB is connected or not.

# Used as fallback source for KBD_DIR. Not referenced directly in functions or aliases.
KBD_LOCAL_DIR="$HOME/personal_repos/kbd"
KBD_STATS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kbd/stats"
KBD_WINDOWS_USER="${MC_WINDOWS_USER:-Luised94}"
KBD_ZOTERO_SOURCE="/mnt/c/Users/$KBD_WINDOWS_USER/Zotero/zotero_library.bib"
KBD_DIR="${USB_KBD_LOCAL_DIR:-$HOME/personal_repos/kbd}"

alias kj='nvim "$KBD_DIR/journal.txt"'
alias kt='nvim "$KBD_DIR/tasks.txt"'
alias kn='nvim "$KBD_DIR/notes.txt"'
alias kva='kvim -a'
alias kst='cd "$KBD_DIR" && git status && cd - > /dev/null'
alias kbd_refresh=usb_refresh
alias kusboff=usb_eject

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
      "${EDITOR:-nvim}" "$KBD_DIR"/{journal,tasks,notes}.txt
      ;;
    all)
      if declare -f vimall &>/dev/null; then
        vimall -d "$KBD_DIR"
      else
        echo "Note: vimall unavailable, opening core files only" >&2
        "${EDITOR:-nvim}" "$KBD_DIR"/{journal,tasks,notes}.txt
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
kbd_usage_stats() {
  local hist="${HISTFILE:-$HOME/.bash_history}"
  echo "kbd command usage (from history):"
  grep -oE '\bk(j|t|n|vim|st|sync|pull)\b' "$hist" 2>/dev/null | sort | uniq -c | sort -rn
}
# =============================================================================
# SECTION 2: USB OPERATIONS (requires USB_CONNECTED=true)
# =============================================================================
# Interface with usb.sh:
#   Reads: USB_CONNECTED, USB_MOUNT_POINT, USB_KBD_REPO_PATH
#   Calls: usb_sync
#
# Bib sync flow:
#   Zotero (Windows) -> USB shared/ -> local repo
#        kbib_sync          usb_sync (auto, startup)
#
# The two legs are intentionally separate. kbib_sync is manual because
# the Zotero leg touches Windows filesystem and is slow.

kpull() {
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        cat <<'EOF'
kpull - pull from USB and sync files
Usage:
  kpull
Wraps usb_pull and usb_sync. See usb_pull -h for details.
EOF
        return 0
    fi
    usb_pull kbd
    usb_sync kbd
}


ksync() {
    if [[ "$1" == "-h" || "$1" == "--help" ]]; then
        cat <<'EOF'
ksync - commit, push to USB, and sync files
Usage:
  ksync
Commits with daily sync message (amends if same day),
pushes to USB bare repo, and runs file sync.
Wraps usb_commit, usb_push, and usb_sync.
EOF
        return 0
    fi
    usb_commit kbd || return 1
    usb_push kbd || return 1
    usb_sync kbd
}

# This path must match the src in kbd.conf sync_files. kbd.conf is the
# source of truth.
kbib_sync() {
    if [[ "$USB_CONNECTED" != true ]]; then
        echo "kbd[ERROR]: USB not connected"
        return 1
    fi
    if [[ ! -f "$KBD_ZOTERO_SOURCE" ]]; then
        echo "kbd[ERROR]: Source bib not found: $KBD_ZOTERO_SOURCE"
        return 1
    fi
    local kbd_usb_bib_dest_path="$USB_MOUNT_POINT/shared/kbd_zotero_library.bib"
    if [[ "$KBD_ZOTERO_SOURCE" -nt "$kbd_usb_bib_dest_path" ]]; then
        cp "$KBD_ZOTERO_SOURCE" "$kbd_usb_bib_dest_path"
        echo "kbd: zotero_library.bib updated on USB"
    else
        echo "kbd: zotero_library.bib already current"
    fi
}
