# Adversarial Hardening Toolkit - Artifacts, Tools, Compositions

A toolkit for critiquing, hardening, modifying, and documenting an
existing codebase. Distilled from a full pipeline run, then **decoupled**:
each tool is a self-contained prompt with a declared input contract and
defined behavior when optional inputs are absent. No tool references
another tool - only artifact types. The original pipeline survives as one
composition recipe among several.

Usage: paste this document (or just Part I plus the tools you need) into a
session along with the target code and whatever artifacts you have. Run
tools in any order their input contracts allow.

---

## Part I - Artifacts (the interfaces)

Tools communicate only through these typed artifacts. All are plain
structured text. IDs are the joins: every artifact references the
artifacts that motivated it by id, and ids are permanent across a
codebase's lifetime (they appear in code comments, tests, and decision
records).

**ConstraintSet**
```
constraint:
  id:         K<n>
  category:   layout | extraction | errors | naming | absence | mutation | output
  statement:  one normative sentence ("TRANSFORM functions may not print")
  evidence:   file/function where the code demonstrates it
  hardness:   rule (violations are bugs) | tendency (violations need justification)
```

**FindingSet** - findings plus their verdicts. A finding without a verdict
is an unfinished artifact; no tool emits one.
```
finding:
  id:          F<n>      # producer chooses a prefix scheme; ids never recycle
  lens:        the perspective or analysis lens that produced it
  statement:   what is wrong / assumed / implied / unmeasured
  location:    file + function/line
  severity:    will-crash | silent-wrong | annoying | cosmetic   # where applicable
  reproduction: command or ó5-line snippet; REQUIRED for will-crash and
               silent-wrong; absent reproduction => finding marked UNVERIFIED
  data_named:  the data concerned + its real or assumed distribution   # pair-2 only
  measurement: the observation that would confirm/refute                # pair-2 only
  constraint_refs: [K..]   # only if a ConstraintSet was available
verdict:
  finding_id:  F<n>
  disposition: correct | context-wrong | tension | falsified
  rationale:   1-3 sentences
```

**FeatureSpec**
```
feature:
  id:          FS<n>
  behavior:    what the user can do afterwards (observable)
  acceptance:  pass/fail criteria
  non_goals:   explicit exclusions
  literal_patch: optional; honored only if it lands on the current tree
               unmodified, otherwise illustrative
```

**Plan**
```
commit:
  id:          C<n>     # permanent
  motivation:  [F.. | FS.. | K..]
  description: one sentence
  tier:        haiku (single-site, mechanically verifiable)
             | sonnet (one coherent function OR one uniform pattern)
             | opus | fable (MUST be decomposed into haiku/sonnet, or parked)
  decomposed_into: [..]
  depends_on:  [C..]    # real (compile/semantic) dependencies only
plan:
  batches:     ordered groups of commit ids + one-line theme
               (= topological sort of depends_on, grouped by theme)
  exclusion_list: [{id, reason}]   # MANDATORY; context-wrong and tension
               verdicts land here by default - silence is not a decision
  environment_checklist:
    - inputs verified on disk + checksummed (missing => stop-and-ask)
    - dependencies declared live | stubbed; "stubbed" is a standing caveat
      every BatchSummary must restate
    - the live-verification step named for any external-contract change
  critical_path: the dependency chain that orders everything else
```

**BatchSummary** - written in ADR form so documentation is assembly, never
archaeology.
```
batch_summary:
  batch:       number + theme
  commits:     [C..] landed, one observable effect each
  adrs:        every non-mechanical decision made during execution:
               {title, context, decision, alternatives, consequences}
  deviations:  every departure from plan or literal spec:
               {what, why, one-line revert path}    # may be "none", never omitted
  tests_added: cases appended to the TestSuite, named by commit id
  caveats:     standing caveats restated verbatim
```

**TestSuite** - one persistent companion file, created at first execution
and appended to forever. Each test names its commit id. Regression = run
the file. Throwaway verification is forbidden for anything later work
could break.

**CompanionArtifact** - anything generated besides the code (prompt packs,
specs, skeletons, the TestSuite itself).
```
companion: {path, duplicates: <what code knowledge it copies>,
            sync_trigger: <the code change that requires updating it>}
```

**Spec** - purpose/scope; data shapes with concrete examples; the
ConstraintSet (amended, with the commit that amended it); ADRs; extension
guide; debts register (= exclusion list + falsified findings + standing
caveats + arbitrary constants labeled arbitrary); companion sync-trigger
table.

**VerdictDelta**
```
delta_row: {original_finding_or_NONE, original_verdict_or_NONE,
            new_finding_or_NONE, new_verdict, drift_note}
plus: telemetry requirements extracted from pair-2 findings, if any.
Small delta = certification; substantial delta = a ready-made FindingSet
for future work.
```

### Lens pair registry (parameter values for T2)

Pairs critique different layers and should be **rotated** across reviews
of the same codebase - a closing review run by the opening review's
critics certifies against the answer key.

**Pair 1 - code shape.** Default for refactoring/convention-heavy work.
- *Jonathan Blow - self-inflicted complexity.* Complexity is chosen;
  abstractions must pay for themselves in reduced cognitive load;
  indirection that obscures what the code does is a defect even when it is
  "good practice." Asks: where is the concrete alternative faster to
  understand? Where does work maintain a pattern rather than solve the
  problem? Which helper would you delete on a fresh read?
- *Casey Muratori - semantic compression and machine reality.* Know what
  the computer actually does; eliminate unnecessary work; maximum semantic
  weight per line; compress only after concrete duplicates exist. Asks:
  which allocations, copies, re-traversals serve only a stylistic
  principle? Which convention charges a complexity tax that pays nothing
  at this scale? Which "clean separation" makes the data take a round
  trip?

**Pair 2 - data and runtime.** Default for performance/feature work and
whenever real usage data exists.
- *Mike Acton - data-oriented design.* Software transforms data; the
  data's actual shape and statistics ARE the problem; "different data is a
  different problem." Asks: what is the actual data - sizes,
  cardinalities, per-case frequencies? Where do structures mismatch the
  transforms run over them? What does the common case pay for the rare
  case's generality? Discipline: every finding names its data and
  distribution; unknown distribution converts the finding into a telemetry
  requirement, never a guess.
- *John Carmack - empirical engineering.* Truth is what runs; beliefs
  about behavior are worthless untraced; abstraction's dominant cost is
  paid while debugging; execution-order visibility justifies linear inline
  code. Asks: what does the program actually do at runtime - has anyone
  watched? Where would a bug hide; how long to a deterministic repro? Can
  every failure be reproduced from the artifacts the program leaves
  behind? What is believed but never measured? Discipline: every finding
  names the measurement that would confirm or refute it - each finding
  doubles as an instrumentation request.

---

## Part II - Tools

Each tool is a standalone prompt. **Inputs** are artifacts attached
alongside the code; *(optional)* inputs have a defined fallback so the
tool runs without them. **Output** names the artifact emitted. No tool
mentions any other tool.

---

### T1 CONSTRAIN - describe what IS

**Inputs:** code. **Output:** ConstraintSet.

> Analyze the structure, style, and conventions of the attached code.
> State what you observe as rules a future editor must follow. Cover:
> (1) section/module layout - what belongs where, what is forbidden where;
> (2) the function-extraction rule you infer - when logic gets its own
> function vs. stays inline, one example of each from the code; (3) how
> cross-cutting variation (providers, backends, formats) is handled and
> what would violate the mechanism; (4) the error-handling pattern - where
> errors are caught, where they propagate, the stdout/stderr convention;
> (5) naming conventions; (6) what the code deliberately does NOT do -
> abstractions a typical developer would add that are conspicuously
> absent, with your inference of why.
> Output numbered constraints (K1, K2, ...), each with the normative
> statement, the evidence in code, and rule-vs-tendency hardness. Describe
> what IS; do not suggest improvements.

---

### T2 REVIEW - adversarial critique through a named lens pair

**Inputs:** code; lens pair (pick from the registry or supply your own
two opposed stances). *(optional)* ConstraintSet - if absent, skip
constraint tagging and note its absence. *(optional)* prior FindingSet -
if present, also emit a VerdictDelta against it.
**Output:** FindingSet (+ VerdictDelta when a prior FindingSet was given).

> Review the attached code through two opposed perspectives:
> Perspective 1: {{LENS_A}} - [paste stance]. Perspective 2: {{LENS_B}} -
> [paste stance].
> For each perspective, state 3-5 concrete findings with file and
> function/line references. If a constraint set is attached, tag each
> finding with the constraint ids it tests or violates. If the lenses
> carry disciplines (e.g. name-the-data, name-the-measurement), honor them
> per finding; a finding whose data distribution is unknown converts into
> a telemetry requirement.
> Then - mandatory - issue a verdict for EVERY finding: (a) correct, the
> code should change; (b) perspective-valid but wrong for this context,
> with the reason; (c) a genuine tension worth recording. A finding
> without a verdict is unfinished. Note any finding where both lenses
> converge - convergence is presumptive priority.
> If a prior finding set is attached, close with a verdict delta: per
> original finding - fixed, unchanged, or drifted; plus any findings that
> are new. Small delta certifies; substantial delta is future work in
> ready form.

---

### T3 FAILMAP - six-lens hardening analysis

**Inputs:** code; a usage horizon (e.g. "one year of daily varied use").
*(optional)* ConstraintSet - if absent, skip constraint refs.
**Output:** FindingSet.

> Analyze the attached code for failure modes. Findings only - fix
> nothing; dispositions come at the end.
> **Assumptions**: what the code assumes about environment, inputs, and
> dependencies that is never checked. **Presuppositions**: what must be
> true for correctness that is never verified. **Entailments**: what the
> implementation logically implies that was probably not intended.
> **Cognitive decay**: inconsistencies between the earliest- and
> latest-written code - degraded error handling, contradictory mechanisms,
> cut corners. **Usage prediction over {{HORIZON}}**: the top five pain
> points in order of likelihood. **Adversarial-by-accident inputs**:
> ordinary user mistakes producing confusing behavior.
> Per finding: id, statement, location, severity (will-crash /
> silent-wrong-behavior / annoying / cosmetic), one-line fix if obvious,
> constraint refs if a constraint set is attached. For every will-crash
> and silent-wrong finding include a minimal reproduction (a command or
> ó5-line snippet); if you cannot construct one, mark the finding
> UNVERIFIED and state what would falsify it. Close with a verdict table:
> every finding dispositioned correct / context-wrong / tension /
> falsified.

---

### T4 PLAN - classify, decompose, sort, batch

**Inputs:** code; one or more FindingSets and/or FeatureSpecs.
*(optional)* ConstraintSet - if absent, derive the minimal conventions
needed to phrase commits safely and say you did. If any supplied findings
lack verdicts, your FIRST step is to assign provisional verdicts and flag
them for confirmation - never schedule an unverdicted finding.
**Output:** Plan.

> Produce a commit-by-commit implementation plan from the attached
> findings and/or feature specs.
> 1. Enumerate commits; each cites its motivating ids and receives a
>    permanent id that will appear in code comments, tests, and decision
>    records. Schedule only findings dispositioned `correct`.
> 2. Classify each commit: haiku / sonnet / opus / fable (definitions in
>    the artifact contract).
> 3. Decompose every opus and fable into haiku/sonnet pieces, or park it
>    in the exclusion list with reasoning. Nothing above sonnet is
>    scheduled as a unit.
> 4. Topologically sort by real dependencies; state why each dependency
>    is real, and note where ordering avoids writing code twice.
> 5. Batch into themed, independently reviewable groups; name the
>    critical path.
> 6. Mandatory sections: the exclusion list (every unscheduled id, with
>    reason - context-wrong and tension verdicts default here) and the
>    environment checklist (inputs on disk + checksummed; live vs. stubbed
>    dependencies; named live-verification step for external-contract
>    changes). Where a feature spec's literal patch would land after
>    refactoring commits, restate it as behavior + acceptance criteria and
>    mark the code illustrative.
> Present the plan and stop. Execution requires an explicit go (or an
> explicit waiver: "the exclusion list is the contract").

---

### T5 EXECUTE - land one batch

**Inputs:** code; Plan; the batch number; the go/waiver decision.
*(optional)* ConstraintSet - if absent, honor T-style conventions inferred
from the code and flag the gap. *(optional)* TestSuite - if absent, CREATE
it as your first deliverable.
**Output:** modified code; TestSuite (appended); BatchSummary; cumulative
diff.

> Execute batch {{N}} of the attached plan.
> - Run the environment checklist first; a missing or unverifiable input
>   is stop-and-ask, never transcribe-and-proceed.
> - If no persistent test file is attached, create one; either way, append
>   cases named by commit id and finish by running the whole suite. No
>   throwaway verification for anything later work could break.
> - Implement intent. Flag EVERY deviation from the plan or a literal
>   spec, with rationale and a one-line revert path.
> - If a commit's tier was misclassified or a missed dependency surfaces,
>   STOP and return the amended plan for a new go decision - do not push
>   through.
> - Tag non-obvious changes with their commit id, in the codebase's own
>   comment style, honoring every attached constraint.
> - Close with a batch summary in ADR form: commits landed (one observable
>   effect each); an ADR for every non-mechanical decision made during
>   execution; the deviation list (may be "none", never omitted); tests
>   added; standing caveats restated verbatim.

---

### T6 SPEC - assemble the maintenance document

**Inputs:** code. *(optional, each)* ConstraintSet, BatchSummaries, Plan
(for the exclusion list), FindingSets (for falsified findings),
CompanionArtifact list. Fallback: for any absent input, reconstruct that
section from the code and conversation and MARK IT RECONSTRUCTED - the
reader must know which decisions are records and which are archaeology.
**Output:** Spec.

> Assemble a self-contained maintenance specification for the attached
> code, for a reader who has seen none of its history: purpose and scope
> (one paragraph); every recurring data shape with one concrete example;
> coding guidelines as rules for a future editor (from the constraint set
> if attached); architecture decision records - concatenated from attached
> batch summaries and any pre-existing decisions, recording reversals as
> reversals; an extension guide for the three most likely future changes;
> a debts register combining the exclusion list, falsified findings,
> standing caveats, and arbitrary constants labeled arbitrary; and a
> companion-artifact table with each artifact's declared sync trigger.
> Describe what IS. Where a decision was arbitrary, say so; where
> principled, cite the principle. Mark any section reconstructed from
> inference rather than records.

---

### T7 GATE - the human's tool

Not a prompt to the model; a message format for the human. Kept in the
catalog so its absence is a choice, not an accident.

> Reviewed. Strike: [ids]. Add: [described changes]. Everything else
> approved - execute batch 1.
> - or -
> Gate waived; the exclusion list is the contract. Execute batch 1.

---

## Part III - Compositions

The tools compose through their artifacts. Recipes, from smallest to
largest:

**Quick audit** (one session, no changes):
`T3(code)`  FindingSet with verdicts and reproductions. Done.

**Opinionated review** (no changes):
`T1(code)`  `T2(code, pair-of-choice, ConstraintSet)`.

**Document an undocumented tool**:
`T1(code)`  `T6(code, ConstraintSet)` - the spec marks its ADRs
reconstructed, which is honest and still useful.

**Measurement session** (when usage data exists):
`T2(code, pair-2)`  telemetry requirements  `T4`  `T5` landing only
instrumentation commits. Feeds the next composition.

**Full pipeline** (the original workflow, now as a recipe):
```
T1 ÄÄConstraintSetÄÄÂÄÄ T2(pair A) ÄÄ¿
                    ³                 ÃÄ FindingSets Ä T4 ÄPlanÄ T7 GATE
                    ÀÄÄ T3 ÄÄÄÄÄÄÄÄÄÄÙ                              ³
        FeatureSpecs ÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄ T4           
                                                          ÚÄ T5 batch i Ä¿
                                                          ³   (summaries, ³
                                                          ³    tests)     ³
                                                          ÀÄÄÄÄÄÄÄÄÄÄÄÄÄÄÙ
                                                                  ³ all batches done
                                                                  
                                T6(everything) ÄSpecÄ   T2(pair B, prior FindingSet)
                                                                  ³
                                                            VerdictDelta
                                                       (cert, or next session's input)
```

**Re-entry** (a later session on the same codebase): start from the Spec -
it carries the ConstraintSet and debts register - then `T2(pair not used
last time)` or `T3`, then `T4` onward. Permanent ids make old findings and
commits citable.

### Invariants (hold in every composition)

1. Nothing above sonnet is ever executed as a unit.
2. Every analysis tool ends in dispositions; findings without verdicts do
   not cross tool boundaries.
3. The id chain Finding  Verdict  Commit  code comment  test  ADR is
   walkable in both directions.
4. Execution stops on tier explosions and missed dependencies; plans are
   amended through the gate, not steamrolled.
5. The gate is exercised or explicitly waived - never silently skipped.
6. Reviews of the same codebase rotate lens pairs.
7. Every companion artifact declares its sync trigger at creation.

---

## Part IV - Rationale ledger

Every rule above traces to a failure observed in the source run. If a rule's
failure never recurs, the rule is a deletion candidate - by this toolkit's
own logic.

| Rule | Failure it corrects |
|---|---|
| T1 exists and runs first in the full pipeline | Conventions were articulated after six batches of edits; critiques lacked a bug-vs-convention rubric |
| Mandatory verdicts (invariant 2) | An adversarial review without dispositions degrades into a refactoring to-do list; verdicts are what kept a debatable abstraction alive and surfaced the one convergent finding as top priority |
| Reproductions for severe findings (T3) | One claimed self-referential failure survived three batches before a test falsified it; a reproduction would have killed it at analysis time |
| Behavior-form feature specs (T4 rule 6) | A literal patch referenced a function the plan deleted before the feature landed; only ordering discipline saved it |
| Persistent TestSuite (T5) | Regression was re-typed throwaway heredocs each batch - it held by luck and context, not process |
| Environment checklist + checksums (T4/T5) | All diffs in the source run were against a reconstructed baseline because the uploaded file was absent from disk; the stubbed-dependency status was a manually repeated disclaimer |
| ADR-form batch summaries (T5) and assembly-not-archaeology (T6) | The final spec required reconstructing fifteen decisions from memory; an auth reversal and a direction-inverted convergence were nearly mis-recorded |
| Explicit gate or explicit waiver (T7, invariant 5) | The designed human filtering step was silently bypassed; the exclusion list became the contract without anyone saying so |
| Companion sync triggers (invariant 7) | Generated artifacts duplicated code schemas and would silently rot when the schema moved |
| Closing review + VerdictDelta (T2's optional prior-FindingSet input) | The code grew ~50% under modification and the central function absorbed six concerns; nobody re-asked the critics whether the result still passed |
| Lens pair registry + rotation (invariant 6) | The source run had only code-shape critics; data-shape and runtime-truth questions went unasked, and the telemetry that would answer them was added late and incidentally |
| Decoupling itself: input contracts + fallbacks (this revision) | The v1 prompts referenced each other by stage name ("the verdicted findings from S1 and S2"), so no prompt ran standalone, partial use was impossible, and the pipeline was the only composition |

Operating principle, stated once: **every tool ends in a decision
artifact - verdicts, tiers, exclusions, deviations, deltas - never in
open-ended analysis; and the artifacts that matter most over time
(constraints, tests, decision records) are produced earliest and accrued
continuously, never reconstructed at the end.**
