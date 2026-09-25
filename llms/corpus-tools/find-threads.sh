#!/bin/sh
# find-threads.sh -- list files that are NAMED after, or MENTION, a thread.
# usage: find-threads.sh 'EXTENDED_REGEX' DIRECTORY [DIRECTORY ...]
#
# Scraped Windows captures are often UTF-16, which plain grep treats as
# binary and silently skips. Deleting every NUL byte turns the ASCII
# range of UTF-16 (either byte order, with or without a byte-order
# mark) back into plain ASCII, and leaves UTF-8 files untouched.
#
# Zip archives are compressed, so grep sees nothing inside them. Each
# member is searched on its own and reported as archive.zip!member, so
# the hit names the page, not only the bundle. Python's zipfile does
# the reading because unzip is not installed on a default WSL image;
# the pattern must therefore also be valid as a Python regex, which a
# plain ERE of alternatives, classes and repeats is.
#
# Output: match count, modification date, path. Highest count first,
# newest first within a count. A filename match adds one.
# ASCII only. POSIX sh plus python3.
set -u
[ $# -ge 2 ] || { echo "usage: find-threads.sh 'REGEX' DIRECTORY..." >&2; exit 2; }
THREAD_PATTERN="$1"; shift
find "$@" -type f -print | while IFS= read -r CANDIDATE_PATH; do
  case "$CANDIDATE_PATH" in
    *.zip|*.ZIP)
      python3 - "$THREAD_PATTERN" "$CANDIDATE_PATH" <<'PYTHON'
import os, re, sys, time, zipfile
thread_pattern = re.compile(sys.argv[1], re.IGNORECASE)
archive_path = sys.argv[2]
archive_modified_date = time.strftime("%Y-%m-%d %H:%M", time.localtime(os.path.getmtime(archive_path)))
try:
    archive = zipfile.ZipFile(archive_path)
except Exception as archive_error:
    # A truncated or non-zip file named .zip is reported, not fatal.
    print("unreadable zip: %s (%s)" % (archive_path, archive_error), file=sys.stderr)
    sys.exit(0)
for member_name in archive.namelist():
    try:
        member_bytes = archive.read(member_name)
    except Exception as member_error:
        print("unreadable member: %s!%s (%s)" % (archive_path, member_name, member_error), file=sys.stderr)
        continue
    member_text = member_bytes.replace(b"\x00", b"").decode("utf-8", "replace")
    match_count = sum(1 for member_line in member_text.splitlines() if thread_pattern.search(member_line))
    if thread_pattern.search(os.path.basename(member_name)):
        match_count += 1
    if match_count > 0:
        print("%6d  %s  %s!%s" % (match_count, archive_modified_date, archive_path, member_name))
PYTHON
      continue ;;
  esac
  MATCH_COUNT="$(tr -d '\000' < "$CANDIDATE_PATH" | grep -aciE "$THREAD_PATTERN")"
  if basename "$CANDIDATE_PATH" | grep -qiE "$THREAD_PATTERN"; then
    MATCH_COUNT=$((MATCH_COUNT + 1))
  fi
  [ "$MATCH_COUNT" -gt 0 ] || continue
  MODIFIED_DATE="$(date -r "$CANDIDATE_PATH" '+%Y-%m-%d %H:%M')"
  printf '%6s  %s  %s\n' "$MATCH_COUNT" "$MODIFIED_DATE" "$CANDIDATE_PATH"
done | sort -k1,1nr -k2,3r
