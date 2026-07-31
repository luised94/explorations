THREAD DRILL-IMPL-002_llm-corpus-consolidation -- CLOSE
=======================================================
date:  2026-07
type:  close
from:  DRILL-IMPL-002
scope: the shape half of the llm-corpus consolidation. What landed,
       what it cost, what was deferred, and what was rejected.

TERMINAL STATE (R9)

  Shape and subtraction complete. Content, classification and the
  re-render are deferred, not abandoned; each is named below with the
  reason it was not taken here.

  drill/llm baseline -> now

    root .md          38 -> 9
    directories        4 -> 5     (design/ added; handoffs/ was already
                                   handoff/ before the thread opened)
    .md under llm/    54 -> 39
    drill/docs/        0 -> 4

  The nine survivors: CODING_CONVENTIONS.md CONTEXT.md PROJECT.md
  STATUS.md decisions.md knowledge-capture.md roadmap.md spec.md
  thread-launch-kit.md

WHAT LANDED

  Eleven commits, in order.

    1  design/ moves            5 files
    2  plan/ moves              7 files
    3  refinements name freed   1 file, its own commit so the RF-DRILL
                                register can take the name later
    4  docs/ exit               study-curriculum-and-conventions.md
    5  series apparatus         APPLY-BY-HAND.md and SERIES-README.md,
                                the only material with no disposition
                                anywhere in the plan
    6  reference sweep          43 references, 11 files
    7  guides to docs/          question-authoring.md and
                                daily-use-and-data-collection.md
    8  test setup to docs/      setup.md -> docs/test-suite-setup.md
    9  two unconditional        adr-index.md (C-102), and
       deletions                llm-thread-protocol.md (C-118c)
   10  retirement               ten documents removed; git holds them
   11  case sweep               13 citations of pre-thread uppercase
                                filenames that no longer resolved

  Plus the phase0 restore and the phase0 sweep, which exist only
  because of a mistake recorded below.

DISCREPANCIES, AND HOW EACH WAS RESOLVED

  This is the section that does not survive in the diff.

  1. THE PLAN'S BASELINE DID NOT MATCH THE TREE.

     APPLY-BY-HAND's identifier was 4296b13b; the tree hashed to
     942575024c75b999d985c75da6ab0792. The plan expected 50 markdown
     files in 2 directories and found 54 in 4. handoffs/ had already
     been renamed handoff/, plan/ and kickoff/ already existed, and
     the plan document was already at plan/.

     Resolved: read as thread scaffolding, not corruption. Three
     scheduled commits were already satisfied. C-107 (create four
     directories) became a no-op except for design/. C-116b (git mv
     eleven handoffs) was a no-op outright.

  2. THE RESET REMOVED THE STATUS VOCABULARY, WHICH THE PLAN IS BUILT ON.

     protocol.md: no supersedes field, no status vocabulary, no
     append-only requirement. C-114's entire content was setting
     status: outdated on thirteen documents. R-02, DEC-D2, C-109c,
     VERIFY check 4 and half of C-113d went with it.

     This left the retired documents with no way to declare
     retirement: archive/ had been retired earlier on the reasoning
     that frontmatter would carry supersession, and the reset then
     removed the frontmatter. Both mechanisms gone.

     Resolved: deletion, per the reset's own reasoning that git holds
     provenance. Recorded as P-5, a ruling the plan did not contain.

  3. PHASE0.MD WAS DELETED AND SHOULD NOT HAVE BEEN. (thread's own
     mistake, and the expensive one.)

     APPLY-BY-HAND listed phase0.md among the retirement targets.
     Before recommending deletion, this thread checked inbound
     references by grepping the literal token "phase0" and reported
     one hit, from a handoff.

     The references are spelled PHASE0_PLAN.md. The grep was
     case-sensitive and matched none of them. phase0.md is the Phase
     0/1 Execution Plan, and thread-launch-kit.md -- which is in the
     STAYS list -- cites it 29 times, by section, in live Attach:
     lines and prompt blocks.

     Cost: the launch kit was broken in 29 places for the length of
     one commit. Resolved by restoring the file to
     llm/plan/phase-0-1-execution.md, where it belonged all along --
     it is a plan, and its presence on the retirement list was the
     original error. Two extra commits.

     The lesson is narrower than "check references": the check ran,
     and returned a confident wrong answer, because the token in the
     citations was not the token in the filename. A reference check
     keyed on a filename cannot see a citation that spells the file
     differently.

  4. TWO COUNTS REPORTED TO THE AUTHOR WERE WRONG.

     A predicted post-move root count of 27 (actual 22 -- the series
     moves sixteen files, not fourteen). And "twelve" pre-existing
     dangling references, which counted unique document-and-name
     pairs from a scan; the occurrence count is 46. Both were caught
     by running the thing rather than by review.

  5. F-08'S REFERENCE COUNTS WERE HALF THE TRUTH.

     F-08 budgeted 42 occurrences. The real count is 97. F-08
     excluded self-references and predates the plan document landing
     inside the tree it measures.

  6. THE PLAN DOCUMENT BREAKS ITS OWN VERIFY CHECK.

     VERIFY check 1 reports ADR-012, ADR-016 and ADR-020 undefined.
     DEC-D1 states F-07 "identified the complete set: one occurrence,
     ADR-020 in g1-findings.md." The plan moved into the grep scope
     and brought two bare playbook citations with it; ADR-020 occurs
     twice in g1-findings.md, not once.

     Three of the five occurrences are prose ABOUT the namespace
     finding, where mechanical rewriting corrupts the record. Left
     for C-113d, which grows from one edit to a judged set.

  7. VERIFY CHECK 2 CANNOT PASS AS WRITTEN.

     45 of 97 reference occurrences were ruled keep, because they sit
     in three record documents whose old names are the record. Those
     names therefore dangle by construction, permanently. The check
     is only meaningful with those three files excluded.

  8. TWO DOCUMENTS HAD NO DISPOSITION ANYWHERE.

     APPLY-BY-HAND.md and SERIES-README.md -- the delivery apparatus
     of the failed eight-commit series, and the artifact whose
     unreachable sandbox baseline is RF-PLAYBOOK-004's second
     occurrence. F-15 asserts the only undisposed file is
     DRILL-DESIGN-consolidation.md. Both were shelved into plan/ with
     descriptive names.

  9. SETUP.MD WAS RETIRED AND SHOULD HAVE BEEN MOVED.

     Caught by the author, not by this thread. It is a reader-facing
     how-to, same class as the three guides that left llm/ under
     DEC-D3. Now docs/test-suite-setup.md.

DEFERRED -- named, with the reason

  C-101   re-render CONTEXT.md. Needs render.sh stamp run in the real
          repository, and needs the chain-1 granularity question
          settled. The current render is stamped in the pre-reset
          format (it carries a v0.1.0 segment the current render.sh
          does not emit) and asserts that drill has no PROJECT.md
          instance rules, which is false.
  C-103   spec.md cedes ADR-001..009 to decisions.md.
  C-104   the STATUS.md rewrite. The plan's only authored file.
  C-105   seven missing ADR headings in decisions.md.
  C-106   backlog pointers.
  C-111   the spike record as a pointer.
  C-113   refinements.md and the RF-DRILL register. Because it does
          not exist, the RF-DRILL entries this thread produced are
          listed below rather than filed.
  C-117   frontmatter for design/ plan/ docs/ kickoff/ handoff/.
  C-118ab frontmatter for the nine survivors.
  C-119   PROJECT.md: the frontmatter contract and the type
          vocabulary; S1..S25 -> S1..S30.
  C-123   ASCII repair. Scope halved: 260626_roadmap-rec-after-D2.md
          was one of the two non-ASCII files and was retired, so
          decisions.md is the only remaining target.

REJECTED -- distinct from deferred

  C-107   as a commit. plan/ and handoff/ already existed, git will
          not track an empty close/, and design/ is created by its
          first move. There was no commit to make and none was
          manufactured.
  C-114   the status: outdated pass. No such field exists.
  C-116b  the eleven-handoff move. Already satisfied by the tree.
  C-109c  supersession frontmatter on DRILL-DESIGN-consolidation.md.
  History rewriting. Proposed as a way to make the corpus look as
          though it had always been organised. Tested and rejected:
          git does not store renames at all -- git mv and mv+git add
          produce byte-identical trees, and log --follow works either
          way -- so a rewrite buys nothing for the moves, while
          invalidating every SHA cited in ten committed documents.
          42298a27 alone appears nine times and is the entire
          recovery mechanism for the pre-reset playbook.
  CLAUDE.md and AGENTS.md. F-16 rests on render.md R-B, and render.md
          died with the reset; CONTEXT.md's own CONSTRAINT-008 says
          no tooling here reads either file. Recommended dropped;
          confirm at C-101.

RF-DRILL ENTRIES, UNFILED

  refinements.md does not exist yet (C-113 deferred), so these have
  no register to go in. File them when it is created.

  i    A reference check keyed on a filename misses citations that
       spell the file differently. Cost: phase0.md deleted, the
       launch kit broken in 29 places. Check the citing side's
       spelling, not only the file's.
  ii   Verify checks that grep the whole tree must exclude the
       documents whose old names are the record, or they can never
       pass.
  iii  A plan document that moves into the tree it governs enters its
       own verify scope and can break its own checks.
  iv   Reference counts measured before the plan lands in the tree
       undercount by roughly half.

FINDINGS FOR THE PLAYBOOK

  Carried in the handoff, not fixed here. See
  drill/llm/handoff/DRILL-IMPL-002-to-playbook.md.

HANDOFFS PRODUCED

  drill/llm/handoff/DRILL-IMPL-002-to-playbook.md
