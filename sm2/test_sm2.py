import datetime
import sys
from typing import TypeAlias

from sm2 import USER_GRADE_TO_SM2_GRADE, sm2_update

# =============================================================================
# CONFIGURATION
# =============================================================================

ReviewResult: TypeAlias = dict[str, float | int]

FLOAT_TOLERANCE: float = 0.0001
failure_count: int = 0
start_date: int = datetime.date(2025, 1, 1).toordinal()

# =============================================================================
# POINT ASSERTIONS
# =============================================================================

# --- grade 2 from SM-2 defaults ---
# inputs:   grade=2, ef=2.5, interval=0.0, rep=0, lapse=0
# expected: ef=2.6, interval=1.0, rep=1, lapse=0, due=start_date+1

result_grade2: ReviewResult = sm2_update(2, 2.5, 0.0, 0, 0, start_date)

if abs(result_grade2["easiness_factor"] - 2.6) > FLOAT_TOLERANCE:
    print(f"FAIL [grade2 ef]: expected 2.6 got {result_grade2['easiness_factor']}")
    failure_count += 1

if result_grade2["interval_days"] != 1.0:
    print(f"FAIL [grade2 interval]: expected 1.0 got {result_grade2['interval_days']}")
    failure_count += 1

if result_grade2["repetition_count"] != 1:
    print(f"FAIL [grade2 rep]: expected 1 got {result_grade2['repetition_count']}")
    failure_count += 1

if result_grade2["lapse_count"] != 0:
    print(f"FAIL [grade2 lapse]: expected 0 got {result_grade2['lapse_count']}")
    failure_count += 1

if result_grade2["due_date"] != start_date + 1:
    print(f"FAIL [grade2 due_date]: expected {start_date + 1} got {result_grade2['due_date']}")
    failure_count += 1

# --- grade 1 from SM-2 defaults ---
# inputs:   grade=1, ef=2.5, interval=0.0, rep=0, lapse=0
# expected: ef=2.36, interval=1.0, rep=1, lapse=0

result_grade1: ReviewResult = sm2_update(1, 2.5, 0.0, 0, 0, start_date)

if abs(result_grade1["easiness_factor"] - 2.36) > FLOAT_TOLERANCE:
    print(f"FAIL [grade1 ef]: expected 2.36 got {result_grade1['easiness_factor']}")
    failure_count += 1

if result_grade1["interval_days"] != 1.0:
    print(f"FAIL [grade1 interval]: expected 1.0 got {result_grade1['interval_days']}")
    failure_count += 1

if result_grade1["repetition_count"] != 1:
    print(f"FAIL [grade1 rep]: expected 1 got {result_grade1['repetition_count']}")
    failure_count += 1

if result_grade1["lapse_count"] != 0:
    print(f"FAIL [grade1 lapse]: expected 0 got {result_grade1['lapse_count']}")
    failure_count += 1

# --- grade 0 from SM-2 defaults ---
# inputs:   grade=0, ef=2.5, interval=0.0, rep=0, lapse=0
# expected: ef=1.96, interval=1.0, rep=0 (no increment on fail), lapse=1

result_grade0: ReviewResult = sm2_update(0, 2.5, 0.0, 0, 0, start_date)

if abs(result_grade0["easiness_factor"] - 1.96) > FLOAT_TOLERANCE:
    print(f"FAIL [grade0 ef]: expected 1.96 got {result_grade0['easiness_factor']}")
    failure_count += 1

if result_grade0["interval_days"] != 1.0:
    print(f"FAIL [grade0 interval]: expected 1.0 got {result_grade0['interval_days']}")
    failure_count += 1

if result_grade0["repetition_count"] != 0:
    print(f"FAIL [grade0 rep]: expected 0 got {result_grade0['repetition_count']}")
    failure_count += 1

if result_grade0["lapse_count"] != 1:
    print(f"FAIL [grade0 lapse]: expected 1 got {result_grade0['lapse_count']}")
    failure_count += 1

# =============================================================================
# EF CLAMP ASSERTIONS
# =============================================================================

# --- EF floor: 10 consecutive grade-0, advancing current_date to due_date each step ---
# after 10 fails ef must be exactly 1.3 (clamped), never go below during loop

current_easiness_factor: float = 2.5
current_interval_days: float = 0.0
current_repetition_count: int = 0
current_lapse_count: int = 0
current_date: int = start_date

for step_index in range(10):
    floor_result: ReviewResult = sm2_update(
        0,
        current_easiness_factor,
        current_interval_days,
        current_repetition_count,
        current_lapse_count,
        current_date,
    )
    current_easiness_factor = floor_result["easiness_factor"]
    current_interval_days = floor_result["interval_days"]
    current_repetition_count = floor_result["repetition_count"]
    current_lapse_count = floor_result["lapse_count"]
    current_date = floor_result["due_date"]

    if current_easiness_factor < 1.3 - FLOAT_TOLERANCE:
        print(f"FAIL [ef floor step {step_index}]: dropped below 1.3: {current_easiness_factor}")
        failure_count += 1

if abs(current_easiness_factor - 1.3) > FLOAT_TOLERANCE:
    print(f"FAIL [ef floor final]: expected 1.3 got {current_easiness_factor}")
    failure_count += 1

# --- EF ceiling: 20 consecutive grade-2, advancing current_date to due_date each step ---
# after enough grade-2s ef must be exactly 3.0 (clamped), never exceed during loop

current_easiness_factor = 2.5
current_interval_days = 0.0
current_repetition_count = 0
current_lapse_count = 0
current_date = start_date

for step_index in range(20):
    ceil_result: ReviewResult = sm2_update(
        2,
        current_easiness_factor,
        current_interval_days,
        current_repetition_count,
        current_lapse_count,
        current_date,
    )
    current_easiness_factor = ceil_result["easiness_factor"]
    current_interval_days = ceil_result["interval_days"]
    current_repetition_count = ceil_result["repetition_count"]
    current_lapse_count = ceil_result["lapse_count"]
    current_date = ceil_result["due_date"]

    if current_easiness_factor > 3.0 + FLOAT_TOLERANCE:
        print(f"FAIL [ef ceil step {step_index}]: exceeded 3.0: {current_easiness_factor}")
        failure_count += 1

if abs(current_easiness_factor - 3.0) > FLOAT_TOLERANCE:
    print(f"FAIL [ef ceil final]: expected 3.0 got {current_easiness_factor}")
    failure_count += 1

# =============================================================================
# INTERVAL PROGRESSION ASSERTIONS
# =============================================================================

# --- first pass (rep=0 -> 1): interval must be 1.0 regardless of ef ---
# inputs: grade=2, interval=0.0, rep=0; vary ef across legal range

for test_easiness_factor in [1.3, 2.5, 3.0]:
    first_pass_result: ReviewResult = sm2_update(2, test_easiness_factor, 0.0, 0, 0, start_date)
    if first_pass_result["interval_days"] != 1.0:
        print(f"FAIL [first pass interval ef={test_easiness_factor}]: expected 1.0 got {first_pass_result['interval_days']}")
        failure_count += 1

# --- second pass (rep=1 -> 2): interval must be 6.0 regardless of ef ---
# inputs: grade=2, interval=1.0, rep=1; vary ef across legal range

for test_easiness_factor in [1.3, 2.5, 3.0]:
    second_pass_result: ReviewResult = sm2_update(2, test_easiness_factor, 1.0, 1, 0, start_date)
    if second_pass_result["interval_days"] != 6.0:
        print(f"FAIL [second pass interval ef={test_easiness_factor}]: expected 6.0 got {second_pass_result['interval_days']}")
        failure_count += 1

# --- third pass (rep=2 -> 3): interval = previous_interval * new_ef ---
# inputs: grade=2, ef=2.5, interval=6.0, rep=2
# new_ef = 2.6, expected interval = 6.0 * 2.6 = 15.6

third_pass_result: ReviewResult = sm2_update(2, 2.5, 6.0, 2, 0, start_date)
expected_third_interval: float = 6.0 * 2.6

if abs(third_pass_result["interval_days"] - expected_third_interval) > FLOAT_TOLERANCE:
    print(f"FAIL [third pass interval]: expected {expected_third_interval} got {third_pass_result['interval_days']}")
    failure_count += 1

# =============================================================================
# SEQUENCE: GRADE-2 PROGRESSION (10 STEPS)
# =============================================================================
# interval must be non-decreasing each step; ef must reach 3.0 by end

current_easiness_factor = 2.5
current_interval_days = 0.0
current_repetition_count = 0
current_lapse_count = 0
current_date = start_date
previous_interval: float = 0.0

for step_index in range(10):
    grade2_seq_result: ReviewResult = sm2_update(
        2,
        current_easiness_factor,
        current_interval_days,
        current_repetition_count,
        current_lapse_count,
        current_date,
    )
    new_interval: float = grade2_seq_result["interval_days"]

    if new_interval < previous_interval - FLOAT_TOLERANCE:
        print(f"FAIL [grade2 seq step {step_index}]: interval decreased {previous_interval} -> {new_interval}")
        failure_count += 1

    previous_interval = new_interval
    current_easiness_factor = grade2_seq_result["easiness_factor"]
    current_interval_days = grade2_seq_result["interval_days"]
    current_repetition_count = grade2_seq_result["repetition_count"]
    current_lapse_count = grade2_seq_result["lapse_count"]
    current_date = grade2_seq_result["due_date"]

if abs(current_easiness_factor - 3.0) > FLOAT_TOLERANCE:
    print(f"FAIL [grade2 seq final ef]: expected 3.0 got {current_easiness_factor}")
    failure_count += 1

# =============================================================================
# SEQUENCE: GRADE-0 PROGRESSION (10 STEPS)
# =============================================================================
# rep stays 0, lapse increments each step, interval stays 1.0, ef floors at 1.3

current_easiness_factor = 2.5
current_interval_days = 0.0
current_repetition_count = 0
current_lapse_count = 0
current_date = start_date

for step_index in range(10):
    grade0_seq_result: ReviewResult = sm2_update(
        0,
        current_easiness_factor,
        current_interval_days,
        current_repetition_count,
        current_lapse_count,
        current_date,
    )

    if grade0_seq_result["repetition_count"] != 0:
        print(f"FAIL [grade0 seq step {step_index} rep]: expected 0 got {grade0_seq_result['repetition_count']}")
        failure_count += 1

    if grade0_seq_result["lapse_count"] != step_index + 1:
        print(f"FAIL [grade0 seq step {step_index} lapse]: expected {step_index + 1} got {grade0_seq_result['lapse_count']}")
        failure_count += 1

    if grade0_seq_result["interval_days"] != 1.0:
        print(f"FAIL [grade0 seq step {step_index} interval]: expected 1.0 got {grade0_seq_result['interval_days']}")
        failure_count += 1

    if grade0_seq_result["easiness_factor"] < 1.3 - FLOAT_TOLERANCE:
        print(f"FAIL [grade0 seq step {step_index} ef floor]: {grade0_seq_result['easiness_factor']} < 1.3")
        failure_count += 1

    current_easiness_factor = grade0_seq_result["easiness_factor"]
    current_interval_days = grade0_seq_result["interval_days"]
    current_repetition_count = grade0_seq_result["repetition_count"]
    current_lapse_count = grade0_seq_result["lapse_count"]
    current_date = grade0_seq_result["due_date"]

if abs(current_easiness_factor - 1.3) > FLOAT_TOLERANCE:
    print(f"FAIL [grade0 seq final ef]: expected 1.3 got {current_easiness_factor}")
    failure_count += 1

# =============================================================================
# SEQUENCE: RECOVERY PATH (3 FAILS THEN 3 PASSES)
# =============================================================================
# after 3 grade-0: ef=1.3, rep=0, lapse=3
# pass 1 (grade=1): interval=1.0, rep=1
# pass 2 (grade=1): interval=6.0, rep=2
# pass 3 (grade=1): interval=6.0*1.3=7.8, rep=3
# note: grade-1 from ef=1.3 yields new_ef=1.16, clamped to 1.3 throughout

current_easiness_factor = 2.5
current_interval_days = 0.0
current_repetition_count = 0
current_lapse_count = 0
current_date = start_date

for step_index in range(3):
    recovery_fail_result: ReviewResult = sm2_update(
        0,
        current_easiness_factor,
        current_interval_days,
        current_repetition_count,
        current_lapse_count,
        current_date,
    )
    current_easiness_factor = recovery_fail_result["easiness_factor"]
    current_interval_days = recovery_fail_result["interval_days"]
    current_repetition_count = recovery_fail_result["repetition_count"]
    current_lapse_count = recovery_fail_result["lapse_count"]
    current_date = recovery_fail_result["due_date"]

if current_repetition_count != 0:
    print(f"FAIL [recovery post-fail rep]: expected 0 got {current_repetition_count}")
    failure_count += 1

if current_lapse_count != 3:
    print(f"FAIL [recovery post-fail lapse]: expected 3 got {current_lapse_count}")
    failure_count += 1

if abs(current_easiness_factor - 1.3) > FLOAT_TOLERANCE:
    print(f"FAIL [recovery post-fail ef]: expected 1.3 got {current_easiness_factor}")
    failure_count += 1

# pass 1: rep 0 -> 1, interval must be 1.0

recovery_pass1_result: ReviewResult = sm2_update(
    1,
    current_easiness_factor,
    current_interval_days,
    current_repetition_count,
    current_lapse_count,
    current_date,
)

if recovery_pass1_result["interval_days"] != 1.0:
    print(f"FAIL [recovery pass1 interval]: expected 1.0 got {recovery_pass1_result['interval_days']}")
    failure_count += 1

if recovery_pass1_result["repetition_count"] != 1:
    print(f"FAIL [recovery pass1 rep]: expected 1 got {recovery_pass1_result['repetition_count']}")
    failure_count += 1

current_easiness_factor = recovery_pass1_result["easiness_factor"]
current_interval_days = recovery_pass1_result["interval_days"]
current_repetition_count = recovery_pass1_result["repetition_count"]
current_lapse_count = recovery_pass1_result["lapse_count"]
current_date = recovery_pass1_result["due_date"]

# pass 2: rep 1 -> 2, interval must be 6.0

recovery_pass2_result: ReviewResult = sm2_update(
    1,
    current_easiness_factor,
    current_interval_days,
    current_repetition_count,
    current_lapse_count,
    current_date,
)

if recovery_pass2_result["interval_days"] != 6.0:
    print(f"FAIL [recovery pass2 interval]: expected 6.0 got {recovery_pass2_result['interval_days']}")
    failure_count += 1

if recovery_pass2_result["repetition_count"] != 2:
    print(f"FAIL [recovery pass2 rep]: expected 2 got {recovery_pass2_result['repetition_count']}")
    failure_count += 1

current_easiness_factor = recovery_pass2_result["easiness_factor"]
current_interval_days = recovery_pass2_result["interval_days"]
current_repetition_count = recovery_pass2_result["repetition_count"]
current_lapse_count = recovery_pass2_result["lapse_count"]
current_date = recovery_pass2_result["due_date"]

# pass 3: rep 2 -> 3, interval = 6.0 * 1.3 = 7.8
# ef=1.3, grade=1 -> new_ef = max(1.3, 1.3 - 0.14) = 1.3 (floor holds)

recovery_pass3_result: ReviewResult = sm2_update(
    1,
    current_easiness_factor,
    current_interval_days,
    current_repetition_count,
    current_lapse_count,
    current_date,
)

expected_pass3_interval: float = 6.0 * 1.3

if abs(recovery_pass3_result["interval_days"] - expected_pass3_interval) > FLOAT_TOLERANCE:
    print(f"FAIL [recovery pass3 interval]: expected {expected_pass3_interval} got {recovery_pass3_result['interval_days']}")
    failure_count += 1

if recovery_pass3_result["repetition_count"] != 3:
    print(f"FAIL [recovery pass3 rep]: expected 3 got {recovery_pass3_result['repetition_count']}")
    failure_count += 1

# =============================================================================
# RESULT
# =============================================================================

if failure_count > 0:
    print(f"{failure_count} assertion(s) failed")
    sys.exit(1)

print("all assertions passed")
