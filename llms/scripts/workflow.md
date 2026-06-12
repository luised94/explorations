# Adversarial Hardening Workflow - Data Model and Prompt Pack

A reusable pipeline for taking an existing codebase through critique,
failure analysis, planned modification, and documented closure. Distilled
from a full execution of the workflow; the refinements below correct the
frictions observed in that run. Self-contained: paste this document plus
the target code into a session and run the prompts in order.

---

## Part I - Data model

### 1. The pipeline as a decision graph

Nodes are stages. Every stage consumes typed artifacts and emits typed
artifacts. Edges carry artifacts; gates are edges that require a human
decision before traversal. No stage may begin until its input artifacts
exist.

```
                ÚÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄÄ¿
                ³                                                    ³
                                                                    ³
  [S0 CONSTRAINTS] ÄÄConstraintSetÄÄ [S1 ADVERSARIAL REVIEW]        ³
                ³                          ³                         ³
                ³                     VerdictedFindings              ³
                ³                                                   ³
                ÀÄÄConstraintSetÄÄ [S2 HARDENING ANALYSIS]          ³
                                           ³                         ³
                                  VerdictedFindings (merged)         ³
                                                                    ³
                  FeatureSpecs ÄÄÄÄÄÄ [S3 PLAN]                     ³
                                           ³                         ³
                                    Plan + ExclusionList             ³
                                                                    ³
                                   ((G1 HUMAN GATE))  Ä strike/add/approve
                                           ³
                                     ApprovedPlan
                                           
                              ÚÄÄ [S4 EXECUTE BATCH i] ÄÄ¿
                              ³            ³              ³
                   next batch ³   BatchSummary(ADR-form)  ³ failure that
                              ³   TestSuite (appended)    ³ invalidates plan
                              ³   Diff (cumulative)       ³
                              ÀÄÄÄÄÄÄÄÄÄÄÄÄÙ              
                                           ³      back to [S3] (replan)
                                  all batches done
                                           
                                     [S5 CLOSE]
                                       ³     ³
                                  Spec(ADRs  ÀÄ re-run [S1] on final code
                                  assembled)        ³   (with the OTHER lens pair)
                                           VerdictDelta ÄÄ next session's S2 backlog
```

The loop edge from S5 back to S1 is the closure refinement: the finished
artifact gets the same adversarial treatment the original did, and the
*difference* in verdicts is the certification (or the next backlog).

### 2. Entity schemas

All artifacts are plain structured text (markdown tables / JSON-ish
records). IDs are the joins - every entity downstream references the
entity that motivated it.

**ConstraintSet** (S0 output)
```
constraint:
  id:            K<n>
  category:      layout | extraction | errors | naming | absence | mutation | output
  statement:     one normative sentence ("TRANSFORM functions may not print")
  evidence:      file/function where the code demonstrates it
  hardness:      rule (violations are bugs) | tendency (violations need justification)
```

**Finding** (S1, S2 output)
```
finding:
  id:            F<n>            # S1 uses lens-prefixed ids (B1.x, M2.x); S2 uses A/P/E/D/U/X
  stage:         S1 | S2
  lens:          (S1) named-critic | (S2) assumption | presupposition | entailment |
                 decay | usage-prediction | adversarial-input
  statement:     what is wrong / assumed / implied
  location:      file + function/line
  severity:      will-crash | silent-wrong | annoying | cosmetic       # S2 only
  reproduction:  command or ó5-line snippet                            # REQUIRED for
                                                                       # will-crash and
                                                                       # silent-wrong
  constraint_refs: [K..]         # which constraints it tests or violates
```

**Verdict** (attached to every Finding before it leaves its stage - no
finding crosses a stage boundary without one)
```
verdict:
  finding_id:    F<n>
  disposition:   correct (code must change)
               | context-wrong (valid lens, wrong for this codebase - record why)
               | tension (neither side clearly right - record both sides)
               | falsified (reproduction failed - keep as a record, never schedule)
  rationale:     1-3 sentences
```

**FeatureSpec** (human input to S3)
```
feature:
  id:            FS<n>
  behavior:      what the user can do afterwards (observable, testable)
  acceptance:    bullet list of pass/fail criteria
  non_goals:     explicit exclusions
  literal_patch: optional - only honored if the feature lands in batch 1,
                 otherwise treated as illustrative (the plan notes this)
```

**Commit** (S3 output)
```
commit:
  id:            C<n>           # ids are permanent; they appear in code comments,
                                # tests, batch summaries, and ADRs
  motivation:    [F.. | FS.. | K..]
  description:   one sentence of intended change
  tier:          haiku  (single site, mechanically verifiable)
               | sonnet (one coherent function OR one pattern applied uniformly)
               | opus   (multiple subsystems or semantic change)  -> MUST decompose
               | fable  (architecture / external contract change) -> MUST decompose
                                                                     or be parked
  decomposed_into: [C<n>a, C<n>b, ...]   # required for opus/fable
  depends_on:    [C..]          # real dependencies only (compile/semantic),
                                # not preferences
```

**Plan** (S3 output)
```
plan:
  batches:        ordered list; each batch = [commit ids] + one-line theme
                  ordering = topological sort of depends_on, then grouped by theme
  exclusion_list: [{commit-or-finding id, reason}]   # MANDATORY section, may be empty
                  # "deliberately not scheduled" is a decision artifact, not silence
  environment_checklist:
    - input files verified on disk + checksummed (missing upload = stop and ask,
      never transcribe-and-proceed)
    - dependency availability noted (live | stubbed); stubbed = standing caveat
      repeated in EVERY batch summary
    - live-verification step named for any change touching an external contract
  critical_path:  the dependency chain that orders everything else
```

**BatchSummary** (S4 output, one per batch - written in ADR form so S5 is
assembly, not archaeology)
```
batch_summary:
  batch:         number + theme
  commits:       [C..] landed, each with one observable effect
  adrs:          for every non-mechanical decision made DURING execution:
                   {title, context, decision, alternatives, consequences}
  deviations:    every departure from the approved plan or a literal spec:
                   {what, why, one-line revert path}      # MANDATORY, may be "none"
  tests_added:   names of cases appended to the persistent suite
  caveats:       standing caveats restated (e.g. "no live API call has run")
```

**TestSuite** - a single persistent companion file created in batch 1 and
APPENDED to by every subsequent batch. Each test names its commit id.
Regression = run the file. Throwaway verification heredocs are forbidden
for anything a later batch could break.

**CompanionArtifact** (anything generated besides the code: prompt packs,
specs, skeletons, this test suite)
```
companion:
  path:          file
  duplicates:    what knowledge it copies from the code (schema, conventions, behavior)
  sync_trigger:  the code change that REQUIRES updating this artifact
                 # declared at creation time, recorded in the spec
```

**Spec** (S5 output) - purpose/scope, data shapes with concrete examples,
constraints (from S0, updated), ADRs (concatenated from BatchSummaries +
any pre-existing decisions), extension guide, debts register (= exclusion
list + falsified findings + standing caveats), companion sync-trigger
table.

**VerdictDelta** (S5 output) - S1 re-run on the final code with the lens
pair NOT used at S1; table of {original verdict, new verdict, drift note},
plus any pair-2 telemetry requirements. Small drift = certification.
Substantial drift = the seed backlog for the next session, already in
Finding format.

### 3. Gates and invariants

- **G1 (after S3)**: the human strikes/adds/approves commits. If the gate
  is waived, say so explicitly - the exclusion list then becomes the
  contract by default. Don't leave it ambiguous.
- **Replan edge**: if execution discovers a dependency the plan missed or
  a tier misclassification (a "sonnet" that is really opus), execution
  STOPS and the plan is amended through G1 again. Tier explosions are plan
  bugs, not things to push through.
- **Invariant: nothing above sonnet is ever executed as a unit.**
- **Invariant: every code comment for a non-obvious change carries its
  commit id.** The chain Finding  Verdict  Commit  code comment  test
   ADR must be walkable in both directions.
- **Invariant: analysis stages emit dispositions, not just observations.**
  A stage that ends at findings has not finished.

---

## Part II - The prompts

Placeholders: `{{CODE}}` the target source, `{{TOOL_DESC}}` one sentence of
what it is and who it's for, `{{LENS_A}}/{{LENS_B}}` named critical
perspectives, `{{HORIZON}}` the usage-prediction window.

### Prompt S0 - Constraints (run FIRST, before any critique)

> Before any review or change, analyze the structure, style, and
> conventions of the attached code. State what you observe as rules a
> future editor must follow. Cover: (1) section/module layout - what
> belongs where, what is forbidden where; (2) the function-extraction rule
> you infer - when logic gets its own function vs. stays inline, with one
> example of each from the code; (3) how cross-cutting variation (e.g.
> providers, backends, formats) is handled, and what would violate the
> mechanism; (4) the error-handling pattern - where errors are caught,
> where they propagate, the stdout/stderr convention; (5) naming
> conventions for functions, variables, constants; (6) what the code
> deliberately does NOT do - abstractions a typical developer would add
> that are conspicuously absent, with your inference of why.
>
> Output each observation as a numbered constraint (K1, K2, ...) with: the
> normative statement, the evidence in the code, and whether it is a hard
> rule or a tendency. Describe what IS - do not suggest improvements. This
> constraint set is the rubric every later stage checks against.

### Lens pair registry (for S1 and S5)

The adversarial prompt (S1) is parameterized by a lens *pair*. Two pairs
are registered; they critique different layers and are deliberately
rotated: the pair used at S1 does NOT run the S5 closing review - the
other one does. Certifying with the same critics whose blind spots shaped
the work would test against the answer key.

**Pair 1 - code shape** (complexity and compression). Default for
refactoring-driven or convention-heavy work.

- *Jonathan Blow - self-inflicted complexity.* Most software complexity is
  chosen, not necessary; abstractions must pay for themselves in reduced
  cognitive load, and indirection that obscures what the code actually
  does is a defect even when it follows "good engineering practice." Asks:
  where would the concrete alternative (the inline branch, the repeated
  block) be *faster to understand* than the abstraction? Where is the code
  doing work to maintain a pattern rather than to solve the user's
  problem? Which helper would you delete if you saw it fresh?
- *Casey Muratori - semantic compression and machine reality.* Understand
  what the computer actually does; eliminate unnecessary work; each line
  should carry maximum semantic weight; compress code only after concrete
  duplicates exist, never speculatively. Asks: what allocations, copies,
  and re-traversals exist only to serve a stylistic principle? Where does
  a convention impose a complexity tax that delivers nothing at this
  program's scale? Which "clean separation" forces the data to make a
  round trip?

**Pair 2 - data and runtime** (what the inputs are; what actually
happens). Default for performance work, feature additions, and any session
where real usage data exists.

- *Mike Acton - data-oriented design.* Software exists to transform data;
  the actual shape and statistics of the data ARE the problem statement,
  and "different data is a different problem." Solving a general problem
  when the real inputs are specific is waste in both directions -
  performance and comprehension. Asks: what is the actual data - sizes,
  cardinalities, how often each code path's case really occurs? Where do
  the data structures mismatch the transforms that run over them (built
  one shape, immediately reshaped)? What does the most common case pay for
  the rare case's generality? Where would the design visibly change if you
  looked at a week of real inputs? **Discipline: every Acton finding must
  name the data it concerns and its real distribution - and where the
  distribution is unknown, the finding converts into a telemetry
  requirement rather than a guess.**
- *John Carmack - empirical engineering.* The truth is what runs, not what
  the code looks like; beliefs about behavior are worthless until traced
  or measured; the dominant cost of abstraction is paid during debugging,
  and execution-order visibility is a legitimate reason to keep code
  inline and linear. Asks: what does the program actually do at runtime -
  has anyone watched it do it? Where would a bug hide, and how long from
  symptom to deterministic reproduction? Can every failure be reproduced
  from the artifacts the program leaves behind (logs, records, exit
  states)? What is believed but has never once been measured? **Discipline:
  every Carmack finding must state the observation or measurement that
  would confirm or refute it - each finding doubles as an instrumentation
  request.**

Pair-2 findings therefore have a second output channel: verdicted
`correct` findings whose fix is "we don't know yet" become telemetry
commits (fields added to the usage record, counters, trace points) rather
than behavior changes - they feed the measurement loop instead of the
edit loop.

### Prompt S1 - Adversarial review (two lenses + forced verdicts)

> Review {{TOOL_DESC}} through two opposed perspectives, taken from one
> registered lens pair (pair 1 for refactoring/convention-heavy sessions,
> pair 2 for performance/feature sessions or whenever real usage data
> exists; record which pair was used - S5 must rotate to the other).
> Perspective 1: {{LENS_A}} - [paste the stance from the registry].
> Perspective 2: {{LENS_B}} - [same].
>
> For each perspective, state 3-5 concrete findings with file and
> function/line references, each tagged with the constraint ids (from the
> S0 set, attached) it tests or violates. If using pair 2, additionally
> honor its disciplines: every Acton finding names its data and the data's
> real or assumed distribution (unknown distribution  the finding becomes
> a telemetry requirement); every Carmack finding names the observation or
> measurement that would confirm or refute it.
>
> Then - mandatory - issue a verdict for EVERY finding: (a) correct, the
> code should change; (b) perspective-valid but wrong for this context,
> with the contextual reason; (c) a genuine tension worth recording even
> though neither side is clearly right. A finding without a verdict is
> unfinished work. End by noting any finding where both lenses converge -
> convergent findings are presumptively highest priority.

### Prompt S2 - Hardening analysis (six lenses + reproductions)

> Perform the following analysis of the attached code. Produce findings
> only - do not fix anything; dispositions come at the end.
>
> **Assumptions**: what the code assumes about environment, inputs, and
> dependencies that is not checked (encoding, sizes, directory existence,
> API response-shape stability, terminal capabilities).
> **Presuppositions**: what must be true for correct behavior that is
> never verified (credentials valid, identifiers valid for their target,
> outputs writable, limits sufficient).
> **Entailments**: what the implementation logically implies that was
> probably not intended (special strings in user content, race conditions,
> equality semantics that don't match intent).
> **Cognitive decay**: re-read fresh; find inconsistencies between the
> earliest and latest code - does error handling degrade, do later parts
> cut corners earlier parts didn't, do two mechanisms contradict?
> **Usage prediction over {{HORIZON}}**: assuming regular varied use,
> predict the top five pain points in order of likelihood.
> **Adversarial-by-accident inputs**: ordinary user mistakes that produce
> confusing behavior (wrong path types, binary input, empty input, special
> characters, format mistakes, no network).
>
> For each finding: id, what it is, where, severity (will-crash /
> silent-wrong-behavior / annoying / cosmetic), constraint refs, and a
> one-line fix if obvious. **For every will-crash and silent-wrong
> finding, include a minimal reproduction** - a command or ó5-line snippet
> that demonstrates it. If you cannot construct a reproduction, mark the
> finding UNVERIFIED and say what would falsify it. Close with a verdict
> table assigning every finding correct / context-wrong / tension /
> falsified.

### Prompt S3 - Plan (classify, decompose, sort, batch)

> Using the verdicted findings from S1 and S2, the constraint set from S0,
> and the attached feature specs, produce a commit-by-commit implementation
> plan.
>
> 1. Enumerate commits: each cites its motivating finding/feature/
>    constraint ids and gets a permanent id (C1, C2, ...) that will appear
>    in code comments, tests, and ADRs.
> 2. Classify each commit: haiku (single-site, mechanically verifiable),
>    sonnet (one coherent function or one uniform pattern), opus (multiple
>    subsystems or semantics), fable (architecture/contract).
> 3. Decompose every opus and fable into haiku/sonnet pieces, or park it
>    in the exclusion list with reasoning. Nothing above sonnet may be
>    scheduled as a unit.
> 4. Topologically sort by real dependencies - state each dependency and
>    why it is real (compile-order or semantic, not preference). Note where
>    ordering avoids writing the same code twice.
> 5. Batch the sorted commits into themed, independently reviewable
>    groups. Name the critical path.
> 6. Mandatory sections: an **exclusion list** (every verdicted finding
>    NOT scheduled, with the reason - context-wrong and tension verdicts
>    land here by default) and the **environment checklist** (inputs
>    verified on disk and checksummed; live vs. stubbed dependencies
>    declared; the live-verification step named for any external-contract
>    change). Where a feature spec contains a literal patch that will land
>    after refactoring commits, restate it as behavior + acceptance
>    criteria and mark the literal code illustrative.
>
> Present the plan and stop. Do not execute until the gate decision.

### Prompt G1 - The gate (human, one message)

> Reviewed. Strike: [ids]. Add: [described changes]. Everything else
> approved. / OR / Gate waived - the exclusion list is the contract.
> Execute batch 1.

### Prompt S4 - Execute a batch

> Execute batch {{N}} of the approved plan. Rules:
>
> - Run the environment checklist first; a missing or unverifiable input
>   is a stop-and-ask, never a transcribe-and-proceed.
> - Batch 1 creates the persistent test file; every batch appends cases
>   named by commit id and finishes by running the whole suite. No
>   throwaway verification for anything a later batch could break.
> - Implement intent. Flag EVERY deviation from the plan or a literal
>   spec with rationale and a one-line revert path.
> - If a commit's tier was misclassified or a missed dependency surfaces,
>   stop and return to the plan - do not push through.
> - Tag non-obvious code changes with their commit id in a comment, in
>   the codebase's own comment style, honoring every S0 constraint.
> - Close with a batch summary in ADR form: commits landed with one
>   observable effect each; an ADR for every non-mechanical decision made
>   during execution (context / decision / alternatives / consequences);
>   the deviation list (may be "none"); tests added; standing caveats
>   restated verbatim (e.g. stubbed-dependency status).

### Prompt S5 - Close

> All batches are landed. Two tasks.
>
> 1. Assemble the maintenance spec from the accrued artifacts - do not
>    reconstruct from memory: purpose and scope; data shapes with one
>    concrete example each; the S0 constraint set, amended where execution
>    legitimately changed a convention (say which commit changed it); the
>    ADRs, concatenated from the batch summaries plus any pre-existing
>    design decisions, including reversals as reversals; the extension
>    guide for the three most likely future changes; the debts register =
>    exclusion list + falsified findings + standing caveats + arbitrary
>    constants labeled arbitrary; the companion-artifact table with each
>    artifact's declared sync trigger.
> 2. Re-run the S1 adversarial prompt on the FINAL code using the lens
>    pair NOT used at S1 (rotation rule - fresh blind spots). Produce the
>    verdict delta against the original review: what was fixed, what new
>    tension the modifications introduced (look especially at functions
>    that grew across many batches), what stands unchanged, and - if the
>    closing pair was pair 2 - which findings became telemetry
>    requirements for the next session's measurement loop. A small delta
>    certifies the work; a substantial one is the next session's S2 input,
>    already in finding format.

---

## Part III - Rationale ledger (why each refinement exists)

| Refinement | Failure it corrects (observed in the source run) |
|---|---|
| S0 before S1/S2 | Conventions were articulated after six batches of edits; critiques lacked a rubric for "bug vs. convention" |
| Mandatory verdicts on every finding | Prevents adversarial review from becoming a refactoring to-do list; the verdicts are what kept a debatable abstraction alive and prioritized the one convergent finding |
| Reproductions for severe findings | One finding (a claimed self-referential delimiter collision) survived three batches before a test falsified it; a reproduction would have killed it at analysis time |
| Behavior-form feature specs | A literal patch referenced a function the plan deleted before the feature landed; the plan caught it, but only by luck of ordering discipline |
| Persistent appended test suite | Regression was re-typed heredocs from memory each batch - it worked, but as luck plus context, not process |
| Environment checklist + checksum | All diffs in the source run were against a reconstructed baseline because the uploaded file was absent from disk; stubbed-dependency status was a recurring manual disclaimer instead of a standing checklist item |
| ADR-form batch summaries | The final spec required archaeology across the whole thread; two decisions (an auth reversal, a direction-inverted convergence) were nearly mis-recorded |
| Explicit gate or explicit waiver | The designed human filtering step was silently bypassed; the exclusion list became the contract without anyone saying so |
| Companion sync triggers | Generated artifacts (prompt packs, skeletons) duplicate code schemas and silently rot when the schema moves |
| S5 verdict delta (closing the loop) | The code grew ~50% under modification and the central API function absorbed six concerns; nobody re-asked the original critics whether the result still passes |
| Lens pair registry + S1/S5 rotation | The source run had only code-shape critics (Blow/Muratori); data-shape and runtime-truth questions (Acton/Carmack) went unasked - e.g. nobody asked what the *typical* input actually is, and the telemetry that would answer it was added late and incidentally. Rotating pairs also stops the closing review from certifying against the opening review's own blind spots |

The workflow's operating principle, stated once: **every stage must end in
a decision artifact - verdicts, severities, tiers, exclusions, deviations,
deltas - never in open-ended analysis. The artifacts that matter most over
time (constraints, tests, decision records) are produced earliest and
accrued continuously, not reconstructed at the end.**
