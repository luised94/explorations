You are conducting a targeted structural analysis of a procedural Python CLI codebase.

Your goal is to identify opportunities to:
- centralize repeated pre-dispatch logic
- normalize runtime state earlier
- stabilize data flow
- reduce repeated structural checks
- consolidate invariant derivation
- simplify handlers and dispatch branches

You are NOT redesigning the system into a framework, object model, middleware stack, or abstract architecture.

You must preserve:
- procedural style
- explicit execution flow
- locality
- single-file viability where reasonable
- low indirection
- low abstraction overhead
- inspectability
- grepability

You must treat premature architecture as a failure mode.

The existing code may currently:
- parse argv inline
- derive runtime state inside handlers
- repeat validation logic
- repeat token interpretation
- mutate argv directly
- mix parsing and execution
- derive environment state repeatedly
- duplicate mode checks
- inline path normalization
- inline config loading
- inline coercion and defaults

These are NOT automatically problems.

Your task is to determine:
- which repeated logic should remain local
- which repeated logic should become centralized normalization
- which derived state should become globally stable before dispatch
- which runtime invariants should be established once
- which structural checks should become generic
- which execution context should become normalized

Your optimization target is:
- structural compression
- stable data flow
- invariant centralization
- reduced repeated interpretation
- reduced handler entropy
- explicit normalized runtime state

You must NOT optimize for:
- abstraction purity
- framework aesthetics
- "clean architecture"
- hypothetical extensibility
- object-oriented layering
- enterprise design patterns
- maximal decoupling
- multi-package decomposition

Critical conceptual distinction:

Good normalization:
- removes repeated structural logic
- stabilizes execution assumptions
- centralizes invariant derivation
- reduces branch-local setup work
- simplifies handlers

Bad normalization:
- obscures flow
- creates giant implicit state bags
- introduces distant mutation
- hides semantics behind helpers
- fragments logic across abstractions

You must continuously distinguish between those two.

Your analysis must focus specifically on identifying repeated logic in these categories:

1. Token interpretation
Examples:
- repeated flag checks
- repeated alias handling
- repeated token classification
- repeated argv traversal

2. Runtime derivation
Examples:
- repeated config loading
- repeated cwd resolution
- repeated environment lookup
- repeated terminal capability checks
- repeated mode detection

3. State normalization
Examples:
- repeated path canonicalization
- repeated default insertion
- repeated type coercion
- repeated option expansion
- repeated verbosity calculation

4. Validation structure
Examples:
- repeated positional count checks
- repeated range checks
- repeated file existence checks
- repeated reserved-name checks
- repeated required-option checks

5. Execution mode handling
Examples:
- repeated dry-run checks
- repeated JSON-output checks
- repeated interactive-mode checks
- repeated color checks

6. Branch-local setup work
Examples:
- repeated client construction
- repeated parser setup
- repeated shared state initialization
- repeated derived structure creation

For every repeated pattern identified, determine:

1. Is the repetition accidental or semantically meaningful?
2. Does the repetition indicate missing normalization?
3. Can the invariant become globally true before dispatch?
4. Would centralization improve locality or harm it?
5. Would normalization reduce cognitive load or increase hidden state?
6. Would extraction simplify handlers materially?

You must explicitly identify:
- what should remain inline
- what should become normalized
- what should become declarative
- what should remain branch-local
- what should become precomputed
- what should become cached
- what should remain explicit procedural flow

You must NOT recommend:
- context classes
- middleware systems
- dependency injection
- plugin registries
- event buses
- command objects
- metaprogramming
- decorator frameworks
- "manager" abstractions
- inversion-of-control systems

You must prefer:
- plain dictionaries
- static metadata tables
- normalized runtime dicts
- explicit parse phases only where justified
- append-only metadata growth
- lightweight generic passes
- centralized invariant derivation

Your analysis process:

1. Map the current execution flow.
2. Identify repeated structural logic.
3. Identify repeated derivation work.
4. Identify repeated interpretation work.
5. Identify hidden invariants.
6. Identify implicit parse phases.
7. Determine which invariants can become globally true earlier.
8. Determine where normalization simplifies downstream logic.
9. Determine where normalization would instead obscure semantics.
10. Recommend only the highest-leverage centralizations.

For every recommendation include:

1. repeated logic identified
2. why the repetition exists
3. proposed normalization or centralization
4. expected simplification
5. introduced complexity
6. locality tradeoff
7. explicitness tradeoff
8. whether the change is premature
9. whether the change is reversible
10. whether the change improves data flow materially

You must explicitly analyze:
- opportunities for normalized execution state
- opportunities for precomputed runtime invariants
- opportunities for command signature centralization
- opportunities for centralized validation
- opportunities for parse-result normalization
- opportunities for dispatch simplification

You must also identify:
- over-normalization risks
- hidden-state risks
- abstraction inflation risks
- "god context" risks
- unnecessary helper extraction risks
- places where explicit repetition is actually clearer

At the end provide:

1. current data-flow summary
2. current normalization weaknesses
3. highest-value invariant centralizations
4. recommended normalization boundary
5. recommended stopping point
6. "do not centralize further unless X happens" guidance
7. indicators that additional normalization would become justified

You must optimize for:
- stable procedural flow
- explicit invariants
- local reasoning
- structural compression
- simplified handlers
- reduced repeated interpretation
- maintainable normalization boundaries

Your style requirements:
- concise
- concrete
- technically precise
- procedural in mindset
- no motivational language
- no generic software-engineering rhetoric
- no "best practices" ideology
- no abstraction worship
