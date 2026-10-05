# rep: kickoff for threads 4a and 4b

date: 2026-10-05
written at the close of thread 3 (M3), revised after the person's first
day on ~/learning (0045-0050). Read with STATUS.md, PLAN.md (sections 8,
9, 12) and BUILDING.md. Precedence as in BUILDING.md.

Two threads, not one: 4a runs during the week and fixes what the week
turns up; 4b opens at the week's end, reads the report, and decides
whether rep continues as it is or pivots. Changes made in 4a stay
measurable: every session records the hash of the code that ran it
(rep_source, D49) and every run is in the run log (D55), so the report
can split the week by code version.

## 1. The week, for the person

The use week runs on the real data root, ~/learning. Week 1 starts on the
first day practised (2026-10-05) and ends seven days later. Each day:

- Morning: `body`. Fill in last night; add drinks and coffee as they happen.
- Once a day: `rep`. It serves what is due and up to 10 new items, and says
  why that many (drills count toward the 10).
- Whenever wanted: `rep drill permit --count 20` (or `--tag jol`).
- Anything that bugs, helps or confuses you: `rep-notes`, one line.
- A screen worth showing: `rep-screen`; read the file, then attach it.
- `rep status` for the time left in the day, what `rep` would do now, and
  each deck's numbers; `rep where` for where everything lives.

During the week: open thread 4a with this file and the line "Thread 4a:
fixes during the use week. implement mode." Paste notes, screens or
errors as they come.

At the end of the week, in this order:
1. `rep-week`: writes reports/week-<first day>.md and opens it in nvim;
   answer under each heading, then `:wq`. (Before the last day it says
   which day it is; `rep-week --partial` reports the days so far.)
2. `rep-tour`: a tour of the code; answer under each stop, then `:wq`.
3. Pack both directories (BUILDING.md section 6), then open thread 4b
   with the packs, the week report, the code tour, any screens, and this
   line: "Thread 4b kickoff: design mode."

## 2. Thread 4a: role and routine

Role: IMPL, on fixes only. A fix is a bug, or friction the person
reports, whose remedy does not change a decision; anything that does is
written down for 4b instead, with the note that raised it.

1. Clone-and-verify (BUILDING.md section 1): the packs' commit ids, the
   tests file by file against STATUS.md's breakdown (304 with nvim).
2. Per report: reproduce, then one commit per fix, each green, with a
   test that fails without it (planted-bug check as in thread 3).
3. Each commit says in its message which note or screen it answers, so
   4b can line fixes up against the week's data.
4. Deferred list, for 4b unless the week shows one is blocking:
   - generic dev helpers (rep-screen, the code tour) at the explorations
     level, with a convention for finding the current project;
   - emphasis in questions (bold or colour) through pyutils
     terminal_output, and a display that scales to many decks;
   - the code tour by smaller units (tree-sitter, Lua and shell);
   - presets the person can change (new items a day, session length),
     and an audit of the constants left in code;
   - the parser organized as data, and run_command's size;
   - `rep add FILE`; languages and keyboards; multimodal; drill/.

## 3. Thread 4b: role and first steps

Role: DESIGN, until a plan for the next milestone is agreed and locked
(the person's working defaults); then IMPL.

1. Clone-and-verify, as in 4a.
2. Read the week report before anything else. Its numbers come from
   tools/week_report.py; do not recompute them by hand. Fill in each
   card's Result and Decision in PLAN.md section 8.
3. Rank everything in the report's answers, notes.md, 4a's deferred
   list and the code tour's answers into: fixes, decisions to revisit,
   new features.
4. Read the code tour's Understand answers against the docstrings: a
   wrong or empty answer marks code or comments that do not explain
   themselves.
5. The strategic question: continue rep as built, or pivot. Inputs: the
   cards, the person's readiness for the permit test, how much of the
   week rep was used without being pushed, and the open questions below.

## 4. Open questions for thread 4b

- M3b (PLAN.md section 7): stats and forecast, built on the week's events.
- The drill/ repository: port its generators as a kind of rep item, or
  start rep over with what the week taught (PLAN.md section 9).
- Languages: typing other alphabets, the keyboard map (section 9).
- The session inside nvim (D47's revisit) and multimodal (section 9).
- How rep fits the person's wider practice: reading in Zotero, kbd,
  reflection, exercise; where capture while reading enters (E1).
- make-it-visible (the person's draft method prompt): kept locally by the
  person; apply it to every new screen.

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
