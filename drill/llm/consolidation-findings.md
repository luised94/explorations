# Consolidating SM-2 and adaptive selection into drill
## Findings, verification, and implementation specification

Status: design complete, all claims spike-verified against the real code.
Audience: the implementing model (Opus 4.8) and the human. Every load-bearing
claim below was verified in a sandbox against the actual repositories; the
spike files named in each section are the executable evidence and ship with
this document. Nothing here is paraphrased from memory.

Baseline: explorations repo, drill/ and sm2/ directories, drill schema
version 3, drill test suite reported as 589 green (not re-run here; confirm
before starting). sm2's own suite: 50 passed (re-run here, confirmed).

---

## 0. Authority, scope, and style contract

DECIDED (human): drill is authoritative. sm2 is folded into drill; anything
that does not translate is archived, not dragged along. The standalone sm2
tool is retired after its exercise content migrates (section 14).

STYLE CONTRACT for all new code (human requirement, and already partially
enforced by the repo itself via ruff TID import bans plus
tests/test_boundary_purity.py):
- Flat procedural code. Pure functions over plain dicts, lists, tuples.
- No classes, no nested functions, no closures, no decorator machinery.
- Reads, writes, clock, and randomness live at the edges (HTTP/MAIN/DATABASE);
  LOGIC never touches any of them. The clock is read once per request at the
  HTTP boundary and passed down as values.
- Full descriptive names carrying domain information. No abbreviations unless
  the noun behaves as a word (url, id, http). Examples used throughout:
  advance_schedule_state, derive_recall_quality, easiness_factor.
- Layering is sacred and mechanical: config <- db <- logic <- http, MAIN wires.

The spike file scheduler_port.py is written in this style and is intended to
be close to landable; treat it as the reference implementation, not
pseudocode. The two exceptions to the style inside it: the two sort key
lambdas in partition_candidates_by_schedule may be replaced with a module
level key function if lambdas are considered a violation.

---

## 1. Verified ground truth (read this before trusting anything)

Confirmed by direct inspection and execution:

- drill/logic.py: pick_next_question(candidates: list[dict], history:
  list[int] | None = None) -> dict | None. Pure. Uniform random from
  candidates not in the recent-history window, else uniform from all.
  Uses module-level random (seeded in tests); new strategies follow the
  same convention or take an explicit random value (spike does the latter).
- drill/db.py: run_migrations(connection, now, target_version=None,
  migrations=None) -> dict. Forward-only, idempotent, one transaction per
  migration. MIGRATIONS currently [(2, metadata), (3, difficulty+leaf_count)].
  SCHEMA_VERSION = 3 lives in drill/config.py. An import-time guard requires
  the top MIGRATIONS version to equal SCHEMA_VERSION and versions to be
  strictly ascending 2..N. init_db builds baseline (version 1) and seeds
  categories; the runner advances from there.
- drill/db.py write API used by this work: insert_bank(connection,
  category_id, name, source, created, language=None, metadata=None) -> int;
  insert_questions_bulk(connection, bank_id, questions, created) -> int;
  insert_response(connection, session_id, question_text, answer_text,
  user_input, correct, answered, question_id=None, elapsed_ms=None,
  difficulty=None, leaf_count=None) -> int; start_session(connection,
  category_id, started, bank_id=None, config=None) -> int. Note bank_id is
  OPTIONAL on sessions: category-wide sessions already exist, which is the
  interleaving hook (section 12).
- responses.question_id is NULL for generated arithmetic; elapsed_ms is
  collected end to end (drill.js marks at answerable phase, omits the field
  if the mark is unset; http_layer accepts it as optional int; db stores).
  So elapsed_ms can be NULL and any consumer must be total over NULL.
- Importable qtypes are exactly free_response, multiple_choice, translate,
  identify. arithmetic is generated-only and REJECTED by the import funnel
  (_normalize_question_dict). Discovered live when a spike tried to import
  qtype arithmetic. Entailment: the authoring path structurally cannot
  create schedulable arithmetic; the bank/arithmetic split is enforced at
  the funnel, not by convention.
- sm2/sm2.py: sm2_update(grade, easiness_factor, interval_days,
  repetition_count, lapse_count, review_date) -> dict;
  USER_GRADE_TO_SM2_GRADE = {0: 1, 1: 3, 2: 5}; EF clamped [1.3, 3.0], never
  reset on failure; grade < 3 -> repetition 0, interval 1, lapse + 1; else
  intervals 1 -> 6 -> interval * EF. apply_throttle_and_cap with defaults
  total_new_max=9, min_per_domain=1, max_reviews=100; domain = item_id
  prefix before first "-".
- CORRECTION to the original handoff: sm2 has NO --validate flag. The
  validation contract is sm2/test_sm2.py (50 tests, re-run here, all pass).
  The scheduler-invariant subset of those tests is the porting contract.
- CORRECTION to an earlier claim in this thread: "rebuild == stored" holds
  only under an unchanged derive_recall_quality policy. Section 8 defines
  rebuild semantics accordingly.
- Dependency ground truth (pyproject.toml): bottle is THE one runtime
  dependency by explicit decision (ADR-001). Tests: pytest + hypothesis
  (dependency group). Frontend tests: jsdom + acorn, dev only. THIS WORK
  ADDS ZERO DEPENDENCIES. Everything below is stdlib.

Relevant repo decisions honored: ADR-005 (selection seam deliberately
swappable), ADR-021/022/023/026 (migration mechanism), ADR-024 (metadata
hatch is on questions, not banks), ADR-025 (scheduling fields migration
reserved; if a grading axis is ever added it rides the SAME migration and
must feed validate_answer's single dispatch, never fork it), ADR-040
(mutable label vs non-drifting fact), roadmap #6/#7 = this work, roadmap
#15 (JSONL export) = the version-control answer (section 13).

---

## 2. Feature C1: the question_schedule table (migration 4)

REASONING. Scheduling state is mutable review state, not content. Folding
six mutable columns into questions would teach the import pipeline
(parse_import -> _normalize_question_dict -> insert_questions_bulk) to
tiptoe around them; a separate 1:1 table keeps the pipeline ignorant, makes
the migration a single idempotent CREATE TABLE, reproduces sm2's proven
"absence of row means never scheduled" semantics, and matches the
content-vs-state instinct of ADR-040. ADR-025's phrasing ("fold the fields
in") is hereby resolved to the separate table; the ADR's real reservation
was the migration slot, not the shape.

SPECIFICATION.

    CREATE TABLE IF NOT EXISTS question_schedule (
        question_id      INTEGER PRIMARY KEY REFERENCES questions(id),
        easiness_factor  REAL    NOT NULL,
        interval_days    REAL    NOT NULL,
        repetition_count INTEGER NOT NULL,
        due_date         INTEGER NOT NULL,
        last_review      INTEGER NOT NULL,
        lapse_count      INTEGER NOT NULL
    )

due_date and last_review are ordinal-day integers (datetime.date.toordinal).
All columns NOT NULL: a row exists only after a first graded review, created
with values computed by the pure core, so there is never a NULL schedule
field and the scheduler needs no NULL handling. No backfill migration:
rows appear lazily (write path, section 5) or via rebuild (section 8).

Implementation: one migrate function in db.py appending
(4, "add question_schedule (SM2 scheduling state, ADR-025)", fn) to
MIGRATIONS; bump SCHEMA_VERSION to 4 in config.py (the import-time guard
enforces the pairing); one test in tests/test_migrate.py following the
version-3 test's pattern. Plus db.py accessors: read all schedule rows for
a bank (join through questions.bank_id), and an UPSERT writer (the spike's
WRITE_SCHEDULE_ROW statement, INSERT ... ON CONFLICT(question_id) DO UPDATE).

VERIFICATION (test_migration_and_simulation.py): walked a fresh in-memory
drill database 1 -> 4 through the REAL run_migrations with the REAL
MIGRATIONS list extended by this entry; version lands at 4; a second run is
a no-op with identical table set (idempotent); existing tables untouched.

RISK: minimal. The only sharp edge is forgetting the config.py bump, and
the import-time guard makes that a loud failure, not a drift.
DIFFICULTY: trivial. One migrate fn, one tuple, one constant, two
accessors, one test.

---

## 3. Feature C2: the scheduler port (advance_schedule_state)

REASONING. Port, do not call and do not share schemas. The reusable asset
is about sixty lines of dependency-free pure arithmetic; calling sm2 as a
library drags its parser, CLI, and a second frozen-schema SQLite; unifying
schemas loses to TEXT-vs-INTEGER key mismatch with maximum blast radius.
The port risk is silent divergence, killed by an equivalence contract.

SPECIFICATION. scheduler_port.py: advance_schedule_state(recall_quality,
easiness_factor, interval_days, repetition_count, lapse_count, review_date)
-> dict with keys easiness_factor, interval_days, repetition_count,
lapse_count, due_date, last_review. Field-for-field the same arithmetic as
sm2_update under drill naming: RECALL_QUALITY_TO_SM2_GRADE {0:1, 1:3, 2:5},
EF delta formula, clamp [1.3, 3.0], failure path (repetition 0, interval
1.0, lapse + 1), success ladder (1 -> 6 -> interval * new EF), due_date =
review_date + round(interval). Lands in drill/logic.py verbatim from the
spike. domain_of is NOT ported (bank_id is a real column). commit_review
is NOT ported (drill's insert_response plus the schedule UPSERT replace
it); sm2's review_log table is NOT ported (responses carries everything;
EF-before/after is recomputable by replay).

VERIFICATION (test_port_equivalence.py): 4860-point grid over grade x EF x
interval x repetition x lapse x review_date; the port agrees with the
original sm2.sm2_update on EVERY field at EVERY point. Additionally port
the scheduler-invariant tests from sm2/test_sm2.py (EF floor across ten
fails, EF ceiling across twenty passes, first-interval-is-one,
second-is-six, third-multiplies, grade-2 intervals never decrease,
stuck-item invariants, recovery-retains-lowered-EF) into drill's suite as
the permanent anti-divergence contract; after that the sm2 file can be
archived without losing the contract.

RISK: divergence after landing if someone edits one constant; mitigated by
the ported invariant tests. DIFFICULTY: trivial (the code exists and is
proven); the care is in porting the tests faithfully.

---

## 4. Feature C3: the grade bridge (derive_recall_quality)

REASONING AND THOUGHT PROCESS. drill grades binary (validate_answer ->
bool); SM-2 wants recall quality 0|1|2. Three options were weighed. A UI
self-grade prompt is rejected: drill's identity is objective grading, and
the prompt taxes every answer to collect one bit that matters only on
correct answers. Deriving quality from correctness plus elapsed_ms is the
right destination but the WRONG v1: thresholds have no data behind them
yet, absolute cutoffs are wrong across qtypes and questions (a seven-leaf
arithmetic expression vs a vocab card), and elapsed_ms can be NULL. The
binary map (wrong -> 0, correct -> 2) is deterministic, total, needs no new
data, and its known failure mode is bounded: easiness never decays on
effortful passes, but a genuinely shaky item eventually lapses, and the
lapse path (interval reset to 1, lapse_count + 1, EF already never reset)
corrects it.

DECISION: a pure seam function with the binary policy inside it.

    derive_recall_quality(correct: bool, elapsed_ms: int | None) -> int

elapsed_ms is accepted and deliberately unused so the timing-derived policy
(fast+correct -> 2, slow+correct -> 1, wrong -> 0, with "slow" defined
against a per-qtype or per-question trailing median, never an absolute
number) can swap in behind the same signature once enough history exists to
fit baselines. Per ADR-025: this is policy in LOGIC, never a persisted
grading column, and it sits strictly downstream of validate_answer's bool.

CONSEQUENCE (accepted, documented): recall quality 1 is unreachable in v1,
so EF can only rise on success and fall on failure. See also section 8:
changing this policy later changes rebuild semantics.

VERIFICATION: exercised throughout the 90-day simulation (section 8);
totality over NULL elapsed_ms exercised (simulation rows carry ints, the
function ignores them; the signature admits None by construction).
RISK: low; the risk is someone "improving" it to timing thresholds without
data. The docstring forbids that explicitly. DIFFICULTY: trivial.

---

## 5. Feature C4: the once-per-day rule (the biggest hidden entailment)

REASONING. drill's history window only SOFTLY avoids repeats, so one
question can be answered twice in a day; SM-2's model assumes one graded
review per item per day. Feeding a same-day second success advances the
interval twice off one day of memory -- silent schedule corruption.

SPECIFICATION. schedule_update_allowed_today(schedule_state, today) ->
bool: True when the state is None (never reviewed) or last_review != today.
The HTTP review path checks this BEFORE calling advance_schedule_state;
when False, the response row is still inserted (the log is complete) but
the schedule is untouched. The rebuild fold (section 8) applies the same
rule, which is what keeps rebuild == stored true.

VERIFICATION: the 90-day simulation's due+new servicing produces same-day
eligible repeats; the invariant held only WITH this rule applied in both
the live path and the rebuild fold (removing it from either side breaks
the rebuild equality check -- this was observed while writing the spike,
which is exactly the class of bug the invariant test exists to catch).
Plus a direct unit check: a state whose last_review == today is blocked.

RISK: medium if forgotten on one of the two paths; the rebuild-invariant
test turns that mistake into a loud failure. DIFFICULTY: trivial code,
but it MUST land in the same commit as the write path.

---

## 6. Feature C5: interval fuzz (deterministic declumping)

REASONING. Questions learned together get identical intervals and stay due
together forever, producing spiky daily load. Standard fix is jitter. The
twist required here: jitter must be DETERMINISTIC PER QUESTION, not random,
or the rebuild-from-log invariant (section 8) dies. Solution: key the
jitter on question_id through a Knuth multiplicative hash, mapped to
[-0.05, +0.05], applied to the computed interval. Intervals of two days or
less are exempt (fuzz there only rounds to the same day or distorts the
fixed 1 -> 6 opening ladder).

    apply_interval_fuzz(interval_days: float, question_id: int) -> float

The caller applies it AFTER advance_schedule_state and recomputes due_date
= review_date + round(fuzzed interval). The rebuild fold applies it
identically.

VERIFICATION (test_port_equivalence.py): deterministic (same inputs, same
output, 2000 ids), bounded within +-5 percent, exempt at <= 2 days.
FINDING with a number: 100 questions at interval 30 spread over only 3
distinct due dates (unfuzzed: 1). Declumping is proportional to interval
length; at short-to-mid intervals the spread is modest. This is acceptable
for v1 and documented as the tuning knob: if load spikes persist in
practice, either raise INTERVAL_FUZZ_FRACTION or switch to a minimum
absolute jitter of +-1 day above the exemption. DECIDED default: 0.05,
revisit with real usage data only.

RISK: low. DIFFICULTY: trivial.

---

## 7. Features C6 + C7: due partition, backlog ordering, new-item throttle

REASONING. Review mode needs three answers each request: which questions
are eligible (due or new), in what order a capped budget is spent, and how
many never-reviewed questions may enter the schedule today.

SPECIFICATION (all pure, all in logic):
- partition_candidates_by_schedule(candidates, schedule_by_question_id,
  today) -> (due, new, not_due). due is ordered by relative_overdueness
  DESCENDING; new is in id order (authoring order -- deliberate, no
  priority column, decided premature).
- relative_overdueness(schedule_state, today) = (today - due_date) /
  max(interval_days, 1). Rationale: a short-interval question three days
  late is at more recall risk than a sixty-day question five days late;
  most-overdue-first is the intuitive but wrong key. This is the sort key
  for spending REVIEWS_PER_SESSION_MAXIMUM on a backlog after time away.
- apply_new_question_throttle(new_candidates, new_introduced_today_by_bank,
  per_day_maximum, per_bank_minimum) -> admitted list. Two passes: floor
  (guarantee per_bank_minimum to each bank with headroom today), then fill
  remaining budget in candidate order. This is sm2's apply_throttle_and_cap
  with the string domain prefix replaced by the real bank_id column.
- Policy constants are DATA in config.py: NEW_QUESTIONS_PER_DAY_MAXIMUM=9,
  NEW_QUESTIONS_PER_BANK_MINIMUM=1, REVIEWS_PER_SESSION_MAXIMUM=100 (sm2's
  proven defaults). They flow config -> HTTP -> context -> pure functions.
  Per-bank overrides are DEFERRED (ADR-024 put metadata on questions, not
  banks; a banks column would be its own migration; do not pre-build).
- The supporting count needs NO new state: new_introduced_today_by_bank is
  one SQL aggregate -- schedule rows with repetition_count = 1 AND
  lapse_count = 0 AND last_review = today, grouped by questions.bank_id.
  (repetition 1 + lapse 0 uniquely identifies "first-ever review was
  today" under the SM-2 state machine.)

VERIFICATION: throttle floor/cap/spent-budget/partial-budget all pass
(test_selection_and_throttle.py); the partition drove the 90-day
simulation; the aggregate ran against the real simulated database
(test_migration_and_simulation.py).

RISK: the throttle's floor pass admits at most per_bank_minimum per bank
even when only one bank has candidates and budget remains -- the fill pass
covers that; covered by the partial-budget test. DIFFICULTY: low.

---

## 8. Feature C8: rebuild from the response log (state is a cache)

REASONING AND THOUGHT PROCESS. Because the scheduler is pure and
deterministic, the fuzz is deterministic, and every graded attempt is
logged with a timestamp, the ENTIRE question_schedule table is a fold over
the responses log. This one observation buys four things: the migration
needs no backfill (rebuild is the backfill for pre-existing response
history); corruption recovery is one function; the strongest possible
integration test exists (rebuild == stored after any simulated history);
and scheduling state needs no versioning or backup discipline beyond the
database file itself (section 13).

HONEST LIMIT (correcting this thread's own earlier claim): the invariant
is "rebuild == stored UNDER UNCHANGED derive_recall_quality POLICY".
DECIDED SEMANTICS: rebuild means "current policy over the full log", which
makes a future policy upgrade retroactive by design -- switching to the
timing-derived quality and rebuilding re-schedules everything as if the
better policy had always applied. This is a feature, and it is written
down here so it is a choice, not a surprise.

SPECIFICATION. rebuild_schedule_from_response_log(response_rows) ->
dict[question_id, schedule_state]. Rows need question_id (NULL rows are
skipped -- arithmetic never schedules), correct, elapsed_ms, and
answered_ordinal (day ordinal of the answered timestamp, computed by the
caller at the edge). The fold applies, in order: once-per-day gate,
derive_recall_quality, advance_schedule_state, apply_interval_fuzz, due
date recompute. Identical steps to the live write path -- keep them
identical or the invariant test will say so.

VERIFICATION (test_migration_and_simulation.py): a 90-day simulation on a
REAL drill database (real init_db, real migrations to 4, real insert_bank /
insert_questions_bulk / start_session / insert_response; 16 questions in
two banks, a fixed correct/wrong pattern, due+new servicing every day; 202
responses, all 16 questions scheduled). rebuild == stored held on every
field of every row to 1e-9. Sanity of the resulting schedule: after 90
days the best-known items sit at intervals near 165 days with EF at the
3.0 ceiling -- textbook SM-2 growth. True-retention over the simulated
history: 0.752, consistent with the injected 75 percent pattern, which
also validates the retention query (section 10).

RISK: the live path and the fold drifting apart; the invariant test is the
guard and must run over a nontrivial simulated history, not a two-row toy.
DIFFICULTY: moderate -- not the code (it exists), but the discipline of
keeping two paths step-identical.

---

## 9. Feature B: adaptive selection (weighted by miss rate, schema-free)

REASONING. Roadmap #7. Must ship ALONE (no migration, only stored data)
and must not be obsoleted when SM-2 lands. Both hold: the weights derive
entirely from existing responses columns (question_id, correct), and after
C lands the two COMPOSE -- SM-2 decides eligibility (due set, new budget),
the miss-rate weighting orders WITHIN the eligible set and remains the
whole engine for practice mode (section 11).

SPECIFICATION.
- miss_rate_weight(attempt_count, correct_count) = (misses + 1) /
  (attempts + 2). Laplace smoothing: a never-attempted question weighs
  exactly 0.5, so a cold bank is uniform -- the policy DEGRADES TO the
  current random behavior instead of starving or looping. This is the
  cold-start design, and it costs zero special cases.
- select_weighted_by_miss_rate(candidates, response_stats_by_question_id,
  history, random_value) -> dict | None. Same soft history-window semantics
  as pick_next_question (fresh pool if any, else full pool). random_value
  is a uniform [0,1) sample supplied by the caller: HTTP passes
  random.random(), tests pass fixed values or a seeded generator --
  determinism without touching the module-random convention.
- Per-candidate stats are one SQL aggregate over responses (COUNT, SUM of
  correct, MAX answered, grouped by question_id for a bank), fetched by
  HTTP and passed down. This is the planned "most-missed" stats query
  generalized; LOGIC never queries (boundary guard stays green).

VERIFICATION (test_selection_and_throttle.py, 20000-draw distributions,
seeded): cold start uniform (worst per-question deviation 5.0 percent of
expected); a question missed 8 of 10 times is picked 9.0x more than
mastered peers, matching the predicted weight ratio exactly; the history
window excludes recent ids when a fresh candidate exists; all-recent falls
back to the full pool and never returns nothing.

RISK: low. Weighted-without-replacement subtleties do not arise (one pick
per request). DIFFICULTY: low. SHIPS FIRST.

---

## 10. Feature: true retention (promoted into C's definition of done)

REASONING. You cannot tune a scheduler you do not measure. True retention
= first-attempt-of-day accuracy per question. It is derivable with NO new
schema from responses alone (and can be restricted to due-at-the-time
items once schedule history exists).

SPECIFICATION: one SQL query (CTE: MIN(id) per question_id per
substr(answered,1,10); AVG(correct) over those first attempts), exposed as
a db.py reader, a stats.js render, and available to the terminal views.

VERIFICATION: ran against the simulated database; returned 0.752 over 202
graded reviews, matching the injected pattern.

RISK: none. DIFFICULTY: trivial. Land in the same thread as C.

---

## 11. Review mode vs practice mode (a required distinction, decided small)

REASONING. Once schedule state exists, "cram this bank now" must not feed
the scheduler, or cramming pollutes the memory model. DECIDED v1: the mode
is a REQUEST property -- the review endpoint path updates schedules, the
existing practice path never does; no schema, no flag column. KNOWN LIMIT
accepted and documented: the response log does not record mode, so a
rebuild treats historical practice responses as reviews. If that ever
matters, sessions.config (already a JSON column on sessions) can carry the
mode without a migration; the rebuild fold would then join through
sessions. Do not build that until it hurts.

RISK: low with the limit documented. DIFFICULTY: trivial.

---

## 12. Strategy seam and interleaving

SPECIFICATION. The seam stays a pure function call from HTTP. Three
policies, all flat functions: random (pick_next_question, unchanged,
default), weighted (section 9), scheduled (partition -> throttle -> serve
due-then-admitted-new, using weighted order within the due set). Dispatch
is a request parameter resolved in HTTP; context is a plain dict assembled
by HTTP (history; stats_by_question_id; and for scheduled mode: today
ordinal, schedule_by_question_id, throttle constants, new-today counts).
No registry object, no strategy classes -- an if/elif in the handler is
the honest amount of machinery for three policies.

INTERLEAVING (learning science, high evidence, near-zero cost): a
category-wide session already exists in the data model (sessions.bank_id
is optional). Serving it means candidates = union of the category's banks'
questions -- every candidate dict already carries bank_id, the throttle is
already bank-aware, and the weighted policy is bank-agnostic. Implement as:
when the request scopes to a category instead of a bank, HTTP fetches
questions for all banks in the category. No logic change.

VERIFICATION: partition/throttle/weighting all verified above on
multi-bank candidate lists. RISK: low. DIFFICULTY: low.

---

## 13. Version control and backup (decided: no rolled git, no new deps)

Three kinds of data, three answers. Review activity: responses is already
an append-only log -- it IS the history. Scheduling state: a cache of that
log (section 8) -- recoverable by rebuild, needs no versioning. Question
content: the only data that benefits from diffable history -- answered by
the roadmap's OWN item #15: a deterministic JSONL export (canonical key
order, ordered by id; the authoring spike already proved the canonical
dict round-trips), committed to ordinary git by the human. Rolling git
functionality or adding dulwich/pygit2 buys nothing over one pure render
function. ZERO dependencies added anywhere in this plan.

---

## 14. sm2 content migration and archive (one-off, closes the fold)

Field verdicts for sm2's Exercise model: item_id DISCARDED (identity moves
to drill's integer ids); tags FOLD to drill tags; source CONSOLIDATES into
questions.metadata (ADR-024 hatch) or a tag; content FOLDS to question
text; criteria is the UNCERTAIN one -- it is self-assessment criteria, not
a matchable answer. DECIDED handling: one throwaway script parses the
exercises/ files with the archived parser, maps criteria -> answer, tags
everything sm2-import, and imports through the standard funnel. Items
whose criteria cannot validate as an answer are the concrete motivation
for ADR-025's deferred grading_kind and simply live as imperfect
free_response until that decision is taken (and per ADR-025, if
grading_kind ever lands it rides one migration with... note: the schedule
migration will already have landed; ADR-025's single-migration clause then
applies to grading_kind's own migration feeding the single dispatch).

Terminal views: KEEP (human requirement; they live in sm2/sm2.py, pure,
rows-in string-out). Verified they render drill-shaped rows as-is, with
one porting note found by execution: leeches_view/preview_view derive a
domain column via domain_of string parsing -- the ported versions replace
that column with bank name supplied in the row. Port render_table, Column,
failures_view (drill improvement: show the stored user_input -- the actual
wrong answer -- instead of sm2's manual error notes), leeches_view (with
LEECH_THRESHOLD and the action policy: a leech is a badly authored item;
surface it next to the authoring edit loop), preview_view, dry_run_view.
Home: a thin cli entry beside MAIN (drill.py subcommands or a small
module -- open choice, section 17). ARCHIVE: the @@@ parser, reconcile,
the argparse CLI, build_review_card/build_reveal, the frozen two-table
schema, review_log.

---

## 15. Authoring (verified earlier in this thread; spec restated)

Core decision: with the database authoritative, the authoring format is a
TRANSIENT INBOX, not a canonical store -- which is what dissolves the @@@
format's complexity (author-managed ids, cross-file duplicate policy,
reconcile all existed to serve files-as-truth).

One pure transform, four edge shells. The transform: a minimal block
format (key: value lines, blank-line-separated blocks, # comments, |
arrays -- drill's existing CSV cell convention, q/a/alt/type/hint aliases)
parsed by author_parse into EXACTLY the canonical dicts
_normalize_question_dict produces -- verified equal to parse_jsonl over
the same records, so JSON serializability is structural. author_render is
the verified inverse (enables a future edit-bank round trip). Errors name
block and line. The shells: bare tty -> the git-commit editor loop
(template buffer, save, errors reinserted as #! comment banner, reopen;
untouched or emptied buffer aborts -- verified headlessly with a scripted
EDITOR including the error-fix-retry cycle); piped stdin -> filter,
errors to stderr as file:line: message; inside nvim -> that error format
IS the integration (makeprg + :make -> quickfix jump-to-error;
:w !drill push --bank X, or a range, pushes without leaving the editor;
no plugin); HTTP -> the existing import endpoint, same funnel.

Style note for the implementer: the spike's author_parse contains a nested
close_block function -- a style violation flagged by the human. Flatten it:
explicit accumulator dict, and the flush becomes either a duplicated
three-line block (loop body and loop exit) or a module-level
flush_author_block(block, block_start_line, records) function. Keep names
full and descriptive throughout.

VERIFIED: 12/12 parser checks (aliases, defaults, difficulty coercion,
parse_jsonl equivalence, round trip, five error paths naming block/line)
and both shell checks (fix-retry loop, untouched-abort). RISK: low.
DIFFICULTY: low. Independent of B and C; can land any time.

---

## 16. What is explicitly NOT built (decided)

Decks (a bank IS a deck; categories and tags cover grouping; a third
grouping concept is pure indirection). Minute-grain learning steps (breaks
the day-ordinal grain; the cheap approximation -- failed items resurface
via the existing soft history window within a session -- is taken
instead). FSRS (the modern fitted scheduler; not now -- wants an optimizer
dependency -- but it is the named payoff of the logging discipline: the
responses log is exactly its training data, and the swappable
advance_schedule_state seam plus the schedule columns being a state
superset means it can replace SM-2 later without schema change).
Gamification. Priority columns for new items. Per-bank throttle overrides.
A second scheduler before the retention metric exists.

---

## 17. Open decisions reserved for the human

1. Throttle domain floor: keyed on bank_id (spiked) or category_id. One
   word in one pure function either way. Recommendation: bank_id.
2. CLI home: subcommands on drill.py (drill add, drill due, drill leeches,
   drill failures, drill check, drill push) vs a separate small module
   MAIN wires. Recommendation: subcommands on drill.py; it is already the
   composition root.
3. Multi-line question text in the authoring format: v1 says no
   (long/complex questions go through raw JSONL); indented continuation
   lines are a backward-compatible later addition.
4. Retire sm2 immediately after content migration, or keep until the
   grading_kind question resolves. Recommendation: retire; the invariant
   tests carry the contract.

---

## 18. Commit sequence (each commit green, suite-extended, in order)

Thread ships B fully before any schema change, per the plan.

B1. db.py: per-question response stats aggregate for a bank (attempt_count,
    correct_count, last_answered). Reader test.
B2. logic.py: miss_rate_weight + select_weighted_by_miss_rate. Seeded
    distribution tests (port the spike's four checks).
B3. http: strategy dispatch parameter; context assembly; weighted mode
    wired end to end. Boundary-purity suite untouched and green.

C1. db.py migration 4 (question_schedule) + config SCHEMA_VERSION=4 +
    accessors (read-for-bank, UPSERT) + migrate test.
C2. logic.py: advance_schedule_state + derive_recall_quality +
    apply_interval_fuzz + schedule_update_allowed_today, WITH the ported
    sm2 invariant tests and the grid-equivalence spirit test.
C3. logic.py: relative_overdueness + partition_candidates_by_schedule +
    apply_new_question_throttle + rebuild_schedule_from_response_log;
    config: the three throttle constants. Unit tests per function.
C4. http: review-mode path (today ordinal stamped once per request;
    partition -> throttle -> serve; once-per-day gate; response insert +
    schedule UPSERT). THE INVARIANT TEST: simulate a multi-week history
    through the HTTP-equivalent path, assert rebuild == stored (port the
    90-day spike as a proper test).
C5. db.py + stats.js: new-today-by-bank aggregate; true-retention query
    and render. Terminal views port (render_table + four views, domain
    column -> bank name, failures shows user_input) behind the cli entry.

A1. logic.py: author_parse (flattened) + author_render + author_template +
    tests (port the 12 spike checks).
A2. cli: author_session editor loop + stdin filter face (file:line: stderr
    format) + import wiring. Headless scripted-EDITOR test.
A3. One-off sm2 exercises migration script; archive sm2/ per section 14.

Estimated sizes: B is small (three focused commits on a proven seam); C is
the meaty one but every pure function already exists verified; A is small.

---

## 19. Risk register (consolidated)

HIGH-VALUE GUARD: the rebuild == stored invariant test (C4). It converts
the three subtle failure modes (live/rebuild drift, once-per-day missed on
one path, nondeterministic fuzz) into loud test failures.
MEDIUM: quality-policy change semantics (section 8) -- documented decision,
retroactive-by-rebuild; revisit when the timing policy is actually fitted.
LOW: fuzz spread modest at mid intervals (finding: 3 distinct dates per
100 questions at interval 30) -- tuning knob documented; throttle floor
edge covered by test; NULL elapsed_ms totality by construction; timezone /
midnight sessions handled by stamping today once per request (write this
sentence into the HTTP docstring).
ZERO NEW DEPENDENCIES; zero frontend changes required for B and C except
the optional stats render; the 589-green baseline is touched only by
additive tests and the schema-version tests, which have an established
pattern from migration 3.

---

## Appendix: spike inventory (executable evidence)

- scheduler_port.py -- reference implementation, target style, all pure.
- test_port_equivalence.py -- 4860-point grid vs original sm2_update: PASS.
  Fuzz determinism/bounds/exemption: PASS. Declumping finding.
- test_migration_and_simulation.py -- real drill db, real runner, migration
  1->4 + idempotency: PASS. 90-day/202-response simulation, rebuild ==
  stored: PASS. Retention 0.752 and new-today aggregates: PASS.
  Once-per-day gate: PASS.
- test_selection_and_throttle.py -- cold-start uniformity, 9.0x
  miss-weighting, history window, fallback, throttle floor/cap/spent/
  partial: all PASS.
- author.py, author_shell.py, test_author.py -- authoring transform,
  render inverse, editor loop: 14/14 PASS (from the earlier session; note
  the nested-function flatten required before landing).
- sm2/test_sm2.py -- 50 passed (the porting contract source).
