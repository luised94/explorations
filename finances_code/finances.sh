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
