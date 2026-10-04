"""A session's plan and its rounds, and the grading sheet, as pure functions
(PLAN.md D9, D31, D36, D37, D39, D41, D45).

REPRESENTATION
  Preset         the session settings (D39), one constant for now; each
                 session_start event records a copy (D40).
  LocatedItem    a checked library Item with the path of its file
                 (library.py), from check_library_files: no item with an
                 error, no id twice (D22, library.py L11).
  PlanSlot       one item id and why it is in the plan: "due" or "new".
  Plan           the ordered slots a session starts with: reviews, then new
                 items. A pure function of the library, the fold's states,
                 the events (for capture times only), the scheduling day and
                 the preset.
  RoundState     the round in progress: its number, its items, those not yet
                 answered in it, and the attempts that answered it so far.
                 Recomputed from the plan and the session's own events after
                 every write (D31): there is no mutable queue, a correction
                 is an event, and replaying the events gives the rounds.
  SheetEntry     one answer as the grading sheet shows it: the attempt, its
                 grade now, the item's place, question, key, what was typed,
                 and whether the item changed since. SheetResult: the amends
                 and suspends a saved sheet asks for, or the problems that
                 stop it.

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
  R1  session_rounds is pure and order-independent in the session's events;
      an item's k-th effective attempt in the session is its round-k answer.
  R2  Round 1 is the plan's items in plan order; round r+1 is the items of
      round r, in R6's order, that did not meet D36's criterion in round r
      (a grade other than Again, and not a new item's first showing) and
      did not leave.
  R3  An item leaves after round r when its round-r answer is ungraded (it
      waits for `rep review`) or when it was suspended.
  R4  If every answer is graded Good, the session takes exactly
      (due slots) + 2 * (new slots) attempts.
  R6  Round 1 is in plan order (P3: a session cut short loses the least;
      D37: a reading's new items in reading order). A later round shows
      its items ordered by sha256 of (session id, round number, item id):
      a different order in every session and round, the same on every
      replay, on any Python version (PLAN.md D48).
  R5  session_rounds never computes a round past through_round: round r+1
      is decided by round r's grades, which exist only once the round's
      sheet has been saved, and nothing in the events says when that was
      (a sheet saved unchanged writes nothing). The caller passes the last
      round it graded plus one.
  G1  read_grading_sheet(render_grading_sheet(entries)) asks for nothing.
  G2  Each entry is one read line, "<grade word> <attempt id> ...";
      everything else in the sheet is a comment or blank.
  G3  read_grading_sheet never raises; problems stop the whole sheet.
  G4  Changing one entry's word gives exactly one amend; `suspend` gives one
      suspend per item, however many of its answers say it; an automatic
      grade cannot be changed back to ?.
  G5  A sheet entry shows the grade in effect (amends applied) and flags an
      item whose fingerprint differs from the one its attempt recorded
      (D20 constraint 2: the key shown may not be the key answered).
  V1  review_attempt_ids lists, once each and in history order, the
      effective attempts of this device's last session, then every other
      effective attempt still without a grade.
"""

import hashlib
from datetime import date
from typing import Literal, TypedDict

from rep.events import AttemptEvent, Event, ItemState, effective_events
from rep.library import LocatedItem, item_fingerprint
from rep.memory_model import AGAIN, DEFAULT_PARAMETERS, retrievability


class Preset(TypedDict):
    session_budget: int  # most attempts the plan serves before the retry rounds
    new_per_day: int
    new_item_cost: int  # budget one new item uses: its showing, its return, a miss
    day_start_hour: int  # local hour a scheduling day starts (D44)
    desired_retention: float


# PLAN.md D36, D39. Approved numbers (relearn_gap retired by D45: the rest of
# a round is the gap). A constant, not config.toml: tuning is an edit and a
# commit, and session_start records the values used.
DEFAULT_PRESET: Preset = {
    "session_budget": 60,
    "new_per_day": 10,
    "new_item_cost": 3,
    "day_start_hour": 4,
    "desired_retention": 0.9,
}


class PlanSlot(TypedDict):
    item_id: str
    reason: Literal["due", "new", "drill"]  # drill: chosen by the person, seen before (D50)


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


# --- rounds and the grading sheet (PLAN.md D45) --------------------------------


class RoundState(TypedDict):
    round_number: int  # the round in progress, or the last one when none follows
    round_item_ids: list[str]  # the items of that round, in plan order
    unanswered_item_ids: list[str]  # its items with no attempt in it yet, in order
    round_attempt_ids: list[str]  # the attempts that answered it so far, in round order


def session_rounds(
    plan: list[PlanSlot], session_events: list[Event], through_round: int, session_id: str
) -> RoundState:
    """Where a session stands, in rounds (PLAN.md D45, D31, D36, D48; R1-R6).

    PRE   plan came from plan_session for this session; session_events are
          the events this session wrote; through_round >= 1; session_id is
          its session_start's id.
    POST  the first round up to through_round that still has an unanswered
          item, with those items; else, with no unanswered items, round
          through_round, or the last round when no round follows an earlier
          one. A caller that passes (rounds graded) + 1 thus sees a round
          that is answered and not yet graded as such, never the round its
          ungraded answers would imply (R5).
    """
    effective = effective_events(session_events)
    # R1: an item's k-th effective attempt is its round-k answer.
    attempts_by_item: dict[str, list[tuple[str, int | None]]] = {}
    suspended_item_ids: set[str] = set()
    for event in effective["ordered_events"]:
        if event["id"] in effective["undone_event_ids"]:
            continue
        if event["kind"] == "suspend":
            suspended_item_ids.add(event["item"])
        elif event["kind"] == "attempt":
            attempts_by_item.setdefault(event["item"], []).append(
                (event["id"], effective["amended_ratings"].get(event["id"], event["rating"]))
            )
    new_item_ids = {slot["item_id"] for slot in plan if slot["reason"] == "new"}

    round_number = 1
    round_item_ids: list[str] = []
    for slot in plan:
        if slot["item_id"] not in round_item_ids:
            round_item_ids.append(slot["item_id"])
    while True:
        unanswered_item_ids = [
            item_id for item_id in round_item_ids if len(attempts_by_item.get(item_id, [])) < round_number
        ]
        round_attempt_ids = [
            attempts_by_item[item_id][round_number - 1][0]
            for item_id in round_item_ids
            if item_id not in unanswered_item_ids
        ]
        if unanswered_item_ids != [] or round_number == through_round:
            return {
                "round_number": round_number, "round_item_ids": round_item_ids,
                "unanswered_item_ids": unanswered_item_ids, "round_attempt_ids": round_attempt_ids,
            }  # fmt: skip
        next_round_item_ids: list[str] = []
        for item_id in round_item_ids:
            round_rating = attempts_by_item[item_id][round_number - 1][1]
            if item_id in suspended_item_ids or round_rating is None:
                continue  # R3: it waits for `rep review`, or was suspended
            # D36's criterion: a grade other than Again, and for a new item
            # not on its first showing (it must be recalled once after other
            # items came between).
            if round_rating == AGAIN or (item_id in new_item_ids and round_number == 1):
                next_round_item_ids.append(item_id)
        if next_round_item_ids == []:
            return {
                "round_number": round_number, "round_item_ids": round_item_ids,
                "unanswered_item_ids": [], "round_attempt_ids": round_attempt_ids,
            }  # fmt: skip
        # R6: random.shuffle is not promised to give the same order on
        # another Python version; a hash is, so a replay years later agrees.
        next_round_item_ids.sort(
            key=lambda item_id: hashlib.sha256(f"{session_id}\n{round_number + 1}\n{item_id}".encode()).digest()
        )
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
    key_changed: bool  # the item's fingerprint now differs from the attempt's (G5)


class SheetResult(TypedDict):
    amends: list[tuple[str, int]]  # (attempt id, new rating), in sheet order
    suspended_item_ids: list[str]
    # (line number, message): the shell shows each above its line. When not
    # empty, nothing is applied.
    problems: list[tuple[int, str]]


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
        # An answer written in $EDITOR (Esc v, PLAN.md D47) or a block key
        # spans lines: each gets its own comment line, indented under the
        # first, so code keeps its shape and no line becomes a read line (G2).
        typed_answer = entry["typed_answer"]
        typed_lines = ["(nothing typed)"] if typed_answer is None or typed_answer.strip() == "" else typed_answer.split("\n")
        sheet_lines.append(f"#         typed:  {typed_lines[0]}")
        sheet_lines.extend(f"#                 {typed_line}" for typed_line in typed_lines[1:])
        if entry["answer"] is not None:
            key_lines = entry["answer"].split("\n")
            sheet_lines.append(f"#         key:    {key_lines[0]}")
            sheet_lines.extend(f"#                 {key_line}" for key_line in key_lines[1:])
        for criterion in entry["criteria"] or []:
            sheet_lines.append(f"#         check:  {criterion}")
        sheet_lines.append(f"#         item:   {entry['path']}:{entry['line']}")
        if entry["key_changed"]:
            sheet_lines.append("#         note:   the item changed after this answer; the key above is today's")
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
    problems: list[tuple[int, str]] = []
    seen_attempt_ids: set[str] = set()
    for line_index, sheet_line in enumerate(sheet_text.split("\n")):
        line_number = line_index + 1
        words = sheet_line.split()
        if words == [] or words[0].startswith("#"):
            continue
        grade_word = words[0].lower()
        if len(words) < 2 or words[1] not in entries_by_attempt_id:
            problems.append((line_number, "no answer of this sheet is named here (the second word is its id)"))
            continue
        attempt_id = words[1]
        if attempt_id in seen_attempt_ids:
            problems.append((line_number, f"answer {attempt_id} appears twice"))
            continue
        seen_attempt_ids.add(attempt_id)
        entry = entries_by_attempt_id[attempt_id]
        if grade_word == SUSPEND_WORD:
            # G4: `rep review` can list two answers of one item.
            if entry["item_id"] not in suspended_item_ids:
                suspended_item_ids.append(entry["item_id"])
            continue
        if grade_word not in GRADE_WORDS:
            problems.append((line_number, f"'{words[0]}' is not a grade (again, hard, good, easy, ?, suspend)"))
            continue
        new_rating = GRADE_WORDS[grade_word]
        if new_rating is None:
            if entry["rating"] is not None:
                # G4: an amend needs a grade (events.py E1), so a grade
                # rep wrote cannot be taken back to "no grade".
                problems.append((line_number, "an automatic grade cannot go back to ?; write again or good"))
            continue
        if new_rating != entry["rating"]:
            amends.append((attempt_id, new_rating))
    if problems != []:
        return {"amends": [], "suspended_item_ids": [], "problems": problems}
    return {"amends": amends, "suspended_item_ids": suspended_item_ids, "problems": []}


def grading_sheet_entries(
    events: list[Event], attempt_ids: list[str], located_items_by_id: dict[str, LocatedItem]
) -> list[SheetEntry]:
    """The sheet entries for some attempts, as the history stands (PLAN.md D41, D45; G5).

    PRE   every id in attempt_ids is an effective attempt in events.
    POST  one entry per attempt, in the order given, except attempts whose
          item is in no library file (lint reports those, I2): with no key
          there is nothing to grade against. The rating is the one in
          effect, amends applied.
    """
    effective = effective_events(events)
    attempts_by_id: dict[str, AttemptEvent] = {
        event["id"]: event for event in effective["ordered_events"] if event["kind"] == "attempt"
    }
    entries: list[SheetEntry] = []
    for attempt_id in attempt_ids:
        attempt = attempts_by_id[attempt_id]
        located_item = located_items_by_id.get(attempt["item"])
        if located_item is None:
            continue
        item = located_item["item"]
        entries.append(
            {
                "attempt_id": attempt_id,
                "item_id": item["id"],
                "rating": effective["amended_ratings"].get(attempt_id, attempt["rating"]),
                "path": located_item["path"],
                "line": item["line"],
                "question": item["question"],
                "typed_answer": attempt["typed_answer"],
                "answer": item["answer"],
                "criteria": item["criteria"],
                # PLAN.md D33: stored on the attempt, never recomputed; a
                # mismatch means the key on the sheet is not the one answered.
                "key_changed": attempt["fingerprint"] != item_fingerprint(item),
            }
        )
    return entries


def review_attempt_ids(events: list[Event], device_id: str) -> list[str]:
    """The attempts `rep review` shows (PLAN.md D41; V1).

    PRE   events is the whole history.
    POST  the effective attempts of the last session this device started,
          graded or not, so a slip can be corrected; then every other
          effective attempt with no grade in effect, from any session or
          device, so none is left ungraded for good. History order.
    """
    effective = effective_events(events)
    last_session_id: str | None = None
    for event in effective["ordered_events"]:
        if event["kind"] == "session_start" and event["device"] == device_id:
            last_session_id = event["id"]
    last_session_attempt_ids: list[str] = []
    ungraded_attempt_ids: list[str] = []
    for event in effective["ordered_events"]:
        if event["kind"] != "attempt" or event["id"] in effective["undone_event_ids"]:
            continue
        if event["session"] == last_session_id:
            last_session_attempt_ids.append(event["id"])
        elif effective["amended_ratings"].get(event["id"], event["rating"]) is None:
            ungraded_attempt_ids.append(event["id"])
    return last_session_attempt_ids + ungraded_attempt_ids
