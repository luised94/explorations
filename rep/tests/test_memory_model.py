"""The transplanted FSRS-6 model against its source, py-fsrs 6.3.2 (PLAN.md D7, I5).

The oracle is configured as a pure memory model: no learning steps, no
relearning steps, no fuzz. Measured before M1: in that configuration every
review stays in State.Review with whole-day intervals. Equality is exact,
not approximate: the transplant performs the same floating-point operations
in the same order, and any drift means the transplant is wrong.
"""

from datetime import UTC, datetime, timedelta
from unittest import mock

import fsrs
import fsrs.scheduler
from hypothesis import given
from hypothesis import strategies as strategy

from rep.memory_model import (
    DEFAULT_DESIRED_RETENTION,
    DEFAULT_MAXIMUM_INTERVAL_DAYS,
    DEFAULT_PARAMETERS,
    DIFFICULTY_MAXIMUM,
    DIFFICULTY_MINIMUM,
    STABILITY_MINIMUM,
    MemoryState,
    first_review,
    fuzzed_interval_days,
    next_interval_days,
    next_review,
)

SECONDS_PER_DAY = 86400

# Gaps between reviews, in seconds. Mixed so the three regimes all appear
# often: same day (short-term formula), the one-day boundary where
# timedelta.days flips from 0 to 1, and long gaps up to 400 days.
review_gap_seconds = strategy.one_of(
    strategy.integers(min_value=0, max_value=SECONDS_PER_DAY - 1),
    strategy.integers(min_value=SECONDS_PER_DAY - 3, max_value=SECONDS_PER_DAY + 3),
    strategy.integers(min_value=0, max_value=400 * SECONDS_PER_DAY),
)
review_histories = strategy.lists(
    strategy.tuples(review_gap_seconds, strategy.integers(min_value=1, max_value=4)),
    min_size=1,
    max_size=25,
)


@given(review_histories)
def test_transplant_matches_oracle_at_every_step(history: list[tuple[int, int]]) -> None:
    oracle_scheduler = fsrs.Scheduler(
        parameters=DEFAULT_PARAMETERS,
        desired_retention=DEFAULT_DESIRED_RETENTION,
        learning_steps=(),
        relearning_steps=(),
        maximum_interval=DEFAULT_MAXIMUM_INTERVAL_DAYS,
        enable_fuzzing=False,
    )
    oracle_card = fsrs.Card(card_id=1)
    reviewed_at = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)
    previous_reviewed_at: datetime | None = None
    transplant_memory: MemoryState | None = None

    for gap_seconds, rating in history:
        reviewed_at = reviewed_at + timedelta(seconds=gap_seconds)
        oracle_card, _review_log = oracle_scheduler.review_card(
            oracle_card, fsrs.Rating(rating), review_datetime=reviewed_at
        )
        if transplant_memory is None or previous_reviewed_at is None:
            transplant_memory = first_review(rating, DEFAULT_PARAMETERS)
        else:
            elapsed_whole_days = (reviewed_at - previous_reviewed_at).days
            transplant_memory = next_review(
                transplant_memory, rating, elapsed_whole_days, DEFAULT_PARAMETERS
            )
        transplant_interval = next_interval_days(
            transplant_memory["stability"],
            DEFAULT_DESIRED_RETENTION,
            DEFAULT_MAXIMUM_INTERVAL_DAYS,
            DEFAULT_PARAMETERS,
        )
        previous_reviewed_at = reviewed_at

        assert oracle_card.state == fsrs.State.Review
        assert transplant_memory["stability"] == oracle_card.stability
        assert transplant_memory["difficulty"] == oracle_card.difficulty
        assert timedelta(days=transplant_interval) == oracle_card.due - reviewed_at
        # MM1, MM2, MM3 on every step, not only where the oracle agrees.
        assert transplant_memory["stability"] >= STABILITY_MINIMUM
        assert DIFFICULTY_MINIMUM <= transplant_memory["difficulty"] <= DIFFICULTY_MAXIMUM
        assert 1 <= transplant_interval <= DEFAULT_MAXIMUM_INTERVAL_DAYS


@given(
    strategy.integers(min_value=1, max_value=DEFAULT_MAXIMUM_INTERVAL_DAYS),
    strategy.floats(min_value=0.0, max_value=1.0, exclude_max=True),
)
def test_fuzz_matches_oracle_for_the_same_random_fraction(
    interval_days: int, random_fraction: float
) -> None:
    # py-fsrs draws its fraction from random(); replacing random() with a
    # function returning our fraction makes the two directly comparable.
    oracle_scheduler = fsrs.Scheduler(enable_fuzzing=True)
    with mock.patch.object(fsrs.scheduler, "random", return_value=random_fraction):
        oracle_interval = oracle_scheduler._get_fuzzed_interval(  # pyright: ignore[reportPrivateUsage]
            interval=timedelta(days=interval_days)
        )
    assert timedelta(
        days=fuzzed_interval_days(interval_days, random_fraction, DEFAULT_MAXIMUM_INTERVAL_DAYS)
    ) == oracle_interval


def test_same_day_success_never_lowers_stability() -> None:
    # A concrete case from the pre-M1 measurement: Again, then Good 15 minutes
    # later, raised stability from 0.7751 to 0.8282 instead of lowering it.
    memory_after_good = first_review(3, DEFAULT_PARAMETERS)
    memory_after_again = next_review(memory_after_good, 1, 0, DEFAULT_PARAMETERS)
    memory_after_same_day_good = next_review(memory_after_again, 3, 0, DEFAULT_PARAMETERS)
    assert round(memory_after_again["stability"], 4) == 0.7751
    assert round(memory_after_same_day_good["stability"], 4) == 0.8282
