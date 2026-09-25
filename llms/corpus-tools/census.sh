#!/bin/sh
# census.sh -- the SHAPE of each directory, never its contents or names.
# usage: census.sh DIRECTORY [DIRECTORY ...] > census-YYYYMMDD.txt
# Prints per directory: file count, disk size, file types by count, and
# the oldest and newest modification dates. It prints NO file names and
# NO file contents, so the output is safe to paste into a chat even when
# a directory holds account exports. .git directories are pruned: their
# object files are history, not material, and would swamp the counts.
# ASCII only. POSIX sh.
set -u
for CENSUS_ROOT in "$@"; do
  if [ ! -d "$CENSUS_ROOT" ]; then
    printf '== %s  MISSING\n\n' "$CENSUS_ROOT"
    continue
  fi
  FILE_COUNT="$(find "$CENSUS_ROOT" -name .git -prune -o -type f -print | wc -l)"
  DISK_SIZE="$(du -sh --exclude=.git "$CENSUS_ROOT" 2>/dev/null | cut -f1)"
  printf '== %s  (%s files, %s)\n' "$CENSUS_ROOT" "$FILE_COUNT" "$DISK_SIZE"
  # Extension only: a name with no dot is reported as "(none)" rather
  # than printed, because a bare name can itself be private.
  find "$CENSUS_ROOT" -name .git -prune -o -type f -print \
    | awk -F/ '{ file_name = $NF; if (index(file_name, ".") > 1) { sub(/.*\./, "", file_name); print tolower(file_name) } else print "(none)" }' \
    | sort | uniq -c | sort -nr | head -8
  printf '  dates: %s\n\n' "$(find "$CENSUS_ROOT" -name .git -prune -o -type f -printf '%TY-%Tm-%Td\n' | sort | sed -n '1p;$p' | tr '\n' ' ')"
done
