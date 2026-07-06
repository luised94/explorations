# LLM thread protocol
## Reusable template for LLM-assisted programming, design, and analysis
## threads on this repo. Distilled from the consolidation thread series;
## commit to llm/ and point kickoff prompts here instead of restating.

## Roles of a thread

Every thread is exactly one of: DESIGN (deliverable: decision-framed docs
plus spikes; no shipped features), IMPLEMENTATION (deliverable: commits
against a plan doc; no new design forks decided silently), or CAPTURE
(deliverable: scored backlog entries plus reasoning docs). Name the role in
the first line of the kickoff prompt. Mixed threads drift; if a thread must
change role, say so at a STOP point.

## Kickoff prompt skeleton (keep it short; the protocol lives here)

1. Role line and deliverable.
2. Repo access: the sparse-clone recipe, the directories in scope.
3. Pointer to the authoritative docs in llm/ (they are committed; do not
   paste unless unpushed, and then say they are unpushed).
4. INLINED GROUND TRUTH: exact signatures and facts the task leans on,
   copied from the code, never from memory. Label each as verify-first.
5. Instincts, labeled as instincts: "my lean is X; pressure-test it" --
   this earns the model the right to overrule with evidence, which is
   where the best corrections come from.
6. The style contract (below), verbatim. Models regress to nested
   functions, helper wrappers, and OOP without it, every time.
7. STOP points and what to do at them.

## The ten working rules

R1. REPO WINS. Every doc claim is a lead; on conflict with the code, the
    code is right. Do not silently comply with a wrong doc and do not
    silently ignore it: record the deviation.
R2. CORRECTIONS ARE FINDINGS. A handoff error discovered (a flag that does
    not exist, a feature already present, a stale assumption from another
    thread) is output, not noise. Keep a running deviations/corrections
    list; it feeds the next handoff.
R3. SPIKE BEFORE SPEC. Load-bearing design claims get executable evidence:
    a spike that runs green against the REAL modules (import the actual
    code; do not reimplement it to test it). Prose that could have been a
    spike is a smell.
R4. SPIKES ARE HANDOFF ARTIFACTS. A green spike is a pre-written
    acceptance test for the implementation thread. Deliver the files, not
    a summary of them.
R5. DECISION-FRAMED DOCS. Each fork: options, recommendation, reasoning,
    and what evidence would change the answer. The human keeps the choice;
    resolved forks become ADR entries in decisions.md IN THE SAME COMMIT
    as the code that resolves them.
R6. DOCS LAND FIRST. An implementation thread's first commit puts the
    design docs into llm/ so every future thread is self-sufficient from
    a clone. Cross-reference sibling docs; one lineage, no forks.
R7. ONE COMMIT AT A TIME. Implement, extend tests, run the full suite,
    commit with the plan id in the message. No batching. Record the real
    baseline number first.
R8. STOP POINTS. Pre-declared checkpoints where the thread summarizes what
    landed, surfaces deviations, asks the open questions, and waits.
    Undecided forks go here; deciding them silently is the failure mode.
R9. SCOPE HONESTY. At delivery, answer three questions: did anything
    called design smuggle in an implementation decision; did a decidable
    fork stay open out of caution; is there a materially simpler design
    that gets 80 percent of the value.
R10. ADVERSARIAL PASS. After delivery, a separate turn attacks the work:
    edge inputs (NULLs, same-day repeats, empty sets), layering and purity,
    migration idempotency, testability, and R9. If nothing changes, the
    review was not hard enough.

## The style contract (state verbatim in every code-producing thread)

Flat procedural code. Pure functions over plain dicts, lists, tuples. No
classes, no nested functions, no closures, no decorator machinery, no
wrapper-helper indirection. Full descriptive names carrying domain
information; no abbreviations unless the noun behaves as a word (url, id,
http). Reads, writes, clock, and randomness at the edges (HTTP/MAIN/
DATABASE); LOGIC never touches them -- time and random values are
parameters. Layering config <- db <- logic <- http is mechanical and
guarded by tests. ASCII only in every file.

## Handoff checklist (end of any DESIGN thread)

[ ] Ground-truth section with exact verified signatures and named
    corrections to prior handoffs.
[ ] Decision-framed doc(s); forks resolved or explicitly reserved.
[ ] Commit-level plan with per-commit files, names, tests, acceptance.
[ ] Green spike files, ASCII-clean, runnable from a fresh clone.
[ ] Deferred items recorded with reasons (so they are choices, not losses).
[ ] The three R9 questions answered in writing.

## Anti-patterns observed and banned

Trusting a summary over the code it summarizes. Reimplementing a function
inside its own test. Deciding a fork mid-commit because stopping felt
slow. Restating the whole protocol in every prompt (point here). Prose
claims of equivalence where a parameter-grid spike was cheap. Improving a
shipped policy (grading, scheduling) by taste instead of by a metric named
in advance.
