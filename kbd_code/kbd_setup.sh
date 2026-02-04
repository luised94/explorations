# kbd.sh - shell tooling for kbd (knowledge base desk)
# Source this file or place in extensions directory

# === LOCAL CONFIGURATION (always available) ===
# Local directory
export KBD_LOCAL_DIR="$HOME/personal_repos/kbd"
export KBD_STATS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kbd/stats"
KBD_WINDOWS_USER="${MC_WINDOWS_USER:-Luised94}"
KBD_ZOTERO_SOURCE="/mnt/c/Users/$KBD_WINDOWS_USER/Zotero/zotero_library.bib"

# Marker file placed on USB root to identify it
export KBD_USB_MARKER=".kbd-usb-marker"

# Cache usb in case environment reloaded during editing.
CACHE_FILE="/tmp/kbd_usb_drive_cache"
KBD_SCRIPT_PATH="$HOME/.config/mc_extensions/kbd_setup.sh"

# === ALIASES ===
# Always defined - they use KBD_LOCAL_DIR, not USB
alias kj='nvim "$KBD_LOCAL_DIR/journal.txt"'
alias kt='nvim "$KBD_LOCAL_DIR/tasks.txt"'
alias kn='nvim "$KBD_LOCAL_DIR/notes.txt"'
alias kva='kvim -a'
alias kst='cd "$KBD_LOCAL_DIR" && git status && cd - > /dev/null'

# === Setup ===
# Reset vars
export KBD_USB_CONNECTED=false
unset KBD_MOUNT_POINT

[[ "$1" == "force" ]] && rm -f "$CACHE_FILE"

# --- WSL/ENVIRONMENT DETECTION ---
if [[ -n "$WSL_DISTRO_NAME" ]]; then
    export KBD_ENV="wsl"

    # 1. FAST PATH: Check cache
    if [[ -f "$CACHE_FILE" ]]; then
      echo "kbd: Found cache file $CACHE_FILE"
        CACHED_DRIVE=$(cat "$CACHE_FILE")
        POTENTIAL_MOUNT="/mnt/${CACHED_DRIVE,,}"

        if [[ -f "$POTENTIAL_MOUNT/$KBD_USB_MARKER" ]]; then
            export KBD_USB_DRIVE="$CACHED_DRIVE"
            export KBD_MOUNT_POINT="$POTENTIAL_MOUNT"
            export KBD_USB_CONNECTED=true
        else
          # Cache stale, continue to slow path
          rm -f "$CACHE_FILE"
        fi
    fi

    # 2. SLOW PATH: PowerShell detection
    if [[ "$KBD_USB_CONNECTED" == false ]] && command -v powershell.exe &>/dev/null; then
        KBD_USB_DRIVE=$(powershell.exe -NoProfile -Command '
            Get-Volume | Where-Object {
                $_.DriveLetter -and (Test-Path "$($_.DriveLetter):\.kbd-usb-marker")
            } | Select-Object -ExpandProperty DriveLetter
        ' 2>/dev/null | tr -d '\r')

        if [[ -n "$KBD_USB_DRIVE" ]]; then
            export KBD_MOUNT_POINT="/mnt/${KBD_USB_DRIVE,,}"
            export KBD_USB_CONNECTED=true

            # Update Cache
            echo "$KBD_USB_DRIVE" > "$CACHE_FILE"

            # Mount logic
            if [[ ! -d "$KBD_MOUNT_POINT" ]]; then
                sudo mkdir -p "$KBD_MOUNT_POINT"
            fi

            # Check if mount is actually active (has contents)
            if [[ ! -d "$KBD_MOUNT_POINT/personal_repos" ]]; then
                echo "kbd: mounting ${KBD_USB_DRIVE}:..."
                if ! sudo mount -t drvfs "${KBD_USB_DRIVE}:" "$KBD_MOUNT_POINT" -o metadata; then
                    echo "kbd[ERROR]: mount failed"
                    export KBD_USB_CONNECTED=false
                    rm -f "$CACHE_FILE"
                fi
            fi
        fi
    fi

else
    # Native Linux
    export KBD_ENV="linux"

    for dir in /mnt/* /media/"$USER"/* /run/media/"$USER"/*; do
        if [[ -f "$dir/$KBD_USB_MARKER" ]]; then
            export KBD_MOUNT_POINT="$dir"
            export KBD_USB_CONNECTED=true
            echo "kbd: USB connected at $KBD_MOUNT_POINT"
            break
        fi
    done

fi

# ==========================================
# PHASE 2: EXECUTION
# ==========================================
if [[ "$KBD_USB_CONNECTED" == true ]]; then

    echo "kbd: USB is connected..."
    export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"

    # Unified Bib Sync Logic (Runs for both WSL and Linux)
    # Define paths once
    KBD_USB_ZOTERO_BIB="$KBD_MOUNT_POINT/zotero_library.bib"
    KBD_LOCAL_ZOTERO_BIB="$KBD_LOCAL_DIR/zotero_library.bib"

    if [[ -f "$KBD_USB_ZOTERO_BIB" ]] && [[ "$KBD_USB_ZOTERO_BIB" -nt "$KBD_LOCAL_ZOTERO_BIB" ]]; then
        cp "$KBD_USB_ZOTERO_BIB" "$KBD_LOCAL_ZOTERO_BIB"
        echo "kbd: zotero_library.bib synced from USB"
    fi

elif [[ "$1" == "force" ]]; then
    # Only warn if user explicitly requested a refresh
    echo ""
    echo "kbd: USB with marker '$KBD_USB_MARKER' not found"
    echo "kbd: Plug in USB, then run: kbd_refresh"
    echo "kbd: Local aliases (j, n) work. Sync (kpull, ksync) won't."
    echo ""
fi

# === FUNCTIONS ===
# --- MULTI-FILE EDITING ---
_kvim_usage() {
  cat <<EOF
Usage: kvim [OPTIONS]

Open kbd files for editing.

Options:
  -a, --all      All files in KBD_LOCAL_DIR (uses vimall if available)
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
      "${EDITOR:-nvim}" "$KBD_LOCAL_DIR"/{journal,tasks,notes}.txt
      ;;
    all)
      if declare -f vimall &>/dev/null; then
        vimall -d "$KBD_LOCAL_DIR"
      else
        echo "Note: vimall unavailable, opening core files only" >&2
        "${EDITOR:-nvim}" "$KBD_LOCAL_DIR"/{journal,tasks,notes}.txt
      fi
      ;;
    subdir)
      local target="$KBD_LOCAL_DIR/$subdir"
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
# Find and optionally mount USB, returns mount point path
kbd_refresh() {
    if [ ! -f "$KBD_SCRIPT_PATH" ]; then
        echo "kbd: script path does not exist, current: source $KBD_SCRIPT_PATH"
        echo "kbd: manually source from repo."
        return 1
    fi

    echo "kbd: refreshing from $KBD_SCRIPT_PATH..."
    source "$KBD_SCRIPT_PATH" force

    # Summary after re-source
    if [[ "$KBD_USB_CONNECTED" == true ]]; then
        echo "kbd: ready ($KBD_ENV, usb: $KBD_MOUNT_POINT)"
    else
        echo "kbd: ready ($KBD_ENV, usb: disconnected)"
    fi
}

# --- Sync functions --- Need USB ---
# Pull from USB
kpull() {
    if [ "$KBD_USB_CONNECTED" != true ]; then
        echo "kbd[ERROR]: USB not connected. Plug in and run: source ~/.config/mc_extensions/kbd_setup.sh"
        return 1
    fi

    # Check local repo exists and is a git repo
    if [ ! -d "$KBD_LOCAL_DIR/.git" ]; then
        echo "kbd[ERROR]: $KBD_LOCAL_DIR is not a git repository"
        return 1
    fi

    local remote_unavailable=false
    local remote="origin"
    local url
    url=$(git -C "$KBD_LOCAL_DIR" remote get-url "$remote" 2>/dev/null)

    if [ -z "$url" ]; then
        echo "kbd[ERROR]: Remote 'origin' not configured"
        return 1
    fi

    if [[ "$url" == /* || "$url" == file://* ]]; then
        [[ ! -d "${url#file://}" ]] && remote_unavailable=true
    fi

    if [[ "$remote_unavailable" == true ]]; then
        echo "kbd[ERROR]: Remote unavailable: $url"
        return 1
    fi

    cd "$KBD_LOCAL_DIR" || return 1
    git pull origin master

    # Sync bib if USB version is newer
    if [ ! -f "$KBD_USB_ZOTERO_BIB" ]; then
      echo "kbd: $KBD_USB_ZOTERO_BIB does not exist."
    fi

    if [ -f "$KBD_USB_ZOTERO_BIB" ] && [ "$KBD_USB_ZOTERO_BIB" -nt "$KBD_LOCAL_ZOTERO_BIB" ]; then
        cp "$KBD_USB_ZOTERO_BIB" "$KBD_LOCAL_ZOTERO_BIB"
        echo "kbd: $KBD_LOCAL_ZOTERO_BIB updated."
    fi

    cd - > /dev/null
}

# Sync to USB: add all, commit with date, push
ksync() {
    if [ "$KBD_USB_CONNECTED" != true ]; then
        echo "kbd[ERROR]: USB not connected. Plug in and run: kbd_refresh or source ~/.config/mc_extensions/kbd_setup.sh"
        return 1
    fi

    # Check local repo exists and is a git repo
    if [ ! -d "$KBD_LOCAL_DIR/.git" ]; then
        echo "kbd[ERROR]: $KBD_LOCAL_DIR is not a git repository"
        return 1
    fi

    local remote_unavailable=false
    local remote="origin"
    local url
    url=$(git -C "$KBD_LOCAL_DIR" remote get-url "$remote" 2>/dev/null)

    if [ -z "$url" ]; then
        echo "kbd[ERROR]: Remote 'origin' not configured"
        return 1
    fi

    if [[ "$url" == /* || "$url" == file://* ]]; then
        [[ ! -d "${url#file://}" ]] && remote_unavailable=true
    fi

    if [[ "$remote_unavailable" == true ]]; then
        echo "kbd[ERROR]: Remote unavailable: $url"
        return 1
    fi

    cd "$KBD_LOCAL_DIR" || return 1
    git add -A

    if git diff --cached --quiet; then
        echo "kbd: nothing to commit"
    else
        git commit
    fi

    # Check if there are commits to push
    local unpushed
    unpushed=$(git rev-list --count origin/master..HEAD 2>/dev/null)

    if [ -z "$unpushed" ]; then
        echo "kbd: cannot determine push status, pushing anyway"
        git push origin master
    elif [ "$unpushed" -gt 0 ]; then
        echo "kbd: pushing $unpushed commit(s)"
        git push origin master
    else
        echo "kbd: nothing to push"
    fi

    cd - > /dev/null
}

# Sync from Zotero to USB.
kbib_sync() {

    if [ "$KBD_USB_CONNECTED" != true ]; then
        echo "kbd[ERROR]: USB not connected"
        return 1
    fi

    if [ ! -f "$KBD_ZOTERO_SOURCE" ]; then
        echo "kbd[ERROR]: Source bib not found: $KBD_ZOTERO_SOURCE"
        return 1
    fi

    # Only copy if source is newer
    if [ "$KBD_ZOTERO_SOURCE" -nt "$KBD_USB_ZOTERO_BIB" ]; then
        cp "$KBD_ZOTERO_SOURCE" "$KBD_USB_ZOTERO_BIB"
        echo "kbd: zotero_library.bib updated on USB"
    else
        echo "kbd: zotero_library.bib already current"
    fi
}

# Unmount USB (run before ejecting)
kusboff() {
    # 1. PRE-CHECK
    if [[ "$KBD_USB_CONNECTED" != true ]]; then
        echo "kbd: USB is not connected. Nothing to unmount."
        return 0
    fi

    # 2. LEAVE DIRECTORY
    # If the shell is currently sitting inside the drive, unmount will fail.
    if [[ "$PWD" == "$KBD_MOUNT_POINT"* ]]; then
        echo "kbd: changing directory to ~"
        cd ~ || return 1
    fi

    # 3. UNMOUNT (OS Agnostic)
    if mountpoint -q "$KBD_MOUNT_POINT" 2>/dev/null; then
        echo "kbd: unmounting $KBD_MOUNT_POINT..."

        if ! sudo umount "$KBD_MOUNT_POINT"; then
            echo "kbd[ERROR]: Unmount failed. Files are in use by:"
            # Show the user exactly what process is blocking the unmount
            lsof +D "$KBD_MOUNT_POINT" 2>/dev/null || echo "  (Could not list processes)"
            return 1
        fi
    fi

    # 4. CLEANUP & EJECT
    # Only run Windows/PowerShell logic if we are in WSL
    if [[ "$KBD_ENV" == "wsl" ]]; then

        # Remove empty mount directory
        if [[ -d "$KBD_MOUNT_POINT" ]]; then
            sudo rmdir "$KBD_MOUNT_POINT" 2>/dev/null
        fi

        # Eject via PowerShell
        if [[ -n "$KBD_USB_DRIVE" ]]; then
            echo "kbd: ejecting ${KBD_USB_DRIVE}: from Windows..."

            # Use 'Eject' verb
            powershell.exe -NoProfile -Command "
                (New-Object -ComObject Shell.Application).NameSpace(17).ParseName('${KBD_USB_DRIVE}:').InvokeVerb('Eject')
            " 2>/dev/null

            # Verify Logic
            # We wait 2 seconds, then check if the path is gone
            sleep 2
            local drive_still_there
            drive_still_there=$(powershell.exe -NoProfile -Command "Test-Path '${KBD_USB_DRIVE}:'" 2>/dev/null | tr -d '\r')

            if [[ "$drive_still_there" == "True" ]]; then
                echo "kbd[WARN]: Windows did not eject the drive (it may be busy)."
            else
                echo "kbd: Drive ejected safely."
            fi
        fi
    else
        # Native Linux Cleanup
        echo "kbd: Unmounted. Safe to unplug."
    fi

    # 5. STATE RESET
    export KBD_USB_CONNECTED=false
    unset KBD_MOUNT_POINT
    unset KBD_USB_DRIVE

    # Delete the cache so next startup doesn't read stale data
    rm -f "$CACHE_FILE"
}

# --- Usage metrics ---
kbd_usage_stats() {
  local hist="${HISTFILE:-$HOME/.bash_history}"
  echo "kbd command usage (from history):"
  grep -oE '\bk(j|t|n|vim|st|sync|pull)\b' "$hist" 2>/dev/null | sort | uniq -c | sort -rn
}

# --- Interface ---
# Modify PS1 with indicator.
kbd_usb_indicator() {
  if [ -f "${KBD_MOUNT_POINT}/$KBD_USB_MARKER" ]; then
    echo "kbd[U]"
  else
    echo "kbd[ ]"
  fi
}

if [ -z "$MC_PS1" ]; then
  MC_PS1='\u@\h:\w\$ '
fi

# Only add if not already present
if [[ "$MC_PS1" != *'kbd_usb_indicator'* ]]; then
  MC_PS1='$(kbd_usb_indicator)'"${MC_PS1}"
fi

export PS1="$MC_PS1"
