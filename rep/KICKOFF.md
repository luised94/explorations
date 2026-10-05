# rep: kickoff for threads 4a and 4b

date: 2026-10-05
written at the close of thread 3 (M3), revised after the person's first
day on ~/learning (0045-0053). Read with STATUS.md, PLAN.md (sections 8,
9, 12), BUILDING.md and ../meta/THREADS.md (the kinds of thread and how
to start one). Precedence as in BUILDING.md.

Two kinds of thread follow, in this order:
- 4a, rolling: fixes while the person uses rep, from now until the week
  ends. If 4a grows long, a continuation (4a-2) picks up from a pack.
- 4b, strategy: on 2026-10-11 or later, reads the week and decides
  whether rep continues as built, changes course, or stops.
Fixes made in 4a stay measurable: every session records the hash of the
code that ran it (rep_source, D49), and every run is in the run log
(D55), so 4b can split the week by code version.

## 1. The week, for the person

Week 1 runs 2026-10-05 to 2026-10-11 (the first day practised, D61).
Each day:
- Morning: `body`. Fill in last night; add drinks and coffee as they
  happen. `/: $` jumps to the next empty field.
- Once a day: `rep`. It serves what is due and up to 10 new items, and
  says why that many.
- Whenever wanted: `rep drill permit --count 20` (or `--tag jol`).
- Anything that bugs, helps or confuses you: `rep-notes`, one line.
- A question about how rep behaves: `faq WORDS` first (rep/FAQ.md); if
  it is not there, `faq --add "the question"` and leave the answer
  blank, or put it in the notes. 4a answers open questions.
- A screen worth showing: `rep-screen`; read the file, then attach it.
- `rep status`: time left today, what `rep` would do now, each deck.
- `rep where`: every place and helper, with paths.

## 2. Thread 4a: rolling fixes

Start it now, or at the first thing worth fixing.

Attach: the three packs (../meta/THREADS.md section 3 has the command),
this thread's last response and the output of its commands.

First message, filled in:

    Thread 4a: rolling fixes during the use week. implement mode.
    Read rep/KICKOFF.md section 2 first.
    HEAD: <git log --oneline -1>
    Today: <date>, day <N> of 7
    Since the last thread: <what happened>
    Context: <anything the files cannot know>
    Asks: <fixes wanted, in order; paste notes, screens, errors below>
    Not now: <what to leave alone>

The thread's routine:
1. Clone-and-verify (BUILDING.md section 1): the packs' commit ids
   against the HEAD given, rep's tests file by file against STATUS.md
   (304 with nvim), and `bash meta/tests/test_faq.sh` (ok: 23 checks).
2. Per report: reproduce, then one commit per fix, green, with a test
   that fails without it (a planted bug, BUILDING.md section 3).
3. Each commit message names the note or screen it answers, so 4b can
   line fixes up against the week's data.
4. A fix that would change a recorded decision is not made: it goes to
   section 4 below, with the note that raised it.
5. Open FAQ questions (`faq --open` in rep/) get answers, each pointing
   at its rule and a command that shows the data (meta/README.md).
6. At about six commits, or when the chat is long: pack, and open 4a-2
   with the same first message, "continuation" in place of "rolling".

Commands the person will want during 4a (each from the explorations
root, D as in THREADS.md):
- apply a delivered series: the COMMANDS block of each reply
  (BUILDING.md section 6 has the shape)
- the state for a report: `rep status; rep where; tail -5
  ~/.local/state/rep/runs.jsonl`
- a week report so far: `rep-week --partial`

## 3. Thread 4b: strategy, at the week's end

On 2026-10-11 or later, in this order:
1. `rep-week`: writes reports/week-2026-10-05.md and opens it in nvim;
   answer under each heading, then `:wq`.
2. `rep-tour`: answer under each stop, then `:wq`.
3. Pack (THREADS.md section 3) and open 4b with the packs, the week
   report, the code tour, notes.md, any screens, and:

    Thread 4b: strategy after use week 1. design mode.
    Read rep/KICKOFF.md section 3 first.
    HEAD: <git log --oneline -1>
    Permit test: <date, or not booked>
    Time I want to give this next month: <hours a week>
    What I want from it: <in your words>
    Context: <anything the files cannot know>

The thread's agenda:
1. Clone-and-verify, as in 4a.
2. The week report first, before any view is formed. Its numbers come
   from tools/week_report.py; do not recompute them by hand. Fill in
   each card's Result and Decision in PLAN.md section 8, and score the
   predictions in section 5 below.
3. Split the numbers by code version (rep_source on session_start)
   wherever 4a changed something that bears on them.
4. Rank the week's answers, notes.md, FAQ entries asked during the
   week, section 4's deferred list and the code tour's answers into:
   fixes, decisions to revisit, new features.
5. The strategic decision, recorded in PLAN.md as a decision with the
   options scored. At least these options, each argued at its best:
   - continue as built: M3b (stats, forecast) on the week's data;
   - narrow: rep serves the permit test until it is passed, nothing else;
   - widen: languages (the person's Spanish, other alphabets), the
     drill/ generators, reading capture from Zotero and kbd;
   - replace the core: a mature tool (Anki, with FSRS) for scheduling,
     rep's ideas kept as small tools around it;
   - stop: what the week taught, written down, and nothing more built.
6. The kickoff for the next build thread, or the pivot's plan.

Tactics for 4b, easy to forget:
- Days not practised are data (E3): ask what happened on them before
  explaining the days that were.
- Day one held a 251-item drill: read E2 and E5 with and without it.
- Count the time spent building rep this week against the time spent
  using it; code is a liability, and the week can show which paid.
- Separate rep's friction from the material's difficulty: a slow
  correct answer on a long permit rule is the material, not the tool.
- The person's goals come before the tool's roadmap: ask, then rank.
- Write the decision's kill criteria down, so the next period can test
  them as this week tested the predictions.

## 4. Deferred, for 4b unless the week shows one blocking

Ranked by value for its cost, scored 1 to 10:
1. Settings the person can change (new items a day, session length),
   and an audit of the constants left in code (8).
2. Emphasis in questions (bold, colour) through pyutils terminal_output,
   so near-identical names (Australia, Austria) stand apart; a display
   that scales to many decks (7).
3. Generic tools at the repository level: rep-screen and the code tour
   into meta/, on its project convention (6).
4. The code tour by smaller units: tree-sitter, Lua and shell (5).
5. The argument parser as a table of data, and run_command's size (5).
6. `rep add FILE` (4).
Open questions as well: languages and keyboards, multimodal, the
session inside nvim (D47's revisit), the drill/ repository, how rep fits
reading, exercise and reflection (rep/FAQ.md has a first answer).

## 5. Predictions at the close of thread 3

Written before the week so the week can test them. The report's numbers
decide; these say what this thread expected, so its judgement can be
calibrated too.

- E1 capture: under 2 items a day from readings. The decks were added in
  bulk, and capture while reading has not yet been practised.
- E2: under 15% of automatic grades corrected; most corrections on
  numeric permit items (a unit typed, "$35"). Median scheduled session
  under 10 minutes.
- E3: scheduled sessions on 4 or 5 of 7 days; drills on the first days,
  fewer later.
- E4: too few reviews older than a day to judge calibration.
- E5: the slowest correct answers are the long permit answers (JOL
  restrictions, the move-over law).
- Grading: some answers still left ? despite D54's offer, mostly on long
  self-graded permit items.
- Body form: bed, wake and quality filled on most days; drinks and coffee
  on fewer; at least one clock-time slip flagged.
- Friction: the arrow keys in vi insert mode (D47) will be noticed.
- Added after day one: a drill started on all 251 items on day one, so
  day one's attempts may be an outlier; compare E2 and E5 with and
  without it.
- Added with the FAQ: fewer than 5 new questions added with `faq --add`
  during the week; most questions arrive as notes instead.
