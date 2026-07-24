HANDOFF -- PLAYBOOK-IMPL-003 to PLAYBOOK-DESIGN-004
====================================================
date: 2026-07
from: PLAYBOOK-IMPL-003 (implementation; gate G-1a)
to:   PLAYBOOK-DESIGN-004 (design; must propose ADRs, not execute)
why a DESIGN thread: what remains is protocol change and document
consolidation. There is no fixed plan to execute -- the work needs
decisions recorded as ADRs first. An implementation thread would have
to invent the design silently, which the deviation rule forbids.

READ FIRST
  drill/llm/g1-findings.md   findings F1-F13, the gate result, and
                             WHAT THIS MEANS FOR G-1.
  llm_playbook/close-PLAYBOOK-IMPL-003.md   the six commits and the
                             open items O1-O6.
  This handoff assumes both. It does not restate them.

STATE
  G-1a PASSES ON TRANSPORT, FAILS ON RENDER EFFECT. The packer, the
  stamp, and the rendered CONTEXT.md are all sound and verified. A
  real design thread was then given the whole drill archive and never
  opened the render; it followed drill's own CODING_CONVENTIONS.md
  instead, found by its own initiative. Six of seven style checks
  still passed, sourced from the competing document and the
  surrounding code. Transport is not the problem. Nothing tells a
  thread that the render binds it.
  T-008+ remains SHUT. G-1 does not close until the render mechanism
  is fixed and re-tested.

WORK, IN DEPENDENCY ORDER
  The first item unblocks the third. Doing the re-test before the
  merge wastes the run, because a competing document confounds it.

  1. MERGE AND RETIRE THE COMPETING DOCUMENT (F11, O4). Blocking.
     drill/llm/CODING_CONVENTIONS.md is what the evaluated thread
     actually followed. While it exists and is more findable than
     the render, no render test is trustworthy.
     Expect a THREE-WAY split, not a two-way merge:
       - rules already generalized into the render: drop, they are
         duplicates and the render wins;
       - rules genuinely specific to drill (module layering,
         operator_depth, the HTTP 400 boundary, and similar): these
         are NOT duplicates. They belong in a new drill/llm/PROJECT.md
         as instance rules, which is what F5/O5 already flagged as
         missing. render.md's pass step 1 reads PROJECT.md and
         instance rules win conflicts, so this is the designed home;
       - the old file: retire it, or reduce it to a single pointer at
         the render. Do not leave a second style document standing.
     Verify by re-rendering drill's CONTEXT.md afterward: instance
     rules lead the document, and the stamp is recomputed.

  2. CLOSE THE PROTOCOL GAP (F10, O3). Needs an ADR; the current set
     does not cover it. ADR-020 fixed WHERE the render lives and
     nothing makes a thread READ it.
     Recommended shape, argued but not decided:
       - the KICKOFF names the render and states that it binds the
         thread. One sentence, both delivery modes. In paste mode the
         render is in the block; in archive mode the kickoff says to
         unpack and read it first.
       - do NOT put this in pack-repo.sh. Transport moves bytes and
         did its job correctly throughout; making the packer emit
         prompts couples transport to protocol, and every later
         protocol change would then require a packer change. A
         discoverability FLAG on the packer has the same defect and
         also adds per-invocation configuration that can be set
         wrongly or forgotten. The instruction belongs in the
         kickoff, which is where instructions already live.
       - the recurring part should be a playbook artifact rather than
         retyped prose: a new protocol/kickoff.md holding a KICKOFF
         template (role, scope, delivery mode, the render-binds-you
         line) and a HANDOFF template (what landed, what is open,
         what does not open yet). close-PLAYBOOK-IMPL-003.md is
         already most of a handoff template; it is simply not
         reusable. naming.md gives handoff filenames the form
         handoff-<FROM>-to-<TO>.md, so the template must produce
         that.
     Also fold in the stamp ORDERING note (O3): the SHA names the
     commit CONTAINING the render, so it is authored as a placeholder
     and filled at commit time. This is safe because the content-hash
     covers the body only. State it in render.md; a naive author will
     otherwise try to stamp first and stall.

  3. RE-TEST ON AN IMPLEMENTATION THREAD, EVALUATED COLD. Only after
     1 and 2.
     The evaluated thread was a DESIGN thread. The style clauses
     mostly bind IMPLEMENTATION: S1 naming, S23 complete files, S24 a
     test per commit. That role is still unmeasured.
     Method that produced the honest result, and should be repeated:
       - give the thread the packed context and the task, and point
         at nothing beyond the kickoff line from item 2;
       - do not tell it that it is being evaluated;
       - ask the diagnostic question, not the checklist: WHAT IN YOUR
         CONTEXT TOLD YOU HOW TO NAME, TEST, AND DELIVER -- QUOTE IT.
         A thread that cites clause ids read the render. A thread
         that says "general best practice" did not. Six of seven
         checklist items passed while the render had zero influence,
         so a pass rate alone cannot distinguish these;
       - EVALUATE IN A FRESH THREAD that did not do the work and is
         not told which document was supposed to bind. Ask it what
         governed the work and let it name the source. A thread
         reporting on itself knows what is being looked for.

  4. PROMOTE THE WORKFLOW PROMPTS. drill/llm/prompts/ holds five
     files, about 400 lines. Measured against drill-specific
     references:
       commit-planning.md    81 lines, ZERO drill references
       plan-review.md        75 lines, ZERO drill references
       spike-and-verify.md   88 lines, ZERO drill references
         -- these three are already generic. Promotion is a MOVE.
       adversarial-review.md 102 lines, three drill references
         -- promote after genericizing those three.
       clone-and-verify.md   54 lines, seven drill references
         -- promote after genericizing, but see the note below.
     Destination and naming are a decision for this thread, not an
     assumption: a protocol/prompts/ directory is the obvious home,
     but naming.md must classify whatever is chosen (N5), and
     precedence.md should say where a workflow prompt sits relative
     to the render and instance rules.

     ON clone-and-verify.md AND ADR-021. This prompt sparse-clones,
     and an earlier draft of this handoff called it obsolete on that
     basis. That was WRONG and is corrected here. ADR-021 retired
     sparse-checkout as the mechanism for getting CONTEXT INTO A
     CHAT, because a second working tree is worthless when a thread
     only needs to read. It did not retire checkouts generally.
     clone-and-verify does a different job: it pins an exact 40-char
     SHA, confirms branch decoration, establishes a GREEN TEST
     BASELINE before any change with a hard stop if the count does
     not match, distinguishes collection and import errors from
     failures, and declares an explicit file scope. Five of its six
     steps have nothing to do with transport. A thread that must RUN
     TESTS needs a real working tree, which pack-repo.sh cannot and
     should not provide -- the packer is scratch-only and
     committed-read by design, and produces no tree at all.
     The division to record: PACK-REPO.SH IS PRIMARY, because most
     work is read-and-reason and that is the common case. A CHECKOUT
     is the exception, used when a thread must execute the suite or
     otherwise operate on a live tree. Neither supersedes the other.
     Worth stating in transport.md so the next reader does not repeat
     this thread's error; consider whether ADR-021's wording invites
     it, since a one-line index entry that says "transport is
     archive-or-paste" reads broader than the decision actually was.

  5. PACKER FEATURE: EXCLUSION. Deferred by IMPL-003 on purpose, not
     overlooked. There is no way to pack a directory MINUS a subtree.
     Now better motivated: drill is 115 files and 1.7 MB, on the
     order of 400k tokens, while a task-selected set is about 200 KB,
     roughly 50k tokens. The shape is undecided -- globs, an ignore
     file, or repeated -x flags -- so it needs a real forcing case
     before it is built. Do not build it on speculation.
     The -n dry run already reports the file set and count before
     packing, which covers the immediate need.

  6. TWO SMALLER OPEN ITEMS.
     O1/F1: the ADR-025 user-identity Persona items are UNAUTHORED.
     No source exists in the repository and they are facts about the
     author, which must not be invented. They need to be supplied,
     not derived. Until then every render is missing that layer.
     O2/F2: check.sh false-positives on documents that QUOTE the
     upward-path pattern while describing the containment rule. Three
     documents now trip it, including this thread's close artifact,
     which was reworded to avoid it. Fold into the deferred check.sh
     rework; nothing is blocked, since the hook is not installed.

WHAT NOT TO DO
  Do not reopen T-005..T-007b. The plan's failure branch aims there,
  but it targets render CONTENT, and the content was fine: 198
  well-formed lines within budget that nobody opened. Reopening it
  would rewrite a document that was never the problem. The defect is
  in the protocol around the render.
  Do not add discoverability to pack-repo.sh. See item 2.
  Do not open T-008+. G-1 is not closed.

WHAT IS SOUND AND SHOULD NOT BE REDONE
  pack-repo.sh after the fixes: archive and paste modes, directory
  expansion, -n dry run, -e rejected outside paste mode, and the
  five-percent-sign boundary markers with per-file line counts.
  Verified: committed-read refuses an uncommitted render and names
  the path; scratch-only writes to /tmp and leaves the tree clean;
  two runs at one SHA are byte-identical; the round trip is lossless
  and the stamp survives transport; a one-character edit to a render
  body shifts the content-hash.
  The rendered drill/llm/CONTEXT.md itself: 198 lines within a 250
  ceiling, all 34 preference items and all 25 style clauses cited by
  id. Its content was never the failure.
  transport.md, and the W1-W8 base-context items added to layers.md
  as CONSTRAINT-008..011 and CONVENTION-008..011.

A NOTE ON THE CEILING (F12)
  The 250-line render ceiling exists to bound a PASTED block. Where a
  thread has the archive and a shell, targeted search into a large
  file beats any fixed-size excerpt: the evaluating thread needed
  four separate regions of a 2431-line module and got each in one
  call, where a 250-line window would have forced repeated
  reconstruction or a lossy summary. Recommended: make the ceiling
  TIER-DEPENDENT, binding for paste and advisory for archive, rather
  than dropping it. Dropping it entirely loses the constraint exactly
  where it still bites. This is an ADR-sized decision.
