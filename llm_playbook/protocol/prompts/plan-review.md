# Prompt: plan review (adversarial critique of a commit-by-commit plan)

date: 2026-07
type: prompt
scope: adversarial critique of a SORTED COMMIT PLAN, before it executes.

The sibling of adversarial-review, aimed at a SORTED COMMIT PLAN rather than a
design. Kept a SEPARATE file on purpose: load it only when reviewing a plan, so
design-review lenses do not bleed into the wrong phase. Some framing is
duplicated from adversarial-review deliberately -- this file should stand alone.

--------------------------------------------------------------------------------
USE THIS WHEN
--------------------------------------------------------------------------------
Run it AFTER commit-planning has produced a classified, edge-named,
topologically-sorted plan, and BEFORE executing it -- especially when:
  - the plan spans multiple threads (the split must fall on a clean DAG seam)
  - any commit is hard to reverse, or lands a shared-assumption change
  - a "green" claim rests on a harness change or a fresh-clone behavior
  - the sequence gates later threads

SKIP IT WHEN the plan is one or two independent commits with obvious ordering.

The bar: "could a single sharp objection change the ORDER, the SPLIT, or a
green-claim?" If no, skip. Reviewing a trivial plan is theater.

--------------------------------------------------------------------------------
HOW TO RUN
--------------------------------------------------------------------------------
Critique the plan through each LENS below. Lenses matter; any persona is just
scaffolding to generate the objection. Ground every objection in the ACTUAL
plan and the ACTUAL code it will touch (read both). One objection that reorders
the plan or moves the thread boundary is worth more than pages of agreement.

LENSES (axis -- the question it forces):
  1. SEQUENCING / GREEN-AT-EACH-STEP -- does every commit land green given ONLY
     its predecessors? Walk the sort and check each commit's stated
     preconditions are satisfied by something earlier. A commit that needs a
     later commit to be green is mis-sorted or is half of a welded pair.
  2. WELDED PAIRS / HIDDEN OPUS -- is any "one commit" secretly two changes for
     different reasons (opus)? Is any pair impossible to green separately (a
     constant bump + the test asserting its old value)? For each welded pair,
     is it ONE commit or a DELIBERATE noted red -- decided on purpose, not by
     accident?
  3. BLAST RADIUS / REVERSIBILITY -- for each shared-assumption or shared-helper
     commit, are ALL consumers mapped (grep, not guess)? Which commit is hardest
     to unwind if wrong? Is the irreversible one sequenced late, after the
     cheap-to-reverse ones have de-risked it?
  4. VERIFICATION HONESTY -- is each "what proves it green" actually TRUE in a
     FRESH clone with the real tool versions, or aspirational? Does any commit
     rely on a harness/glob/loader behavior that has not been spiked? A green
     claim that has not been run in the clean room is a hypothesis.
  5. THREAD SPLIT / SYNC POINTS -- does the multi-thread boundary fall on a clean
     cut in the dependency DAG (few edges crossing, no atomic step straddling
     the seam)? Is any ATOMIC commit (one that cannot be partial -- e.g. a
     cutover that reddens many tests at once) kept WHOLE within one thread's
     working memory? A split that puts a sync point across threads is wrong.
  6. CONTEXT BUDGET -- is any commit's co-load set too large to execute well
     (opus-by-context)? Does the sort minimize re-loading (dependencies extracted
     before dependents)? Is each thread's total context plausibly holdable?
  7. BEHAVIOR-PRESERVATION (for refactors) -- does any commit claim "no behavior
     change" while actually rewriting logic? A cut must be relocation + import
     plumbing only; if the diff carries new logic, it is mis-classified and its
     green claim is suspect.

OUTPUT
  - For each lens: the sharpest objection, or "confirms" with one line of why.
  - A CONSENSUS ATTACK if several lenses converge on the same commit/seam (the
    signal to re-sort or move the thread boundary).
  - A revised sort / split, or an explicit "plan stands because ...".

--------------------------------------------------------------------------------
NOTE
--------------------------------------------------------------------------------
This prompt reviews the PLAN. If an objection reaches back into the DESIGN
(the boundaries themselves are wrong), stop and re-open adversarial-review --
do not patch a design flaw with a resort. If an objection reaches a factual
UNKNOWN ("we are assuming the loader does X"), stop and spike it
(spike-and-verify) rather than sorting around a guess.
