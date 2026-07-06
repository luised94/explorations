# Design-Thread Handoffs -- B+C (adaptive+SM2), D (conversion), E (authoring)

STATUS: HANDOFF for DESIGN threads (not implementation). Each section below is
the starting kit for a PLANNING/STRATEGY thread that will produce a design doc
(the way design-A-quick-consolidation.md is a design doc). Everything gathered
in the Thread-N + survey session is captured here at high density so the design
threads do not re-derive it. Rough plans and instincts are marked as such --
they are STARTING POSITIONS to interrogate, not decisions.

Repo access for these threads: sparse-clone BOTH `drill/` and `sm2/` from the
explorations repo in one checkout (they are peer top-level dirs). B/C need both;
D needs `drill/` + the import pipeline; E needs both. ASCII only. Single-user.

================================================================================
0. SHARED GROUND TRUTH (facts all these threads rely on -- verified this session)
================================================================================
DRILL data model (SQLite): categories -> banks -> questions -> (sessions) ->
responses.
  - questions columns: id, bank_id, qtype, question, answer, + JSON columns
    (alternatives, distractors, hints, tags), media_url, metadata (TEXT JSON,
    added v2/D1, the UNCOMMITTED structured-extras hatch per ADR-024), plus
    difficulty-era additions.
  - responses columns: id, session_id, question_id (NULL for generated
    arithmetic; SET for bank questions), question_text (a SNAPSHOT of what was
    shown), answer_text, user_input, correct, answered (ISO-8601), elapsed_ms
    (NULL|int -- collected since C-018c), difficulty (NULL|int), leaf_count
    (NULL|int). NO ease/interval/repetition/due columns yet.
  - Migration runner is DONE and PROVEN (run_migrations + MIGRATIONS registry +
    schema-driven drift guard; ADR-021/022/023/026). Adding columns = write a
    migrate fn, append a MIGRATIONS tuple, bump SCHEMA_VERSION, add a
    test_migrate test. The procedure is in decisions.md (the D1 handoff block).
  - pick_next_question(candidates, history) -> dict|None. PURE, in logic.py.
    v1 policy: uniform random from candidates whose id is not in the recent
    window, else uniform from all. This is THE selection seam (ADR-005 called
    adaptive out-of-scope for v1; the seam was built swappable on purpose).
    HTTP fetches candidates from DATABASE and calls this; LOGIC never queries.
  - Layering: config.py <- db.py <- logic.py <- http_layer.py, one-way DAG,
    enforced by the C0.1 boundary-purity guard. LOGIC is pure (no clock/IO/DB).
    The clock enters at the MAIN/HTTP boundary and is passed down as a param.

SM2 tool (sm2/sm2.py, ~1000 lines, standalone, no deps): parses @@@-delimited
Markdown flashcards from exercises/*.md, schedules via SM-2, stores state in
its OWN SQLite (data/sm2.db), CLI review loop, analytics.sql, --validate suite.
  - PURE CORE: sm2_update(grade, easiness_factor, interval_days,
    repetition_count, lapse_count, review_date) -> dict of new state. This is a
    clean, portable pure function -- the single most reusable asset for
    consolidation. USER_GRADE_TO_SM2_GRADE = {0:1, 1:3, 2:5}; EF clamped
    [1.3,3.0], never reset on failure; grade<3 -> repetition 0 / interval 1 /
    lapse+1; else interval 1 -> 6 -> interval*EF.
  - ItemState vector: item_id, easiness_factor, interval_days, repetition_count,
    due_date (ordinal int), last_review, lapse_count. THIS is the column set
    ADR-025 reserved for a drill migration.
  - ReviewOutcome: the atomic unit (new state + log row), built purely by
    grade_item, executed by commit_review. Same pure-build / impure-execute
    split drill uses.
  - Throttle policy: total_new_max=9, min_per_domain=1, max_reviews=100;
    apply_throttle_and_cap is pure. Domain = item_id prefix before first "-".
  - Authoring model (RELEVANT TO SECTION E): content is READ-ONLY Markdown in
    exercises/, parsed at runtime (parse_exercises). @@@ id: <domain>-<topic>-
    <hint>, optional after:/tags:/criteria: lines, free-text body. Ids unique
    across files. This is a PROVEN file-based authoring model in the same repo.

TWO NOTIONS OF A REVIEW (the core reconciliation problem, per ADR-025/roadmap):
  - drill: a "response" is one answer to one question in a session; grading is
    correct/incorrect (validate_answer's qtype dispatch: exact/numeric/etc).
  - sm2: a "review" is one graded recall with a 0/1/2 quality grade that feeds
    scheduling; no notion of session, category, or bank.
  These do not map 1:1. drill grades RIGHT/WRONG; sm2 grades RECALL QUALITY on a
  3-point scale. Bridging them is the central C-design decision (Section 2).

CONSTRAINTS FROM ADR-054 (still binding): avoid a second schema-invasive thread
immediately after a heavy one; want product movement WITH comprehension; study
runs in parallel auditing each thread's fresh code. Implication: schedule the
schema-free work (adaptive, Doc A) before the schema-invasive work (SM2).

================================================================================
1. HANDOFF B+C -- ADAPTIVE SELECTION + SM2 (CO-DESIGNED, SHIPPED SEPARATELY)
================================================================================
Why co-designed: SM2 IS a selection strategy (due-date ordering + throttle), so
the adaptive-selection interface (B) must be shaped so the SM2 scheduler (C)
drops into it without rework. Design them together; BUILD B first (schema-free),
then C (the migration) as its own thread.

--------------------------------------------------------------------------------
1.1 The design thread's job
--------------------------------------------------------------------------------
Produce TWO design docs (or one doc with two build-thread sections):
  - Doc B: adaptive selection as a pure strategy swapped into pick_next_question,
    using ONLY data already stored. No migration.
  - Doc C: SM2 consolidation -- the migration (ItemState columns on questions or
    a new table), the pure sm2_update port, the grade-bridging decision, and how
    SM2 becomes the selection strategy behind the same seam.

--------------------------------------------------------------------------------
1.2 Doc B design forks to resolve (adaptive selection, schema-free)
--------------------------------------------------------------------------------
- INTERFACE SHAPE. pick_next_question(candidates, history) is the current seam.
  FORK: keep the signature and make the policy swappable internally, vs widen to
  pick_next_question(candidates, history, strategy=...) or a strategy object.
  INSTINCT: introduce a pure strategy function type
  select(candidates, context) -> dict|None where `context` carries history +
  per-candidate stats (recent accuracy, last-seen, miss-count). Keep
  pick_next_question as the default strategy; register others. This is the shape
  SM2 needs (SM2 is just another strategy whose context is due-dates).
- WHAT SIGNAL DRIVES SELECTION BEFORE SM2 EXISTS. Data available now: per-
  question correct/incorrect history (responses.question_id + correct),
  recency (answered), difficulty/leaf_count. INSTINCT: an accuracy-weighted
  pick (favor questions the user misses) + the existing recency avoidance is a
  meaningful non-SM2 adaptive step, and it REUSES the most-missed aggregate Doc
  A builds. So Doc A's most_missed query is a dependency-of-convenience for B:
  if A ships first, B has the miss-rate data path already.
- WHERE STATS FOR SELECTION COME FROM. LOGIC is pure and cannot query. So HTTP
  must fetch per-candidate stats and pass them in `context`. FORK: a new reader
  (get_candidate_stats(bank_id)) vs enriching the existing candidate fetch.
  Note the layering rule: the reader is DATABASE, the policy is LOGIC.
- COLD START. A question never answered has no accuracy signal. Define the
  policy (treat as high-priority-new, like SM2's new-item budget, or neutral).
- TESTABILITY. The strategy is pure -> property tests (never returns a recent
  item when a fresh one exists; favors low-accuracy items; deterministic under a
  seeded RNG the way the generator's tests inject randomness).

--------------------------------------------------------------------------------
1.3 Doc C design forks to resolve (SM2 consolidation, schema-invasive)
--------------------------------------------------------------------------------
- PORT vs CALL vs SHARE-SCHEMA (the big one).
    (a) PORT sm2_update (and grade_item, apply_throttle_and_cap) into drill's
        logic.py as pure functions; add ItemState columns via a migration;
        drill owns everything. CLEANEST fit to drill's architecture (pure core
        + migration runner + one SQLite). Recommended starting position.
    (b) CALL the sm2 tool as a library (import sm2). Couples two codebases with
        two SQLite files and two schemas; fights drill's single-file-per-layer
        model. Not recommended.
    (c) SHARE/UNIFY schemas. Largest blast radius; only if the tools truly merge.
  INSTINCT: (a). sm2_update is ~35 lines of pure arithmetic with a validation
  suite proving it; porting it is low-risk and it lands where drill's other pure
  logic lives. The sm2 tool stays as the standalone authoring/CLI companion (or
  is retired later); its ALGORITHM becomes drill's.
- GRADE BRIDGING (the core reconciliation). drill grades right/wrong (binary);
  SM2 needs 0/1/2 recall quality. FORKS:
    - Map binary -> {0 = wrong, 2 = right} and lose the "passed with effort" (1)
      middle grade; OR
    - Add a 3-way grade to drill's answer UI for SRS-scheduled questions (a real
      UI change -- the SM2 "how easily did you recall?" prompt after reveal); OR
    - Derive quality from correctness + elapsed_ms (fast+correct=2, slow+correct
      =1, wrong=0) -- drill ALREADY collects elapsed_ms, so this bridges the two
      review notions using data in hand. INSTINCT: this is the elegant one and
      it justifies N.2's timing work retroactively; prototype it, validate the
      thresholds against the sm2 --validate discipline.
- SCHEDULING STATE HOME. ItemState is per-question. FORK: new columns on
  questions (ease/interval/repetition/due/last_review/lapse) vs a new
  question_schedule table (1:1 with questions). INSTINCT: a separate table
  (questions stays content; schedule is mutable review state) -- cleaner
  separation and matches ADR-040's "mutable label vs non-drifting fact" instinct.
  But note ADR-025 said "fold in WITH the SM2 fields as a single migration" and
  reserved the migration here. Either way it is ONE forward-only additive
  migration through the proven runner.
- ARITHMETIC vs BANK. Generated arithmetic has no question_id (not stored), so
  it CANNOT carry per-item SM2 state. SM2 scheduling applies to BANK questions
  only (finite, identified, authored). State this boundary explicitly -- SM2 is
  a vocab/flashcard feature, not an arithmetic one. Arithmetic keeps difficulty-
  rung selection; bank questions get SM2. The strategy interface (B) must
  dispatch on this.
- DUE-DATE CLOCK. SM2 due dates are dates; drill's clock enters at HTTP. Keep
  the pure sm2_update taking review_date as a param (it already does); HTTP
  supplies today. Consistent with drill's clock-at-the-boundary rule.
- THROTTLE / SESSION SHAPE. sm2's session is "review all due items up to caps";
  drill's session is "keep drilling one category." FORK: does an SM2 bank
  session adopt the due-queue+throttle model, or does drill keep its
  open-ended session and just let SM2 order the picks? INSTINCT: SM2 ordering
  behind pick_next_question, keep drill's session model; the throttle becomes a
  candidate-set filter (only-due + new-budget) applied by the reader/strategy.

--------------------------------------------------------------------------------
1.4 Rough build sequence (once designed)
--------------------------------------------------------------------------------
B (schema-free): strategy seam + accuracy-weighted adaptive + tests. One thread.
C1: the migration (schedule table/columns) through the runner + tests. Small.
C2: port sm2_update + grade-bridge + wire as the bank strategy + the recall-
    grade UI (if that fork is chosen) + tests. The meaty thread.
C3 (optional): analytics parity (port the useful analytics.sql queries as
    stats-panel sections, reusing Doc A's breakdown seam).
Study-track audits each of B/C1/C2 as fresh code (parallel).

================================================================================
2. HANDOFF D -- CONVERSION PIPELINES (dataset -> JSONL)
================================================================================
Fully INDEPENDENT of B/C and of drill internals: it targets the EXISTING import
format as its output contract. Can be prototyped as a standalone script before
any drill integration. This is the "find or convert a dataset" path.

--------------------------------------------------------------------------------
2.1 The output contract (verified)
--------------------------------------------------------------------------------
drill's importer already accepts JSONL and CSV (C-008 parsing). A converter's
job is: emit one JSON object per line matching the question shape the importer
expects -- qtype, question, answer, and the optional JSON fields (alternatives,
distractors, hints, tags, media_url). The A.4 export commit (Doc A) will make
the round-trip explicit (export -> import identity), which DOUBLES as the
converter's target spec: whatever A.4 exports is exactly what a converter should
emit. SEQUENCING NOTE: if Doc A ships A.4 first, D has a concrete, tested target.

--------------------------------------------------------------------------------
2.2 Design forks
--------------------------------------------------------------------------------
- SOURCE TYPES, easiest -> hardest:
    (1) Existing structured datasets (word lists, CSV vocab, Anki exports,
        wordfreq lists) -> JSONL. Mostly field-mapping. START HERE.
    (2) A dictionary PDF -> JSONL. Harder: PDF text extraction (columns,
        headwords, senses), parsing entries, deciding what becomes
        question/answer (headword->definition? definition->headword?
        both directions?). The reusable pipeline the user wants.
    (3) An encyclopedia PDF -> JSONL. Hardest: unstructured prose; entry
        segmentation and question generation are genuinely hard (borders on
        roadmap #27 AI-generated content). Likely OUT of a first pass.
- DIRECTIONALITY. A vocab pair (L1, L2) yields up to 4 question types
  (L1->L2, L2->L1, and with/without a prompt sentence). This is the DEMOTED
  "direction" idea from vocab-language-futures.md -- it belongs to the
  converter's OUTPUT choices, not drill's runtime. A converter can emit both
  directions as separate questions; drill needs no new concept.
- PDF TOOLING. Out-of-scope to pick here, but flag: PDF extraction is the risky,
  reusable part; consider building it as a separate `convert/` tool (like sm2 is
  separate) that emits JSONL, rather than inside drill. Keeps drill clean and
  makes the pipeline reusable for the encyclopedia case and beyond.
- QUALITY GATE. Converted content needs a validation pass (dedupe ids, non-empty
  answers, valid JSON per line) before import -- mirror sm2's --validate ethos.

--------------------------------------------------------------------------------
2.3 Instinct
--------------------------------------------------------------------------------
Build (1) as a tiny standalone converter proving the JSONL target, THEN (2) the
PDF->JSONL pipeline as its own `convert/` tool with a validation step. Treat (3)
as research, likely deferred or folded into an AI-generation thread (#27). The
converter is the cheapest way to get real vocab content into drill for B/C to
schedule -- so D partly UNBLOCKS C (SM2 wants a real corpus to be worth it).

================================================================================
3. HANDOFF E -- AUTHORED CONTENT (content you WRITE, not convert)
================================================================================
The harder infra question: when the user authors questions by hand (vocab you
choose, grammar drills, the SM2-style cards), where does that content live and
how is it created? Entangled with C (SM2), so consider designing E INSIDE the
C thread rather than standalone.

--------------------------------------------------------------------------------
3.1 The key realization
--------------------------------------------------------------------------------
sm2 ALREADY SOLVES authoring one way: read-only Markdown files in exercises/,
@@@-delimited, parsed at runtime, ids unique, never written by the tool. This is
a proven, git-friendly, plain-text authoring model sitting in the same repo. The
strategic question is whether drill ADOPTS this model or builds a UI.

--------------------------------------------------------------------------------
3.2 Design forks
--------------------------------------------------------------------------------
- FILE-BASED (adopt sm2's model): author questions in Markdown/JSONL files,
  import (or parse-at-runtime) into drill. PROS: git-versioned, diffable, no UI
  to build, matches sm2 so consolidation reuses the parser. CONS: not editable
  from the running app; a content change is a file edit + re-import.
- UI-BASED (the in-browser bank editor, roadmap #32 Tier 4): author/edit
  questions in the app. PROS: no context switch, immediate. CONS: a real build
  (forms, validation, the mutation seam drill has deliberately deferred; CRUD
  endpoints exist in db.py but no UI). Bigger than it looks.
- HYBRID: files are the source of truth (authored + converted content both land
  as files), the app is read-mostly, and a THIN "add one card" affordance covers
  the quick-capture case without a full editor. INSTINCT: this fits the tool's
  "single-user, reload-is-a-clean-slate, git-backed" character best.
- RELATION TO CONVERSION (D). Converted content (D) and authored content (E)
  should land in the SAME format (JSONL/importer shape), so they share one
  ingestion path. Do not build two ingestion mechanisms.

--------------------------------------------------------------------------------
3.3 Instinct
--------------------------------------------------------------------------------
Default to FILE-BASED authoring reusing the importer (and, if C adopts sm2's
parser, the @@@ Markdown format for flashcard-style cards). Defer the in-browser
editor (#32) unless quick-capture friction proves real. Fold the authoring-format
decision INTO Doc C, because SM2's card format and its scheduling are entangled
and should be decided together. E is therefore likely NOT its own thread -- it is
a section of C plus a possible tiny later UI thread.

================================================================================
4. RECOMMENDED THREAD MAP (instinct, to be confirmed by the design threads)
================================================================================
- PARALLEL now: Doc A build thread (schema-free stats + export) + Doc D pipeline
  (1) prototype (standalone, no drill risk). Study track audits A.
- THEN: B (adaptive, schema-free) -- reuses A's most-missed data path.
- THEN: C (SM2: migration + sm2_update port + grade-bridge + authoring format
  from E) -- the schema-invasive thread, taken alone per ADR-054, once re-warmed
  by A/B. D's converter (2) gives it a real corpus to schedule.
- LATER/OPTIONAL: encyclopedia pipeline (D3) and/or in-browser editor (#32) if
  authoring friction justifies them.

Dependencies worth stating: A.most_missed --de-risks--> B.accuracy-signal;
A.4 export --defines--> D's JSONL target; D's corpus --justifies--> C's SM2;
E's format decision --lives-inside--> C. Nothing here blocks A or D from
starting immediately.

================================================================================
5. DOCS THESE THREADS SHOULD UPDATE (so the trail stays single-source)
================================================================================
- decisions.md: new ADRs for the real decisions (grade-bridging, schedule-state
  home, strategy-interface shape, authoring format). Do NOT pre-write; let the
  design produce them. Add to adr-index.md when they land.
- STATUS.md: the phase map (B/C/D threads), keep #3 study-track parallel.
- roadmap.md: mark #6 (SM2), #7 (adaptive), the vocab importers as they move.
- vocab-language-futures.md: promote/retire items as consumers appear
  (direction, per-question language -- D gives direction a home in the converter).
- knowledge-capture.md: any new runtime-semantics facts (e.g. PDF-extraction
  gotchas are NOT semantics; grade-bridge threshold findings ARE decisions).
