"""Equivalence spike: the ported advance_schedule_state must agree with the
original sm2.sm2_update on every field over a dense parameter grid, and the
fuzz must be deterministic, bounded, and exempt below the opening steps."""

import sys

sys.path.insert(0, "/home/claude/explorations/sm2")
import sm2 as original_sm2
from scheduler_port import (
    advance_schedule_state,
    apply_interval_fuzz,
    INTERVAL_FUZZ_FRACTION,
)

failure_count = 0
comparison_count = 0

for grade in (0, 1, 2):
    for easiness_times_ten in range(13, 31, 2):
        for interval_days in (0.0, 1.0, 6.0, 15.0, 87.5, 365.0):
            for repetition_count in (0, 1, 2, 3, 10):
                for lapse_count in (0, 1, 5):
                    for review_date in (700000, 739000):
                        original = original_sm2.sm2_update(
                            grade,
                            easiness_times_ten / 10.0,
                            interval_days,
                            repetition_count,
                            lapse_count,
                            review_date,
                        )
                        ported = advance_schedule_state(
                            grade,
                            easiness_times_ten / 10.0,
                            interval_days,
                            repetition_count,
                            lapse_count,
                            review_date,
                        )
                        comparison_count += 1
                        for field in original:
                            if original[field] != ported[field]:
                                failure_count += 1
                                print(
                                    "MISMATCH",
                                    grade,
                                    easiness_times_ten / 10.0,
                                    interval_days,
                                    repetition_count,
                                    field,
                                    original[field],
                                    ported[field],
                                )

print("compared %d parameter points" % comparison_count)
print(
    ("PASS  " if failure_count == 0 else "FAIL  ")
    + "ported scheduler is field-identical to sm2.sm2_update"
)

fuzz_ok = True
for question_id in range(1, 2000):
    once = apply_interval_fuzz(30.0, question_id)
    twice = apply_interval_fuzz(30.0, question_id)
    if once != twice:
        fuzz_ok = False
    if abs(once - 30.0) > 30.0 * INTERVAL_FUZZ_FRACTION + 1e-9:
        fuzz_ok = False
for short_interval in (0.0, 1.0, 2.0):
    if apply_interval_fuzz(short_interval, 7) != short_interval:
        fuzz_ok = False
print(("PASS  " if fuzz_ok else "FAIL  ") + "fuzz deterministic, bounded, exempt <= 2d")

distinct_due_dates = len(
    {700000 + int(round(apply_interval_fuzz(30.0, qid))) for qid in range(1, 101)}
)
print(
    "FINDING  100 questions at interval 30 spread over %d distinct due dates "
    "(unfuzzed: 1)" % distinct_due_dates
)

raise SystemExit(1 if failure_count else 0)
