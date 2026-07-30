DRILL llm/ CORPUS CONSOLIDATION -- EXECUTION PLAN
==================================================
date: 2026-07
type: plan
scope: everything to be changed in drill/llm by DRILL-IMPL-002 -- the
  surviving part of the earlier eight-commit series, refinements.md,
  the lifecycle directories, frontmatter, renames, and the spike
  retirement. Does NOT write a single byte in llm_playbook: every
  playbook change this work implies is PLAYBOOK-DESIGN-005's, and the
  boundary between the two threads is exactly the read-only rule
  (ADR-004, precedence.md) turned into a thread boundary.
status: current
supersedes: the earlier "DRILL execution plan", drafted before the
  PLAYBOOK-IMPL-004 handoff landed and against the pre-DEC-9 archive
  rule

TARGET PATH: drill/llm/plan/llm-corpus-consolidation.md. It cannot go
there until C-107 creates plan/, so it lands at drill/llm/ in C-101
and moves with everything else in C-109. Recorded so the move is not read
later as churn.

--------------------------------------------------------------------------
BASELINE
--------------------------------------------------------------------------

  files  50 markdown, 8 python, 2 directories (handoffs/, spike/)

  Sorted-md5 identifier, as the earlier plan measured it. Run from
  drill/llm:

    find . -name '*.md' | sort | xargs md5sum | md5sum
    4296b13bf21a46146589d785635db02c

  VERIFIED at plan time: matches. Nothing from the earlier series has
  been applied.

  This identifier is find(1)-order dependent and does not cover file
  modes. The playbook thread hit exactly that problem (close artifact
  D1) and switched to the git subtree hash. Do the same here at thread
  time: `git rev-parse HEAD:drill/llm`. It is not recorded in this
  plan because this plan was written from a pack, which carries no
  git history.

--------------------------------------------------------------------------
WHAT CHANGED FROM THE SUPERSEDED PLAN, AND WHY
--------------------------------------------------------------------------

The earlier plan was written against a drill-only view and before the
handoff. Seven things changed. Each is a rule that landed upstream, not
a preference.

R-01  archive/ IS RETIRED, NOT CREATED. DEC-9 and the ADR-012
      amendment retire archive/ repo-wide, explicitly including the
      project skeleton at implementation-plan.md T-011 "and therefore
      drill". Superseded and outdated documents STAY WHERE THEY ARE
      and declare their state in the status field; genuinely removed
      documents are DELETED, because git holds them.
      Consequence: the earlier Stage 0 commit 1 (archive skeleton plus
      a non-authority README) is deleted outright. Commit 8 (move 14
      documents into archive/) becomes "set status: outdated on 14
      documents in place". Stage 3's "then archive them" for the
      handoffs becomes the same. Stage 1's "g1-findings.md is already
      archived; this reads from the archived copy" becomes "read it in
      place, then mark it superseded".
      This also resolves a live off-by-one: plan/consolidation-by-hand-procedure.md's prose
      says ten replacement files and its Step 2 table lists eleven.
      The eleventh is archive/README.md. With archive/ retired there
      are exactly ten, and the discrepancy was never real.

R-02  THE STATUS VOCABULARY HAS THREE VALUES AND historical IS NOT
      ONE. naming.md and DEC-10 fix current / superseded / outdated.
      The close artifact records that historical was considered and
      dropped by name. Every "status: historical" in the earlier plan
      reads "status: outdated".

R-03  THE TYPE VOCABULARY IS LARGER THAN THE EARLIER PLAN KNEW.
      naming.md carries toolkit-rules, preference-source,
      instance-rules, prompt, design, plan, handoff, kickoff, close,
      decisions, refinements, render. The earlier plan listed six and
      would have misclassified refinements.md (it said type: decisions;
      there is a distinct refinements type), llm-thread-protocol.md
      (toolkit-rules) and thread-launch-kit.md (kickoff).

R-04  THE RE-RENDER COMES FIRST. The earlier plan does not mention it.
      layers.md and style-contract.md both changed substantially and
      drill's CONTEXT.md is built from them, so every commit below is
      otherwise made under a stale authority. See F-03; this is not
      ceremony, the stale render instructs the opposite of the current
      delivery rule.

R-05  THE PLAYBOOK GATES ARE GONE. The earlier plan held commits 9 and
      10 pending playbook P5 and P6. P5 landed: protocol/
      thread-protocol.md exists with R11-R13 and a reserved hole. P6
      did not land and was not deferred -- it was handed to drill as
      work item 8, and the close artifact lists it under "Blocked, not
      deferred -- these need input this thread did not have". There is
      nothing to wait for. Both items are drill's own work and are
      scheduled below.

R-06  THE ELEVEN HANDOFFS ARE NOT RELEASED BY A PLAYBOOK COMMIT. They
      are released by the diff in C-115, whose correct outcome may be
      that no new playbook text is written at all.

R-07  study-curriculum-and-conventions.md LEAVES llm/. Author ruling:
      it is written for a human reader, so it belongs in drill/docs/,
      not in the instance directory. This replaces the earlier plan's
      open question about splitting its convention material into
      CODING_CONVENTIONS.md; nothing is split, the whole file moves.

--------------------------------------------------------------------------
FINDINGS
--------------------------------------------------------------------------

Each verified against the tree at the baseline above, by execution.

F-01  THE REVIEW-VERSUS-CAPTURE QUESTION IS ANSWERED BY READING ONE
      FILE, AND THE PLAYBOOK'S PREMISE IS FALSE.
      thread-protocol.md records: "the drill original uses
      DESIGN/IMPL/REVIEW. Whether REVIEW is a fourth role or CAPTURE
      under an older name is a real decision and is not settled here."
      llm-thread-protocol.md, section "Roles of a thread", says:
      "Every thread is exactly one of: DESIGN (deliverable:
      decision-framed docs plus spikes; no shipped features),
      IMPLEMENTATION (deliverable: commits against a plan doc; no new
      design forks decided silently), or CAPTURE (deliverable: scored
      backlog entries plus reasoning docs)."
      There is no REVIEW role. CAPTURE is present and defined in one
      line, which also answers the close artifact's "CAPTURE is named
      in five documents and defined in none". The likely source of the
      wrong premise is the filename review-D1.md. Residue: drill says
      IMPLEMENTATION where the grammar says IMPL.
      Consequence: the handoff asks for two ADRs and neither decides
      anything. They are records, and they say so.

F-02  R1-R10 TRANSFER WITH NO RENUMBERING AND NO INVENTION.
      llm-thread-protocol.md carries exactly R1 through R10, in order,
      no gaps: R1 REPO WINS, R2 CORRECTIONS ARE FINDINGS, R3 SPIKE
      BEFORE SPEC, R4 SPIKES ARE HANDOFF ARTIFACTS, R5 DECISION-FRAMED
      DOCS, R6 DOCS LAND FIRST, R7 ONE COMMIT AT A TIME, R8 STOP
      POINTS, R9 SCOPE HONESTY, R10 ADVERSARIAL PASS. They abut R11-R13
      exactly. The reserved numbers were reserved correctly.

F-03  THE RENDER IS STALE, AND IT INVERTS THIS THREAD'S OWN DELIVERY
      RULE. CONTEXT.md line 2 stamps playbook v0.1.0 at
      2d5ec7f1a9e6c47c8e6ea26a4e5b9093cc7ec29e, content-hash 90f3e04b.
      Recomputing the body hash (`tail -n +3 CONTEXT.md | sha1sum |
      cut -c1-8`) returns 90f3e04b, so there has been no hand edit --
      the render is faithfully stale rather than tampered with. But it
      carries S1-S25 against a style contract that now runs to S30,
      and:
        CONTEXT.md   CONSTRAINT-005  produce the COMPLETE updated
                     file, not a diff or snippet, unless asked
        layers.md    CONSTRAINT-005  never a bare snippet; an EDIT
                     ships as a git-apply-able unified diff, with the
                     complete file as a fallback
      A thread run under this render is instructed to deliver the
      opposite of the rule that now governs. ADR-035 is the resolution
      and S26/S27 carry the detail.

F-04  THE RENDER IS STALE IN A SECOND WAY THE HANDOFF DOES NOT NAME.
      CONTEXT.md states "Drill has no PROJECT.md instance rules at this
      commit, so no instance overrides are emitted." PROJECT.md exists
      and carries instance rules. It in turn cites "S1..S25, D1..D3",
      also stale. The re-render must compose PROJECT.md, which the
      current render does not.

F-16  THE R-B RENDER TARGETS DO NOT EXIST. render.md R-B requires
      CLAUDE.md and AGENTS.md beside CONTEXT.md in <project>/llm/,
      "generated from the same sources in the same render pass at zero
      marginal maintenance". Neither file is in drill/llm. The
      superseded plan's final shape lists both as "sentinels,
      generated" and treats them as present. C-101 therefore CREATES
      them rather than refreshing them, and the "zero marginal
      maintenance" claim has never been tested here because the
      marginal maintenance was never performed.

F-17  THE SPIKES ARE NOT TESTS, ARE NOT RUNNABLE, AND WOULD BREAK THE
      SUITE IF FILED AS TESTS. Three defects, all in the way of the
      superseded plan's "spikes -> drill/tests/spikes/".
      (a) ZERO TEST FUNCTIONS. All five test_*.py files define no
          `def test_`. test_port_equivalence.py is a top-level script:
          module-level parameter-grid loops, print() calls, and a
          closing `raise SystemExit(1 if failure_count else 0)`.
      (b) COLLECTION WOULD EXECUTE THEM. drill/tests holds conftest.py
          and run.sh does a directory pytest run (STATUS.md: "the
          backend pytest side is still a directory run"). pytest
          collects test_*.py by IMPORTING it, so filing these under
          drill/tests/spikes/ runs the grids at collection time and
          raises SystemExit during collection. The 668-green suite
          would not survive the move.
      (c) HARDCODED ABSOLUTE SANDBOX PATHS. Every spike inserts a path
          from a previous sandbox before importing:
            sys.path.insert(0, "/home/claude/explorations/drill")
            sys.path.insert(0, "/home/claude/explorations/sm2")
          Neither resolves on the author's machine. R4 requires spikes
          to be "runnable from a fresh clone" and llm-thread-protocol
          .md's own handoff checklist repeats it. They are not.
      Additionally, test_port_equivalence.py imports the external sm2
      module, and STATUS.md schedules sm2/ retirement under A3. That
      spike has a shelf life independent of where it is filed.
      Consequence: C-111 and C-112 replace it. See DEC-D7.

F-18  llm-thread-protocol.md IS NOT DELETABLE YET, AND THE RESIDUE IS
      SEVEN ITEMS. Diffed section by section against the playbook.
      CARRIED by work already scheduled:
        Roles of a thread             -> C-121 (F-01)
        The ten working rules R1-R10  -> C-120 (F-02)
      ALREADY COVERED, nothing owed:
        flat procedural, no classes, no nested functions, no wrapper
          indirection                 -> S28, S29
        full descriptive names, no abbreviations unless the noun
          behaves as a word           -> S1
        ASCII only                    -> S25, CONSTRAINT-007
        the config <- db <- logic <- http layering invariant
                                      -> PROJECT.md ARCHITECTURE,
                                         which states it far more
                                         completely than this file does
        handoff checklist: decision-framed docs -> R5; commit-level
          plan -> commit-planning.md; green spikes -> R4 and
          spike-and-verify.md; deferred items with reasons ->
          close.md DEFERRED; the three R9 questions -> R9
        anti-patterns: trusting a summary over the code it summarizes
          -> R1; reimplementing a function inside its own test -> R3;
          deciding a fork mid-commit -> R8; prose claims of
          equivalence where a spike was cheap -> R3
      RESOLVED AGAINST drill, so dropped rather than carried:
        the anti-pattern "restating the whole protocol in every prompt
        (point here)". PLAYBOOK-ADR-007 decides the opposite: prompts
        are standalone and pasteable alone, and "duplication between
        prompts is accepted as the price of statelessness", because a
        stateless chat cannot resolve includes. drill's rule assumes a
        reader who can follow a pointer -- true in archive mode, false
        in paste mode. The playbook has already chosen. Record the
        drop rather than carrying a rule the toolkit rejects.
      RESIDUE -- seven items with no home in the playbook:
        1. kickoff item 2, repo access: the sparse-clone recipe and
           the directories in scope. clone-and-verify.md covers the
           procedure; kickoff.md's template has no slot for it.
        2. kickoff item 3's nuance: do not paste committed docs unless
           they are unpushed, and if you do, say they are unpushed.
        3. kickoff item 4, INLINED GROUND TRUTH: exact signatures and
           facts copied from the code, never from memory, each
           labelled verify-first.
        4. kickoff item 5, INSTINCTS labelled as instincts -- "my lean
           is X; pressure-test it" -- which is what earns the model
           the right to overrule with evidence.
        5. kickoff item 7: a STOP-points slot. R8 makes STOP points a
           rule; the kickoff template has nowhere to declare them.
        6. handoff checklist item 1: a ground-truth section carrying
           exact VERIFIED SIGNATURES. kickoff.md's HANDOFF TEMPLATE
           has STATE, which is where things stand, not signatures.
        7. the anti-pattern: improving a shipped policy (grading,
           scheduling) by taste instead of by a metric named in
           advance. Zero coverage anywhere in the playbook -- grep for
           "metric" and for "taste" across llm_playbook returns
           nothing.
      Items 1-6 are kickoff.md edits; item 7 is a style clause or a
      CONVENTION item. All playbook-side. See DEC-D8.

F-05  g1-findings.md CANNOT BE MIGRATED MECHANICALLY. Fourteen findings,
      F1-F14. At least two are already discharged or falsified by the
      tree: F5 records "drill has no PROJECT.md, so the render emits no
      instance rules" (PROJECT.md exists); F4 records CODING_CONVENTIONS
      .md as redundant with the render, which interacts with R-07 and
      with ADR-030's account of a thread that followed
      CODING_CONVENTIONS.md instead of the render. Renumbering F1-F14
      to RF-DRILL-001..014 verbatim would import a false statement as a
      durable record. Each entry is triaged on migration and its
      disposition stated.

F-06  THE ADR NAMESPACES COLLIDE, LIVE, IN THREE PLACES AT LEAST.
      drill/llm/decisions.md defines its own ADR-001..061.
      llm_playbook/decisions/era-2026-q3.md defines its own
      ADR-001..036. Confirmed collisions on the same id:
        ADR-024  drill: which table gets metadata (questions.metadata)
                 playbook: naming-options-2026-07 logged as
                 convention-adoption evidence
        ADR-035  drill: optional global result ceiling, shipped dark
                 playbook: delivery form is set by the CASE
        ADR-036  drill: bounded retry / fail-loud generation
                 playbook: the settings block is generated
      The superseded plan cites "ADR-024 says this stays parked in
      drill", meaning the playbook's. Read against drill's decisions.md
      that sentence is about a database column. PROJECT.md line 62
      already writes "drill's own ADR-008" to disambiguate by hand,
      which is the convention arriving informally. See DECISIONS below.

F-07  THE SUPERSEDED PLAN'S VERIFY CHECK CANNOT PASS, AND THE FIX IS
      F-06'S RULE. It greps ADR-[0-9]{3} tree-wide and expects every
      id undefined in decisions.md to be empty. Measured now:
        undefined: ADR-001 002 003 004 005 006 007 008 009 020
      ADR-001..009 are defined in spec.md under `### ADR-NNN:` headings
      and are ceded to decisions.md by C-103. Simulating that cession:
        remaining undefined: ADR-020
      ADR-020 is a PLAYBOOK ADR (CONTEXT.md lives in the project's llm/
      instance dir), cited from g1-findings.md and therefore migrating
      into refinements.md. Under the namespace rule it becomes
      PLAYBOOK-ADR-020 and the check goes empty. Verified by simulation
      at plan time; the check is achievable and is stated correctly in
      VERIFY below.

F-08  RENAME COST IS SMALL AND UNIFORM. Inbound references, counted
      across all .md in drill/llm, excluding self:
        consolidation-findings            8    implementation-plan  8
        vocab-language-futures            5    refinements-and-wiring 5
        adr-index                         5    feature-backlog-2026-07 4
        usage-and-study-guide             3    design-A-quick-consol.  2
        llm-thread-protocol               2    thread-launch-kit       2
        design-handoffs-BCDE              1    naming-options-2026-07  1
        study-curriculum-and-conventions  1    use-period-plan-2026-07 1
        thread-N-vocab-plan               1    authoring-guide-2026-07 0
        v1-completion-guide               0    g1-findings             0
      Nothing approaches the 31-reference case naming.md's
      classification note was written to forbid (the playbook's own
      implementation-plan.md). Every rename below is affordable and
      every reference fix is small enough to land in the rename commit.

F-09  drill CANNOT RUN check.sh AS IT STANDS, SO HANDOFF ITEM 5 IS
      MOOT UNTIL SOMETHING CHANGES. The script sets
      PLAYBOOK_DIRECTORY="$WORKTREE_ROOT/llm_playbook" and walks only
      that tree; its containment exemption is the literal path
      llm_playbook/llm/*. It never looks at drill. "Scope containment
      if drill runs check.sh" describes a configuration that does not
      exist. Recorded, not built -- generalizing the script is playbook
      work and is out of scope here.

F-10  TWO drill FILES CONTAIN NON-ASCII BYTES, AGAINST drill'S OWN
      STATED RULE. STATUS.md says "ASCII only" and CONSTRAINT-007 /
      S25 say the same.
        260626_roadmap-rec-after-D2.md   line 10, two arrow characters
        decisions.md                     line 1135, a curly apostrophe
      Both files are touched by this thread anyway. Under check.sh's
      severities this is a hard FAIL, not a warning.

F-11  THREE PLAYBOOK FILES STATE THE CLOSE-ARTIFACT FILENAME AND TWO
      OF THEM ARE WRONG, INCLUDING THE GRAMMAR ITSELF.
        naming.md, CLOSE-ARTIFACT FILENAMES:
          close-<THREAD-ID>.md, in the project's llm/ directory
        kickoff.md, NOTES ON USE:
          "The close artifact (close-<THREAD-ID>.md, naming.md)"
        close.md, NOTES ON USE:
          "llm/close/<THREAD-ID>_<descriptive>.md -- the id names the
          thread and the descriptive segment names the SUBJECT"
      close.md is correct and cites naming.md as its authority for a
      form naming.md contradicts. DEC-3 drops genre prefixes in all
      cases, close artifacts included; N7's worked example is
      close/PLAYBOOK-IMPL-003_g1a-transport-render-gate.md; the
      handoff names the sending thread's close artifact in that form.
      The CLOSE-ARTIFACT section was not updated when N6-N8 landed and
      kickoff.md propagated the stale form.
      A drill thread writing its first close artifact has two rules
      and no way to choose from naming.md alone, which N5 makes a
      finding by definition. Recorded as a refinement against the
      playbook, not repaired here (DEC-D5).

F-12  THE HANDOFF AND THE CLOSE ARTIFACT DISAGREE ON WHETHER THE
      HANDOFF EXISTS. The close artifact: "HANDOFF ARTIFACTS PRODUCED:
      none. The drill handoff was scoped into this thread and is not
      written; it is the next thread's first task or this thread's
      outstanding debt." The handoff exists and declares
      from: PLAYBOOK-IMPL-004. It was therefore written after the close
      artifact, by a thread the close artifact does not name. Not
      blocking -- the handoff's content is consistent with the close
      artifact throughout -- but its provenance is unrecorded, and R12
      cannot record it because llm_playbook still has no STATUS.md.

F-13  THE PARENT-NAME GREP'S FALSE-POSITIVE EVIDENCE IS CITED TWO
      DIFFERENT WAYS. The close artifact says the check works "only
      because 'explorations' is a distinctive word". The handoff says
      "a repository named 'full' produced twelve false failures on the
      same tree". Both describe the same defect and neither is drill's
      to fix; noted only so a reader does not treat them as two
      separate findings.

F-14  plan/consolidation-by-hand-procedure.md's STATED STATUS.md SIZE IS OFF BY FOUR.
      It records the rewrite as 256 -> 198 lines. The file at the
      verified baseline is 252 lines. Small, but the sending series
      hit a baseline-measurement error once already (close artifact
      D1), so it is recorded rather than rounded away.

F-15  THE FOURTEEN DOCUMENTS SLATED FOR RETIREMENT ARE ENUMERATED, AND
      ONE FILE IS STILL UNACCOUNTED FOR. plan/consolidation-by-hand-procedure Step 1 names
      eleven at the root and three under handoffs/. Cross-checked
      against the tree: all fourteen exist. The only file in drill/llm
      with no disposition in either document is
      handoffs/DRILL-DESIGN-consolidation.md -- an earlier handoff to a
      drill design thread, from an unnamed playbook design thread,
      declaring itself self-contained and assuming only drill/llm. It
      is superseded by the PLAYBOOK-IMPL-004 handoff and nothing says
      so. Disposition assigned in C-109.

--------------------------------------------------------------------------
DECISIONS
--------------------------------------------------------------------------

DEC-D1  ADR CITATION NAMESPACE. A bare ADR-NNN in a drill document
        means DRILL's ADR-NNN. A playbook decision is always cited as
        PLAYBOOK-ADR-NNN. No id is renumbered, in either repository,
        and no existing bare citation is rewritten except where it
        means a playbook ADR (F-07 identified the complete set: one
        occurrence, ADR-020 in g1-findings.md).
        Rationale and the alternatives are in OPTIONS below. This is a
        drill instance rule and goes in PROJECT.md; it is proposed to
        the playbook as a refinement, because the same collision will
        recur in the next consumer project.

DEC-D2  g1-findings.md IS SUPERSEDED IN PLACE, NOT DELETED. Its own
        frontmatter says it is deleted when refinements.md lands.
        DEC-9 deletes what is REMOVED and keeps what is SUPERSEDED,
        and this file is superseded: refinements.md names it in its
        supersedes field and carries its content forward. Its
        TEMPORARY status is discharged by the migration, not by the
        deletion.

DEC-D3  study-curriculum-and-conventions.md MOVES TO drill/docs/, WHOLE.
        Author ruling: it addresses a human reader, and drill/llm is
        instance state for threads. Nothing is split into
        CODING_CONVENTIONS.md. It gets frontmatter anyway, because its
        one inbound reference (STATUS.md) survives the move and a
        reader arriving from there needs to know whether it binds.

DEC-D4  THE TWO REQUESTED ADRs ARE RECORDS, NOT DECISIONS. F-01 makes
        both answerable by reading. They are written as ADRs because
        the handoff asks for ADRs and because the playbook's
        thread-protocol.md carries an OPEN that must be closed by a
        citable record. Each states plainly that it records what a
        file already said rather than choosing between options, so a
        later reader does not mistake a transcription for a judgement.

DEC-D5  PLAYBOOK DEFECTS ARE RECORDED, NOT REPAIRED. F-09, F-11, F-12,
        F-13 are all playbook-side. ADR-004 and precedence.md make the
        playbook checkout read-only from a thread's point of view;
        fixes travel as refinement entries and reach the playbook
        through a human editorial pass. They land in refinements.md as
        RF-DRILL entries citing the playbook item, and are named in
        this thread's close artifact.

DEC-D6  THE CROSS-PROJECT HANDOFF FORM. Author ruling, and it ratifies
        what the inherited handoff already did rather than changing it.
        The DEFAULT is silence: an unqualified slot is self-referencing
        -- same project as the sender. A slot that crosses a project
        boundary carries the project code.
          TO, same project, id unknown      <ROLE>
          TO, same project, id known        <ROLE>-<NNN>
          TO, cross project, id unknown     <PROJ>-<ROLE>
          TO, cross project, id known       <PROJ>-<ROLE>-<NNN>
        FROM needs no rule: it is always the full thread id, which
        already carries PROJ. So PLAYBOOK-IMPL-004-to-DRILL-DESIGN.md
        is correct as written, and the OPEN ITEM it recorded is closed
        by ratification.
        PARSING, and this is why the rule is unambiguous: split the
        filename on "_" to strip any descriptive segment, then on
        "-to-". The TO segment's FIRST token is either a ROLE word --
        a closed set of three -- or it is a project code. There is no
        third case.
        ONE ADDITION IS REQUIRED FOR THAT TO HOLD: a project code must
        not be one of DESIGN, IMPL or CAPTURE. Otherwise DESIGN-007
        parses as both ROLE-NNN and PROJ-NNN and the rule collapses on
        its one edge case. naming.md already says PROJ is chosen once
        per project and recorded in PROJECT.md; this is a one-line
        constraint on that choice. Proposed as a refinement (DEC-D5),
        together with the rule itself.

DEC-D7  THE SPIKES ARE RETIRED, NOT RELOCATED. Author ruling. They
        depend on code being deleted (spike_port_equivalence imports
        the sm2 module STATUS.md retires under A3) and on absolute
        sandbox paths that resolve nowhere (F-17c), so they are not
        self-contained and not self-sufficient. What is worth keeping
        is what they ESTABLISHED, not the files that established it.
        THE RECORD POINTS AT GIT; IT DOES NOT REPLACE THE FILES.
        Author ruling, and it is what drops this from the most
        expensive judgement in the plan to a routine one. The record
        captures WHAT EACH SPIKE ESTABLISHED and the commit the files
        were removed at. It does not attempt to carry the method
        across in enough detail to reconstruct them, because the files
        are reconstructible -- git has them, and the record says so
        and says where. An omission is therefore recoverable, and a
        reader who needs the technique has a path to it.
        This is the difference between a summary that must be complete
        because its source is gone and a pointer that must be accurate
        because its source is not. The second is a much easier thing
        to get right, and it is all that is needed here.
        EXTRACT FIRST, THEN REMOVE, IN SEPARATE COMMITS anyway. The
        cost is one commit boundary and it keeps the record checkable
        against the files while they are still in the working tree.

DEC-D8  THE WORK SPLITS INTO TWO THREADS AND THE BOUNDARY IS THE
        READ-ONLY RULE. Author ruling. Everything that READS drill's
        files is DRILL-IMPL-002; everything that WRITES llm_playbook
        files is PLAYBOOK-DESIGN-005. That is not an arbitrary cut: it
        is ADR-004 and precedence.md's read-only-checkout rule, which
        already forbids a drill thread from editing the playbook,
        promoted from a constraint into the thing that defines the two
        threads. The superseded draft's C-22 and C-23 straddled it and
        that is why they were wrong.
        PLAYBOOK-DESIGN-005 RUNS FIRST. Ten of its eleven items are
        fully specified by this thread and depend on nothing drill has
        yet to discover; only the workflow-contract residue depends on
        drill, and it arrives as a supplementary handoff at
        DRILL-IMPL-002's close. Running it first buys two things that
        running it second does not: DRILL-IMPL-002 renders ONCE at
        C-101 against sources that are already final, which removes
        A-1's entire risk, and llm-thread-protocol.md can be DELETED
        at C-118c rather than parked at status: outdated, because its
        residue is already upstream by then.
        ORDER: PLAYBOOK-DESIGN-005 -> DRILL-IMPL-002 -> the residue
        supplement. ADR-016's tripwire makes parallel a non-option
        regardless: one thread at a time is load-bearing for the
        kickoff-only render hash check, and two threads editing
        style-contract.md and a render built from it is exactly the
        case it forbids.

--------------------------------------------------------------------------
OPTIONS -- THE ADR NAMESPACE (F-06)
--------------------------------------------------------------------------

Ranked, scored out of ten, one recommendation.

  9  A. BARE MEANS LOCAL; THE FOREIGN NAMESPACE IS PREFIXED.
        Written as a rule: a bare ADR-NNN in a drill document is
        drill's; a playbook decision is cited PLAYBOOK-ADR-NNN. Zero
        renumbering, one rewritten citation in the whole tree (F-07),
        and it is the convention PROJECT.md line 62 already reaches
        for by hand. It makes the verify check pass -- provably, see
        F-07 -- and it generalizes: the next consumer project gets the
        same rule for free. Costs: it is asymmetric, so a playbook
        document citing drill would have to say DRILL-ADR-NNN, which
        no playbook document currently does.

  7  B. PREFIX FOREIGN CITATIONS BY HABIT, WITH NO WRITTEN RULE.
        What PROJECT.md does today. Same churn as A, which is almost
        none. But an unwritten convention is what N4 exists to warn
        about -- the next author imitates whichever neighbour they saw
        last -- and it leaves the verify check unable to distinguish
        the namespaces, so the check stays broken and gets silenced
        rather than fixed.

  6  C. PREFIX BOTH NAMESPACES SYMMETRICALLY: DRILL-ADR-NNN and
        PLAYBOOK-ADR-NNN, everywhere.
        Grammatically the cleanest: naming.md already namespaces
        refinement ids by project (RF-DRILL-NNN, RF-PLAYBOOK-NNN) and
        thread ids by project, so this is the same shape applied to
        the third id family. Any tool can parse it. Costs: several
        hundred occurrences across a 1700-line decisions.md and every
        document that cites one, done by pattern substitution, which
        is precisely what S30 and the earlier plan's own rename
        warning forbid. Deliverable later as its own thread if the
        symmetry proves worth it; not worth bundling into this one.

  2  D. DO NOTHING; RELY ON CONTEXT.
        The status quo. It has already produced one ambiguous citation
        in a live plan document (the superseded plan's ADR-024) that
        could only be resolved by fetching the playbook's decision
        record. Cheap only until it is not.

  1  E. RENUMBER ONE SIDE TO REMOVE THE OVERLAP.
        Violates N3 outright -- ids are stable forever and never
        reused -- and breaks every reference in both repositories to
        buy a property A gets for one citation's worth of work.

  RECOMMENDATION: A. It is B made explicit, which is the difference
  between a convention and a habit, and it is the only option that
  makes the verify check correct rather than tolerated. C stays
  available: A is forward-compatible with C, because every citation A
  rewrites is one C would also rewrite.

--------------------------------------------------------------------------
THE TEN REPLACEMENT FILES
--------------------------------------------------------------------------

plan/consolidation-by-hand-procedure.md Step 2 lists eleven; the eleventh is archive/README.md
and R-01 removes it. The ten:

  1  STATUS.md                    rewritten, 252 -> ~198 lines
  2  decisions.md                 7 section headings + ADR block +
                                  the absorbed adr-index scope note
  3  spec.md                      section 3 becomes a pointer; cedes
                                  ADR-001..009 to decisions.md
  4  roadmap.md                   3 citation fixes
  5  feature-backlog-2026-07.md   pointer block added
  6  design-handoffs-BCDE.md      1 citation fix
  7  consolidation-findings.md    spike-location note
  8  implementation-plan.md       spike-location note
  9  refinements-and-wiring.md    spike-location note
  10 v1-completion-guide.md       spike-location note

  THE FILE CONTENTS WERE NOT DELIVERED. Only this manifest was. Four
  of the ten (7-10) are fully reproducible: plan/consolidation-by-hand-procedure gives the
  inserted paragraph verbatim and it is one paragraph per file. Five
  more (2-6) are mechanically re-derivable from the tree -- headings,
  pointers and citation fixes are all checkable against what they
  point at. ONE is not: the STATUS.md rewrite is authored prose, and
  reproducing it means rewriting it rather than applying it.
  Consequence for C-104: it is a rewrite by this thread, delivered
  whole, and the earlier plan's claim that the series was "already
  written, verified to apply cleanly" does not hold for it.

--------------------------------------------------------------------------
ADVERSARIAL PASS
--------------------------------------------------------------------------

A-1  THE RE-RENDER IS A CROSS-REPOSITORY COMMIT AND WILL NOT BISECT
     ALONE. C-101 rewrites CONTEXT.md, CLAUDE.md and AGENTS.md from
     playbook sources at a specific playbook sha. If the playbook sha
     is not recorded in the stamp correctly, every later verification
     of the render is worthless and the failure is silent -- which is
     the exact failure the content hash exists to expose (render.md).
     Pin the sha before C-101, not during it.

A-2  RETIRING archive/ REMOVES THE SIGNAL BEFORE THE REPLACEMENT
     EXISTS. Under the old plan a document's supersession was visible
     from its path. Under DEC-9 it is visible only from frontmatter.
     Between C-104 and C-114 there is a window where the retired
     documents are neither in an archive nor carrying a status field,
     and they look live. Mitigation: C-114 sets status on thirteen of
     them in ONE commit, and C-113d sets the fourteenth,
     and lands before any thread other than this one reads the tree.
     Do not spread it across the rename commits.

A-3  EVERY RENAME BREAKS INBOUND REFERENCES AND THE FIX MUST BE IN THE
     SAME COMMIT. F-08 is the sweep that makes this affordable; it was
     run before any rename was proposed. A commit that leaves a
     dangling pointer is not independently valid and the series stops
     bisecting.

A-4  THE SM-2 CLUSTER IS NOT FIXED BY FILING IT. design/sm2-and-
     adaptive-selection.md, plan/sm2-and-adaptive-selection.md,
     plan/scheduler-observability-wiring.md and plan/v1-completion-
     route.md declare their own internal conflict order and are
     coherent only read together. Directories and a type field improve
     navigability and change nothing about that. Carried forward from
     the superseded plan deliberately unresolved; it needs its own
     pass and it is named in OUT OF SCOPE so it is not half-done here.

A-5  TWO FILES WILL SHARE A SUBJECT AND THAT IS CORRECT.
     design/sm2-and-adaptive-selection.md and
     plan/sm2-and-adaptive-selection.md have the same name in
     different directories. DEC-1 says the frontmatter carries the
     classification and the directory is shelving -- which is exactly
     the case where two files may legitimately share a name. But
     DEC-1 also says the path does not survive transport: pasted into
     a chat, these two arrive as two documents with one name and only
     the type field to tell them apart. That is the designed behaviour
     and it is uncomfortable. Flagged, not changed.

A-6  THE WORKFLOW-CONTRACT DIFF MAY CORRECTLY PRODUCE NOTHING. Eight
     of the eleven carriers are undiffed and at least four are known
     to diverge. The handoff is explicit: if the residue is empty, no
     new playbook text is written and all eleven are released anyway,
     and that is a success. The failure mode is authoring from drill's
     copies to have something to show. Diff first, and record the
     residue even when it is empty.

A-7  A REFINEMENT ENTRY IS NOT A HABIT. The playbook thread recorded
     RF-PLAYBOOK-008 for a script that edited half its files and
     committed anyway, then repeated the same failure at the next
     commit, by the same author. Anything scripted in C-114
     (thirteen files, one field each) asserts every anchor before the
     first write, and the commit is chained to the script's exit
     status.

A-8  C-103 MOVES ADR TEXT BETWEEN TWO FILES THAT BOTH DEFINE ADRs.
     spec.md defines ADR-001..009 under `### ADR-NNN:` headings;
     decisions.md defines the rest under bare `ADR-NNN:` lines. The
     cession must normalise to one form or the verify check needs
     both, and the check as written below needs both. Cheaper to
     accept both forms in the check than to reflow decisions.md.

A-9  DELETING adr-index.md MAKES FIVE INBOUND REFERENCES DANGLE.
     F-08 counts five. The handoff says delete it rather than repair
     it, "unless something now depends on it". Five prose mentions are
     not a dependency, but they are five edits, and they belong in
     C-102 with the deletion.

--------------------------------------------------------------------------
TIERS
--------------------------------------------------------------------------

Every operation below is classified by the smallest model that can do it
correctly without supervision. The classification is about the DECISION
CONTENT of the operation, not its size: a two-hundred-line mechanical
substitution is haiku, and a one-line ruling that binds every future
reader is not.

  HAIKU   Fully determined. Nothing has to be decided, because this
          plan or the source file already decided it. Input,
          transformation and output are all named. A reviewer checks it
          by exact match or by running a command.

  SONNET  Bounded judgement against a written rule. The file must be
          read and the rule applied, but there is one defensible answer
          and a reviewer can check it against the rule that produced
          it. Classifying a document's type from a fixed vocabulary,
          writing a scope line from what a document actually says,
          fixing references after a rename while checking prose
          context (S30).

  OPUS    Synthesis across documents, or resolution of a conflict, or
          prose that will bind later readers. More than one defensible
          answer exists and the choice has to be argued. A reviewer
          checks the argument, not the output.

  FABLE   The answer is not determined by anything in the corpus, the
          cost of getting it wrong is high, and the failure would be
          invisible. Reserved. In this plan it appears exactly once,
          and the reason it appears is worth reading.

THE DECOMPOSITION RULE, AND WHY THE SERIES ENDS UP FLAT

An opus operation is usually a hard judgement welded to a pile of
mechanical work. Split them and the mechanical part drops two tiers. So
every opus operation below is decomposed into:

  an INVENTORY   (sonnet) -- enumerate the material into a table, one
                  row per thing that needs a decision, with the
                  evidence for each row already gathered
  a RULING       (opus) -- decide each row
  an APPLICATION (sonnet or haiku) -- write the result from the ruled
                  table

The ruling is what cannot be pushed down. So it is pushed OUT: the four
rulings are lifted out of the commit series entirely, as pre-work items
P-1 to P-4, produced before the series runs and reviewed as decisions
rather than as diffs. With those four out, EVERY COMMIT IN THE SERIES IS
HAIKU OR SONNET. That is the point of the exercise: the expensive
thinking happens once, in artifacts that can be argued with, and the
execution thread never has to make a call it cannot check against
something written down.

PRE-WORK -- THE FOUR RULINGS, OUTSIDE THE SERIES

  P-1  OPUS   STATUS.md live-versus-historical ruling. Input: the
              inventory from C-104a -- every factual claim in the
              current 252-line file, with its line, and whether the
              tree still supports it. Output: one disposition per row.
              Feeds C-104c. Not fable: the old file survives in git and
              a wrong call surfaces the next time anyone reads STATUS.

  P-2  RETIRED. It was the spike synthesis, and it was the one fable
              item in this plan, for a reason that no longer holds:
              the record was going to have to be complete because its
              source was being destroyed. DEC-D7 now makes the record
              a POINTER at material git still holds, so an omission is
              recoverable and the judgement collapses to sonnet. It is
              folded into C-111b. The id is not reused (N3), and this
              entry stays so a reader meeting a reference to P-2
              knows it was retired rather than forgotten.

  P-3  OPUS   g1-findings F1-F14 triage. Input: the inventory from
              C-113a -- per finding, what it claims, what it cites, and
              whether the cited thing still holds. Output: live,
              discharged or falsified, plus the RF-DRILL entry text for
              the live ones. Feeds C-113c. Not fable: g1-findings.md
              survives at status: superseded, so nothing is lost.

  P-4  OPUS   Workflow-contract residue ruling. Input: the clause
              coverage map from C-115c. Output: for each uncovered
              clause, new playbook text or already-implied. Feeds
              C-115d. Not fable: the eleven carriers survive, and an
              empty residue is an explicitly correct outcome (A-6).

--------------------------------------------------------------------------
COMMIT SEQUENCE -- TOPOLOGICALLY SORTED
--------------------------------------------------------------------------

Ids are C-101 onward: a fresh space that does not collide with drill's
landed C-001..C-019b or with the superseded draft's C-01..C-23. The
mapping from the draft's ids is at the end of this section; nothing has
landed, so nothing is being renumbered in the sense naming.md forbids.

One concern per commit. Each parses, runs, and bisects. Tier shown per
operation; where a commit lists two tiers, the operations are separable
but the COMMIT is not, because splitting it would leave a dangling
reference (A-3).

PHASE 0 -- AUTHORITY. Nothing below is done under a stale render.

  C-101  RE-RENDER.
         a  SONNET  Compose the manifest: every layers.md item id,
                    every style-contract clause id, every PROJECT.md
                    rule, with the chain-1 winner marked at each
                    conflict (precedence.md: instance wins, full
                    stop). Checkable against the two source files.
         b  SONNET  Write the body from the manifest, condensing per
                    render.md -- emit each item's imperative, keep its
                    id, drop the because-clauses. Never merge two
                    items; never drop an imperative.
         c  HAIKU   Prepend lines 1-2, compute the stamp
                    (`tail -n +3 CONTEXT.md | sha1sum | cut -c1-8`),
                    copy verbatim to CLAUDE.md and AGENTS.md. Both are
                    CREATED, not refreshed (F-16).
         Depends on: the pinned playbook sha, which is author-owned.

PHASE 1 -- CONTENT, UNDER THE OLD SHAPE. No file moves yet, so every
reference in the tree still resolves and these commits are readable as
content changes rather than as churn.

  C-102  ADR SCOPE NOTE ABSORBED; adr-index.md DELETED.
         a  SONNET  Write the scope note into decisions.md from what
                    adr-index.md actually says.
         b  HAIKU   git rm adr-index.md; fix the five inbound
                    references (F-08 located them).

  C-103  spec.md CEDES ADR-001..009 TO decisions.md.
         a  HAIKU   Move the nine blocks verbatim; normalise the
                    heading form from `### ADR-NNN:` to `ADR-NNN:` so
                    one definition form exists (A-8).
         b  SONNET  Write spec.md section 3 as a pointer.

  C-104  STATUS.md COLLAPSED TO ONE CURRENT BASELINE.
         a  SONNET  Inventory: every factual claim, its line, and
                    whether the tree still supports it. ~30 rows.
         -  P-1     the ruling, outside the series
         c  SONNET  Write the new file from the ruled inventory.
         d  HAIKU   Assert the four still-open items from
                    3-to-E10-cutover.md are present; run
                    `grep -nE '[0-9]{3} green' STATUS.md` and read the
                    hits. 668 stands; its composition is out of scope.

  C-105  decisions.md: THE SEVEN MISSING SECTION HEADINGS.
         a  SONNET  Identify them. plan/consolidation-by-hand-procedure says seven and does
                    not say which; they are found structurally, by
                    where a section begins with no heading.
         b  HAIKU   Insert.

  C-106  feature-backlog POINTERS TO DECIDED-BUT-UNBUILT FEATURES.
         -  SONNET  Cross-reference decisions.md against the backlog.

PHASE 2 -- SHAPE. Directories, then moves. Every rename fixes its own
inbound references in the same commit.

  C-107  CREATE design/ plan/ handoff/ close/. No archive/ (DEC-9).
         -  HAIKU   close/ stays empty and git will not track it; the
                    plan records that so its absence is not later read
                    as an omission.

  C-108  design/ MOVES AND RENAMES.
         a  HAIKU   git mv, five files, targets named in MOVES below.
         b  SONNET  Reference sweep and fix. Not blind substitution:
                    check each token in prose, in commit-message
                    fragments and in output format strings before
                    replacing it (S30).

  C-109  plan/ MOVES AND RENAMES, plus the two exits from llm/.
         a  HAIKU   git mv, seven files to plan/, targets in MOVES;
                    study-curriculum-and-conventions.md to drill/docs/
                    (DEC-D3); handoffs/DRILL-DESIGN-consolidation.md to
                    handoff/, name unchanged (pre-grammar, F-15).
         b  SONNET  Reference sweep and fix, including STATUS.md's
                    pointer at the study-curriculum file.
         c  SONNET  DRILL-DESIGN-consolidation.md: status: superseded,
                    successor named in the supersedes field.

  C-110  refinements-and-wiring.md -> plan/scheduler-observability-wiring.md
         a  HAIKU   git mv.
         b  SONNET  Reference sweep and fix (five inbound).
         ITS OWN COMMIT. The rename is the point, not a side effect:
         this file has nothing to do with refinements in the
         RF-DRILL-NNN sense, and C-113 creates a real refinements.md.
         Two files whose names both say "refinements" meaning different
         things is the wrong-document trap that started all of this.

PHASE 3 -- SPIKES. After the renames, so the four citations are edited
at their final paths and not twice.

  C-111  RECORD WHAT THE SPIKES ESTABLISHED.
         a  SONNET  Per-spike inventory: what each asserts, what it
                    imports, what it prints, what its exit condition
                    is. Five files, one at a time, mechanical reading.
         b  SONNET  Write design/sm2-port-and-authoring-transform.md:
                    one entry per spike -- the claim it established,
                    the shape of the evidence, and the path the files
                    lived at. It is a POINTER, not a replacement
                    (DEC-D7); it states that the files are recoverable
                    from git and names the commit that removes them.
                    That commit is C-112, so the reference is written
                    in C-112a once its sha exists -- C-111 leaves the
                    slot and C-112 fills it.
         NOTHING IS DELETED IN THIS COMMIT (DEC-D7).

  C-112  RETIRE THE SPIKE FILES.
         a  SONNET  Repoint the four spike-location citations at the
                    new document. They currently cite by bare
                    filename; they will cite a document and a section.
         b  HAIKU   git rm the eight files; the directory goes with
                    them. Fill C-111b's recovery slot with this
                    commit's own reference -- it is the last commit at
                    which the files exist, which is the only fact a
                    later reader needs.
         Runs only after C-111 has been reviewed against its source.

PHASE 4 -- RECORDS.

  C-113  CREATE refinements.md; MIGRATE g1-findings.
         a  SONNET  Inventory F1-F14: claim, citation, does the cited
                    thing still hold.
         -  P-3     the triage, outside the series
         c  SONNET  Write RF-DRILL-001.. from the ruled inventory.
         d  HAIKU   ADR-020 -> PLAYBOOK-ADR-020, one occurrence
                    (DEC-D1). g1-findings.md status: superseded;
                    refinements.md names it in supersedes (DEC-D2).

  C-114  status: outdated ON THE THIRTEEN RETIRED DOCUMENTS, IN PLACE.
         a  SONNET  Build the table: file, date from content, type,
                    one-line scope. Thirteen rows.
         b  HAIKU   Apply it. If scripted: assert EVERY anchor before
                    the first write, and chain the commit to the
                    script's exit status (A-7, RF-PLAYBOOK-008).
         THIRTEEN, NOT FOURTEEN. g1-findings.md is the fourteenth on
         plan/consolidation-by-hand-procedure's list and it takes status: superseded at
         C-113d, not outdated. It has a successor.

  C-115  THE WORKFLOW-CONTRACT DIFF.
         a  HAIKU   Extract the WORKFLOW CONTRACT / DELIVERY
                    DISCIPLINE section from all eleven carriers.
         b  HAIKU   Pairwise diff the eleven; emit a divergence report.
                    Four are known to diverge and eight are undiffed.
         c  SONNET  Map 3-to-E10-cutover's version -- the most recent,
                    and the only copy whose heading admits revision --
                    clause by clause against commit-planning.md,
                    clone-and-verify.md, runtime-verification.md and
                    precedence.md. Mark each clause covered or not.
         -  P-4     the residue ruling, outside the series
         d  SONNET  Record the residue, INCLUDING WHEN IT IS EMPTY. An
                    empty residue means no new playbook text is written
                    and all eleven are released anyway. That is the
                    success case (A-6). The failure mode is authoring
                    from drill's copies to have something to show.

  C-116  THE ELEVEN HANDOFFS -> handoff/.
         a  HAIKU   Assert the four 3-to-E10-cutover open items are in
                    the STATUS.md written at C-104. Gate: if they are
                    not, stop.
         b  HAIKU   git mv, eleven files, NAMES UNCHANGED. They predate
                    the thread-id grammar and no ids exist for them;
                    inventing ids to make them conformant fabricates
                    history.
         c  SONNET  Frontmatter on each: date, type: handoff, scope,
                    status: outdated, and a note recording pre-grammar
                    nonconformance.
         thread-N-vocab-plan.md is NOT among these. It went to plan/ at
         C-109; it is a plan carrying a contract copy, not a handoff.

PHASE 5 -- CLASSIFICATION. Last, because nothing is classified until it
has stopped moving.

  C-117  FRONTMATTER ON design/, plan/ AND drill/docs/.
         -  SONNET  Fourteen documents. Write scope from what each
                    document SAYS, not from its title. Where the real
                    scope contradicts the title, state the real one and
                    say so in the commit message -- that is a finding.

  C-118  FRONTMATTER ON THE ROOT INSTANCE DOCUMENTS.
         a  HAIKU   Types, which this plan already fixed:
                      decisions.md            decisions
                      refinements.md          refinements
                      CODING_CONVENTIONS.md   instance-rules
                      spec.md, roadmap.md     design
                      knowledge-capture.md    design
                      llm-thread-protocol.md  toolkit-rules
                      thread-launch-kit.md    kickoff
         b  SONNET  Scope lines, same rule as C-117.
         c  HAIKU   git rm llm-thread-protocol.md. It is DELETED, not
                    parked: PLAYBOOK-DESIGN-005 ran first and placed
                    all seven residue items, R1-R10 and the role
                    record upstream, so nothing it holds is unique any
                    more (DEC-D8). GATE: if PLAYBOOK-DESIGN-005 did
                    not land, this operation becomes SONNET instead --
                    status: outdated plus a note naming what is still
                    only here -- and the deletion waits.
         SENTINELS EXEMPT: STATUS.md, PROJECT.md, CONTEXT.md,
         CLAUDE.md, AGENTS.md. Their name is their role, and
         CONTEXT.md lines 1-2 are specified byte-for-byte by render.md.

  C-119  PROJECT.md.
         a  SONNET  DEC-D1's namespace rule as a drill instance rule;
                    DEC-D6's PROJ code recorded.
         b  HAIKU   S1..S25 -> S1..S30 (F-04). D1..D3 is unchanged.

PHASE 6 -- SWEEP.

  C-123  ASCII REPAIR.
         -  HAIKU   Two arrows in 260626_roadmap-rec-after-D2.md, one
                    curly apostrophe in decisions.md (F-10). Last,
                    because C-102, C-103 and C-105 all edit
                    decisions.md and a sweep before them can be undone
                    by them.

PHASE 7 -- THE HANDBACK. No commit in this thread writes a byte in
llm_playbook (DEC-D8). PLAYBOOK-DESIGN-005 already landed the ten items
this thread specified; C-124 sends it the eleventh.

  C-124  THE RESIDUE SUPPLEMENT TO PLAYBOOK-DESIGN-005.
         -  SONNET  A handoff carrying C-115's output: the clause
                    coverage map, the residue, and P-4's ruling on
                    each uncovered clause. Nothing else -- everything
                    else in the register was known before this thread
                    opened and went out with the kickoff.
                    Filename under DEC-D6, cross-project so the TO
                    slot carries the project code:
                      handoff/DRILL-IMPL-002-to-PLAYBOOK-DESIGN-005_
                        workflow-contract-residue.md
                    If the residue is empty, this handoff still ships
                    and says so. An empty residue is the success case
                    (A-6) and an unsent handoff is indistinguishable
                    from a forgotten one, which is the condition R12
                    exists to remove.

  RETIRED FROM THIS PLAN, IDS NOT REUSED (N3):
    C-120  R1-R10 into protocol/thread-protocol.md
    C-121  the two ADRs closing the REVIEW-versus-CAPTURE OPEN
    C-122  the upstream register
  All three wrote playbook files. They are PLAYBOOK-DESIGN-005's, they
  are specified in the kickoff this thread produces, and they run
  BEFORE this thread. The ids stay vacant here so a reader meeting a
  reference to C-120 finds out where it went.

  Then VERIFY, below. All seven checks are HAIKU.

TIER TOTALS, AFTER DECOMPOSITION AND THE SPLIT

  In the series:  21 commits, 42 operations.
                  HAIKU  17    SONNET  25    OPUS 0    FABLE 0
  Outside it:     3 rulings.
                  OPUS 3 (P-1, P-3, P-4)     FABLE 0

  No opus or fable operation remains anywhere in this thread's
  execution. Every commit is checkable against something already
  written down, and the three rulings are reviewed as decisions rather
  than as diffs.

  FABLE went to zero for a reason worth keeping. P-2 was fable because
  a record was going to have to be complete -- its source was being
  destroyed. Pointing the record at git instead of replacing the files
  did not make the work smaller; it made an omission RECOVERABLE, and
  recoverability is most of what separates the top tier from the one
  below it. When something looks fable, the first question is whether
  the irreversibility is real or self-inflicted.

MAPPING FROM THE SUPERSEDED DRAFT'S IDS

  C-01 -> C-101      C-09 -> C-107      C-17 -> C-118
  C-02 -> C-102      C-10 -> C-108      C-18 -> C-120
  C-03 -> C-103      C-11 -> C-109      C-19 -> C-121
  C-04 -> C-104      C-12 -> C-110      C-20 -> C-115
  C-05 -> C-105      C-13 -> C-114      C-21 -> C-119
  C-06 -> C-106      C-14 -> C-113      C-22 -> C-122
  C-07 -> C-111 and C-112, and its meaning changed (DEC-D7)
  C-08 -> C-123, moved to last            C-23 -> dropped (DEC-D8)
  C-15 -> C-116      C-16 -> C-117
  C-18, C-19 and C-22 left this plan entirely with the thread split
  and are PLAYBOOK-DESIGN-005's; C-124 is new and is the handback.

  Three orderings changed and each has a reason. The ASCII sweep moved
  to last so the three commits that edit decisions.md cannot undo it.
  The spike work moved after the renames so the four citations are
  edited once, at their final paths. The workflow-contract diff moved
  ahead of the handoff move so the eleven carriers are read where the
  documents that cite them still point.

DEPENDENCY EDGES, STATED SO THE SORT CAN BE CHECKED

  C-101  -> everything                 (stale-render rule)
  C-104  -> C-116a                     (the gate reads STATUS.md)
  C-107  -> C-108, C-109, C-110, C-116 (directories before moves)
  C-108, C-109, C-110 -> C-111, C-112  (citations edited once, at
                                        their final paths)
  C-111  -> C-112                      (extract before delete, DEC-D7)
  C-108, C-109, C-110 -> C-117         (frontmatter after the move)
  C-113  -> C-122                      (the register cites RF-DRILL
                                        ids that C-113 assigns)
  C-115  -> C-116                      (read the eleven where the
                                        citing documents still point)
  C-115  -> C-124                      (the handback carries C-115's
                                        residue and nothing else)
  C-102, C-103, C-105 -> C-123         (sweep after the edits)

  ONE EDGE POINTS OUT OF THIS THREAD:
  PLAYBOOK-DESIGN-005 -> C-101         (render once, against final
                                        sources -- DEC-D8)
  and one points back in:
  C-124 -> PLAYBOOK-DESIGN-005's residue commit

  No cycles. Phases are a reading aid; the edges are the constraint.

--------------------------------------------------------------------------
MOVES, IN FULL
--------------------------------------------------------------------------

  design/ (C-108)
    consolidation-findings.md      -> design/sm2-and-adaptive-selection.md
    design-A-quick-consolidation.md-> design/stats-depth-and-jsonl-export.md
    design-handoffs-BCDE.md        -> design/design-thread-kits-b-to-e.md
    vocab-language-futures.md      -> design/vocabulary-and-language-features.md
    naming-options-2026-07.md      -> design/bank-and-category-naming.md
  naming-options stays in drill and is not retired:
  PLAYBOOK-ADR-024 records it as convention-adoption evidence,
  design-complete and parked pending usage data.

  plan/ (C-109)
    implementation-plan.md         -> plan/sm2-and-adaptive-selection.md
    v1-completion-guide.md         -> plan/v1-completion-route.md
    use-period-plan-2026-07.md     -> plan/use-period-feedback.md
    feature-backlog-2026-07.md     -> plan/feature-backlog.md
    thread-N-vocab-plan.md         -> plan/vocabulary-hints-and-timing.md
    usage-and-study-guide.md       -> plan/daily-use-and-data-collection.md
    authoring-guide-2026-07.md     -> plan/question-authoring.md
    refinements-and-wiring.md      -> plan/scheduler-observability-wiring.md
                                      (C-110, its own commit)

  out of llm/ (C-109)
    study-curriculum-and-conventions.md -> drill/docs/
    handoffs/DRILL-DESIGN-consolidation.md -> handoff/, name unchanged

  new (C-111)
    design/sm2-port-and-authoring-transform.md

  deleted
    adr-index.md                        (C-102)
    llm/spike/ -- all eight files       (C-112)

  design/sm2-and-adaptive-selection.md and
  plan/sm2-and-adaptive-selection.md share a name deliberately. The type
  field and the directory distinguish them, which is what DEC-1 says
  they are for -- and A-5 records why that is still uncomfortable.

--------------------------------------------------------------------------
NOT MOVED, AND WHY
--------------------------------------------------------------------------

  CONTEXT.md, CLAUDE.md, AGENTS.md, PROJECT.md, STATUS.md,
  decisions.md, refinements.md, CODING_CONVENTIONS.md, spec.md,
  roadmap.md, knowledge-capture.md all stay at drill/llm/. Sentinels
  do not move; spec, roadmap and decisions are cited by path from
  dozens of places.

  llm-thread-protocol.md stays, at status: outdated, with a note
  naming the seven residue items it still uniquely holds (F-18). It is
  deleted by whoever lands those upstream, not here (DEC-D8). C-118c
  writes the status and the note; C-122 hands the evidence over.

  thread-launch-kit.md stays, type: kickoff. It shares a subject with
  protocol/kickoff.md and the handoff says to resolve it against the
  playbook rather than file it under design/ as though settled. That
  resolution is not in this thread's scope.

--------------------------------------------------------------------------
VERIFY AT THE END
--------------------------------------------------------------------------

Run from drill/llm.

  # 1. No ADR id is referenced but undefined. Accepts both definition
  # forms (A-8) and excludes the foreign namespace (DEC-D1).
  { grep -ohE '^#* *ADR-[0-9]{3}' decisions.md
    grep -ohE '^#+ *ADR-[0-9]{3}' spec.md
  } | grep -oE 'ADR-[0-9]{3}' | sort -u > /tmp/adr_defined.txt
  grep -rhoE '(PLAYBOOK-)?ADR-[0-9]{3}' --include='*.md' . \
    | grep -v '^PLAYBOOK-' | sort -u > /tmp/adr_referenced.txt
  comm -13 /tmp/adr_defined.txt /tmp/adr_referenced.txt
  # expect: empty. Verified achievable at plan time by simulation (F-07).

  # 2. Every referenced *.md filename exists somewhere in the tree.
  grep -rhoE '[A-Za-z0-9_-]+\.md' --include='*.md' . | sort -u \
    | while read -r REFERENCED_MARKDOWN_NAME; do
        find . .. -name "$REFERENCED_MARKDOWN_NAME" -print -quit | grep -q . \
          || echo "DANGLING: $REFERENCED_MARKDOWN_NAME"
      done
  # expect: empty. The `..` is because study-curriculum moved to
  # drill/docs/. The spikes are deleted, not moved (DEC-D7), so no
  # spike filename should appear in prose after C-112.

  # 3. Every non-sentinel document carries frontmatter.
  find . -name '*.md' \
    ! -name CONTEXT.md ! -name CLAUDE.md ! -name AGENTS.md \
    ! -name PROJECT.md ! -name STATUS.md \
    | while read -r DOCUMENT_PATH; do
        head -5 "$DOCUMENT_PATH" | grep -q '^date:' \
          || echo "NO FRONTMATTER: $DOCUMENT_PATH"
      done
  # expect: empty. head -5 and not head -1, because these files open
  # with a title and an underline before the block.

  # 4. Every document declares whether it binds.
  find . -name '*.md' ! -name CONTEXT.md ! -name CLAUDE.md \
    ! -name AGENTS.md ! -name PROJECT.md ! -name STATUS.md \
    | while read -r DOCUMENT_PATH; do
        grep -qE '^status: (current|superseded|outdated)$' "$DOCUMENT_PATH" \
          || echo "NO STATUS: $DOCUMENT_PATH"
      done
  # expect: empty. The three values are exhaustive; historical is not
  # one of them (R-02).

  # 5. ASCII only (F-10).
  find . -type f | while read -r ANY_FILE_PATH; do
    LC_ALL=C grep -q "[^ -~$(printf '\t')]" "$ANY_FILE_PATH" \
      && echo "NON-ASCII: $ANY_FILE_PATH"
  done
  # expect: empty.

  # 6. One current baseline in STATUS.md.
  grep -nE '[0-9]{3} green' STATUS.md
  # Currently 7 hits. After C-104, exactly one figure is claimed as
  # current (668) and any others are explicitly prose about past
  # drift. Read the hits; do not count them.

  # 7. archive/ does not exist, anywhere.
  find . -type d -name archive
  # expect: empty (DEC-9).

--------------------------------------------------------------------------
OUT OF SCOPE -- named, and staying out
--------------------------------------------------------------------------

  The 668 test-suite composition. Author ruling: not relevant at this
    stage. STATUS.md records the total and says the split is
    unrecorded, which is the honest state.
  The SM-2 cluster's internal conflict order (A-4). Filing improves
    navigability and does not touch it. Its own pass.
  Generalizing check.sh to reach drill (F-09). Playbook work.
  Repairing naming.md's close-artifact contradiction (F-11), the
    parent-name grep (F-13), and llm_playbook's missing STATUS.md.
    All playbook-side; recorded as refinements under DEC-D5.
  Symmetric ADR namespacing (option C). Available later; A is
    forward-compatible with it.
  Splitting CODING_CONVENTIONS.md, or reconciling it against the
    render (g1-findings F4). It interacts with ADR-030's account of a
    thread that followed it instead of the render, and that is a
    question about whether the render binds, not about filing.
  Resolving thread-launch-kit.md against protocol/kickoff.md.

--------------------------------------------------------------------------
OPEN -- decide before the commits they gate
--------------------------------------------------------------------------

CLOSED SINCE THE FIRST DRAFT, recorded so the reasoning is not lost:
  the playbook sha for the re-render is author-owned and pinned at
  thread time; the cross-project handoff form is DEC-D6; the spikes
  are retired rather than relocated, which also disposes of their
  absolute sandbox paths and their dependency on the sm2 module
  (DEC-D7); llm-thread-protocol.md's residue goes upstream as a
  supplementary thread and drill's job is the register (DEC-D8).

OPEN-1  (gates P-2, and therefore C-111) How much of the spike
        material is worth carrying? DEC-D7 says findings, principles,
        tactics and strategies. Findings are the easy part -- the
        spikes print them. Principles and tactics are a judgement
        about what generalises, and the honest range runs from a page
        to a paragraph. P-2 is the one fable item in this plan
        precisely because that judgement is made once, against files
        that will not exist afterwards. Worth an explicit steer before
        the extraction runs rather than a correction after it.

OPEN-2  (gates nothing in this series) Who runs the supplementary
        upstream thread, and when? C-122 produces the register
        regardless and drill closes with it delivered. The register is
        a handoff, so it needs a TO slot -- and under DEC-D6 that slot
        reads PLAYBOOK-DESIGN or PLAYBOOK-IMPL depending on the
        answer. F-18's items 1 to 6 are rule text, which is design
        work; item 7 and the DEC-D1/DEC-D6 proposals are too. The lean
        is DESIGN, but naming the file requires the ruling.
