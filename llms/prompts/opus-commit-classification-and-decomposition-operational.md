## Classification

Classify each commit into one of three categories:

**Haiku**: A single-concern change producible in one act. This includes:
- Trivial edits (typo, one-line fix, variable rename)
- Mechanical transformations across many files (regex, sed, find-and-replace) - scope is irrelevant if the transformation is deterministic and expressible as a rule

**Sonnet**: A single-concern change requiring sustained coherence across multiple edits. The edits are interdependent and require holding one intent in mind, but the concern is singular. Examples: adding a feature with its tests, refactoring a module's internal structure, updating a function signature and all call sites where each site requires judgment.

**Opus**: A multi-concern change. Two or more logically independent changes bundled together. The test: could you explain this commit without using "and" to join unrelated clauses? If not, it's an opus.

## For Each Commit, Specify

```
Commit: <identifier> - <message>
Classification: haiku | sonnet | opus
Modality: command | single_edit | full_rewrite | patch
  - command: expressible as shell command or editor command (sed, awk, :% s///)
  - single_edit: one site, paste or manual
  - full_rewrite: replace entire file(s)
  - patch: targeted edits across multiple sites requiring judgment
Context needed: <which files/symbols the executor must see>
```

## Decomposition (Opus only)

Break into the minimal sequence of haiku and/or sonnet sub-commits:

```
Decomposition:
  1. [haiku|sonnet] - <description>
     Modality: <command|single_edit|full_rewrite|patch>
     Files: <...>
     Depends on: none | #N
  2. ...
```

## Edge Cases
- Deterministic transformation across many files  **haiku**, modality: command
- No opus commits  state: *"No opus commits identified."*
- Ambiguous  classify higher, note ambiguity
Execution strategy: incremental | batch | hybrid
  - incremental: produce and verify one commit at a time
  - batch: produce all commits, verify programmatically as sequence
  - hybrid: batch where verification is automated, pause where judgment needed

For batch/hybrid, each commit must include:
  Verification: <command(s) that confirm correctness without reading the diff>
    e.g., "cargo build", "pytest tests/auth/", "diff <(cmd) expected.txt"
