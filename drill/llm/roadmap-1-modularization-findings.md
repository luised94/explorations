# Roadmap #1 Modularization -- Design Findings (spikes S1-S5)

Project-state-specific findings from the modularization DESIGN thread. These
are facts about THIS repo at THIS SHA, gathered to de-risk the commit plan
(see roadmap-1-modularization-commit-plan.md). They are NOT general LLM/prompt
strategy (that lives in knowledge-capture.md); they are the empirical basis the
plan rests on. The next thread should treat the FACTS here as settled and the
JUDGMENTS as recommended-but-open-to-plan-review. ASCII only.

Baseline for all spikes: SHA 72b52ad6452a7b79654460ce5fe4c5c12649b315, 311 green
(backend 197, frontend 114), Node v22, jsdom 26.1.1, ruff 0.15.20.

================================================================================
FACTS (settled -- not reversible by opinion; a spike measured them)
================================================================================

S1  jsdom does NOT execute <script type=module> -- neither inline nor external
    src -- at jsdom 26.1.1. Classic scripts (inline and external) DO run; a
    module script's source even leaked into textContent as inert text. Proven
    with a minimal probe against the real jsdom.
    CONSEQUENCE: the frontend cannot be tested by letting jsdom run the modular
    page. Test options that need boot.js to run under jsdom are DEAD:
      (a) boot.js hangs a window test-surface  -- dead
      (c) drive only through DOM events         -- dead
    Only option (b) survives.

S1b OPTION (b) WORKS: jsdom builds the DOM with runScripts:"outside-only";
    publish window+document as globals BEFORE importing; Node imports the real
    ES module through its own loader and drives it. Proven 4/4. This is the
    frontend mirror of the backend load_drill() pattern (import the real
    artifact by path, drive it).
    LATENT REQUIREMENT (proven): a module that touches the DOM at IMPORT TIME
    (top-level getElementById) throws on import unless globals pre-exist, and is
    fragile in the browser too (module scripts defer past parse). Rule minted:
    modules touch the DOM only INSIDE functions, never at import time.

S1c OPTION (b) fits a plain .test.js via async IIFE + dynamic import(); the
    run.sh glob (*.test.js) discovers it with ZERO run.sh changes. .mjs is NOT
    needed. Keep frontend test files as .test.js.

S2  BACKEND IS A CLEAN ONE-WAY DAG. AST census of drill.py: ZERO forward
    cross-section references. Legal backward refs only -- HTTP->DB (23),
    LOGIC->CONFIG (19), HTTP->LOGIC (12), DB->CONFIG (6), MAIN->DB (5). The
    package split (config<-db<-logic<-http; main wires) is a pure transcription
    of a boundary that already holds.
    ANALYZER LESSON (important for the guard): the first census run reported 3
    "violations", ALL false positives -- a parameter named leaf_count shadowing
    the LOGIC function; an arbitrary line-range bound misfiling two LOGIC
    functions. The real guard MUST be scope-aware (ignore params/locals) and
    assign layer by SYMBOL, not raw line number. Distrust the first analyzer
    result.

S3  FRONTEND state IS A CLEAN LEAF; el IS THE PROBLEM. state.* has ~22 writes,
    concentrated (phase x6, current x3, answerStartMark x3). state is safe to
    extract first. BUT a top-level `el` object caches 156 DOM nodes via
    getElementById AT IMPORT TIME -- it is both the biggest cross-module
    dependency AND a direct violation of the S1b import-time rule. el must
    become LAZY before any frontend module is importable under option (b).

S4  THE GUARDS WORK, BOTH DIRECTIONS.
    - Data-driven AST purity guard (policy as a TABLE, 13 rows, scope-aware):
      GREEN on the clean monolith; RED on an injected datetime.now() inside a
      LOGIC function. The injection used a FUNCTION-LOCAL `import datetime`,
      which a module-level import ban would MISS -- only the call-level AST
      check caught it.
    - Ruff flake8-tidy-imports banned-api + per-file-ignores: enforces
      import-direction declaratively (logic.py importing db FAILS; http_layer.py
      importing db PASSES via per-file relaxation).
    CONCLUSION: use BOTH. Ruff catches the import (cheap, declarative, pairs
    with `uv format`); the AST test catches the call (function-local dodges).
    Neither alone suffices; the injection proof shows why.

S5  THE FRONTEND TEST HARNESS IS ALL-OR-NOTHING COUPLED. All 7 frontend test
    files load the whole index.html and read win.state / win.submitAnswer /
    win.questionQuery / win.endSession -- names that exist ONLY because the
    classic inline script leaks its scope onto window. Flipping the <script> to
    type=module makes them ALL undefined at once (proven). So harness migration
    is NOT naively incremental-per-module: the first extraction that modularizes
    the tag breaks all 7 tests simultaneously.

================================================================================
JUDGMENTS (recommended -- open to plan-review; a lens could still overturn)
================================================================================

J1  DOM OWNERSHIP: registry-with-owner-tags, NOT module-prefixed IDs. el already
    IS a central name->node registry; give each entry an owner tag
    (logicalName -> {id, owner}) and a test asserts each getElementById id is
    owned by the referencing module. Rationale: no codebase-wide ID rename,
    single source, auto-enforced (a stale registry reddens the suite). Prefix-
    in-ID was the alternative (locality at use-site, but a rename and drift just
    relocates into the ID). Chosen because el's existence makes the registry the
    lower-churn, self-checking option.

J2  FRONTEND STRATEGY: R1 duplicate-then-delete, NOT R2 dual-load bridge. Build
    each ES module ALONGSIDE the untouched inline script; prove each with a new
    option-(b) test; the old 7 tests keep passing against the inline script
    until a single CUTOVER commit flips the tag, deletes the inline script,
    migrates the 7 tests, and lands the frontend guards. R2 (load modules also
    as classic scripts that assign to window) was rejected: dual-mode modules
    are a complection and risk divergence. R1's duplication is transient,
    visible, and removed atomically.

J3  EXTRACTION ORDER: dependencies first. Backend: config, db, logic, http,
    main. Frontend: state first (S3 clean leaf), then api, timing, speech,
    stats, session, drill, boot; cutover last. Each module = 2 commits (cut,
    then style); guards/data changes are their own commits, front-loaded.

J4  THE CUTOVER (frontend) is the one unavoidably-atomic, non-small commit. It
    is a candidate for the "let it go red" tool (commit-planning) since it
    reddens many tests at once by design -- but R1 keeps it delete+rewire+
    migrate (mechanical), not design, because every module already exists and is
    green via new tests before it lands.

================================================================================
DEFERRED (recorded here so the plan does not silently drop them)
================================================================================
- Thin DOM seam (Eskil quarantine): wrap the DOM behind named ops
  (setText/show/hide/makeButton) the way fetch and speechSynthesis already are,
  making the [hidden] guard impossible-to-violate-by-construction rather than
  merely linted. Deferred: it rewrites behavior at 156 sites (not relocation).
  Do it AFTER modularization, on already-separated modules. Its own roadmap item.
- Bulk-import bounding (the batch/yield/throttle pattern): insert_questions_bulk
  / parse_import have no batch size or row bound. Not a problem at single-user
  scale, but the one real place volume could bite. Drop an inert scaffold-comment
  when the split touches the import code; fix in its own thread.
- Functional/explicit DOM-state threading: REJECTED for this project -- fights
  the no-build, directly-manipulable, reload-is-truth property. The thin seam
  gets ~90% of the decomplection without the paradigm cost.

================================================================================
HOW THE NEXT THREAD USES THIS
================================================================================
1. clone-and-verify at the (new) baseline SHA (fill BASELINE_TOTAL from STATUS).
2. adversarial-review the DESIGN (boundaries, option-b, J1/J2) -- the facts
   above are givens; attack the judgments.
3. spike-and-verify is largely DONE (S1-S5); re-spike only if a review surfaces
   a new gating assumption.
4. commit-planning: classify (haiku/sonnet/opus), name edges, topo-sort, assign
   the co-load set per commit, decide the thread split (likely: Phase 0 + backend
   in one thread; frontend + cutover + close-out in another, so the atomic
   cutover stays whole).
5. plan-review the sorted plan (verification-honesty + thread-split lenses).
6. Execute; ADRs land after code per project convention (the design ADRs here
   are pre-recorded as DECIDED-pending-implementation in decisions.md).
