-- =============================================================================
-- SM-2 ANALYTICS REFERENCE QUERIES
-- =============================================================================
-- All dates in sm2.db are stored as Python ordinal integers:
--   datetime.date.today().toordinal()
-- To derive today's ordinal inside SQLite use:
--   cast(julianday('now', 'localtime') - 1721424.5 AS INTEGER)
-- Queries below use a WITH today CTE wherever a live date is required.
-- Run against: data/sm2.db
-- =============================================================================

-- 7-day retention rate per domain
-- Healthy target: pass rate >= 85% per domain over any rolling 7-day window.
-- Pass is grade >= 1 (user chose "passed with effort" or "easy, fluent").
WITH today AS (
    SELECT cast(julianday('now', 'localtime') - 1721424.5 AS INTEGER) AS ordinal
)
SELECT
    domain,
    count(*)                                                          AS total_reviews,
    sum(CASE WHEN grade >= 1 THEN 1 ELSE 0 END)                      AS passed,
    round(
        100.0 * sum(CASE WHEN grade >= 1 THEN 1 ELSE 0 END) / count(*),
        1
    )                                                                 AS pass_rate_percent
FROM review_log, today
WHERE review_date >= today.ordinal - 7
GROUP BY domain
ORDER BY domain;

-- -----------------------------------------------------------------------------

-- Easiness factor distribution across all items
-- Healthy target: median easiness_factor above 2.2;
--   fewer than 10% of items below 1.6 (struggling items).
SELECT
    round(easiness_factor, 1)  AS easiness_factor_bucket,
    count(*)                   AS item_count
FROM items
GROUP BY round(easiness_factor, 1)
ORDER BY easiness_factor_bucket;

-- -----------------------------------------------------------------------------

-- Daily review load: items due each day for the next 14 days
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

-- -----------------------------------------------------------------------------

-- Leech detection: items with three or more lapses
-- Healthy target: zero leeches. Each leech warrants content review or
--   item restructuring (split overly complex items, improve criteria clarity).
SELECT
    item_id,
    lapse_count,
    easiness_factor,
    interval_days,
    repetition_count
FROM items
WHERE lapse_count >= 3
ORDER BY lapse_count DESC, easiness_factor ASC;

-- -----------------------------------------------------------------------------

-- New item introduction rate per domain over the last 30 days
-- Healthy target: 3-9 new items per day total; no single day above 9
--   (matches TOTAL_NEW_MAX). Consistent daily intake beats irregular bursts.
WITH today AS (
    SELECT cast(julianday('now', 'localtime') - 1721424.5 AS INTEGER) AS ordinal
)
SELECT
    review_date,
    domain,
    count(*)  AS new_items_introduced
FROM review_log, today
WHERE repetition_count_before = 0
  AND review_date >= today.ordinal - 30
GROUP BY review_date, domain
ORDER BY review_date DESC, domain;
