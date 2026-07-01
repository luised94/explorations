# Drill Tool -- STATUS (single source of truth for project state)

This file is the ONE place that records what is done, what is next, and the
current baseline. Other documents (roadmap.md, knowledge-capture.md,
thread-launch-kit.md, the handoffs) describe PLANS, CONVENTIONS, and RATIONALE
that change slowly; they must NOT restate live status -- they link here instead.
This is the project's anti-drift discipline (Nelson: single-source every fact)
made structural: when status changes, edit THIS file only.

ASCII only. Single-user assumption holds throughout.

Last updated: end of the UI-selector thread (C-2U-a..e + docs).

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
  work, and confirm 311 green on a clean clone before building.

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
- #20 Module docstring / status-drift cleanup + ADR index. THIS docs work
      (STATUS.md + CODING_CONVENTIONS.md + reconciling stale status across the
      doc set) is the bulk of #20. An ADR index is still outstanding and can be
      finished in or alongside the modularization thread.

================================================================================
NEXT (the phase map)
================================================================================
The next major checkpoint is MODULARIZATION (roadmap #1). It is sequenced after
the arithmetic round (score-vs-sequence: refactor code you understand cold) and
is split around a quality pass:

- Phase A (current): foundation cleanup -- glob test discovery (done, C-2U-e),
  STATUS.md, CODING_CONVENTIONS.md, and drift reconciliation. Then archive the
  thread.
- Phase B: modularization (#1) -- extract index.html into ES modules
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
- The ADR index (part of #20) is not yet written.
- run.sh glob is done, but the backend pytest side is still a directory run;
  no per-module test split exists yet (arrives naturally with modularization).
