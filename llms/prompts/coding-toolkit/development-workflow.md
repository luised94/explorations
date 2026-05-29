# LLM Development Workflow
VERSION: 1
UPDATED: 2026-05-27

Reusable process guide for LLM-assisted development across all projects.
Paste relevant sections at the start of new threads as context injection.

---

## Thread Types and Setup

### Design Thread
Purpose: explore problem space, make architecture decisions, produce spec.

Attach: `environment.md`, `coding_style.md`, any prior specs or handoff docs from related projects.

Opening prompt:
```
Peruse the attached documents. They may be out of date or out of sync.
Cross-reference and identify any issues, contradictions, ambiguities,
decisions to make, or conflicts. Verbalize suggested reconciliation.
Once aligned, I need to design [component/system] for [project].
Here is what I know so far: [2-3 sentences of context].
Provide feedback, then gather context by asking targeted questions,
socratic questions, veteran questions.
```

Expected rhythm:
1. LLM audits documents, surfaces issues, reconciles
2. LLM gives feedback on the design problem + asks questions
3. You answer, LLM refines
4. Converge on decisions with inline ADRs
5. Produce spec artifact
6. Produce commit plan
7. Write handoff document for implementation threads

### Implementation Thread
Purpose: execute commits from a spec/plan.

Attach: `coding_style.md`, `workflow_rhythm.md`, project spec, handoff document, current codebase files.

Opening prompt:
```
Peruse the attached documents. They may be out of date or out of sync.
Cross-reference and identify any issues, contradictions, ambiguities,
decisions to make, or conflicts. Verbalize suggested reconciliation.
The main goal is to complete commits [##-##] of phase [N] in this
thread, then handoff to another thread for [next scope]. Start with
commit [##] after reconciliation. Follow the commit rhythm in
workflow_rhythm.md.
```

Expected rhythm: reconciliation pass, then per-commit cycle (see Commit Rhythm below).

### Refinement Thread
Purpose: analyze, harden, refactor existing code.

Attach: `coding_style.md`, `analysis_checklist.md`, current codebase files, usage data if available.

Opening prompt:
```
Peruse the attached documents. They may be out of date or out of sync.
Cross-reference and identify any issues, contradictions, ambiguities,
or drift from the spec. Verbalize suggested reconciliation. Then run
end-of-phase analysis on the codebase: presuppositions, assumptions,
entailments, cognitive decay, pre/post conditions. Recommend hardening,
refactoring, or extraction opportunities. Prioritize by impact.
```

---

## Commit Rhythm

Every commit follows this cycle. Request this structure from the LLM.

### 1. Commit Request

Ask the LLM to produce:

```
COMMIT ##: scope(project): imperative description

PURPOSE
  One sentence on what this commit accomplishes.

CONTEXT
  Relevant spec sections, prior commits, current file state.

IMPLEMENTATION
  Precise editing instructions:
  - Which file, which section
  - Code blocks to add (with exact insertion point)
  - Substitution instructions (old  new) where modifying existing code
  - No ambiguous instructions like "add appropriate error handling"

INVARIANTS
  Testable assertions that must hold after this commit.
  Format: "assert: [condition] - [what it validates]"
  Examples:
    assert: parse_file("empty_file.txt") returns [] - empty file handling
    assert: every record in output has 'id' key - ID generation integrity

ERROR HANDLING
  Specific failure modes introduced by THIS commit:
  - [input condition]  [behavior] (e.g., "no summary arg  print usage, exit 1")
  Not hypothetical future errors. Only what this code introduces.

STRATEGIC PRINTS
  Permanent UX confirmation output (not debug logging):
  - [command]  prints "[message]" to [stdout/stderr]
  Examples:
    tsk add  prints "added: T0525a summary text" to stdout
    missing arg  prints "error: summary required" to stderr

VERIFICATION
  Exact commands to run with expected output:
  ```
  $ tsk add "test task" --project test
  added: T0527a test task
  
  $ cat $TASKS_LOCAL_DIR/active.txt
  id = T0527a
  type = task
  ...
  ```

COMMIT MESSAGE
  scope(project): imperative description
  - bullet point 1
  - bullet point 2
  - (max 4 points)
```

### 2. Review and Execute

- Read the implementation instructions
- Apply changes
- Run verification commands
- If output doesn't match, paste actual output and ask LLM to diagnose

### 3. Progress Footer

Every LLM response during implementation ends with:
```
PROGRESS: [##/total] | commit_## level | thread_X | phase_N | status
```

---

## Commit Classification

### Haiku
- Mechanical, minimal judgment
- Obvious implementation from spec
- Examples: create files, add a thin wrapper command, register in dispatch table
- LLM needs: commit description + relevant spec section

### Sonnet
- Moderate judgment, bounded scope
- Requires understanding context and making local decisions
- Examples: parser implementation, command with branching logic, display formatting
- LLM needs: commit description + relevant spec section + exemplar if available

### Opus
- NOT allowed in commit plans
- Always decompose into haiku and sonnet commits
- If a commit feels like opus, it means the spec isn't detailed enough - refine the spec first

---

## Exemplar Strategy

Identify 1-2 commits that demonstrate all recurring patterns. Implement these first (even if it means reordering the plan slightly). All subsequent commits reference exemplars for structural consistency.

Common exemplar archetypes:
- **Mutation command**: reads file, modifies data, writes file, confirms action
- **View command**: reads file(s), filters/transforms, formats output
- **Parser/transformer**: takes raw input, produces structured output

When requesting implementation of a non-exemplar commit, reference the exemplar:
```
Implement commit ##. Follow the same patterns established in commit ##
(the exemplar): argument parsing style, error handling, usage logging
sandwich, confirmation output format.
```

---

## Parallelization

### Thread Map Convention

Organize commits into named threads (independent work streams). Use ASCII art:

```
01 ÄÂÄ [A] 020304 Ä¿
    ÃÄ [B] 0506 ÄÄÄÄÄ´
    ÀÄ [C] 07 ÄÄÄÄÄÄÄÄÙ
                       
                  convergence point
```

### Rules
- Commits in different threads have no shared dependencies
- "Parallel" means "can be done in any order or interleaved"
- When stuck on one thread, switch to another - no blocking
- Mark convergence points explicitly - these are integration moments that may need extra verification

---

## Hardening Standards

### Per-Commit (minimum, always applied)
- Invariants: at least one testable assertion per commit
- Error handling: handle every failure mode this commit introduces
- Strategic prints: every user-facing action gets confirmation output
- Type hints: every new function gets full signatures

### End-of-Phase (after completing a phase, before starting next)
Run the full analysis checklist:

1. **Presuppositions audit**: what does the code assume about its environment that isn't checked? (file exists, env var set, valid UTF-8, etc.)
2. **Assumptions audit**: what did you assume during implementation that the spec didn't explicitly state? Mark each and verify.
3. **Entailments check**: what does the current implementation logically imply that you didn't intend? (e.g., "allowing empty summaries means tsk list shows blank lines")
4. **Cognitive decay review**: re-read the spec. What did you forget or drift from during implementation? What shortcuts did you take that you told yourself were temporary?
5. **Pre/post condition verification**: for each command, state what must be true before it runs and what must be true after. Verify these hold.
6. **Usage data review**: if the tool has been in use, analyze usage_log.txt. Which commands are used? Which aren't? Any surprises?

---

## Interaction Patterns

### Requesting Design Feedback
```
Provide feedback, then gather context by asking targeted questions,
socratic questions, veteran questions.
```

### Requesting Naive-to-Veteran Analysis
```
Consider naive or beginner approaches, explain drawbacks and discard
them. Then verbalize veteran approaches with prioritized suggestion.
```

### Requesting Implementation
```
Start with commit [##]. Follow the commit rhythm in workflow_rhythm.md.
Use commit [##] as the exemplar for patterns.
```

### Requesting Analysis
```
Run end-of-phase analysis on the current codebase. Here is the code
[paste]. Here is the spec [paste]. Identify drift, forgotten items,
unhardened paths, and extraction opportunities.
```

### Course Correction
When the LLM drifts from your style:
```
This uses [classes/main pattern/clever Python/etc]. Refer to
coding_style.md: [specific rule]. Redo with [explicit correction].
```

---

## Prompt File Management

### Directory Structure
```
prompts/
  developer_profile.md  - who I am, tendencies, background
  interaction_modes.md  - how the LLM should communicate with me
  coding_style.md       - language and structural conventions
  environment.md        - tools, directories, sync, constraints
  workflow_rhythm.md    - per-commit process, hardening, verification
  spec_format.md        - how to write specs
  analysis_checklist.md - end-of-phase analysis steps
  naive_to_veteran.md   - thinking pattern: discard naive, surface veteran
  latent_knowledge.md   - thinking pattern: surface undiscussed considerations
  ranking_task.md       - task: rank by usefulness, complexity as note
  debugger.md           - task: find and fix code bugs
  mindset_extractor.md  - task: extract thread mindset at end of thread
  thread_templates/
    design_thread.md    - opening prompt for design threads
    impl_thread.md      - opening prompt for implementation threads
    refinement_thread.md - opening prompt for analysis threads
  mindsets/
    thread_mindset_tsk.md   - tsk project domain knowledge
    thread_mindset_*.md     - future project mindsets
```

### Versioning Convention
- Filename stays stable: `coding_style.md`
- Version header inside: `VERSION: 3` / `UPDATED: 2026-05-27`
- Archived snapshots (optional): `coding_style_v2.md`
- Rule: file without version suffix is always current

### Update Triggers
- After completing a phase: review all prompt files for drift
- After a thread where you repeatedly corrected the LLM: update
  the relevant file with the correction
- After extracting a new shared library: update environment.md
- After formalizing a new convention: add to coding_style.md
- After a significant design thread: extract a thread_mindset_*.md
  using mindset_extractor.md
- After noticing a new personal tendency: update developer_profile.md

---

## Branch and Thread Management

### When to Branch a Conversation
- Topic shifts from design to implementation
- Switching to a different project or module
- Thread is getting long (context window pressure)
- Phase boundary (end of phase 0, start of phase 1)

### Handoff Document Template
Write at the end of every design thread. Structure:

```
# Branch Handoff: [Project/Phase Name]

## Project: [name]
### Architecture - key structural decisions
### Directory Structure - where code and data live
### Environment - how to run, dependencies, sync
### Data Format - how data is stored and parsed
### Key Decisions - ADR-style, with rejected alternatives
### Artifacts Produced - list of specs, plans, documents
### What the Next Thread Should Do - specific scope
```

### Continuation Thread Checklist
Before starting a new implementation thread, verify you have:
- [ ] developer_profile.md and interaction_modes.md (always)
- [ ] coding_style.md (always)
- [ ] workflow_rhythm.md (for implementation threads)
- [ ] Spec document (paste or reference)
- [ ] Handoff document (paste)
- [ ] Thread mindset file if one exists for this project
- [ ] Current codebase state (paste files or describe)
- [ ] Clear scope: which commits this thread covers
- [ ] Exemplar commit identified (if past commit 01)
