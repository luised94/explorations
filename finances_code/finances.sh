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
export FINANCES_DIR="${USB_FINANCES_LOCAL_DIR:-$HOME/personal_repos/finances}"
export LEDGER_FILE="$FINANCES_DIR/2026.journal"
if command -v hledger > /dev/null 2>&1; then
    FINANCES_HLEDGER_AVAILABLE=true
else
    FINANCES_HLEDGER_AVAILABLE=false
    echo "finances[WARN]: hledger not found in PATH"
fi
if [[ "$(basename "$LEDGER_FILE" .journal)" != "$(date +%Y)" ]]; then
    echo "finances[WARN]: LEDGER_FILE points at $(basename "$LEDGER_FILE"), current year is $(date +%Y)"
    echo "finances[WARN]: run 'hlyear $(date +%Y)' to switch"
fi
alias bal='hledger bal'
alias bs='hledger bs'
alias is='hledger is'
alias reg='hledger reg'
alias add='hledger add'
finances_edit() {
    ${EDITOR:-nvim} "$LEDGER_FILE"
}
finances_month_to_date() {
    if [[ "$FINANCES_HLEDGER_AVAILABLE" != true ]]; then
        echo "finances[ERROR]: hledger not found in PATH"
        return 1
    fi
    hledger is -p "$(date +%Y-%m)-01..today"
}
finances_last_month() {
    if [[ "$FINANCES_HLEDGER_AVAILABLE" != true ]]; then
        echo "finances[ERROR]: hledger not found in PATH"
        return 1
    fi
    local first_of_current_month
    local start_of_last_month
    local end_of_last_month
    first_of_current_month="$(date +%Y-%m-01)"
    start_of_last_month="$(date -d "$first_of_current_month -1 month" +%Y-%m-%d)"
    end_of_last_month="$(date -d "$first_of_current_month -1 day" +%Y-%m-%d)"
    hledger is -p "$start_of_last_month..$end_of_last_month"
}
finances_year_to_date() {
    if [[ "$FINANCES_HLEDGER_AVAILABLE" != true ]]; then
        echo "finances[ERROR]: hledger not found in PATH"
        return 1
    fi
    hledger is -p "$(date +%Y)-01-01..today"
}
finances_recent() {
    if [[ "$FINANCES_HLEDGER_AVAILABLE" != true ]]; then
        echo "finances[ERROR]: hledger not found in PATH"
        return 1
    fi
    local days="${1:-30}"
    local start_date
    start_date="$(date -d "$days days ago" +%Y-%m-%d)"
    hledger reg -p "$start_date..today"
}
finances_reconcile() {
    if [[ "$FINANCES_HLEDGER_AVAILABLE" != true ]]; then
        echo "finances[ERROR]: hledger not found in PATH"
        return 1
    fi
    if [[ -z "$1" ]]; then
        echo "finances[ERROR]: usage: hlreconcile ACCOUNT"
        return 1
    fi
    hledger aregister "$1"
}
finances_set_year() {
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
    if [[ ! -f "$LEDGER_FILE" ]]; then
        echo "finances[WARN]: $LEDGER_FILE does not exist"
    fi
}
finances_status() {
    echo "finances: LEDGER_FILE=$LEDGER_FILE"
    if [[ -f "$LEDGER_FILE" ]]; then
        if [[ "$FINANCES_HLEDGER_AVAILABLE" == true ]]; then
            echo "finances: file exists, $(hledger stats 2>/dev/null | head -1)"
        else
            echo "finances: file exists (hledger not available for stats)"
        fi
    else
        echo "finances: WARNING -- file does not exist"
    fi
    echo "finances: USB_CONNECTED=$USB_CONNECTED"
}
finances_new_year() {
    local new_year
    new_year="$(date +%Y)"
    local new_file="$FINANCES_DIR/$new_year.journal"
    if [[ -f "$new_file" ]]; then
        echo "finances[ERROR]: $new_file already exists"
        return 1
    fi
    if [[ ! -f "$LEDGER_FILE" ]]; then
        echo "finances[ERROR]: current LEDGER_FILE does not exist: $LEDGER_FILE"
        return 1
    fi
    if ! grep -q '^; === End of Declarations ===$' "$LEDGER_FILE"; then
        echo "finances[ERROR]: sentinel line not found in $(basename "$LEDGER_FILE")"
        echo "finances[ERROR]: expected: ; === End of Declarations ==="
        return 1
    fi
    sed -n '1,/^; === End of Declarations ===/p' "$LEDGER_FILE" > "$new_file"
    echo "finances: created $new_file from directives in $(basename "$LEDGER_FILE")"
    echo "finances: next steps:"
    echo "  1. Edit header comment (update year and date)"
    echo "  2. Add opening balances transaction"
    echo "  3. Run: hlyear $new_year"
}
# --- Section 1 Aliases ---
alias hledit='finances_edit'
alias hlmtd='finances_month_to_date'
alias hllm='finances_last_month'
alias hlytd='finances_year_to_date'
alias hlrecent='finances_recent'
alias hlreconcile='finances_reconcile'
alias hlyear='finances_set_year'
alias hlstatus='finances_status'
alias hlnewyear='finances_new_year'
# =============================================================================
# SECTION 2: USB OPERATIONS (delegates to usb_push/usb_pull)
# =============================================================================
finances_push() {
    if [[ ! -d "$FINANCES_DIR/.git" ]]; then
        echo "finances[ERROR]: $FINANCES_DIR is not a git repo"
        return 1
    fi
    if [[ -n "$(git -C "$FINANCES_DIR" status --porcelain 2>/dev/null)" ]]; then
        local untracked_count
        untracked_count=$(git -C "$FINANCES_DIR" ls-files --others --exclude-standard | wc -l)
        if [[ "$untracked_count" -gt 0 ]]; then
            echo "finances[WARN]: $untracked_count untracked file(s):"
            git -C "$FINANCES_DIR" ls-files --others --exclude-standard
        fi
        git -C "$FINANCES_DIR" add -A
        git -C "$FINANCES_DIR" commit || return 1
    fi
    usb_push finances
    usb_sync finances
}
finances_pull() {
    usb_pull finances
    usb_sync finances
}
# --- Section 2 Aliases ---
alias hlpush='finances_push'
alias hlpull='finances_pull'
