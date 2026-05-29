# Workflow Rhythm
VERSION: 2
UPDATED: 2026-05-28

Per-commit development process for LLM-assisted implementation.
Paste into every implementation thread.

---

## Commit Classification

### Haiku
Mechanical, minimal judgment. Obvious implementation from spec.
Examples: create files, thin wrapper commands, register in dispatch.
LLM needs: commit description + relevant spec section.

### Sonnet
Moderate judgment, bounded scope. Requires context and local decisions.
Examples: parser, commands with branching logic, display formatting.
LLM needs: commit description + spec section + exemplar if available.

### Opus
Not allowed. Decompose into haiku and sonnet commits. If a commit
feels like opus, the spec is not detailed enough -- refine spec first.

---

## Commit Rhythm

Each commit follows this cycle. The LLM produces the full block.
The developer reviews, applies, verifies, commits.

### Commit Block Format

```
COMMIT ##: scope(project): imperative description

PURPOSE
  One sentence -- what this commit accomplishes and why it matters.

CONTEXT
  Relevant spec sections, prior commits referenced, current file state.

IMPLEMENTATION
  Precise editing instructions:
  - Which file, which section (by section header name)
  - Code blocks with exact insertion points
  - Substitution instructions: old text -> new text
  - No ambiguous instructions ("add appropriate handling")
  - Every line of code accounted for

INVARIANTS
  Testable assertions that must hold after this commit.
  Format: assert: [condition] -- [what it validates]
  At least one per commit. Examples:
    assert: parse_file on empty file returns [] -- empty input
    assert: every record has 'id' key -- ID generation integrity
    assert: write then parse round-trips without data loss -- fidelity

ERROR HANDLING
  Specific failure modes introduced by THIS commit. Not hypothetical.
  Format: [condition] -> [behavior]
  Examples:
    missing summary argument -> print usage to stderr, exit 1
    file not found -> create empty file, continue
    ambiguous ID prefix -> print matches to stderr, exit 1

STRATEGIC PRINTS
  Permanent UX confirmation output. Not debug logging.
  Format: [trigger] -> prints "[message]" to [stdout/stderr]
  Examples:
    successful add -> "added: T0527a summary text" to stdout
    successful done -> "completed: T0527a -> done.txt" to stdout
    missing argument -> "error: summary required" to stderr

VERIFICATION
  Exact shell commands with expected output. Developer runs these
  after applying the commit to confirm correctness.
  ```
  $ command
  expected output
  ```
  Include at least one positive case and one error case.

COMMIT MESSAGE
  scope(project): imperative description
  - point 1
  - point 2
  - point 3
  - (4 max)
```

---

## Exemplar Strategy

Identify 1-2 commits as reference implementations that demonstrate
all recurring patterns. Implement these first.

### Exemplar archetypes

**Mutation command** (add, done, edit): reads file -> parses -> modifies
data -> writes file -> confirms action -> logs usage. Demonstrates:
argument parsing, record construction, file I/O pattern, error
handling, confirmation output, usage logging sandwich.

**View command** (today, list): reads file(s) -> parses -> filters ->
computes derived data -> formats output -> logs usage. Demonstrates:
multi-file reads, filtering logic, display formatting, no-write path.

### Referencing exemplars

When requesting non-exemplar commits:
```
Implement commit ##. Follow the patterns established in commit ##
(the exemplar): argument parsing style, error handling, usage logging
sandwich, confirmation output format.
```

---

## Hardening Standards

### Per-Commit (minimum, always applied)

Every commit includes:
- At least one invariant assertion
- Error handling for every failure mode the commit introduces
- Confirmation output for every user-facing mutation
- Type hints on every new function
- Docstring on every new function (2-4 lines)

### Hardening Checklist (review before committing)

Before running `git add`:
- [ ] All verification commands produce expected output
- [ ] Error cases produce correct stderr message and exit code
- [ ] No implicit state introduced (module-level mutable variables)
- [ ] New functions have type hints and docstrings
- [ ] Section headers present if new section was added
- [ ] Strategic prints are stdout (confirmations) or stderr (errors), not mixed
- [ ] No single-caller function extractions (review each `def` -- does it have 2+ call sites in this phase, or is it a dispatch target?)
- [ ] No functions defined solely to pass to higher-order functions (review each `lambda`, nested `def`, and `key=` argument -- is the ordering already known? build directly if so)
- [ ] Variable names use domain vocabulary, not generic programming terms (no bare `key`, `value`, `item`, `data`, `result`)
- [ ] Function length is not a concern if the logic is one irreducible top-to-bottom sequence -- do not split a single-path function for length alone

---

## Batching Sequential Commits

When a thread covers multiple sequential commits, the LLM assesses
whether batching is safe:

1. Sum the commit levels. Multiple haiku = still haiku/sonnet. Haiku + sonnet = sonnet. Multiple sonnets = assess case by case.
2. If combined complexity would require opus-level judgment, do not batch.
3. Commits must be sequential (no skipping dependencies).
4. State the assessment briefly before producing the batch.

---

## Parallelization

### Thread map convention

Commits organized into named threads (independent work streams):
```
01 -+- [A] 02->03->04 -+
    +- [B] 05->06 -----+
    +- [C] 07 ---------+
                        v
                   convergence
```

### Rules
- Commits in different threads have no shared dependencies
- When stuck on one thread, switch to another
- Mark convergence points -- these need extra verification
- "Parallel" means "any order" for a solo developer

---

## Progress Tracking

Every LLM implementation response ends with:
```
PROGRESS: [##/total] | commit_## level | thread_X | phase_N | status
```

Status values: `complete`, `in_progress`, `blocked:[reason]`

Example:
```
PROGRESS: [03/17] | commit_03 haiku | thread_A | phase_0 | complete
```

---

## Cross-Reference Analysis

When starting a new implementation thread or receiving updated documents,
the LLM performs a cross-reference pass before writing code:

1. **Contradictions** -- where do documents disagree? Which is authoritative?
2. **Deviations** -- what was decided during implementation that differs from the plan?
3. **Ambiguities** -- what does the plan leave unspecified that the code must decide?
4. **Call site audit** -- for every function to be introduced, name its callers in this phase. If < 2 and not a dispatch target, inline.
5. **Pattern check** -- does the commit follow an established exemplar? If so, name it.

State findings briefly. Resolve or flag as [ASSUME]/[GAP]. Then proceed.

---

## End-of-Phase Analysis

After completing all commits in a phase, before starting the next
phase. Request in a refinement thread.

### Checklist

1. **Presuppositions audit** -- what does the code assume about its
   environment that is not checked? (file exists, env var set, UTF-8)
2. **Assumptions audit** -- what was assumed during implementation that
   the spec did not explicitly state? Verify each.
3. **Entailments check** -- what does the implementation logically imply
   that was not intended? (e.g., empty summaries allowed means blank
   lines in list output)
4. **Cognitive decay review** -- re-read the spec. What drifted? What
   shortcuts were taken and labeled temporary?
5. **Pre/post condition verification** -- for each command, state what
   must be true before and after. Verify.
6. **Usage data review** -- if the tool has been used, analyze logs.
   Which commands used? Which unused? Surprises?

### Requesting analysis
```
Run end-of-phase analysis on the current codebase. Here is the code
[paste]. Here is the spec [paste]. Identify drift, forgotten items,
unhardened paths, and extraction opportunities. Prioritize by impact.
```

---

## Thread Management

### Scope per thread
Each implementation thread covers a bounded set of commits (typically
4-10). State scope in the opening prompt. Do not let threads grow
unbounded -- context window pressure degrades LLM output quality.

### Handoff between threads
At end of an implementation thread, produce or update:
- Current file state (paste the full file for next thread)
- Which commits are complete
- Any deviations from the spec (decisions made during implementation)
- What the next thread should start with

### When to start a new thread
- Completed the scoped commits
- Thread exceeds ~15-20 exchanges
- Switching from implementation to design or refinement
- Phase boundary
