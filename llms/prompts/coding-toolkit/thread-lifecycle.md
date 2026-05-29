อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: design_thread.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ

# Design Thread
VERSION: 1
UPDATED: 2026-05-27

Prompts for exploratory design work. Two forms: an opening prompt
that starts the thread, and a multi-round protocol that governs
the full design cycle from exploration to spec.

---

## Opening Prompt

Attach: environment.md, coding_style.md, any prior specs or handoff
docs from related projects.

```
Peruse the attached documents. They may be out of date or out of
sync. Cross-reference and identify any issues, contradictions,
ambiguities, decisions to make, or conflicts. Verbalize suggested
reconciliation.

Once aligned, I need to design [component/system] for [project].
Here is what I know so far: [2-3 sentences of context].

Provide feedback, then gather context by asking targeted questions,
socratic questions, veteran questions.
```

---

## Multi-Round Protocol

Paste this when you want the LLM to follow a structured design
cycle rather than free-form conversation. Useful for complex design
problems that will take 3-5+ rounds.

```
Follow this design cycle:

PHASE 1 - EXPLORE
Provide initial feedback on the problem as stated. Ask targeted,
socratic, and veteran questions to understand constraints, goals,
unknowns, and existing context. Do not propose solutions yet.
Surface latent knowledge - things a veteran would consider that
I haven't mentioned. We will go through as many rounds of Q&A
as needed.

PHASE 2 - CONVERGE
I will signal convergence ("I agree with X", "let's narrow to Y",
"let's focus on Z"). When I do, synthesize the decisions made so
far. Identify remaining open questions. For each open question,
use naive-to-veteran analysis: present naive approaches, explain
drawbacks, discard. Then present veteran approaches with
prioritized recommendation. I will make final decisions.

PHASE 3 - SPECIFY
Once all decisions are made, produce a spec artifact following
data dictionary + command reference format: entities and fields
first, then file layout, then operations, then display formats,
then metrics, then commit plan. Include inline ADRs (Decision /
Why / Rejected, 3 lines each) for every significant decision.

PHASE 4 - PLAN
Produce a commit-by-commit breakdown. Every commit is haiku or
sonnet level - no opus. Include dependency graph showing
parallelization threads. Classify each commit.

Signal which phase you're in at the start of each response.
```

---

## Phase Transition Signals (user's side)

- "Provide feedback"  stay in Phase 1
- "I agree with X" / "let's narrow"  move to Phase 2
- "Produce the spec" / "ready for spec"  move to Phase 3
- "Produce the commit plan"  move to Phase 4
- "I want to go back to exploring"  return to Phase 1


อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: thread_consolidator.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ

# Thread Consolidator
VERSION: 1
UPDATED: 2026-05-27

Prompts for compressing thread state. Two uses: mid-thread
compression to fight context window decay, and end-of-thread
archival for record-keeping.

---

## Mid-Thread Consolidation

Use when a thread is getting long (15+ exchanges) and you want to
reset context without losing decisions. Paste the output back into
the same thread as a "here's where we are" anchor.

```
Consolidate this thread. Produce a concise state summary covering:

1. DECISIONS MADE - each decision with its rationale, one line each
2. CURRENT STATE - what exists now (files, code, data, artifacts)
3. OPEN QUESTIONS - unresolved items, pending decisions
4. NEXT STEPS - what we were about to do when this consolidation
   was requested

Format for re-injection: the output should be pasteable into this
thread or a new thread as complete context. A reader with no prior
context should understand the project state from this summary alone.

Do not editorialize or add new suggestions. Capture the state as-is.
```

### After receiving the consolidation

Paste it back with:
```
Here is the consolidated state of our work so far. Verify it
matches your understanding of the thread. Flag anything missing
or incorrect. Then continue from NEXT STEPS.
```

---

## End-of-Thread Archival

Use at the end of a thread for record-keeping. This is a snapshot,
not a handoff (see handoff_creator.md for starting new threads).

```
Archive this thread. Produce a concise record covering:

1. THREAD PURPOSE - what this thread set out to accomplish
2. DECISIONS MADE - each decision with rationale, one line each
3. ARTIFACTS PRODUCED - list with one-line descriptions
4. OUTCOME - what was accomplished, what was deferred
5. LESSONS - anything learned about the process, tools, or domain
   that should inform future work

Keep it factual. This is a record, not a narrative.
```

---

## Conventions

- Consolidations should be 30-60 lines, not longer
- Every decision listed should be traceable to a point in the thread
- Open questions should state WHY they're open (missing info?
  deferred? disagreement?)
- The consolidation replaces reading the thread, not supplements it


อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: handoff_creator.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ

# Handoff Creator
VERSION: 1
UPDATED: 2026-05-27

Prompt for generating handoff documents at thread boundaries.
A handoff enables a new thread (or a future reader) to continue
work without access to the original conversation.

---

## When to use

- Ending a design thread, starting implementation
- Ending an implementation phase, starting the next
- Switching between projects
- Any time the next conversation needs full context from this one

## Prompt

```
Produce a handoff document for this thread. The document must be
self-contained - a reader in a new thread with no access to this
conversation should have everything they need to continue the work.

Include sections for each of the following that is relevant to
what this thread covered. Skip sections that don't apply. Order
by importance to the next thread.

Possible sections:
- Project overview and purpose
- Architecture and structural decisions
- Directory structure (code and data locations)
- Environment and tooling
- Data format and conventions
- Key decisions with rejected alternatives (ADR-style)
- Current implementation state (what exists, what doesn't)
- File and naming conventions
- API or command interface
- Metrics and instrumentation
- Integration points with other modules
- Deferred work and known gaps
- Artifacts produced in this thread (with one-line descriptions)
- What the next thread should do (specific scope)
- Veteran advice and pitfalls to avoid

Format: markdown with ## headers. Each section should be scannable
- use short paragraphs, key-value pairs, or compact tables where
they aid clarity. No bullet-point lists unless genuinely needed.

Title the document: "Branch Handoff: [project/phase name]"
```

---

## Conventions

- The handoff is flexible - sections adapt to what the thread
  actually covered, not a rigid template
- Every decision should state what was rejected and why
- "What the next thread should do" is mandatory - it's the reason
  the handoff exists
- Keep under 200 lines. If it's longer, the thread covered too
  much and should have been split earlier
- Include enough context to reconstruct reasoning, not just
  conclusions


อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: thread_explainer.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ

# Thread Explainer
VERSION: 1
UPDATED: 2026-05-27

Prompts for recovering context after being away. Two forms:
returning to the same thread, or starting a new thread with
a handoff document from a prior conversation.

---

## Same-Thread Return

Use when you're back in a thread after days away and need to
re-orient before continuing.

```
I've been away from this thread for a while. Before we continue:

1. Summarize where we are - what was the goal, what decisions
   were made, what state are we in.
2. What were we about to do when the thread went inactive?
3. Are there any decisions or open questions that I should
   reconsider with fresh eyes?
4. What's the most important next step?

Keep the summary concise. I'll tell you when I'm oriented and
ready to continue.
```

---

## New-Thread Orientation

Use when opening a new thread with a handoff document or prior
artifacts and you need the LLM to internalize the context before
starting work.

Attach: handoff document, spec, and any other relevant artifacts.

```
Peruse the attached documents. They describe a project I've been
working on in prior threads. Before we start new work:

1. Summarize your understanding of the project - architecture,
   current state, key decisions, what's been built and what hasn't.
2. Identify anything that seems unclear, inconsistent, or
   incomplete in the attached documents.
3. State what you think the next priorities should be, based on
   the documents.

I'll confirm or correct your understanding, then we'll proceed.
```

---

## Compact Same-Thread Form

For quick re-orientation when you've only been away briefly:

```
Quick recap - where are we and what's next?
```

---

## Conventions

- The explainer should not introduce new ideas or suggestions
  beyond what's in the existing context - that comes after
  orientation is confirmed
- For same-thread: the LLM has full history, so it should
  reference specific exchanges, not just generalize
- For new-thread: the LLM only knows what's in the attached docs,
  so it should flag gaps honestly rather than filling them
- Always wait for the user to confirm orientation before
  proceeding with new work
