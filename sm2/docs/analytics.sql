-- =============================================================================
-- SM-2 ANALYTICS REFERENCE QUERIES
-- =============================================================================
-- ORDINAL DATE CONVERSION
-- =============================================================================
-- Python stores dates as ordinal integers (date.toordinal()).
-- julianday('0001-01-01') = 1721425.5, ordinal of that date = 1,
-- so offset = 1721424.5.
--
-- Today's ordinal (for WHERE clauses):
--   cast(julianday('now', 'localtime') - 1721424.5 AS INTEGER)
--
-- Convert stored ordinal to ISO date string:
--   date(review_date + 1721424.5)
--
-- Example: items reviewed in the last 7 days:
--   WHERE review_date >= cast(julianday('now','localtime')
--                             - 1721424.5 AS INTEGER) - 7
-- =============================================================================
-- Run against: data/sm2.db
-- =============================================================================

-- =============================================================================
-- DOMAIN BALANCE: total / unseen / active per domain
-- =============================================================================
SELECT substr(item_id, 1, instr(item_id, '-') - 1) AS domain,
       count(*)                                      AS total,
       sum(CASE WHEN repetition_count = 0 THEN 1 ELSE 0 END) AS unseen,
       sum(CASE WHEN repetition_count > 0 THEN 1 ELSE 0 END) AS active
FROM items
GROUP BY domain
ORDER BY domain;

-- =============================================================================
-- AUTHORING RATE: cards added per week per domain (last 28 days)
-- =============================================================================
-- Uses original due_date as proxy for creation date (new items
-- get due_date = today at insert time). Not exact after a lapse
-- resets due_date, but good enough for monitoring authoring pace
-- on genuinely new cards.
WITH t AS (
    SELECT cast(julianday('now','localtime') - 1721424.5 AS INTEGER) AS today
)
SELECT substr(item_id, 1, instr(item_id, '-') - 1) AS domain,
       (t.today - due_date) / 7                     AS weeks_ago,
       count(*)                                      AS added
FROM items, t
WHERE repetition_count = 0
  AND due_date > t.today - 28
GROUP BY domain, weeks_ago
ORDER BY domain, weeks_ago;

-- =============================================================================
-- 7-DAY RETENTION RATE per domain
-- =============================================================================
-- Healthy target: pass rate >= 85% per domain over any rolling 7-day window.
-- Pass is grade >= 1 (user chose "passed with effort" or "easy, fluent").
WITH today AS (
    SELECT cast(julianday('now', 'localtime') - 1721424.5 AS INTEGER) AS ordinal
)
SELECT
    domain,
    count(*)                                                     AS total_reviews,
    sum(CASE WHEN grade >= 1 THEN 1 ELSE 0 END)                 AS passed,
    round(
        100.0 * sum(CASE WHEN grade >= 1 THEN 1 ELSE 0 END) / count(*),
        1
    )                                                            AS pass_rate_percent
FROM review_log, today
WHERE review_date >= today.ordinal - 7
GROUP BY domain
ORDER BY domain;

-- =============================================================================
-- EASINESS FACTOR DISTRIBUTION across all items
-- =============================================================================
-- Healthy target: median easiness_factor above 2.2;
--   fewer than 10% of items below 1.6 (struggling items).
SELECT
    round(easiness_factor, 1)  AS easiness_factor_bucket,
    count(*)                   AS item_count
FROM items
GROUP BY round(easiness_factor, 1)
ORDER BY easiness_factor_bucket;

-- =============================================================================
-- DAILY REVIEW LOAD: items due each day for the next 14 days
-- =============================================================================
-- Healthy target: average daily load below 30; no single day above 50.
-- Spikes suggest a past session introduced too many items at once.
WITH today AS (
    SELECT cast(julianday('now', 'localtime') - 1721424.5 AS INTEGER) AS ordinal
)
SELECT
    due_date - today.ordinal  AS days_from_today,
    count(*)                  AS items_due
FROM items, today
WHERE due_date >= today.ordinal
  AND due_date <= today.ordinal + 14
GROUP BY due_date
ORDER BY due_date;

-- =============================================================================
-- NEW ITEM INTRODUCTION RATE per domain over the last 30 days
-- =============================================================================
-- Healthy target: 3-9 new items per day total; no single day above 9
--   (matches TOTAL_NEW_MAX). Consistent daily intake beats irregular bursts.
WITH today AS (
    SELECT cast(julianday('now', 'localtime') - 1721424.5 AS INTEGER) AS ordinal
)
SELECT
    date(review_date + 1721424.5)  AS review_date_iso,
    domain,
    count(*)                        AS new_items_introduced
FROM review_log, today
WHERE repetition_count_before = 0
  AND review_date >= today.ordinal - 30
GROUP BY review_date, domain
ORDER BY review_date DESC, domain;
