# FAQ: rep

> Questions asked about this project, each answered by the rule behind it
> and the command that shows the data the rule acts on. One entry each:
>
>   ## How many items does a session hold, and why that many?
>   asked: Why only 8 due?                 the words it was asked in; repeat
>   answer: The rule, in prose. Lines below it, up to a blank line, are
>     part of it.
>   see: rep status                        a command that shows the numbers now
>   rule: PLAN.md D36; src/rep/session.py  where the rule is written (gF opens)
>   date: 2026-10-05                       when the answer was last checked
>
> Write the heading one level above the question as asked: not "why 8?"
> but "how many, and why that many?". The asked: lines keep the words it
> came in, so a search for them still finds it. An entry without an
> answer is an open question.
> In nvim (`faq`): each question is one folded line; j and k move between
> them, zo opens one, zc closes it, zR opens all, / searches everything.
> From the shell: faq WORDS, faq --questions, faq --open,
> faq --add "QUESTION", faq --check. meta/README.md has the rest.

## How many items does a session hold, and why that many?
asked: Why only 8 due? 8 due seems small.
asked: Why is it three new? Why is it only permit?
asked: Why only 3 questions?
answer: Due items first: every item whose due day is today or earlier,
  least likely remembered first, up to 60 answers (session_budget). Then
  new items: up to 10 a day (new_per_day), minus every item first seen
  today, drills included, and fewer when the due items leave less room
  (a new item costs 3 of the 60: its showing, its return, a likely miss).
  New items come deck by deck, in the order the decks were added. Early
  on few items are due: everything is days old, and a first "good" puts
  the next review about 2 days away. A drill is different: it serves the
  items you choose, and its never-seen items count toward the day's 10.
see: rep status   (the session and new items lines; per deck: new, due now)
see: the start screen's "N new:" line gives the terms for that session
rule: PLAN.md D36, D37, D50, D59; src/rep/session.py plan_session (P3, P4)
date: 2026-10-05

## When does an item come back, and why then?
asked: Retest: why does it matter, and which items are retested?
asked: Why is the next review on 2026-10-06?
answer: Within a session, in rounds: an item graded again comes back in
  the next round until you recall it; a new item comes back once more
  after other items came between, even when recalled, because that second
  recall is what makes it last past today. Across days, the memory model:
  the first grade sets how long the memory should last (its stability:
  again about 0.2 days, hard 1.3, good 2.3, easy 8.3), and the item is due
  when the chance of recalling it falls to 90%. Each later recall
  lengthens the interval and a miss shortens it; repeats on the same day,
  as in drills, barely change it.
see: rep why "words from the question"   (stability, recall now, due, attempts)
see: the end of a session: "Next reviews: N on DAY"
rule: PLAN.md D36, D44, D45; src/rep/memory_model.py DEFAULT_PARAMETERS
  (its first four numbers are the first-grade stabilities, in days)
date: 2026-10-05

## Can I take more new items, fewer, or put the practice off?
asked: Should I be able to add more items for the next day, or delay?
answer: The limits are fixed defaults for now: 10 new a day, 60 answers.
  To take more today: rep drill DECK --count N; its never-seen items
  count toward today's 10, and tomorrow starts with a fresh 10. To skip a
  day: skip it; due items wait, and the next session takes the least
  likely remembered first, up to 60. To stop an item: suspend on the
  grading sheet; rep unsuspend brings it back. Settings you can change
  are on the list for the next threads.
see: rep status   (the new items line)
rule: PLAN.md D36, D39; src/rep/session.py DEFAULT_PRESET
date: 2026-10-05

## What happens when I stop a session or a drill partway?
asked: What happens on stopping, to the scheduler, on rerunning, and to
  the day's session?
answer: Every answer is written the moment you press Enter. Ctrl-D: the
  round's answers so far go to the grading sheet, then it ends. Ctrl-C:
  it ends at once, and the round's answers wait, ungraded, for rep
  review. Graded answers update the schedule whether or not the session
  finished; items not reached are untouched. Running rep again the same
  day plans afresh: an item answered today is not served as new again,
  and a due one only while still due. A drill never replaces the day's
  session; it adds to it, and its new items use the day's allowance.
see: rep status   (waiting, today did, session)
rule: PLAN.md D45, D50, D54
date: 2026-10-05

## Why is rep add fed on standard input?
asked: Why stdin? Should the usage show < file.md?
answer: One way in for every source: a file (rep add --stdin --to DECK
  < file.md), a pipe, and nvim's :RepCapture, which pipes the buffer's
  text. A file argument is deferred: add's default deck is named after
  the items' source (the @citekey), and a file name would compete with it.
  The item format is in CONVENTIONS.md and in rep --help's example.
see: rep add --help
rule: PLAN.md D29, D58; CONVENTIONS.md
date: 2026-10-05

## Why is the package under src/rep/ and not directly in rep/?
asked: Why is there an additional rep folder?
answer: The standard Python src layout: the package can be imported only
  once installed, so the tests run against the installed rep, as you run
  it, and never against the working directory by accident.
see: uv run python -c "import rep; print(rep.__file__)"
rule: pyproject.toml (uv_build); PLAN.md section 4
date: 2026-10-05

## Should I learn an item before rep first asks it?
asked: Drill to near 100% first, before relying on the scheduler?
asked: Does spaced repetition assume I knew the answer at some point
  recently? (the capitals, from an eighth-grade exam)
answer: Spaced repetition schedules the recall of something already
  learned; it does not teach. rep's first showing is a test before study:
  you attempt, the grading sheet shows the key (that is the study), and
  the same session asks again until you recall it once. So rep does not
  assume you knew it: a blank first attempt is fine, and the schedule
  starts from that first grade (again: back tomorrow). What the scheduler
  cannot know is whether the question makes sense to you yet; that is on
  you and the item. The rule from the spaced repetition canon (Wozniak's
  first two): do not memorize what you do not understand, and see the
  whole before the parts.
why: Ranked, for the two decks:
  1. Capitals: let rep bring them in, 10 a day, and on each sheet find
     the country on a map (8). The pair is arbitrary, the key is the
     study, and a place gives it something to hang on. School knowledge
     helps: relearning is faster than first learning (Ebbinghaus's
     savings), and the first attempt shows which ones survived.
  2. Capitals: an hour with a map, region by region, then rep (7). Better
     first learning of the ones you never knew, for an hour's cost.
  3. Permit: read the handbook section first, then rep, and drills as
     the test nears (8, for that deck). Rules need understanding before
     their facts are worth recalling.
  4. Drill every item to 100% before rep schedules it (4). Massed practice
     looks best the same day and fades fastest; one correct recall per
     session, repeated across days (successive relearning), is what lasts.
  With no idea at all, type ? or anything and move on: a guess helps when
  it is related to the answer and the key follows soon; with nothing to
  guess, the gain is small, and the sheet is where the learning happens.
sources: Wozniak, Twenty rules of formulating knowledge, rules 1 and 2:
  https://www.supermemo.com/en/blog/twenty-rules-of-formulating-knowledge
sources: Rawson and Dunlosky 2011, Optimizing schedules of retrieval
  practice: how much is enough? https://eric.ed.gov/?id=EJ934616
sources: Kornell, Hays and Bjork 2009, Unsuccessful retrieval attempts
  enhance subsequent learning:
  http://hayslab.com/publications/kornell.hays.bjork.2009.INPRESS.pdf
see: rep why "words from the question"   (after a first miss: due tomorrow)
rule: PLAN.md D36, D54 (the sheet as the study); PLAN.md section 3
date: 2026-10-05

## How does rep fit with reading, drills and the rest of practice?
asked: How do the program, items, decks and workflow relate to studying,
  reading, reflection, exercise and practice?
answer: rep is the recall part. Reading (Zotero, kbd) is where the
  understanding comes from; while reading, :RepCapture turns a passage
  into items in that source's deck, and rep schedules them. Drills are
  for deadlines and for a deck you choose. The body form and the notes
  are measurement: the week's report sets practice beside sleep, caffeine
  and time of day. Reflection is the week's report and the threads that
  read it. Exercise and other practice are outside rep for now; the
  strategy thread decides whether they come in.
see: rep where   (each place and what it is for)
rule: PLAN.md sections 1, 2 and 8; KICKOFF.md
date: 2026-10-05
