CLOSE PLAYBOOK-DESIGN-006_reset-recovery
========================================
date:     2026-07
type:     close
baseline: playbook e19174f4dc07dbdc8ac9063aa64a84246fc817ce
          project  e19174f4dc07dbdc8ac9063aa64a84246fc817ce  same repo
          pre-reset 42298a27ad4abec49aa4dc12976b5c466b62f097
scope:    looking back at the thread that recovered four sections the
          July 2026 reset removed, amended R6, and repaired four
          broken citations. Writes in llm_playbook only.

TERMINAL STATE: LANDED.


WHAT LANDED

  Five files rewritten whole (accretion rule TWO), applied and
  committed by the author against real HEAD.

    protocol.md            236 -> 334 lines
      PRECEDENCE replaced. Chain 1 (live human > project instance >
      playbook > model defaults) with the emission clause -- the
      render emits ONLY the winner, the losing rule never reaches the
      model -- and the bottom link, silence means the model default
      stands. Chain 2 unchanged in substance. The WORKED EXAMPLE
      walks both. The section carries the pre-reset rationale that a
      stateless model cannot arbitrate a chain whose lower links it
      never sees, which is the reason the split exists at all.
      READ-ONLY CHECKOUT added as its own section, without the
      pre-reset ADR-004 credit: ADR-004 did not say it, precedence.md
      did.
      IDENTITY AND NAMING gained the twelve-value type vocabulary,
      the RF-PROJ-NNN grammar, and a ruling on <id>.
      R6 replaced in place. No R13; the cap did not fire.
      KICKOFF gained a clause for a project with no render.

    settled.md             193 -> 260 lines
      ADR-022 entry corrected. Stable-forever-ids retirement narrowed.
      Authority-tiers entry amended. Four new entries: the size
      ruling, the llm/ ruling, the retyping decision, the absent
      playbook render.

    refinements.md         136 -> 183 lines
      RF-PLAYBOOK-004 second occurrence recorded on the existing
      entry. RF-PLAYBOOK-010 and RF-PLAYBOOK-011 opened.

    README.md              184 -> 185 lines
      Three RESET-2026-07.md citations repointed to docs/; docs/ added
      to the WHAT IS HERE inventory.

    prompts/clone-and-verify.md   93 -> 94 lines
      transport.md, ADR-032 and ADR-021 repointed to README TRANSPORT
      and settled.md. The ADR record was not restored.

  Created: llm_playbook/llm/kickoff/ and llm_playbook/llm/close/,
  holding this thread's kickoff and this document.


DISCREPANCIES, AND HOW EACH WAS RESOLVED

  This is the section that does not survive in the diff.

  1  THE KICKOFF ARRIVED TWICE AND WAS THE SAME FILE. The thread was
     asked to reconcile a handoff against reset-recovery notes that
     "may be contradictory". Both attachments were byte-identical.
     There was no contradiction to reconcile. Resolved by saying so
     rather than synthesising a difference to justify the request.

  2  THE EXTRACTS WERE NOT IN THE PACK. HAVE listed
     extracts/precedence-extract.txt and extracts/naming-extract.txt;
     the tarball held 17 files, all under llm_playbook/. The
     precedence extract was pasted inline and was truncated after
     READ-ONLY CHECKOUT. /tmp/playbook-pre-reset did not exist and the
     pack carries no .git, so not one command from
     docs/RESET-2026-07.md was runnable. Resolved by declaring the
     absence under R11 and asking for both files by name; both
     arrived complete on the next turn. COST: one turn. The S1
     inventory shipped citing SECTIONS rather than line numbers at
     42298a27, because a paste carries no line numbering tied to a
     commit and estimating them would have been the RF-PLAYBOOK-001
     failure one level up.

  3  T-5 MIS-CITED ITS OWN EVIDENCE. The kickoff named three prompts
     as already permitting a deliberate red. Two do.
     spike-and-verify.md lines 58-59 describe proving a guard inside a
     SPIKE -- green on clean code, red on an injected violation -- and
     name no commit at all. It stays out of the evidence base. The
     second occurrence README rule ONE requires is met without it,
     because commit-planning.md supplies both the "LET IT GO RED"
     section and the welded-pair line at 44-46.

  4  R6's REAL COLLISION WAS NOT THE MISSING EXCEPTION. It was the
     phrase "each independently valid", which a red intermediate
     violates by definition. The kickoff did not name it.

  5  THE DELIBERATE RED BREAKS BISECT, AND R6 SAYS THE SERIES
     BISECTS. Found in the adversarial pass, and it would have
     shipped a rule contradicting its own next sentence. A red commit
     poisons git bisect run: the suite fails there for a reason
     unrelated to the bug being hunted. Resolved by BOUNDING the red
     rather than merely permitting it -- the repair follows in the
     very next commit, so the red spans one commit and a bisect skips
     it rather than reporting it.

  6  THE type: VOCABULARY IS NOT RECOVERABLE VERBATIM. The source
     entry names example files -- precedence.md, kickoff.md,
     render.md, transport.md -- that the reset deleted. Recovering it
     as written would have imported five citations to files that do
     not exist, which is the class of defect this thread was convened
     to repair. The lists were rewritten against the current tree.
     This is a recovery WITH EDIT, not a transcription, and it is
     recorded as one.

  7  A REVERSED CALL, MINE. At S1 I argued the twelve values were
     mostly consumerless and recovering them would be accretion.
     Wrong. Applying the vocabulary's own requirement to the current
     tree gives protocol.md toolkit-rules, settled.md decisions,
     refinements.md refinements; the thread-artifact values go live
     the moment llm/ exists; render is drill's CONTEXT.md and
     instance-rules is drill's PROJECT.md. All twelve acquire a
     consumer. The objection did not survive contact with the source
     and was withdrawn.

  8  A SECOND REVERSED CALL, ALSO MINE. I recommended retyping
     docs/RESET-2026-07.md, whose type: value the vocabulary does not
     name. The file states at line 8 that it is historical and is not
     amended. Retyping it amends it. Left untouched; recorded in
     settled.md as a decision so the next reader meets it as a ruling
     and not as drift.

  9  THE RECOVERED type: REQUIREMENT HAD A DANGLING TERM. The source
     requires type: "on every non-sentinel document", and defines
     sentinel in naming.md N1, which is not recovered. Landing the
     requirement without its definition would have created a rule
     containing an undefined word. Only the vocabulary was landed,
     plus the one concrete carve-out: README.md carries no type:
     because its name is its role.

  10 THE WORKFLOW PROMPTS SECTION WAS A TRAP AND WAS NOT LANDED. The
     complete precedence extract carries a five-tier standing:
     workflow prompt < playbook items < project instance rules <
     render < live human. settled.md rejects more than two runtime
     tiers. Its substance already exists as "a prompt is a method and
     never an authority". Nothing from it was recovered, and the
     authority-tiers entry was amended to say why chain 1's four
     LINKS are not four TIERS -- otherwise a reader meets
     protocol.md PRECEDENCE and settled.md as a contradiction.

  11 FLAG, DO NOT FOLLOW WAS ALREADY LANDED AS R1 and was not
     recovered. Its one non-duplicate asset is the origin incident: a
     handoff instructed use of a command-line flag that did not exist
     in the code. Deferred, not entered anywhere.

  12 MY OWN EDIT SCRIPT HIT RF-PLAYBOOK-008. THIRD OCCURRENCE. The
     first script asserted each file's anchor immediately before that
     file's own write. The settled.md anchor was mis-transcribed
     indentation, the script died, and README.md had already been
     written -- a half-edited tree, the exact shape of the entry, in
     the thread that was recording that entry's history. Resolved by
     rebuilding from the pack and re-running with every anchor across
     every file asserted before any write. No fourth-occurrence note
     was opened: the second already made it a promotion candidate and
     a third does not change the disposition. COST: one rebuild,
     nothing lost, because the build tree was a copy and the pack was
     still on disk.

  13 A CITATION I CLAIMED FIXED AND HAD NOT. After the ancillary (a)
     pass I asserted the RESET-2026-07.md citations were repointed.
     Verification by grep found a third at settled.md:94 still bare.
     The kickoff had said "settled.md repeats the error once" and I
     had read it and still missed it. Found by executing the check
     rather than by asserting the fix (CONSTRAINT-014), which is the
     entire argument for running it.

  14 MY LINE-COUNT FORECAST WAS WRONG BY 32. I predicted protocol.md
     at 302 and it is 334. The kickoff predicted +110 and I predicted
     +66; the truth is +98. The overage is display formatting on the
     chain blocks, the <id> ruling, and a KICKOFF clause I added
     without forecasting. The S2 absorb ruling survives, but on the
     scope-line argument ("there is no second file") and not on the
     line-count argument, which was mine and was wrong.

  15 TWO PIECES OF NEW TEXT ARE NOT RECOVERIES AND WERE NOT ON THE S1
     INVENTORY. The <id> ruling and the KICKOFF renderless clause.
     Both were flagged before landing and both were accepted. Named
     here because an S1 inventory that silently grew is exactly the
     scope drift CONSTRAINT-011 says to counteract.


DEFERRED

  Nothing here is rejected; each has a home and no owner yet.

  render.sh verify is blind to the drift it exists to catch
    (kickoff FINDINGS 1). It recomputes the body hash and never
    re-resolves the stamp SHA, so it detects hand-editing only. Every
    other finding in that list went unnoticed behind its green
    checkmark. Three lines inside verify would close it. THIS IS THE
    ROOT CAUSE AND IT SHOULD BE NEXT.

  scripts/pack-repo.sh cites ADR-021 twice and ADR-022 once in its
    header; all are retired. Left untouched by design --
    docs/RESET-2026-07.md keeps the file "untouched here precisely
    because that record is its value" -- so the dangling citations are
    recorded and not repaired.

  preferences/ findings 5, 6 and 7. Recorded, changed nothing. Wave B,
    serialized behind DRILL-IMPL-002's C-101. Includes: version: 0.1.0
    surviving in both sources, CONVENTION-001 assuming concurrent
    threads that CONSTRAINT-010 forbids, and L3's private-overlay
    clause, which was designed, never implemented, never given a
    location, and is a deletion candidate rather than a recovery.

  ADR-033's closure rule -- "a field this list does not name is a
    finding, not an exception" -- has no home. The reset removed
    exactly the three accreted fields (status, role, supersedes)
    without knowing that is what it was doing, then added baseline:
    without noting it. The LIST is fine. The closure rule is the
    homeless part. A value-level version of it landed in protocol.md
    for type:; the field-level version did not.

  F-18 residue item (ii): never improve a shipped policy by taste
    instead of by a metric named in advance. No recorded occurrence in
    this repository, so it is not in refinements.md, which takes
    OBSERVED failures. An entry with no observation is a rule wearing
    a refinement's clothes.

  The origin incident behind R1 (discrepancy 11).


REJECTED

  A second protocol file. S2 ruled absorb. Restoring
    protocol/precedence.md and protocol/naming.md would have required
    rewriting protocol.md's scope line and reopened seams the reset
    closed because they were arbitrary, not because the file was long.

  The pre-reset handoff filename grammar, handoff/<FROM>-to-<TO>.md.
    Superseded by protocol.md's llm/<slot>/<id>_<subject>.md, and it
    depended on the status and role fields the reset correctly
    removed. Not restored alongside llm/.

  The five-tier prompt standing (discrepancy 10).

  Restoring any deleted file wholesale, and any re-litigation of the
    reset. Held throughout.


THE ACCEPTED BREACH, AS DECLARED

  T-1 and T-5 rewrote PRECEDENCE and R6, which BIND the open
  DRILL-IMPL-002 thread. settled.md's DECLARED ASSUMPTIONS say a hot
  fix reaches an open thread through the live human channel only, and
  that the render hash is checked at kickoff because nothing can
  change the render mid-thread. Two of those three mechanisms were
  stressed here. The human was the channel and carried it.

  Recorded as a real breach rather than assumed harmless. What kept
  it survivable is the boundary that was held: NOTHING IN
  preferences/ WAS TOUCHED, so render.sh's stamp SHA -- resolved from
  git log -1 -- llm_playbook/preferences and nothing else -- did not
  move, and drill's CONTEXT.md is no more stale than it already was.
  Had the boundary been crossed, finding 1 guarantees the drift would
  have been silent.


HANDOFFS PRODUCED

  None, and that is deliberate. protocol.md HANDOFF is written for a
  thread that has not started. DRILL-IMPL-002 is OPEN and resumes at
  its Phase 0 against a kickoff it already holds, so a handoff would
  be a second binding document on a live thread. What it needs is the
  delta, and the delta travelled as a live human message: C-101a is
  unblocked, P-4 is resolved, and the R6 it planned against no longer
  exists.

  This close artifact is the durable trace (R9).
