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
    echo ""
    echo "kbd: USB with marker '$KBD_USB_MARKER' not found"
    echo "kbd: Ensure KBD USB is connected."
    echo "kbd: Afterwards, source kbd_setup.sh"
    echo "kbd: Local aliases (j, n) still work. Sync (kpull, ksync) won't."
    echo ""
    export KBD_USB_CONNECTED=false
  else
    export KBD_USB_CONNECTED=true
    export KBD_MOUNT_POINT="/mnt/${KBD_USB_DRIVE,,}"

    if [ ! -d "$KBD_MOUNT_POINT" ]; then
      sudo mkdir -p "$KBD_MOUNT_POINT"
    fi

    if [ ! -d "$KBD_MOUNT_POINT/personal_repos" ]; then
      echo "kbd: mounting ${KBD_USB_DRIVE}: to $KBD_MOUNT_POINT"
      sudo mount -t drvfs "${KBD_USB_DRIVE}:" "$KBD_MOUNT_POINT" -o metadata
      if [ $? -ne 0 ]; then
        echo "kbd: mount failed" >&2
        export KBD_USB_CONNECTED=false
      fi
    fi

    if [ "$KBD_USB_CONNECTED" = true ]; then
      echo "kbd: Mount point is '$KBD_MOUNT_POINT'"
      export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"
    fi
  fi

else
  # Native Linux: scan common mount points (NOT TESTED)
  export KBD_USB_CONNECTED=false

  for dir in /mnt/* /media/"$USER"/* /run/media/"$USER"/*; do
    if [ -f "$dir/$KBD_USB_MARKER" ]; then
      export KBD_MOUNT_POINT="$dir"
      export KBD_USB_CONNECTED=true
      export KBD_ORIGIN_DIR="$KBD_MOUNT_POINT/personal_repos/kbd.git"
      break
    fi
  done

  if [ "$KBD_USB_CONNECTED" = false ]; then
    echo ""
    echo "kbd: USB with marker '$KBD_USB_MARKER' not found"
    echo "kbd: Ensure KBD USB is connected."
    echo "kbd: Afterwards, source kbd_setup.sh"
    echo "kbd: Local aliases (j, n) still work. Sync (kpull, ksync) won't."
    echo ""
  fi
fi

# Aliases always defined - they use KBD_LOCAL_DIR, not USB
alias kj='nvim "$KBD_LOCAL_DIR/journal.txt"'
alias kn='nvim "$KBD_LOCAL_DIR/notes.txt"'
alias kst='cd "$KBD_LOCAL_DIR" && git status && cd - > /dev/null'

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

    cd ~
    sudo umount "$KBD_MOUNT_POINT"

    if [ $? -eq 0 ]; then
        echo "kbd: unmounted $KBD_MOUNT_POINT, safe to eject"
        export KBD_USB_CONNECTED=false    # Update state
    else
        echo "kbd[ERROR]: unmount failed - files may be in use"
        return 1
    fi
}
