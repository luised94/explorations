"""The plan and the queue, tested at their contract (session.py P1-P4, Q1-Q4)."""

import random
from datetime import UTC, datetime, timedelta

import pytest
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
from rep.session import (
    DEFAULT_PRESET,
    PlanSlot,
    SheetEntry,
    plan_session,
    read_grading_sheet,
    render_grading_sheet,
    session_queue,
    session_rounds,
)

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


# --- rounds (R1-R4, PLAN.md D45) -----------------------------------------------


def answer_in_rounds(plan: list[PlanSlot], grade_for: dict[str, list[int | None]]) -> tuple[list[Event], list[int]]:
    """Answer every round to its end, each attempt written with its grade
    (as rep writes exact and numeric ones); grade_for gives an item's grades
    in order, Good once they run out. Returns the events and the size of
    each round."""
    session_events: list[Event] = []
    grades_left = {item_id: list(grades) for item_id, grades in grade_for.items()}
    round_sizes: list[int] = []
    while True:
        state = session_rounds(plan, session_events)
        if state["unanswered_item_ids"] == []:
            return session_events, round_sizes
        if len(round_sizes) < state["round_number"]:
            round_sizes.append(len(state["round_item_ids"]))
        assert len(session_events) < 1000, "the rounds did not end"
        item_id = state["unanswered_item_ids"][0]
        item_grades = grades_left.get(item_id, [])
        rating = item_grades.pop(0) if item_grades != [] else 3
        moment = START + timedelta(seconds=len(session_events))
        session_events.append(attempt(len(session_events), moment, item_id, rating, "2026-10-01"))


@given(strategies.integers(min_value=0, max_value=12), strategies.integers(min_value=0, max_value=12))
def test_all_good_rounds_take_reviews_plus_twice_the_new_items(due_count: int, new_count: int) -> None:
    # R4: a review is answered once; a new item twice, its first showing
    # always returning (D36).
    plan: list[PlanSlot] = [{"item_id": f"due{index}-7q2m", "reason": "due"} for index in range(due_count)]
    new_slots: list[PlanSlot] = [{"item_id": f"new{index}-7q2m", "reason": "new"} for index in range(new_count)]
    plan += new_slots
    session_events, round_sizes = answer_in_rounds(plan, {})
    assert len(session_events) == due_count + 2 * new_count
    assert round_sizes == ([due_count + new_count] if due_count + new_count > 0 else []) + ([new_count] if new_count > 0 else [])


def test_a_miss_returns_in_the_next_round_until_recalled() -> None:
    plan: list[PlanSlot] = [{"item_id": f"item{index}-7q2m", "reason": "due"} for index in range(3)]
    session_events, round_sizes = answer_in_rounds(plan, {"item1-7q2m": [1, 1, 3]})
    assert round_sizes == [3, 1, 1]
    assert [event["item"] for event in session_events if event["kind"] == "attempt"] == [
        "item0-7q2m", "item1-7q2m", "item2-7q2m", "item1-7q2m", "item1-7q2m",
    ]  # fmt: skip


def test_rounds_wait_on_their_unanswered_items_in_plan_order() -> None:
    plan: list[PlanSlot] = [{"item_id": f"item{index}-7q2m", "reason": "due"} for index in range(3)]
    first: list[Event] = [attempt(0, START, "item0-7q2m", None, "2026-10-01")]
    assert session_rounds(plan, first) == {
        "round_number": 1,
        "round_item_ids": ["item0-7q2m", "item1-7q2m", "item2-7q2m"],
        "unanswered_item_ids": ["item1-7q2m", "item2-7q2m"],
    }


def test_an_ungraded_answer_or_a_suspend_ends_the_item_and_an_amend_decides() -> None:
    # R3: after the round, "?" and suspend leave; the round's grades, by
    # amend, decide the rest.
    plan: list[PlanSlot] = [{"item_id": f"item{index}-7q2m", "reason": "due"} for index in range(3)]
    answers: list[Event] = [attempt(index, START + timedelta(seconds=index), f"item{index}-7q2m", None, "2026-10-01") for index in range(3)]
    ungraded_round = session_rounds(plan, answers)
    assert (ungraded_round["round_number"], ungraded_round["unanswered_item_ids"]) == (1, [])
    graded: list[Event] = []
    for position, (answer, rating) in enumerate(zip(answers, [1, 1, 3], strict=True)):
        amend: AmendEvent = {
            "format_version": EVENT_FORMAT_VERSION, "id": event_id_for(10 + position),
            "at": format_canonical_time(START + timedelta(minutes=1)), "device": DEVICE, "kind": "amend",
            "target": answer["id"], "rating": rating,
        }  # fmt: skip
        graded.append(amend)
    suspend: SuspendEvent = {
        "format_version": EVENT_FORMAT_VERSION, "id": event_id_for(20), "at": format_canonical_time(START + timedelta(minutes=1)),
        "device": DEVICE, "kind": "suspend", "item": "item1-7q2m",
    }  # fmt: skip
    assert session_rounds(plan, [*answers, *graded, suspend]) == {
        "round_number": 2, "round_item_ids": ["item0-7q2m"], "unanswered_item_ids": ["item0-7q2m"],
    }  # fmt: skip


def test_a_new_item_recalled_at_first_sight_returns_for_one_more_round() -> None:
    plan: list[PlanSlot] = [{"item_id": "new-7q2m", "reason": "new"}, {"item_id": "due-7q2m", "reason": "due"}]
    session_events, round_sizes = answer_in_rounds(plan, {})
    assert round_sizes == [2, 1]
    assert [event["item"] for event in session_events if event["kind"] == "attempt"] == ["new-7q2m", "due-7q2m", "new-7q2m"]


@given(strategies.lists(strategies.sampled_from([1, 3, None]), min_size=1, max_size=12), strategies.randoms(use_true_random=False))
def test_rounds_are_a_function_of_the_events_not_their_order(grades: list[int | None], shuffler: random.Random) -> None:
    # R1: replaying a session's events in any order gives the same state.
    plan: list[PlanSlot] = [{"item_id": f"item{index}-7q2m", "reason": "due"} for index in range(4)]
    plan.append({"item_id": "new-7q2m", "reason": "new"})
    session_events, _ = answer_in_rounds(plan, {"item0-7q2m": list(grades), "new-7q2m": list(grades)})
    shuffled = list(session_events)
    shuffler.shuffle(shuffled)
    assert session_rounds(plan, shuffled) == session_rounds(plan, session_events)
    assert session_rounds(plan, session_events)["unanswered_item_ids"] == []


# --- the grading sheet (G1-G4, PLAN.md D41, D45) -------------------------------


def sheet_entry(position: int, rating: int | None, question: str = "What does Km measure?") -> SheetEntry:
    return {
        "attempt_id": event_id_for(position), "item_id": f"item{position}-7q2m", "rating": rating,
        "path": "/home/person/learning/library/a.md", "line": 3 + 4 * position, "question": question,
        "typed_answer": "half vmax", "answer": "half of Vmax", "criteria": None,
    }  # fmt: skip


def test_an_unedited_sheet_asks_for_nothing_and_lays_out_each_answer() -> None:
    entries = [sheet_entry(0, None), sheet_entry(1, 3, "Capital of\nFrance?"), sheet_entry(2, 1)]
    sheet_text = render_grading_sheet(entries, "round 1")
    assert read_grading_sheet(sheet_text, entries) == {"amends": [], "suspended_item_ids": [], "problems": []}
    read_lines = [line for line in sheet_text.split("\n") if line.strip() != "" and not line.startswith("#")]
    assert read_lines == [
        f"?       {event_id_for(0)}  What does Km measure?",
        f"good    {event_id_for(1)}  Capital of / France?",
        f"again   {event_id_for(2)}  What does Km measure?",
    ]
    assert "#         typed:  half vmax\n#         key:    half of Vmax\n#         item:   /home/person/learning/library/a.md:3" in sheet_text


@given(
    strategies.lists(strategies.sampled_from([None, 1, 3]), min_size=1, max_size=8),
    strategies.lists(strategies.sampled_from(["again", "hard", "good", "easy", "?", "suspend", "Good"]), min_size=8, max_size=8),
)
def test_each_changed_word_asks_for_exactly_its_change(ratings: list[int | None], new_words: list[str]) -> None:
    entries = [sheet_entry(position, rating) for position, rating in enumerate(ratings)]
    edited_lines: list[str] = []
    for sheet_line in render_grading_sheet(entries, "round 1").split("\n"):
        words = sheet_line.split()
        if words != [] and not words[0].startswith("#"):
            position = [entry["attempt_id"] for entry in entries].index(words[1])
            sheet_line = new_words[position] + sheet_line[len(words[0]):]
        edited_lines.append(sheet_line)
    result = read_grading_sheet("\n".join(edited_lines), entries)
    expected_amends: list[tuple[str, int]] = []
    expected_suspends: list[str] = []
    expect_problem = False
    for entry, word in zip(entries, new_words, strict=False):
        if word == "suspend":
            expected_suspends.append(entry["item_id"])
            continue
        new_rating = {"again": 1, "hard": 2, "good": 3, "easy": 4, "?": None}[word.lower()]
        if new_rating is None:
            expect_problem = expect_problem or entry["rating"] is not None
        elif new_rating != entry["rating"]:
            expected_amends.append((entry["attempt_id"], new_rating))
    if expect_problem:
        assert result["amends"] == [] and result["suspended_item_ids"] == [] and result["problems"] != []
    else:
        assert result == {"amends": expected_amends, "suspended_item_ids": expected_suspends, "problems": []}


@pytest.mark.parametrize(
    ("edited_line", "problem_fragment"),
    [
        (f"goood   {event_id_for(0)}  What does Km measure?", "is not a grade"),
        ("good    zzzzzzzzzzzz  What does Km measure?", "no answer of this sheet"),
        ("good", "no answer of this sheet"),
    ],
)
def test_a_sheet_with_a_problem_applies_nothing(edited_line: str, problem_fragment: str) -> None:
    entries = [sheet_entry(0, None), sheet_entry(1, None)]
    sheet_lines = render_grading_sheet(entries, "round 1").split("\n")
    first_read_line = next(index for index, line in enumerate(sheet_lines) if line.startswith("?"))
    sheet_lines[first_read_line] = edited_line
    sheet_lines.append(f"good    {event_id_for(1)}  What does Km measure?")  # a second line for the same answer
    result = read_grading_sheet("\n".join(sheet_lines), entries)
    assert result["amends"] == [] and result["suspended_item_ids"] == []
    assert any(problem_fragment in problem for problem in result["problems"])
    assert any("appears twice" in problem for problem in result["problems"])


def test_a_deleted_line_leaves_its_answer_as_it_is() -> None:
    entries = [sheet_entry(0, 1), sheet_entry(1, None)]
    sheet_lines = [line for line in render_grading_sheet(entries, "round 1").split("\n") if event_id_for(0) not in line]
    assert read_grading_sheet("\n".join(sheet_lines), entries) == {"amends": [], "suspended_item_ids": [], "problems": []}


def test_a_new_item_left_ungraded_does_not_return() -> None:
    # R3 before D36's blocking rule: a new item's first showing returns
    # whatever its grade, unless it was left ungraded; "?" waits for review.
    plan: list[PlanSlot] = [{"item_id": "new-7q2m", "reason": "new"}, {"item_id": "due-7q2m", "reason": "due"}]
    answers: list[Event] = [
        attempt(0, START, "new-7q2m", None, "2026-10-01"),
        attempt(1, START + timedelta(seconds=1), "due-7q2m", 1, "2026-10-01"),
    ]
    assert session_rounds(plan, answers) == {
        "round_number": 2, "round_item_ids": ["due-7q2m"], "unanswered_item_ids": ["due-7q2m"],
    }  # fmt: skip
