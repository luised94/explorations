CLOSE -- PLAYBOOK-IMPL-003
==========================
date: 2026-07
thread: PLAYBOOK-IMPL-003 (implementation role)
gate: G-1a TRANSPORT/RENDER -- the transport/render half of the split
G-1 early-use gate (ADR-020..023, plan Edit 7).
predecessor: PLAYBOOK-DESIGN-002 (produced ADR-020..029 and the plan
edits; Stage A landed the plan and the ADRs in two commits).
bootstrap SHA: 69ae0609b575b885afb51ffe1c1445eba07b884f

RESULT: G-1a PASSES ON TRANSPORT, FAILS ON RENDER EFFECT.
  The corrected transport path was exercised end to end on real
  content: a hand-authored render was committed, packed, unpacked,
  and verified intact with its stamp. That half holds.
  The author then ran the G-1b real-thread test. It FAILED on its
  stated question. A design thread given the entire drill archive
  never opened CONTEXT.md; it followed drill's own
  CODING_CONVENTIONS.md, found by its own initiative. Six of seven
  style checks passed anyway, sourced from that competing document
  and the surrounding code -- which is the trap: a pass rate can be
  produced entirely by sources other than the artifact under test.
  Transport is sound. Nothing tells a thread the render binds it.
  G-1 does NOT close. T-008+ stays SHUT. The remaining work is
  protocol change and document consolidation, handed off to
  PLAYBOOK-DESIGN-004 (see HANDOFF below).

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
  ---  After the six commits, on real use, the packer was found
       broken for directory arguments in paste mode and its boundary
       marker collided with content 342 times in drill. Both were
       fixed in a follow-up commit (directory expansion, -e rejected
       outside paste mode, -n dry run, five-percent-sign markers with
       per-file line counts). Findings F6-F8 record the defects and
       the test-shape lesson: seven invariant tests passed against a
       tool that failed its primary use case, because only
       single-FILE paths were ever exercised.

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

HANDOFF
  llm_playbook/handoff-PLAYBOOK-IMPL-003-to-DESIGN-004.md carries the
  remaining work in dependency order: merge and retire drill's
  competing style document (blocking), close the protocol gap with an
  ADR so a kickoff names the render as binding, then re-test on an
  IMPLEMENTATION thread evaluated cold by a fresh thread. Also:
  promote the generic workflow prompts into the playbook, and decide
  whether the render ceiling should be tier-dependent.
  The G-1b instructions below are retained as the record of what was
  run and how. The method held up; the result was a failure, which is
  the correct outcome for a gate that was doing its job.

NEXT: G-1b REAL THREAD (AS RUN -- RESULT ABOVE)
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
