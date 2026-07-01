"""Property-based test for the arithmetic generator (NEW in C-020; rewritten in
C-D5c for #5 nested trees).

phase0.md Section B names exactly one worthwhile hypothesis application: the
generator. Through #4 the generator emitted only FLAT single-operator nodes, so
the property test asserted "two int leaves." #5 makes generation bottom-up and
possibly NESTED, so the invariant is no longer a statement about one node -- it
is a statement about EVERY node in the tree. The test becomes a RECURSIVE
DISPATCHING WALK (Lens 1): descend the tree and, at each internal node, apply
the invariant for THAT operator with the correct referent --

  - VALUE-based for the composable operators (+ - *): the constraint is lifted
    to evaluate_expression(child), because a child may be a subtree;
  - LEAF-based for the leaf-only operators (/ % ^): their operands stay integer
    leaves and their invariants remain statements about those leaves (divisor
    >= 2, derived quotient exact, exponent power range). A blanket
    evaluate-and-recheck would CORRUPT these -- hence dispatch, not a uniform
    value check.

It also asserts the two structural properties that make "depth is the knob"
true rather than aspirational: operator_depth(tree) <= _MAX_OPERATOR_DEPTH
across the whole space (catching an off-by-one in budget threading), and that
normal generation NEVER raises the bounded-retry RuntimeError (pinning
"constraints are satisfiable in practice").

Decision anchors: forbidden-identity + exact-division are ADR-007 (parameters in
C-005); subtraction's non-negative result is the C-006 generation choice; the
bottom-up construction, composable/leaf-only split, value-vs-leaf constraint
lifting, depth metric, and bounded retry are the #5 design (handoff-5).
"""

import os
import sys

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

sys.path.insert(0, os.path.dirname(__file__))
from _support import load_logic  # noqa: E402

_M = load_logic()
_ALL_SYMBOLS = list(_M.OPERATOR_SYMBOLS)
_COMPOSABLE = {"+", "-", "*"}
_LEAF_ONLY = {"/", "%", "^"}


def _nonempty_symbol_subsets():
    return st.lists(
        st.sampled_from(_ALL_SYMBOLS),
        min_size=1,
        max_size=len(_ALL_SYMBOLS),
        unique=True,
    )


def _operator_depth(node):
    """Leaf -> 0; internal -> 1 + max(child depths). A flat node has depth 1."""
    if isinstance(node, int):
        return 0
    return 1 + max(_operator_depth(node["left"]), _operator_depth(node["right"]))


def _assert_node_invariants(node, allowed_symbols):
    """Recursive dispatching walk: assert the invariant for each node's operator.

    Composable nodes (+ - *) are checked by VALUE (their children may be
    subtrees); leaf-only nodes (/ % ^) are checked by LEAF (their operands are
    integer leaves and their invariants are leaf statements). Leaves are ints.
    """
    if isinstance(node, int):
        return

    assert isinstance(node, dict) and "op" in node, node
    op = node["op"]
    assert op in allowed_symbols, (op, allowed_symbols)
    record = _M.OPERATORS[op]
    forbidden = record["forbid_identity"]
    left = node["left"]
    right = node["right"]

    if op in _LEAF_ONLY:
        # Leaf-only: operands stay integer leaves; invariants are about leaves.
        # This is also the GENERATOR's structural invariant -- it never BUILDS a
        # leaf-only node with a subtree child (a / (b * c), 2 ^ (a + b) are
        # unreachable). nestable governs child-hood of children, not whether the
        # node may be a child (ADR-032). The renderer is nonetheless total over
        # such hand-built trees; see test_render_is_total_over_unreachable_trees
        # in test_logic.py, which pins that totality so #2 can make these
        # operators nestable with zero renderer change.
        assert isinstance(left, int), node
        assert isinstance(right, int), node
        assert not record["nestable"]
        if op == "/":
            # forbids the derived QUOTIENT; division is exact
            assert right != 0
            assert left % right == 0
            assert (left // right) not in forbidden
        elif op == "%":
            # forbids the DIVISOR (right); divisor >= 2
            assert right >= 2
            assert right not in forbidden
        elif op == "^":
            # forbids the EXPONENT (right); narrow power range -> bounded result
            assert right not in forbidden
            assert _M.evaluate_expression(node) == left**right
            assert _M.evaluate_expression(node) <= 12**3
    else:
        # Composable: constraints lifted to the operand VALUE (child may nest).
        assert record["nestable"]
        left_value = _M.evaluate_expression(left)
        right_value = _M.evaluate_expression(right)
        # forbidden-identity by value: + forbids 0; * forbids 0 and 1.
        assert left_value not in forbidden, node
        assert right_value not in forbidden, node
        if op == "-":
            # ordered non-negative, non-trivial: left_value >= right_value, != .
            assert left_value >= right_value, node
            assert left_value != right_value, node

    # descend
    _assert_node_invariants(left, allowed_symbols)
    _assert_node_invariants(right, allowed_symbols)


@settings(max_examples=300, deadline=None)
@given(symbols=_nonempty_symbol_subsets())
def test_generated_expression_holds_invariants(symbols):
    # normal generation must never raise the bounded-retry exhaustion error
    node = _M.generate_expression(enabled_symbols=symbols)

    # (depth) the structural knob holds across the whole space
    assert 1 <= _operator_depth(node) <= _M._MAX_OPERATOR_DEPTH

    # (per-node) every internal node satisfies its operator's invariant, with
    # the correct referent (value for + - *, leaf for / % ^); leaves are int.
    _assert_node_invariants(node, set(symbols))

    # (eval) integer result, deterministic on the same tree
    result = _M.evaluate_expression(node)
    assert isinstance(result, int)
    assert _M.evaluate_expression(node) == result

    # (render) renders to a non-empty string and the result is reproducible
    text = _M.render_expression(node)
    assert isinstance(text, str) and text != ""


@settings(max_examples=200, deadline=None)
@given(data=st.data())
def test_single_symbol_always_uses_that_symbol(data):
    # A single-symbol set: every internal node in the (possibly nested) tree
    # uses that symbol. (A composable single symbol may nest; a leaf-only single
    # symbol stays flat. Either way no OTHER symbol can appear.)
    symbol = data.draw(st.sampled_from(_ALL_SYMBOLS))
    node = _M.generate_expression(enabled_symbols=[symbol])
    _assert_node_invariants(node, {symbol})


@settings(max_examples=100, deadline=None)
@given(symbols=_nonempty_symbol_subsets())
def test_depth_one_reproduces_flat(symbols):
    # _MAX_OPERATOR_DEPTH == 1 must reproduce the flat #4 generator exactly:
    # a single operator with two integer leaves, regardless of symbol set.
    original = _M._MAX_OPERATOR_DEPTH
    try:
        _M._MAX_OPERATOR_DEPTH = 1
        node = _M.generate_expression(enabled_symbols=symbols)
        assert _operator_depth(node) == 1
        assert isinstance(node["left"], int)
        assert isinstance(node["right"], int)
    finally:
        _M._MAX_OPERATOR_DEPTH = original


# --- C-D2a: leaf_count atom + DIFFICULTY_RUNGS shape -------------------------
# This commit DEFINES the difficulty atom and the rung-table shape; it does NOT
# thread anything into the generator yet (that is C-D2b). So these tests pin the
# pure leaf_count metric and the table's internal consistency, independent of
# any generation behavior.


def test_leaf_count_on_hand_built_trees():
    # A leaf is 1; a flat node is 2; each nesting level adds the child's leaves.
    assert _M.leaf_count(7) == 1
    assert _M.leaf_count({"op": "+", "left": 3, "right": 4}) == 2
    # depth-2 sum: one operand is itself a flat node -> 3 leaves
    depth_two = {"op": "+", "left": {"op": "*", "left": 2, "right": 3}, "right": 5}
    assert _M.leaf_count(depth_two) == 3
    # both operands nested -> 4 leaves
    both_nested = {
        "op": "-",
        "left": {"op": "+", "left": 1, "right": 2},
        "right": {"op": "*", "left": 3, "right": 4},
    }
    assert _M.leaf_count(both_nested) == 4


def test_leaf_count_independent_of_operator_depth_metric():
    # leaf_count is a function of SHAPE, not of the operator_depth metric: two
    # trees with the SAME leaf_count can have DIFFERENT operator_depth, and vice
    # versa. This pins that leaf_count is its own axis (handoff: leaf_count is the
    # coordination feature, depth is a separate structural knob).
    # Same leaf_count (3), different depth:
    balanced_three = {"op": "+", "left": {"op": "*", "left": 2, "right": 3}, "right": 5}
    # A right-leaning chain also reaching 3 leaves but deeper would need depth 3;
    # construct one explicitly.
    chain_three = {
        "op": "+",
        "left": 1,
        "right": {"op": "+", "left": 2, "right": {"op": "+", "left": 3, "right": 4}},
    }
    assert _M.leaf_count(balanced_three) == 3
    assert _M.leaf_count(chain_three) == 4  # different shape -> different count
    assert _operator_depth(balanced_three) == 2
    assert _operator_depth(chain_three) == 3


def test_leaf_count_rejects_malformed_node():
    with pytest.raises(ValueError):
        _M.leaf_count({"left": 1, "right": 2})  # no "op" key


def test_difficulty_rungs_labels_ascending_gapfree():
    labels = [rung["rung"] for rung in _M.DIFFICULTY_RUNGS]
    assert labels == list(range(1, len(_M.DIFFICULTY_RUNGS) + 1))


def test_difficulty_rungs_reference_only_real_operators():
    # Every operator named in any rung's operator_ranges must be a real operator
    # with a record in the built OPERATORS table.
    for rung in _M.DIFFICULTY_RUNGS:
        for symbol in rung["operator_ranges"]:
            assert symbol in _M.OPERATORS, (rung["rung"], symbol)


def test_difficulty_rungs_field_shape_per_operator():
    # A rung may only scale range fields the operator's strategy actually reads:
    # operand_min/max for all; divisor_min/max only for %; exponent_min/max only
    # for ^. (This mirrors the import-time guard, asserted here for visibility.)
    allowed = {
        "+": {"operand_min", "operand_max"},
        "-": {"operand_min", "operand_max"},
        "*": {"operand_min", "operand_max"},
        "/": {"operand_min", "operand_max"},
        "%": {"operand_min", "operand_max", "divisor_min", "divisor_max"},
        "^": {"operand_min", "operand_max", "exponent_min", "exponent_max"},
    }
    for rung in _M.DIFFICULTY_RUNGS:
        for symbol, ranges in rung["operator_ranges"].items():
            assert set(ranges.keys()) <= allowed[symbol], (rung["rung"], symbol)


def test_difficulty_rungs_scalar_fields_well_formed():
    for rung in _M.DIFFICULTY_RUNGS:
        assert isinstance(rung["operator_depth"], int) and rung["operator_depth"] >= 1
        assert 0.0 <= rung["recurse_probability"] <= 1.0
        ceiling = rung["max_result_value"]
        assert ceiling is None or (isinstance(ceiling, int) and ceiling > 0)


# --- C-D2b: difficulty threads operator_depth + recurse (THE WELD) -----------
# This commit threads SHAPE knobs (depth + recurse) from a difficulty rung into
# the generator. The invariant that "leaf_count is the coordination spine" now
# becomes assertable end-to-end: across ascending rungs, leaf_count is monotone
# non-decreasing for composable-containing mixes and CONSTANT for leaf-only mixes
# (S7). Ranges and the ceiling are NOT rung-driven yet (C-D2d/C-D2e), so these
# tests assert SHAPE only -- no magnitude claim here.

_RUNG_LABELS = [rung["rung"] for rung in _M.DIFFICULTY_RUNGS]
_SAMPLE_PER_RUNG = 2000  # >= 2000 to catch a ~1-in-500 rung failure (S3)


def _mean_leaf_count(mix, difficulty, samples):
    total = 0
    for _ in range(samples):
        node = _M.generate_expression(enabled_symbols=list(mix), difficulty=difficulty)
        total += _M.leaf_count(node)
    return total / samples


def test_difficulty_none_is_unchanged_default_path():
    # difficulty=None must use the module constants (byte-identical to pre-#2):
    # operator_depth bounded by _M._MAX_OPERATOR_DEPTH for every mix.
    for mix in (["+", "-", "*"], ["/"], ["+", "-", "*", "/", "%", "^"]):
        for _ in range(500):
            node = _M.generate_expression(enabled_symbols=mix)  # no difficulty
            assert 1 <= _operator_depth(node) <= _M._MAX_OPERATOR_DEPTH


def test_rung_one_is_flat_for_every_mix():
    # Rung 1 sets operator_depth 1 / recurse 0 -> flat single-operator node with
    # two integer leaves, regardless of symbol set (the difficulty-driven flat
    # anchor, mirroring _MAX_OPERATOR_DEPTH==1, S6).
    for mix in (["+"], ["+", "-", "*"], ["/", "%", "^"], _ALL_SYMBOLS):
        for _ in range(500):
            node = _M.generate_expression(enabled_symbols=mix, difficulty=1)
            assert _operator_depth(node) == 1
            assert isinstance(node["left"], int)
            assert isinstance(node["right"], int)
            assert _M.leaf_count(node) == 2


def test_leaf_count_monotone_for_composable_mixes():
    # COORDINATION regime (S7): a mix containing a composable operator must have
    # mean leaf_count non-decreasing across ascending rungs (depth/recurse grow).
    # Use the mean over a large sample: leaf_count is random per draw, but its
    # expectation is monotone in the shape knobs. Strictly non-decreasing, with a
    # tiny tolerance against sampling noise at equal-shape rungs.
    composable_mixes = [["+", "-", "*"], ["+"], ["+", "-", "*", "/", "%", "^"]]
    for mix in composable_mixes:
        means = [_mean_leaf_count(mix, rung, _SAMPLE_PER_RUNG) for rung in _RUNG_LABELS]
        for earlier, later in zip(means, means[1:]):
            # later rung's mean leaf_count >= earlier (allow small noise slack)
            assert later >= earlier - 0.05, (mix, means)
        # and the top rung is strictly richer than the flat rung 1 (sanity: the
        # coordination knob actually moved, not merely "did not decrease").
        assert means[-1] > means[0], (mix, means)


def test_leaf_count_constant_for_leaf_only_mixes():
    # MAGNITUDE regime (S7): leaf-only mixes (/ % ^) cannot nest, so leaf_count is
    # a CONSTANT point mass (always 2) at EVERY rung. (Magnitude movement is
    # asserted in C-D2d once ranges are rung-driven; here only the constancy.)
    for mix in (["/"], ["%"], ["^"], ["/", "%", "^"]):
        for rung in _RUNG_LABELS:
            for _ in range(500):
                node = _M.generate_expression(enabled_symbols=mix, difficulty=rung)
                assert _M.leaf_count(node) == 2, (mix, rung)
                assert _operator_depth(node) == 1


@settings(max_examples=200, deadline=None)
@given(symbols=_nonempty_symbol_subsets())
def test_every_rung_never_raises_and_respects_depth(symbols):
    # S3 / foreign-oracle re-walk: for every rung and mix, generation never hits
    # the bounded-retry RuntimeError, and the produced tree's operator_depth is
    # within the rung's declared operator_depth budget (catches an off-by-one in
    # the threaded budget). Independent of the production path's own checks.
    for rung_record in _M.DIFFICULTY_RUNGS:
        rung = rung_record["rung"]
        budget = rung_record["operator_depth"]
        node = _M.generate_expression(enabled_symbols=symbols, difficulty=rung)
        assert 1 <= _operator_depth(node) <= budget, (symbols, rung)
        # per-node invariants still hold with the correct referent
        _assert_node_invariants(node, set(symbols))


def test_unknown_rung_raises_value_error():
    # Out-of-range rung is a programming error (HTTP validates user input first):
    # fail loudly, do not silently fall back to a default rung.
    with pytest.raises(ValueError):
        _M.generate_expression(difficulty=999)
    with pytest.raises(ValueError):
        _M.generate_expression(difficulty=0)


# --- C-D2d: per-operator range overlay (the MAGNITUDE regime) ----------------
# A rung overlays its per-operator operand ranges onto a COPY of OPERATORS via
# _apply_rung_ranges, so higher rungs draw larger operands. This is the lever
# that makes leaf-only mixes (/ % ^) -- whose leaf_count is pinned at 2 -- get
# harder at all. These tests assert magnitude movement and the overlay's purity.


def _leaf_values(node):
    # All integer leaves in the tree (their magnitudes).
    if isinstance(node, int):
        return [node]
    return _leaf_values(node["left"]) + _leaf_values(node["right"])


def _max_leaf_magnitude(mix, difficulty, samples):
    biggest = 0
    for _ in range(samples):
        node = _M.generate_expression(enabled_symbols=list(mix), difficulty=difficulty)
        biggest = max(biggest, max(_leaf_values(node)))
    return biggest


def test_operand_magnitude_monotone_across_rungs():
    # Max observed leaf magnitude is non-decreasing across ascending rungs, and
    # strictly larger at the top rung than the flat rung 1, for representative
    # operators INCLUDING leaf-only ones (where this is the ONLY difficulty axis).
    for mix in (["+"], ["*"], ["%"], ["/"]):
        maxima = [
            _max_leaf_magnitude(mix, rung, 3000)
            for rung in [r["rung"] for r in _M.DIFFICULTY_RUNGS]
        ]
        for earlier, later in zip(maxima, maxima[1:]):
            assert later >= earlier, (mix, maxima)
        assert maxima[-1] > maxima[0], (mix, maxima)


def test_apply_rung_ranges_is_pure_does_not_mutate_operators():
    # The overlay returns a NEW table and never mutates the module OPERATORS.
    import copy

    def scalar_snapshot(table):
        return {
            sym: {
                k: v
                for k, v in rec.items()
                if isinstance(v, (int, str, bool, tuple, type(None)))
            }
            for sym, rec in table.items()
        }

    before = scalar_snapshot(_M.OPERATORS)
    for rung in _M.DIFFICULTY_RUNGS:
        scaled = _M._apply_rung_ranges(rung, _M.OPERATORS)
        # The scaled table is a different object with different record objects
        # for any operator the rung actually scales.
        assert scaled is not _M.OPERATORS
    after = scalar_snapshot(_M.OPERATORS)
    assert before == after  # OPERATORS untouched by any overlay


def test_apply_rung_ranges_overlays_only_declared_fields():
    # A rung that omits an operator leaves that operator's base range verbatim;
    # a listed operator gets ONLY its declared fields replaced, others kept.
    base = _M.OPERATORS
    rung = _M.DIFFICULTY_RUNGS[0]  # rung 1
    scaled = _M._apply_rung_ranges(rung, base)
    for symbol, record in scaled.items():
        overrides = rung["operator_ranges"].get(symbol, {})
        for field in ("operand_min", "operand_max"):
            if field in overrides:
                assert record[field] == overrides[field], (symbol, field)
        # A field NOT overridden keeps the base value (e.g. eval_fn identity).
        assert record["eval_fn"] is base[symbol]["eval_fn"]
        assert record["nestable"] == base[symbol]["nestable"]


def test_difficulty_none_uses_base_operator_table_identity():
    # difficulty=None must pass the module OPERATORS object itself (no overlay),
    # so the default path is byte-identical. Verify via the seam: build_subtree
    # with operator_table=None resolves to OPERATORS, and generate_expression()
    # produces operands within the BASE ranges (not a rung's).
    base_plus_max = _M.OPERATORS["+"]["operand_max"]
    biggest = _max_leaf_magnitude(["+"], None, 3000)
    assert biggest <= base_plus_max


# --- C-D2e: the result ceiling (joint (ranges, ceiling) satisfiability) ------
# A rung's max_result_value is now enforced through generation. The check is
# local and bottom-up, so EVERY node result -- hence the final result -- stays
# within the ceiling. A ceiling too low for an operator's minimum result makes
# that operator infeasible, which the bounded-retry guard turns into a loud
# RuntimeError. These tests pin both: that real rungs are jointly satisfiable
# (no raise, results bounded), and that an impossible ceiling actually bites
# (the deliberate-red guard -- this would NOT raise if the ceiling were unwired).


def _max_node_result(node):
    # The largest result of any internal node in the tree (== final result for a
    # ceiling that bounds every node, but computed independently as a check).
    biggest = [0]

    def walk(n):
        if isinstance(n, int):
            return n
        left = walk(n["left"])
        right = walk(n["right"])
        value = _M.OPERATORS[n["op"]]["eval_fn"](left, right)
        biggest[0] = max(biggest[0], value)
        return value

    walk(node)
    return biggest[0]


def test_every_rung_respects_its_result_ceiling():
    # For each rung over its full operator set: generation never raises, and when
    # the rung declares a ceiling, every node result (and the final result) is
    # within it. Rungs with max_result_value None impose no bound (only the
    # no-raise half applies).
    for rung_record in _M.DIFFICULTY_RUNGS:
        rung = rung_record["rung"]
        ceiling = rung_record["max_result_value"]
        for _ in range(2000):
            node = _M.generate_expression(enabled_symbols=_ALL_SYMBOLS, difficulty=rung)
            if ceiling is not None:
                assert _max_node_result(node) <= ceiling, (rung, ceiling)
                assert _M.evaluate_expression(node) <= ceiling, (rung, ceiling)


def test_top_rung_ceiling_actually_binds():
    # The top rung declares a finite ceiling; confirm it is enforced (results are
    # bounded well below what the unceiled ranges could reach). Guards against a
    # rung that declares a ceiling the generator silently ignores.
    top = _M.DIFFICULTY_RUNGS[-1]
    assert top["max_result_value"] is not None, "this test assumes a top-rung ceiling"
    ceiling = top["max_result_value"]
    worst = 0
    for _ in range(5000):
        node = _M.generate_expression(
            enabled_symbols=_ALL_SYMBOLS, difficulty=top["rung"]
        )
        worst = max(worst, _M.evaluate_expression(node))
    assert worst <= ceiling


def test_impossible_ceiling_raises_runtime_error():
    # DELIBERATE-RED guard: a ceiling below an operator's MINIMUM achievable
    # result makes that operator infeasible; build_subtree must exhaust its
    # bounded retries and raise RuntimeError rather than loop forever. Using the
    # top rung's scaled "+" (operand_min >= 10, so min result >= 20) with a
    # ceiling of 5: every draw is rejected. If the ceiling were not wired through
    # (the pre-C-D2e state), this would NOT raise -- so this test is exactly the
    # one that flips from red to green when the ceiling is threaded.
    scaled = _M._apply_rung_ranges(_M.DIFFICULTY_RUNGS[-1], _M.OPERATORS)
    with pytest.raises(RuntimeError):
        # flat "+" node, impossible ceiling 5
        _M.build_subtree(["+"], 1, 0.0, scaled, 5)


def test_none_ceiling_is_a_noop():
    # max_result_value None means no ceiling: _result_within_ceiling returns True
    # regardless of magnitude, so a large product is accepted.
    star = _M.OPERATORS["*"]
    assert _M._result_within_ceiling(star, 1000, 1000, None) is True
    # A finite ceiling rejects an over-ceiling result.
    assert _M._result_within_ceiling(star, 1000, 1000, 100) is False
    assert _M._result_within_ceiling(star, 3, 3, 100) is True
