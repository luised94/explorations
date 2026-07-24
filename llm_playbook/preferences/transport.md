TRANSPORT
=========
date: 2026-07
version: 0.1.0
scope: how a chosen file set reaches a chat thread. Transport moves
CONTENT; it is firewalled from the preferences overlay, which moves
private PREFERENCES (layers.md, ADR-008). Neither references the
other's mechanism. Composition of base-plus-overlay at pack time is
a SEPARATE later increment (ADR-022 staging); this document and the
current pack-repo.sh cover archive-or-paste only.

PRINCIPLE
  Transport gets content INTO a chat. It does NOT materialize a
  second on-disk copy of the repository: one thread runs at a time,
  so a second working tree is worthless (ADR-021, superseding the
  sparse-checkout bootstrap of ADR-004). Three invariants hold for
  every mode:
    scratch-only    the pack step writes ONLY under /tmp, NEVER into
                    the git tree; it produces nothing the repo keeps.
    committed-read  the pack step reads ONLY committed content (it
                    sees HEAD). A render must therefore be COMMITTED
                    before it is packed; packing an uncommitted file
                    is caught with a clear error, not silently
                    omitted. Committed-only reading keeps the
                    recorded SHA honest.
    idempotent      same SHA and same file set produce byte-identical
                    output; the pack never appends or mutates in
                    place, it regenerates from source every run.
  The recorded SHA is ground truth: the pack is OF that SHA, echoed
  at pack time, not a note attached after the fact (AF6).

THE PACKER: scripts/pack-repo.sh
  Usage: pack-repo.sh [-p] [-e] [-o OUTDIR] PATH [PATH ...]
  Selective packing is first-class: PATH... is any subset of the
  tree a thread needs, not the whole repo.
  Archive mode (default): git archive --format=tar.gz of the set at
    HEAD, written to /tmp/pack-<sha8>.tar.gz; the full SHA is echoed.
    The consumer unpacks the tarball into a scratch dir on the model
    side. Extracted files carry no .git (a git archive strips
    history), which is why MODE A delivery is apply-and-commit-
    locally, not git-am (ADR-023).
  Paste mode (-p): the same set concatenated into one text block at
    /tmp/pack-<sha8>.txt, each file fenced with BEGIN/END markers and
    the pack SHA in a header. With -e the block opens in $EDITOR
    (default nvim) for the author to copy out; without -e the path is
    printed. The author pastes the block into a plain chat.
  -o OUTDIR overrides the scratch dir but MUST stay under /tmp; any
    other location is refused (scratch-only is enforced, not just
    documented).

THE THREE TRANSPORT SITUATIONS (W6)
  A consumer project lives in one of three places; each has one
  concrete recipe. In all three the packer is the same; only where
  it runs and how the artifact travels differ.

  1. INSIDE THE PARENT REPO (the common v0.x case; the toolkit and
     the project share one tree).
       cd <parent-repo>
       git rev-parse HEAD            # record; this is ground truth
       scripts/pack-repo.sh llm_playbook <project>/llm/CONTEXT.md
     Upload the tarball (archive) or paste the block (-p). Pack a
     SUBSET: the toolkit files the role needs plus the project's
     committed render, not the whole monorepo.

  2. OWN GITHUB REPO (the project has been promoted to its own
     online remote).
       git clone <url> && cd <repo>   # or pull the existing clone
       git rev-parse HEAD
       scripts/pack-repo.sh <paths...>
     Same packer; the tarball is the transport artifact. A model
     with repository access (Tier A) can instead be pointed at the
     paths directly and skip packing.

  3. PRIVATE LOCAL REPO, NO ONLINE REMOTE (content must be extracted
     to reach a chat at all).
       cd <local-repo>
       git rev-parse HEAD
       scripts/pack-repo.sh -p <paths...>    # paste block for a
                                             # plain chat (Tier C)
     Archive mode also works when the chat accepts a file upload;
     paste mode is the fallback when only text can cross the gap.

WHEN A CHECKOUT IS STILL THE RIGHT TOOL
  This document covers getting content INTO A CHAT, and for that the
  packer is PRIMARY: most work is read-and-reason, and a second
  working tree buys nothing (ADR-021). That is the common case and
  the default.
  It is not the only case. A thread that must RUN something -- a test
  suite, a build, a migration -- needs a real working tree, which the
  packer cannot supply: it is scratch-only and committed-read by
  design and produces no tree at all. For that, clone or check out
  normally.
  ADR-021 retired sparse-checkout as a CONTEXT-DELIVERY mechanism. It
  did not retire checkouts. Read the decision narrowly: the claim is
  that copying a tree to READ it is waste, not that trees are
  obsolete.
  A verification workflow is the standard example: pin an exact
  40-char SHA, confirm the branch, establish a green baseline BEFORE
  changing anything, and stop if the count does not match. Only the
  first step resembles transport; the rest is why a tree exists.
  Rule of thumb: READING is a pack; EXECUTING is a checkout.

GOTCHAS
  - Pack a render and it is missing: it was not committed. The
    packer reads HEAD, so commit CONTEXT.md first (committed-read).
    The error names the offending path.
  - The tarball has no history. Do not try to git am a patch built
    from it; deliver file content plus apply-and-commit-locally
    (ADR-023).
  - A stale SHA in a kickoff means the pack lags the repo. The
    render stamp (render.md) is the cross-check the reader states at
    thread start.
