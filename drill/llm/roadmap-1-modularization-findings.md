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
C-MOD-REVIEW ADDENDA (facts measured during adversarial-review + plan-review +
one new spike; the design's judgments survived, refined -- see ADR-051/052/053)
================================================================================
S6  THE FRONTEND HAS A REAL drill<->session CYCLE (not in the original design).
    Measured, comments stripped: drill.loadQuestion -> session.startSession +
    renderSessionUI; drill.gradeAndShow -> session.recordStats + renderSessionUI;
    session.onStartSession/onRestartSession -> drill.loadQuestion (these handlers
    are wired INSIDE renderSessionControls, so they are session-owned, not boot).
    The cycle is inherent to the domain (loading a question auto-starts a
    session; grading records to it). It does NOT dissolve by extracting shared
    helpers. Resolution: ADR-053 Option A (accept it) + a pure-relocation
    stage.js that thins the session-side edge down to just loadQuestion.

S7  THE CYCLE RESOLVES GREEN UNDER OPTION (b) -- SPIKED. Real Node v22 + jsdom,
    option-(b) harness, both import orders: 7/7 and 3/3 green. DURABLE MECHANISM:
    cross-cycle calls to HOISTED function declarations work at module-eval time;
    a cycle breaks ONLY if a module reads another's const/arrow export at eval
    time (proven RED via TDZ -- the both-directions check). The real script has
    ZERO module-level eval-time cross-references (only the boot-guard calling
    boot), so the "no eval-time cross-module use" condition holds across the
    WHOLE surface, not just the DOM (F2 generalizes). This is the cheapest
    knowledge the modularization bought; it is a candidate for knowledge-capture
    as a general ESM fact.

S8  ANALYZER FALSE POSITIVES, AGAIN (the S2 lesson, reconfirmed twice). A naive
    call-graph pass reported a speech->boot edge that was the word "isDrillable"
    inside a COMMENT; a naive el.<key> scan matched sel.bankId / label.className /
    el.importPanel.textContent. CONSEQUENCE for the J1 ownership guard: it MUST
    be scope-aware / symbol-based (strip comments, ignore member chains on other
    objects), never a substring grep -- exactly the discipline ADR-050 forced on
    the backend AST guard.

S9  NAMING DEBT IS TINY AND ONE-SIDED (census for the per-module style pass).
    Python (drill.py): ZERO abbreviation violations -- backend style commits are
    near-empty, so they COLLAPSE into their cut unless the check finds something
    (decision: no ceremony commits). Frontend: only two real abbreviations --
    `sel` (21 uses, local for state.selection) and a `cat` local (createElement
    span; the .run-cat/.stats-cat CSS class names are HTML identifiers and stay).
    The JS naming pass is small and lands in the style half of the modules that
    hold sel/cat (session, boot, stats).

================================================================================
S10  EXECUTION-SURFACED MEMBERSHIP FACTS (C0.1 guard, thread one) -- for D1/D2
================================================================================
The C0.1 boundary-purity guard, run on the monolith, surfaced two symbols whose
physical section does NOT match their true layer. Both must be honored by the
D-phase cuts; the guard encodes them today via a small LAYER_OVERRIDES table so
the clean file stays green. Neither is a redesign; both are membership calls.

S10a  MIGRATION FUNCTIONS ARE DATABASE, NOT CONFIG (contradicts the R-plan D1
      line "config gets MIGRATIONS"). _migrate_2_add_questions_metadata and
      _migrate_3_add_response_difficulty call connection.execute (DDL) -- pure
      DB operations that merely SIT in the CONFIG region for readability next to
      SCHEMA_VERSION. RESOLUTION (low complexity, no signature change): move the
      two functions, the MIGRATIONS registry, and _check_migration_version_
      consistency (+ its import-time call) into db.py as one cohesive unit ("the
      one place a schema change is expressed"); keep the SCHEMA_VERSION scalar in
      config.py. The version-consistency guard reads SCHEMA_VERSION from config
      (legal down-stack). run_migrations ALREADY injects `migrations=` and `now=`
      (clock stays out of DB), so nothing about the call path changes -- this is
      pure relocation. D1 puts SCHEMA_VERSION in config; D2 takes the migration
      unit.

S10b  THE OPERATOR TABLE IS CALLABLE-BEARING -> LOGIC, NOT CONFIG (refines the
      R-plan D1 line "config gets OPERATOR_DEFINITIONS"). OPERATOR_DEFINITIONS
      records carry eval_fn / operand_strategy CALLABLES (phase0.md already noted
      "a record carrying callables is not pure scalar data"). _build_operator_
      table + its validation constants (_OPERATOR_RECORD_REQUIRED_KEYS,
      _KNOWN_FORBID_IDENTITY_REFERENTS) are pure validation; every consumer
      (generate/evaluate/render/_child_needs_parentheses + one HTTP reader) is
      already LOGIC/HTTP. TWO options for D1, decision deferred to D1:
        (1) SIMPLEST: the whole operator system (DEFINITIONS, _build_operator_
            table, OPERATORS, the two validation constants) is LOGIC; config
            keeps only OPERATOR_SYMBOLS (strings) and the operand-range scalars.
            Zero new cross-edges (consumers are already logic). Matches "records
            carry callables => not config".
        (2) PARAMETERIZE (the "pass the data in" idea): make the builder pure of
            its inputs -- OPERATORS = _build_operator_table(OPERATOR_DEFINITIONS,
            OPERATOR_SYMBOLS) -- so the definitions are explicit data. Cleaner
            signature, but the definitions STILL carry callables, so it does not
            by itself make them config; it is a nice refinement that can fold
            INTO option (1). Recommendation: option (1), optionally with (2)'s
            signature tidy as a tiny same-cut refactor.
      Either way, the guard's current stance (operator system in LOGIC by
      physical position, no override needed for it) is already correct; only the
      migration functions needed an override entry.

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
