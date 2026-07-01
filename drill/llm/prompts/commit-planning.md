# Prompt: commit planning (decompose, sort, predict downstream)

Turn an agreed design into an ordered, each-commit-green implementation plan.
Born in D1, where it exposed two things the prose plan hid: a commit that was
secretly two (the "opus"), and a shared-assumption change whose blast radius
was larger than the diff.

--------------------------------------------------------------------------------
USE THIS WHEN
--------------------------------------------------------------------------------
  - the change is more than ~3 commits, OR
  - commits have interdependencies (one must land before another), OR
  - the change touches a SHARED ASSUMPTION (a constant many things read) or a
    WIDELY-USED HELPER (a fixture/util many tests call).

SKIP IT WHEN the change is one or two independent commits with no shared-state
ripple. Do not ceremony-plan a typo fix.

--------------------------------------------------------------------------------
STEP 1 -- CLASSIFY each proposed commit
--------------------------------------------------------------------------------
  HAIKU  -- one atomic change, one idea, trivially reviewable.
  SONNET -- structured, multi-part, but ONE coherent movement (e.g. a code
            change + its test; parts in obligatory relation).
  OPUS   -- multiple INDEPENDENT movements riding together; each stands alone
            and is separately reviewable. DECOMPOSE opus into haiku/sonnet.

The opus tell: "this commit does X and ALSO Y, for different reasons, touching
different things." Split it.

--------------------------------------------------------------------------------
STEP 2 -- NAME THE DEPENDENCY EDGES (this is the real payoff)
--------------------------------------------------------------------------------
For each commit, what must already be true for it to be green? Writing the
edges down is what surfaces WELDED pairs -- two changes that cannot each be
green alone (e.g. bumping a constant reddens the test that asserts its old
value). A welded pair is either ONE commit, or an accepted red intermediate
(see "let it go red" below). Decide which, on purpose.

--------------------------------------------------------------------------------
STEP 3 -- PREDICT DOWNSTREAM EFFECTS *BEFORE* EDITING
--------------------------------------------------------------------------------
The highest-leverage habit. For any shared-assumption or shared-helper change:
  - grep EVERY consumer of the thing you are about to change.
  - for each consumer, ask: what does it ASSUME about the thing? (a version
    number? a fixture's state? a column's existence?)
  - the ones whose assumption you are breaking are your blast radius. Map them
    ALL in one pass, then fix in one pass.
Reactive (fix each red as it appears) is far more expensive than proactive
(map first). D1 did both; proactive won decisively.

A frequent finding: a single helper is serving two MEANINGS that happened to
coincide (e.g. temp_db = "baseline" AND "current version" while they were the
same number). When a change splits them, name the two meanings into two
explicit helpers rather than overloading one. Extract the implicit into the
explicit.

--------------------------------------------------------------------------------
STEP 4 -- TOPOLOGICAL SORT
--------------------------------------------------------------------------------
Order so every commit lands green (or with a deliberate, noted red). Output the
ordered list; for each: id, classification, files touched, the one-line goal,
what proves it green, and the CO-LOAD SET (below).

CO-LOAD SET (context budget -- the LLM-execution axis). For each commit, the
minimal set of files that must be in context TOGETHER to execute it correctly
(the file(s) edited + the source region being moved + the test that proves it +
the conventions it must honor). A commit whose co-load set is too large to hold
in one comfortable working context is an OPUS-BY-CONTEXT even if it is one
coherent movement -- split it, or sequence it so the set shrinks (e.g. extract a
dependency first so the dependent commit need not re-load it). This
operationalizes "keep commits at or below sonnet complexity": complexity is
measured by the co-load set, not just line count.

--------------------------------------------------------------------------------
"LET IT GO RED" (a deliberate tool, not sloppiness)
--------------------------------------------------------------------------------
When a test's red/green state would CONFIRM a hypothesis about coupling, it can
be worth landing a change that reddens it on purpose, observing the red, then
fixing -- because the red is evidence the guard works. Use only when the red is
informative; never as an excuse to skip green discipline.
