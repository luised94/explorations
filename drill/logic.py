"""LOGIC layer -- pure functions, no IO/DB/HTTP/clock (D3 extraction).

Pure functions of plain data (numbers, strings, dicts, lists) returning plain
data. Randomness is the one tolerated impurity (generation draws from `random`,
which the spec's generator inherently requires). This layer sits above db:
config <- db <- logic <- http; main wires. logic imports ONLY config
(down-stack) plus stdlib. The boundary-purity guard now enforces this per-file:
a clock/DB call landing here reddens the suite immediately.

TWO internal sections, separated by `# === ... ===` banners:

  1. ARITHMETIC ENGINE -- the operator table + expression generation,
     evaluation, rendering, and difficulty-rung application. Self-contained: it
     is the arithmetic drill's own small DSL. Per the D-2 layering resolution
     the operator TABLE lives here (its records carry eval_fn/operand_strategy
     CALLABLES, so it is logic, not config -- S10b); config keeps only the scalar
     OPERATOR_SYMBOLS + operand-range knobs, which this section imports.

  2. GENERAL LOGIC -- validation, import parsing, stats summaries,
     next-question selection, and question-payload assembly.

The two sections have ZERO cross-references (measured), so the arithmetic
section is a clean future extraction into its own arithmetic.py if it ever earns
one; the `# === ARITHMETIC ENGINE ===` / `# === GENERAL LOGIC ===` banners mark
that seam. Kept as one module for now to avoid adding a file.

Behavior-preserving: every symbol is identical to its pre-split definition;
drill.py now imports these from here. The suite is the proof.
"""

from __future__ import annotations

import csv
import io
import json
import operator
import random
import re

from config import (
    DIFFICULTY_RUNGS,
    OPERATOR_SYMBOLS,
    QTYPE_ARITHMETIC,
    QTYPE_FREE_RESPONSE,
    QTYPE_IDENTIFY,
    QTYPE_MULTIPLE_CHOICE,
    QTYPE_TRANSLATE,
    QTYPES,
    _DEFAULT_OPERAND_RANGE,
    _EXPONENT_POWER_RANGE,
    _MAX_GENERATION_ATTEMPTS,
    _MAX_OPERATOR_DEPTH,
    _MAX_RESULT_VALUE,
    _MULTIPLICATIVE_OPERAND_RANGE,
    _RECURSE_PROBABILITY,
)


# === ARITHMETIC ENGINE =======================================================
# Self-contained arithmetic DSL: operator table + expression generate/evaluate/
# render + difficulty-rung application. Zero references to the GENERAL LOGIC
# section below; a clean future arithmetic.py extraction point.
# C-006: Operator table, expression generation, evaluation, rendering.
#
# The operator table combines the scalar config from CONFIG (C-005) with the
# callables defined here. Per the layering resolution, the callables live in
# LOGIC and the table is assembled here, once, as a module-level constant.
#
# Expression tree shape (spec section 4.3, runtime only -- never stored):
#   internal node: {"op": str, "left": node, "right": node}
#   leaf:          a plain int
# A node's "op" is an operator symbol; left and right are themselves nodes
# or int leaves, allowing nested expressions.


# Operand-generation strategies. Each takes the operator's record and returns
# a (left, right) pair. A strategy OWNS its forbidden-identity referent -- i.e.
# what forbid_identity is checked against -- and declares it via the record's
# forbid_identity_referent field, so a new operator cannot silently inherit
# the wrong meaning. (forbid_identity historically meant raw operands for the
# standard strategy but the derived quotient for division; that ambiguity is
# now explicit in the record, not implicit in which strategy reads it.)


def _generate_operands_standard(
    operator_record: dict,
) -> tuple[int, int]:
    """Generate a (left, right) operand pair for a non-division operator.

    Draws both operands from the record's inclusive [operand_min, operand_max]
    range and rejects pairs whose RAW OPERANDS hit a forbidden-identity value
    (forbid_identity_referent == "operands", ADR-007).

    When the record declares result_constraint == "non_negative" (subtraction),
    the strategy enforces that ONE intent with both its mechanics together:
    it orders the operands so left >= right (result never negative) AND rejects
    equal operands (x - x = 0 is the trivial result). Declaring the invariant
    rather than two independent knobs prevents a future editor from setting
    them inconsistently (e.g. ordering without equal-rejection, leaking 0).
    Rejection-resamples until a valid pair is found.
    """
    minimum = operator_record["operand_min"]
    maximum = operator_record["operand_max"]
    forbidden = operator_record["forbid_identity"]
    non_negative = operator_record.get("result_constraint") == "non_negative"
    while True:
        left_value = random.randint(minimum, maximum)
        right_value = random.randint(minimum, maximum)
        if non_negative and left_value < right_value:
            left_value, right_value = right_value, left_value
        # Referent is the raw operands: reject if either is a forbidden
        # identity value.
        if left_value in forbidden or right_value in forbidden:
            continue
        # The non_negative intent also rejects equal operands, whose result
        # (0) is the trivial case for subtraction.
        if non_negative and left_value == right_value:
            continue
        return left_value, right_value


def _generate_operands_division(
    operator_record: dict,
) -> tuple[int, int]:
    """Generate a (dividend, divisor) pair guaranteeing an integer quotient.

    Picks the divisor and quotient from the record's range, then derives the
    dividend as divisor * quotient (ADR-007). This guarantees exact division
    without post-hoc filtering. The forbidden-identity referent is the derived
    QUOTIENT (forbid_identity_referent == "quotient"): a quotient of 1 makes
    x / x, a trivial identity, so it is rejected.
    """
    minimum = operator_record["operand_min"]
    maximum = operator_record["operand_max"]
    forbidden = operator_record["forbid_identity"]
    while True:
        divisor = random.randint(minimum, maximum)
        quotient = random.randint(minimum, maximum)
        if quotient in forbidden:
            continue
        dividend = divisor * quotient
        return dividend, divisor


def _generate_operands_modulo(
    operator_record: dict,
) -> tuple[int, int]:
    """Generate a (left, divisor) pair for modulo.

    The left operand is drawn from the record's [operand_min, operand_max]
    range; the divisor is drawn from a SECOND range (divisor_min..divisor_max,
    >= 2) declared on the record. left < divisor IS allowed -- a % b == a is a
    legitimate non-trivial case. The forbidden-identity referent is the DIVISOR
    (forbid_identity_referent == "divisor"): a divisor of 1 makes x % 1 == 0
    for every x, a trivial result, so it is rejected.
    """
    left_minimum = operator_record["operand_min"]
    left_maximum = operator_record["operand_max"]
    divisor_minimum = operator_record["divisor_min"]
    divisor_maximum = operator_record["divisor_max"]
    forbidden = operator_record["forbid_identity"]
    while True:
        left_value = random.randint(left_minimum, left_maximum)
        divisor = random.randint(divisor_minimum, divisor_maximum)
        if divisor in forbidden:
            continue
        return left_value, divisor


def _generate_operands_exponent(
    operator_record: dict,
) -> tuple[int, int]:
    """Generate a (base, exponent) pair for exponentiation.

    Mirrors the division strategy's two-range shape: the base is drawn from the
    record's [operand_min, operand_max] range, and the exponent from a SECOND
    narrow range (exponent_min..exponent_max) declared on the record, keeping
    results integer and UI-tractable. The forbidden-identity referent is the
    EXPONENT (forbid_identity_referent == "exponent"): exponent 0 (x^0 == 1)
    and exponent 1 (x^1 == x) are trivial, so both are rejected.
    """
    base_minimum = operator_record["operand_min"]
    base_maximum = operator_record["operand_max"]
    exponent_minimum = operator_record["exponent_min"]
    exponent_maximum = operator_record["exponent_max"]
    forbidden = operator_record["forbid_identity"]
    while True:
        base = random.randint(base_minimum, base_maximum)
        exponent = random.randint(exponent_minimum, exponent_maximum)
        if exponent in forbidden:
            continue
        return base, exponent


# Per-operator records. One record fully defines an operator: the earlier
# split across OPERATOR_CONFIG + _OPERATOR_EVAL_FUNCTIONS +
# _OPERATOR_OPERAND_GENERATORS plus hidden `if symbol == "-"` branches is
# collapsed here, removing the symbol-string-as-foreign-key join.
#
# Record fields:
#   symbol      -- rendered operator string; also the table key
#   name        -- human-readable operator name
#   arity       -- operand count (all current operators binary)
#   operand_min, operand_max -- inclusive operand range (interpreted by the
#                  strategy; division treats it as the divisor/quotient range)
#   forbid_identity -- values rejected at generation to avoid trivial results
#                  (ADR-007)
#   forbid_identity_referent -- WHAT forbid_identity is checked against:
#                  "operands" (raw operands), "quotient" (derived, division),
#                  "divisor" (modulo), or "exponent" (the power). Each strategy
#                  declares its own; see strategy docstrings.
#   result_constraint -- declared invariant the strategy must uphold, or None.
#                  "non_negative" (subtraction) bundles ordering + equal
#                  rejection as one intent.
#   nestable    -- whether this operator may have SUBTREE children (#5). True
#                  for the composable operators (+ - *); False for the leaf-only
#                  operators (/ % ^), whose operands stay integer leaves. NOTE:
#                  nestable governs whether an operator may have subtree
#                  CHILDREN; it does NOT govern whether the operator's node may
#                  itself BE a child -- a / % ^ node is a valid subtree child of
#                  a composable parent.
#   precedence  -- explicit integer binding tier (#5): + - => 1, * / % => 2,
#                  ^ => 3. Compared with < by the renderer to decide
#                  parenthesization. Represented, not inferred from list order.
#   associativity -- "left" or "right" (#5): + - * / % are left-associative;
#                  ^ is right-associative. Drives same-tier wrong-side
#                  parenthesization in the renderer.
#   eval_fn     -- stdlib operator callable; full namespace, no alias
#   operand_strategy -- the generator producing this operator's operand pair
# Some operators carry a SECOND range as extra record fields read only by their
# own strategy (not a generic override -- see the per-operand-range decision):
#   modulo:   divisor_min, divisor_max  (the divisor's range, >= 2)
#   exponent: exponent_min, exponent_max  (the power's range)
OPERATOR_DEFINITIONS: list[dict] = [
    {
        "symbol": "+",
        "name": "addition",
        "arity": 2,
        "operand_min": _DEFAULT_OPERAND_RANGE[0],
        "operand_max": _DEFAULT_OPERAND_RANGE[1],
        "forbid_identity": [0],
        "forbid_identity_referent": "operands",
        "result_constraint": None,
        "nestable": True,
        "precedence": 1,
        "associativity": "left",
        "eval_fn": operator.add,
        "operand_strategy": _generate_operands_standard,
    },
    {
        "symbol": "-",
        "name": "subtraction",
        "arity": 2,
        "operand_min": _DEFAULT_OPERAND_RANGE[0],
        "operand_max": _DEFAULT_OPERAND_RANGE[1],
        "forbid_identity": [0],
        "forbid_identity_referent": "operands",
        # One intent: non-negative, non-trivial result. The standard strategy
        # implements both mechanics (order left >= right; reject equal).
        "result_constraint": "non_negative",
        "nestable": True,
        "precedence": 1,
        "associativity": "left",
        "eval_fn": operator.sub,
        "operand_strategy": _generate_operands_standard,
    },
    {
        "symbol": "*",
        "name": "multiplication",
        "arity": 2,
        "operand_min": _MULTIPLICATIVE_OPERAND_RANGE[0],
        "operand_max": _MULTIPLICATIVE_OPERAND_RANGE[1],
        "forbid_identity": [0, 1],
        "forbid_identity_referent": "operands",
        "result_constraint": None,
        "nestable": True,
        "precedence": 2,
        "associativity": "left",
        "eval_fn": operator.mul,
        "operand_strategy": _generate_operands_standard,
    },
    {
        "symbol": "/",
        "name": "division",
        "arity": 2,
        # The range bounds the divisor and quotient; the dividend is derived
        # as divisor * quotient (ADR-007). Range [2..12] matches the spec.
        "operand_min": _MULTIPLICATIVE_OPERAND_RANGE[0],
        "operand_max": _MULTIPLICATIVE_OPERAND_RANGE[1],
        "forbid_identity": [1],
        # Referent is the derived quotient, not the raw operands: a quotient
        # of 1 makes x / x, a trivial identity.
        "forbid_identity_referent": "quotient",
        "result_constraint": None,
        "nestable": False,
        "precedence": 2,
        "associativity": "left",
        # Floor division (operator.floordiv) is always EXACT here: the dividend
        # is a guaranteed multiple of the divisor (ADR-007), so there is no
        # remainder to floor away; the divisor is never zero (positive range).
        "eval_fn": operator.floordiv,
        "operand_strategy": _generate_operands_division,
    },
    {
        "symbol": "%",
        "name": "modulo",
        "arity": 2,
        # Left operand spans the default range; the divisor has its own range
        # (>= 2) below. left < divisor is allowed -- a % b == a is a valid,
        # non-trivial case.
        "operand_min": _DEFAULT_OPERAND_RANGE[0],
        "operand_max": _DEFAULT_OPERAND_RANGE[1],
        "divisor_min": _MULTIPLICATIVE_OPERAND_RANGE[0],
        "divisor_max": _MULTIPLICATIVE_OPERAND_RANGE[1],
        "forbid_identity": [1],
        # Referent is the divisor: a divisor of 1 makes x % 1 == 0 for every x.
        "forbid_identity_referent": "divisor",
        "result_constraint": None,
        "nestable": False,
        "precedence": 2,
        "associativity": "left",
        "eval_fn": operator.mod,
        "operand_strategy": _generate_operands_modulo,
    },
    {
        "symbol": "^",
        "name": "exponent",
        "arity": 2,
        # Base from the multiplicative range; the power from its own narrow
        # range (_EXPONENT_POWER_RANGE) below, keeping results UI-tractable.
        "operand_min": _MULTIPLICATIVE_OPERAND_RANGE[0],
        "operand_max": _MULTIPLICATIVE_OPERAND_RANGE[1],
        "exponent_min": _EXPONENT_POWER_RANGE[0],
        "exponent_max": _EXPONENT_POWER_RANGE[1],
        "forbid_identity": [0, 1],
        # Referent is the exponent: x^0 == 1 and x^1 == x are trivial.
        "forbid_identity_referent": "exponent",
        "result_constraint": None,
        "nestable": False,
        "precedence": 3,
        "associativity": "right",
        # Right-associativity (2^2^3) is a #5 concern; the flat v1 generator
        # never associates, so it is a non-issue here.
        "eval_fn": operator.pow,
        "operand_strategy": _generate_operands_exponent,
    },
]

# Required keys every record must carry; _build_operator_table validates
# completeness against this set rather than re-joining separate structures.
_OPERATOR_RECORD_REQUIRED_KEYS = frozenset(
    {
        "symbol",
        "name",
        "arity",
        "operand_min",
        "operand_max",
        "forbid_identity",
        "forbid_identity_referent",
        "result_constraint",
        "nestable",
        "precedence",
        "associativity",
        "eval_fn",
        "operand_strategy",
    }
)

# Known forbid-identity referents; a record declaring anything else is a typo
# or an unimplemented strategy contract.
_KNOWN_FORBID_IDENTITY_REFERENTS = frozenset(
    {"operands", "quotient", "divisor", "exponent"}
)


def _build_operator_table() -> dict:
    """Index OPERATOR_DEFINITIONS by symbol, validating record completeness.

    Returns a dict mapping each operator symbol to its record. Because each
    record is now self-contained, this no longer joins four structures; it
    validates that every record is COMPLETE (all required keys present, eval_fn
    and operand_strategy callable, referent known) and that every enabled
    symbol in OPERATOR_SYMBOLS has a record. Raises ValueError at import time
    on any failure -- catching typos early rather than at request time.
    """
    table: dict = {}
    for record in OPERATOR_DEFINITIONS:
        missing = _OPERATOR_RECORD_REQUIRED_KEYS - record.keys()
        if missing:
            raise ValueError(
                "operator record "
                + repr(record.get("symbol", "<no symbol>"))
                + " is missing required keys: "
                + ", ".join(sorted(missing))
            )
        symbol = record["symbol"]
        if not callable(record["eval_fn"]):
            raise ValueError(
                "operator record " + repr(symbol) + " has a non-callable eval_fn"
            )
        if not callable(record["operand_strategy"]):
            raise ValueError(
                "operator record "
                + repr(symbol)
                + " has a non-callable operand_strategy"
            )
        if record["forbid_identity_referent"] not in _KNOWN_FORBID_IDENTITY_REFERENTS:
            raise ValueError(
                "operator record "
                + repr(symbol)
                + " has unknown forbid_identity_referent "
                + repr(record["forbid_identity_referent"])
            )
        if symbol in table:
            raise ValueError("duplicate operator record for symbol " + repr(symbol))
        table[symbol] = record

    for symbol in OPERATOR_SYMBOLS:
        if symbol not in table:
            raise ValueError(
                "enabled operator symbol "
                + repr(symbol)
                + " has no record in OPERATOR_DEFINITIONS"
            )
    return table


# Built once at import. Module-level constant; not rebuilt per request.
OPERATORS: dict = _build_operator_table()


def _draw_composable_leaf(operator_record: dict) -> int:
    """Draw a single integer leaf for a composable operator's operand.

    Bottom-up construction builds each operand of a composable (+ - *) node
    INDEPENDENTLY, so it needs a single-operand draw rather than the paired
    leaf strategy (which bakes in ordering/forbid logic for the flat case). The
    leaf is drawn from the operator's own [operand_min, operand_max] range; the
    forbidden-identity and ordering rules are applied UNIFORMLY afterward by the
    caller against the operand's VALUE (a leaf is its own value), so they cover
    subtree operands too. The composable leaf ranges already start above their
    forbidden values (+ - from 1, * from 2), so a leaf never hits a forbidden
    identity on its own -- the value check only ever rejects a SUBTREE operand
    that happens to evaluate to a forbidden value (e.g. (9 % 3) == 0 under +).
    """
    return random.randint(
        operator_record["operand_min"], operator_record["operand_max"]
    )


def _build_composable_operand(
    symbols: list[str],
    remaining_depth: int,
    operator_record: dict,
    recurse_probability: float,
    operator_table: dict,
    max_result_value: int | None,
) -> dict | int:
    """Build ONE operand of a composable node: a subtree or an integer leaf.

    With depth budget remaining (remaining_depth >= 2, so a child can be at
    least a flat node), flip an independent Bernoulli(recurse_probability): on
    success recurse into build_subtree with the budget decremented; otherwise
    draw an integer leaf. With no budget remaining, always a leaf -- this is the
    depth floor that bounds operator_depth at the caller's depth budget.

    C-D2b: recurse_probability is a PLAIN-DATA PARAMETER threaded from the caller.
    C-D2d: operator_table is threaded so a recursing subtree draws its own
    operator from the same (possibly rung-scaled) table the parent used.
    C-D2e: max_result_value is threaded onward to the recursing build_subtree so
    the whole tree enforces one consistent ceiling (a leaf never needs the
    ceiling -- a bare integer leaf is its own value and was drawn within range).
    """
    if remaining_depth >= 2 and random.random() < recurse_probability:
        return build_subtree(
            symbols,
            remaining_depth - 1,
            recurse_probability,
            operator_table,
            max_result_value,
        )
    return _draw_composable_leaf(operator_record)


def _result_within_ceiling(
    operator_record: dict,
    left_value: int,
    right_value: int,
    max_result_value: int | None,
) -> bool:
    """Local feasibility check for the optional result ceiling (C-D2e).

    Returns True (always feasible) when max_result_value is None -- the default
    (difficulty=None and the lower rungs that declare no ceiling), making this a
    no-op so the generator is identical to the no-ceiling version. Otherwise
    returns whether THIS node's evaluated result is within the ceiling.

    The check is LOCAL and bottom-up: both operand values are already in hand, so
    it evaluates only this node's operator over the two known child values, not
    the whole subtree again. Because a parent only ACCEPTS children whose own
    results already passed this same check, the local bound transitively bounds
    every subtree result -- so a tree assembled entirely from accepted nodes has
    every node result (hence the final result) within the ceiling. ADR-035: the
    ceiling bounds RESULTS, not leaves; operand magnitude is still governed by the
    per-operator ranges, so a too-small ceiling makes a node INFEASIBLE (it can
    never satisfy) rather than merely rare, which the bounded-retry guard turns
    into a loud RuntimeError instead of an infinite loop.

    C-D2e: max_result_value is now a PLAIN-DATA PARAMETER threaded from the
    caller (generate_expression passes the rung's max_result_value, or None on
    the no-rung path), replacing the read of the module-global _MAX_RESULT_VALUE.
    The module constant remains as the documented dark default but is no longer
    read here.
    """
    if max_result_value is None:
        return True
    return operator_record["eval_fn"](left_value, right_value) <= max_result_value


def build_subtree(
    symbols: list[str],
    remaining_depth: int,
    recurse_probability: float = _RECURSE_PROBABILITY,
    operator_table: dict | None = None,
    max_result_value: int | None = None,
) -> dict:
    """Build an expression subtree (an internal node) bottom-up.

    INTERNAL helper for generate_expression (#5). Calls random.* directly -- no
    rng parameter (threading an rng is speculative seedability; tests seed the
    global RNG instead). Returns an {op, left, right} node whose operator_depth
    is at most remaining_depth (>= 1).

    Construction is BOTTOM-UP: for a composable operator (+ - *), each operand
    is built first (subtree or leaf) so its integer VALUE is known, then the
    operator's constraints are checked against those values and the node is
    assembled -- a built subtree is never mutated to fit a parent; on a
    constraint failure the whole node is redrawn. Leaf-only operators (/ % ^)
    keep their existing paired leaf strategy unchanged (their invariants are
    statements about LEAVES -- divisor >= 2, derived quotient, exponent power
    range -- and must not be lifted to values). A leaf-only operator may still
    be CHOSEN here (it is a valid subtree child of a composable parent); it just
    never grows subtree children of its own (nestable=False).

    remaining_depth <= 1 forces a flat node: no operand recurses, reproducing
    the #4 generator exactly. Each redraw counts against _MAX_GENERATION_ATTEMPTS
    and raises RuntimeError on exhaustion rather than looping forever.

    C-D2b (THE WELD): recurse_probability is a PLAIN-DATA PARAMETER (door D1
    opened with its real caller, generate_expression). It defaults to the module
    constant _RECURSE_PROBABILITY so existing direct callers and the
    difficulty=None path are byte-identical to before; a difficulty rung passes
    the rung's recurse_probability instead. operator_depth is threaded as the
    EXISTING remaining_depth parameter (generate_expression chooses its starting
    value from the rung or the module _MAX_OPERATOR_DEPTH).

    C-D2d: operator_table is the (possibly rung-scaled) operator table to draw
    records from. None -> the module-global OPERATORS (the default ranges,
    byte-identical to before). generate_expression overlays a rung's per-operator
    ranges onto a COPY via _apply_rung_ranges and passes that table here, so a
    rung changes operand MAGNITUDE. The table is threaded onward to
    _build_composable_operand so recursing subtrees use the same scaled records.

    C-D2e: max_result_value is the rung's result ceiling (None -> no ceiling, the
    default and the lower rungs). Threaded into every _result_within_ceiling call
    and onward to recursing subtrees. Because the check is local and bottom-up
    and a parent only accepts ceiling-passing children, the whole tree's results
    stay within the ceiling. A ceiling too low for an operator's minimum result
    makes that operator infeasible; the bounded-retry guard then raises
    RuntimeError rather than looping (the joint (ranges, ceiling) satisfiability
    is asserted per rung in the C-D2e tests).
    """
    if operator_table is None:
        operator_table = OPERATORS
    attempts = 0
    while True:
        attempts += 1
        if attempts > _MAX_GENERATION_ATTEMPTS:
            raise RuntimeError(
                "build_subtree exceeded "
                + str(_MAX_GENERATION_ATTEMPTS)
                + " attempts; operator constraints appear unsatisfiable for "
                "symbols " + repr(symbols)
            )
        symbol = random.choice(symbols)
        operator_record = operator_table[symbol]

        # Leaf-only (/ % ^): integer leaves via the existing paired strategy,
        # invariants unchanged. Also the only path when no depth budget remains
        # for a composable operator (handled below by the leaf-only operand
        # builder), but a leaf-only operator takes this branch regardless.
        if not operator_record["nestable"]:
            left_value, right_value = operator_record["operand_strategy"](
                operator_record
            )
            if not _result_within_ceiling(
                operator_record, left_value, right_value, max_result_value
            ):
                continue
            return {"op": symbol, "left": left_value, "right": right_value}

        # Composable (+ - *). At the depth floor (remaining_depth <= 1) no
        # operand may recurse, so use the existing paired strategy verbatim --
        # this is what makes operator_depth == 1 reproduce flat #4 exactly.
        if remaining_depth <= 1:
            left_value, right_value = operator_record["operand_strategy"](
                operator_record
            )
            if not _result_within_ceiling(
                operator_record, left_value, right_value, max_result_value
            ):
                continue
            return {"op": symbol, "left": left_value, "right": right_value}

        # Budget remains: build each operand independently (subtree or leaf),
        # then apply the value-based constraints (constraint lifting). The
        # per-tree recurse_probability is threaded into each operand build.
        left = _build_composable_operand(
            symbols,
            remaining_depth,
            operator_record,
            recurse_probability,
            operator_table,
            max_result_value,
        )
        right = _build_composable_operand(
            symbols,
            remaining_depth,
            operator_record,
            recurse_probability,
            operator_table,
            max_result_value,
        )
        left_value = evaluate_expression(left)
        right_value = evaluate_expression(right)

        # Subtraction: order by EVALUATED value (left >= right) and reject equal
        # (result 0 is trivial). Swapping the operand POSITIONS is arrangement,
        # not mutation of a built node.
        if operator_record.get("result_constraint") == "non_negative":
            if left_value < right_value:
                left, right = right, left
                left_value, right_value = right_value, left_value
            if left_value == right_value:
                continue

        # Forbidden-identity lifted to VALUE for + (forbid 0) and * (forbid
        # 0 and 1): a * (subtree evaluating to 1) is the trivial identity.
        forbidden = operator_record["forbid_identity"]
        if left_value in forbidden or right_value in forbidden:
            continue

        # Optional result ceiling: redraw this node's operands if the assembled
        # result would exceed the ceiling. Local: only this node's children are
        # discarded, not the whole tree. None -> no ceiling (the default path).
        if not _result_within_ceiling(
            operator_record, left_value, right_value, max_result_value
        ):
            continue

        return {"op": symbol, "left": left, "right": right}


def _resolve_difficulty_rung(difficulty: int) -> dict:
    """Resolve a scalar difficulty rung to its DIFFICULTY_RUNGS record (C-D2b).

    Pure lookup by the rung label. Raises ValueError on an unknown rung -- this
    is a PROGRAMMING-ERROR guard, not user-input handling: the HTTP layer
    validates ?difficulty= against the known rung range and returns a 400 before
    calling generate_expression (mirroring how ?operators= is validated against
    OPERATORS up front). Reaching here with a bad rung therefore means an
    internal caller passed an out-of-range value, so fail loudly rather than
    silently falling back to a default rung.

    Returns the full rung record; in C-D2b only operator_depth and
    recurse_probability are CONSUMED (the shape knobs). operator_ranges and
    max_result_value are present on the record but not yet applied -- C-D2d and
    C-D2e wire those.
    """
    for rung_record in DIFFICULTY_RUNGS:
        if rung_record["rung"] == difficulty:
            return rung_record
    known = [rung_record["rung"] for rung_record in DIFFICULTY_RUNGS]
    raise ValueError(
        "unknown difficulty rung "
        + repr(difficulty)
        + "; known rungs are "
        + repr(known)
    )


def _apply_rung_ranges(rung_record: dict, base_table: dict) -> dict:
    """Overlay a rung's per-operator range fields onto a base operator table (C-D2d).

    PURE: returns a NEW operator table (a fresh dict of fresh record dicts);
    base_table and its records are never mutated, so the module-global OPERATORS
    stays the canonical default and is safe to reuse across requests. This is the
    magnitude lever -- the rung's operator_ranges replace ONLY the range fields
    each operator's strategy reads (operand_min/max for all; divisor_min/max for
    %; exponent_min/max for ^), leaving every other record field (eval_fn,
    operand_strategy, nestable, forbid_identity, precedence, ...) untouched. So
    the generator's behavior is identical except for the magnitudes it draws.

    A rung need not list every operator: an operator absent from operator_ranges
    keeps its base-table range verbatim (the rung "only states what it CHANGES",
    per the DIFFICULTY_RUNGS docstring). A field absent from a listed operator's
    range dict likewise keeps its base value -- the overlay is field-level, not
    record-replacement, so e.g. a rung that scales only operand_min/max for %
    leaves that operator's divisor_min/max at the base.

    The import-time guard (_check_difficulty_rungs_consistency) has already
    proven every declared field is one the operator legitimately reads, so this
    overlay never introduces a field a strategy ignores.
    """
    new_table = {}
    for symbol, base_record in base_table.items():
        overrides = rung_record["operator_ranges"].get(symbol)
        if not overrides:
            # Operator not scaled by this rung: reuse the base record as-is.
            # Safe because we never mutate records; the new table just points at
            # the same immutable-by-convention record object.
            new_table[symbol] = base_record
            continue
        # Field-level overlay onto a COPY, so the base record is untouched.
        scaled_record = dict(base_record)
        for field_name, field_value in overrides.items():
            scaled_record[field_name] = field_value
        new_table[symbol] = scaled_record
    return new_table


def generate_expression(
    enabled_symbols: list[str] | None = None,
    difficulty: int | None = None,
) -> dict:
    """Generate an arithmetic expression tree, possibly nested (#5, #2).

    Picks operators at random from enabled_symbols (defaulting to the module
    OPERATOR_SYMBOLS) and builds a tree bottom-up via build_subtree. Composable
    operators (+ - *) may have subtree children; leaf-only operators (/ % ^)
    keep integer leaves.

    DIFFICULTY (C-D2b): difficulty is an optional scalar rung. When None (the
    default), generation is BYTE-IDENTICAL to before -- it uses the module
    constants _MAX_OPERATOR_DEPTH and _RECURSE_PROBABILITY, so an existing caller
    that passes no difficulty (the no-parameter live endpoint path, Q6) sees no
    behavior change. When a rung is given, it is resolved against DIFFICULTY_RUNGS
    to per-rung operator_depth and recurse_probability, which are threaded as
    plain-data parameters into build_subtree (door D1, opened with its real
    caller per ADR-034). operator_depth == 1 reproduces the flat #4 generator
    exactly.

    SCOPE NOTE (C-D2e completes the generator response): a rung now changes tree
    depth, nesting probability, per-operator operand magnitude (C-D2d), AND
    applies its result ceiling (max_result_value) -- the full generator-side
    difficulty response. A rung with max_result_value None has no ceiling. The
    tree shape feeds evaluate_expression and render_expression unchanged.
    """
    # Distinguish "omitted" (None -> use the default set) from "given but
    # empty" ([] -> an error). Treating [] as falsy and silently falling back
    # to all operators would mask a caller that meant to restrict generation
    # and produced an empty set (e.g. a query string that parsed to no valid
    # symbols).
    symbols = OPERATOR_SYMBOLS if enabled_symbols is None else enabled_symbols
    if not symbols:
        raise ValueError("generate_expression requires at least one operator symbol")
    unknown = [symbol for symbol in symbols if symbol not in OPERATORS]
    if unknown:
        # A caller passed a symbol with no operator-table entry. HTTP already
        # validates ?operators= against OPERATORS, so reaching here means a
        # programming error rather than bad user input -- fail loudly.
        raise ValueError(
            "generate_expression got unknown operator symbols: "
            + ", ".join(repr(symbol) for symbol in unknown)
        )

    # difficulty=None: the module-constant defaults, byte-identical to today.
    # A rung: resolve to its shape knobs (depth + recurse), overlay its
    # per-operator ranges (magnitude, C-D2d), AND apply its result ceiling
    # (C-D2e). A rung whose max_result_value is None has no ceiling.
    if difficulty is None:
        operator_depth = _MAX_OPERATOR_DEPTH
        recurse_probability = _RECURSE_PROBABILITY
        operator_table = OPERATORS
        max_result_value = _MAX_RESULT_VALUE
    else:
        rung_record = _resolve_difficulty_rung(difficulty)
        operator_depth = rung_record["operator_depth"]
        recurse_probability = rung_record["recurse_probability"]
        operator_table = _apply_rung_ranges(rung_record, OPERATORS)
        max_result_value = rung_record["max_result_value"]

    return build_subtree(
        symbols, operator_depth, recurse_probability, operator_table, max_result_value
    )


def evaluate_expression(node: dict | int) -> int:
    """Evaluate an expression tree to an integer result.

    Recursively evaluates internal nodes by applying the operator's eval
    function to its evaluated operands; integer leaves return themselves.
    Pure and deterministic: the same tree always evaluates to the same
    result.
    """
    if isinstance(node, int):
        return node
    if not isinstance(node, dict) or "op" not in node:
        raise ValueError(
            "evaluate_expression expected an int leaf or an {op,left,right} "
            "node, got " + repr(node)
        )
    if node["op"] not in OPERATORS:
        raise ValueError("evaluate_expression got unknown operator " + repr(node["op"]))
    operator_record = OPERATORS[node["op"]]
    left_value = evaluate_expression(node["left"])
    right_value = evaluate_expression(node["right"])
    return operator_record["eval_fn"](left_value, right_value)


def leaf_count(node: dict | int) -> int:
    """Count the integer leaves in an expression tree (C-D2a, ADR-038).

    The structural difficulty proxy for the #2 model: an integer leaf is one
    minimal input the solver must hold, so leaf_count is the element-
    interactivity / minimal-input analog. A flat node (two int leaves) has
    leaf_count 2; each level of nesting adds leaves. It is a pure function of
    TREE SHAPE only -- it does not depend on operator_depth, operand magnitude,
    or which operators appear (a deep all-+ tree and a deep all-* tree of the
    same shape have the same leaf_count). That independence is exactly why it is
    the COORDINATION-regime feature (handoff Q1/S7): for composable-containing
    mixes it moves monotonically with the rung's depth/recurse knobs, while for
    leaf-only mixes (/ % ^, which cannot nest) it is a CONSTANT 2 and difficulty
    must ride magnitude instead.

    It is also the NON-DRIFTING fact stored on responses (ADR-040): recomputable
    from question_text by re-parsing, unlike the rung label, which re-means if a
    later thread re-tunes the rung table. Recurses over the same {op,left,right}
    shape as evaluate_expression; an int leaf is 1, an internal node is the sum
    of its children's leaf counts.
    """
    if isinstance(node, int):
        return 1
    if not isinstance(node, dict) or "op" not in node:
        raise ValueError(
            "leaf_count expected an int leaf or an {op,left,right} node, got "
            + repr(node)
        )
    return leaf_count(node["left"]) + leaf_count(node["right"])


def _child_needs_parentheses(parent_record: dict, child: dict | int, side: str) -> bool:
    """Decide whether a rendered child operand must be parenthesized.

    The renderer is the SOLE owner of correct printing (#5): the tree shape is
    the grouping truth, and the rendered string must, read under standard
    precedence and associativity, parse back to THIS tree. evaluate_expression
    never consults precedence -- a wrong parenthesization silently makes the
    displayed question and the stored answer disagree.

    A child is wrapped IFF it is an INTERNAL node AND either
      - its operator binds LESS tightly than the parent
        (child.precedence < parent.precedence), or
      - it binds EQUALLY tightly but sits on the associativity-WRONG side:
        the right child of a left-associative parent, or the left child of a
        right-associative parent. (On the associativity-correct side, equal
        precedence needs no parens: a - b + c is (a-b)+c with no wrapping.)
    An integer leaf is never wrapped.
    """
    if not isinstance(child, dict):
        return False
    child_record = OPERATORS[child["op"]]
    if child_record["precedence"] < parent_record["precedence"]:
        return True
    if child_record["precedence"] == parent_record["precedence"]:
        parent_associativity = parent_record["associativity"]
        wrong_side = "right" if parent_associativity == "left" else "left"
        if side == wrong_side:
            return True
    return False


def render_expression(node: dict | int) -> str:
    """Render an expression tree as a human-readable infix string.

    Integer leaves render as their digits. Internal nodes render as
    "left symbol right", with each child parenthesized only when the tree's
    grouping would otherwise be lost under standard precedence/associativity
    (see _child_needs_parentheses). A flat single-operator expression (the v1
    case) has int leaves, so it produces no parentheses. The rendered string is
    what gets stored in responses.question_text.
    """
    if isinstance(node, int):
        return str(node)
    parent_record = OPERATORS[node["op"]]
    left_text = render_expression(node["left"])
    right_text = render_expression(node["right"])
    if _child_needs_parentheses(parent_record, node["left"], "left"):
        left_text = "(" + left_text + ")"
    if _child_needs_parentheses(parent_record, node["right"], "right"):
        right_text = "(" + right_text + ")"
    return left_text + " " + node["op"] + " " + right_text


# === GENERAL LOGIC ===========================================================
# Validation, import parsing, stats summaries, next-question selection, and
# question-payload assembly. Zero references to the ARITHMETIC ENGINE section
# above; the two halves are independent (the arithmetic.py seam).

# C-007: Answer validation.
# Pure functions. Two public functions: normalize_text (the text
# normalization pipeline) and validate_answer (the dispatcher across qtypes).
# free_response, translate, and identify share one normalized-text path;
# multiple_choice does an exact comparison of server-generated strings;
# arithmetic parses the input as a number and compares within a tolerance.


# Punctuation stripped during normalization. Deliberately excludes hyphens
# and apostrophes: "well-known" vs "wellknown" and "don't" vs "dont" are
# real distinctions in vocabulary drills (decision in C-007 feedback).
_STRIP_PUNCTUATION = ",.!?:;"

# Quote and bracket characters stripped only from the outer edges of the
# text (surrounding quotes and parentheses), not from the interior.
_STRIP_OUTER_CHARACTERS = "\"'()"

# Matches any run of whitespace, for collapsing internal whitespace to a
# single space.
_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalize free-text for lenient answer comparison.

    Pipeline: lowercase; remove the defined interior punctuation set
    (commas, periods, exclamation/question marks, colons, semicolons);
    collapse internal whitespace runs to single spaces; trim outer
    whitespace; strip surrounding quotes and parentheses from the ends.

    Does NOT strip hyphens, apostrophes, or Unicode accents -- these carry
    meaning in language drills (decision in C-007 feedback). Accent
    sensitivity means an answer written with accents must be typed with
    them; a per-bank accent_insensitive flag is a possible future addition.
    """
    lowered = text.lower()
    without_punctuation = "".join(
        character for character in lowered if character not in _STRIP_PUNCTUATION
    )
    collapsed = _WHITESPACE_RUN.sub(" ", without_punctuation).strip()
    return collapsed.strip(_STRIP_OUTER_CHARACTERS).strip()


def _validate_numeric(given: str, expected: str, tolerance: float | None) -> bool:
    """Compare a numeric answer to the expected value within a tolerance.

    Parses both sides as floats. A tolerance of None (or 0) requires exact
    equality; a positive tolerance accepts answers within that absolute
    difference (for future float-producing operators). Non-numeric input
    (e.g. letters typed for a math question) is simply an incorrect answer,
    returning False rather than raising.

    A non-numeric tolerance (e.g. a stray string from a client) is treated as
    no tolerance (exact match) rather than raising, so a malformed optional
    field cannot crash the validator.
    """
    try:
        given_value = float(given.strip())
        expected_value = float(str(expected).strip())
    except (ValueError, AttributeError):
        return False

    numeric_tolerance: float | None
    try:
        numeric_tolerance = None if tolerance is None else float(tolerance)
    except (ValueError, TypeError):
        numeric_tolerance = None

    if numeric_tolerance is None or numeric_tolerance == 0:
        return given_value == expected_value
    return abs(given_value - expected_value) <= numeric_tolerance


def validate_answer(
    expected: str,
    given: str,
    qtype: str,
    alternatives: list[str] | None = None,
    tolerance: float | None = None,
) -> bool:
    """Return whether the user's answer is correct for the given qtype.

    Dispatch by qtype:
      free_response / translate / identify -- normalize both sides and check
        given against [expected] + alternatives, returning True on the first
        normalized match. These three share one path in v1; identify and
        free_response are presently identical, with qtype kept in the
        signature so the paths can diverge later without a signature change.
      multiple_choice -- exact string comparison of given against expected.
        Both strings are server-generated (the server builds the shuffled
        options and the user submits the chosen option's text), so no
        normalization is needed.
      arithmetic -- parse given as a number and compare to expected within
        tolerance.

    An unrecognized qtype returns False rather than raising, so a bad qtype
    can never be silently scored correct.
    """
    if qtype == QTYPE_ARITHMETIC:
        return _validate_numeric(given, expected, tolerance)

    if qtype == QTYPE_MULTIPLE_CHOICE:
        return given == expected

    if qtype in (QTYPE_FREE_RESPONSE, QTYPE_TRANSLATE, QTYPE_IDENTIFY):
        normalized_given = normalize_text(given)
        acceptable = [expected] + (alternatives or [])
        for candidate in acceptable:
            if normalize_text(candidate) == normalized_given:
                return True
        return False

    return False


# C-008: Import parsing (JSON Lines and CSV).
# Pure functions that turn raw uploaded text into a list of canonical
# question dicts ready for DATABASE.insert_questions_bulk (C-003). JSONL is
# the canonical format (ADR-004); CSV is a convenience adapter that produces
# the identical dict shape. Both routes converge through
# _normalize_question_dict, which is the single place that validates required
# fields and fills optional defaults -- so the bulk insert can assume valid
# dicts (decision in C-003).

# Within a CSV cell, array-valued fields (alternatives, distractors, hints,
# tags) are pipe-separated, because the comma is the CSV column delimiter and
# would collide. Example: a tags cell "capital|europe|france" becomes
# ["capital", "europe", "france"].
_CSV_ARRAY_SEPARATOR = "|"

# The array-valued optional fields, handled uniformly by both parsers.
_ARRAY_FIELDS = ("alternatives", "distractors", "hints", "tags")


class ImportParseError(ValueError):
    """Raised when import text cannot be parsed into valid question dicts.

    Carries a human-readable message naming the offending line or field so
    the HTTP layer can report which row of an upload failed.
    """


def _coerce_difficulty(value: object) -> int | None:
    """Coerce a difficulty value to an int in 1..5, or None.

    Accepts None, empty string, or a parseable integer. Returns None for
    absent/empty input. Raises ImportParseError for a present but invalid
    value (non-integer, or out of the 1..5 range from the data model).
    """
    if value is None or value == "":
        return None
    try:
        difficulty = int(value)
    except (ValueError, TypeError):
        raise ImportParseError("difficulty must be an integer 1-5, got " + repr(value))
    if difficulty < 1 or difficulty > 5:
        raise ImportParseError(
            "difficulty must be between 1 and 5, got " + repr(difficulty)
        )
    return difficulty


def _normalize_question_dict(raw: dict) -> dict:
    """Validate and normalize one raw record into a canonical question dict.

    Required fields: question and answer, both non-empty after stripping.
    qtype defaults to free_response and, if present, must be one of QTYPES.
    The four array fields default to empty lists. media_url defaults to None.
    difficulty is coerced to an int 1..5 or None. The returned dict has
    exactly the keys insert_questions_bulk consumes.

    Raises ImportParseError naming the problem when a record is invalid.
    """
    question = raw.get("question")
    answer = raw.get("answer")
    if question is None or str(question).strip() == "":
        raise ImportParseError("record is missing a non-empty 'question'")
    if answer is None or str(answer).strip() == "":
        raise ImportParseError("record is missing a non-empty 'answer'")

    qtype = raw.get("qtype") or QTYPE_FREE_RESPONSE
    if qtype not in QTYPES:
        raise ImportParseError(
            "qtype must be one of " + repr(QTYPES) + ", got " + repr(qtype)
        )

    normalized = {
        "qtype": qtype,
        "question": str(question),
        "answer": str(answer),
        "media_url": raw.get("media_url") or None,
        "difficulty": _coerce_difficulty(raw.get("difficulty")),
    }
    for field in _ARRAY_FIELDS:
        value = raw.get(field)
        if value is None or value == "":
            normalized[field] = []
        elif isinstance(value, list):
            normalized[field] = [str(item) for item in value]
        else:
            raise ImportParseError(
                "field " + repr(field) + " must be a list, got " + repr(value)
            )
    return normalized


def parse_jsonl(text: str) -> list[dict]:
    """Parse JSON Lines import text into a list of canonical question dicts.

    One JSON object per line (ADR-004). Blank lines and lines that are only
    whitespace are skipped, so trailing newlines are harmless. Each object is
    normalized and validated. Raises ImportParseError naming the line number
    (1-based) when a line is not valid JSON or fails validation.
    """
    questions = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "":
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise ImportParseError(
                "line " + str(line_number) + " is not valid JSON: " + str(error)
            )
        if not isinstance(raw, dict):
            raise ImportParseError("line " + str(line_number) + " is not a JSON object")
        try:
            questions.append(_normalize_question_dict(raw))
        except ImportParseError as error:
            raise ImportParseError("line " + str(line_number) + ": " + str(error))
    return questions


def parse_csv(text: str) -> list[dict]:
    """Parse CSV import text into a list of canonical question dicts.

    Expects a header row naming columns; question and answer columns are
    required, the rest optional. Array-valued columns (alternatives,
    distractors, hints, tags) hold pipe-separated values within a single
    cell, since the comma is the column delimiter. Empty cells become absent
    fields (handled as defaults by normalization). Produces the same dict
    shape as parse_jsonl. Raises ImportParseError naming the row number
    (1-based, excluding the header) when a row fails validation.
    """
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return []

    questions = []
    for row_number, row in enumerate(reader, start=1):
        # Split pipe-separated array cells into lists before normalizing.
        prepared: dict = {}
        for key, value in row.items():
            if key is None:
                continue
            if key in _ARRAY_FIELDS:
                if value is None or value.strip() == "":
                    prepared[key] = []
                else:
                    prepared[key] = [
                        item.strip()
                        for item in value.split(_CSV_ARRAY_SEPARATOR)
                        if item.strip() != ""
                    ]
            else:
                prepared[key] = value
        try:
            questions.append(_normalize_question_dict(prepared))
        except ImportParseError as error:
            raise ImportParseError("row " + str(row_number) + ": " + str(error))
    return questions


def parse_import(text: str, file_format: str) -> list[dict]:
    """Dispatch import parsing by format string ("jsonl" or "csv").

    The HTTP layer determines the format from the upload's file extension or
    an explicit format parameter and passes it here. Both formats yield the
    same canonical list of question dicts. Raises ImportParseError for an
    unrecognized format.
    """
    if file_format == "jsonl":
        return parse_jsonl(text)
    if file_format == "csv":
        return parse_csv(text)
    raise ImportParseError(
        "unknown import format " + repr(file_format) + "; expected 'jsonl' or 'csv'"
    )


# A1: Authoring transform (pure). A minimal editor-buffer block format for
# writing questions by hand: 'key: value' lines, blank-line-separated blocks,
# '#' comment lines, '|'-separated arrays (the same in-cell convention as CSV
# import). Short aliases q/a/alt/type/hint keep the typing burden low. The
# buffer is a TRANSIENT INBOX, not a canonical store -- no ids, no source
# tracking, no cross-file policy (those existed in sm2's @@@ format to serve
# files-as-truth, which the database-authoritative model dissolves; see
# consolidation-findings.md section 15). Every parsed block funnels through
# _normalize_question_dict, so this section adds a projection, not a second
# validation authority: author_parse output is exactly what parse_jsonl
# produces for the same records. author_render is the inverse (enables a
# future edit-bank round trip); author_template is the commented starter
# buffer the editor loop opens. The impure shells (editor loop, stdin
# filter) live at the MAIN edge in drill.py (A2), never here.

AUTHOR_KEY_ALIASES = {
    "q": "question",
    "a": "answer",
    "alt": "alternatives",
    "type": "qtype",
    "hint": "hints",
}

AUTHOR_KNOWN_KEYS = (
    "question",
    "answer",
    "qtype",
    "alternatives",
    "distractors",
    "hints",
    "tags",
    "media_url",
    "difficulty",
)


def flush_author_block(block: dict, block_start_line: int, records: list) -> None:
    """Normalize one accumulated authoring block and append it to records.

    Module-level on purpose (no nested closure in author_parse, per the
    style contract). An empty block is a no-op, so blank-line runs and a
    trailing blank line are harmless. Re-raises ImportParseError with the
    block's starting line prepended, so the editor loop can point at the
    offending block. Every ImportParseError raised on the authoring path
    carries an integer error_line attribute (here, the block's first line)
    so the A2 stdin-filter shell can emit file:line: messages -- the nvim
    quickfix contract -- without re-parsing its own error strings.
    """
    if not block:
        return
    try:
        records.append(_normalize_question_dict(block))
    except ImportParseError as error:
        block_error = ImportParseError(
            "block starting at line " + str(block_start_line) + ": " + str(error)
        )
        block_error.error_line = block_start_line
        raise block_error


def author_parse(text: str) -> list[dict]:
    """Parse an editor buffer into canonical question dicts. Pure.

    Raises ImportParseError naming the line or block on any problem, so the
    shells can report position (editor banner, or file:line: on stderr).
    """
    records: list[dict] = []
    block: dict = {}
    block_start_line = 0

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        if line.lstrip().startswith("#"):
            continue
        if line.strip() == "":
            flush_author_block(block, block_start_line, records)
            block = {}
            continue
        if ":" not in line:
            bare_line_error = ImportParseError(
                "line " + str(line_number) + ": expected 'key: value', got " + repr(line)
            )
            bare_line_error.error_line = line_number
            raise bare_line_error
        key, _, value = line.partition(":")
        key = AUTHOR_KEY_ALIASES.get(key.strip(), key.strip())
        value = value.strip()
        if key not in AUTHOR_KNOWN_KEYS:
            unknown_key_error = ImportParseError(
                "line " + str(line_number) + ": unknown key " + repr(key)
                + " (known: " + ", ".join(AUTHOR_KNOWN_KEYS) + ")"
            )
            unknown_key_error.error_line = line_number
            raise unknown_key_error
        if not block:
            block_start_line = line_number
        if key in block:
            duplicate_key_error = ImportParseError(
                "line " + str(line_number) + ": duplicate key " + repr(key)
                + " in one block"
            )
            duplicate_key_error.error_line = line_number
            raise duplicate_key_error
        if key in _ARRAY_FIELDS:
            block[key] = [
                piece.strip()
                for piece in value.split(_CSV_ARRAY_SEPARATOR)
                if piece.strip() != ""
            ]
        else:
            block[key] = value
    flush_author_block(block, block_start_line, records)
    return records


def author_render(records: list[dict]) -> str:
    """Render canonical question dicts back into the buffer format. Pure.

    Inverse of author_parse for every representable record; omits empty and
    default-valued fields so round trips stay minimal.
    """
    blocks: list[str] = []
    for record in records:
        lines = ["q: " + record["question"], "a: " + record["answer"]]
        if record.get("qtype") and record["qtype"] != QTYPE_FREE_RESPONSE:
            lines.append("type: " + record["qtype"])
        for field in _ARRAY_FIELDS:
            values = record.get(field) or []
            if values:
                lines.append(
                    field + ": "
                    + (" " + _CSV_ARRAY_SEPARATOR + " ").join(values)
                )
        if record.get("media_url"):
            lines.append("media_url: " + record["media_url"])
        if record.get("difficulty") is not None:
            lines.append("difficulty: " + str(record["difficulty"]))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def author_template(count: int = 1) -> str:
    """Starter buffer with the format documented in comments. Pure."""
    header = (
        "# One question per block; blank line between blocks.\n"
        "# Required: q, a. Optional: type (" + "|".join(QTYPES) + "),\n"
        "# alt, distractors, hint, tags, media_url, difficulty (1-5).\n"
        "# Arrays use ' | '. Lines starting with '#' are ignored.\n"
        "# An empty buffer aborts.\n\n"
    )
    return header + "\n\n".join("q: \na: " for _ in range(count)) + "\n"


# C-011 support: session stats summary (pure). Takes the ordered correctness
# sequence from DATABASE.get_session_correctness and computes the summary the
# UI stats bar shows. Streak is the count of consecutive correct answers
# ending at the most recent response (a current run), which is natural in
# Python and awkward in SQL -- hence the split.


def summarize_correctness(correctness: list[bool]) -> dict:
    """Summarize an ordered correct/incorrect sequence for the stats bar.

    Returns a dict with:
        total    -- number of answers
        correct  -- number marked correct
        accuracy -- correct / total as a float, or 0.0 when total is 0
        streak   -- length of the current run of consecutive correct answers
                    counting backward from the most recent answer (0 if the
                    most recent answer was incorrect or there are none)
    Pure and deterministic.
    """
    total = len(correctness)
    # An empty sequence (a session with no answers yet -- the very first
    # question, or a freshly started session) yields zeros and a 0.0 accuracy
    # rather than a division error. This is the time-zero case for every new
    # session and must be handled, not asserted away.
    correct_count = sum(1 for is_correct in correctness if is_correct)
    accuracy = (correct_count / total) if total > 0 else 0.0

    streak = 0
    for is_correct in reversed(correctness):
        if not is_correct:
            break
        streak += 1

    return {
        "total": total,
        "correct": correct_count,
        "accuracy": accuracy,
        "streak": streak,
    }


def breakdown_by(
    rows: list[dict],
    key_of,
    label_of,
    *,
    include_row=None,
) -> list[dict]:
    """Group response rows into a sorted accuracy breakdown by an arbitrary key.

    The pure grouping mechanism behind the stats breakdowns (ADR-041). The
    grouping POLICY is supplied entirely as callables, so the same function backs
    the per-category breakdown and the per-difficulty breakdown, and a future
    consumer (#7 adaptive selection, a CLI report, an export) can reuse it with
    its own key without touching this function or summarize_stats:

        key_of(row)      -> the bucket key (any hashable). Rows with the same key
                            are grouped together.
        label_of(row)    -> the human-facing label for that key. Read from the
                            FIRST row seen for each key (labels are a function of
                            the key, so any row in the bucket gives the same one).
        include_row(row) -> optional predicate; when given, only rows for which it
                            returns truthy participate (e.g. arithmetic-only, or
                            "leaf_count is not None"). None means include all.

    Each returned bucket is {key, label, total, correct, accuracy}. Buckets are
    sorted by descending total then label (a stable, deterministic tiebreak), so
    the most-practiced bucket leads regardless of input or dict order -- the same
    ordering rule the category breakdown uses. accuracy is correct/total, or 0.0
    for an empty bucket (which cannot arise here, but keeps the rule total-safe).

    PURE: no IO, no clock, no randomness; the same rows and callables always
    produce the same list. This is why the S11 grouping-key choice (leaf_count
    vs rung) is a one-line swap at the call site -- the mechanism is fixed and
    the key is data passed in (ADR-041 switchability note).
    """
    grouped: dict = {}
    order: list = []  # first-seen order, only for stable grouping of the keys
    for row in rows:
        if include_row is not None and not include_row(row):
            continue
        key = key_of(row)
        bucket = grouped.get(key)
        if bucket is None:
            bucket = {
                "key": key,
                "label": label_of(row),
                "total": 0,
                "correct": 0,
            }
            grouped[key] = bucket
            order.append(key)
        bucket["total"] += 1
        if row.get("correct"):
            bucket["correct"] += 1

    buckets = []
    for key in order:
        bucket = grouped[key]
        bucket_total = bucket["total"]
        bucket["accuracy"] = (
            (bucket["correct"] / bucket_total) if bucket_total > 0 else 0.0
        )
        buckets.append(bucket)

    # Most-practiced first; label as a stable tiebreak. label may be non-string
    # for some keys, so coerce to str for a total-safe comparison.
    buckets.sort(key=lambda entry: (-entry["total"], str(entry["label"])))
    return buckets


def _median(values: list):
    """Median of a PRE-SORTED numeric list, or None when the list is empty.

    Thread N.2 timing helper. Pure and deterministic. Returns an int for an
    odd-length list (the middle element) and the int-rounded average of the two
    middle elements for an even-length list, so the surfaced figure is always a
    whole number of milliseconds. Callers pass a sorted list (summarize_stats
    sorts once); this does not re-sort.
    """
    count = len(values)
    if count == 0:
        return None
    mid = count // 2
    if count % 2 == 1:
        return int(values[mid])
    # Even length: average the two central values, rounded to the nearest int.
    return int(round((values[mid - 1] + values[mid]) / 2))


def summarize_stats(rows: list[dict]) -> dict:
    """Summarize durable cross-session stats for the stats view (C-019a).

    Pure counterpart to the DATABASE reader get_responses_for_stats. Takes the
    response rows it returns (each with at least `correct` and the owning
    `category_id`/`category_name`) and produces the text-only summary the view
    renders (section 9 -- no charts in v1):

        total      -- number of responses in the window/filter
        correct    -- number marked correct
        accuracy   -- correct / total as a float, or 0.0 when total is 0
        categories -- per-category breakdown, a list of
                      {category_id, category_name, total, correct, accuracy},
                      ordered by descending total then category name, so the
                      most-practiced category leads
        difficulty_breakdown -- per-leaf_count breakdown of ARITHMETIC responses
                      that carry a leaf_count, a list of
                      {key, label, total, correct, accuracy} where key is the
                      leaf_count and label is "N leaves", ordered most-practiced
                      first. Grouped by leaf_count, NOT by the rung label
                      (ADR-038 S11): the rung is incomparable across operator
                      mixes (a division-only rung 3 and an all-ops rung 3 differ),
                      while leaf_count is the comparable structural fact. Empty
                      when no arithmetic response carries a leaf_count (e.g.
                      bank-only practice, or all responses pre-#2). The render
                      layer decides whether to show it (single-bucket suppression
                      is a display choice, C-D2i-3), exactly as for categories.
        median_elapsed_ms -- the MEDIAN think+type time across responses that
                      carry a non-null elapsed_ms, as an int (ms), or None when
                      no response carries timing. Median not mean (Thread N.2):
                      response times are right-skewed (a few long pauses), so the
                      mean misleads while the median is the honest central figure.
                      Rows with a null elapsed_ms are skipped, NOT treated as 0.

    The empty case (a fresh database, or a window/filter with no responses)
    yields total 0, accuracy 0.0, an empty categories list, an empty
    difficulty_breakdown, and a None median_elapsed_ms rather than a division
    error -- the time-zero case, handled like summarize_correctness.

    elapsed_ms is surfaced as a single aggregate (median_elapsed_ms) as of
    Thread N.2. Timing collection began at C-018c; the rows already carry
    elapsed_ms, so this summary reads it without a new query. Only the median
    is exposed; per-answer timing remains unsurfaced.

    Pure and deterministic (the category ordering is total/name, not input
    order, so the same rows always summarize identically).
    """
    total = len(rows)
    correct_count = sum(1 for row in rows if row.get("correct"))
    accuracy = (correct_count / total) if total > 0 else 0.0

    # Group by category, preserving each category's id and display name.
    grouped: dict[int, dict] = {}
    for row in rows:
        category_id = row.get("category_id")
        bucket = grouped.get(category_id)
        if bucket is None:
            bucket = {
                "category_id": category_id,
                "category_name": row.get("category_name"),
                "total": 0,
                "correct": 0,
            }
            grouped[category_id] = bucket
        bucket["total"] += 1
        if row.get("correct"):
            bucket["correct"] += 1

    categories = []
    for bucket in grouped.values():
        bucket_total = bucket["total"]
        bucket["accuracy"] = (
            (bucket["correct"] / bucket_total) if bucket_total > 0 else 0.0
        )
        categories.append(bucket)

    # Most-practiced first; name as a stable tiebreak so the order is
    # deterministic regardless of dict/input ordering. (name may be None only
    # for malformed data; coerce to "" for a total-safe sort key.)
    categories.sort(key=lambda entry: (-entry["total"], entry["category_name"] or ""))

    # Per-difficulty breakdown, grouped by leaf_count via the breakdown_by seam
    # (ADR-041). Arithmetic-only and only rows that actually carry a leaf_count
    # (bank rows, and pre-#2 / no-rung arithmetic rows, are NULL and excluded).
    # The grouping KEY is leaf_count, not the rung label (S11): leaf_count is the
    # cross-mix-comparable structural fact. Swapping the key later (e.g. to the
    # rung) is a one-line change here -- the mechanism is in breakdown_by.
    difficulty_breakdown = breakdown_by(
        rows,
        key_of=lambda row: row.get("leaf_count"),
        label_of=lambda row: str(row.get("leaf_count")) + " leaves",
        include_row=lambda row: (
            row.get("category_name") == "arithmetic"
            and row.get("leaf_count") is not None
        ),
    )

    # Median think+type time (Thread N.2). Collect only non-null elapsed_ms
    # values; a null means the response predates timing collection or was not
    # timed, and must be skipped (not counted as 0, which would drag the median
    # down). None when no response carries timing -- the time-zero case, so the
    # render layer suppresses the figure the way it does for empty breakdowns.
    elapsed_values = sorted(
        row.get("elapsed_ms")
        for row in rows
        if row.get("elapsed_ms") is not None
    )
    median_elapsed_ms = _median(elapsed_values)

    return {
        "total": total,
        "correct": correct_count,
        "accuracy": accuracy,
        "categories": categories,
        "difficulty_breakdown": difficulty_breakdown,
        "median_elapsed_ms": median_elapsed_ms,
    }


# C-012: bank question selection and payload assembly (pure LOGIC).
# pick_next_question chooses one question dict from a list of candidates
# (fetched by HTTP from DATABASE -- LOGIC never queries the DB). v1 uses
# simple random selection with a soft avoid-recent rule; adaptive selection
# is explicitly out of scope (ADR-005, section 9). build_question_payload
# turns a stored question dict into the client-facing payload, including the
# shuffled options list for multiple_choice (the C-007 options contract).


def pick_next_question(
    candidates: list[dict],
    history: list[int] | None = None,
) -> dict | None:
    """Choose the next question from candidates, softly avoiding recent ids.

    candidates is a list of question dicts (as returned by DATABASE). history
    is a list of recently served question ids, most-recent-last. Returns one
    chosen question dict, or None when candidates is empty.

    Policy (v1, non-adaptive): prefer a uniformly random pick from the
    candidates whose id is not in the recent-history window; if that filtered
    set is empty (e.g. the bank is smaller than the window, or every
    candidate was recently seen), fall back to a uniformly random pick from
    all candidates. This avoids immediate repeats when the bank is large
    enough without ever failing to return a question.
    """
    if not candidates:
        return None

    recent = set(history or [])
    fresh = [question for question in candidates if question.get("id") not in recent]
    pool = fresh if fresh else candidates
    return random.choice(pool)


def build_question_payload(question: dict) -> dict:
    """Build the client-facing question payload from a stored question dict.

    The payload mirrors the shape the arithmetic branch returns, so the
    client handles both uniformly and echoes it back to /api/answer:
        qtype, question_text, expected, question_id, alternatives, media_url
    For multiple_choice, an additional "options" list is included: the
    correct answer plus the question's distractors, shuffled, so the UI can
    render choices. The user submits the chosen option's text, which
    validate_answer exact-matches against expected (C-007 contract). For
    non-multiple_choice types, alternatives carries the also-acceptable
    answers and no options list is present.
    """
    required_keys = ("qtype", "question", "answer", "id")
    missing = [key for key in required_keys if key not in question]
    if missing:
        # A question dict reaching here always comes from DATABASE row
        # conversion, which always supplies these keys. Missing keys mean a
        # programming error upstream, so fail loudly rather than emitting a
        # payload with null question_text/expected that the client would
        # silently mis-grade against.
        raise ValueError(
            "build_question_payload got a question missing required keys: "
            + ", ".join(missing)
        )
    payload = {
        "qtype": question["qtype"],
        "question_text": question["question"],
        "expected": question["answer"],
        "question_id": question["id"],
        "alternatives": question.get("alternatives") or [],
        "media_url": question.get("media_url"),
        # Thread N.1: forward the stored per-question hint list so the client
        # can offer a progressive "reveal hint" affordance. Questions already
        # store `hints` (imported via JSONL/CSV, db.py row conversion); it was
        # never forwarded before. Additive + display-only: hints NEVER feed
        # validate_answer's grading dispatch (columns grade; hints only hint).
        # Absent/empty -> [], so the client can uniformly test truthiness.
        "hints": question.get("hints") or [],
    }
    # ---- C-018b scaffold: deferred "Option A" (per-question language) -------
    # TTS (C-018a) needs a language code to pronounce a prompt. It currently
    # resolves one CLIENT-SIDE from the selected bank (banks.language, already
    # sent by GET /api/banks), so this payload deliberately carries NO
    # "language" field and the backend stays frozen.
    #
    # The future, more general path ("Option A") is to thread language THROUGH
    # this payload instead. That would matter when language is a property of
    # the QUESTION rather than the bank -- e.g. a single mixed-language bank,
    # or per-row language overrides -- which the client's bank-level lookup
    # cannot express. Shipping it would mean, in rough order:
    #   1. carry a language up to here -- either as question["language"] (new
    #      per-question column or metadata key, a schema/import change) or by
    #      passing the owning bank's language in as a parameter, e.g.
    #          def build_question_payload(question, *, bank_language=None)
    #      and setting payload["language"] = question.get("language")
    #      or bank_language;
    #   2. have the bank-question handler below fetch the bank row (it already
    #      has bank_id) and pass bank_language=bank["language"] (see the
    #      matching comment at the call site);
    #   3. update the section-6 payload contract + the frontend to prefer
    #      payload.language over the client bank lookup when present.
    #
    # This is intentionally NOT built here: it changes the frozen backend and
    # the API contract, so per the working agreement it needs its own spec
    # amendment and commit. Until then, build_question_payload stays a pure
    # function of the question dict alone. See DECISIONS C-018b.
    # -------------------------------------------------------------------------
    if question["qtype"] == QTYPE_MULTIPLE_CHOICE:
        options = [question["answer"]] + list(question.get("distractors") or [])
        random.shuffle(options)
        payload["options"] = options
    return payload


# B2: adaptive selection (roadmap #7, ADR-005 seam). A second selection
# strategy alongside pick_next_question: weight candidates by their smoothed
# historical miss rate so struggling questions surface more often. The
# response aggregates arrive from DATABASE (get_response_stats_for_bank);
# the uniform random sample arrives from HTTP as a parameter, so unlike
# pick_next_question (module-level random by the v1 convention) these
# functions are fully deterministic given their inputs.


def miss_rate_weight(attempt_count: int, correct_count: int) -> float:
    """Laplace-smoothed miss rate: (misses + 1) / (attempts + 2).

    A never-attempted question weighs 0.5, so a cold bank is uniform and
    the weighted policy degrades to the current random policy instead of
    starving or looping.
    """
    miss_count = attempt_count - correct_count
    return (miss_count + 1.0) / (attempt_count + 2.0)


def select_weighted_by_miss_rate(
    candidates: list[dict],
    response_stats_by_question_id: dict,
    history: list[int] | None,
    random_value: float,
) -> dict | None:
    """Choose one candidate, weighted by smoothed miss rate.

    Adaptive selection (roadmap #7, schema-free): weight candidates by
    Laplace-smoothed miss rate (miss_rate_weight over the per-question
    attempt_count/correct_count aggregates in response_stats_by_question_id),
    softly avoiding the recent-history window exactly as pick_next_question
    does -- prefer candidates outside the window, fall back to all when the
    filtered pool is empty. random_value is a uniform [0, 1) sample supplied
    by the caller (HTTP reads randomness at the edge) so the function stays
    deterministic in tests. Returns None only for an empty candidate list.
    """
    if not candidates:
        return None
    recent_question_ids = set(history or [])
    fresh = [
        candidate
        for candidate in candidates
        if candidate.get("id") not in recent_question_ids
    ]
    pool = fresh if fresh else candidates

    weights = []
    for candidate in pool:
        stats = response_stats_by_question_id.get(candidate["id"])
        if stats is None:
            weights.append(miss_rate_weight(0, 0))
        else:
            weights.append(
                miss_rate_weight(stats["attempt_count"], stats["correct_count"])
            )

    total_weight = sum(weights)
    threshold = random_value * total_weight
    cumulative = 0.0
    for candidate, weight in zip(pool, weights):
        cumulative += weight
        if cumulative > threshold:
            return candidate
    return pool[-1]


# C2: SM2 scheduler pure core (roadmap #7, ADR-025). Ported from the spike
# scheduler_port.py, itself pinned field-identical to sm2.sm2_update by the
# equivalence spike. Schedule state is a plain dict mirroring the
# question_schedule row (C1): question_id, easiness_factor, interval_days,
# repetition_count, due_date, last_review, lapse_count. Dates are ordinal-day
# integers (datetime.date.toordinal), stamped ONCE per request at the HTTP
# boundary and passed down -- no clock and no IO anywhere in these functions.

EASINESS_FACTOR_MINIMUM = 1.3
EASINESS_FACTOR_MAXIMUM = 3.0
EASINESS_FACTOR_INITIAL = 2.5
RECALL_QUALITY_TO_SM2_GRADE = {0: 1, 1: 3, 2: 5}
INTERVAL_FUZZ_FRACTION = 0.05


def derive_recall_quality(correct: bool, elapsed_ms: int | None) -> int:
    """Map a drill grading outcome to an SM-2 recall quality 0|1|2.

    Version 1 policy: binary. Wrong -> 0, correct -> 2. elapsed_ms is
    accepted but deliberately unused so the timing-derived policy can swap
    in behind the same signature once per-qtype baselines exist -- do NOT
    add timing thresholds here before those baselines are measured (C5),
    per ADR-025 (no persisted grading column; quality is derived at grading
    time). The middle grade (1, "correct with effort") is unreachable until
    then; the cost is that easiness never decays on effortful passes,
    bounded by the lapse path resetting interval to one day.
    """
    if correct:
        return 2
    return 0


def advance_schedule_state(
    recall_quality: int,
    easiness_factor: float,
    interval_days: float,
    repetition_count: int,
    lapse_count: int,
    review_date: int,
) -> dict:
    """Advance one question's schedule after a graded review. Pure SM-2.

    Port of sm2.sm2_update with drill naming; the arithmetic is identical
    and pinned by the equivalence spike against the original. review_date
    is an ordinal day supplied by the caller. An unknown recall_quality
    raises KeyError -- programmer errors stay loud, never value-ified.
    """
    sm2_grade = RECALL_QUALITY_TO_SM2_GRADE[recall_quality]
    easiness_delta_inner = 0.08 + (5 - sm2_grade) * 0.02
    easiness_delta = 0.1 - (5 - sm2_grade) * easiness_delta_inner
    new_easiness_factor = easiness_factor + easiness_delta
    if new_easiness_factor < EASINESS_FACTOR_MINIMUM:
        new_easiness_factor = EASINESS_FACTOR_MINIMUM
    if new_easiness_factor > EASINESS_FACTOR_MAXIMUM:
        new_easiness_factor = EASINESS_FACTOR_MAXIMUM

    if sm2_grade < 3:
        new_repetition_count = 0
        new_interval_days = 1.0
        new_lapse_count = lapse_count + 1
    else:
        new_repetition_count = repetition_count + 1
        new_lapse_count = lapse_count
        if new_repetition_count == 1:
            new_interval_days = 1.0
        elif new_repetition_count == 2:
            new_interval_days = 6.0
        else:
            new_interval_days = interval_days * new_easiness_factor

    return {
        "easiness_factor": new_easiness_factor,
        "interval_days": new_interval_days,
        "repetition_count": new_repetition_count,
        "lapse_count": new_lapse_count,
        "due_date": review_date + int(round(new_interval_days)),
        "last_review": review_date,
    }


def apply_interval_fuzz(interval_days: float, question_id: int) -> float:
    """Spread intervals by a deterministic per-question jitter of at most
    +-INTERVAL_FUZZ_FRACTION, so questions learned together do not stay
    due together forever. Deterministic (keyed on question_id, no RNG) so
    replaying the response log reproduces the stored schedule exactly.
    Intervals of two days or less are exempt: fuzzing there can only
    round to the same day or distort the fixed 1 -> 6 opening steps.
    """
    if interval_days <= 2.0:
        return interval_days
    jitter_step = (question_id * 2654435761) % 1024
    jitter_fraction = (jitter_step / 1023.0) * 2.0 - 1.0
    return interval_days * (1.0 + INTERVAL_FUZZ_FRACTION * jitter_fraction)


def schedule_update_allowed_today(schedule_state: dict | None, today: int) -> bool:
    """One schedule update per question per day: only the first graded
    attempt schedules; later same-day attempts log a response but must
    not advance the interval again off one day of memory. A question
    with no schedule row (never reviewed) is always allowed.
    """
    if schedule_state is None:
        return True
    return schedule_state["last_review"] != today


# C3: review-mode candidate handling (roadmap #7). Partition a bank into
# due/new/not_due against the schedule, order the due backlog by recall risk,
# budget how many new questions enter the schedule per day, and rebuild the
# whole schedule table from the response log (state is a cache of the log).
# All pure; the daily budget values live in config
# (NEW_QUESTIONS_PER_DAY_MAXIMUM et al.) and arrive here as parameters.


def relative_overdueness(schedule_state: dict, today: int) -> float:
    """Sort key for spending a capped review budget on a backlog: days
    overdue divided by interval. A short-interval question three days
    late is at greater recall risk than a long-interval one five days
    late. Larger means more at risk; not-yet-due yields <= 0.
    """
    interval_days = schedule_state["interval_days"]
    if interval_days < 1.0:
        interval_days = 1.0
    return (today - schedule_state["due_date"]) / interval_days


def _overdueness_of_decorated_pair(decorated_pair: tuple) -> float:
    """Sort key for the (overdueness, candidate) pairs built in
    partition_candidates_by_schedule -- module-level per the style contract
    (the spike used a closure-carrying lambda here)."""
    return decorated_pair[0]


def _question_id_of_candidate(candidate: dict) -> int:
    """Sort key: a candidate's id (authoring order for new questions)."""
    return candidate["id"]


def partition_candidates_by_schedule(
    candidates: list[dict],
    schedule_by_question_id: dict,
    today: int,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split bank candidates into (due, new, not_due) for review mode.

    due: has a schedule row and due_date <= today, ordered most at risk
    first (relative overdueness, DESCENDING -- risk order, deliberately not
    most-days-overdue-first). new: no schedule row yet, in id order
    (authoring order). not_due: scheduled for the future.
    """
    due: list[dict] = []
    new: list[dict] = []
    not_due: list[dict] = []
    for candidate in candidates:
        schedule_state = schedule_by_question_id.get(candidate["id"])
        if schedule_state is None:
            new.append(candidate)
        elif schedule_state["due_date"] <= today:
            due.append(candidate)
        else:
            not_due.append(candidate)

    decorated_due = []
    for candidate in due:
        overdueness = relative_overdueness(
            schedule_by_question_id[candidate["id"]], today
        )
        decorated_due.append((overdueness, candidate))
    decorated_due.sort(key=_overdueness_of_decorated_pair, reverse=True)
    due = [candidate for _overdueness, candidate in decorated_due]

    new.sort(key=_question_id_of_candidate)
    return due, new, not_due


def apply_new_question_throttle(
    new_candidates: list[dict],
    new_introduced_today_by_bank: dict,
    per_day_maximum: int,
    per_bank_minimum: int,
) -> list[dict]:
    """Budget how many never-reviewed questions enter the schedule today.

    Port of sm2's apply_throttle_and_cap floor/cap idea with the string
    domain prefix replaced by the real bank_id column (throttle floor keyed
    on bank_id per the plan amendment). Two passes: first guarantee
    per_bank_minimum slots per bank that still has headroom today, then
    fill remaining budget in candidate order.
    """
    total_introduced_today = sum(new_introduced_today_by_bank.values())
    budget = per_day_maximum - total_introduced_today
    if budget <= 0:
        return []

    admitted: list[dict] = []
    admitted_ids: set[int] = set()
    admitted_count_by_bank: dict[int, int] = {}

    for candidate in new_candidates:
        if len(admitted) >= budget:
            break
        bank_id = candidate["bank_id"]
        already_today = new_introduced_today_by_bank.get(bank_id, 0)
        admitted_so_far = admitted_count_by_bank.get(bank_id, 0)
        if already_today + admitted_so_far >= per_bank_minimum:
            continue
        admitted.append(candidate)
        admitted_ids.add(candidate["id"])
        admitted_count_by_bank[bank_id] = admitted_so_far + 1

    for candidate in new_candidates:
        if len(admitted) >= budget:
            break
        if candidate["id"] in admitted_ids:
            continue
        admitted.append(candidate)
        admitted_ids.add(candidate["id"])

    return admitted


def rebuild_schedule_from_response_log(
    response_rows: list[dict],
) -> dict:
    """Fold the responses log into schedule state: state is a cache of the
    log. Each row needs question_id, correct, elapsed_ms, answered_ordinal.
    Applies the same once-per-day rule and fuzz the live path applies, so
    rebuild == stored holds while the quality policy is unchanged. This is
    the backfill for the migration, the corruption-recovery path, and the
    invariant check (C4's simulation test) in one function. Rows with
    question_id None (generated arithmetic) are skipped -- they were never
    scheduled.
    """
    schedule_by_question_id: dict = {}
    for row in response_rows:
        question_id = row["question_id"]
        if question_id is None:
            continue
        review_date = row["answered_ordinal"]
        existing = schedule_by_question_id.get(question_id)
        if not schedule_update_allowed_today(existing, review_date):
            continue
        if existing is None:
            easiness_factor = EASINESS_FACTOR_INITIAL
            interval_days = 0.0
            repetition_count = 0
            lapse_count = 0
        else:
            easiness_factor = existing["easiness_factor"]
            interval_days = existing["interval_days"]
            repetition_count = existing["repetition_count"]
            lapse_count = existing["lapse_count"]
        recall_quality = derive_recall_quality(row["correct"], row["elapsed_ms"])
        advanced = advance_schedule_state(
            recall_quality,
            easiness_factor,
            interval_days,
            repetition_count,
            lapse_count,
            review_date,
        )
        fuzzed_interval = apply_interval_fuzz(advanced["interval_days"], question_id)
        advanced["interval_days"] = fuzzed_interval
        advanced["due_date"] = review_date + int(round(fuzzed_interval))
        advanced["question_id"] = question_id
        schedule_by_question_id[question_id] = advanced
    return schedule_by_question_id


# C5: terminal views (roadmap #7 measurement). One table renderer ported from
# sm2 (its T3 refactor: the pre-refactor printers differed only in columns,
# so the differences live in column tables and the mechanism exists once).
# Style translation from sm2: the Column NamedTuple becomes a plain 4-tuple
# (header, align, width, fmt) and the nested line() closure becomes the
# module-level _render_table_row. Views stay pure -- rows in, string out; all
# fetching happens in the cli entry (drill.py). width None fits the widest of
# header and cells; a left-aligned LAST column is emitted unpadded so no line
# carries trailing whitespace.


def _render_table_row(cells: list, columns: tuple, widths: list) -> str:
    """Render one table line: each cell aligned to its column width, except a
    left-aligned final column, which is emitted bare (no trailing pad)."""
    last_index = len(columns) - 1
    parts = []
    for index in range(len(columns)):
        cell = cells[index]
        _header, align, _width, _fmt = columns[index]
        if index == last_index and align == "<":
            parts.append(cell)
        else:
            parts.append(format(cell, align + str(widths[index])))
    return "  ".join(parts)


def render_table(columns: tuple, rows: list) -> str:
    """Render rows under headers. columns is a tuple of
    (header, align, width, fmt) 4-tuples; rows are same-length value tuples.
    """
    grid = []
    for row in rows:
        formatted_row = []
        for column, value in zip(columns, row):
            _header, _align, _width, fmt = column
            formatted_row.append(format(value, fmt) if fmt else str(value))
        grid.append(formatted_row)

    widths = []
    for index, column in enumerate(columns):
        header, _align, width, _fmt = column
        if width is not None:
            widths.append(width)
        else:
            widest_cell = max((len(row[index]) for row in grid), default=0)
            widths.append(max(len(header), widest_cell))

    header_cells = [column[0] for column in columns]
    lines = [_render_table_row(header_cells, columns, widths)]
    for formatted_row in grid:
        lines.append(_render_table_row(formatted_row, columns, widths))
    return "\n".join(lines)


FAILURES_COLUMNS: tuple = (
    ("question_id", "<", None, ""),
    ("bank", "<", 12, ""),
    ("date", "<", 10, ""),
    ("lapses", ">", 6, ""),
    ("user_input", "<", None, ""),
)


def failures_view(failure_rows: list[dict]) -> str:
    """Wrong answers with what the user actually typed. sm2 showed a manually
    written error note; drill stores the real wrong answer on every response,
    so user_input replaces the note. rows from get_failure_rows."""
    if not failure_rows:
        return "no recorded failures."
    table_rows = [
        (
            row["question_id"],
            row["bank_name"],
            row["answered_day"],
            row["lapse_count"],
            row["user_input"],
        )
        for row in failure_rows
    ]
    return render_table(FAILURES_COLUMNS, table_rows)


LEECHES_COLUMNS: tuple = (
    ("question_id", "<", None, ""),
    ("bank", "<", 12, ""),
    ("lapses", ">", 6, ""),
    ("EF", ">", 5, ".2f"),
    ("days_since", "<", None, ""),
)


def leeches_view(leech_rows: list[dict], today: int, leech_threshold: int) -> str:
    """Questions that keep lapsing (lapse_count >= threshold), worst first.
    bank_name replaces sm2's domain_of prefix parse. rows from
    get_leech_rows; today is an ordinal stamped by the caller."""
    if not leech_rows:
        return (
            "no leeches found (lapse_count < "
            + str(leech_threshold)
            + " for all questions)."
        )
    table_rows = [
        (
            row["question_id"],
            row["bank_name"],
            row["lapse_count"],
            row["easiness_factor"],
            str(today - row["last_review"]),
        )
        for row in leech_rows
    ]
    return render_table(LEECHES_COLUMNS, table_rows)


PREVIEW_COLUMNS: tuple = (
    ("question_id", "<", None, ""),
    ("bank", "<", 12, ""),
    ("due_in", ">", 6, ""),
    ("rep", ">", 3, ""),
    ("EF", ">", 5, ".2f"),
)


def preview_view(upcoming_rows: list[dict], today: int) -> str:
    """Upcoming reviews, soonest first. rows from get_upcoming_schedule_rows."""
    if not upcoming_rows:
        return "no upcoming reviews scheduled."
    table_rows = [
        (
            row["question_id"],
            row["bank_name"],
            row["due_date"] - today,
            row["repetition_count"],
            row["easiness_factor"],
        )
        for row in upcoming_rows
    ]
    return render_table(PREVIEW_COLUMNS, table_rows)


DRY_RUN_COLUMNS: tuple = (
    ("question_id", "<", None, ""),
    ("bank", "<", 12, ""),
    ("kind", "<", 4, ""),
    ("rep", ">", 3, ""),
    ("EF", ">", 5, ".2f"),
    ("interval", ">", 8, ".1f"),
    ("days_overdue", "<", None, ""),
)


def dry_run_view(
    due_candidates: list[dict],
    admitted_new_candidates: list[dict],
    schedule_by_question_id: dict,
    bank_name_by_id: dict,
    today: int,
) -> str:
    """What a review session TODAY would serve, without serving it: the due
    backlog in risk order, then the throttle-admitted new questions. The cli
    entry runs the same partition/cap/throttle sequence as the scheduled
    strategy and hands the results here."""
    total = len(due_candidates) + len(admitted_new_candidates)
    header = (
        "dry run: "
        + str(total)
        + " question(s) in today's review queue ("
        + str(len(due_candidates))
        + " due, "
        + str(len(admitted_new_candidates))
        + " new)"
    )
    if total == 0:
        return header
    table_rows = []
    for candidate in due_candidates:
        state = schedule_by_question_id[candidate["id"]]
        table_rows.append(
            (
                candidate["id"],
                bank_name_by_id.get(candidate["bank_id"], "?"),
                "due",
                state["repetition_count"],
                state["easiness_factor"],
                state["interval_days"],
                str(today - state["due_date"]),
            )
        )
    for candidate in admitted_new_candidates:
        table_rows.append(
            (
                candidate["id"],
                bank_name_by_id.get(candidate["bank_id"], "?"),
                "new",
                0,
                EASINESS_FACTOR_INITIAL,
                0.0,
                "-",
            )
        )
    return header + "\n" + render_table(DRY_RUN_COLUMNS, table_rows)


def _percentile_nearest_rank(sorted_values: list, fraction: float):
    """Nearest-rank percentile over an ascending list: the value at ceiling
    (fraction * n), 1-indexed. No interpolation -- every reported number is
    a real observed sample, and the definition is exact for tests."""
    rank = int(fraction * len(sorted_values))
    if rank * 1.0 != fraction * len(sorted_values):
        rank = rank + 1
    if rank < 1:
        rank = 1
    return sorted_values[rank - 1]


def summarize_elapsed_percentiles(samples: list[dict]) -> dict:
    """Median and p90 of elapsed_ms per qtype and per bank (S2).

    samples from get_elapsed_ms_samples. Returns {"by_qtype": {...},
    "by_bank": {...}} where each value is {"count", "median_ms", "p90_ms"}
    (nearest-rank). These per-qtype medians are exactly the baselines the
    future timing-derived derive_recall_quality needs -- the measurement
    lands before the policy, deliberately. Samples with bank_name None
    (generated arithmetic) appear only in the qtype grouping.
    """
    elapsed_by_qtype: dict = {}
    elapsed_by_bank: dict = {}
    for sample in samples:
        elapsed_by_qtype.setdefault(sample["qtype"], []).append(
            sample["elapsed_ms"]
        )
        if sample["bank_name"] is not None:
            elapsed_by_bank.setdefault(sample["bank_name"], []).append(
                sample["elapsed_ms"]
            )

    summary: dict = {"by_qtype": {}, "by_bank": {}}
    for qtype, values in elapsed_by_qtype.items():
        values.sort()
        summary["by_qtype"][qtype] = {
            "count": len(values),
            "median_ms": _percentile_nearest_rank(values, 0.5),
            "p90_ms": _percentile_nearest_rank(values, 0.9),
        }
    for bank_name, values in elapsed_by_bank.items():
        values.sort()
        summary["by_bank"][bank_name] = {
            "count": len(values),
            "median_ms": _percentile_nearest_rank(values, 0.5),
            "p90_ms": _percentile_nearest_rank(values, 0.9),
        }
    return summary


STATS_PERCENTILES_COLUMNS: tuple = (
    ("group", "<", None, ""),
    ("count", ">", 6, ""),
    ("median_ms", ">", 9, ""),
    ("p90_ms", ">", 7, ""),
)


def stats_view(retention: dict, percentile_summary: dict) -> str:
    """The measurement one-pager: true retention (S1) plus the elapsed_ms
    percentile tables (S2). retention from get_true_retention; the summary
    from summarize_elapsed_percentiles."""
    lines = []
    if retention["retention"] is None:
        lines.append("true retention: no graded reviews yet.")
    else:
        lines.append(
            "true retention: "
            + format(retention["retention"], ".1%")
            + " over "
            + str(retention["graded_reviews"])
            + " first-attempts-of-day"
        )
    for group_key, title in (("by_qtype", "qtype"), ("by_bank", "bank")):
        groups = percentile_summary[group_key]
        lines.append("")
        if not groups:
            lines.append("elapsed_ms by " + title + ": no timed responses.")
            continue
        lines.append("elapsed_ms by " + title + ":")
        table_rows = [
            (
                group_name,
                groups[group_name]["count"],
                groups[group_name]["median_ms"],
                groups[group_name]["p90_ms"],
            )
            for group_name in sorted(groups)
        ]
        lines.append(render_table(STATS_PERCENTILES_COLUMNS, table_rows))
    return "\n".join(lines)
