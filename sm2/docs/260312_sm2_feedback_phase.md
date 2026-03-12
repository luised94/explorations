===============================================================================
SM-2 FEEDBACK PHASE - METRICS AND WATCH LIST
===============================================================================

Reference document for the first two weeks of daily use.
Run these periodically. Act on patterns, not individual data points.


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

If due-tomorrow is consistently above 30 after the first two weeks,
drop --new-max to 5 or 6 until the backlog stabilizes. Pass rate
below 70% sustained means cards are too hard or too vague - check
--failures notes for patterns.


2. WEEKLY REVIEW HABIT
---------------------
Every Sunday (or end of study week), run these in order:

    uv run sm2.py --failures
    uv run sm2.py --leeches

Read the error notes. For each failure, decide: rewrite the card,
split it into smaller cards, or update your mental model. This is
the deliberate practice loop (Ericsson). The grade is the signal;
the error note is the diagnosis.


3. ZOMBIE ITEMS (Wozniak)
-------------------------
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

If items show up here repeatedly, the card formulation is fighting
you. Rewrite to be more atomic, add a cue, or split the card.


4. RESPONSE TIME DISTRIBUTION (Ericsson)
-----------------------------------------
After D.02 lands and you have ~50 reviews logged with timing:

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

Watch for:
  - Very fast responses (<3s) on non-trivial cards: recognition,
    not recall. The card may be too easy or the cue too obvious.
  - Very slow responses (>60s) on simple cards: the formulation
    is unclear or the card is actually testing multiple things.
  - Domain-level differences: a domain with consistently high
    average times may indicate unfamiliar material (expected early)
    or poor card design (investigate if it persists).

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


5. PREREQUISITE GATE QUALITY (Skycak)
--------------------------------------
After D.06 lands and prerequisite chains are in use:

Watch for this pattern in --failures output: a downstream card
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
-------------------------------------
Run weekly alongside --failures/--leeches:

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


7. THROTTLE SCALING
-------------------
Current: TOTAL_NEW_MAX=9, MIN_PER_DOMAIN=1, 4 domains.
Reserved slots = 4, non-reserved = 5. Comfortable.

With each new domain added, reserved slots grow by 1. At 9 domains,
reserved = non-reserved budget = 0. The throttle loses all
flexibility.

Monitor after adding each domain:

    uv run sm2.py --dry-run

If the queue is entirely new items with no room for natural
ordering, the reservation model is saturated. Options at that
point:
  - Bump TOTAL_NEW_MAX proportionally (3 per active domain)
  - Drop MIN_PER_DOMAIN to 0 for stable domains
  - Add active/inactive domain concept to throttle


7. SESSION-LEVEL GUT CHECKS
----------------------------
Not everything needs a query. Track these in your friction log:

  - Am I dreading any particular domain? (burnout or card quality)
  - Are error notes getting repetitive? (same confusion recurring)
  - Am I skipping the answer prompt too often? (cards too vague)
  - Do grade-1 items feel like coin flips? (criteria too ambiguous)
  - Is the session length comfortable? (>30 min may need --max-reviews)


11. FIRST TWO WEEKS CALENDAR
----------------------------
Days 1-3:   Just use it. Don't optimize anything. Author history cards.
Days 4-7:   Run domain balance query. Check unseen backlog.
Day 7:      First --failures and --leeches review. Read error notes.
Days 8-14:  Run zombie query. Check response_seconds distribution.
Day 14:     Full review: all queries above. Decide what to change.
