"""HTTP-tier tests -- the Bottle app driven through its WSGI callable over a
temp DB. No server, no socket (phase0.md Section B, Pattern 1).

Concern: the endpoint contracts and the 400 envelope. Harvested from the
WSGI half of test_c019a.py (GET /api/stats: all-time, filters, window echo,
the 400s) and extended to the other read endpoints (/api/categories) plus a
seam-level check on /api/question so the boundary payload shape is covered.

What is NOT tested here: Bottle's routing internals. We test our handlers and
the JSON contracts they emit.
"""

import io
import json
import re
import os
import sys
from datetime import datetime, timedelta, timezone

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from _support import (  # noqa: E402
    current_db,
    load_http,
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
    m = load_http()
    conn = current_db(m, tmp_path)

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
    # C-D2i-2: the payload carries a difficulty_breakdown list. The seeded rows
    # have NULL leaf_count, so it is empty here -- but the key is always present.
    assert data["difficulty_breakdown"] == []


def test_stats_difficulty_breakdown_surfaces_leaf_count(app_with_data):
    # C-D2i-2 end to end: arithmetic responses carrying a leaf_count appear in
    # the per-difficulty breakdown, grouped by leaf_count. Record a few via the
    # answer endpoint (the real capture path, C-D2g) so this exercises the full
    # echo -> capture -> surface -> summarize chain.
    m, ids = app_with_data
    _, start = _post_json(m, "/api/session/start", {"category_id": ids["arith"]})
    sid = start["session_id"]
    for leaf, ui in ((2, "2"), (2, "9"), (3, "20")):  # 2-leaf: 1 right 1 wrong
        _post_json(
            m,
            "/api/answer",
            {
                "session_id": sid,
                "qtype": "arithmetic",
                "question_text": "q",
                "expected": "2" if leaf == 2 else "20",
                "user_input": ui,
                "difficulty": 4,
                "leaf_count": leaf,
            },
        )
    _, data = _get_json(m, "/api/stats")
    by_key = {e["key"]: e for e in data["difficulty_breakdown"]}
    assert by_key[2]["total"] == 2 and by_key[2]["correct"] == 1
    assert by_key[3]["total"] == 1 and by_key[3]["correct"] == 1
    assert by_key[2]["label"] == "2 leaves"


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


# ---- /api/difficulty-rungs: the rung list read endpoint (C-2U-a) ----------
def test_difficulty_rungs_endpoint_lists_config(app_with_data):
    m, _ = app_with_data
    status, data = _get_json(m, "/api/difficulty-rungs")
    assert status.startswith("200")
    rungs = data["rungs"]
    # One entry per configured rung, in the same ascending order, each
    # carrying the structural facts the client composes its label from.
    assert [r["rung"] for r in rungs] == [c["rung"] for c in m.DIFFICULTY_RUNGS]
    for got, conf in zip(rungs, m.DIFFICULTY_RUNGS):
        assert got["operator_depth"] == conf["operator_depth"]
        assert got["recurse_probability"] == conf["recurse_probability"]
        assert got["max_result_value"] == conf["max_result_value"]
        # Pure read: no operator_ranges leak, no label invented server-side.
        assert set(got.keys()) == {
            "rung",
            "operator_depth",
            "recurse_probability",
            "max_result_value",
        }


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
    m = load_http()
    conn = current_db(m, tmp_path)
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


# ---- /api/answer: difficulty + leaf_count capture (C-D2g) ----------------
# post_answer reads the difficulty + leaf_count the client echoes from the
# served question payload (C-D2c) and records them on the v3 responses columns
# (C-D2f). Malformed values are a 400 (the _optional_int contract); omitted
# values store NULL. We read the row back through a fresh connection on the same
# DATABASE_PATH the app used.


def _last_response_row(m):
    conn = m.connect(m.DATABASE_PATH)
    try:
        return conn.execute(
            "SELECT difficulty, leaf_count FROM responses ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()


def test_answer_captures_difficulty_and_leaf_count(app_blank):
    m, cats = app_blank
    _, start = _post_json(m, "/api/session/start", {"category_id": cats["arithmetic"]})
    status, _ = _post_json(
        m,
        "/api/answer",
        {
            "session_id": start["session_id"],
            "qtype": "arithmetic",
            "question_text": "(2 + 3) * 4",
            "expected": "20",
            "user_input": "20",
            "difficulty": 4,
            "leaf_count": 3,
        },
    )
    assert status.startswith("200")
    row = _last_response_row(m)
    assert row["difficulty"] == 4
    assert row["leaf_count"] == 3


def test_answer_omitted_difficulty_stores_null(app_blank):
    # No difficulty/leaf_count echoed (e.g. a bank answer, or the no-rung path
    # where the client omits them) -> NULL columns, not a default or an error.
    m, cats = app_blank
    _, start = _post_json(m, "/api/session/start", {"category_id": cats["arithmetic"]})
    status, _ = _post_json(
        m,
        "/api/answer",
        {
            "session_id": start["session_id"],
            "qtype": "arithmetic",
            "question_text": "6 + 7",
            "expected": "13",
            "user_input": "13",
        },
    )
    assert status.startswith("200")
    row = _last_response_row(m)
    assert row["difficulty"] is None
    assert row["leaf_count"] is None


def test_answer_non_int_difficulty_is_400(app_blank):
    m, cats = app_blank
    _, start = _post_json(m, "/api/session/start", {"category_id": cats["arithmetic"]})
    status, _ = wsgi_post_json(
        m,
        "/api/answer",
        {
            "session_id": start["session_id"],
            "qtype": "arithmetic",
            "question_text": "6 + 7",
            "expected": "13",
            "user_input": "13",
            "difficulty": "hard",
        },
    )
    assert status.startswith("400")


def test_answer_non_int_leaf_count_is_400(app_blank):
    m, cats = app_blank
    _, start = _post_json(m, "/api/session/start", {"category_id": cats["arithmetic"]})
    status, _ = wsgi_post_json(
        m,
        "/api/answer",
        {
            "session_id": start["session_id"],
            "qtype": "arithmetic",
            "question_text": "6 + 7",
            "expected": "13",
            "user_input": "13",
            "leaf_count": "two",
        },
    )
    assert status.startswith("400")


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
    m = load_http()
    conn = current_db(m, tmp_path)
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


# ---- /api/question: selection strategy dispatch (B3) ----------------------
# The strategy parameter is optional; absent or "random" is the existing
# pick_next_question path (covered by the bank-branch tests above, unchanged).
# "weighted" assembles context at the HTTP edge (stats reader + random sample)
# and dispatches to select_weighted_by_miss_rate. Unknown values get the
# standard error envelope.
def test_question_strategy_random_explicit_returns_payload(app_with_bank):
    m, cat_name, full, _ = app_with_bank
    status, data = _get_json(
        m,
        "/api/question",
        "category=%s&bank_id=%d&strategy=random" % (cat_name, full),
    )
    assert status.startswith("200")
    assert data["question_text"] in ("hola", "adios")


def test_question_strategy_weighted_returns_candidate(app_with_bank):
    m, cat_name, full, _ = app_with_bank
    status, data = _get_json(
        m,
        "/api/question",
        "category=%s&bank_id=%d&strategy=weighted" % (cat_name, full),
    )
    assert status.startswith("200")
    assert data["question_text"] in ("hola", "adios")
    assert data["qtype"] == "translate"
    assert isinstance(data["question_id"], int)


def test_question_strategy_weighted_respects_recent_window(app_with_bank):
    # With one of the two questions marked recent, the weighted path must
    # serve the other one, exactly like the random path's soft window.
    m, cat_name, full, _ = app_with_bank
    status, first = _get_json(
        m, "/api/question", "category=%s&bank_id=%d" % (cat_name, full)
    )
    assert status.startswith("200")
    recent_id = first["question_id"]
    for _ in range(10):
        status, data = _get_json(
            m,
            "/api/question",
            "category=%s&bank_id=%d&strategy=weighted&recent=%d"
            % (cat_name, full, recent_id),
        )
        assert status.startswith("200")
        assert data["question_id"] != recent_id


def test_question_strategy_weighted_empty_bank_is_404(app_with_bank):
    m, cat_name, _, empty = app_with_bank
    status, data = _get_json(
        m,
        "/api/question",
        "category=%s&bank_id=%d&strategy=weighted" % (cat_name, empty),
    )
    assert status.startswith("404")
    assert "error" in data


def test_question_unknown_strategy_is_400_with_error_envelope(app_with_bank):
    m, cat_name, full, _ = app_with_bank
    status, data = _get_json(
        m,
        "/api/question",
        "category=%s&bank_id=%d&strategy=galaxy_brain" % (cat_name, full),
    )
    assert status.startswith("400")
    assert "error" in data
    assert "strategy" in data["error"]


# ---- /api/question: arithmetic operator validation -----------------------
def test_question_arithmetic_unknown_operator_is_400(app_blank):
    m, _ = app_blank
    # "$" has no operator record, so restricting to it is a 400. (Was "^"
    # before #4 enabled exponent; "^" is a valid operator now, so the unknown
    # sentinel must be a symbol that genuinely has no record.)
    status, _ = wsgi_get(m, "/api/question", "category=arithmetic&operators=$")
    assert status.startswith("400")


def test_question_arithmetic_separators_only_operators_is_400(app_blank):
    # operators=,, is present-but-empty-after-parsing -> 400 (a malformed
    # restriction, not "use all"). Note operators= (truly empty) is a 200;
    # the handler treats the empty string as "omitted".
    m, _ = app_blank
    status, _ = wsgi_get(m, "/api/question", "category=arithmetic&operators=,,")
    assert status.startswith("400")


# ---- /api/question: difficulty rung (C-D2c) ------------------------------
# The HTTP layer parses ?difficulty=, validates it against the known rung
# labels, threads it to generate_expression, and echoes the served rung plus
# the expression's leaf_count in the payload so the client can round-trip them
# to /api/answer. Capture into responses is C-D2g (gated on the v3 migration);
# here we test only the parse + echo + 400 surface.


def test_question_arithmetic_no_difficulty_echoes_null(app_blank):
    # The default (no-rung) path: difficulty is omitted -> payload difficulty is
    # null, and leaf_count is still present (a fact about the served tree).
    m, _ = app_blank
    status, data = _get_json(m, "/api/question", "category=arithmetic")
    assert status.startswith("200")
    assert data["difficulty"] is None
    assert "leaf_count" in data and isinstance(data["leaf_count"], int)
    assert data["leaf_count"] >= 2


def test_question_arithmetic_valid_difficulty_is_echoed(app_blank):
    # A known rung is accepted and echoed back verbatim. Rung 1 is flat, so its
    # leaf_count is exactly 2.
    m, _ = app_blank
    status, data = _get_json(m, "/api/question", "category=arithmetic&difficulty=1")
    assert status.startswith("200")
    assert data["difficulty"] == 1
    assert data["leaf_count"] == 2


def test_question_arithmetic_top_rung_is_accepted(app_blank):
    # The highest declared rung is valid (guards an off-by-one in the known-rung
    # membership check). leaf_count is present and at least the flat minimum.
    m, _ = app_blank
    top = m.DIFFICULTY_RUNGS[-1]["rung"]
    status, data = _get_json(
        m, "/api/question", "category=arithmetic&difficulty=%d" % top
    )
    assert status.startswith("200")
    assert data["difficulty"] == top
    assert data["leaf_count"] >= 2


def test_question_arithmetic_unknown_difficulty_is_400(app_blank):
    # A syntactically-valid int that is not a known rung label -> 400 (mirrors
    # the unknown-operator 400). generate_expression's ValueError guard never
    # fires for user input because HTTP rejects it first.
    m, _ = app_blank
    status, _ = wsgi_get(m, "/api/question", "category=arithmetic&difficulty=999")
    assert status.startswith("400")


def test_question_arithmetic_non_int_difficulty_is_400(app_blank):
    # A non-integer difficulty -> 400 (not a 500).
    m, _ = app_blank
    status, _ = wsgi_get(m, "/api/question", "category=arithmetic&difficulty=hard")
    assert status.startswith("400")


def test_question_arithmetic_empty_difficulty_is_default(app_blank):
    # difficulty= (present but empty) is treated as omitted -> default path,
    # difficulty null (mirrors the operators= empty-is-omitted rule).
    m, _ = app_blank
    status, data = _get_json(m, "/api/question", "category=arithmetic&difficulty=")
    assert status.startswith("200")
    assert data["difficulty"] is None


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


# ---- Frontend ES module serving (C-MOD-E10 cutover) -----------------------
# After the E10 cutover index.html is a single <script type="module"
# src="boot.js">; the browser then fetches each module over HTTP. These tests
# guard the route that serves them -- the gap that made the page render but sit
# inert (boot.js 404 -> no modules load -> nothing wired) when it was missing.

_FRONTEND_MODULE_FILES = [
    "state.js", "el.js", "api.js", "timing.js", "stage.js",
    "speech.js", "stats.js", "session.js", "drill.js", "boot.js",
]


def _wsgi_get_with_headers(m, path):
    """GET path, returning (status, headers_dict, body_bytes). Local to these
    tests because the shared wsgi_get helper does not surface headers, and the
    Content-Type is the whole point here (browsers reject type=module scripts
    served with a non-JavaScript MIME)."""
    captured = {}
    environ = {
        "REQUEST_METHOD": "GET",
        "PATH_INFO": path,
        "QUERY_STRING": "",
        "SERVER_NAME": "test",
        "SERVER_PORT": "80",
        "wsgi.input": io.BytesIO(),
        "wsgi.errors": sys.stderr,
        "wsgi.url_scheme": "http",
    }

    def start_response(status, headers, exc_info=None):
        captured["status"] = status
        captured["headers"] = {k.lower(): v for k, v in headers}

    body = b"".join(m.app(environ, start_response))
    return captured["status"], captured.get("headers", {}), body


@pytest.mark.parametrize("filename", _FRONTEND_MODULE_FILES)
def test_frontend_module_is_served_as_javascript(app_blank, filename):
    m, _ = app_blank
    status, headers, body = _wsgi_get_with_headers(m, "/" + filename)
    assert status.startswith("200"), (filename, status)
    # A JavaScript MIME so the browser evaluates it as an ES module.
    assert "javascript" in headers.get("content-type", ""), (filename, headers.get("content-type"))
    assert len(body) > 0


def test_boot_module_body_is_the_real_module(app_blank):
    m, _ = app_blank
    _, _, body = _wsgi_get_with_headers(m, "/boot.js")
    text = body.decode("utf-8")
    # It is the actual entry module: imports siblings and defines boot().
    assert 'from "./state.js"' in text
    assert "function boot" in text


def test_every_import_specifier_resolves_to_a_served_module(app_blank):
    """The whole graph must be fetchable: every `./x.js` any module imports must
    itself be a served module (else the browser 404s mid-graph and nothing runs
    -- a subtler version of the original bug)."""
    m, _ = app_blank
    served = set(_FRONTEND_MODULE_FILES)
    specifiers = set()
    for filename in _FRONTEND_MODULE_FILES:
        _, _, body = _wsgi_get_with_headers(m, "/" + filename)
        for match in re.findall(r'from "\./([A-Za-z0-9_-]+\.js)"', body.decode("utf-8")):
            specifiers.add(match)
    missing = specifiers - served
    assert not missing, "imported but not served: " + ", ".join(sorted(missing))


@pytest.mark.parametrize("path", [
    "/config.js",      # a real sibling .py exists as config.py -- must NOT leak as .js
    "/logic.js",
    "/nonexistent.js",
    "/drill.py",       # never serve source
])
def test_non_module_paths_are_404(app_blank, path):
    m, _ = app_blank
    status, _, _ = _wsgi_get_with_headers(m, path)
    assert status.startswith("404"), (path, status)


# ---- C4: review mode -- scheduled strategy + schedule write path ----------
# The day boundary in these tests is the REAL local today (the handler stamps
# date.today().toordinal() once per request); tests that need a controlled
# clock (the multi-week invariant) inject ordinals by replicating the
# handler's exact function sequence instead of going through WSGI.
from datetime import date as _date  # noqa: E402


@pytest.fixture
def review_app(tmp_path):
    """A module + temp DB with one bank of three questions, a session, and
    nothing scheduled yet. Returns (m, cat_name, bank_id, question_ids,
    session_id, conn). The connection stays open for direct inspection."""
    m = load_http()
    conn = current_db(m, tmp_path)
    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    cat_id = next(cid for n, cid in cats.items() if n != "arithmetic")
    cat_name = next(n for n in cats if n != "arithmetic")
    now = m.utc_now_iso()
    bank_id = m.insert_bank(
        conn, category_id=cat_id, name="review-bank", source="manual", created=now
    )
    m.insert_questions_bulk(
        conn,
        bank_id,
        [
            {"question": "uno", "answer": "one", "qtype": "translate"},
            {"question": "dos", "answer": "two", "qtype": "translate"},
            {"question": "tres", "answer": "three", "qtype": "translate"},
        ],
        now,
    )
    question_ids = [q["id"] for q in m.list_questions(conn, bank_id)]
    session_id = m.start_session(conn, cat_id, now, bank_id=bank_id)
    conn.commit()
    yield m, cat_name, bank_id, question_ids, session_id, conn
    conn.close()


def _answer_payload(session_id, question_id, correct, mode=None):
    payload = {
        "session_id": session_id,
        "qtype": "translate",
        "question_text": "uno",
        "expected": "one",
        "user_input": "one" if correct else "wrong",
        "question_id": question_id,
        "elapsed_ms": 1200,
    }
    if mode is not None:
        payload["mode"] = mode
    return payload


def test_scheduled_strategy_serves_new_question_on_fresh_bank(review_app):
    m, cat_name, bank_id, question_ids, session_id, conn = review_app
    status, data = _get_json(
        m,
        "/api/question",
        "category=%s&bank_id=%d&strategy=scheduled" % (cat_name, bank_id),
    )
    assert status.startswith("200")
    # Nothing scheduled -> everything is new; admitted new is served in id
    # order, so the first question arrives first.
    assert data["question_id"] == question_ids[0]


def test_scheduled_strategy_serves_due_before_new(review_app):
    m, cat_name, bank_id, question_ids, session_id, conn = review_app
    today = _date.today().toordinal()
    # Seed one OVERDUE schedule row directly: question 3 due yesterday,
    # last reviewed before today so the once-per-day rule cannot block it.
    m.upsert_schedule_row(
        conn,
        {
            "question_id": question_ids[2],
            "easiness_factor": 2.5,
            "interval_days": 6.0,
            "repetition_count": 2,
            "due_date": today - 1,
            "last_review": today - 7,
            "lapse_count": 0,
        },
    )
    status, data = _get_json(
        m,
        "/api/question",
        "category=%s&bank_id=%d&strategy=scheduled" % (cat_name, bank_id),
    )
    assert status.startswith("200")
    assert data["question_id"] == question_ids[2]


def test_review_answer_creates_schedule_row(review_app):
    m, cat_name, bank_id, question_ids, session_id, conn = review_app
    today = _date.today().toordinal()
    status, data = wsgi_post_json(
        m,
        "/api/answer",
        _answer_payload(session_id, question_ids[0], True, mode="review"),
    )
    assert status.startswith("200")
    stored = m.get_schedule_for_question(conn, question_ids[0])
    assert stored is not None
    assert stored["repetition_count"] == 1
    assert stored["lapse_count"] == 0
    assert stored["interval_days"] == 1.0  # first pass; <= 2d so fuzz exempt
    assert stored["last_review"] == today
    assert stored["due_date"] == today + 1


def test_practice_answer_never_touches_schedule(review_app):
    m, cat_name, bank_id, question_ids, session_id, conn = review_app
    # Explicit practice AND the default (mode absent) both leave no row.
    status, _ = wsgi_post_json(
        m,
        "/api/answer",
        _answer_payload(session_id, question_ids[0], True, mode="practice"),
    )
    assert status.startswith("200")
    status, _ = wsgi_post_json(
        m,
        "/api/answer",
        _answer_payload(session_id, question_ids[1], True),
    )
    assert status.startswith("200")
    assert m.get_schedule_for_question(conn, question_ids[0]) is None
    assert m.get_schedule_for_question(conn, question_ids[1]) is None


def test_review_answer_same_day_repeat_logs_but_never_reschedules(review_app):
    # THE same-day-repeat case: the second response IS logged (the log is
    # complete) but the schedule is unchanged on every field.
    m, cat_name, bank_id, question_ids, session_id, conn = review_app
    status, _ = wsgi_post_json(
        m,
        "/api/answer",
        _answer_payload(session_id, question_ids[0], True, mode="review"),
    )
    assert status.startswith("200")
    schedule_after_first = m.get_schedule_for_question(conn, question_ids[0])

    # Same day, second graded attempt -- and a FAIL, which would reset the
    # interval and bump lapse_count if it were allowed to schedule.
    status, _ = wsgi_post_json(
        m,
        "/api/answer",
        _answer_payload(session_id, question_ids[0], False, mode="review"),
    )
    assert status.startswith("200")
    schedule_after_second = m.get_schedule_for_question(conn, question_ids[0])
    assert schedule_after_second == schedule_after_first

    response_count = conn.execute(
        "SELECT COUNT(*) FROM responses WHERE question_id = ?",
        (question_ids[0],),
    ).fetchone()[0]
    assert response_count == 2


def test_review_answer_arithmetic_question_id_null_never_schedules(review_app):
    m, cat_name, bank_id, question_ids, session_id, conn = review_app
    payload = _answer_payload(session_id, None, True, mode="review")
    payload["qtype"] = "arithmetic"
    payload["question_text"] = "1 + 1"
    payload["expected"] = "2"
    payload["user_input"] = "2"
    status, _ = wsgi_post_json(m, "/api/answer", payload)
    assert status.startswith("200")
    count = conn.execute("SELECT COUNT(*) FROM question_schedule").fetchone()[0]
    assert count == 0


def test_answer_unknown_mode_is_400(review_app):
    m, cat_name, bank_id, question_ids, session_id, conn = review_app
    status, data = wsgi_post_json(
        m,
        "/api/answer",
        _answer_payload(session_id, question_ids[0], True, mode="cramming"),
    )
    assert status.startswith("400")
    assert "mode" in json.loads(data)["error"]


def test_scheduled_strategy_nothing_due_and_budget_spent_is_404(review_app):
    m, cat_name, bank_id, question_ids, session_id, conn = review_app
    today = _date.today().toordinal()
    # Everything scheduled for the FUTURE (nothing due, nothing new) and the
    # daily new budget fully spent by rows introduced today in this bank.
    for question_id in question_ids:
        m.upsert_schedule_row(
            conn,
            {
                "question_id": question_id,
                "easiness_factor": 2.5,
                "interval_days": 6.0,
                "repetition_count": 1,
                "due_date": today + 5,
                "last_review": today,
                "lapse_count": 0,
            },
        )
    status, data = _get_json(
        m,
        "/api/question",
        "category=%s&bank_id=%d&strategy=scheduled" % (cat_name, bank_id),
    )
    assert status.startswith("404")
    assert "error" in data


def test_new_introduced_today_aggregate_counts_first_reviews_only(review_app):
    m, cat_name, bank_id, question_ids, session_id, conn = review_app
    today = _date.today().toordinal()
    # question 1: introduced today (rep 1, lapse 0, last_review today).
    m.upsert_schedule_row(
        conn,
        {
            "question_id": question_ids[0],
            "easiness_factor": 2.6,
            "interval_days": 1.0,
            "repetition_count": 1,
            "due_date": today + 1,
            "last_review": today,
            "lapse_count": 0,
        },
    )
    # question 2: reviewed today but NOT new (rep 2).
    m.upsert_schedule_row(
        conn,
        {
            "question_id": question_ids[1],
            "easiness_factor": 2.7,
            "interval_days": 6.0,
            "repetition_count": 2,
            "due_date": today + 6,
            "last_review": today,
            "lapse_count": 0,
        },
    )
    # question 3: first review happened yesterday.
    m.upsert_schedule_row(
        conn,
        {
            "question_id": question_ids[2],
            "easiness_factor": 2.6,
            "interval_days": 1.0,
            "repetition_count": 1,
            "due_date": today,
            "last_review": today - 1,
            "lapse_count": 0,
        },
    )
    introduced = m.get_new_introduced_today_by_bank(conn, today)
    assert introduced == {bank_id: 1}


# ---- C4: THE INVARIANT TEST -- rebuild == stored over a simulated history --
# Port of the spike test_migration_and_simulation.py as a proper suite test.
# A multi-week (90-day) review history is driven through the HTTP-EQUIVALENT
# flow: each simulated request replicates the scheduled-strategy handler's
# exact function sequence (fetch via the real db readers, partition ->
# throttle -> weighted-due-then-admitted-new, insert_response, then the gated
# advance/fuzz/upsert write path) with the today ordinal injected instead of
# read from the clock -- the one substitution WSGI cannot provide. Deliberate
# same-day repeats are injected along the way. The invariant: folding the
# responses log through rebuild_schedule_from_response_log reproduces the
# stored question_schedule on every field to 1e-9. This is what makes
# "state is a cache of the log" a tested property, not a slogan.
def test_rebuild_from_response_log_equals_stored_schedule_over_90_days(tmp_path):
    import random as random_module

    from _support import load_logic

    m = load_http()
    logic_module = load_logic()
    conn = current_db(m, tmp_path)

    cats = {c["name"]: c["id"] for c in m.list_categories(conn)}
    cat_id = next(cid for n, cid in cats.items() if n != "arithmetic")
    now = m.utc_now_iso()
    bank_alpha = m.insert_bank(
        conn, category_id=cat_id, name="sim-alpha", source="manual", created=now
    )
    bank_beta = m.insert_bank(
        conn, category_id=cat_id, name="sim-beta", source="manual", created=now
    )
    m.insert_questions_bulk(
        conn,
        bank_alpha,
        [
            {"question": "alpha question %d" % index, "answer": "answer %d" % index}
            for index in range(12)
        ],
        now,
    )
    m.insert_questions_bulk(
        conn,
        bank_beta,
        [
            {"question": "beta question %d" % index, "answer": "answer %d" % index}
            for index in range(4)
        ],
        now,
    )
    session_id = m.start_session(conn, cat_id, now, bank_id=bank_alpha)
    conn.commit()

    start_ordinal = datetime(2026, 7, 3).date().toordinal()
    review_outcome_pattern = [True, True, False, True, True, True, False, True]
    pattern_index = 0
    seeded_random = random_module.Random(20260706)

    for day_offset in range(90):
        today = start_ordinal + day_offset
        answered_text = (
            datetime.fromordinal(today).date().isoformat() + "T09:00:00"
        )
        first_reviewed_today = None
        for bank_id in (bank_alpha, bank_beta):
            # One simulated GET+POST cycle per iteration, exactly the
            # handler's sequence, until this bank has nothing to serve.
            while True:
                candidates = m.list_questions(conn, bank_id)
                response_stats = m.get_response_stats_for_bank(conn, bank_id)
                schedule_by_question_id = m.get_schedule_for_bank(conn, bank_id)
                new_introduced_today = m.get_new_introduced_today_by_bank(
                    conn, today
                )
                due, new, not_due = m.partition_candidates_by_schedule(
                    candidates, schedule_by_question_id, today
                )
                due_capped = due[:100]  # REVIEWS_PER_SESSION_MAXIMUM
                admitted_new = m.apply_new_question_throttle(
                    new, new_introduced_today, 9, 1
                )
                if due_capped:
                    chosen = m.select_weighted_by_miss_rate(
                        due_capped,
                        response_stats,
                        None,
                        seeded_random.random(),
                    )
                elif admitted_new:
                    chosen = admitted_new[0]
                else:
                    break

                question_id = chosen["id"]
                correct = review_outcome_pattern[
                    pattern_index % len(review_outcome_pattern)
                ]
                pattern_index += 1
                elapsed_ms = 4000 + 137 * (question_id + day_offset)
                m.insert_response(
                    conn,
                    session_id,
                    chosen["question"],
                    chosen["answer"],
                    chosen["answer"] if correct else "wrong",
                    correct,
                    answered_text,
                    question_id=question_id,
                    elapsed_ms=elapsed_ms,
                )
                if first_reviewed_today is None:
                    first_reviewed_today = question_id
                existing = m.get_schedule_for_question(conn, question_id)
                if not m.schedule_update_allowed_today(existing, today):
                    continue
                if existing is None:
                    easiness_factor = m.EASINESS_FACTOR_INITIAL
                    interval_days = 0.0
                    repetition_count = 0
                    lapse_count_value = 0
                else:
                    easiness_factor = existing["easiness_factor"]
                    interval_days = existing["interval_days"]
                    repetition_count = existing["repetition_count"]
                    lapse_count_value = existing["lapse_count"]
                recall_quality = m.derive_recall_quality(correct, elapsed_ms)
                advanced = m.advance_schedule_state(
                    recall_quality,
                    easiness_factor,
                    interval_days,
                    repetition_count,
                    lapse_count_value,
                    today,
                )
                fuzzed = m.apply_interval_fuzz(
                    advanced["interval_days"], question_id
                )
                advanced["interval_days"] = fuzzed
                advanced["due_date"] = today + int(round(fuzzed))
                advanced["question_id"] = question_id
                m.upsert_schedule_row(conn, advanced)

        # Every tenth day: a deliberate same-day SECOND graded attempt on a
        # question already reviewed today, driven through the same gated
        # write path -- the response logs, the gate blocks the reschedule,
        # and the rebuild fold must ignore it identically.
        if day_offset % 10 == 0 and first_reviewed_today is not None:
            repeat_question = next(
                q
                for q in m.list_questions(conn, bank_alpha)
                + m.list_questions(conn, bank_beta)
                if q["id"] == first_reviewed_today
            )
            m.insert_response(
                conn,
                session_id,
                repeat_question["question"],
                repeat_question["answer"],
                "wrong",
                False,
                answered_text,
                question_id=first_reviewed_today,
            )
            existing = m.get_schedule_for_question(conn, first_reviewed_today)
            assert m.schedule_update_allowed_today(existing, today) is False
            # Gate blocked: no advance, no upsert -- exactly the handler.
    conn.commit()

    response_count = conn.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
    scheduled_count = conn.execute(
        "SELECT COUNT(*) FROM question_schedule"
    ).fetchone()[0]
    assert response_count > 100  # a real multi-week history
    assert scheduled_count == 16  # every question eventually entered

    response_rows_for_rebuild = [
        {
            "question_id": row["question_id"],
            "correct": bool(row["correct"]),
            "elapsed_ms": row["elapsed_ms"],
            "answered_ordinal": datetime.fromisoformat(
                row["answered"][:10]
            ).date().toordinal(),
        }
        for row in conn.execute(
            "SELECT question_id, correct, elapsed_ms, answered "
            "FROM responses ORDER BY id"
        )
    ]
    rebuilt = logic_module.rebuild_schedule_from_response_log(
        response_rows_for_rebuild
    )
    stored = {
        row["question_id"]: dict(row)
        for row in conn.execute("SELECT * FROM question_schedule")
    }
    assert set(rebuilt.keys()) == set(stored.keys())
    for question_id, rebuilt_state in rebuilt.items():
        stored_state = stored[question_id]
        for field in (
            "easiness_factor",
            "interval_days",
            "repetition_count",
            "due_date",
            "last_review",
            "lapse_count",
        ):
            assert abs(rebuilt_state[field] - stored_state[field]) <= 1e-9, (
                "rebuild mismatch: question %d field %s rebuilt %r stored %r"
                % (question_id, field, rebuilt_state[field], stored_state[field])
            )
    conn.close()
