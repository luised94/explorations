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
    # The registry as shipped must satisfy the import-time guard. As of D1 it
    # holds the single v2 entry (questions.metadata) and SCHEMA_VERSION is 2; the
    # guard already ran at import (load_drill would have raised otherwise), so
    # re-invoking it here documents the invariant and re-checks it explicitly.
    # This asserts the SHIPPED registry, not just the guard, so adding a
    # migration without updating it (or vice versa) surfaces here as a red.
    m, _conn = db
    m._check_migration_version_consistency()  # must not raise
    assert len(m.MIGRATIONS) == 1
    assert m.MIGRATIONS[0][0] == 2
    assert m.SCHEMA_VERSION == 2


def test_drift_guard_rejects_constant_ahead_of_registry(db):
    # SCHEMA_VERSION bumped without adding the matching migration -> reject.
    # The shipped registry now tops out at v2 (D1), so to be genuinely "ahead"
    # the constant must exceed the real top entry; computing from the registry
    # keeps this meaningful as the ceiling rises.
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
    # The shipped T2 case: DB baselined at 1 by init_db, empty registry, nothing
    # to do. from == to, no migrations applied, version untouched.
    m, conn = db
    before = m.get_schema_version(conn)
    result = m.run_migrations(conn, FIXED_NOW)
    assert result["from_version"] == before
    assert result["to_version"] == before
    assert result["applied"] == []
    assert m.get_schema_version(conn) == before


def test_run_migrations_applies_pending_in_order(db):
    # Two injected migrations layered ABOVE the real schema ceiling apply in
    # order, advance the version to the target, and report what ran. Versions
    # are computed from SCHEMA_VERSION (not literals) so this stays pending --
    # rather than silently no-opping -- as the shipped ceiling rises (D1+).
    m, conn = db
    base = m.SCHEMA_VERSION  # DB sits here after init_db; inject base+1, base+2
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
    v = m.SCHEMA_VERSION + 1  # one above the real ceiling, so genuinely pending
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
    base = m.SCHEMA_VERSION
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
    base = m.SCHEMA_VERSION
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
    # main() uses, lands at SCHEMA_VERSION. With the shipped empty registry the
    # runner is a no-op and the version is the init_db baseline (1).
    m = load_drill()
    dbpath = os.path.join(str(tmp_path), "fresh.db")
    m.DATABASE_PATH = dbpath
    conn = m.connect(dbpath)
    try:
        m.init_db(conn)
        conn.commit()
        result = m.run_migrations(conn, FIXED_NOW)
    finally:
        pass
    assert m.get_schema_version(conn) == m.SCHEMA_VERSION
    assert result["to_version"] == m.SCHEMA_VERSION
    assert result["applied"] == []  # empty registry: nothing to apply
    conn.close()


def test_existing_baselined_db_is_untouched_by_startup_sequence(tmp_path):
    # An existing DB already at the baseline is not re-stamped or advanced when
    # the startup sequence runs again: init_db is stamp-once, runner is a no-op.
    m = load_drill()
    conn = temp_db(m, tmp_path)  # init_db already ran; DB is at v1
    before_rows = conn.execute(
        "SELECT version, applied FROM schema_version ORDER BY version"
    ).fetchall()

    # Re-run the sequence as a restart would.
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
    base = m.SCHEMA_VERSION
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

    v = m.SCHEMA_VERSION + 1  # above the real ceiling, so genuinely pending
    injected = [(v, "add banks.note", add_column)]
    result = m.run_migrations(conn, FIXED_NOW, target_version=v, migrations=injected)
    assert result["to_version"] == v

    row = conn.execute(
        "SELECT id, name, note FROM banks WHERE id = ?", (bank_id,)
    ).fetchone()
    assert row["name"] == "pre-existing bank"  # data preserved
    assert row["note"] == ""  # new column present with default


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
