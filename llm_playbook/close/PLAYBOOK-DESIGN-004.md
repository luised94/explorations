CLOSE -- PLAYBOOK-DESIGN-004
============================
date: 2026-07
thread: PLAYBOOK-DESIGN-004 (design role)
gate: G-1 -- closes the PROTOCOL gap behind G-1a/G-1b; does NOT itself
close G-1, which requires a re-test (handed off).
predecessor: PLAYBOOK-IMPL-003 (ran G-1a/G-1b; passed transport, failed
render effect).

RESULT: THE PROTOCOL GAP IS CLOSED; G-1 REMAINS OPEN PENDING RE-TEST.
  G-1b failed because nothing made the render authoritative: a thread
  given the full archive followed a competing document and never
  opened the render, yet passed most style checks because the rules
  leaked from that document and the surrounding code. This thread
  removed the confound and gave the render binding force. It did NOT
  run the re-test -- that requires a subject thread that does not know
  it is being tested and a fresh evaluator, neither of which the
  authoring thread can be. The re-test is handed to PLAYBOOK-IMPL.

WHAT LANDED
  ADR-030  a kickoff names the render and states it binds; recurring
           text becomes protocol/kickoff.md (KICKOFF + HANDOFF
           templates). Also supplied the "kickoff skeleton" that
           render.md referenced but never defined.
  ADR-031  render ceiling is tier-dependent -- binding for paste,
           advisory for archive.
  ADR-032  pack is primary for reading, a checkout remains correct for
           executing; narrows ADR-021's wording, not its substance.
  ADR-033  handoff filenames drop the redundant prefix (directory
           carries the classification); frontmatter field set is
           enumerated.
  ADR-034  scoped packing is the render-test delivery; no exclusion
           feature built because git-archive path selection already is
           one. Reverses the earlier "leave exclusion unbuilt" note on
           the record.
  drill/llm/PROJECT.md created; CODING_CONVENTIONS.md deleted, its
  rules split three ways (dropped where the render already covers them,
  moved to PROJECT.md where drill-specific, moved to prompts where a
  practice). CONTEXT.md re-rendered.
  Prompts promoted to protocol/prompts/: three moved unchanged,
  runtime-verification authored from the deleted file, clone-and-verify
  and adversarial-review genericized (drill values point at
  PROJECT.md/STATUS.md). naming.md classifies the prompts directory.
  T-024: stamp-ordering note in render.md; O1 parked in
  drill/llm/refinements.md.

TWO CORRECTIONS MADE ON THE RECORD (not silent)
  1. O3 (in close-PLAYBOOK-IMPL-003) says the stamp "names the commit
     that contains the render." Verified false against drill's actual
     render: the stamp names the 40-char PLAYBOOK commit the render was
     built FROM, which exists at render time, so there is no stamp-first
     stall. The T-024 note corrects the misread rather than encoding it.
  2. The IMPL-003 handoff ordered the merge before the ADRs and said to
     leave packer exclusion unbuilt. Both were adjusted with reasons:
     ADR-030/032 landed before the merge (the merge's PROJECT.md needs
     the precedence decision first), and scoped packing was adopted now
     (G-1b was the forcing case; the mechanism already existed).

WHAT IS SOUND AND MUST NOT BE REOPENED
  Render content (T-005..T-007b), transport, the packer, the
  three-way split, the promoted prompts. Only DELIVERY EFFECT is under
  test. T-008+ stays shut behind G-1.

HANDOFFS PRODUCED
  handoff/PLAYBOOK-DESIGN-004-to-IMPL.md -- the G-1 re-test. Scoped
    pack, ordinary (non-tell) kickoff, cold subject thread, fresh
    evaluator, causal pass criterion. This closes or fails G-1.
  handoff/DRILL-DESIGN-consolidation (self-contained) -- the 49-doc
    drill/llm sprawl. Out of scope for G-1. Map, then plan, then
    consolidate. Assumes only the drill/llm directory.

OPEN ITEMS CARRIED
  O1 persona layer -- parked, blocked on user-supplied facts.
  O2 check.sh false positive on quoted upward-path patterns --
     unaddressed, does not block G-1.
