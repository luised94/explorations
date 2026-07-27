HANDOFF -- PLAYBOOK-DESIGN-004 to IMPL
======================================
date: 2026-07
type: handoff
from: PLAYBOOK-DESIGN-004
to:   IMPL
role: IMPL
scope: the G-1 render-effect re-test. The receiving thread executes it
  and may NOT redesign the protocol. The sending thread closed the
  protocol gap behind G-1a and G-1b.
status: current

WHY A TWO-THREAD TEST, NOT A SELF-CHECK
  The thread that does drill
  work under the render must NOT know it is a render test, or it will
  perform binding and prove nothing. The thread that EVALUATES must not
  be the thread that authored the render or read this conversation, or
  it grades its own priors. Three roles, kept apart: the AUTHORING
  thread (DESIGN-004, done), the SUBJECT thread (ordinary drill IMPL,
  told nothing), the EVALUATOR thread (fresh, sees only the transcript
  and the pack manifest).

READ FIRST
  - decisions/era-2026-q3.md ADR-030 and ADR-034 -- WHY a kickoff must
    name the render, and WHY the test pack is scoped. The rest of the
    protocol change is context; these two are the test's logic.
  - the close artifact of this thread, for what is already sound and
    must not be reopened.

STATE
  G-1a passed on transport (bytes arrive) and FAILED on effect (the
  render was not read; a competing document was followed instead). The
  protocol gap that allowed this is now closed: the competing document
  is deleted, its rules split into the render and drill/llm/PROJECT.md,
  and kickoffs now name the render and state it binds. G-1 is OPEN
  until a subject thread, given a scoped pack and an ordinary kickoff,
  is shown to have been bound by the render. T-008+ stays shut behind
  G-1.

WORK, IN DEPENDENCY ORDER
  1. BUILD THE SCOPED PACK (ADR-034). Pack drill code + exactly three
     doc sources: CONTEXT.md, PROJECT.md, STATUS.md. No other
     rule-bearing document. Record the manifest (the exact path list)
     -- the evaluator needs it to confirm no other rule source was
     present.
  2. WRITE AN ORDINARY KICKOFF for real drill implementation work,
     using protocol/kickoff.md. It NAMES the render and states it
     binds (that is the protocol now, not a test tell). It does NOT say
     "this is a render test." Pick real, small drill work that a render
     rule would visibly shape.
  3. RUN THE SUBJECT THREAD cold on that pack + kickoff. Let it work.
     Do not coach. Capture the full transcript.
  4. ASK THE DIAGNOSTIC, once, at the end, in the subject thread:
     "What in your context told you to do it this way? Quote it."
     This is causal, not stylistic -- see the pass criterion.
  5. EVALUATE in a FRESH thread that has not seen DESIGN-004's work.
     Give it the transcript and the pack manifest. It decides pass/fail
     against the criterion below.

THE PASS CRITERION (this is the whole point; get it exactly right)
  PASS requires the subject thread to quote, as its source, EITHER the
  render's stamp line OR a rule that lives ONLY in the render or
  PROJECT.md and nowhere else in the packed code. Because the pack is
  scoped (ADR-034), such a rule cannot have come from anywhere else, so
  a correct quote is proof the render bound.
  NOT a pass: code that happens to match the render's style. G-1b
  already showed six of seven style checks passing while the render
  went unread -- the rules leaked from the deleted competitor and from
  surrounding code. Matching style is consistent with never opening the
  render. Only a sourced quote of a render-only rule distinguishes
  "bound by the render" from "agreed with it by chance."
  Pick the subject task in step 2 so that at least one render-only or
  PROJECT.md-only rule is load-bearing for it -- otherwise the subject
  can succeed without ever needing the render, and the test is inert.

WHAT NOT TO DO
  - Do not tell the subject thread it is being tested. The tell
    invalidates the result.
  - Do not evaluate in the subject thread, or in any thread that read
    DESIGN-004's transcript. Self-grading is the failure mode this
    two-thread structure exists to prevent.
  - Do not add the other 49 drill docs "for realism." That is the
    exact confound ADR-034 removes; realism here means an unreadable
    result.
  - Do not reopen T-005..T-007b. Render CONTENT was fine; DELIVERY
    EFFECT was the defect. Do not open T-008+ until G-1 closes.
  - Do not treat a style-check pass as a gate pass. Re-read the pass
    criterion.

WHAT IS SOUND AND SHOULD NOT BE REDONE
  The render content (T-005..T-007b), transport (bytes arrive), the
  packer (scoped packing works via path selection, ADR-034), the
  three-way split of the old conventions file, and the promoted
  prompts. None of these is under test. Only DELIVERY EFFECT is.

OPEN ITEMS
  O1 (persona layer) is parked in drill/llm/refinements.md, blocked on
     the user supplying identity facts; it does not block G-1.
  O2 (check.sh false positive on quoted upward-path patterns) is
     unaddressed and does not block G-1; note it for a later thread.
  The drill/llm 49-doc sprawl is out of scope for G-1 and has its own
     handoff (handoff/DRILL-DESIGN-consolidation, self-contained).
