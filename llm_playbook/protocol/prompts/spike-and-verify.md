# Prompt: spike and verify (de-risk the plan empirically before committing)

date: 2026-07
type: prompt
scope: proving risky assumptions with cheap experiments, between an
agreed design and a locked plan.

Between a converged DESIGN (adversarial-review) and a locked PLAN
(commit-planning) sits the phase where you PROVE the risky assumptions with the
cheapest possible experiments, instead of discovering them mid-implementation.
Born in the modularization thread, where five spikes turned three guessed
answers into measured ones and reordered the whole frontend approach.

--------------------------------------------------------------------------------
USE THIS WHEN
--------------------------------------------------------------------------------
Run it once the design is agreed but the plan rests on assumptions you have not
VERIFIED against the real code / real tools:
  - a capability you are assuming (does the runtime/library actually do X?)
  - a boundary you believe is clean (is the dependency graph really one-way?)
  - a harness change whose blast radius you are guessing at
  - a guard you intend to build (does it actually catch the thing, and stay
    green on clean code?)

SKIP IT WHEN the assumptions are already known-true from THIS codebase (not from
training-data memory of how the tool "usually" behaves) or the change is
mechanical. A spike proves a claim you are otherwise about to TRUST blindly.

The bar: "if this assumption is wrong, does the plan change?" If yes, spike it.

--------------------------------------------------------------------------------
PRINCIPLE
--------------------------------------------------------------------------------
Spike only where a wrong guess forces rework across many commits. Cheap-to-
reverse decisions do not need a spike -- decide inline and note the assumption.
Expensive-to-reverse or plan-gating ones do. Rank spikes by (blast radius if
wrong) x (uncertainty), do the gating ones first, and let each result prune the
next (a dead option removes its dependent spikes).

--------------------------------------------------------------------------------
HOW TO RUN
--------------------------------------------------------------------------------
1. STATE THE ASSUMPTION as a falsifiable claim. Not "jsdom probably runs
   modules" but "jsdom AT THIS VERSION executes <script type=module> from a
   string-loaded doc." Name the version / file / real inputs.

2. BUILD THE SMALLEST EXPERIMENT that could FALSIFY it. A throwaway file, a
   probe script, an AST pass over the real source -- not the real change.
   Read-only analysis spikes (census the dependency graph, count the mutation
   sites) are safe to run before any decision is locked; they modify nothing.

3. RUN IT AGAINST THE REAL ARTIFACT, at the pinned SHA, with the real tool
   versions. A spike on a toy that does not match the repo proves nothing.

4. PROVE BOTH DIRECTIONS for a guard: it must be GREEN on the clean code AND
   RED on an injected violation. A guard that cannot fail is worthless; inject
   the violation and watch it catch it. (The modularization purity guard was
   proven this way -- a function-local `import datetime` dodged a module-level
   import ban and only the AST call-check caught it.)

5. PRUNE ONE-BY-ONE. Do gating spikes first; report each result before the
   next, so a dead answer collapses the option tree instead of spending the
   remaining spikes on branches that no longer exist.

6. DISTRUST YOUR OWN ANALYZER. An AST/grep spike produces FALSE POSITIVES:
   parameter names shadowing top-level names; layer-by-line-range misfiling a
   symbol; a substring match hitting a comment. Before believing a spike's
   "violation," confirm it is real in the source. Prefer scope-aware, symbol-
   based checks over line-range / raw-substring ones. A spike that "found 3
   problems" all of which are analyzer artifacts is the normal first result.

--------------------------------------------------------------------------------
OUTPUT
--------------------------------------------------------------------------------
For each spike: the falsifiable claim; the experiment (and why it is the
smallest one); the RESULT as a fact; and the CONSEQUENCE for the plan (which
option it kills, which assumption it confirms, what it reorders). Carry the
confirmed facts into commit-planning as givens, and record the surprising ones
(and the false-positive lessons) in the findings doc -- they are the cheapest
knowledge the project will buy.

--------------------------------------------------------------------------------
CONTEXT / INFORMATION GATHERING (do this before AND during spikes)
--------------------------------------------------------------------------------
  - Read the real code first; ground every assumption in it, never in how a
    tool "usually" behaves.
  - Census before deciding: count the call sites / mutation sites / cross-
    boundary references. "Where there is one, there are many" -- the count
    changes the plan (concentrated vs smeared is a different problem).
  - Verify tool + language versions at the pinned SHA; behavior differs across
    them and the plan inherits whatever the clone actually runs.
  - When a reference is a name you do not yet have (a symbol, a file, a
    version), resolve it by looking, not by guessing.
