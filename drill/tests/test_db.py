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
from _support import current_db, load_db  # noqa: E402


def _iso(dt):
    return dt.isoformat()


@pytest.fixture
def seeded(tmp_path):
    """A fresh module + temp DB seeded with a known response spread.

    Arithmetic: 3 recent (2 correct, 1 wrong) + 1 ten-day-old correct.
    Second category: 1 recent correct.
    Returns (module, conn, ids dict).
    """
    m = load_db()
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


def test_rows_surface_difficulty_and_leaf_count(seeded):
    # C-D2h: get_responses_for_stats SELECTs and surfaces the v3 columns so the
    # C-D2i breakdown can group on them. The seeded rows carry NULL (inserted
    # without these values); a row inserted WITH values surfaces them verbatim.
    m, conn, ids = seeded
    # Every seeded row exposes both keys, as NULL.
    rows = m.get_responses_for_stats(conn)
    assert all("difficulty" in r and "leaf_count" in r for r in rows)
    assert all(r["difficulty"] is None and r["leaf_count"] is None for r in rows)
    # A row recorded with a rung + leaf_count surfaces those values.
    s = m.start_session(conn, ids["arith"], _iso(ids["now"]))
    m.insert_response(
        conn,
        session_id=s,
        question_text="(2 + 3) * 4",
        answer_text="20",
        user_input="20",
        correct=True,
        answered=_iso(ids["now"]),
        difficulty=4,
        leaf_count=3,
    )
    conn.commit()
    rows = m.get_responses_for_stats(conn)
    surfaced = [r for r in rows if r["difficulty"] == 4]
    assert len(surfaced) == 1
    assert surfaced[0]["leaf_count"] == 3


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


def test_insert_response_difficulty_leaf_count_round_trip(seeded):
    # C-D2g: insert_response persists difficulty and leaf_count to the v3 columns
    # (C-D2f); both default to NULL when omitted. Read the responses table
    # directly here -- get_responses_for_stats does not surface these columns
    # until C-D2h, so testing through it would be premature.
    m, conn, ids = seeded
    s = m.start_session(conn, ids["arith"], _iso(ids["now"]))
    # explicit values
    with_vals = m.insert_response(
        conn,
        session_id=s,
        question_text="(2 + 3) * 4",
        answer_text="20",
        user_input="20",
        correct=True,
        answered=_iso(ids["now"]),
        difficulty=4,
        leaf_count=3,
    )
    # omitted -> NULL (the bank / no-rung default)
    without_vals = m.insert_response(
        conn,
        session_id=s,
        question_text="7",
        answer_text="7",
        user_input="7",
        correct=True,
        answered=_iso(ids["now"]),
    )
    conn.commit()
    row_with = conn.execute(
        "SELECT difficulty, leaf_count FROM responses WHERE id = ?", (with_vals,)
    ).fetchone()
    assert row_with["difficulty"] == 4
    assert row_with["leaf_count"] == 3
    row_without = conn.execute(
        "SELECT difficulty, leaf_count FROM responses WHERE id = ?", (without_vals,)
    ).fetchone()
    assert row_without["difficulty"] is None
    assert row_without["leaf_count"] is None

# --- B1: per-question response stats reader (adaptive selection feed) ---


@pytest.fixture
def bank_with_responses(tmp_path):
    """A fresh current-schema DB with one bank of three questions and a
    known response spread, plus a NULL-question_id arithmetic response.

    Question 1: 3 attempts, 2 correct. Question 2: 1 attempt, 0 correct.
    Question 3: never attempted. Arithmetic: 1 correct response with
    question_id NULL (must never appear in bank stats).
    Returns (module, conn, bank_id, question_ids, timestamps).
    """
    m = load_db()
    conn = current_db(m, tmp_path)

    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    second_name = next(n for n in cats if n != "arithmetic")
    second_id = cats[second_name]

    now = datetime.now(timezone.utc)
    earlier = now - timedelta(days=2)

    bank_id = m.insert_bank(conn, second_id, "b1-stats-bank", "test", _iso(now))
    m.insert_questions_bulk(
        conn,
        bank_id,
        [
            {"question": "q one", "answer": "a one"},
            {"question": "q two", "answer": "a two"},
            {"question": "q three", "answer": "a three"},
        ],
        _iso(now),
    )
    question_ids = [q["id"] for q in m.list_questions(conn, bank_id)]

    session_id = m.start_session(conn, second_id, _iso(now), bank_id=bank_id)
    m.insert_response(
        conn, session_id, "q one", "a one", "a one", True,
        _iso(earlier), question_id=question_ids[0],
    )
    m.insert_response(
        conn, session_id, "q one", "a one", "wrong", False,
        _iso(earlier), question_id=question_ids[0],
    )
    m.insert_response(
        conn, session_id, "q one", "a one", "a one", True,
        _iso(now), question_id=question_ids[0],
    )
    m.insert_response(
        conn, session_id, "q two", "a two", "wrong", False,
        _iso(now), question_id=question_ids[1],
    )
    # Generated arithmetic: question_id NULL, must be excluded by the join.
    m.insert_response(
        conn, session_id, "1+1", "2", "2", True,
        _iso(now), question_id=None,
    )
    conn.commit()

    yield m, conn, bank_id, question_ids, {"now": now, "earlier": earlier}
    conn.close()


def test_response_stats_empty_bank_returns_empty_dict(bank_with_responses):
    m, conn, bank_id, question_ids, times = bank_with_responses
    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    second_name = next(n for n in cats if n != "arithmetic")
    empty_bank_id = m.insert_bank(
        conn, cats[second_name], "b1-empty-bank", "test", _iso(times["now"])
    )
    assert m.get_response_stats_for_bank(conn, empty_bank_id) == {}


def test_response_stats_counts_exact(bank_with_responses):
    m, conn, bank_id, question_ids, times = bank_with_responses
    stats = m.get_response_stats_for_bank(conn, bank_id)
    assert stats[question_ids[0]]["attempt_count"] == 3
    assert stats[question_ids[0]]["correct_count"] == 2
    assert stats[question_ids[0]]["last_answered"] == _iso(times["now"])
    assert stats[question_ids[1]]["attempt_count"] == 1
    assert stats[question_ids[1]]["correct_count"] == 0
    assert stats[question_ids[1]]["last_answered"] == _iso(times["now"])


def test_response_stats_never_attempted_question_absent(bank_with_responses):
    m, conn, bank_id, question_ids, times = bank_with_responses
    stats = m.get_response_stats_for_bank(conn, bank_id)
    assert question_ids[2] not in stats
    assert set(stats.keys()) == {question_ids[0], question_ids[1]}


def test_response_stats_excludes_null_question_id_rows(bank_with_responses):
    m, conn, bank_id, question_ids, times = bank_with_responses
    # The fixture inserted one arithmetic response (question_id NULL). The
    # total attempts across the stats dict must equal only the 4 bank-question
    # responses; the NULL row joins nothing and can appear under no key.
    stats = m.get_response_stats_for_bank(conn, bank_id)
    assert None not in stats
    total_attempts = sum(entry["attempt_count"] for entry in stats.values())
    assert total_attempts == 4
