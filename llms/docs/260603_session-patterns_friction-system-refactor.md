# Session Patterns: Friction System Refactor (2026-06-03)

## Project Context

Personal productivity CLI tool for rapid-capture friction logging. Bash-sourced script with awk backend. Single user, git-backed, USB-synced. The system follows an inbox model: FRICTION.md is the working queue, archive/ is the graveyard.

Files: `13_friction.sh` (bash, sourced), `mc_friction_process_entries.awk` (awk, called by bash). Scripts live at `~/personal_repos/my_config/scripts/`. Data lives at `~/personal_repos/friction/`.

---

## Coding Guidelines (Consolidated)

### Universal
1. Data-oriented procedural, top-to-bottom. No OOP patterns, no premature abstraction.
2. Full descriptive variable names. No abbreviations except "usb".
3. No helpers unless 3+ call sites AND the helper is substantial AND self-contained.
4. Inline by default. Extract only when the threshold is met.
5. ASCII only in source files.
6. Minimal nesting and indirection. Early returns for error cases, main path stays flat.

### Bash-Specific
1. Standard bash only. No bashisms that require specific versions, no non-portable flags.
2. `[[ ]]` throughout. Never `[ ]`.
3. Bash regex for validation (`[[ "$var" =~ ^pattern$ ]]`). No external regex tools for simple checks.
4. Standard if statements. No `[[ condition ]] && action` as control flow.
5. Sourced files: prefix all variables with module name (`friction_`, `MC_FRICTION_`) to avoid namespace collisions.
6. Local variables in functions: always `local`.
7. Errors to stderr with `module[ERROR]:` prefix. Warnings with `module[WARN]:`.
8. Functions return 1 on failure. Callers use `|| return 1` for propagation.

### Awk-Specific
1. Shorter-but-meaningful names are acceptable (awk convention). Not single-letter except loop indices, but abbreviated prefixes fine: `entry_date`, `matched_count`, `proj_count`.
2. `flush_entry()` pattern: accumulate state for current record, flush when next record starts and in END. This is the one established helper pattern - it always has exactly 2 call sites and that's acceptable.
3. Output routing: data to stdout, diagnostics/summaries to `/dev/stderr`.
4. Insertion sort for ordering (no external sort dependency).
5. Mode variable (`-v mode=show|archive`) to consolidate related parsers into one file. One parser, multiple output behaviors.

### Output Contract (CLI Tools)
1. Entry/data to stdout. Always.
2. Diagnostics, summaries, feedback, counts to stderr. Always.
3. This makes every command pipe-friendly by default: `fshow project | wc -l` works, `fshow project 2>/dev/null` gives clean data, bare `fshow project` shows both at terminal.
4. Confirmation prompts go to stderr, read from stdin.

### Defensive Practices
1. Destructive operations (archive, delete, move) are dry-run by default. Preview then prompt. Add `--execute` for scripting.
2. Atomic file swaps: write to temp, verify (count entries, check exit status), then mv. Never overwrite the original until verification passes.
3. CRLF stripping on input (`gsub(/\r$/, "")`). Files travel via git across platforms.
4. When parsing structured data, never use grep with user-provided patterns as regex. Use awk with string comparison. The project name `a-b` is a regex metacharacter bomb in grep.
5. Malformed input: warn to stderr, pass through unchanged. Never silently drop data. Never crash.
6. Source-time checks: verify dependencies exist when the script is sourced. Warn but don't fail - degrade gracefully.

---

## Human-AI Interaction Workflow

### What worked in this session

**Phase 1: Context dump.** User pastes all relevant files, describes the situation loosely, says "I kind of dumped a bunch of stuff." This is the right move. The LLM needs full context to synthesize - partial context leads to wrong assumptions. Dump everything, let the LLM sort it out.

**Phase 2: Analysis before action.** "No code yet" is a critical instruction. Forces the LLM to analyze, surface decisions, identify bugs, and propose strategy before generating anything. Without this, the LLM jumps to code that bakes in unexamined assumptions.

**Phase 3: Decision surfacing.** Each round surfaced decisions the user hadn't explicitly considered (archive matching semantics, dry-run default, non-@@ line behavior, pipe-friendly output). The user confirmed or adjusted. This iterative narrowing is more reliable than trying to specify everything upfront.

**Phase 4: Deep audit.** Explicitly asking "any bugs, issues, inconsistencies?" produced the grep substring bug, the grep -v description-text bug, and the non-portable grep -oP. These are the kind of bugs that live in code for years because they work 95% of the time. The audit pass catches them before the rewrite bakes them in again.

**Phase 5: Structured implementation.** Commit-by-commit plan with classification (haiku/sonnet/opus), topological sort, and batching. This prevents the LLM from generating a wall of code that's impossible to review. Each batch is verifiable independently.

**Phase 6: Pattern extraction (this document).** Consolidating tacit knowledge into explicit patterns before context is lost. This is the step most people skip.

### Effective instructions for the LLM

These instructions produced measurably better output in this session:

- **"No code yet."** Prevents premature implementation. Use during planning phases.
- **"Articulate your strategy, then we go from there."** Forces the LLM to commit to an approach the user can review.
- **"Any tacit, latent knowledge that should be made explicit?"** Surfaces assumptions the LLM is making silently.
- **"Rank order them."** Forces prioritization instead of flat lists.
- **"Structure as commit by commit."** Produces reviewable, atomic units instead of monolithic output.
- **"Decompose any opus commits."** Prevents the LLM from hiding complexity behind a single large commit.
- **"Perform batching analysis."** Groups independent work for efficient output.
- **"Output editing instructions, not just code."** Anchored edits (find this line, add after it) are faster than diffing an entire file.

### Instructions that need care

- **The full Processing Protocol.** It's valuable for complex sessions like this one. For simple queries it adds overhead the LLM spends on scratchpad ceremony instead of answering. Consider a lighter version for quick questions or explicitly suspend it: "skip protocol, just answer."
- **Mode selection.** Useful when the LLM is uncertain about scope. Less useful when the task is obvious. The LLM shouldn't spend tokens justifying why it picked EXECUTE over DESIGN for a factual question.

### Anti-patterns observed

- **Lost threads.** The user lost track of previous conversations about this project. For multi-session projects: maintain a `PROJECT_STATUS.md` or similar artifact that tracks decisions made, current state, and next steps. Paste it at the start of each new session.
- **Late requirements.** Dry-run default came up in the final batch. It was easy to fold in here, but in a larger project this kind of late addition can cascade. Surface destructive-operation UX decisions during the audit phase, not the implementation phase.
- **Guideline drift.** The "no abbreviations" guideline was written for bash but the existing awk scripts didn't follow it. Resolving this required a pragmatic decision (bash = verbose, awk = awk-conventional). Document language-specific exceptions explicitly in the guidelines rather than letting them be implicit.

---

## Reusable Workflow Template

For future sessions on this or similar CLI tool projects:

```
1. CONTEXT DUMP
   - Paste all relevant source files
   - Paste coding guidelines
   - Describe current state and what changed since last session
   - Paste any relevant friction/notes entries about the project

2. ANALYSIS (no code)
   - LLM describes what it sees: architecture, patterns, conventions
   - LLM identifies bugs, inconsistencies, format mismatches
   - LLM surfaces decisions that need to be made
   - LLM suggests resolutions for each decision

3. DECISION ROUND (1-2 passes)
   - User confirms/adjusts suggestions
   - LLM asks "any tacit knowledge to surface?"
   - LLM asks "any additional decisions I missed?"
   - Defensive practices, error handling, feedback audit

4. IMPLEMENTATION PLAN (no code)
   - Commit-by-commit with haiku/sonnet/opus classification
   - Topological sort for dependencies
   - Batching analysis for output efficiency

5. BATCH EXECUTION
   - For each commit: purpose, inventory, editing instructions, verification, commit message
   - User applies and verifies between batches
   - Mid-stream corrections integrated into remaining batches

6. CONSOLIDATION
   - Extract patterns, guidelines, and decisions into reusable document
   - Update project status for next session
   - Log any friction encountered during the session itself
```

---

## Friction Project: Future Work

### Immediate (next session)
- Verify all batch 1-3 changes work end-to-end on real data
- Run `fshow` on actual FRICTION.md and check summary output
- Archive some real entries to test the dry-run flow
- Delete the three old awk files if not already done (user confirmed deletion)

### Medium-term
- **Entry search.** `fgrep` or `fsearch` to search descriptions across active and archived entries. Useful when you remember logging something but not which project.
- **Archive reading.** `fshow --archive friction` to read archived entries for a project. Low priority (graveyard) but near-free to implement since the awk script already parses @@ format.
- **Shell completion.** Tab-completion for project names in fshow/farchive. Extract unique project names from FRICTION.md, feed to bash completion. Addresses the "I don't remember subcategories" friction.
- **Stale threshold configuration.** Currently hardcoded at 14 days. Could be an environment variable `MC_FRICTION_STALE_DAYS`.

### Structural observations
- The friction tool has friction about itself (`project:friction` entries about remembering commands, needing features). This is a healthy signal - the tool is used enough to generate its own improvement backlog.
- The hierarchical naming convention emerged organically and was only formalized in this session. Watch for new conventions emerging in practice and formalize them before they drift.
- The inbox model (log  review  archive) is clean but there's no "review" step beyond `fshow`. If a structured review workflow emerges (weekly triage, batch archive), consider a `freview` command that walks through entries interactively.

---

## Veteran Notes

**On grep as a parser.** Every time you use grep to match structured data, you're writing a latent bug. Grep matches patterns anywhere in a line. When your data has multiple fields and you're matching one of them, grep will eventually match the wrong field. Use awk. It was literally designed for this.

**On destructive defaults.** Any command that moves, deletes, or overwrites data should preview by default. The cost of a preview is one extra awk pass (milliseconds). The cost of accidentally archiving the wrong entries is manual git archaeology. Always default to dry-run. Always.

**On format convergence.** This project had three awk scripts parsing three different entry formats, only one of which matched what the bash script actually produced. This happens whenever a tool evolves through phases - each phase leaves behind artifacts from the previous format. Audit for format mismatches whenever you refactor. Dead formats are dead code with better camouflage.

**On the Processing Protocol.** The scratchpad discipline is genuinely useful for complex, multi-constraint problems. It forces the LLM to think before writing. But for this session, the most productive instructions were the simple ones: "no code yet," "rank order them," "any tacit knowledge?" The protocol's value is in the habit of structured thinking, not in the ceremony of metadata tags. Use the protocol for complex work, suspend it for quick tasks.

**On session continuity.** The biggest friction in this session was reconstructing context from a project the user hadn't touched in a while. The solution is a living project status document that gets updated at the end of each session and pasted at the start of the next. Three sections: Decisions Made, Current State, Next Steps. Five minutes of writing saves thirty minutes of re-derivation.
