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
from _support import (  # noqa: E402
    load_drill,
    temp_db,
    wsgi_get,
    wsgi_post_json,
    wsgi_post_multipart,
)


def _iso(dt):
    return dt.isoformat()


@pytest.fixture
def app_with_data(tmp_path):
    """Module + temp DB seeded for stats endpoint tests. DATABASE_PATH is
    bound to the temp file so the handlers read it."""
    m = load_drill()
    conn = temp_db(m, tmp_path)

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
            conn,
            session_id=sid,
            question_text="q",
            answer_text="a",
            user_input="a" if correct else "x",
            correct=correct,
            answered=_iso(when),
            question_id=None,
            elapsed_ms=ms,
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


# ==========================================================================
# C-020b: the remaining endpoints and their 400 surfaces.
#
# Built against the real handlers and verified path-by-path before being
# written down. One thing the probing corrected: GET /api/question with an
# EMPTY operators value (operators=) is a 200 -- the handler treats the empty
# string as falsy and falls back to all operators. The 400 fires only when
# the value is present-but-all-separators (operators=,,). The test below
# pins the path that actually 400s, not the one the docstring might suggest.
# ==========================================================================


def _post_json(m, path, payload):
    status, body = wsgi_post_json(m, path, payload)
    return status, json.loads(body)


# A fresh module + empty temp DB (no responses seeded). The category ids are
# returned for building valid/invalid foreign keys.
@pytest.fixture
def app_blank(tmp_path):
    m = load_drill()
    conn = temp_db(m, tmp_path)
    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    conn.close()
    return m, cats


# ---- /api/session/start ---------------------------------------------------
def test_session_start_returns_id(app_blank):
    m, cats = app_blank
    status, data = _post_json(
        m, "/api/session/start", {"category_id": cats["arithmetic"]}
    )
    assert status.startswith("200")
    assert isinstance(data["session_id"], int)


def test_session_start_missing_category_is_400(app_blank):
    m, _ = app_blank
    status, _ = wsgi_post_json(m, "/api/session/start", {})
    assert status.startswith("400")


def test_session_start_non_int_category_is_400(app_blank):
    m, _ = app_blank
    status, _ = wsgi_post_json(m, "/api/session/start", {"category_id": "xyz"})
    assert status.startswith("400")


def test_session_start_unknown_category_is_400_integrity(app_blank):
    # The IntegrityError -> 400 translation path (foreign key to a missing
    # category). This is the handler turning a DB exception into a clean 400
    # instead of a 500.
    m, _ = app_blank
    status, data = _post_json(m, "/api/session/start", {"category_id": 999999})
    assert status.startswith("400")
    assert "error" in data


# ---- /api/answer ----------------------------------------------------------
def test_answer_grades_correct_and_incorrect(app_blank):
    m, cats = app_blank
    _, start = _post_json(m, "/api/session/start", {"category_id": cats["arithmetic"]})
    sid = start["session_id"]

    _, right = _post_json(
        m,
        "/api/answer",
        {
            "session_id": sid,
            "qtype": "arithmetic",
            "question_text": "6 + 7",
            "expected": "13",
            "user_input": "13",
        },
    )
    assert right["correct"] is True
    assert right["session_stats"] == {
        "total": 1,
        "correct": 1,
        "accuracy": 1.0,
        "streak": 1,
    }

    _, wrong = _post_json(
        m,
        "/api/answer",
        {
            "session_id": sid,
            "qtype": "arithmetic",
            "question_text": "6 + 7",
            "expected": "13",
            "user_input": "12",
        },
    )
    assert wrong["correct"] is False
    # streak resets on the miss; accuracy is now 1/2.
    assert wrong["session_stats"]["streak"] == 0
    assert abs(wrong["session_stats"]["accuracy"] - 0.5) < 1e-9


@pytest.mark.parametrize(
    "missing",
    ["session_id", "qtype", "question_text", "expected", "user_input"],
)
def test_answer_missing_required_field_is_400(app_blank, missing):
    m, cats = app_blank
    _, start = _post_json(m, "/api/session/start", {"category_id": cats["arithmetic"]})
    payload = {
        "session_id": start["session_id"],
        "qtype": "arithmetic",
        "question_text": "x",
        "expected": "1",
        "user_input": "1",
    }
    del payload[missing]
    status, _ = wsgi_post_json(m, "/api/answer", payload)
    assert status.startswith("400")


def test_answer_unknown_session_is_400_integrity(app_blank):
    m, _ = app_blank
    status, data = _post_json(
        m,
        "/api/answer",
        {
            "session_id": 999999,
            "qtype": "arithmetic",
            "question_text": "x",
            "expected": "1",
            "user_input": "1",
        },
    )
    assert status.startswith("400")
    assert "error" in data


# ---- /api/session/end -----------------------------------------------------
def test_session_end_real_session_returns_true(app_blank):
    m, cats = app_blank
    _, start = _post_json(m, "/api/session/start", {"category_id": cats["arithmetic"]})
    status, data = _post_json(
        m, "/api/session/end", {"session_id": start["session_id"]}
    )
    assert status.startswith("200")
    assert data["ended"] is True


def test_session_end_unknown_session_is_harmless_noop(app_blank):
    # DELIBERATE contract: ending an unknown/already-cleaned session is a
    # no-op returning ended=false, NOT a 404. Pins it against a future
    # "fix" that turns it into an error.
    m, _ = app_blank
    status, data = _post_json(m, "/api/session/end", {"session_id": 888888})
    assert status.startswith("200")
    assert data["ended"] is False


def test_session_end_missing_id_is_400(app_blank):
    m, _ = app_blank
    status, _ = wsgi_post_json(m, "/api/session/end", {"session_id": None})
    assert status.startswith("400")


# ---- /api/question: bank branch ------------------------------------------
@pytest.fixture
def app_with_bank(tmp_path):
    """A module + temp DB carrying one populated bank and one empty bank in a
    non-arithmetic category. Returns (m, category_id, full_bank_id,
    empty_bank_id)."""
    m = load_drill()
    conn = temp_db(m, tmp_path)
    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    cat_id = next(cid for n, cid in cats.items() if n != "arithmetic")
    cat_name = next(n for n in cats if n != "arithmetic")
    now = m.utc_now_iso()
    full = m.insert_bank(
        conn, category_id=cat_id, name="b", source="manual", created=now
    )
    m.insert_questions_bulk(
        conn,
        full,
        [
            {"question": "hola", "answer": "hello", "qtype": "translate"},
            {"question": "adios", "answer": "goodbye", "qtype": "translate"},
        ],
        now,
    )
    empty = m.insert_bank(
        conn, category_id=cat_id, name="empty", source="manual", created=now
    )
    conn.commit()
    conn.close()
    return m, cat_name, full, empty


def test_question_bank_branch_returns_payload(app_with_bank):
    m, cat_name, full, _ = app_with_bank
    status, data = _get_json(
        m, "/api/question", "category=%s&bank_id=%d" % (cat_name, full)
    )
    assert status.startswith("200")
    assert data["question_text"] in ("hola", "adios")
    assert data["qtype"] == "translate"
    assert isinstance(data["question_id"], int)


def test_question_bank_missing_bank_id_is_400(app_with_bank):
    m, cat_name, _, _ = app_with_bank
    status, _ = wsgi_get(m, "/api/question", "category=%s" % cat_name)
    assert status.startswith("400")


def test_question_bank_non_int_bank_id_is_400(app_with_bank):
    m, cat_name, _, _ = app_with_bank
    status, _ = wsgi_get(m, "/api/question", "category=%s&bank_id=abc" % cat_name)
    assert status.startswith("400")


def test_question_bank_bad_recent_is_400(app_with_bank):
    m, cat_name, full, _ = app_with_bank
    status, _ = wsgi_get(
        m, "/api/question", "category=%s&bank_id=%d&recent=1,x" % (cat_name, full)
    )
    assert status.startswith("400")


def test_question_empty_bank_is_404(app_with_bank):
    m, cat_name, _, empty = app_with_bank
    status, data = _get_json(
        m, "/api/question", "category=%s&bank_id=%d" % (cat_name, empty)
    )
    assert status.startswith("404")
    assert "error" in data


def test_question_missing_category_is_400(app_with_bank):
    m, _, _, _ = app_with_bank
    status, _ = wsgi_get(m, "/api/question", "")
    assert status.startswith("400")


# ---- /api/question: arithmetic operator validation -----------------------
def test_question_arithmetic_unknown_operator_is_400(app_blank):
    m, _ = app_blank
    status, _ = wsgi_get(m, "/api/question", "category=arithmetic&operators=^")
    assert status.startswith("400")


def test_question_arithmetic_separators_only_operators_is_400(app_blank):
    # operators=,, is present-but-empty-after-parsing -> 400 (a malformed
    # restriction, not "use all"). Note operators= (truly empty) is a 200;
    # the handler treats the empty string as "omitted".
    m, _ = app_blank
    status, _ = wsgi_get(m, "/api/question", "category=arithmetic&operators=,,")
    assert status.startswith("400")


# ---- /api/banks -----------------------------------------------------------
def test_banks_list_includes_seeded_bank(app_with_bank):
    m, _, full, _ = app_with_bank
    status, data = _get_json(m, "/api/banks")
    assert status.startswith("200")
    assert any(b["id"] == full for b in data["banks"])


def test_banks_non_int_category_is_400(app_with_bank):
    m, _, _, _ = app_with_bank
    status, _ = wsgi_get(m, "/api/banks", "category_id=notint")
    assert status.startswith("400")


# ---- /api/banks/import ----------------------------------------------------
def test_import_jsonl_round_trips(app_blank):
    m, cats = app_blank
    cat_id = next(cid for n, cid in cats.items() if n != "arithmetic")
    jsonl = (
        '{"question": "capital of France", "answer": "Paris"}\n'
        '{"question": "capital of Spain", "answer": "Madrid"}\n'
    )
    status, body = wsgi_post_multipart(
        m,
        "/api/banks/import",
        {"category_id": cat_id, "name": "geo", "format": "jsonl"},
        "file",
        "geo.jsonl",
        jsonl.encode("utf-8"),
    )
    data = json.loads(body)
    assert status.startswith("200")
    assert data["imported"] == 2
    assert isinstance(data["bank_id"], int)


def test_import_missing_file_part_is_400(app_blank):
    m, cats = app_blank
    cat_id = cats["arithmetic"]
    status, _ = wsgi_post_multipart(
        m,
        "/api/banks/import",
        {"category_id": cat_id},
        "notfile",
        "x.jsonl",
        b"",
    )
    assert status.startswith("400")


def test_import_missing_category_is_400(app_blank):
    m, _ = app_blank
    status, _ = wsgi_post_multipart(
        m,
        "/api/banks/import",
        {"format": "jsonl"},
        "file",
        "x.jsonl",
        b'{"question":"q","answer":"a"}\n',
    )
    assert status.startswith("400")


def test_import_non_utf8_is_400(app_blank):
    m, cats = app_blank
    cat_id = next(cid for n, cid in cats.items() if n != "arithmetic")
    status, _ = wsgi_post_multipart(
        m,
        "/api/banks/import",
        {"category_id": cat_id, "format": "jsonl"},
        "file",
        "bad.jsonl",
        b"\xff\xfe\x00bad",
    )
    assert status.startswith("400")


def test_import_malformed_jsonl_is_400(app_blank):
    m, cats = app_blank
    cat_id = next(cid for n, cid in cats.items() if n != "arithmetic")
    status, data = wsgi_post_multipart(
        m,
        "/api/banks/import",
        {"category_id": cat_id, "format": "jsonl"},
        "file",
        "m.jsonl",
        b"{not valid json}\n",
    )
    assert status.startswith("400")
    assert "error" in json.loads(data)
