# Consultation Initiation - Three Approaches

---

## Approach 1 - Structured Intake

**When to use:** You have a clear idea but have not written it down. You know what you want to build but the spec does not exist yet.

**Mechanism:** The LLM runs a structured discovery session. You answer; it extracts. No spec writing on your end.

**Initiation prompt:**
> You are conducting a technical intake for a software project. Your goal is to produce a draft specification suitable for adversarial review. Ask me questions one at a time - do not batch them. Cover these dimensions in order, but adapt based on my answers:
>
> 1. What the system does in one sentence.
> 2. What it must never do - hard constraints, non-negotiable exclusions.
> 3. What the data is: what goes in, what comes out, what persists.
> 4. Who uses it and in what context (single user, CLI, library, service).
> 5. What "done" looks like for a first working version.
> 6. What I am most uncertain about.
>
> After all questions are answered, produce: (a) a one-paragraph project summary, (b) a flat constraint list, (c) a draft specification with data layout, phase structure, and a commit plan. Label it "DRAFT - ready for red team review." Do not refine it further. Its job is to survive criticism, not to be correct.

**Output artifact:** Draft spec + constraint list.

**Workflow slot:** Replaces the self-written spec. Feeds directly into the red team prompt. The constraint list seeds Block S.

---

## Approach 2 - Constraint-First Narrowing

**When to use:** You know your taste and values strongly but have not defined the positive requirements yet. You think in terms of what you want to avoid more than what you want to build. Works well for refactors of existing systems.

**Mechanism:** Establish what the project must not be. The spec emerges from what remains.

**Initiation prompt:**
> We are defining a software project by elimination. I will tell you what I do not want. Your job is to derive what I must want from the constraints I give you, surface any contradictions, and produce a minimal viable spec from what survives.
>
> Start by asking me for my hard rejections - paradigms, patterns, dependencies, architectural decisions I will not accept under any circumstances. Then ask what problem the system must solve. Then ask what the simplest possible version looks like.
>
> After each answer, reflect back what the constraint rules out and what it implies. When we have enough to proceed, produce:
> (a) A constraint document - the hard rejections with one-line rationale for each.
> (b) A minimum viable spec - the smallest system that satisfies the positive requirements left after elimination.
>
> Label it "DRAFT - constraint-derived." Flag any place where my constraints conflict with each other.

**Output artifact:** Constraint document (becomes Block S input) + minimal spec.

**Workflow slot:** The constraint document feeds Block S directly - review it before the red team runs so the red team is already working against your actual values. The minimal spec feeds the red team. This approach produces the tightest initial specs because scope is bounded by exclusion before anything is added.

---

## Approach 3 - Analogical Anchoring

**When to use:** You think in terms of examples, taste, and reference systems. You know what you admire and what you want to avoid, but requirements feel abstract until you can point at something. Works well for novel projects where you are still discovering what you want.

**Mechanism:** Extract design values from analogies. Build the spec from those values, not from requirements.

**Initiation prompt:**
> We are defining a software project through analogy. I will describe it in terms of systems I admire or want to avoid. Your job is to extract the underlying design values from my references and derive a specification from those values - not from the surface features of the analogies.
>
> Ask me:
> 1. What existing system is the closest thing to what I want to build - and what specifically about it I want to preserve.
> 2. What existing system represents what I want to avoid - and what specifically I am rejecting.
> 3. Where the analogy breaks down - what is genuinely different about what I am building.
>
> After each answer, name the design values my references imply. Check them against each other for contradictions. When the value set is stable, produce:
> (a) A design values document - the extracted principles with one-line rationale.
> (b) A draft spec built from those values, not from the analogies directly.
>
> Label it "DRAFT - value-derived." Also note which expert personas the design values suggest for the review panel - the values should predict who will have the most useful friction with this design.

**Output artifact:** Design values document + draft spec + suggested expert personas.

**Workflow slot:** The design values document informs expert persona selection before the red team runs - you know which reviewers will produce maximum friction because the values already predict the disagreements. The draft spec feeds the red team. This is the only initiation approach that feeds directly into expert panel composition.

---

## Where Each Approach Slots

```
                    ÚÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄ¿
                    ³         INITIATION PHASE            ³
                    ³                                     ³
  Approach 1 ÄÄÄÄÄÄÄ´  Draft spec + constraint list       ³
  Approach 2 ÄÄÄÄÄÄÄ´  Constraint doc + minimal spec      ³
  Approach 3 ÄÄÄÄÄÄÄ´  Values doc + draft spec + personas ³
                    ÀÄÄÄÄÄÄÄÄÄÄÄÄÄÄÂÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÙ
                                   ³
                          Block S assembly
                          (constraints  1)
                                   ³
                    ÚÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄ¿
                    ³           RED TEAM                  ³
                    ³  (adversarial filter on draft spec) ³
                    ÀÄÄÄÄÄÄÄÄÄÄÄÄÄÄÂÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÙ
                                   ³
                              Prompt C
                          (user verdicts)
                                   ³
                    ÚÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄ¿
                    ³         EXPERT PANEL                ³
                    ÀÄÄÄÄÄÄÄÄÄÄÄÄÄÄÂÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÙ
                                   ³
                    ÚÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄ¿
                    ³           INTEGRATION               ³
                    ÀÄÄÄÄÄÄÄÄÄÄÄÄÄÄÂÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÙ
                                   ³
                          Style compliance
                          Conflict resolution
                          Handoff assembly
                                   ³
                    ÚÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄ¿
                    ³         IMPLEMENTATION              ³
                    ÀÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÙ
```
