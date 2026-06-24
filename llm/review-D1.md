# Review: D1 (questions.metadata) -- reflective record

Backward-looking and honest, for study and metacognitive reflection -- NOT a
rulebook. The actionable distillations live in llm/handoff-D1-to-arithmetic.md
and llm/prompts/. This document is the "why it actually went this way," the
friction, and the judgment calls that resist proceduralizing.

================================================================================
WHAT D1 WAS REALLY ABOUT
================================================================================
The nominal goal was "add the first real migration." The nominal goal was the
LEAST interesting thing that happened. The real value:

  - Exercising the migration runner end-to-end immediately exposed a LATENT
    DEFECT (init_db stamped the moving SCHEMA_VERSION, not a fixed baseline)
    that would have shipped broken to every fresh install -- invisible to
    static review, surfaced only when a test read a migration-added column off
    a freshly-initialized DB. This is EXACTLY the rationale the forward-rec gave
    for sequencing D1 first: "if the mechanism is awkward in practice, we learn
    it now, cheaply, on the very next thread." It paid off literally. Lesson:
    the value of a "first consumer" thread is often the bug it flushes out, not
    the feature it adds. Budget for that; do not treat the discovered bug as a
    distraction from the "real" work -- it IS the work.

  - The biggest decision (defer grading_kind) was a decision to do LESS than the
    brief asked. The brief required two columns; we shipped one. Doing less was
    correct, and arriving there took an adversarial review plus checking for the
    supposed consumer (SM2) and finding it wanted DIFFERENT columns. Lesson:
    "the brief says to" is not sufficient justification for a costly,
    irreversible change. The cheapest version of a speculative column is the one
    not yet added.

================================================================================
THE FRICTION (the part worth studying most)
================================================================================
A large fraction of D1's turns went not to the feature but to:
  (a) discovering the init_db bug REACTIVELY (test went red) the first time,
      then mapping the temp_db blast radius PROACTIVELY the second time. The
      contrast is the lesson: the proactive pass (grep all consumers, map, fix
      once) was dramatically cheaper than whack-a-mole. The habit now lives in
      the commit-planning prompt's "predict downstream" step -- but note it had
      to be LEARNED mid-thread, not applied from the start.
  (b) the patch-transmission problem. Claude's sandbox repo and the user's repo
      are separate; for most of D1 the user hand-copied files, which broke on
      the large decisions.md append. The fix (git diff -> git apply) was only
      discovered near the end. Real cost in turns and in risk of local/sandbox
      drift. Lesson: establish the TRANSPORT mechanism before the work, not
      after. A process gap compounds across every commit.
  (c) Claude not committing in its own sandbox, so every patch defaulted to
      "everything since the start" -- which is why the first cumulative patch
      failed to apply against the user's partially-advanced repo. Mapping the
      apply-failure (5 files "already applied," 2 files genuinely missing) was
      itself the diagnostic that revealed the true gap. Lesson: granular commits
      on BOTH sides keep the diff math honest.

Meta-lesson across (a)-(c): the technical work was sound; the COORDINATION
overhead was where the cost hid. For a multi-thread project, the workflow
contract is not bureaucracy -- it is the thing that prevents silent divergence.

================================================================================
JUDGMENT CALLS (recorded as reasoning, not rules)
================================================================================
  - SCOPE GREW, and that was right but worth scrutiny. The init_db fix and the
    temp_db/current_db split were NOT in the topo plan. Each was necessary for
    D1 to be correct. But the honest question for next time: should the plan
    have ANTICIPATED "the first SCHEMA_VERSION bump will test every assumption
    that conflated baseline-with-current"? Probably yes. A pre-mortem ("what
    does the first bump break?") would have predicted the init_db stamp and the
    temp_db meaning-split before runtime did. Consider a lightweight pre-mortem
    when changing a value that was previously constant.

  - THE ADVERSARIAL REVIEW MOSTLY CONFIRMED. Only 2 of 6 lenses (REAL-vs-
    SPECULATIVE, USAGE-BEFORE-INTERFACE) overturned anything; the rest agreed.
    That is not a failure of the technique -- it is the expected hit rate. The
    technique earns its cost on the rare flip, so the discipline is to keep the
    BAR high (run it only when one objection could change the plan), not to run
    it everywhere hoping for value.

  - PERSONAS vs LENSES. The six named reviewers were useful SCAFFOLDING for
    generating diverse objections, but they are a liability if treated as a
    checklist to fill in. The prompts deliberately demote the names and keep the
    AXES. Watch yourself (and Claude) for cargo-culting the personas.

  - "UPHOLD, DON'T OVERRIDE." Framing the init_db fix as upholding ADR-022
    (which already said "init_db stamps version 1") rather than a new contrary
    decision kept the decision log coherent. The code had silently DRIFTED from
    its own documented decision; D1 just exposed it. This framing matters for a
    project whose decisions.md is meant to be a teaching artifact -- a log full
    of apparent contradictions teaches confusion.

================================================================================
THINGS LEFT UNDONE / DEFERRED (so future-you is not surprised)
================================================================================
  - grading_kind: deferred to #7/Phase 4 with a real trigger (ADR-025). Not
    forgotten -- parked with flags in code and roadmap.
  - General magic-number-to-constant audit: only BASELINE_SCHEMA_VERSION was
    extracted (the one the bug forced). A broader pass over version literals and
    other in-code constants remains a deferred cleanup (fits #20, docstring/ADR
    cleanup). Do it when touching those headers anyway.
  - The D1 handoff PROCEDURE in decisions.md had a wrong worked example
    (banks.metadata_extra) and omitted the init_db baseline interaction. Noted
    in the D1 verdict; the procedure prose itself was not rewritten -- a small
    future edit for D2+.

================================================================================
QUESTIONS TO SIT WITH (metacognitive)
================================================================================
  - When does "the brief says so" deserve to be overridden, and how do you tell
    correction from scope-creep in the moment rather than in hindsight?
  - The proactive-vs-reactive blast-radius lesson cost real turns to learn.
    What is the cue that should trigger "map all consumers first"? (Proposed:
    any edit to something previously CONSTANT or WIDELY SHARED. Test that cue on
    the arithmetic chain.)
  - How much process is worth it? D1 suggests: for a SINGLE change, little; for
    a MULTI-THREAD project with a separate-repo transport problem, the contract
    paid for itself. Calibrate, do not maximize.
