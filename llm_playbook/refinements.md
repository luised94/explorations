REFINEMENTS
===========
date: 2026-07
type: refinements
scope: observed failures of a model working in this repository, each
  with the fix that resolved it. An accreting log, not a rule set.
  Nothing here binds until it is promoted.

  THIS FILE IS THE INTAKE FOR ACCRETION RULE ONE (README). A finding
  becomes a rule when it has cost something TWICE in a real project.
  This is where the first occurrence waits. Without it a finding
  either becomes a rule immediately, which is accretion, or is lost.

  It is therefore expected to grow, and it is the ONE file here under
  no size discipline. Growth is the signal working.


HOW THIS WORKS
  An entry is written when a model FAILS at something and the failure
  is diagnosable -- not when it merely does something suboptimal.
  Each entry records the observation, the fix, and whether it has
  been promoted. Promotion is a human editorial decision, never
  automatic.

  A second occurrence of an existing entry is recorded ON that entry,
  because the count is what licenses promotion.

  Promotion into protocol.md is subject to the twelve-rule cap and
  must name what it replaces. Promotion into preferences/ is not
  capped, and is the usual destination.

  Ids are RF-PLAYBOOK-NNN and are never reused. Ids may be renumbered
  freely elsewhere in this playbook because git holds the old numbers
  (README, RECOVERING WITH GIT), but not here: an entry id is cited
  from close artifacts that git will not rewrite.


RF-PLAYBOOK-001  patches must be generated from a real file pair
  OBSERVED  Hand-authored @@ headers and line counts drift from the
    real body, and git apply rejects the result.
  FIX  Copy the target file, edit the copy, run diff -u between the
    two. Never hand-author hunk headers, line counts, or offsets.
  PROMOTED  not yet. Mechanism for R12; R12 states WHICH form, not
    how to produce it correctly.

RF-PLAYBOOK-002  a patch is unverified until it has been applied
  OBSERVED  A patch that looks correct is not evidence that it applies.
  FIX  Round-trip it: apply to a fresh copy of the original, confirm
    it reproduces the intended file byte for byte, before sending.
    git apply --check on a clean copy is the cheapest form and needs
    no commit identity at all.
  PROMOTED  not yet.

RF-PLAYBOOK-003  prefer plain git apply; --recount is a fallback
  OBSERVED  --recount silently absorbs real context drift, so a patch
    that should have been rejected lands wrong.
  FIX  Use plain git apply as the standard mechanism. Keep --recount
    as a manual fallback, never the default.
  PROMOTED  not yet.

RF-PLAYBOOK-004  editing without git present
  OBSERVED  A git archive export has no .git, so there is no way to
    generate offsets from the repository.
  FIX  diff -u two real copies to get correct offsets rather than
    estimating them, or deliver the complete updated file and let the
    author's real repository produce the patch.
  PROMOTED  yes, in substance. R12 makes baseline fidelity the
    discriminator, which is the general form of this entry. Kept
    because the mechanism is still needed.
  SECOND OCCURRENCE 2026-07: an eight-commit drill consolidation was
    delivered as "git checkout e3aabfb; git am patches/*.patch".
    e3aabfb is a SANDBOX commit; git rev-parse on it in the author's
    repository returns "Invalid revision range". The patches were
    byte-verified in the sandbox and were undeliverable. The fallback
    document, ten replacement files and the reasoning behind one
    reversed decision were pasted into the chat and lost with it.
    NOTE WHAT THIS SECOND OCCURRENCE MEANS. The usual reading of a
    second occurrence is "promote it", and this entry was ALREADY
    promoted, into R12. So the promotion is not the fix and R12 is
    not where the hole is: R12 says which FORM to deliver and says
    nothing about which baseline a form may cite. The missing rule is
    narrower -- never cite a SHA the author's repository does not
    contain -- and its home is the kickoff template's delivery
    paragraph, where the sender states the baseline, rather than a
    thirteenth rule.

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
    delivered scripts; this extends it to throwaway verification work,
    where it was being forgotten.

RF-PLAYBOOK-007  destructive git commands against uncommitted work
  OBSERVED  git reset --hard was run to undo a dry run while an
    unrelated file rewrite sat uncommitted in the same tree. The
    rewrite was destroyed. It was recoverable only because it had been
    written through a scratch copy first, which was luck rather than
    method.
  FIX  Commit or stash before any reset --hard, clean -fd, or rm -rf
    of a tracked directory, or run the dry run in a separate clone. A
    dry run that can destroy real work is not a dry run.
  PROMOTED  not yet. SECOND OCCURRENCE 2026-07: the reset delivery
    handed the author `rm -rf llm_playbook` with no preceding commit
    or stash check. Nothing was lost, but the command was the same
    shape. This entry has now cost twice and is a promotion candidate.

RF-PLAYBOOK-008  a partial edit script that still gets committed
  OBSERVED  A script applied three replacements in sequence, asserting
    each anchor immediately before its own write. The second anchor
    was wrong -- a comma in the source text the anchor omitted -- so
    the script died after the first write, leaving the file
    half-edited. The commit command was on the next line rather than
    chained with &&, so it ran regardless, and a commit landed whose
    message described nine items when two were present.
  FIX  Assert EVERY anchor before performing ANY write, so a bad
    anchor fails before the file is touched. Chain a commit to the
    script's exit status, never merely place it afterwards. And check
    that what landed matches what the message claims before moving on.
  PROMOTED  not yet. CONSTRAINT-014 covers the principle; this is the
    mechanism. SECOND OCCURRENCE 2026-07: the reset's BINDS HERE
    correction pass asserted each file's anchor immediately before
    that file's own write rather than asserting all of them first. No
    file was left half-edited because each was independent, so the
    blast radius was smaller, but the shape was identical. Promotion
    candidate.

RF-PLAYBOOK-009  a GENERATED file must never be delivered as a patch
  OBSERVED  A render was shipped as a git patch with a placeholder in
    its stamp, to be filled by one command after applying, because the
    source sha differs between sandbox and real repository. The fill
    worked. But the next change to that file could no longer be
    delivered: the committed content had diverged by one line, so the
    follow-up patch failed, and failed again under three-way merge
    with a conflict in the stamp.
  FIX  Deliver a generated file as its BODY plus the generation
    command, never as a diff. A diff assumes both sides share a base;
    a generated file's base is its SOURCES, not its previous text, and
    the two sides can legitimately differ in provenance lines while
    being equally correct.
  PROMOTED  YES, 2026-07, into R12. It was nearly lost in the reset:
    R12 was written to send everything through a patch after a tar
    pack, which is exactly the failure above, and the hole was found
    only when this file was read before deletion. Kept as the record
    of why R12 carries an exception that otherwise looks arbitrary.

RF-PLAYBOOK-010  a name copied from a neighbor instead of from a rule
  OBSERVED  The drill project's handoff directory accreted four
    coexisting filename shapes -- 1-to-implementation.md,
    handoff-2-to-implementation.md, handoff-D1-to-arithmetic.md,
    launch-2-ui-selector.md -- because each new file imitated
    whichever neighbor its author saw last. Imitation compounds
    drift; a rule does not.
  FIX  A name is conformant because it follows a rule written in
    protocol.md IDENTITY AND NAMING, not because it resembles a
    neighbor. A file the naming section cannot classify is a finding,
    not an exception.
  PROMOTED  not yet. ONE occurrence, and it is the pre-reset naming.md
    N4 rule arriving without its document. Under accretion rule ONE it
    waits here for a second.

RF-PLAYBOOK-011  pasting a committed document into a thread
  OBSERVED  Committed files are pasted into a chat that could have
    cited them by path, which spends context on material the thread
    could already reach and makes it unclear whether the paste or the
    repository is current.
  FIX  Do not paste a committed document. Where it must be pasted --
    it is unpushed, or the reader has no checkout -- say that it is
    unpushed, so the reader knows the repository does not hold it.
  PROMOTED  not yet. ONE occurrence. Residue of drill's F-18; the
    other F-18 item (never improve a shipped policy by taste instead
    of by a metric named in advance) has no recorded occurrence in
    this repository at all and is not entered here, because this file
    takes OBSERVED failures and an entry with no observation would be
    a rule wearing a refinement's clothes.
