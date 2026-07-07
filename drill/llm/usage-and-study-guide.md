# Usage and Study Guide

STATUS: reference doc, written at the close of the authoring thread (A1-A3).
Its purpose is to make a stretch of DAILY USE productive -- both as study
(understanding the codebase) and as data collection (learning what to build
next from real friction, not memory). Five sections:

  1. Pre-use wiring -- what to record before daily use, and what to defer.
  2. Study sequence -- the order to read the files, and the question each
     file should leave you able to answer.
  3. Testing workflows -- how to exercise the system to maximize what you
     learn.
  4. Observations log -- a dated running template so the next thread's spec
     writes itself from real use.
  5. Open follow-ups -- the named, agreed, not-yet-built items this use
     period should inform.

Nothing here is committed to a thread; it is a guide to fold future work
from. Related docs: roadmap.md (ranked plan), feature-backlog-2026-07.md
(new candidates), decisions.md (the reasoning archive -- ADR-058/059/060
are the authoring thread's).

================================================================================
1. PRE-USE WIRING -- record the unreconstructable, defer the speculative
================================================================================

Principle: premature instrumentation records fields you have not learned to
want, in shapes you will regret. Add almost nothing before starting, for one
reason -- the event log is already rich enough to reconstruct most patterns
retroactively. The exceptions are events that happen and vanish if unrecorded.

WHAT IS ALREADY CAPTURED (needs surfacing, not wiring):
The responses table already stores, per answer: question_text, answer_text,
user_input (what you actually typed, not just right/wrong), correct,
elapsed_ms, answered (timestamp), difficulty, leaf_count. That answers "what
do I get wrong," "what do I type when wrong" (near-miss vs blank), "how long
do items take," "how does accuracy move over time," and per-bank/per-question
cuts of all of these. The failures and leeches reports read some of it. The
rest is collected-but-unsummarized -- which is exactly what the roadmap's
stats-depth items cover (timing-stats, most-missed, over-time, per-bank). So
the first "wiring" is really the stats-depth render work, not new collection.

WHAT IS NOT CAPTURED, ranked by whether to wire it NOW:

  WIRE BEFORE DAILY USE (cheap, and unreconstructable after the fact):
  - Hint/reveal usage. The review UI has a progressive hint-reveal control
    (Thread N.1), but revealing a hint writes NOTHING to the database. Whether
    you recalled unaided vs gave up and looked is the single most valuable
    signal for the future recall qtype (ADR-060) and for spotting
    memorized-shallow items -- and a non-recorded reveal leaves no trace.
    Minimal wiring: record a hint-reveal count (or a flag) on the response row
    when the answer is finally submitted.
  - Skip / abandon. Distinguish "I skipped this" from "I never reached it in
    the session." Also unreconstructable, also cheap.

  VERIFY (not wiring, just a check):
  - elapsed_ms is nullable; a NULL is indistinguishable from "not measured."
    Confirm it is actually populated on every review path before trusting
    timing data.

  DEFER (add when a specific question makes you want it, never speculatively):
  - Session-level mood / self-rated confidence, tags-at-review-time,
    answer-edit history, anything session-shaped rather than answer-shaped.

Do NOT build the wiring as part of studying. It is its own small, deliberate
change (touches the review UI + one response column). Decide it explicitly.

================================================================================
2. STUDY SEQUENCE -- dependency order, bottom-up
================================================================================

Read in the order the code's own layering enforces (config <- db <- logic <-
http <- main). Bottom-up means every file uses only things you have already
seen; top-down forces you to hold unexplained machinery in your head.

  config.py  (the leaf: pure data, no logic)
    Q: What are the seeded categories, and why those?
    Q: What are the tunable constants (throttle budgets, leech threshold, EF
       bounds) and roughly what does each control?
    Q: What do QTYPES contain, and what is deliberately excluded (arithmetic)?
    You finish this file knowing the whole system's vocabulary.

  db.py  (schema + every read/write)
    Q: What are the four tables (categories, banks, questions, responses,
       plus question_schedule) and their columns?
    Q: Which columns are nullable-and-optional (elapsed_ms, difficulty,
       leaf_count) and why does that pattern recur?
    Q: What do _normalize_question_dict + insert_questions_bulk do -- the
       import funnel the authoring thread extended?
    Answer fully: "how does a question get from a JSONL line to a stored row?"

  logic.py  (the heart: pure functions only -- budget the most time here)
    Q: How does advance_schedule_state implement SM2 (EF update, interval
       progression, lapse handling)?
    Q: How does apply_new_question_throttle decide what is introduced today?
    Q: How does normalize_text make grading lenient (and what does it
       deliberately NOT strip -- accents, hyphens)?
    Q: How do the five views (render_table, failures/leeches/preview/
       dry_run) turn rows into text?
    Q: (authoring thread) How do author_parse / author_render / author_template
       work, and how does flush_author_block keep the parse flat?
    Answer fully: "given my answer, how is the next due-date computed?"

  http_layer.py  (the web routes)
    Q: For each endpoint, which db reads and logic calls does it compose?
    Q: Especially /api/answer -- the whole review loop in one handler.
    Answer fully: "what happens end-to-end when I submit an answer?"

  drill.py  (the composition root -- you extended this)
    Q: How does main dispatch (serve, then AUTHORING_COMMANDS, then
       REPORT_COMMANDS)?
    Q: How do the add/push shells wire the pure author_parse to the db?
    This reads fast; you wrote part of it.

  THEN the tests, as a SECOND pass (not first):
    tests/test_logic.py is the executable specification. The SM2 invariant
    section tells you exactly what the scheduler is guaranteed to do. Reading
    tests before their code makes you memorize assertions without
    understanding mechanisms.

Most useful habit while reading: keep a running list of every "why is it done
this way" and check each against decisions.md. Almost every non-obvious choice
has an ADR naming the rejected alternatives. The code is the conclusion;
decisions.md is the reasoning.

(Aside: terminal_output.py is no longer in this repo -- it was a general
module, now extracted to the top-level pyutils/ package; see ADR-059 and
pyutils/README.md. Not part of the drill study path.)

================================================================================
3. TESTING WORKFLOWS -- exercise every rail deliberately
================================================================================

Goal: exercise each grading rail on purpose rather than drifting into only the
easy one. The failure modes you most need to find live in the paths you would
naturally avoid.

AUTHOR ACROSS ALL THREE GRADING SHAPES in the first week (use the push filter):
  - Short-answer FACTS (capitals, dates, definitions) -- the string-match
    rail, which works today.
  - Self-assessment CONCEPT questions (sm2-style, paragraph criteria) --
    deliberately, because this is where the false-leech problem surfaces and
    proves or disproves the need for the recall qtype (ADR-060). Expect these
    to grade as "wrong" when you do not type the criterion verbatim; that
    friction is the data.
  - Generable ARITHMETIC via the existing generator.
Drilling all three tells you which grading modes actually serve you before
building more.

USE BOTH AUTHORING FACES so you learn which fits your flow:
  - drill add --bank X --category Y   (terminal, $EDITOR loop; one-offs)
  - :w !drill push --bank X           (nvim, pipe the buffer; batches)
    (and :make with makeprg=drill\ push\ --bank\ X\ % for quickfix errors)
Which becomes your daily driver informs whether the reserved in-buffer
bank:/category: header (ADR-058) is worth building.

DRILL DAILY, even briefly. The entire value of spaced repetition is
time-decay behavior, which only manifests across days. One long session
teaches almost nothing about scheduling; ten short daily ones expose whether
intervals feel right, whether the throttle paces new items sanely, and which
items become leeches.

ONCE A WEEK, run the reports and read them as a user:
  drill stats | drill failures | drill leeches | drill preview | drill dry-run
Ask of each: "does this tell me something I would act on?" Every time a report
leaves you wanting a cut it does not offer, that is a stats-depth backlog item
writing itself.

DELIBERATELY DO THE ANNOYING THINGS (adversarial week-one use finds cheap-to-
fix edges):
  - Submit near-miss answers to test grading leniency (casing, punctuation,
    extra words).
  - Let some items lapse repeatedly to see leech detection fire.
  - Author a malformed buffer and confirm the file:line: error lands in your
    nvim quickfix.
  - Try to create a bank with a typo'd --bank and no --category; confirm it
    refuses (option ii, ADR-058) rather than minting a stray bank.

================================================================================
4. OBSERVATIONS LOG -- append-only, dated
================================================================================

Append a dated entry per session or per notable friction. When the next thread
starts, its spec is already half-written from these. Suggested shape:

  ## YYYY-MM-DD
  - USED: <which faces/commands/banks>
  - FRICTION: <what annoyed me, what I wanted that was not there>
  - GRADING: <false leeches? near-misses graded wrong? felt-right?>
  - SCHEDULING: <intervals too short/long? new-item pace? leeches?>
  - REPORT WISH: <a cut a report did not offer>
  - BUG/ROUGH EDGE: <anything broken or surprising>
  - IDEA: <feature thought, however rough>

(Start entries below this line.)

--------------------------------------------------------------------------------

================================================================================
5. OPEN FOLLOW-UPS this use period should inform
================================================================================

Agreed, recorded, NOT yet built (ADR-060 unless noted). Daily use is the input
that converts each from a guess into a specified thread:

  - Self-graded recall qtype: prompt shows a criterion after the attempt; user
    presses pass/fail instead of string-matching. The honest home for
    self-assessment content. USE TELLS US: how often free_response grading
    buries concept questions as false leeches -- i.e. how urgent this is.

  - Category-taxonomy re-grain: category = grading/session domain, subject =
    tags. USE TELLS US: whether subject collision in "trivia" actually hurts
    coverage/balance once you have banks across several subjects.

  - Pre-use wiring (section 1): hint-reveal + skip capture, and surfacing the
    existing log via stats-depth. USE TELLS US: which cuts you actually reach
    for.

  - Keyboard-first flow + grade-keys (backlog, 3.28): pairs with the recall
    qtype's pass/fail step. USE TELLS US: where input friction actually is.

BUILD TRACK (independent of the above, safe next thread per roadmap +
backlog): a generable-math bundle -- bitwise arithmetic (4.04, the standout),
number-base conversion, and linear solve-for-x -- all data+eval additions on
the existing arithmetic tree engine. Low risk, high learn, no schema change,
does not wait on usage data. A good re-warm-up thread.
