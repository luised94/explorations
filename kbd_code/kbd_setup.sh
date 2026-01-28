# kbd.sh - shell tooling for kbd (knowledge base desk)
# Source this file or place in extensions directory

export KBD_DIR="$HOME/personal_repos/kbd"

# Marker file placed on USB root to identify it
KBD_USB_MARKER=".kbd-usb-marker"

# Find and optionally mount USB, returns mount point path
kbd_find_usb() {
    local marker="$KBD_USB_MARKER"

    # Check if WSL
    if [[ -z "$WSL_DISTRO_NAME" ]]; then
        # WSL: use PowerShell to find drive letter with marker
        local drive
        drive=$(powershell.exe -NoProfile -Command 'Get-Volume |
                  Where-Object { $_.DriveLetter -and (Test-Path -LiteralPath "$($_.DriveLetter):\.kbd-usb-marker") } |
                  Select-Object -ExpandProperty DriveLetter' 2>/dev/null | tr -d '\r')

        if [ -z "$drive" ]; then
            echo "kbd: USB with marker '$marker' not found" >&2
            return 1
        fi

        local mount_point="/mnt/${drive,,}"  # lowercase

        # Mount if not already mounted with content
        if [ ! -d "$mount_point/personal_repos" ]; then
            echo "kbd: mounting ${drive}: to $mount_point"
            sudo mount -t drvfs "${drive}:" "$mount_point" -o metadata
            if [ $? -ne 0 ]; then
                echo "kbd: mount failed" >&2
                return 1
            fi
        fi

        echo "$mount_point"
        return 0
    else
        # Native Linux: scan common mount points
        local dir
        for dir in /mnt/* /media/"$USER"/* /run/media/"$USER"/*; do
            if [ -f "$dir/$marker" ]; then
                echo "$dir"
                return 0
            fi
        done

        echo "kbd: USB with marker '$marker' not found" >&2
        return 1
    fi
}

# Get path to bare repo on USB
kbd_repo_path() {
    local usb
    usb=$(kbd_find_usb) || return 1
    echo "$usb/personal_repos/kbd.git"
}

# Pull from USB
kpull() {
    local repo
    repo=$(kbd_repo_path) || return 1

    cd "$KBD_DIR" || return 1
    git pull origin master
    cd - > /dev/null
}

# Sync to USB: add all, commit with date, push
ksync() {
    local repo
    repo=$(kbd_repo_path) || return 1

    cd "$KBD_DIR" || return 1
    git add -A

    # Only commit if there are changes
    if git diff --cached --quiet; then
        echo "kbd: nothing to commit"
    else
        git commit -m "$(date +%F)"
    fi

    git push origin master
    cd - > /dev/null
}

# Unmount USB (run before ejecting)
kusboff() {
    local usb
    usb=$(kbd_find_usb) || return 1

    cd ~
    sudo umount "$usb"
    echo "kbd: unmounted $usb, safe to eject"
}

# Open journal
alias j='nvim "$KBD_DIR/journal.txt"'

# Open notes
alias n='nvim "$KBD_DIR/notes.txt"'

# Quick status
alias kst='cd "$KBD_DIR" && git status && cd - > /dev/null'
