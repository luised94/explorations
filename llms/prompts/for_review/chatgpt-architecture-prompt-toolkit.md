
Below is a structured prompt set organized by analysis layer. The important thing is not the wording itself but the decomposition strategy. Each prompt attempts to isolate one semantic dimension so the model does not collapse everything into premature implementation.

You can think of these prompts as intermediate representation generators.

---

# 1. System Identity / Ontology Extraction

Use early.

Purpose:
Determine what kind of system actually wants to exist before discussing implementation.

```text id="x4u2c9"
The user will describe a software idea vaguely and imprecisely.

Your task is NOT to generate features or implementation plans.

Your task is to infer:
- the underlying operational pressures
- the implicit workflows
- the cognitive constraints
- the temporal patterns
- the trust assumptions
- the coordination model
- the likely system archetypes hidden beneath the request

Do NOT collapse immediately into familiar categories like:
- CRUD app
- dashboard
- note-taking app
- task manager

Instead:
1. extract latent constraints
2. infer hidden semantic structure
3. identify competing possible system identities
4. identify what must remain stable for the system to feel coherent
5. identify what properties are likely accidental rather than essential

Output:
- inferred system archetypes
- governing pressures
- semantic center of gravity
- unresolved ambiguities
- questions that would maximally reduce uncertainty
```

---

# 2. User Constraint Interrogation

Purpose:
Extract architectural pressures from human workflows.

```text id="f95g6h"
You are analyzing the human operating environment surrounding a software system.

Do not ask primarily about features.

Extract:
- interruption patterns
- trust requirements
- latency sensitivity
- offline requirements
- collaboration patterns
- error tolerance
- cognitive load constraints
- persistence expectations
- temporal rhythms
- workload variability
- organizational habits
- information decay patterns

Classify findings into:
- stable invariants
- negotiable preferences
- inferred heuristics

For each finding:
- explain architectural implications
- identify which subsystems are affected
- identify likely tradeoffs
```

---

# 3. State Topology Analysis

One of the highest leverage prompts.

```text id="yjlwmq"
Assume the conceptual purpose of the system is already understood.

Analyze the system as a state-transition architecture.

Determine:
- canonical state
- derived state
- ephemeral/runtime state
- external state dependencies

For each state category:
- define ownership
- define persistence requirements
- define rebuildability
- define invalidation semantics
- define synchronization requirements
- define failure consequences

Identify:
- which state must never diverge
- which state may become eventually consistent
- which state can be recomputed
- which state requires stable identity
```

---

# 4. Mutation Algebra Prompt

Critical for architecture stabilization.

```text id="st4hsf"
Define the complete mutation algebra of the system.

For every legal operation:
- name the operation
- define inputs
- define outputs
- define preconditions
- define invariants preserved
- define state transitions
- define derived-state invalidations
- define side effects
- define failure modes
- define reversibility
- define idempotency requirements

Assume all architecture emerges from legal state transitions.

Do NOT discuss frameworks or UI yet.
```

---

# 5. Temporal Semantics Analysis

Especially useful for schedulers, queues, workflows, sync systems.

```text id="d5sykg"
Analyze the temporal semantics of the system.

Identify:
- monotonic processes
- reversible processes
- replayable processes
- time-sensitive state
- scheduling requirements
- ordering guarantees
- causal dependencies
- expiration/decay behavior
- retry semantics
- interruption recovery requirements

Determine:
- what must happen immediately
- what may happen eventually
- what may be deferred
- what requires deterministic replay

Output the system's temporal model.
```

---

# 6. Projection / Index Analysis

Useful for preventing derived-state corruption.

```text id="j0mr7m"
Assume canonical state and mutations already exist.

Identify all useful projections, indexes, caches, and derived structures.

For each:
- define source canonical state
- define recomputation cost
- define invalidation triggers
- define consistency guarantees
- define storage requirements
- define rebuild strategy
- define whether materialization is justified

Distinguish clearly between:
- authoritative state
- derived state
- optimization layers
```

---

# 7. Contradiction / Pressure Reconciliation

One of the most important prompts.

```text id="dglwxu"
Analyze the current system assumptions for hidden contradictions.

Search for:
- UX assumptions incompatible with persistence semantics
- scalability assumptions incompatible with consistency guarantees
- workflow assumptions incompatible with interruption patterns
- automation assumptions incompatible with trust requirements
- local optimizations that globally increase complexity
- projections incorrectly treated as canonical
- abstractions compensating for earlier accidental complexity

For each contradiction:
- identify affected layers
- identify root pressure
- propose resolution strategies
- estimate architectural impact
```

---

# 8. Architecture Compression Prompt

Useful against overengineering.

```text id="7ye8rf"
Assume the current architecture is likely overcomplicated.

Your task:
compress the architecture while preserving semantic identity.

For every subsystem:
- explain what pressure created it
- explain whether another subsystem already resolves that pressure
- identify redundancy
- identify accidental complexity
- identify abstractions with weak justification
- identify features that should become derived instead of canonical

Search for structures that resolve multiple pressures simultaneously.

Prefer:
- minimal canonical state
- fewer mutation types
- rebuildable projections
- local reasoning
- strong invariants
```

---

# 9. Prototype Extraction Prompt

For transitioning from design to implementation.

```text id="mksn7m"
Determine the minimum executable closure of the system.

Do NOT minimize features blindly.

Instead determine:
- the smallest implementation that preserves the system's semantic identity
- the minimum invariant set
- the minimum canonical state
- the minimum viable mutation algebra
- the minimum interaction loop
- the minimum persistence layer

Output:
- prototype ontology
- excluded concerns
- deferred complexity
- architectural risks hidden by minimization
```

---

# 10. Commit-by-Commit Planning Prompt

Your existing approach already aligns well with this.

```text id="06hdu8"
Generate a dependency-aware implementation plan.

Constraints:
- preserve architectural coherence
- avoid premature abstraction
- maximize local verifiability
- isolate semantic transformations
- minimize cross-cutting mutations

Classify implementation units as:
- Haiku: local/simple/coherent
- Sonnet: subsystem-level semantic unit
- Opus: multi-phase architectural milestone

For each unit:
- purpose
- dependencies
- invariants introduced
- files affected
- verification strategy
- rollback strategy
- commit message
- expected architectural leverage

Prefer:
- stable ontology before optimization
- pure transformations before adapters
- canonical state before projections
- projections before UI
```

---

# 11. Context Continuity Prompt

For carrying work across sessions/windows.

```text id="2cw64o"
Summarize the project as portable semantic state.

Preserve:
- canonical ontology
- stable invariants
- mutation algebra
- architectural decisions
- unresolved contradictions
- implementation status
- dependency graph
- deferred concerns
- known risks
- terminology definitions

Avoid:
- conversational fluff
- repeated implementation details
- low-level code dumps

The output should allow another context window
to reconstruct architectural continuity accurately.
```

---

# 12. Multi-Persona / Multi-Vector Exploration Prompt

Closest to your "pincer" strategy.

```text id="h8r3q8"
You will analyze the system through multiple independent semantic lenses.

Maintain separation between lenses until final synthesis.

Lenses:
1. User cognition and workflow
2. State topology and persistence
3. Temporal/scheduling semantics
4. Failure and recovery semantics
5. Scalability and synchronization
6. Interface and interaction topology
7. Operational/deployment constraints
8. Architectural compression/minimality

For each lens:
- identify pressures
- identify invariants
- identify assumptions
- identify conflicts with other lenses

Do NOT prematurely unify them.

After independent analysis:
- reconcile contradictions
- identify dominant constraints
- identify structures satisfying multiple pressures simultaneously
- produce consolidated architecture
```

---

# 13. Implementation Output Formatting Prompt

For practical execution.

```text id="gld4dd"
When generating implementation work:

Do NOT emit monolithic code dumps.

For each implementation unit provide:
1. architectural purpose
2. invariants affected
3. exact edits
4. dependency assumptions
5. verification commands
6. expected outputs
7. rollback instructions
8. commit message

Separate:
- canonical-state mutations
- projection/index updates
- interface changes
- persistence changes

Prefer causally understandable diffs over maximal code generation.
```

---

# 14. Meta-Architecture Prompt

This is the deepest layer.

```text id="1je8n8"
Treat software architecture as constrained state evolution over time.

Do NOT optimize primarily for:
- patterns
- frameworks
- abstractions
- stylistic conventions

Instead optimize for:
- invariant preservation
- mutation locality
- replayability
- recomputation boundaries
- identity stability
- interruption recovery
- semantic coherence
- projection correctness
- causal traceability

Assume implementation syntax is downstream from these constraints.
```

---

# Suggested Overall Workflow

The prompts themselves form a pipeline.

A strong sequence is usually:

```text id="umq1w1"
1. ontology extraction
2. user constraint interrogation
3. multi-lens exploration
4. state topology analysis
5. mutation algebra
6. temporal semantics
7. contradiction analysis
8. architecture compression
9. prototype extraction
10. commit planning
11. implementation
12. continuity summarization
```

The important thing is that each phase reduces uncertainty differently.

You are progressively freezing:

* semantics
* invariants
* identities
* transformations
* execution ordering
* implementation commitments

rather than jumping directly from idea to code.

Tags: [prompt_engineering, systems_architecture, llm_workflows, semantic_modeling, implementation_planning]
