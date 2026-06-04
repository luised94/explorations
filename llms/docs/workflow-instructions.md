# Workflow Prompt Instructions

Reusable instructions organized by phase. Paste relevant sections into conversations. Each section is self-contained.

---

## Phase 0: Context Loading

Use when starting or resuming a project session.

```
Here is the current project state. Files are attached/pasted below.

Demonstrate your understanding before acting:
- Describe the architecture, patterns, and conventions you observe
- Identify the coding guidelines in effect (stated and unstated)
- Note any format mismatches, dead artifacts, or convention drift between files

Do not generate code. Summarize what you see.
```

### Why this works
Forces comprehension proof before action. Catches stale artifacts (like awk scripts parsing a format the bash script no longer produces). The LLM's description reveals its mental model - correct it now, not after it writes wrong code.

---

## Phase 1: Analysis and Decision Surfacing

Use after context is loaded and understood.

```
No code yet. Analyze the current state:

1. Identify bugs, inconsistencies, and defensive gaps in the existing code.
   Rank by severity (data loss > incorrect behavior > guideline violation > cosmetic).
2. Surface every decision required before implementation.
   For each, state your suggested resolution. Do not ask me to choose from bare options -
   give me a default with reasoning. I will confirm or adjust.
3. Identify tacit or latent knowledge that should be made explicit -
   undocumented conventions, implicit data models, unstated contracts.
4. Note anything I should address but likely forgot to mention.

Present suggestions, then articulate your strategy. These are two separate outputs.
```

### Why this works
"Rank by severity" prevents flat lists where a data-loss bug sits next to a naming quibble. "Suggested resolution" with reasoning eliminates back-and-forth - the user confirms or adjusts, never starts from zero. "Tacit knowledge" catches the things nobody writes down (like "FRICTION.md is an inbox" or "archive files are a graveyard").

---

## Phase 2: Decision Refinement

Use after the LLM presents its analysis. Expect 1-2 rounds.

```
I agree with your suggestions, with these adjustments: [adjustments].

Before we proceed:
- Are there additional decisions I forgot to address?
- Any remaining tacit knowledge or unstated assumptions?
- Defensive practices, error handling, or user-facing safety gaps we haven't covered?

Integrate my adjustments and your answers into an updated strategy.
No code yet.
```

### Pattern note
"I agree with your suggestions" is a baseline, not a stop signal. The adjustments that follow are the actual input. When the user says "I agree" then adds constraints, treat the constraints as primary and the agreement as "your direction is right, here are the specifics."

---

## Phase 3: Implementation Planning

Use when all decisions are made and strategy is confirmed.

```
Structure the implementation as commit-by-commit.

For each commit:
- Classify as haiku (small, <20 lines changed), sonnet (medium, one function or file),
  or opus (large, multiple interacting changes).
- Decompose any opus commits into haiku and sonnet.

Perform topological sort to surface dependencies between commits.
Then batch analysis: which commits can be output together without conflicts?

No code yet. Plan only.
```

### Why this works
Complexity classification prevents the LLM from hiding a rewrite inside "update the archive function." Topological sort ensures the LLM doesn't output code that depends on code it hasn't written yet. Batching reduces round-trips without sacrificing reviewability.

---

## Phase 4: Batch Execution

Use to trigger each batch of implementation.

```
Start with batch N. For each commit in the batch:

1. Purpose: one sentence, what and why.
2. Inventory: files, functions, sections touched.
3. Editing instructions: choose the most efficient method for each change -
   anchored copy-paste block, nvim substitution, sed command, or full artifact
   for new files. Use line anchors (nearby unique strings), not line numbers.
4. Verification: commands to run with expected outputs.
5. Commit message: type(scope): imperative declaration, then bullet points.

We proceed batch by batch. I will verify and report before the next batch.
```

### Why this works
Anchored edits ("find this line, add after it") are faster and less error-prone than diffing a full file. Verification with expected outputs catches integration bugs immediately. Batch-by-batch flow lets the user course-correct between batches (like renaming a file or removing unused functions).

---

## Phase 5: Session Consolidation

Use at the end of any substantial session.

```
Consolidate tacit and latent knowledge from this session into reusable patterns.

Capture:
- Coding guidelines: stated, observed, and any conflicts resolved
- Workflow patterns: what sequence of steps we followed and why
- Interaction patterns: which instructions produced good output, which needed adjustment
- Project-specific decisions: what was decided, what was rejected, and why
- Issues and frictions encountered during the session
- Future work: immediate, medium-term, and structural observations
- Veteran notes: advice, critiques, blind spots

Output as a standalone document that can be pasted into future sessions
for context recovery.
```

### Extension: Prompt extraction

```
Additionally: formalize reusable patterns from this session into
structured prompt instructions.

Look for tacit knowledge in my messages - things I meant but
didn't explicitly say, inferred from how you responded and how I
reacted to your output. Convert these into explicit instructions
others (or I) can reuse.

Organize by position in workflow. Keep each instruction concise.
```

---

## Cross-Phase Instructions

These apply throughout any session. Paste once at the start.

```
Planning and implementation are separate phases. Do not generate code
during planning phases. I will say when to start.

When I provide a bulk context dump, synthesize it - do not ask me to
re-explain or re-organize. Handle messy input.

When I state priorities late or casually, elevate them. If my actual
focus is buried in paragraph three, lead with it.

When I telegraph interaction shape ("I will likely give one more round
of feedback then we proceed"), adjust your pacing - don't over-invest
in areas I've signaled are nearly final.

For technical judgment calls (which implementation is better, what to
keep vs discard), make the call and show your reasoning. I delegate
judgment but verify reasoning. Do not present bare options without
a recommendation.

For destructive or irreversible operations, always default to preview.
Surface this as a design concern during analysis, not as an afterthought
during implementation.

Track mid-stream corrections (renames, removed features, changed requirements)
and integrate them into remaining work without re-prompting.
```

---

## Tacit Patterns Extracted From This Session

These are behaviors the user demonstrated but did not state as instructions. Formalized here for reuse.

**Confirm-then-refine.** User says "I agree" then immediately adds modifications. The agreement means "direction is right." The modifications are the actual specification. Never treat "I agree" as "ship it."

**Audit as a phase.** "Any bugs? Issues? Inconsistencies?" is a genuine request for proactive critique, not a rhetorical question. The LLM should spend real effort here - this is where the grep substring bug and the dry-run gap were caught.

**Surgical over wholesale.** User prefers anchored edits to full file replacement. Thinks in diffs, not snapshots. When the change is small, give a sed command or nvim instruction. When the change is a full function rewrite, give the function as a block with anchor instructions for where to paste it. Reserve full-file artifacts for new files only.

**Commits as the unit of thought.** User thinks in commits, not files or features. Each commit has a purpose, a scope, and a verification step. This maps naturally to LLM output batching.

**Verification is not optional.** Every change needs a "run this, expect that" block. The user will actually run it. If the expected output is wrong, trust is damaged. Be precise about expected outputs, including stderr.

**Dump-and-sort.** User prefers to dump all context at once ("I kind of dumped a bunch of stuff") and expects the LLM to sort, prioritize, and synthesize. Do not ask the user to re-organize their input. Do not complain about messiness. Parse it.

**Telegraph acknowledgment.** When the user says "I will likely provide one more round of feedback," they're telling you the planning phase is almost over. Tighten your output - fewer open questions, more consolidated recommendations. Match the user's sense of momentum.
