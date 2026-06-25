# Handoff: roadmap #5 -- nested expression trees (DESIGN SETTLED + COMMIT PLAN)

Status: design conversation COMPLETE. This document is the output of the #5
design thread. It records the settled decisions (Q1-Q6 plus the unstated
presuppositions surfaced in review), the adversarial-review outcome, and a
topologically-sorted, HAIKU/SONNET-classified commit plan a fresh implementer
can execute cold against the workflow contract.

Baseline verified in-thread: SHA eda0bbdf8884cb2b6447654c9d8057d552ba1518, on
main, sparse tree clean (only drill/ at top level). Suite 179 green (backend
104, frontend 75), ends "ALL GREEN". Node v22, uv 0.11.

ASCII only. Single-user assumption holds throughout. This is a LOGIC-only
change: no schema, no HTTP contract, no frontend change.

================================================================================
0. THE ONE-PARAGRAPH SUMMARY
================================================================================
generate_expression becomes bottom-up and may emit nested {op,left,right}
trees instead of only flat single-operator nodes. Operators split into
COMPOSABLE (+ - *), which may have subtree children, and LEAF-ONLY (/ % ^),
which keep integer leaves as their own operands but may themselves appear as
subtree children of a composable parent. The renderer becomes precedence- and
associativity-aware (it currently over-parenthesizes every nested operand) and
is the SOLE owner of correct printing. Tree size is bounded by a module
constant (_MAX_OPERATOR_DEPTH), NOT a new function parameter. The flat-node
property test becomes a recursive dispatching tree walk. No public signature
changes; nesting is internal behavior governed by module config, exactly as the
operator set is.

================================================================================
1. SETTLED DECISIONS (Q1-Q6)
================================================================================

--- Q3 (THE SPINE): construction approach + operand/subtree rule -------------

DECISION: BOTTOM-UP construction. Build children first; their integer values
are known before the parent operator is chosen or its sibling derived. The
parent is CHOSEN/DERIVED to fit the children -- a built subtree is NEVER
mutated to fit a parent. This keeps generation a pure transformation (the only
impurity is random.*, identical to the existing flat generator).

DECISION: one simple rule, declared per operator as a boolean field on the
record: nestable: bool.
  - COMPOSABLE (nestable=True): + - *   -- may have subtree children.
  - LEAF-ONLY  (nestable=False): / % ^  -- operands stay integer leaves.

PRECISE READING (the most misread point; state it in the ADR verbatim):
nestable governs whether an operator may have subtree CHILDREN. It does NOT
govern whether an operator's node may itself BE a child. A / % ^ node IS a
valid subtree child of a composable parent.
  - REACHABLE:    (a / b) * c   -- * is nestable; the / node is a valid child.
  - REACHABLE:    a * (b / c)   -- same; renderer must parenthesize the right
                                   child (see Q2 associativity).
  - NOT REACHABLE: a / (b * c)  -- / is leaf-only; its operands stay leaves.
  - NOT REACHABLE: 2 ^ (a + b)  -- ^ is leaf-only.
Unreachable trees are unreachable because the GENERATOR never builds them, not
because the renderer cannot print them. The renderer is total over all
well-formed trees (this is what lets #2 widen generation with zero renderer
change).

RATIONALE for the split: / % ^ DERIVE one operand from another (division:
dividend = divisor * quotient; exponent: narrow power range; modulo: divisor
range >= 2). A subtree in a derived position forces "derive a compatible
sibling from a fixed subtree value" -- sparse-factor failure for division, a
magnitude blowup for exponent. + - * have no cross-operand value dependency, so
a subtree value slots in cleanly.

CONSTRAINT LIFTING (composable operators only): a constraint stated over leaves
generalizes to "the same check against evaluate_expression(child)":
  - + forbids operand value 0; * forbids 0 and 1: check against the operand's
    EVALUATED value (a * (subtree-evaluating-to-1) is the trivial identity and
    must be rejected).
  - - (subtraction) orders by EVALUATED value so left_value >= right_value, and
    rejects equal values (result 0 is trivial). The ordering compares
    evaluate_expression(left) vs evaluate_expression(right), not raw ints.
Because construction is bottom-up, the child's value is already in hand; the
check is cheap and pure. If a built subtree's value is forbidden for the
operator being placed above it, redraw the operator or the subtree -- never
mutate the built node.

LEAF-ONLY operators keep their existing leaf-based generation UNCHANGED. Their
invariants remain statements about leaves (divisor >= 2, derived quotient,
exponent power range). Do NOT lift these to values (see Lens 1, section 3).

--- Q1: depth / size control ------------------------------------------------

DECISION: depth, not operator-count. Metric is OPERATOR DEPTH:
  operator_depth(int leaf) = 0
  operator_depth(internal) = 1 + max(operator_depth(left), operator_depth(right))
A flat single-operator node has operator_depth 1. (a+b)*c has 2.

KNOB: module constant _MAX_OPERATOR_DEPTH (>= 1). _MAX_OPERATOR_DEPTH == 1
reproduces the flat #4 generator EXACTLY (a satisfying, assertable property).
Provisional default: 2. NOT a function parameter (see consensus attack,
section 3).

SHAPE CONTROL: at each operand position of a composable node with depth budget
remaining, an INDEPENDENT per-operand Bernoulli choice "subtree or leaf?" with
probability p_recurse. The two operands flip independently; the probabilities
do NOT form a distribution and need not sum to 1. p_recurse is a single scalar
in [0,1]. p_recurse == 0 reproduces flat generation; p_recurse == 1 always
recurses until the depth floor forces leaves. Provisional default: 0.5, as a
module constant (_RECURSE_PROBABILITY).

ASSERTION (the invariant that makes "depth is the knob" true rather than
aspirational): the property test asserts operator_depth(node) <=
_MAX_OPERATOR_DEPTH for every generated tree across the whole hypothesis space.
This catches the most likely implementation bug (an off-by-one in budget
threading).

--- Q2: precedence + parenthesization (the cs showpiece) --------------------

DECISION: precedence is REPRESENTED as an explicit integer tier per operator,
declared on the record. NOT computed, NOT inferred from list position, NOT a
categorical string compared via lookup. A plain int compared with <.
  precedence:    + - => 1 ;  * / % => 2 ;  ^ => 3
  associativity: + - * / % => "left" ;  ^ => "right"
This closes ADR-031's open exponent-associativity item: ^ is right-associative.

THE RENDER RULE (the entire logic; ~8 lines): when rendering an internal node,
render each child; wrap a child in parentheses IFF the child is an internal
node AND
  (child.precedence < parent.precedence)
  OR (child.precedence == parent.precedence AND the child is on the
      associativity-WRONG side: the right child of a left-associative parent,
      or the left child of a right-associative parent).
The current renderer is the degenerate "wrap every internal child" version
(it keys on isinstance(child, dict)). Replace "always wrap" with this rule.

WHY IT IS CORRECT-CRITICAL: the rendered string IS the question; the answer is
computed from the tree structure (evaluate_expression never consults
precedence -- the tree shape is the grouping). The renderer must emit a string
that, read under standard precedence, parses back to THAT tree. A mismatch
silently makes the displayed question and the stored answer disagree. There is
exactly one correct parenthesization per tree; "leave it to chance" or "just go
left-to-right" is not an option (left-to-right is only the associativity half;
it does not resolve cross-tier cases).

TESTING: the renderer is a pure total function with a small exact spec, so test
it EXHAUSTIVELY with HAND-BUILT trees (decoupled from what the generator happens
to emit), table-driven over operator-pair x nested-side, asserting exact
strings. Must cover the same-tier associativity traps:
  a - (b - c)  -> KEEP parens (right child of left-assoc -, same tier)
  a - b + c    -> NO parens   (tree (a-b)+c; left child, same tier)
  a / b * c    -> NO parens   (tree (a/b)*c; left child same tier)
  a * (b / c)  -> KEEP parens (right child of left-assoc *, same tier) REACHABLE
  (a + b) * c  -> KEEP parens (lower-precedence child) -- already tested today
  2 ^ 3 ^ 2    -> hand-built only: 2 ^ (3 ^ 2) right-assoc; NOT generator-reachable

--- Q4: exponent magnitude under nesting ------------------------------------

DECISION: mostly dissolves under the Q3 rule. ^ is leaf-only, so no subtree
ever feeds its base or power; the #4 ceiling (base 2..12, power 2..3, max
12**3 = 1728) stands UNCHANGED. The "subtree as exponent explodes" scenario is
unreachable in #5.

RESIDUAL (a composable operator ABOVE leaf-only nodes can still grow, e.g.
(2^3) * (5^2)): handled by the optional global result ceiling below, NOT by a
new exponent rule.

GLOBAL RESULT CEILING: a CONFIG-controllable parameter, DEFAULT OFF (None) in
#5. The MECHANISM is designed in even though the default is off: a LOCAL
feasibility check at node assembly. Because construction is bottom-up, when
assembling a node both child VALUES are in hand, so check
value(left) <op> value(right) <= ceiling BEFORE committing the node; on
failure redraw the OPERAND (or pick a different operator), not the whole tree.
This co-locates the cost away from the worst case (root-level whole-tree reject
throws away the most work exactly when trees are largest). Do NOT implement
backtracking/subtree-memoization ("travel down and reuse") -- it adds state and
fights purity; the local check already gets the win.
ADR frames the ceiling as a DIFFICULTY-RELEVANT knob #2 may turn, not a fixed
sanity guard #2 should leave alone.

--- Q5: what #5 ships vs what #2 owns ---------------------------------------

DECISION: #5 ships the nesting CAPABILITY with its governing config as module
constants (provisional defaults). #5 does NOT build the difficulty controller
and does NOT expose a depth function-parameter (see Q1 and consensus attack).
#2 adds the parameter together with its real caller when it needs to vary depth
per difficulty.

DOMAIN NOTE (Lens 6): the ADR must state that depth is a STRUCTURAL parameter,
ONE input among several #2 will weigh (operator mix, operand magnitude, depth),
explicitly NOT a difficulty score. 2 + 3 + 4 (depth 2) is easier than 7 * 8
(depth 1); depth != difficulty. This keeps the atom unambiguous for #2.

--- Q6: renderer output stability -------------------------------------------

VERIFIED IN-THREAD:
  - schema: responses.question_text is TEXT NOT NULL (SQLite TEXT, unbounded).
    No length constraint nesting can violate. (drill.py line ~218.)
  - frontend renders question_text via textContent; nested output is digits,
    operators, spaces, parens -- nothing needing escaping.
  - no test pins the flat "a op b" format in a way nesting breaks: the only
    hardcoded shapes are a frontend mock fixture ("6 + 7") and the unrelated
    translate qtype ("hola"/"adios"). test_render_nested_parenthesizes_
    subexpressions uses * over + and asserts (1 + 2) * 3, which a
    precedence-aware renderer KEEPS -- it will not fight the rewrite.
ADD: a regression assertion that a generated max-depth question_text stays
under a sane length (a few hundred chars), doubling as a guard if _MAX_
OPERATOR_DEPTH is later cranked high.

================================================================================
2. PRESUPPOSITIONS SURFACED IN REVIEW (not in the original Q1-Q6)
================================================================================

TERMINATION: bottom-up with reject-and-redraw presupposes a draw eventually
succeeds. For composable operators over the existing ranges it does easily, but
"redraw forever" has no termination proof and #5 compounds it (a redraw at
depth rebuilds a subtree). DECISION: a generous bounded retry. Module constant
_MAX_GENERATION_ATTEMPTS (e.g. 1000). Each redraw loop counts down and RAISES a
clear RuntimeError on exhaustion rather than hanging -- hitting the ceiling is
the SIGNAL of a generation bug, not a thing to absorb (matches the generator's
existing "fail loudly on unknown symbol" stance). The property test asserts
normal generation NEVER raises this (pins "constraints are satisfiable in
practice" as a tested property).

REPRODUCIBILITY: generation is intentionally nondeterministic (determinism is a
property of evaluate over a fixed tree, not of generate). DECISION: production
stays nondeterministic; NO seed parameter is threaded (no caller needs it,
single-user). Tests achieve reproducibility by seeding the global random RNG
(random.seed(N)) when an example test wants a specific tree. ADR states this;
note global-seed tests are order-sensitive if they share process state -- follow
the existing _support/test pattern.

CONFIG SHAPE (Lens 4 incidental find): there is NO CONFIG class; OPERATOR_
SYMBOLS is a module global (drill.py line ~149). The generate_expression
docstring's reference to "CONFIG.OPERATOR_SYMBOLS" (line ~1382) is STALE. New
constants (_MAX_OPERATOR_DEPTH, _RECURSE_PROBABILITY, _MAX_GENERATION_ATTEMPTS,
and the ceiling default) follow the ACTUAL module-global pattern, placed beside
OPERATOR_SYMBOLS. Fix the stale docstring while in there.

================================================================================
3. ADVERSARIAL REVIEW OUTCOME (six lenses, grounded in the code)
================================================================================

Lens 1 DATA/TRANSFORM: OVERTURNED a detail. "Lift checks to value" is too
  coarse and WRONG for leaf-only operators -- the property test for % asserts
  node["right"] >= 2 (the divisor LEAF), for / the derived quotient over leaves,
  for ^ the exponent leaf. A blanket evaluate-and-recheck would corrupt these.
  FIX: the test is a RECURSIVE DISPATCHING WALK -- descend the tree, apply each
  internal node's invariant at that node with the correct referent (VALUE-based
  for + - *, LEAF-based for / % ^). Not "evaluate everything."

Lens 2 SIMPLICITY/STATE: confirms. The feature is three separable coherent
  changes (precedence+renderer; nestable+bottom-up generator; ceiling-dark),
  coupled by the feature not by convenience -- which is good news for the sort.
  Purity holds (build-then-choose, no mutation).

Lens 3 REAL vs SPECULATIVE: OVERTURNED the depth parameter. The single caller
  (drill.py ~2173) is generate_expression(enabled_symbols); nothing varies
  depth. A depth PARAMETER with only a default and no caller is the exact
  speculative interface ADR-028 warns against ("write the concrete caller
  first"). FIX: ship depth as a MODULE CONSTANT; #2 adds the parameter with its
  real caller.

Lens 4 USAGE BEFORE INTERFACE: confirms Lens 3 and adds: generate_expression's
  SIGNATURE DOES NOT CHANGE. The internal helper is build_subtree(symbols,
  remaining_depth) calling random.* directly -- NO rng parameter (threading rng
  is speculative seedability Lens 3 already killed; tests seed the global).
  Also surfaced the stale CONFIG docstring.

Lens 5 STRUCTURE/INTENT: confirms. precedence/associativity/nestable are
  DECLARED per record (the ADR-027 "cannot silently inherit the wrong meaning"
  pattern), not computed. The tree stays the single source of grouping truth;
  the parenthesized string is recomputed from the tree every render, never
  denormalized/stored.

Lens 6 DOMAIN CORRECTNESS: one fix. Depth must not be implied to EQUAL
  difficulty (a deep sum can be easier than a flat product). ADR states depth
  is structural, one input among several for #2. The ceiling, when #2 turns it
  on, is likewise a difficulty knob, not just a guard.

CONSENSUS ATTACK (Lenses 3 + 4 converge): _MAX_OPERATOR_DEPTH is a MODULE
CONSTANT, not a function parameter. generate_expression's public signature is
unchanged. This makes #5 SMALLER and guardrail-aligned. Acted on.

Separately, Lens 1 is a must-fix: the property-test rewrite is a dispatching
tree walk, not a blanket value-recheck. Acted on.

The spine survived every lens: bottom-up, nestable bool, precedence-on-records,
renderer-is-sole-printer.

================================================================================
4. WHAT MUST NOT BE REOPENED (from the brief section 4, still binding)
================================================================================
- Node shape {op,left,right} with int leaves (ADR brief 2A). No dataclass
  (ADR-030, deferred to #2).
- Operator-record design (ADR-027). New fields (nestable, precedence,
  associativity) are ADDED to the existing record shape, not a new structure.
- No new operators, no unary/n-ary (ADR-029).
- No generic per-operand-range override (ADR-028): nestable is a plain bool,
  NOT subtree_positions; the global ceiling is a single value, not a
  per-operator knob. Widen only when a concrete caller (#2) needs it.
- Pure LOGIC only: no clock, no IO, no HTTP/schema/frontend change.
- stdlib + Bottle only; no new runtime dep (ADR-001). (hypothesis is test-only.)
- "Nothing too clever": explicit integer precedence + declared fields over
  magic. No backtracking/memoization for the ceiling.

================================================================================
5. COMMIT PLAN (topologically sorted; each lands GREEN)
================================================================================
Ordering principle: each commit leaves the suite green. Renderer correctness
lands BEFORE the generator emits trees that exercise it, so no commit ever
ships a generator producing strings the renderer prints wrong. Record-field
additions land before the code that reads them. Docs last.

Identifiers C-D5a .. C-D5f. Classification: HAIKU = mechanical / low-judgment /
tightly specified; SONNET = judgment, cross-cutting, or correctness-critical.

--- C-D5a  ADD declarative fields to operator records  [HAIKU] --------------
WHAT: add three fields to every OPERATOR_DEFINITIONS record: nestable (bool),
  precedence (int), associativity ("left"|"right"). Add them to _OPERATOR_
  RECORD_REQUIRED_KEYS so _build_operator_table validates completeness. Values:
    +  nestable T, prec 1, left
    -  nestable T, prec 1, left
    *  nestable T, prec 2, left
    /  nestable F, prec 2, left
    %  nestable F, prec 2, left
    ^  nestable F, prec 3, right
WHY GREEN: pure data addition; nothing reads the fields yet; the table
  validator now requires them (a record missing one fails loudly at import).
TESTS: extend the existing record-completeness/validation test to assert the
  new required keys are present and well-typed for all six operators.
RISK: low. Pure additive data.

--- C-D5b  precedence-aware renderer + exhaustive table test  [SONNET] ------
WHAT: replace render_expression's "wrap every internal child" with the Q2 rule
  (wrap iff internal AND lower precedence OR same-precedence wrong-side). Reads
  precedence/associativity from the records added in C-D5a.
WHY GREEN/ORDER: lands BEFORE the generator nests, so the renderer is proven
  correct on hand-built trees independent of generator output. The existing
  test_render_nested_parenthesizes_subexpressions ((1+2)*3) still passes (lower
  precedence child still wrapped).
TESTS: new table-driven exhaustive test in test_logic.py over operator-pair x
  nested-side with exact-string assertions, covering all traps in Q2 (a-(b-c)
  keeps, a-b+c drops, a/b*c drops, a*(b/c) keeps, 2^(3^2) right-assoc
  hand-built). This is the cs showpiece; assert exact strings, not "contains".
RISK: medium. Correctness-critical; the associativity wrong-side cases are
  where a plausible-looking renderer is wrong. SONNET.

--- C-D5c  bottom-up generator + module config (depth, recurse, retry)  [SONNET]
WHAT: rewrite generate_expression internals to bottom-up via an internal helper
  build_subtree(symbols, remaining_depth) (calls random.* directly; NO rng
  param; signature of generate_expression UNCHANGED). Add module constants
  beside OPERATOR_SYMBOLS: _MAX_OPERATOR_DEPTH (default 2), _RECURSE_PROBABILITY
  (0.5), _MAX_GENERATION_ATTEMPTS (1000). Composable operators may recurse
  (per-operand Bernoulli); leaf-only operators always take integer leaves via
  their existing strategies. Constraint lifting for + - * (value-based forbid;
  subtraction orders by evaluated value). Bounded-retry loops raise RuntimeError
  on exhaustion. Fix the stale CONFIG.OPERATOR_SYMBOLS docstring.
WHY GREEN/ORDER: renderer (C-D5b) already prints any tree correctly, so a
  generator that now emits trees is safe. _MAX_OPERATOR_DEPTH default 2 means
  output changes from flat to possibly-nested -- the property test update lands
  in the SAME commit (welded site).
TESTS (welded; this is the test rewrite Lens 1 sharpened):
  - rewrite test_generator_property.py as a RECURSIVE DISPATCHING WALK: descend
    the tree; assert at each internal node the invariant for ITS operator with
    the correct referent (value-based + - *; leaf-based / % ^); assert leaves
    are int; assert every internal op in the requested symbol subset.
  - assert operator_depth(node) <= _MAX_OPERATOR_DEPTH across the space.
  - assert normal generation never raises the retry-exhaustion error.
  - keep/adjust the example tests in test_logic.py: division-always-integral
    still holds; add a depth==1-reproduces-flat example (set the constant or
    drive p_recurse=0 via a seeded test) and a nested-generation example.
RISK: high. The spine. Welded test site. SONNET.

--- C-D5d  global result ceiling mechanism, default OFF  [SONNET] -----------
WHAT: add the ceiling as a module constant default None and wire the LOCAL
  feasibility check into build_subtree's node-assembly point (value-in-hand;
  redraw operand on failure; counts against _MAX_GENERATION_ATTEMPTS). With
  default None the check is a no-op -- behavior identical to C-D5c.
WHY GREEN: default off => no behavioral change => suite stays green. Lands the
  mechanism dark so #2 flips a value with zero plumbing.
TESTS: a test that SETS a low ceiling (via the constant, seeded) and asserts
  every generated tree's evaluated result <= ceiling and that an
  infeasible-too-low ceiling raises the retry-exhaustion error (proves the
  mechanism, not just the default).
RISK: medium. Isolated behind an off-by-default flag, but the assembly-point
  wiring touches the spine. SONNET. (Could fold into C-D5c; kept separate so
  the dark mechanism is reviewable in isolation.)

--- C-D5e  question_text length regression guard  [HAIKU] -------------------
WHAT: a test asserting a generated max-depth arithmetic question_text stays
  under a sane length bound (e.g. < 400 chars). No production change.
WHY GREEN: pure test addition; current output is well under any sane bound.
TESTS: the guard itself.
RISK: low. HAIKU.

--- C-D5f  docs: ADRs + close ADR-031 open item  [HAIKU] --------------------
WHAT: decisions.md ADRs for: (1) bottom-up + composable/leaf-only split + the
  "nestable governs children not child-hood" reading + value-vs-leaf constraint
  lifting; (2) precedence integers + associativity + the render rule; (3) depth
  as a module constant + p_recurse + depth-is-structural-not-difficulty; (4)
  the dark result ceiling as a difficulty knob; (5) bounded retry / fail-loud;
  (6) nondeterministic generation, test-time seeding, no seed param. CLOSE
  ADR-031's exponent right-associativity open item. Name the DEFERRED doors for
  #2 explicitly (per-position subtree control; making / % ^ nestable via
  derive-compatible-sibling; ceiling default; p_recurse/depth defaults) as
  convenience-not-principle.
WHY GREEN: docs only.
RISK: low. HAIKU.

PLAN-LEVEL NOTES:
- C-D5d MAY be folded into C-D5c if the reviewer prefers one spine commit;
  kept separate for isolated review of the dark mechanism. Implementer's call.
- If C-D5c's property-test rewrite proves large, the test change may be split
  from the production change ONLY IF an intermediate green state exists; it
  likely does not (the moment depth default is 2, the old isinstance==int
  assertion fails), so expect them welded.

================================================================================
6. WORKFLOW CONTRACT (standing; unchanged)
================================================================================
At each commit boundary: edit in-sandbox, run bash tests/run.sh (bash not sh),
COMMIT in-sandbox with the agreed message, then deliver the TRIPLE:
  (a) SUMMARY ending with a "files modified" list;
  (b) PATCH = git diff <prev_sha> HEAD --relative from inside drill/ (paths
      start drill.py / tests/... / llm/...), delivered as a DOWNLOADABLE file,
      NOT pasted inline;
  (c) COMMIT MESSAGE: scope(drill/section): imperative; bullets; final line =
      identifier (e.g. C-D5a).
The user applies each patch from a byte-intact download and commits with the
provided message. Sandboxes are separate; the patch IS the transfer, so commit
in-sandbox so patches map one-to-one onto the user's commits.

Expected end state: suite green at each commit; final count rises by the new
tests (renderer table test, depth/walk property assertions, ceiling test,
length guard). Record the exact new totals when C-D5f lands.
