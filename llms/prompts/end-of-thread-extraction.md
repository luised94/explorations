Extract the portable artifacts from this conversation. A new thread will use these as its entire starting context - it has no access to this conversation.
Produce the following sections. Include only what exists - do not generate or infer missing content.
1. Spec or partial spec The most complete version of the specification or requirements that exists in this thread. Paste as-is if present. If partial, label each section as COMPLETE or INCOMPLETE.
2. Decisions made Flat list. Decisions that were reached and would not be revisited. One line each with rationale in a parenthetical.
3. Rejected approaches Flat list. Things explicitly ruled out and why. One line each.
4. Open questions Flat list. Unresolved questions that would affect the design. One line each.
5. Code or implementation state (if applicable) What was built, what works, what broke, and what caused the stop. If code blocks exist in the thread, include them.
6. Friction points (if applicable) Problems encountered during implementation or design that were not resolved.
Format the entire output as a single code block for clean copying.
---
Review this conversation and produce a thread triage report. Be brief and direct.
1. Thread type - classify as one of:
* Seed: a raw idea, mostly questions, nothing decided
* Concept: idea with emerging constraints or values, no spec
* Draft: concept with partial requirements or a rough spec
* Spec: complete enough for adversarial review
* Partial implementation: code was started, may be incomplete or broken
* Abandoned: implementation stopped due to a specific problem
* Research: domain exploration with no deliverable yet
* Problem statement: a pain point identified, no solution yet
2. Core idea - one sentence. What is the thing.
3. What is already decided - constraints, values, or rejections that emerged and would survive into a spec. Flat list, one line each.
4. What is unresolved - questions that would change the design significantly if answered differently. Flat list.
5. Artifacts present - list any specs, commit plans, code, or structured documents that exist in this thread.
6. Recommended entry point - where this thread enters the planning workflow:
* Crystallization: idea not ready, needs more thinking first
* Initiation - Approach 1: ready for structured intake interview
* Initiation - Approach 2: strong constraints exist, use constraint-first
* Initiation - Approach 3: strong references/analogies exist, use analogical anchoring
* Red team: spec exists, enter adversarial review directly
* Recovery: implementation exists, needs retrospective before re-entering
7. Readiness - one of: not ready / ready with gaps / ready
