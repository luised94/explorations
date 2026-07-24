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

GATE RESULT: G-1a PASSES ON TRANSPORT, FAILS ON RENDER EFFECT.
  The transport path works end to end on real content: every check
  below ran against the committed 198-line render, not a stand-in.
  But the subsequent real-thread run (F9-F13) showed the render
  itself was never read and had no effect on the thread's behavior.
  Transport is sound; the render mechanism is not yet doing its job.
  See WHAT THIS MEANS FOR G-1 at the end of this file.

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

  F6. PASTE MODE SHIPPED BROKEN for directory arguments. Passing a
      directory emitted a git TREE LISTING, not file contents -- a
      paste block that looks like content but carries none. Cause:
      B2c verification only ever passed single FILE paths, so the
      directory case never ran. Seven invariant tests passed against
      a tool that failed its primary use case. The lesson is about
      test SHAPE: invariants were checked, real invocation was not.
      Fixed in-thread (directories expand via git ls-tree; -e outside
      paste mode now rejected; -n dry-run added to show the file set
      and count before packing).
  F7. THE BOUNDARY MARKER COLLIDED WITH CONTENT. Paste blocks fenced
      files with a row of equals signs, which occurs 342 times at
      line start in drill's own committed files -- every markdown
      setext underline is one. Boundaries were therefore not
      greppable and not distinguishable from content; the rendered
      CONTEXT.md's own title underline sits inside a packed block as
      a live example. Replaced with a five-percent-sign marker
      (zero occurrences in drill; no meaning at line start in
      markdown, Python, or JavaScript) plus a line count per file.
      Markers must be chosen against real content, not assumed.
  F8. PASTE MODE DOES NOT SCALE TO A WHOLE PROJECT and cannot be
      made to. Drill at this commit is 115 committed files, 34832
      lines, 1.7 MB -- on the order of 400k tokens, several times a
      context window, regardless of marker format or compression.
      A plausible SELECTED set for one task (the render plus the
      three modules it touches) is about 200 KB, roughly 50k tokens:
      an 8.7x reduction and comfortably packable. Paste mode is
      therefore a SELECTED-FILE channel by nature; archive mode is
      the whole-tree channel, and it is the one that carried a real
      task successfully. -n reports the file count before packing.
      Exclusion (pack a directory MINUS a subtree) is not
      implemented and is the next likely need; deliberately not
      built on speculation.

G-1b RESULT (run by the author after this thread's B5; recorded here
because it bears directly on the render mechanism G-1a delivered)
  F9. THE RENDER DID NOT LAND. A real DESIGN thread was given the
      ENTIRE drill archive (115 files, 1.7 MB, on the order of 400k
      tokens) and asked only what the coding style and conventions
      were, with nothing pointed at. It never opened
      CONTEXT.md. It found and followed CODING_CONVENTIONS.md by its
      own initiative, quoted that file, and took its naming and ASCII
      behavior from it plus the surrounding code. The render had ZERO
      influence on the thread. Six of seven style checks still
      passed, which is the trap: a pass rate can be produced entirely
      by sources other than the artifact under test. The diagnostic
      question ("what in your context told you this -- quote it")
      caught the failure that the checklist would have masked.
  F10. THE DEFECT IS DISCOVERABILITY, NOT TRANSPORT. An archive
      delivers everything and signals nothing; CONTEXT.md had no more
      salience in a 30-file instance directory than any dated
      options memo. Pasting would fail the same way with the render
      buried mid-block. The whole-archive delivery sharpens this:
      the render was one file among 115, competing with roughly 400k
      tokens, with no ordering signal of any kind. ADR-020 fixed
      WHERE the render lives and nothing makes a thread READ it. A render that is not read is
      not a render. Minimum fix: the kickoff must name the render
      explicitly, or carry it inline. This is a protocol gap, not a
      packer gap -- transport worked correctly throughout.
  F11. F4 WAS THE CAUSE, NOT A CLEANUP ITEM. This file recorded
      CODING_CONVENTIONS.md as redundant with the render and left it
      OPEN. It was not dormant: it WON. The competing document was
      the one the thread found, and it is the reason the style checks
      passed at all. Retiring it or reducing it to a pointer is now
      blocking, not deferred. The project's own single-source rule
      (S21) is violated by its own style documentation.
  F12. THE 250-LINE RENDER CEILING IS WRONG FOR ARCHIVE DELIVERY.
      It exists to bound a pasted block. Where a thread has the
      archive and a shell, targeted search into a large file beats
      any fixed-size excerpt: the evaluating thread needed four
      separate regions of a 2431-line module and got them in one
      call each, where a 250-line window would have forced repeated
      reconstruction or a lossy summary. B4 compressed 288 lines of
      source to 198 to satisfy a ceiling that this delivery tier does
      not need. The ceiling should be tier-dependent -- binding for
      paste, advisory for archive -- rather than absolute.
  F13. NO REFINEMENTS WERE PRODUCED BY THE EVALUATED THREAD. It did
      not notice or record gaps in its own context; the gaps surfaced
      only when the author asked directly. Whatever teaches a thread
      to file refinements is not currently reaching threads, which
      is consistent with F9: the document that would teach it was
      never read. Note the evaluated thread was a DESIGN thread, and
      refinement-filing may be role-specific; this is untested for
      implementation threads.

  F14. ADR-021'S WORDING INVITES OVERREADING. Its index entry says
      transport is archive-or-paste, which reads as though checkouts
      are retired generally. The decision was narrower: copying a
      tree merely to READ it is waste when one thread runs at a
      time. This thread misread its OWN decision, calling drill's
      clone-and-verify prompt obsolete because it sparse-clones --
      when five of its six steps are verification (exact-SHA pin,
      branch confirmation, green baseline before any change,
      collection-error handling, explicit file scope) and a thread
      that must RUN a suite needs a working tree the packer cannot
      supply. Division to record: the packer is PRIMARY, since most
      work is read-and-reason; a checkout is correct when a thread
      must EXECUTE. Reading is a pack, executing is a checkout.
      Corrected in transport.md; proposed as ADR-032. That the
      implementing thread made this error within one session is the
      evidence the wording needs narrowing.

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

WHAT THIS MEANS FOR G-1
  G-1a's own deliverables stand: the packer is correct, the stamp
  survives transport, the render is well-formed and within budget.
  G-1b is a FAIL on its stated question -- whether rendered
  preferences reach working code. They did not; equivalent behavior
  arrived from a competing document.
  The failure branch in the plan (reopen T-005..T-007b) is aimed at
  render CONTENT. That is the wrong target here: the content was
  fine and unread. What needs work is the PROTOCOL around the render
  -- how a thread is told the render exists and is bound by it --
  plus retiring the competing document (F11). Recommend an ADR
  before reopening anything, since this is a gap the current ADR set
  does not cover.
  T-008+ stays SHUT.
  ONE ROLE TESTED ONLY. The evaluated thread was a DESIGN thread.
  Whether a render reaches an IMPLEMENTATION thread -- the role the
  style clauses mostly govern, since it is the one that names
  variables, ships tests, and delivers files -- is still unmeasured.
  A design thread plans; an implementation thread is where S1, S23,
  and S24 actually bind. Re-run on that role before drawing a
  conclusion about the render mechanism as a whole.
  EVALUATE IN A FRESH THREAD. The next evaluation should be read by
  a thread that did not produce the work, since a thread reporting
  on itself knows what is being looked for before it answers.
