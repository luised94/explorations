# Roadmap #1 Modularization -- Commit-by-Commit Plan (design artifact)

STATUS: DESIGN. No code landed yet. This is the plan to execute, grounded in
the spike battery run this thread (results below). ASCII only. Single-user.

Baseline verified: SHA 72b52ad6452a7b79654460ce5fe4c5c12649b315, 311 green
(backend 197, frontend 114). Every commit below states before/after counts and
re-verifies in a fresh clone. Delivery is git-apply-able patches; no push.

================================================================================
A. WHAT THE SPIKES ESTABLISHED (facts the plan rests on)
================================================================================
S1 (jsdom module execution): jsdom 26.1.1 does NOT execute <script type=module>
   -- neither inline nor external src. Classic scripts DO run. Proven both ways.
   => The frontend test harness cannot rely on the runtime executing the page
      once it is modular. Test options (a) window-seam and (c) drive-by-events
      are DEAD (both need boot.js to run under jsdom). Option (b) is FORCED.

S1b (option b works): jsdom builds the DOM with runScripts:"outside-only";
   publish window+document as globals BEFORE import; Node imports the real ES
   module and drives it. Proven 4/4. This is the frontend mirror of the backend
   load_drill() pattern -- import the real artifact by path, drive it directly.

S1c (option b, inside a .test.js): async IIFE + dynamic import() works in a
   CommonJS .test.js. run.sh glob (*.test.js) discovers it with ZERO changes.
   .mjs is NOT needed. Keep test files as .test.js.

S2 (backend DAG): AST census of drill.py -> ZERO forward cross-section refs.
   Legal backward refs only: HTTP->DB(23), LOGIC->CONFIG(19), HTTP->LOGIC(12),
   DB->CONFIG(6), MAIN->DB(5). The package split is a pure transcription.
   Caveat learned: a naive AST checker produced 3 false positives (a parameter
   named leaf_count shadowing a LOGIC fn; a bad line-range bound). The real
   guard MUST be scope-aware (ignore params/locals) and assign layer by SYMBOL,
   not raw line number.

S3 (frontend state): state.* has ~22 writes, concentrated (phase x6). state is
   a clean shared-data leaf -> safe first extraction. BUT: a top-level `el`
   object caches 156 DOM nodes via getElementById at IMPORT TIME. Eager DOM
   access breaks option (b) (throws unless globals pre-exist) and is fragile in
   the browser (module scripts defer past parse). `el` must become LAZY.

S4 (guards): a DATA-DRIVEN AST purity guard (13 policy rows, generic checker)
   is GREEN on the clean monolith and PROVEN RED on an injected
   `datetime.now()` inside a LOGIC function (a violation a module-level import
   ban would MISS, because the injection used a function-local import).
   Ruff flake8-tidy-imports banned-api + per-file-ignores enforces
   import-direction declaratively (logic.py importing db FAILS; http_layer.py
   importing db PASSES via per-file relaxation). CONCLUSION: use BOTH -- ruff
   for import-direction (declarative, pairs with `uv format`), AST test for
   call-purity (in the suite, portable to the clean room). They catch different
   things; the injection proof shows neither alone suffices.

S5 (harness coupling -- the decisive finding): ALL 7 frontend test files load
   the whole index.html and read win.state / win.submitAnswer / win.questionQuery
   / win.endSession -- names that exist ONLY via the classic script's global
   leak. Flipping the <script> to type=module makes them all undefined AT ONCE.
   => Harness migration is NOT incremental-per-module in the naive sense. The
      resolution (S2' below) is to build the module tree ALONGSIDE the untouched
      inline script, prove each module with new option-(b) tests, and flip
      index.html to modules (deleting the inline script + migrating old tests)
      in a single cutover commit -- AFTER all modules exist and are tested.

================================================================================
B. SEQUENCING PRINCIPLE
================================================================================
Front-load DATA and GUARDS (low-risk, high-leverage, protect everything after),
THEN backend modularization (pure transcription, verified DAG), THEN frontend
(the harder half: build-alongside then cut over). Each module extraction is
2 commits (cut, then style) per the discipline; guards/data changes are their
own commits. "Cut" = verbatim relocation + import/export plumbing ONLY. "Style"
= renames (nvim quickfix, word-boundary, confirm) + docstrings + assert splits;
formatting is already handled by `uv format`, so the Python style pass is
naming/docstrings/asserts only.

CONTEXT-BUDGET NOTE (LLM assistance): each commit lists the files that must be
co-loaded to execute it. A commit is "too big" if that set is too big -- this
operationalizes "keep commits at/below sonnet complexity". Modules are sized to
be individually loadable-and-editable in one thread.

================================================================================
C. PHASE 0 -- GUARDS AND DATA (front-loaded, before any extraction)
================================================================================
C0.1  test(guard): data-driven boundary-purity guard, on the MONOLITH.
      - Add tests/test_boundary_purity.py: scope-aware AST checker driven by a
        policy TABLE (forbidden call-substrings per layer). Pre-split, layer is
        assigned by the confirmed section line-ranges; the table is the policy.
      - GREEN on current drill.py (proven in S4). This is the instrument that
        protects every later extraction: a bad cut that drags a clock/db/bottle
        call into LOGIC goes red immediately.
      - Suite: 311 -> 312. Co-load: drill.py, the new test.
C0.2  chore(lint): ruff for import-direction (declarative), + adopt `uv format`
      as the formatting authority.
      - Add [tool.ruff.lint] TID251 banned-api + per-file-ignores to
        pyproject.toml. Pre-split this is inert (one module) but LANDS THE
        POLICY AS DATA so the backend split inherits it. Document that
        `uv format` owns formatting (shrinks the style pass to naming/docstrings).
      - Suite unchanged (311 or 312). Co-load: pyproject.toml.
C0.3  feat(frontend-data): make `el` LAZY + introduce the DOM registry (data).
      - This is the S3-mandated change and the home of the registry decision.
      - index.html inline script: replace the eager `var el = {..getElementById..}`
        with a single registry object mapping logicalName -> elementId (DATA),
        and a lazy accessor that resolves nodes on first use (after DOM exists).
        NO behavior change: same nodes, same call sites (el.answer still works,
        now lazily). This is a data+adjustment change, not modularization.
      - Registry carries owner tags (logicalName -> {id, owner}) so a later test
        can assert module ownership WITHOUT an ID rename (the chosen approach).
      - Behavior-preserving: all 311 stay green (old tests still run the classic
        inline script, now with lazy el). Co-load: index.html, the frontend tests.
      NOTE: this commit is frontend but lands in PHASE 0 because it is a data
      adjustment that unblocks option (b) for every later frontend module.

================================================================================
D. PHASE 1 -- BACKEND MODULARIZATION (pure transcription; verified DAG)
================================================================================
Target package (mirrors sections; import direction is the contract):
   config <- db <- logic <- http ; main wires. Nothing imports http.
Order: config, then db, then logic, then http, then main (dependencies first).
Each module = 2 commits (cut, style). The purity guard (C0.1) and ruff (C0.2)
re-run every commit; post-split the guard's layer-of-symbol switches from
line-range to "the file it lives in" (table unchanged).

D1  config  (cut / style)  -- scalars, QTYPES, DIFFICULTY_RUNGS, SCHEMA_*,
    MIGRATIONS, OPERATOR_DEFINITIONS constants. Leaf; imports nothing internal.
D2  db      (cut / style)  -- connect, migrations, CRUD, row->dict readers,
    utc_now_iso. Imports config only. Decide: tests import package or submodule
    (D-MOD-3); keep WSGI drive path working.
D3  logic   (cut / style)  -- generators, evaluator, validate, parse, summaries,
    pick_next_question, build_question_payload. Imports config only. The purity
    guard is now ENFORCEABLE per-file (S4).
D4  http    (cut / style)  -- app, route handlers, request helpers. Imports
    db+logic. BIGGEST module; if the cut exceeds sonnet complexity, split the
    cut across 2 commits (handlers group A / group B) rather than one heavy one.
D5  main    (cut / style)  -- entrypoint/bootstrap. Imports db+http.
Co-load per commit: the module being cut + its source region in drill.py + its
test + conventions. Never the whole package.

================================================================================
E. PHASE 2 -- FRONTEND MODULARIZATION (build-alongside, then cut over)
================================================================================
Resolution of the S5 coupling: extract modules into files that Node can import
(option b) while index.html KEEPS its working inline script. Prove each new
module with a NEW option-(b) .test.js (glob-discovered, run.sh untouched). The
old 7 tests keep passing against the untouched inline script the whole time.
Only at the end do we flip index.html to modules and migrate the old tests.

Target modules (convention order): state, api, drill, session, stats, speech,
timing, boot. Dependency-first, state first (S3).

E1  state   (cut / style)  -- STREAK_PIPS_MAX, RECENT_MAX, ZERO_STATS, state.
    Pure data, no DOM. New option-(b) test proves it (spike did this 4/4).
    index.html inline script now IMPORTS nothing yet -- state.js is extracted
    but the inline copy is removed and the inline script will need state; see
    cutover note. To keep 311 green pre-cutover, the inline script retains its
    own copy until E9 OR state.js is loaded as a classic script bridge.
    DECISION POINT E-BRIDGE (below) resolves how the inline script sees state
    during the alongside phase.
E2  api      (cut / style)  -- apiGet/apiPost/readJson (fetch wrappers). Imports
    nothing DOM. Thin, per server-returns-facts.
E3  timing   (cut / style)  -- nowMs + timing helpers (performance.now wrapper).
E4  speech   (cut / style)  -- speak/cancelSpeech/speaker visibility (the
    speechSynthesis quarantine). Leaf-ish; imports state.
E5  stats    (cut / style)  -- renderStats/streak pips/run log/figure.
E6  session  (cut / style)  -- startSession/recordStats/endSession/session UI.
E7  drill    (cut / style)  -- question render/answer/feedback/phase machine.
E8  boot     (cut / style)  -- wiring, event listeners, initial boot, lazy-el
    init call. This is where DOM listeners attach.
E9  CUTOVER (single commit): index.html <script> becomes
    <script type=module src=static/boot.js>; delete the inline script; migrate
    the 7 original tests to option (b); land the frontend ownership guard
    (registry owner-tags -> test asserts each getElementById id is owned by the
    referencing module) and the "no DOM access at import time" AST guard.
    Suite: same tests re-expressed + new guards; >= 311.

E-BRIDGE decision (resolve before E1): during the alongside phase, how does the
still-inline script use the extracted code? Two viable routes, both keep 311
green:
  (R1) Duplicate-then-delete: the inline script keeps its own copy of each
       extracted piece until E9 deletes the whole inline script wholesale. The
       extracted modules are proven by NEW tests only. Simple, but the code
       lives twice between E1 and E9 (acceptable: transient, deleted atomically).
  (R2) Classic-script bridge: load each extracted module ALSO as a classic
       <script> (non-module) that assigns to window, so the inline script reads
       the extracted copy. Avoids duplication but requires the modules to be
       dual-loadable (classic + ESM), which is awkward and risks divergence.
  RECOMMENDATION: R1 (duplicate-then-delete). The duplication is transient,
  visible, and removed in one atomic cutover; it keeps each extracted module a
  CLEAN ES module (not dual-mode) and keeps every commit green. R2's dual-load
  is a complection we do not want.

================================================================================
F. PHASE 3 -- CLOSE-OUT
================================================================================
F1  ADRs: record D-MOD-1..4 resolved (order backend-first-then-frontend; option
    (b) forced by jsdom S1; backend tests import submodules; commit granularity
    2/module + R1 alongside strategy). Land AFTER code (project convention).
F2  Update STATUS.md (new green count, new layout), roadmap.md (#1 DONE),
    knowledge-capture.md (the jsdom S1 fact; the registry+owner-tag pattern; the
    "no DOM at import time" convention; the duplicate-then-delete strategy),
    decisions.md (guards-as-data, registry approach).
F3  CODING_CONVENTIONS.md: add the HTML/CSS section (9 rules, gap-anchored) now
    that option (b) is settled and phrasing for rules 3/6 is fixed.

================================================================================
G. DEFERRED (recorded, NOT done here -- separate roadmap items)
================================================================================
- Thin DOM seam (Steenberg/quarantine): wrap the DOM behind named ops
  (setText/show/hide/makeButton) the way fetch and speechSynthesis already are,
  making the [hidden] guard structural (impossible-by-construction, not linted).
  Deferred: it is behavior-rewriting at 156 sites, not relocation. Do it AFTER
  modularization so the seam is added to already-separated modules.
- Bulk-import bounding (the Zotero-export pattern): insert_questions_bulk /
  parse_import have no batch size or row bound. Not a problem at single-user
  scale now, but the one real place volume could bite. Record an inert
  scaffold-comment when E/D touches the import code; fix in its own thread.
- Functional/explicit DOM-state threading: rejected for this project (fights the
  no-build, directly-manipulable, reload-is-truth property). The thin seam gets
  ~90% of the decomplection without the paradigm cost.

================================================================================
H. RISK / COMPLEXITY TABLE (for the eventual concrete-plan review)
================================================================================
Lowest risk : C0.1, C0.2, D1(config), E1(state) -- pure data/leaf, proven.
Medium      : D2(db), D3(logic), E2-E7 -- transcription with import plumbing.
Highest     : D4(http, biggest -- may split), E9(cutover -- atomic, touches all
              7 tests + index.html + adds guards). E9 is the one commit that is
              NOT small; mitigate by having every module already extracted and
              green via new tests BEFORE E9, so E9 is delete+rewire+migrate, not
              design.
