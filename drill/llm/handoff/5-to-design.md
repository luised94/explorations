# Launch kit: roadmap #5 -- generalize expression generation (nested trees)

This is a DESIGN-thread brief, not a locked commit plan. Unlike the D2 handoff
(whose design was settled and whose thread only implemented), #5's design is
OPEN: precedence, parenthesization, depth control, and the difficulty-facing
shape are real decisions to be made WITH you in-thread, possibly with searches
or papers you upload. This brief frames the open questions sharply, records what
the code already locks, and names what must NOT be reopened, so the design
conversation starts from the right place instead of re-deriving context.

The output of that thread is: (a) settled design decisions, (b) a locked
commit plan in the D2 style, (c) then implementation commit-by-commit per the
workflow contract. This brief feeds step (a).

ASCII only. Single-user assumption holds throughout.

================================================================================
0. SETUP (same as every thread)
================================================================================
Sparse-clone drill/, verify the SHA the user supplies (do not guess it),
`uv sync --group test`, `npm install jsdom --no-save` (Node 18+),
`bash tests/run.sh` (bash, not sh). Baseline at the post-#4 SHA: 179 green
(backend 104, frontend 75), ending "ALL GREEN". If NOT 179 green on a clean
clone at the verified SHA, STOP and report (collection/import/syntax errors
count as red). Attach: drill.py, llm/spec.md, llm/decisions.md, llm/roadmap.md,
this brief.

================================================================================
1. WHAT #5 IS
================================================================================
Today generate_expression builds a FLAT single-operator node: one op, two int
leaves. #5 makes the generator produce NESTED multi-operator trees -- the same
{op, left, right} shape, but left/right may themselves be nodes. The roadmap
calls this "the meaty one" and the cs payoff of Phase 1.

The leverage point (verified in code): evaluate_expression and render_expression
ALREADY recurse over arbitrary trees. evaluate_expression handles a dict-or-int
node recursively; render_expression recurses and parenthesizes any nested dict
operand. So #5 is mostly:
  (1) a recursive/iterative generate_expression that emits depth > 1 trees, and
  (2) precedence-aware parenthesization in the renderer (the current renderer
      over-parenthesizes -- correct but ugly: it wraps EVERY nested operand).
Plus the property tests that must now hold over trees, not just flat nodes.

This is a LOGIC-only change. No schema change, no HTTP contract change. Frontend
renders question_text via textContent and is untouched (confirm before relying
on it). The validator is unaffected: trees still evaluate to one integer.

================================================================================
2. WHAT THE CODE ALREADY LOCKS (constraints, not decisions)
================================================================================
These are facts about the current tree at the baseline SHA. Design around them;
do not relitigate them as part of #5.

A. NODE SHAPE IS FIXED: {"op": symbol, "left": node|int, "right": node|int};
   leaves are plain ints. evaluate_expression and render_expression already
   assume exactly this. Keep it. (A dataclass promotion is deferred to #2 per
   ADR-030; do not introduce it here.)

B. OPERATORS ARE RECORDS (post-#4, ADR-027): OPERATOR_DEFINITIONS is one record
   per operator carrying symbol, name, arity, range(s), forbid_identity,
   forbid_identity_referent, result_constraint, eval_fn, operand_strategy.
   Six operators enabled: + - * / % ^. The generator picks an operator and asks
   its operand_strategy for a (left, right) pair. #5 must decide how strategies
   compose when an operand is itself a subtree (see open question Q3).

C. EXISTING INVARIANTS THAT MUST SURVIVE (currently asserted in
   test_generator_property.py over flat nodes; #5 must preserve them over
   trees): integer result; deterministic re-evaluation; forbidden-identity
   avoidance per each operator's declared referent; division exactness;
   subtraction non-negativity (result_constraint); modulo divisor >= 2;
   exponent result >= 1 and bounded. The hard question is what these MEAN for an
   interior node whose operands are subtrees (Q3).

D. ARITY IS A FIELD, ALL CURRENT OPERATORS BINARY. Trees are binary. Do not add
   unary/n-ary operators here (factorial etc. are deferred, ADR-029).

E. EXPONENT IS RIGHT-ASSOCIATIVE (ADR-031, flagged in #4 for #5): 2^2^3 =
   2^(2^3), unlike + - * /. The flat #4 generator never associated, so it was a
   non-issue. #5 nests, so this is now LIVE and is the canonical example for the
   precedence/associativity question (Q2). This brief does not pre-decide it.

================================================================================
3. THE OPEN DESIGN QUESTIONS (decide WITH the user in-thread)
================================================================================
These are genuinely open. Each names the tension and some options, NOT a
verdict. Expect to iterate; some may want a search or a paper.

Q1. DEPTH / SIZE CONTROL. How is tree size bounded and chosen?
    - Options: fixed depth; max-depth with random shape; target operator-count
      (n internal nodes); weighted by depth. The roadmap notes Catalan-number
      uniform sampling over tree shapes was CONSIDERED AND SET ASIDE as overkill
      (roadmap section 5) -- revisit only if guaranteed structural diversity is
      wanted. Default expectation: a simple max-depth or op-count knob, since #2
      (difficulty) is the real consumer of this knob (see Q5).
    - Tension: pedagogy (is a 5-deep tree useful to drill, or just noise?) vs
      implementation simplicity vs giving #2 something clean to turn.

Q2. PRECEDENCE + PARENTHESIZATION. The renderer currently wraps every nested
    operand. Real math notation parenthesizes by PRECEDENCE and ASSOCIATIVITY:
    2*3+4 needs no parens; 2*(3+4) does; 2^2^3 associates right.
    - Decisions needed: a precedence order over the six operators (where do %
      and ^ sit?); associativity per operator (^ is right, others left); when to
      emit parens (only when child precedence < parent, plus the
      same-precedence-wrong-side associativity case). Does the GENERATOR need to
      know precedence, or only the RENDERER? (Cleanest: generator builds any
      tree; renderer is the sole owner of precedence-correct printing.)
    - This is the instructive cs core. A standard reference on operator-
      precedence printing / minimal parenthesization may be worth pulling in.
    - Watch: the rendered string is the QUESTION; its parenthesization must
      match the evaluation order the answer assumes, or the drill is wrong. This
      is the correctness crux of the whole feature.

Q3. OPERAND STRATEGIES VS SUBTREES (the deepest one). Today an operand_strategy
    returns two INT leaves and enforces per-operator constraints on them
    (divisor >= 2, non-negative subtraction, exact division, etc.). When an
    operand is a SUBTREE, what do those constraints check against?
    - Division must stay exact: if the dividend is a subtree, its VALUE must be
      a multiple of the divisor -- but the subtree's value is only known after
      generation. Options: generate the subtree first then derive a compatible
      sibling; restrict which operators may sit under which (e.g. division's
      dividend is always a leaf or a value-controlled subtree); or generate-
      and-reject. Each has very different complexity.
    - Subtraction non-negativity, modulo divisor range, exponent magnitude
      bound: same problem -- a constraint stated over leaves now ranges over
      subtree VALUES. The forbid_identity_referent work in #4 (ADR-027) was
      partly to make "what is checked against" explicit; #5 extends that axis
      from leaves to evaluated subtrees.
    - This likely forces a "generate bottom-up, know each subtree's value as you
      build" approach rather than top-down shape-then-fill. Name the approach
      explicitly; it is the design's spine.

Q4. EXPONENT MAGNITUDE UNDER NESTING. Exponent is bounded in #4 (base 2..12,
    power 2..3, ceiling 12^3 = 1728). Under nesting, a subtree could feed a huge
    base, or (worse) a subtree could be an EXPONENT, and 12^(something) explodes.
    Decide: cap result magnitude globally? forbid exponent above a certain
    depth? forbid exponent-of-exponent? This interacts with Q1 and Q3.

Q5. WHAT #5 SHIPS VS WHAT #2 OWNS. Per ADR-031, "all operators enabled, uniform
    sampling" is a provisional default #2 (difficulty) supersedes. #5 adds depth
    as a new axis. Decide the seam: #5 should expose depth/size as a PARAMETER
    with a provisional default, the same way operator-set is exposed, so #2 can
    later drive it -- but #5 should NOT build the difficulty controller (that is
    #2, gated on #5 per the dependency graph A2 -> A3). Keep the knob; defer the
    hand on the knob.

Q6. RENDERER OUTPUT STABILITY. question_text is stored in responses and read by
    the frontend via textContent. Confirm nested rendering introduces no
    characters needing escaping (it should not -- digits, operators, spaces,
    parens) and that no existing test pins the flat "a op b" format in a way
    that nesting breaks (grep for hardcoded question_text shapes).

================================================================================
4. DECISIONS THAT MUST NOT BE REOPENED
================================================================================
- The node shape (section 2A) and the operator-record design (2B / ADR-027).
- No dataclass promotion (ADR-030, deferred to #2).
- No new operators, no unary/n-ary (ADR-029).
- No generic per-operand-range override (ADR-028 finding D): if nesting needs
  per-position control, write the concrete caller first.
- Layering invariant: this is pure LOGIC. No clock, no IO, no HTTP changes.
- Forward-only mindset (no schema change here, but standing).

================================================================================
5. SUGGESTED SHAPE OF THE THREAD (not binding)
================================================================================
1. Design conversation: settle Q1-Q6, in roughly that order (Q3 is the spine;
   Q2 is the cs showpiece). Use searches / uploaded papers as needed for
   precedence printing and tree generation. Record conclusions as you go.
2. Lock a commit plan in the D2 style: topologically sorted, each commit landing
   green, classified HAIKU/SONNET, with the property-test changes called out
   (the flat-node assertions become tree assertions -- expect a welded test site
   like #4 had).
3. Implement commit-by-commit per the workflow contract (section 6).
4. Final docs commit: ADRs for the precedence order, the associativity handling,
   the subtree-constraint approach (Q3), and the depth knob's provisional
   default -- plus resolve the ADR-031 exponent-associativity open item.

================================================================================
6. WORKFLOW CONTRACT (standing, unchanged from D1/D2)
================================================================================
At each commit boundary: make edits in-sandbox, run the suite, COMMIT in-sandbox
with the agreed message, then deliver the TRIPLE:
  (a) SUMMARY ending with a "files modified" list;
  (b) PATCH cut as `git diff <prev_sha> HEAD --relative` from inside drill/
      (paths start drill.py / tests/... / llm/...), delivered as a downloadable
      file -- NOT pasted inline (paste corrupts whitespace; download and apply);
  (c) COMMIT MESSAGE: scope(project/section): imperative; bullets; final line =
      identifier (e.g. C-D5a).
The user applies each patch from a byte-intact download (git apply from inside
drill/, or `git apply --directory drill` from the repo root) and commits with
the provided message. Claude's sandbox and the user's repo are SEPARATE; the
patch IS the transfer, so Claude must actually commit in-sandbox so patches map
one-to-one onto the user's commits.

================================================================================
7. STATE AT HANDOFF
================================================================================
- Baseline: post-#4, suite 179 green (backend 104, frontend 75), "ALL GREEN".
- #4 landed six commits (C-D2a..C-D2f): operator-record refactor + modulo and
  exponent. Relevant ADRs: ADR-027 (one record per operator; explicit referent;
  subtraction intent), ADR-028 (own-strategy named ranges; no generic override),
  ADR-029 (deferred operators + "easy operator" gate), ADR-030 (deferred to #2:
  Approach B + dataclass), ADR-031 (provisional defaults; exponent right-
  associativity OPEN for #5 -- this thread closes it).
- Nothing in #5 is started. The tree is clean at the baseline SHA.
- The user drives the SHA/pin and will supply it in the launch brief; do not
  hard-code it.
