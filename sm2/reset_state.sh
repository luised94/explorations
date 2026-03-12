#!/usr/bin/env bash
set -euo pipefail
DATABASE_PATH="${1:-data/sm2.db}"
if [ ! -f "$DATABASE_PATH" ]; then
    echo "error: database not found at '$DATABASE_PATH'" >&2
    exit 1
fi
sqlite3 "$DATABASE_PATH" <<'SQL'
PRAGMA wal_checkpoint(TRUNCATE);
SELECT 'resetting ' || count(*) || ' item(s)...' FROM items;
UPDATE items SET
    easiness_factor  = 2.5,
    interval_days    = 0.0,
    repetition_count = 0,
    -- offset derivation: see analytics.sql ordinal conversion comment
    due_date         = cast(julianday('now', 'localtime') - 1721424.5
                       AS INTEGER),
    last_review      = 0,
    lapse_count      = 0;
SELECT 'reset complete: ' || count(*) || ' item(s) reset.' FROM items;
SQL
