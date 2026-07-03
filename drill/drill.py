"""Drill -- a local, single-user practice tool with cross-session tracking.

This module is the entire backend. It is organized into clearly separated
sections that follow a data-oriented procedural style:

    CONFIG    -- constants and scalar configuration; no callables
    DATABASE  -- functions over a sqlite3.Connection; IO only, no logic
    LOGIC     -- pure functions; no IO, no DB, no HTTP
    HTTP      -- thin Bottle route handlers
    MAIN      -- server startup (added with C-013a)

Boundary invariant (spec section 5): DATABASE never calls LOGIC or HTTP;
LOGIC never calls DATABASE or HTTP; HTTP calls both. Data crosses
boundaries as plain dicts, lists, strings, and numbers.

Status: backend complete through C-019a. Every API endpoint in spec section 6
is implemented, including GET /api/stats (C-019a): the DATABASE stats reader
(get_responses_for_stats), the pure LOGIC summary (summarize_stats), and the
handler that computes the day-window cutoff and returns the summary. The
frontend (index.html) is built in C-013 onward; the stats VIEW that consumes
this endpoint is C-019b.

C-018b note: build_question_payload and the bank-question handler carry a
comment-block scaffold for the deferred per-question-language TTS path; that
remains comment-only (no executable backend code from C-018b).

Error-handling contract for the HTTP layer: handlers return the standard
{"error": message} envelope with a 4xx status for bad input (missing or
non-integer fields, malformed uploads) and for database integrity conflicts
(referencing an id that does not exist, e.g. a row deleted in another open
tab). Pure LOGIC functions raise ValueError on violated preconditions, which
indicate programming errors rather than user input and are intended to fail
loudly during development rather than emit silently wrong output.
"""

from __future__ import annotations

import os

from config import DEFAULT_DATABASE_PATH
from db import connect, init_db, run_migrations, utc_now_iso

# The full backend now lives in the layer modules: config.py (CONFIG leaf),
# db.py (DATABASE), logic.py (LOGIC), http_layer.py (HTTP). drill.py is the thin
# MAIN composition root -- it wires the request-path global and serves the app.
# http_layer is imported as a MODULE (not `from http_layer import app`) so main
# can rebind http_layer.DATABASE_PATH and have the route handlers -- which read
# that module global -- see the startup path. (Named http_layer, not http, to
# avoid shadowing the stdlib http package that bottle imports.)
import http_layer


# =============================================================================
# --- MAIN ---
#
# Server entry point. Pulled forward to C-013a (originally bundled with the
# C-019 stats work) so the app is runnable while the frontend is built.
#
# Spec section 5 (# --- MAIN ---) defines this block as exactly three things:
# the init_db call, bottle.run, and the __main__ guard. As of C-019a the stats
# endpoint (GET /api/stats) and its DB query are implemented in their proper
# sections above; the only remaining stats work is the frontend view (C-019b),
# which adds nothing here. This block stays the minimum that makes the app
# runnable end to end.
#
# This block is meant to be appended to the END of drill.py (after the
# /api/banks/import handler). It is kept in a separate file here only so the
# verification thread stays clean; reinject it into drill.py's MAIN section.
#
# Design notes:
#   - Runs the explicit `app` object (app.run), not bottle's module-global
#     default, matching how routes are attached.
#   - Rebinds the module global DATABASE_PATH before serving, because the
#     per-request handlers read that global (the spec says "MAIN may override
#     this at startup"). Overriding a local would not reach the handlers.
#   - init_db is idempotent (schema IF NOT EXISTS, version stamp once, seed
#     via INSERT OR IGNORE), so calling it on every startup is safe and is
#     what creates + seeds drill.db the first time -- no separate init step.
#   - No argparse/CLI flags (the spec does not specify any); host/port/db are
#     overridable via environment variables for convenience (notably under
#     WSL), defaulting to 127.0.0.1:8080 and the standard drill.db. Adds no
#     new dependencies (os is already imported).


def main() -> None:
    """Initialize the database and start the drill server.

    Reads optional overrides from the environment:
      DRILL_HOST  (default 127.0.0.1)
      DRILL_PORT  (default 8080)
      DRILL_DB    (default DEFAULT_DATABASE_PATH, i.e. drill.db)

    Calls init_db once at startup (creating and seeding the database on first
    run) and then serves the app. The database path is published to the module
    global DATABASE_PATH so the per-request handlers open the same file.
    """
    host = os.environ.get("DRILL_HOST", "127.0.0.1")
    database_path = os.environ.get("DRILL_DB", DEFAULT_DATABASE_PATH)

    port_raw = os.environ.get("DRILL_PORT", "8080")
    try:
        port = int(port_raw)
    except ValueError:
        raise SystemExit("DRILL_PORT must be an integer (got: " + repr(port_raw) + ")")

    # Publish the chosen path onto the HTTP module so its request handlers
    # (which read http_layer.DATABASE_PATH) open the same database this startup
    # initialized. Set on the module object, not a local, so the rebind is
    # visible in http_layer's namespace where the handlers resolve it.
    http_layer.DATABASE_PATH = database_path

    # Create the schema and seed categories if needed, then apply any pending
    # schema migrations. Reconciliation (decisions.md ADR): init_db stays the
    # version-1 baseline -- it builds today's schema and stamps v1 -- and the
    # migration runner layers versions 2..N on top. Both fresh and existing
    # databases reach the current version by this one path: a fresh DB is built
    # to v1 by init_db then advanced by the runner; an existing DB is left as-is
    # by init_db's IF NOT EXISTS / stamp-once and advanced from its current
    # version by the runner. With an empty MIGRATIONS (T2) the runner is a
    # no-op. Idempotent and safe on every startup. One connection here.
    #
    # The clock is read HERE (MAIN boundary) and injected into the runner, so
    # the DATABASE layer stays clock-free.
    connection = connect(database_path)
    try:
        init_db(connection)
        connection.commit()
        result = run_migrations(connection, utc_now_iso())
    finally:
        connection.close()

    # Operator-facing migration report: what ran and the resulting version.
    if result["applied"]:
        for version, description in result["applied"]:
            print("drill: applied migration " + str(version) + " (" + description + ")")
        print(
            "drill: schema migrated "
            + str(result["from_version"])
            + " -> "
            + str(result["to_version"])
        )
    else:
        print("drill: schema up to date (version " + str(result["to_version"]) + ")")

    # Friendly startup line so the operator knows the exact URL to open, plus a
    # short note on what to expect. The server is PASSIVE: at startup it only
    # initializes the DB, registers routes, and listens -- no application code
    # runs yet. The app "starts" on the CLIENT's timeline: opening the URL serves
    # index.html, which loads <script type="module" src="boot.js">; the browser
    # then fetches the module graph and calls boot(). So the lines below print
    # only once a browser connects -- silence here is normal, not a stall.
    # (Bottle also prints its own banner.)
    url = "http://" + host + ":" + str(port) + "/"
    print("drill: serving on " + url + " (database: " + database_path + ")")
    print("drill: ready and listening. The app runs when a browser opens the URL")
    print("drill:   -- it will fetch index.html, then the ES modules (boot.js and")
    print("drill:   its imports), then call boot(). Watch for 'serving module ...'")
    print("drill:   lines below once you connect; if you open the URL and see NO")
    print("drill:   such lines, the page could not load its scripts (check the")
    print("drill:   browser Network/Console tabs).")

    http_layer.app.run(host=host, port=port)


if __name__ == "__main__":
    main()
