"""HTTP-tier tests -- the Bottle app driven through its WSGI callable over a
temp DB. No server, no socket (phase0.md Section B, Pattern 1).

Concern: the endpoint contracts and the 400 envelope. Harvested from the
WSGI half of test_c019a.py (GET /api/stats: all-time, filters, window echo,
the 400s) and extended to the other read endpoints (/api/categories) plus a
seam-level check on /api/question so the boundary payload shape is covered.

What is NOT tested here: Bottle's routing internals. We test our handlers and
the JSON contracts they emit.
"""
import json
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from _support import load_drill, temp_db, wsgi_get  # noqa: E402


def _iso(dt):
    return dt.isoformat()


@pytest.fixture
def app_with_data():
    """Module + temp DB seeded for stats endpoint tests. DATABASE_PATH is
    bound to the temp file so the handlers read it."""
    m = load_drill()
    conn = temp_db(m)

    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    arith_id = cats["arithmetic"]
    second_id = next(cid for n, cid in cats.items() if n != "arithmetic")

    now = datetime.now(timezone.utc)
    old = now - timedelta(days=10)
    recent = now - timedelta(days=1)
    s_arith = m.start_session(conn, arith_id, _iso(now))
    s_second = m.start_session(conn, second_id, _iso(now))
    conn.commit()

    def resp(sid, correct, when, ms):
        m.insert_response(
            conn, session_id=sid, question_text="q", answer_text="a",
            user_input="a" if correct else "x", correct=correct,
            answered=_iso(when), question_id=None, elapsed_ms=ms,
        )

    resp(s_arith, True, recent, 1500)
    resp(s_arith, True, recent, 900)
    resp(s_arith, False, recent, None)
    resp(s_arith, True, old, 4000)
    resp(s_second, True, recent, 2200)
    conn.commit()
    conn.close()

    return m, {"arith": arith_id, "second": second_id}


def _get_json(m, path, qs=""):
    status, body = wsgi_get(m, path, qs)
    return status, json.loads(body)


# ---- /api/categories ------------------------------------------------------
def test_categories_endpoint_lists_seeded(app_with_data):
    m, _ = app_with_data
    status, data = _get_json(m, "/api/categories")
    assert status.startswith("200")
    names = {c["name"] for c in data["categories"]}
    assert "arithmetic" in names


# ---- /api/stats: happy paths ---------------------------------------------
def test_stats_all_time(app_with_data):
    m, _ = app_with_data
    status, data = _get_json(m, "/api/stats")
    assert status.startswith("200")
    assert data["total"] == 5
    assert data["window"]["since"] is None
    assert data["window"]["days"] is None
    assert data["window"]["category_id"] is None


def test_stats_category_filter(app_with_data):
    m, ids = app_with_data
    status, data = _get_json(m, "/api/stats", "category_id=%d" % ids["arith"])
    assert data["total"] == 4
    assert data["window"]["category_id"] == ids["arith"]


def test_stats_day_window_excludes_old(app_with_data):
    m, _ = app_with_data
    status, data = _get_json(m, "/api/stats", "days=7")
    assert data["total"] == 4
    assert data["window"]["days"] == 7
    assert isinstance(data["window"]["since"], str)


def test_stats_category_and_days(app_with_data):
    m, ids = app_with_data
    _, data = _get_json(m, "/api/stats", "category_id=%d&days=7" % ids["arith"])
    assert data["total"] == 3


# ---- /api/stats: the 400 envelope ----------------------------------------
@pytest.mark.parametrize("qs", ["days=0", "days=-3", "days=abc", "category_id=notint"])
def test_stats_bad_params_are_400(app_with_data, qs):
    m, _ = app_with_data
    status, _ = wsgi_get(m, "/api/stats", qs)
    assert status.startswith("400")


def test_stats_empty_category_is_200_zeros(app_with_data):
    m, ids = app_with_data
    # Find a seeded category with no responses.
    status0, data0 = _get_json(m, "/api/categories")
    used = {ids["arith"], ids["second"]}
    empty = next((c["id"] for c in data0["categories"] if c["id"] not in used), None)
    if empty is None:
        pytest.skip("only two categories seeded; no empty category available")
    status, data = _get_json(m, "/api/stats", "category_id=%d" % empty)
    assert status.startswith("200")
    assert data["total"] == 0


# ---- /api/question: boundary payload shape -------------------------------
def test_question_payload_shape_for_arithmetic(app_with_data):
    m, _ = app_with_data
    status, data = _get_json(m, "/api/question", "category=arithmetic")
    assert status.startswith("200")
    # The frontend contract: a renderable prompt and an expected answer.
    assert "question_text" in data
    assert "expected" in data
    assert data["qtype"] == "arithmetic"
