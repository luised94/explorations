# Handoff Prompt Template
VERSION: 1
UPDATED: 2026-05-28

Prompt instructions for producing a handoff document at the end of an
implementation thread. Paste into the thread when requesting handoff.

---

## Prompt

```
Produce a handoff document for this thread. Cover all sections below.
The audience is an LLM in a fresh thread that has no memory of this
conversation -- it will receive this document, the spec, the commit
plan, and the current file state. Everything it needs to continue
must be in these documents.

COMPLETED COMMITS
  Table: commit number, level, thread, one-line summary.

WHAT WAS BUILT
  Table: commit number, summary, key output (functions, constants,
  patterns introduced). Dense but complete -- a reader should know
  every def, every constant, every structural decision from this table
  without reading the code.

SHARED FUNCTIONS AND SIGNATURES
  Table: function name, full signature with types, what it returns,
  every call site in the current phase (name the callers). This is the
  contract the next thread builds on. If a function has an assumed
  future caller that has not materialized yet, note it.

ESTABLISHED PATTERNS
  Named patterns with numbered steps. The next thread will be told
  "follow the X pattern" -- these must be concrete enough to follow
  without seeing the exemplar code. Include the prefix match
  consumption pattern, mutation command pattern, view command pattern,
  or whatever patterns this project uses.

DEVIATIONS FROM SPEC OR PLAN
  Numbered list. Each entry: what the plan said, what was implemented
  instead, why, and impact on later commits. These are now canonical
  -- the next thread treats them as decisions, not drift.

CURRENT FILE STATE
  Instruct the user to paste the full file into the next thread.
  Do not reproduce the file in the handoff -- it is a separate
  attachment.

NEXT THREAD SCOPE
  Which commits the next thread should cover. Recommended batching
  with rationale (which commits can be batched, which need isolation).
  Note any dependencies or convergence points.

OPEN QUESTIONS
  Anything unresolved that the next thread should address before
  writing code. Mark each as [DECISION NEEDED] or [VERIFY].
```

---

## When to request handoff

- Scoped commits for the thread are complete
- Thread is approaching 15-20 exchanges
- Switching from implementation to design or refinement
- Phase boundary reached
- You realize the tool is not yet usable and want to extend scope
  (adjust before requesting handoff, not after)

---

## Receiving a handoff in a new thread

Opening prompt for the new thread:

```
This is an implementation thread for [project]. Scope: commits [N-M].

Here is the spec: [paste]
Here is the commit plan: [paste]
Here is the handoff from the previous thread: [paste]
Here is the current file state: [paste]
Here are the workflow and style rules: [paste]

Cross-reference all documents before producing code. Identify any
contradictions, ambiguities, or decisions needed. Then proceed with
the first commit (or batch).
```
