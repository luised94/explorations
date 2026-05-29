# Prompt: Generate Detailed Commit Plan

Use this prompt after a spec is finalized to produce an implementation plan. Paste the spec as context, then this instruction.

---

## Instruction

Generate a detailed commit-by-commit implementation plan for the attached spec. Follow these rules and structure exactly.

### Classification

Every commit must be either:
- **haiku** - mechanical, minimal judgment. The implementation is obvious from the description. A less capable model or a quick session can handle it.
- **sonnet** - moderate judgment, bounded scope. Requires understanding context and making reasonable decisions, but the scope is clearly defined.

No opus-level commits. If a commit requires complex design decisions, decompose it into multiple haiku/sonnet commits. The first decomposition step is always to separate the decision-making (sonnet) from the mechanical implementation (haiku).

### Parallelization

Organize commits into named threads - independent work streams that can proceed without blocking each other. Mark dependencies explicitly per commit (e.g., "DEPENDS ON: 02, 05"). Produce a visual thread map showing the dependency graph using ASCII art.

Strategy for identifying threads:
- **Layer-based threads**: data layer, identity/utility layer, observability layer - these are often independent foundations that converge when feature commands begin.
- **Feature-based threads**: after foundation converges, group commands by independence. Two commands that touch different files and share no new logic can be parallel.
- **Wiring thread**: dispatch, help, integration - always comes last, depends on all feature commits.

### Exemplar Strategy

Identify 1-2 commits that serve as **exemplars** - reference implementations establishing patterns that subsequent commits follow. Mark these explicitly. An exemplar commit should:
- Be the first commit of its archetype (e.g., first mutation command, first view command)
- Introduce shared utilities that later commits reuse (e.g., argument parser, output formatter)
- Demonstrate the full vertical slice: input  validation  data transformation  persistence  output  logging

Subsequent commits in the same archetype should reference the exemplar: "follows patterns from commit N."

### Commit Template

Every commit must include ALL of these sections:

```
COMMIT ##: scope(project): imperative description
LEVEL: haiku | sonnet
THREAD: thread name
DEPENDS ON: commit numbers or "none"

PURPOSE:
  One sentence. What does this commit accomplish and why.

FILES TOUCHED:
  - filepath (create | modify)

IMPLEMENTATION OUTLINE:
  Numbered steps. Concrete enough that the implementer doesn't need to
  make architectural decisions, abstract enough to not be pseudocode.
  For exemplar commits, explicitly name the patterns being established.

INVARIANTS:
  Assertions that must hold after this commit. These become assert
  statements or verification checks in the code. Format as testable
  propositions:
  - "after add, active.txt contains exactly one more record"
  - "parse then write produces identical output"
  Think: what would break if this commit has a bug?

ERROR HANDLING:
  Specific failure modes introduced by THIS commit. Not hypothetical
  future errors - the ones that can happen with the code being written
  right now. For each: what triggers it, what the user sees, what
  exit code.

STRATEGIC PRINTS:
  User-facing confirmation output. These are permanent UX, not debug
  logging. Answer: "how does the user know the command worked?"
  Specify stdout vs stderr. If none needed (pure utility function),
  say "none."

VERIFICATION:
  Shell commands to run after the commit, with expected output.
  These should be copy-pasteable into a terminal. Include:
  - The happy path (command works correctly)
  - At least one error path (bad input, missing arg)
  - Regression check (earlier commands still work)

COMMIT MESSAGE:
  scope(project): imperative verb phrase
  - bullet point per notable change (max 4)
```

### Ordering Principles

1. **Foundation before features.** Parser, writer, ID generation, logging - these come first because every feature depends on them.
2. **Exemplar before variants.** The exemplar mutation command comes before the three commands that copy its pattern.
3. **Independent features can interleave.** If two commands don't share code beyond the foundation, they're parallel.
4. **Wiring last.** Dispatch table finalization, help command, shell integration - after all commands exist.
5. **Scaffolding as commit 01.** Directory structure, empty files, script skeleton with section headers and dispatch placeholders. This commit makes every subsequent commit a "fill in this section" operation rather than "create from scratch."

### Implicit Strategies to Apply

- **Deferred features get placeholders.** Commands planned for later phases appear in the dispatch table with "not implemented" handlers. This reserves the command name, makes it discoverable via help, and signals intent.
- **Field-agnostic data layer.** The parser should not know about entity types. It reads any key=value pairs. Validation happens in command logic, not parsing. This means future fields work without parser changes.
- **Separate selection from formatting.** View commands have two phases: "which records to show" (filtering/sorting) and "how to display them" (formatting). Implement these as separate functions so either can change independently.
- **Auto-populated fields.** id, created, updated, status are set by the tool, not the user. This reduces input burden and ensures consistency. updated is refreshed on any modification (edit, done).
- **Round-trip fidelity.** The parser+writer combination must preserve file contents through a read-write cycle. Test this explicitly (commit it as its own verification step). This matters because files are hand-edited in nvim AND machine-written by the tool.

### Progress Tracking Footer

Include a tracking format specification. Every implementation message (when executing commits) should end with a dense one-line footer:

```
PROGRESS: [##/total] | commit_## level | thread_X | phase_N | status
```

Where status is one of: `complete`, `in_progress`, `blocked(reason)`.

Example: `PROGRESS: [03/19] | commit_03 haiku | thread_A | phase_0 | complete`

This allows scanning a conversation to see implementation state at a glance.
