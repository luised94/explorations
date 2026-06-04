# Session Retrospective: tsk Phase 0

DATE: 2026-06-04
THREAD SPAN: Commits 09-17e + hardening + phase-0 review
TOOL: tsk -- task, calendar & habit tracker
PARTICIPANTS: Developer (solo, procedural style, USB-sync workflow) + LLM

---

## 1. Coding Guidelines

### Stated rules that held throughout

The function extraction rule (2+ call sites or dispatch target) was the single
most consequential style constraint. It was applied correctly in every commit
and prevented premature abstraction repeatedly. Specific instances where it
fired:

- parse_habit_log: extracted at commit 12 with handle_today (commit 15) named
  as the second caller. The assumption was marked and later confirmed.
- ensure_data_files: extracted at commit 17d when handle_init became the second
  caller alongside module-level derived section.
- validate_priority: extracted at commit 08 with handle_goal (commit 09) named
  as assumed second caller. Confirmed when 09 landed.
- validate_time_of_day: extracted within commit 11 (handle_event) -- two calls
  within the same handler (start and end validation). Borderline case; the rule
  says "2+ call sites" without specifying they must be in different functions.
  Decision: 2 calls within one handler counts. Defensible but worth noting.

The no-higher-order-function rule was tested by every sort operation. The
resolution pattern that emerged: sorts on record fields where order is unknown
at write-time (priority, due date, time_start) use inline tuple keys in
sorted() -- the style doc's explicit exception for "genuine comparison-based
sorting." Sorts where the order IS known (FIELD_ORDER) walk the known sequence
directly. This distinction was applied consistently but required active
vigilance in every commit that sorted anything.

The domain-vocabulary naming rule produced the most revisions during drafting.
Generic names (key, value, item, result) were caught and replaced in every
handler. The pattern that worked: name the variable for what it IS in the task
tracker, not what it IS in Python. field_name not key, task_summary not text,
matching_records not results, target_record not match.

### Observed rules (not stated, emerged from practice)

Error message format solidified by repetition: "error: {what}" to stderr,
optional "usage: tsk ..." line, then sys.exit(1). This was never formally
stated as a rule but became canonical through the handle_add exemplar. Every
subsequent handler followed it without being told. The pattern should be
documented in the coding style doc.

Confirmation print format also solidified implicitly: "added: {id} {summary}",
"completed: {id} {summary} -> done.txt", "retired: {id} {summary} -> done.txt".
The verb-colon-id-summary shape was established by handle_add and never
deviated from. Worth formalizing.

Write-order discipline emerged from handle_done: write done.txt before
active.txt so a crash after the first write doesn't lose the record from both
files. This was a design decision made inline during commit 12 and noted in
the response but never added to the spec or style doc. Should be a stated rule:
when a mutation touches two files, write the destination before the source.

### Conflicts resolved

Blueprint vs CLI dispatcher: The standard phase blueprint (7 sections) was
designed for batch processors. Sections 1-3 (CONFIGURATION, PREFLIGHT,
DERIVED) mapped cleanly to tasks.py. Sections 5-6 (main-loop metrics,
post-run summary, 1:1 artifact assertion) were judged N/A for a dispatcher.
The resolution was to apply 1-3 as ASCII headers, record 5-6 as N/A with a
code comment explaining why, and note that the dispatch-level usage log and
per-command confirmation prints serve the same roles. This was a pushback
on the developer's template -- the LLM flagged which sections fit and which
didn't rather than cargo-culting the full blueprint. The developer accepted.

Atomic writes vs simplicity: The original write_file was a direct write_text.
The LLM proposed write-to-temp-then-rename as a robustness improvement,
motivated by the USB-sync context (yanked drive = truncated file). The
developer accepted. This was a case where the LLM's context awareness
(remembering the USB constraint from the spec) drove a recommendation the
developer hadn't asked for. Good pattern: LLM should proactively connect
environment constraints to implementation choices.

---

## 2. Workflow Patterns

### The sequence that worked

1. Spec provided upfront (complete, with decisions documented)
2. Commit plan with levels (haiku/sonnet) and dependency graph
3. Exemplar commit first (handle_add), establishing all patterns
4. Subsequent commits reference the exemplar explicitly
5. Cross-reference analysis before each batch (contradictions, ambiguities,
   call-site audits)
6. Commit block format (PURPOSE/CONTEXT/IMPLEMENTATION/INVARIANTS/ERROR
   HANDLING/STRATEGIC PRINTS/VERIFICATION/COMMIT MESSAGE) before code
7. Code as artifact updates, not full-file rewrites (until structural changes)
8. Deviations documented in-flight with [ASSUME]/[GAP] markers
9. End-of-batch progress line
10. Hardening commits after feature-complete
11. Usage-driven review before phase advancement

### What the commit block format caught

The commit block format forced explicit answers to questions that otherwise
get deferred or forgotten:

- INVARIANTS: forced the LLM to state what must be true after the commit,
  which caught the "events not visible in list" entailment early (it was noted
  as a deferred gap, not discovered in production).
- ERROR HANDLING: forced enumeration of every failure mode THIS commit
  introduces. Prevented the pattern where error handling is "added later."
- STRATEGIC PRINTS: distinguished permanent UX output from debug logging.
  Without this field, confirmation messages would have been inconsistent.
- VERIFICATION: exact shell commands with expected output. The developer
  runs these before committing. This caught issues that unit tests would
  catch in a test-driven project -- but this project has no test framework,
  so verification commands are the substitute.

### What batching rules caught

The haiku+haiku+sonnet = sonnet assessment prevented under-scoping batches.
The "sum levels, check for opus" rule worked in practice: commits 09+10+11
batched safely (three creation commands, independent), 12+13 batched (sonnet
+ haiku, sequential dependency), 15+16 batched (two view commands, parallel).
No batch exceeded sonnet combined complexity.

The rule "if combined complexity requires opus-level judgment, do not batch"
was never triggered, which validates the commit plan's decomposition -- no
commit in phase 0 required opus-level judgment, confirming the spec was
detailed enough.

### What did NOT work well

The one-artifact-per-response limit created friction when the developer
requested two deliverables (README + feedback log, or tasks.py + tsk.sh
edits). The workaround (one as artifact, one inline) was acceptable but
not ideal. In future sessions, the developer should expect this constraint
and sequence requests accordingly, or batch related changes into one file.

The "verbalize your plan" instruction was effective but occasionally produced
responses that were too long before reaching code. The developer corrected
this once ("address quickly") which calibrated subsequent responses. The
lesson: the LLM should state the assessment/plan in 3-5 sentences, then
proceed to code, not write a full essay before producing output.

---

## 3. Interaction Patterns

### Instructions that produced good output

"Follow the handle_add exemplar" -- referencing a concrete, completed
implementation rather than abstract principles. Every subsequent creation
handler was faster and more consistent because of this anchor.

"Cross-reference all documents before producing code. Identify contradictions,
ambiguities, or decisions needed with verbalized suggested reconciliation or
tradeoff." -- This forced the LLM to audit before building, catching the
validate_priority second-caller assumption, the per-file ambiguity resolution,
and the updated-on-done/retire question before they became bugs.

"Do two things: [specific item 1] and [specific item 2]." -- Scoped requests
with explicit deliverables produced focused responses. Open-ended requests
("what do you think about X") produced longer exploratory responses, which
were useful for design but slower for implementation.

"Verbalize feedback" -- Explicitly asking the LLM to push back and offer
opinions produced the blueprint-applicability critique, the atomic-write
recommendation, and the auto-create rejection (USB shadow-dir hazard). Without
this instruction, the LLM would have applied the blueprint uncritically and
skipped the atomic-write suggestion.

"Quick gut check" -- Signaled that a short opinion was wanted, not a full
analysis. The flag-dict-placement question got a 4-sentence answer instead of
a 4-paragraph analysis. Calibrating response depth via the request phrasing
worked well.

### Instructions that needed adjustment

The initial prompt ("implement commits 09-17") was too broad for one response.
The LLM correctly assessed batching but the developer refined to "follow
workflow rhythm for batch 2 commits and from now on" -- adding the commit-block
format requirement mid-thread. In future sessions, state the format requirement
in the opening prompt, not as a correction.

"Remind me what you consider end-of-phase analysis to be" -- The LLM
interpreted this correctly as a recall request, but the phrasing invited a
longer answer than needed. "List the end-of-phase analysis checks" would have
been more direct.

### The correction that improved all subsequent output

"Main branch: Remember to follow workflow rhythm for the batch 2 commits and
from now on." -- This one sentence changed the output format for every
subsequent commit from code-only to full commit blocks. The lesson: format
expectations should be stated once, early, and the LLM should be told they
persist ("from now on"). The LLM does not reliably infer format expectations
from the presence of a workflow document; it must be told to use it.

---

## 4. Project-Specific Decisions

### Decisions made and accepted

| Decision | Chosen | Rejected | Why |
|----------|--------|----------|-----|
| Help dispatch | tsk help <command> | per-command --help flag | One implementation site vs N; no parse_flags pollution |
| Data-dir bootstrap | tsk init (explicit) | Auto-create on every run | USB shadow-dir hazard; typo'd path silently swallowed |
| Event type validation | Open set, no validation | Closed enum | Field-agnostic philosophy; solo tool flexibility |
| Retire vs done | Distinct status values | Reuse status=done | Semantic distinction for metrics and review |
| Atomic writes | Temp file + rename | Direct write_text | USB-sync crash safety; ~3 lines cost |
| Flag dict placement | Next to handler | Top-of-script config block | Single-consumer config co-locates; reduces jumps |
| Blueprint sections 5-6 | N/A for CLI | Apply as-is | Batch-processor patterns don't fit a dispatcher |
| Tags guard | No guard; document quoting | Runtime # detection heuristic | # is legitimate in summaries; false positives > benefit |
| Habit flag rejection | Accept fall-through (noise in summary) | Add rejection logic | No second caller; marginal benefit for solo tool |
| Symlinker mechanism | Copy/move into repo (planned) | Symlink into repo from outside | Symlinks dangle after USB sync; repo must be source of truth |
| Phase advance trigger | Signal-based (friction-driven) | Calendar-based (fixed interval) | Build when the need shows, not when time passes |

### Decisions deferred

- Event lifecycle (how to view, archive, or dismiss past events)
- Creation-command consolidation (one handler vs four)
- List output grouping (by type, hierarchical, by date)
- Recurrence logic for events
- Habit workflow (untested -- zero usage in 5 days)
- Help registry consolidation (three dicts vs one config structure)

---

## 5. Issues and Frictions

### ID reuse bug

Discovered via usage-log analysis, not user friction. generate_id checks only
active.txt; after done moves a record out, its suffix is reused. Confirmed by
log evidence: T0601a and T0601b each appear twice in done.txt. Fix: check all
files. Classification: phase-0 bugfix.

### Event invisibility

Events live in calendar.txt; list and done only read active.txt. Created events
became immediately invisible except on their date via today. Three friction
entries in 5 days. The spec's "events pass" design did not survive contact
with real use.

### Help frequency

help was 26% of all invocations (tied with list). Per-command help mitigated
the issue but the help-before-action pattern persists. The remaining friction:
error paths (no summary) don't print flags, forcing a separate help call.

### Sync discipline

The single-writer model assumes prompt commits. The "task not removed" friction
entry was caused by an uncommitted done-write on one machine, not a tool bug.
The tool cannot enforce commit discipline; the user must.

### One-artifact-per-response

A platform constraint, not a project issue, but it shaped the session. The
workaround (one artifact + one inline code block) was acceptable. Future
sessions should anticipate this and batch same-file changes.

---

## 6. Future Work

### Immediate (phase-0 bugfix, landed in next thread)

- ID reuse fix: generate_id checks all files.

### Medium-term (phase 1, informed by friction)

- Event visibility and lifecycle (urgent; 3 friction entries in 5 days)
- Creation-command consolidation (2 friction entries; reduces maintenance)
- List output grouping by type
- Error-on-missing-summary prints flags (help frequency reduction)
- tsk week (7-day view; natural home for upcoming events)

### Structural observations

The active.txt/calendar.txt split was designed for write-pattern separation
(bounded vs slow-growth) but created a read-pattern gap (events invisible to
list/done). Phase 1 must decide: either list reads multiple files, or events
move to active.txt (losing the write-pattern distinction), or a new view
command (tsk events) surfaces calendar.txt. The decision has architectural
implications for how "show me everything" works.

The today vs list tension (list used 4.5x more than today) suggests the
dashboard may not be the primary orientation tool the spec assumed. If list
is the reflex, today may need to become a richer list-with-context rather
than a separate structured view. Monitor in phase 1.

Habit workflow is entirely untested. The streak logic, daily-completion flow,
and today's habit section have zero real-world validation. This is not a
problem yet but means phase-1 habit features (if any) are building on
assumptions, not data.

---

## 7. Veteran Notes

### For the developer

Your instinct to consolidate the creation commands was correct and should have
been the original design. The spec split them into four handlers because each
entity "felt different" at design time, but in implementation the overlap was
obvious. The lesson: when multiple commands share the same mutation pattern
(read file, generate ID, build record, write file, confirm), they are one
command with a type parameter, not four commands. Future tools should start
consolidated and split only when the branches genuinely diverge.

The friction log was the most valuable artifact in the project. It caught the
event-invisibility gap, the help-registry maintenance issue, and the
consolidation desire -- all things that static analysis or spec review would
not have surfaced. Continue logging friction in real-time; it is more reliable
than retrospective analysis.

The USB-sync constraint shaped more decisions than any other environmental
factor: atomic writes, no auto-create, symlinks rejected, commit discipline
required. Future tools in this ecosystem should treat "USB-synced, single
writer" as a first-class design constraint stated in the spec's first section,
not discovered piecemeal during implementation.

### For the LLM (context recovery notes)

The developer's coding style is procedural, data-oriented, anti-abstraction.
The default is inline; extraction must be justified by call-site count.
Functions are not too long; they are too short (when extracted without
justification). Do not refactor for length. Do not extract for "readability"
or "separation of concerns" -- extract for reuse.

The developer values honest pushback. When the blueprint didn't fit, saying
"sections 5-6 are N/A for a CLI dispatcher" was correct and appreciated.
Applying it uncritically would have produced cargo-culted code and eroded
trust. Always explain WHY something doesn't apply rather than silently
omitting or silently applying.

The developer's prompt style shifts between modes: "quick gut check" means
3-5 sentences; "verbalize feedback" means full analysis with reasoning;
"do two things" means produce both deliverables, no preamble. Match the
response depth to the request phrasing. When uncertain, default to shorter.

The commit-block format (PURPOSE through COMMIT MESSAGE) must be used for
every commit once requested. It is not optional and does not need to be
re-requested. Producing code without the commit block is a format violation
the developer will correct.

Cross-reference analysis before producing code is mandatory, not optional.
The developer explicitly requested it once and expected it thereafter. It
catches contradictions, resolves ambiguities, and prevents assumptions from
becoming bugs. Skip it at the cost of rework.

The one-line progress footer (PROGRESS: [##/total] | commit_## level |
thread_X | phase_N | status) is expected after every implementation response.
It anchors the developer's sense of where the thread is. Omitting it makes
the thread feel unbounded.

---

## 8. Reusable Patterns (for future projects)

### Exemplar-first development

Identify one command/handler that exercises all recurring patterns (file I/O,
argument parsing, validation, confirmation output, error handling, logging).
Implement it first as a sonnet-level commit. Reference it explicitly in every
subsequent handler: "follow the handle_add exemplar." This reduces per-commit
decision load from sonnet to haiku for similar commands.

### Friction-log-driven phase advancement

Do not advance phases on a calendar. Advance when: (a) usage data exists for
the end-of-phase analysis, and (b) the user keeps reaching for commands that
don't exist. The friction log names the phase-1 priorities; the usage log
confirms them quantitatively. Together they prevent building features on
guesses.

### Cross-reference before code

Before producing code in a new thread, audit all input documents for
contradictions, deviations, and ambiguities. State findings. Resolve with
[ASSUME] or [GAP]. Then proceed. This takes 5-10 minutes of LLM time and
prevents hours of rework.

### Commit block as forcing function

The commit block format (INVARIANTS, ERROR HANDLING, STRATEGIC PRINTS,
VERIFICATION) forces answers to questions that are otherwise deferred. It is
not bureaucracy; it is a substitute for a test suite in a test-free project.
Use it for every commit regardless of level.

### Write-destination-first for multi-file mutations

When a mutation touches two files (e.g., done moves a record from active.txt
to done.txt), write the destination first. A crash after the first write
leaves the record in both files (recoverable) rather than in neither
(data loss).

### Single-source-of-truth for flag existence

Help/documentation should derive the list of available flags from the flag
definition dicts, not maintain a separate copy. This was achieved by having
handle_help read the *_FLAGS dicts at call time and only maintaining a
FIELD_HELP dict for human descriptions. The flag names have one source;
descriptions are the only addition.
