#!/bin/sh
# render.sh -- stamp a composed render, or verify one that already exists.
#
# WHAT THIS DOES NOT DO, DELIBERATELY: it does not compose. Choosing
# which preference items survive, and which project instance rule beats
# which playbook rule, is the authoring-time precedence judgment
# (protocol.md, PRECEDENCE) and it is the human's. Automating it would
# hide the only step that carries thought. What IS mechanical is the
# stamp: resolving the source SHA and computing a
# sha1 over the body. Doing that by hand is how a stamp goes stale
# without anyone noticing.
#
# The render is a COMMITTED artifact. A stamp can only be compared
# against something that exists on disk, so this writes a file rather
# than emitting a block to paste. That is also why rendering is not a
# stage of packing: a render generated during a pack would be
# ephemeral, and nothing could later detect that it had drifted.
#
# ASCII only. POSIX sh.

set -u

USAGE='usage:
  render.sh stamp  <body-file> <output-file>   compose done, write stamped render
  render.sh verify <render-file>               recompute and compare the stamp'

# The body is everything from line 3 onward. Lines 1 and 2 are the
# do-not-edit notice and the stamp itself, excluded so that the hash is
# computable -- a hash covering the line it is written on cannot exist.
BODY_STARTS_AT_LINE=3

DO_NOT_EDIT_NOTICE='DO NOT EDIT. Generated; fixes go to refinements, then rerender.'

[ $# -ge 1 ] || { echo "$USAGE" >&2; exit 2; }
REQUESTED_MODE="$1"

WORKTREE_ROOT="$(git rev-parse --show-toplevel 2>/dev/null)" || {
  echo "render.sh: not inside a git repository" >&2; exit 1; }

case "$REQUESTED_MODE" in

stamp)
  [ $# -eq 3 ] || { echo "$USAGE" >&2; exit 2; }
  COMPOSED_BODY_PATH="$2"
  RENDER_OUTPUT_PATH="$3"

  [ -f "$COMPOSED_BODY_PATH" ] || {
    echo "render.sh: no such body file: $COMPOSED_BODY_PATH" >&2; exit 1; }

  # No version number in the stamp. A hand-maintained semver says nothing
  # the source SHA does not say precisely, and it is one more figure that
  # goes stale silently. The SHA answers "which sources", the hash answers
  # "has the body drifted", and those are the only two questions a reader
  # of this line has.

  # The SHA cited is the commit that last touched the SOURCES, not the
  # commit containing the render. A render generated from the playbook
  # into the playbook cannot cite its own commit: that SHA does not
  # exist until after the commit is made. The sources SHA is knowable
  # now and answers the question a reader actually has, which is which
  # version of the preferences this was built from.
  PREFERENCE_SOURCE_PATHS="$WORKTREE_ROOT/llm_playbook/preferences"
  SOURCE_COMMIT_SHA="$(git -C "$WORKTREE_ROOT" log -1 --format=%H \
                       -- "$PREFERENCE_SOURCE_PATHS" 2>/dev/null)"
  [ -n "$SOURCE_COMMIT_SHA" ] || SOURCE_COMMIT_SHA="uncommitted"

  # Written in two steps rather than one pipeline: the hash must cover
  # the body exactly as it will sit in the output file, so the body is
  # placed first and hashed from there. Hashing the input file instead
  # would silently diverge the moment the two differ by a trailing
  # newline.
  {
    echo "$DO_NOT_EDIT_NOTICE"
    echo "STAMP PLACEHOLDER"
    cat "$COMPOSED_BODY_PATH"
  } > "$RENDER_OUTPUT_PATH.partial"

  BODY_CONTENT_HASH="$(tail -n +$BODY_STARTS_AT_LINE "$RENDER_OUTPUT_PATH.partial" \
                       | sha1sum | cut -c1-8)"
  STAMP_LINE="rendered from playbook $SOURCE_COMMIT_SHA content-hash $BODY_CONTENT_HASH"

  {
    echo "$DO_NOT_EDIT_NOTICE"
    echo "$STAMP_LINE"
    cat "$COMPOSED_BODY_PATH"
  } > "$RENDER_OUTPUT_PATH"
  rm -f "$RENDER_OUTPUT_PATH.partial"

  echo "render.sh: wrote $RENDER_OUTPUT_PATH"
  echo "render.sh: $STAMP_LINE"
  echo "render.sh: COMMIT THIS FILE. An uncommitted render cannot be verified."
  ;;

verify)
  [ $# -eq 2 ] || { echo "$USAGE" >&2; exit 2; }
  RENDER_PATH_TO_VERIFY="$2"

  [ -f "$RENDER_PATH_TO_VERIFY" ] || {
    echo "render.sh: no such render: $RENDER_PATH_TO_VERIFY" >&2; exit 1; }

  STAMPED_HASH="$(sed -n 2p "$RENDER_PATH_TO_VERIFY" \
                  | sed 's/.*content-hash //')"
  RECOMPUTED_HASH="$(tail -n +$BODY_STARTS_AT_LINE "$RENDER_PATH_TO_VERIFY" \
                     | sha1sum | cut -c1-8)"

  if [ "$STAMPED_HASH" = "$RECOMPUTED_HASH" ]; then
    echo "render.sh: stamp matches ($RECOMPUTED_HASH)"
    exit 0
  fi

  # A mismatch means the render was hand-edited after stamping, which is
  # the exact failure the hash exists to expose. It is not repaired here:
  # the fix goes to the sources and the render is regenerated, or the
  # edit was legitimate and belongs in the sources anyway.
  echo "render.sh: STAMP MISMATCH" >&2
  echo "  stamped:    $STAMPED_HASH" >&2
  echo "  recomputed: $RECOMPUTED_HASH" >&2
  echo "  the render was edited after stamping; fix the sources and re-stamp" >&2
  exit 1
  ;;

*)
  echo "$USAGE" >&2
  exit 2
  ;;
esac
