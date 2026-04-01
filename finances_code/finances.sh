#!/bin/bash
# finances.sh - shell tooling for personal plain text accounting (hledger)
# Location: ~/personal_repos/explorations/finances_code/finances.sh
# Symlink: ~/.config/mc_extensions/finances.sh
# Load chain: ~/.bashrc -> bash/99_extensions.sh -> mc_extensions/finances.sh
#
# --- usb.sh integration check ---
# usb.sh is loaded by infrastructure (bash/06_usb.sh) before extensions.
# This module does not source usb.sh. It reads variables usb.sh set
# during shell initialization. If usb.sh has not run, USB features
# degrade gracefully via variable fallbacks below.
#
# This check is a runtime safety net, not dead code. It fires when:
# - usb-sh repo is not cloned on this machine
# - bash/ chain load order changed and usb.sh loads after extensions
# - usb.sh was removed from the infrastructure chain
# See: ~/personal_repos/usb-sh/docs/usb-setup.md (Loading Architecture)
if [[ "${USB_INITIALIZED:-}" != true ]]; then
    if [[ -f "$HOME/personal_repos/usb-sh/usb.sh" ]]; then
        echo "finances[WARN]: usb.sh found but not loaded (check bash/ chain load order)"
    else
        echo "finances[WARN]: usb.sh not found, USB features unavailable"
    fi
    export USB_CONNECTED="${USB_CONNECTED:-false}"
fi

# =============================================================================
# SECTION 1: LOCAL CONFIGURATION (always available, no USB dependency)
# =============================================================================

FINANCES_DIR="${USB_FINANCES_LOCAL_DIR:-$HOME/personal_repos/finances}"
export LEDGER_FILE="$FINANCES_DIR/2026.journal"

alias bal='hledger bal'
alias bs='hledger bs'
alias is='hledger is'
alias reg='hledger reg'
alias add='hledger add'

hledit() {
    ${EDITOR:-nvim} "$LEDGER_FILE"
}

hlmtd() {
    hledger is -p "$(date +%Y-%m)-01..today"
}

hllm() {
    local first_of_current_month
    local start_of_last_month
    local end_of_last_month
    first_of_current_month="$(date +%Y-%m-01)"
    start_of_last_month="$(date -d "$first_of_current_month -1 month" +%Y-%m-%d)"
    end_of_last_month="$(date -d "$first_of_current_month -1 day" +%Y-%m-%d)"
    hledger is -p "$start_of_last_month..$end_of_last_month"
}

hlytd() {
    hledger is -p "$(date +%Y)-01-01..today"
}

hlrecent() {
    local days="${1:-30}"
    local start_date
    start_date="$(date -d "$days days ago" +%Y-%m-%d)"
    hledger reg -p "$start_date..today"
}
hlreconcile() {
    if [[ -z "$1" ]]; then
        echo "finances[ERROR]: usage: hlreconcile ACCOUNT"
        return 1
    fi
    hledger aregister "$1"
}

hlyear() {
    if [[ -z "$1" ]]; then
        echo "finances[ERROR]: usage: hlyear YEAR"
        return 1
    fi
    if [[ ! "$1" =~ ^[0-9]{4}$ ]]; then
        echo "finances[ERROR]: year must be four digits (e.g. 2026)"
        return 1
    fi
    export LEDGER_FILE="$FINANCES_DIR/$1.journal"
    echo "finances: LEDGER_FILE set to $LEDGER_FILE"
}

# =============================================================================
# SECTION 2: USB OPERATIONS (requires USB_CONNECTED=true)
# =============================================================================

hlpush() {
    if [[ "$USB_CONNECTED" != true ]]; then
        echo "finances[ERROR]: USB not connected"
        return 1
    fi
    if [[ ! -d "$FINANCES_DIR/.git" ]]; then
        echo "finances[ERROR]: $FINANCES_DIR is not a git repository"
        return 1
    fi
    cd "$FINANCES_DIR" || return 1
    git add -A
    if git diff --cached --quiet; then
        echo "finances: nothing to commit"
    else
        git commit
    fi
    git push origin main
    usb_sync finances
    cd - > /dev/null
}

hlpull() {
    if [[ "$USB_CONNECTED" != true ]]; then
        echo "finances[ERROR]: USB not connected"
        return 1
    fi
    if [[ ! -d "$FINANCES_DIR/.git" ]]; then
        echo "finances[ERROR]: $FINANCES_DIR is not a git repository"
        return 1
    fi
    cd "$FINANCES_DIR" || return 1
    git pull origin main
    usb_sync finances
    cd - > /dev/null
}
