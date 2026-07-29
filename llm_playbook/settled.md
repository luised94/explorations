SETTLED
=======
date: 2026-07
scope: closed questions and roads not taken. Rules carry their own
  reasoning inline, so this file holds only what no rule can carry:
  the alternatives that were rejected, and the things deliberately
  NOT done. An absence cannot have a why-clause attached to it.

  Reopening one of these is fine. Doing it without reading the entry
  is what this file exists to prevent.


SETTLED, WITH THE ROAD NOT TAKEN

  Prompts are standalone and duplicate framing on purpose.
    Rejected: "point at the protocol instead of restating it." A
    stateless chat cannot resolve an include. Duplication is the
    price of a prompt that works when pasted alone.

  A prompt is a method and never an authority.
    Where one appears to contradict a rule, the rule wins and the
    conflict is a finding. Each prompt names the rules binding at its
    phase (BINDS HERE), which is retrieval-by-workflow-stage without
    a new hierarchy.

  find-the-isomorph and survey-the-space are SEPARATE prompts.
    They were briefly merged, on the argument that abstraction
    generates the search targets and the two are one phase. Split
    again on use: the isomorph pass is a thinking tool and a response
    anchor that surfaces latent knowledge, and it frequently does not
    lead to search at all. Merging made retrieval look mandatory.

  ADR-022 is SUPERSEDED: composition does NOT happen at pack time.
    It decided that the pack step assembles base plus project overlay
    and emits a composed result, so the reader receives resolved
    preferences. This session decided the opposite before knowing
    ADR-022 existed, and the decision stands on its own reasoning: a
    render must be COMMITTED for its stamp to be verifiable, and a
    render composed during a pack is ephemeral, so nothing could ever
    detect that it had drifted. Noted because a reader finding ADR-022
    in git should see it was overruled, not overlooked. It was also
    never implemented -- it was staged as a second increment that
    never came.

  Rendering and packing are separate, in that order.
    A render is a COMMITTED artifact; a stamp can only be compared
    against something on disk. Rejected: making the render a stage of
    packing, which would produce an ephemeral render that nothing
    could later detect had drifted. render.sh automates the stamp
    only -- composition is precedence judgment and stays manual.

  Stale-render detection lives in the reading model, not in a script.
    The model recomputes the content hash at kickoff, which is the
    first thing it does. Rejected: a check inside pack-repo.sh, whose
    entire value is that it has not been modified.

  A project carries deltas, never a copy of the playbook.
    Instance rules append to or supersede a section. Rejected:
    duplicating files into each project, because both copies then
    look authoritative and the drift between them is silent.

  Every kickoff records both SHAs, separately, labelled.
    Even while playbook and project are one repository. Worktrees and
    a shared playbook are the expected direction, and a single
    unlabelled SHA becomes unrecoverable the moment that happens.

  Delivery form follows BASELINE FIDELITY, not operation type (R12).
    Rejected the older rule that keyed on the operation -- new file,
    edit, move, delete -- because git apply handles all four and the
    distinction was never the real one. What decides it is whether
    the exact bytes are held: tar pack at a known SHA gives patches,
    a paste gives whole files.

  The author is the committer.
    The model proposes; the human applies, reviews and commits
    against real HEAD. Rejected: shipping .git so patches apply
    directly.

  Reading is a pack; executing is a checkout.
    Rejected: sparse-clone bootstrap as the way to get context into a
    chat. It survives only where a thread must actually RUN
    something, and packing is the more consistent discipline because
    it forces a deliberate choice of what travels.

  Thread ids carry a descriptive segment: PROJ-ROLE-NNN_descriptive.
    Because the id is pasted into the chat title and has to be
    readable there. One split on "_" still recovers the id.

  Filenames are dateless, with one exception: a record OF a dated
  event.
    RESET-2026-07.md carries its date because the date is its
    subject. The rule exists because names describing a position in a
    process go stale; a historical record cannot.

  Rules were renumbered R1-R12 at the reset, and again when the
  absence rule landed.
    Safe because git holds the old numbers and every citing document
    was rewritten in the same pass. The second renumbering DID break
    the BINDS HERE headers, which cited pre-merge numbers for one
    turn. Recorded because it is the exact failure that blind
    substitution causes and it happened anyway.


DELIBERATELY NOT DONE

  check.sh -- retired.
    An uninstalled pre-commit hook that nobody ran. Its two FAIL
    checks were real; its five WARN thresholds were hand-set, never
    measured, and warned to nobody. Their numbers had become
    load-bearing in prose: a ruler nobody held was generating
    arguments.

  MANIFEST, load classes, required-read lists and token budgets --
  retired.
    They existed to manage context and consumed more than they saved.
    With seventeen files a reader can see all of them. The budgets
    were set 87 percent below the figure they were later measured
    against.

  The ADR record -- retired.
    Thirty-six decisions with recorded alternatives, 11,000 tokens.
    What survives is above, one line each. Git holds the rest.

  Terminal-state taxonomy, status vocabulary, supersedes fields,
  append-only records, stable-forever ids, bulk-rename prohibitions
  -- retired.
    All of it duplicated git, badly. See README, RECOVERING WITH GIT.

  Sunset dates and periodic review -- rejected.
    Calendar-driven mechanisms need discipline nobody sustains, and
    the reviewer is the person who wrote the thing. The three
    accretion rules act at write time instead.

  More authority tiers -- rejected.
    Two (the render, and everything else) are enough. A third is
    where overengineering starts.

  An index, taxonomy or tag system for retrieval -- rejected.
    That was MANIFEST and it failed. Retrieval is by workflow stage
    instead, via the BINDS HERE headers.

  A worked example of a close artifact, a design, or a decision --
  rejected.
    protocol.md exemplifies FORMS only. Anchoring on a form aids
    consistency; anchoring on someone else's reasoning replaces your
    own, which is the more expensive failure.


DECLARED ASSUMPTIONS

  ONE THREAD AT A TIME. Recovered from ADR-016, and undeclared in the
  first reset pass. Three mechanisms here depend on it and fail
  TOGETHER if it stops holding:
    - a hot fix reaches an open thread through the live human channel
      only, because there is no other channel;
    - the render hash is checked at KICKOFF only, because nothing can
      change the render mid-thread;
    - no push-freeze convention is needed.
  Worktrees, or the playbook shared with projects outside one tree,
  are the stated near-term direction and are exactly what breaks this.
  Revisit the three as a SET, never one at a time.

  PROMOTION OUT OF THE MONOREPO IS NOW UNGUARDED. Recovered from
  ADR-002: the playbook lives inside the parent monorepo and
  promotion to a standalone repository was kept cheap by check.sh's
  containment checks -- no upward path references, no parent-repo name
  in prose. check.sh is retired, so nothing enforces that any more and
  an upward reference will fail silently until promotion day. Accepted
  deliberately: the check was never installed and never ran. If
  promotion becomes real, the check is one grep, not a script.


OPEN, AND KNOWN TO BE

  The twelve-rule cap is a guess.
    Its value is that it forces a comparison, not that twelve is
    correct. Revise once there is a real project's worth of evidence,
    and record the measurement rather than a new guess.

  protocol.md was targeted at 150 lines and is longer.
    The 150 was a guess of the same kind as the retired budgets and
    is not being defended. The overage is the templates, which are
    the part that gets used.

  refinements.md is the one file under no size discipline.
    Everything else here fights growth; that file's growth IS the
    mechanism, because a finding must be able to wait somewhere for
    its second occurrence. Rejected: folding it into settled.md, which
    holds CLOSED questions -- an unpromoted refinement is open.

  Nothing here has been validated on a project that is not this one.
    That is the next thread's job and the only thing that will tell
    us which of these rules are real.
