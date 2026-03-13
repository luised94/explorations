===============================================================================
SM-2 FEEDBACK PHASE - METRICS AND WATCH LIST
===============================================================================
Reference document for the first two weeks of daily use.
Run these periodically. Act on patterns, not individual data points.

Perspectives integrated: Wozniak (card quality, zombie detection),
Skycak (prerequisites, difficulty calibration, card progression),
Ericsson (deliberate practice, response time diagnostics, full
attention), Acton (solve the real problem, measure external outcomes,
don't lie about whether it's working).


1. DAILY GLANCE (after each session)
-------------------------------------
Before closing the terminal, run these two. Five seconds total.

Due tomorrow:
    sqlite3 data/sm2.db "SELECT COUNT(*) AS due_tomorrow FROM items
    WHERE due_date <= $(python3 -c 'import datetime; print(datetime.date.today().toordinal() + 1)')"

Pass rate over last 7 days:
    sqlite3 data/sm2.db "
    WITH t AS (SELECT cast(julianday('now','localtime') - 1721424.5 AS INTEGER) AS today)
    SELECT round(100.0 * SUM(CASE WHEN grade > 0 THEN 1 ELSE 0 END)
           / COUNT(*), 1) AS pass_pct
    FROM review_log, t
    WHERE review_date > t.today - 7"

Action thresholds:
  - due-tomorrow consistently above 30 after week two: drop --new-max
    to 5 or 6 until backlog stabilizes.
  - Pass rate below 70% sustained: cards are too hard or too vague.
    Check --show-failures for patterns. See section 2 for rewrite
    protocol.
  - Pass rate above 95% sustained: cards may be too easy or review
    is on autopilot. Cross-check against response time data
    (section 4). If average response times are also very fast,
    cards need more challenge or the criteria need tightening.


2. WEEKLY REVIEW HABIT
-----------------------
Every Sunday (or end of study week), run these in order:

    uv run sm2.py --show-failures
    uv run sm2.py --show-leeches

Read the error notes. For each failure, apply this decision tree:

    Is the error note vague or missing?
       The card's criteria need tightening. Rewrite criteria first.
    Did you get the answer right but couldn't articulate the reasoning?
       The card is testing recognition, not understanding. Add a
        "why" or "how" element to the question or criteria.
    Is the same confusion recurring across sessions?
       The card may be too complex. Split into smaller cards.
        Or the prerequisite understanding is shaky - check whether
        a foundational card exists and whether it's solid.
    Did you fail because the card was ambiguous, not because you
    didn't know the material?
       Rewrite the question for clarity. The card is fighting you,
        not teaching you.
    Is the material something you genuinely don't care about anymore?
       Delete the card. Dead weight kills motivation.

This is the deliberate practice loop (Ericsson). The grade is the
signal; the error note is the diagnosis; the rewrite is the
intervention. All three parts must happen.

Also run the domain balance query (section 6) at the same time.
Three queries, one sitting, weekly.


3. ZOMBIE ITEMS (Wozniak)
--------------------------
Items that technically pass but are drifting toward the EF floor.
Not leeches (they don't lapse), but they consume disproportionate
review time without real retention. Signal: EF below 1.8 with
multiple reviews and no recent lapse.

    sqlite3 data/sm2.db "
    SELECT item_id,
           easiness_factor AS ef,
           repetition_count AS reps,
           lapse_count AS lapses,
           CAST(julianday('now','localtime') - 1721424.5 AS INTEGER)
               - last_review AS days_since
    FROM items
    WHERE easiness_factor < 1.8
      AND repetition_count >= 3
      AND lapse_count < 3
    ORDER BY easiness_factor ASC"

Action protocol for zombies:
  - Check the source: field (once Phase F lands). Trace back to the
    original material. Reread the relevant section.
  - If the card is a bare fact, add a mnemonic cue or personal
    connection. Wozniak: vivid associations rescue drifting items.
  - If the card is testing too many things at once, split it.
  - If you can't make it stick after two rewrites, the problem is
    likely upstream - you don't understand the material well enough.
    Go back to the source and rebuild understanding before
    reformulating.


4. RESPONSE TIME DISTRIBUTION (Ericsson)
------------------------------------------
After you have ~50 reviews logged with timing:

    sqlite3 data/sm2.db "
    SELECT domain,
           COUNT(*) AS n,
           ROUND(MIN(response_seconds), 1) AS min_s,
           ROUND(AVG(response_seconds), 1) AS avg_s,
           ROUND(MAX(response_seconds), 1) AS max_s
    FROM review_log
    WHERE response_seconds IS NOT NULL
    GROUP BY domain
    ORDER BY domain"

Watch for and act on:

  Very fast responses (<3s) on non-trivial cards:
    Recognition, not recall. The card may be too easy or the cue
    too obvious (pattern matching the first few words, not actually
    thinking). Action: tighten the criteria to require articulating
    the reasoning, not just the answer. Or retire the card if it's
    now subsumed by a harder card that exercises the same knowledge.

  Very slow responses (>60s) on simple cards:
    The formulation is unclear or the card is actually testing
    multiple things. Action: check whether the card violates minimum
    information. Split or rewrite. If the slowness is because the
    material is genuinely difficult, that's fine - but track whether
    the time decreases over reviews. Sustained slowness without
    improvement means the card isn't working.

  Domain-level differences:
    A domain with consistently high average times may indicate
    unfamiliar material (expected during bootstrapping) or poor
    card design (investigate if it persists past week two). Compare
    against domain success rates (section 4b) to distinguish.

Per-item outliers (cards that consistently take longest):

    sqlite3 data/sm2.db "
    SELECT item_id,
           COUNT(*) AS reviews,
           ROUND(AVG(response_seconds), 1) AS avg_s
    FROM review_log
    WHERE response_seconds IS NOT NULL
    GROUP BY item_id
    HAVING COUNT(*) >= 3
    ORDER BY avg_s DESC
    LIMIT 10"

These are your highest-friction items. Cross-reference with
--show-failures. Items that are both slow and failing are prime
candidates for rewrite or split. Items that are slow but passing
may be legitimately hard - monitor but don't rush to change them.


4b. PER-DOMAIN SUCCESS RATE (Skycak)
--------------------------------------
The aggregate pass rate (section 1) hides domain-level variation.
A domain stuck at 55% tells you something different from one at 90%.

    sqlite3 data/sm2.db "
    WITH t AS (SELECT cast(julianday('now','localtime') - 1721424.5 AS INTEGER) AS today)
    SELECT domain,
           COUNT(*) AS reviews,
           round(100.0 * SUM(CASE WHEN grade > 0 THEN 1 ELSE 0 END)
                 / COUNT(*), 1) AS pass_pct
    FROM review_log, t
    WHERE review_date > t.today - 14
    GROUP BY domain
    ORDER BY pass_pct ASC"

Target range: 70-85% per domain (Skycak's calibration window).

  Below 70%: cards are too hard, too vague, or prerequisites are
    missing. Check --show-failures filtered to that domain. Look
    for patterns: are failures concentrated on a few items or
    spread across many? Concentrated means bad cards. Spread means
    the domain needs more foundational items before you add
    advanced ones.

  Above 90%: the domain may be under-challenged. You're in
    maintenance mode. If this is a domain you're actively trying
    to grow, add harder cards or convert textbook problems into
    entries (section 11). If it's a stable domain you just want
    to maintain, 90%+ is fine.


5. PREREQUISITE GATE QUALITY (Skycak)
---------------------------------------
After prerequisite chains are in use (build_blocked_set re-enabled):

Watch for this pattern in --show-failures output: a downstream card
fails, and the error note reveals shaky understanding of a
prerequisite that technically passed the gate (single grade > 0).

Track manually at first. If it happens more than twice in two
weeks, tighten build_blocked_set to require:
  - grade > 0 on at least 2 distinct review_dates, OR
  - repetition_count >= 2 in items table

Don't tighten preemptively. The lenient gate is correct for
bootstrapping - you need cards flowing through the system to
generate the feedback that tells you whether stricter gating
is needed.


6. DOMAIN BALANCE AND AUTHORING PACE
--------------------------------------
Run weekly alongside --show-failures/--show-leeches:

    sqlite3 data/sm2.db "
    SELECT substr(item_id, 1, instr(item_id, '-') - 1) AS domain,
           COUNT(*) AS total,
           SUM(CASE WHEN repetition_count = 0 THEN 1 ELSE 0 END) AS unseen,
           SUM(CASE WHEN repetition_count > 0 THEN 1 ELSE 0 END) AS active
    FROM items
    GROUP BY domain
    ORDER BY domain"

Key metric: unseen count per domain. If unseen grows for two
straight weeks in any domain, you're authoring faster than the
throttle introduces cards. Either slow authoring or bump --new-max.

Quick card count per file without touching the database:

    grep -c "^@@@ id:" exercises/*.md

Authoring tools (exnew / exopen) are available in .bashrc.
EX_EXERCISES_DIR must point to the correct location before use.
Update that variable when exercises move (worktree  USB, etc.).

Domain balance check (Skycak): are you only authoring cards in
domains where you're already comfortable? If your strong domains
have 20+ items and your weak domains have 3, the system is
reinforcing existing strengths rather than building new ones.
This is the natural path of least resistance - resist it
deliberately during authoring sessions.


7. THROTTLE SCALING
--------------------
Current: TOTAL_NEW_MAX=9, MIN_PER_DOMAIN=1.

Reserved slots = number of active domains. Non-reserved budget
= TOTAL_NEW_MAX - reserved - already_new_today.

With each new domain added, reserved slots grow by 1. At 9 domains,
reserved = budget = 0. The throttle loses all flexibility.

Monitor after adding each domain:

    uv run sm2.py --dry-run

If the queue is entirely new items with no room for natural
ordering, the reservation model is saturated. Options at that point:
  - Bump TOTAL_NEW_MAX proportionally (3 per active domain)
  - Drop MIN_PER_DOMAIN to 0 for stable domains
  - Add active/inactive domain concept to throttle

Domains are growing actively. Run --dry-run after each new domain
is introduced, not just when problems appear.


8. RETIRED ITEMS IN READ-ONLY FLAGS
-------------------------------------
--show-failures and --show-leeches do not filter by parsed_ids.
Retired or removed items can appear in their output. This is
intentional (historical diagnostics) but worth keeping in mind
during weekly review: an item that appears here but no longer
exists in exercises/ can be ignored or noted in the friction log.

If this becomes noisy, the fix is to add a parsed_ids filter to
both queries - same pattern as --preview.


9. SESSION-LEVEL GUT CHECKS
-----------------------------
Not everything needs a query. Track these in your friction log
(flog) during or after sessions:

  - Am I dreading any particular domain? (burnout or card quality)
  - Are error notes getting repetitive? (same confusion recurring)
  - Am I skipping the answer prompt too often? (cards too vague)
  - Do grade-1 items feel like coin flips? (criteria too ambiguous)
  - Is the session length comfortable? (>30 min may need --max-reviews)
  - Am I reviewing on autopilot? (Ericsson: if you're not
    concentrating, you're not practicing. Shorter focused sessions
    beat long distracted ones.)

Cross-project friction patterns are visible in the central friction
log. Run ffriction sm2 to filter entries for this project.


10. EXTERNAL VALIDATION (Acton)
--------------------------------
Every metric above is internal to the system. EF, pass rate, and
response time measure how well you're doing at flashcards, not
whether you can actually use the knowledge. These are proxies.
The real question is: can you do something with this knowledge that
you couldn't do before?

Monthly check (first Sunday of each month, after section 2 review):

  For each active domain, answer honestly in your friction log:

  - Can I explain a concept from this domain to someone without
    looking anything up? Pick one at random and try.
  - When I read new material in this domain, do I understand more
    than I did a month ago?
  - Can I see connections between this domain and others that I
    couldn't see before?
  - For STEM domains: can I solve problems I couldn't solve a
    month ago?
  - For non-STEM domains: can I construct or evaluate an argument
    I couldn't a month ago?

If the answer is consistently "no" for a domain despite good
internal metrics, the cards are testing the wrong things. The
retention is real but the knowledge is inert. Rewrite cards to
target the actual capability you want, not the facts that are
easy to formulate.

This check has no query. It's a deliberate pause to ask Acton's
question: is this solving the real problem, or am I just good at
my own flashcards?


11. CARD EVOLUTION AND CONTENT STRATEGY
-----------------------------------------
Cards should evolve over time. The trajectory is:

  Basic facts (bootstrapping)  compound problems (proficiency)
     cross-domain synthesis (integration)

Track this qualitatively during weekly review. In each domain, ask:

  - Are most of my cards still isolated facts, or have I started
    writing problems that require combining multiple facts?
  - Have I written any cards that connect this domain to another?
  - In STEM domains: am I solving multi-step problems, or just
    recalling definitions?
  - In non-STEM domains: am I evaluating arguments and making
    connections, or just recalling names and dates?

When basic fact cards in a domain consistently pass at 90%+, that's
the signal to start converting textbook problems or writing compound
prompts that subsume those facts. The basic cards can then fade in
frequency - they're being exercised implicitly by the harder items
(Skycak's Math Academy insight: prerequisites practiced inside
advanced problems count as practiced).

Textbook problem conversion protocol:
  - Select problems that test concepts you found genuinely tricky,
    not routine drill problems with different numbers.
  - Rewrite in your own words. Trim setup to the essential challenge.
  - Write criteria yourself BEFORE checking the textbook solution.
  - Add source: field pointing to the textbook and problem number.
  - Prefer problems that are confusable with other items in your
    deck - these build discrimination, not just recall (Skycak).

For non-STEM domains, the equivalent of textbook problems:
  - Philosophy/theology: argument evaluation prompts from syllabi
    or textbook discussion questions. Criteria should require
    identifying premises, key moves, and at least one objection.
  - History: causal explanation prompts ("Why did X lead to Y?").
    Criteria should require naming specific factors, not just
    the conclusion.
  - Literature: analysis prompts about technique, form, or
    thematic connection. Avoid plot-recall cards - they're low
    value.

When to start: after day 14 review, once basic items are flowing
and you have a feel for the system's rhythm. Don't front-load
complexity during the bootstrapping phase.


12. LLM-ASSISTED REFINEMENT
-----------------------------
LLMs can be useful as card editors. They are harmful as card
authors. The act of formulating a card is itself deliberate
practice (Ericsson) - outsourcing it shortcuts the most valuable
part of the process.

Permitted uses (after you have written the card yourself):
  - "Is this card ambiguous? Could it be interpreted differently?"
  - "What's a common misconception related to this concept that I
    should make a confusable variant card for?"
  - "Does my criteria actually capture understanding, or just
    surface recall?"
  - "Is this card actually testing two things? Should I split it?"

Not permitted (before you have struggled with formulation):
  - Having an LLM generate cards from source material.
  - Having an LLM write criteria for you.
  - Having an LLM decide what's important from a chapter.

Tag any card that received substantial LLM editing input with
source: llm-refined (or append to existing source). This enables
future auditing via --show-sources (deferred) to see whether
LLM-refined cards have different failure/leech rates than
self-authored ones. Do not over-tag - minor wording suggestions
don't need the tag.

For weak domains where bootstrapping is hardest: the temptation
to use LLMs for card generation will be strongest here, because
formulation is most difficult when understanding is thin. Resist.
Write provisional cards marked [draft], struggle with them, and
refine through the weekly review cycle. The struggle is the
learning.


13. BOOTSTRAPPING WEAK DOMAINS
--------------------------------
In domains where you're a novice, Wozniak's rule 1 (understand
before memorizing) creates a chicken-and-egg problem. You can't
make good cards because you don't understand enough yet.

Protocol:
  - Start with orientation cards that map the territory: major
    schools of thought, central questions, key figures, major
    divisions. These structural cards are the scaffold.
  - Mark early cards as provisional: add [draft] to the content
    or a tag. Plan to revisit them after more reading.
  - Use your strong domains as bridges. Write cross-domain cards
    that connect new material to things you already know deeply.
    These are high-value items unique to your breadth.
  - Accept a higher failure rate (section 4b) in new domains
    during weeks 1-4. Below-70% pass rate in a brand-new domain
    is expected and not a signal to slow down - it's a signal to
    keep reading alongside reviewing.
  - Track the [draft]  rewritten conversion rate informally.
    If provisional cards are still marked [draft] after four
    weeks, either rewrite them or delete them. Stale drafts are
    a sign you've moved past what they were trying to capture.


14. FIRST TWO WEEKS CALENDAR
------------------------------
Days 1-3:   Just use it. Don't optimize anything. Author content
            with exnew. Use flog to capture friction as it surfaces.

Days 4-7:   Run domain balance query. Check unseen backlog.
            Check EX_EXERCISES_DIR still points to correct location.

Day 7:      First --show-failures and --show-leeches review.
            Read error notes. Apply section 2 decision tree.
            Run ffriction sm2 alongside.

Days 8-14:  Run zombie query. Check response_seconds distribution.
            Run per-domain success rate query (section 4b).

Day 14:     Full review: all queries above. Decide what to change.
            If domains >= 7, check throttle headroom via --dry-run.
            First external validation check (section 10) - brief,
            one honest answer per active domain.
            Decide whether to begin textbook problem conversion
            (section 11) based on which domains have stabilized.

Day 15+:    System enters steady state. Weekly reviews continue.
            Monthly external validation continues. Card evolution
            (section 11) becomes the primary authoring focus.
