# kbd.sh - shell tooling for kbd (knowledge base desk)
# Source this file or place in extensions directory

# Local directory
export KBD_LOCAL_DIR="$HOME/personal_repos/kbd"

# Marker file placed on USB root to identify it
export KBD_USB_MARKER=".kbd-usb-marker"

if [[ ! -z "$WSL_DISTRO_NAME" ]]; then
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
    echo "kbd: USB with marker '$KBD_USB_MARKER' not found" >&2
    echo "kbd: Ensure KBD USB is connected." >&2
    echo "kbd: Afterwards, source kbd_setup.sh." >&2
    echo "Local aliases (j, n) still work. Sync (kpull, ksync) won't."
    export KBD_USB_CONNECTED=false
  fi

  export KBD_USB_CONNECTED=true
  export KBD_MOUNT_POINT="/mnt/${KBD_USB_DRIVE,,}"

  # Ensure mount point directory exists
  if [ ! -d "$KBD_MOUNT_POINT" ]; then
      sudo mkdir -p "$KBD_MOUNT_POINT"
  fi

  if [ ! -d "$KBD_MOUNT_POINT/personal_repos" ]; then
    echo "kbd: mounting ${KBD_USB_DRIVE}: to $KBD_MOUNT_POINT"
    sudo mount -t drvfs "${KBD_USB_DRIVE}:" "$KBD_MOUNT_POINT" -o metadata
    if [ $? -ne 0 ]; then
      echo "kbd: mount failed" >&2
      return 1
    fi
  fi

  echo "kbd: Mount point is '$KBD_MOUNT_POINT'"

else
  # Native Linux: scan common mount points (NOT TESTED)
  for dir in /mnt/* /media/"$USER"/* /run/media/"$USER"/*; do
    if [ -f "$dir/$KBD_USB_MARKER" ]; then
      export KBD_MOUNT_POINT="$dir"
      break
    fi
  done

  if [ -z "$KBD_MOUNT_POINT" ]; then
      echo "kbd: USB with marker '$KBD_USB_MARKER' not found" >&2
      echo "kbd: Ensure KBD USB is connected." >&2
      return 1
  fi

fi

export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"

# Find and optionally mount USB, returns mount point path
kbd_refresh() {
    local marker="$KBD_USB_MARKER"

    # Check if WSL
    if [[ ! -z "$WSL_DISTRO_NAME" ]]; then
        echo "kbd: WSL_DISTRO_NAME found." >&2
        # WSL: use PowerShell to find drive letter with marker
        local drive
        drive=$(powershell.exe -NoProfile -Command 'Get-Volume |
          Where-Object { $_.DriveLetter -and (Test-Path -LiteralPath "$($_.DriveLetter):\.kbd-usb-marker") } |
          Select-Object -ExpandProperty DriveLetter' 2>/dev/null | tr -d '\r')

        if [ -z "$drive" ]; then
            echo "kbd: USB with marker '$marker' not found" >&2
            echo "kbd: Drive is '$drive'" >&2
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

# Get path to origin dir (bare repo on USB)
kbd_check_origin() {
  if [[ -z "$KBD_ORIGIN_DIR" ]]; then
    echo "kbd: KBD_ORIGIN_DIR unset."
    return 1

  fi
  # add additional error handling?
  if [[ ! -d "$KBD_ORIGIN_DIR" ]]; then
    echo "kbd: KBD_ORIGIN_DIR does not exist."
    return 1

  fi

  echo "$KBD_ORIGIN_DIR"
}

# Pull from USB
kpull() {
  if [ "$KBD_USB_CONNECTED" = false ]; then
    echo "kbd: USB is not connected. Sync not available."
    return 1
  fi

    local repo
    repo=$(kbd_check_origin) || return 1

    cd "$KBD_LOCAL_DIR" || return 1
    git pull origin master
    cd - > /dev/null
}

# Sync to USB: add all, commit with date, push
ksync() {
  if [ "$KBD_USB_CONNECTED" = false ]; then
    echo "kbd: USB is not connected. Sync not available."
    return 1

  fi

    local repo
    repo=$(kbd_check_origin) || return 1

    cd "$KBD_LOCAL_DIR" || return 1
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
  if [ "$KBD_USB_CONNECTED" = false ]; then
    echo "kbd: USB is not connected. Nothing to dismount."
    return 1

  fi
    local usb
    usb=$(kbd_find_usb) || return 1

    cd ~
    sudo umount "$usb"
    echo "kbd: unmounted $usb, safe to eject"
}

# Open journal
alias kj='nvim "$KBD_LOCAL_DIR/journal.txt"'

# Open notes
alias kn='nvim "$KBD_LOCAL_DIR/notes.txt"'

# Quick status
alias kst='cd "$KBD_LOCAL_DIR" && git status && cd - > /dev/null'
