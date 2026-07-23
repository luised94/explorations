G-1a FINDINGS
=============
date: 2026-07
thread: PLAYBOOK-IMPL-003
scope: findings from the G-1a transport/render gate -- authoring the
first CONTEXT.md and packing it through the real channel. TEMPORARY:
this file exists because drill has no refinements.md until D-101.
When that skeleton lands, these entries move there as RF-DRILL-NNN
refinement entries and this file is deleted. Nothing here is a
durable record in its own right.

GATE RESULT: PASS
  The transport path works end to end on real content. Every check
  below ran against the committed 198-line render, not a stand-in.

VERIFIED
  V1. Committed-read holds. Packing a render present in the working
      tree but absent at HEAD fails with exit 1 and names the
      offending path. The documented gotcha is caught, not silently
      producing an artifact missing the file.
  V2. Archive mode packs at HEAD and echoes the full SHA.
  V3. Scratch-only holds. The pack wrote only to /tmp; git status
      was clean afterward and no pack artifact appeared anywhere in
      the tree. An OUTDIR outside /tmp is refused with exit 1.
  V4. Idempotent. Two runs a second apart at the same SHA produced
      byte-identical archives (sha256 equal), so no timestamp bleeds
      into the artifact.
  V5. Round-trip is lossless and the STAMP SURVIVES TRANSPORT. The
      unpacked render is byte-identical to the committed one and
      recomputes to the stamped content-hash, so a reader at the far
      end can verify what they received.
  V6. Subset packing works, pulling named directories recursively:
      one command packs a project's render plus exactly the toolkit
      files a thread needs.
  V7. Paste mode composes the render into a fenced text block
      carrying the pack SHA in its header.
  V8. Content-hash catches hand edits. A one-character change to the
      render body shifts the hash (90f3e04b -> 8dd2d344), satisfying
      the T-007 accept criterion.

FINDINGS
  F1. layers.md lacked the ADR-025 base-context items although T-005
      was marked LANDED. The plan text carried the EDIT 6 wording but
      the items were never written. Resolved in-thread: a new step
      B2d added W1-W8 as CONSTRAINT-008..011 and CONVENTION-008..011.
      The USER-IDENTITY Persona items remain UNAUTHORED -- no source
      for them exists in the packed tree, and they are facts about the
      author that must not be invented. OPEN: supply the facts and
      author them as PERSONA-006 onward.
  F2. check.sh reports upward-path-reference violations against
      implementation-plan.md and consolidation-PLAYBOOK_DESIGN-002.md.
      Both are FALSE POSITIVES: each QUOTES the upward-path pattern
      inside prose describing the containment rule check.sh enforces.
      A document cannot currently discuss the rule without violating
      it. The close artifact for this thread hit the same trap and
      was reworded, which is evidence the defect is real and
      recurring rather than incidental. Pre-existing, unrelated to
      this thread, not repaired here. Consistent with ADR-028
      (budgets provisional, hook not installed, nothing blocked).
  F3. The render stamp needs the commit SHA of the commit that
      CONTAINS the render, which cannot be known before that commit
      exists. The SHA field is therefore authored as a placeholder
      and filled by the author at commit time. This is sound rather
      than a defect: the content-hash covers the body only (lines 3
      onward), so filling the SHA does not invalidate it -- verified.
      Worth stating explicitly in render.md, since the ordering is
      not obvious and a naive author would try to stamp first.
  F4. drill/llm/CODING_CONVENTIONS.md is now redundant with the
      rendered CONTEXT.md. It is the ancestor the playbook style
      contract was generalized from, so the two say the same things
      in different words -- exactly the documents-disagreeing drift
      CRITERIA-009 warns about. Not touched here (out of scope).
      OPEN: retire it or reduce it to a pointer at the render.
  F5. drill has no PROJECT.md, so the render emits no instance rules
      and precedence chain 1 had nothing to arbitrate. The render
      says so in its header rather than letting the playbook items
      pass as drill's own instance rules. Not a defect at this
      commit; it becomes one the moment drill acquires an instance
      rule that contradicts a playbook item.

NOT TESTED
  N1. Paste mode's -e editor path. No editor is present in the
      sandbox used for verification; the no-editor fallback (print a
      message, leave the file) was exercised instead. The -e path
      needs one manual run on the author's machine.
  N2. check.sh as a pre-commit hook. The hook is not installed
      (ADR-028), so nothing in this gate was gated by it. check.sh
      was run manually.

NAMING CHECK (N5)
  Every artifact this thread created or renamed is classifiable using
  naming.md alone: transport.md and pack-repo.sh are playbook
  artifacts (lowercase, dateless, hyphenated); drill/llm/CONTEXT.md is
  a listed sentinel at the instance dir per ADR-020;
  drill/llm/g1-findings.md is lowercase and hyphenated;
  close-PLAYBOOK-IMPL-003.md matches close-<THREAD-ID>.md. No
  nonconformance to report.
