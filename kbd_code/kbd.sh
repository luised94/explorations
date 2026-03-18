# kbd.sh - shell tooling for kbd (knowledge base desk)
# Source kbd.sh or place in mc_extensions directory
source "$HOME/.config/mc_extensions/usb.sh"
# === LOCAL CONFIGURATION (always available) ===

# Local directory
# Used as fallback source for KBD_DIR. Not referenced directly in functions or aliases.
export KBD_LOCAL_DIR="$HOME/personal_repos/kbd"
export KBD_STATS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kbd/stats"
KBD_WINDOWS_USER="${MC_WINDOWS_USER:-Luised94}"
KBD_ZOTERO_SOURCE="/mnt/c/Users/$KBD_WINDOWS_USER/Zotero/zotero_library.bib"

# === ALIASES ===
# Always defined - they use KBD_LOCAL_DIR, not USB
alias kj='nvim "$KBD_DIR/journal.txt"'
alias kt='nvim "$KBD_DIR/tasks.txt"'
alias kn='nvim "$KBD_DIR/notes.txt"'
alias kva='kvim -a'
alias kst='cd "$KBD_DIR" && git status && cd - > /dev/null'
alias kbd_refresh=usb_refresh
alias kusboff=usb_eject

KBD_DIR="${USB_KBD_LOCAL_DIR:-$HOME/personal_repos/kbd}"

# === FUNCTIONS ===
# --- MULTI-FILE EDITING ---
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

# --- Sync functions --- Need USB ---
# Pull from USB
kpull() {
    if [ "$USB_CONNECTED" != true ]; then
        echo "kbd[ERROR]: USB not connected"
        return 1
    fi
    if [ ! -d "$KBD_DIR/.git" ]; then
        echo "kbd[ERROR]: $KBD_DIR is not a git repository"
        return 1
    fi
    cd "$KBD_DIR" || return 1
    git pull "$USB_MOUNT_POINT/$USB_KBD_REPO_PATH" master
    usb_sync kbd
    cd - > /dev/null
}

# Sync to USB: add all, commit with date, push
ksync() {
    if [ "$USB_CONNECTED" != true ]; then
        echo "kbd[ERROR]: USB not connected"
        return 1
    fi
    if [ ! -d "$KBD_DIR/.git" ]; then
        echo "kbd[ERROR]: $KBD_DIR is not a git repository"
        return 1
    fi
    cd "$KBD_DIR" || return 1
    git add -A
    if git diff --cached --quiet; then
        echo "kbd: nothing to commit"
    else
        git commit
    fi
    git push "$USB_MOUNT_POINT/$USB_KBD_REPO_PATH" master
    usb_sync kbd
    cd - > /dev/null
}

# Sync from Zotero to USB.
kbib_sync() {
    if [ "$USB_CONNECTED" != true ]; then
        echo "kbd[ERROR]: USB not connected"
        return 1
    fi
    if [ ! -f "$KBD_ZOTERO_SOURCE" ]; then
        echo "kbd[ERROR]: Source bib not found: $KBD_ZOTERO_SOURCE"
        return 1
    fi
    local kbd_usb_bib_dest_path="$USB_MOUNT_POINT/shared/kbd_zotero_library.bib"
    if [ "$KBD_ZOTERO_SOURCE" -nt "$kbd_usb_bib_dest_path" ]; then
        cp "$KBD_ZOTERO_SOURCE" "$kbd_usb_bib_dest_path"
        echo "kbd: zotero_library.bib updated on USB"
    else
        echo "kbd: zotero_library.bib already current"
    fi
}

# --- Usage metrics ---
kbd_usage_stats() {
  local hist="${HISTFILE:-$HOME/.bash_history}"
  echo "kbd command usage (from history):"
  grep -oE '\bk(j|t|n|vim|st|sync|pull)\b' "$hist" 2>/dev/null | sort | uniq -c | sort -rn
}

# --- Interface ---
# Modify PS1 with indicator.
kbd_origin_indicator() {
    if [ "$USB_CONNECTED" == true ]; then
        echo "kbd[O]"
    else
        echo "kbd[ ]"
    fi
}
if [ -z "$MC_PS1" ]; then
    MC_PS1='\u@\h:\w\$ '
fi
if [[ "$MC_PS1" != *'kbd_origin_indicator'* ]]; then
    MC_PS1='$(kbd_origin_indicator)'"${MC_PS1}"
fi
export PS1="$MC_PS1"
