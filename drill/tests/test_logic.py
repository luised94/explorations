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

Decision anchors (decisions.md):
  validate_answer ............ C-007 (single dispatcher; unknown qtype -> False)
  generate/forbid_identity ... C-005, C-006, ADR-007 (operand ranges, identities)
  division derivation ........ C-005 / ADR-007 (dividend = divisor * quotient)
  subtraction non-negative ... C-006 (left >= right, reject x - x)
  pick_next_question ......... C-012, ADR-005 (random + avoid-recent, v1)
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(__file__))
from _support import load_logic  # noqa: E402


@pytest.fixture(scope="module")
def m():
    # D3: the entire LOGIC layer (arithmetic engine + general logic) lives in
    # logic.py. Tests read config scalars (QTYPE_*, _MAX_*, _RECURSE_PROBABILITY)
    # through logic's re-exports, and state-mutating tests rebind logic's own
    # module globals (which the arithmetic functions read), so a single handle
    # suffices. (D-4: tests import the submodule they exercise.)
    return load_logic()


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
    assert s["difficulty_breakdown"] == []
    assert s["median_elapsed_ms"] is None


def test_summarize_stats_median_elapsed_ms_odd(m):
    # Thread N.2: median over the non-null timing values. Odd count -> the
    # middle value after sorting (900, 1500, 2200 -> 1500).
    rows = _rows(
        (1, "arithmetic", True, 1500),
        (1, "arithmetic", True, 900),
        (2, "vocabulary", True, 2200),
    )
    assert m.summarize_stats(rows)["median_elapsed_ms"] == 1500


def test_summarize_stats_median_elapsed_ms_even(m):
    # Even count -> average of the two central values, int-rounded.
    # sorted 900, 1500, 2000, 2200 -> (1500 + 2000) / 2 = 1750.
    rows = _rows(
        (1, "arithmetic", True, 1500),
        (1, "arithmetic", True, 900),
        (1, "arithmetic", True, 2000),
        (2, "vocabulary", True, 2200),
    )
    assert m.summarize_stats(rows)["median_elapsed_ms"] == 1750


def test_summarize_stats_median_skips_null_elapsed_ms(m):
    # The subtle case: a null elapsed_ms is SKIPPED, not counted as 0 (which
    # would drag the median down). With one null, the median is over the two
    # real values -> average(900, 1500) = 1200, NOT median(0, 900, 1500)=900.
    rows = _rows(
        (1, "arithmetic", True, 1500),
        (1, "arithmetic", False, None),
        (1, "arithmetic", True, 900),
    )
    assert m.summarize_stats(rows)["median_elapsed_ms"] == 1200


def test_summarize_stats_median_null_when_all_null(m):
    # All responses lack timing (e.g. all pre-C-018c) -> no figure.
    rows = _rows(
        (1, "arithmetic", True, None),
        (2, "vocabulary", False, None),
    )
    assert m.summarize_stats(rows)["median_elapsed_ms"] is None


def test_summarize_stats_is_order_independent(m):
    import random

    rows = _rows(
        (1, "arithmetic", True, None),
        (1, "arithmetic", False, None),
        (2, "vocabulary", True, None),
    )
    shuffled = rows[:]
    random.Random(7).shuffle(shuffled)
    assert (
        m.summarize_stats(shuffled)["categories"]
        == m.summarize_stats(rows)["categories"]
    )


# --------------------------------------------------------------------------
# breakdown_by -- the pure grouping seam (C-D2i-1, ADR-041)
# --------------------------------------------------------------------------
def _bd_rows(*specs):
    """specs: (key, label_source, correct) -> rows carrying a generic key field."""
    return [
        {"grp": key, "name": label, "correct": correct}
        for (key, label, correct) in specs
    ]


def test_breakdown_by_groups_and_counts(m):
    rows = _bd_rows(
        ("a", "Alpha", True),
        ("a", "Alpha", False),
        ("b", "Beta", True),
    )
    out = m.breakdown_by(rows, key_of=lambda r: r["grp"], label_of=lambda r: r["name"])
    by_key = {entry["key"]: entry for entry in out}
    assert by_key["a"]["total"] == 2 and by_key["a"]["correct"] == 1
    assert abs(by_key["a"]["accuracy"] - 0.5) < 1e-9
    assert by_key["b"]["total"] == 1 and by_key["b"]["accuracy"] == 1.0
    assert by_key["a"]["label"] == "Alpha"


def test_breakdown_by_orders_most_practiced_first(m):
    rows = _bd_rows(
        ("b", "Beta", True),
        ("a", "Alpha", True),
        ("a", "Alpha", False),
        ("a", "Alpha", True),
    )
    out = m.breakdown_by(rows, key_of=lambda r: r["grp"], label_of=lambda r: r["name"])
    assert out[0]["key"] == "a"  # 3 beats 1
    assert out[0]["total"] == 3


def test_breakdown_by_label_tiebreak_is_deterministic(m):
    # Equal totals -> sorted by label, regardless of input order.
    rows = _bd_rows(("z", "Zeta", True), ("a", "Alpha", True))
    out = m.breakdown_by(rows, key_of=lambda r: r["grp"], label_of=lambda r: r["name"])
    assert [e["label"] for e in out] == ["Alpha", "Zeta"]


def test_breakdown_by_include_row_filters(m):
    rows = [
        {"grp": 2, "correct": True, "keep": True},
        {"grp": 2, "correct": False, "keep": True},
        {"grp": 9, "correct": True, "keep": False},  # filtered out
    ]
    out = m.breakdown_by(
        rows,
        key_of=lambda r: r["grp"],
        label_of=lambda r: str(r["grp"]),
        include_row=lambda r: r["keep"],
    )
    assert len(out) == 1
    assert out[0]["key"] == 2 and out[0]["total"] == 2


def test_breakdown_by_empty_is_empty_list(m):
    assert m.breakdown_by([], key_of=lambda r: r["x"], label_of=lambda r: "") == []
    # All rows filtered out also yields an empty list (not an error).
    rows = [{"grp": 1, "correct": True}]
    out = m.breakdown_by(
        rows,
        key_of=lambda r: r["grp"],
        label_of=lambda r: "x",
        include_row=lambda r: False,
    )
    assert out == []


def test_breakdown_by_is_order_independent(m):
    import random

    rows = _bd_rows(
        ("a", "Alpha", True),
        ("a", "Alpha", False),
        ("b", "Beta", True),
        ("c", "Gamma", True),
    )
    shuffled = rows[:]
    random.Random(11).shuffle(shuffled)
    a = m.breakdown_by(rows, key_of=lambda r: r["grp"], label_of=lambda r: r["name"])
    b = m.breakdown_by(
        shuffled, key_of=lambda r: r["grp"], label_of=lambda r: r["name"]
    )
    assert a == b


# --------------------------------------------------------------------------
# summarize_stats difficulty_breakdown -- grouped by leaf_count (C-D2i-2, S11)
# --------------------------------------------------------------------------
def _arith_rows(*specs):
    """specs: (leaf_count, correct) for arithmetic responses."""
    return [
        {
            "category_id": 1,
            "category_name": "arithmetic",
            "correct": correct,
            "elapsed_ms": None,
            "answered": "2026-01-01T00:00:00+00:00",
            "difficulty": None,  # recording-only; the breakdown ignores it
            "leaf_count": leaf_count,
        }
        for (leaf_count, correct) in specs
    ]


def test_difficulty_breakdown_groups_by_leaf_count(m):
    rows = _arith_rows((2, True), (2, False), (4, True), (4, True))
    s = m.summarize_stats(rows)
    by_key = {entry["key"]: entry for entry in s["difficulty_breakdown"]}
    assert by_key[2]["total"] == 2 and by_key[2]["correct"] == 1
    assert by_key[4]["total"] == 2 and by_key[4]["correct"] == 2
    assert by_key[2]["label"] == "2 leaves"
    # ordered most-practiced first; equal totals -> label tiebreak ("2" < "4")
    assert [e["key"] for e in s["difficulty_breakdown"]] == [2, 4]


def test_difficulty_breakdown_excludes_null_and_nonarithmetic(m):
    rows = _arith_rows((2, True), (3, False)) + [
        # arithmetic but NULL leaf_count (no-rung / pre-#2) -> excluded
        {
            "category_id": 1,
            "category_name": "arithmetic",
            "correct": True,
            "elapsed_ms": None,
            "answered": "2026-01-01T00:00:00+00:00",
            "difficulty": None,
            "leaf_count": None,
        },
        # non-arithmetic with a leaf_count somehow set -> excluded
        {
            "category_id": 2,
            "category_name": "vocabulary",
            "correct": True,
            "elapsed_ms": None,
            "answered": "2026-01-01T00:00:00+00:00",
            "difficulty": None,
            "leaf_count": 2,
        },
    ]
    s = m.summarize_stats(rows)
    keys = sorted(e["key"] for e in s["difficulty_breakdown"])
    assert keys == [2, 3]  # only the two real arithmetic-with-leaf_count rows
    totals = {e["key"]: e["total"] for e in s["difficulty_breakdown"]}
    assert totals == {2: 1, 3: 1}


def test_difficulty_breakdown_empty_when_no_leaf_counts(m):
    # All arithmetic but every row NULL leaf_count -> empty breakdown, while the
    # category summary is still populated (the two are independent).
    rows = _rows((1, "arithmetic", True, None), (1, "arithmetic", False, None))
    s = m.summarize_stats(rows)
    assert s["difficulty_breakdown"] == []
    assert s["categories"][0]["total"] == 2  # category path unaffected


def test_difficulty_breakdown_does_not_disturb_category_summary(m):
    # Adding leaf_count rows must not change total/correct/accuracy/categories.
    rows = _arith_rows((2, True), (4, False))
    s = m.summarize_stats(rows)
    assert s["total"] == 2 and s["correct"] == 1
    assert s["categories"][0]["category_name"] == "arithmetic"
    assert s["categories"][0]["total"] == 2


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
    # C-007 [DECIDED]: an unrecognized qtype returns False (never silently
    # scored correct), rather than raising -- even on an exact string match.
    assert m.validate_answer("x", "x", "no_such_qtype") is False


# --------------------------------------------------------------------------
# generate / evaluate / render -- example-based invariants
# (the exhaustive sweep is the hypothesis test in test_generator_property.py)
# --------------------------------------------------------------------------
def test_evaluate_leaf_and_node(m):
    assert m.evaluate_expression(7) == 7
    assert m.evaluate_expression({"op": "+", "left": 2, "right": 3}) == 5


def test_evaluate_modulo_and_exponent(m):
    # #4: modulo uses operator.mod, exponent uses operator.pow.
    assert m.evaluate_expression({"op": "%", "left": 17, "right": 5}) == 2
    assert m.evaluate_expression({"op": "^", "left": 3, "right": 2}) == 9


def test_render_flat_has_no_parentheses(m):
    assert m.render_expression({"op": "+", "left": 6, "right": 7}) == "6 + 7"


def test_render_modulo_and_exponent(m):
    # #4: symbols render infix like the existing operators (server-side only).
    assert m.render_expression({"op": "%", "left": 17, "right": 5}) == "17 % 5"
    assert m.render_expression({"op": "^", "left": 3, "right": 2}) == "3 ^ 2"


def test_render_nested_parenthesizes_subexpressions(m):
    node = {"op": "*", "left": {"op": "+", "left": 1, "right": 2}, "right": 3}
    assert m.render_expression(node) == "(1 + 2) * 3"


# --------------------------------------------------------------------------
# precedence-aware renderer -- C-D5b (the cs showpiece)
# The renderer is the SOLE owner of correct printing: the rendered string must
# parse back, under standard precedence/associativity, to the SAME tree it came
# from. evaluate_expression never consults precedence, so a wrong wrap silently
# desyncs the displayed question from the stored answer. Test EXHAUSTIVELY with
# HAND-BUILT trees (decoupled from generator output), table-driven over
# operator-pair x nested-side, asserting EXACT strings -- not "contains". Some
# trees here (e.g. anything nesting under / % ^) are NOT generator-reachable in
# #5; the renderer is nonetheless total over all well-formed trees, which is
# what lets #2 widen generation with zero renderer change.
# --------------------------------------------------------------------------
def _n(op, left, right):
    return {"op": op, "left": left, "right": right}


_RENDER_CASES = [
    # --- flat / leaf: no parentheses ever ---
    ("flat add", _n("+", 1, 2), "1 + 2"),
    ("flat sub", _n("-", 9, 4), "9 - 4"),
    ("flat mul", _n("*", 3, 4), "3 * 4"),
    ("flat div", _n("/", 12, 4), "12 / 4"),
    ("flat mod", _n("%", 17, 5), "17 % 5"),
    ("flat pow", _n("^", 3, 2), "3 ^ 2"),
    # --- lower-precedence child under higher-precedence parent: KEEP ---
    # (a + b) * c -- already exercised by the legacy test; here both sides.
    ("sum left of product", _n("*", _n("+", 1, 2), 3), "(1 + 2) * 3"),
    ("sum right of product", _n("*", 3, _n("+", 1, 2)), "3 * (1 + 2)"),
    ("diff left of product", _n("*", _n("-", 5, 2), 4), "(5 - 2) * 4"),
    ("sum under exponent", _n("^", _n("+", 1, 2), 2), "(1 + 2) ^ 2"),
    ("product under exponent", _n("^", _n("*", 2, 3), 2), "(2 * 3) ^ 2"),
    # --- higher-precedence child under lower-precedence parent: DROP ---
    # a * b + c -> tree (a*b)+c ; product binds tighter, no parens needed.
    ("product left of sum", _n("+", _n("*", 2, 3), 4), "2 * 3 + 4"),
    ("product right of sum", _n("+", 4, _n("*", 2, 3)), "4 + 2 * 3"),
    ("exponent under product", _n("*", _n("^", 2, 3), 5), "2 ^ 3 * 5"),
    ("exponent right of product", _n("*", 5, _n("^", 2, 3)), "5 * 2 ^ 3"),
    # --- same-tier, LEFT-associative parent ---
    # left child on the correct (left) side: DROP.
    ("sub then add: a - b + c", _n("+", _n("-", 8, 3), 2), "8 - 3 + 2"),
    ("div then mul: a / b * c", _n("*", _n("/", 12, 4), 3), "12 / 4 * 3"),
    ("add then add left", _n("+", _n("+", 1, 2), 3), "1 + 2 + 3"),
    # right child on the wrong (right) side: KEEP.
    ("sub of sub: a - (b - c)", _n("-", 9, _n("-", 5, 1)), "9 - (5 - 1)"),
    ("add then sub right: a + (b - c)", _n("+", 8, _n("-", 5, 1)), "8 + (5 - 1)"),
    ("mul of div: a * (b / c)", _n("*", 6, _n("/", 8, 2)), "6 * (8 / 2)"),
    ("mul of mod: a * (b % c)", _n("*", 6, _n("%", 17, 5)), "6 * (17 % 5)"),
    ("mod right of mul: a * (b % c)", _n("*", 4, _n("%", 9, 2)), "4 * (9 % 2)"),
    # --- same-tier, RIGHT-associative parent (exponent) ---
    # right child on the correct (right) side for right-assoc: DROP.
    ("pow right-assoc: 2 ^ 3 ^ 2", _n("^", 2, _n("^", 3, 2)), "2 ^ 3 ^ 2"),
    # left child on the wrong (left) side for right-assoc: KEEP.
    ("pow left-nested: (2 ^ 3) ^ 2", _n("^", _n("^", 2, 3), 2), "(2 ^ 3) ^ 2"),
    # --- deeper compositions ---
    # ((1 + 2) * 3) - 4 : product binds tighter than the outer -, so the
    # product needs no wrap on the left of -, but the inner sum still wraps.
    ("nested two levels", _n("-", _n("*", _n("+", 1, 2), 3), 4), "(1 + 2) * 3 - 4"),
    # a * (b - c) on a left branch of +, plus a same-tier right sub: exercises
    # both rules in one tree. tree: (2 * (5 - 1)) + (9 - 3)
    (
        "mixed left product-of-diff, right diff",
        _n("+", _n("*", 2, _n("-", 5, 1)), _n("-", 9, 3)),
        "2 * (5 - 1) + (9 - 3)",
    ),
]


@pytest.mark.parametrize(
    "label,tree,expected", _RENDER_CASES, ids=[c[0] for c in _RENDER_CASES]
)
def test_render_precedence_and_associativity(m, label, tree, expected):
    assert m.render_expression(tree) == expected


def test_render_roundtrips_through_evaluate(m):
    # Independent of exact strings: every hand-built case must round-trip --
    # evaluating the tree and the string-as-read agree by construction here,
    # but at minimum the renderer must not raise and must produce a non-empty
    # string for every well-formed tree (the renderer is total).
    for _label, tree, _expected in _RENDER_CASES:
        text = m.render_expression(tree)
        assert isinstance(text, str) and text != ""
        assert isinstance(m.evaluate_expression(tree), int)


# Trees the #5 GENERATOR never builds (a leaf-only operator with a subtree
# child: / % ^ are nestable=False, ADR-032). The renderer is nonetheless TOTAL
# over them -- it parenthesizes by precedence/associativity regardless of which
# operator owns the subtree. This test locks that totality in: it is the
# counterpart to the property walk's structural invariant (which pins that the
# generator never EMITS these). Together they make ADR-033's "renderer is the
# sole owner of printing, total over well-formed trees" a tested guarantee, so
# #2 can make / % ^ nestable (ADR-037 deferred door) with ZERO renderer change.
# If a future contributor "tightens" the renderer to reject these, this test
# goes red with the reason attached.
_UNREACHABLE_RENDER_CASES = [
    # a / (b * c): division over a product subtree. * (prec 2) under / (prec 2,
    # left-assoc) on the right side -> wrong side -> KEEP.
    ("div over product", _n("/", 24, _n("*", 2, 3)), "24 / (2 * 3)"),
    # a / (b + c): + (prec 1) under / (prec 2) -> lower precedence -> KEEP.
    ("div over sum", _n("/", 30, _n("+", 2, 3)), "30 / (2 + 3)"),
    # 2 ^ (a + b): + under ^ (prec 3) -> lower precedence -> KEEP.
    ("pow over sum", _n("^", 2, _n("+", 1, 2)), "2 ^ (1 + 2)"),
    # (a + b) % c: + under % (prec 2) on the left -> lower precedence -> KEEP.
    ("mod of sum", _n("%", _n("+", 7, 6), 5), "(7 + 6) % 5"),
    # a % (b - c): - (prec 1) under % (prec 2) on the right -> KEEP.
    ("mod over diff", _n("%", 20, _n("-", 9, 2)), "20 % (9 - 2)"),
    # nested leaf-only under leaf-only: (a ^ b) / c -- ^ (prec 3) under / (prec
    # 2) on the left -> higher precedence, correct side -> DROP.
    ("div of power-left", _n("/", _n("^", 2, 3), 4), "2 ^ 3 / 4"),
]


@pytest.mark.parametrize(
    "label,tree,expected",
    _UNREACHABLE_RENDER_CASES,
    ids=[c[0] for c in _UNREACHABLE_RENDER_CASES],
)
def test_render_is_total_over_unreachable_trees(m, label, tree, expected):
    # The renderer must PRINT these (not raise, not reject), and print them
    # correctly under the same precedence/associativity rule.
    assert m.render_expression(tree) == expected
    # and they evaluate like any other well-formed tree
    assert isinstance(m.evaluate_expression(tree), int)


def test_generate_empty_symbol_set_raises(m):
    with pytest.raises(ValueError):
        m.generate_expression(enabled_symbols=[])


def test_generate_unknown_symbol_raises(m):
    with pytest.raises(ValueError):
        # "$" is not a defined operator symbol. (Was "%" before #4 enabled
        # modulo; "%" is a valid operator now, so the sentinel must be a symbol
        # that genuinely has no record.)
        m.generate_expression(enabled_symbols=["$"])


def test_generate_division_is_always_integral(m):
    # ADR-007 / C-005: division generation derives the dividend as
    # divisor*quotient, so the quotient is exact every time. Sample enough to
    # catch a regression.
    for _ in range(200):
        node = m.generate_expression(enabled_symbols=["/"])
        assert node["left"] % node["right"] == 0
        assert isinstance(m.evaluate_expression(node), int)


# --------------------------------------------------------------------------
# bottom-up nested generation -- C-D5c (#5 spine)
# Example-based companions to the recursive property walk in
# test_generator_property.py: pin the depth knob's two reproduction points and
# show that nesting actually happens at the default. Reproducibility is via
# seeding the GLOBAL RNG (no seed parameter is threaded -- production is
# intentionally nondeterministic; tests seed random.seed(N) per the existing
# pattern).
# --------------------------------------------------------------------------
def _operator_depth(node):
    if isinstance(node, int):
        return 0
    return 1 + max(_operator_depth(node["left"]), _operator_depth(node["right"]))


def test_generate_depth_one_reproduces_flat(m):
    # _MAX_OPERATOR_DEPTH == 1 reproduces the flat #4 generator exactly: every
    # tree is a single operator over two integer leaves.
    original = m._MAX_OPERATOR_DEPTH
    try:
        m._MAX_OPERATOR_DEPTH = 1
        for _ in range(200):
            node = m.generate_expression()
            assert _operator_depth(node) == 1
            assert isinstance(node["left"], int)
            assert isinstance(node["right"], int)
    finally:
        m._MAX_OPERATOR_DEPTH = original


def test_generate_p_recurse_zero_reproduces_flat(m):
    # _RECURSE_PROBABILITY == 0 also reproduces flat generation even with depth
    # budget available: no operand is ever chosen to be a subtree.
    original = m._RECURSE_PROBABILITY
    try:
        m._RECURSE_PROBABILITY = 0.0
        for _ in range(200):
            node = m.generate_expression(enabled_symbols=["+", "-", "*"])
            assert _operator_depth(node) == 1
    finally:
        m._RECURSE_PROBABILITY = original


def test_generate_default_depth_produces_some_nesting(m):
    # At the provisional defaults (_MAX_OPERATOR_DEPTH == 2, _RECURSE_PROBABILITY
    # == 0.5) over composable operators, at least some trees nest (depth 2) and
    # none exceed the depth ceiling. Seeded for determinism.
    import random

    random.seed(1234)
    depths = set()
    for _ in range(500):
        node = m.generate_expression(enabled_symbols=["+", "-", "*"])
        d = _operator_depth(node)
        assert 1 <= d <= m._MAX_OPERATOR_DEPTH
        depths.add(d)
    assert 2 in depths  # nesting actually occurs at the default


def test_generate_nested_round_trips_value_through_render(m):
    # The renderer must emit a string that, read under standard precedence and
    # associativity, parses back to the SAME tree's value. Map ^ -> ** and /
    # -> // (our division is exact, so // == /), then re-evaluate the rendered
    # string with Python's grammar and compare to evaluate_expression.
    import random

    random.seed(2025)
    for _ in range(500):
        node = m.generate_expression()
        expected = m.evaluate_expression(node)
        rendered = m.render_expression(node)
        reparsed = eval(rendered.replace("^", "**").replace("/", "//"))
        assert reparsed == expected, (rendered, reparsed, expected)


def test_generate_retry_exhaustion_raises(m):
    # Bounded retry: when attempts are exhausted, build_subtree raises a clear
    # RuntimeError rather than hanging. Force it by setting the ceiling to 0.
    original = m._MAX_GENERATION_ATTEMPTS
    try:
        m._MAX_GENERATION_ATTEMPTS = 0
        with pytest.raises(RuntimeError):
            m.generate_expression(enabled_symbols=["+"])
    finally:
        m._MAX_GENERATION_ATTEMPTS = original


# --------------------------------------------------------------------------
# global result ceiling -- C-D5d (dark mechanism, default OFF)
# _MAX_RESULT_VALUE is None by default: the local feasibility check at node
# assembly is a no-op, so behavior is identical to C-D5c. Setting it bounds the
# evaluated RESULT of every internal node (value(left) <op> value(right) <=
# ceiling); an infeasible-too-low ceiling exhausts the bounded retry and raises.
# The ceiling bounds node RESULTS, not input-leaf magnitudes -- division derives
# a dividend that can exceed the ceiling while the quotient result stays under
# it -- so this test exercises composable operators (+ - *), where the node
# result is the natural quantity bounded.
# --------------------------------------------------------------------------
def _max_internal_result(m, node):
    # Max evaluated result over INTERNAL nodes only (a leaf is an input operand,
    # not the result of an operation).
    if isinstance(node, int):
        return None
    values = [m.evaluate_expression(node)]
    for child in (node["left"], node["right"]):
        child_max = _max_internal_result(m, child)
        if child_max is not None:
            values.append(child_max)
    return max(values)


def test_result_ceiling_default_off_is_unbounded(m):
    # Sanity that the default is genuinely OFF: over composable operators some
    # generated tree's result comfortably exceeds a value a low ceiling would
    # reject, proving the no-op default is not silently clamping.
    import random

    assert m._MAX_RESULT_VALUE is None  # the shipped default
    random.seed(11)
    biggest = 0
    for _ in range(500):
        node = m.generate_expression(enabled_symbols=["+", "-", "*"])
        biggest = max(biggest, _max_internal_result(m, node))
    assert biggest > 30  # unbounded by default (a ceiling of 30 would have cut)


def test_result_ceiling_bounds_every_node_result(m):
    # With a low ceiling set, EVERY internal node's evaluated result stays within
    # it -- including nodes nested under a composable parent.
    import random

    original = m._MAX_RESULT_VALUE
    try:
        m._MAX_RESULT_VALUE = 25
        random.seed(13)
        nested_seen = False
        for _ in range(800):
            node = m.generate_expression(enabled_symbols=["+", "-", "*"])
            assert _max_internal_result(m, node) <= 25
            if _operator_depth(node) > 1:
                nested_seen = True
        assert nested_seen  # the ceiling still permits nesting at this bound
    finally:
        m._MAX_RESULT_VALUE = original


def test_result_ceiling_too_low_raises(m):
    # An infeasible ceiling (below the smallest possible result for the only
    # enabled operator) exhausts the bounded retry and raises RuntimeError --
    # proving the mechanism, not just the default. The smallest non-trivial
    # addition result is 1 + 2 == 3 (0 is forbidden), so a ceiling of 2 is
    # unsatisfiable for "+".
    original = m._MAX_RESULT_VALUE
    try:
        m._MAX_RESULT_VALUE = 2
        with pytest.raises(RuntimeError):
            m.generate_expression(enabled_symbols=["+"])
    finally:
        m._MAX_RESULT_VALUE = original


# --------------------------------------------------------------------------
# question_text length regression guard -- C-D5e
# responses.question_text is TEXT NOT NULL (unbounded in SQLite), so nesting
# violates no schema constraint; this guard is a SANITY bound, not a storage
# limit. A generated max-depth arithmetic question_text must stay well under a
# few hundred chars. It catches a renderer/generator regression that blows up
# output (runaway depth, pathological over-parenthesizing) and doubles as a
# guard if _MAX_OPERATOR_DEPTH is later cranked high. At the provisional
# defaults the longest observed output is ~20 chars; 400 is generous headroom.
# --------------------------------------------------------------------------
_QUESTION_TEXT_LENGTH_BOUND = 400


def test_question_text_stays_under_length_bound(m):
    import random

    random.seed(404)
    longest = 0
    for _ in range(2000):
        node = m.generate_expression()
        text = m.render_expression(node)
        longest = max(longest, len(text))
        assert len(text) < _QUESTION_TEXT_LENGTH_BOUND, (len(text), text)
    # the longest sample should be comfortably under the bound, not skating it
    assert longest < _QUESTION_TEXT_LENGTH_BOUND // 2


# --------------------------------------------------------------------------
# operator-record declarative fields -- C-D5a (#5 nesting groundwork)
# nestable / precedence / associativity are now REQUIRED record keys validated
# by _build_operator_table. Assert they are present and well-typed for every
# operator, and that they carry the settled #5 values. Nothing reads these yet
# (the renderer change is C-D5b, the generator change C-D5c); this pins the
# data and the validator contract.
# --------------------------------------------------------------------------
def test_operator_records_declare_nesting_fields(m):
    expected = {
        # symbol: (nestable, precedence, associativity)
        "+": (True, 1, "left"),
        "-": (True, 1, "left"),
        "*": (True, 2, "left"),
        "/": (False, 2, "left"),
        "%": (False, 2, "left"),
        "^": (False, 3, "right"),
    }
    for symbol, (nestable, precedence, associativity) in expected.items():
        record = m.OPERATORS[symbol]
        # present
        assert "nestable" in record
        assert "precedence" in record
        assert "associativity" in record
        # well-typed (bool is checked strictly: precedence must not be a bool,
        # since bool is an int subclass and a stray True would slip through a
        # bare isinstance(..., int) check)
        assert isinstance(record["nestable"], bool)
        assert isinstance(record["precedence"], int) and not isinstance(
            record["precedence"], bool
        )
        assert record["associativity"] in ("left", "right")
        # carries the settled #5 values
        assert record["nestable"] is nestable
        assert record["precedence"] == precedence
        assert record["associativity"] == associativity


def test_operator_record_missing_new_key_fails_table_build(m):
    # The validator must REQUIRE the new keys: a record missing one fails loudly
    # at table-build time, the same guard that protects the older required keys.
    import copy

    incomplete = copy.deepcopy(m.OPERATOR_DEFINITIONS[0])
    del incomplete["precedence"]
    original = m.OPERATOR_DEFINITIONS
    try:
        m.OPERATOR_DEFINITIONS = [incomplete]
        with pytest.raises(ValueError):
            m._build_operator_table()
    finally:
        m.OPERATOR_DEFINITIONS = original


# --------------------------------------------------------------------------
# pick_next_question -- avoid-recent policy with safe fallbacks
# C-012 / ADR-005: v1 is uniformly-random with an avoid-recent window; falls
# back to the full pool rather than ever failing to return for a non-empty bank.
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


# --------------------------------------------------------------------------
# normalize_text -- the lenient free-text comparison pipeline (C-007 feedback)
# What it DOES: lowercase, drop interior punctuation (,.!?:;), collapse
# whitespace, strip surrounding quotes/parens. What it deliberately does NOT
# do: strip interior hyphens, apostrophes, or Unicode accents -- those carry
# meaning in language drills. These tests pin both halves so a future
# "clean up normalization" change cannot silently widen what counts as equal.
# --------------------------------------------------------------------------
def test_normalize_lowercases_and_drops_interior_punctuation(m):
    assert m.normalize_text("Hello, World!") == "hello world"


def test_normalize_collapses_whitespace(m):
    assert m.normalize_text("a   b\t c") == "a b c"


def test_normalize_strips_surrounding_quotes_and_parens(m):
    assert m.normalize_text('"answer"') == "answer"
    assert m.normalize_text("(answer)") == "answer"


def test_normalize_preserves_interior_apostrophe(m):
    # C-007: apostrophes carry meaning -> NOT stripped from the interior.
    assert m.normalize_text("don't") == "don't"


def test_normalize_preserves_interior_hyphen(m):
    # C-007: hyphens carry meaning -> NOT stripped.
    assert m.normalize_text("e-mail") == "e-mail"


def test_normalize_preserves_accents(m):
    # C-007: accent-sensitive by decision -> accents survive normalization.
    # "caf\u00e9" is "cafe" + lowercase e-acute (U+00E9). Written as an ASCII
    # \u escape, not a literal accented byte: a raw 0x82 here (CP1252 e-acute)
    # was invalid UTF-8 and broke pytest collection -- see decisions.md C-021.
    assert m.normalize_text("caf\u00e9") == "caf\u00e9"


def test_validate_translate_is_accent_sensitive(m):
    # The consequence of accent preservation: an unaccented answer to an
    # accented expected value is WRONG. Pins the decision at the validator.
    assert m.validate_answer("caf\u00e9", "cafe", m.QTYPE_TRANSLATE) is False
    assert m.validate_answer("caf\u00e9", "caf\u00e9", m.QTYPE_TRANSLATE) is True


# --------------------------------------------------------------------------
# _validate_numeric tolerance -- the arithmetic comparison band (ADR-007 path)
# tolerance None/0 means exact; a positive tolerance is an INCLUSIVE absolute
# band (<=); a malformed tolerance degrades to exact rather than raising.
# This is the path the property test does not cover (it tests generation, not
# answer comparison).
# --------------------------------------------------------------------------
def test_tolerance_none_requires_exact(m):
    assert m.validate_answer("10", "10.0", m.QTYPE_ARITHMETIC) is True
    assert m.validate_answer("10", "10.1", m.QTYPE_ARITHMETIC) is False


def test_tolerance_band_is_inclusive(m):
    # A difference exactly equal to the tolerance is accepted (<=, not <).
    assert m.validate_answer("10", "10.5", m.QTYPE_ARITHMETIC, tolerance=0.5) is True


def test_tolerance_just_outside_band_is_wrong(m):
    assert m.validate_answer("10", "10.6", m.QTYPE_ARITHMETIC, tolerance=0.5) is False


def test_tolerance_zero_is_exact(m):
    assert m.validate_answer("10", "10.0", m.QTYPE_ARITHMETIC, tolerance=0) is True
    assert m.validate_answer("10", "10.1", m.QTYPE_ARITHMETIC, tolerance=0) is False


def test_malformed_tolerance_degrades_to_exact(m):
    # A stray non-numeric tolerance from a client must not crash the
    # validator; it falls back to exact-match.
    assert (
        m.validate_answer("10", "10.1", m.QTYPE_ARITHMETIC, tolerance="oops") is False
    )
    assert m.validate_answer("10", "10.0", m.QTYPE_ARITHMETIC, tolerance="oops") is True


def test_non_numeric_given_is_wrong_not_error(m):
    # Letters typed for a math question are simply incorrect, never an error.
    assert m.validate_answer("13", "abc", m.QTYPE_ARITHMETIC) is False


# --------------------------------------------------------------------------
# build_question_payload -- hints forwarding (Thread N.1)
# --------------------------------------------------------------------------
# The payload is the client-facing question shape. Thread N.1 adds `hints`:
# questions store a hint LIST (imported per question); it was never forwarded
# before. Additive + display-only -- it never feeds validate_answer's grading.
def _bank_question(**overrides):
    # Minimal stored-question dict as db row conversion produces it. The four
    # required keys (qtype, question, answer, id) must be present; the rest are
    # optional and default the way build_question_payload expects.
    q = {
        "qtype": "translate",
        "question": "hola",
        "answer": "hello",
        "id": 7,
    }
    q.update(overrides)
    return q


def test_payload_forwards_hints_when_present(m):
    payload = m.build_question_payload(
        _bank_question(hints=["starts with h", "a greeting"])
    )
    assert payload["hints"] == ["starts with h", "a greeting"]


def test_payload_hints_is_empty_list_when_absent(m):
    # A question with no hints key yields [] (not None, not missing), so the
    # client can test truthiness uniformly.
    payload = m.build_question_payload(_bank_question())
    assert payload["hints"] == []


def test_payload_hints_empty_list_stays_empty(m):
    payload = m.build_question_payload(_bank_question(hints=[]))
    assert payload["hints"] == []


def test_payload_single_hint_forwarded(m):
    # SPIKE 1 note: hints is a LIST at N (not N=1); the single-hint case must
    # still arrive as a one-element list, not a bare string.
    payload = m.build_question_payload(_bank_question(hints=["only clue"]))
    assert payload["hints"] == ["only clue"]
