# Handoff: D2 design+plan complete -> implementation thread (#4 operators)

Forward-looking and prescriptive. The DESIGN and COMMIT PLAN for roadmap #4
(arithmetic operators: add modulo and exponent) are LOCKED. The next thread
IMPLEMENTS the plan below commit by commit; it does not re-open the design.
Decisions that were settled in planning are recorded in section 4 with their
rationale so they are not re-litigated. The decisions.md ADRs themselves are
deliberately NOT written yet -- they land as the final commit (C-D2f) once the
code is real, so the decision log never describes code that does not exist.

================================================================================
1. CURRENT STATE
================================================================================
- Nothing in #4 is implemented. This thread did design + planning ONLY. The
  tree is clean at the baseline SHA; the next thread starts at C-D2a.
- Baseline at the pinned SHA: suite 177 green (backend 102, frontend 75 =
  6/21/19/23/6), ending "ALL GREEN". This is the post-D1 end-state.
- The cut point is a commit boundary with nothing half-done -- the cheapest
  possible handoff state. No re-derivation required.
- The user manages the SHA/pin (the repo may host more than one project). The
  next thread is told the SHA by the user via the launch brief; do not assume
  or hard-code it.

================================================================================
2. WHAT #4 IS (scope, stated honestly)
================================================================================
This is a STRUCTURAL REFACTOR + 2 OPERATORS, not "add dict entries." The
refactor is enabling work for the feature AND for #2 (difficulty); it is
scope-by-correction, not creep -- name it that way. The operators (modulo,
exponent) cannot be added cleanly until the refactor lands, because today the
definition of one operator is scattered across four structures plus hidden
symbol-string branches (see section 4, finding A).

NO SCHEMA CHANGE. #4 is pure LOGIC; the migration apparatus stays dormant.
Operators FEED evaluate_expression and the existing numeric validator; they do
NOT fork validate_answer's qtype dispatch (guardrail).

Frontend is UNTOUCHED throughout. index.html renders payload.question_text via
textContent (verified ~line 1458); operator symbols are entirely server-side.
No escaping concern, no operator logic in the client.

GUARDRAILS (drill-specific): stdlib + Bottle only, no new runtime deps
(ADR-001) -- the one stdlib addition here is `import operator`. "Nothing too
clever": data-first, explicit declarations over magic numbers. Forward-only
migrations (N/A for #4 but standing).

================================================================================
3. THE LOCKED COMMIT PLAN (topologically sorted; land each green)
================================================================================
Six commits. Classification: HAIKU = one atomic idea; SONNET = one coherent
movement (code + its forced tests); no OPUS remains (the original refactor opus
was split into C-D2d1 + C-D2d2).

  C-D2a  HAIKU   drill.py
    Goal: rename the local variable `operator` -> `operator_record` in the four
      functions that bind it: _generate_operands_standard (param+body),
      _generate_operands_division (param+body), evaluate_expression (local),
      _build_operator_table (loop var). Pure rename, no behavior change.
    Why first: C-D2c adds `import operator`; a local named `operator` would
      shadow the module. Free the name before the import.
    Green: 177 unchanged. After editing, grep `\boperator\b` for any stray
      local still bound to the old name.

  C-D2c  SONNET  drill.py
    Goal: add `import operator` (alphabetical slot between json and os); delete
      _add/_subtract/_multiply/_divide; map symbols to operator.add / .sub /
      .mul / .floordiv in _OPERATOR_EVAL_FUNCTIONS. Preserve _divide's ADR-007
      rationale (why floor division is always exact) as a COMMENT on the `/`
      entry -- that is the only knowledge being lost otherwise.
    Edge: depends on C-D2a (name freed).
    Green: 177 unchanged. The four fns are referenced ONLY in
      _OPERATOR_EVAL_FUNCTIONS; no test imports them (grepped). No predicted
      red.
    NOTE: C-D2b was intentionally merged here (the import and the deletion are
      one thought). There is no separate C-D2b.
    NAMING CONVENTION (user): full namespace, no alias -- `operator.add`, never
      `import operator as op`. No abbreviations in new identifiers.

  C-D2d1 HAIKU   drill.py
    Goal: extract the repeated operand-range literals into named constants --
      _DEFAULT_OPERAND_RANGE = (1, 20) and _MULTIPLICATIVE_OPERAND_RANGE =
      (2, 12) -- and reference them. The repetition (1,20 on + and -; 2,12 on *
      and /) is a magic-number smell: equal values that are really shared
      named defaults, not coincidence.
    Green: 177 unchanged (values identical; pure extract-constant).

  C-D2d2 SONNET  drill.py
    Goal: consolidate the four scattered structures (OPERATOR_CONFIG,
      _OPERATOR_EVAL_FUNCTIONS, _OPERATOR_OPERAND_GENERATORS, and the hidden
      `if symbol == "-"` branches) into ONE list of records: OPERATOR_DEFINITIONS
      (Option 1: list of record dicts). Each record carries symbol, name,
      arity, range(s), the trivial-rejection rule, eval_fn, and operand
      strategy. Then:
        - Subtraction: replace the two `if symbol == "-"` branches with a single
          declared INTENT field, result_constraint: "non_negative" (see section
          4, finding C). The strategy implements ordering + equal-operand
          rejection together as one intent, not two independent knobs.
        - forbid_identity referent: make it EXPLICIT per strategy (section 4,
          finding B). Today it silently means different things (standard: raw
          operands; division: the quotient). The strategy must own/declare what
          its forbidden set is checked against, so new operators do not
          re-litigate it.
        - Slim _build_operator_table to validate RECORD COMPLETENESS (required
          keys present, eval_fn callable, strategy known) rather than join four
          sources. Keep the import-time ValueError loud-failure guard.
        - Delete _OPERATOR_EVAL_FUNCTIONS and _OPERATOR_OPERAND_GENERATORS
          (folded into records).
    Edge: depends on C-D2d1 (records reference the constants) and C-D2c
      (records hold operator.add etc.).
    Green: 177 PREDICTED green (behavior preserved). WATCH
      test_generator_property.py:75 (the `if op == "-": assert result >= 0`
      branch). It is predicted green; if it REDDENS, that red is INFORMATIVE --
      it means the intent-field refactor broke subtraction's non-negativity.
      Stop and fix before proceeding; do not paper over it. This is the one
      "let it go red as evidence" guard in the plan -- a diagnostic red, not a
      planned one.

  C-D2e  SONNET  drill.py, tests/test_logic.py, tests/test_generator_property.py
    Goal: add the two operators as records + their strategies, enable them by
      default, and fix/extend the two welded test sites IN THIS COMMIT.
        - Modulo "%": eval_fn operator.mod. Divisor drawn >= 2 from the
          multiplicative range; left operand from the default range; a < b IS
          ALLOWED (a % b == a is a legitimate, non-trivial case -- user's call).
          Trivial-rejection referent is the DIVISOR (divisor of 1 -> x % 1 == 0
          always). Add its own operand strategy.
        - Exponent "^": eval_fn operator.pow. Its OWN strategy
          (_generate_operands_exponent), mirroring _generate_operands_division:
          base from one range (2..12), exponent from its OWN narrow range
          (2..3) declared on the exponent record. forbid exponent 0 and 1
          (x^0 == 1, x^1 == x). The narrow exponent range keeps results integer
          and UI-tractable; both ranges are plain record fields, hand- or
          difficulty-adjustable later.
        - Enable "%" and "^" by default in OPERATOR_SYMBOLS.
        - WELDED FIX 1: test_logic.py:185 uses ["%"] as its UNKNOWN-symbol
          example. Enabling "%" makes that assert-raises test wrong. Change the
          sentinel to a genuinely-never-valid symbol (e.g. "$") in this commit.
        - WELDED FIX 2: test_generator_property.py auto-extends
          (_ALL_SYMBOLS = OPERATOR_SYMBOLS), so it runs against % and ^ the
          moment they are enabled. Its `if op == "/" ... else` forbidden-referent
          branch (lines ~61-67) will MIS-ASSERT for % (divisor-referent) and ^
          (right-operand-referent). Add explicit % and ^ branches asserting the
          correct referent and each operator's invariant (modulo: 0 <= result
          and result == left % right with divisor >= 2; exponent: result >= 1,
          magnitude bounded by the 2..3 ceiling). Without these the new operators
          pass VACUOUSLY.
        - Add example-based tests in test_logic.py mirroring the existing +/ /
          examples (one eval + one render each for % and ^).
    Green: suite > 177 (new assertions exercise % and ^ non-vacuously; the two
      welded sites fixed in-commit). Report the new total after the run; do not
      hard-code it before observing it.

  C-D2f  HAIKU   llm/decisions.md
    Goal: write the ADRs for what landed. (a) The operator-record refactor --
      frame as UPHOLDING ADR-007 (data-driven ranges/identities), not
      contradicting it. (b) Deferred Tier B/C operators with revisit criteria
      (section 4, finding E). (c) Deferred to #2: full per-operand-range
      generalization (Approach B) and the dataclass promotion (Option 3), each
      with its trigger. (d) Note exponent right-associativity is an OPEN
      question for #5. (e) Note "all six operators enabled, uniform sampling" is
      a provisional default that #2 (difficulty) supersedes -- so a future
      reader does not mistake it for a considered pedagogical choice.
    Green: unchanged from C-D2e (docs only).

Sequence rationale: a -> c (name freed before import) -> d1 (de-magic before
records move) -> d2 (records reference constants + stdlib fns) -> e (clean
structure before new operators) -> f (docs reflect landed reality).

================================================================================
4. DESIGN CONCLUSIONS -- SETTLED; DO NOT RE-OPEN
================================================================================
These came out of an adversarial-lens critique in planning. They are the "why"
behind the plan; re-deriving them wastes the thread.

A. THE TOUCH LIST IS A DATA SMELL, NOT JUST CONFIG. One operator's definition
   is scattered across OPERATOR_CONFIG + _OPERATOR_EVAL_FUNCTIONS +
   _OPERATOR_OPERAND_GENERATORS + OPERATOR_SYMBOLS, joined by the symbol string
   as an implicit foreign key, plus subtraction's behavior hidden as
   `if symbol == "-"` branches inside a function named "standard."
   _build_operator_table exists only to re-join these and validate the join --
   the validation is the code defending against the distribution it created.
   The refactor (C-D2d2) collapses this to one record per operator. That is the
   point of #4's refactor.

B. forbid_identity HAS TWO MEANINGS TODAY (extract the implicit into the
   explicit). In _generate_operands_standard it is checked against the RAW
   OPERANDS (line ~1143). In _generate_operands_division it is checked against
   the derived QUOTIENT (line ~1166). The property test even hard-codes this
   split (`if op == "/"` checks quotient, `else` checks operands). Adding modulo
   (referent = divisor) and exponent (referent = right operand) adds two MORE
   referents. So the real axis is not "forbidden values" but "forbidden WHAT."
   Each strategy must own/declare its referent. Do NOT ship a bare int list
   whose meaning floats with the strategy.

C. SUBTRACTION = ONE INTENT, NOT TWO KNOBS. The two branches (force left >=
   right; reject left == right) jointly serve ONE goal: non-negative,
   non-trivial results. Splitting them into two independent boolean fields lets
   a future editor set them inconsistently (e.g. descending but allowing equal
   -> 5 - 5 = 0; or forbidding equal but not ordering -> negatives leak).
   Declare the INTENT (result_constraint: "non_negative") and let the strategy
   implement both mechanics together. Declare the invariant, not the steps.

D. NO GENERIC PER-OPERAND-RANGE OVERRIDE (consensus of three lenses; killed in
   planning). An earlier draft proposed a generic "per-operand range override"
   field on every record as a hook for the future. It was DROPPED because:
   (1) it had no caller in the commit that introduced it (untested by
   construction); (2) the established sibling pattern -- division already solves
   "two ranges" with its OWN named strategy (_generate_operands_division) --
   shows the honest interface is "exponent gets its own strategy with two named
   ranges," not a generic indexed override invented ahead of its only caller;
   (3) a generic indexed override repeats the magic-list mistake one level up.
   Exponent declares base + exponent ranges on its own record and its own
   strategy reads them. Generalize to all-operators (Approach B) ONLY when #2
   has a real consumer for per-position ranges. WRITE THE CALLER FIRST.

E. DEFERRED OPERATORS + revisit criteria (record as ADR in C-D2f):
   - True division (float result): deferred. Trigger to revisit = the first
     feature that genuinely needs non-integer results. Cost when revisited:
     change evaluate_expression's -> int contract or add a per-operator
     result_type, plus a real decimal/tolerance policy. (The numeric validator
     already parses floats + supports tolerance, so the validator is NOT the
     blocker -- the -> int contract and _divide's // are.)
   - GCD / LCM: deferred. They are FUNCTIONS, not infix operators -- they break
     the renderer's infix assumption (render_expression emits "left op right").
     Revisit alongside #5 (nested trees), which generalizes the renderer anyway.
   - Factorial: deferred. UNARY; the table assumes arity 2 (it is a field).
     Revisit when unary support is otherwise needed.
   - THE REVISIT GATE (one sentence): an operator is "easy" (addable as a record)
     iff it is binary, integer-in / integer-out with bounded magnitude, and
     renders infix. Anything failing that test is a structural change, not a
     record.

F. OPEN FOR #5 (note, do not implement in #4): exponent is RIGHT-ASSOCIATIVE
   (2^2^3 = 2^(2^3)), unlike + - * /. The flat #4 generator never associates,
   so it is a non-issue now. But #5 nests, and a naive renderer/generator will
   get exponent associativity wrong. The renderer currently parenthesizes any
   nested dict operand unconditionally (verified ~lines 1300-1303), which is
   safe-but-over-parenthesizing -- precedence-aware parenthesization is the #5
   subtlety. Flag, do not fix here.

================================================================================
5. WORKFLOW CONTRACT (standing; from D1)
================================================================================
At EACH commit boundary, Claude (in its sandbox) will: make edits, run the
suite, COMMIT in-sandbox with the agreed message, then deliver a TRIPLE:
  (a) a SUMMARY ending with an explicit "files modified" list;
  (b) a PATCH cut as `git diff <prev_sha> HEAD --relative`, presented as a
      downloadable file (paths start with llm/..., tests/..., drill.py so they
      apply from inside drill/);
  (c) the COMMIT MESSAGE (scope(project/section): imperative; bullets; final
      line = identifier, e.g. C-D2a).
The user reviews the diff, `git apply`s the patch from inside drill/, and
commits with the provided message. Claude's sandbox and the user's repo are
SEPARATE; nothing syncs -- the patch IS the transfer. Claude must actually
COMMIT in-sandbox so patches map one-to-one onto the user's commits.

`git apply` gotchas: cut with `--relative` from drill/ so paths do not carry a
`drill/` prefix. If `git apply --check` says "already applied" on some files,
the user's local state is ahead there -- cut a narrower patch of only the
missing files.

================================================================================
6. SETUP FOR THE IMPLEMENTATION THREAD
================================================================================
Same as D1/D2 launch: sparse-clone drill/, verify the SHA the user supplies,
`uv sync --group test`, `npm install jsdom --no-save` (Node 18+), `bash
tests/run.sh` -> expect 177 ALL GREEN as the baseline. If NOT 177 green on a
clean clone at the verified SHA, STOP and report (collection/import/syntax
errors count as red even though pytest calls them "errors"). Invoke run.sh with
`bash`, not `sh`. The user supplies the exact SHA; do not guess it. The SHA to
verify against is the one the user pushes AFTER applying this handoff commit --
i.e. this handoff doc will already be present in the tree at that SHA.
