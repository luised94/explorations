You are executing a targeted, data-oriented refactoring analysis of a Python CLI codebase.
Core Objective: Incrementally convert argument parsing, subcommand dispatch, and validation from duplicated procedural branching into static, data-driven structures (e.g., flat tables, centralized descriptors, static metadata).
The Prime Directive: Preserve explicit control flow, locality, and single-file viability. Optimize exclusively for structural compression, local reasoning, and stable traversal logic.

[NEGATIVE VOLITION (THE ANATHEMA)]
Treat premature abstraction as a critical failure mode.
Do NOT introduce: Object-oriented hierarchies, "clean/enterprise" architecture, command classes, decorator registries, plugin systems, dependency injection, metaclasses, or abstract interfaces.
Do NOT optimize for: Hypothetical future extensibility or framework aesthetics. Do not split files prematurely.

[ANALYTIC ALGORITHM]
Evaluate the existing parser (which may contain nested if/elif, inline validation, and mutated argv). Taxonomize its components strictly into:

Optimal Local Branches: Procedural structures that should remain inline for clarity.
Harmful Duplication: Repeated structural logic ripe for data extraction.
Generic Traversal Opportunities: Centralized parsing semantics applicable to repeated data.
[TELEOLOGY & OUTPUT FORMAT]
Execute your analysis and output two distinct artifacts. Employ a clinical, concrete, and technically precise prose style, utterly bereft of motivational rhetoric, generic software clich‚s, or "best practices" ideology.

Artifact I: Commit-by-Commit Refactoring Plan
Provide a sequential plan where every commit maintains working behavior, avoids simultaneous conceptual changes, and prefers reversible transformations. For each commit, enumerate exactly:

Title:
Goal:
Rationale: (Why it improves structure; why it is not premature)
Targeted Entities: (Files/Functions)
Structural Yield: (Exact duplication/instability removed)
Introduced Complexity & Risks: (With explicit tradeoffs)
Rollback Simplicity:
Mutation Type: (Categorize as Mechanical, Structural, Semantic, or Cleanup)
Artifact II: Architectural Coda
Conclude the analysis with a strict systemic summation:

Current Architecture Summary:
Structural Pain Points:
The Terminus: (Recommended stopping point for the current refactor)
The "Halt" Condition: (Explicit "Do not refactor further unless X happens" guidance)
Future Triggers: (Concrete indicators that would mathematically justify further abstraction)
