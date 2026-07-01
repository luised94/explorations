"""HTTP layer -- Bottle request/response glue (D4 extraction), module http_layer.

Named http_layer (not http) because a top-level http.py shadows the stdlib http
package that bottle imports (http.client) -- the findings' S4 prototype used this
name for the same reason.

Thin route handlers over the DATABASE and LOGIC layers: each parses the request,
calls down the stack, and formats the JSON response. No business logic lives
here -- an if-statement that is not about request parsing or response formatting
belongs in LOGIC. HTTP is the top data-flow layer (config <- db <- logic <-
http); nothing imports http except main, which wires it. It is the only layer
that reads the clock (per-request timestamps handed to the DB writes).

D4a lands the request-helper preamble only -- the stateless parsing/error
helpers (_json_error, _integrity_message, _request_json, _BadParameter,
_require_int, _optional_int), which have zero coupling to the app object or the
DATABASE_PATH global. The app object, DATABASE_PATH, and the route handlers move
here in D4b as one coherent unit (they share the mutable DATABASE_PATH that main
rebinds at startup, so they relocate together to keep that binding in one file).

Behavior-preserving: every symbol is identical to its pre-split definition.
"""

from __future__ import annotations

import sqlite3

import bottle


def _json_error(message: str, status: int = 400) -> dict:
    """Set the response status and return the standard error body.

    The error envelope is {"error": message} with the given HTTP status, per
    spec section 6. Returning the dict lets Bottle serialize it as JSON while
    the status is applied as a side effect on the response object.
    """
    bottle.response.status = status
    return {"error": message}


def _integrity_message(error: sqlite3.IntegrityError) -> str:
    """Translate a SQLite IntegrityError into a user-facing 400 message.

    The common cause in this app is a foreign-key violation: a request
    references a category, bank, session, or question id that does not exist
    (or was deleted in another browser tab between being served and being
    answered -- a real time-gradient case for a single user with multiple
    tabs open). The raw SQLite text is terse; this gives a clearer hint
    without leaking schema internals.
    """
    raw = str(error).lower()
    if "foreign key" in raw:
        return (
            "request references an id that does not exist "
            "(it may have been deleted in another tab)"
        )
    return "the request conflicts with the database state: " + str(error)


def _request_json() -> dict:
    """Return the parsed JSON body of the current request as a dict.

    Bottle's request.json is None when the body is absent or not JSON, and
    can be a non-dict (list, string, number) when the client sends valid JSON
    that is not an object. This helper normalizes both cases to an empty dict
    so handlers can use .get without a None check and without an
    AttributeError on a non-dict body. A client that sends a JSON array or
    scalar is treated as having sent no fields; required-field checks in the
    handler then produce the standard 400, rather than a 500 from .get on a
    list. Malformed JSON (not parseable at all) raises bottle.HTTPError 400
    inside bottle.request.json; handlers need not catch it -- Bottle renders
    it as a 400.
    """
    try:
        parsed = bottle.request.json
    except (ValueError, TypeError):
        # Body present but not parseable as JSON. Treat as no fields; the
        # handler's required-field check will return a descriptive 400.
        return {}
    if not isinstance(parsed, dict):
        return {}
    return parsed


class _BadParameter(Exception):
    """Internal signal that a request parameter failed integer parsing.

    Carries the 400-ready message. Used by _require_int / _optional_int so
    handlers can convert client-supplied strings to integers in one place
    with one consistent error shape, instead of scattering try/except int()
    (a previously unguarded path that turned bad input into 500s).
    """

    def __init__(self, message: str):
        super().__init__(message)
        self.message = message


def _require_int(value: object, field_name: str) -> int:
    """Parse a required value as an int, raising _BadParameter on failure.

    Accepts an int directly or a string of digits. None, empty string, or a
    non-integer string raises _BadParameter with a message naming the field,
    which the handler turns into a 400. This guards the JSON-body integer
    fields (session_id, category_id) that were previously passed straight to
    int() and could raise an unhandled ValueError -> 500.
    """
    if value is None or value == "":
        raise _BadParameter("missing required field: " + field_name)
    try:
        return int(value)
    except (ValueError, TypeError):
        raise _BadParameter(field_name + " must be an integer")


def _optional_int(value: object, field_name: str) -> int | None:
    """Parse an optional value as an int, or None when absent.

    None or empty string yields None. A present but non-integer value raises
    _BadParameter (named) for a 400. Used for optional body fields such as
    bank_id and question_id so a malformed optional value is reported
    cleanly rather than crashing a later int() or DB insert.
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        raise _BadParameter(field_name + " must be an integer")
