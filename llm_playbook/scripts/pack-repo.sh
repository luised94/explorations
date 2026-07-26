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
#                      it can be packed. This is ENFORCED, not merely
#                      documented: a target whose working-tree state
#                      differs from HEAD -- modified, staged, deleted,
#                      or containing untracked files -- is rejected
#                      rather than packed silently from HEAD.
#   idempotent      -- same SHA and same file set produce byte-identical
#                      output; never appends or mutates in place.
#
# EXIT CODES:
#   0  packed (or listed, under -n)
#   1  environment / git failure (no repo, no commits, bad OUTPUT_DIRECTORY)
#   2  usage error
#   3  input rejected (untracked, dirty, targets in two working trees)
# PATHS AND REPO SELECTION:
#   Targets may be absolute or relative, with or without a trailing
#   slash; all are normalized to repo-root-relative before use.
#   WHICH repo is inferred from the TARGETS, not from cwd, so the
#   script runs from anywhere. All targets in one invocation must
#   resolve to the SAME working tree: one pack, one SHA, which is the
#   property that makes a pack traceable to a single commit. Targets
#   that straddle are an error.
#   A submodule is a separate working tree with its own HEAD. A target
#   inside one packs that submodule at ITS HEAD; a submodule nested
#   under a packed directory is skipped with a note.
#   Paths containing newlines or tabs are NOT supported.
#
# This increment does archive-or-paste ONLY. Base-plus-overlay
# COMPOSITION is a separate later increment (ADR-022 staging); this
# script deliberately does not compose.
# ASCII only. POSIX sh.

set -u

usage() {
  echo "usage: pack-repo.sh [-p] [-e] [-n] [-o OUTPUT_DIRECTORY] PATH [PATH ...]" >&2
  echo "  -p        paste mode (text block) instead of archive mode" >&2
  echo "  -e        paste mode only: open the temp file in \$EDITOR/nvim" >&2
  echo "  -n        list the files that WOULD be packed, then exit" >&2
  echo "  -o OUTPUT_DIRECTORY" >&2
  echo "            scratch directory for output (must be under /tmp;" >&2
  echo "            default /tmp)" >&2
  echo "  PATH may be a file or a directory; directories expand to their" >&2
  echo "  committed files. PATH may be absolute or relative and is" >&2
  echo "  normalized to repository-root-relative; the repository is" >&2
  echo "  inferred from PATH, so this may be run from anywhere, but all" >&2
  echo "  PATHs must be in the same working tree." >&2
  echo "exit: 0 ok, 1 environment, 2 usage, 3 input rejected" >&2
  exit 2
}

PACK_MODE=archive
OPEN_IN_EDITOR=0
DRY_RUN=0
OUTPUT_DIRECTORY=/tmp
while getopts "peno:" OPTION_FLAG; do
  case "$OPTION_FLAG" in
    p) PACK_MODE=paste ;;
    e) OPEN_IN_EDITOR=1 ;;
    n) DRY_RUN=1 ;;
    o) OUTPUT_DIRECTORY="$OPTARG" ;;
    *) usage ;;
  esac
done
shift $((OPTIND - 1))
[ $# -ge 1 ] || usage

# --- -e is meaningful only in paste mode; never accept it silently ----
if [ "$OPEN_IN_EDITOR" -eq 1 ] && [ "$PACK_MODE" != paste ]; then
  echo "pack-repo.sh: -e applies to paste mode only; add -p (or drop -e)" >&2
  exit 2
fi

# --- scratch-only guard: refuse any OUTPUT_DIRECTORY not under /tmp -------------
case "$OUTPUT_DIRECTORY" in
  /tmp|/tmp/*) : ;;
  *) echo "pack-repo.sh: OUTPUT_DIRECTORY must be under /tmp (scratch-only); got $OUTPUT_DIRECTORY" >&2
     exit 1 ;;
esac
[ -d "$OUTPUT_DIRECTORY" ] || mkdir -p "$OUTPUT_DIRECTORY"

# --- normalize each target's FORM -------------------------------------
# Strip trailing slashes, make absolute against the invocation cwd, and
# resolve symlinks physically. `cd ... && pwd -P` is used rather than
# realpath, which is neither POSIX nor present on a stock macOS. A
# target need not exist on disk (it may be tracked at HEAD and deleted
# locally), so walk up to the deepest ancestor that DOES exist, resolve
# that, and re-attach the walked-off suffix.
INVOCATION_DIRECTORY="$(pwd -P)"
INFERRED_WORKTREE_ROOT=""
FIRST_TARGET_FOR_ROOT=""
NORMALIZED_TARGETS=""
REWRITTEN_TARGET_FORMS=""
for REQUESTED_TARGET in "$@"; do
  TRIMMED_TARGET="$REQUESTED_TARGET"
  while [ "${TRIMMED_TARGET%/}" != "$TRIMMED_TARGET" ] && [ "$TRIMMED_TARGET" != / ]; do TRIMMED_TARGET="${TRIMMED_TARGET%/}"; done
  case "$TRIMMED_TARGET" in
    /*) ABSOLUTE_TARGET="$TRIMMED_TARGET" ;;
    *)  ABSOLUTE_TARGET="$INVOCATION_DIRECTORY/$TRIMMED_TARGET" ;;
  esac
  EXISTING_ANCESTOR_DIRECTORY="$ABSOLUTE_TARGET"
  MISSING_PATH_SUFFIX=""
  while [ ! -d "$EXISTING_ANCESTOR_DIRECTORY" ] && [ "$EXISTING_ANCESTOR_DIRECTORY" != / ]; do
    REMOVED_PATH_SEGMENT="${EXISTING_ANCESTOR_DIRECTORY##*/}"
    EXISTING_ANCESTOR_DIRECTORY="${EXISTING_ANCESTOR_DIRECTORY%/*}"
    [ -n "$EXISTING_ANCESTOR_DIRECTORY" ] || EXISTING_ANCESTOR_DIRECTORY=/
    if [ -z "$MISSING_PATH_SUFFIX" ]; then MISSING_PATH_SUFFIX="$REMOVED_PATH_SEGMENT"; else MISSING_PATH_SUFFIX="$REMOVED_PATH_SEGMENT/$MISSING_PATH_SUFFIX"; fi
  done
  RESOLVED_ANCESTOR_DIRECTORY="$(cd "$EXISTING_ANCESTOR_DIRECTORY" 2>/dev/null && pwd -P)" || RESOLVED_ANCESTOR_DIRECTORY=""
  if [ -z "$RESOLVED_ANCESTOR_DIRECTORY" ]; then
    echo "pack-repo.sh: cannot resolve '$REQUESTED_TARGET' (no readable ancestor directory)" >&2
    exit 3
  fi
  if [ -n "$MISSING_PATH_SUFFIX" ]; then ABSOLUTE_TARGET="$RESOLVED_ANCESTOR_DIRECTORY/$MISSING_PATH_SUFFIX"; else ABSOLUTE_TARGET="$RESOLVED_ANCESTOR_DIRECTORY"; fi

  # Which working tree encloses this target? Inferring from the TARGET
  # rather than from cwd is what allows invocation from anywhere. A
  # linked worktree and a submodule each report their own toplevel,
  # which is correct: each has its own HEAD.
  TARGET_WORKTREE_ROOT="$(cd "$RESOLVED_ANCESTOR_DIRECTORY" && git rev-parse --show-toplevel 2>/dev/null)" || TARGET_WORKTREE_ROOT=""
  if [ -z "$TARGET_WORKTREE_ROOT" ]; then
    echo "pack-repo.sh: '$REQUESTED_TARGET' is not inside a git repository" >&2
    exit 1
  fi
  TARGET_WORKTREE_ROOT="$(cd "$TARGET_WORKTREE_ROOT" && pwd -P)"

  # One pack, one SHA. Targets that land in different working trees have
  # different HEADs, so the pack could not be traced to a single commit.
  # This is the property the old "run from inside the repo" rule bought,
  # kept explicitly now that cwd no longer decides.
  if [ -z "$INFERRED_WORKTREE_ROOT" ]; then
    INFERRED_WORKTREE_ROOT="$TARGET_WORKTREE_ROOT"
    FIRST_TARGET_FOR_ROOT="$REQUESTED_TARGET"
  elif [ "$TARGET_WORKTREE_ROOT" != "$INFERRED_WORKTREE_ROOT" ]; then
    echo "pack-repo.sh: targets span two working trees (one pack, one SHA):" >&2
    echo "  $INFERRED_WORKTREE_ROOT  <- $FIRST_TARGET_FOR_ROOT" >&2
    echo "  $TARGET_WORKTREE_ROOT  <- $REQUESTED_TARGET" >&2
    exit 3
  fi

  # Re-express root-relative. The prefix is quoted inside the parameter
  # expansion because the operand is a PATTERN: an unquoted root
  # containing [ * or ? would silently fail to strip. A target that is
  # the root itself becomes "." -- never the empty string, which git
  # rejects as a pathspec.
  if [ "$ABSOLUTE_TARGET" = "$INFERRED_WORKTREE_ROOT" ]; then
    REPO_RELATIVE_TARGET="."
  elif [ "$INFERRED_WORKTREE_ROOT" = / ]; then
    REPO_RELATIVE_TARGET="${ABSOLUTE_TARGET#/}"
  else
    REPO_RELATIVE_TARGET="${ABSOLUTE_TARGET#"$INFERRED_WORKTREE_ROOT"/}"
  fi
  # Drop an exact repeat, keeping first-seen order (the file set order
  # is author-meaningful, so sort -u is wrong). Normalization makes
  # repeats likelier: ~/dev/x/drill/ and drill now collapse to one
  # string and can no longer be told apart by eye.
  if printf '%s' "$NORMALIZED_TARGETS" | grep -Fxq -e "$REPO_RELATIVE_TARGET"; then
    continue
  fi
  NORMALIZED_TARGETS="$NORMALIZED_TARGETS$REPO_RELATIVE_TARGET
"
  if [ "$REPO_RELATIVE_TARGET" != "$REQUESTED_TARGET" ]; then
    REWRITTEN_TARGET_FORMS="$REWRITTEN_TARGET_FORMS  $REQUESTED_TARGET  ->  $REPO_RELATIVE_TARGET
"
  fi
done

# --- adopt the inferred root; everything below is root-relative -------
# From here on the script speaks ONE dialect of path: root-relative.
# cwd is moved to the root so pathspecs mean the same thing to every
# git invocation below, including git archive.
WORKTREE_ROOT="$INFERRED_WORKTREE_ROOT"
cd "$WORKTREE_ROOT" || { echo "pack-repo.sh: cannot enter $WORKTREE_ROOT" >&2; exit 1; }

# Replace the positional parameters with the normalized set. Field
# splitting on newline with globbing off is safe because a path
# containing a newline is unsupported (see header).
set -f
IFS='
'
set -- $NORMALIZED_TARGETS
unset IFS
set +f

HEAD_COMMIT_SHA="$(git rev-parse HEAD 2>/dev/null)" || {
  echo "pack-repo.sh: repository has no commits (nothing to pack)" >&2; exit 1; }
HEAD_COMMIT_SHORT_SHA="$(printf '%s' "$HEAD_COMMIT_SHA" | cut -c1-8)"

# --- committed-read guard + directory expansion -----------------------
# Every requested path must exist AT HEAD (catches the documented
# gotcha: packing a render before committing it). A directory expands
# to its committed files, so paste mode emits CONTENTS, not a tree
# listing. EXPANDED_FILE_SET holds the newline-separated expanded set.
INPUT_REJECTED=0
EXPANDED_FILE_SET=""
SKIPPED_SUBMODULES=""
for NORMALIZED_TARGET in "$@"; do
  # "." is the root tree; HEAD:. is not a valid object name.
  if [ "$NORMALIZED_TARGET" = . ]; then HEAD_OBJECT_NAME="HEAD^{tree}"; else HEAD_OBJECT_NAME="HEAD:$NORMALIZED_TARGET"; fi

  if ! git cat-file -e "$HEAD_OBJECT_NAME" 2>/dev/null; then
    if git ls-files --error-unmatch -- "$NORMALIZED_TARGET" >/dev/null 2>&1; then
      echo "pack-repo.sh: '$NORMALIZED_TARGET' is staged but not committed at HEAD -- commit it before packing" >&2
    else
      echo "pack-repo.sh: '$NORMALIZED_TARGET' is not tracked in $WORKTREE_ROOT at HEAD" >&2
    fi
    INPUT_REJECTED=1
    continue
  fi

  # Dirty check. --porcelain rather than diff --quiet HEAD because it
  # also reports UNTRACKED files: the trap that otherwise omits a new
  # render from the pack in silence, with nothing printed at all.
  # Ignored files are excluded by default, so build artifacts and
  # editor droppings do not trip it.
  WORKTREE_STATUS="$(git status --porcelain -- "$NORMALIZED_TARGET")"
  if [ -n "$WORKTREE_STATUS" ]; then
    if printf '%s\n' "$WORKTREE_STATUS" | grep -q -e '^D' -e '^.D'; then
      echo "pack-repo.sh: '$NORMALIZED_TARGET' has uncommitted changes -- commit them (or restore deleted files) before packing" >&2
    else
      echo "pack-repo.sh: '$NORMALIZED_TARGET' has uncommitted changes -- commit them before packing" >&2
    fi
    printf '%s\n' "$WORKTREE_STATUS" | head -n 10 | sed 's/^/    /' >&2
    WORKTREE_STATUS_LINE_COUNT=$(printf '%s\n' "$WORKTREE_STATUS" | grep -c .)
    if [ "$WORKTREE_STATUS_LINE_COUNT" -gt 10 ]; then
      echo "    ... and $((WORKTREE_STATUS_LINE_COUNT - 10)) more" >&2
    fi
    INPUT_REJECTED=1
    continue
  fi

  HEAD_OBJECT_TYPE="$(git cat-file -t "$HEAD_OBJECT_NAME" 2>/dev/null)"
  if [ "$HEAD_OBJECT_TYPE" = tree ]; then
    # Blobs only. ls-tree also emits gitlinks (mode 160000, type
    # commit) for nested submodules; paste mode would then run
    # git show on one and get no file content, while archive mode
    # skips it silently -- so the two modes disagreed. quotePath=false
    # stops git C-quoting non-ASCII paths into an unusable literal.
    EXPANDED_BLOB_PATHS="$(git -c core.quotePath=false ls-tree -r HEAD -- "$NORMALIZED_TARGET" \
      | awk -F'\t' '{ split($1, a, " "); if (a[2] == "blob") print $2 }')"
    SUBMODULE_GITLINK_PATHS="$(git -c core.quotePath=false ls-tree -r HEAD -- "$NORMALIZED_TARGET" \
      | awk -F'\t' '{ split($1, a, " "); if (a[2] == "commit") print $2 }')"
    if [ -n "$SUBMODULE_GITLINK_PATHS" ]; then
      SKIPPED_SUBMODULES="$SKIPPED_SUBMODULES$SUBMODULE_GITLINK_PATHS
"
    fi
    if [ -z "$EXPANDED_BLOB_PATHS" ]; then
      echo "pack-repo.sh: '$NORMALIZED_TARGET' is an empty directory at HEAD" >&2
      INPUT_REJECTED=1
      continue
    fi
    EXPANDED_FILE_SET="$EXPANDED_FILE_SET$EXPANDED_BLOB_PATHS
"
  else
    EXPANDED_FILE_SET="$EXPANDED_FILE_SET$NORMALIZED_TARGET
"
  fi
done
[ "$INPUT_REJECTED" -eq 0 ] || exit 3

# A nested submodule is a separate working tree with its own HEAD, so
# it cannot be part of this pack. Not an error -- the pack is still
# complete for what it claims to cover -- but noted, so nobody assumes
# the submodule's contents are in the file. Under -n the summary block
# lists these instead, so do not say it twice.
if [ -n "$SKIPPED_SUBMODULES" ] && [ "$DRY_RUN" -eq 0 ]; then
  printf '%s' "$SKIPPED_SUBMODULES" | grep . | while read -r SUBMODULE_PATH; do
    echo "pack-repo.sh: note: skipped submodule '$SUBMODULE_PATH' (pack it separately)" >&2
  done
fi

# --- dry run: show the expanded set and its size, then stop ----------
if [ "$DRY_RUN" -eq 1 ]; then
  # The list is the body and stays first; the summary goes AFTER it so
  # it survives a scroll on a repo with many files. Both the list and
  # the count go through one pipeline -- they used to differ (printf
  # '%s' vs echo) and could disagree by one on an empty set.
  printf '%s\n' "$EXPANDED_FILE_SET" | grep .
  echo "--"
  echo "repo:   $WORKTREE_ROOT"
  echo "SHA:    $HEAD_COMMIT_SHA"
  if [ -n "$REWRITTEN_TARGET_FORMS" ]; then
    # Only targets whose FORM actually changed, so the ordinary
    # repo-relative invocation stays quiet.
    echo "normalized:"
    printf '%s' "$REWRITTEN_TARGET_FORMS"
  fi
  if [ -n "$SKIPPED_SUBMODULES" ]; then
    echo "skipped:"
    printf '%s' "$SKIPPED_SUBMODULES" | grep . | sed 's/^/  /;s/$/ (submodule)/'
  fi
  PACKED_FILE_COUNT=$(printf '%s\n' "$EXPANDED_FILE_SET" | grep -c .)
  echo "$PACKED_FILE_COUNT files would be packed"
  exit 0
fi

if [ "$PACK_MODE" = archive ]; then
  # --- archive mode -------------------------------------------------
  OUTPUT_FILE_PATH="$OUTPUT_DIRECTORY/pack-$HEAD_COMMIT_SHORT_SHA.tar.gz"
  # "$@" is the NORMALIZED, root-relative set, and cwd is the root, so
  # git archive resolves the same pathspecs the guard validated. It
  # previously received the raw arguments and resolved them against
  # cwd while the guard resolved against the root, so from a
  # subdirectory the two could pack different sets.
  #
  # The targets are passed, not the expanded file set: the two cover
  # the same content (git archive skips gitlinks as the expansion now
  # does), and the short list cannot run into ARG_MAX on a large tree.
  #
  # git archive output is deterministic for a fixed SHA, path set and
  # git version, so rerunning overwrites with byte-identical content
  # (idempotent).
  git archive --format=tar.gz -o "$OUTPUT_FILE_PATH" HEAD -- "$@" || {
    echo "pack-repo.sh: git archive failed" >&2; exit 1; }
  echo "packed (archive) from $WORKTREE_ROOT at SHA $HEAD_COMMIT_SHA"
  echo "  $OUTPUT_FILE_PATH"
else
  # --- paste mode ---------------------------------------------------
  OUTPUT_FILE_PATH="$OUTPUT_DIRECTORY/pack-$HEAD_COMMIT_SHORT_SHA.txt"
  # Rebuild from scratch each run (idempotent; never append).
  : > "$OUTPUT_FILE_PATH"
  {
    echo "# pack at SHA $HEAD_COMMIT_SHA"
    echo "# file set: $*"
    echo ""
    echo "$EXPANDED_FILE_SET" | grep . | while read -r PACKED_FILE_PATH; do
      # Capture once so the line count and the body come from the same
      # read; %%%%% is the boundary marker because it cannot collide
      # with markdown, Python, or JavaScript at line start.
      FILE_CONTENT_AT_HEAD="$(git show "HEAD:$PACKED_FILE_PATH")"
      FILE_LINE_COUNT=$(printf '%s\n' "$FILE_CONTENT_AT_HEAD" | wc -l | tr -d ' ')
      echo "%%%%% BEGIN $PACKED_FILE_PATH ($FILE_LINE_COUNT lines)"
      printf '%s\n' "$FILE_CONTENT_AT_HEAD"
      echo "%%%%% END $PACKED_FILE_PATH"
      echo ""
    done
  } > "$OUTPUT_FILE_PATH"
  if [ "$OPEN_IN_EDITOR" -eq 1 ]; then
    EDITOR_COMMAND="${EDITOR:-nvim}"
    if command -v "$EDITOR_COMMAND" >/dev/null 2>&1; then
      "$EDITOR_COMMAND" "$OUTPUT_FILE_PATH"
    else
      echo "pack-repo.sh: editor '$EDITOR_COMMAND' not found; temp file left at path below" >&2
    fi
  fi
  echo "packed (paste) from $WORKTREE_ROOT at SHA $HEAD_COMMIT_SHA"
  echo "  $OUTPUT_FILE_PATH"
fi
exit 0
