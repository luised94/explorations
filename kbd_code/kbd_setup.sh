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
alias kst='cd "$KBD_LOCAL_DIR" && git status && cd - > /dev/null'

# === Setup ===
[[ "$1" == "force" ]] && rm -f "$CACHE_FILE"

# --- WSL/ENVIRONMENT DETECTION ---
# === WSL LOGIC ===
if [[ -n "$WSL_DISTRO_NAME" ]]; then
    export KBD_ENV="wsl"

    # 1. FAST PATH: Check cache
    if [[ -f "$CACHE_FILE" ]]; then
        CACHED_DRIVE=$(cat "$CACHE_FILE")
        POTENTIAL_MOUNT="/mnt/${CACHED_DRIVE,,}"

        if [[ -f "$POTENTIAL_MOUNT/.kbd-usb-marker" ]]; then
            export KBD_USB_CONNECTED=true
            export KBD_MOUNT_POINT="$POTENTIAL_MOUNT"
            export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"

            # Sync bib if USB version is newer
            KBD_USB_ZOTERO_BIB="$KBD_MOUNT_POINT/zotero_library.bib"
            KBD_LOCAL_ZOTERO_BIB="$KBD_LOCAL_DIR/zotero_library.bib"
            if [[ -f "$KBD_USB_ZOTERO_BIB" ]] && [[ "$KBD_USB_ZOTERO_BIB" -nt "$KBD_LOCAL_ZOTERO_BIB" ]]; then
                cp "$KBD_USB_ZOTERO_BIB" "$KBD_LOCAL_ZOTERO_BIB"
                echo "kbd: bib synced from USB"
            fi

            return 0
        fi
        # Cache stale, continue to slow path
        rm -f "$CACHE_FILE"
    fi

    # 2. SLOW PATH: PowerShell detection
    if command -v powershell.exe &>/dev/null; then
        KBD_USB_DRIVE=$(powershell.exe -NoProfile -Command '
            Get-Volume | Where-Object { 
                $_.DriveLetter -and (Test-Path "$($_.DriveLetter):\.kbd-usb-marker") 
            } | Select-Object -ExpandProperty DriveLetter
        ' 2>/dev/null | tr -d '\r')

        if [[ -z "$KBD_USB_DRIVE" ]]; then
            export KBD_USB_CONNECTED=false
            [[ "$1" == "force" ]] && echo "kbd: USB not found"
        else
            export KBD_USB_CONNECTED=true
            export KBD_MOUNT_POINT="/mnt/${KBD_USB_DRIVE,,}"
            echo "$KBD_USB_DRIVE" > "$CACHE_FILE"

            # Mount if needed
            if [[ ! -d "$KBD_MOUNT_POINT/personal_repos" ]]; then
                sudo mkdir -p "$KBD_MOUNT_POINT"
                echo "kbd: mounting ${KBD_USB_DRIVE}:..."
                if ! sudo mount -t drvfs "${KBD_USB_DRIVE}:" "$KBD_MOUNT_POINT" -o metadata; then
                    echo "kbd[ERROR]: mount failed"
                    export KBD_USB_CONNECTED=false
                    rm -f "$CACHE_FILE"
                fi
            fi

            [[ "$KBD_USB_CONNECTED" == true ]] && \
                export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"
        fi
    else
        export KBD_USB_CONNECTED=false
    fi

    # 3. If usb bib is newer, sync to local..
    if [[ "$KBD_USB_CONNECTED" == true ]]; then
        export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"

        # Sync bib if USB version is newer
        KBD_USB_ZOTERO_BIB="$KBD_MOUNT_POINT/zotero_library.bib"
        KBD_LOCAL_ZOTERO_BIB="$KBD_LOCAL_DIR/zotero_library.bib"
        if [[ -f "$KBD_USB_ZOTERO_BIB" ]] && [[ "$KBD_USB_ZOTERO_BIB" -nt "$KBD_LOCAL_ZOTERO_BIB" ]]; then
            cp "$KBD_USB_ZOTERO_BIB" "$KBD_LOCAL_ZOTERO_BIB"
            echo "kbd: bib synced from USB"
        fi
    fi

else
    # Native Linux
    export KBD_ENV="linux"
    export KBD_USB_CONNECTED=false

    for dir in /mnt/* /media/"$USER"/* /run/media/"$USER"/*; do
        if [ -f "$dir/$KBD_USB_MARKER" ]; then
            export KBD_MOUNT_POINT="$dir"
            export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"
            if [ -f "$KBD_USB_ZOTERO_BIB" ] && [ "$KBD_USB_ZOTERO_BIB" -nt "$KBD_LOCAL_ZOTERO_BIB" ]; then
              cp "$KBD_USB_ZOTERO_BIB" "$KBD_LOCAL_ZOTERO_BIB"
              echo "kbd: zotero_library.bib synced from USB"
            fi
            export KBD_USB_CONNECTED=true
            echo "kbd: USB connected at $KBD_MOUNT_POINT"
            break
        fi
    done

fi

# Let user know something went wrong with usb connection.
[[ "$1" == "force" ]] && if [ "$KBD_USB_CONNECTED" = false ]; then
  echo ""
  echo "kbd: USB with marker '$KBD_USB_MARKER' not found"
  echo "kbd: Plug in USB, then run: kbd_refresh"
  echo "kbd: Local aliases (j, n) work. Sync (kpull, ksync) won't."
  echo ""
fi

# === FUNCTIONS (defined after variables set) ===
# Sync functions need USB - they check KBD_USB_CONNECTED internally

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
    if [ "$KBD_USB_CONNECTED" != true ]; then
        echo "kbd: USB is not connected. Nothing to unmount."
        return 0
    fi

    # Step 1: Leave mount directory if inside it
    local current_dir
    current_dir=$(pwd)

    if [[ "$current_dir" == "$KBD_MOUNT_POINT"* ]]; then
        cd ~
        echo "kbd: changed directory from $current_dir to ~"
    fi

    # Step 2: Unmount from WSL
    if mountpoint -q "$KBD_MOUNT_POINT" 2>/dev/null; then
        echo "kbd: unmounting $KBD_MOUNT_POINT from WSL..."
        if ! sudo umount "$KBD_MOUNT_POINT" 2>&1; then
            echo "kbd[WARN]: WSL unmount failed"
            echo "kbd: Check other tmux panes, terminal tabs, VS Code terminals"
        fi
    else
        echo "kbd: $KBD_MOUNT_POINT not mounted in WSL"
    fi

    # Step 2b: Remove mount point directory
    if [ -d "$KBD_MOUNT_POINT" ] || [ -e "$KBD_MOUNT_POINT" ]; then
        sudo rmdir "$KBD_MOUNT_POINT" 2>/dev/null
    fi

    # Step 3: Windows eject (skip dismount, go straight to eject)
    if [ "$KBD_POWERSHELL_AVAILABLE" != true ]; then
        echo "kbd: WSL unmounted. Manually eject from Windows Explorer."
        export KBD_USB_CONNECTED=false
        return 0
    fi

    echo "kbd: ejecting ${KBD_USB_DRIVE}: from Windows..."
    powershell.exe -NoProfile -Command "
        \$dl = '$KBD_USB_DRIVE:'
        (New-Object -ComObject Shell.Application).NameSpace(17).ParseName(\$dl).InvokeVerb('Eject')
    " 2>/dev/null

    # Give Windows a moment, then check if drive still exists
    sleep 1
    local drive_exists
    drive_exists=$(powershell.exe -NoProfile -Command "
        if (Test-Path '${KBD_USB_DRIVE}:\') { Write-Output 'yes' } else { Write-Output 'no' }
    " 2>/dev/null | tr -d '\r')

    if [ "$drive_exists" = "no" ]; then
        echo "kbd: ejected ${KBD_USB_DRIVE}: - safe to unplug"
        export KBD_USB_CONNECTED=false
        return 0
    else
        echo "kbd[WARN]: Eject requested but drive still present"
        echo "kbd: May be safe to unplug, or check Windows for 'busy' notification"
        export KBD_USB_CONNECTED=false
        return 0
    fi
}

# Modify PS1 with indicator.
kbd_usb_indicator() {
    [ -f "${KBD_MOUNT_POINT}/.kbd-usb-marker" ] && echo "[U] "
}

# Prepend indicator to existing prompt
if [ -z $MC_PS1 ]; then
  MC_PS1='\u@\h:\w\$ '
  echo "kbd: MC_PS1 not set. Setting to default..."
fi
MC_PS1="\$(kbd_usb_indicator)${MC_PS1}"
export PS1="$MC_PS1"
