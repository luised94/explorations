# Complete Prompt Library

## Phase 0: System Prompts (Reusable Across Projects)

### 0A: Opus Design Partner

```markdown
You are a senior software architect engaged in collaborative system design.

BEHAVIOR:
- Challenge assumptions before accepting requirements
- Propose alternatives when you see simpler paths
- Flag risks, edge cases, and failure modes early
- Keep a running mental model of all decisions made and WHY
- Track what was considered and rejected - this matters later
- Ask clarifying questions rather than assuming

When the user says "let's move to implementation planning," shift modes:
- Stop exploring alternatives
- Consolidate decisions into a concrete plan
- Identify the minimal set of changes needed
- Think in terms of atomic, independently-verifiable commits

OUTPUT STYLE:
- Be direct and concise during exploration
- Use structured formats when presenting plans
- Call out your confidence level on uncertain recommendations
```

### 0B: Sonnet Executor

```markdown
You are a senior developer executing a precisely-scoped task.

RULES:
- Do EXACTLY what the task describes. No more.
- Do NOT refactor adjacent code unless explicitly asked.
- Do NOT add features, optimizations, or "improvements" beyond scope.
- Follow the patterns shown in the provided context exactly.
- If something seems wrong or missing in the task spec, SAY SO
  rather than guessing. Output your concern and stop.
- Match the existing code style in the provided files precisely.

OUTPUT FORMAT:
- Output the complete modified file(s), not diffs or snippets.
- If creating a new file, output the complete file.
- After the code, write 1-2 sentences confirming what you changed and why.
- Flag anything you're uncertain about with [UNCERTAINTY: reason].
```

---

## Phase 1: Design Conversation

No rigid prompt needed - this is organic conversation with Opus using System Prompt 0A. But when you're ready to transition:

### 1-TRANSITION: Shift From Design to Planning

```markdown
Let's freeze the design and move to implementation planning.

Before we plan tasks, consolidate what we've decided:

1. ARCHITECTURE SUMMARY
   The key components and how they interact. Brief.

2. DECISIONS LOG
   Every significant choice we made and the reasoning.
   Include what we REJECTED and why.

3. OPEN QUESTIONS
   Anything still ambiguous that might affect implementation.

4. TECHNICAL CONSTRAINTS
   Frameworks, patterns, conventions, and non-negotiables
   we've established.

Don't start planning yet. Just produce this summary
so we're aligned before decomposition.
```

---

## Phase 2: Decomposition (Opus, Same Thread)

### 2A: Task Decomposition

```markdown
Now decompose the implementation into atomic commits.

TARGET COMPLEXITY: Each task should be "Haiku-level" - meaning
simple enough that a less capable model could execute it given
sufficient context. Single purpose, minimal judgment required,
one clear behavioral change.

STRUCTURE:

For each task output:

**[Thread.Sequence] Task Title**
- Complexity: ?? HAIKU | ?? SONNET | ?? OPUS
- Thread: [which parallel track]
- Depends on: [task IDs that must complete first]
- Produces: [what downstream tasks need from this]
- Files touched: [list]
- Description: [1-2 sentences]

RULES:
- Start with Step 0: shared interface contracts and types
  that all threads will code against. This runs before
  any parallel work.
- Group tasks into parallel threads where possible.
  Tasks within a thread are sequential.
  Threads are independent until explicit merge points.
- If a task is ??, explain why it can't be decomposed further
  and what decision blocks it.
- Most tasks should be ??. More than 20% ?? means
  the decomposition is too coarse. Any ?? should be rare.
- End with explicit MERGE POINT tasks where threads reconnect.

OUTPUT ORDERING:
1. Step 0 (interfaces/types)
2. Thread definitions with task sequences  
3. Dependency graph (simple ASCII showing relationships)
4. Merge points and integration tasks
```

### 2B: Dependency Graph Validation

```markdown
Review the decomposition you just produced.

Check for:
1. CIRCULAR DEPENDENCIES between threads
2. MISSING DEPENDENCIES - does any task assume something
   exists that no prior task creates?
3. INTERFACE MISMATCHES - could two threads independently
   drift to incompatible implementations?
4. ORDERING ERRORS - is any task sequenced before
   something it depends on?
5. GRANULARITY - any task that's actually 2+ tasks
   hiding as one? Look for "and" in descriptions.

If you find issues, fix the decomposition and re-output
the corrected version. If clean, say "Validated" and
output the final task count and thread summary.
```

---

## Phase 2C: Context Compilation (The Key Phase)

### 2C-INSTRUCTION: Generate Context Packets

```markdown
Now generate a SELF-CONTAINED CONTEXT PACKET for each task.

The executing model has ZERO knowledge of our conversation.
It will receive ONLY the packet you produce. Nothing else.

For each task, output:

---
## PACKET [Thread.Sequence]: [Task Title]

### SYSTEM CONTEXT
[Language/framework, 1 line]
[Project description, 1 line]

### FILES
[Complete content of each file being modified.
 Mark NEW FILE if creating from scratch.
 If file is long, include only the relevant section
 with 20 lines of surrounding context and a comment
 indicating "// ... rest of file unchanged"]

### INTERFACES
[Only type signatures and function signatures this task
 interacts with. Not implementations. Copy these exactly
 from Step 0 contracts or from prior task outputs.]

### PATTERNS TO FOLLOW
[Copy-paste a concrete example from the codebase
 of an analogous function/component/test.
 Say "Follow this pattern:" and show it.]

### TASK
[2-3 sentences. What to change and why.]

### EXPECTED RESULT
[Concrete before/after, or input  output example,
 or "The file should now export X which does Y"]

### LANDMINES
[Things the executing model might naturally do wrong.
 Decisions we made against the obvious approach.
 Non-obvious constraints. Leave empty if none.
 Format: "Do NOT [thing]. Reason: [why]"]

### VERIFICATION
[How to confirm correctness. Test command,
 type-check expectation, or behavioral description.]
---

CRITICAL RULES:
- Each packet STANDS ALONE. Never reference other packets.
  If two tasks need the same context, DUPLICATE it.
- Include ONLY what this specific task needs.
  Extra context hurts more than it helps.
- The PATTERNS section is the most important.
  Showing beats telling. Always include a concrete example.
- LANDMINES should capture insights from our design
  conversation that a fresh model wouldn't know.
  This is where our discussion adds the most value.
```

### 2C-PARALLEL: Thread Header Packets

```markdown
Also generate a THREAD HEADER for each parallel thread:

---
## THREAD [Letter]: [Thread Name]

### Purpose
[What this thread accomplishes overall, 2 sentences]

### Shared Contracts
[The interface definitions from Step 0 that this thread
 must conform to. Copy them in full.]

### Task Sequence
[Ordered list of task IDs in this thread]

### Boundary Rules
- This thread ONLY modifies: [list of files/directories]
- This thread does NOT touch: [files owned by other threads]
- When you need something from another thread, import
  from the interfaces defined in Shared Contracts.
  The implementation will exist at merge time.
---

Append this thread header to the top of every packet
in that thread. This gives the executor awareness of
the larger context without needing the full plan.
```

---

## Phase 3: Execution

### 3A: Task Execution Prompt (Wraps Each Packet)

```markdown
[INSERT SYSTEM PROMPT 0B HERE]

[INSERT THREAD HEADER HERE]

[INSERT CONTEXT PACKET HERE]

Execute this task now. Output:
1. The complete updated file(s)
2. A CHANGES summary (2-3 bullet points, what you did)
3. A COMMIT MESSAGE following conventional commits format
4. Any [UNCERTAINTY] flags if something in the spec
   seems incomplete or contradictory
```

### 3B: Sequential Task Chaining

When tasks within a thread are sequential and each builds on the last:

```markdown
[INSERT SYSTEM PROMPT 0B HERE]

[INSERT THREAD HEADER HERE]

Previous task output:
```
[paste the file(s) output by the previous task]
```

[INSERT CURRENT TASK'S CONTEXT PACKET HERE]

Note: The "FILES" section in the packet shows the ORIGINAL
file state. The "Previous task output" above shows the
CURRENT state after prior changes. Work from the current state
but use the packet's interfaces and patterns sections.

Execute this task now.
[same output format as 3A]
```

### 3C: Handling Uncertainty Flags

When Sonnet outputs an `[UNCERTAINTY]` flag:

```markdown
The executing model flagged an uncertainty:

[paste the uncertainty]

Original task packet:
[paste packet]

Model's output:
[paste what it produced]

Either:
A) The uncertainty is valid - revise the packet and re-execute
B) The output is actually correct - proceed  
C) This reveals a decomposition gap - needs re-planning

Which is it? And what's the fix?
```

*Run this on Sonnet for quick triage, or Opus if the uncertainty seems architectural.*

---

## Phase 4: Integration

### 4A: Thread Merge Review

```markdown
Two parallel threads have completed. Review their outputs
for compatibility before merging.

SHARED CONTRACTS THEY CODED AGAINST:
[paste Step 0 interfaces]

THREAD A OUTPUT:
[paste final files from Thread A]

THREAD B OUTPUT:  
[paste final files from Thread B]

Check for:
1. Do both threads conform to the shared contracts?
2. Any naming mismatches, type mismatches, or import errors?
3. Any implicit assumptions one thread makes about the other?
4. When these files coexist in one codebase, are there conflicts?

Output:
- COMPATIBLE / INCOMPATIBLE
- If incompatible: what specifically conflicts
  and which thread should be adjusted
- If compatible: any minor adjustments needed
  for clean integration (import paths, etc.)
```

### 4B: Final Integration Verification

```markdown
All threads have been merged. Here is the complete
set of new/modified files:

[paste all files]

And here are the original shared contracts:
[paste Step 0 interfaces]

Verify:
1. All interfaces are implemented correctly
2. All imports resolve to real exports  
3. No orphaned code or missing connections
4. Error handling is consistent across thread boundaries
5. The feature works end-to-end (trace the happy path
   and one error path through the code)

Output:
- PASS / FAIL
- If FAIL: specific issues and which task packets
  need re-execution or revision
```

---

## Quick Reference: When To Use What

```
PROMPT           MODEL    WHEN
컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴�
0A               Opus     Start of design session
1-TRANSITION     Opus     Design  planning shift  
2A               Opus     Decompose tasks
2B               Opus     Validate decomposition
2C-INSTRUCTION   Opus     Generate context packets
2C-PARALLEL      Opus     Generate thread headers
3A               Sonnet   Execute individual task
3B               Sonnet   Chain sequential tasks
3C               Sonnet*  Handle uncertainties
4A               Sonnet   Merge thread outputs
4B               Sonnet   Final verification
```

## Token Budget Reality Check

```
Phase 1-2 (Opus):  ~10-20k tokens output
                    Done ONCE per feature

Phase 3 (Sonnet):  ~1-3k tokens per task
                    x N tasks
                    Bulk of the spend but cheap per-unit

Phase 4 (Sonnet):  ~2-5k tokens per merge point
                    Done once per thread pair
```

---

## One Reusable Meta-Prompt

If you want to bootstrap this whole system in a single shot to start a new project or feature:

```markdown
I'm about to describe a feature I need to build.

I want you to:
1. Discuss the design with me until I say "let's build it"
2. Consolidate our decisions (architecture, choices, rejections)
3. Decompose into Haiku-level atomic commits grouped
   into parallel threads with a dependency graph
4. Generate a self-contained context packet for each task
   that a fresh Sonnet instance could execute with zero
   additional context

Start with Step 0 interface contracts before any
parallel tasks. Flag any ?? tasks that need
architectural decisions I should make.

Each context packet must include: relevant file content,
interface signatures, a pattern to follow from the codebase,
the specific task, expected result, landmines from our
conversation, and verification criteria.

Here's what I need to build:
[describe feature]
```

This single prompt sets the trajectory for the entire pipeline.
