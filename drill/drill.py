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
import subprocess
import sys
import tempfile
from datetime import date

from config import (
    DEFAULT_DATABASE_PATH,
    LEECH_THRESHOLD,
    NEW_QUESTIONS_PER_BANK_MINIMUM,
    NEW_QUESTIONS_PER_DAY_MAXIMUM,
    REVIEWS_PER_SESSION_MAXIMUM,
)
from db import (
    connect,
    get_elapsed_ms_samples,
    get_failure_rows,
    get_leech_rows,
    get_new_introduced_today_by_bank,
    get_schedule_for_bank,
    get_true_retention,
    get_upcoming_schedule_rows,
    init_db,
    insert_bank,
    insert_questions_bulk,
    list_banks,
    list_categories,
    list_questions,
    run_migrations,
    utc_now_iso,
)
from logic import (
    ImportParseError,
    apply_new_question_throttle,
    author_parse,
    author_template,
    dry_run_view,
    failures_view,
    leeches_view,
    partition_candidates_by_schedule,
    preview_view,
    stats_view,
    summarize_elapsed_percentiles,
)

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
#   - No flags on serve itself (C5 adds report SUBCOMMANDS, dispatched in
#     main() below, but serve stays flagless); host/port/db are
#     overridable via environment variables for convenience (notably under
#     WSL), defaulting to 127.0.0.1:8080 and the standard drill.db. Adds no
#     new dependencies (os is already imported).


def run_serve_command() -> None:
    """Initialize the database and start the drill server (the default and
    the pre-C5 sole behavior; `drill.py` and `drill.py serve` are identical).

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


# =============================================================================
# --- CLI subcommands (C5) ---
#
# Terminal measurement views over the review schedule and response log. Every
# report command has the same shape -- open the database, fetch plain rows
# through DATABASE readers, hand them to a pure LOGIC view, print the string
# -- so dispatch is a data table (REPORT_COMMANDS below) rather than argparse
# machinery: one dict entry per command, usage text generated from the same
# table, nothing else to keep in sync. `serve` is the one command that is not
# a report (it never returns), so it is dispatched before the table lookup.
# The database path comes from DRILL_DB exactly like serve; the day ordinal
# and the clock are read HERE (MAIN boundary) and passed down.


def open_reporting_connection(database_path: str):
    """Open the database for a report command through the same one path serve
    uses: init_db (idempotent) plus the migration runner, so a report against
    a fresh or older-version file works instead of failing on a missing
    table. Returns an open connection; the caller closes it."""
    connection = connect(database_path)
    init_db(connection)
    connection.commit()
    run_migrations(connection, utc_now_iso())
    return connection


def build_stats_report(database_path: str) -> str:
    """True retention (S1) and elapsed_ms percentiles per qtype/bank (S2)."""
    connection = open_reporting_connection(database_path)
    try:
        retention = get_true_retention(connection)
        samples = get_elapsed_ms_samples(connection)
    finally:
        connection.close()
    return stats_view(retention, summarize_elapsed_percentiles(samples))


def build_failures_report(database_path: str) -> str:
    """Every wrong answer with what was actually typed, newest first."""
    connection = open_reporting_connection(database_path)
    try:
        failure_rows = get_failure_rows(connection)
    finally:
        connection.close()
    return failures_view(failure_rows)


def build_leeches_report(database_path: str) -> str:
    """Questions with lapse_count >= LEECH_THRESHOLD, worst first."""
    today_ordinal = date.today().toordinal()
    connection = open_reporting_connection(database_path)
    try:
        leech_rows = get_leech_rows(connection, LEECH_THRESHOLD)
    finally:
        connection.close()
    return leeches_view(leech_rows, today_ordinal, LEECH_THRESHOLD)


def build_preview_report(database_path: str) -> str:
    """Upcoming scheduled reviews, soonest first."""
    today_ordinal = date.today().toordinal()
    connection = open_reporting_connection(database_path)
    try:
        upcoming_rows = get_upcoming_schedule_rows(connection, today_ordinal)
    finally:
        connection.close()
    return preview_view(upcoming_rows, today_ordinal)


def build_dry_run_report(database_path: str) -> str:
    """What a review session TODAY would serve, without serving it: the same
    partition -> cap -> throttle sequence as the scheduled strategy, run over
    every bank at once (partition is bank-agnostic; the throttle budget is
    global by design), rendered instead of served."""
    today_ordinal = date.today().toordinal()
    connection = open_reporting_connection(database_path)
    try:
        banks = list_banks(connection)
        candidates = []
        schedule_by_question_id = {}
        for bank in banks:
            candidates.extend(list_questions(connection, bank["id"]))
            schedule_by_question_id.update(
                get_schedule_for_bank(connection, bank["id"])
            )
        new_introduced_today = get_new_introduced_today_by_bank(
            connection, today_ordinal
        )
    finally:
        connection.close()
    due, new, not_due = partition_candidates_by_schedule(
        candidates, schedule_by_question_id, today_ordinal
    )
    due_within_session_cap = due[:REVIEWS_PER_SESSION_MAXIMUM]
    admitted_new = apply_new_question_throttle(
        new,
        new_introduced_today,
        NEW_QUESTIONS_PER_DAY_MAXIMUM,
        NEW_QUESTIONS_PER_BANK_MINIMUM,
    )
    bank_name_by_id = {bank["id"]: bank["name"] for bank in banks}
    return dry_run_view(
        due_within_session_cap,
        admitted_new,
        schedule_by_question_id,
        bank_name_by_id,
        today_ordinal,
    )


# =============================================================================
# A2: authoring shells (the impure edges around the pure A1 transform).
#
# Two faces, one parse. `drill add` is the terminal face: the git-commit
# pattern (open $EDITOR on a template buffer; on a parse error, reinsert the
# error as a #! comment banner and reopen so the fix happens where the eyes
# already are; an untouched or emptied buffer aborts). `drill push` is the
# editor-integration face: a stdin/file filter whose errors go to stderr as
# file:line: message -- the nvim quickfix contract (errorformat=%f:%l:\ %m),
# so :w !drill push --bank X pushes a buffer and :make jumps to the failing
# line. Both faces call author_parse and append through the same
# insert_questions_bulk path the HTTP import uses; neither validates
# anything itself.
#
# Bank targeting is append-first (the human's decision): --bank names an
# EXISTING bank; creating one requires an explicit --category so a typo can
# never silently mint a stray bank. Clock reads and all IO live here at the
# MAIN edge, per the layering contract.
# =============================================================================

AUTHOR_ERROR_BANNER_PREFIX = "#! "
AUTHOR_EDITOR_MAX_ATTEMPTS = 5


def strip_author_error_banner(text: str) -> str:
    """Drop the #!-prefixed error-banner lines the retry loop inserts."""
    kept_lines = [
        line for line in text.splitlines()
        if not line.startswith(AUTHOR_ERROR_BANNER_PREFIX)
    ]
    return "\n".join(kept_lines)


def author_session(
    initial_text: str,
    editor_command: list[str],
    max_attempts: int = AUTHOR_EDITOR_MAX_ATTEMPTS,
) -> list[dict] | None:
    """Run the $EDITOR loop: buffer out, editor, parse on save.

    On a parse error the error text is reinserted at the top of the buffer
    as #! comment lines and the editor reopens (up to max_attempts). An
    untouched or emptied buffer aborts and returns None -- the git-commit
    contract. Returns the parsed canonical records on success.
    """
    buffer_text = initial_text
    for _attempt in range(max_attempts):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".drill", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(buffer_text)
            buffer_path = handle.name
        try:
            subprocess.run(editor_command + [buffer_path], check=True)
            with open(buffer_path, "r", encoding="utf-8") as handle:
                edited_text = handle.read()
        finally:
            os.unlink(buffer_path)
        cleaned_text = strip_author_error_banner(edited_text)
        if (
            cleaned_text.strip() == ""
            or cleaned_text == strip_author_error_banner(buffer_text)
        ):
            return None
        try:
            return author_parse(cleaned_text)
        except ImportParseError as error:
            buffer_text = (
                AUTHOR_ERROR_BANNER_PREFIX + "ERROR: " + str(error) + "\n"
                + AUTHOR_ERROR_BANNER_PREFIX
                + "fix and save again; empty the buffer to abort\n"
                + cleaned_text
            )
    return None


def parse_author_arguments(arguments: list[str]) -> dict:
    """Parse `add`/`push` arguments into {bank, category, file_path}.

    --bank NAME is required; --category NAME is optional (needed only to
    create a bank); one optional positional is a file path (push face).
    Prints the problem to stderr and exits 2 on anything malformed, matching
    main()'s unknown-command behavior.
    """
    bank_name = None
    category_name = None
    file_path = None
    index = 0
    while index < len(arguments):
        argument = arguments[index]
        if argument == "--bank" or argument == "--category":
            if index + 1 >= len(arguments):
                print("missing value after " + argument, file=sys.stderr)
                raise SystemExit(2)
            if argument == "--bank":
                bank_name = arguments[index + 1]
            else:
                category_name = arguments[index + 1]
            index += 2
            continue
        if argument.startswith("--"):
            print("unknown flag " + repr(argument), file=sys.stderr)
            raise SystemExit(2)
        if file_path is not None:
            print("unexpected extra argument " + repr(argument), file=sys.stderr)
            raise SystemExit(2)
        file_path = argument
        index += 1
    if bank_name is None:
        print("missing required --bank <name>", file=sys.stderr)
        raise SystemExit(2)
    return {
        "bank": bank_name,
        "category": category_name,
        "file_path": file_path,
    }


def resolve_author_bank(connection, bank_name: str, category_name) -> int:
    """Return the id of the named bank, creating it only when allowed.

    An existing bank name resolves regardless of --category. A missing bank
    is created only when --category names a seeded category (source
    "manual"); without --category the command refuses, so a typo in --bank
    appends nowhere instead of silently minting a stray bank.
    """
    for bank in list_banks(connection):
        if bank["name"] == bank_name:
            return bank["id"]
    if category_name is None:
        print(
            "bank " + repr(bank_name) + " not found; "
            + "pass --category <name> to create it",
            file=sys.stderr,
        )
        raise SystemExit(2)
    for category in list_categories(connection):
        if category["name"] == category_name:
            bank_id = insert_bank(
                connection,
                category_id=category["id"],
                name=bank_name,
                source="manual",
                created=utc_now_iso(),
            )
            print(
                "created bank " + repr(bank_name)
                + " in category " + repr(category_name),
                file=sys.stderr,
            )
            return bank_id
    known_names = ", ".join(
        category["name"] for category in list_categories(connection)
    )
    print(
        "unknown category " + repr(category_name) + " (known: " + known_names + ")",
        file=sys.stderr,
    )
    raise SystemExit(2)


def run_add_command(arguments: list[str]) -> None:
    """`drill add --bank <name> [--category <name>]`: the $EDITOR loop.

    Resolves the target bank FIRST so a bad target fails before an editor
    session is spent, then loops the editor via author_session and appends
    the accepted records. Aborting the buffer exits 1 with a note; success
    prints the inserted count.
    """
    parsed = parse_author_arguments(arguments)
    if parsed["file_path"] is not None:
        print("add takes no file argument (use push to filter a file)",
              file=sys.stderr)
        raise SystemExit(2)
    database_path = os.environ.get("DRILL_DB", DEFAULT_DATABASE_PATH)
    editor_command = os.environ.get("EDITOR", "vi").split()
    connection = open_reporting_connection(database_path)
    try:
        bank_id = resolve_author_bank(
            connection, parsed["bank"], parsed["category"]
        )
        records = author_session(author_template(1), editor_command)
        if records is None:
            print("aborted: buffer untouched or emptied", file=sys.stderr)
            raise SystemExit(1)
        inserted = insert_questions_bulk(
            connection, bank_id, records, utc_now_iso()
        )
    finally:
        connection.close()
    print("added " + str(inserted) + " question(s) to bank " + repr(parsed["bank"]))


def run_push_command(arguments: list[str]) -> None:
    """`drill push --bank <name> [--category <name>] [file]`: the filter.

    Reads the file argument if given, else stdin (so `:w !drill push --bank
    X` works from nvim). A parse failure prints ONE line to stderr in the
    quickfix shape `file:line: message` (stdin reads report as "stdin") and
    exits 1; nothing is written on failure. Success appends every record
    and prints the inserted count.
    """
    parsed = parse_author_arguments(arguments)
    if parsed["file_path"] is not None:
        source_name = parsed["file_path"]
        with open(parsed["file_path"], "r", encoding="utf-8") as handle:
            text = handle.read()
    else:
        source_name = "stdin"
        text = sys.stdin.read()
    try:
        records = author_parse(text)
    except ImportParseError as error:
        error_line = getattr(error, "error_line", 0)
        print(
            source_name + ":" + str(error_line) + ": " + str(error),
            file=sys.stderr,
        )
        raise SystemExit(1)
    if not records:
        print(source_name + ":0: no question blocks found", file=sys.stderr)
        raise SystemExit(1)
    database_path = os.environ.get("DRILL_DB", DEFAULT_DATABASE_PATH)
    connection = open_reporting_connection(database_path)
    try:
        bank_id = resolve_author_bank(
            connection, parsed["bank"], parsed["category"]
        )
        inserted = insert_questions_bulk(
            connection, bank_id, records, utc_now_iso()
        )
    finally:
        connection.close()
    print("added " + str(inserted) + " question(s) to bank " + repr(parsed["bank"]))


# The two authoring commands take flags and have side effects, so they do
# not fit REPORT_COMMANDS' (database_path -> str) shape; like serve, they
# dispatch before the table lookup in main(). Recorded as a deviation from
# the "extend the table" amendment.
AUTHORING_COMMANDS: dict = {
    "add": (run_add_command, "author questions in $EDITOR (--bank, --category)"),
    "push": (run_push_command, "filter stdin/file into a bank (--bank [file])"),
}


# The dispatch table: command name -> (builder, one-line help). Adding a
# report = one reader + one view + one entry here; usage stays in sync for
# free because it is generated from this table.
REPORT_COMMANDS: dict = {
    "stats": (build_stats_report, "true retention and elapsed_ms percentiles"),
    "failures": (build_failures_report, "wrong answers with what was typed"),
    "leeches": (build_leeches_report, "questions that keep lapsing"),
    "preview": (build_preview_report, "upcoming scheduled reviews"),
    "dry-run": (build_dry_run_report, "what a review session today would serve"),
}


def build_usage_text() -> str:
    command_names = sorted(REPORT_COMMANDS) + sorted(AUTHORING_COMMANDS)
    lines = [
        "usage: drill.py [serve | " + " | ".join(command_names) + "]",
        "",
        "  serve     start the drill server (the default)",
    ]
    for command_name in sorted(REPORT_COMMANDS):
        _builder, help_text = REPORT_COMMANDS[command_name]
        lines.append("  " + format(command_name, "<8") + "  " + help_text)
    for command_name in sorted(AUTHORING_COMMANDS):
        _runner, help_text = AUTHORING_COMMANDS[command_name]
        lines.append("  " + format(command_name, "<8") + "  " + help_text)
    lines.append("")
    lines.append("database: DRILL_DB (default " + DEFAULT_DATABASE_PATH + ")")
    return "\n".join(lines)


def main() -> None:
    """Dispatch: no arguments or `serve` starts the server; an authoring
    command runs its shell; a report command prints its view and exits;
    anything else prints usage and exits 2."""
    arguments = sys.argv[1:]
    if not arguments or arguments == ["serve"]:
        run_serve_command()
        return
    if arguments[0] in AUTHORING_COMMANDS:
        runner, _help_text = AUTHORING_COMMANDS[arguments[0]]
        runner(arguments[1:])
        return
    if len(arguments) != 1 or arguments[0] not in REPORT_COMMANDS:
        print(build_usage_text(), file=sys.stderr)
        raise SystemExit(2)
    builder, _help_text = REPORT_COMMANDS[arguments[0]]
    database_path = os.environ.get("DRILL_DB", DEFAULT_DATABASE_PATH)
    print(builder(database_path))


if __name__ == "__main__":
    main()
