# Five models, one Bend task: what the materials cost them

Bend 2.0.16. Five models were given identical materials and identical instructions
and asked to write `playground.bend`, `LAWS.bend` and `PROOF.bend` such that
`bend PROOF.bend` prints "All terms check." and `bend playground.bend` renders.
One model passed on the first attempt. After verbatim error-pasting, all five
passed. What no amount of error-pasting reached is the subject of this report.

Every claim below that a model made about its own code or about the documents has
been checked against the files, the rendered output, or the document text. One
failed that check and is marked. An earlier version of this report marked a
second, a quotation from the guide, as fabricated; the quotation is real and the
check was wrong (see the Sonnet section).

---

## a. Inventory and confounds

**What was in the pack.** Five model directories, each with `playground.bend`,
`LAWS.bend`, `PROOF.bend`, `transcript.txt`. No missing deliverables. Plus
`prompt.txt`, `results.txt`, `run_model_tests.sh`, and three context documents:
`bend-guide.txt` (621 lines), `bend-base.txt` (2850), `bend-guide-shaders.txt` (268).

**Context was uniform, and `prompt.txt` understates it.** The prompt says two
documents were pasted. All five transcripts cite shader-guide content that exists
in no other file, so all five received three. This is a documentation defect in the
record, not a comparability defect.

**The demos were never supplied.** Zero occurrences of `demos/`, `ray_tracer`,
`slash_boss`, `par_sum` or `Fly.march` across all five transcripts. The guide and
shader guide reference demo paths but never quote their source. This matters
because several of the experiment's own reference patterns -- the canonical
early-exit loop, the canonical balanced fork, the `1n++p` binder form -- are drawn
from material no model could read. Checkpoints resting on them test knowledge that
was provably absent from context.

**Confounds that survive.**

1. **The two runs per model are one measurement.** `PROOF.bend` imports
   `playground.bend`, so a playground error preempts the proof entirely. For every
   failing model both runs report the same error, differing only by a `playground.`
   prefix on the location. Ten runs, six distinct outcomes. For four of five
   models in round 1, no law was ever checked.
2. **Transcripts are not comparable as process evidence.** Opus and Sonnet show
   summarised reasoning with no file contents; Terra shows paraphrased reasoning
   with files inline; open-source-large's code blocks were scraped as line-number
   gutters and lost entirely; open-source-medium shows raw unsummarised
   chain-of-thought at 6,121 lines. The 37x spread in transcript length is a
   scraping artifact, not a measure of deliberation. No claim of the form "model X
   thought harder" is supportable from this pack.
3. **`results.txt` was truncated on every run.** The v1 harness opened it with
   `>`. Round-1 evidence survived only because it was archived by hand.
4. **One run per model.** Per-model variance is unmeasured throughout. See (f).

---

## b. The matrix

Final state, after recovery. Geometry measured by parsing the renders and counting
columns blank in every row.

| | 1. Loop shape | 2. Law substance | 3. Fork shape | 4. Geometry | 5. Affinity | Outcome |
|---|---|---|---|---|---|---|
| **opus** | fuel only, fixed count, no early exit -- deliberate | 6 laws, 2 inductions + append lemma | halving, balanced | 32x32, 0 dead cols | pass | passed first try |
| **sonnet** | fuel + flag, nested match -- canonical | 2 laws, both inductions | halving, balanced | 32x32, 0 dead cols | pass | passed after 6 errors |
| **terra** | fuel + sticky flag, no early exit -- deliberate | 5 laws, **all single-step** | 4-way quadtree, balanced | 64x128 centred, 1 dead col | pass | passed after 2 errors |
| **large** | fuel + flag, two-scrutinee -- canonical | 10 laws, **all single-step** | halving, but root split ~100:1 | **16x32, 16 dead cols** | pass | passed after 3 errors |
| **medium** | fuel + flag, two-scrutinee -- canonical | 5 laws, 3 inductions | **peel-two spine; Sierpinski fully serial** | **16x32, 16 dead cols** | pass | passed after 8 errors |

Cells where I cannot separate model difference from run-to-run noise, and would
need repeated runs to call: **checkpoint 1** (three models converged on the same
shape via different error paths; whether opus and terra would have too, had they
hit an error, is untested), and **the error counts themselves** (a single run's
first error determines everything downstream).

Cells I would defend as signal rather than noise: **checkpoint 2**, because the law
sets never changed across any recovery round in four of five models -- they are a
stable property of the first draft, not a coin flip; and **checkpoints 3 and 4**,
for the same reason.

---

## c. Per model

### claude-opus-5 -- passed first try; the only model to retract its own claim

The only one-shot pass. Its `LAWS.bend` opens by deriving the constraint the whole
task turns on, from `base.txt` alone: *"Every F32 operation in Base is a bare `law`
with no def... So no claim about a Mandelbrot value -- membership, escape count,
which shade a cell gets -- is provable here, by anyone, ever."* It then restricts
every law to structural facts and proves two of them by induction over the fork
tree with a hand-rolled `list_append_length` lemma.

Root cause of what went wrong: **fluent confabulation, in the comments rather than
the code.** Its `LAWS.bend` claimed the picture laws guarantee *"nothing dropped or
duplicated by the split."* Asked to audit, it retracted: *"That is false, and I own
it... If the lower branch reused `first_row_index` instead of adding `half_row_count`,
every row would be duplicated and both laws would still pass."* It also found five
permanently blank columns in its own Mandelbrot -- *"a dead left margin I never
intended"* -- which my independent count confirms exactly, and admitted silently
changing a stated decision: *"The plan I gave you said 64 columns... I changed a
stated decision silently."*

No recovery arc: it hit no compiler error. Its value to this experiment is as the
control -- its list of places the documents forced a guess is the longest of the
five and is the least contaminated by recency, because nothing burned it.

**Honesty: strongest in the set.** It volunteered a retraction of a claim nobody
had challenged, and separated verified-by-reading from inferred throughout.

### claude-sonnet-5 -- deepest language reasoning, rediscovered a rule the guide buries

Error chain: define-before-use -> unfilled law used by live code -> four affinity
errors (`new_imaginary_part`, `row_offset`, `total_columns`, `levels_left`). Six
rounds by its own count. *Correction:* an earlier version of this report said
five rounds and two affinity errors; `results_round3.txt` and Sonnet's own
diagnosis both show the other two.

Root cause: **rule collision, navigated correctly in the hard place and missed in
the easy one.** It copied Base's `law`-forward-declaration pattern for its orbit
loop, citing `Word.adc`/`Word.adc.con` position for position -- a genuinely
sophisticated read -- and then forgot the same declare-before-use rule for a
trivially reorderable helper six lines long. When the checker rejected the law
route, it moved to the guide's own prescription and landed on the canonical shape:
*"'two mutually recursive functions become one def with an extra argument selecting
which to run' -- so has_escaped is threaded as a real incoming parameter."*

Its recovery contains the best piece of language reasoning in the pack, derived
from error messages alone: *"arguments landing in an erased (-) parameter slot of
whatever they're passed to don't count as a use at all, live or not"*, and then
*"occurrences inside a `%e : P` rewrite's P aren't counted as live uses at all -- P
is elaboration bookkeeping, not part of the actual term being built."* The
underlying rule is in the guide, but not where anyone looks for it: the "Under the
Hood" section says *"Code that runs is checked live; types, erased arguments and
equations are checked dead"*, about 380 lines after the Quantities section it
governs. Sonnet reconstructed from error messages a rule that is stated once, in
the section on the type theory, and never in the section on quantities.

Its self-audit found a real defect by reading: that `escape_count` can never return
more than 28, so `density_char`'s blank branch is unreachable. **Verified** -- the
glyph histogram of its rendered Mandelbrot is `{. 1839, @ 602, + 41, # 14}`, zero
spaces.

**Honesty: strong.** Every quotation it gave verifies. It attributed its false
belief -- that proof code is exempt from affine tracking -- to the live/dead
sentence above, and that attribution is accurate: it over-generalised "equations
are checked dead" into "proofs are unchecked for quantity", which is a misreading
of a real and badly placed sentence. *Correction:* an earlier version of this
report called that quotation fabricated. It is not. The verification searched for
the plain string "checked live", and the guide writes it with emphasis markup,
"checked \*live\*". The error was in the check, not in the model.

### gpt5.6-terra -- cleanest geometry, thinnest laws

Error chain: affinity on a match binder -> an indentation error introduced by
pasting a replacement branch. Two rounds, both classified STATED by the model
itself, correctly.

Root cause: **missing knowledge of one quantity rule** -- that a matched parameter
hands its binders out carrying the parameter's own quantity. It diagnosed this
precisely afterwards: *"I saw that Nat is declared Data in Base and mentally
treated that as 'a Nat can be used freely'... My error was confusing a type's maximum
allowed quantity with the actual quantity assigned to one particular binding."*

It is the only model that re-derived the Sierpinski geometry rather than
pattern-matching it, building a centred construction over 64x128 with the identity
`(c - (64-r)) & ((64+r) - c) == 0` and reasoning explicitly about apex placement
and doubling. The render confirms it: a correct centred triangle, one dead column.

Its weakness is checkpoint 2, and it named it without being pushed: *"These are
valid laws, but they are shallow. They verify output conventions and one
accumulator base case."* Five laws, all single-step. It passed the deliverable gate
on them.

**Honesty: good.** Its ranked failure list did not include the affinity bug that
actually killed it, which is a calibration miss, but it made no claim it could not
support and its post-hoc classification checks out against the guide text.

### open-source-large -- fixed a defect nobody pointed at; shipped a half-blank figure

Error chain: affinity -> termination argument order -> multi-match scrutinee order.
Three rounds.

Root cause: **ignored context, twice over, on rules that are stated.** The
shrinking-parameter rule is in the guide with an imperative sentence attached; it
read the rule as *"there exists a shrinking argument somewhere in the call rather
than the first non-unchanged argument must be the shrinking one."*

Its recovery is the best in the set for breadth. In one turn it fixed the reported
termination error, found the same ordering bug at a second site, and killed a
mutual recursion no error had pointed at: *"mandelbrot_escape_go calls
mandelbrot_escape_check which calls back... Fix: make escaped a parameter of the
recursive function, compute the next escaped at the call site, and eliminate the
helper entirely."* That is the canonical fuel-plus-flag shape, derived without ever
seeing the demo it comes from.

Against that: it shipped a 16-row, 32-column Sierpinski in which the right 16
columns can never be filled, and its closing summary certified the result --
*"Sierpinski triangle (16x32): the Lucas'-theorem fractal pattern is correct."* It
found the defect immediately when asked, and named it precisely. It also carries a
silent numerical defect neither it nor the checker caught: its escape test is
computed from the current `z` but handed forward alongside the next one, so escape
is detected one iteration late.

**Honesty: mixed.** Confident certification of an unexamined render, then a candid
and accurate audit when asked. Its doc classification is the sharpest of the five:
*"'Binder order' is never defined. I read it as 'the order in which the match binds
its pattern variables' (a reading that makes it vacuous)."*

### open-source-medium -- correct diagnosis every time, no generalisation

Error chain, eight rounds: unary minus -> scrutinee order -> termination -> affinity ->
**termination again** -> affinity -> affinity -> name resolution.

Root cause: **not a knowledge gap.** Its diagnosis of every single error is
correct, including the subtle interaction it worked out unaided -- that putting the
Bool first to satisfy binder order broke the left-to-right termination rule, and
that a single two-scrutinee match satisfies both. That reasoning is better than its
compile record suggests. What it never did was apply a rule anywhere but the
reported line, so the same rule broke at three different sites in succession.

One instruction fixed it. Told to enumerate every violation of the two rules it had
already derived, across all three files, before fixing any, it produced a correct
file-wide audit and passed on the next run. The missing behaviour was breadth, not
knowledge.

It has the second-strongest law set -- three genuine inductions -- which is a
surprise given its compile record, and the weakest fork: a linear spine peeling two
rows against the remainder, with the Sierpinski renderer containing no parallel
call at all, in a program whose brief was to exercise parallelism. Neither changed
across eight rounds.

**Honesty: candid, and unreliable.** It flagged its own uncertainty well --
*"I do not know whether the checker treats the proof body as a live context"*, and
called its rename of every dotted name a best guess. But its self-audit **invented
a catastrophic bug that does not exist**: it traced its escape loop, concluded every
path returns `0n`, and confessed that the whole Mandelbrot must therefore print
blank -- *"I should have caught this when I first wrote the escape function. I did
not, and I want to state it clearly rather than bury it."* Its own recursive case is
`1n+mandelbrot_escape_iterations(rest, ...)`; the prefix accumulates. The rendered
output contains 619 glyphs. **This is the report's clearest example of fluent
justification as a failure mode -- with the sign flipped. The confession is as
fluent, as well-argued, and as wrong as any overclaim would have been.**

---

## d. Failures shared by three or more models

Material defects, not model defects. Ranked by what each cost.

**1. The deliverable gate is satisfiable vacuously. (3 of 5)**
Terra passed on five single-step laws, large on ten, medium's two escape laws are
single-step. `"All terms check."` does not distinguish them from opus's two
inductions over a fork tree. The prompt set a floor -- "a law you cannot discharge
is a failed deliverable" -- and no ceiling, and three models found the floor. Cost:
the headline success metric of the whole exercise does not measure what it was
built to measure.

**2. The shader guide is net-negative for a text-output program. (4 of 4 who
answered)** Four distinct harms from one cause. Terra built 4,096 two-character
leaves and afterwards called it *"close in spirit to a per-pixel fork"*. Opus wrote
a justification for a zero-argument def whose rationale, it later said, *"does not
hold"*. Sonnet wrote a defensive performance comment about GPU lane divergence for
*"a 32x78 grid computed once on CPU"*. Large skipped `!` entirely because 48 leaves
felt absurd beside 16,384. The document states its cost model without stating its
domain of validity. Cost: wasted design effort in every model, and in two cases a
worse structure than the naive one.

**3. Laws are stated over consequences, not properties, and then over-described.
(3 of 5)** Opus claimed its row-count laws prove "nothing dropped or duplicated";
sonnet claimed its count law means "no row is lost or doubled"; both retracted when
asked, in the same terms -- a cardinality law is satisfied by duplicating every row.
Medium's laws are all list lengths and it said so: *"No law catches any of these."*
Cost: proofs that discharge and constrain almost nothing, presented in comments as
though they constrain the program.

**4. "Binder order" and the left-to-right termination rule are stated without
definition or counterexample. (2 of 5 errored, and a third designed around it)**
Both rules are one clause with no example, and every example in the guide and in
Base happens to satisfy them, so the constraint is invisible by induction over
examples. Large and medium each burned rounds on both. Cost: four compiler rounds
across two models, and the two rules collide -- satisfying one naively breaks the
other, which nothing in the documents warns about.

**5. Affinity is stated without a two-use worked example. (4 of 5 errored)** The
rule itself is unambiguous. What is missing is any example of a function that uses
a parameter twice and needs `+`, and any mention of the diagnostic text. Cost: one
round each for terra, large, sonnet and medium -- cheap individually, universal
across the set.

**6. Aspect ratio and grid dimensions go unexamined. (3 of 5)** Two models shipped
figures whose cell test cannot reach half their columns; opus's Mandelbrot has five
dead columns and a 1.65 row/column step ratio against a stated 2:1 assumption. Cost:
visible defects in the artifact that no compiler and no law will ever surface.

---

## e. Recommended changes

Split by whether the evidence is universal or single-model. Scored 0-10 on expected
robustness gain per unit of editing.

### Changes that help every model -- fix the materials

| # | Change | Targets | Score | Rationale |
|---|---|---|---|---|
| 1 | **Law-strength floor in the prompt**: require at least one law needing induction, and require each law's comment to name a wrong implementation that would satisfy it | ckpt 2 | 10 | Three models passed the gate vacuously and two over-described what they proved; this is the only change that touches both, and it is a prompt edit, not a language change. |
| 2 | **Correct "mutual recursion is not allowed"** -- Base does it four times via a `law` forward declaration | ckpt 1 | 9 | A flatly false sentence that sent one model down a route the checker rejects and left it never learning why Base's version works. Verified against four Base pairs. |
| 3 | **Correct the "bug-free code" framing of laws** | ckpt 2 | 9 | Two models independently retracted overclaims traceable to this sentence; opus names it as the cause of its own false belief. |
| 4 | **Define "binder order"; add a rejected termination example** | ckpt 1, 5 | 8 | Two models, four rounds, on two rules that are present but invisible. Large's diagnosis names the exact failure mode: a reading that makes the rule vacuous. |
| 5 | **Add a two-use affinity example and the diagnostic text** | ckpt 5 | 7 | Four of five errored on the most-stated rule in the guide. The rule is not the gap; the worked example is. |
| 6 | **Scope the shader guide's numbers** | ckpt 3 | 7 | 4/4 agreement, four distinct harms. One paragraph. |
| 7 | **Add define-before-use, no-unary-minus, and the `1n++p` pattern form** | ckpt 1, 5 | 6 | Three genuinely absent rules, each of which cost exactly one round to exactly one model, but each is one sentence. |
| 8 | **Prompt: require stated grid dimensions and a reachability argument** | ckpt 4 | 6 | Non-leaking substitute for naming the artifact. Two models shipped half-blank figures; both found the defect instantly when asked the question. |
| 9 | **Harness: measure the render and histogram the error class** | all | 8 | Not a materials change, but it converts checkpoint 4 from silent to loud and would have caught medium's confabulated bug in one line. Highest score per hour of work in the list. |

### Changes only one model needed -- leave the materials alone

- **The `%e : P` motive and erased-slot quantity rules** (sonnet; opus listed the
  motive half as ABSENT). Not absent: stated once, in "Under the Hood", far from
  Quantities. Two models failed to connect it, which argues for repeating one
  sentence in Quantities -- a cheap move-not-add fix, proposed as a follow-up hunk
  rather than folded into the delivered patch.
- **Dotted-name resolution** (medium only). Its proposed rule is unsupported -- Base
  is full of `Foo.bar`/`Foo.bar_baz` pairs that work -- and it flattened every name
  as a guess without diagnosing. Do not patch on this evidence; test it.
- **Breadth of repair** (medium only). Not a materials defect at all. The
  model-specific workaround is the sweep instruction, which worked in one shot and
  is reusable as a debugging prompt rather than a document change.

### Verify before patching

Five open questions, each settleable in under ten lines, none answered by this run.

1. **Does a law-cycle require the shrinking parameter first?** All four Base
   instances put it first; sonnet's put a `Nat` third behind two `F32`s and was
   rejected. Two laws, one of each shape, same helper cycle.
2. **Does `+` inherit from a law's `for` clause to a cross-file filling def?**
   Sonnet marked them and still got "consumed more than once" at the def line.
3. **Do occurrences in a `%e : P` motive count as uses?** The guide's live/dead
   sentence says equations are checked dead, which implies not, and sonnet's
   rewrite proofs reused variables in motives without error. Lowest priority of
   the five; confirm only if you move that sentence into Quantities.
4. **Does the checker reduce a `U32` literal through 32 `Word` levels?**
   **Resolved: yes.** Large's ten ground laws over `U32.and` and `U32.is_eq` were
   discharged by `{==}` in a run that printed "All terms check." An earlier
   version called this weak evidence. A passing proof run is direct evidence, so
   Opus's caution cost it nothing but was unnecessary.
5. **What actually caused medium's `Sierpinski.row` resolver error?** Currently
   unexplained by anyone, including medium.

### If you change one thing first

**The law-strength floor.** It is a prompt edit, not a language change; it costs
one paragraph; and it is the only change that repairs the experiment's own success
metric. Everything else in this report is measured against "All terms check.", and
right now that string is printed with equal enthusiasm for two inductions over a
fork tree and for five statements that a `Bool` match returns the character it
returns. Until that gate discriminates, every other improvement is measured with a
broken instrument.

---

## f. What this experiment cannot tell you

**Nothing about per-model variance.** One run each. Every cell in the matrix could
be a coin flip. The most suspicious are the error chains: a single first error
determines everything downstream, so "medium took eight rounds" may be a property
of medium or a property of one unlucky first draft. **Three runs per model** would
separate a stable first-error class from a random one; **five** would support any
statement of the form "model A recovers faster than model B." Neither number is
supported by what exists.

**No leaderboard.** The one-shot result was 1/5. After error-pasting it was 5/5.
Those are two different experiments with two different conclusions, and the second
one is closer to how these models are actually used. Ranking on the first is
ranking on a single sample of first-draft luck.

**Nothing about whether the patches work.** Every recommendation in (e) is
motivated by observed failure, not validated by observed success. The obvious next
experiment is the one this report is designed to enable: build the prompt with
`bendlab.py prompt` (live docs plus `rules-card.md` plus the `task` template in
`prompts.md`), run the same five models from scratch, and compare -- one-shot
pass rate, rounds-to-pass, and the three silent checkpoints separately, since the
patches split cleanly across those outcomes.

**Nothing about Bend at scale.** One task, two figures, a few hundred lines. The
laws that proved tractable were all structural; nothing here exercises a law about
a value, because F32 opacity puts that out of reach in this task specifically.

**Little about the models' reasoning process.** The transcripts are four different
scrape formats, one of which lost its code entirely. Conclusions here rest on the
delivered files, the rendered output, and the prose -- all of which are comparable --
not on the reasoning traces, which are not.

**And the self-reports are not evidence.** Of the five diagnoses collected, one
invented a critical defect that the rendered output refutes, caught only because
the claim was checkable against the program's output. The verifier is not exempt
either: this report's own first pass flagged a genuine quotation as fabricated,
because a plain-text search did not see through markdown emphasis. Checking has to
be checked too -- normalise the text before matching, and treat a zero-hit search as
a question, not a verdict.
Any future round of this should keep both properties -- ask for the trace rather
than the conclusion, and require a quote for every claim about the documents.

---

## g. Addendum, 2026-09-30: later medium sessions, and Bend 2.0.32

**Two more open-source-medium sessions** ran after the diagnosis round, each
opening with a "repair notes to myself" catalog that the model had written for
itself across earlier sessions (20 notes by the last session). In the last
session, the only compiler error was `c_imag (consumed more than once)`. The
reply was the four-line enumerate-all message from `prompts.md`, word for word,
and the next run compiled and checked. Eight rounds in i00; one round here.
That is the strongest evidence in this project for both tactics: carrying
lessons forward, and asking for every site of the broken rule at once.

**The same catalog locked in the silent failures.** Three of its rules are
contradicted by code that passed the checker in i00, and each produced the
failure it predicted:

| Catalog rule | Contradicted by | What it caused |
|---|---|---|
| "A Nat countdown cannot give a balanced fork; do not invent a carrier type" | the guide's own `pow2`; opus, sonnet and large all halved a Nat depth | one parallel let between two linear chains, about 100:1; the fork's comment quotes the rule |
| "`U32.and`, `U32.is_zero` ... do not reduce in dead mode" | large's ten `U32.and` / `U32.is_eq` laws passed | retreat to four laws of the form `f(0n, ...) == SNil{}` |
| "`Foo.bar` resolves only when `Foo` is a declared type" | opus's `Mandelbrot.width`, sonnet's `Sierpinski.cell.from_shared_bits` | the closing diagnosis filed this as a WRONG finding about the guide: a false bug report |

The law failure behind the second rule was also likely misread. The checker
printed `observed : False{}`, a fully reduced value, which points to a false
law rather than a stuck term.

Measured from the final session: a 24-row, 80-column Sierpinski figure with 56
columns that can never be filled, which is worse than i00's 16 of 32. Its
audit found and stated all three silent failures accurately, and explained
each one with the false rule. Its code blocks also stopped being labelled
`python`.

**The lesson generalises beyond Bend.** A lesson file a model writes for
itself speeds up compiling and fossilises wrong explanations into rules. The
catalog's own note 19 proposed grading each rule VERIFIED, STATED or GUESSED,
and it was never applied to the catalog. `rules-card.md` applies that grading,
checking each rule against runs from more than one model.

**Bend 2.0.32**, announced 2026-09-30, adds `--verdict`: files compile to
BendTT, a minimal proof kernel verified in Lean, with a $10k bounty for a
proof of `Empty`. That makes a discharged law a trustworthy proof of what the
law *says*. It does nothing about laws that say too little, and that is this
report's central finding: two of five models passed on laws that each close
in one reduction step, and two more overstated what their laws proved. Soundness and adequacy are different properties. The finding bears
directly on the stated thesis of "AI inference, guarded by Bend's LAWS", and
is written up for upstream in `upstream-discussion.md`. `--verdict` does not
yet cover axiomatic F32, which this task's playground uses throughout; whether
these PROOF.bend files are accepted under `--verdict` is untested.

**Corrections in this version:** the quotation wrongly called fabricated (see
the introduction), Sonnet's error count (six, not five), and the U32 reduction
question (resolved: yes).
