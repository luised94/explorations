# Handoff: roadmap #1 -- modularization THREAD TWO (frontend cutover + close-out)

Status: THREAD ONE (Phase 0 guards + lazy-el + the BACKEND split) is COMPLETE
and green. This hands off to THREAD TWO: the frontend build-alongside, the
atomic cutover to ES modules, and the roadmap-#1 close-out. Predecessor handoff
1b-to-execution.md launched thread one; it is kept for history.

Baseline for thread two: the tip of thread one (the commit that lands C-MOD-D4b
+ this handoff). A launch message pins the exact SHA. Verify the clone matches
and confirm 317 green ("ALL GREEN") on a clean clone before any work.

ASCII only. Single-user assumption holds. Behavior-preserving refactor: no
schema, no HTTP contract, no UI behavior change. The suite is the proof.

================================================================================
0. WHAT THREAD ONE DELIVERED (verified)
================================================================================
Backend fully split into a one-way layer DAG, drill.py reduced to a thin MAIN
composition root. Ten commits on top of the thread-one baseline:

  C-MOD-C0.1  scope-aware AST boundary-purity guard (tests/test_boundary_purity.py)
  C-MOD-C0.2  ruff import-direction config + `uv format` adoption (pyproject.toml)
  C-MOD-C0.3a lazy `el` DOM accessor (index.html)
  C-MOD-C0.3b DOM ownership registry EL_REGISTRY with owner tags (index.html)
  C-MOD-S10   findings note: migration-unit + operator-table membership facts
  C-MOD-D1    config.py extracted (CONFIG leaf)
  C-MOD-D2    db.py extracted (DATABASE) + migration unit relocated here (S10a)
  C-MOD-D3    logic.py extracted (LOGIC): arithmetic engine + general logic, one
              module, two `# === ... ===` sections (a clean future arithmetic.py
              seam; operator table lives here per S10b/D-2)
  C-MOD-D4a   http_layer.py: stateless request-helper preamble
  C-MOD-D4b   http_layer.py: app + DATABASE_PATH + all routes; drill.py is MAIN

Final backend shape (config <- db <- logic <- http_layer; main wires):
  config.py       499 lines   CONFIG leaf; imports nothing but __future__
  db.py           895 lines   DATABASE; imports config; owns the migration unit
  logic.py       1511 lines   LOGIC; imports config; arithmetic + general logic
  http_layer.py   690 lines   HTTP; imports config+db+logic; the Bottle app+routes
  drill.py        156 lines   MAIN root; imports config+db+http_layer; main()

Verified at close-out:
- Full suite 317 green, ends "ALL GREEN" (backend 203, frontend 114). The
  backend grew 197 -> 203: +6 from the boundary-purity guard (net; C0.1 added a
  guard, D-phase evolved it), no test lost.
- Actual cross-module import edges: zero up-stack; http_layer imported ONLY by
  drill.py (MAIN). "Nothing imports http except main" holds in shipped code.
- ruff check + `uv format --check` clean across all 14 files.
- End-to-end smoke: the assembled app boots and serves (GET /api/categories ->
  200 with 7 categories; GET /api/question -> 200). `drill = "drill:main"`
  entry point resolves.
- Clean-room jsdom resolved 29.1.1 (same as thread one's spikes noted).

================================================================================
1. THE FOUR HANDOFF REQUIREMENTS (from 1b Section 4) -- all satisfied
================================================================================
a) NEW BASELINE SHA: the pinned tip of thread one (317 green). Confirm on clone.

b) C0.1 IS THE TEMPLATE FOR THREAD TWO'S E10 OWNERSHIP GUARD. tests/test_
   boundary_purity.py is a scope-aware AST checker driven by data tables. Reuse
   its shape for E10 (assert each getElementById id is referenced only by its
   owning frontend module). It has ALREADY grown file-aware across the D-phase
   (it assigns layer by the module a symbol lives in, tolerates a layer's banner
   leaving drill.py, and checks cross-file import direction). Its injection
   RED-proofs (a guard that cannot fail is not a guard) are a pattern to copy:
   prove GREEN on clean code AND RED on an injected violation.

c) F1 (jsdom does not run type=module) -- RE-CONFIRM against thread two's clean-
   room jsdom. Thread one's clean room resolved jsdom 29.1.1, and the frontend
   tests still drive the CLASSIC inline <script> via `runScripts:"dangerously"`
   (verified: difficulty/drill/import/speech/stats.integration all do). The
   type=module cutover is thread two's; when it lands, F1 is the thing that
   forces the build-alongside + atomic-cutover approach rather than incremental
   module-by-module conversion. Re-run the F1 probe on the actual jsdom the
   thread-two clean room resolves before relying on it.

d) C0.3 (lazy el + registry with owner tags) IS IN PLACE. index.html has
   EL_REGISTRY (logicalName -> {id, owner}) with all 26 nodes owner-tagged
   across six modules (drill/boot/stats/session/stage/speech), and the lazy
   memoizing accessor reads ids from it. Every frontend module depends on this.
   The owner tags are INERT until E10 consumes them.

================================================================================
2. THREAD TWO'S JOB (unchanged from the reviewed plan)
================================================================================
- Read llm/roadmap-1-modularization-commit-plan.md SECTION R (E-series: the
  frontend module extractions E1-E9, the E10 ownership guard, the atomic
  cutover) and llm/roadmap-1-modularization-findings.md S6-S9 (the measured
  drill<->session cycle; it resolves green under option (b) with the hoisting-
  vs-TDZ mechanism; ADR-053 accepts the cycle, Option A).
- ADR-049..053 are the frontend contract. ADR-053 (the drill<->session cycle)
  is load-bearing for thread two -- read it, not just skim.
- Build the ES modules alongside the still-authoritative inline script, then
  ATOMIC cutover (the inline script stays authoritative until one commit flips
  index.html to type=module imports). The cutover must stay whole in one
  context -- do not begin it and pause.

================================================================================
3. FLAGS / DEVIATIONS FROM THE ORIGINAL PLAN (read before trusting plan text)
================================================================================
These are places the executed reality differs from what the plan/design docs
say. The docs below were written pre-execution; where they conflict with this
section, this section (and STATUS) win.

F-1  MODULE NAMED http_layer.py, NOT http.py. A top-level http.py shadows the
     stdlib `http` package that bottle imports (http.client), breaking import at
     runtime. The findings' S4 prototype already used http_layer for this reason;
     the R-plan's "http.py" (D4a/D4b lines), phase0.md, and roadmap.md "http.py"
     are SUPERSEDED. The guard LAYER_MODULES and the C0.2 ruff banned-api /
     per-file-ignores use http_layer.

F-2  FLAT TOP-LEVEL MODULES, NOT A `drill/` PACKAGE. D-1 (this thread) chose
     thin drill.py-as-MAIN with sibling top-level modules (config.py, db.py,
     logic.py, http_layer.py), NOT the `drill/` package with __init__.py that
     phase0.md sketches. The `drill = "drill:main"` entry point resolves to
     drill.py's main() and works unchanged. Consequence: D5 "cut main.py" as the
     plan specced it (a separate main.py inside a package) is EFFECTIVELY ALREADY
     DONE -- drill.py IS main. D5 is a no-op unless you deliberately want to
     rename drill.py -> main.py (not recommended; it would break the entry-point
     string and buys nothing). Recommend: mark D5 satisfied-by-D4b in the plan.

F-3  SUITE COUNT 311 -> 317 (not the plan's "312"). C0.1 landed as +5 pytest
     functions (3 invariant + 2 injection RED-proofs), not the +1 the 1b handoff
     estimated, because the both-directions proof (S4) needs the clean/injected
     pair stated explicitly. The D-phase then evolved the guard (retired a
     brittle monolith-era count assertion, added file-aware import-direction +
     purity-across-modules tests), netting backend 197 -> 203. Every commit is
     independently green; the count is truthful, not the doc's estimate.

F-4  D-4 TEST PATTERN ("tests import the submodule they exercise"). _support.py
     gained load_config/load_db/load_logic/load_http alongside load_drill.
     test_db/test_migrate load db (+ a load_config handle for QTYPE names not
     re-exported by db); test_logic/test_generator_property load logic;
     test_http loads http_layer. temp_db/current_db resolve DB SETUP
     (connect/init_db/run_migrations) from db.py -- not from the module under
     test -- because an HTTP module has connect (via route imports) but not
     init_db (a startup concern). The stats.integration FRONTEND driver likewise
     now loads db (setup) + http_layer (app + WSGI) instead of drill.py-as-whole-
     backend. Thread two's frontend module tests inherit this discipline.

F-5  S10 MEMBERSHIP FACTS, CONFIRMED IN EXECUTION. S10a: the migration unit
     (v2/v3 functions + MIGRATIONS + version guard) moved to db.py; SCHEMA_VERSION
     scalar stayed in config; db imports it (legal down-stack) and the import-
     time guard-weld still fires. S10b: the operator table + _build_operator_table
     + validation constants are LOGIC (callable-bearing); config keeps only
     OPERATOR_SYMBOLS + operand scalars. Both landed as pure relocation, no
     signature change. The C0.1 LAYER_OVERRIDES table (the two migration fns) is
     now moot on the monolith (they physically live in db.py) but the override
     mechanism remains in the guard for any future misfiling.

================================================================================
4. DOWNSTREAM CONCERNS (not blocking thread two, but track)
================================================================================
- ADR-052 still reads "[DECIDED, pending plan-review]" in decisions.md; plan-
  review is done. Drop the "pending plan-review" qualifier when convenient.
- The plan docs (phase0.md, roadmap.md, commit-plan D4/D5 lines) still say
  "http.py" / "main.py inside a package". They describe intent and are left as
  history; F-1/F-2 above are the corrections of record. If you touch those docs,
  fix in passing; otherwise STATUS + this handoff are authoritative.
- logic.py is 1511 lines with a clean internal arithmetic/general seam. If it
  ever earns a split, arithmetic.py is the extraction point (zero cross-section
  references, measured). Not needed now; recorded so the seam is not lost.
- The guard's injection RED-proofs now target logic.py (clock) and config.py
  (up-stack import). If a future cut removes those exact targets, update the
  injections (they assert loudly with a "update the injection" message).

================================================================================
5. WORKFLOW CONTRACT (standing; unchanged)
================================================================================
At each commit boundary: edit in-sandbox, run `bash tests/run.sh` (bash, not
sh), COMMIT in-sandbox, then deliver the TRIPLE: (a) SUMMARY + files-modified;
(b) PATCH = git diff <prev_sha> HEAD rooted at drill/..., verified to APPLY in a
fresh clone at the pinned SHA with the full suite re-run there (verify the green
COUNT, not just the banner); (c) COMMIT MESSAGE: type(scope): subject; bulleted
body; suite-delta line; commit tag. One patch per commit; NO push.
