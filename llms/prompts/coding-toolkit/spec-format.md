# Spec Format
VERSION: 1
UPDATED: 2026-05-27

Task module. Invoke when a design thread has converged and it's
time to produce a formal specification.

---

## When to invoke

- Design decisions are made, ready to document
- Moving from design thread to implementation thread
- Need a single source of truth for a component or system

## Prompt

```
Produce a spec using data dictionary + command reference format.
Organize as follows:

1. CONSTRAINTS - coding style, environment, interfaces, explicit
   non-goals
2. ENTITIES - one subsection per entity type. For each: field table
   (field, required, default, type, notes), lifecycle description
   (how it's created, how it changes state, how it terminates).
   Inline ADR under each entity for key decisions (Decision / Why /
   Rejected, 3 lines max).
3. FILES - layout diagram, file characteristics table (write
   pattern, git diff behavior, growth rate)
4. FORMAT - data syntax, parsing rules, edge case handling
5. COMMANDS - one subsection per command. For each: flags table,
   auto-populated fields, behavior description, error cases
6. DISPLAY FORMATS - exact output layout for each view command,
   formatting and sorting rules
7. METRICS - raw data sources, derived metrics table (metric,
   source, what it tells you), scaffolding cost
8. COMMIT PLAN - ordered table (number, level, summary,
   dependencies, notes). All commits haiku or sonnet - no opus.
   Include parallelization thread map as ASCII diagram.

Appendices for: deferred fields (with reasons), example records.

Include inline ADRs throughout using:
  Decision: [what was chosen]
  Why: [concrete reason]
  Rejected: [alternative and why it lost]

The spec must be self-contained. A reader in a new thread with
no access to this conversation should be able to implement from
the spec alone.
```

## Evaluated and rejected spec styles

For reference when a different format might suit a different project:

| Style | What it is | Best for | Why rejected as default |
|-------|-----------|----------|----------------------|
| Narrative | Prose organized by feature | Explaining to non-technical readers | Ambiguous, hard to verify, easy to contradict across sections |
| RFC/formal | Numbered requirements, MUST/SHOULD/MAY | Multi-stakeholder systems, public standards | Ceremony overhead not justified for personal projects |
| ADR collection | One doc per decision: context, decision, consequences | Capturing WHY, especially in teams | Describes decisions but not the system holistically |
| Entity lifecycle | Organized around birth/change/death of each entity | State-machine-heavy systems | Covered by adding lifecycle annotations to data dictionary |
| Data dictionary + command reference | Entities  files  operations  display | Implementation-ready specs for data-oriented projects | **Selected as default** |

## Conventions

- Entities and data shapes come first - they are the design
- Operations are consequences of the data model
- Every significant decision gets an inline ADR
- Commit plan is part of the spec, not a separate document
- All commits classified haiku or sonnet, opus decomposed
- Spec should be under 400 lines for a single-module project
