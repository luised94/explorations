You are conducting a targeted refactoring analysis of a Python CLI codebase.

Your goal is NOT to redesign the system into a framework, object hierarchy, plugin architecture, or "clean architecture" abstraction stack.

Your goal is to incrementally increase the data-orientedness of:
- argument parsing
- subcommand parsing
- command dispatch
- option handling
- validation flow

while preserving:
- procedural style
- locality
- explicit control flow
- single-file viability where reasonable
- low indirection
- grepability
- low cognitive overhead

You must treat premature architecture as a failure mode.

The existing code may currently use:
- nested if/elif dispatch
- inline parsing
- inline validation
- procedural handlers
- shared mutable parsing state
- argv mutation
- duplicated parsing patterns

Those are NOT automatically problems.

Your task is to determine:
- which branching structures are still locally optimal
- which repeated structures should become data
- which parsing logic should become generic
- which refactors improve scalability without increasing abstraction debt

You must optimize for:
- structural compression
- explicitness
- centralized command metadata
- reduced branching duplication
- stable traversal logic
- generic parsing where repetition already exists

You must NOT optimize for:
- maximal abstraction
- extensibility for hypothetical futures
- framework aesthetics
- "enterprise" architecture
- object orientation
- design patterns for their own sake
- splitting into many files prematurely

Important conceptual distinction:

Data-oriented does NOT mean:
- introducing many helper layers
- hiding flow behind abstractions
- replacing explicit code with indirection

Data-oriented DOES mean:
- representing command structure explicitly as data
- stabilizing traversal algorithms
- reducing duplicated structural logic
- separating command metadata from dispatch logic where beneficial
- centralizing repeated parsing semantics

Your analysis process:

1. Analyze the existing parser and dispatcher structure.
2. Identify repeated structural patterns.
3. Identify where command structure currently lives in control flow.
4. Identify where parsing logic duplicates across branches.
5. Distinguish:
   - acceptable procedural branching
   - harmful branching duplication
   - premature abstraction opportunities
   - genuinely useful data extraction opportunities
6. Propose the MINIMAL refactors that improve:
   - scalability
   - inspectability
   - maintainability
   - command metadata locality
7. Preserve procedural execution style unless strong evidence suggests otherwise.

You must continuously evaluate tradeoffs between:
- explicitness
- indirection
- locality
- genericity
- parsing flexibility
- simplicity

You must prefer:
- flat tables
- static metadata structures
- centralized descriptors
- parse phases only where pressure already exists
- append-only command registration
- lightweight normalization passes

You must avoid:
- command classes
- parser frameworks
- decorator registries
- dependency injection
- plugin systems
- metaclass tricks
- over-generalized helper layers
- abstract interfaces
- filesystem/package explosion

When proposing changes:
- explain WHY the change improves structural properties
- explain WHY the change is not premature
- explain WHAT duplication or instability it removes
- explain WHAT complexity it introduces
- explain the tradeoff clearly

After analysis, produce a commit-by-commit refactoring plan.

The plan must:
- preserve working behavior after every commit
- minimize simultaneous conceptual changes
- isolate mechanical refactors from semantic changes
- prefer reversible transformations
- preserve readability during transition
- avoid "big bang" rewrites

For each commit include:
1. commit title
2. exact goal
3. rationale
4. files/functions affected
5. expected structural improvement
6. risks introduced
7. rollback simplicity
8. whether the commit is:
   - mechanical
   - structural
   - semantic
   - cleanup

You must explicitly identify:
- which current if/elif structures should remain
- which should become table-driven
- which should become generic traversal
- which repeated parsing behaviors justify extraction
- which behaviors should remain inline for locality

You must also identify:
- likely overengineering traps
- unnecessary abstractions
- architectural inflation risks
- places where procedural explicitness is superior

At the end provide:
1. current parser architecture summary
2. structural pain points
3. recommended stopping point
4. "do not refactor further unless X happens" guidance
5. indicators that future abstraction would become justified

Your style requirements:
- concise
- concrete
- procedural
- technically precise
- no motivational language
- no "best practices" rhetoric
- no generic software engineering clich‚s
- no appeals to clean architecture ideology

Optimize for:
- local reasoning
- stable execution flow
- explicit structure
- incremental compression of duplication
- practical maintainability
