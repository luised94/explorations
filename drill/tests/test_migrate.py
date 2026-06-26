"""DATABASE-tier tests for the schema migration runner (ASCII only).

Concern: the forward-only migration mechanism -- the transaction-safe apply
primitive, the ordered runner loop, its idempotent no-op behavior, and the
all-or-nothing rollback that keeps a failed migration from leaving the DB
half-migrated. Exercised over a real temp SQLite file via temp_db, so the
connection under test is the one connect() actually returns (its isolation
mode is what makes the explicit-transaction discipline necessary -- see
_apply_one's docstring and decisions.md ADR on the transaction-mode finding).

What is deliberately NOT tested here: sqlite itself. We test our apply/rollback
discipline and our version bookkeeping, not the database engine.

Grown across commits: C-T2a-1 lands the _apply_one rollback proof; the runner
loop, init_db reconciliation, and the full contract suite arrive in later
commits of this thread.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from _support import load_drill, temp_db  # noqa: E402


# A fixed timestamp string standing in for the injected clock read. The runner
# takes the time as a parameter (clock reads live at the MAIN/HTTP boundary, not
# in DATABASE), so tests supply their own and never read the real clock.
FIXED_NOW = "2026-01-01T00:00:00+00:00"


@pytest.fixture
def db(tmp_path):
    """A fresh module + temp DB at the current (init_db) schema version."""
    m = load_drill()
    conn = temp_db(m, tmp_path)
    yield m, conn
    conn.close()


def test_apply_one_success_stamps_version_and_runs_migration(db):
    # A migration that adds a throwaway table commits, and its version row is
    # recorded. We use a probe table rather than a real schema column so this
    # test introduces no actual schema change (that is D1's job, not T2's).
    m, conn = db
    target = m.get_schema_version(conn) + 1

    def migrate(c):
        c.execute("CREATE TABLE _probe_ok (id INTEGER)")

    m._apply_one(conn, target, "add probe table", migrate, FIXED_NOW)

    assert m.get_schema_version(conn) == target
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "_probe_ok" in tables
    applied = conn.execute(
        "SELECT applied FROM schema_version WHERE version = ?", (target,)
    ).fetchone()["applied"]
    assert applied == FIXED_NOW


def test_apply_one_failure_rolls_back_ddl_and_version(db):
    # The core guarantee: a migration that performs DDL and then fails must
    # leave NEITHER the DDL NOR a version row behind. This is exactly the case
    # Python's default sqlite3 isolation gets wrong (DDL autocommits and
    # survives rollback); _apply_one's explicit BEGIN/ROLLBACK must defeat it.
    m, conn = db
    prior_version = m.get_schema_version(conn)
    target = prior_version + 1

    class Boom(Exception):
        pass

    def migrate(c):
        c.execute("CREATE TABLE _probe_fail (id INTEGER)")  # DDL, then fail
        raise Boom("deliberate failure mid-migration")

    with pytest.raises(Boom):
        m._apply_one(conn, target, "doomed migration", migrate, FIXED_NOW)

    # Version unchanged: the DB sits at the last good version, not target.
    assert m.get_schema_version(conn) == prior_version
    # The DDL rolled back too: the probe table must not exist.
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "_probe_fail" not in tables
    # No stray version row for the failed target.
    rows = conn.execute(
        "SELECT COUNT(*) AS n FROM schema_version WHERE version = ?", (target,)
    ).fetchone()["n"]
    assert rows == 0


def test_shipped_migrations_consistent_with_schema_version(db):
    # The registry as shipped must satisfy the import-time guard. As of #2 it
    # holds v2 (questions.metadata) and v3 (responses difficulty + leaf_count)
    # and SCHEMA_VERSION is 3; the guard already ran at import (load_drill would
    # have raised otherwise), so re-invoking it here documents the invariant and
    # re-checks it explicitly. This asserts the SHIPPED registry, not just the
    # guard, so adding a migration without bumping the constant (or vice versa)
    # surfaces here as a red.
    m, _conn = db
    m._check_migration_version_consistency()  # must not raise
    assert len(m.MIGRATIONS) == 2
    assert [version for version, _desc, _fn in m.MIGRATIONS] == [2, 3]
    assert m.SCHEMA_VERSION == 3


def test_drift_guard_rejects_constant_ahead_of_registry(db):
    # SCHEMA_VERSION bumped without adding the matching migration -> reject.
    # The shipped registry now tops out at v3 (#2); to be genuinely "ahead" the
    # constant must exceed the real top entry; computing from the registry keeps
    # this meaningful as the ceiling rises.
    m, _conn = db
    top = m.MIGRATIONS[-1][0]  # highest shipped migration version
    m.SCHEMA_VERSION = top + 1  # constant ahead of the registry top
    with pytest.raises(RuntimeError):
        m._check_migration_version_consistency()


def test_drift_guard_rejects_nonascending_versions(db):
    # Out-of-order / duplicated versions break the runner's ordered walk.
    m, _conn = db
    noop = lambda c: None  # noqa: E731 -- trivial stand-in migration
    m.SCHEMA_VERSION = 3
    m.MIGRATIONS = [(3, "later", noop), (2, "earlier", noop)]
    with pytest.raises(RuntimeError):
        m._check_migration_version_consistency()


def test_drift_guard_rejects_gap_from_baseline(db):
    # Migrations must run gap-free from the version-1 baseline (first is 2).
    m, _conn = db
    noop = lambda c: None  # noqa: E731
    m.SCHEMA_VERSION = 3
    m.MIGRATIONS = [(3, "skips 2", noop)]  # starts at 3, leaves a gap
    with pytest.raises(RuntimeError):
        m._check_migration_version_consistency()


# --- run_migrations loop ---


def test_run_migrations_empty_registry_is_noop(db):
    # An empty registry has nothing to apply, regardless of the DB's version:
    # from == to, nothing applied, version untouched. The shipped MIGRATIONS is
    # non-empty as of D1, so this passes migrations=[] explicitly to test the
    # empty-registry contract itself (the DB is at the baseline via temp_db).
    m, conn = db
    before = m.get_schema_version(conn)
    result = m.run_migrations(conn, FIXED_NOW, migrations=[])
    assert result["from_version"] == before
    assert result["to_version"] == before
    assert result["applied"] == []
    assert m.get_schema_version(conn) == before


def test_run_migrations_applies_pending_in_order(db):
    # Two injected migrations layered ABOVE the DB's current version apply in
    # order, advance the version to the target, and report what ran. Versions
    # are computed from the DB's actual version (temp_db is at the baseline),
    # not a literal or SCHEMA_VERSION, so the injected steps are genuinely
    # pending regardless of where the baseline/ceiling sit.
    m, conn = db
    base = m.get_schema_version(conn)  # the DB's current version (baseline)
    v1, v2 = base + 1, base + 2
    calls = []

    def mk(tag):
        def migrate(c):
            calls.append(tag)
            c.execute("CREATE TABLE _probe_%s (id INTEGER)" % tag)

        return migrate

    injected = [(v1, "add two", mk("two")), (v2, "add three", mk("three"))]
    result = m.run_migrations(conn, FIXED_NOW, target_version=v2, migrations=injected)

    assert calls == ["two", "three"]  # ascending order
    assert result["from_version"] == base
    assert result["to_version"] == v2
    assert result["applied"] == [(v1, "add two"), (v2, "add three")]
    assert m.get_schema_version(conn) == v2


def test_run_migrations_is_idempotent_on_rerun(db):
    # Running the same set again selects nothing: a safe no-op.
    m, conn = db
    v = m.get_schema_version(conn) + 1  # one above the DB's current version
    injected = [(v, "add two", lambda c: c.execute("CREATE TABLE _p2 (id INTEGER)"))]
    first = m.run_migrations(conn, FIXED_NOW, target_version=v, migrations=injected)
    assert first["applied"] == [(v, "add two")]

    second = m.run_migrations(conn, FIXED_NOW, target_version=v, migrations=injected)
    assert second["from_version"] == v
    assert second["to_version"] == v
    assert second["applied"] == []
    assert m.get_schema_version(conn) == v


def test_run_migrations_respects_target_version(db):
    # target_version stops the walk short of the latest available migration.
    m, conn = db
    base = m.get_schema_version(conn)
    v1, v2 = base + 1, base + 2
    injected = [
        (v1, "two", lambda c: c.execute("CREATE TABLE _t2 (id INTEGER)")),
        (v2, "three", lambda c: c.execute("CREATE TABLE _t3 (id INTEGER)")),
    ]
    result = m.run_migrations(conn, FIXED_NOW, target_version=v1, migrations=injected)
    assert result["to_version"] == v1
    assert result["applied"] == [(v1, "two")]
    assert m.get_schema_version(conn) == v1


def test_run_migrations_stops_at_last_good_version_on_failure(db):
    # A failing migration partway through leaves the DB at the last good
    # version, with the earlier migration committed and the later one absent.
    m, conn = db
    base = m.get_schema_version(conn)
    v1, v2, v3 = base + 1, base + 2, base + 3

    class Boom(Exception):
        pass

    def ok(c):
        c.execute("CREATE TABLE _good (id INTEGER)")

    def bad(c):
        c.execute("CREATE TABLE _bad (id INTEGER)")  # DDL, then fail
        raise Boom("migration fails")

    injected = [(v1, "good", ok), (v2, "bad", bad), (v3, "never", ok)]
    with pytest.raises(Boom):
        m.run_migrations(conn, FIXED_NOW, target_version=v3, migrations=injected)

    # Stopped at v1: the first migration committed, the second rolled back,
    # the third never ran.
    assert m.get_schema_version(conn) == v1
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "_good" in tables
    assert "_bad" not in tables


# --- init_db reconciliation (the startup sequence MAIN runs) ---


def test_fresh_db_reaches_current_version_via_startup_sequence(tmp_path):
    # A fresh DB, taken through the exact init_db -> run_migrations sequence
    # main() uses, lands at SCHEMA_VERSION with every migration applied. init_db
    # stamps the BASELINE (1) and builds the baseline schema; the runner then
    # advances 1 -> SCHEMA_VERSION, applying the shipped migrations. This is the
    # regression guard for the defect where init_db stamped SCHEMA_VERSION
    # directly: a fresh DB then skipped the migrations and lacked their columns.
    m = load_drill()
    dbpath = os.path.join(str(tmp_path), "fresh.db")
    m.DATABASE_PATH = dbpath
    conn = m.connect(dbpath)
    try:
        m.init_db(conn)
        conn.commit()
        assert m.get_schema_version(conn) == m.BASELINE_SCHEMA_VERSION  # stamped 1
        result = m.run_migrations(conn, FIXED_NOW)
    finally:
        pass
    assert m.get_schema_version(conn) == m.SCHEMA_VERSION
    assert result["from_version"] == m.BASELINE_SCHEMA_VERSION
    assert result["to_version"] == m.SCHEMA_VERSION
    # The shipped registry is non-empty (D1+), so the fresh path applies it.
    assert [v for v, _desc in result["applied"]] == list(
        range(m.BASELINE_SCHEMA_VERSION + 1, m.SCHEMA_VERSION + 1)
    )
    # The proof the migration actually ran on the fresh path: its column exists.
    cols = [r[1] for r in conn.execute("PRAGMA table_info(questions)")]
    assert "metadata" in cols
    conn.close()


def test_existing_baselined_db_is_untouched_by_startup_sequence(tmp_path):
    # An existing DB already at the CURRENT version is not re-stamped or advanced
    # when the startup sequence runs again: init_db is stamp-once and the runner
    # finds nothing pending. temp_db stamps only the baseline (1) and does not
    # migrate, so we first bring the DB fully current (init_db already ran; apply
    # the shipped migrations once), then assert the SECOND sequence is a no-op.
    m = load_drill()
    conn = temp_db(m, tmp_path)  # init_db ran; DB at the baseline (1)
    m.run_migrations(conn, FIXED_NOW)  # advance to SCHEMA_VERSION
    assert m.get_schema_version(conn) == m.SCHEMA_VERSION
    before_rows = conn.execute(
        "SELECT version, applied FROM schema_version ORDER BY version"
    ).fetchall()

    # Re-run the sequence as a restart would: must change nothing.
    m.init_db(conn)
    conn.commit()
    result = m.run_migrations(conn, FIXED_NOW)

    after_rows = conn.execute(
        "SELECT version, applied FROM schema_version ORDER BY version"
    ).fetchall()
    assert [tuple(r) for r in after_rows] == [tuple(r) for r in before_rows]
    assert result["applied"] == []
    assert result["from_version"] == result["to_version"] == m.SCHEMA_VERSION
    conn.close()


# --- C-T2c capstone: recovery, data preservation, and the unbaselined path ---


def test_rerun_after_failed_migration_recovers_and_advances(db):
    # The realistic operator path: a migration fails (DB stays at the last good
    # version), the migration is corrected, and the next run succeeds and
    # advances. Proves a rolled-back failure does not poison the connection for
    # a later successful run.
    m, conn = db
    base = m.get_schema_version(conn)
    v = base + 1

    class Boom(Exception):
        pass

    def bad(c):
        c.execute("CREATE TABLE _recover (id INTEGER)")
        raise Boom("first attempt fails")

    failing = [(v, "attempt", bad)]
    with pytest.raises(Boom):
        m.run_migrations(conn, FIXED_NOW, target_version=v, migrations=failing)
    assert m.get_schema_version(conn) == base  # held at last good version

    # Corrected migration, same version, re-run: now it advances cleanly.
    def good(c):
        c.execute("CREATE TABLE _recover (id INTEGER)")

    fixed = [(v, "attempt", good)]
    result = m.run_migrations(conn, FIXED_NOW, target_version=v, migrations=fixed)
    assert result["applied"] == [(v, "attempt")]
    assert m.get_schema_version(conn) == v
    tables = {
        r["name"]
        for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
    }
    assert "_recover" in tables


def test_existing_user_data_survives_a_migration(db):
    # The data-loss guarantee: a user's rows (their only copy -- the .db file IS
    # the backup) must survive a schema change. Seed a category + bank, run a
    # column-adding migration, and confirm the pre-existing rows are intact and
    # the new column is present with its default.
    m, conn = db
    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    arith_id = cats["arithmetic"]
    bank_id = m.insert_bank(
        conn,
        category_id=arith_id,
        name="pre-existing bank",
        source="seed",
        created=FIXED_NOW,
        language=None,
    )
    conn.commit()

    def add_column(c):
        # An additive, non-destructive change of the kind D1 makes. This injected
        # column (banks.note) is test-only and distinct from the real v2
        # (questions.metadata); the test runs ONLY this injected registry.
        c.execute("ALTER TABLE banks ADD COLUMN note TEXT NOT NULL DEFAULT ''")

    v = m.get_schema_version(conn) + 1  # one above the DB's current version
    injected = [(v, "add banks.note", add_column)]
    result = m.run_migrations(conn, FIXED_NOW, target_version=v, migrations=injected)
    assert result["to_version"] == v

    row = conn.execute(
        "SELECT id, name, note FROM banks WHERE id = ?", (bank_id,)
    ).fetchone()
    assert row["name"] == "pre-existing bank"  # data preserved
    assert row["note"] == ""  # new column present with default


def test_real_v2_migration_adds_questions_metadata_over_existing_rows(db):
    # D1's deliverable, exercised through the REAL MIGRATIONS (not an injected
    # list): a baseline database with several pre-existing questions across
    # multiple qtypes is migrated to the current version; every pre-existing row
    # backfills to the '{}' default. temp_db (via the db fixture) sits at the
    # baseline with the migration unapplied -- exactly the pre-migration state.
    # Seeding MANY rows across qtypes (not one) proves the default applies to
    # the whole table, not a single row.
    m, conn = db
    assert m.get_schema_version(conn) == m.BASELINE_SCHEMA_VERSION  # pre-migration

    # Pre-existing data, seeded BEFORE the migration, spanning qtypes.
    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    bank_id = m.insert_bank(
        conn,
        category_id=cats["arithmetic"],
        name="pre-existing bank",
        source="seed",
        created=FIXED_NOW,
        language=None,
    )
    seeded = [
        {"qtype": m.QTYPE_FREE_RESPONSE, "question": "q-free", "answer": "a"},
        {"qtype": m.QTYPE_MULTIPLE_CHOICE, "question": "q-mc", "answer": "b"},
        {"qtype": m.QTYPE_TRANSLATE, "question": "q-tr", "answer": "c"},
        {"qtype": m.QTYPE_IDENTIFY, "question": "q-id", "answer": "d"},
    ]
    m.insert_questions_bulk(conn, bank_id, seeded, FIXED_NOW)
    conn.commit()

    # Sanity: the baseline questions table has no metadata column yet.
    precols = [r[1] for r in conn.execute("PRAGMA table_info(questions)")]
    assert "metadata" not in precols

    # Run the REAL registry: it must advance the baseline to the current version
    # via the shipped v2 entry.
    result = m.run_migrations(conn, FIXED_NOW)
    assert result["from_version"] == m.BASELINE_SCHEMA_VERSION
    assert result["to_version"] == m.SCHEMA_VERSION
    assert (2, "add questions.metadata") in result["applied"]
    assert m.get_schema_version(conn) == m.SCHEMA_VERSION

    # The new column exists...
    postcols = [r[1] for r in conn.execute("PRAGMA table_info(questions)")]
    assert "metadata" in postcols

    # ...and EVERY pre-existing row backfilled to the '{}' default, intact.
    rows = conn.execute(
        "SELECT question, metadata FROM questions ORDER BY id"
    ).fetchall()
    assert len(rows) == len(seeded)  # all rows survived
    assert {r["question"] for r in rows} == {s["question"] for s in seeded}
    assert all(r["metadata"] == "{}" for r in rows)  # default on every row


def test_run_migrations_on_unbaselined_db_treats_current_as_zero(tmp_path):
    # When no baseline is stamped yet (get_schema_version is None), the runner
    # treats current as 0 for selection and reports from_version as 0. This
    # isolates that selection rule, so it passes an explicit empty registry:
    # the raw DB has no tables for the real (D1+) migrations to ALTER, and the
    # rule under test is independent of what the shipped registry contains.
    m = load_drill()
    dbpath = os.path.join(str(tmp_path), "raw.db")
    m.DATABASE_PATH = dbpath
    conn = m.connect(dbpath)  # NOT init_db'd: schema_version table absent
    try:
        assert m.get_schema_version(conn) is None
        result = m.run_migrations(conn, FIXED_NOW, migrations=[])
        assert result["from_version"] == 0
        assert result["to_version"] == 0
        assert result["applied"] == []
    finally:
        conn.close()


def test_real_v3_migration_adds_response_difficulty_over_existing_rows(db):
    # #2's migration deliverable, exercised through the REAL MIGRATIONS: a
    # baseline DB with several pre-existing responses is migrated to the current
    # version; both new columns appear and EVERY pre-existing row backfills to
    # NULL (the honest "not recorded" value for rows answered before #2). The db
    # fixture sits at the baseline with the migration unapplied -- the
    # pre-migration state. Seeding MANY rows proves NULL applies to the whole
    # table. Capture of real values into these columns is C-D2g, NOT this commit.
    m, conn = db
    assert m.get_schema_version(conn) == m.BASELINE_SCHEMA_VERSION  # pre-migration

    # Pre-existing responses, seeded BEFORE the migration. Need a session to own
    # them (responses.session_id is NOT NULL with a FK to sessions).
    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    session_id = m.start_session(
        conn, category_id=cats["arithmetic"], started=FIXED_NOW
    )
    for index in range(4):
        m.insert_response(
            conn,
            session_id=session_id,
            question_text="%d + %d" % (index, index),
            answer_text=str(index + index),
            user_input=str(index + index),
            correct=True,
            answered=FIXED_NOW,
        )
    conn.commit()

    # Sanity: the baseline responses table has neither new column yet.
    precols = [r[1] for r in conn.execute("PRAGMA table_info(responses)")]
    assert "difficulty" not in precols
    assert "leaf_count" not in precols

    # Run the REAL registry: advance the baseline to the current version, which
    # now includes the v3 entry.
    result = m.run_migrations(conn, FIXED_NOW)
    assert result["from_version"] == m.BASELINE_SCHEMA_VERSION
    assert result["to_version"] == m.SCHEMA_VERSION
    assert (3, "add responses.difficulty and leaf_count") in result["applied"]
    assert m.get_schema_version(conn) == m.SCHEMA_VERSION

    # Both new columns exist...
    postcols = [r[1] for r in conn.execute("PRAGMA table_info(responses)")]
    assert "difficulty" in postcols
    assert "leaf_count" in postcols

    # ...and EVERY pre-existing row backfilled to NULL on both, intact.
    rows = conn.execute(
        "SELECT question_text, difficulty, leaf_count FROM responses ORDER BY id"
    ).fetchall()
    assert len(rows) == 4  # all rows survived
    assert all(r["difficulty"] is None for r in rows)
    assert all(r["leaf_count"] is None for r in rows)


def test_v3_columns_are_nullable(db):
    # Confirm the columns accept NULL explicitly (the elapsed_ms precedent): a
    # row inserted after the migration without these values stores NULL, not a
    # numeric default. insert_response does not yet write them (that is C-D2g);
    # here we just prove the schema permits NULL.
    m, conn = db
    m.run_migrations(conn, FIXED_NOW)
    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    session_id = m.start_session(
        conn, category_id=cats["arithmetic"], started=FIXED_NOW
    )
    response_id = m.insert_response(
        conn,
        session_id=session_id,
        question_text="2 + 2",
        answer_text="4",
        user_input="4",
        correct=True,
        answered=FIXED_NOW,
    )
    row = conn.execute(
        "SELECT difficulty, leaf_count FROM responses WHERE id = ?", (response_id,)
    ).fetchone()
    assert row["difficulty"] is None
    assert row["leaf_count"] is None
