# rep: kickoff for thread 4

date: 2026-10-05
written at the close of thread 3 (M3). Read with STATUS.md, PLAN.md
(sections 8, 9, 12) and BUILDING.md. Precedence as in BUILDING.md.

## 1. The week, for the person

The use week runs on the real data root, ~/learning. Each day:

- Morning: `body`. Fill in last night; add drinks and coffee as they happen.
- Once a day: `rep`. It serves what is due and up to 10 new items.
- Whenever wanted: `rep drill permit` (or `--count 10`, or `--tag jol`).
- Anything that bugs, helps or confuses you: `rep-notes`, one line.
- A screen worth showing: `rep-screen`, then attach the file it prints.
- `rep status` when unsure what is due or which data root is in use.

At the end of the week, in this order:
1. `rep-week`: answers a few questions, writes reports/week-<day>.md.
2. `rep-tour`: a tour of the code; answer under each stop, then `:wq`.
3. Pack both directories (BUILDING.md section 6), then open thread 4 with
   the packs, the week report, the code tour, any screens, and this line:
   "Thread 4 kickoff: design mode."

## 2. Thread 4: role and first steps

Role: DESIGN, until a plan for the next milestone is agreed and locked
(the person's working defaults); then IMPL.

1. Clone-and-verify (BUILDING.md section 1): both packs' commit ids, the
   tests file by file against STATUS.md's breakdown (300 with nvim).
2. Read the week report before anything else. Its numbers come from
   tools/week_report.py; do not recompute them by hand. Fill in each
   card's Result and Decision in PLAN.md section 8.
3. Rank everything in the report's notes and answers, and in the code
   tour's answers, into: fixes (bugs, friction), decisions to revisit,
   new features. Fixes first, one commit each.
4. Read the code tour's Understand answers against the docstrings: a
   wrong or empty answer marks code or comments that do not explain
   themselves.
5. Then the open questions below, in design mode.

## 3. Open questions for thread 4

- M3b (PLAN.md section 7): stats and forecast, built on the week's events.
- The drill/ repository: port its generators as a kind of rep item, or
  start rep over with what the week taught (PLAN.md section 9).
- Languages: typing other alphabets, the keyboard map (section 9).
- The session inside nvim (D47's revisit) and multimodal (section 9).
- run_command's size (section 9; the code tour's question).
- make-it-visible (the person's draft method prompt): kept locally by the
  person; apply it to every new screen.

## 4. Predictions at the close of thread 3

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
