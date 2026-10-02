"""The plan and the queue, tested at their contract (session.py P1-P4, Q1-Q4)."""

import random
from datetime import UTC, datetime, timedelta

from hypothesis import given
from hypothesis import strategies as strategies

from rep.events import (
    EVENT_FORMAT_VERSION,
    AmendEvent,
    AttemptEvent,
    Event,
    ItemStampedEvent,
    SuspendEvent,
    UndoEvent,
    fold_events,
    format_canonical_time,
)
from rep.library import LocatedItem, check_source_item, parse_library_text
from rep.machine import DEVICE_ID_ALPHABET
from rep.session import DEFAULT_PRESET, PlanSlot, plan_session, session_queue

DEVICE = "6a2ah35zhe"
START = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)


def event_id_for(position: int) -> str:
    digits = ""
    remaining = position
    while len(digits) < 12:
        digits = DEVICE_ID_ALPHABET[remaining % 32] + digits
        remaining //= 32
    return digits


def attempt(position: int, moment: datetime, item_id: str, rating: int | None, day: str) -> AttemptEvent:
    return {
        "format_version": EVENT_FORMAT_VERSION, "id": event_id_for(position), "at": format_canonical_time(moment),
        "device": DEVICE, "kind": "attempt", "session": "s", "item": item_id, "rating": rating,
        "latency_milliseconds": 1000, "typed_answer": None, "fingerprint": "f1:0", "day": day,
    }  # fmt: skip


def stamped(position: int, moment: datetime, item_id: str) -> ItemStampedEvent:
    return {
        "format_version": EVENT_FORMAT_VERSION, "id": event_id_for(position), "at": format_canonical_time(moment),
        "device": DEVICE, "kind": "item_stamped", "item": item_id,
    }  # fmt: skip


def located(path: str, library_text: str) -> list[LocatedItem]:
    located_items: list[LocatedItem] = []
    for source_item in parse_library_text(library_text):
        item, problems = check_source_item(source_item)
        assert item is not None, problems
        located_items.append({"path": path, "item": item})
    return located_items


def library_text(*item_ids: str) -> str:
    return "".join(f"### Q: question {item_id}\nid: {item_id}\nA: answer\n\n" for item_id in item_ids)


# --- the plan (P1-P4) ----------------------------------------------------------


def test_due_items_come_first_lowest_retrievability_first_and_future_items_wait() -> None:
    # One first review each, on one day: Again, Good and Easy give three
    # different stabilities, so on any day all three are due their
    # retrievabilities differ and the order is exact.
    items = located("a.md", library_text("weak-7q2m", "middle-7q2m", "strong-7q2m", "fresh-7q2m"))
    events: list[Event] = [
        attempt(0, START, "weak-7q2m", 1, "2026-10-01"),
        attempt(1, START, "middle-7q2m", 3, "2026-10-01"),
        attempt(2, START, "strong-7q2m", 4, "2026-10-01"),
    ]
    states = fold_events(events)["items"]
    strong_due_day = states["strong-7q2m"]["due_day"]
    assert strong_due_day is not None
    plan = plan_session(items, states, events, strong_due_day, DEFAULT_PRESET)
    assert plan == [
        {"item_id": "weak-7q2m", "reason": "due"},
        {"item_id": "middle-7q2m", "reason": "due"},
        {"item_id": "strong-7q2m", "reason": "due"},
        {"item_id": "fresh-7q2m", "reason": "new"},
    ]
    # The next day only the Again item (interval 1 day) is due.
    plan_on_day_two = plan_session(items, states, events, "2026-10-02", DEFAULT_PRESET)
    assert [slot["item_id"] for slot in plan_on_day_two if slot["reason"] == "due"] == ["weak-7q2m"]


def test_suspended_items_are_never_planned() -> None:
    items = located("a.md", library_text("kept-7q2m", "paused-7q2m"))
    suspend: SuspendEvent = {
        "format_version": EVENT_FORMAT_VERSION, "id": event_id_for(9), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "suspend", "item": "paused-7q2m",
    }  # fmt: skip
    events: list[Event] = [suspend]
    plan = plan_session(items, fold_events(events)["items"], events, "2026-10-01", DEFAULT_PRESET)
    assert plan == [{"item_id": "kept-7q2m", "reason": "new"}]


def test_one_budget_caps_reviews_and_shrinks_new_intake() -> None:
    due_ids = [f"due{index}-7q2m" for index in range(4)]
    new_ids = [f"new{index}-7q2m" for index in range(5)]
    items = located("a.md", library_text(*due_ids, *new_ids))
    events: list[Event] = [attempt(index, START, item_id, 3, "2026-09-01") for index, item_id in enumerate(due_ids)]
    states = fold_events(events)["items"]
    # Budget 7, cost 2: 4 reviews leave 3, which buys one new item.
    preset = DEFAULT_PRESET.copy()
    preset["session_budget"], preset["new_item_cost"] = 7, 2
    plan = plan_session(items, states, events, "2026-10-01", preset)
    assert [slot["reason"] for slot in plan] == ["due", "due", "due", "due", "new"]
    # Budget 3: the backlog is capped and no new item enters.
    preset["session_budget"] = 3
    plan = plan_session(items, states, events, "2026-10-01", preset)
    assert [slot["reason"] for slot in plan] == ["due", "due", "due"]


def test_items_introduced_today_use_up_the_daily_allowance() -> None:
    new_ids = [f"new{index}-7q2m" for index in range(6)]
    items = located("a.md", library_text(*new_ids))
    # Earlier today: two items shown, one graded, one left for review (`?`).
    events: list[Event] = [
        attempt(0, START, "new0-7q2m", 3, "2026-10-01"),
        attempt(1, START, "new1-7q2m", None, "2026-10-01"),
    ]
    preset = DEFAULT_PRESET.copy()
    preset["new_per_day"] = 3
    plan = plan_session(items, fold_events(events)["items"], events, "2026-10-01", preset)
    # 3 per day, 2 introduced: one more, and never the ungraded one again.
    assert plan == [{"item_id": "new2-7q2m", "reason": "new"}]
    # The next day the ungraded item is new again; the graded one is not.
    plan = plan_session(items, fold_events(events)["items"], events, "2026-10-02", preset)
    assert [slot["item_id"] for slot in plan if slot["reason"] == "new"] == ["new1-7q2m", "new2-7q2m", "new3-7q2m"]


def test_new_items_follow_capture_order_between_files_and_line_order_within() -> None:
    # b.md was captured first, so its items come first, in line order even
    # where a later line was captured earlier. An item with no capture time
    # (a hand-written id) comes last.
    items = located("a.md", library_text("a1-7q2m", "a2-7q2m")) + located(
        "b.md", library_text("b1-7q2m", "b2-7q2m", "byhand-7q2m")
    )
    events: list[Event] = [
        stamped(0, START + timedelta(days=2), "a1-7q2m"),
        stamped(1, START + timedelta(days=2), "a2-7q2m"),
        stamped(2, START + timedelta(days=1), "b2-7q2m"),
        stamped(3, START + timedelta(days=1, hours=1), "b1-7q2m"),
    ]
    plan = plan_session(items, fold_events(events)["items"], events, "2026-10-05", DEFAULT_PRESET)
    assert [slot["item_id"] for slot in plan] == ["b1-7q2m", "b2-7q2m", "a1-7q2m", "a2-7q2m", "byhand-7q2m"]


def test_plan_is_pure() -> None:
    items = located("a.md", library_text("one-7q2m", "two-7q2m"))
    events: list[Event] = [attempt(0, START, "one-7q2m", 3, "2026-09-01")]
    states = fold_events(events)["items"]
    assert plan_session(items, states, events, "2026-10-01", DEFAULT_PRESET) == plan_session(
        list(items), dict(states), list(events), "2026-10-01", DEFAULT_PRESET
    )


# --- the queue (Q1-Q4) ---------------------------------------------------------


def run_session(plan: list[PlanSlot], grade_for: dict[str, list[int | None]]) -> tuple[list[Event], int]:
    """Answer the head of the queue until it empties; grade_for gives each
    item's grades in order, Good once they run out. Returns the events and
    the number of attempts."""
    session_events: list[Event] = []
    grades_left = {item_id: list(grades) for item_id, grades in grade_for.items()}
    queue = session_queue(plan, session_events, DEFAULT_PRESET)
    while queue != []:
        assert len(session_events) < 1000, "the queue did not empty"
        head_item_id = queue[0]["item_id"]
        item_grades = grades_left.get(head_item_id, [])
        rating = item_grades.pop(0) if item_grades != [] else 3
        moment = START + timedelta(seconds=len(session_events))
        session_events.append(attempt(len(session_events), moment, head_item_id, rating, "2026-10-01"))
        queue = session_queue(plan, session_events, DEFAULT_PRESET)
    return session_events, len(session_events)


@given(strategies.integers(min_value=0, max_value=12), strategies.integers(min_value=0, max_value=12))
def test_all_good_session_ends_after_reviews_plus_twice_the_new_items(due_count: int, new_count: int) -> None:
    # Q4: each review is shown once; each new item twice (its first showing
    # always returns, D36).
    plan: list[PlanSlot] = [{"item_id": f"due{index}-7q2m", "reason": "due"} for index in range(due_count)]
    new_slots: list[PlanSlot] = [{"item_id": f"new{index}-7q2m", "reason": "new"} for index in range(new_count)]
    plan += new_slots
    _, attempt_count = run_session(plan, {})
    assert attempt_count == due_count + 2 * new_count


def test_again_returns_after_the_gap_and_at_the_end_when_fewer_remain() -> None:
    plan: list[PlanSlot] = [{"item_id": f"item{index}-7q2m", "reason": "due"} for index in range(6)]
    missed: list[Event] = [attempt(0, START, "item0-7q2m", 1, "2026-10-01")]
    queue = session_queue(plan, missed, DEFAULT_PRESET)
    assert [slot["item_id"] for slot in queue] == [
        "item1-7q2m", "item2-7q2m", "item3-7q2m", "item0-7q2m", "item4-7q2m", "item5-7q2m",
    ]  # fmt: skip
    assert queue[3]["reason"] == "relearn"
    short_plan: list[PlanSlot] = plan[:2]
    queue = session_queue(short_plan, missed, DEFAULT_PRESET)
    assert [slot["item_id"] for slot in queue] == ["item1-7q2m", "item0-7q2m"]


def test_question_mark_and_suspend_drop_the_item_and_undoing_the_suspend_restores_it() -> None:
    plan: list[PlanSlot] = [{"item_id": f"item{index}-7q2m", "reason": "due"} for index in range(3)]
    ungraded = attempt(0, START, "item0-7q2m", None, "2026-10-01")
    assert [slot["item_id"] for slot in session_queue(plan, [ungraded], DEFAULT_PRESET)] == ["item1-7q2m", "item2-7q2m"]
    suspend: SuspendEvent = {
        "format_version": EVENT_FORMAT_VERSION, "id": event_id_for(1), "at": format_canonical_time(START),
        "device": DEVICE, "kind": "suspend", "item": "item1-7q2m",
    }  # fmt: skip
    assert [slot["item_id"] for slot in session_queue(plan, [suspend], DEFAULT_PRESET)] == ["item0-7q2m", "item2-7q2m"]
    undo: UndoEvent = {
        "format_version": EVENT_FORMAT_VERSION, "id": event_id_for(2), "at": format_canonical_time(START + timedelta(seconds=1)),
        "device": DEVICE, "kind": "undo", "target": suspend["id"],
    }  # fmt: skip
    assert session_queue(plan, [suspend, undo], DEFAULT_PRESET) == plan


def test_an_amend_from_again_to_good_takes_the_item_out_of_relearning() -> None:
    # PLAN.md D35: `u` corrects a grade with an amend, and the queue follows.
    plan: list[PlanSlot] = [{"item_id": f"item{index}-7q2m", "reason": "due"} for index in range(4)]
    missed = attempt(0, START, "item0-7q2m", 1, "2026-10-01")
    corrected: AmendEvent = {
        "format_version": EVENT_FORMAT_VERSION, "id": event_id_for(1), "at": format_canonical_time(START + timedelta(seconds=1)),
        "device": DEVICE, "kind": "amend", "target": missed["id"], "rating": 3,
    }  # fmt: skip
    assert [slot["item_id"] for slot in session_queue(plan, [missed, corrected], DEFAULT_PRESET)] == [
        "item1-7q2m", "item2-7q2m", "item3-7q2m",
    ]  # fmt: skip


def test_a_new_item_recalled_at_first_sight_still_returns_once() -> None:
    plan: list[PlanSlot] = [{"item_id": "new-7q2m", "reason": "new"}, {"item_id": "due-7q2m", "reason": "due"}]
    first_sight = attempt(0, START, "new-7q2m", 3, "2026-10-01")
    queue = session_queue(plan, [first_sight], DEFAULT_PRESET)
    assert queue == [{"item_id": "due-7q2m", "reason": "due"}, {"item_id": "new-7q2m", "reason": "relearn"}]
    after_gap = attempt(2, START + timedelta(seconds=2), "new-7q2m", 3, "2026-10-01")
    between = attempt(1, START + timedelta(seconds=1), "due-7q2m", 3, "2026-10-01")
    assert session_queue(plan, [first_sight, between, after_gap], DEFAULT_PRESET) == []


@given(strategies.lists(strategies.sampled_from([1, 3, None]), min_size=1, max_size=15), strategies.randoms(use_true_random=False))
def test_queue_is_a_function_of_the_events_not_their_order(grades: list[int | None], shuffler: random.Random) -> None:
    # Q1: a session replayed from its events in any order gives the same
    # queue, because the events are sorted as the fold sorts them.
    plan: list[PlanSlot] = [{"item_id": f"item{index}-7q2m", "reason": "due"} for index in range(5)]
    plan.append({"item_id": "new-7q2m", "reason": "new"})
    grade_for: dict[str, list[int | None]] = {"item0-7q2m": list(grades), "new-7q2m": list(grades)}
    session_events, _ = run_session(plan, grade_for)
    shuffled = list(session_events)
    shuffler.shuffle(shuffled)
    assert session_queue(plan, shuffled, DEFAULT_PRESET) == session_queue(plan, session_events, DEFAULT_PRESET) == []
