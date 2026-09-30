"""Event records (one JSON object per line) and the fold that turns them into item states.

REPRESENTATION
  Event: one of the TypedDicts below, discriminated by "kind". Records are
  plain JSON-native dicts (strings, ints, None), so a line decodes into a
  record with no conversion step. Common fields on every event:
    format_version   EVENT_FORMAT_VERSION (PLAN.md I11)
    id               EVENT_ID_LENGTH characters of the device-id alphabet
    at               canonical UTC time, "YYYY-MM-DDTHH:MM:SS.ffffffZ"; fixed
                     width, so string order is time order
    device           the writing device's id (machine.DEVICE_ID_PATTERN)
    kind             which record this is
  Kinds in M1 are the ones the fold reads. session_start, session_end and
  item_stamped (PLAN.md D10) are added with their writers in M2 and M3.

  ItemState: what the fold knows about one item. FoldResult: every item's
  state plus problems found, as data.

INVARIANTS
  E1  decode_event accepts a line only if every field has its declared type
      and range; encode_event(decode_event(line)) is canonical and
      decode_event(encode_event(event)) == event.
  E2  fold_events is order-independent: it sorts by (at, id) itself.
  E3  An undone event has no effect; the fold result equals the result
      without that event and without its undo.
  E4  An amended attempt is replayed with the amended rating, at the time the
      attempt happened; the latest amend wins.
  E5  An attempt whose effective rating is None (ungraded) changes no memory.
  E6  Due dates are deterministic: fuzz comes from a hash of the item id and
      its graded review index, never from a random number generator.
"""

import hashlib
import json
import re
from datetime import UTC, datetime, timedelta
from typing import Literal, TypedDict, cast

from rep.machine import DEVICE_ID_ALPHABET, DEVICE_ID_PATTERN
from rep.memory_model import (
    AGAIN,
    DEFAULT_DESIRED_RETENTION,
    DEFAULT_MAXIMUM_INTERVAL_DAYS,
    DEFAULT_PARAMETERS,
    EASY,
    MemoryState,
    first_review,
    fuzzed_interval_days,
    next_interval_days,
    next_review,
)

EVENT_FORMAT_VERSION = 1
# 12 characters of a 32-character alphabet = 60 bits: at a million events the
# chance of any collision is below 1 in a million.
EVENT_ID_LENGTH = 12
EVENT_ID_PATTERN = re.compile(r"^[" + DEVICE_ID_ALPHABET + r"]{12}$")
CANONICAL_TIME_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}\.\d{6}Z$")


class EventDecodeError(Exception):
    """A line that is not a valid event. The message says which field and why."""


class AttemptEvent(TypedDict):
    format_version: int
    id: str
    at: str
    device: str
    kind: Literal["attempt"]
    session: str
    item: str
    rating: int | None  # None: answered "?", graded later by an amend
    latency_milliseconds: int  # prompt shown to answer committed
    typed_answer: str | None  # None unless the item asks for a typed attempt
    fingerprint: str  # hash of the item text, to detect edits since review


class AmendEvent(TypedDict):
    format_version: int
    id: str
    at: str
    device: str
    kind: Literal["amend"]
    target: str  # id of an attempt event
    rating: int


class UndoEvent(TypedDict):
    format_version: int
    id: str
    at: str
    device: str
    kind: Literal["undo"]
    target: str  # id of any event except another undo


class SuspendEvent(TypedDict):
    format_version: int
    id: str
    at: str
    device: str
    kind: Literal["suspend"]
    item: str


# A separate record, not kind: Literal["suspend", "unsuspend"]: one literal
# per kind lets the checker narrow an Event from a single comparison.
class UnsuspendEvent(TypedDict):
    format_version: int
    id: str
    at: str
    device: str
    kind: Literal["unsuspend"]
    item: str


Event = AttemptEvent | AmendEvent | UndoEvent | SuspendEvent | UnsuspendEvent


class ItemState(TypedDict):
    item: str
    memory: MemoryState | None  # None until the first graded review
    last_review_at: str | None  # canonical UTC time of the last graded review
    scheduled_interval_days: int | None  # before fuzz
    due_at: str | None  # canonical UTC time; last review plus fuzzed interval
    graded_review_count: int
    lapse_count: int  # Again on an item that already had a memory state
    suspended: bool


class FoldResult(TypedDict):
    items: dict[str, ItemState]
    problems: list[str]


def format_canonical_time(moment: datetime) -> str:
    """PRE moment is timezone-aware. POST a string matching CANONICAL_TIME_PATTERN."""
    assert moment.tzinfo is not None, "naive datetime has no defined UTC time"
    # isoformat, not strftime("%Y"): glibc's strftime writes year 999 as "999",
    # which breaks the fixed width that makes string order equal time order.
    canonical_text = (
        moment.astimezone(UTC).isoformat(timespec="microseconds").replace("+00:00", "Z")
    )
    assert CANONICAL_TIME_PATTERN.match(canonical_text), f"formatter broke: {canonical_text!r}"
    return canonical_text


def parse_canonical_time(text: str) -> datetime:
    """PRE text matches CANONICAL_TIME_PATTERN. POST a UTC-aware datetime."""
    assert CANONICAL_TIME_PATTERN.match(text), f"not a canonical time: {text!r}"
    return datetime.fromisoformat(text)


def encode_event(event: Event) -> str:
    """One line of JSON, without the newline. Keys sorted so equal events are equal text.

    PRE   event was built by this program or returned by decode_event.
    POST  decode_event(result) == event (E1).
    """
    assert event["format_version"] == EVENT_FORMAT_VERSION, "refusing to write an unversioned event"
    # ensure_ascii=False keeps typed answers readable in the file (UTF-8);
    # json.dumps escapes newlines inside strings, so the result is one line.
    return json.dumps(event, ensure_ascii=False, separators=(",", ":"), sort_keys=True)


def decode_event(line: str) -> Event:
    """Parse and validate one line. The only way an event enters the program.

    PRE   line is one line of an events file, with or without its newline.
    POST  a record satisfying E1, or EventDecodeError naming the problem.
          Fields this version does not know are dropped, so a newer writer's
          additions do not break an older reader.
    """
    try:
        raw: object = json.loads(line)
    except json.JSONDecodeError as decode_error:
        raise EventDecodeError(f"not JSON: {decode_error}") from decode_error
    if not isinstance(raw, dict):
        raise EventDecodeError("not a JSON object")
    # JSON object keys are always strings; the cast only tells the checker.
    fields = cast(dict[str, object], raw)

    # type(...) is int, not isinstance: bool is a subclass of int, and a
    # true/false in a numeric field is a writer bug to reject, not to coerce.
    format_version = fields.get("format_version")
    if type(format_version) is not int or format_version != EVENT_FORMAT_VERSION:
        raise EventDecodeError(
            f"format_version must be {EVENT_FORMAT_VERSION}, found {format_version!r}"
        )
    event_id = fields.get("id")
    if not isinstance(event_id, str) or EVENT_ID_PATTERN.match(event_id) is None:
        raise EventDecodeError(f"id must be {EVENT_ID_LENGTH} id-alphabet characters, found {event_id!r}")
    at = fields.get("at")
    if not isinstance(at, str) or CANONICAL_TIME_PATTERN.match(at) is None:
        raise EventDecodeError(f"at must be canonical UTC time, found {at!r}")
    try:
        parse_canonical_time(at)
    except ValueError as time_error:
        raise EventDecodeError(f"at is not a real time: {at!r}") from time_error
    device = fields.get("device")
    if not isinstance(device, str) or DEVICE_ID_PATTERN.match(device) is None:
        raise EventDecodeError(f"device must be a device id, found {device!r}")
    kind = fields.get("kind")

    if kind == "attempt":
        session = fields.get("session")
        item = fields.get("item")
        rating = fields.get("rating")
        latency_milliseconds = fields.get("latency_milliseconds")
        typed_answer = fields.get("typed_answer")
        fingerprint = fields.get("fingerprint")
        if not isinstance(session, str) or session == "":
            raise EventDecodeError("attempt.session must be a non-empty string")
        # The item id format belongs to the library grammar (M2); here only
        # its presence is checked.
        if not isinstance(item, str) or item == "":
            raise EventDecodeError("attempt.item must be a non-empty string")
        if rating is not None and (type(rating) is not int or not AGAIN <= rating <= EASY):
            raise EventDecodeError(f"attempt.rating must be 1..4 or null, found {rating!r}")
        if type(latency_milliseconds) is not int or latency_milliseconds < 0:
            raise EventDecodeError(
                f"attempt.latency_milliseconds must be a non-negative integer, found {latency_milliseconds!r}"
            )
        if typed_answer is not None and not isinstance(typed_answer, str):
            raise EventDecodeError("attempt.typed_answer must be a string or null")
        if not isinstance(fingerprint, str) or fingerprint == "":
            raise EventDecodeError("attempt.fingerprint must be a non-empty string")
        attempt_event: AttemptEvent = {
            "format_version": format_version,
            "id": event_id,
            "at": at,
            "device": device,
            "kind": "attempt",
            "session": session,
            "item": item,
            "rating": rating,
            "latency_milliseconds": latency_milliseconds,
            "typed_answer": typed_answer,
            "fingerprint": fingerprint,
        }
        return attempt_event

    if kind == "amend":
        target = fields.get("target")
        rating = fields.get("rating")
        if not isinstance(target, str) or EVENT_ID_PATTERN.match(target) is None:
            raise EventDecodeError(f"amend.target must be an event id, found {target!r}")
        if type(rating) is not int or not AGAIN <= rating <= EASY:
            raise EventDecodeError(f"amend.rating must be 1..4, found {rating!r}")
        amend_event: AmendEvent = {
            "format_version": format_version,
            "id": event_id,
            "at": at,
            "device": device,
            "kind": "amend",
            "target": target,
            "rating": rating,
        }
        return amend_event

    if kind == "undo":
        target = fields.get("target")
        if not isinstance(target, str) or EVENT_ID_PATTERN.match(target) is None:
            raise EventDecodeError(f"undo.target must be an event id, found {target!r}")
        undo_event: UndoEvent = {
            "format_version": format_version,
            "id": event_id,
            "at": at,
            "device": device,
            "kind": "undo",
            "target": target,
        }
        return undo_event

    if kind == "suspend" or kind == "unsuspend":
        item = fields.get("item")
        if not isinstance(item, str) or item == "":
            raise EventDecodeError(f"{kind}.item must be a non-empty string")
        if kind == "suspend":
            suspend_event: SuspendEvent = {
                "format_version": format_version,
                "id": event_id,
                "at": at,
                "device": device,
                "kind": "suspend",
                "item": item,
            }
            return suspend_event
        unsuspend_event: UnsuspendEvent = {
            "format_version": format_version,
            "id": event_id,
            "at": at,
            "device": device,
            "kind": "unsuspend",
            "item": item,
        }
        return unsuspend_event

    raise EventDecodeError(f"unknown kind {kind!r}")


def fold_events(
    events: list[Event],
    parameters: tuple[float, ...] = DEFAULT_PARAMETERS,
    desired_retention: float = DEFAULT_DESIRED_RETENTION,
    maximum_interval_days: int = DEFAULT_MAXIMUM_INTERVAL_DAYS,
) -> FoldResult:
    """Replay every event and return each item's state (E2-E6).

    PRE   every event came from decode_event or satisfies E1.
    POST  result.items holds every item mentioned by an effective (not undone)
          attempt, suspend or unsuspend; result.problems lists references
          the fold had to ignore, each naming the event id.
    """
    problems: list[str] = []

    # E2: a total order independent of input order and of which device file
    # an event came from. Canonical times sort correctly as strings; the id
    # breaks ties between events written in the same microsecond.
    ordered_events = sorted(events, key=lambda event: (event["at"], event["id"]))
    events_by_id: dict[str, Event] = {}
    for event in ordered_events:
        if event["id"] in events_by_id:
            problems.append(f"event {event['id']}: duplicate id, later copy ignored")
            continue
        events_by_id[event["id"]] = event

    # E3: undo removes its target. An undo of an undo is refused: allowing it
    # would make "is this event in effect" depend on a chain of undos, and
    # the session never needs redo.
    undone_event_ids: set[str] = set()
    for event in events_by_id.values():
        if event["kind"] != "undo":
            continue
        target_event = events_by_id.get(event["target"])
        if target_event is None:
            problems.append(f"event {event['id']}: undo targets unknown event {event['target']}")
        elif target_event["kind"] == "undo":
            problems.append(f"event {event['id']}: undo of an undo is not allowed, ignored")
        else:
            undone_event_ids.add(event["target"])

    # E4: the latest effective amend of an effective attempt sets its rating.
    # events_by_id preserves the sorted order, so a later amend overwrites.
    amended_ratings: dict[str, int] = {}
    for event in events_by_id.values():
        if event["kind"] != "amend" or event["id"] in undone_event_ids:
            continue
        target_event = events_by_id.get(event["target"])
        if target_event is None or target_event["kind"] != "attempt":
            problems.append(f"event {event['id']}: amend target {event['target']} is not an attempt")
        elif event["target"] in undone_event_ids:
            problems.append(f"event {event['id']}: amend target {event['target']} was undone")
        else:
            amended_ratings[event["target"]] = event["rating"]

    items: dict[str, ItemState] = {}
    for event in events_by_id.values():
        # Undo and amend were consumed above; undone events never touch state.
        if event["id"] in undone_event_ids or event["kind"] == "undo" or event["kind"] == "amend":
            continue
        item_state = items.get(event["item"])
        if item_state is None:
            new_item_state: ItemState = {
                "item": event["item"],
                "memory": None,
                "last_review_at": None,
                "scheduled_interval_days": None,
                "due_at": None,
                "graded_review_count": 0,
                "lapse_count": 0,
                "suspended": False,
            }
            items[event["item"]] = new_item_state
            item_state = new_item_state
        if event["kind"] == "suspend" or event["kind"] == "unsuspend":
            item_state["suspended"] = event["kind"] == "suspend"
            continue

        effective_rating = amended_ratings.get(event["id"], event["rating"])
        if effective_rating is None:
            continue  # E5

        reviewed_at = parse_canonical_time(event["at"])
        previous_memory = item_state["memory"]
        previous_review_at = item_state["last_review_at"]
        if previous_memory is None or previous_review_at is None:
            new_memory = first_review(effective_rating, parameters)
        else:
            # timedelta.days floors, exactly as py-fsrs measures elapsed days;
            # the sort guarantees the difference is not negative.
            elapsed_whole_days = (reviewed_at - parse_canonical_time(previous_review_at)).days
            new_memory = next_review(previous_memory, effective_rating, elapsed_whole_days, parameters)
            if effective_rating == AGAIN:
                item_state["lapse_count"] += 1

        interval_days = next_interval_days(
            new_memory["stability"], desired_retention, maximum_interval_days, parameters
        )
        # E6: the fraction comes from the item and how many graded reviews it
        # had before this one, so replay reproduces every due date.
        fuzz_digest = hashlib.sha256(
            f"{event['item']}\n{item_state['graded_review_count']}".encode()
        ).digest()
        fuzz_fraction = int.from_bytes(fuzz_digest[:8], "big") / 2**64
        due_days = fuzzed_interval_days(interval_days, fuzz_fraction, maximum_interval_days)

        item_state["memory"] = new_memory
        item_state["last_review_at"] = event["at"]
        item_state["scheduled_interval_days"] = interval_days
        item_state["due_at"] = format_canonical_time(reviewed_at + timedelta(days=due_days))
        item_state["graded_review_count"] += 1

    return {"items": items, "problems": problems}
