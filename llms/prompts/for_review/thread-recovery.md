# Thread Recovery System

---

## Step 1 - Triage Prompt
# Paste this into any old thread to classify it and identify the entry point.

---

> Review this conversation and produce a thread triage report. Be brief and direct.
>
> **1. Thread type** - classify as one of:
> - *Seed*: a raw idea, mostly questions, nothing decided
> - *Concept*: idea with emerging constraints or values, no spec
> - *Draft*: concept with partial requirements or a rough spec
> - *Spec*: complete enough for adversarial review
> - *Partial implementation*: code was started, may be incomplete or broken
> - *Abandoned*: implementation stopped due to a specific problem
> - *Research*: domain exploration with no deliverable yet
> - *Problem statement*: a pain point identified, no solution yet
>
> **2. Core idea** - one sentence. What is the thing.
>
> **3. What is already decided** - constraints, values, or rejections that emerged and would survive into a spec. Flat list, one line each.
>
> **4. What is unresolved** - questions that would change the design significantly if answered differently. Flat list.
>
> **5. Artifacts present** - list any specs, commit plans, code, or structured documents that exist in this thread.
>
> **6. Recommended entry point** - where this thread enters the planning workflow:
> - *Crystallization*: idea not ready, needs more thinking first
> - *Initiation - Approach 1*: ready for structured intake interview
> - *Initiation - Approach 2*: strong constraints exist, use constraint-first
> - *Initiation - Approach 3*: strong references/analogies exist, use analogical anchoring
> - *Red team*: spec exists, enter adversarial review directly
> - *Recovery*: implementation exists, needs retrospective before re-entering
>
> **7. Readiness** - one of: *not ready / ready with gaps / ready*

---
---

## Step 2 - Recovery Prompt
# Paste this after triage to extract the portable artifacts from the thread.
# Use for Spec, Partial implementation, or Abandoned threads.

---

> Extract the portable artifacts from this conversation. A new thread will use these as its entire starting context - it has no access to this conversation.
>
> Produce the following sections. Include only what exists - do not generate or infer missing content.
>
> **1. Spec or partial spec**
> The most complete version of the specification or requirements that exists in this thread. Paste as-is if present. If partial, label each section as COMPLETE or INCOMPLETE.
>
> **2. Decisions made**
> Flat list. Decisions that were reached and would not be revisited. One line each with rationale in a parenthetical.
>
> **3. Rejected approaches**
> Flat list. Things explicitly ruled out and why. One line each.
>
> **4. Open questions**
> Flat list. Unresolved questions that would affect the design. One line each.
>
> **5. Code or implementation state** *(if applicable)*
> What was built, what works, what broke, and what caused the stop. If code blocks exist in the thread, include them.
>
> **6. Friction points** *(if applicable)*
> Problems encountered during implementation or design that were not resolved.
>
> Format the entire output as a single code block for clean copying.

---
---

## Thread Category  Workflow Entry Point

```
THREAD TYPE          ENTRY POINT                 FIRST PROMPT TO RUN
-----------          -----------                 -------------------
Seed                 Crystallization             Crystallization prompt
                                                 (may return "not ready")

Problem statement    Initiation - Approach 2     Constraint-first narrowing
                     (constraint-first)          (pain point  what to exclude)

Research             Crystallization             Crystallization prompt
                                                 (often returns "not ready")

Concept              Initiation - choose by      Approach 1, 2, or 3
                     dominant signal:            depending on triage output
                     constraints  2
                     analogies  3
                     uncertainty  1

Draft                Initiation - Approach 1     Structured intake to fill gaps
                     (fill the gaps)             then red team the output

Spec                 Red team directly           Red team prompt
                                                 (where this session started)

Partial              Recovery  then             Recovery prompt  assess what
implementation       Red team or Continue        exists  re-enter at spec or
                                                 continue from last commit

Abandoned            Recovery  Retrospective    Recovery prompt  then:
                      then Red team             "What broke and why? What
                                                 would the design need to
                                                 change to avoid it?"
                                                  then red team revised spec
```

---

## Retrospective Prompt
# For Abandoned threads only. Run after Recovery.

---

> This project was abandoned. Before re-entering the planning workflow, run a retrospective.
>
> Based on the recovered artifacts, answer:
>
> **1. What broke** - the specific problem that caused the stop. One sentence.
>
> **2. Root cause** - was it a design problem, an implementation problem, a tooling problem, or a motivation problem? One sentence.
>
> **3. What the design would need to change** - the minimum change to the spec or approach that would avoid the same stop. If nothing needs to change, say so.
>
> **4. Re-entry verdict** - one of:
> - *Resume*: the design is sound, the stop was incidental. Continue from last commit.
> - *Revise then resume*: apply the design change, then continue.
> - *Restart*: the design has a fundamental problem. Re-enter at red team with revised spec.
> - *Abandon*: the problem that caused the stop is not solvable within the current constraints.
>
> Do not produce a new spec. Do not start planning. This is a diagnosis only.
