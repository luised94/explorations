"""Spike: prep the two highest-leverage backlog items against the real code.

Part 1 -- bitwise rail: prove &, |, xor, <<, >> ride the existing operator
table, generator, evaluator, and renderer as data rows plus one operand
strategy; surface the real findings (symbol collision, display, ranges).

Part 2 -- numeric/epsilon path for AUTHORED questions: prove the tolerance
machinery already in logic covers it, and that the only missing wiring is
(a) a funnel change (metadata/tolerance not currently importable) and
(b) reading tolerance server-side from the stored question, never the client.
"""

import random
import sys

sys.path.insert(0, "/home/claude/explorations/drill")
import logic as drill_logic
from logic import ImportParseError

failure_count = 0


def check(name, condition):
    global failure_count
    print(("PASS  " if condition else "FAIL  ") + name)
    if not condition:
        failure_count += 1


def generate_operands_shift(operator_record: dict) -> tuple[int, int]:
    """Left operand from the record range; shift amount from a second narrow
    range (shift_min..shift_max), mirroring the exponent strategy's two-range
    shape. Shift of 0 is the identity and is excluded by the range floor."""
    left_value = random.randint(
        operator_record["operand_min"], operator_record["operand_max"])
    shift_amount = random.randint(
        operator_record["shift_min"], operator_record["shift_max"])
    return left_value, shift_amount


BITWISE_OPERATOR_DEFINITIONS = [
    {"symbol": "&", "name": "bitwise_and", "arity": 2,
     "operand_min": 1, "operand_max": 31,
     "forbid_identity": [0], "forbid_identity_referent": "operands",
     "result_constraint": None, "nestable": True,
     "precedence": 3, "associativity": "left",
     "eval_fn": lambda a, b: a & b,
     "operand_strategy": drill_logic._generate_operands_standard},
    {"symbol": "|", "name": "bitwise_or", "arity": 2,
     "operand_min": 1, "operand_max": 31,
     "forbid_identity": [0], "forbid_identity_referent": "operands",
     "result_constraint": None, "nestable": True,
     "precedence": 1, "associativity": "left",
     "eval_fn": lambda a, b: a | b,
     "operand_strategy": drill_logic._generate_operands_standard},
    {"symbol": "xor", "name": "bitwise_xor", "arity": 2,
     "operand_min": 1, "operand_max": 31,
     "forbid_identity": [0], "forbid_identity_referent": "operands",
     "result_constraint": None, "nestable": True,
     "precedence": 2, "associativity": "left",
     "eval_fn": lambda a, b: a ^ b,
     "operand_strategy": drill_logic._generate_operands_standard},
    {"symbol": "<<", "name": "shift_left", "arity": 2,
     "operand_min": 1, "operand_max": 15, "shift_min": 1, "shift_max": 4,
     "forbid_identity": [0], "forbid_identity_referent": "operands",
     "result_constraint": None, "nestable": False,
     "precedence": 4, "associativity": "left",
     "eval_fn": lambda a, b: a << b,
     "operand_strategy": generate_operands_shift},
    {"symbol": ">>", "name": "shift_right", "arity": 2,
     "operand_min": 8, "operand_max": 255, "shift_min": 1, "shift_max": 4,
     "forbid_identity": [0], "forbid_identity_referent": "operands",
     "result_constraint": None, "nestable": False,
     "precedence": 4, "associativity": "left",
     "eval_fn": lambda a, b: a >> b,
     "operand_strategy": generate_operands_shift},
]

# FINDING (symbol collision): "^" is TAKEN by exponent in the existing table,
# so bitwise xor cannot use Python's glyph; the spike uses the word "xor".
existing_symbols = {record["symbol"] for record in drill_logic.OPERATOR_DEFINITIONS}
check("collision surfaced: '^' already means exponent", "^" in existing_symbols)

# Feasibility injection: append rows, rebuild the validated table exactly as
# import time does. The REAL implementation is these rows in OPERATOR_DEFINITIONS
# plus the symbols in config OPERATOR_SYMBOLS; the spike mutates module state
# only to avoid editing the read-only checkout.
drill_logic.OPERATOR_DEFINITIONS.extend(BITWISE_OPERATOR_DEFINITIONS)
drill_logic.OPERATORS = drill_logic._build_operator_table()
check("table builder validates and accepts the five bitwise rows",
      all(symbol in drill_logic.OPERATORS
          for symbol in ("&", "|", "xor", "<<", ">>")))

random.seed(20260703)
bitwise_symbols = ["&", "|", "xor", "<<", ">>"]
generated_count = 0
render_evaluate_consistent = True
sample_renders = []
for _ in range(500):
    expression_tree = drill_logic.generate_expression(
        enabled_symbols=bitwise_symbols)
    answer_value = drill_logic.evaluate_expression(expression_tree)
    rendered_text = drill_logic.render_expression(expression_tree)
    generated_count += 1
    reevaluated = eval(rendered_text.replace("xor", "^"))  # spike-only check
    if reevaluated != answer_value:
        render_evaluate_consistent = False
    if len(sample_renders) < 3:
        sample_renders.append(rendered_text + " = " + str(answer_value))
check("500 bitwise expressions generate, evaluate, render through the "
      "REAL engine", generated_count == 500)
check("render agrees with evaluate on every tree (via python re-eval)",
      render_evaluate_consistent)
print("FINDING  samples:", "; ".join(sample_renders))

nested = 0
for _ in range(200):
    tree = drill_logic.generate_expression(enabled_symbols=["&", "|", "xor"],
                                           difficulty=4)
    if isinstance(tree.get("left"), dict) or isinstance(tree.get("right"), dict):
        nested += 1
check("nestable bitwise operators nest under difficulty rungs (%d/200)"
      % nested, nested > 0)


def render_leaf_in_base(leaf_value: int, base: int) -> str:
    if base == 2:
        return format(leaf_value, "#b")
    if base == 16:
        return format(leaf_value, "#x")
    return str(leaf_value)


def render_expression_in_base(node, base: int) -> str:
    """Base-aware display wrapper: same tree walk shape as render_expression,
    leaves formatted in the requested base. Pure; display-only."""
    if not isinstance(node, dict):
        return render_leaf_in_base(node, base)
    left_text = render_expression_in_base(node["left"], base)
    right_text = render_expression_in_base(node["right"], base)
    return "(" + left_text + " " + node["op"] + " " + right_text + ")"


tree = drill_logic.generate_expression(enabled_symbols=["&"])
binary_render = render_expression_in_base(tree, 2)
check("binary display renders (pedagogy requires it; decimal bitwise is "
      "pointless)", "0b" in binary_render)
print("FINDING  binary display sample:", binary_render, "=",
      format(drill_logic.evaluate_expression(tree), "#b"))
# FINDING (spike walk assumes binary arity keys left/right/op; confirm the
# real node shape against render_expression before landing).

# Part 2: numeric/epsilon for authored bank questions.
check("exact-match semantics when tolerance is None",
      drill_logic.validate_answer("3.1416", "3.1416", "arithmetic") is True
      and drill_logic.validate_answer("3.1416", "3.14159", "arithmetic") is False)
check("tolerance accepts within epsilon and rejects outside",
      drill_logic.validate_answer("3.1416", "3.14159", "arithmetic",
                                  tolerance=0.001) is True
      and drill_logic.validate_answer("3.1416", "3.24", "arithmetic",
                                      tolerance=0.001) is False)
check("malformed tolerance degrades to exact match, never raises",
      drill_logic.validate_answer("5", "5", "arithmetic",
                                  tolerance="bogus") is True)

try:
    drill_logic._normalize_question_dict(
        {"question": "sqrt(2)?", "answer": "1.414",
         "metadata": {"tolerance": 0.001}})
    funnel_accepts_metadata = True
except ImportParseError:
    funnel_accepts_metadata = False
check("FINDING (better than assumed): the funnel ALREADY accepts metadata; "
      "the only epsilon gap is the server-side answer path",
      funnel_accepts_metadata is True)

print("\n%d failure(s)" % failure_count)
raise SystemExit(1 if failure_count else 0)
