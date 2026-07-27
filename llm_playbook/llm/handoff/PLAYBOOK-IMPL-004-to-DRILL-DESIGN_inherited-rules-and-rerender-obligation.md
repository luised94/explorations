HANDOFF -- PLAYBOOK-IMPL-004 to DRILL-DESIGN
============================================
date: 2026-07
type: handoff
from: PLAYBOOK-IMPL-004
to:   DRILL-DESIGN
role: DESIGN
scope: what a drill thread inherits from the playbook consolidation --
  rule changes that reach drill, a re-render obligation, and the four
  questions drill is the only place that can answer. It does NOT carry
  drill's own consolidation plan; that is the receiving thread's to
  write.
status: current

  NOTE ON THIS FILENAME. The TO slot carries a project code,
  DRILL-DESIGN, where the grammar says it carries a bare ROLE word.
  A bare DESIGN would read as a playbook thread. naming.md's handoff
  form assumes sender and receiver share a project and has no rule for
  the cross-project case; this file uses the unambiguous form and
  records the gap in OPEN ITEMS rather than inventing a rule after the
  sending thread has closed.

WHY A DESIGN THREAD
  What drill faces is not execution of a fixed plan. It has to decide
  how the inherited rules apply to a repository with roughly fifty
  documents and its own history, decide two questions the playbook
  could not answer without it, and produce ADRs for both. An
  implementation thread would have to invent those decisions silently,
  which the deviation rule forbids.

READ FIRST
  llm_playbook/llm/close/PLAYBOOK-IMPL-004_repo-consolidation-and-
  check-rework.md -- the sending thread's close artifact. Its
  DISCREPANCIES section is the part worth your time; twelve of them,
  five self-inflicted, and at least three describe failure modes you
  will meet.
  llm_playbook/protocol/naming.md -- the grammar you are adopting.
  llm_playbook/decisions/era-2026-q3.md -- ADR-035 and ADR-036 are new;
  ADR-012, ADR-026, ADR-028 and ADR-033 are amended.
  llm_playbook/llm/plan/repo-consolidation.md -- the execution plan,
  including DEC-7 through DEC-18 and the findings behind them.

STATE
  llm_playbook is at subtree de0a6964, 32 files, check.sh clean and
  exit 0 with five non-blocking warnings (two line ceilings, three
  token budgets, all uncalibrated and all recorded).
  Its root is three files and five directories. Every thread artifact
  lives under llm/{design,plan,handoff,close}/.
  drill has not been touched by this thread and was not in the pack it
  worked from. Nothing below has been verified against drill's actual
  tree.

WORK, IN DEPENDENCY ORDER
  1. RE-RENDER. layers.md and style-contract.md both changed
     substantially: nine new layer items, five new style clauses, and
     CONSTRAINT-005 and S23 reversed in meaning. Every CONTEXT.md built
     from them, drill's included, now carries a stamp that no longer
     matches its sources. Do this first -- everything after it is work
     done under a stale render otherwise.
  2. CREATE drill/llm/refinements.md. render.md names three instance
     documents beside CONTEXT.md (STATUS.md, decisions.md,
     refinements.md) and drill has two. Migrate g1-findings.md into it
     as RF-DRILL-NNN entries; that file is then spent and its archiving
     is unconditional. This was the first finding of the whole effort
     and is still undone.
  3. ADOPT THE GRAMMAR. Frontmatter field set, three-value status,
     N6-N8 descriptive segments, the type vocabulary including
     toolkit-rules and preference-source. Expect the same surprise the
     sending thread had: the count of non-conformant frontmatter fields
     was three times its estimate.
  4. RETIRE drill/archive/. Repo-wide means drill. Superseded and
     outdated documents stay where they are and say so in status;
     genuinely removed ones are deleted, because git holds them. The
     project skeleton at implementation-plan.md T-011 still lists
     archive/README.md and was deliberately not edited -- it is status
     outdated and the ADR outranks it. Do not treat that stale line as
     permission.
  5. SCOPE CONTAINMENT if drill runs check.sh. llm/ is exempt; the
     toolkit layer is not.
  6. ANSWER THE TWO QUESTIONS ONLY DRILL CAN ANSWER, as ADRs:
     is drill's REVIEW role a fourth role or CAPTURE under an older
     name; and what does a CAPTURE thread actually do. CAPTURE is named
     in five playbook documents and defined in none.
  7. SUPPLY R1-R10. protocol/thread-protocol.md exists with R11, R12
     and R13 and an explicit hole where R1-R10 belong, because they
     were specified only as generalized from drill's
     llm-thread-protocol.md. Bring them across at their reserved
     numbers. R12 and R13 are cited by number from naming.md and
     kickoff.md and must NOT move.
  8. RECONCILE THE WORKFLOW CONTRACT. Eleven drill documents carry a
     WORKFLOW CONTRACT or DELIVERY DISCIPLINE section:
       handoffs/1-to-implementation.md
       handoffs/1b-to-execution.md
       handoffs/2-to-frontend-cutover.md
       handoffs/3-to-E10-cutover.md
       handoffs/5-to-design.md
       handoffs/5-to-implementation.md
       handoffs/handoff-D1-to-arithmetic.md
       handoffs/handoff-D2-to-implementation.md
       handoffs/handoff-modularization.md
       handoffs/launch-2-ui-selector.md
       thread-N-vocab-plan.md
     Verified divergent for the first four; the other seven are
     confirmed carriers and undiffed.
     Take the 3-to-E10-cutover version -- the most recent, and the only
     copy whose heading admits revision -- and diff it against what the
     playbook ALREADY says in commit-planning.md, clone-and-verify.md,
     runtime-verification.md and precedence.md. Only the residue
     becomes new text. If the residue is empty, the correct outcome is
     that no new playbook text is written and all eleven documents are
     released for archiving anyway. That is a success, not a failure to
     deliver.

WHAT NOT TO DO
  Do not renumber R12 or R13 to fit drill's ordering. Two live playbook
  documents cite them by number.
  Do not re-litigate DEC-1 through DEC-18 or ADR-035 and ADR-036. They
  are landed with their alternatives recorded; if one is wrong, that is
  a new ADR superseding it, not a reopening.
  Do not create archive/ anywhere, including in a new project skeleton.
  Do not author the workflow contract from drill's copies. Diff first.
  Eight of the eleven are undiffed and at least four are known to
  diverge from each other.
  Do not trim required reading to satisfy the token budgets. They are
  uncalibrated, they warn rather than gate, and all three are already
  exceeded in the playbook. Fitting correct lists to a guessed number
  is the failure this thread refused twice.
  Do not rename a file for conformance where the references are heavy
  and the file is outdated. naming.md's classification note governs:
  nonconformance of a pre-grammar artifact is recorded, not repaired.
  drill's adr-index.md is a derived artifact that drifted seven records
  before anyone noticed; delete it rather than repairing it, unless
  something now depends on it.

WHAT IS SOUND AND SHOULD NOT BE REDONE
  The frontmatter-carries-classification decision and the field set
  built on it. Four documents disagreed and the disagreement is
  resolved with reasons recorded.
  The check.sh severity split. It was validated twice under load in the
  sending thread: ceilings warned rather than blocking the thread that
  breached them, and budgets warned rather than blocking the commit
  that first measured them. Adopt it; do not re-derive it.
  The llm/ containment exemption, dry-run verified before the move.
  The delivery-form split by case (ADR-035). It resolved a three-way
  contradiction without any side losing.
  A kickoff is a handoff (DEC-18), confirmed against practice as well
  as reasoning.
  The descriptive-segment underscore boundary (N7). It closes ADR-026's
  deferred fork; the separator question is settled.

OPEN ITEMS
  THE CROSS-PROJECT HANDOFF FORM. naming.md's TO slot takes a bare ROLE
  word and assumes sender and receiver share a project. This file had
  to write DRILL-DESIGN to be unambiguous. Either the rule gains a
  cross-project case or the TO slot always carries the project code.
  Decide it in whichever repository touches naming.md next.
  llm_playbook HAS NO STATUS.md. The sending thread's terminal state
  could not be positively recorded as R12 requires, because the file
  CONVENTION-003 and render.md both assume does not exist. This is the
  playbook's own gap and the first thing a playbook thread should fix;
  it is listed here so drill does not inherit the same hole silently
  when it adopts the skeleton.
  SPLITTING naming.md. 241 lines against a 200 ceiling, 3013 tokens,
  half the IMPL budget on its own. The single change most likely to
  bring the budgets back into range. Deferred, not rejected.
  RECALIBRATING the ceilings and budgets. The playbook now holds the
  first measurement ever taken against them. One repository's numbers
  are a data point; drill's would make two.
  check.sh's PARENT-NAME GREP is a bare case-insensitive substring
  match. It works today only because the parent repository has a
  distinctive name. Verified: a repository named "full" produced twelve
  false failures on the same tree.
  PROMOTING RF-PLAYBOOK-001..009 into the preference layers. Several
  are ripe. RF-PLAYBOOK-009 sits directly against S26, which sets
  delivery form by case and does not yet name the generated-file case.
  ERA SHARDING. ADR-012's trigger fired during the sending thread and
  was deferred with the reason recorded; era-2026-q3.md is past 700
  lines.

  Under the kickoff template as amended, your first message declares
  your thread id, the task in your own words, and the filenames you
  expect to produce. If your one-sentence task and this file's scope
  line disagree, say so then.
