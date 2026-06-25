# Kickoff: roadmap #2 -- difficulty control (DESIGN THREAD, not implementation)

Status: design conversation NOT yet held. This document opens the #2 design
thread. Unlike the #5 handoff (which recorded SETTLED decisions for an
implementer to execute cold), this is the INPUT to a design conversation: it
frames the central question, enumerates the doors #5 deliberately left open for
#2, names the known sensitivities, and states what must NOT be reopened. The
OUTPUT of the #2 design thread will be a settled-decisions + commit-plan handoff
in the #5 format; this is the thing that thread starts from.

Baseline at kickoff: SHA after C-D5g (the #5 implementation thread), on main.
Suite 225 green (backend 150, frontend 75), ends "ALL GREEN". Node v22, uv 0.11.
(If you are starting fresh: sparse-clone drill/, verify the SHA you are given,
`uv sync --group test`, `npm install jsdom --no-save`, `bash tests/run.sh`. If
NOT green on a clean clone at the verified SHA, STOP and report.)

ASCII only. Single-user assumption holds. Expected to be LOGIC-mostly with a
thin HTTP touch (a new request parameter); whether it touches schema is an OPEN
question this thread must answer (see Q5).

Attach to the design thread: drill.py, llm/spec.md, llm/decisions.md (ADR-027
through ADR-037 especially), llm/roadmap.md, and this kickoff.

================================================================================
0. WHY #2 IS NEXT (the case, briefly)
================================================================================
#2 is the designed CONSUMER of everything #5 shipped dark. The roadmap sequence
is operators (#4) -> nested trees (#5) -> difficulty (#2); #5 just landed, and
it ends with four pre-wired doors that #2 was named to open (section 3). Doing
#2 now means those doors are opened by the thread they were designed for, while
the rationale is fresh -- if we pivot away, the half-finished constants (depth
as a constant not a parameter; the dark ceiling; the provisional p_recurse/depth
defaults) sit unexplained and the next person reconstructs the "why."

Two more reasons it leads:
- It is the commit that makes #5 PAY OFF. The nesting capability is inert until
  something varies it per difficulty; #2 is that something.
- It serves BOTH goals at once. #2 makes the arithmetic drill immediately more
  useful to a USER (dial difficulty), and it is high on the LEARN axis (a real
  difficulty model is a genuine design problem). The other top-ranked item,
  modularization (#1), serves only the build-to-learn goal and is invisible to a
  user -- so #2 leads, and #1 is the RECOMMENDED FOLLOW-ON (see section 7):
  #2 is the last feature to add to the monolith; #1 then modularizes code you
  understand cold, before #6/#7/#9/#10 widen the surface further.

What #2 is NOT: a new drill type, a selection-policy change, or SM2. Adaptive
selection (#7) is the natural follow-on AFTER difficulty exists; SM2 (#6) comes
after #7. #2 is strictly "vary the generated arithmetic question's difficulty."

================================================================================
1. THE CENTRAL QUESTION (resolve this FIRST; everything hangs off it)
================================================================================
WHAT IS DIFFICULTY? Is it ONE scalar, or a VECTOR over independent structural
inputs?

This is the live debate, and ADR-034 already constrains it: "depth is a
STRUCTURAL parameter, ONE input among several, explicitly NOT a difficulty
score. 2 + 3 + 4 (depth 2) is easier than 7 * 8 (depth 1). depth != difficulty."
So #2 cannot just expose depth and call it difficulty. It must DEFINE difficulty
in terms of the structural knobs it drives. The candidate inputs (each already a
real knob in the code or trivially addable):
  - OPERATOR DEPTH               (_MAX_OPERATOR_DEPTH, exists)
  - RECURSE PROBABILITY / shape  (_RECURSE_PROBABILITY, exists)
  - OPERAND MAGNITUDE / digits   (operand_min/max per record; ADR-030 door)
  - OPERATOR SET / mix           (enabled_symbols already a request param;
                                  weighting is not yet a thing)
  - RESULT CEILING               (_MAX_RESULT_VALUE, exists, dark/off)

THREE SHAPES the thread should weigh (not prejudged here):
  (A) ONE SCALAR difficulty (e.g. 1..5) -> a fixed mapping to a config bundle.
      Simplest caller; matches the existing questions.difficulty INTEGER 1..5
      convention; but bakes in a curriculum opinion (which #5's ADR-031 warned
      against calling pedagogical). The mapping table IS the curriculum.
  (B) A VECTOR/config object the caller supplies (depth, magnitude, operators,
      ceiling) with no single "difficulty number." Most honest to ADR-034
      (difficulty is multi-input); most flexible; but pushes the
      "what is hard?" decision onto every caller and has no obvious UI.
  (C) A SCALAR that EXPANDS to a vector via a documented, overridable mapping --
      one knob for the common case, with the underlying config still reachable.
      Likely the pragmatic answer, but the thread should EARN it, not assume it.

The decision here determines the caller signature (Q4), whether the ceiling
turns on (Q3), and whether anything is stored (Q5). Do not proceed to those
until this is settled.

DOMAIN HONESTY (carry ADR-034's warning forward): whatever shape wins, the ADR
must state what difficulty does and does NOT claim. A higher difficulty number
should produce RELIABLY harder questions on average, but the model is a
heuristic over structural features, not a validated measure of cognitive load.
Say so, so a future reader does not over-trust the number.

================================================================================
2. OPEN QUESTIONS (Q1-Q6, to be settled in-thread)
================================================================================
Q1  THE SPINE -- difficulty model shape. Section 1. Settle first.

Q2  OPERAND MAGNITUDE as a difficulty input. ADR-030 deferred "full per-operand
    -range generalization" to #2 with an explicit gate: "write the caller first;
    do not generalize ahead of it." #2 IS that caller. The question: does
    difficulty widen operand ranges, and if so, HOW -- a uniform multiplier on
    every operator's [operand_min, operand_max], or per-operator scaling? ADR-028
    kept ranges as per-operator named fields and refused a generic indexed
    override; #2 must decide whether a real difficulty consumer now justifies the
    generalization ADR-030 reserved, or whether a coarser per-difficulty range
    table suffices. Beware: widening multiplicative/division/exponent ranges
    interacts with the result ceiling (Q3) and with UI-tractability (12^3=1728
    was already near the comfortable mental-arithmetic ceiling, ADR-028).

Q3  THE RESULT CEILING -- does #2 turn it on? _MAX_RESULT_VALUE ships dark (None)
    from C-D5d/ADR-035, framed explicitly as "a difficulty-relevant knob #2 may
    turn, not a fixed sanity guard." The question: is the ceiling part of the
    difficulty model (lower ceiling = easier), a fixed sanity bound independent
    of difficulty, or both (a difficulty-scaled ceiling)? Note the ceiling bounds
    node RESULTS, not input-leaf magnitudes (the division-dividend subtlety,
    ADR-035) -- the difficulty model must not assume it caps operand size.

Q4  THE CALLER -- signature and HTTP surface. The single caller today is
    generate_expression(enabled_symbols) at the arithmetic endpoint
    (drill.py ~2415); the endpoint already parses ?operators= into
    enabled_symbols (~2390). ADR-034 says #2 "adds the [depth] parameter TOGETHER
    WITH its real caller." So this thread writes BOTH the parameter(s) on
    generate_expression AND the endpoint wiring (a new ?difficulty= or
    ?depth=/?magnitude= parameter set) in the same design. Decide: one
    ?difficulty= scalar, or explicit structural params, mirroring Q1's shape.
    Keep the existing "?operators= present but empty is an error, not 'use all'"
    discipline (drill.py ~2401) for any new parameter.

Q5  STORAGE -- does difficulty persist anywhere? Arithmetic questions are
    GENERATED per request, not banked, so they have no questions row and no
    questions.difficulty value (that column is for imported bank items, 1..5 or
    NULL, ADR-002-era). The question: is per-request arithmetic difficulty purely
    a request parameter (no schema change), or does the session/run want to
    record the difficulty it served (which WOULD touch schema -- a responses or
    session column -- and therefore the migration runner, #11/ADR-021..023)?
    Default expectation: request-parameter only, NO schema change, unless a
    concrete consumer (stats-by-difficulty, adaptive #7) is being built in the
    same thread. Resist speculative columns (ADR-028/030 spirit).

Q6  DEFAULTS / BACKWARD COMPATIBILITY -- what does the endpoint do with NO
    difficulty given? Today, post-#5, the endpoint already serves nested
    questions at _MAX_OPERATOR_DEPTH=2 / _RECURSE_PROBABILITY=0.5 (the #5
    provisional defaults). The question: does "no difficulty parameter" mean
    "the current provisional defaults," or does introducing difficulty re-anchor
    the default to a defined middle rung? Decide whether the module constants
    REMAIN the no-parameter fallback or become the implementation detail of one
    difficulty rung. (This also subsumes ADR-031's note that the uniform six-way
    operator sample was provisional, not pedagogical -- #2 owns the real policy.)

================================================================================
3. INHERITED DOORS (what #5 left open FOR #2 -- ADR-037, verbatim agenda)
================================================================================
These are the concrete hooks #5 shipped deliberately incomplete, each marked
"reconsider when #2 has a concrete caller." #2 IS the caller. Opening them is
the bulk of the thread's agenda:

  D1  DEPTH AS A PARAMETER. _MAX_OPERATOR_DEPTH is a module constant; #5 refused
      to make it a generate_expression parameter "with only a default and no
      caller" (ADR-034, Lens 3/4 consensus). #2 adds the parameter with its real
      caller. -> feeds Q1, Q4.
  D2  PER-POSITION / SHAPE CONTROL. #5 uses one scalar _RECURSE_PROBABILITY with
      independent per-operand flips. #2 may widen to asymmetric or per-operator
      shaping IF difficulty needs it -- not before. -> feeds Q1.
  D3  OPERAND-RANGE GENERALIZATION. ADR-030's Approach B (per-position ranges
      across operators behind one interface) was reserved for "a real consumer."
      -> feeds Q2.
  D4  THE RESULT-CEILING DEFAULT. _MAX_RESULT_VALUE = None ships dark; #2 owns
      turning it on and choosing the value. -> feeds Q3.
  D5  THE PROVISIONAL DEFAULTS. _RECURSE_PROBABILITY=0.5, _MAX_OPERATOR_DEPTH=2,
      and the uniform operator sample (ADR-031) are provisional, not pedagogical.
      #2 owns the real values. -> feeds Q1, Q6.

Doors #2 should NOT open (deferred PAST #2): making / % ^ nestable via
derive-compatible-sibling (ADR-037 -- that is a generator-capability change, not
a difficulty knob; only open it if difficulty genuinely needs nested division,
which is unlikely); the dataclass promotion (ADR-030, deferred until the record
field set stabilizes).

================================================================================
4. KNOWN SENSITIVITIES (the places most likely to go subtly wrong)
================================================================================
This section is new discipline carried from the #5 thread: promote the review's
"most-likely-wrong" spots to an explicit checklist the implementer verifies. For
#2, watch:

  S1  depth != difficulty (ADR-034). The single easiest mistake is to expose
      depth and label it difficulty. A deep sum is easier than a flat product;
      any difficulty scalar MUST combine depth with magnitude/operator-mix.
  S2  ceiling bounds RESULTS not LEAVES (ADR-035). A difficulty model that
      "caps operand size via the ceiling" is wrong -- division derives a large
      dividend leaf under a small quotient result. If difficulty wants to cap
      operand magnitude, it does so via the operand RANGES (Q2), not the ceiling.
  S3  range-widening x ceiling x retry interaction. Widening operand ranges for
      "hard" while also lowering a ceiling can make constraints jointly
      infeasible -> _MAX_GENERATION_ATTEMPTS exhaustion -> RuntimeError
      (ADR-036). Any difficulty rung must be PROVEN satisfiable (a property test
      asserting normal generation at every rung never raises), exactly as #5
      pinned for the base case.
  S4  the empty-parameter discipline. ?operators= empty is an error, not "use
      all" (drill.py ~2401). A new ?difficulty= must decide its own malformed-vs-
      omitted semantics with the same care -- do not silently coerce a bad value
      to a default.
  S5  output length / UI-tractability. Higher difficulty (more depth, bigger
      operands) lengthens question_text and grows results. The C-D5e length
      guard (<400 chars) and the exponent magnitude ceiling (ADR-028) are the
      existing guards; a high difficulty rung must stay within them or
      consciously raise them with rationale.
  S6  _MAX_OPERATOR_DEPTH==1 must STILL reproduce flat #4 exactly (a tested
      property, ADR-034). Whatever #2 does, the "depth 1 == flat" invariant and
      the "p_recurse 0 == flat" invariant must not regress -- they are the
      compatibility anchors.

================================================================================
5. WHAT MUST NOT BE REOPENED (binding from #4/#5)
================================================================================
- Node shape {op, left, right} with int leaves; no dataclass (ADR-030).
- Operator-record design (ADR-027): new difficulty inputs are DATA on records or
  new module constants, not a new structure.
- The composable/leaf-only split and the bottom-up generator (ADR-032); the
  precedence/associativity renderer (ADR-033). #2 varies the KNOBS these expose;
  it does not rearchitect them.
- generate_expression stays PURE LOGIC; the clock and IO stay in HTTP. A new
  request parameter is parsed in HTTP and passed down as plain data.
- No new operators, no unary/n-ary (ADR-029). No multi-user/auth/concurrency.
- The layering invariant (CONFIG scalars only; DATABASE IO-only; LOGIC pure;
  HTTP thin glue and the only clock-reader).

================================================================================
6. STRATEGIES TO CARRY INTO THIS THREAD (process, from the #5 retro)
================================================================================
These worked in #4/#5; keep them.

  P1  HANDOFF FIDELITY IS THE BIGGEST LEVER. The #5 handoff had a one-paragraph
      spine, settled decisions WITH rationale, an adversarial-review record
      showing what got overturned and why, a topo-sorted commit plan with a
      per-commit "why this lands green" line and HAIKU/SONNET classification, and
      a "do not reopen" list. That is why the implementation thread never had to
      guess. The #2 design thread's OUTPUT handoff should match this fidelity.
      The single highest-value section was "why each commit lands green / the
      ordering principle" -- it removed all sequencing judgment from the
      implementer. Reproduce it.

  P2  MARK WELD POINTS EXPLICITLY. #5 pre-identified that the generator rewrite
      and its property-test rewrite could not be split (no intermediate green
      state once depth default flips). Stating which commits are atomic and WHY
      prevents a failed split and a confusing red middle. The #2 plan should
      flag the same: e.g. if turning depth into a parameter and rewiring the
      caller cannot be green separately, weld them.

  P3  OUT-OF-BAND VERIFICATION WITH A FOREIGN ORACLE. The two real findings in
      #5 came from running large-sample checks against the code, NOT from the
      suite -- and the strongest was re-parsing the rendered string with Python's
      OWN grammar (a different oracle than evaluate_expression). For #2, the
      analogous foreign-oracle check: at each difficulty rung, generate a large
      sample and verify the structural properties hold (depth bound, every node
      satisfies its invariant, generation never raises) independent of the
      production code path. Make this a standing step for any correctness-
      critical commit.

  P4  SURFACE, DON'T SMOOTH -- and check the CODE, not your assumption, when a
      check fails. Twice in #5 a verification check failed and the CODE was right
      while the CHECK was wrong; the discipline that mattered was going to the
      code to find which side the DESIGN supports before editing anything. State
      this as a standing instruction in the implementation brief.

  P5  THE KNOWN-SENSITIVITIES CHECKLIST (section 4) is itself a carried-over
      improvement: #5 lacked it and my two findings were exactly the items an
      adversarial review had flagged but the handoff had not promoted to a
      checklist. The #2 design thread should END its adversarial review by
      writing the implementer's sensitivity checklist explicitly.

  P6  FROZEN-BY-DEFAULT for the eventual implementation thread. Implementation
      threads treat the design as settled and push back only on a discovered
      contradiction (trivial: fix with judgment + note; substantial: stop, go to
      the code, bring evidence). That default kept #5 fast. Keep it -- and if you
      DO want a second design opinion mid-implementation, say so explicitly, or
      it will (correctly) treat the design as frozen.

================================================================================
7. AFTER #2 (the sequence, so this thread knows what it is setting up)
================================================================================
Recommended path (from roadmap.md section 4, with the retro's adjustment):
  #2 difficulty (this) -> #1 MODULARIZE (extract JS modules; split drill.py into
  config/db/logic/http/main mirroring the existing section boundaries) -> then
  #7 adaptive selection (a clean single-function swap of pick_next_question,
  which difficulty makes meaningful) -> #6 SM2 (a selection policy that plugs
  into the #7 seam; lands its own migration for the scheduling fields reserved
  in ADR-025).
Rationale for #1 immediately after #2: #2 is the LAST feature to add to the
1900-line index.html / monolithic drill.py (roadmap flags this as the single
biggest maintainability risk); doing #1 right after means modularizing code you
understand cold, before new drills (#9/#10) or SM2 widen the surface. #2 sets
this up by being self-contained LOGIC+HTTP -- it should not entangle itself with
selection or storage in ways that complicate the modular split.

================================================================================
8. HOW THIS THREAD ENDS (the deliverable)
================================================================================
A settled-decisions + commit-plan handoff in the #5 format:
  - one-paragraph spine;
  - Q1-Q6 resolved with rationale;
  - adversarial review (the lenses), ending in the implementer's KNOWN-
    SENSITIVITIES checklist (P5);
  - a topologically-sorted commit plan, each commit landing green, with the
    "why green / ordering" line and HAIKU/SONNET classification, weld points
    marked (P2);
  - ADRs to write (next free numbers ADR-038+), and which existing ADRs to
    CLOSE (ADR-030's per-operand-range item if Q2 opens it; ADR-031's
    provisional-defaults note if Q6 re-anchors them; ADR-037's D1/D2/D4/D5 doors
    as they are opened);
  - the "do not reopen" list (section 5) restated as binding.
