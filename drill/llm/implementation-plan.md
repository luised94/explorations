# Implementation plan: SM-2 + adaptive selection consolidation
## Commit-by-commit execution spec (supersedes consolidation-findings.md
## section 18, which it expands; on conflict, this document wins)

Audience: the implementing thread. Companion documents, both authoritative:
consolidation-findings.md (design, verification evidence, decided forks)
and refinements-and-wiring.md (deferred policy and phase D wiring).
Reference code: scheduler_port.py (landable pure core, target style) and
four spike test files (acceptance tests to port, all green as of writing).

## Thread protocol

P1. Verify before trusting. Re-confirm consolidation-findings.md section 1
    (ground truth) against the code FIRST: pick_next_question,
    run_migrations, insert_response signatures; SCHEMA_VERSION location
    and import guard; importable QTYPES excluding arithmetic. If any doc
    claim mismatches the repo, THE REPO WINS -- note the deviation and
    proceed.
P2. Baseline. Run bash drill/tests/run.sh (needs uv sync --group test in
    drill/, npm install jsdom acorn --no-save for frontend tests). Expect
    589 green; record the actual number as the baseline. Every commit
    below ends with the full suite green at baseline-plus-new-tests.
P3. One commit at a time, in order, no batching. Each commit: implement,
    extend tests, run suite, commit with a message naming the plan id
    (e.g. "C2: port scheduler pure core (plan C2)").
P4. Style contract (human requirement, non-negotiable): flat procedural
    code; pure functions over plain dicts/lists; no classes, no nested
    functions, no closures; full descriptive names, no abbreviations
    unless the noun is a word (url, id, http); clock/IO/DB/randomness at
    HTTP/MAIN/DATABASE edges only; layering config <- db <- logic <- http.
    ASCII only in all files.
P5. Record decisions. Append ADR entries to drill/llm/decisions.md as each
    resolved fork lands: the question_schedule separate-table resolution
    of ADR-025 (with C1), the once-per-day rule and rebuild semantics
    (with C4), the binary derive_recall_quality policy (with C2). Update
    STATUS.md thread notes at each STOP point.
P6. STOP points for human review: after D0, after B3, after C4, after A2.
    Summarize what landed, surface any deviations, wait.

## Phase D0: documentation lands first

D0. Commit consolidation-findings.md, refinements-and-wiring.md, and this
    plan into drill/llm/. Intent: future threads are self-sufficient; the
    repo convention (STATUS.md, decisions.md live there) extends to these.
    Acceptance: files present, ASCII clean, suite untouched and green.

## Phase B: adaptive selection (schema-free, ships alone)

B1. Per-question response stats reader.
    Files: drill/db.py, drill/tests/test_db.py.
    Add get_response_stats_for_bank(connection, bank_id) -> dict keyed by
    question_id with attempt_count, correct_count, last_answered. One
    aggregate over responses joined through questions (question_id IS NOT
    NULL). Tests: empty bank -> {}; mixed correctness counts exact;
    arithmetic (NULL question_id) rows excluded.
    Acceptance: reader pure-SQL, no logic import; suite green.

B2. Weighted selection pure core.
    Files: drill/logic.py, drill/tests/test_logic.py.
    Add miss_rate_weight(attempt_count, correct_count) and
    select_weighted_by_miss_rate(candidates, response_stats_by_question_id,
    history, random_value) exactly per scheduler_port.py. Port the four
    spike checks from test_selection_and_throttle.py: cold-start
    uniformity (seeded, tolerance 10 percent), miss-weighting ratio
    (struggling item favored by the predicted weight ratio, tolerance 15
    percent), history-window exclusion, all-recent fallback.
    Acceptance: functions pure (no random module use inside; random_value
    is a parameter); boundary-purity test green; suite green.

B3. Strategy dispatch wired end to end.
    Files: drill/http_layer.py, drill/tests/test_http.py.
    The next-question handler accepts a strategy parameter: "random"
    (default; existing pick_next_question path byte-identical) or
    "weighted" (fetch stats via B1, pass random.random() down). Context
    assembled entirely in HTTP. Tests: default path unchanged (existing
    tests prove it); weighted path returns a candidate; unknown strategy
    -> the standard error envelope.
    Acceptance: logic never queries; no frontend change required (the
    parameter is optional); suite green. STOP for human review.

## Phase C: SM-2 consolidation

C1. Migration 4: question_schedule.
    Files: drill/db.py, drill/config.py, drill/tests/test_migrate.py,
    drill/tests/test_db.py.
    Migrate fn creating question_schedule per consolidation-findings.md
    section 2 (all columns NOT NULL, ordinal-day integers); append
    (4, "add question_schedule (SM2 scheduling state, ADR-025)", fn) to
    MIGRATIONS; SCHEMA_VERSION = 4 in config.py (import guard enforces the
    pairing). Accessors: get_schedule_for_bank(connection, bank_id) ->
    dict keyed by question_id; upsert_schedule_row(connection, state_dict)
    using INSERT ... ON CONFLICT(question_id) DO UPDATE (spike statement).
    Tests: follow the migration-3 test pattern (fresh walk 1 -> 4;
    idempotent rerun; version stamped); accessor round trip.
    Acceptance: existing tables untouched; suite green.

C2. Scheduler pure core with its contract.
    Files: drill/logic.py, drill/tests/test_logic.py.
    Land from scheduler_port.py: constants; derive_recall_quality (binary
    v1 -- docstring forbids timing thresholds until per-qtype baselines
    exist, per ADR-025 no persisted grading column);
    advance_schedule_state; apply_interval_fuzz;
    schedule_update_allowed_today. Port the scheduler-invariant tests from
    sm2/test_sm2.py (EF floor across ten fails; ceiling across twenty
    passes; intervals 1 then 6 then multiply; grade-2 intervals never
    decrease; stuck-item invariants; recovery retains lowered EF) plus
    fuzz determinism/bounds/exemption checks from test_port_equivalence.py.
    Acceptance: invariant tests green; no clock/IO in any new function;
    suite green.

C3. Partition, backlog ordering, throttle, rebuild.
    Files: drill/logic.py, drill/config.py, drill/tests/test_logic.py.
    Land from scheduler_port.py: relative_overdueness;
    partition_candidates_by_schedule; apply_new_question_throttle;
    rebuild_schedule_from_response_log. Config: three constants
    (NEW_QUESTIONS_PER_DAY_MAXIMUM = 9, NEW_QUESTIONS_PER_BANK_MINIMUM = 1,
    REVIEWS_PER_SESSION_MAXIMUM = 100). The two partition sort lambdas may
    be flattened to module-level key functions per style. Tests: throttle
    floor/cap/spent/partial (spike checks); partition ordering (relative
    overdueness descending, not most-overdue-first -- assert the
    distinguishing case: short-interval 3-days-late outranks long-interval
    5-days-late); rebuild unit cases (NULL question_id skipped; once-per-
    day gate inside the fold).
    Acceptance: all pure; suite green.

C4. Review mode end to end plus THE INVARIANT TEST.
    Files: drill/http_layer.py, drill/db.py (new-today aggregate),
    drill/tests/test_http.py.
    The review path: stamp today = date.today().toordinal() ONCE per
    request at the top of the handler (write the midnight/timezone
    sentence into the docstring); fetch candidates, schedules, stats,
    new-today-by-bank (aggregate: repetition_count = 1 AND lapse_count = 0
    AND last_review = today, grouped by bank); partition -> throttle ->
    serve due (weighted order within due set) then admitted new; on
    answer: insert_response always, then IF schedule_update_allowed_today:
    derive_recall_quality -> advance_schedule_state -> apply_interval_fuzz
    -> recompute due_date -> upsert. Practice path untouched (never
    schedules; known limit recorded in findings section 11). THE TEST:
    port test_migration_and_simulation.py as a proper suite test -- multi-
    week simulated history through the HTTP-equivalent flow, assert
    rebuild_schedule_from_response_log(responses) equals stored
    question_schedule on every field to 1e-9, plus the same-day-repeat
    case (second response logged, schedule unchanged).
    Acceptance: invariant test green; boundary-purity green; suite green.
    STOP for human review.

C5. Measurement and terminal views.
    Files: drill/db.py, drill/logic.py (view builders), stats.js if a
    render is added, a thin cli entry (drill.py subcommands per the open
    decision -- confirm with human at the B3 stop), drill/tests.
    True-retention reader (verified CTE from the spike) and elapsed_ms
    percentiles per qtype/bank (refinements doc S1/S2). Port render_table
    and Column from sm2; port failures_view (show stored user_input -- the
    actual wrong answer -- instead of manual notes), leeches_view (bank
    name column replacing domain_of; LEECH_THRESHOLD to config),
    preview_view, dry_run_view. Views stay pure (rows in, string out);
    the cli entry does the fetching.
    Acceptance: views render against a populated test db; suite green.

## Phase A: authoring

A1. Pure transform.
    Files: drill/logic.py, drill/tests/test_logic.py.
    Land author_parse (FLATTENED: no nested close_block -- explicit
    accumulator plus a module-level flush function or duplicated flush at
    loop exit), author_render, author_template, funneling through
    _normalize_question_dict. Port all twelve spike checks from
    test_author.py including parse_jsonl equivalence and render round
    trip.
    Acceptance: no second validation authority (every block goes through
    the existing funnel); suite green.

A2. Shells.
    Files: cli entry, drill/tests.
    author_session editor loop (tempfile, $EDITOR, error banner reinsert,
    untouched-or-empty aborts) tested headlessly with a scripted EDITOR
    (port author_shell.py's demonstration as a test); stdin filter face
    emitting errors to stderr as file:line: message (the nvim quickfix
    contract); wire accepted records through the import path.
    Acceptance: tty and pipe faces share one parse; suite green. STOP.

A3. Content migration and archive.
    One-off script: parse sm2/exercises with the existing sm2 parser, map
    content -> question, criteria -> answer, tags fold, source into
    questions.metadata, tag all rows sm2-import, import through the
    funnel. Then archive sm2/ per findings section 14 (the invariant tests
    ported in C2 carry the contract; per the human's standing decision the
    standalone tool retires -- confirm at the A2 stop).

## Explicitly out of scope for this thread

Everything marked deferred or phase D in refinements-and-wiring.md (R1,
R2, S3-S5, F1, W1), operational logging (roadmap #17), FSRS, decks,
minute-grain learning steps, per-bank throttle overrides, multi-line
authoring values. If the implementing thread believes one should move into
scope, raise it at a STOP point; do not fold it in silently.

## Open decisions to confirm with the human at STOP points

1. Throttle floor keyed on bank_id (recommended, spiked) vs category_id.
2. CLI home: drill.py subcommands (recommended) vs separate module.
3. Retire sm2/ immediately after A3 (recommended) vs keep until
   grading_kind resolves.
