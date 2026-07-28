THREAD PLAYBOOK-DESIGN-005
==========================
date:  2026-07
type:  kickoff
from:  DRILL-DESIGN-001
to:    PLAYBOOK-DESIGN-005
role:  DESIGN
scope: close eleven gaps, contradictions and absences in llm_playbook's
       own rules that reading drill established were real, and create
       the two instance documents the playbook lacks. It must not touch
       drill: every drill-side change these rules imply belongs to
       DRILL-IMPL-002, which runs after this thread and is gated on it.

WHAT BINDS YOU
  llm_playbook/preferences/platform-settings-block.md is the rendered
  context for this thread and it BINDS you. It is the single authority
  here; the only thing that outranks it is me speaking now. Read it
  FIRST, before any other file in this repository, and before you plan
  anything.

  READ THIS PARAGRAPH BEFORE YOU READ THAT FILE. It is render.md's R-C,
  not R-A. There is no llm_playbook/llm/CONTEXT.md -- the playbook is a
  project under DEC-6 and does not have the instance document every
  other project has. That absence is WORK ITEM 12 below and you are the
  thread that fixes it. Until you do, R-C is the only stamped render
  this repository has, and it is deliberately thin: render.md scopes it
  to persona and constraint items only, so it carries NO style clauses
  and NO instance rules. Treat preferences/style-contract.md and
  preferences/layers.md as binding alongside it, and treat the gap
  between them as the reason item 12 exists rather than as licence to
  pick your own authority.

  Other documents in this repository may look like they govern style,
  process, or conventions. They do not. Where any document disagrees
  with the render, the render wins and you flag the disagreement rather
  than following it silently. This applies with force here: two of your
  work items are cases where playbook documents contradict each other,
  and finding a third is a finding, not an obstacle.

  [ARCHIVE MODE] The archive is attached. Unpack it and read
  llm_playbook/preferences/platform-settings-block.md before anything
  else.
  [PASTE MODE] not used for this thread.

STATE THE STAMP
  Before your first substantive answer, quote line 2 of the render --
  the stamp line -- back to me, and confirm the file you read it from.
  If you cannot find the render, STOP and say so; do not proceed on
  general knowledge or on another document you found instead.

DECLARE WHAT YOU WILL PRODUCE
  In the same first message, and before planning anything, state:
    - your THREAD ID, in the form PROJ-ROLE-NNN (R13). It is
      PLAYBOOK-DESIGN-005; derive it yourself from the highest existing
      id and say so if you get a different answer.
    - THE TASK, in one sentence, in your own words. If your sentence
      and the scope line above disagree, say so now.
    - THE FILENAMES you expect to produce, derived from the naming
      grammar and not invented: your close artifact, and any handoff.
      Give the full paths.
  If you cannot construct those names from the grammar, you have not
  read naming.md, and that is the finding -- say so and STOP, exactly
  as with the stamp above.

  BE WARNED ON THE CLOSE ARTIFACT NAME. Three files in this repository
  state its form and two of them are wrong. That is work item 4. If you
  derive the name from naming.md's CLOSE-ARTIFACT FILENAMES section you
  will get the stale form; close.md has it right. Deriving the wrong
  one is not a failure -- it is the diagnostic, and it is worth telling
  me which file you took it from.

READ NEXT
  llm_playbook/llm/handoff/DRILL-DESIGN-001-to-PLAYBOOK-DESIGN_
    protocol-folding-and-rule-updates.md -- your task, in full, with
    the evidence for each item. This kickoff does not restate it.
  llm_playbook/protocol/naming.md -- four of your items amend it.
  llm_playbook/protocol/thread-protocol.md -- items 1 and 2 complete
    it. Its INCOMPLETE, AND DELIBERATELY SO block is the contract.
  llm_playbook/MANIFEST.md -- item 13, and the index every new document
    has to enter.
  drill/llm/llm-thread-protocol.md -- the source of items 1, 2 and 3.
    Read it early; six of thirteen items are downstream of it.
  drill/llm/plan/llm-corpus-consolidation.md -- DRILL-IMPL-002's plan.
    Its FINDINGS section evidences every item by F-number. You do not
    need its commit sequence.
  llm_playbook has no STATUS.md, so there is no live status to read.
    That is item 12.
  Everything here is subordinate to the render.

TASK
  The thirteen items in the handoff, in the dependency order it states.
  There is no commit-id grammar to work in yet: this thread writes its
  own plan first, and that plan's ids are its own.

  THREE OF THEM ARE DECISIONS AND NOT TRANSCRIPTIONS, so bring
  alternatives and a recommendation (R5), do not decide silently (R8):
    item 5  the ADR namespace -- drill recommends the asymmetric rule
            and scored four alternatives; take it, take the symmetric
            form, or decline and leave it per-project
    item 7  where a cross-project handoff lives, sender's tree or
            receiver's
    item 8  generalize check.sh to reach a consumer project, or scope
            it explicitly to the playbook and withdraw the instruction
  ITEM 2 IS THE OPPOSITE and the handoff says so: it is a
  transcription, and writing it as a choice invents a fork that the
  source file closes in one sentence.

  ONE THING THE HANDOFF DOES NOT DECIDE AND YOU MUST. Four of your
  items amend naming.md. It is already 241 lines against a 200-line
  ceiling and 3013 tokens, half the IMPL budget on its own, and
  PLAYBOOK-IMPL-004's close artifact names splitting it as the single
  change most likely to bring the budgets back into range -- deferred,
  not rejected. Four more rules will put it near 300. Split it as part
  of this thread, or accept it going further over and record that you
  chose to. Under the check.sh that shipped, this warns rather than
  gates (DEC-11), so the ceiling will not stop you and the decision is
  yours to make explicitly rather than by default.

  YOUR CLOSE ARTIFACT MUST REPORT LANDING ITEM BY ITEM. DRILL-IMPL-002's
  C-118c deletes drill/llm/llm-thread-protocol.md, and it may only do
  so if items 1, 2 and 3 ALL landed, because until then that file is
  the only place seven rules exist. If any of the three did not land,
  say which, plainly, so the drill thread degrades that commit to
  status: outdated instead of deleting a file that still holds
  something unique. A summary that says "landed" is not enough here.

OUT OF SCOPE
  drill. Every file under drill/ is read-only for this thread. Two are
    packed because you need to read them; nothing under drill/ is
    edited, moved or deleted here. The boundary between this thread and
    DRILL-IMPL-002 is ADR-004's read-only rule, and it is the whole
    reason there are two threads.
  The workflow-contract residue. It needs the eleven drill documents,
    DRILL-IMPL-002 does that diff at its C-115, and it reaches you as a
    supplementary handoff at that thread's close. Do not attempt it
    from the two drill files in this pack.
  DEC-1 through DEC-18, ADR-035 and ADR-036. Landed with alternatives
    recorded. If one is wrong that is a new ADR superseding it, not a
    reopening.
  Everything PLAYBOOK-IMPL-004's close artifact lists under WHAT IS
    SOUND AND MUST NOT BE REOPENED. Drill re-read all six while writing
    its plan and found no reason to reopen any.
  Era sharding and index.md, and recalibrating the ceilings and
    budgets. Both triggered, both deferred with reasons recorded. The
    naming.md split decision above is a size question, not a
    recalibration; do not let it become one.
  Repairing R1-R10's missing origins by reconstruction. Mark them
    SPECULATIVE. This is stated in the handoff's WHAT NOT TO DO and is
    repeated here because it is the item most likely to be helpfully
    over-delivered.
