"""Event records and the fold, tested at their contract (events.py E1-E6)."""

import json
import random
from datetime import UTC, datetime, timedelta

import pytest
from hypothesis import given
from hypothesis import strategies as strategy

from rep.events import (
    EVENT_FORMAT_VERSION,
    AmendEvent,
    AttemptEvent,
    Event,
    EventDecodeError,
    ItemStampedEvent,
    SuspendEvent,
    UndoEvent,
    decode_event,
    encode_event,
    fold_events,
    format_canonical_time,
    new_item_stamped_events,
    parse_canonical_time,
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
    expected_last_review: dict[str, datetime] = {}
    for event in events:
        assert event["kind"] == "attempt"
        rating = event["rating"]
        if rating is None:
            continue
        moment = parse_canonical_time(event["at"])
        previous = expected_memory.get(event["item"])
        if previous is None:
            expected_memory[event["item"]] = first_review(rating, DEFAULT_PARAMETERS)
        else:
            elapsed_whole_days = (moment - expected_last_review[event["item"]]).days
            expected_memory[event["item"]] = next_review(
                previous, rating, elapsed_whole_days, DEFAULT_PARAMETERS
            )
        expected_last_review[event["item"]] = moment
    for item, item_state in result["items"].items():
        assert item_state["memory"] == expected_memory.get(item)
        memory = item_state["memory"]
        if memory is None:
            assert item_state["due_at"] is None
            continue
        interval = next_interval_days(
            memory["stability"], DEFAULT_DESIRED_RETENTION, DEFAULT_MAXIMUM_INTERVAL_DAYS,
            DEFAULT_PARAMETERS,
        )  # fmt: skip
        assert item_state["scheduled_interval_days"] == interval
        due_at = item_state["due_at"]
        last_review_at = item_state["last_review_at"]
        assert due_at is not None and last_review_at is not None
        due_days = (parse_canonical_time(due_at) - parse_canonical_time(last_review_at)).days
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
