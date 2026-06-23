"""Pure LOGIC tests -- no DB, no HTTP, no jsdom. The fastest, most total
tier (phase0.md Section B: "Pure LOGIC is the high-value target").

Concerns gathered here, by source:
  - summarize_stats      : harvested from test_c019a.py (the pure-summary half).
  - summarize_correctness: NEW in C-020 (live stats bar contract).
  - validate_answer      : NEW in C-020 (every qtype branch + the unknown-qtype
                           "never silently correct" guarantee).
  - generate / evaluate /
    render_expression    : NEW in C-020 (example-based invariants; the
                           exhaustive property test lives in
                           test_generator_property.py).
  - pick_next_question   : NEW in C-020 (avoid-recent policy + fallbacks).

These are functions of plain data, so they need no fixtures beyond the module.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from _support import load_drill  # noqa: E402


@pytest.fixture(scope="module")
def m():
    return load_drill()


# --------------------------------------------------------------------------
# summarize_correctness -- the live stats bar (total/correct/accuracy/streak)
# --------------------------------------------------------------------------
def test_summarize_correctness_empty_is_time_zero(m):
    s = m.summarize_correctness([])
    assert s == {"total": 0, "correct": 0, "accuracy": 0.0, "streak": 0}


def test_summarize_correctness_counts_and_accuracy(m):
    s = m.summarize_correctness([True, False, True, True])
    assert s["total"] == 4
    assert s["correct"] == 3
    assert abs(s["accuracy"] - 0.75) < 1e-9


def test_summarize_correctness_streak_counts_back_from_most_recent(m):
    assert m.summarize_correctness([False, True, True])["streak"] == 2
    assert m.summarize_correctness([True, True, False])["streak"] == 0
    assert m.summarize_correctness([True, True, True])["streak"] == 3


# --------------------------------------------------------------------------
# summarize_stats -- durable cross-session summary (harvested from C-019a)
# --------------------------------------------------------------------------
def _rows(*specs):
    """specs: (category_id, category_name, correct, elapsed_ms) tuples."""
    return [
        {
            "category_id": cid,
            "category_name": name,
            "correct": correct,
            "elapsed_ms": ms,
            "answered": "2026-01-01T00:00:00+00:00",
        }
        for (cid, name, correct, ms) in specs
    ]


def test_summarize_stats_totals_and_accuracy(m):
    rows = _rows(
        (1, "arithmetic", True, 1500),
        (1, "arithmetic", True, 900),
        (1, "arithmetic", False, None),
        (2, "vocabulary", True, 2200),
    )
    s = m.summarize_stats(rows)
    assert s["total"] == 4
    assert s["correct"] == 3
    assert abs(s["accuracy"] - 0.75) < 1e-9


def test_summarize_stats_breakdown_orders_most_practiced_first(m):
    rows = _rows(
        (2, "vocabulary", True, None),
        (1, "arithmetic", True, None),
        (1, "arithmetic", False, None),
        (1, "arithmetic", True, None),
    )
    s = m.summarize_stats(rows)
    assert s["categories"][0]["category_id"] == 1
    assert s["categories"][0]["total"] == 3


def test_summarize_stats_empty_is_time_zero(m):
    s = m.summarize_stats([])
    assert s["total"] == 0
    assert s["accuracy"] == 0.0
    assert s["categories"] == []


def test_summarize_stats_ignores_elapsed_ms(m):
    s = m.summarize_stats(_rows((1, "arithmetic", True, 1500)))
    assert not any(
        ("elapsed" in k) or ("ms" in k) or ("time" in k) for k in s.keys()
    )


def test_summarize_stats_is_order_independent(m):
    import random

    rows = _rows(
        (1, "arithmetic", True, None),
        (1, "arithmetic", False, None),
        (2, "vocabulary", True, None),
    )
    shuffled = rows[:]
    random.Random(7).shuffle(shuffled)
    assert m.summarize_stats(shuffled)["categories"] == m.summarize_stats(rows)[
        "categories"
    ]


# --------------------------------------------------------------------------
# validate_answer -- dispatch by qtype, plus the unknown-qtype guarantee
# --------------------------------------------------------------------------
def test_validate_arithmetic_numeric_within_tolerance(m):
    assert m.validate_answer("13", "13", m.QTYPE_ARITHMETIC) is True
    assert m.validate_answer("13", "14", m.QTYPE_ARITHMETIC) is False


def test_validate_free_response_normalizes_both_sides(m):
    assert m.validate_answer("Paris", "  paris.  ", m.QTYPE_FREE_RESPONSE) is True


def test_validate_free_response_accepts_alternatives(m):
    ok = m.validate_answer(
        "color", "colour", m.QTYPE_FREE_RESPONSE, alternatives=["colour"]
    )
    assert ok is True


def test_validate_multiple_choice_is_exact(m):
    assert m.validate_answer("Option A", "Option A", m.QTYPE_MULTIPLE_CHOICE) is True
    assert m.validate_answer("Option A", "option a", m.QTYPE_MULTIPLE_CHOICE) is False


def test_validate_unknown_qtype_is_never_correct(m):
    # The "can never be silently scored correct" guarantee, even on an exact
    # string match.
    assert m.validate_answer("x", "x", "no_such_qtype") is False


# --------------------------------------------------------------------------
# generate / evaluate / render -- example-based invariants
# (the exhaustive sweep is the hypothesis test in test_generator_property.py)
# --------------------------------------------------------------------------
def test_evaluate_leaf_and_node(m):
    assert m.evaluate_expression(7) == 7
    assert m.evaluate_expression({"op": "+", "left": 2, "right": 3}) == 5


def test_render_flat_has_no_parentheses(m):
    assert m.render_expression({"op": "+", "left": 6, "right": 7}) == "6 + 7"


def test_render_nested_parenthesizes_subexpressions(m):
    node = {"op": "*", "left": {"op": "+", "left": 1, "right": 2}, "right": 3}
    assert m.render_expression(node) == "(1 + 2) * 3"


def test_generate_empty_symbol_set_raises(m):
    with pytest.raises(ValueError):
        m.generate_expression(enabled_symbols=[])


def test_generate_unknown_symbol_raises(m):
    with pytest.raises(ValueError):
        m.generate_expression(enabled_symbols=["%"])


def test_generate_division_is_always_integral(m):
    # Division generation derives the dividend as divisor*quotient, so the
    # quotient is exact every time. Sample enough to catch a regression.
    for _ in range(200):
        node = m.generate_expression(enabled_symbols=["/"])
        assert node["left"] % node["right"] == 0
        assert isinstance(m.evaluate_expression(node), int)


# --------------------------------------------------------------------------
# pick_next_question -- avoid-recent policy with safe fallbacks
# --------------------------------------------------------------------------
def test_pick_next_empty_returns_none(m):
    assert m.pick_next_question([]) is None


def test_pick_next_avoids_recent_when_possible(m):
    candidates = [{"id": 1}, {"id": 2}, {"id": 3}]
    # With ids 1 and 2 recent, only id 3 is fresh -> must pick it every time.
    for _ in range(50):
        assert m.pick_next_question(candidates, history=[1, 2])["id"] == 3


def test_pick_next_falls_back_when_all_recent(m):
    candidates = [{"id": 1}, {"id": 2}]
    # Every candidate recently seen -> fall back to the full pool, never None.
    for _ in range(50):
        assert m.pick_next_question(candidates, history=[1, 2])["id"] in (1, 2)
