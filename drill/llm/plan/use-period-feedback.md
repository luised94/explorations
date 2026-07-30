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

Each of Q1-Q8 has at least one deliberate probe in the Experiments
section below; the questions say WHAT we want to know, the experiments
say what to DO so the answer exists.

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

## Experiments (deliberate probes; each names the questions it feeds)

E1. Day-zero snapshot (feeds all): before real use, run drill feedback,
    stats, status and save the outputs to a dated file (e.g.
    snapshots/2026-07-XX.txt outside the repo or in the observations
    log). Every later run is then a delta, not an absolute.

E2. Authoring throughput (Q2): for EACH use case, author ~10 questions in
    one sitting. Record: minutes taken, how many buffer errors the editor
    loop caught, whether the worked example was consulted, any field you
    wanted that does not exist (record the concrete question that wanted
    it). Three sittings, three data points on the authoring rail.

E3. Recall discipline run (Q5, Q6): one bank of ~10 recall items from the
    work readings. Three sessions across one week, grading EVERY pass.
    Note each hesitation ("was that a pass?") and which criterion caused
    it -- hesitations locate vague criteria (minimum-information
    principle) and tell us whether "unsure" is genuinely missed.

E4. Abandonment probe (Q6, data trust): after recall attempts, end one
    session with the explicit End button and one by closing the tab
    before grading. Then check drill feedback: the ungraded count must
    match what you abandoned, and the graded counts must match what you
    graded. This is a live audit of the rec-1 invariant with real hands.

E5. Pacing/wiring demonstration (Q4): drill one small bank daily for a
    week, then read drill status (due counts) and the schedule envelope
    in drill feedback. EXPECTED with the current browser client:
    scheduled questions stays 0, because the browser posts practice mode
    (ADR-061 finding). Feeling this gap -- items never spacing out, every
    session re-serving everything -- is the experiment; if it chafes,
    review-mode wiring is the top of the next roadmap. Optional
    counterfactual probe: grade one recall response with mode=review via
    curl against the running server (POST /api/response/grade with
    {"response_id": N, "correct": true, "mode": "review"}) and watch one
    schedule row appear in drill status -- the rails work; only the UI
    wiring is absent.

E6. Alphabet direction split (Q2b): author letter -> name and
    name -> letter as SEPARATE banks (or tag them separately). After a
    week, compare accuracy per bank in drill stats. Also record the
    input-method reality: typing Cyrillic/Greek answers needs keyboard
    layout switching -- note whether identify/translate chafed and
    whether recall (self-graded, no exact typing) sidestepped it (Q13).

E7. Distractor quality check (Q2a): while drilling the driving-test bank,
    tally MC questions answerable by distractor elimination alone
    (without knowing the rule). A high tally means MC is testing
    test-taking, not knowledge -- data for qtype guidance.

E8. Feedback-capture habit split (Q3): week one, rate/note only sessions
    that felt notably good or bad; week two, rate the first session of
    every day. Compare which regime produced notes the reflection thread
    can actually use.

## Workflows (the standing routine the experiments hang off)

Daily: drill status -> drill one or two banks -> ALWAYS end with the
explicit End button (the grading pass and the summary live there; tab-
closing is the abandonment path, fine occasionally, but the End button is
the primary exit) -> rate/note per the E8 regime -> one dated line in the
observations log (what was drilled + one sentence of felt experience).

Weekly: run drill feedback and drill leeches, append both to the
snapshot file, skim for surprises, add a weekly one-paragraph note.

Authoring: separate sittings from drilling (E2); batch 10-20 items per
buffer; when a question fights the format, record it verbatim in the
observations log before bending it to fit -- the fight is the data.

## Additional questions (written down now; answer opportunistically)

Q9.  Data trust: do the report numbers match felt reality? Any moment of
     "that count looks wrong" is a bug report even if unproven (E4 is the
     deliberate version of this).
Q10. Content lifecycle: when a question turns out wrong, vague, or
     duplicated, what do you DO? There is no edit/retire UI; record each
     time you wanted one and what you did instead (sqlite by hand? left
     it?). This decides whether question editing enters the roadmap.
Q11. Session size and caps: how many items feel right per sitting; does
     the reviews-per-session cap (100) or the 9/day new budget ever
     actually bind; would you have changed them if a knob existed?
Q12. Media: did any content want an image (road signs!) or audio (letter
     pronunciation)? media_url exists in the schema; note per concrete
     question whether its absence in the UI was felt.
Q13. Input methods: non-Latin answer entry (Cyrillic/Greek IME switching)
     -- real friction or non-issue? (Paired with E6.)
Q14. Habit and motivation: what made you skip a day; what pulled you
     back; does the tool need anything (streaks? a due nudge?) or is
     external routine enough? Anti-feature data counts double here --
     "nothing, leave it alone" is a valid and valuable answer.
Q15. Operations: database file backup/location habits across the
     WSL/Windows boundary; any near-miss with data loss; should the tool
     do anything (a backup command?) or is cp enough?

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
