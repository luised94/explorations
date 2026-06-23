# Drill Tool -- Thread Launch Kit

Everything needed to start each work thread cleanly, in the right order, with
the conventions we have used since C-001. Copy the prompts verbatim; they
encode the discipline so each fresh thread behaves consistently.

How to use this file:
1. Put the **Reusable Context Block** (Section 1) into Settings > Profile >
   user preferences once. It then applies to every thread automatically.
2. For each thread, start a new conversation, attach the listed files, and
   paste the thread's **starter prompt** (Section 3).
3. Follow the **launch order** (Section 2): start Wave 0 threads now; later
   waves unlock as their dependencies land.

ASCII only, consistent with the project.

---

## 1. Reusable Context Block (paste into user preferences once)

> I am developing a single-user practice/drill tool (Python + Bottle backend in
> drill.py, vanilla JS/HTML/CSS frontend). Apply these standing rules to all of
> our work on it:
>
> Engineering philosophy: data-oriented; apprehensive of abstraction and
> indirection; pure transformations at the core with IO quarantined at the
> edges. No classes, DAOs, service layers, dependency injection, or ABCs unless
> a concrete duplication forces it -- prefer module-level functions over plain
> data (dicts, lists, strings, numbers). Do not abstract, reify, or generalize
> prematurely: build the concrete case, and only extract a seam once two real
> uses reveal the shared shape. Single-user always (no concurrency, auth, or
> pooling concerns).
>
> Layering invariant (must hold): CONFIG holds scalars only; DATABASE is IO over
> a sqlite connection with no logic; LOGIC is pure (no IO/DB/HTTP); HTTP is thin
> glue and the only layer that reads the clock; data crosses boundaries as plain
> dicts/lists/scalars. DATABASE never calls LOGIC/HTTP; LOGIC never calls
> DATABASE/HTTP.
>
> Working agreement: produce code only when I explicitly ask and cite a commit
> ID; generate only what that commit describes (do not anticipate future
> commits); when modifying a file, produce the complete updated file; mark
> changes with commit-ID comments; if the spec seems wrong or incomplete, raise
> it before coding; keep DECISIONS.md updated by appending non-spec decisions
> and flags per commit. Verify every commit with a real test (jsdom for
> frontend, WSGI-over-temp-DB for backend) and report pass/fail before I accept.
>
> Output rules: all code and prose ASCII only. Be concise. Before writing code,
> read the relevant section of the attached spec and DECISIONS so you match the
> existing patterns rather than inventing new ones.

---

## 2. Launch order (topological waves)

Computed from the dependency DAG (dependency_plan.mermaid). Threads in the same
wave have no dependency on each other and can run in parallel. A thread unlocks
when every thread feeding it has landed.

```
Wave 0 (start now, fully parallel):
  DONE THREAD-TEST     tests + safety net      (T1)   <- do this one FIRST of the wave
  THREAD-MIGRATE  migration runner         (T2)
  THREAD-DOCS     docstring/ADR cleanup    (T3)
  THREAD-ARITH    arithmetic operators     (A1)  (can start; A2 waits on TEST)
  THREAD-REVIEW   mistake-review at run end(X1)
  THREAD-GRID     minimal mastery grid     (X2)

Wave 1 (unlocks after its dep lands):
  THREAD-ARITH    nested generator (A2)         needs TEST(T1) + A1
  THREAD-MODEL    grading-kind + metadata (D1)  needs MIGRATE(T2)
  THREAD-MODFE    frontend ES modules (M2)      needs TEST(T1)

Wave 2:
  THREAD-ARITH    difficulty mapping (A3)       needs A2
  THREAD-LOGICDR  logic drill (X3)              needs MODEL(D1)
  THREAD-CODEDR   code drill (X4)               needs MODEL(D1)

Wave 3:
  THREAD-MODBE    backend package (M1)          needs TEST(T1); soft-prefers A3
  THREAD-TUNER    difficulty tuner (S4)         needs A3
  THREAD-TYPING   typing + timed mode (X5)      needs A3

Wave 4:
  THREAD-SCHED    adaptive scheduler (S1)       needs MODBE(M1) + MODEL(D1)
  THREAD-SM2      SM2 scheduler (S2)            needs MODBE(M1)
  THREAD-CURRIC   curriculum (C1)               needs MODBE(M1) + MODFE(M2)

Wave 5:
  THREAD-SCHED    extract select_next seam (S3) needs S1 + S2 (Muratori: after both)
  THREAD-CURRIC   concept-review bank (C2)      needs SM2(S2) + C1

Wave 6:
  THREAD-SESSION  plan_session/config (SC)      needs S3
```

Practical advice on concurrency: you are one person, so "parallel" means
"these can be separate threads you switch between without blocking," not
literally simultaneous. The highest-throughput path is to run **TEST first**
(it is the safety net everything leans on), then keep ARITH and one of
MODEL/MODFE going as your two active threads, since they rarely touch the same
code.

The one soft edge: MODBE (backend modularization) only hard-needs the tests.
The "do an arithmetic round first" link is a preference (you refactor code you
just touched and understand), not a true dependency -- if you would rather
modularize earlier, you can, as long as the tests exist.

---

## 3. Per-thread starter prompts

Each prompt is self-contained. Attach the listed files, paste the prompt. Every
prompt assumes the Reusable Context Block is already in your preferences.

Commit-ID scheme for the next phase (continue the C-0xx line, new range to keep
threads from colliding): tests C-020, migrate C-021, docs C-022, arithmetic
C-023..C-025, data model C-026, modularize C-027 (FE) / C-028 (BE), drills
C-029 (logic) / C-030 (code) / C-031 (typing), schedulers C-032..C-035,
curriculum C-036..C-037, mistake-review C-038, mastery grid C-039. Adjust
freely; the point is each thread owns a disjoint ID range.

---

### THREAD-TEST (C-020) -- start first
THREAD-TEST (T1) DONE - tests/ suite, 159 assertions green (backend 84: logic 35, http 40, db 7, property 2; frontend 75). Baseline for all post-merge "re-run the suite" checks. Unlocks A2, M2, M1.
Attach: drill.py, index.html, spec.md, decisions.md, PHASE0_PLAN.md

> Commit C-020. Per PHASE0_PLAN.md Section B, set up the permanent test suite by
> recovering the throwaway harnesses we have been writing. Create a tests/
> directory: test_logic.py (pure LOGIC -- generator validity incl. integer
> results and no forbidden identities, validate_answer, summarize_correctness,
> summarize_stats, pick_next_question), test_db.py (DATABASE over a temp DB --
> insert/read round-trips, get_responses_for_stats filters, elapsed_ms
> persistence), test_http.py (WSGI against the app + temp DB -- every endpoint
> and its 400s), and a run.sh runner. Reuse the patterns from the harnesses in
> our prior work. Add one targeted property-based test (hypothesis) for the
> arithmetic generator invariants. Do not test Bottle/sqlite/the DOM
> themselves. Scope is the harness only -- no behavior changes to drill.py.
> Report the pass count.

Post-merge protocol (all threads touching tested code): after merging into the integration branch, run bash tests/run.sh from the merged tree (not just the feature branch). Expect 159 green. A red test is a real contract change to reconcile, not a merge artifact. If a thread deliberately changes a pinned contract, update the test and note it in decisions.md in the same commit.

### THREAD-MIGRATE (C-021)
Attach: drill.py, spec.md, decisions.md, PHASE0_PLAN.md

> Commit C-021. Add a version-aware schema migration runner per PHASE0_PLAN.md
> Section B / roadmap item #11. The schema_version table already exists; add a
> migrate(connection) that reads the current version and applies ordered
> ALTER-style steps to reach SCHEMA_VERSION, idempotent and safe to call on
> every startup (alongside init_db). For now there are zero migrations to apply
> (we are at v1) -- the deliverable is the runner mechanism plus the registry
> structure and a test proving a no-op on a current DB and a stepwise upgrade on
> a simulated older one. This is the foundation the data-model thread (C-026)
> will use to add the questions.metadata column. Raise any boundary concerns
> before coding.

### THREAD-DOCS (C-022)
Attach: drill.py, spec.md, decisions.md

> Commit C-022. Documentation-only pass per roadmap item #20. Reconcile stale
> status lines so the docs are the single source of truth: the drill.py module
> header, the section comments, and an ADR index appended to DECISIONS.md that
> lists every ADR/commit decision with a one-line summary and anchor. No code
> changes -- prove it with an AST-equality check against the prior drill.py
> (only docstrings/comments may differ). ASCII only.

### THREAD-ARITH (C-023, C-024, C-025) -- sequential within the thread
Attach: drill.py, spec.md, decisions.md, PHASE0_PLAN.md
Note: start C-023 now; C-024 after THREAD-TEST lands (it needs the generator tests).

> Commit C-023. Per PHASE0_PLAN.md Section D step 1, add new arithmetic
> operators (exponentiation and modulo) by adding entries to OPERATOR_CONFIG
> and the LOGIC operator table -- data plus one generate/eval/render hookup
> each, no structural change (the evaluator/renderer already handle any
> registered operator). Mind operand ranges: cap exponent growth; modulo needs
> a non-zero divisor and is only interesting when a > b. Add tests for the new
> operators' invariants. Then stop and report; C-024 (nested generator) and
> C-025 (difficulty) are separate commits I will request next.

### THREAD-MODEL (C-026)
Attach: drill.py, spec.md, decisions.md, PHASE0_PLAN.md
Prereq: THREAD-MIGRATE (C-021) landed.

> Commit C-026. Per PHASE0_PLAN.md Section F, do the data-model design pass
> before we add drill types. (1) Name a grading-kind enum (string-equality,
> numeric, speed, spatial, set/order) and make validate_answer dispatch on it --
> it already special-cases arithmetic, so this names the existing pattern rather
> than adding a hierarchy. (2) Add a per-question metadata JSON column to the
> questions table via the C-021 migration runner (banks have metadata; questions
> do not). (3) Confirm every current qtype maps to a grading kind and document
> which future types use the JSON slot (logic premises, spatial targets). No new
> class hierarchy. Raise any boundary concern first. Tests for the dispatch and
> the migration.

### THREAD-MODFE (C-027)
Attach: index.html, spec.md, decisions.md, PHASE0_PLAN.md
Prereq: THREAD-TEST (C-020) landed.

> Commit C-027. Per PHASE0_PLAN.md Section A, split index.html's single script
> block into ES modules (state.js, api.js, drill.js, session.js, stats.js,
> speech.js, timing.js, boot.js) loaded via <script type="module">. No build
> step, no framework. State stays a single shared object imported where needed
> -- do NOT turn it into a store/observable. index.html keeps markup + CSS and
> one module script tag. Behavior must be identical: prove it by running the
> existing jsdom suites unchanged against the modular version. Note the file://
> CORS caveat (must be served, which it already is).

### THREAD-MODBE (C-028)
Attach: drill.py, spec.md, decisions.md, PHASE0_PLAN.md
Prereq: THREAD-TEST (C-020) landed. Soft-prefer after C-025.

> Commit C-028. Per PHASE0_PLAN.md Section A, split drill.py into a package
> (config.py, db.py, logic.py, http.py, main.py) one-to-one with the existing
> sections, preserving the layering invariant via import direction (http imports
> db+logic; logic imports config; db imports config; nothing imports http). Move
> the four coupling points (OPERATORS table to logic; app + DATABASE_PATH +
> _MODULE_DIRECTORY to http; main rebinds DATABASE_PATH). No classes, no
> re-export hub in __init__. Behavior identical: the full test suite (C-020)
> must pass unchanged. Report results.

### THREAD-LOGICDR (C-029) / THREAD-CODEDR (C-030)
Attach: drill.py (or the package if C-028 landed), index.html, spec.md, decisions.md, PHASE0_PLAN.md
Prereq: THREAD-MODEL (C-026) landed.

> Commit C-029 [or C-030]. Add a logic/deduction drill [or code "what does this
> output?" drill] as a new bank type that projects onto the general question
> record (PHASE0_PLAN.md Section F): prompt + string-equality grading, using the
> grading-kind enum from C-026, with structured content (premises / snippet) in
> the question metadata JSON slot. Reuse the existing text/multiple_choice
> rendering; code drill wants <pre> rendering for the snippet. No new grading
> machinery beyond what C-026 established. Include a small sample bank and tests.

### THREAD-TUNER (C-032) -- difficulty tuner
Attach: drill.py (or package), spec.md, decisions.md, PHASE0_PLAN.md
Prereq: arithmetic difficulty (C-025) landed.

> Commit C-032. Per PHASE0_PLAN.md Section E, add a pure difficulty tuner:
> next_difficulty(recent_accuracy, current_level) -> level, a simple
> proportional controller (raise on a hot streak, lower on misses) feeding the
> C-025 difficulty_to_params mapping. Pure LOGIC, fully unit-tested across
> accuracy ranges. Do not wire it into selection yet -- that is the scheduler
> thread. Just the controller + tests.

### THREAD-SCHED (C-033 adaptive, then C-034 seam)
Attach: drill.py (or package), spec.md, decisions.md, PHASE0_PLAN.md
Prereq: C-028 + C-026. The seam commit (C-034) also needs SM2 (C-035).

> Commit C-033. Per PHASE0_PLAN.md Section E and the Muratori note, implement an
> adaptive-by-accuracy scheduler CONCRETELY -- a pure function that weights
> selection toward low-recent-accuracy items, taking exactly the inputs it needs
> (do NOT design a generalized context object yet). It replaces random selection
> behind the existing pick_next_question seam. Tests over crafted item-stat
> sets. Stop after this; the generalized select_next seam is C-034, to be
> extracted only after SM2 (C-035) also exists so the shared shape is real.

### THREAD-SM2 (C-035)
Attach: drill.py (or package), spec.md, decisions.md, PHASE0_PLAN.md, plus your SM2 source files
Prereq: C-028. Bring your existing SM2 code into this thread.

> Commit C-035. Per PHASE0_PLAN.md Section E, integrate my existing SM2 spaced-
> repetition engine as a scheduler behind the selection seam. SM2 is a selection
> policy: it reads each item's ease/interval/last-review and decides what is due.
> Map its state onto per-item fields (use the C-026 metadata slot or a dedicated
> review table -- recommend which, and raise it before coding). Keep it a
> concrete implementation; the shared seam with the adaptive scheduler is
> extracted later (C-034). I will attach my SM2 files to this thread.

### THREAD-CURRIC (C-036, C-037)
Attach: drill.py (or package), index.html (or app/ modules), spec.md, decisions.md, PHASE0_PLAN.md, ROADMAP.md
Prereq: C-027 + C-028 (modular code makes lessons map to files).

> Commit C-036. Per PHASE0_PLAN.md Section C, generate the self-study curriculum.
> It must LINK INTO the real code and DECISIONS by anchor (Nelson's rule -- never
> copy/restate, so it cannot drift). Structure per the module list in Section C
> (Orientation through Capstone), each module: read (worked example) -> explain
> (Feynman) -> extend (a real, effortful exercise). Ground it in the learning-
> science basis stated there. Output as markdown linked to file/section anchors.
> C-037 (the concept-review SM2 bank built from DECISIONS) is a separate commit.

### THREAD-REVIEW (C-038) -- mistake review
Attach: index.html (or app/ modules), drill.py, spec.md, decisions.md, PHASE0_PLAN.md

> Commit C-038. Add end-of-run mistake review (PHASE0_PLAN.md Section G new
> features): at session end, show the items missed this run and offer to drill
> just those. The run log already holds the data, so this is mostly frontend.
> Keep it separate from the live stats bar and the stats view. Tests via jsdom.

### THREAD-GRID (C-039) -- minimal mastery grid (Victor)
Attach: index.html (or app/ modules), drill.py, spec.md, decisions.md, PHASE0_PLAN.md, ROADMAP.md

> Commit C-039. Per the Victor reprioritization (PHASE0_PLAN.md Section G), build
> a MINIMAL mastery grid: a static grid of banks colored by accuracy (from
> /api/stats), each cell clickable to start drilling that bank. Not the full
> explorable Mode D -- the minimal seed only. Text/CSS-grid, no charting lib.
> Reuse the stats endpoint. Tests via jsdom.

---

## 4. Quick-reference: what to attach to (almost) every thread

The standing four -- spec.md, decisions.md, drill.py (or the package once
C-028 lands), index.html (or app/ modules once C-027 lands) -- plus
PHASE0_PLAN.md for any thread doing design work. ROADMAP.md only for the
curriculum and grid threads (they reference the prioritization). Add
thread-specific files (your SM2 source) where noted.

Once C-027/C-028 land and the code is modular, attach only the specific modules
a thread touches, not the whole tree -- smaller context, sharper work.
