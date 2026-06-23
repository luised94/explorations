THREAD-MIGRATE (T2), Wave 0. Build the schema migration runner.

HANDOFF CONTEXT (so you don't re-investigate settled history):
- C-020 (T1) built the permanent test suite: tests/ organized by concern,
  159 assertions green. That is your safety net and your baseline.
- C-021 was a quick-fix thread immediately before this one: a source file
  contained invalid UTF-8 that broke pytest collection at the prior pinned
  commit. It is FIXED and committed; the baseline is back to 159 green at the
  SHA your SETUP verifies against. Do not re-investigate the corruption or
  "re-fix" encoding -- it is resolved. If your clean-clone baseline is not
  159 green, that is a NEW problem: STOP and report per SETUP, do not patch.

GOAL
A single-user local SQLite tool needs a disciplined, forward-only way to evolve
drill.db's schema across versions without losing a user's data (their drill.db
is their only copy -- per README "Backup", the file IS the backup). Today the
schema is created once in init_db with no versioning. Build the runner that
lets every later thread add a schema change safely.

WHY THIS THREAD MATTERS (dependency context -- do not implement these, just
design so they're cheap):
- D1 (next wave, THREAD-MODEL) will CONSUME this runner to add a grading-kind
  column and a metadata column. It must be able to add a migration by dropping
  in a new migration WITHOUT editing the runner's own code. Design for that.
- Later scheduler/curriculum threads add more columns and tables the same way.
  The runner is the one place schema change is expressed from now on.

REQUIREMENTS
- Track the applied schema version IN the database (PRAGMA user_version, or a
  schema_migrations table -- pick one, justify it briefly, record the choice
  as an ADR in decisions.md).
- Migrations are forward-only, ordered, idempotent to re-run (running the
  runner on an up-to-date DB is a safe no-op), and each runs in a transaction
  so a failure leaves the DB at the last good version, not half-migrated.
- A fresh DB (no version set) is brought to the current version by the same
  path -- reconcile this with the existing init_db so the two don't diverge
  (decide and document: does init_db become "migrate from empty", or does it
  stay and the runner layers on top? Your call; record it).
- Wire it to run at startup before serving (MAIN), and to be invokable on its
  own so a thread/test can migrate a temp DB. Keep the convention that
  timestamps/clock reads live at the HTTP/MAIN boundary, not in DATABASE.
- Clear operator-facing messages: what ran, and what version the DB is now at.

SCOPE / GUARDRAILS
- You MAY: add the migration runner and its migration definitions; add the
  startup wiring in MAIN; add the version-tracking mechanism; add tests under
  tests/ using the existing patterns (load_drill, temp_db, the WSGI helpers in
  tests/_support.py).
- You MAY NOT: change existing LOGIC/HTTP behavior or any endpoint contract;
  alter the live schema's existing columns; add the grading-kind/metadata
  columns themselves (that is D1's job -- you provide the mechanism, not the
  migration). No new runtime dependency -- stdlib sqlite3 only (ADR-001:
  Bottle is the ONE external dep).
- The runner's FIRST migration is a baseline that records the current schema
  as version 1 (or 0->1), so existing drill.db files adopt versioning cleanly
  without a destructive rebuild. Handle the already-populated drill.db case
  explicitly -- a user with real data must not lose it.

TESTS (extend the suite, do not weaken it)
- Add tests/test_migrate.py (DATABASE-tier, over a temp DB via temp_db):
  fresh DB migrates to current version; re-running is a no-op; version is
  readable after; a deliberately failing migration rolls back and leaves the
  prior version intact; an already-at-version DB is untouched.
- All 159 existing assertions must still pass. Report the new total.

ENCODING / TOOLING NOTES (carried from C-021 -- save yourself the round trip):
- The "ASCII only" rule applies to SOURCE and committed files, NOT generated
  bytecode or binary artifacts. tests/__pycache__/ and __pycache__/ contain
  non-ASCII .pyc bytes; they are gitignored and normal -- do not flag them as
  ASCII violations and do not try to "clean" them.
- If you ever diff/grep around data that may contain non-UTF-8 bytes, route
  the output through a latin-1 or errors=backslashreplace decode rather than
  fighting raw bytes -- git diff and UTF-8-expecting tools break on invalid
  UTF-8. (Unlikely to bite a schema thread, but noted so it doesn't surprise
  you if it does.)
- Any new source files you add must themselves be valid UTF-8 / ASCII -- the
  thing C-021 fixed. The suite will catch a regression at collection time.

DELIVERABLES
- The changed/added files, the ADR text for decisions.md (version mechanism +
  the init_db reconciliation decision), and a one-line roadmap note marking
  T2 done with the new assertion count.
- Tell me explicitly how D1 should add its migration: the exact, minimal steps
  a future thread follows to add a column. I will hand that verbatim to the D1
  launch, so make it copy-pasteable and complete.

Peruse, analyze, provide feedback. Do not start coding or changing any of the files. Confirm, ask questions, then we will plan, clarify and whatnot.
