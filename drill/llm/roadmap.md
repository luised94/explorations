# Drill Tool -- Development Roadmap (Ranked)

A quantitative, multi-axis ranking of where to take the tool next, weighted
toward your stated priorities and balanced with engineering value. The scoring
model is reproducible (`roadmap_model.py`); a sensitivity check confirms the
top tier is stable across reasonable re-weightings, so the ordering is not an
artifact of the weights I chose.

ASCII only. Single-user assumption preserved throughout: nothing below
introduces concurrency, auth, or multi-tenant concerns unless explicitly noted
as out of scope.

This file is the PLAN and its rationale. For live status (what is done, what is
next, the current baseline and green count), see llm/STATUS.md -- the single
source of truth. The DONE markers in the tables below are a convenience; if they
disagree with STATUS.md, STATUS.md wins.

---

## 1. How the ranking was built

Each candidate is scored 1-5 on six axes; the weighted sum is its priority
score. Weights sum to 1.0 and encode your instruction to "prioritize the
things I think are important, then balance."

| Axis | Weight | Meaning |
|------|-------:|---------|
| USER | 0.28 | Alignment with the priorities you named. Highest, per your instruction. |
| LEARN | 0.22 | How much building it teaches the underlying tech / math / cs. A stated primary goal. |
| FOUND | 0.18 | Foundational leverage: how many later items it unblocks or de-risks. |
| EFFORT | 0.14 | Inverse effort (5 = trivial, 1 = multi-week). Pre-inverted so higher is better. |
| QUAL | 0.10 | Correctness, robustness, maintainability, documentation. |
| RISK | 0.08 | Inverse risk (5 = safe/understood, 1 = invasive/research-y). |

Scores are grounded in a read of the actual code, which raised several
feasibility numbers: the operator table is data-driven, `pick_next_question`
is a single swappable function, the `difficulty` and `elapsed_ms` columns
already exist, the expression evaluator and renderer already recurse over
nested trees (only the generator is flat), and the server host is already
env-overridable. Those facts make several "big-sounding" items cheap.

---

## 2. The ranked list (tiers)

Tier 1 = do first (high alignment, high leverage, mostly low risk). Tier 4 =
defer or skip for a single-user tool. Full per-axis scores are in the appendix.

NOTE (2026-07): the tables below are the ORIGINAL pre-modularization ranking,
kept as history. Six items have shipped (marked DONE). For the CURRENT ranking
of what remains -- rescored against the actual code after modularization -- see
section 2a (Reassessment 2026-07) and ADR-054; the runnable model is roadmap.py.

### Tier 1 -- Foundation and core priorities (do these first)

| # | Item | Score |
|--:|------|------:|
| 1 | Modularize: extract JS into modules, split Python into packages | 4.56 | DONE (C-MOD-*)
| 2 | Extend arithmetic: difficulty control (digits / #operations / operator set) | 4.50 | DONE
| 3 | Study curriculum derived from the codebase | 4.44 | PARALLEL (see 2a)
| 4 | Extend arithmetic: more operators (exponent, modulo, ...) | 4.32 | DONE
| 5 | Generalize expression generation (nested multi-operator trees) | 4.32 | DONE
| 6 | Consolidate the SM2 spaced-repetition engine | 4.04 | NEXT+1 (see 2a)
| 7 | Adaptive question selection (swap `pick_next_question`) | 3.98 | with SM2
| 8 | Automated test suite checked into the repo | 3.94 | DONE
| 9 | Logic / deduction drill (truth tables, syllogisms) | 3.80 |
| 10 | Code drill ("what does this snippet output?") | 3.72 |

### Tier 2 -- High value, near-term

| # | Item | Score |
|--:|------|------:|
| 11 | Schema migration runner (version-aware ALTER sequence) | 3.58 | DONE
| 12 | Typing / text-entry speed drill | 3.50 |
| 13 | Timed-round / speed-drill mode (uses `elapsed_ms`) | 3.50 |
| 14 | Assertion / invariant pass (boundary + pre/postconditions) | 3.44 |

### Tier 3 -- Worthwhile, later

| # | Item | Score |
|--:|------|------:|
| 15 | JSONL export / backup endpoint + button | 3.18 |
| 16 | Mastery map / explorable space (Victor "Mode D") | 3.14 |
| 17 | Structured logging + error-envelope audit | 3.12 |
| 18 | Timing stats (compute / display `elapsed_ms`) | 3.12 |
| 19 | Stats depth: most-missed, over-time, per-bank | 3.08 |
| 20 | Module docstring / status-drift cleanup + ADR index | 3.04 | DONE (STATUS.md + conventions done; ADR index at llm/adr-index.md, Thread N.3)
| 21 | Alphabet / romanization drill | 3.04 |
| 22 | Grammar exercises (fill-in / reorder) | 3.04 |
| 23 | Trivia importers (OpenTriviaDB/QA, FreebaseQA) | 2.86 |
| 24 | Vocabulary importers (CodingFriends, doozan/spanish_data) | 2.86 |
| 25 | Dashboard: live stats beside the drill (Victor "Mode C") | 2.82 |

### Tier 4 -- Defer, or skip for a single-user tool

| # | Item | Score |
|--:|------|------:|
| 26 | Geography visual mode (point-to-on-a-map) | 2.68 |
| 27 | AI-generated content (server-side Anthropic calls) | 2.64 |
| 28 | wordfreq frequency-ranking integration | 2.62 |
| 29 | Document 0.0.0.0 / WSL binding (already env-overridable) | 2.54 |
| 30 | Music interval / rhythm drill | 2.40 |
| 31 | Chart.js rendering in stats view | 2.36 |
| 32 | In-browser bank editor | 2.18 |
| 33 | Dictionary / encyclopedia dump pipeline | 2.08 |
| 34 | Handwriting canvas (CJK / Arabic / Devanagari) | 1.90 |
| 35 | Pronunciation via SpeechRecognition (already deferred, ADR-006) | 1.46 |
| 36 | Multi-user / auth / connection pooling | 1.32 |

---

## 2a. Reassessment 2026-07 (post-modularization) -- ADR-054

The tiers above are the ORIGINAL pre-modularization ranking. After roadmap #1
shipped, the remaining items were rescored against a fresh read of the actual
code (weights unchanged; only code-reality axes EFFORT/RISK/FOUND moved). The
runnable model is `roadmap.py` (REASSESS_2026_07); the rationale, alternatives,
and sequence decision are ADR-054. Current ranking of what remains:

| # | Item | Score | delta | note |
|--:|------|------:|------:|------|
| 1 | Study curriculum from the codebase | 4.26 | -0.18 | runs in PARALLEL |
| 2 | Consolidate SM2 (spaced repetition) engine | 4.26 | +0.22 | Thread N+1 |
| 3 | Vocab/language features (extend qtypes/banks/import) | 4.00 | new | **Thread N** |
| 4 | Adaptive selection (swap `pick_next_question`) | 3.94 | -0.04 | with SM2 |
| 5 | Logic/deduction drill | 3.80 | - | |
| 6 | Code drill (what does this output?) | 3.72 | - | |
| 7 | Typing / text-entry speed drill | 3.58 | +0.08 | Thread N+2 |
| 8 | Timed-round / speed-drill mode | 3.50 | - | |
| 9 | Assertion / invariant pass | 3.44 | - | |
| 10 | Timing stats (display `elapsed_ms`) | 3.26 | +0.14 | quick win -> Thread N |
| 11 | Stats depth: most-missed, over-time, per-bank | 3.22 | +0.14 | |
| 12 | JSONL export/backup endpoint + button | 3.18 | - | |
| 13 | Module docstring/status drift + ADR index | 3.04 | - | DONE in Thread N.3 (llm/adr-index.md) |
| 14 | Alphabet/romanization drill | 3.04 | - | |
| 15 | Grammar exercises (fill-in / reorder) | 3.04 | - | |
| 16 | Vocabulary importers (CodingFriends, doozan) | 2.86 | - | feeds vocab |

What moved and why (survey facts, all verified against shipped code): the
`pick_next_question(candidates, history)` seam is a single pure swappable
function, so SM2 (+0.22) and adaptive selection are cheaper/safer to slot in;
the migration runner is DONE and `elapsed_ms`/`difficulty` columns exist, so
new-migration and timing work are de-risked; the JSONL/CSV import pipeline and
the translate/identify/free_response qtypes + bank-language plumbing already
exist, so vocab/language is mostly content + small extension (new item, 4.00),
not net-new; typing has no infra beyond an empty `"typing"` config category
stub, so it stays genuinely net-new; the stats pipeline is modular with
`elapsed_ms` collected-but-unsummarized, so timing-stats and stats-depth become
render additions (+0.14 each, quick wins); and FOUND drops for items whose
leverage was "unblocks the refactor" (curriculum, adaptive) now that it is done.

**Recommended sequence (score TEMPERED by user constraints -- ADR-054).** The
raw top ties study-curriculum with SM2, but three constraints reshape the order:
the study runs in parallel (not a next thread); the user wants product movement
with comprehension (pure study is off the table); and SM2 is schema-invasive, to
be avoided immediately after a heavy refactor. So:

- **Thread N -- Vocab/language features + timing-stats + ADR index.** One
  meaty-but-safe feature on proven seams, plus two quick wins that touch the
  same files. Cashes in the modularization and is a safe re-warm-up.
- **Thread N+1 -- SM2 consolidation (+ adaptive selection).** Its own focused,
  schema-invasive thread; both plug the `pick_next_question` seam. The SM2
  scheduling-fields migration (reserved in ADR-025) lands here.
- **Thread N+2 -- Typing drill.** A deliberate net-new qtype: the test of
  whether the modular seams absorb a genuinely new question kind cleanly.
- **Parallel -- Study curriculum.** Throughout, feeding on each thread's fresh
  code (auditing new code teaches more per hour than re-reading the cutover).

Alternatives weighed and rejected as the immediate next thread: "SM2 next"
(raw-score winner but schema-invasive right after a refactor); "study next"
(now parallel; a reflective-only phase risks avoidance); "deferred-cleanup
thread" (more refactoring after a refactor -- interleaved into feature threads
instead); "typing next" (least de-risked by modularization; better once
re-warmed up). Full rationale in ADR-054.

---

## 3. Engineering-quality items I added (not in your list)

You asked me to fold in anything relevant to code quality. Six items, each
placed in the ranking above:

1. DONE **Automated test suite in the repo (T1, #8).** We have been writing
   throwaway jsdom and Python harnesses each commit and discarding them. The
   single highest-quality-leverage move is to keep them: a `tests/` directory
   with the WSGI-over-temp-DB pattern for the backend and the jsdom pattern for
   the frontend, plus a one-line runner. This is what lets every later item be
   refactored fearlessly -- it scores high on FOUND for that reason.
2. **Schema migration runner (T2, #11). [DONE]** The `schema_version` table exists but
   nothing reads it to migrate. Before you add columns (difficulty tuning,
   timing features, SM2 fields) you want a tiny `migrate(conn)` that checks the
   version and applies ordered `ALTER TABLE` steps. Cheap now, painful to
   retrofit after you have real data in `drill.db`.
   DONE (C-T2, wave 0): forward-only run_migrations + MIGRATIONS registry +
   schema-driven drift guard + MAIN wiring; init_db stays the v1 baseline and
   the runner layers v2..N (ADR-021/022/023). Mechanism only, registry ships
   empty; D1 consumes it. Suite 159 -> 175 green (backend 84 -> 100).
   DONE (D1, wave 1): first real consumer -- the v2 migration adds
   questions.metadata (additive NOT NULL DEFAULT '{}'), surfaced through the
   readers; runner validated end-to-end. Fixed a latent init_db defect the bump
   exposed (now stamps BASELINE_SCHEMA_VERSION=1, not the moving SCHEMA_VERSION;
   ADR-026). grading_kind from the original brief deferred to #6/#7 (ADR-025).
   Suite 175 -> 177 green (backend 100 -> 102).
3. **Assertion / invariant pass (T2, #14).** LOGIC functions already raise
   `ValueError` on violated preconditions; extend that discipline to the
   boundary seams (e.g. assert payload shape at the DATABASE->LOGIC handoff)
   and add a couple of postcondition checks in the generator (result is an int,
   no forbidden identities slipped through). High QUAL, teaches you defensive
   design.
4. **JSONL export / backup endpoint + button (T3, #15).** The `.db` file is the
   backup today. A formal export closes the import/export loop and is a natural
   teaching example of streaming a response.
5. **Structured logging + error-envelope audit (T3, #17).** One place that logs
   requests and unhandled exceptions, and a sweep confirming every handler
   returns the `{"error": ...}` envelope with a correct 4xx/5xx. Modest, but it
   is what "production quality, single-user scope" actually looks like.
6. **Docstring / status-drift cleanup + ADR index (T3, #20).** We have already
   hit stale status lines twice (the "C-019 not built yet" comments). A short
   pass to make the module header and an ADR index the single source of truth
   prevents the docs from lying as the tool grows.

A specific bug-watch item, not a feature: the **frontend lives entirely in one
1900-line HTML file**. That is not a bug, but it is the single biggest
maintainability risk, which is exactly why modularization is ranked #1.

---

## 4. Recommended sequencing (the path, not just the ranking)

The ranking tells you what is valuable; this tells you what order avoids
rework. Dependencies matter more than raw score for the first moves.

STATUS (2026-07): Phases 0-2 are DONE (foundation, arithmetic depth,
modularization). The sequencing for what REMAINS has been re-derived post-
modularization -- see section 2a and ADR-054. Phases 3-5 below are the ORIGINAL
plan text, kept as reference; where 2a and the phase text differ on ordering,
2a/ADR-054 win (notably: the study curriculum now runs in PARALLEL rather than
as a standalone Phase 3, and vocab/language + quick wins lead the next thread).

**Phase 0 -- lock the foundation (do before anything else). [DONE]**
Test suite (#8) and the migration runner (#11) -- both now complete. The
reason they came first: every Tier 1 feature either changes the generator/
selection logic (wants tests) or adds columns (wants migrations). The small
upfront cost was spent so the rest is safe. Pair this with the docstring/ADR
cleanup (#20) since
you will be touching headers anyway.

**Phase 1 -- arithmetic depth (your top content priority). [DONE]**
Do them in this order, because each builds on the last:
`operators (#4)` -> `generalize expression trees (#5)` -> `difficulty control
(#2)`. Operators is the warm-up (add dicts to the data-driven table, near-zero
risk). Tree generalization is the meaty one: the evaluator and renderer already
recurse, so this is mostly a new recursive `generate_expression` plus
parenthesization in the renderer -- a genuinely instructive piece of cs.
Difficulty then sits on top as the knob that drives depth, operand digits, and
operator set. Adaptive selection (#7) is the natural follow-on once difficulty
exists, and is a clean single-function swap. [Adaptive selection is NOT done --
it now pairs with SM2 in the next-thread plan, section 2a.]

**Phase 2 -- modularize. [DONE -- C-MOD-*, roadmap #1 COMPLETE]**
Extract the frontend JS into ES modules (`state.js`, `api.js`, `drill.js`,
`stats.js`, `speech.js`) loaded via `<script type="module">` -- no build step,
which keeps the "vanilla, no framework" property. Split `drill.py` into a small
package (`config.py`, `db.py`, `logic.py`, `http.py`, `main.py`) mirroring the
existing section comments, which is unusually low-risk here because those
sections already have a strict one-way dependency boundary. This is #1 on the
ranking but sequenced second on purpose: doing it after a round of arithmetic
work means you modularize code you understand cold, and the seams will be
obvious. It also directly serves your "understand how concerns separate" goal.
AS-BUILT: ten frontend ES modules (state, el, api, timing, stage, speech, stats,
session, drill, boot) + backend config/db/logic/http_layer/drill; the E10 atomic
cutover shipped with an enforced ownership guard. See STATUS.md and the handoffs.
DESIGN + SPIKES COMPLETE (C-MOD-design): see llm/roadmap-1-modularization-
findings.md and llm/roadmap-1-modularization-commit-plan.md, and decisions.md
ADR-049..052. Implementation (adversarial-review -> commit-planning ->
plan-review -> execute) is handed to a separate thread; the SHA/baseline for it
are in STATUS.md.
DONE (C-MOD-E10, roadmap #1 COMPLETE): both tiers are modular. Backend split
into config.py/db.py/logic.py/http_layer.py + drill.py (thread one). Frontend
extracted into TEN ES modules (state, el, api, timing, stage, speech, stats,
session, drill, boot) loaded via a single `<script type="module" src="boot.js">`
-- no build step, the "vanilla, no framework" property preserved. The E10 atomic
cutover flipped the tag, deleted the inline script, migrated the 7 classic tests
to option (b), and landed the enforced ownership guard (ADR-051). Suite 539
green. As-built details in STATUS.md and llm/handoffs/3-to-E10-cutover.md.

**Phase 3 -- the study curriculum (capstone of the learning goal).**
Once the code is modular, the codebase becomes the textbook: a guided
walkthrough that reconstructs the tool commit-by-commit (you already have a
near-perfect teaching artifact in DECISIONS.md and the spec). Structure it as
"read this layer, here is the principle it demonstrates, now extend it
yourself" -- the boundary invariant, data-oriented design, the operator-table
pattern, pure-vs-IO separation, the swappable-policy seam. This is why the
curriculum is ranked #3 but sequenced after modularization: a modular codebase
is far easier to teach from.

**Phase 4 -- SM2 consolidation.**
Fold your existing spaced-repetition engine in. High value and high learning,
but the lowest-effort score in Tier 1 because it means reconciling two schemas
and two notions of "a review." Sequence it after adaptive selection (#7) exists,
since SM2 *is* a selection policy -- it should plug into the same seam, not
bolt on beside it.
SCHEMA RESERVATION (from D1, ADR-025): the SM2 scheduling fields (ease,
interval, repetition, next-review) are NOT yet added -- they land here, after
#7, as their own migration. The grading_kind column from the original D1 brief
was also deferred to this point: decide then whether a persisted grading axis is
needed at all, and if so add it WITH the SM2 fields in one migration (it must
FEED validate_answer's qtype dispatch, never fork it). Meanwhile per-question
experimental state can live in questions.metadata (the uncommitted hatch D1
added). The migration mechanism (#11) and a worked example (D1) are in place, so
adding these is the documented four-step procedure -- mind BASELINE_SCHEMA_VERSION
(ADR-026) when bumping.

**Phase 5+ -- breadth (new drills) and depth (stats/UX).**
Add drills cheapest-first: logic (#9) and code (#10) reuse the existing text/MC
structure with almost no new infrastructure; typing (#12) and the timed mode
(#13) share the `elapsed_ms` plumbing. Geography-visual, music, and handwriting
are real new input modes (Tier 4) -- fun, but each is a mode unto itself.

---

## 5. Notable judgment calls (where I deviated from the obvious)

- **Modularization outranks the arithmetic work** on raw score (FOUND + QUAL +
  LEARN all max), but I sequenced arithmetic first anyway. Score and sequence
  are different questions: modularization is most valuable, but doing one
  arithmetic round first means you refactor code you fully understand. The
  ranking and the path intentionally disagree here, and that is the point of
  separating them.
- **SM2 ranks Tier 1 despite being the hardest Tier 1 item.** Its USER/LEARN/
  FOUND scores carry it; the effort cost is real (schema reconciliation), which
  is why it is sequenced late within the tier rather than demoted.
- **Mastery map (Mode D) ranks higher (T3, #16) than its tiny effort score
  would suggest** because you clearly care about it (the "Victor ideal") and it
  scores well on USER/LEARN. It is the one Tier 3/4 item I would happily pull
  forward if it is the thing that keeps you engaged -- motivation is a real
  axis the model only partly captures.
- **Chart.js ranks low (T4)** not because charts are bad but because FOUND is
  minimal (nothing depends on it) and the stats view is already useful as text.
  Pure polish; do it when you want it, not because it is on a list.
- **"Document 0.0.0.0 binding" is near the bottom (T4) because it is nearly
  already done** -- the host is env-overridable (`DRILL_HOST`), so this is a
  one-line README note, not a feature. Catalan-number expression sampling (from
  your notes) is deliberately omitted from the ranked list: it is a neat
  property but, as you already concluded, overkill for drilling; revisit only
  if you want *guaranteed* structural diversity, in which case it attaches to
  the tree generator from Phase 1.
- **Out of scope, correctly:** multi-user/auth (#36), SpeechRecognition
  pronunciation (#35), and the dictionary-dump pipeline (#33) all sit at the
  bottom. The first two violate the single-user scope or were already deferred
  with good reason; the third is a large data-engineering prong that is its own
  project.

---

## Appendix -- Full per-axis scores

Reproduce with `python3 roadmap_model.py`. Columns: USER, LEARN, FOUND,
EFFORT, RISK as defined in section 1 (EFFORT and RISK pre-inverted).

| # | Item | Score | U | L | F | E | Q | R |
|--:|------|------:|--:|--:|--:|--:|--:|--:|
| 1 | Modularize: extract JS modules + split Python | 4.56 | 5 | 5 | 5 | 3 | 5 | 3 |
| 2 | Extend arithmetic: difficulty (digits/#ops/operators) | 4.50 | 5 | 5 | 4 | 4 | 4 | 4 |
| 3 | Study curriculum from the codebase | 4.44 | 5 | 5 | 4 | 3 | 4 | 5 |
| 4 | Extend arithmetic: operators (^, mod, etc.) | 4.32 | 5 | 4 | 3 | 5 | 4 | 5 |
| 5 | Generalize expression generation (nested trees) | 4.32 | 5 | 5 | 3 | 4 | 4 | 4 |
| 6 | Consolidate SM2 (spaced repetition) engine | 4.04 | 5 | 5 | 4 | 2 | 3 | 3 |
| 7 | Adaptive question selection (swap pick_next_question) | 3.98 | 4 | 5 | 4 | 3 | 3 | 4 |
| 8 | Automated test suite checked into the repo | 3.94 | 3 | 4 | 5 | 3 | 5 | 5 |
| 9 | Logic/deduction drill (truth tables, syllogisms) | 3.80 | 4 | 5 | 3 | 3 | 3 | 4 |
| 10 | Code drill (what does this output?) | 3.72 | 4 | 4 | 3 | 4 | 3 | 4 |
| 11 | Schema migration runner (version-aware ALTER) | 3.58 | 3 | 4 | 4 | 3 | 4 | 4 |
| 12 | Typing/text-entry speed drill | 3.50 | 4 | 3 | 3 | 4 | 3 | 4 |
| 13 | Timed-round / speed-drill mode (use elapsed_ms) | 3.50 | 4 | 3 | 3 | 4 | 3 | 4 |
| 14 | Assertion/invariant pass (boundary + pre/postconditions) | 3.44 | 2 | 4 | 3 | 4 | 5 | 5 |
| 15 | JSONL export/backup endpoint + button | 3.18 | 3 | 2 | 3 | 4 | 4 | 5 |
| 16 | Mastery map / explorable space (Mode D) | 3.14 | 4 | 4 | 3 | 1 | 3 | 2 |
| 17 | Structured logging + error envelope audit | 3.12 | 2 | 3 | 3 | 4 | 4 | 5 |
| 18 | Timing stats (compute/display elapsed_ms) | 3.12 | 3 | 3 | 2 | 4 | 3 | 5 |
| 19 | Stats depth: most-missed, over-time, per-bank | 3.08 | 3 | 3 | 3 | 3 | 3 | 4 |
| 20 | Module docstring/status drift cleanup + ADR index | 3.04 | 2 | 2 | 3 | 5 | 4 | 5 |
| 21 | Alphabet/romanization drill | 3.04 | 3 | 3 | 2 | 4 | 3 | 4 |
| 22 | Grammar exercises (fill-in / reorder) | 3.04 | 3 | 4 | 2 | 3 | 3 | 3 |
| 23 | Trivia importers (OpenTriviaDB/QA, Freebase) | 2.86 | 3 | 2 | 3 | 3 | 3 | 4 |
| 24 | Vocabulary importers (CodingFriends, doozan) | 2.86 | 3 | 2 | 3 | 3 | 3 | 4 |
| 25 | Dashboard (live stats beside drill, Mode C) | 2.82 | 3 | 3 | 2 | 3 | 3 | 3 |
| 26 | Geography visual mode (point-to on a map) | 2.68 | 3 | 3 | 2 | 2 | 3 | 3 |
| 27 | AI-generated content (server-side API) | 2.64 | 3 | 3 | 2 | 3 | 2 | 2 |
| 28 | wordfreq frequency ranking integration | 2.62 | 2 | 3 | 2 | 3 | 3 | 4 |
| 29 | Document 0.0.0.0/WSL binding (already env-overridable) | 2.54 | 2 | 1 | 2 | 5 | 3 | 5 |
| 30 | Music interval/rhythm drill | 2.40 | 2 | 3 | 2 | 2 | 3 | 3 |
| 31 | Chart.js rendering in stats view | 2.36 | 2 | 2 | 1 | 4 | 3 | 4 |
| 32 | In-browser bank editor | 2.18 | 2 | 2 | 2 | 2 | 3 | 3 |
| 33 | Dictionary/encyclopedia dump pipeline | 2.08 | 2 | 3 | 2 | 1 | 2 | 2 |
| 34 | Handwriting canvas (CJK/Arabic/Devanagari) | 1.90 | 2 | 3 | 1 | 1 | 2 | 2 |
| 35 | Pronunciation via SpeechRecognition (deferred) | 1.46 | 1 | 2 | 1 | 2 | 2 | 1 |
| 36 | Multi-user / auth / pooling (out of scope) | 1.32 | 1 | 2 | 1 | 1 | 2 | 1 |

### Sensitivity check

Re-running the model under four weightings -- base (user-led), learning-max,
ship-fast (effort-weighted), and quality-first -- keeps the same ~8 items in
the top tier in every scenario. The top five never fall below rank 6 except SM2
(which drops under effort-weighting, as expected for the largest item). The
ranking is therefore robust to reasonable disagreement about the weights.
