"""Selection + throttle spike.

Proves, with a seeded RNG:
  1. Cold start: with no response stats at all, the weighted policy's
     pick distribution is statistically uniform -- it degrades to the
     current random policy instead of starving or looping.
  2. Signal: a question missed often is picked more, proportional to its
     Laplace-smoothed miss rate.
  3. The history window still softly prevents immediate repeats, exactly
     like pick_next_question.
  4. Throttle: per-bank minimum floor and daily cap both hold, and a day
     with the budget already spent admits nothing.
"""

import random

from scheduler_port import (
    apply_new_question_throttle,
    miss_rate_weight,
    select_weighted_by_miss_rate,
)

failure_count = 0


def check(name, condition):
    global failure_count
    print(("PASS  " if condition else "FAIL  ") + name)
    if not condition:
        failure_count += 1


candidates = [{"id": question_id, "bank_id": 1} for question_id in range(1, 11)]
seeded_random = random.Random(20260703)

cold_pick_counts = {question_id: 0 for question_id in range(1, 11)}
for _ in range(20000):
    chosen = select_weighted_by_miss_rate(
        candidates, {}, None, seeded_random.random())
    cold_pick_counts[chosen["id"]] += 1
expected_per_question = 20000 / 10
worst_deviation = max(
    abs(count - expected_per_question) for count in cold_pick_counts.values())
check("cold start is uniform (worst deviation %.1f%% of expected)"
      % (100.0 * worst_deviation / expected_per_question),
      worst_deviation < expected_per_question * 0.10)

response_stats = {
    question_id: {"attempt_count": 10, "correct_count": 10}
    for question_id in range(1, 11)
}
response_stats[7] = {"attempt_count": 10, "correct_count": 2}
weighted_pick_counts = {question_id: 0 for question_id in range(1, 11)}
for _ in range(20000):
    chosen = select_weighted_by_miss_rate(
        candidates, response_stats, None, seeded_random.random())
    weighted_pick_counts[chosen["id"]] += 1
mastered_weight = miss_rate_weight(10, 10)
struggling_weight = miss_rate_weight(10, 2)
expected_ratio = struggling_weight / mastered_weight
observed_ratio = weighted_pick_counts[7] / (
    sum(weighted_pick_counts.values()) - weighted_pick_counts[7]) * 9.0
check("missed question favored ~%.1fx (observed %.1fx)"
      % (expected_ratio, observed_ratio),
      abs(observed_ratio - expected_ratio) / expected_ratio < 0.15)

history = [1, 2, 3, 4, 5, 6, 7, 8, 9]
only_fresh_picked = True
for _ in range(2000):
    chosen = select_weighted_by_miss_rate(
        candidates, response_stats, history, seeded_random.random())
    if chosen["id"] != 10:
        only_fresh_picked = False
check("history window excludes recent ids when a fresh candidate exists",
      only_fresh_picked)

everything_recent = list(range(1, 11))
fallback = select_weighted_by_miss_rate(
    candidates, response_stats, everything_recent, seeded_random.random())
check("all-recent falls back to the full pool (never returns nothing)",
      fallback is not None)

new_candidates = (
    [{"id": 100 + index, "bank_id": 1} for index in range(6)]
    + [{"id": 200, "bank_id": 2}]
    + [{"id": 300, "bank_id": 3}]
)
admitted = apply_new_question_throttle(
    new_candidates, {}, per_day_maximum=4, per_bank_minimum=1)
admitted_banks = {candidate["bank_id"] for candidate in admitted}
check("floor pass guarantees each bank a slot before fill (banks %s)"
      % sorted(admitted_banks),
      len(admitted) == 4 and admitted_banks == {1, 2, 3})

nothing = apply_new_question_throttle(
    new_candidates, {1: 3, 2: 1}, per_day_maximum=4, per_bank_minimum=1)
check("spent budget admits nothing", nothing == [])

partial = apply_new_question_throttle(
    new_candidates, {1: 2}, per_day_maximum=4, per_bank_minimum=1)
check("partial budget admits exactly the remainder", len(partial) == 2)

print("\n%d failure(s)" % failure_count)
raise SystemExit(1 if failure_count else 0)
