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
from _support import load_drill  # noqa: E402

_M = load_drill()
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
