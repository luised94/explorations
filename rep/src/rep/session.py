"""A session's plan and its queue, as pure functions (PLAN.md D9, D31, D36, D37, D39).

REPRESENTATION
  Preset         the session settings (D39), one constant for now; each
                 session_start event records a copy (D40).
  LocatedItem    a checked library Item with the path of its file
                 (library.py), from check_library_files: no item with an
                 error, no id twice (D22, library.py L11).
  PlanSlot       one item id and why it is in the queue: "due", "new", or
                 "relearn" for a showing added during the session.
  Plan           the ordered slots a session starts with: reviews, then new
                 items. A pure function of the library, the fold's states,
                 the events (for capture times only), the scheduling day and
                 the preset.
  The queue      the slots still to show, recomputed from the plan and the
                 session's own events after every action (D31). There is no
                 mutable queue: a correction is an event, and replaying the
                 events gives the queue.

INVARIANTS
  P1  plan_session is pure: equal inputs give an equal plan.
  P2  Every slot names an item of the located items that has no fold state
      marked suspended; no item appears twice.
  P3  Due slots come first: items with a memory state due on or before
      today, lowest retrievability first (ties: due day, then id), at most
      session_budget of them.
  P4  New slots follow: items with no memory state not first attempted
      today, at most max(0, min(new_per_day - introduced today,
      (session_budget - due slots) // new_item_cost)), in D37 order.
  Q1  session_queue is pure, and order-independent in the session's events
      (it sorts them, as the fold does): replaying a session reproduces it.
  Q2  An attempt graded Again puts its item back after relearn_gap other
      slots, or at the end when fewer remain.
  Q3  An item leaves the queue on a graded attempt other than Again that is
      not a new item's first showing, on an ungraded attempt (it waits for
      `rep review`, D35), or on a suspend.
  Q4  If every showing is graded Good, the queue empties after exactly
      (due slots) + 2 * (new slots) attempts.
"""

from datetime import date
from typing import Literal, TypedDict

from rep.events import Event, ItemState, effective_events
from rep.library import LocatedItem
from rep.memory_model import AGAIN, DEFAULT_PARAMETERS, retrievability


class Preset(TypedDict):
    session_budget: int  # most attempts the plan serves before relearning
    new_per_day: int
    new_item_cost: int  # budget one new item uses: its showing, its return, a miss
    relearn_gap: int  # other slots between two showings of one item
    day_start_hour: int  # local hour a scheduling day starts (D44)
    desired_retention: float


# PLAN.md D36, D39. Approved numbers. A constant, not config.toml: tuning is
# an edit and a commit, and session_start records the values used.
DEFAULT_PRESET: Preset = {
    "session_budget": 60,
    "new_per_day": 10,
    "new_item_cost": 3,
    "relearn_gap": 3,
    "day_start_hour": 4,
    "desired_retention": 0.9,
}


class PlanSlot(TypedDict):
    item_id: str
    reason: Literal["due", "new", "relearn"]


def plan_session(
    located_items: list[LocatedItem],
    item_states: dict[str, ItemState],
    events: list[Event],
    today: str,
    preset: Preset,
) -> list[PlanSlot]:
    """The ordered slots a session starts with (PLAN.md D36, D37; P1-P4).

    PRE   located_items hold no item with an error and no id twice (the
          caller applies D22). item_states is fold_events(...)["items"] over
          the same events. today is a scheduling day, YYYY-MM-DD.
    POST  due slots, then new slots, satisfying P2-P4.
    """
    today_date = date.fromisoformat(today)

    # --- due: a memory state, due on or before today, lowest retrievability first ---
    # (retrievability, due day, id) sorts as P3 says: the item most likely
    # forgotten first, so a session cut short loses the least.
    due_candidates: list[tuple[float, str, str]] = []
    new_candidates: list[LocatedItem] = []
    introduced_today_count = 0
    for located_item in located_items:
        item_state = item_states.get(located_item["item"]["id"])
        if item_state is not None and item_state["first_attempt_day"] == today:
            introduced_today_count += 1
        if item_state is not None and item_state["suspended"]:
            continue
        if item_state is None or item_state["memory"] is None:
            # P4: an item shown today and not yet graded stays out of today's
            # new items; its grade comes from `rep review`.
            if item_state is None or item_state["first_attempt_day"] != today:
                new_candidates.append(located_item)
            continue
        due_day = item_state["due_day"]
        last_review_day = item_state["last_review_day"]
        assert due_day is not None and last_review_day is not None, "a memory state has a due day"
        if date.fromisoformat(due_day) > today_date:
            continue
        # A clock behind the history (D40) can put the last review after
        # today; retrievability is then that of a review made today.
        elapsed_days = max((today_date - date.fromisoformat(last_review_day)).days, 0)
        recall_probability = retrievability(item_state["memory"]["stability"], elapsed_days, DEFAULT_PARAMETERS)
        due_candidates.append((recall_probability, due_day, located_item["item"]["id"]))
    due_candidates.sort()
    due_slots: list[PlanSlot] = [
        {"item_id": item_id, "reason": "due"} for _, _, item_id in due_candidates[: preset["session_budget"]]
    ]

    # --- new: D37 order, D36 cap ---
    # Earliest capture per item. Only item_stamped events say when an item
    # was written; undoing one is never done, so they are read as they are.
    first_stamped_at: dict[str, str] = {}
    for event in events:
        if event["kind"] == "item_stamped":
            known_at = first_stamped_at.get(event["item"])
            if known_at is None or event["at"] < known_at:
                first_stamped_at[event["item"]] = event["at"]
    # A file is ordered by the earliest capture among its new items: the
    # reading begun first is finished first; inside a file, line order.
    file_first_stamped_at: dict[str, str] = {}
    for located_item in new_candidates:
        stamped_at = first_stamped_at.get(located_item["item"]["id"])
        known_at = file_first_stamped_at.get(located_item["path"])
        if stamped_at is not None and (known_at is None or stamped_at < known_at):
            file_first_stamped_at[located_item["path"]] = stamped_at
    # Items with no capture time (a hand-written id) come last, by path and line.
    new_candidates.sort(
        key=lambda located_item: (
            located_item["item"]["id"] not in first_stamped_at,
            file_first_stamped_at.get(located_item["path"], ""),
            located_item["path"],
            located_item["item"]["line"],
        )
    )
    new_allowance = min(
        preset["new_per_day"] - introduced_today_count,
        (preset["session_budget"] - len(due_slots)) // preset["new_item_cost"],
    )
    new_slots: list[PlanSlot] = [
        {"item_id": located_item["item"]["id"], "reason": "new"} for located_item in new_candidates[: max(new_allowance, 0)]
    ]
    return due_slots + new_slots


def session_queue(plan: list[PlanSlot], session_events: list[Event], preset: Preset) -> list[PlanSlot]:
    """The slots still to show, after this session's events (PLAN.md D31, D35, D36; Q1-Q4).

    PRE   plan came from plan_session for this session; session_events are
          the events this session wrote (attempts carrying its id, and the
          amends, undos and suspends it wrote).
    POST  the queue, head first; empty when the session is complete.
    """
    effective = effective_events(session_events)
    queue: list[PlanSlot] = list(plan)
    shown_item_ids: set[str] = set()
    for event in effective["ordered_events"]:
        if event["id"] in effective["undone_event_ids"]:
            continue
        if event["kind"] == "suspend":
            queue = [slot for slot in queue if slot["item_id"] != event["item"]]
            continue
        if event["kind"] != "attempt":
            continue
        item_id = event["item"]
        # The slot this attempt answered: the item's first slot in the queue.
        # An attempt for an item no longer queued (its slot removed by a
        # later correction) is still applied, so replay never fails.
        answered_reason: str = "relearn"
        for slot in queue:
            if slot["item_id"] == item_id:
                answered_reason = slot["reason"]
                break
        queue = [slot for slot in queue if slot["item_id"] != item_id]
        first_showing_of_new_item = answered_reason == "new" and item_id not in shown_item_ids
        shown_item_ids.add(item_id)
        effective_rating = effective["amended_ratings"].get(event["id"], event["rating"])
        if effective_rating is None:
            continue  # Q3: `?` waits for review
        if effective_rating == AGAIN or first_showing_of_new_item:
            # Q2, and D36's blocking rule: a new item must be recalled once
            # after other items came between.
            return_position = min(preset["relearn_gap"], len(queue))
            queue.insert(return_position, {"item_id": item_id, "reason": "relearn"})
    return queue
