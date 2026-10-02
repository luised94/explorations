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
  (session_queue is replaced by session_rounds when the session loop moves
  to rounds, PLAN.md D45.)

ROUNDS AND THE GRADING SHEET (PLAN.md D45, D41)
  RoundState     the round in progress: its number, its items, and those
                 not yet answered in it.
  SheetEntry     one answer as the grading sheet shows it: the attempt, its
                 grade now, the item's place, question, key, and what was
                 typed. SheetResult: the amends and suspends a saved sheet
                 asks for, or the problems that stop it.
  R1  session_rounds is pure and order-independent in the session's events;
      an item's k-th effective attempt in the session is its round-k answer.
  R2  Round 1 is the plan's items in plan order; round r+1 is the items of
      round r, in that order, that did not meet D36's criterion in round r
      (a grade other than Again, and not a new item's first showing) and
      did not leave.
  R3  An item leaves after round r when its round-r answer is ungraded (it
      waits for `rep review`) or when it was suspended.
  R4  If every answer is graded Good, the session takes exactly
      (due slots) + 2 * (new slots) attempts.
  G1  read_grading_sheet(render_grading_sheet(entries)) asks for nothing.
  G2  Each entry is one read line, "<grade word> <attempt id> ...";
      everything else in the sheet is a comment or blank.
  G3  read_grading_sheet never raises; problems stop the whole sheet.
  G4  Changing one entry's word gives exactly one amend or one suspend; an
      automatic grade cannot be changed back to ?.
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


# --- rounds and the grading sheet (PLAN.md D45) --------------------------------


class RoundState(TypedDict):
    round_number: int  # the round in progress, or the last one when none follows
    round_item_ids: list[str]  # the items of that round, in plan order
    unanswered_item_ids: list[str]  # its items with no attempt in it yet, in order


def session_rounds(plan: list[PlanSlot], session_events: list[Event]) -> RoundState:
    """Where a session stands, in rounds (PLAN.md D45, D31, D36; R1-R4).

    PRE   plan came from plan_session for this session; session_events are
          the events this session wrote.
    POST  the first round that still has an unanswered item, with those
          items; or, when every round so far is answered and none follows,
          the last round with no unanswered items. Whether that last round
          has been graded is the caller's to know: grades arrive by amend
          after the round's answers, and an ungraded answer ends the item's
          session (R3).
    """
    effective = effective_events(session_events)
    # R1: an item's k-th effective attempt is its round-k answer.
    attempt_ratings_by_item: dict[str, list[int | None]] = {}
    suspended_item_ids: set[str] = set()
    for event in effective["ordered_events"]:
        if event["id"] in effective["undone_event_ids"]:
            continue
        if event["kind"] == "suspend":
            suspended_item_ids.add(event["item"])
        elif event["kind"] == "attempt":
            attempt_ratings_by_item.setdefault(event["item"], []).append(
                effective["amended_ratings"].get(event["id"], event["rating"])
            )
    new_item_ids = {slot["item_id"] for slot in plan if slot["reason"] == "new"}

    round_number = 1
    round_item_ids: list[str] = []
    for slot in plan:
        if slot["item_id"] not in round_item_ids:
            round_item_ids.append(slot["item_id"])
    while True:
        unanswered_item_ids = [
            item_id for item_id in round_item_ids if len(attempt_ratings_by_item.get(item_id, [])) < round_number
        ]
        if unanswered_item_ids != []:
            return {"round_number": round_number, "round_item_ids": round_item_ids, "unanswered_item_ids": unanswered_item_ids}
        next_round_item_ids: list[str] = []
        for item_id in round_item_ids:
            round_rating = attempt_ratings_by_item[item_id][round_number - 1]
            if item_id in suspended_item_ids or round_rating is None:
                continue  # R3: it waits for `rep review`, or was suspended
            # D36's criterion: a grade other than Again, and for a new item
            # not on its first showing (it must be recalled once after other
            # items came between).
            if round_rating == AGAIN or (item_id in new_item_ids and round_number == 1):
                next_round_item_ids.append(item_id)
        if next_round_item_ids == []:
            return {"round_number": round_number, "round_item_ids": round_item_ids, "unanswered_item_ids": []}
        round_number += 1
        round_item_ids = next_round_item_ids


class SheetEntry(TypedDict):
    attempt_id: str
    item_id: str
    rating: int | None  # the attempt's grade now: automatic for exact and numeric, else None
    path: str
    line: int
    question: str
    typed_answer: str | None
    answer: str | None
    criteria: list[str] | None


class SheetResult(TypedDict):
    amends: list[tuple[str, int]]  # (attempt id, new rating), in sheet order
    suspended_item_ids: list[str]
    problems: list[str]  # "line N: ..." for the person; when not empty, nothing is applied


GRADE_WORDS: dict[str, int | None] = {"again": AGAIN, "hard": 2, "good": 3, "easy": 4, "?": None}
SUSPEND_WORD = "suspend"


def render_grading_sheet(entries: list[SheetEntry], title: str) -> str:
    """The grading sheet for a round or for `rep review` (PLAN.md D41, D45; G1, G2).

    PRE   entries hold distinct attempt ids.
    POST  a text whose only read lines are one per entry, "<grade word>
          <attempt id> <question>"; everything else is a comment (#) or
          blank. The typed answer and the key are lined up below each entry
          for comparison, with the item's path:line for `gF`.
    """
    sheet_lines = [
        f"# {title}",
        "# Change the first word of an answer to: again, hard, good, easy;",
        "# ? leaves it for `rep review`; suspend stops the item. Save and quit to",
        "# apply; quit without saving (:cq) applies nothing. gF on a path opens the item.",
        "",
    ]
    for entry in entries:
        grade_word = "?"
        for word, rating in GRADE_WORDS.items():
            if rating is not None and rating == entry["rating"]:
                grade_word = word
        # Questions and keys may span lines; the read line must not.
        sheet_lines.append(f"{grade_word:<7} {entry['attempt_id']}  {' / '.join(entry['question'].splitlines())}")
        typed_answer = entry["typed_answer"]
        sheet_lines.append(f"#         typed:  {'(nothing typed)' if typed_answer is None or typed_answer.strip() == '' else typed_answer}")
        if entry["answer"] is not None:
            sheet_lines.append(f"#         key:    {' / '.join(entry['answer'].splitlines())}")
        for criterion in entry["criteria"] or []:
            sheet_lines.append(f"#         check:  {criterion}")
        sheet_lines.append(f"#         item:   {entry['path']}:{entry['line']}")
        sheet_lines.append("")
    return "\n".join(sheet_lines)


def read_grading_sheet(sheet_text: str, entries: list[SheetEntry]) -> SheetResult:
    """The changes a saved grading sheet asks for (PLAN.md D41, D45; G1, G3, G4).

    PRE   entries are those the sheet was rendered from.
    POST  never raises. With problems, no amends and no suspends: a sheet
          is applied whole or not at all. Without, one amend per entry whose
          word names a grade other than its current one, one suspend per
          `suspend` word; an entry whose line was deleted is left as it is.
    """
    entries_by_attempt_id = {entry["attempt_id"]: entry for entry in entries}
    amends: list[tuple[str, int]] = []
    suspended_item_ids: list[str] = []
    problems: list[str] = []
    seen_attempt_ids: set[str] = set()
    for line_index, sheet_line in enumerate(sheet_text.split("\n")):
        line_number = line_index + 1
        words = sheet_line.split()
        if words == [] or words[0].startswith("#"):
            continue
        grade_word = words[0].lower()
        if len(words) < 2 or words[1] not in entries_by_attempt_id:
            problems.append(f"line {line_number}: no answer of this sheet is named here (the second word is its id)")
            continue
        attempt_id = words[1]
        if attempt_id in seen_attempt_ids:
            problems.append(f"line {line_number}: answer {attempt_id} appears twice")
            continue
        seen_attempt_ids.add(attempt_id)
        entry = entries_by_attempt_id[attempt_id]
        if grade_word == SUSPEND_WORD:
            suspended_item_ids.append(entry["item_id"])
            continue
        if grade_word not in GRADE_WORDS:
            problems.append(f"line {line_number}: '{words[0]}' is not a grade (again, hard, good, easy, ?, suspend)")
            continue
        new_rating = GRADE_WORDS[grade_word]
        if new_rating is None:
            if entry["rating"] is not None:
                # G4: an amend needs a grade (events.py E1), so a grade
                # rep wrote cannot be taken back to "no grade".
                problems.append(f"line {line_number}: an automatic grade cannot go back to ?; write again or good")
            continue
        if new_rating != entry["rating"]:
            amends.append((attempt_id, new_rating))
    if problems != []:
        return {"amends": [], "suspended_item_ids": [], "problems": problems}
    return {"amends": amends, "suspended_item_ids": suspended_item_ids, "problems": []}
