# Design Doc A -- Quick-Consolidation Thread (stats-depth + JSONL export)

STATUS: DESIGN (ready to become a commit plan). Independent of SM2/adaptive
(Docs B/C) and of the content pipelines (Doc D). No schema migration. Cashes in
the modular stats seams built through Thread N. Safe next build thread.

Baseline: whatever main is at after the Thread N series + the study-track audit
commit. Sparse-clone the drill directory; verify HEAD before work. ASCII only.
Single-user.

================================================================================
0. WHAT THIS THREAD IS
================================================================================
Three render/read additions on the EXISTING modular stats pipeline, plus one
export endpoint. Chosen because they exercise the modularization (proof it pays
off) at near-zero schema risk, and because Thread N.2 just de-risked the timing
half of the stats surface. Roadmap 2a items #10 (partly, done in N.2), #11
(stats depth), #12 (JSONL export).

The unifying property: the durable stats path is PURE-summary + separate render
(ratified in the N.2 audit). Every item here is either (a) a new pure aggregate
+ a suppressed figure, or (b) a new pure breakdown via the existing swappable
breakdown_by seam, or (c) a read endpoint that streams existing rows. None
touch the generator, the schema, the answer hot path, or selection.

================================================================================
1. THE SEAMS THIS RESTS ON (verified against HEAD, not memory)
================================================================================
- summarize_stats(rows) -> {total, correct, accuracy, categories,
  difficulty_breakdown, median_elapsed_ms}. Pure, deterministic, handles the
  empty case. (N.2 added median_elapsed_ms + the _median helper.)
- breakdown_by(rows, key_of, label_of, *, include_row=None) -> sorted accuracy
  breakdown. PURE, swappable-key seam (ADR-041/046). Already called twice
  (categories inline loop NOT on it; difficulty_breakdown IS on it). A new
  breakdown is a new call with new callables -- zero change to breakdown_by.
- get_responses_for_stats(connection, category_id=None, since=None) -> rows.
  Each row TODAY carries: correct(bool), elapsed_ms(int|None), answered(str),
  difficulty(int|None), leaf_count(int|None), category_id(int),
  category_name(str). Ordered answered DESC, id DESC. Pure reader; the HTTP
  layer computes `since` from the clock (DATABASE never reads the clock).
- responses.question_id EXISTS as a stored column (NULL for generated
  arithmetic; SET for bank questions). It is written by insert_response but is
  NOT currently SELECTed by get_responses_for_stats.
- responses has NO bank_id column. bank_id lives on questions
  (questions.bank_id). Bank attribution requires a JOIN responses -> questions.
- stats.js: renderStatsPanel(summary) builds figures via statsFigure(value,
  label) and breakdown rows in .stats-breakdown; formatElapsed(ms) added in N.2.
- The stats endpoint: GET /api/stats (all-time / category_id / days window).
  http tests do NOT pin an exact key set, so additive summary keys pass through.

CRITICAL SCOPING FACT (drives the commit split below): "most-missed" and
"per-bank" need data the stats reader does not currently return. They are
QUERY/JOIN changes (add question_id to the SELECT; join to questions/banks),
NOT schema migrations -- the columns already exist. "Over-time" needs only
`answered`, already present, so it is a pure summary+render addition. This
asymmetry is the reason the commits are ordered pure-first.

================================================================================
2. COMMIT PLAN (ordered easiest/purest -> query-touching -> endpoint)
================================================================================
Each commit: edit in-sandbox, bash tests/run.sh, commit, deliver the triple
(summary+files, patch verified in a fresh clone with prior patches re-applied +
green count, house-format message). One patch per commit.

--------------------------------------------------------------------------------
A.1 -- OVER-TIME breakdown (pure; no query change)
--------------------------------------------------------------------------------
GOAL: a per-day (or per-week) accuracy trend from the rows already returned.
Each row has `answered` (ISO-8601). Group by calendar day.

BACKEND: summarize_stats gains `over_time` (a list of {key=YYYY-MM-DD, label,
total, correct, accuracy}, most-recent-first or chronological -- pick one, state
it). Implement via breakdown_by with key_of = the date prefix of row["answered"]
(slice the first 10 chars; do NOT parse to a datetime in the pure layer -- the
ISO prefix IS the day key, string-sortable). label_of = the same date. No
include_row (all rows count). This delivers on breakdown_by's reuse promise a
third time.
  - EDGE: chronological vs most-practiced sort. breakdown_by sorts by
    (-total, label) today. Over-time wants CHRONOLOGICAL, not most-practiced.
    DECISION FORK for the plan: either (a) add an optional `sort_key` parameter
    to breakdown_by (small, general, keeps it swappable), or (b) sort the
    over_time list at the call site after breakdown_by returns. Recommend (a)
    only if a second caller wants custom sort; else (b) keeps breakdown_by
    untouched. Lean (b) for A.1; promote to (a) if A.2/A.3 also need it.
FRONTEND: renderStatsPanel renders an over-time section (a small text table or
a sparkline-in-text). Keep it TEXT (no Chart.js -- that is roadmap #31, Tier 4,
explicitly out). Suppress when <2 days of data (single-day trend is noise),
mirroring the single-category/single-bucket suppression (C-D2i-3).
TESTS: backend -- over_time buckets days correctly, empty -> [], single day ->
suppressed-or-one-row (state which). frontend -- section renders with >=2 days,
suppressed with <2.
RISK: none (pure). AUDIT HOOK: this is the cleanest "breakdown_by reused a third
time" datapoint for the parallel study track -- curriculum entry candidate.

--------------------------------------------------------------------------------
A.2 -- MOST-MISSED questions (query change: SELECT question_id + join text)
--------------------------------------------------------------------------------
GOAL: the questions most often answered incorrectly, so the user sees what to
drill. Only meaningful for BANK questions (arithmetic is generated, question_id
NULL, each expression unique -- "most-missed arithmetic" is not a thing; exclude
it, the way difficulty_breakdown is arithmetic-only in reverse).

BACKEND (the query change): get_responses_for_stats adds r.question_id to the
SELECT (and, to show the question, LEFT JOIN questions q ON r.question_id = q.id
to carry q.question AS question_text -- note responses ALSO stores its own
question_text snapshot; DECISION FORK: use the stored responses.question_text
snapshot (no join, honest to what was shown) vs the live questions.question
(join, reflects edits). Recommend the responses snapshot -- no join, and it is
the text actually shown; a since-edited question should not relabel history.)
So A.2 may need NO join at all: SELECT r.question_id + r.question_text.
  - summarize_stats gains `most_missed` via breakdown_by: key_of = question_id,
    label_of = the question_text, include_row = question_id is not None AND
    (optionally) row is a miss. NOTE: breakdown_by computes accuracy per bucket,
    so "most-missed" = buckets sorted by LOWEST accuracy (or highest miss
    count). breakdown_by sorts by (-total, label) today -> this needs a sort by
    miss-rate. This is the SAME sort-fork as A.1. Resolve consistently: if A.1
    took fork (b), A.2 sorts at the call site too (sort the returned list by
    (accuracy asc, -total)). Cap to top N (e.g. 10) at the call site.
FRONTEND: a "most missed" section, bank questions only, top N, each row
question text + miss rate. Suppress when empty (no bank misses / arithmetic-only
user).
TESTS: backend -- most_missed ranks by miss-rate, excludes arithmetic (NULL
question_id), caps at N, empty -> []. frontend -- section renders / suppressed.
RISK: LOW. The only non-pure change is one added SELECT column (question_id +
the already-stored question_text). No migration. Verify the existing stats http
tests still pass (they do not pin the row shape, but the SELECT change is the
one thing to smoke-check).

--------------------------------------------------------------------------------
A.3 -- PER-BANK breakdown (query change: join to banks for the bank name)
--------------------------------------------------------------------------------
GOAL: accuracy grouped by bank (which vocabulary set is strong/weak). Bank
questions only.

BACKEND (the heavier query change): bank_id is on questions, not responses. To
attribute a response to a bank, get_responses_for_stats must JOIN
responses -> questions (r.question_id = q.id) -> banks (q.bank_id = b.id),
carrying b.id AS bank_id, b.name AS bank_name. This is the ONE join this thread
adds. LEFT JOIN so arithmetic rows (question_id NULL) survive with bank_id NULL.
  - summarize_stats gains `bank_breakdown` via breakdown_by: key_of = bank_id,
    label_of = bank_name, include_row = bank_id is not None. Most-practiced sort
    is fine here (breakdown_by's default) -- no sort fork.
FRONTEND: a per-bank section, suppressed when the user has no bank responses or
only one bank (single-bank suppression, consistent with single-category).
TESTS: backend -- bank_breakdown groups by bank, excludes arithmetic, single
bank -> suppressed-or-one-row, empty -> []. Join correctness: a response whose
question was later deleted (question_id dangling) -> LEFT JOIN keeps it with
NULL bank, excluded by include_row (assert this -- it is the subtle case).
frontend -- section renders / suppressed.
RISK: LOW-MODERATE (a real join, and the dangling-question_id edge). This is the
only commit that changes the reader's JOIN shape; smoke-test the /api/stats
happy paths after.

SEQUENCING NOTE: A.2 and A.3 both touch get_responses_for_stats' SELECT. If
built back-to-back, A.3's join supersedes A.2's bare-column add (A.3's join
already carries question_id). Option: fold the SELECT change once in A.2 and
only ADD the bank join in A.3, so A.2's diff is minimal and A.3 extends it.
State this in the commit plan so the two do not fight over the same SELECT.

--------------------------------------------------------------------------------
A.4 -- JSONL export / backup endpoint (roadmap #12/#15)
--------------------------------------------------------------------------------
GOAL: close the import/export loop. Import (JSONL/CSV) exists; export does not.
A read endpoint that streams bank questions (and optionally responses) as JSONL.

BACKEND: GET /api/banks/<bank_id>/export (or /api/export?bank_id=) that reads
the bank's questions via the existing list_questions_for_bank reader and emits
one JSON object per line (the SAME shape the importer accepts -- round-trip
fidelity is the contract and the test). Content-Type application/x-ndjson (or
application/jsonl); Content-Disposition attachment with a filename. Pure read;
no schema, no mutation.
  - DECISION FORK: export questions only (round-trips through the importer) vs
    also export response history (a backup of drill.db activity). Recommend
    QUESTIONS-ONLY for A.4 (it is the import/export loop; the .db file is the
    activity backup already, per roadmap #15's own note). Response-history
    export is a separate, later item if wanted.
FRONTEND: an "Export" button near the import panel (boot.js owns import UI;
export sits beside it). Clicking triggers the download (an <a download> or a
fetch->blob->objectURL). No new el node if it can reuse the import section
container; if a node is needed, apply the N.1-audit ownership rule (owner ==
its dominant manipulator = boot).
TESTS: backend -- export emits valid JSONL, one object per line, and the output
re-imports to an identical question set (round-trip: export -> parse -> compare).
Empty bank -> empty body (or 204; state which). frontend -- button present;
(the actual download is a browser action, assert the fetch/URL wiring, not the
OS save dialog).
RISK: LOW. The round-trip test is the valuable one. VERIFICATION-PRACTICES HOOK:
this changes a load/route path (a new endpoint + a browser download), so per
CODING_CONVENTIONS "runtime verification" rule, smoke-test the REAL download end
to end, not only the jsdom wiring.

================================================================================
3. SUITE PROJECTION + WORKFLOW
================================================================================
Baseline 589 -> 589 + (a handful of asserts per commit; realistically +15..30
given this thread's test density, NOT the "one per commit" the old plans
under-estimated). State the true before/after count each commit against the
ACTUAL prior number, not a projection. Order A.1 -> A.2 -> A.3 -> A.4 (pure ->
query -> join -> endpoint), each green independently in a fresh clone with prior
A-patches re-applied. Set a git identity before the first commit.

================================================================================
4. WHAT IS EXPLICITLY OUT
================================================================================
- Chart.js / any charting (roadmap #31, Tier 4). Stats stay TEXT.
- Response-history export (A.4 is questions-only; .db is the activity backup).
- Any schema migration. If an item seems to want one, it is mis-scoped -- stop
  and re-plan; everything here rests on existing columns.
- Selection / SM2 / adaptive (Docs B/C).
- Per-question language in the payload (demoted, vocab-futures doc).

================================================================================
5. PARALLEL-TRACK HOOKS (for the study curriculum audit of this thread)
================================================================================
Pre-identified curriculum/audit material so the parallel track has targets:
- A.1: breakdown_by reused a THIRD time (the reuse-promise payoff; the sort-fork
  is a design-tension teaching point -- when to generalize a pure seam vs sort
  at the call site).
- A.2/A.3: the reader's SELECT/JOIN growth -- the DATABASE-layer analog of the
  el-ownership question (what belongs in the query vs computed in the pure
  summary). The snapshot-vs-live-text fork (A.2) is a real correctness decision
  worth an ADR IF it constrains a consumer (per the N.2 audit's docstring-vs-ADR
  rule).
- A.4: the import/export ROUND-TRIP as an invariant (export then import ==
  identity) -- a clean property-test teaching example.
