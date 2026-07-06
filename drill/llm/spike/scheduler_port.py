"""Spike: the complete pure scheduling core as it would land in drill/logic.py.

Style contract: flat procedural code, pure functions, plain dicts and lists,
full descriptive names, no classes, no nested functions, no clock and no IO
anywhere in this module. Effects (clock, database) belong to HTTP/MAIN.

Schedule state dict shape (mirrors the question_schedule table row):
    {"question_id": int, "easiness_factor": float, "interval_days": float,
     "repetition_count": int, "due_date": int, "last_review": int,
     "lapse_count": int}
Dates are ordinal-day integers (datetime.date.toordinal), computed once per
request at the HTTP boundary and passed down.
"""

EASINESS_FACTOR_MINIMUM = 1.3
EASINESS_FACTOR_MAXIMUM = 3.0
EASINESS_FACTOR_INITIAL = 2.5
RECALL_QUALITY_TO_SM2_GRADE = {0: 1, 1: 3, 2: 5}
INTERVAL_FUZZ_FRACTION = 0.05
NEW_QUESTIONS_PER_DAY_MAXIMUM = 9
NEW_QUESTIONS_PER_BANK_MINIMUM = 1
REVIEWS_PER_SESSION_MAXIMUM = 100


def derive_recall_quality(correct: bool, elapsed_ms: int | None) -> int:
    """Map a drill grading outcome to an SM-2 recall quality 0|1|2.

    Version 1 policy: binary. Wrong -> 0, correct -> 2. elapsed_ms is
    accepted but deliberately unused so the timing-derived policy can swap
    in behind the same signature once per-qtype baselines exist. The
    middle grade (1, "correct with effort") is unreachable until then;
    the cost is that easiness never decays on effortful passes, bounded
    by the lapse path resetting interval to one day.
    """
    if correct:
        return 2
    return 0


def advance_schedule_state(
    recall_quality: int,
    easiness_factor: float,
    interval_days: float,
    repetition_count: int,
    lapse_count: int,
    review_date: int,
) -> dict:
    """Advance one question's schedule after a graded review. Pure SM-2.

    Port of sm2.sm2_update with drill naming; the arithmetic is identical
    and pinned by the equivalence spike against the original. review_date
    is an ordinal day supplied by the caller.
    """
    sm2_grade = RECALL_QUALITY_TO_SM2_GRADE[recall_quality]
    easiness_delta_inner = 0.08 + (5 - sm2_grade) * 0.02
    easiness_delta = 0.1 - (5 - sm2_grade) * easiness_delta_inner
    new_easiness_factor = easiness_factor + easiness_delta
    if new_easiness_factor < EASINESS_FACTOR_MINIMUM:
        new_easiness_factor = EASINESS_FACTOR_MINIMUM
    if new_easiness_factor > EASINESS_FACTOR_MAXIMUM:
        new_easiness_factor = EASINESS_FACTOR_MAXIMUM

    if sm2_grade < 3:
        new_repetition_count = 0
        new_interval_days = 1.0
        new_lapse_count = lapse_count + 1
    else:
        new_repetition_count = repetition_count + 1
        new_lapse_count = lapse_count
        if new_repetition_count == 1:
            new_interval_days = 1.0
        elif new_repetition_count == 2:
            new_interval_days = 6.0
        else:
            new_interval_days = interval_days * new_easiness_factor

    return {
        "easiness_factor": new_easiness_factor,
        "interval_days": new_interval_days,
        "repetition_count": new_repetition_count,
        "lapse_count": new_lapse_count,
        "due_date": review_date + int(round(new_interval_days)),
        "last_review": review_date,
    }


def apply_interval_fuzz(interval_days: float, question_id: int) -> float:
    """Spread intervals by a deterministic per-question jitter of at most
    +-INTERVAL_FUZZ_FRACTION, so questions learned together do not stay
    due together forever. Deterministic (keyed on question_id, no RNG) so
    replaying the response log reproduces the stored schedule exactly.
    Intervals of two days or less are exempt: fuzzing there can only
    round to the same day or distort the fixed 1 -> 6 opening steps.
    """
    if interval_days <= 2.0:
        return interval_days
    jitter_step = (question_id * 2654435761) % 1024
    jitter_fraction = (jitter_step / 1023.0) * 2.0 - 1.0
    return interval_days * (1.0 + INTERVAL_FUZZ_FRACTION * jitter_fraction)


def schedule_update_allowed_today(schedule_state: dict | None, today: int) -> bool:
    """One schedule update per question per day: only the first graded
    attempt schedules; later same-day attempts log a response but must
    not advance the interval again off one day of memory. A question
    with no schedule row (never reviewed) is always allowed.
    """
    if schedule_state is None:
        return True
    return schedule_state["last_review"] != today


def relative_overdueness(schedule_state: dict, today: int) -> float:
    """Sort key for spending a capped review budget on a backlog: days
    overdue divided by interval. A short-interval question three days
    late is at greater recall risk than a long-interval one five days
    late. Larger means more at risk; not-yet-due yields <= 0.
    """
    interval_days = schedule_state["interval_days"]
    if interval_days < 1.0:
        interval_days = 1.0
    return (today - schedule_state["due_date"]) / interval_days


def partition_candidates_by_schedule(
    candidates: list[dict],
    schedule_by_question_id: dict[int, dict],
    today: int,
) -> tuple[list[dict], list[dict], list[dict]]:
    """Split bank candidates into (due, new, not_due) for review mode.

    due: has a schedule row and due_date <= today, ordered most at risk
    first (relative overdueness, descending). new: no schedule row yet,
    in id order (authoring order). not_due: scheduled for the future.
    """
    due: list[dict] = []
    new: list[dict] = []
    not_due: list[dict] = []
    for candidate in candidates:
        schedule_state = schedule_by_question_id.get(candidate["id"])
        if schedule_state is None:
            new.append(candidate)
        elif schedule_state["due_date"] <= today:
            due.append(candidate)
        else:
            not_due.append(candidate)
    due.sort(
        key=lambda candidate: relative_overdueness(
            schedule_by_question_id[candidate["id"]], today
        ),
        reverse=True,
    )
    new.sort(key=lambda candidate: candidate["id"])
    return due, new, not_due


def apply_new_question_throttle(
    new_candidates: list[dict],
    new_introduced_today_by_bank: dict[int, int],
    per_day_maximum: int,
    per_bank_minimum: int,
) -> list[dict]:
    """Budget how many never-reviewed questions enter the schedule today.

    Port of sm2's apply_throttle_and_cap floor/cap idea with the string
    domain prefix replaced by the real bank_id column. Two passes: first
    guarantee per_bank_minimum slots per bank that still has headroom
    today, then fill remaining budget in candidate order.
    """
    total_introduced_today = sum(new_introduced_today_by_bank.values())
    budget = per_day_maximum - total_introduced_today
    if budget <= 0:
        return []

    admitted: list[dict] = []
    admitted_ids: set[int] = set()
    admitted_count_by_bank: dict[int, int] = {}

    for candidate in new_candidates:
        if len(admitted) >= budget:
            break
        bank_id = candidate["bank_id"]
        already_today = new_introduced_today_by_bank.get(bank_id, 0)
        admitted_so_far = admitted_count_by_bank.get(bank_id, 0)
        if already_today + admitted_so_far >= per_bank_minimum:
            continue
        admitted.append(candidate)
        admitted_ids.add(candidate["id"])
        admitted_count_by_bank[bank_id] = admitted_so_far + 1

    for candidate in new_candidates:
        if len(admitted) >= budget:
            break
        if candidate["id"] in admitted_ids:
            continue
        admitted.append(candidate)
        admitted_ids.add(candidate["id"])

    return admitted


def miss_rate_weight(attempt_count: int, correct_count: int) -> float:
    """Laplace-smoothed miss rate: (misses + 1) / (attempts + 2).

    A never-attempted question weighs 0.5, so a cold bank is uniform and
    the weighted policy degrades to the current random policy instead of
    starving or looping.
    """
    miss_count = attempt_count - correct_count
    return (miss_count + 1.0) / (attempt_count + 2.0)


def select_weighted_by_miss_rate(
    candidates: list[dict],
    response_stats_by_question_id: dict[int, dict],
    history: list[int] | None,
    random_value: float,
) -> dict | None:
    """Adaptive selection (roadmap #7, schema-free): weight candidates by
    smoothed miss rate, softly avoiding the recent-history window exactly
    as pick_next_question does. random_value is a uniform [0, 1) sample
    supplied by the caller so the function stays deterministic in tests.
    """
    if not candidates:
        return None
    recent_question_ids = set(history or [])
    fresh = [c for c in candidates if c.get("id") not in recent_question_ids]
    pool = fresh if fresh else candidates

    weights: list[float] = []
    for candidate in pool:
        stats = response_stats_by_question_id.get(candidate["id"])
        if stats is None:
            weights.append(miss_rate_weight(0, 0))
        else:
            weights.append(
                miss_rate_weight(stats["attempt_count"], stats["correct_count"])
            )

    total_weight = sum(weights)
    threshold = random_value * total_weight
    cumulative = 0.0
    for candidate, weight in zip(pool, weights):
        cumulative += weight
        if cumulative > threshold:
            return candidate
    return pool[-1]


def rebuild_schedule_from_response_log(
    response_rows: list[dict],
) -> dict[int, dict]:
    """Fold the responses log into schedule state: state is a cache of the
    log. Each row needs question_id, correct, elapsed_ms, answered_ordinal.
    Applies the same once-per-day rule and fuzz the live path applies, so
    rebuild == stored holds while the quality policy is unchanged. This is
    the backfill for the migration, the corruption-recovery path, and the
    invariant check in one function.
    """
    schedule_by_question_id: dict[int, dict] = {}
    for row in response_rows:
        question_id = row["question_id"]
        if question_id is None:
            continue
        review_date = row["answered_ordinal"]
        existing = schedule_by_question_id.get(question_id)
        if not schedule_update_allowed_today(existing, review_date):
            continue
        if existing is None:
            easiness_factor = EASINESS_FACTOR_INITIAL
            interval_days = 0.0
            repetition_count = 0
            lapse_count = 0
        else:
            easiness_factor = existing["easiness_factor"]
            interval_days = existing["interval_days"]
            repetition_count = existing["repetition_count"]
            lapse_count = existing["lapse_count"]
        recall_quality = derive_recall_quality(row["correct"], row["elapsed_ms"])
        advanced = advance_schedule_state(
            recall_quality,
            easiness_factor,
            interval_days,
            repetition_count,
            lapse_count,
            review_date,
        )
        fuzzed_interval = apply_interval_fuzz(advanced["interval_days"], question_id)
        advanced["interval_days"] = fuzzed_interval
        advanced["due_date"] = review_date + int(round(fuzzed_interval))
        advanced["question_id"] = question_id
        schedule_by_question_id[question_id] = advanced
    return schedule_by_question_id
