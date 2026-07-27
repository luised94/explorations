REFINEMENTS -- llm_playbook
===========================
date: 2026-07
type: refinements
scope: observed failures of a model working in this repository, each
  with the fix that resolved it. An accreting log, not a rule set: an
  entry earns promotion into layers.md or style-contract.md by an
  editorial pass, and until then it binds nothing.
status: current

HOW THIS WORKS
  An entry is written when a model FAILS at something and the failure
  is diagnosable -- not when it merely does something suboptimal. Each
  entry records the observation, the fix, and whether it has been
  promoted. Promotion is a human editorial decision, never automatic,
  because a preference layer is a fixed set of self-contained items
  (layers.md L1, L2) and this file is neither fixed nor self-contained.

  Ids are RF-PLAYBOOK-NNN and are never reused (naming.md).

------------------------------------------------------------------------

RF-PLAYBOOK-001  patches must be generated from a real file pair
  OBSERVED  Hand-authored @@ headers and line counts drift from the
    real body, and git apply rejects the result.
  FIX  Copy the target file, edit the copy, run diff -u between the
    two. Never hand-author hunk headers, line counts, or offsets.
  PROMOTED  not yet.

RF-PLAYBOOK-002  a patch is unverified until it has been applied
  OBSERVED  A patch that looks correct is not evidence that it applies.
  FIX  Round-trip it: apply to a fresh copy of the original, confirm it
    reproduces the intended file byte for byte, before sending.
    git apply --check on a clean copy is the cheapest form and needs no
    commit identity at all.
  PROMOTED  not yet.

RF-PLAYBOOK-003  prefer plain git apply; --recount is a fallback
  OBSERVED  --recount silently absorbs real context drift, so a patch
    that should have been rejected lands wrong.
  FIX  Use plain git apply as the standard mechanism. Keep --recount as
    a manual fallback, never the default.
  PROMOTED  not yet.

RF-PLAYBOOK-004  editing without git present
  OBSERVED  A git archive export has no .git, so there is no way to
    generate offsets from the repository.
  FIX  diff -u two real copies to get correct offsets rather than
    estimating them, or deliver the complete updated file and let the
    author's real repository produce the patch.
  PROMOTED  not yet. Interacts with the delivery clauses; see the
    delivery-form entry below.

RF-PLAYBOOK-005  a throwaway repository has no commit identity
  OBSERVED  A fresh git init has no user.email or user.name, and the
    first git commit aborts.
  FIX  Set both in the same command chain as git init, before any
    commit is attempted.
  PROMOTED  not yet.

RF-PLAYBOOK-006  the sandbox shell is dash, not bash
  OBSERVED  Process substitution and other bashisms fail; the shell is
    /bin/sh.
  FIX  POSIX sh constructs only. No <(...).
  PROMOTED  not yet. style-contract.md already requires POSIX sh for
    delivered scripts; this extends the same constraint to throwaway
    verification work, where it was being forgotten.

RF-PLAYBOOK-008  a partial edit script that still gets committed
  OBSERVED  A script applied three replacements in sequence, asserting
    each anchor immediately before its own write. The second anchor was
    wrong -- a comma in the source text the anchor omitted -- so the
    script died after the first write, leaving the file half-edited.
    The commit command was on the next line rather than chained with
    &&, so it ran regardless, and a commit landed whose message
    described nine items when two were present.
  FIX  Assert EVERY anchor before performing ANY write, so a bad
    anchor fails before the file is touched. Chain a commit to the
    script's exit status, never merely place it afterwards. And check
    that what landed matches what the message claims before moving on.
  PROMOTED  not yet. The verify-by-executing item (CONSTRAINT-014)
    covers the general principle; this is the specific mechanism.

RF-PLAYBOOK-007  destructive git commands against uncommitted work
  OBSERVED  git reset --hard was run to undo a dry run while an
    unrelated file rewrite sat uncommitted in the same tree. The
    rewrite was destroyed. It was recoverable only because it had been
    written through a scratch copy first, which was luck rather than
    method.
  FIX  Commit or stash before any reset --hard or clean -fd, or run the
    dry run in a separate clone. A dry run that can destroy real work
    is not a dry run.
  PROMOTED  not yet.
