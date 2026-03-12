This thread is ending. Produce a handoff document for the first implementation session. A new LLM instance will receive this document as its entire context — it has no access to this conversation.
The handoff document must contain exactly these sections, in this order. Be dense. Cut anything that does not change how the implementation LLM would behave.
1. Project (2 sentences max) What is being built and what is the runtime/language/constraints summary.
2. Hard constraints (flat list, one line each) Every constraint that applies to every commit. These are never repeated per-commit.
3. Final spec The complete integrated specification produced in this thread. Include the full commit plan with commit messages, files, and what each commit does. Do not summarize — paste the spec as-is. This is the source of truth.
4. Design decisions made in this thread that are not in the spec (flat list) Any decision reached during review that overrides or supplements the spec. One line per decision with rationale in a parenthetical.
5. Session scope Which commits to execute in the first implementation session. State the stopping commit explicitly.
6. First action One sentence: what the implementation LLM does first.
Format the entire handoff document as a single code block so it can be copied cleanly.
