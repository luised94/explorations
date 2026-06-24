"""DATABASE-tier tests -- real readers/writers over a temp SQLite file.

Concern: persistence round-trips and the get_responses_for_stats filter /
ordering / elapsed_ms contract. Harvested from the DB half of test_c019a.py
and given a proper fixture so each test gets a fresh seeded DB.

What is deliberately NOT tested here (phase0.md Section B, "what NOT to
test"): sqlite itself. We test our queries and our row->dict shaping, not the
database engine.
"""

import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from _support import current_db, load_drill  # noqa: E402


def _iso(dt):
    return dt.isoformat()


@pytest.fixture
def seeded(tmp_path):
    """A fresh module + temp DB seeded with a known response spread.

    Arithmetic: 3 recent (2 correct, 1 wrong) + 1 ten-day-old correct.
    Second category: 1 recent correct.
    Returns (module, conn, ids dict).
    """
    m = load_drill()
    conn = current_db(m, tmp_path)

    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    arith_id = cats["arithmetic"]
    second_name = next(n for n in cats if n != "arithmetic")
    second_id = cats[second_name]

    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)
    recent = now - timedelta(days=1)

    s_arith = m.start_session(conn, arith_id, _iso(now))
    s_second = m.start_session(conn, second_id, _iso(now))
    conn.commit()

    def resp(sid, q, a, ui, correct, when, ms):
        m.insert_response(
            conn,
            session_id=sid,
            question_text=q,
            answer_text=a,
            user_input=ui,
            correct=correct,
            answered=_iso(when),
            question_id=None,
            elapsed_ms=ms,
        )

    resp(s_arith, "1+1", "2", "2", True, recent, 1500)
    resp(s_arith, "2+2", "4", "4", True, recent, 900)
    resp(s_arith, "3+3", "6", "5", False, recent, None)
    resp(s_arith, "9+9", "18", "18", True, old, 4000)
    resp(s_second, "cat", "gato", "gato", True, recent, 2200)
    conn.commit()

    ids = {
        "arith": arith_id,
        "second": second_id,
        "now": now,
        "old": old,
    }
    yield m, conn, ids
    conn.close()


def test_all_rows_returned(seeded):
    m, conn, _ = seeded
    assert len(m.get_responses_for_stats(conn)) == 5


def test_rows_carry_elapsed_ms_and_category_name(seeded):
    m, conn, _ = seeded
    rows = m.get_responses_for_stats(conn)
    assert any(r["elapsed_ms"] == 1500 for r in rows)
    assert all("category_name" in r for r in rows)


def test_rows_ordered_newest_first(seeded):
    m, conn, ids = seeded
    rows = m.get_responses_for_stats(conn)
    assert rows[-1]["answered"] == _iso(ids["old"])


def test_category_filter(seeded):
    m, conn, ids = seeded
    assert len(m.get_responses_for_stats(conn, category_id=ids["arith"])) == 4


def test_since_filter_drops_old_row(seeded):
    m, conn, ids = seeded
    cutoff = _iso(ids["now"] - timedelta(days=7))
    assert len(m.get_responses_for_stats(conn, since=cutoff)) == 4


def test_category_and_since_combined(seeded):
    m, conn, ids = seeded
    cutoff = _iso(ids["now"] - timedelta(days=7))
    rows = m.get_responses_for_stats(conn, category_id=ids["arith"], since=cutoff)
    assert len(rows) == 3


def test_insert_response_elapsed_ms_round_trips_null_and_value(seeded):
    # A null elapsed_ms persists as None; a value persists exactly. This is
    # the timing-column reservation contract (C-018c) at the DB layer.
    m, conn, _ = seeded
    rows = m.get_responses_for_stats(conn)
    elapsed = sorted(r["elapsed_ms"] for r in rows if r["elapsed_ms"] is not None)
    assert elapsed == [900, 1500, 2200, 4000]
    assert any(r["elapsed_ms"] is None for r in rows)


def test_question_metadata_surfaces_through_readers(seeded):
    # v2/D1 read path: questions.metadata is surfaced (parsed to a dict) by the
    # canonical reader, so get_question and list_questions return it. A freshly
    # inserted question carries the '{}' default as {}; a row whose metadata was
    # written parses back to the stored object. current_db is migrated to
    # SCHEMA_VERSION, so the column exists here. This covers the reader only --
    # the client payload (build_question_payload) does not forward metadata (ADR-D1).
    m, conn, ids = seeded
    bank_id = m.insert_bank(
        conn,
        category_id=ids["arith"],
        name="meta bank",
        source="seed",
        created=_iso(ids["now"]),
        language=None,
    )
    m.insert_questions_bulk(
        conn,
        bank_id,
        [
            {"qtype": m.QTYPE_FREE_RESPONSE, "question": "default-meta", "answer": "a"},
            {"qtype": m.QTYPE_FREE_RESPONSE, "question": "set-meta", "answer": "b"},
        ],
        _iso(ids["now"]),
    )
    conn.commit()

    questions = {q["question"]: q for q in m.list_questions(conn, bank_id)}
    # Bulk insert uses the v1 column set, so both rows take the '{}' default,
    # which the reader parses to an empty dict.
    assert questions["default-meta"]["metadata"] == {}
    assert questions["set-meta"]["metadata"] == {}

    # A stored (non-default) metadata object round-trips through the reader as
    # the parsed dict -- the shape a future writer (e.g. SM2 state) would use.
    target_id = questions["set-meta"]["id"]
    conn.execute(
        "UPDATE questions SET metadata = ? WHERE id = ?",
        ('{"source_tag": "imported", "weight": 3}', target_id),
    )
    conn.commit()
    fetched = m.get_question(conn, target_id)
    assert fetched["metadata"] == {"source_tag": "imported", "weight": 3}
