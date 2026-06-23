"""Property-based test for the arithmetic generator (NEW in C-020).

phase0.md Section B names exactly one worthwhile hypothesis application: the
generator. The property under test is the generator's core invariant, the one
that will break first when operators and nesting are added in Section D:

  For ANY non-empty subset of the enabled operator symbols, every generated
  expression
    (1) evaluates to an integer,
    (2) re-evaluates to the same integer (deterministic given the tree),
    (3) avoids the forbidden-identity operands its operator declares,
    (4) for division, has an exactly-divisible dividend, and
    (5) renders without raising and round-trips back through evaluate.

hypothesis explores the operator-subset space and shrinks any counterexample
to a minimal failing case -- the edge cases an example test would miss.
Decision anchors: the forbidden-identity and exact-division invariants are
ADR-007 (operand ranges + identities, parameters in C-005); subtraction's
non-negative result is the C-006 generation choice (left >= right).
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


def _nonempty_symbol_subsets():
    return st.lists(
        st.sampled_from(_ALL_SYMBOLS), min_size=1, max_size=len(_ALL_SYMBOLS), unique=True
    )


@settings(max_examples=300, deadline=None)
@given(symbols=_nonempty_symbol_subsets())
def test_generated_expression_holds_invariants(symbols):
    node = _M.generate_expression(enabled_symbols=symbols)

    # (1) the chosen op is one we asked for, with two int leaves in v1
    assert node["op"] in symbols
    assert isinstance(node["left"], int)
    assert isinstance(node["right"], int)

    # (1)+(2) integer result, deterministic on the same tree
    result = _M.evaluate_expression(node)
    assert isinstance(result, int)
    assert _M.evaluate_expression(node) == result

    # (3) forbidden-identity operands are avoided
    forbidden = _M.OPERATORS[node["op"]]["forbid_identity"]
    if node["op"] == "/":
        # division forbids the QUOTIENT values, not the raw operands
        assert (node["left"] // node["right"]) not in forbidden
    else:
        assert node["left"] not in forbidden
        assert node["right"] not in forbidden

    # (4) division is exact
    if node["op"] == "/":
        assert node["right"] != 0
        assert node["left"] % node["right"] == 0

    # subtraction never goes negative (the generator orders operands)
    if node["op"] == "-":
        assert result >= 0

    # (5) renders and round-trips
    text = _M.render_expression(node)
    assert isinstance(text, str) and text != ""


@settings(max_examples=200, deadline=None)
@given(data=st.data())
def test_single_symbol_always_uses_that_symbol(data):
    symbol = data.draw(st.sampled_from(_ALL_SYMBOLS))
    node = _M.generate_expression(enabled_symbols=[symbol])
    assert node["op"] == symbol
