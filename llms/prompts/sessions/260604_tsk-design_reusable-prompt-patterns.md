# Reusable Prompt Instructions

Extracted from tsk phase-0 session. Organized by workflow position.
Paste relevant sections into future thread openings.

---

## 1. Thread Setup

### 1.1 State format expectations once, early

> Follow the commit block format (PURPOSE / CONTEXT / IMPLEMENTATION /
> INVARIANTS / ERROR HANDLING / STRATEGIC PRINTS / VERIFICATION / COMMIT
> MESSAGE) for every commit from now on. This persists for the entire thread.

WHY: The LLM does not reliably infer format expectations from the presence of
a workflow document. Stating "from now on" prevents re-requesting per commit.
Discovered when the first batch produced code without commit blocks and required
correction.

### 1.2 Name the exemplar explicitly

> Commit 08 (handle_add) is the exemplar mutation command. Follow its patterns
> for argument parsing, error handling, confirmation output, and file I/O in
> all subsequent creation handlers.

WHY: "Follow established patterns" is too vague. Naming the specific commit
and the specific patterns to carry forward reduces per-commit decision load
from sonnet to haiku for similar commands.

### 1.3 Require cross-reference before code

> Cross-reference all documents before producing code. Identify contradictions,
> ambiguities, or decisions needed with verbalized suggested reconciliation.
> Then determine if the commits can be batched and proceed.

WHY: Without this, the LLM starts coding from the most recent document and
misses conflicts with earlier ones. The cross-reference caught the
validate_priority second-caller assumption, the updated-on-done/retire
ambiguity, and the per-file edit ambiguity before they became bugs.

### 1.4 Declare thread scope and inputs

> This is an implementation thread for [project]. Scope: commits [N-M]
> (phase X remaining). [Paste: spec, commit plan, workflow docs, current
> code, handoff from prior thread if any.]

WHY: Unbounded threads degrade. Stating scope sets expectations for when to
stop and produce a handoff vs when to keep building.

---

## 2. During Implementation

### 2.1 Batch assessment before producing code

> Assess whether commits [N, M, K] can be batched. State the combined level,
> dependencies, and whether batching is safe. Then produce the batch.

WHY: Prevents under-scoping (batching commits that need separate treatment)
and over-splitting (producing three responses for three haiku commits). The
assessment itself is one line; it forces the LLM to check before proceeding.

### 2.2 Signal response depth with phrasing

These phrases were tested and produced calibrated responses:

| Phrase | Expected depth |
|--------|---------------|
| "Quick gut check" | 3-5 sentences, opinion only, no analysis |
| "Verbalize feedback" | Full analysis with reasoning and alternatives |
| "Do [N] things" | Produce all deliverables, minimal preamble |
| "Address quickly" | Short treatment, then move to the main task |
| "What do you think?" | Explore tradeoffs, present options, recommend one |
| "Remind me" | Recall from provided documents, concise |

WHY: The LLM defaults to thorough. Without calibration signals, simple
questions get essay-length answers. These phrases were each used once and
immediately produced the right depth.

### 2.3 Request pushback explicitly

> Verbalize feedback. Feel free to peruse [X] and then suggest your own
> analysis and observations.

WHY: Without explicit invitation, the LLM applies templates uncritically
rather than flagging when something doesn't fit. The blueprint-applicability
critique (sections 5-6 are N/A for a CLI) only happened because pushback was
invited. The atomic-write recommendation was unsolicited but within the spirit
of "verbalize feedback." Make the invitation once per thread; it persists.

### 2.4 End every implementation response with a progress line

> End every implementation response with:
> PROGRESS: [##/total] | commit_## level | thread_X | phase_N | status

WHY: Anchors the developer's sense of position in the thread. Without it,
long threads feel unbounded. The format is compact enough to scan without
reading.

---

## 3. Design and Consultation

### 3.1 Present decisions as chosen/rejected pairs

> For each design question, state what was chosen, what was rejected, and why.
> Rejected alternatives must appear in the output, not only in reasoning.

WHY: Recording rejected alternatives prevents re-exploration of dead paths in
future threads. It also makes the decision auditable: a future reader (or LLM)
can assess whether the rejection reasoning still holds.

### 3.2 Use [ASSUME] and [GAP] markers for all ambiguity

> Every interpretation, default, or filled gap must be marked. No silent fills.
> [ASSUME: what - why] continues processing. [GAP: what's missing] halts.

WHY: Silent fills are the primary source of bugs that survive code review.
The LLM's tendency is to pick the most plausible interpretation and proceed
without marking it. The marker forces visibility. In this session, five
[ASSUME]s were tracked; all five were resolved by end-of-phase (three
confirmed, two accepted-and-documented).

### 3.3 Connect environment constraints to implementation choices proactively

> [No explicit instruction needed -- this is a note for the LLM.]
> When you know the deployment environment (USB-synced, single-writer,
> no cloud, specific filesystem), proactively connect those constraints to
> implementation choices without being asked. The atomic-write recommendation
> and the auto-create rejection both came from remembering "USB-synced" from
> the spec and applying it to a later decision.

WHY: The developer states the environment once in the spec. They should not
need to re-invoke it at every decision point. The LLM should carry it forward
as a standing constraint.

---

## 4. Code Review and Hardening

### 4.1 Hardening as a distinct phase, not an afterthought

> After feature-complete, do a hardening pass: preflight checks, fail-fast
> with distinct exit codes, atomic writes, input validation for untested
> paths. These are separate commits with their own commit blocks.

WHY: Hardening interleaved with feature commits gets skipped under schedule
pressure. A dedicated pass after features are done ensures it happens and
keeps feature commits clean.

### 4.2 The checklist before committing

> Before producing code, verify: no single-caller function extractions,
> no functions defined solely for higher-order function arguments, variable
> names use domain vocabulary, function length is not a splitting criterion.

WHY: These are the four most common style violations the LLM produces under
its own defaults. Stating them as a pre-flight check in the prompt prevents
the correction cycle.

---

## 5. Documentation and Handoff

### 5.1 Handoff is an output of analysis, not a prerequisite

> At phase boundaries (implementation -> refinement/analysis), do NOT
> pre-write a formal handoff. Paste the raw artifacts (code, spec, docs,
> logs) into the new thread. The handoff document is an output of the
> end-of-phase analysis, written against the reviewed code.

WHY: A handoff written before analysis risks rework (the analysis may surface
fixes that change the handoff). At implementation-to-implementation boundaries
(e.g., commits 01-08 to 09-17), a handoff IS useful because the next thread
needs digested patterns. At implementation-to-analysis boundaries, the analysis
needs the raw material.

### 5.2 Friction log as primary phase-advance signal

> Maintain a friction log during use. Each entry: timestamp, project tag,
> observation. Do not filter or prioritize during capture -- that happens
> during review. Advance to the next phase when the friction log names
> commands you keep reaching for, not when a calendar interval passes.

WHY: The friction log surfaced the event-invisibility gap, the consolidation
desire, and the help-registry maintenance issue -- none of which were
predictable from the spec. Static analysis and spec review would not have
caught them. The log is more reliable than retrospective recall because it
captures irritation in the moment.

### 5.3 Usage log as quantitative confirmation

> Paste the usage log into the review/analysis thread. Analyze command
> frequency, error rates, and usage patterns before planning the next phase.

WHY: The friction log says what hurts; the usage log says how much. "help is
26% of all invocations" is a stronger argument for help refinement than "I
feel like I use help a lot." The ID-reuse bug was discovered purely from
usage-log sequence analysis, not from friction or user report.

---

## 6. Meta-Instructions (for the LLM)

### 6.1 Match response depth to request phrasing

Default to shorter. A factual question gets a factual answer, not an essay.
An implementation request gets code with a commit block, not a design
discussion. A design question gets tradeoff analysis. When uncertain about
depth, produce the shorter version and let the developer ask for more.

### 6.2 Do not refactor for length

The developer's style permits long functions that perform one irreducible
top-to-bottom sequence. A 200-line handler that reads, filters, computes,
and prints is correct if it has one caller and one control path. Do not split
it into helpers. Do not suggest splitting it. Length is not a code smell in
this codebase; premature extraction is.

### 6.3 Pushback is expected and valued

When a template, pattern, or instruction does not fit the current context,
say so and explain why. "Sections 5-6 are N/A for a CLI dispatcher because
[reason]" is better output than silently applying or silently omitting them.
The developer explicitly values honest pushback over compliant application.

### 6.4 Carry environment constraints forward

"USB-synced, single-writer, no cloud, no git inside the tool" is a standing
constraint that applies to every decision. Do not wait to be reminded. Apply
it proactively when it intersects with a design or implementation choice.

### 6.5 Track [ASSUME] markers across the thread

When an [ASSUME] is made, note when and where it should be resolved. When the
resolution point arrives (the second caller materializes, the commit that
tests the assumption lands), state explicitly: "[ASSUME] from commit N
resolved: [outcome]." Do not let assumptions accumulate unresolved across
a thread.

### 6.6 One-artifact-per-response workaround

When the developer requests two file deliverables, produce the larger or
more-iterable one as the artifact and deliver the smaller one as an inline
code block with clear paste instructions. State the constraint briefly so the
developer understands why. Do not apologize or over-explain.
