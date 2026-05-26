
The refactor relied on a collection of tacit systems-design heuristics applied to prompts as if prompts were software architectures.

The key latent insight was:

> A large prompt is not "text."
> It is a behavioral specification system.

The refactor therefore treated the original prompt as:

* a coupled system
* with mixed concerns
* hidden dependencies
* duplicated constraints
* unstable interfaces
* implicit execution semantics

The following are reusable meta-prompts that encode the strategies used.

---

# 1. PROMPT ONTOLOGY EXTRACTION

This is the foundational decomposition heuristic.

---

## Prompt: Extract Prompt Ontology

```text id="wsl4bz"
Analyze the prompt as a system specification rather than as prose.

Identify and separate the following distinct layers:

1. Identity
   - Who the model is supposed to be

2. Epistemology
   - What counts as truth or grounding

3. Philosophy
   - Core non-negotiable worldview constraints

4. Behavioral Contracts
   - What outputs must contain

5. Interaction Protocol
   - Runtime commands and control flow

6. Curriculum / Knowledge Scope
   - Subject matter boundaries

7. Style Constraints
   - Tone, rhetoric, verbosity, structure

8. Execution Heuristics
   - Implicit reasoning strategies

9. Formatting Rules
   - Output syntax and layout requirements

10. Quality Constraints
   - What must be avoided or optimized

Return:
- the extracted ontology
- hidden coupling between categories
- duplicated responsibilities
- implicit assumptions
```

---

# 2. CONCERN DECOUPLING HEURISTIC

This is the primary modularization strategy.

---

## Prompt: Decouple Mixed Prompt Concerns

```text id="c5g0az"
Refactor the prompt by separating orthogonal concerns.

A concern is orthogonal if it can change independently without requiring changes elsewhere.

Separate:
- persona
- domain knowledge
- pedagogy
- formatting
- interaction commands
- reasoning constraints
- output schema
- stylistic rules

For each concern:
- isolate it into a self-contained reusable prompt
- minimize dependencies on other prompts
- define explicit interfaces and assumptions

Avoid:
- duplicated instructions
- hidden dependencies
- mixed semantic layers
- redundant constraints
```

---

# 3. PROMPT NORMALIZATION

Equivalent to database normalization or software modularization.

---

## Prompt: Normalize a Large Prompt

```text id="jlwmjj"
Normalize the prompt into reusable components.

Apply these normalization rules:

1NF - Atomicity
- Each prompt module should do one conceptual job.

2NF - Dependency Isolation
- Remove instructions that depend on unrelated sections.

3NF - Eliminate Redundant Semantics
- If two sections encode the same behavioral rule, unify them.

BCNF - Remove Behavioral Coupling
- No module should implicitly control another module unless explicitly declared.

Output:
- normalized prompt modules
- module responsibilities
- dependency graph
- reusable composition patterns
```

---

# 4. HIDDEN ASSUMPTION EXTRACTION

Most large prompts contain unstated execution assumptions.

This is one of the most important tacit strategies.

---

## Prompt: Extract Hidden Prompt Assumptions

```text id="njlwmq"
Identify implicit assumptions embedded in the prompt.

Look for unstated assumptions about:
- reasoning style
- abstraction level
- intended audience
- truth criteria
- verbosity
- execution order
- interaction model
- error tolerance
- pedagogical philosophy
- model cognition expectations

Convert implicit assumptions into explicit instructions.

For each assumption:
- state where it appears indirectly
- explain its behavioral effect
- rewrite it as a direct reusable prompt rule
```

---

# 5. BEHAVIORAL INTERFACE EXTRACTION

This treats prompts as APIs.

---

## Prompt: Extract Prompt Interfaces

```text id="m8v01w"
Treat the prompt as an executable behavioral interface.

Identify:
- inputs
- commands
- state transitions
- expected outputs
- invariants
- extension points

Convert all interaction semantics into explicit protocol definitions.

Separate:
- static configuration
- runtime commands
- output contracts
- extension mechanisms

Design the result as a composable protocol rather than a monolithic instruction block.
```

---

# 6. PROMPT AS SOFTWARE ARCHITECTURE

This was the deepest tacit mapping used in the refactor.

---

## Prompt: Refactor Prompt Like a Software System

```text id="kpn9l4"
Treat the prompt as a software architecture problem.

Analyze:
- coupling
- cohesion
- composability
- reusability
- interface clarity
- hidden state
- duplicated logic
- control flow
- dependency direction

Apply:
- separation of concerns
- explicit interfaces
- orthogonality
- modular composition
- dependency minimization
- schema extraction

Refactor the prompt into modules analogous to:
- configuration
- policy
- runtime protocol
- rendering layer
- domain model
- execution engine
```

---

# 7. SEMANTIC LAYER EXTRACTION

Large prompts usually collapse multiple abstraction layers together.

---

## Prompt: Separate Semantic Layers

```text id="ihnm0r"
Identify distinct semantic layers in the prompt.

Possible layers include:
- ontology
- methodology
- rhetoric
- pedagogy
- domain expertise
- execution protocol
- formatting
- evaluation criteria

Separate instructions by abstraction level.

Do not allow:
- formatting rules mixed with reasoning rules
- persona mixed with curriculum
- pedagogy mixed with interaction protocol
- ontology mixed with style

Produce:
- clean layer boundaries
- responsibilities per layer
- reusable prompt fragments
```

---

# 8. PROMPT COMPOSITION ARCHITECTURE

This is the composability heuristic.

---

## Prompt: Design Prompt Composition System

```text id="vgfqz9"
Convert the monolithic prompt into a composable architecture.

Requirements:
- each module must be reusable independently
- modules must compose predictably
- modules must avoid semantic overlap
- modules should expose explicit purpose and scope

For each module define:
- purpose
- inputs
- behavioral effects
- dependencies
- safe combinations
- conflicting combinations

Output:
- composition graph
- minimal core prompt
- optional augmentation prompts
- specialization prompts
```

---

# 9. INSTRUCTION DENSITY REDUCTION

Large prompts often repeat constraints in different language.

This was another major latent heuristic.

---

## Prompt: Compress Redundant Prompt Semantics

```text id="4uhc2o"
Identify semantically redundant instructions.

Collapse repeated behavioral constraints into canonical rules.

Look for repeated concepts such as:
- precision
- rigor
- grounding
- clarity
- explicitness
- anti-abstraction
- hardware awareness

Replace multiple phrasings with:
- one precise invariant
- one reusable behavioral rule

Minimize token count while preserving behavioral specificity.
```

---

# 10. EXECUTION MODEL EXTRACTION

Most advanced prompts encode an implied execution engine.

This was heavily used in the refactor.

---

## Prompt: Extract the Prompt Execution Model

```text id="6pyk96"
Determine how the prompt expects the model to operate internally.

Infer:
- planning order
- reasoning sequence
- decomposition strategy
- output synthesis process
- state management
- interaction lifecycle

Convert the implicit execution behavior into explicit instructions.

Describe:
- initialization phase
- runtime behavior
- output generation flow
- iterative interaction model
```

---

# 11. PROMPT COHESION ANALYSIS

This identifies when sections belong together.

---

## Prompt: Analyze Prompt Cohesion

```text id="0xv7e0"
Evaluate the internal cohesion of prompt sections.

A cohesive module:
- serves one conceptual purpose
- changes for one reason
- has minimal external assumptions

Identify:
- tightly cohesive sections
- weakly related instructions
- accidental groupings
- overloaded sections

Refactor weakly cohesive sections into independent modules.
```

---

# 12. DATA-ORIENTED PROMPT ENGINEERING

This is the deepest architectural analogy.

This is the actual meta-pattern behind the entire refactor.

---

## Prompt: Apply Data-Oriented Design to Prompt Engineering

```text id="9vvv55"
Treat the prompt as a data-oriented system.

Do not organize prompts around narrative flow.

Instead organize around:
- instruction locality
- semantic coherence
- transform stages
- explicit interfaces
- reusable schemas

Design prompts as:
- composable transforms
- independent behavioral tables
- orthogonal instruction sets

Optimize for:
- maintainability
- composability
- predictability
- behavioral clarity
- instruction locality

Avoid:
- giant monolithic prompts
- mixed abstraction layers
- duplicated semantics
- hidden execution assumptions
- tightly coupled instruction blocks
```

---

# 13. META-HEURISTICS USED DURING THE REFACTOR

These were the implicit expert heuristics operating underneath everything else.

---

## Prompt: Expert Prompt Refactoring Heuristics

```text id="l1bj0s"
Apply the following expert heuristics during prompt refactoring:

1. Every sentence should justify its existence.
2. Separate identity from behavior.
3. Separate behavior from formatting.
4. Separate ontology from pedagogy.
5. Separate runtime protocol from static configuration.
6. Replace repeated semantics with invariants.
7. Convert implicit assumptions into explicit interfaces.
8. Minimize hidden coupling.
9. Prefer composable modules over narrative continuity.
10. Treat prompts as executable behavioral architectures.
11. Optimize for future recombination, not immediate readability alone.
12. Design prompts so modules can be swapped independently.
13. Extract latent execution models.
14. Collapse synonymous constraints into canonical forms.
15. Reduce ambiguity before reducing complexity.
```

---

# 14. THE DEEPEST LATENT KNOWLEDGE

The deepest implicit strategy was this:

```text id="c0p4kk"
A prompt is not primarily text.

A prompt is:
- a constraint system
- a behavioral architecture
- an execution protocol
- a cognitive routing mechanism
- a state-conditioning artifact
```

Once viewed that way, the refactor becomes identical to:

* systems architecture
* compiler IR decomposition
* protocol design
* schema normalization
* data-oriented decomposition

The same engineering instincts apply:

* isolate state
* reduce coupling
* maximize locality
* define interfaces
* expose invariants
* minimize ambiguity
* separate transforms
* make hidden structure explicit

That is the actual transferable expertise behind the refactor.

Tags: [prompt_engineering, systems_architecture, abstraction_design]
