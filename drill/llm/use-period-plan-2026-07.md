# Use-period plan: information gathering for the feedback phase (2026-07)
Status: ACTIVE during the use period. The reflection thread that opens the
feedback phase reads THIS doc first, then the data it names, then
re-assesses roadmap.md and feature-backlog-2026-07.md against the
evidence (promote / demote / drop; the backlog is not a queue, it is a
candidate list awaiting exactly this data).

## How to gather (run these when ready, paste outputs into the thread)

    drill feedback   # activity span, recall grading outcomes + abandonment,
                     # schedule envelope, every session rating/note (use-1)
    drill stats      # accuracy breakdowns, timing percentiles
    drill status     # config, budgets, today's due/new picture
    drill leeches    # what keeps lapsing (false-leech question)

Plus: the observations log (usage-and-study-guide section 4) and the
friction log (section "Friction log" below). Nothing else needs setting up;
this was settled before the use period on purpose so the gathering step is
mechanical.

## Questions to answer, mapped to their data

Q1. UI issues -- made specific. Not "the UI was annoying" but, per entry:
    the SCREEN (drill stage / session controls / summary / authoring
    editor / a report), the STEP being performed, EXPECTED vs ACTUAL, and
    how often it bit. Source: friction log. The qol-6/7/8 fold showed the
    pattern works: "thin block line always visible" was fixable in one
    commit because the report named the exact element and condition.

Q2. Authoring + drilling across the three planned use cases. For EACH,
    note: which qtypes were used and whether they fit; template/buffer
    friction (worked example sufficient?); whether tags carried the
    subject axis well; what the sessions felt like. The use cases and
    their suggested shapes (suggestions, not prescriptions -- deviating IS
    data):
    (a) MA driving-test knowledge exam: multiple_choice with distractors
        for rule recognition; free_response for numeric rules (distances,
        limits, fines). Tags: driving, ma-permit.
    (b) Russian and Greek alphabets: identify or translate for
        letter -> name/sound (both directions are separate questions);
        recall for produce-the-letter-from-the-name practice (grade
        against the revealed criterion). Tags: russian, greek, alphabet.
    (c) Work-readings trivia (biology, biochemistry, genetics, molecular
        biology, ...): recall is the designed home for concept/criterion
        content (ADR-059/061); multiple_choice where distractors are easy
        to write. Tags carry the subject (biology, biochem, genetics...),
        exercising the tags-as-fine-axis decision (ADR-060) for real.

Q3. Session-level experience: fill the end-of-session rating/note when a
    session felt notably good or bad (not compulsorily -- sparse honest
    data beats dense noise). Surface: drill feedback prints them all.
    Meta-question: did the capture itself earn its place (Q4b assessment)?

Q4. Scheduler pacing: did intervals and the new-item budget (9/day
    global, 1/bank minimum) feel right? Source: schedule envelope in
    drill feedback + status due counts + felt experience in the notes.
    CAVEAT that shapes this question: the browser client is still
    practice/random (ADR-061 finding) -- schedules only advance if
    something posts mode=review. If during the period the missing
    review wiring is FELT (items never spacing out), that is the
    strongest possible prioritization signal for wiring it.

Q5. Recall self-assessment quality: was honest pass/fail grading easy or
    did criteria turn out too vague (Wozniak's minimum-information
    principle -- vague criteria make self-grading mushy)? Was "unsure"
    actually missed (ADR-061 defers it, mapping to fail)? Source: recall
    outcome counts + notes on specific questions.

Q6. Grading-pass abandonment: the ungraded count in drill feedback. High
    abandonment means the batched pass has a UX problem or sessions end
    the wrong way (unload vs explicit End).

Q7. Naming friction: moments where "bank" or "category" misled in the
    moment. Feeds the evidence section of naming-options-2026-07.md.

Q8. Report reach: which report commands were actually reached for, which
    cuts were missing (-> stats-depth priorities, roadmap).

## Recommended additions (beyond the three named areas)

- A daily one-liner in the observations log beats a weekly essay: date,
  what was drilled, one sentence of felt experience. The reflection
  thread can aggregate one-liners; it cannot recover unrecorded days.
- Note the FIRST TIME each pain occurs with detail; subsequent hits can
  be tally marks. First-occurrence detail is what makes fixes cheap.
- If authoring content for (a)-(c) surfaces missing FIELDS (an image for
  a road sign -> media_url exists but is unrendered? a source/citation
  field?), record the concrete question that wanted the field.
- Deferred items to keep half an eye on so the reflection thread can rule
  on them: unified daily-session flow (does drilling three banks in
  sequence chafe?), browser auto-open (still wanted? spec is in the
  qol-8-era discussion), hint-reveal wiring, generable-math bundle.

## Friction log

The human keeps a running friction log OUTSIDE the repo and may or may
not append it when opening the feedback phase. Placeholder:

    [FRICTION LOG -- appended by the human at feedback time, or absent.
     Format per Q1: screen / step / expected / actual / frequency.]

If absent, Q1 is answered from the observations log and memory; the
thread should ask before assuming no UI issues existed.

## Exit criteria for the use period

Enough data to answer Q1-Q8 with at least one concrete instance each, or
three weeks of use, whichever comes first. Then: open the reflection
thread with the dumps above; it re-verifies the repo state (Phase 0 as
always), answers the questions, re-grains the roadmap/backlog, and plans
the next build thread. Section 5 of the QoL/recall handoff seeds that
thread's shape; this doc supersedes it where they differ.
