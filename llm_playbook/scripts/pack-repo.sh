#!/bin/sh
# pack-repo.sh -- transport packer for the playbook (T-015b, ADR-021).
# Gets a chosen file set INTO a chat, two ways:
#   archive mode (default): git archive --format=tar.gz of the set at
#     HEAD, written to /tmp; the HEAD SHA is echoed.
#   paste mode (-p): the same set concatenated into one text block in a
#     /tmp temp file; with -e the file opens in an editor first,
#     otherwise its path is printed for the author to copy out. Each
#     file is fenced with %%%%% BEGIN <path> (<n> lines) and %%%%% END
#     <path>; the marker is chosen to be greppable and to never occur
#     at line start in markdown, Python, or JavaScript.
#
# INVARIANTS (ADR-021):
#   scratch-only    -- writes ONLY under /tmp, NEVER into the git tree.
#   committed-read  -- reads ONLY committed content (git archive / git
#                      show see HEAD). A file must be committed BEFORE
#                      it can be packed; an uncommitted render is a
#                      documented gotcha, caught below.
#   idempotent      -- same SHA and same file set produce byte-identical
#                      output; never appends or mutates in place.
#
# EXIT CODES:
#   0  packed (or listed, under -n)
#   1  environment / git failure (no repo, no commits, bad OUTDIR)
#   2  usage error
#   3  input rejected (untracked, dirty, targets in two working trees)
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

# --- normalize each target's FORM -------------------------------------
# Strip trailing slashes, make absolute against the invocation cwd, and
# resolve symlinks physically. `cd ... && pwd -P` is used rather than
# realpath, which is neither POSIX nor present on a stock macOS. A
# target need not exist on disk (it may be tracked at HEAD and deleted
# locally), so walk up to the deepest ancestor that DOES exist, resolve
# that, and re-attach the walked-off suffix.
ORIGDIR="$(pwd -P)"
NEWROOT=""
ROOTSRC=""
NORM=""
CHANGED=""
for p in "$@"; do
  T="$p"
  while [ "${T%/}" != "$T" ] && [ "$T" != / ]; do T="${T%/}"; done
  case "$T" in
    /*) ABS="$T" ;;
    *)  ABS="$ORIGDIR/$T" ;;
  esac
  DIR="$ABS"
  SUFFIX=""
  while [ ! -d "$DIR" ] && [ "$DIR" != / ]; do
    BASE="${DIR##*/}"
    DIR="${DIR%/*}"
    [ -n "$DIR" ] || DIR=/
    if [ -z "$SUFFIX" ]; then SUFFIX="$BASE"; else SUFFIX="$BASE/$SUFFIX"; fi
  done
  PHYS="$(cd "$DIR" 2>/dev/null && pwd -P)" || PHYS=""
  if [ -z "$PHYS" ]; then
    echo "pack-repo.sh: cannot resolve '$p' (no readable ancestor directory)" >&2
    exit 3
  fi
  if [ -n "$SUFFIX" ]; then ABS="$PHYS/$SUFFIX"; else ABS="$PHYS"; fi

  # Which working tree encloses this target? Inferring from the TARGET
  # rather than from cwd is what allows invocation from anywhere. A
  # linked worktree and a submodule each report their own toplevel,
  # which is correct: each has its own HEAD.
  TOP="$(cd "$PHYS" && git rev-parse --show-toplevel 2>/dev/null)" || TOP=""
  if [ -z "$TOP" ]; then
    echo "pack-repo.sh: '$p' is not inside a git repository" >&2
    exit 1
  fi
  TOP="$(cd "$TOP" && pwd -P)"

  # One pack, one SHA. Targets that land in different working trees have
  # different HEADs, so the pack could not be traced to a single commit.
  # This is the property the old "run from inside the repo" rule bought,
  # kept explicitly now that cwd no longer decides.
  if [ -z "$NEWROOT" ]; then
    NEWROOT="$TOP"
    ROOTSRC="$p"
  elif [ "$TOP" != "$NEWROOT" ]; then
    echo "pack-repo.sh: targets span two working trees (one pack, one SHA):" >&2
    echo "  $NEWROOT  <- $ROOTSRC" >&2
    echo "  $TOP  <- $p" >&2
    exit 3
  fi

  # Re-express root-relative. The prefix is quoted inside the parameter
  # expansion because the operand is a PATTERN: an unquoted root
  # containing [ * or ? would silently fail to strip. A target that is
  # the root itself becomes "." -- never the empty string, which git
  # rejects as a pathspec.
  if [ "$ABS" = "$NEWROOT" ]; then
    REL="."
  elif [ "$NEWROOT" = / ]; then
    REL="${ABS#/}"
  else
    REL="${ABS#"$NEWROOT"/}"
  fi
  # Drop an exact repeat, keeping first-seen order (the file set order
  # is author-meaningful, so sort -u is wrong). Normalization makes
  # repeats likelier: ~/dev/x/drill/ and drill now collapse to one
  # string and can no longer be told apart by eye.
  if printf '%s' "$NORM" | grep -Fxq -e "$REL"; then
    continue
  fi
  NORM="$NORM$REL
"
  if [ "$REL" != "$p" ]; then
    CHANGED="$CHANGED  $p  ->  $REL
"
  fi
done

# --- adopt the inferred root; everything below is root-relative -------
# From here on the script speaks ONE dialect of path: root-relative.
# cwd is moved to the root so pathspecs mean the same thing to every
# git invocation below, including git archive.
ROOT="$NEWROOT"
cd "$ROOT" || { echo "pack-repo.sh: cannot enter $ROOT" >&2; exit 1; }

# Replace the positional parameters with the normalized set. Field
# splitting on newline with globbing off is safe because a path
# containing a newline is unsupported (see header).
set -f
IFS='
'
set -- $NORM
unset IFS
set +f

SHA="$(git rev-parse HEAD 2>/dev/null)" || {
  echo "pack-repo.sh: repository has no commits (nothing to pack)" >&2; exit 1; }
SHORT="$(printf '%s' "$SHA" | cut -c1-8)"

# --- committed-read guard + directory expansion -----------------------
# Every requested path must exist AT HEAD (catches the documented
# gotcha: packing a render before committing it). A directory expands
# to its committed files, so paste mode emits CONTENTS, not a tree
# listing. FILES holds the newline-separated expanded set.
REJECT=0
FILES=""
SKIPPED=""
for p in "$@"; do
  # "." is the root tree; HEAD:. is not a valid object name.
  if [ "$p" = . ]; then OBJ="HEAD^{tree}"; else OBJ="HEAD:$p"; fi

  if ! git cat-file -e "$OBJ" 2>/dev/null; then
    if git ls-files --error-unmatch -- "$p" >/dev/null 2>&1; then
      echo "pack-repo.sh: '$p' is staged but not committed at HEAD -- commit it before packing" >&2
    else
      echo "pack-repo.sh: '$p' is not tracked in $ROOT at HEAD" >&2
    fi
    REJECT=1
    continue
  fi

  # Dirty check. --porcelain rather than diff --quiet HEAD because it
  # also reports UNTRACKED files: the trap that otherwise omits a new
  # render from the pack in silence, with nothing printed at all.
  # Ignored files are excluded by default, so build artifacts and
  # editor droppings do not trip it.
  ST="$(git status --porcelain -- "$p")"
  if [ -n "$ST" ]; then
    if printf '%s\n' "$ST" | grep -q -e '^D' -e '^.D'; then
      echo "pack-repo.sh: '$p' has uncommitted changes -- commit them (or restore deleted files) before packing" >&2
    else
      echo "pack-repo.sh: '$p' has uncommitted changes -- commit them before packing" >&2
    fi
    printf '%s\n' "$ST" | head -n 10 | sed 's/^/    /' >&2
    NST=$(printf '%s\n' "$ST" | grep -c .)
    if [ "$NST" -gt 10 ]; then
      echo "    ... and $((NST - 10)) more" >&2
    fi
    REJECT=1
    continue
  fi

  TYPE="$(git cat-file -t "$OBJ" 2>/dev/null)"
  if [ "$TYPE" = tree ]; then
    # Blobs only. ls-tree also emits gitlinks (mode 160000, type
    # commit) for nested submodules; paste mode would then run
    # git show on one and get no file content, while archive mode
    # skips it silently -- so the two modes disagreed. quotePath=false
    # stops git C-quoting non-ASCII paths into an unusable literal.
    EXPANDED="$(git -c core.quotePath=false ls-tree -r HEAD -- "$p" \
      | awk -F'\t' '{ split($1, a, " "); if (a[2] == "blob") print $2 }')"
    LINKS="$(git -c core.quotePath=false ls-tree -r HEAD -- "$p" \
      | awk -F'\t' '{ split($1, a, " "); if (a[2] == "commit") print $2 }')"
    if [ -n "$LINKS" ]; then
      SKIPPED="$SKIPPED$LINKS
"
    fi
    if [ -z "$EXPANDED" ]; then
      echo "pack-repo.sh: '$p' is an empty directory at HEAD" >&2
      REJECT=1
      continue
    fi
    FILES="$FILES$EXPANDED
"
  else
    FILES="$FILES$p
"
  fi
done
[ "$REJECT" -eq 0 ] || exit 3

# A nested submodule is a separate working tree with its own HEAD, so
# it cannot be part of this pack. Not an error -- the pack is still
# complete for what it claims to cover -- but noted, so nobody assumes
# the submodule's contents are in the file. Under -n the summary block
# lists these instead, so do not say it twice.
if [ -n "$SKIPPED" ] && [ "$DRYRUN" -eq 0 ]; then
  printf '%s' "$SKIPPED" | grep . | while read -r s; do
    echo "pack-repo.sh: note: skipped submodule '$s' (pack it separately)" >&2
  done
fi

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
  # "$@" is the NORMALIZED, root-relative set, and cwd is the root, so
  # git archive resolves the same pathspecs the guard validated. It
  # previously received the raw arguments and resolved them against
  # cwd while the guard resolved against the root, so from a
  # subdirectory the two could pack different sets.
  #
  # The targets are passed, not the expanded FILES list: the two cover
  # the same content (git archive skips gitlinks as the expansion now
  # does), and the short list cannot run into ARG_MAX on a large tree.
  #
  # git archive output is deterministic for a fixed SHA, path set and
  # git version, so rerunning overwrites with byte-identical content
  # (idempotent).
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
      # Capture once so the line count and the body come from the same
      # read; %%%%% is the boundary marker because it cannot collide
      # with markdown, Python, or JavaScript at line start.
      BODY="$(git show "HEAD:$f")"
      N=$(printf '%s\n' "$BODY" | wc -l | tr -d ' ')
      echo "%%%%% BEGIN $f ($N lines)"
      printf '%s\n' "$BODY"
      echo "%%%%% END $f"
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
