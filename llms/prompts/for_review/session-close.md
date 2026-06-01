# SESSION CLOSE PROMPT A
# Use at the end of a design/review thread, before starting implementation.
# Produces the opening prompt for the first implementation session.

---

> This thread is ending. Produce a handoff document for the first implementation session. A new LLM instance will receive this document as its entire context - it has no access to this conversation.
>
> The handoff document must contain exactly these sections, in this order. Be dense. Cut anything that does not change how the implementation LLM would behave.
>
> **1. Project** (2 sentences max)
> What is being built and what is the runtime/language/constraints summary.
>
> **2. Hard constraints** (flat list, one line each)
> Every constraint that applies to every commit. These are never repeated per-commit.
>
> **3. Final spec**
> The complete integrated specification produced in this thread. Include the full commit plan with commit messages, files, and what each commit does. Do not summarize - paste the spec as-is. This is the source of truth.
>
> **4. Design decisions made in this thread that are not in the spec** (flat list)
> Any decision reached during review that overrides or supplements the spec. One line per decision with rationale in a parenthetical.
>
> **5. Session scope**
> Which commits to execute in the first implementation session. State the stopping commit explicitly.
>
> **6. First action**
> One sentence: what the implementation LLM does first.
>
> Format the entire handoff document as a single code block so it can be copied cleanly.

---
---

# SESSION CLOSE PROMPT B
# Use at the end of an implementation session that will continue in a new thread.
# Produces the opening prompt for the next implementation session.

---

> This thread is ending. Produce a handoff document for the next implementation session. A new LLM instance will receive this document as its entire context - it has no access to this conversation or the codebase.
>
> The handoff document must contain exactly these sections. Be maximally dense. Omit anything that does not change how the next LLM would write code.
>
> **1. Project** (1 sentence)
> What is being built.
>
> **2. Hard constraints** (flat list, one line each)
> Every constraint applying to all remaining commits.
>
> **3. Commit plan status**
> The full commit list. Mark each as DONE / CURRENT / PENDING. For DONE commits, one line only. For the CURRENT commit (if incomplete) or the next PENDING commit, include the full spec entry - message, files, what it does, and verification script.
>
> **4. Established patterns** (flat list, one line each)
> Code-level patterns set in prior commits that the next LLM must match. Examples: naming conventions, how module-level state is declared, how precondition asserts are written, how verification scripts are structured. Only patterns that are non-obvious or that deviate from the spec.
>
> **5. Spec deviations** (flat list, or "None")
> Any place where the implementation diverged from the spec and why. If the deviation is now the canonical approach, say so.
>
> **6. Current state**
> Last commit completed and whether its verification script passed. If the current commit is partially implemented, describe what exists and what remains.
>
> **7. First action**
> One sentence: what the implementation LLM does first.
>
> Format the entire handoff document as a single code block so it can be copied cleanly.

---
---

# SESSION OPEN TEMPLATE
# This is the wrapper the user pastes the handoff document into at the start
# of a new thread. Works for both Case A and Case B.

---

> You are continuing a software implementation project. Your entire context for this session is the handoff document below. Do not ask about anything not covered in the document - make reasonable assumptions consistent with the constraints and proceed.
>
> Begin with the first action stated at the end of the document. After completing each commit, confirm the commit message and ask before proceeding to the next.
>
> [PASTE HANDOFF DOCUMENT HERE]
