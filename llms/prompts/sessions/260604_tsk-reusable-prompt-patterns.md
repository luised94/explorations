# Reusable Prompt Patterns for LLM-Assisted Implementation
VERSION: 1
DATE: 2026-06-04
SOURCE: Extracted from tsk phase-1 implementation session.

Paste into implementation threads alongside project-specific documents.
Organized by position in the commit workflow.

---

## 1. Thread Setup

### 1.1 Separation of design and implementation
Do all design exploration in a separate thread. The implementation thread
receives final decisions, not open questions. State in the thread opener:
"All decisions are final." The LLM produces code, not design exploration.

Why: design deliberation inside implementation threads causes drift,
bloats context, and produces hedged code. Pre-decided constraints
produce focused output.

### 1.2 Document loading order
Paste documents in this order:
1. Thread scope (commits covered, dependencies, key decisions)
2. Current source code (full file, not diffs)
3. Spec (authoritative for behavior)
4. Workflow rhythm (authoritative for commit format)
5. Coding style (authoritative for code patterns)
6. Session notes from prior threads (context recovery)

Why: the LLM weights earlier context more heavily. Scope and code first
means implementation details are freshest. Session notes last because
they're advisory, not authoritative.

### 1.3 Explicit scope boundaries
State what is NOT in scope for this thread. List features, files, and
patterns that are off-limits. The LLM will otherwise drift toward
adjacent improvements it notices.

Example: "Scope boundaries: handle_edit does not change. Habit feature
unchanged. parse_flags does not gain --flag=value syntax."

---

## 2. Commit Requests

### 2.1 Minimal prompting for sequential commits
After the first commit, "continue with the next commit" is sufficient.
The LLM maintains thread state. Do not re-explain the project, re-paste
documents, or re-state decisions. Adding context mid-thread signals that
prior context was lost - use it only when that's true.

### 2.2 Do not ask for options
Do not prompt "what should we do next?" or "which commit should we
tackle?" The commit plan is in the scope document. The LLM should
follow it in order unless a dependency is blocked. If you want to skip
a commit, say "skip commit N, proceed to N+1."

### 2.3 Signal satisfaction briefly
"Awesome" or "looks good, continue" is sufficient positive signal. The
LLM does not need detailed praise to maintain quality. Lengthy approval
wastes context window.

---

## 3. Commit Block Production

### 3.1 Invariants before implementation
State all postconditions, error behaviors, and user-facing prints before
writing any code. The implementation is then written against explicit
constraints rather than generating constraints retroactively.

Why: constraints stated after code tend to rationalize what was written
rather than verify what was intended.

### 3.2 Substitution-based implementation instructions
For modifications to existing code, use explicit old/new blocks:

```
Old:
    [exact text being replaced]

New:
    [exact replacement text]
```

Do not use "add appropriate handling" or "modify the function to also..."
Every line of code must be accounted for. The developer applies changes
mechanically, not interpretively.

### 3.3 One code path per commit
Each commit should have one primary code path it introduces or changes.
If a commit touches multiple independent code paths, it's too large.
Exception: a refactor that consolidates N paths into 1 (like commit 18)
is one conceptual change even though it touches many sites.

### 3.4 Verification commands are contracts
Every verification command promises specific behavior. Rules:
- Include at least one success case and one error case.
- Use obviously-test data ("test task consolidation", not "buy milk").
- When output depends on existing data state, say "output will include"
  rather than showing exact expected output.
- Cover every user-facing print introduced by the commit.
- Cover every postcondition stated in invariants.

### 3.5 Call site audit for every new function
Before writing a `def`, name every caller in the current phase. Write
them in the commit block. If fewer than 2 and not a dispatch target,
inline the logic. If extracting with 1 caller for readability reasons
(e.g., inside a nested loop), mark with [ASSUME] and state the
justification.

### 3.6 Edge cases surfaced during implementation
When the LLM notices an edge case not covered by the design (e.g.,
shell quoting interactions, flag collision), state it explicitly at
the end of the commit block with a recommendation. Do not silently
handle it or silently ignore it. The developer decides.

---

## 4. Code Generation

### 4.1 Config-driven handlers over parallel handlers
When N entity types share >70% of their handler logic, use a config
dict mapping type name to {type-specific data} and one handler that
reads the config. Do not write N parallel handlers with copy-pasted
logic.

The config holds data (prefix, file path, defaults, usage string).
Behavior that differs per type (validation, field parsing) lives in
the handler as explicit branches, not in the config as callables -
unless the callable is trivially simple (single-expression lambda).

Watch for: config creep. If the config dict grows display logic,
lifecycle rules, or complex validation, the abstraction is pulling
in too much. Split back into explicit branches.

### 4.2 Manual subcommand detection before argument parsing
When a handler needs one flag-like argument that changes its entire
behavior (e.g., `done --cleanup-events`), check for it manually before
the normal argument parsing path:

```python
if arguments and arguments[0] == "--cleanup-events":
    # entirely different code path
    ...
    return
# normal path continues
```

This pattern works for exactly one subcommand. If a second appears,
refactor to a secondary dispatch or flag-aware branching.

### 4.3 Policy comments at decision points
When code does something surprising - accepts all flags when you'd
expect per-type rejection, searches one file when you'd expect all,
uses ID prefix instead of type field - place a comment explaining
the policy, not just the mechanism:

```python
# All flags accepted for all entity types (field-agnostic philosophy).
# Exception: --date is required for events. No flags are rejected by type.
```

Not: `# parse flags` (mechanism, no policy).
Not: `# this is intentional` (assertion without explanation).

### 4.4 Confirmation output matches the operation's semantics
Each entity type gets confirmation phrasing that matches its domain
meaning:
- Tasks: `"added: {id} {summary}"` (bare, default entity)
- Goals: `"added goal: {id} {summary}"` (type-qualified)
- Events: `"added event: {id} {summary} on {date}"` (includes key field)
- Completion: `"completed: {id} {summary} -> done.txt"` (destination)
- Batch operations: `"archived N event(s): {ids} -> done.txt"` (count + list)

Do not use generic `"created record"` or `"operation successful"`.

### 4.5 Sort key functions for runtime-determined ordering
When sorted() needs a multi-field key that varies by mode (sort by
date vs priority vs project), extract a named key function rather than
an inline lambda. Prefix with _ to signal single-module scope. This is
the genuine-comparison exception to the "no functions as arguments to
higher-order functions" rule - the order is not known until runtime.

---

## 5. Cross-Commit Patterns

### 5.1 Fix before refactor
When a bug exists in code that is about to be refactored, fix the bug
first in a separate commit. This gives:
- A working checkpoint if the refactor introduces new bugs
- A clean diff on the refactor (not interleaved with the fix)
- Proof that the fix works independently

### 5.2 Stretch goals last, no dependents
Place optional/stretch commits at the end of the commit plan. They must
depend on required commits but no required commit may depend on them.
If the thread runs out of context window, nothing critical is missing.

### 5.3 Duplication tracking across commits
When implementation creates duplication (e.g., descriptions dict in two
places, event formatting in three places), note it in the commit block
but do not fix it in that commit. Track duplications in session notes.
Extract when the Nth site appears (where N makes the maintenance burden
concrete, typically 3-4 for formatting, 2 for data).

---

## 6. Tacit Knowledge (Inferred from Reactions)

These patterns were never explicitly stated but are inferred from which
outputs received "awesome" / "continue" vs. which needed correction or
adjustment.

### 6.1 Completeness over brevity in commit blocks
Full commit blocks with all sections populated received immediate
approval. The developer does not want abbreviated commits that save
LLM tokens at the cost of ambiguity. Every section earns its space.

### 6.2 No hedging in implementation threads
Phrases like "you might want to consider" or "an alternative approach
would be" are unwanted in implementation threads. Decisions are made.
The LLM picks the approach consistent with the design document and
executes it. Hedge in design threads; commit in implementation threads.

### 6.3 Progress tracking matters
The PROGRESS line at the end of each commit response was never
questioned or asked to be removed. It provides orientation: where we
are, what level, which phase. Keep it.

### 6.4 Edge case notes at the end, not inline
When an edge case is discovered during implementation (commit 18: shell
quoting interaction with positional subcommands), stating it after the
commit block as a separate note received engagement. Burying it in the
implementation section would have been missed. Rule: edge cases and
design tensions go in a clearly labeled note after the commit message,
not woven into the implementation steps.

### 6.5 Confidence calibration
The developer trusts "confidence: high" and acts on it. "Confidence:
moderate" with a stated reason ([ASSUME] that could go wrong) is
informative. Do not default to moderate out of caution - calibrate
honestly. High means: no significant assumptions, all paths tested
in verification, no design ambiguity. Moderate means: one or more
assumptions that the developer should verify.

### 6.6 The developer reads every line
Do not summarize or abbreviate code under the assumption that the
developer will fill in details. Every line of generated code will be
read, evaluated, and applied literally. Incomplete code blocks ("add
similar logic for other types") are rejected. The commit block is a
specification, not a sketch.

### 6.7 Commit messages are terse
Four bullet points maximum. Each bullet is a clause, not a sentence.
No period at the end. The first line is scope(project): imperative
verb phrase. The developer writes git history for future-self grep,
not for prose readers.

### 6.8 Domain immersion over generic patterns
The LLM should use the project's vocabulary: "record" not "item",
"active.txt" not "the data file", "prefix match" not "fuzzy search",
"field-agnostic" not "flexible". Reading the spec and code establishes
the lexicon. Using it signals that the LLM has internalized the project,
not just pattern-matched the request.
