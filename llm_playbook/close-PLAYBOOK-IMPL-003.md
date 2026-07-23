CLOSE -- PLAYBOOK-IMPL-003
==========================
date: 2026-07
thread: PLAYBOOK-IMPL-003 (implementation role)
gate: G-1a TRANSPORT/RENDER -- the transport/render half of the split
G-1 early-use gate (ADR-020..023, plan Edit 7).
predecessor: PLAYBOOK-DESIGN-002 (produced ADR-020..029 and the plan
edits; Stage A landed the plan and the ADRs in two commits).
bootstrap SHA: 69ae0609b575b885afb51ffe1c1445eba07b884f

RESULT: G-1a PASSES.
  The corrected transport path was exercised end to end on real
  content: a hand-authored render was committed, packed, unpacked,
  and verified intact with its stamp. G-1 as a whole does NOT close
  until G-1b also passes.

WHAT LANDED (six commits, plan order)
  B2a  T-007 re-land. render.md relocates the primary render target
       to <project>/llm/CONTEXT.md (ADR-020) and places the generated
       CLAUDE.md / AGENTS.md copies beside it.
  B2b  T-007b re-land. scripts/bootstrap.sh deleted, retiring the
       sparse-checkout mechanism (ADR-021, superseding the mechanism
       of ADR-004); README's BOOTSTRAP section rewritten as TRANSPORT.
  B2c  T-015b increment 1. New preferences/transport.md and
       scripts/pack-repo.sh implementing archive-or-paste. NO
       composition: base-plus-overlay is increment 2 (ADR-022
       staging) and was deliberately not started.
  B2d  T-005 re-land (NEW STEP, added mid-thread; see OPEN O1). W1-W8
       workflow ground truth added to layers.md as CONSTRAINT-008..011
       and CONVENTION-008..011 (ADR-025).
  B4   drill/llm/CONTEXT.md authored BY HAND and committed: 198 lines
       against a 250 ceiling, composing all 34 preference items and
       all 25 style clauses plus 3 deviations, each cited by id.
  B5   Gate run and findings -> drill/llm/g1-findings.md.

WHAT WAS VERIFIED
  Committed-read, scratch-only, and idempotence all hold on the real
  render. The pack refuses a render that is not yet committed and
  names the path; it writes only under /tmp and leaves the tree
  clean; two runs at one SHA are byte-identical. The round trip is
  lossless and the STAMP SURVIVES TRANSPORT -- an unpacked render
  recomputes to its stamped content-hash, so a reader can verify what
  they received. A one-character edit to a render body shifts the
  hash, satisfying the T-007 accept criterion. Details and the two
  NOT-TESTED items are in drill/llm/g1-findings.md.

OPEN ITEMS CARRIED FORWARD
  O1. USER-IDENTITY PERSONA ITEMS UNAUTHORED. ADR-025 calls for
      user-identity facts as Persona items in layers.md. No source
      for them exists in the repository, and they are facts about the
      author that must not be invented. B2d therefore landed the W1-W8
      half only. Supply the facts and author them as PERSONA-006
      onward. Until then every render is missing that layer.
  O2. check.sh false-positives on documents that QUOTE the
      upward-path pattern while describing the containment rule
      check.sh enforces (implementation-plan.md and
      consolidation-PLAYBOOK_DESIGN-002.md both trip it). A document
      cannot currently discuss the rule without violating it -- this
      close artifact hit the same trap while writing this entry and
      was reworded to avoid it. Nothing was blocked, since the hook
      is not installed (ADR-028). Fold into the deferred check.sh
      rework.
  O3. render.md should state the stamp ORDERING explicitly: the SHA
      field names the commit that CONTAINS the render, so it cannot
      be known before that commit exists. It is authored as a
      placeholder and filled at commit time; this is safe because the
      content-hash covers the body only. A naive author will
      otherwise try to stamp first and stall.
  O4. drill/llm/CODING_CONVENTIONS.md is now redundant with the
      rendered CONTEXT.md -- the same rules in different words, the
      drift CRITERIA-009 warns against. Retire it or reduce it to a
      pointer at the render.
  O5. drill has no PROJECT.md, so the render emits no instance rules.
      Harmless now; a defect the moment drill acquires an instance
      rule that contradicts a playbook item.
  O6. drill/llm/g1-findings.md is TEMPORARY. It exists only because
      drill has no refinements.md until D-101. When that skeleton
      lands, its entries move there as RF-DRILL-NNN and the file is
      deleted.

WHAT DOES NOT OPEN YET
  T-008 and beyond remain SHUT. The original implementation range
  opens only when G-1a AND G-1b have both passed. G-1b was not
  started in this thread and no work beyond B6 was performed.

NEXT: G-1b REAL THREAD
  Run ONE real thread through the packed context and see whether the
  rendered preferences reach working code. The task is fixed by the
  plan: BITWISE ARITHMETIC from drill's feature-backlog-2026-07.md
  (scored 4.04, Tier 1, described there as the standout -- the
  cheapest new drill with the most teaching). It is a data-row plus
  eval-rule addition that reuses the existing tree machinery; the
  only genuinely new work is display of operands and answers in
  binary or hex, since bitwise drills are pointless in decimal.
  Open design questions recorded in the backlog: operand base display
  (bin/hex/dec), fixed versus arbitrary bit width, and whether the
  unary NOT needs a declared width to be well-defined.

  Setup for that thread:
    1. Commit everything from this thread first. The packer reads
       HEAD, so an uncommitted render packs as an error, by design.
    2. Fill the SHA placeholder in drill/llm/CONTEXT.md line 2 with
       the commit that contains the render. The content-hash
       (90f3e04b) stays as is; filling the SHA does not invalidate it.
    3. Pack the context:
         scripts/pack-repo.sh drill/llm/CONTEXT.md <drill source paths>
       Archive mode for a chat that accepts an upload, -p for paste.
       Include the drill sources the task touches, not the whole tree.
    4. Kick off a fresh IMPLEMENTATION thread on the bitwise task,
       giving it the packed context and NOTHING ELSE from the
       playbook. That is the actual test.

  The gate question is NOT whether the feature ships. It is whether
  the rendered context alone carried the preferences into the work:
  did the thread hold scope, ship a test with the commit, produce
  complete files rather than snippets, avoid premature abstraction,
  and stay ASCII -- WITHOUT being told any of it in the kickoff?
  File what it missed as refinement entries. A rule the render failed
  to carry is a finding about the RENDER, not about the thread.

  FAILURE BRANCH (unchanged): reopen T-005..T-007b only.
