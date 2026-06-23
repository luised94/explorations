THREAD-MODEL (D1), Wave 1. Consume the migration runner: add the first real
schema migration (the grading-kind + question-metadata columns).

This file is the launch brief. It has three parts: SETUP (verbatim, run before
anything else), the THREAD itself (goal/scope/tests/deliverables), and a
FORWARD RECOMMENDATION for what comes after D1.

================================================================================
SETUP -- do this before anything else, and STOP if any check fails.
Report results back at each numbered step before proceeding.
================================================================================
0. PRECONDITIONS (fill these in; if any are still placeholders, STOP and ask):
   - REPO_URL : https://github.com/luised94/explorations.git   (public, read-only)
   - BRANCH   : main
   - SHA      : <SET THIS YOURSELF -- the commit at the tip of T2, after the
                six C-T2* commits land. Do NOT proceed against a guessed SHA.>
   You have NO push credentials: do not push, open PRs, or modify the remote
   in any way.
1. Sparse-clone just the drill/ directory:
   git clone --depth 1 --filter=blob:none --sparse REPO_URL /tmp/repo
   cd /tmp/repo && git sparse-checkout set drill && cd drill
   NOTE: cone-mode sparse-checkout also materializes ROOT-level files
   (README.md, .gitignore). That is expected -- it is NOT "the rest of the
   repo." Only top-level *directories* other than drill/ would be a problem.
2. Verify you have the right code, and report all four back before proceeding:
   - `ls -la /tmp/repo`     (confirm the only top-level DIRECTORY is drill/)
   - `ls -laR .`            (the drill/ working tree)
   - `git -C /tmp/repo rev-parse HEAD`            (must equal SHA exactly)
   - `git -C /tmp/repo log -1 --oneline --decorate` (must show HEAD -> BRANCH)
   If HEAD != SHA or the branch is wrong, STOP -- do not work against the wrong
   tree.
3. Establish the safety net is green BEFORE changing anything:
   - uv sync --group test
   - npm install jsdom --no-save          (needs Node 18+; verify `node -v`)
   - bash tests/run.sh
   Expected baseline at the T2 tip: 175 assertions green -- backend 100,
   frontend 75 (6/21/19/23/6), ending "ALL GREEN". Backend 100 = the original
   84 plus the 16 in tests/test_migrate.py.
   If the baseline is NOT 175 green on a clean clone at the verified SHA, STOP
   and report what failed -- including collection/import/syntax errors, which
   count as red even though pytest reports "errors" not "failures." That is a
   problem with the STARTING STATE, not something to patch silently. Wait for
   go-ahead.
   PORTABILITY: tests/run.sh and helpers assume bash. If a command uses
   bash-only syntax (e.g. ${PIPESTATUS[...]}), invoke it with `bash`, not `sh`;
   `$?` on the immediately-following line is the portable fallback.

SCOPE for this thread (do not touch files outside this list; if you think you
need to, STOP and ask):
   - drill.py                  (the migration fn, the MIGRATIONS entry, the
                                SCHEMA_VERSION bump, and any LOGIC/HTTP wiring
                                that READS the new columns -- see scope notes)
   - tests/test_migrate.py     (the migration's own DATABASE-tier test)
   - tests/test_db.py and/or tests/test_http.py (only if the new columns are
                                read back through existing functions/endpoints
                                and you add coverage for that read path)
   - llm/decisions.md          (ALWAYS in scope for recording a decision)
   - llm/roadmap.md            (one-line status note if D1 completes a roadmap
                                item)
   decisions.md is ALWAYS in scope for recording a decision, even when the code
   change is elsewhere.

================================================================================
THREAD: D1 -- the first real migration
================================================================================
HANDOFF CONTEXT (settled history -- do not re-investigate):
- T1 (C-020) built the permanent test suite; T2 (C-T2*) built the forward-only
  migration runner. The runner is your mechanism; you are its first consumer.
- The exact, copy-pasteable procedure for adding a migration is in
  decisions.md under the "--- HANDOFF: how D1 adds a migration ---" marker.
  Follow it verbatim. If a step is wrong or awkward in practice, that is a
  FINDING worth recording (the procedure is untested prose until you run it).
- The runner ships with an EMPTY MIGRATIONS list and SCHEMA_VERSION = 1
  (today's schema is the version-1 baseline produced by init_db). Your
  migration is version 2.

GOAL
Add the first real schema change through the runner: a persisted grading-kind
column and a question-level metadata column, so later threads (difficulty, SM2,
new drill types) have somewhere to record per-question grading intent and
arbitrary structured extras without another schema scramble.

WHY THIS THREAD MATTERS
- It exercises the T2 runner end-to-end while the mechanism is fresh: if the
  registry/SCHEMA_VERSION/transaction design is awkward in practice, we learn it
  now, cheaply, on the very next thread.
- It validates the verbatim D1 handoff instructions in decisions.md.
- grading-kind is the PERSISTED counterpart to validate_answer's existing
  qtype dispatch (spec 4.5). T1 deliberately test-covered that dispatch seam so
  you can refactor against a green net.

REQUIREMENTS / DECISIONS TO PIN (these are open -- decide and record as ADRs):
- WHICH TABLE gets metadata. banks.metadata ALREADY EXISTS (drill.py schema).
  The original T2 brief said "a metadata column"; the obvious gap is
  questions.metadata (questions has none). Confirm the intent is a
  questions-level metadata column, or correct it.
- grading-kind SEMANTICS vs qtype. The spec (4.2/4.5) already dispatches
  validation by qtype, including the validator-only "arithmetic" kind. Decide
  explicitly: is grading_kind a NEW axis (e.g. exact / numeric-tolerance /
  set-membership) orthogonal to qtype, or a persisted denormalization of the
  qtype-derived grading path? Do NOT duplicate the validate_answer model; the
  column should feed it, not fork it. Record the relationship as an ADR.
- COLUMN SHAPE. Additive only, NOT NULL DEFAULT, so existing rows backfill
  cleanly (the .db file is the user's only copy -- no data loss). Pick the
  default that makes pre-existing questions keep their current behavior
  (grading_kind default must reproduce today's validate_answer result).

SCOPE / GUARDRAILS
- You MAY: add the version-2 migration fn + MIGRATIONS entry; bump
  SCHEMA_VERSION to 2; read the new columns where a handler/validator needs
  them; add tests.
- You MAY NOT: edit the runner (_apply_one / run_migrations /
  _check_migration_version_consistency); change the version-1 baseline DDL in
  SCHEMA_STATEMENTS/init_db (your change is a migration, not a baseline edit);
  alter or drop existing columns; weaken the suite. No new runtime dependency
  (stdlib sqlite3 + Bottle only; ADR-001).
- Migration is additive and reversible-by-omission only (forward-only; no down
  migrations).

TESTS (extend the suite, do not weaken it)
- In tests/test_migrate.py, add a DATABASE-tier test that runs the REAL
  MIGRATIONS (not an injected list) over a temp DB and asserts: the new columns
  exist with their defaults; a pre-existing row (seeded before the migration)
  survives and reads back its default; SCHEMA_VERSION/registry consistency holds
  (the import-time guard already enforces this, but assert the DB reaches
  version 2).
- If a handler or validator now READS the columns, cover that read path in
  test_http.py / test_db.py using the existing patterns (load_drill, temp_db,
  wsgi_* helpers in tests/_support.py).
- All 175 existing assertions must still pass. Report the new total.

DELIVERABLES
- The changed files; the ADR text (which-table + grading_kind-vs-qtype
  relationship + default choice); a one-line roadmap note if a roadmap item is
  completed; the new assertion count.
- A short note on whether the decisions.md D1 handoff procedure was correct as
  written, or needed correction -- so the procedure can be fixed for D2+.

Peruse, analyze, provide feedback. Do not start coding. Confirm, ask questions,
then plan/clarify.

================================================================================
FORWARD RECOMMENDATION (from the T2 thread, for sequencing after D1)
================================================================================
Context: as of the T2 tip, two roadmap foundations are DONE -- the test suite
(T1, #8) and the migration runner (T2, #11). The roadmap's own Section 4
sequencing still holds, with these adjustments given what is now built:

1. D1 (this thread) -- the migration's first consumer. Highest leverage NOW
   because it exercises the fresh runner end-to-end and validates the handoff
   procedure. (You are here.)

2. Assertion / invariant pass (#14, tagged T2). Either FOLD INTO D1 (D1 already
   touches the validate_answer/qtype seam, which is exactly where boundary
   assertions belong) or take it as the thread immediately after D1. Doing it
   on/near the qtype seam hardens the boundary D1's grading_kind leans on.

3. Arithmetic-depth chain (Phase 1), in this order because each builds on the
   last: operators (#4) -> generalize expression trees (#5) -> difficulty
   control (#2) -> adaptive selection (#7). Operators is the near-zero-risk
   warm-up (data added to the operator table). Tree generalization is the
   instructive centerpiece (a recursive generate_expression + renderer
   parenthesization; evaluator/renderer already recurse). Difficulty is the knob
   on top; adaptive selection is the clean single-function swap that follows.
   Now unblocked because both safety nets (tests + migrations) exist.

4. Modularize (Phase 2, #1 on value). Deliberately sequenced AFTER a round of
   arithmetic work so you split code you understand cold; the section-comment
   boundaries in drill.py already mark the seams (config/db/logic/http/main).

5. Then per the roadmap: study curriculum (Phase 3, gated behind modularization)
   -> SM2 consolidation (Phase 4, gated behind adaptive selection #7, since SM2
   IS a selection policy and should plug into that seam) -> breadth/depth
   (Phase 5+: logic #9 and code #10 drills reuse existing text/MC structure
   cheaply; typing #12 and timed mode later).

Do NOT jump ahead to modularization or the curriculum before the arithmetic
round: the roadmap gates them on purpose, and the rationale is rework-avoidance,
not preference.
