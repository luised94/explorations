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
