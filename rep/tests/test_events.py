"""Event records and the fold, tested at their contract (events.py E1-E6)."""

import json
import random
import time
from datetime import UTC, date, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as strategy

from rep.events import (
    EVENT_FORMAT_VERSION,
    EVENT_ID_PATTERN,
    AmendEvent,
    AttemptEvent,
    Event,
    EventDecodeError,
    ItemStampedEvent,
    SessionEndEvent,
    SessionStartEvent,
    SuspendEvent,
    UndoEvent,
    decode_event,
    encode_event,
    fold_events,
    format_canonical_time,
    new_event_id,
    new_item_stamped_events,
    parse_canonical_time,
    scheduling_day,
)
from rep.machine import DEVICE_ID_ALPHABET
from rep.memory_model import (
    DEFAULT_DESIRED_RETENTION,
    DEFAULT_MAXIMUM_INTERVAL_DAYS,
    DEFAULT_PARAMETERS,
    MemoryState,
    first_review,
    next_interval_days,
    next_review,
)

DEVICE = "6a2ah35zhe"
START = datetime(2026, 1, 1, 9, 0, tzinfo=UTC)


def scheduling_day_for(moment: datetime) -> str:
    # The tests' own writer rule (PLAN.md D44): UTC as the local zone, a
    # 04:00 rollover. The fold never derives a day; it reads this one.
    return (moment - timedelta(hours=4)).date().isoformat()


def make_attempt(
    event_id: str, moment: datetime, item: str, rating: int | None
) -> AttemptEvent:
    return {
        "format_version": EVENT_FORMAT_VERSION,
        "id": event_id,
        "at": format_canonical_time(moment),
        "device": DEVICE,
        "kind": "attempt",
        "session": "session-one",
        "item": item,
        "rating": rating,
        "latency_milliseconds": 4200,
        "typed_answer": None,
        "fingerprint": "fingerprint-one",
        "day": scheduling_day_for(moment),
    }


def event_id_for(position: int) -> str:
    # Deterministic, valid, distinct ids: position written in the id alphabet.
    digits = ""
    remaining = position
    while len(digits) < 12:
        digits = DEVICE_ID_ALPHABET[remaining % 32] + digits
        remaining //= 32
    return digits


# A history for one or two items: (gap in seconds, item, rating or None).
history_steps = strategy.lists(
    strategy.tuples(
        strategy.integers(min_value=0, max_value=60 * 86400),
        strategy.sampled_from(["km-measure-7q2m", "atp-synthase-k3xa"]),
        strategy.one_of(strategy.none(), strategy.integers(min_value=1, max_value=4)),
    ),
    min_size=1,
    max_size=20,
)


def build_history(steps: list[tuple[int, str, int | None]]) -> list[Event]:
    events: list[Event] = []
    moment = START
    for position, (gap_seconds, item, rating) in enumerate(steps):
        moment = moment + timedelta(seconds=gap_seconds)
        events.append(make_attempt(event_id_for(position), moment, item, rating))
    return events


# ---------------------------------------------------------------- E1: records


@given(history_steps)
def test_encode_then_decode_is_identity(steps: list[tuple[int, str, int | None]]) -> None:
    for event in build_history(steps):
        line = encode_event(event)
        assert "\n" not in line
        assert decode_event(line) == event


def test_every_kind_round_trips() -> None:
    amend: AmendEvent = {
        "format_version": 1, "id": event_id_for(1), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "amend", "target": event_id_for(0), "rating": 2,
    }  # fmt: skip
    undo: UndoEvent = {
        "format_version": 1, "id": event_id_for(2), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "undo", "target": event_id_for(0),
    }  # fmt: skip
    suspend: SuspendEvent = {
        "format_version": 1, "id": event_id_for(3), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "suspend", "item": "km-measure-7q2m",
    }  # fmt: skip
    typed_attempt = make_attempt(event_id_for(4), START, "km-measure-7q2m", 3)
    typed_attempt["typed_answer"] = "half of Vmax\nwith a newline and a lambda: \u03bb"
    item_stamped: ItemStampedEvent = {
        "format_version": 1, "id": event_id_for(5), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "item_stamped", "item": "km-measure-7q2m",
    }  # fmt: skip
    for event in (amend, undo, suspend, typed_attempt, item_stamped):
        assert decode_event(encode_event(event)) == event


def test_unknown_fields_are_dropped_not_rejected() -> None:
    fields = json.loads(encode_event(make_attempt(event_id_for(0), START, "km-measure-7q2m", 3)))
    fields["added_by_a_newer_version"] = True
    decoded = decode_event(json.dumps(fields))
    assert "added_by_a_newer_version" not in decoded


@pytest.mark.parametrize(
    ("field", "bad_value", "message_fragment"),
    [
        ("format_version", 2, "format_version"),
        ("format_version", True, "format_version"),
        ("id", "SHORT", "id must be"),
        ("at", "2026-01-01T09:00:00Z", "canonical UTC"),
        ("at", "2026-02-30T09:00:00.000000Z", "not a real time"),
        ("device", "not-a-device", "device"),
        ("kind", "teleport", "unknown kind"),
        ("rating", 5, "rating"),
        ("rating", True, "rating"),
        ("latency_milliseconds", -1, "latency"),
        ("fingerprint", "", "fingerprint"),
        ("session", "", "session"),
        ("day", "2026-02-30", "not a real date"),
        ("day", "20260101", "scheduling day"),
        ("day", "2026-W01-1", "scheduling day"),
        ("day", None, "scheduling day"),
    ],
)
def test_invalid_field_is_rejected_with_its_name(
    field: str, bad_value: object, message_fragment: str
) -> None:
    fields = json.loads(encode_event(make_attempt(event_id_for(0), START, "km-measure-7q2m", 3)))
    fields[field] = bad_value
    with pytest.raises(EventDecodeError, match=message_fragment):
        decode_event(json.dumps(fields))


def test_non_json_and_non_object_lines_are_rejected() -> None:
    with pytest.raises(EventDecodeError, match="not JSON"):
        decode_event('{"format_version": 1')  # a line truncated by a crash
    with pytest.raises(EventDecodeError, match="not a JSON object"):
        decode_event("[1, 2, 3]")


@given(strategy.lists(strategy.datetimes(timezones=strategy.just(UTC)), min_size=2, max_size=20))
def test_canonical_time_strings_sort_in_time_order(moments: list[datetime]) -> None:
    by_string = sorted(moments, key=format_canonical_time)
    assert by_string == sorted(moments)
    for moment in moments:
        assert parse_canonical_time(format_canonical_time(moment)) == moment


# ------------------------------------------------------------ fold behavior


@given(history_steps)
def test_fold_equals_stepping_the_model_by_hand(steps: list[tuple[int, str, int | None]]) -> None:
    events = build_history(steps)
    result = fold_events(events)
    assert result["problems"] == []
    expected_memory: dict[str, MemoryState] = {}
    expected_last_review_day: dict[str, date] = {}
    for event in events:
        assert event["kind"] == "attempt"
        rating = event["rating"]
        if rating is None:
            continue
        review_day = date.fromisoformat(event["day"])
        previous = expected_memory.get(event["item"])
        if previous is None:
            expected_memory[event["item"]] = first_review(rating, DEFAULT_PARAMETERS)
        else:
            elapsed_whole_days = (review_day - expected_last_review_day[event["item"]]).days
            expected_memory[event["item"]] = next_review(
                previous, rating, elapsed_whole_days, DEFAULT_PARAMETERS
            )
        expected_last_review_day[event["item"]] = review_day
    for item, item_state in result["items"].items():
        assert item_state["memory"] == expected_memory.get(item)
        memory = item_state["memory"]
        if memory is None:
            assert item_state["due_day"] is None
            continue
        interval = next_interval_days(
            memory["stability"], DEFAULT_DESIRED_RETENTION, DEFAULT_MAXIMUM_INTERVAL_DAYS,
            DEFAULT_PARAMETERS,
        )  # fmt: skip
        assert item_state["scheduled_interval_days"] == interval
        due_day = item_state["due_day"]
        last_review_day = item_state["last_review_day"]
        assert due_day is not None and last_review_day is not None
        due_days = (date.fromisoformat(due_day) - date.fromisoformat(last_review_day)).days
        # Loose sanity window only; exact fuzz is pinned against py-fsrs in
        # test_memory_model. The window half-width grows to about
        # 2 + 5% of the interval, and rounding can land one day past it.
        if interval < 3:
            assert due_days == interval
        else:
            assert 2 <= due_days and abs(due_days - interval) <= 0.05 * interval + 4


@given(history_steps, strategy.randoms(use_true_random=False))
def test_fold_is_independent_of_input_order(
    steps: list[tuple[int, str, int | None]], shuffler: random.Random
) -> None:
    events = build_history(steps)
    shuffled = list(events)
    shuffler.shuffle(shuffled)
    assert fold_events(shuffled) == fold_events(events)


@given(history_steps, strategy.integers(min_value=0, max_value=19))
def test_undo_removes_exactly_its_target(
    steps: list[tuple[int, str, int | None]], undo_position: int
) -> None:
    events = build_history(steps)
    target = events[undo_position % len(events)]
    undo: UndoEvent = {
        "format_version": 1, "id": event_id_for(900), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "undo", "target": target["id"],
    }  # fmt: skip
    without_target = [event for event in events if event["id"] != target["id"]]
    assert fold_events([*events, undo]) == fold_events(without_target)


@given(history_steps, strategy.integers(min_value=0, max_value=19), strategy.integers(1, 4))
def test_amend_replays_the_attempt_with_the_new_rating(
    steps: list[tuple[int, str, int | None]], amend_position: int, new_rating: int
) -> None:
    events = build_history(steps)
    target = events[amend_position % len(events)]
    assert target["kind"] == "attempt"
    amend: AmendEvent = {
        "format_version": 1, "id": event_id_for(901),
        # Amends are written after the session; a later time than any attempt.
        "at": format_canonical_time(START + timedelta(days=5000)),
        "device": DEVICE, "kind": "amend", "target": target["id"], "rating": new_rating,
    }  # fmt: skip
    rewritten: list[Event] = []
    for event in events:
        if event["id"] == target["id"]:
            assert event["kind"] == "attempt"
            replaced = event.copy()
            replaced["rating"] = new_rating
            rewritten.append(replaced)
        else:
            rewritten.append(event)
    assert fold_events([*events, amend]) == fold_events(rewritten)


def test_ungraded_attempt_changes_no_memory_until_amended() -> None:
    ungraded = make_attempt(event_id_for(0), START, "km-measure-7q2m", None)
    ungraded_result = fold_events([ungraded])
    assert ungraded_result["items"]["km-measure-7q2m"]["memory"] is None
    assert ungraded_result["items"]["km-measure-7q2m"]["graded_review_count"] == 0
    amend: AmendEvent = {
        "format_version": 1, "id": event_id_for(1),
        "at": format_canonical_time(START + timedelta(hours=1)),
        "device": DEVICE, "kind": "amend", "target": ungraded["id"], "rating": 3,
    }  # fmt: skip
    amended_result = fold_events([ungraded, amend])
    graded_result = fold_events([make_attempt(event_id_for(0), START, "km-measure-7q2m", 3)])
    assert amended_result == graded_result


def test_lapses_count_only_again_after_a_first_review() -> None:
    events: list[Event] = [
        make_attempt(event_id_for(0), START, "km-measure-7q2m", 1),
        make_attempt(event_id_for(1), START + timedelta(days=1), "km-measure-7q2m", 3),
        make_attempt(event_id_for(2), START + timedelta(days=5), "km-measure-7q2m", 1),
    ]
    item_state = fold_events(events)["items"]["km-measure-7q2m"]
    assert item_state["lapse_count"] == 1
    assert item_state["graded_review_count"] == 3


def test_relearning_in_one_day_is_not_a_lapse() -> None:
    # PLAN.md D38, E8. The M1 fold counted 1 lapse for a new item graded
    # Again, Again, Good in its first session (measured, PLAN.md section 3).
    first_session: list[Event] = [
        make_attempt(event_id_for(0), START, "km-measure-7q2m", 1),
        make_attempt(event_id_for(1), START + timedelta(minutes=5), "km-measure-7q2m", 1),
        make_attempt(event_id_for(2), START + timedelta(minutes=10), "km-measure-7q2m", 3),
    ]
    assert fold_events(first_session)["items"]["km-measure-7q2m"]["lapse_count"] == 0
    # Forgotten three days later, then relearned in the same session: one lapse.
    later_session: list[Event] = [
        make_attempt(event_id_for(3), START + timedelta(days=3), "km-measure-7q2m", 1),
        make_attempt(event_id_for(4), START + timedelta(days=3, minutes=5), "km-measure-7q2m", 1),
        make_attempt(event_id_for(5), START + timedelta(days=3, minutes=10), "km-measure-7q2m", 3),
    ]
    assert fold_events([*first_session, *later_session])["items"]["km-measure-7q2m"]["lapse_count"] == 1


def test_time_of_day_of_a_session_does_not_change_memory() -> None:
    # PLAN.md D44, E7. Six daily Goods with each session 30 minutes earlier
    # than the day before, and with each 30 minutes later: one review per
    # scheduling day either way, so the memory must be the same. Under the
    # M1 fold the earlier sessions ended at 2.31 days of stability and the
    # later ones at 24.76 (measured, PLAN.md section 3).
    def daily_goods(step: timedelta) -> list[Event]:
        first_moment = datetime(2026, 1, 1, 20, 0, tzinfo=UTC)
        return [
            make_attempt(event_id_for(position), first_moment + step * position, "km-measure-7q2m", 3)
            for position in range(6)
        ]

    earlier_each_day = fold_events(daily_goods(timedelta(hours=23, minutes=30)))
    later_each_day = fold_events(daily_goods(timedelta(hours=24, minutes=30)))
    assert earlier_each_day["items"]["km-measure-7q2m"]["memory"] == later_each_day["items"]["km-measure-7q2m"]["memory"]
    stability = later_each_day["items"]["km-measure-7q2m"]["memory"]
    assert stability is not None and stability["stability"] > 10


def test_first_attempt_day_is_the_earliest_effective_attempt_graded_or_not() -> None:
    # PLAN.md D36: "introduced today" counts any first attempt, so an
    # ungraded one sets the day; an undone one never happened.
    undone_first = make_attempt(event_id_for(0), START, "km-measure-7q2m", 3)
    ungraded_second = make_attempt(event_id_for(1), START + timedelta(days=2), "km-measure-7q2m", None)
    graded_third = make_attempt(event_id_for(2), START + timedelta(days=4), "km-measure-7q2m", 3)
    undo: UndoEvent = {
        "format_version": 1, "id": event_id_for(3), "at": format_canonical_time(START + timedelta(days=5)),
        "device": DEVICE, "kind": "undo", "target": undone_first["id"],
    }  # fmt: skip
    item_state = fold_events([undone_first, ungraded_second, graded_third, undo])["items"]["km-measure-7q2m"]
    assert item_state["first_attempt_day"] == ungraded_second["day"]
    suspend_only: SuspendEvent = {
        "format_version": 1, "id": event_id_for(4), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "suspend", "item": "atp-synthase-k3xa",
    }  # fmt: skip
    assert fold_events([suspend_only])["items"]["atp-synthase-k3xa"]["first_attempt_day"] is None


def test_fuzz_spreads_items_reviewed_alike_over_several_due_days() -> None:
    # What fuzz is for (E6): items reviewed on the same days with the same
    # grades must not all come due on one day. Twenty items, Good on day 0
    # and Good on day 3, reach an interval where fuzz applies (3 days or
    # more); without fuzz all twenty share one due day. The hash is fixed,
    # so the spread is the same on every run.
    events: list[Event] = []
    for item_position in range(20):
        item_id = f"item{item_position}-7q2m"
        events.append(make_attempt(event_id_for(2 * item_position), START, item_id, 3))
        events.append(make_attempt(event_id_for(2 * item_position + 1), START + timedelta(days=3), item_id, 3))
    item_states = fold_events(events)["items"].values()
    intervals = {item_state["scheduled_interval_days"] for item_state in item_states}
    assert len(intervals) == 1 and min(interval for interval in intervals if interval is not None) >= 3
    assert len({item_state["due_day"] for item_state in item_states}) > 1


def test_a_day_before_the_previous_review_is_reported_and_counted_as_the_same_day() -> None:
    # Two machines in different time zones can write a later time with an
    # earlier day. The fold must neither raise nor go negative (E7).
    first = make_attempt(event_id_for(0), START, "km-measure-7q2m", 3)
    second = make_attempt(event_id_for(1), START + timedelta(hours=2), "km-measure-7q2m", 3)
    second["day"] = (date.fromisoformat(first["day"]) - timedelta(days=1)).isoformat()
    same_day_second = make_attempt(event_id_for(1), START + timedelta(hours=2), "km-measure-7q2m", 3)
    result = fold_events([first, second])
    assert len(result["problems"]) == 1 and "is before the previous review's day" in result["problems"][0]
    assert result["items"]["km-measure-7q2m"]["memory"] == fold_events([first, same_day_second])["items"]["km-measure-7q2m"]["memory"]


def test_suspend_and_unsuspend_latest_wins_and_undo_applies() -> None:
    suspend: SuspendEvent = {
        "format_version": 1, "id": event_id_for(0), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "suspend", "item": "km-measure-7q2m",
    }  # fmt: skip
    assert fold_events([suspend])["items"]["km-measure-7q2m"]["suspended"] is True
    undo: UndoEvent = {
        "format_version": 1, "id": event_id_for(1),
        "at": format_canonical_time(START + timedelta(minutes=1)),
        "device": DEVICE, "kind": "undo", "target": suspend["id"],
    }  # fmt: skip
    assert fold_events([suspend, undo])["items"] == {}


def test_bad_references_are_reported_as_problems_not_raised() -> None:
    attempt = make_attempt(event_id_for(0), START, "km-measure-7q2m", 3)
    undo_of_missing: UndoEvent = {
        "format_version": 1, "id": event_id_for(1), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "undo", "target": event_id_for(77),
    }  # fmt: skip
    undo_of_undo: UndoEvent = {
        "format_version": 1, "id": event_id_for(2), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "undo", "target": event_id_for(1),
    }  # fmt: skip
    amend_of_undo: AmendEvent = {
        "format_version": 1, "id": event_id_for(3), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "amend", "target": event_id_for(1), "rating": 2,
    }  # fmt: skip
    duplicate = make_attempt(event_id_for(0), START, "km-measure-7q2m", 1)
    result = fold_events([attempt, undo_of_missing, undo_of_undo, amend_of_undo, duplicate])
    problem_text = "\n".join(result["problems"])
    assert "unknown event" in problem_text
    assert "undo of an undo" in problem_text
    assert "is not an attempt" in problem_text
    assert "duplicate id" in problem_text
    # The valid attempt still counts once.
    assert result["items"]["km-measure-7q2m"]["graded_review_count"] == 1


def test_due_dates_are_deterministic_across_replays() -> None:
    events = build_history([(86400 * gap, "km-measure-7q2m", 3) for gap in (0, 3, 9, 27, 81)])
    assert fold_events(events) == fold_events(list(events))


def test_item_stamped_changes_no_state_and_creates_no_item() -> None:
    stamped: ItemStampedEvent = {
        "format_version": 1, "id": event_id_for(90), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "item_stamped", "item": "km-measure-7q2m",
    }  # fmt: skip
    history = build_history([(60, "km-measure-7q2m", 3), (86400, "km-measure-7q2m", 1)])
    assert fold_events([stamped]) == {"items": {}, "problems": []}
    assert fold_events([stamped, *history]) == fold_events(history)


def test_new_item_stamped_events_are_valid_and_distinct() -> None:
    random_source = random.Random(7)
    stamped_events = new_item_stamped_events(["a-7q2m", "b-7q2m"], DEVICE, START, random_source.randbytes)
    assert [event["item"] for event in stamped_events if event["kind"] == "item_stamped"] == ["a-7q2m", "b-7q2m"]
    assert len({event["id"] for event in stamped_events}) == 2
    for event in stamped_events:
        assert decode_event(encode_event(event)) == event


# ------------------------------------------------- session events (PLAN.md D40)


def session_start_event(position: int) -> SessionStartEvent:
    return {
        "format_version": 1, "id": event_id_for(position), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "session_start",
        "preset": {"session_budget": 60, "desired_retention": 0.9},
    }  # fmt: skip


def test_session_start_keeps_what_d49_records_and_reads_older_sessions_without_it() -> None:
    # PLAN.md D49: offset, plan and source hash survive a round trip; a
    # session written before D49 (none of them) still reads, unchanged.
    recorded = session_start_event(80)
    recorded["utc_offset"] = "-04:00"
    recorded["plan"] = [{"item": "km-measure-7q2m", "reason": "due"}, {"item": "capital-france-7q2m", "reason": "new"}]
    recorded["rep_source"] = "0123456789ab"
    assert decode_event(encode_event(recorded)) == recorded
    older = session_start_event(81)
    assert decode_event(encode_event(older)) == older and "plan" not in decode_event(encode_event(older))


def test_session_events_round_trip_and_change_no_state() -> None:
    session_start = session_start_event(80)
    session_end: SessionEndEvent = {
        "format_version": 1, "id": event_id_for(81), "at": format_canonical_time(START + timedelta(minutes=9)),
        "device": DEVICE, "kind": "session_end", "session": session_start["id"], "reason": "completed",
    }  # fmt: skip
    for event in (session_start, session_end):
        assert decode_event(encode_event(event)) == event
    history = build_history([(60, "km-measure-7q2m", 3), (86400, "km-measure-7q2m", 1)])
    assert fold_events([session_start, *history, session_end]) == fold_events(history)


@pytest.mark.parametrize(
    ("changes", "message_fragment"),
    [
        ({"preset": {}}, "preset must be a non-empty object"),
        ({"preset": [60]}, "preset must be a non-empty object"),
        ({"preset": {"session_budget": True}}, "session_budget must be a number"),
        ({"preset": {"session_budget": "60"}}, "session_budget must be a number"),
        ({"utc_offset": "-4"}, "utc_offset must be"),
        ({"utc_offset": "EDT"}, "utc_offset must be"),
        ({"plan": {"item": "x"}}, "plan must be a list"),
        ({"plan": ["km-measure-7q2m"]}, "plan entries must be objects"),
        ({"plan": [{"item": "", "reason": "due"}]}, "plan item must be an item id"),
        ({"plan": [{"item": "km-measure-7q2m", "reason": "later"}]}, "plan reason must be due or new"),
        ({"rep_source": "0123"}, "rep_source must be 12 hex digits"),
    ],
)
def test_invalid_session_start_is_rejected(changes: dict[str, object], message_fragment: str) -> None:
    fields = json.loads(encode_event(session_start_event(80)))
    fields.update(changes)
    with pytest.raises(EventDecodeError, match=message_fragment):
        decode_event(json.dumps(fields))


@pytest.mark.parametrize(
    ("changes", "message_fragment"),
    [
        ({"reason": "crashed"}, "reason must be completed, quit or interrupted"),
        ({"reason": None}, "reason must be"),
        ({"session": "not-an-id"}, "session must be an event id"),
    ],
)
def test_invalid_session_end_is_rejected(changes: dict[str, object], message_fragment: str) -> None:
    session_end: SessionEndEvent = {
        "format_version": 1, "id": event_id_for(81), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "session_end", "session": event_id_for(80), "reason": "quit",
    }  # fmt: skip
    fields = json.loads(encode_event(session_end))
    fields.update(changes)
    with pytest.raises(EventDecodeError, match=message_fragment):
        decode_event(json.dumps(fields))


def test_new_event_ids_are_valid() -> None:
    random_source = random.Random(11)
    event_ids = {new_event_id(random_source.randbytes) for _ in range(200)}
    assert len(event_ids) == 200
    assert all(EVENT_ID_PATTERN.match(event_id) for event_id in event_ids)


@pytest.mark.parametrize(
    ("utc_moment", "expected_day"),
    [
        # New York, UTC-4 in October: 07:59 UTC is 03:59 local, before the
        # 04:00 rollover, so it belongs to the day before (D44).
        (datetime(2026, 10, 2, 7, 59, tzinfo=UTC), "2026-10-01"),
        (datetime(2026, 10, 2, 8, 0, tzinfo=UTC), "2026-10-02"),
        (datetime(2026, 10, 3, 3, 30, tzinfo=UTC), "2026-10-02"),  # 23:30 local
        # 2026-11-01: clocks go back at 02:00 (UTC-5 after). 08:30 UTC is
        # 03:30 EST, before the rollover; 09:00 UTC is 04:00 EST.
        (datetime(2026, 11, 1, 8, 30, tzinfo=UTC), "2026-10-31"),
        (datetime(2026, 11, 1, 9, 0, tzinfo=UTC), "2026-11-01"),
    ],
)
def test_scheduling_day_uses_local_time_and_the_rollover_hour(
    monkeypatch: pytest.MonkeyPatch, utc_moment: datetime, expected_day: str
) -> None:
    monkeypatch.setenv("TZ", "America/New_York")
    time.tzset()
    try:
        assert scheduling_day(utc_moment, 4) == expected_day
    finally:
        monkeypatch.delenv("TZ")
        time.tzset()
