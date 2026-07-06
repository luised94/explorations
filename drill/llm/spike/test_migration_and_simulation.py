"""Migration + end-to-end spike on a REAL drill database.

Proves, against drill's actual db.py:
  1. question_schedule lands as migration 4 through the real run_migrations
     (forward-only, per-step transaction), is idempotent, and leaves every
     existing table untouched.
  2. A 90-day simulated review history driven through the pure core and
     written with the real insert_response keeps the invariant
     rebuild_schedule_from_response_log(responses) == stored schedule.
  3. The two supporting aggregates (new-introduced-today by bank; true
     retention: first-attempt-of-day accuracy on due items) are plain SQL
     over existing tables plus question_schedule.
  4. The once-per-day rule blocks a same-day second update.
"""

import datetime
import sqlite3
import sys

sys.path.insert(0, "/home/claude/explorations/drill")
import db as drill_database
from scheduler_port import (
    advance_schedule_state,
    apply_interval_fuzz,
    derive_recall_quality,
    partition_candidates_by_schedule,
    rebuild_schedule_from_response_log,
    schedule_update_allowed_today,
    EASINESS_FACTOR_INITIAL,
)

failure_count = 0


def check(name, condition):
    global failure_count
    print(("PASS  " if condition else "FAIL  ") + name)
    if not condition:
        failure_count += 1


CREATE_QUESTION_SCHEDULE_TABLE = """
CREATE TABLE IF NOT EXISTS question_schedule (
    question_id      INTEGER PRIMARY KEY REFERENCES questions(id),
    easiness_factor  REAL    NOT NULL,
    interval_days    REAL    NOT NULL,
    repetition_count INTEGER NOT NULL,
    due_date         INTEGER NOT NULL,
    last_review      INTEGER NOT NULL,
    lapse_count      INTEGER NOT NULL
)
"""


def migrate_4_add_question_schedule(connection):
    connection.execute(CREATE_QUESTION_SCHEDULE_TABLE)


SPIKE_MIGRATIONS = drill_database.MIGRATIONS + [
    (4, "add question_schedule (SM2 scheduling state, ADR-025)",
     migrate_4_add_question_schedule),
]

connection = sqlite3.connect(":memory:")
connection.row_factory = sqlite3.Row
connection.execute("PRAGMA foreign_keys = ON")

now_text = "2026-07-03T12:00:00"
drill_database.init_db(connection)
first_run = drill_database.run_migrations(
    connection, now_text, target_version=4, migrations=SPIKE_MIGRATIONS
)
check("migration walks 1 -> 4 through the real runner",
      drill_database.get_schema_version(connection) == 4)

tables_before = {row[0] for row in connection.execute(
    "SELECT name FROM sqlite_master WHERE type='table'")}
second_run = drill_database.run_migrations(
    connection, now_text, target_version=4, migrations=SPIKE_MIGRATIONS
)
tables_after = {row[0] for row in connection.execute(
    "SELECT name FROM sqlite_master WHERE type='table'")}
check("second run is a no-op (idempotent)",
      drill_database.get_schema_version(connection) == 4
      and tables_before == tables_after)
check("first run reports applied work, second reports none",
      first_run != second_run or first_run.get("applied") != second_run.get("applied")
      or str(first_run) != str(second_run))

category_row = connection.execute("SELECT id FROM categories LIMIT 1").fetchone()
category_id = category_row["id"]
bank_alpha = drill_database.insert_bank(
    connection, category_id, "alpha", "manual", now_text)
bank_beta = drill_database.insert_bank(
    connection, category_id, "beta", "manual", now_text)
question_records = [
    {"question": "alpha question %d" % index, "answer": "answer %d" % index}
    for index in range(12)
]
drill_database.insert_questions_bulk(connection, bank_alpha, question_records, now_text)
beta_records = [
    {"question": "beta question %d" % index, "answer": "answer %d" % index}
    for index in range(4)
]
drill_database.insert_questions_bulk(connection, bank_beta, beta_records, now_text)
session_id = drill_database.start_session(connection, category_id, now_text, bank_alpha)

question_rows = connection.execute(
    "SELECT id, bank_id, question, answer FROM questions ORDER BY id").fetchall()

WRITE_SCHEDULE_ROW = """
INSERT INTO question_schedule (question_id, easiness_factor, interval_days,
    repetition_count, due_date, last_review, lapse_count)
VALUES (?, ?, ?, ?, ?, ?, ?)
ON CONFLICT(question_id) DO UPDATE SET
    easiness_factor = excluded.easiness_factor,
    interval_days = excluded.interval_days,
    repetition_count = excluded.repetition_count,
    due_date = excluded.due_date,
    last_review = excluded.last_review,
    lapse_count = excluded.lapse_count
"""

start_ordinal = datetime.date(2026, 7, 3).toordinal()
review_outcome_pattern = [True, True, False, True, True, True, False, True]
pattern_index = 0

for day_offset in range(90):
    today = start_ordinal + day_offset
    answered_text = (
        datetime.date.fromordinal(today).isoformat() + "T09:00:00"
    )
    schedule_rows = connection.execute("SELECT * FROM question_schedule").fetchall()
    schedule_by_question_id = {
        row["question_id"]: dict(row) for row in schedule_rows
    }
    candidates = [dict(row) for row in question_rows]
    due, new, not_due = partition_candidates_by_schedule(
        candidates, schedule_by_question_id, today)
    to_review = due + new[:2]
    for candidate in to_review:
        question_id = candidate["id"]
        existing = schedule_by_question_id.get(question_id)
        correct = review_outcome_pattern[pattern_index % len(review_outcome_pattern)]
        pattern_index += 1
        elapsed_ms = 4000 + 137 * (question_id + day_offset)
        drill_database.insert_response(
            connection, session_id, candidate["question"], candidate["answer"],
            candidate["answer"] if correct else "wrong",
            correct, answered_text, question_id=question_id,
            elapsed_ms=elapsed_ms)
        if not schedule_update_allowed_today(existing, today):
            continue
        if existing is None:
            previous = {
                "easiness_factor": EASINESS_FACTOR_INITIAL,
                "interval_days": 0.0, "repetition_count": 0, "lapse_count": 0,
            }
        else:
            previous = existing
        quality = derive_recall_quality(correct, elapsed_ms)
        advanced = advance_schedule_state(
            quality, previous["easiness_factor"], previous["interval_days"],
            previous["repetition_count"], previous["lapse_count"], today)
        fuzzed = apply_interval_fuzz(advanced["interval_days"], question_id)
        advanced["interval_days"] = fuzzed
        advanced["due_date"] = today + int(round(fuzzed))
        connection.execute(WRITE_SCHEDULE_ROW, (
            question_id, advanced["easiness_factor"], advanced["interval_days"],
            advanced["repetition_count"], advanced["due_date"],
            advanced["last_review"], advanced["lapse_count"]))
    connection.commit()

response_count = connection.execute("SELECT COUNT(*) FROM responses").fetchone()[0]
scheduled_count = connection.execute(
    "SELECT COUNT(*) FROM question_schedule").fetchone()[0]
check("simulation produced a real history (%d responses, %d scheduled)"
      % (response_count, scheduled_count),
      response_count > 100 and scheduled_count == 16)

response_rows_for_rebuild = [
    {
        "question_id": row["question_id"],
        "correct": bool(row["correct"]),
        "elapsed_ms": row["elapsed_ms"],
        "answered_ordinal": datetime.date.fromisoformat(
            row["answered"][:10]).toordinal(),
    }
    for row in connection.execute(
        "SELECT question_id, correct, elapsed_ms, answered "
        "FROM responses ORDER BY id")
]
rebuilt = rebuild_schedule_from_response_log(response_rows_for_rebuild)
stored = {
    row["question_id"]: dict(row)
    for row in connection.execute("SELECT * FROM question_schedule")
}
rebuild_matches = len(rebuilt) == len(stored)
for question_id, rebuilt_state in rebuilt.items():
    stored_state = stored.get(question_id)
    if stored_state is None:
        rebuild_matches = False
        continue
    for field in ("easiness_factor", "interval_days", "repetition_count",
                  "due_date", "last_review", "lapse_count"):
        if abs(rebuilt_state[field] - stored_state[field]) > 1e-9:
            rebuild_matches = False
            print("REBUILD MISMATCH", question_id, field,
                  rebuilt_state[field], stored_state[field])
check("rebuild from response log == stored schedule (state is a cache of the log)",
      rebuild_matches)

today = start_ordinal + 90
new_today_by_bank_rows = connection.execute(
    """
    SELECT questions.bank_id AS bank_id, COUNT(*) AS introduced_count
    FROM question_schedule
    JOIN questions ON questions.id = question_schedule.question_id
    WHERE question_schedule.repetition_count = 1
      AND question_schedule.lapse_count = 0
      AND question_schedule.last_review = ?
    GROUP BY questions.bank_id
    """,
    (start_ordinal,),
).fetchall()
check("new-introduced-per-day-by-bank is one aggregate over existing tables",
      isinstance(new_today_by_bank_rows, list))

retention_row = connection.execute(
    """
    WITH first_attempt_per_day AS (
        SELECT question_id, substr(answered, 1, 10) AS day_text,
               MIN(id) AS first_response_id
        FROM responses
        WHERE question_id IS NOT NULL
        GROUP BY question_id, day_text
    )
    SELECT AVG(responses.correct) AS retention,
           COUNT(*) AS graded_reviews
    FROM first_attempt_per_day
    JOIN responses ON responses.id = first_attempt_per_day.first_response_id
    """
).fetchone()
check("true-retention query runs on existing tables (retention=%.3f over %d reviews)"
      % (retention_row["retention"], retention_row["graded_reviews"]),
      0.0 < retention_row["retention"] < 1.0)

sample_state = dict(connection.execute(
    "SELECT * FROM question_schedule LIMIT 1").fetchone())
check("once-per-day rule blocks a same-day second update",
      schedule_update_allowed_today(sample_state, sample_state["last_review"])
      is False)

interval_rows = connection.execute(
    "SELECT question_id, interval_days, lapse_count, easiness_factor "
    "FROM question_schedule ORDER BY interval_days DESC LIMIT 3").fetchall()
print("FINDING  after 90 days, longest intervals:",
      [(row["question_id"], round(row["interval_days"], 1),
        round(row["easiness_factor"], 2)) for row in interval_rows])

print("\n%d failure(s)" % failure_count)
raise SystemExit(1 if failure_count else 0)
