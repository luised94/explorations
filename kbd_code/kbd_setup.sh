# kbd.sh - shell tooling for kbd (knowledge base desk)
# Source this file or place in extensions directory

# === LOCAL CONFIGURATION (always available) ===
# Local directory
export KBD_LOCAL_DIR="$HOME/personal_repos/kbd"
export KBD_STATS_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/kbd/stats"

# Marker file placed on USB root to identify it
export KBD_USB_MARKER=".kbd-usb-marker"

# === ALIASES ===
# Always defined - they use KBD_LOCAL_DIR, not USB
alias kj='nvim "$KBD_LOCAL_DIR/journal.txt"'
alias kt='nvim "$KBD_LOCAL_DIR/tasks.txt"'
alias kn='nvim "$KBD_LOCAL_DIR/notes.txt"'
alias kst='cd "$KBD_LOCAL_DIR" && git status && cd - > /dev/null'

# === WSL/ENVIRONMENT DETECTION ===
if [[ ! -z "$WSL_DISTRO_NAME" ]]; then
    export KBD_ENV="wsl"

    # Check PowerShell availability
    if command -v powershell.exe &> /dev/null; then
        export KBD_POWERSHELL_AVAILABLE=true
        ps_version=$(powershell.exe -NoProfile -Command '$PSVersionTable.PSVersion.Major' 2>/dev/null | tr -d '\r')
        if [ -n "$ps_version" ] && [ "$ps_version" -lt 5 ]; then
            echo "kbd[WARN]: PowerShell version $ps_version < 5. Some features may not work."
        fi
    else
        export KBD_POWERSHELL_AVAILABLE=false
        echo "kbd[WARN]: powershell.exe not found. USB features disabled."
    fi

    # USB detection (requires PowerShell)
    if [ "$KBD_POWERSHELL_AVAILABLE" = true ]; then
        export KBD_USB_DRIVE=$(powershell.exe -NoProfile -Command '
            Get-Volume |
            Where-Object {
                $_.DriveLetter -and
                (Test-Path -LiteralPath "$($_.DriveLetter):\.kbd-usb-marker") 
            } |
            Select-Object -ExpandProperty DriveLetter
            ' 2>/dev/null | tr -d '\r'
        )

        if [ -z "$KBD_USB_DRIVE" ]; then
            echo ""
            echo "kbd: USB with marker '$KBD_USB_MARKER' not found"
            echo "kbd: Plug in USB, then run: kbd_refresh"
            echo "kbd: Local aliases (j, n) work. Sync (kpull, ksync) won't."
            echo ""
            export KBD_USB_CONNECTED=false
        else
            export KBD_USB_CONNECTED=true
            export KBD_MOUNT_POINT="/mnt/${KBD_USB_DRIVE,,}"

            # Handle stale mount point (exists but broken after eject)
            if [ -e "$KBD_MOUNT_POINT" ] && [ ! -d "$KBD_MOUNT_POINT" ]; then
                echo "kbd: Removing stale mount point."
                sudo rmdir "$KBD_MOUNT_POINT" 2>/dev/null
            fi

            if [ ! -d "$KBD_MOUNT_POINT" ]; then
                echo "kbd: KBD_MOUNT_POINT dir does not exist."
                echo "kbd: Requires mounting."
                sudo mkdir -p "$KBD_MOUNT_POINT"
            fi

            if [ ! -d "$KBD_MOUNT_POINT/personal_repos" ]; then
                echo "kbd: mounting ${KBD_USB_DRIVE}: to $KBD_MOUNT_POINT"
                sudo mount -t drvfs "${KBD_USB_DRIVE}:" "$KBD_MOUNT_POINT" -o metadata
                if [ $? -ne 0 ]; then
                    echo "kbd[ERROR]: mount failed"
                    export KBD_USB_CONNECTED=false
                fi
            fi

            if [ "$KBD_USB_CONNECTED" = true ]; then
                echo "kbd: USB connected at $KBD_MOUNT_POINT"
                export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"
            fi
        fi
    else
        export KBD_USB_CONNECTED=false
    fi

else
    # Native Linux
    export KBD_ENV="linux"
    export KBD_POWERSHELL_AVAILABLE=false
    export KBD_USB_CONNECTED=false

    for dir in /mnt/* /media/"$USER"/* /run/media/"$USER"/*; do
        if [ -f "$dir/$KBD_USB_MARKER" ]; then
            export KBD_MOUNT_POINT="$dir"
            export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"
            export KBD_USB_CONNECTED=true
            echo "kbd: USB connected at $KBD_MOUNT_POINT"
            break
        fi
    done

    if [ "$KBD_USB_CONNECTED" = false ]; then
        echo ""
        echo "kbd: USB with marker '$KBD_USB_MARKER' not found"
        echo "kbd: Plug in USB, then run: kbd_refresh"
        echo "kbd: Local aliases (j, n) work. Sync (kpull, ksync) won't."
        echo ""
    fi
fi

# === FUNCTIONS (defined after variables set) ===
# Sync functions need USB - they check KBD_USB_CONNECTED internally

# Find and optionally mount USB, returns mount point path
kbd_refresh() {
    local script_path="${BASH_SOURCE[0]}"

    if [ -z "$script_path" ]; then
        echo "kbd: cannot determine script path, manually run:"
        echo "kbd: source ~/.config/mc_extensions/kbd_setup.sh"
        return 1
    fi

    echo "kbd: refreshing from $script_path..."
    source "$script_path"

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
