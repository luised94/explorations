# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest"]
# ///
"""Tests for sm2.py. Frozen clock throughout: no test reads today's date.

Sections mirror sm2.py's banners: ALGORITHM tests are migrated from the
standalone assertion script (point values, EF clamps, interval progression,
sequences, recovery path); PARSER, SCHEDULER, and STORE tests are new with
the Phase 1 conversions (R5: one happy path, one error path, one non-effect
assertion per converted unit).

Run: uv run test_sm2.py        (provisions pytest via inline metadata)
 or: python -m pytest test_sm2.py -q
"""

import datetime
import sqlite3

import pytest

import sm2
from sm2 import (
    DueItem,
    Exercise,
    ItemState,
    apply_throttle_and_cap,
    commit_review,
    connect,
    domain_of,
    fetch_due_queue,
    fetch_item_state,
    fetch_today_new_by_domain,
    grade_item,
    init_schema,
    parse_text,
    reconcile,
    sm2_update,
)

TOL = 0.0001
START = datetime.date(2025, 1, 1).toordinal()  # frozen clock


# =============================================================================
# IMPORT INERTNESS
# =============================================================================


def test_import_is_inert(tmp_path, monkeypatch):
    """Importing sm2 must perform no filesystem access of its own.
    Proxy check: import succeeded above with no data/ or exercises/ present
    in an arbitrary cwd; module exposes main() instead of running it."""
    monkeypatch.chdir(tmp_path)
    import importlib

    importlib.reload(sm2)
    assert callable(sm2.main)


# =============================================================================
# ALGORITHM: point assertions (migrated)
# =============================================================================


@pytest.mark.parametrize(
    "grade, ef, interval, rep, lapse",
    [
        (2, 2.6, 1.0, 1, 0),
        (1, 2.36, 1.0, 1, 0),
        (0, 1.96, 1.0, 0, 1),
    ],
)
def test_point_values_from_defaults(grade, ef, interval, rep, lapse):
    r = sm2_update(grade, 2.5, 0.0, 0, 0, START)
    assert abs(r["easiness_factor"] - ef) < TOL
    assert r["interval_days"] == interval
    assert r["repetition_count"] == rep
    assert r["lapse_count"] == lapse
    assert r["due_date"] == START + round(interval)


def test_illegal_grade_is_loud():
    """A3 boundary: programmer errors stay loud, not value-ified."""
    with pytest.raises(KeyError):
        sm2_update(3, 2.5, 0.0, 0, 0, START)


# =============================================================================
# ALGORITHM: EF clamps under compounding (migrated)
# =============================================================================


def _run_sequence(grade, steps):
    ef, interval, rep, lapse, date = 2.5, 0.0, 0, 0, START
    history = []
    for _ in range(steps):
        r = sm2_update(grade, ef, interval, rep, lapse, date)
        ef = r["easiness_factor"]
        interval = r["interval_days"]
        rep = r["repetition_count"]
        lapse = r["lapse_count"]
        date = r["due_date"]
        history.append(r)
    return history


def test_ef_floor_holds_across_ten_fails():
    history = _run_sequence(0, 10)
    for step in history:
        assert step["easiness_factor"] >= 1.3 - TOL
    assert abs(history[-1]["easiness_factor"] - 1.3) < TOL


def test_ef_ceiling_holds_across_twenty_passes():
    history = _run_sequence(2, 20)
    for step in history:
        assert step["easiness_factor"] <= 3.0 + TOL
    assert abs(history[-1]["easiness_factor"] - 3.0) < TOL


# =============================================================================
# ALGORITHM: interval progression (migrated)
# =============================================================================


@pytest.mark.parametrize("ef", [1.3, 2.5, 3.0])
def test_first_pass_interval_is_one_regardless_of_ef(ef):
    assert sm2_update(2, ef, 0.0, 0, 0, START)["interval_days"] == 1.0


@pytest.mark.parametrize("ef", [1.3, 2.5, 3.0])
def test_second_pass_interval_is_six_regardless_of_ef(ef):
    assert sm2_update(2, ef, 1.0, 1, 0, START)["interval_days"] == 6.0


def test_third_pass_interval_multiplies_by_new_ef():
    r = sm2_update(2, 2.5, 6.0, 2, 0, START)
    assert abs(r["interval_days"] - 6.0 * 2.6) < TOL


def test_grade2_sequence_intervals_never_decrease():
    previous = 0.0
    for step in _run_sequence(2, 10):
        assert step["interval_days"] >= previous - TOL
        previous = step["interval_days"]


def test_grade0_sequence_stuck_item_invariants():
    for index, step in enumerate(_run_sequence(0, 10)):
        assert step["repetition_count"] == 0
        assert step["lapse_count"] == index + 1
        assert step["interval_days"] == 1.0


# =============================================================================
# ALGORITHM: recovery path (migrated)
# =============================================================================


def test_recovery_after_three_fails_retains_lowered_ef():
    ef, interval, rep, lapse, date = 2.5, 0.0, 0, 0, START
    for _ in range(3):
        r = sm2_update(0, ef, interval, rep, lapse, date)
        ef, interval, rep, lapse, date = (
            r["easiness_factor"],
            r["interval_days"],
            r["repetition_count"],
            r["lapse_count"],
            r["due_date"],
        )
    assert rep == 0 and lapse == 3
    assert abs(ef - 1.3) < TOL
    # pass 1: rep 0 -> 1, interval 1.0
    r = sm2_update(1, ef, interval, rep, lapse, date)
    assert r["interval_days"] == 1.0 and r["repetition_count"] == 1
    ef, interval, rep, lapse, date = (
        r["easiness_factor"],
        r["interval_days"],
        r["repetition_count"],
        r["lapse_count"],
        r["due_date"],
    )
    # pass 2: rep 1 -> 2, interval 6.0
    r = sm2_update(1, ef, interval, rep, lapse, date)
    assert r["interval_days"] == 6.0 and r["repetition_count"] == 2
    ef, interval, rep, lapse, date = (
        r["easiness_factor"],
        r["interval_days"],
        r["repetition_count"],
        r["lapse_count"],
        r["due_date"],
    )
    # pass 3: interval = 6.0 * 1.3 (floor holds on grade 1 at ef=1.3)
    r = sm2_update(1, ef, interval, rep, lapse, date)
    assert abs(r["interval_days"] - 6.0 * 1.3) < TOL
    assert r["repetition_count"] == 3


# =============================================================================
# ALGORITHM: grade_item (new pure apply step)
# =============================================================================


def _fresh_state(item_id="drive-x", last_review=0):
    return ItemState(item_id, 2.5, 0.0, 0, START, last_review, 0)


def test_grade_item_builds_complete_outcome():
    outcome = grade_item(_fresh_state(), 1, START, "note", "answer", 3.5)
    assert outcome.domain == "drive"
    assert outcome.sm2_grade == 3
    assert outcome.elapsed_days == 0  # never reviewed
    assert abs(outcome.easiness_factor_after - 2.36) < TOL
    assert outcome.repetition_count_after == 1
    assert outcome.due_date == START + 1
    assert outcome.error_note == "note"


def test_grade_item_elapsed_days_from_last_review():
    state = _fresh_state(last_review=START - 4)
    assert grade_item(state, 2, START).elapsed_days == 4


def test_domain_of():
    assert domain_of("drive-row-4way") == "drive"
    assert domain_of("c-pointers") == "c"


# =============================================================================
# PARSER
# =============================================================================

SAMPLE = """\
@@@ id: drive-a
tags: right-of-way, intersections
Body line one.

Body line two.
criteria: Yield right.
source: dmv2024
@@@ id: bio-b
tags:
no-metadata body
"""


def test_parse_text_happy_path():
    exercises, warnings = parse_text("f.md", SAMPLE)
    assert warnings == []
    by_id = {e.item_id: e for e in exercises}
    a = by_id["drive-a"]
    assert a.tags == ("right-of-way", "intersections")
    assert a.criteria == "Yield right."
    assert a.source == "dmv2024"
    assert a.content == "Body line one.\n\nBody line two."
    b = by_id["bio-b"]
    assert b.tags == () and b.criteria == "" and b.source == ""
    assert b.content == "no-metadata body"


def test_parse_text_duplicate_id_raises():
    text = "@@@ id: x-1\nbody\n@@@ id: x-1\nbody\n"
    with pytest.raises(ValueError, match="duplicate item id 'x-1'"):
        parse_text("f.md", text)


def test_parse_text_after_line_discarded_with_warning():
    text = "@@@ id: x-1\nafter: x-0\nbody\n"
    exercises, warnings = parse_text("f.md", text)
    assert exercises[0].content == "body"
    assert len(warnings) == 1
    assert "after" in warnings[0] and "x-1" in warnings[0]


def test_parse_text_preamble_before_first_delimiter_ignored():
    text = "stray preamble\n@@@ id: x-1\nbody\n"
    exercises, _ = parse_text("f.md", text)
    assert len(exercises) == 1 and exercises[0].content == "body"


def test_parse_exercises_cross_file_duplicate_raises(tmp_path):
    (tmp_path / "a.md").write_text("@@@ id: x-1\nbody a\n")
    (tmp_path / "b.md").write_text("@@@ id: x-1\nbody b\n")
    with pytest.raises(ValueError, match="duplicate item id 'x-1'"):
        sm2.parse_exercises(str(tmp_path))


def test_parse_exercises_reads_only_md(tmp_path):
    (tmp_path / "a.md").write_text("@@@ id: x-1\nbody\n")
    (tmp_path / "notes.txt").write_text("@@@ id: y-1\nignored\n")
    exercises, _ = sm2.parse_exercises(str(tmp_path))
    assert set(exercises) == {"x-1"}


# =============================================================================
# SCHEDULER
# =============================================================================


def _new(item_id):
    return DueItem(item_id, 0, START)


def _rev(item_id):
    return DueItem(item_id, 3, START)


def test_throttle_fresh_db_caps_new_items():
    """Migrated from run_validation: 15 fresh items across 3 domains, cap 9."""
    queue = [_new(f"{d}-val-{i}") for d in ("drive", "c", "bio") for i in range(1, 6)]
    result = apply_throttle_and_cap(queue, {}, 9, 1, 100)
    assert len(result) == 9


def test_throttle_reviews_always_pass_through():
    queue = [_rev(f"a-{i}") for i in range(20)] + [_new("b-1")]
    result = apply_throttle_and_cap(queue, {}, 0, 0, 100)
    assert len(result) == 20 and "b-1" not in result


def test_throttle_floor_reserves_one_per_starved_domain():
    # budget exhausted by domain 'a'; 'b' still gets its floor item
    queue = [_new(f"a-{i}") for i in range(5)] + [_new("b-1")]
    result = apply_throttle_and_cap(queue, {"a": 9}, 9, 1, 100)
    assert result == ["b-1"]


def test_throttle_max_reviews_truncates():
    queue = [_rev(f"a-{i}") for i in range(10)]
    result = apply_throttle_and_cap(queue, {}, 9, 1, 4)
    assert len(result) == 4
    assert result == [d.item_id for d in queue[:4]]


def test_throttle_preserves_due_order():
    queue = [_rev("a-2"), _new("b-1"), _rev("a-1")]
    result = apply_throttle_and_cap(queue, {}, 9, 1, 100)
    assert result == ["a-2", "b-1", "a-1"]


# =============================================================================
# STORE (in-memory DB, frozen clock)
# =============================================================================


def _db():
    conn = sqlite3.connect(":memory:", isolation_level=None)
    init_schema(conn)
    return conn


def _exercises(*item_ids, source=""):
    return {
        i: Exercise(i, f"content {i}", "", (), source if i == item_ids[0] else "") for i in item_ids
    }


def test_reconcile_inserts_new_and_is_idempotent():
    conn = _db()
    exercises = _exercises("drive-1", "bio-1", source="wozniak1999")
    inserted = reconcile(conn, exercises, START)
    assert inserted == {"drive-1", "bio-1"}
    # source round-trips at insert; absent source defaults to ""
    assert fetch_item_state(conn, "drive-1").due_date == START
    row = conn.execute("SELECT source FROM items WHERE item_id='drive-1'").fetchone()
    assert row[0] == "wozniak1999"
    # idempotent: second reconcile inserts nothing
    assert reconcile(conn, exercises, START) == set()
    assert conn.execute("SELECT COUNT(*) FROM items").fetchone()[0] == 2


def test_fetch_due_queue_filters_and_orders():
    conn = _db()
    reconcile(conn, _exercises("a-1", "a-2", "a-3"), START)
    conn.execute("UPDATE items SET due_date=? WHERE item_id='a-1'", (START + 5,))
    conn.execute("UPDATE items SET due_date=? WHERE item_id='a-3'", (START - 2,))
    queue = fetch_due_queue(conn, {"a-1", "a-2", "a-3"}, START)
    assert [d.item_id for d in queue] == ["a-3", "a-2"]
    assert fetch_due_queue(conn, set(), START) == []


def test_fetch_due_queue_ignores_orphan_filter_ids():
    """Items in the DB but absent from item_ids (deleted from files) are
    excluded -- characterizes current orphan behavior."""
    conn = _db()
    reconcile(conn, _exercises("a-1", "a-2"), START)
    queue = fetch_due_queue(conn, {"a-1"}, START)
    assert [d.item_id for d in queue] == ["a-1"]


def test_commit_review_is_atomic_and_consistent():
    conn = _db()
    reconcile(conn, _exercises("drive-1"), START)
    state = fetch_item_state(conn, "drive-1")
    outcome = grade_item(state, 2, START, None, "my answer", 1.5)
    commit_review(conn, outcome)
    after = fetch_item_state(conn, "drive-1")
    assert after.repetition_count == 1
    assert after.due_date == START + 1
    assert after.last_review == START
    log = conn.execute("SELECT grade, sm2_grade, domain, answer_text FROM review_log").fetchall()
    assert log == [(2, 5, "drive", "my answer")]
    assert fetch_today_new_by_domain(conn, START) == {"drive": 1}


def test_commit_review_rolls_back_whole_transaction_on_failure():
    """Negative/non-effect test: sabotage the log insert via a trigger; the
    item update must roll back too -- no advanced-but-unlogged state."""
    conn = _db()
    reconcile(conn, _exercises("drive-1"), START)
    conn.execute(
        "CREATE TRIGGER sabotage BEFORE INSERT ON review_log "
        "BEGIN SELECT RAISE(ABORT, 'sabotaged'); END"
    )
    state = fetch_item_state(conn, "drive-1")
    outcome = grade_item(state, 2, START)
    with pytest.raises(sqlite3.DatabaseError):
        commit_review(conn, outcome)
    # NON-effect: rejected operation left state untouched
    assert fetch_item_state(conn, "drive-1") == state
    assert conn.execute("SELECT COUNT(*) FROM review_log").fetchone()[0] == 0


def test_rehearse_path_is_a_non_call_not_a_flag():
    """Rehearse safety is structural: grading without commit_review leaves
    the DB byte-identical."""
    conn = _db()
    reconcile(conn, _exercises("drive-1"), START)
    state = fetch_item_state(conn, "drive-1")
    grade_item(state, 0, START)  # outcome built, never executed
    assert fetch_item_state(conn, "drive-1") == state
    assert conn.execute("SELECT COUNT(*) FROM review_log").fetchone()[0] == 0


def test_schema_matches_frozen_pre_refactor_columns():
    conn = _db()
    items_cols = [r[1] for r in conn.execute("PRAGMA table_info(items)")]
    assert items_cols == [
        "item_id",
        "easiness_factor",
        "interval_days",
        "repetition_count",
        "due_date",
        "last_review",
        "lapse_count",
        "source",
    ]
    log_cols = [r[1] for r in conn.execute("PRAGMA table_info(review_log)")]
    assert log_cols == [
        "id",
        "item_id",
        "grade",
        "sm2_grade",
        "review_date",
        "elapsed_days",
        "easiness_factor_before",
        "easiness_factor_after",
        "interval_days_before",
        "interval_days_after",
        "repetition_count_before",
        "domain",
        "error_note",
        "answer_text",
        "response_seconds",
    ]


# =============================================================================
# PIPELINE: the validation scenario, against the REAL pipeline
# =============================================================================


def test_full_pipeline_fresh_db_matches_old_validation_scenario():
    """The old run_validation scenario, now exercising the actual functions:
    15 fresh items, throttle to 9, grades cycling 0/1/2, state checked."""
    conn = _db()
    ids = [f"{d}-val-{i}" for d in ("drive", "c", "bio") for i in range(1, 6)]
    exercises = {i: Exercise(i, f"content {i}", "", (), "") for i in ids}
    reconcile(conn, exercises, START)
    queue = fetch_due_queue(conn, set(ids), START)
    review_queue = apply_throttle_and_cap(queue, fetch_today_new_by_domain(conn, START), 9, 1, 100)
    assert len(review_queue) == 9
    grades = [0, 1, 2, 0, 1, 2, 0, 1, 2]
    for item_id, grade in zip(review_queue, grades):
        state = fetch_item_state(conn, item_id)
        commit_review(conn, grade_item(state, grade, START))
    assert conn.execute("SELECT COUNT(*) FROM review_log").fetchone()[0] == 9
    expected_ef = {0: 1.96, 1: 2.36, 2: 2.60}
    expected_rep = {0: 0, 1: 1, 2: 1}
    for item_id, grade in zip(review_queue, grades):
        s = fetch_item_state(conn, item_id)
        assert abs(s.easiness_factor - expected_ef[grade]) < TOL
        assert s.repetition_count == expected_rep[grade]
        assert s.lapse_count == (1 if grade == 0 else 0)
        assert s.interval_days == 1.0
        assert s.due_date == START + 1


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
