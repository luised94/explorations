# Drill Tool -- Phase 0/1 Execution Plan

Answers the actionable parts of the planning questions: how to modularize and
add tests without over-abstracting, a curriculum spec, a scheduler/difficulty
design, an adversarial review, and a data-model analysis. Companion to
ROADMAP.md.

Standing constraints honored throughout: single-user (no concurrency/auth),
data-oriented, abstraction- and indirection-apprehensive, pure transformations
at the core, IO quarantined at edges. ASCII only.

---

## A. Modularization -- how hard, and how to keep it targeted

**Difficulty: low. About half a day for the backend, half a day for the
frontend.** The reason it is cheap is that the hard part -- the actual
separation of concerns -- is already done. The code is sectioned CONFIG /
DATABASE / LOGIC / HTTP / MAIN with a strict one-way dependency rule, and a
grep confirms LOGIC has zero references to `connection.`, `bottle.`, or
`sqlite3`. The boundary is real, not aspirational. Modularizing is therefore
mechanical: cut along lines that already exist. The risk is not the split; the
risk is using the split as an excuse to add indirection. Don't.

### Backend: `drill.py` (2252 lines) -> a small package

One file per existing section, same names, same boundary:

```
drill/
  __init__.py      # nothing but version; not a re-export hub
  config.py        # CONFIG: constants, SEED_CATEGORIES, OPERATOR_CONFIG
  db.py            # DATABASE: connect, init_db, readers/writers (28 fns)
  logic.py         # LOGIC: pure fns -- generator, validator, summaries (22)
  http.py          # HTTP: the Bottle app + route handlers (14)
  main.py          # MAIN: init_db + app.run + __main__
```

Coupling points to handle (there are only four, all explicit):
- `OPERATORS` / `OPERATOR_SYMBOLS` -- the assembled operator table. Lives in
  `logic.py` (it holds callables), reads scalars from `config.py`. One import.
- `app = bottle.Bottle()` and the `DATABASE_PATH` module global -- both move to
  `http.py`; `main.py` rebinds `DATABASE_PATH` at startup (it already does).
- `_MODULE_DIRECTORY` for serving index.html -- moves to `http.py`.
- Import direction enforces the boundary: `http` imports `db` and `logic`;
  `logic` imports `config`; `db` imports `config`; nothing imports `http`.
  If you ever find `logic` importing `db`, the boundary broke -- that import
  line is your tripwire.

What NOT to do: no repository/DAO classes, no service layer, no dependency
injection, no ABCs. The functions are already pure-or-IO and take plain data.
A class here would add indirection without removing duplication. Keep them as
module-level functions. The package is the only new structure; everything
inside stays flat.

### Frontend: one 1900-line `<script>` -> ES modules (no build step)

This is the higher-value half (it is the worst maintainability hotspot) and is
still low-risk because the JS already has clear functional clusters. Split into
ES modules loaded with `<script type="module">` -- native, no bundler, keeps
the "vanilla, no framework" property:

```
app/
  state.js     # the single state object + ZERO_STATS + el cache
  api.js       # apiGet/apiPost/readJson
  drill.js     # loadQuestion, renderQuestion, gradeAndShow, phase machine
  session.js   # start/record/endSession, run log, renderSessionUI
  stats.js     # onStatsToggle, renderStatsPanel (C-019b)
  speech.js    # the speechSynthesis quarantine (C-018a)
  timing.js    # nowMs + the elapsed_ms mark (C-018c)
  boot.js      # wires listeners, the entry point
```

`index.html` keeps the markup + CSS and one `<script type="module"
src="app/boot.js">`. State stays a single shared object imported where needed
(do not turn it into a store/observable -- that is the premature reification to
avoid). The serve handler already returns static files, so serving an `app/`
directory is a one-line root change.

Caveat worth stating: `file://` blocks ES module loading (CORS), so the app
must be opened through the server (`python -m drill`), which is already how it
runs. No regression, but note it so nobody double-clicks the HTML and is
confused.

**Sequence note:** do one round of arithmetic work *first* (Section D), then
modularize. You will be cutting code you just touched and understand cold, and
the seams will be obvious rather than guessed.

---

## B. Tests -- how hard, and what is worth testing

**Difficulty: very low, because the tests already exist -- they are just being
thrown away each commit.** Every commit this session shipped a jsdom harness or
a WSGI-over-temp-DB Python harness and then discarded it. Phase 0 is mostly
*keeping* them, not writing them.

```
tests/
  test_logic.py     # pure LOGIC: generator validity, validate_answer,
                    # summarize_correctness, summarize_stats, pick_next_question
  test_db.py        # DATABASE over a temp DB: insert/read round-trips,
                    # get_responses_for_stats filters, elapsed_ms persistence
  test_http.py      # WSGI against the app + temp DB: every endpoint, the 400s
  frontend/         # the jsdom suites already written (C-018a/c, C-019b)
  run.sh            # python3 -m pytest tests + node tests/frontend/*.js
```

What to test, targeted (not coverage theater):
- **Pure LOGIC is the high-value target** -- it is deterministic and needs no
  DB, so tests are fast and total. Generator invariants especially: integer
  results only, no forbidden identities, division stays integral. These are the
  properties that will break when you add operators and nesting (Section D), so
  the tests pay off immediately.
- **The boundary contracts**: the `{question_text, expected, ...}` payload
  shape, the `{error}` envelope on 400s. These are the seams modularization
  will move; tests make that move safe.
- **What NOT to test**: Bottle's routing, sqlite itself, the DOM rendering
  pixel-by-pixel. Test your logic and your contracts, not your dependencies.

Property-based testing (hypothesis) is worth one targeted use: the arithmetic
generator. "For any enabled operator set and difficulty, the generated
expression evaluates to an integer and contains no forbidden identity" is a
property, and hypothesis will find the edge cases you won't. That is a
high-learning, high-value single application -- not a mandate to property-test
everything.

**Combined Phase 0 estimate: ~1-1.5 days** for both modularization and tests,
precisely because both are consolidation of work already done rather than new
construction.

---

## C. Self-study curriculum -- specification

You asked for the curriculum to be *generated*; this is its design spec (the
generation itself is a Phase 3 task, best done once the code is modular so each
lesson maps to a file). Grounded in modern learning science, supplemented by
older traditions, using LLM capabilities where they genuinely help.

### Learning-science basis (the non-platitude version)
- **Retrieval practice over re-reading.** Each lesson ends with the learner
  reconstructing or extending code from a blank, not re-reading it. (This is
  literally what the tool itself does -- the curriculum eats its own dog food.)
- **Spaced repetition of concepts**, not just facts. Concepts (the boundary
  invariant, pure-vs-IO, the data-driven table) recur across lessons at
  widening intervals -- and you have an SM2 engine to schedule them (Section E
  ties this together: the curriculum's own review schedule is an SM2 bank).
- **Interleaving.** Don't teach all of DATABASE then all of LOGIC; interleave a
  DB reader with the LOGIC that consumes it, because that is how they are used.
- **Worked-example-to-faded-guidance.** Early lessons show a full commit; later
  ones give the spec and DECISIONS entry and ask the learner to produce the
  code, fading the scaffolding -- the documented "expertise reversal" remedy.
- **Desirable difficulties.** The exercises should be effortful (extend the
  generator to N operands) not trivial (rename a variable).

### Traditional supplements
- **The Feynman pass**: each lesson requires explaining the concept in plain
  prose with no jargon (DECISIONS.md is already a model of this).
- **Socratic commit archaeology**: the real git/commit history (C-001..C-019b)
  is the syllabus. Each lesson asks "why did the author decide X?" before
  revealing the DECISIONS entry. The repo is unusually well-suited to this
  because the decisions are already written down.

### Where the LLM is actually useful (not platitudes)
- Generating *variations* of an exercise at a target difficulty (this is the
  same capability as the AI-content feature, pointed inward).
- Acting as the Socratic questioner / reviewer of the learner's extension.
- Producing the spaced-repetition items (concept Q&A) as a vocabulary/logic
  bank the tool itself drills.

### Structure (maps to the modular codebase)
```
Module 0  Orientation: run it, read the spec + DECISIONS, the boundary invariant
Module 1  CONFIG + data-oriented design: why scalars-not-callables, the operator table
Module 2  LOGIC I: pure functions, the expression tree, evaluate/render recursion
          Exercise: add an operator (faded: add modulo yourself)
Module 3  LOGIC II: the generator, forbidden identities, validate_answer
          Exercise: generalize to nested trees (the real cs lesson)
Module 4  DATABASE: sqlite, row-to-dict, the IO boundary, why no logic in SQL
Module 5  HTTP: thin handlers, the clock-reader rule, the error envelope
Module 6  The seam: pick_next_question as swappable policy -> adaptive + SM2
Module 7  Frontend: state-as-single-source, derived render, the speech quarantine
Capstone  Design + build a new drill type end to end (logic or code drill)
```

Each module: read (worked example) -> explain (Feynman) -> extend (retrieval/
desirable difficulty) -> the extension's concept enters the SM2 review bank.

---

## D. Arithmetic depth + the generator (the cs core)

This is sequenced first because it is instructive, low-risk, and everything
downstream (difficulty, adaptive, SM2) wants it to exist. Order within:

1. **More operators (#4).** Add dicts to `OPERATOR_CONFIG`. Exponent and modulo
   need operand-range care (exponent explodes fast -- cap it; modulo needs a
   non-zero divisor and is only interesting when `a > b`). Pure data + a
   generate/eval/render entry. Near-zero risk; the evaluator/renderer already
   handle any registered operator.
2. **Generalize expression generation (#5).** The genuine cs piece. The
   evaluator and renderer ALREADY recurse over nested `{op,left,right}` nodes
   (verified) -- only `generate_expression` is flat. So this is: a recursive
   generator that builds a tree of depth/operand-count drawn from difficulty,
   plus correct parenthesization in the renderer (precedence-aware), plus
   keeping the integer-result and no-identity invariants under composition
   (e.g. division must stay integral through nesting -- generate top-down from
   the quotient). This is where property-based tests earn their keep.
   (Catalan-number uniform tree sampling from your notes attaches HERE if you
   want guaranteed structural diversity -- still optional, still arguably
   overkill, but this is the seam it plugs into.)
3. **Difficulty control (#2).** Now that depth and operator set are parameters,
   difficulty is the knob that sets them: operand digit count, number of
   operations (tree size), allowed operators. A pure function
   `difficulty_to_params(level) -> {max_digits, num_ops, operators}` keeps it
   data-oriented and testable. This is also what writes a meaningful value into
   the long-unused `questions.difficulty` column for stored banks.

---

## E. Schedulers and difficulty tuners (feature #6) -- the design

You want to programmatically control session shape -- how many items, which
items, adapting over time. This is real and the architecture already has the
seam for it: `pick_next_question(candidates, history)` is the single function
the HTTP layer calls to choose the next item. Every scheduler is a different
implementation behind that one seam. Keep it that way -- one seam, swappable
pure policies, no scheduler framework.

### The seam, generalized (minimal change)
Today: `pick_next_question(candidates, history) -> question | None`.
Generalize the *inputs* it is allowed to see, not the structure:
```
select_next(candidates, context) -> question | None
  context = { history:[ids], stats_by_item:{id: {seen,correct,last_ts,...}},
              session_config:{...}, now:iso }
```
`context` is plain data assembled by HTTP from the DB (the clock-reader rule
holds: HTTP passes `now` in; the policy never reads the clock). Each scheduler
is a pure function of `(candidates, context)`. This is a projection: random
selection ignores all of context except history; adaptive reads
`stats_by_item`; SM2 reads `last_ts` + an interval. Same signature, three
bodies.

### The schedulers (each a pure function, ranked by value)
1. **Adaptive by accuracy (#7).** Weight selection toward items with low recent
   accuracy. Pure: `(candidates, stats) -> weighted choice`. One function.
2. **SM2 (#6 consolidation).** SM2 *is* a scheduler: it reads each item's
   ease/interval/last-review and is "due" or not. Plug your existing engine in
   behind `select_next`; the only integration work is mapping its state onto
   per-item fields (Section F: this needs a place to store ease/interval).
3. **Difficulty tuner (the dynamic knob).** A pure controller:
   `next_difficulty(recent_accuracy, current) -> level` -- raise on a hot
   streak, lower on misses (a simple proportional controller; this is a
   genuinely nice control-theory-lite learning bite). Feeds Section D's
   `difficulty_to_params`.

### Session design (how many items, shape)
`sessions.config` is an unused `'{}'` JSON column -- it is the designed home for
this. A session config is plain data: `{length:20, scheduler:"adaptive",
difficulty:"adaptive", mix:{arithmetic:0.5, vocab:0.5}}`. A pure
`plan_session(config) -> session_plan` turns intent into a target item
count/mix; the scheduler fills it. No new tables; the slot already exists.

---

## F. Does the data model accommodate all drill types? (the projection question)

This is the sharpest question in the set, and the answer is: **mostly yes -- the
`questions` row is already a general "prompt -> answer" structure, and most
drill types are projections of it. Three types strain it, and exactly one
breaks it.** Worth designing now, before banks are populated, because changing
the answer model after you have data is the expensive kind of change.

The general record today:
`{qtype, question(prompt), answer, alternatives[], distractors[], hints[],
media_url, tags[], difficulty}` + `bank.language` + JSON slots
(`bank.metadata`, `category.config`).

| Drill type | Projection of the general record? | Notes |
|---|---|---|
| arithmetic | Yes (as payload, not a stored row) | ephemeral; generated, projects onto `{qtype,question_text,expected}` |
| vocab / translate | Yes | prompt=term, answer=translation, language on bank |
| trivia free_response | Yes | prompt=Q, answer=A |
| multiple_choice | Yes | uses `distractors[]` |
| identify (image) | Yes | uses `media_url` |
| music interval | Yes | audio via `media_url`, like identify |
| alphabet / romanization | Yes | like translate |
| code (what outputs?) | Yes | snippet is text; wants `<pre>` rendering only |
| logic (truth table/syllogism) | Yes, with a JSON blob | structured premises live fine in a metadata/JSON field |
| grammar fill-in | Yes | answer is the token; reorder wants an ordered-set answer |
| typing speed | Degenerate fit | `answer == prompt`; the real metric is `elapsed_ms`, not correctness -- it projects, but scoring differs |
| **geography point-on-map** | **No** | answer is a coordinate/region, not a string -- the one type the string-answer model cannot express |

**The structural insight:** the model is really `prompt -> expected-answer +
how-to-grade`. What varies across types is not the prompt (always renderable
content + optional media) but the **answer/grading kind**:
- *string-equality* (with alternatives) -- covers the large majority,
- *numeric* (arithmetic -- already a separate validate branch),
- *speed* (typing -- correctness is trivial, time is the score),
- *spatial* (geography -- distance-to-target),
- *set/order* (grammar reorder).

Today `qtype` conflates "what kind of prompt" with "how to grade." The
targeted, non-over-engineered move is to recognize that **grading kind is the
real axis**, and there are only a handful. You do not need a polymorphic answer
hierarchy; you need `validate_answer` to dispatch on a small grading-kind enum
(it already special-cases arithmetic -- this just names the pattern). Most types
share `string`. Spatial is the one that needs a genuinely different answer
representation (store a region id or lat/long + tolerance), and it is fine for
that to be the one type that carries an extra JSON field.

**Recommendation:** before adding new drill types, do a small design pass (half
a day, mostly thinking) that (a) names the grading-kind enum, (b) confirms
`validate_answer` dispatches on it, and (c) decides that structured prompts
(logic premises, spatial targets) live in a per-question JSON `metadata` column
-- which the schema does NOT yet have (banks have `metadata`, questions do
not; adding it is one `ALTER TABLE`, which is exactly why the migration runner
in Section B is sequenced early). This keeps every type a projection of one
record, with one honest extension point (the JSON slot) for the genuinely
structured cases, and no premature class hierarchy.

---

## G. Adversarial review (Acton / Carmack / Muratori / Victor / Nelson)

Operational lenses, tuned to no-platitude critique. Where they disagree with
the plan above, the disagreement is the point.

**Mike Acton (data-oriented design).** "Where is your data, what shape, how
much, how often touched? You have a *single user* and a *local sqlite file* --
the entire 'concurrency/pooling' branch is solving problems you do not have.
Good that it is ranked last. But: you are storing question banks as rows with
JSON-blob columns (`alternatives`, `distractors` as TEXT). For a drill that
pulls one random row at a time, fine -- the access pattern is trivial. Don't
let anyone talk you into an ORM; you have none now, keep it that way. The
generator producing a tree of dicts (`{op,left,right}`) per question is
pointer-chasing for a structure that is always tiny -- it is fine *because* it
is tiny and not hot, but know that you are choosing clarity over layout
deliberately, not by default." Verdict: plan passes; watch that the JSON slot
in Section F does not metastasize into a schemaless dumping ground.

**John Carmack.** "The single best thing here is that the boundary is real and
testable, and you are finally keeping the tests. Do that first, not 'after a
round of arithmetic' -- you want the safety net under you *before* you change
the generator, not after. I'd reorder: tests are Phase 0.0." This is a direct
challenge to my sequencing, and he is right: pull the LOGIC tests in front of
the arithmetic work, since the arithmetic work is what stresses them. "Also:
2252 lines in one Python file is fine to *read*; the modular split is for your
understanding, not the machine's. Don't pretend it is a performance or
correctness win. It is a learning win. Be honest about why you are doing it."

**Casey Muratori (compression-oriented, anti-premature-abstraction).** "Your
`select_next` generalization in Section E is the dangerous one. You are adding a
`context` dict 'so future schedulers can read it' before you have written two
schedulers. That is speculative generality -- the thing you said you don't want.
Write the adaptive scheduler *concretely*, with the exact inputs it needs.
Write SM2 concretely. THEN look at the two and compress out what is actually
shared. The common signature will reveal itself; do not design it up front." A
sharp, correct hit: build two schedulers, then extract the seam from their
overlap, rather than designing the generalized seam speculatively. Amend
Section E accordingly.

**Bret Victor.** "Everything you have is a verbal/numeric loop. Where is the
*seeing*? The mastery map (Mode D) is ranked Tier 3 -- that is the only item
that changes the learner's relationship to their own knowledge from 'a number
went up' to 'I can see the shape of what I know and don't.' You are
under-valuing it because it scores low on effort. The question is not 'is it
cheap' but 'does it change what the tool *is*.' Consider pulling a minimal
version forward: even a static grid of banks colored by accuracy, clickable to
drill, is the seed." Legitimate reprioritization: a *minimal* mastery grid is
higher value-per-effort than the full Mode D and worth pulling into Tier 2.

**Ted Nelson.** "Your 'curriculum' and your 'code' and your 'decisions' are
three separate documents that will drift. They should be one deeply
interlinked structure -- the DECISIONS entry, the code it describes, and the
lesson that teaches it, transcluded, not copied. You already felt this pain:
you have hit 'stale status line' drift twice. That is the documents lying to
each other because they are separate. The curriculum should *link into* the
real code and decisions, not restate them." A genuine insight: the curriculum
(Section C) should reference code and DECISIONS by anchor, never duplicate
them, so it cannot drift -- and the recurring drift bug is evidence for it.

### Reprioritizations from the review
1. **Tests move to Phase 0.0, before arithmetic** (Carmack). The net of the
   change you are about to make should exist first.
2. **Build two schedulers concretely, then extract the seam** (Muratori).
   Delete the speculative `context` design in E; let it emerge.
3. **Pull a minimal mastery grid into Tier 2** (Victor). Not full Mode D -- a
   static accuracy-colored, clickable bank grid. High identity-changing value.
4. **Curriculum links, never copies** (Nelson). Anchors into code/DECISIONS;
   drift becomes structurally impossible.
5. **Name the grading-kind axis before adding drills** (Acton + the projection
   analysis). One enum, one JSON slot, no hierarchy.

### High-value features the review surfaced (not on the original list)
- **A "session replay" / mistake review** at end of run: show the items you
  missed, drill just those. Cheap (the run log already holds the data), high
  pedagogical value (retrieval practice on exactly your gaps).
- **A grading-kind enum + per-question JSON `metadata` column** -- the
  foundation that makes logic/geography/grammar clean rather than hacked.
- **Concept-review bank auto-built from DECISIONS.md** -- the curriculum's
  spaced-repetition items, drilled by the tool itself (Nelson's interlink made
  concrete).
