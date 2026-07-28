HANDOFF -- DRILL-DESIGN-001 to PLAYBOOK-DESIGN
==============================================
date: 2026-07
type: handoff
from: DRILL-DESIGN-001 (DESIGN; the thread that read drill/llm against
      the PLAYBOOK-IMPL-004 handoff and produced the consolidation plan)
to:   PLAYBOOK-DESIGN (may write llm_playbook; must not touch drill)
role: DESIGN
scope: eleven playbook changes that reading drill established were
  needed. It carries the EVIDENCE and not the rule text: drill found
  these and cannot write them, because the playbook checkout is
  read-only from a drill thread. It does NOT carry drill's own
  consolidation; that is DRILL-IMPL-002's, and it runs after this.
status: current

THREAD ID, AND WHY IT IS 001
  Drill has run at least six threads and none of them has an id.
  They predate the grammar and no ids exist for them, so none is
  invented here: fabricating history to make a counter look continuous
  is the failure naming.md's classification note forbids and the
  failure DRILL-IMPL-002's C-116b avoids for the eleven handoffs.
  The counter therefore opens at 001 with the first thread that
  declares one, and the gap is recorded rather than filled.

NOTE ON THIS FILENAME
  Cross-project, so the TO slot carries the project code and not a
  bare ROLE word. That is DEC-D6, ratified in this thread from the
  author's ruling and from what PLAYBOOK-IMPL-004's own handoff
  already did under protest. Item 7 below asks you to write it down.
  THE LOCATION IS A GUESS. naming.md says "<FROM>-to-<TO>.md in the
  project's handoff/ directory" and does not say WHOSE project when
  the two differ. This file is placed in the RECEIVER's -- llm_playbook
  /llm/handoff/ -- because that is where PLAYBOOK-IMPL-004's handoff to
  drill actually landed, and observed practice beats a coin flip. It is
  item 7's second half.

WHY A DESIGN THREAD
  Ten of the eleven items below are gaps, contradictions or absences in
  the playbook's own rules. Closing them means writing rule text that
  binds every future thread in every consumer project, and in three
  cases it means choosing between defensible alternatives. An
  implementation thread would have to make those choices silently,
  which R5 and the deviation rule forbid. Items 1 and 8 are closer to
  execution; they travel with the rest because splitting them buys
  nothing and costs a thread boundary.

READ FIRST
  drill/llm/llm-thread-protocol.md -- 96 lines, the source of items 1,
    2 and 3. This is the file PLAYBOOK-IMPL-004 was specified against
    and could not read. Read it before anything else here; six of the
    eleven items are downstream of it.
  drill/llm/plan/llm-corpus-consolidation.md -- DRILL-IMPL-002's plan.
    Its FINDINGS section is where every item below is evidenced, by
    F-number. You do not need the commit sequence.
  llm_playbook/protocol/thread-protocol.md -- the file items 1 and 2
    complete. Its INCOMPLETE, AND DELIBERATELY SO block states the
    contract you are discharging.

STATE
  llm_playbook is at the state PLAYBOOK-IMPL-004 landed: 32 files,
  check.sh clean, exit 0, five non-blocking warnings. Nothing has
  changed since.
  drill is UNTOUCHED. DRILL-IMPL-002 has not run and will not run until
  this thread lands. Its plan is written, verified against the tree at
  sorted-md5 4296b13bf21a46146589d785635db02c, and gated on you.
  YOU RUN FIRST, AND THAT IS DELIBERATE (DEC-D8). Running second costs
  two things. drill would render at its C-101 against layers.md and
  style-contract.md that item 3 is about to change, so it would go
  stale inside its own thread and need a second render. And drill could
  not delete llm-thread-protocol.md, because until items 1, 2 and 3
  land, that file is the only place seven rules exist. Running first
  makes drill render once and delete cleanly.
  ADR-016's tripwire forbids running these in parallel anyway: one
  thread at a time is load-bearing for the kickoff-only render hash
  check, and two threads editing style-contract.md and a render built
  from it is the case it names.

WORK, IN DEPENDENCY ORDER

  1. R1-R10 INTO protocol/thread-protocol.md, AT THEIR RESERVED
     NUMBERS. The ten rules exist verbatim in
     drill/llm/llm-thread-protocol.md and abut R11-R13 exactly: R1
     REPO WINS, R2 CORRECTIONS ARE FINDINGS, R3 SPIKE BEFORE SPEC, R4
     SPIKES ARE HANDOFF ARTIFACTS, R5 DECISION-FRAMED DOCS, R6 DOCS
     LAND FIRST, R7 ONE COMMIT AT A TIME, R8 STOP POINTS, R9 SCOPE
     HONESTY, R10 ADVERSARIAL PASS. No gap, no collision, no
     renumbering of anything.
     THE TRANSCRIPTION IS NOT THE WHOLE JOB. thread-protocol.md's
     accept criterion requires every rule to cite an origin failure or
     be marked SPECULATIVE, and drill's ten carry no origins. Mark all
     ten SPECULATIVE rather than reconstructing origins from drill's
     history -- that is what was done for R11 and R13 and it is the
     same reasoning. Record that the originating failures are
     recoverable from drill's decisions.md and its pre-grammar handoffs
     if anyone later wants them.

  2. CLOSE THE ROLES OPEN. thread-protocol.md records: "the drill
     original uses DESIGN/IMPL/REVIEW. Whether REVIEW is a fourth role
     or CAPTURE under an older name is a real decision." THE PREMISE IS
     FALSE. drill's file says: "Every thread is exactly one of: DESIGN
     ... IMPLEMENTATION ... or CAPTURE (deliverable: scored backlog
     entries plus reasoning docs)." There is no REVIEW role and CAPTURE
     is defined, which also answers the close artifact's "CAPTURE is
     named in five documents and defined in none". The likely source of
     the wrong premise is drill's filename review-D1.md.
     Write it as an ADR that says plainly it RECORDS what a file
     already said rather than choosing between options, so a later
     reader does not mistake a transcription for a judgement. Residue:
     drill writes IMPLEMENTATION where the grammar writes IMPL.

  3. FOLD llm-thread-protocol.md's SEVEN RESIDUE ITEMS. Everything else
     in that file is carried by item 1, carried by item 2, already
     covered by the playbook, or resolved against drill. The diff is in
     the plan at F-18 and the "already covered" column is worth reading
     before you write anything -- PROJECT.md already states drill's
     layering invariant more completely than the protocol file does.
     Items 1 to 6 are kickoff.md's KICKOFF TEMPLATE:
       (a) a repo-access slot: the clone recipe and the directories in
           scope. clone-and-verify.md has the procedure; the template
           has nowhere to name it.
       (b) do not paste committed documents unless they are unpushed,
           and if you do, say they are unpushed.
       (c) INLINED GROUND TRUTH: exact signatures and facts copied from
           the code, never from memory, each labelled verify-first.
       (d) INSTINCTS, labelled as instincts -- "my lean is X;
           pressure-test it". This is what earns the model the right to
           overrule with evidence, and it is the item drill rates
           highest.
       (e) a STOP-points slot. R8 makes them a rule and the template
           has nowhere to declare them.
       (f) the HANDOFF TEMPLATE's ground-truth section should carry
           exact VERIFIED SIGNATURES. STATE is where things stand,
           which is a different thing.
     Item 7 is a style clause or a CONVENTION item, and it has zero
     coverage anywhere: improving a shipped policy -- grading,
     scheduling -- by taste instead of by a metric named in advance.
     Grep the playbook for "metric" and for "taste"; both return
     nothing.
     ONE ANTI-PATTERN IS DELIBERATELY NOT CARRIED. drill bans
     "restating the whole protocol in every prompt (point here)".
     ADR-007 decides the opposite and gives the reason: a stateless
     chat cannot resolve includes, so prompts are standalone and
     duplication is the price. drill's rule assumes a reader who can
     follow a pointer -- true in archive mode, false in paste mode. The
     playbook has already chosen; record the drop so it is visibly a
     decision and not an oversight.
     WHEN 1, 2 AND 3 HAVE LANDED, drill deletes
     llm-thread-protocol.md at its C-118c. Until then it cannot.

  4. THE CLOSE-ARTIFACT FILENAME, STATED THREE TIMES AND WRONG TWICE.
       naming.md, CLOSE-ARTIFACT FILENAMES:
         close-<THREAD-ID>.md in the project's llm/ directory
       kickoff.md, NOTES ON USE:
         "The close artifact (close-<THREAD-ID>.md, naming.md)"
       close.md, NOTES ON USE:
         "llm/close/<THREAD-ID>_<descriptive>.md"
     close.md is right and cites naming.md as its authority for a form
     naming.md contradicts. DEC-3 drops genre prefixes in all cases,
     close artifacts included; N7's own worked example is
     close/PLAYBOOK-IMPL-003_g1a-transport-render-gate.md; and
     PLAYBOOK-IMPL-004's close artifact is named in that form in the
     handoff that commissioned this work. The CLOSE-ARTIFACT section
     was not updated when N6-N8 landed and kickoff.md propagated the
     stale form.
     A thread writing its first close artifact has two rules and no way
     to choose from naming.md alone, which N5 makes a finding by
     definition. drill will hit this the moment DRILL-IMPL-002 closes.

  5. THE ADR NAMESPACE. drill's decisions.md defines ADR-001..061 and
     era-2026-q3.md defines ADR-001..036, in two namespaces, with
     confirmed live collisions:
       ADR-024  drill: which table gets metadata
                playbook: naming-options logged as adoption evidence
       ADR-035  drill: optional global result ceiling, shipped dark
                playbook: delivery form set by the CASE
       ADR-036  drill: bounded retry / fail-loud generation
                playbook: the settings block is generated
     drill's PROJECT.md already writes "drill's own ADR-008" to
     disambiguate by hand, which is the convention arriving as a habit.
     DRILL'S RECOMMENDATION, scored 9/10 against four alternatives in
     the plan: a bare ADR-NNN means the LOCAL project's; a foreign
     decision is cited PLAYBOOK-ADR-NNN. It costs one rewritten
     citation across drill's fifty files -- verified, it is ADR-020 in
     g1-findings.md -- and it is what makes drill's dangling-ADR check
     able to pass at all. Symmetric prefixing (DRILL-ADR-NNN as well)
     scored 6: grammatically cleaner and consistent with RF-DRILL-NNN,
     but several hundred substitutions in a 1700-line file, which is
     what S30 forbids. The recommendation is forward-compatible with
     it: every citation it rewrites is one the symmetric form would
     rewrite too.
     drill adopts this as an instance rule at its C-119 regardless. It
     is here because the next consumer project will collide the same
     way and an instance rule does not reach it.

  6. THE CROSS-PROJECT TO SLOT. naming.md's TO slot takes a bare ROLE
     word and assumes sender and receiver share a project.
     PLAYBOOK-IMPL-004's handoff had to write DRILL-DESIGN to be
     unambiguous and recorded the gap rather than inventing a rule.
     AUTHOR RULING, ratified in this thread as DEC-D6 and used to name
     this file: the default is silence -- an unqualified slot is
     self-referencing. A slot that crosses a project boundary carries
     the project code.
       TO, same project, id unknown    <ROLE>
       TO, same project, id known      <ROLE>-<NNN>
       TO, cross project, id unknown   <PROJ>-<ROLE>
       TO, cross project, id known     <PROJ>-<ROLE>-<NNN>
     FROM needs no rule: it is always the full thread id and already
     carries PROJ.
     ONE CONSTRAINT IS REQUIRED FOR THIS TO PARSE. Split on "_" to
     strip the descriptive segment, then on "-to-"; the TO segment's
     first token is either a ROLE word or a project code, and there is
     no third case -- UNLESS a project code IS a role word, at which
     point DESIGN-007 is both ROLE-NNN and PROJ-NNN and the rule
     collapses. Add: a project code must not be DESIGN, IMPL or
     CAPTURE. naming.md already says PROJ is chosen once and recorded
     in PROJECT.md, so it is one line on an existing rule.

  7. WHERE A CROSS-PROJECT HANDOFF LIVES. Found by writing this file.
     naming.md says "in the project's handoff/ directory" and does not
     say whose when the two differ. Sender's is the more natural
     reading of the words; receiver's is what actually happened, since
     PLAYBOOK-IMPL-004's handoff to drill landed in drill's tree. This
     file follows practice and says so. Decide it, because the close
     artifact template asks a thread to name the handoffs it produced
     by filename, and a filename without a directory is not one.

  8. check.sh CANNOT REACH A CONSUMER PROJECT. The PLAYBOOK-IMPL-004
     handoff instructs drill to "scope containment if drill runs
     check.sh". It cannot: the script sets PLAYBOOK_DIRECTORY to
     "$WORKTREE_ROOT/llm_playbook", walks only that tree, and exempts
     the literal path llm_playbook/llm/*. Nothing in it looks at drill.
     Either generalize it to take a project directory and derive the
     exemption, or state that it is a playbook-only ruler and remove
     the instruction from the handoff template's vocabulary. drill has
     no opinion on which; it needs the instruction to stop being one it
     cannot follow.

  9. llm_playbook HAS NO STATUS.md. This is the close artifact's own
     NEXT STEPS item 1 and it is still open. CONVENTION-003 puts live
     status in exactly one file called STATUS.md, render.md names
     STATUS.md among the instance documents beside CONTEXT.md, DEC-6
     makes the playbook a project like any other, and the file does not
     exist -- so R12's positive-record requirement cannot be met by any
     playbook thread, including this one. Related and unrecorded:
     PLAYBOOK-IMPL-004's close artifact states "HANDOFF ARTIFACTS
     PRODUCED: none" while the handoff to drill exists and declares
     from: PLAYBOOK-IMPL-004. It was written after the close artifact
     by a thread the record does not name. The content is consistent
     throughout; the provenance is not recorded, and item 9 is why it
     could not be.

  10. THE PARENT-NAME GREP IS A BARE SUBSTRING MATCH. Case-insensitive,
      unanchored, against basename "$WORKTREE_ROOT". Deferred in the
      close artifact and named in the handoff's open items. Recorded
      here only because the two describe it with different evidence --
      the close artifact says it works because "explorations" is
      distinctive, the handoff says a repository named "full" produced
      twelve false failures -- and a later reader should not treat them
      as two findings. drill has no stake in it and offers no fix.

  11. THE WORKFLOW-CONTRACT RESIDUE. NOT IN THIS HANDOFF. It requires
      the eleven drill documents and DRILL-IMPL-002 does that diff at
      its C-115: extract the WORKFLOW CONTRACT / DELIVERY DISCIPLINE
      section from all eleven, pairwise-diff them, map
      3-to-E10-cutover's version clause by clause against
      commit-planning.md, clone-and-verify.md, runtime-verification.md
      and precedence.md, and rule on what is uncovered. It arrives as a
      supplement -- DRILL-IMPL-002-to-PLAYBOOK-DESIGN-005_workflow-
      contract-residue.md -- at that thread's close.
      IF THE RESIDUE IS EMPTY, NO NEW PLAYBOOK TEXT IS WRITTEN and all
      eleven drill documents are released anyway. That is the success
      case. The supplement ships either way, because an unsent handoff
      is indistinguishable from a forgotten one.

  12. THE PLAYBOOK HAS NEITHER OF ITS OWN INSTANCE DOCUMENTS.
      llm_playbook/llm/CONTEXT.md does not exist and neither does
      STATUS.md. DEC-6 makes the playbook a project like any other and
      it is the only project that has neither. This is not cosmetic:
      protocol/kickoff.md's WHAT BINDS YOU section names
      <project>/llm/CONTEXT.md and CANNOT BE FILLED HONESTLY for the
      playbook's own threads. Your own kickoff had to point at R-C, the
      platform settings block, and explain why -- read it; it is the
      worked example of the gap.
      Create both. CONTEXT.md is R-A per render.md, authored from
      layers.md and style-contract.md with the stamp computed the same
      way R-C's was. STATUS.md is item 9 and the close artifact's own
      NEXT STEPS item 1; record PLAYBOOK-IMPL-004's terminal state in
      it retroactively, which is the positive record R12 required and
      could not get.
      DO THIS EARLY. Every later item in this list is easier to write
      against a render than against three source files, and the thread
      after you will be the first playbook thread whose kickoff can be
      filled as the template intends.

  13. MANIFEST.md. It is the sole authoritative index -- per-role
      required-read lists with token budgets, and each document's load
      class -- and items 1 through 12 add rules, change two templates
      and create at least two documents. Every one of those is a
      MANIFEST edit. Drill flags this rather than specifying it,
      because drill has never seen MANIFEST.md: it was not in the pack
      DRILL-DESIGN-001 worked from. Treat the list above as incomplete
      in exactly this one respect and reconcile it against the index
      yourself.
      EXPECT THE BUDGETS TO GET WORSE. They are already exceeded on the
      common set alone -- DESIGN by 2038 tokens, IMPL by 5202, CAPTURE
      by 1771 -- and this thread adds documents. Do not trim the lists
      to fit; that is the failure PLAYBOOK-IMPL-004 refused twice and
      DEC-11 exists so the budgets warn rather than gate.

A NOTE ON SIZE, WHICH IS A DECISION AND NOT A WARNING
  Items 4, 5, 6 and 7 all amend naming.md. It is 241 lines against a
  200-line ceiling and 3013 tokens, and PLAYBOOK-IMPL-004's close
  artifact names splitting it as the single change most likely to bring
  the budgets back into range, deferred and not rejected. Four more
  rules put it near 300. Split it in this thread or accept it going
  further over, but decide it rather than discovering it: the ceiling
  warns and does not gate (DEC-11), so nothing will stop you.

WHAT NOT TO DO
  Do not reconstruct origin failures for R1-R10 from drill's history.
    They are not recorded in the source file. Ten invented origins
    under authoritative numbers is the failure that left R1-R10 unwritten
    in the first place; SPECULATIVE is the answer the playbook already
    chose twice.
  Do not renumber R11, R12 or R13. naming.md and kickoff.md cite R12
    and R13 by number.
  Do not treat item 2 as a decision. It is a transcription. Writing it
    as a choice between REVIEW and CAPTURE invents a fork that the
    source file closes in one sentence.
  Do not carry drill's "point here instead of restating" anti-pattern.
    ADR-007 decided against it with a reason that still holds.
  Do not touch drill. Every drill-side change these items imply is in
    DRILL-IMPL-002's plan and is that thread's. The boundary between
    these two threads is the read-only rule (ADR-004, precedence.md),
    and it is the whole reason there are two.
  Do not renumber or repair drill's ADR ids under item 5. The rule is a
    citation convention. N3 makes the ids stable forever.

WHAT IS SOUND AND SHOULD NOT BE REDONE
  Everything PLAYBOOK-IMPL-004's close artifact lists under WHAT IS
  SOUND. Drill re-read the frontmatter-carries-classification decision,
  the three-value status vocabulary, the check.sh severity split, the
  llm/ containment exemption, the delivery-form split by case, and
  a-kickoff-is-a-handoff while writing its plan, and found no reason to
  reopen any of them. Two were load-bearing in drill's favour: the
  status vocabulary caught the superseded drill plan's invented fourth
  value, and the delivery-form split resolved a live contradiction
  between drill's stale render and the current sources.
  R1-R10's reserved numbering. It was reserved correctly; the ten rules
  fit with no gap and no collision. That guess was right and is worth
  saying so, because the close artifact recorded it as a risk.
  DEC-1 through DEC-18, ADR-035 and ADR-036. Landed with alternatives
  recorded. Drill applied them and did not re-litigate any.

OPEN ITEMS
  O-1  Item 5's scope. drill recommends the asymmetric rule and adopts
       it locally either way. Whether the playbook takes it as a
       general rule, takes the symmetric form instead, or declines and
       leaves it per-project is yours. Nothing is blocked on it;
       drill's own check passes under the local rule alone.
  O-2  Item 8's direction. Generalize check.sh or scope it explicitly
       to the playbook. drill has no stake and will follow either.
  O-3  Item 3(d), the instincts slot, is the one residue item drill
       would argue for hardest and the one least like the others -- it
       is a technique for getting better corrections, not a rule. If it
       does not belong in the kickoff template it may belong in the
       CONVENTION layer. Named so it is not dropped by falling between
       two homes.
  O-4  Whether this handoff is in the right directory. Item 7 is the
       rule; this file is the instance. If item 7 decides "sender's",
       move it and note that the first application of the rule was
       wrong, which is a better record than a silent relocation.
