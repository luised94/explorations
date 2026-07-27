THREAD PROTOCOL
===============
date: 2026-07
type: toolkit-rules
scope: the numbered rules governing a thread's identity, its role, its
  drift repair, and its terminal states. Rules are cited by number from
  naming.md and kickoff.md, so the numbering is fixed and a rule is
  never renumbered to close a gap.
status: current

INCOMPLETE, AND DELIBERATELY SO
  R1 through R10 are NOT here. The implementation plan specifies them
  as "generalized from the drill original", and that original --
  drill/llm/llm-thread-protocol.md -- is not available to the thread
  that wrote this file. The accept criterion for this document
  requires every rule to cite an origin failure or be marked
  SPECULATIVE, and neither is possible for a rule that has not been
  read. Ten invented rules under authoritative numbers would be worse
  than a stated gap.

  What this file does now: it makes R11, R12 and R13 exist, because
  naming.md and kickoff.md already cite R12 and R13 by number and were
  pointing at a file that did not exist at all. R1-R10 land when drill
  is in scope, at their reserved numbers, with no renumbering of
  anything below.

ROLES
  A thread plays exactly one role: DESIGN, IMPL, or CAPTURE
  (naming.md, README role routing; CONSTRAINT-011).
  OPEN: the drill original uses DESIGN/IMPL/REVIEW. Whether REVIEW is
  a fourth role or CAPTURE under an older name is a real decision and
  is not settled here, because settling it requires reading the
  document that names it. Do not assume either answer.

R11 -- DRIFT REPAIR AT STOP
  At a STOP, drift between what the plan says and what the repository
  contains is repaired before work continues, not noted and worked
  around. A plan that has stopped describing the tree is not a plan.
  ORIGIN: recorded in the implementation plan at T-009 as a rule of
  its own; the failure it generalizes is not restated there, so treat
  the rationale above as SPECULATIVE and confirm it when R1-R10 land.

R12 -- TERMINAL STATES, OF WHICH THERE ARE FOUR
  Every thread ends in exactly one of these, and every one of them is
  POSITIVELY RECORDED as a state line in the project's STATUS.md.
  Absence is never a signal: a thread that has stopped appearing is
  not thereby parked or abandoned, it is unrecorded, which is the
  condition this rule exists to remove.

  landed     implementation merged. Close artifact MANDATORY.
  bounced    rejected at review. Close artifact MANDATORY.
  parked     a design or idea thread that produced artifacts but never
             reached an implementation commitment. Its EXISTING design
             artifacts ARE its close artifact; the only ritual is
             flipping the state line in STATUS.md. Promotable to a
             full close artifact if the thread is revived.
  abandoned  died mid-implementation. Close artifact MANDATORY.

  ORIGIN: review findings AF8 and W5. W5 records that
  mid-implementation abandonment is rare and that the thread which
  dies is almost always a design thread that never reached a
  commitment -- which is why parked exists as a state rather than
  being folded into abandoned, and why it is the only state whose
  close artifact is satisfied by what the thread already produced.

R13 -- THREAD IDENTITY
  A thread declares its id in the FIRST message of the conversation.
  The conversation is ephemeral. Its only durable trace is the close
  artifact, or -- for a parked thread -- its design artifacts plus the
  STATUS line.
  ORIGIN: SPECULATIVE as stated here. The rule's content is fixed by
  T-009 and cited by naming.md and kickoff.md; the originating failure
  is not recorded in either, and is expected to arrive with R1-R10.
