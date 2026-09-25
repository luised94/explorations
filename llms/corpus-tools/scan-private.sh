#!/bin/sh
# scan-private.sh -- COUNT private-looking strings per file; never print them.
# usage: scan-private.sh PRIVATE_TERMS_FILE DIRECTORY [DIRECTORY ...]
#        SHOW_MASKED=1 scan-private.sh ...   also list each key-shaped
#        match as its first 8 characters and its length, to judge it
#        locally. Still no full value; do not paste that listing.
#
# PRIVATE_TERMS_FILE holds your own identifiers, one per line: email
# addresses, full name, phone, street address, employer, usernames. It
# stays on your machine (chmod 600) and is never pasted anywhere; an
# empty file is allowed and matches nothing.
#
# Three columns per file with any hit: email-shaped strings, key-shaped
# strings, and your listed terms. Only COUNTS are printed, so the report
# itself leaks nothing but file paths -- and paths can carry chat titles,
# so read the report before pasting it anywhere.
#
# Key shapes: OpenAI and Anthropic style sk-, GitHub ghp_ and
# github_pat_, GitLab glpat-, AWS AKIA, Slack xox?-, Hugging Face hf_,
# Google AIza, JSON web tokens (three base64url parts starting eyJ),
# bearer tokens, and PEM private-key headers. A hit is a reason to
# ROTATE that key, not only to redact it: the provider already holds
# the chat.
# Every key shape must START a token: the character before it may not
# be a letter, digit, "_" or "-". Without that, "sk-" matched inside
# ordinary words -- "ask-before-...", "task-...", "risk-..." -- and
# inflated the count with false positives.
# NUL bytes are deleted first so UTF-16 exports are read (see
# find-threads.sh). ASCII only. POSIX sh.
set -u
[ $# -ge 2 ] || { echo "usage: scan-private.sh PRIVATE_TERMS_FILE DIRECTORY..." >&2; exit 2; }
PRIVATE_TERMS_FILE="$1"; shift
[ -f "$PRIVATE_TERMS_FILE" ] || { echo "scan-private.sh: no such terms file: $PRIVATE_TERMS_FILE" >&2; exit 2; }
EMAIL_SHAPE='[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}'
KEY_SHAPE='(^|[^A-Za-z0-9_-])(sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{36}|github_pat_[A-Za-z0-9_]{20,}|glpat-[A-Za-z0-9_-]{20}|AKIA[0-9A-Z]{16}|xox[abprs]-[A-Za-z0-9-]{10,}|hf_[A-Za-z0-9]{30,}|AIza[0-9A-Za-z_-]{35}|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}|[Bb]earer [A-Za-z0-9._~+/-]{20,}|-----BEGIN [A-Z ]*PRIVATE KEY-----)'
printf '%7s %7s %7s  %s\n' emails keys terms path
find "$@" -name .git -prune -o -type f -print | while IFS= read -r SCANNED_PATH; do
  EMAIL_COUNT="$(tr -d '\000' < "$SCANNED_PATH" | grep -aoE "$EMAIL_SHAPE" | wc -l)"
  KEY_COUNT="$(tr -d '\000' < "$SCANNED_PATH" | grep -aoE "$KEY_SHAPE" | wc -l)"
  # grep -f with an empty file matches nothing, which is the wanted
  # behaviour when no personal terms have been listed yet.
  TERM_COUNT="$(tr -d '\000' < "$SCANNED_PATH" | grep -aoiF -f "$PRIVATE_TERMS_FILE" | wc -l)"
  [ $((EMAIL_COUNT + KEY_COUNT + TERM_COUNT)) -gt 0 ] || continue
  printf '%7s %7s %7s  %s\n' "$EMAIL_COUNT" "$KEY_COUNT" "$TERM_COUNT" "$SCANNED_PATH"
  if [ "${SHOW_MASKED:-0}" = 1 ] && [ "$KEY_COUNT" -gt 0 ]; then
    # Strip the one boundary character the pattern consumed, keep the
    # first 8 characters, report the length: enough to tell a word
    # from a key, not enough to use one.
    tr -d '\000' < "$SCANNED_PATH" | grep -aoE "$KEY_SHAPE" \
      | sed -E 's/^[^A-Za-z-]//' \
      | awk '{ printf "          key-shaped: %s...  (%d characters)\n", substr($0, 1, 8), length($0) }' \
      | sort | uniq -c
  fi
done
