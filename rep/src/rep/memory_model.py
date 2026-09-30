"""FSRS-6 memory model: how one review changes what you remember.

Transplanted from py-fsrs 6.3.2 (fsrs/scheduler.py), MIT License,
Copyright (c) 2022 Open Spaced Repetition. Only the memory math and the
interval and fuzz rules are taken; py-fsrs's learning-step state machine is
not, because rep's sessions handle same-day relearning themselves
(PLAN.md D7). tests/test_memory_model.py holds this file to py-fsrs 6.3.2,
configured with no learning steps, no relearning steps and no fuzz, on random
review histories. An FSRS upgrade means re-transplanting and re-running that
test; never edit a formula here without it.

REPRESENTATION
  Rating             int: AGAIN 1, HARD 2, GOOD 3, EASY 4 (py-fsrs Rating values)
  MemoryState        {stability, difficulty}
    stability        days until recall probability falls to 90%; >= STABILITY_MINIMUM
    difficulty       in [DIFFICULTY_MINIMUM, DIFFICULTY_MAXIMUM]
  parameters         21 floats, FSRS-6 order; parameters[index] is w_index in
                     the FSRS literature. DEFAULT_PARAMETERS until the
                     optimizer has enough history.
  elapsed_whole_days int >= 0: whole days between two reviews, floored the way
                     py-fsrs floors them (timedelta.days). 0 means same day and
                     selects the short-term stability formula.

INVARIANTS
  MM1  Every returned stability is >= STABILITY_MINIMUM.
  MM2  Every returned difficulty is within [DIFFICULTY_MINIMUM, DIFFICULTY_MAXIMUM].
  MM3  Every returned interval is a whole number of days in [1, maximum_interval_days].
  MM4  Every function here is pure: same inputs, same output, no clock, no
       randomness (fuzz takes its random fraction as an argument).
"""

import math
from typing import TypedDict

AGAIN = 1
HARD = 2
GOOD = 3
EASY = 4

DEFAULT_PARAMETERS: tuple[float, ...] = (
    0.212, 1.2931, 2.3065, 8.2956, 6.4133, 0.8334, 3.0194, 0.001, 1.8722,
    0.1666, 0.796, 1.4835, 0.0614, 0.2629, 1.6483, 0.6014, 1.8729, 0.5425,
    0.0912, 0.0658, 0.1542,
)  # fmt: skip
PARAMETER_COUNT = 21
STABILITY_MINIMUM = 0.001
DIFFICULTY_MINIMUM = 1.0
DIFFICULTY_MAXIMUM = 10.0
DEFAULT_DESIRED_RETENTION = 0.9
DEFAULT_MAXIMUM_INTERVAL_DAYS = 36500

# Fuzz spreads reviews created on the same day so they do not all come due on
# the same later day. Each band adds factor * (days of the interval inside the
# band) to the half-width of the fuzz window. Copied from py-fsrs FUZZ_RANGES.
FUZZ_BANDS: tuple[tuple[float, float, float], ...] = (
    # (band start in days, band end in days, factor)
    (2.5, 7.0, 0.15),
    (7.0, 20.0, 0.1),
    (20.0, math.inf, 0.05),
)


class MemoryState(TypedDict):
    stability: float
    difficulty: float


def first_review(rating: int, parameters: tuple[float, ...]) -> MemoryState:
    """Memory state after the first graded review of an item.

    PRE   rating in AGAIN..EASY; len(parameters) == PARAMETER_COUNT.
    POST  MM1, MM2.
    """
    assert AGAIN <= rating <= EASY, f"rating {rating} out of range"
    assert len(parameters) == PARAMETER_COUNT, "FSRS-6 needs 21 parameters"
    # w0..w3 are the initial stabilities for Again, Hard, Good, Easy.
    initial_stability = max(parameters[rating - 1], STABILITY_MINIMUM)
    initial_difficulty = parameters[4] - (math.e ** (parameters[5] * (rating - 1))) + 1
    initial_difficulty = min(max(initial_difficulty, DIFFICULTY_MINIMUM), DIFFICULTY_MAXIMUM)
    return {"stability": initial_stability, "difficulty": initial_difficulty}


def retrievability(
    stability: float, elapsed_whole_days: int, parameters: tuple[float, ...]
) -> float:
    """Probability of recall after elapsed_whole_days, by the FSRS-6 power curve.

    PRE   stability >= STABILITY_MINIMUM; elapsed_whole_days >= 0.
    POST  result in (0, 1]; exactly 1 when elapsed_whole_days == 0.
    """
    assert stability >= STABILITY_MINIMUM, "stability below minimum"
    assert elapsed_whole_days >= 0, "elapsed days must not be negative"
    # w20 is the decay. The factor is chosen so that retrievability is exactly
    # 0.9 when elapsed time equals stability, which is what stability means.
    decay = -parameters[20]
    factor = 0.9 ** (1 / decay) - 1
    return (1 + factor * elapsed_whole_days / stability) ** decay


def next_review(
    memory_state: MemoryState,
    rating: int,
    elapsed_whole_days: int,
    parameters: tuple[float, ...],
) -> MemoryState:
    """Memory state after a graded review of an item already reviewed before.

    PRE   memory_state satisfies MM1 and MM2; rating in AGAIN..EASY;
          elapsed_whole_days >= 0; len(parameters) == PARAMETER_COUNT.
    POST  MM1, MM2.
    """
    assert AGAIN <= rating <= EASY, f"rating {rating} out of range"
    assert elapsed_whole_days >= 0, "elapsed days must not be negative"
    assert len(parameters) == PARAMETER_COUNT, "FSRS-6 needs 21 parameters"
    stability = memory_state["stability"]
    difficulty = memory_state["difficulty"]

    if elapsed_whole_days < 1:
        # Same-day review (FSRS-6 short-term memory, w17..w19). A successful
        # same-day review may not lower stability, hence the floor of 1.0 on
        # the multiplier for Hard, Good and Easy.
        short_term_multiplier = (math.e ** (parameters[17] * (rating - 3 + parameters[18]))) * (
            stability ** -parameters[19]
        )
        if rating in (HARD, GOOD, EASY):
            short_term_multiplier = max(short_term_multiplier, 1.0)
        next_stability = max(stability * short_term_multiplier, STABILITY_MINIMUM)
    else:
        recall_probability = retrievability(stability, elapsed_whole_days, parameters)
        if rating == AGAIN:
            # Forgetting: stability after a lapse (w11..w14), capped by the
            # short-term bound so a lapse can never raise stability much.
            long_term_forget_stability = (
                parameters[11]
                * (difficulty ** -parameters[12])
                * (((stability + 1) ** (parameters[13])) - 1)
                * (math.e ** ((1 - recall_probability) * parameters[14]))
            )
            short_term_forget_stability = stability / (math.e ** (parameters[17] * parameters[18]))
            next_stability = min(long_term_forget_stability, short_term_forget_stability)
        else:
            # Successful recall (w8..w10), with the Hard penalty (w15) and the
            # Easy bonus (w16). Lower recall probability at review time means a
            # larger gain: the desirable-difficulty effect, in the model.
            hard_penalty = parameters[15] if rating == HARD else 1
            easy_bonus = parameters[16] if rating == EASY else 1
            next_stability = stability * (
                1
                + (math.e ** (parameters[8]))
                * (11 - difficulty)
                * (stability ** -parameters[9])
                * ((math.e ** ((1 - recall_probability) * parameters[10])) - 1)
                * hard_penalty
                * easy_bonus
            )
        next_stability = max(next_stability, STABILITY_MINIMUM)

    # Difficulty update, applied on every review including same-day ones, as
    # py-fsrs does in its Review state: a linear step by rating (w6), damped as
    # difficulty approaches 10, then mean reversion (w7) toward the unclamped
    # initial difficulty of an Easy first review.
    difficulty_step = -(parameters[6] * (rating - 3))
    damped_difficulty = difficulty + (10.0 - difficulty) * difficulty_step / 9.0
    easy_initial_difficulty = parameters[4] - (math.e ** (parameters[5] * (EASY - 1))) + 1
    next_difficulty = parameters[7] * easy_initial_difficulty + (1 - parameters[7]) * damped_difficulty
    next_difficulty = min(max(next_difficulty, DIFFICULTY_MINIMUM), DIFFICULTY_MAXIMUM)

    return {"stability": next_stability, "difficulty": next_difficulty}


def next_interval_days(
    stability: float,
    desired_retention: float,
    maximum_interval_days: int,
    parameters: tuple[float, ...],
) -> int:
    """Days until recall probability is expected to fall to desired_retention.

    PRE   stability >= STABILITY_MINIMUM; 0 < desired_retention < 1;
          maximum_interval_days >= 1.
    POST  MM3.
    """
    assert 0 < desired_retention < 1, "desired retention must be inside (0, 1)"
    assert maximum_interval_days >= 1, "maximum interval must be at least one day"
    decay = -parameters[20]
    factor = 0.9 ** (1 / decay) - 1
    interval = (stability / factor) * ((desired_retention ** (1 / decay)) - 1)
    # round() is Python's round-half-to-even, as in py-fsrs; kept on purpose so
    # the two agree on every tie.
    return min(max(round(interval), 1), maximum_interval_days)


def fuzzed_interval_days(
    interval_days: int, random_fraction: float, maximum_interval_days: int
) -> int:
    """The interval moved to a point inside its fuzz window.

    The caller supplies random_fraction, derived deterministically from the
    item and its review count, so replaying history reproduces every due date
    (PLAN.md D7, invariant I4). py-fsrs calls random() at this point instead.

    PRE   interval_days >= 1; 0 <= random_fraction < 1; maximum_interval_days >= 1.
    POST  MM3; intervals under 2.5 days are returned unchanged.
    """
    assert interval_days >= 1, "interval must be at least one day"
    assert 0 <= random_fraction < 1, "random fraction must be in [0, 1)"
    if interval_days < 2.5:
        return interval_days
    half_width = 1.0
    for band_start, band_end, band_factor in FUZZ_BANDS:
        half_width += band_factor * max(min(float(interval_days), band_end) - band_start, 0.0)
    minimum_days = max(2, round(interval_days - half_width))
    maximum_days = min(round(interval_days + half_width), maximum_interval_days)
    minimum_days = min(minimum_days, maximum_days)
    fuzzed_days = random_fraction * (maximum_days - minimum_days + 1) + minimum_days
    return min(round(fuzzed_days), maximum_interval_days)
