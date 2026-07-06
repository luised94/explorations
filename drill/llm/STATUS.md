# Drill Tool -- STATUS (single source of truth for project state)

This file is the ONE place that records what is done, what is next, and the
current baseline. Other documents (roadmap.md, knowledge-capture.md,
thread-launch-kit.md, the handoffs) describe PLANS, CONVENTIONS, and RATIONALE
that change slowly; they must NOT restate live status -- they link here instead.
This is the project's anti-drift discipline (Nelson: single-source every fact)
made structural: when status changes, edit THIS file only.

ASCII only. Single-user assumption holds throughout.

Last updated: THREAD THREE complete -- E10 cutover landed; roadmap #1 DONE.

================================================================================
BASELINE
================================================================================
- Code size: drill.py ~3590 lines (Bottle backend, sections
  CONFIG/DATABASE/LOGIC/HTTP/MAIN); index.html ~2620 lines (single <script>
  block, pre-modularization).
- Test suite: 311 green, ends "ALL GREEN".
    backend  197  (pytest: logic, db, http, generator property, migrations)
    frontend 114  (node + jsdom, real index.html):
                   drill 10, speech 21, timing 19, stats 30,
                   stats.integration 6, difficulty 20, import 8
- Tooling: Node v22 (jsdom needs 18+), uv for the Python venv. Run the suite
  with `bash tests/run.sh` (bash, not sh). Frontend tests are glob-discovered
  from tests/frontend/*.test.js (leading-underscore files are skipped).
- The baseline SHA for the NEXT thread is whatever this docs work lands at on
  main; a launch message pins it explicitly. Verify the clone matches before any
  work. NOTE: the "311 green" figures in this BASELINE block are the PRE-
  modularization baseline. Thread one (backend split) is done; the baseline for
  THREAD TWO is 317 green (backend 203, frontend 114) at the tip of thread one --
  confirm 317 on a clean clone before frontend work. See the Phase B thread-one
  marker below and llm/handoffs/2-to-frontend-cutover.md.
  UPDATE (mid-thread-two): frontend modules E1-E9 are now extracted and green.
  Suite is 528 green (backend 203 unchanged; frontend 114 original classic +
  211 across ten new *.module.test.js). The baseline for the E10 cutover is the
  tip of thread two (C-MOD-E8, boot); see llm/handoffs/3-to-E10-cutover.md.
  UPDATE (THREAD THREE, C-MOD-E10 -- roadmap #1 DONE): the atomic cutover landed.
  index.html now carries a single <script type="module" src="boot.js"> and NO
  inline JS (was ~2620 lines; now ~908). Suite is 539 green (backend 203
  unchanged; frontend 336). Frontend composition: 211 across the ten
  *.module.test.js + 114 across the SEVEN classic tests migrated in place to
  option (b) (belt-and-suspenders per ADR-051 option i -- every classic assert
  kept) + 11 in the new ownership.guard.test.js. As-built notes:
    - TEN frontend modules (state, el, api, timing, stage, speech, stats,
      session, drill, boot); the as-built DAG is in handoffs/3-to-E10-cutover.md
      Section 0 and dependency-plan.mermaid.
    - The E10 cutover surfaced + fixed TWO latent missing-import bugs the inline
      shared scope had masked: boot.js called endSession() and drill.js called
      onEndSession() without importing them from session.js. Both now imported.
    - The ownership guard (ADR-051) is ENFORCED as of this commit: four scope-
      aware acorn checks (registry integrity; owner-declares; cross-owner
      allowlist of 9 re-derived edges; no-DOM-at-import with boot's readyState
      guard the sole exemption) + RED-proofs. acorn is a NEW test-only dep --
      NOT on jsdom 29.1.1's tree here, contradicting the pre-E1 "zero new deps"
      assumption. Install BOTH in ONE command: `npm install jsdom acorn
      --no-save` (two separate --no-save installs prune each other).

================================================================================
DONE (roadmap items and the commit arc)
================================================================================
- Initial plan C-001..C-019b: scaffolding, schema, logic, HTTP, MAIN, import,
  TTS, stats. (MAIN pulled forward to C-013a; MC layout fix C-016a; TTS split
  C-018a/b/c; stats split C-019a/b.)
- #8  Automated test suite checked into the repo (C-020): the by-concern split
      (logic/db/http + frontend jsdom) plus one hypothesis property test.
- #11 Schema migration runner (C-T2): version-aware, forward-only run_migrations
      + MIGRATIONS registry + import-time consistency guard. SCHEMA_VERSION 3.
      Migrations v2 (questions.metadata) and v3 (responses.difficulty,leaf_count)
      applied. This CLOSED the archive "no migration runner / no questions
      metadata column" gaps.
- #4  Extend arithmetic: more operators -- exponent (^) and modulo (%) added as
      data, each with its own operand ranges.
- #5  Generalize expression generation: generate_expression now RECURSES over
      nested operator trees (operator_depth / recurse_probability); depth 1
      reproduces the old flat generator exactly. (The old "only the generator is
      flat" note is therefore obsolete -- evaluator, renderer, AND generator now
      all recurse.)
- #2  Extend arithmetic: difficulty control. Backend + data path (C-D2a..i:
      DIFFICULTY_RUNGS, the difficulty query param, the recorded rung, the
      per-rung stats path) PLUS the UI (C-2U-a..d): GET /api/difficulty-rungs,
      the rung selector, the active-rung badge, arithmetic-only gating. ADR-047
      closed. Difficulty=None stays byte-identical to the pre-#2 path.
- C-2U-e: tests/run.sh now glob-discovers frontend tests (was a hand list).

================================================================================
IN PROGRESS
================================================================================
- #20 Module docstring / status-drift cleanup + ADR index. DONE. The docs work
      (STATUS.md + CODING_CONVENTIONS.md + reconciling stale status across the
      doc set) was the bulk of #20; the last outstanding piece, the ADR index,
      is now written at llm/adr-index.md (Thread N.3).

================================================================================
NEXT (the phase map)
================================================================================
MODULARIZATION (roadmap #1) is DONE (C-MOD-*, through the E10 cutover). The
project has been REASSESSED (2026-07, ADR-054): the remaining roadmap items were
rescored against the actual code and the next threads sequenced by score tempered
with the user's constraints (study runs in parallel; want product movement with
comprehension; avoid a second schema-invasive thread right after the refactor).
See roadmap.md section 2a, ADR-054, and the runnable model roadmap.py.

CURRENT PLAN (post-reassessment):
- Thread N (NEXT): Vocab/language features + timing-stats + ADR index. One
  meaty-but-safe feature on proven seams (translate/identify/free_response
  qtypes, bank-language plumbing, and the JSONL/CSV import pipeline all already
  exist), with two quick wins folded in (timing-stats is a stats.js render
  addition against elapsed_ms already collected; the ADR index is the last WIP
  cleanup item). Cashes in the modularization; a safe re-warm-up.
  SCOPED + REVIEWED: the workflow prompts NARROWED this to ONE real feature
  (surface stored hints -- questions carry a hints list the payload never
  forwards) + two quick wins. Per-question-language-in-payload was DEMOTED (it
  is redundant with the client-side C-018a bank lookup; no consumer). The
  executable commit plan is llm/thread-N-vocab-plan.md (sort: hints -> timing
  stats -> ADR index, lead-with-meatier per user steer). Demoted/deferred vocab
  ideas live in llm/vocab-language-futures.md.
- Thread N+1: SM2 consolidation (roadmap #6) + adaptive selection (#7). Its own
  focused, schema-invasive thread; both plug the pure swappable pick_next_question
  seam. The SM2 scheduling-fields migration (reserved in ADR-025) lands here.
  DESIGN-FIRST: adaptive (B) and SM2 (C) are to be co-designed then shipped
  separately (B schema-free first, C the migration). Design handoff with all
  gathered facts + forks + instincts: llm/design-handoffs-BCDE.md (also covers
  D conversion pipelines and E authored content). The next SAFE build thread
  (schema-free stats-depth + JSONL export) is fully planned in
  llm/design-A-quick-consolidation.md.
- Thread N+2: Typing drill (#12). A deliberate net-new qtype -- the test of
  whether the modular seams absorb a genuinely new question kind cleanly. No
  typing infra exists yet beyond an empty "typing" config category stub.
- PARALLEL (ongoing): Study curriculum (roadmap #3) + the JS/Python/HTML/CSS
  coding-conventions formalization. Runs alongside the feature threads, auditing
  each thread's fresh code (per-file audit + encapsulation pass); it is the
  comprehension throttle, NOT a standalone phase. Operating doc:
  llm/study-curriculum-and-conventions.md (audit axes, the semantics-vs-
  conventions split, the drafted encapsulation rule + its first-pass audit
  result). FIRST THREAD AUDIT DONE: Thread N (S6 of that doc) -- two curriculum
  entries, one ratified convention (el-node ownership), one fix-backlog item
  (the DOM-mutation seam now has three named customers). See also
  CODING_CONVENTIONS.md.

The baseline SHA for Thread N is whatever this reassessment docs commit lands at
on main; a launch message pins it. Verify the clone matches before any work.

--------------------------------------------------------------------------------
HISTORY (the modularization arc, for reference)
--------------------------------------------------------------------------------
Modularization was sequenced after the arithmetic round (refactor code you
understand cold) and split around a quality pass:

- Phase A (current): foundation cleanup -- glob test discovery (done, C-2U-e),
  STATUS.md, CODING_CONVENTIONS.md, and drift reconciliation. Then archive the
  thread.
- Phase B: modularization (#1).
  ** THREAD ONE DONE (Phase 0 guards + lazy-el + BACKEND split). ** Commits
  C-MOD-C0.1..C0.3b, S10, D1..D4b. drill.py is now a 156-line MAIN composition
  root; config.py <- db.py <- logic.py <- http_layer.py is a verified one-way DAG
  (zero up-stack edges; nothing imports http_layer but drill). Suite 311 -> 317
  green (backend 197 -> 203 = the boundary-purity guard; frontend 114 unchanged).
  NEW BASELINE for thread two is the tip of thread one. Two plan-text deviations,
  detailed in llm/handoffs/2-to-frontend-cutover.md (F-1/F-2): the HTTP module is
  http_layer.py not http.py (a top-level http.py shadows the stdlib http package
  bottle imports); and the layout is flat top-level modules with thin-drill.py-
  as-MAIN (D-1), not a drill/ package -- so the plan's D5 "cut main.py" is
  satisfied-by-D4b (drill.py IS main; the drill:main entry point resolves).
  THREAD TWO (frontend build-alongside + atomic cutover + close-out) is NEXT;
  see llm/handoffs/2-to-frontend-cutover.md.
  ** THREAD TWO IN PROGRESS (frontend build-alongside). ** Commits C-MOD-E1..E8
  (+ C-MOD-E-naming). All ten frontend modules are extracted as clean ES modules
  and proven in isolation by option-(b) tests, WITHOUT touching index.html (R1
  duplicate-then-delete): state, api, timing (leaves); el (shared DOM leaf, an
  as-built module the plan did not enumerate); stage (ADR-053 relocation);
  speech; stats; session + drill (the ADR-053 cycle, landed as one commit); boot
  (entry module, top of the DAG). Suite 317 -> 528 green (frontend 114 classic
  unchanged + 211 new module asserts; backend 203 unchanged). The inline script
  in index.html is STILL authoritative and all 7 classic frontend tests still
  pass against it. The ONLY remaining frontend commit is E10, the atomic
  cutover, which is handed off fresh: llm/handoffs/3-to-E10-cutover.md.
  As-built deviations recorded there and in decisions.md: el.js is a 10th module;
  speech imports state+el (not state+stage); session imports speech+drill beyond
  the plan's list; the E4 owner-flip was reversed (choices/feedback stay drill-
  owned); the E10 guard is JS/acorn with a four-check design + a named boot-guard
  exemption to check D.
  The plan text below describes the whole of #1 and is preserved as reference.
- Phase B (plan text, as designed): extract index.html into ES modules
  (state/api/drill/session/stats/speech/timing/boot) and split drill.py into a
  package (config/db/logic/http/main), mirroring the existing one-way section
  boundaries. Behavior-preserving. FOLD the mechanical style sweep into each
  module extraction (apply CODING_CONVENTIONS.md to the code being touched), and
  add AST/lint guards (boundary purity; naming/idiom checks) so the conventions
  become structural rather than disciplinary. See handoff-modularization.md.
  DESIGN + SPIKES DONE (C-MOD-design); PLAN REVIEWED (C-MOD-review): the design
  survived adversarial-review and the sorted plan survived plan-review; the
  commit list is classified, topologically sorted, and thread-split. Read these
  before implementing:
    - llm/roadmap-1-modularization-findings.md -- spikes S1-S5 (design) + S6-S9
      (review addenda: the measured drill<->session cycle; the cycle resolves
      green under option (b) with the hoisting-vs-TDZ mechanism; reconfirmed
      analyzer false positives; naming debt is tiny and JS-only).
    - llm/roadmap-1-modularization-commit-plan.md -- SECTION R is the executable
      plan (classified/sorted/thread-split). The draft C/D/E below it is design
      rationale, superseded by R for sequencing.
    - decisions.md ADR-049..053 -- ADR-049/050 facts; ADR-051 (ownership registry,
      relabelled from "quarantine") + ADR-052 (R1) now DECIDED (pending status
      resolved by the review); ADR-053 NEW (accept the drill<->session cycle,
      Option A, + the pure-relocation stage.js).
  THREAD SPLIT: thread one = Phase 0 (guards + lazy-el) + backend (config, db,
  logic, http split in two, main); thread two = frontend build-alongside +
  atomic cutover + close-out. Zero dependency edges cross the seam; the cutover
  stays whole in thread two.
  Also landed this design arc: new/updated workflow prompts (adversarial-
  review lenses, spike-and-verify, plan-review, commit-planning co-load set,
  clone-and-verify parameterized baseline).
- Phase C: residual cross-module style sweep (whatever Phase B's per-module
  passes did not reach), then resume feature development on the roadmap's Tier-1
  remainder (curriculum #3, etc.).

================================================================================
KNOWN REMAINING GAPS (real, not yet addressed)
================================================================================
- qtype conflates prompt-kind with grading-kind. The true axis of variation is
  the GRADING kind {string-equality, numeric, speed, spatial, set/order}; every
  drill type projects onto the general prompt->answer record EXCEPT geography
  point-on-map (spatial). Addressed when a spatial or speed drill is built.
- run.sh glob is done, but the backend pytest side is still a directory run;
  no per-module test split exists yet (arrives naturally with modularization).
