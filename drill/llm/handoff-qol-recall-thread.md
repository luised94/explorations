# Handoff: QoL + recall-qtype thread (the last thread before a use period)
Working on personal study tool employing arithmetic generation, sm2 scheduling, etcetera.
Trying to complete the last updates before going into use and feedback gathering phase to stop developing without concrete use data.

STATUS: planning handoff, written at the close of the authoring thread
(A1-A3 + pyutils extraction + usage guide). This transfers verified state
and thinking; it does NOT execute. The next thread does its own Phase 0
verification, planning, and sign-off before any code, per
llm-thread-protocol.md.

--------------------------------------------------------------------------------
0. REPO ACCESS (sparse clone -- sm2/ is GONE, do not fetch it)
--------------------------------------------------------------------------------
sm2/ was retired in A3 (ADR-059); the only live top-level dirs are drill/.
Sparse-clone just those:

    git clone --no-checkout --depth 1 https://github.com/luised94/explorations.git
    cd explorations
    git sparse-checkout init --cone
    git sparse-checkout set drill
    git checkout

Record the HEAD hash in the first reply; the human confirms it matches
local HEAD before any code. (If the sm2 exercise CONTENT is ever wanted,
it is recoverable per ADR-059: git checkout bf8f43d -- sm2/ , after
git fetch --unshallow, since this is a shallow clone.)

READ ORDER (all in drill/llm/): llm-thread-protocol.md (binding rules);
decisions.md ADR-058/059/060 (this lineage's decisions);
roadmap.md and feature-backlog-2026-07.md (where deferred items live).
THE CODE WINS on any doc/code conflict; record deviations (R1/R2).

STYLE CONTRACT unchanged and binding: flat procedural; pure functions over
plain dicts/lists/tuples; no classes (except exception subclasses), no
nested funcs/closures/decorators/wrapper indirection; full descriptive
names; reads/writes/clock/randomness at the edges (HTTP/MAIN/DB), never in
LOGIC; layering config <- db <- logic <- http; ASCII everywhere including
commits and patches. Delivery: git format-patch files the human applies locally
with git am; The user cant copy from tool output. Inlining the patch consumes more tokens I believe; the thread does NOT push. One plan commit at a time; full
suite green at baseline-plus-new before each commit unless its docs or comments, they shouldnt alter the code right?; STOP points as the
plan defines, then WAIT for sign-off.

Baseline to reproduce and report (R1/R7): in drill/, uv sync --group test;
npm install jsdom acorn --no-save (one command); bash tests/run.sh. At this
handoff that was backend 340 passed + 1 skipped (the retired-fixtures
guard in test_migrate_sm2.py skips now that sm2/ is gone -- EXPECTED, not a
failure), frontend 363, ending ALL GREEN. Report the real numbers.

NOTE FROM THE HUMAN: the next thread will run on Claude Fable 5, whose
classifier is stricter and flagged the prior conversation (reason unclear;
the work is a personal spaced-repetition study tool -- flashcards,
scheduling, terminal formatting -- with no misuse vector). Keep requests
concrete and scoped; if a benign request is flagged, note it plainly and
proceed with the code, which speaks for itself.

--------------------------------------------------------------------------------
1. VERIFIED GROUND TRUTH (established this thread; re-verify per R1)
--------------------------------------------------------------------------------
These correct real misconceptions and are the spine of the work:

(a) add != queue. `drill add` inserts questions into a bank and touches
    scheduling NOWHERE. Whether/when an item appears in a session is
    decided later by the scheduler. Adding 40 items does NOT queue 40 for
    today.

(b) The scheduler is per-bank at review time, and GLOBAL for the new-item
    budget. A live session is scoped to one bank_id (http_layer.py session
    handler). Within a bank: due-for-review has STRICT PRIORITY over new
    (new introduced only when nothing is due -- the `elif admitted_new`
    branch). Due items are picked one at a time, weighted by miss-rate
    (select_weighted_by_miss_rate). The new-item throttle
    (apply_new_question_throttle) is a GLOBAL daily budget
    (NEW_QUESTIONS_PER_DAY_MAXIMUM) with a per-bank minimum. dry-run runs
    the same partition->cap->throttle across ALL banks at once.

(c) Consequence for the human's "daily routine across content types"
    question: there is NO cross-content-type interleaving in one session.
    You drill ONE bank at a time; math/trivia/recall are not woven into a
    single daily flow. A unified daily-session flow does not exist yet.
    This is a genuine design question, DEFERRED to post-use planning (see
    section 4), not this thread.

(d) The seeded categories are: arithmetic, vocabulary, trivia, geography,
    logic, typing, code (config.py SEED_CATEGORIES). The human's naming
    critique is CORRECT: these are not parallel. geography/code/etc. can
    themselves BE trivia; the set mixes grouping axes (subject vs format vs
    grading-kind). See section 3.

(e) Authoring buffer format (author_parse/author_template): each field is
    its OWN line, `key: value`; q and a are SEPARATE lines (never same
    line). Arrays (alt, distractors, hint, tags) use ' | ' on one line.
    Blocks separated by a blank line. Aliases: q->question, a->answer,
    alt->alternatives, type->qtype, hint->hints. The template currently
    shows only bare `q:`/`a:` with a terse comment header and NO worked
    example -- the documented cause of the human's field-format confusion.

--------------------------------------------------------------------------------
2. THIS THREAD'S SCOPE -- QoL fixes + the recall qtype
--------------------------------------------------------------------------------
Confirm/refine at Phase 0; the human agreed to the shape but wants
"additional questions, investigations and verifications to properly
specify" before locking. Treat each below as a proposal to verify, not a
frozen spec.

QoL FIXES (small, mostly view/text, low-risk -- likely one STOP group):

  Q1. Worked-example template. author_template should include one fully
      commented example block showing EVERY field (q, a, type, alt,
      distractors, hint, tags, difficulty) so the format is
      self-documenting. Verify: does a commented example round-trip
      cleanly through author_parse (comments stripped, no phantom block)?
    Add a test. Clarify if multiple items can be included in a single session.

  Q2. `drill status` command (new; extends the dispatch, NOT REPORT_COMMANDS
      if it needs args, but likely arg-less so it MAY be a report). Prints
      the invisible state: scheduler budgets (new-per-day,
      reviews-per-session, per-bank min), leech threshold, EF bounds, DB
      path in use, bank+question counts per category, new-introduced-today
      vs remaining budget, and count due today. This is the single most
      requested-by-implication view -- it would have pre-answered most of
      the human's Q1. Verify: which of these are already readable via
      existing db functions vs need a new reader.

  Q3. Better `add` success message. Not just "added N" but sets the
      queueing expectation: e.g. "added N to bank X; new items enter
      sessions up to <budget>/day, so these appear over the next few
      sessions." Kills the add==queue misconception at the point of action.

  Q4. End-of-session summary. A closing line/view: got X/Y correct, Z new
      introduced, N due next. Closes the loop without needing separate
      report commands. Touches the session-end path (HTTP). Verify where
      session end is handled and whether the counts are already on hand.
      Gotta make sure the interaction/gameplay cycle is clean and streamlined.

  Q4b. (Human addition) Session-level feedback capture at end-of-session.
      The human wants to "collect feedback on the overall session" during
      the end phase -- a lightweight subjective note/rating per session
      (e.g. how it felt, energy, difficulty). This is genuinely new
      collection (a session-level field or a small session_feedback store),
      unlike the answer-level log which is already rich. SPECIFY at Phase 0:
      free-text vs rating vs both; stored on sessions table vs new table;
      surfaced where. Keep it minimal and optional.

THE ONE REAL FEATURE -- recall qtype with DEFERRED, BATCHED self-assessment:

  Supersedes the inline sketch in ADR-060. Design (verify + specify):
  - A `recall` qtype: prompt shown; user attempts (types or thinks); marks
    "attempted" and moves on -- NO answer shown, NO grade inline.
    Not sure what is meant by attempted. I think the user should submit answer and that should trigger next item. If the box is empty, there should be an instruction that the user should write something simple. Not sure what the attempted is referring to.
  - At SESSION END, a review pass shows each recall item with the user's
    attempt (if typed), reveals the criterion (the answer field), and the
    user presses pass/fail (or scores each item for sm2?) per item. Batched self-assessment feeds the
    scheduler exactly as a normal boolean would (derive_recall_quality is
    indifferent to the boolean's source).
  - Rationale (scholarship, from prior turns): effortful retrieval before
    reveal is where learning happens; batching keeps the retrieval pass
    uninterrupted and reduces generous-self-grading bias (heat-of-the-moment
    streak pressure). Precedent: test-then-mark, catechism recitation,
    retrieval-practice literature; Wozniak's minimum-information principle
    is the complementary guard (make criteria specific enough that honest
    self-grading is easy).
  - KNOWN CAVEATS to resolve in-thread (not blockers):
    * elapsed_ms would measure attempt-time only, not attempt+grade. Decide
      what the timer captures for recall items.
    * Session abandonment before the grading pass: attempted-but-ungraded
      recall items must stay "attempted, ungraded" and NOT corrupt the
      schedule (no phantom pass/fail). Specify the persistence.
    * This touches review-mode HTTP (C4 territory / the session handler)
      and the frontend review flow -- the heaviest part of the thread. It
      likely warrants its own STOP separate from the QoL group.
  - Verify at Phase 0: how the current session handler serves and records a
    single question, so the two-phase (attempt pass, then grade pass) flow
    can be specified against the real payload/response contract.

--------------------------------------------------------------------------------
3. NAMING PROBLEM (the human raised; specify, likely its own small decision)
--------------------------------------------------------------------------------
The human wants better names for "bank" and "category", and notes the
seeded categories are not parallel (trivia vs geography vs code vs typing
mix subject / format / grading-kind). This is the same issue ADR-060's
"category-taxonomy re-grain" names, now with a naming (not just structure)
dimension.

Direction already agreed (ADR-060): the fine axis (subject: physics,
biochem, calculus) belongs in TAGS; the coarse axis should be
grading/session-shaped, not subject-shaped. The naming task is to find the
right words for the two levels. Candidate framing to explore (thesaurus/
naming pass, per the human): the coarse grouping might be "domain" or
"track" or "subject-area"; the mid grouping ("bank") might be "set",
"deck" (rejected earlier -- avoid), "collection", "list", or "pack". The
MISSING category concept the human sensed: the current set conflates
"what the question is ABOUT" with "how it is GRADED/DRILLED"; a clean
taxonomy separates those. A recall/self-assessment grading-kind is exactly
the newly-needed axis member.

RECOMMENDATION: do the NAMING exploration and propose options in this
thread (cheap, all doc/label + maybe a rename), but treat any SCHEMA
re-grain (changing how categories key scheduling/coverage) as DEFERRED to
post-use planning -- it is schema+consumer-touching and wants usage data.
A pure rename (labels/strings) may be safe now; a structural re-grain is
not. Draw that line explicitly at Phase 0.
Leave for later unless the change can be executed mechanically and deterministically with sed or awk. Maybe with nvim in headless form?

--------------------------------------------------------------------------------
4. EXPLICITLY DEFERRED to post-use planning (do NOT fold in)
--------------------------------------------------------------------------------
- Unified DAILY-SESSION flow across content types (math + trivia + recall
  in one routine, cross-bank interleaving). Section 1(c) shows it doesn't
  exist; designing it wants real use first. The human named this as
  future.
- Generable-math build bundle (bitwise arithmetic 4.04, base conversion,
  linear solve-for-x). Independent, safe, but not this thread.
- Structural category-taxonomy re-grain (vs pure rename) -- section 3.
- hint-reveal / skip WIRING (usage-and-study-guide section 1): record the
  unreconstructable before heavy use. NOTE: if the recall-qtype work is
  already touching the session handler, capturing hint-reveal MAY become
  cheap to include -- flag at Phase 0 as a possible opportunistic add, but
  do not force it.
- The pyutils repo split (git subtree split --prefix=pyutils after
  git fetch --unshallow) -- human executes when ready; see
  pyutils/README.md.

--------------------------------------------------------------------------------
5. POST-USE ASSESSMENT STRATEGY (seed; concretize at next thread's start)
--------------------------------------------------------------------------------
After a few weeks of daily use, a reflection thread should read the
observations log (usage-and-study-guide section 4) + the response/schedule
data and answer: which grading rails served (false-leech rate on recall
content?); did the scheduler pace feel right (intervals, new-item budget);
which report cuts were reached for (-> stats-depth priorities); did the
naming/taxonomy hold up; is the unified daily-session flow now specifiable
from real routine. That thread concretizes the next roadmap. This handoff
just seeds it; the plan is written then.

--------------------------------------------------------------------------------
6. SUGGESTED THREAD SHAPE
--------------------------------------------------------------------------------
Phase 0: clone (section 0), baseline, re-verify section 1 ground truth,
re-read the session handler for the recall two-phase design, and reply with
HEAD hash + baseline + confirmations + refined specs for the QoL group,
the recall qtype (with the caveats resolved), the session-feedback capture,
and the naming options (rename-only vs deferred re-grain line). THEN STOP.
Likely STOP grouping after go: (I) QoL fixes + naming/labels + session
feedback; (II) recall qtype with deferred batched assessment. format-patch
at each STOP; human applies with git am and confirms before continuing.
