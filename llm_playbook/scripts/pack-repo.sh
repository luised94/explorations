#!/bin/sh
# pack-repo.sh -- transport packer for the playbook (T-015b, ADR-021).
# Gets a chosen file set INTO a chat, two ways:
#   archive mode (default): git archive --format=tar.gz of the set at
#     HEAD, written to /tmp; the HEAD SHA is echoed.
#   paste mode (-p): the same set concatenated into one text block in a
#     /tmp temp file; with -e the file opens in an editor first,
#     otherwise its path is printed for the author to copy out.
#
# INVARIANTS (ADR-021):
#   scratch-only    -- writes ONLY under /tmp, NEVER into the git tree.
#   committed-read  -- reads ONLY committed content (git archive / git
#                      show see HEAD). A file must be committed BEFORE
#                      it can be packed; an uncommitted render is a
#                      documented gotcha, caught below.
#   idempotent      -- same SHA and same file set produce byte-identical
#                      output; never appends or mutates in place.
# This increment does archive-or-paste ONLY. Base-plus-overlay
# COMPOSITION is a separate later increment (ADR-022 staging); this
# script deliberately does not compose.
# ASCII only. POSIX sh.

set -u

usage() {
  echo "usage: pack-repo.sh [-p] [-e] [-n] [-o OUTDIR] PATH [PATH ...]" >&2
  echo "  -p        paste mode (text block) instead of archive mode" >&2
  echo "  -e        paste mode only: open the temp file in \$EDITOR/nvim" >&2
  echo "  -n        list the files that WOULD be packed, then exit" >&2
  echo "  -o OUTDIR scratch dir for output (must be under /tmp; default /tmp)" >&2
  echo "  PATH may be a file or a directory; directories expand to their" >&2
  echo "  committed files." >&2
  exit 2
}

MODE=archive
EDIT=0
DRYRUN=0
OUTDIR=/tmp
while getopts "peno:" opt; do
  case "$opt" in
    p) MODE=paste ;;
    e) EDIT=1 ;;
    n) DRYRUN=1 ;;
    o) OUTDIR="$OPTARG" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[ $# -ge 1 ] || usage

# --- -e is meaningful only in paste mode; never accept it silently ----
if [ "$EDIT" -eq 1 ] && [ "$MODE" != paste ]; then
  echo "pack-repo.sh: -e applies to paste mode only; add -p (or drop -e)" >&2
  exit 2
fi

# --- scratch-only guard: refuse any OUTDIR not under /tmp -------------
case "$OUTDIR" in
  /tmp|/tmp/*) : ;;
  *) echo "pack-repo.sh: OUTDIR must be under /tmp (scratch-only); got $OUTDIR" >&2
     exit 1 ;;
esac
[ -d "$OUTDIR" ] || mkdir -p "$OUTDIR"

# --- must be inside a git repo; resolve HEAD as ground truth ----------
ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "pack-repo.sh: not inside a git repository" >&2; exit 1; }
SHA="$(git rev-parse HEAD 2>/dev/null)" || {
  echo "pack-repo.sh: repository has no commits (nothing to pack)" >&2; exit 1; }
SHORT="$(printf '%s' "$SHA" | cut -c1-8)"

# --- committed-read guard + directory expansion -----------------------
# Every requested path must exist AT HEAD (catches the documented
# gotcha: packing a render before committing it). A directory expands
# to its committed files, so paste mode emits CONTENTS, not a tree
# listing. FILES holds the newline-separated expanded set.
MISSING=0
FILES=""
for p in "$@"; do
  if ! git cat-file -e "HEAD:$p" 2>/dev/null; then
    echo "pack-repo.sh: '$p' is not committed at HEAD -- commit it before packing" >&2
    MISSING=1
    continue
  fi
  TYPE="$(git cat-file -t "HEAD:$p" 2>/dev/null)"
  if [ "$TYPE" = tree ]; then
    EXPANDED="$(git ls-tree -r --name-only HEAD -- "$p")"
    if [ -z "$EXPANDED" ]; then
      echo "pack-repo.sh: '$p' is an empty directory at HEAD" >&2
      MISSING=1
      continue
    fi
    FILES="$FILES$EXPANDED
"
  else
    FILES="$FILES$p
"
  fi
done
[ "$MISSING" -eq 0 ] || exit 1

# --- dry run: show the expanded set and its size, then stop ----------
if [ "$DRYRUN" -eq 1 ]; then
  COUNT=$(printf '%s' "$FILES" | grep -c .)
  echo "$FILES" | grep . 
  echo "--"
  echo "$COUNT files would be packed at SHA $SHA"
  exit 0
fi

if [ "$MODE" = archive ]; then
  # --- archive mode -------------------------------------------------
  OUT="$OUTDIR/pack-$SHORT.tar.gz"
  # git archive output is deterministic for a fixed SHA and path set,
  # so rerunning overwrites with byte-identical content (idempotent).
  git archive --format=tar.gz -o "$OUT" HEAD -- "$@" || {
    echo "pack-repo.sh: git archive failed" >&2; exit 1; }
  echo "packed (archive) at SHA $SHA"
  echo "  $OUT"
else
  # --- paste mode ---------------------------------------------------
  OUT="$OUTDIR/pack-$SHORT.txt"
  # Rebuild from scratch each run (idempotent; never append).
  : > "$OUT"
  {
    echo "# pack at SHA $SHA"
    echo "# file set: $*"
    echo ""
    echo "$FILES" | grep . | while read -r f; do
      echo "===== BEGIN $f ====="
      git show "HEAD:$f"
      echo "===== END $f ====="
      echo ""
    done
  } > "$OUT"
  if [ "$EDIT" -eq 1 ]; then
    ED="${EDITOR:-nvim}"
    if command -v "$ED" >/dev/null 2>&1; then
      "$ED" "$OUT"
    else
      echo "pack-repo.sh: editor '$ED' not found; temp file left at path below" >&2
    fi
  fi
  echo "packed (paste) at SHA $SHA"
  echo "  $OUT"
fi
exit 0
