# Handoff: roadmap #2 -- difficulty control (DESIGN SETTLED -> IMPLEMENTATION)

Status: design conversation HELD and settled. This is the OUTPUT of the #2
design thread, in the #5 handoff format. It is the thing an implementation
thread starts from: a one-paragraph spine, Q1-Q6 resolved with rationale, the
adversarial-review record (what the lenses overturned), a topologically-sorted
commit plan with each commit's green-proof and HAIKU/SONNET class and weld
points, the ADRs to write/close, the implementer's known-sensitivities
checklist, and the binding "do not reopen" list.

Baseline: SHA 5b5c3f2 (after C-D5g), on main. Suite 225 green (backend 150,
frontend 75), ends "ALL GREEN". Node v22, uv 0.11. If starting fresh:
sparse-clone drill/, verify the SHA you are given, `uv sync --group test`,
`npm install jsdom --no-save`, `bash tests/run.sh` (bash, not sh). If NOT 225
green on a clean clone at the verified SHA, STOP and report (collection /
import / syntax errors count as red).

ASCII only. Single-user assumption holds. This is LOGIC-mostly with a thin HTTP
touch (a new request parameter), ONE additive forward-only migration, and a
small frontend addition (a stats-panel breakdown). It DOES touch schema -- Q5
resolved YES, minimal, because a real consumer (the per-difficulty stats
breakdown, C7) is built in this same thread.

Attach to the implementation thread: drill.py, index.html, llm/spec.md,
llm/decisions.md (ADR-027 through ADR-037 especially), llm/roadmap.md,
llm/knowledge-capture.md, and this handoff.

Commit-ID range: this thread owns C-D2a..C-D2z (suggested, provisional per the
knowledge-capture UNSURE note on numbering -- renumber if it collides with a
live range; keep them disjoint and contiguous).

================================================================================
NEW CODING CONVENTIONS (binding from this thread forward; do NOT retrofit)
================================================================================
The user has added three naming/clarity conventions. They apply to all NEW and
MODIFIED code from here on. Do NOT rewrite existing code to conform -- the user
will handle that separately. Only what you touch in a commit follows them.

  N1  EXPLICIT CONTROL FLOW. Plain if/else over compressed ternaries or clever
      one-liners wherever the if/else is clearer. A nested ternary or a
      comprehension doing real branching is a smell; expand it. (This sits with
      the existing "nothing too clever" / data-first taste, now made explicit
      for control flow.)
  N2  FULL DESCRIPTIVE NAMES carrying domain information. Variables and
      functions are named for what they mean in the problem, not abbreviated.
      `served_difficulty_rung`, not `diff` or `d`. `leaf_count`, not `lc`.
  N3  NO ABBREVIATIONS in identifiers, EXCEPT (a) abbreviations that are
      essentially nouns (usb, json, http, ascii, sql, utc) and (b)
      well-established conventions -- and even those get expanded toward clarity
      where it helps (a bare `x` becomes `x_axis` when that is what it is).

These refine, they do not override, the existing CONVENTIONS layer in
knowledge-capture.md. Where the codebase already has a clear local idiom (e.g.
`operand_min` / `operand_max` on operator records, the `_optional_int` helper
name), MATCH the established idiom rather than renaming around it -- consistency
with the file beats the abstract rule, and N3's "established conventions"
clause covers it. The point is new code reads clearly, not that it fights the
house style it lives in.

================================================================================
0. SPINE (one paragraph)
================================================================================
Difficulty is a SCALAR rung (shape C) that expands, via a documented,
overridable mapping DIFFICULTY_RUNGS, into the PER-OPERATOR structural config
the generator already exposes (operator depth, recurse probability, and each
operator's own operand ranges; the optional global result ceiling). The
caller-facing surface is one scalar (one knob for the common case); the
INTERNAL representation is a per-operator config vector, because difficulty
genuinely tunes several knobs and the operators do NOT share a single range
semantics. "Reliably harder" is operationalized PER OPERATOR-MIX: for mixes
that contain a composable operator (+ - *), difficulty is COORDINATION-driven
and the proxy is leaf_count (the element-interactivity / minimal-input analog),
which a property test pins as monotone non-decreasing across rungs; for
all-leaf-only mixes (/ % ^, which cannot nest), leaf_count is CONSTANT by
construction and difficulty is MAGNITUDE-driven (wider operand ranges), pinned
by a separate magnitude-monotonicity assertion. The served rung AND the
leaf_count of the served expression are recorded on responses, so the model is
empirically refinable and the per-difficulty stats breakdown has real data; the
leaf_count is the non-drifting ground truth (recomputable from question_text)
while the rung is a mutable human-facing label. Difficulty does NOT claim to be
a validated measure of cognitive load -- it is a heuristic over structural
features; the ADR says so, so a future reader does not over-trust the number.

================================================================================
1. Q1-Q6 RESOLVED (with rationale)
================================================================================

Q1  THE SPINE -- difficulty model shape. RESOLVED: shape C (scalar expands to a
    vector via an overridable mapping), but with a correction the design thread
    earned and did not assume: the internal vector is PER-OPERATOR, not a
    uniform config. The thread initially proposed leaf_count as a single scalar
    feature with a uniform range multiplier; the code overturned both halves
    (see section 2). Final model: scalar rung -> DIFFICULTY_RUNGS -> per-operator
    config. leaf_count is the coordination spine for composable-containing mixes
    only; magnitude carries the leaf-only operators. Rationale: A (bare scalar)
    bakes in a curriculum and hides a vector behind a number with no documented
    expansion -- the ADR-034 trap. B (caller supplies the full vector) is most
    honest but pushes "what is hard?" onto every caller and has no UI. C earns
    its keep ONLY because there is a near-dominant structural feature
    (leaf_count) for the common case, with the per-operator config still
    reachable; where leaf_count does not move (leaf-only mixes) the mapping
    falls back to magnitude, stated explicitly. Domain honesty: a higher rung
    produces RELIABLY harder questions on average within an operator mix; it is
    not a cross-mix cardinal scale (7 % 3 and 2 ^ 3 both have leaf_count 2 and
    are not commensurable by it).

Q2  OPERAND MAGNITUDE as a difficulty input. RESOLVED: YES, difficulty widens
    operand ranges, PER OPERATOR, reading each operator record's own range
    fields -- NOT a uniform multiplier and NOT a generic indexed override. This
    is forced by the code (ADR-028/030 kept ranges per-operator on the record
    with bespoke semantics): `+ -` draw from _DEFAULT_OPERAND_RANGE (1,20); `* /`
    from _MULTIPLICATIVE_OPERAND_RANGE (2,12); `%` has BOTH operand_min/max AND
    divisor_min/max; `^` has operand_min/max (base) AND exponent_min/max (power),
    and `/` DERIVES its dividend as divisor*quotient so its "range" is not a leaf
    range at all. A uniform multiplier would scale `+` operands while leaving the
    exponent power and modulo divisor untouched, and would blow the dividend
    (~quadratically) against the ceiling. So each rung declares scaled ranges
    per operator. This OPENS ADR-030's reserved per-operand generalization door
    in the shape the door was actually cut: per-operator, on the record, not
    generic. Beware exponent: 12^3 = 1728 is already at the UI ceiling (ADR-028),
    so `^` has almost no magnitude headroom -- a rung likely holds it fixed.

Q3  THE RESULT CEILING. RESOLVED: the ceiling is PART of the difficulty model
    (a difficulty-scaled bound: lower ceiling = easier), turned on per rung from
    its dark default (_MAX_RESULT_VALUE = None, ADR-035). It is NOT a fixed
    sanity guard independent of difficulty. CRITICAL: the ceiling bounds node
    RESULTS, not input-leaf magnitudes (the division-dividend subtlety, ADR-035)
    -- the difficulty model must NOT assume it caps operand size; operand size is
    capped via the ranges (Q2). Q2 and Q3 are resolved TOGETHER as one
    feasible-region decision (the "hidden object" the design thread named): a
    rung's (per-operator ranges, ceiling) pair must be PROVEN jointly satisfiable
    by a property test, because widening ranges while lowering the ceiling can
    make generation infeasible -> _MAX_GENERATION_ATTEMPTS exhaustion ->
    RuntimeError (ADR-036, S3). See the deliberate red in C-D2e.

Q4  THE CALLER -- signature and HTTP surface. RESOLVED: ONE scalar
    `?difficulty=` query parameter on the arithmetic branch of the question
    endpoint, mirroring Q1's scalar surface. generate_expression gains a
    `difficulty` parameter (plain data) ALONGSIDE its real caller (the endpoint),
    per ADR-034's "add the parameter together with its caller." Internally the
    function resolves the rung against DIFFICULTY_RUNGS to the per-operator
    config and threads operator depth into build_subtree as a PARAMETER (opening
    door D1). Malformed-vs-omitted discipline mirrors `?operators=` exactly
    (drill.py ~2399): absent -> None -> current defaults; present-but-unparseable
    or out-of-range -> 400 via the _optional_int / _BadParameter pattern, never a
    silent coercion to a default and never a raw int() that 500s.

Q5  STORAGE. RESOLVED: YES, minimal, schema DOES change -- ONE additive
    forward-only migration (v3) adding TWO nullable INTEGER columns to responses:
    the served difficulty rung (the human-facing label) and the served
    expression's leaf_count (the non-drifting structural fact). Rationale: the
    default expectation in the kickoff was "request-parameter only, NO schema
    change, UNLESS a concrete consumer is built in the same thread." That
    consumer IS built here (C7, the per-difficulty stats breakdown), so the gate
    opens. Why TWO columns and not one: a bare rung integer denormalizes a
    MUTABLE label -- when a later thread re-tunes rung 3's config (which the
    monitor-and-adjust strategy explicitly invites), every historical
    difficulty=3 row silently re-means. leaf_count is recomputable from
    question_text and does not drift, so it is the trustworthy axis for analysis;
    the rung stays for human readability. arithmetic rows get both; non-arithmetic
    and pre-#2 rows get NULL (unknown, not a default rung -- inventing a backfill
    value would poison the analysis, matching the v2 migration's no-data-loss
    discipline).

Q6  DEFAULTS / BACKWARD COMPATIBILITY. RESOLVED: "no difficulty parameter" means
    the CURRENT provisional defaults (_MAX_OPERATOR_DEPTH=2,
    _RECURSE_PROBABILITY=0.5, uniform operator sample), NOT a re-anchored middle
    rung. generate_expression(difficulty=None) is BYTE-IDENTICAL in behavior to
    today. Rationale: re-anchoring is the ONLY Q6 answer that changes the live
    endpoint's output distribution for an existing caller with no parameter, and
    we avoid silent behavior change. The module constants REMAIN the no-parameter
    fallback; a rung is an explicit opt-in override. This keeps S6 (depth-1==flat,
    p_recurse-0==flat) as the untouched compatibility anchor. ADR-031's note that
    the uniform six-way sample was provisional/not-pedagogical is now OWNED: #2's
    real policy is "no parameter = the provisional sample; a rung = the rung's
    declared mix," so ADR-031's provisional flag is superseded for the
    rung-driven path and retained for the default path.

================================================================================
2. ADVERSARIAL REVIEW (what the lenses overturned -- the record)
================================================================================
Run against the knowledge-capture lens roster (Acton: data shape at N; Carmack:
safety-net-first + honesty; Muratori: anti-speculative-generality; Victor:
does it change what the tool is; Nelson: anti-drift), plus the project's
DATA/SIMPLICITY/REAL-vs-SPECULATIVE/USAGE-BEFORE-INTERFACE/STRUCTURE/DOMAIN
axes. The review OVERTURNED the first plan; this section records what and why,
because the "why each thing changed" is the highest-value part of a handoff.

CONSENSUS ATTACK (three lenses converged on one code fact -> changed the plan):
  The first plan proposed leaf_count as a SINGLE scalar difficulty feature with
  a UNIFORM operand-range multiplier. Three lenses independently hit the same
  wall, and the wall is in the code:
   - DATA/TRANSFORM (Acton): measured it. generate_expression(['/']) yields
     leaf_count == 2 for 5000/5000 samples -- a point mass, zero variance --
     because / % ^ are nestable=False. A monotonicity test on leaf_count is a
     LIE for any leaf-only mix; it would pass on the default mix and hide that
     half the operators cannot move.
   - USAGE-BEFORE-INTERFACE (Muratori): the code already said the interface was
     wrong. Ranges are per-operator with bespoke fields (divisor_min/max,
     exponent_min/max, derived dividend); a uniform multiplier is precisely the
     generic indexed override ADR-028/030 refused, and it is incoherent against
     the data (scales + but not the exponent power or modulo divisor).
   - DOMAIN CORRECTNESS: the "difficulty" atom was ambiguous for the next
     consumer (#7). leaf_count conflates a coordination scale (works for + - *)
     with a per-operator intrinsic scale (the only thing that moves / % ^).
  FIX (folded into the spine): difficulty is per-operator-aware with two named
  regimes (coordination for composable-containing mixes, magnitude for
  leaf-only), and the rung config is per-operator, not a multiplier. The
  property tests assert PER MIX, not on the default mix.

Other lens findings, folded in:
  - SIMPLICITY/STATE: the first plan welded range-scaling and ceiling-on into
    the depth-parameter commit "for green convenience." Only depth is a true
    weld (it flips recursion; no green intermediate). Ranges and ceiling do NOT
    change tree shape, so they are SEPARATE commits that land green alone and
    are tested alone. Split (see C-D2d, C-D2e). The opus tell fired: "scales
    ranges AND turns on the ceiling, for different reasons, touching different
    fields."
  - STRUCTURE/INTENT (Nelson, anti-drift): storing a bare rung integer flattens
    a derived-from-a-mutable-table fact. Resolved by also storing leaf_count
    (the non-drifting ground truth). See Q5.
  - REAL-vs-SPECULATIVE (Muratori) + the user's correction: the first plan had
    an analysis FUNCTION with no caller (a Spearman trend-sign). Overturned
    twice: (a) the user will not revisit a deferred TODO reliably, so build the
    consumer now or not at all; (b) the code shows the consumer is REAL --
    summarize_stats already produces a per-category breakdown rendered by an
    existing stats panel (.stats-breakdown, "By category", with a
    single-group-suppression rule). A per-difficulty breakdown is the SAME shape
    with a different grouping key. So C7 is "extend the existing breakdown,"
    not "invent a surface" -- a real caller, dissolving the speculative-generality
    objection. The standalone Spearman function is dropped; a human reading
    "rung 1: 95%, rung 4: 60%" sees monotonicity directly. Automated trend-sign
    waits for #7 (more N).

================================================================================
3. KNOWN-SENSITIVITIES CHECKLIST (the implementer verifies each; P5)
================================================================================
Promoted from the review to an explicit checklist, because in #5 the two real
findings were exactly the items a review flagged but the handoff did not promote.

  S1  depth != difficulty (ADR-034). Do not expose depth and label it
      difficulty. A deep sum is easier than a flat product. Any rung's
      difficulty combines depth WITH magnitude and operator mix.
  S2  ceiling bounds RESULTS, not LEAVES (ADR-035). Division derives a large
      dividend leaf under a small quotient result. Cap operand magnitude via the
      RANGES (Q2), never via the ceiling.
  S3  range-widening x ceiling x retry interaction. Widening ranges while
      lowering the ceiling can make a rung jointly infeasible ->
      _MAX_GENERATION_ATTEMPTS (1000) exhaustion -> RuntimeError (ADR-036). Every
      rung MUST be proven satisfiable by the per-rung property test, with enough
      samples (>= 2000) to catch a rung that fails ~1-in-500. The division and
      exponent mixes are where this bites (derived dividend, near-ceiling power).
  S4  empty/malformed-parameter discipline. `?difficulty=` present-but-bad is a
      400, not a silent default -- same care as `?operators=` empty (drill.py
      ~2410). Use _optional_int / _BadParameter, never raw int().
  S5  output length / UI-tractability. Higher rungs lengthen question_text and
      grow results. The C-D5e length guard (< 400 chars) and the exponent
      magnitude ceiling (12^3, ADR-028) are the existing guards; a high rung
      stays within them or consciously raises them WITH rationale in an ADR.
      A rung that pushes past the length guard reddens test_http or the render
      tests, NOT the generator test -- so run the FULL suite, not just generator
      tests, as each rung's green-proof.
  S6  _MAX_OPERATOR_DEPTH==1 still reproduces flat #4 exactly; p_recurse==0 still
      flat (ADR-034). These invariants must not regress -- they are the
      compatibility anchors and the difficulty=None path depends on them.
  S7  leaf_count is a POINT MASS for leaf-only mixes. Any monotonicity assertion
      on leaf_count MUST be scoped to composable-containing mixes; for leaf-only
      mixes assert leaf_count is CONSTANT and that MAGNITUDE moves instead.
      (This is the consensus-attack finding; do not let it regress into a
      single-mix test.)
  S8  the stored rung is a MUTABLE label; leaf_count is the stable fact. Analysis
      and any future adaptive consumer (#7) should treat the rung as a
      human-facing tag and leaf_count as the structural ground truth (Q5).
  S9  live in-session state vs durable DB history are SEPARATE render paths
      (knowledge-capture convention). The per-difficulty breakdown (C7) is a
      DURABLE-history view (summarize_stats / the stats panel), NOT the live
      stats bar -- do not cross them.
  S10 the round-trip is STATELESS. The served rung+leaf_count must travel:
      question payload -> client echoes -> answer body -> insert_response, the
      same path expected/elapsed_ms already take (drill.py ~2489-2545). There is
      no server-side per-question state to attach difficulty to. This means the
      recorded value is CLIENT-ASSERTED (as trustworthy as expected/elapsed_ms
      already are -- no worse, no better); state this in the ADR for #7's sake.
  S11 *** CRITICAL -- decide before C-D2i. *** ?operators= and ?difficulty= are
      ORTHOGONAL params (the endpoint parses them separately, drill.py ~2399), so
      the user can request any (mix, rung) pair -- including division-only at the
      top rung, where leaf_count is pinned at 2 and only magnitude moves. The
      rung number is therefore NOT comparable across operator mixes. But C-D2i
      groups arithmetic responses by rung REGARDLESS of the served mix, so it
      silently compares incomparable buckets (easy all-ops rung 3 vs hard
      division-only rung 3). The monotonicity property tests are correct because
      they are PER MIX; the bug is that the DISPLAY aggregates across mixes. This
      is the domain-correctness objection resurfacing at the storage+display
      layer, where the generation-layer fix (S7) did not reach. RESOLVE before
      building C-D2i. RECOMMENDED: group the breakdown by LEAF_COUNT, not rung --
      leaf_count is the comparable structural fact, which is exactly why it is
      stored (ADR-040), so this makes the stored-fact decision pay off now, not
      only for #7. Alternatives: scope the breakdown to a fixed mix, or label it
      "rung as dialed, not comparable across operator sets." See ADR-038 [OPEN].

================================================================================
4. COMMIT PLAN (topologically sorted; each green except one noted red)
================================================================================
Classification per the commit-planning prompt (HAIKU/SONNET/OPUS-decomposed).
Edges named. The one true weld and the one deliberate red are marked. Every
commit follows the NEW conventions N1-N3 for code it adds or touches.

EDGE MAP:
  C-D2a -> C-D2b -> { C-D2c, C-D2d, C-D2e }
  C-D2f (migration) is independent of the generator chain (can land any time
        after baseline; placed after the HTTP surface so the feature reads
        end-to-end before it is recorded)
  C-D2f -> { C-D2g, C-D2h }
  { C-D2c, C-D2g, C-D2h } -> C-D2i

--------------------------------------------------------------------------------
C-D2a  define the atom: leaf_count + per-operator DIFFICULTY_RUNGS shape
--------------------------------------------------------------------------------
  Class: SONNET (trivial metric; the design judgment -- per-operator config,
         which mixes are coordination- vs magnitude-movable -- is the one
         coherent movement: defining the atom).
  Files: drill.py (CONFIG + LOGIC), tests/test_generator_property.py.
  Goal: add a pure leaf_count(node) over the {op,left,right} tree, and declare
        DIFFICULTY_RUNGS as ordered per-operator config (NOT a multiplier),
        with each operator's scaled ranges read from its own record fields.
  Edges: none new. Green standalone.
  Green-proof: leaf_count unit-checked on hand-built trees (flat node -> 2,
        depth-2 sum -> 3, etc.) and shown independent of operator_depth; the
        rung table imports and the consistency of its per-operator fields is
        asserted (every declared operator exists in OPERATORS).
  Notes: DECIDE the rung count and the exact per-operator scaled values here,
        informed by a throwaway probe across operator-mix singletons/pairs
        (measured headroom, not guessed). leaf_count lives in LOGIC (the
        property test and a future analysis consume it); the test file's private
        _operator_depth stays as-is (test-internal, do not refactor).

--------------------------------------------------------------------------------
C-D2b  thread operator-depth + recurse as parameters (THE WELD)
--------------------------------------------------------------------------------
  Class: SONNET. Genuinely welded: the moment build_subtree takes operator depth
         as a parameter (door D1), the property tests asserting the constant's
         behavior (test_generator_property.py ~133, ~162) must change in the
         SAME commit -- no green state exists where the param exists but the
         depth-1-flat / never-raises invariants are unasserted at the new path.
         This is the #5-style weld (P2). ONE commit.
  Files: drill.py (LOGIC), tests/test_generator_property.py.
  Goal: generate_expression(enabled_symbols=None, difficulty=None); when a rung
        is given, resolve it to per-operator config and thread operator depth
        and recurse probability into build_subtree as plain-data parameters.
        difficulty=None is byte-identical to today (Q6).
  Edges: needs C-D2a (DIFFICULTY_RUNGS exists).
  Green-proof: the existing 3 generator tests pass UNCHANGED on the None path;
        new per-mix monotonicity test -- leaf_count monotone non-decreasing for
        composable-containing mixes, CONSTANT for leaf-only mixes (S7); per-rung
        never-raises (S3, foreign-oracle re-walk asserting depth bound). Run the
        FULL suite (S5).
  Notes: depth becomes a build_subtree parameter; pass per-operator config as
        plain dicts/scalars across the call (layering invariant -- LOGIC stays
        pure, no new structure; ADR-030 node shape unchanged).

--------------------------------------------------------------------------------
C-D2c  HTTP ?difficulty= on the question endpoint
--------------------------------------------------------------------------------
  Class: HAIKU. One parse, one payload field, mirrors ?operators=.
  Files: drill.py (HTTP), tests/test_http.py.
  Goal: parse optional ?difficulty=, resolve+pass to generate_expression, and
        ECHO the served rung + computed leaf_count in the question payload so
        they survive the stateless round-trip (S10).
  Edges: needs C-D2b.
  Green-proof: new HTTP cases -- valid rung serves harder + payload carries
        rung and leaf_count; absent -> unchanged from today (regression guard);
        malformed (?difficulty=99, =abc, =) -> 400 with a clear message
        (S4). Existing endpoint tests stay green.

--------------------------------------------------------------------------------
C-D2d  per-operator operand-range scaling per rung (no shape change)
--------------------------------------------------------------------------------
  Class: SONNET. Split out of the first plan's opus (SIMPLICITY lens): ranges do
         not change tree shape, so this is independent of the ceiling.
  Files: drill.py (LOGIC/CONFIG), tests/test_generator_property.py.
  Goal: each rung's per-operator scaled ranges take effect in the operand
        strategies (reading each record's own range fields -- Q2, per-operator,
        NOT a multiplier).
  Edges: needs C-D2b (config plumbing). Independent of C-D2e.
  Green-proof: C-D2b structural tests still green (shape unchanged); new test --
        leaf MAGNITUDE increases across rungs for leaf-only mixes (the regime
        that leaf_count cannot serve, S7).

--------------------------------------------------------------------------------
C-D2e  turn on the result ceiling per rung (THE DELIBERATE RED)
--------------------------------------------------------------------------------
  Class: SONNET. Split out of the opus.
  Files: drill.py (LOGIC/CONFIG), tests/test_generator_property.py.
  Goal: set _MAX_RESULT_VALUE per rung from its dark default (Q3); add the
        per-rung satisfiability property test over the / % ^ mixes specifically.
  Edges: needs C-D2b. Resolves Q2 x Q3 jointly with C-D2d.
  Green-proof: LET IT GO RED FIRST, on purpose. Land a ceiling that is too low
        for a rung's widened ranges and WATCH the satisfiability test go red
        (division: dividend = divisor*quotient collides with a low ceiling ->
        retry exhaustion). That red IS the S3 feasibility proof -- evidence the
        guard works. Then reconcile (raise the ceiling or narrow the rung's
        ranges) until green. This is the one place a noted red is worth more
        than a clean green; everywhere else, strict green.

--------------------------------------------------------------------------------
C-D2f  migration v3: store served rung + leaf_count (non-drifting fact)
--------------------------------------------------------------------------------
  Class: HAIKU, but GUARD-WELDED internally: the import-time guard
         _check_migration_version_consistency (drill.py ~320) welds the
         SCHEMA_VERSION bump (to 3) to the MIGRATIONS append -- bumping one
         without the other RAISES at import and reddens the whole suite at
         collection. The two edits are atomic by construction.
  Files: drill.py (DATABASE: schema + a _migrate_3_* fn + MIGRATIONS entry +
         SCHEMA_VERSION), tests/test_migrate.py.
  Goal: ALTER responses ADD COLUMN difficulty INTEGER (nullable) and ADD COLUMN
        leaf_count INTEGER (nullable). Additive, forward-only, NULL for pre-#2
        and non-arithmetic rows (Q5, S8). The fn does ONLY the ALTERs; the runner
        owns the transaction and stamps the version.
  Edges: independent of the generator chain.
  Green-proof: import guard passes (bump+register together); migration applies
        cleanly on a v2 DB; existing rows read NULL for both columns; version
        stamps to 3. (Mirrors the v2 / questions.metadata migration exactly.)
  Notes: column on responses, NOT questions -- arithmetic is generated with
        question_id NULL, so it has no questions row; the questions.metadata
        hatch is unreachable for it, and responses has no extras column. Honest
        recording REQUIRES this migration; there is no free hatch.

--------------------------------------------------------------------------------
C-D2g  capture: thread rung+leaf_count into insert_response + post_answer
--------------------------------------------------------------------------------
  Class: HAIKU. (Split from a mild capture+readback opus; this is the write
         path only.)
  Files: drill.py (DATABASE insert_response, HTTP post_answer),
         tests/test_db.py, tests/test_http.py.
  Goal: insert_response gains optional difficulty/leaf_count params (the
        elapsed_ms shape); post_answer reads them from the echoed body via
        _optional_int and passes them through.
  Edges: needs C-D2f (columns exist).
  Green-proof: insert-with reads both back; insert-without reads NULL; existing
        answer tests stay green (fields optional -- a client that omits them
        still works). Blast radius confirmed zero: the single insert_response
        caller and all current tests omit the new params.

--------------------------------------------------------------------------------
C-D2h  readback: surface rung+leaf_count in get_responses_for_stats
--------------------------------------------------------------------------------
  Class: HAIKU. (The read path; independent of C-D2g.)
  Files: drill.py (DATABASE get_responses_for_stats), tests/test_db.py.
  Goal: SELECT and surface r.difficulty and r.leaf_count in the returned row
        dicts (the elapsed_ms "available for a future feature" pattern).
  Edges: needs C-D2f.
  Green-proof: reader returns the fields; summarize_stats is UNAFFECTED (it reads
        only correct/category_* keys, ignores extras) -- so this is green with no
        change to the summary yet.

--------------------------------------------------------------------------------
C-D2i  the consumer: per-difficulty breakdown in summarize_stats + render
--------------------------------------------------------------------------------
  Class: SONNET. Backend grouping + frontend render + their tests, one coherent
         movement (the display the user asked for).
  Files: drill.py (LOGIC summarize_stats), index.html (stats panel + tests),
         tests/test_logic.py, tests/frontend/stats.test.js.
  Goal: EXTRACT the implicit grouping into an explicit helper
        breakdown_by(rows, key_function) and call it twice -- by category (the
        existing breakdown, now via the helper) and by difficulty rung (the new
        one). Render a "By difficulty" section in the existing .stats-breakdown
        panel, arithmetic-category only.
  Edges: needs C-D2c + C-D2g + C-D2h (real served values flowing end to end).
  Green-proof: category breakdown UNCHANGED (regression -- the extracted helper
        must reproduce it byte-for-byte in output); new difficulty rows render;
        single-rung suppression MIRRORS the single-category suppression rule
        (stats.test.js ~140); empty/time-zero handled (zeros, no div-by-zero).
  Notes: STEP-3 finding -- get_responses_for_stats + summarize_stats are about to
        serve TWO grouping meanings (category AND difficulty) that currently
        coincide as one. Extract breakdown_by; do NOT copy-paste the group loop.
        This is the "name the two meanings into two explicit helpers" instruction
        from the commit-planning prompt. The difficulty breakdown is
        arithmetic-only by intent (other categories have no difficulty) -- show
        it only for arithmetic, do not render empty difficulty rows for
        vocabulary; this is intended, not a bug.
  *** GATED BY S11 (CRITICAL): the grouping KEY -- rung vs leaf_count -- is NOT
        yet decided. Grouping by rung compares incomparable buckets across
        operator mixes. Resolve S11 / ADR-038 [OPEN] BEFORE writing this commit;
        the recommended answer is group by leaf_count. Do not build C-D2i until
        that is settled. ***

================================================================================
5. ADRs TO WRITE / CLOSE
================================================================================
WRITE (next free numbers, ADR-038+):
  ADR-038  difficulty model shape: scalar rung -> per-operator config (shape C
           with the per-operator correction); leaf_count as the coordination
           spine; the two regimes (coordination vs magnitude); the domain-honesty
           caveat (heuristic over structural features, not validated cognitive
           load); cite the consensus attack as the reason the uniform-multiplier
           first design was rejected.
  ADR-039  Q2 x Q3 feasible-region resolution: per-operator range scaling +
           difficulty-scaled ceiling, jointly proven satisfiable; the
           division-dividend / exponent-power sensitivities (S2, S3).
  ADR-040  responses.difficulty + responses.leaf_count storage: why two columns
           (mutable label vs non-drifting fact, S8); NULL semantics; the
           client-asserted-trust caveat for #7 (S10).
  ADR-041  the per-difficulty stats breakdown as the real consumer that opened
           Q5; breakdown_by extraction; arithmetic-only scoping; live-vs-durable
           separation (S9).

CLOSE / SUPERSEDE (from ADR-037's doors and earlier):
  D1 (depth as a parameter)         -> opened in C-D2b. Mark ADR-037 D1 closed.
  D4 (result-ceiling default)       -> opened in C-D2e. Mark ADR-037 D4 closed.
  D5 (provisional defaults)         -> re-owned in C-D2a/C-D2b/Q6. Mark closed.
  ADR-030 per-operand-range item    -> OPENED per-operator (Q2). Note in ADR-030
                                       that #2 opened it in the per-operator
                                       shape, NOT the generic override it
                                       refused; close the reserved item.
  ADR-031 provisional-sample note   -> superseded for the rung-driven path,
                                       retained for the default path (Q6).
  D2 (per-position/shape control)   -> only PARTIALLY touched (recurse probability
                                       becomes a per-rung scalar; asymmetric /
                                       per-operator SHAPE is NOT added -- not
                                       needed). Leave D2 open for a future thread;
                                       note #2 did not require it.

DO NOT OPEN (deferred past #2, per ADR-037): making / % ^ nestable via
derive-compatible-sibling (a generator-capability change, not a difficulty knob;
difficulty does not need nested division); the dataclass promotion (ADR-030,
deferred until the record field set stabilizes -- and #2 ADDS per-operator range
fields, so the field set is LESS stable now, not more: keep dicts).

================================================================================
6. DO NOT REOPEN (binding from #4/#5; restated)
================================================================================
- Node shape {op, left, right} with int leaves; no dataclass (ADR-030).
- Operator-record design (ADR-027): new difficulty inputs are DATA on records or
  new module constants, not a new structure. (The per-rung config is plain data.)
- The composable/leaf-only split and the bottom-up generator (ADR-032); the
  precedence/associativity renderer (ADR-033). #2 varies the KNOBS these expose;
  it does not rearchitect them.
- generate_expression stays PURE LOGIC; the clock and IO stay in HTTP. The new
  request parameter is parsed in HTTP and passed down as plain data.
- No new operators, no unary/n-ary (ADR-029). No multi-user/auth/concurrency.
- The layering invariant (CONFIG scalars only; DATABASE IO-only; LOGIC pure;
  HTTP thin glue and the only clock-reader). Import direction unchanged.
- Forward-only migrations, additive, NULL-safe, no data loss (the .db is the
  user's only copy).
- stdlib + Bottle only; no new runtime deps (ADR-001). The analysis is plain
  arithmetic over rows, no scipy/pandas.
- Do not fork validate_answer's qtype dispatch; the new columns FEED stats, they
  do not touch grading.

================================================================================
7. PROCESS STRATEGIES TO CARRY (from the #5 retro + this thread)
================================================================================
  P1  Handoff fidelity is the biggest lever. This document's highest-value
      section is section 4's "why each commit lands green / the ordering / the
      one weld / the one deliberate red" -- it removes sequencing judgment from
      the implementer. The "what the lenses overturned" record (section 2) is
      second: it stops the implementer re-deriving the rejected uniform-multiplier
      design.
  P2  Mark weld points explicitly. The ONLY true weld is C-D2b (depth parameter +
      its test). C-D2f is guard-welded by the import-time consistency check. The
      first plan's range+ceiling weld was FALSE (convenience, not necessity) and
      was split -- stating which welds are real prevents a failed split and a
      confusing red middle.
  P3  Out-of-band verification with a foreign oracle. The leaf-only point-mass
      finding came from RUNNING the generator at N=5000 per mix, not from the
      suite. For each correctness-critical rung, generate a large sample and
      verify structural properties (depth bound, per-node invariant, leaf_count
      regime, never-raises) INDEPENDENT of the production path. Standing step.
  P4  Surface, don't smooth -- and check the CODE, not your assumption, when a
      check fails. This thread's pivot came from reading OPERATOR_DEFINITIONS and
      finding per-operator range fields the plan had assumed away. When a design
      assumption meets the code, the code wins; go read it before editing.
  P5  The known-sensitivities checklist (section 3) is itself the carried-over
      improvement. This thread END-ed its review by writing it.
  P6  Frozen-by-default. The implementation thread treats this design as settled
      and pushes back only on a discovered contradiction (trivial: fix with a
      noted judgment call; substantial: STOP, go to the code, bring evidence).
      If you WANT a second design opinion mid-implementation, say so explicitly,
      or the design is frozen.

================================================================================
8. INFORMATION-RETRIEVAL / DEBUGGING TACTICS USED (reusable)
================================================================================
  T1  Read the data structure before designing the transform over it. The
      per-operator range finding (divisor_min/max, exponent_min/max, derived
      dividend) came from reading OPERATOR_DEFINITIONS, not from the function
      signatures -- the records carry the semantics the functions only read.
  T2  Measure the distribution, do not assume it. A two-line script over
      generate_expression at N=5000 per operator-mix turned "leaf_count is the
      feature" into "leaf_count is a point mass for half the operators." Cheap
      empiricism beats confident design.
  T3  Find the consumer before declaring a thing speculative. "Analysis function
      with no caller" was speculative until a grep of summarize_stats +
      stats.test.js showed the per-category breakdown is the exact shape and the
      panel is the exact surface -- the caller existed; the plan had not looked.
  T4  Let the import guard do the welding. _check_migration_version_consistency
      means you cannot bump the version without registering the migration; trust
      the guard rather than hand-coordinating the two edits.
  T5  Trace the stateless round-trip end to end before deciding where a fact
      lives. Following expected/elapsed_ms from question payload -> client echo
      -> answer body -> insert_response is what revealed there is no server-side
      question state, so difficulty must ride the echo (S10) and is therefore
      client-asserted.
