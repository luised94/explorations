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

import csv
import io
import json
import operator
import os
import random
import re
import sqlite3
from datetime import datetime, timedelta, timezone

try:
    import bottle
except ImportError:  # pragma: no cover - environment setup guard
    raise SystemExit(
        "The 'bottle' package is required but not installed. "
        "Run 'uv sync' (or 'pip install bottle') and try again."
    )


# --- CONFIG ---
# Constants and scalar configuration only. No callables (resolution to the
# operator-table layering tension: the operator table is built in LOGIC in
# C-006, not here). Operator definitions are intentionally absent from C-002.

# Current schema version: the highest version the code knows about, reached by
# init_db (the baseline) plus every migration in MIGRATIONS. v2 (D1) adds
# questions.metadata via the runner; init_db builds the baseline and
# run_migrations layers v2..N on top of it.
SCHEMA_VERSION: int = 3

# The version init_db itself builds and stamps. init_db lays down the v1-shaped
# SCHEMA_STATEMENTS, so the baseline IS version 1 -- it must be stamped as 1,
# NOT as SCHEMA_VERSION, or the runner (which only applies versions GREATER than
# the stamped one) skips every migration on a fresh DB and leaves it at the
# baseline schema while claiming the current version. Kept as its own constant,
# distinct from SCHEMA_VERSION, so the "init_db builds version 1" fact is
# explicit and cannot silently track a future SCHEMA_VERSION bump (the defect
# this constant fixes: while the two happened to be equal at v1, init_db stamped
# SCHEMA_VERSION directly and a bump to 2 made fresh DBs skip the v2 migration).
BASELINE_SCHEMA_VERSION: int = 1

# Seed categories (spec section 4.1). Inserted once at init if absent.
# Each entry is (name, description). Config defaults to an empty JSON object
# at seed time; per-category config is populated by later commits as needed.
SEED_CATEGORIES: list[tuple[str, str]] = [
    ("arithmetic", "Generated arithmetic expressions to evaluate"),
    ("vocabulary", "Vocabulary terms and translations"),
    ("trivia", "General trivia and history questions"),
    ("geography", "Places, capitals, and map knowledge"),
    ("logic", "Logic and reasoning puzzles"),
    ("typing", "Typing accuracy and speed drills"),
    ("code", "Code snippet recall and comprehension"),
]

# Question types (qtype enum). free_response is the default for trivia and
# arithmetic; translate is for vocabulary (show term, type translation);
# identify is for "what is this" media questions; multiple_choice is the
# only type that uses the distractors field.
QTYPE_FREE_RESPONSE: str = "free_response"
QTYPE_MULTIPLE_CHOICE: str = "multiple_choice"
QTYPE_TRANSLATE: str = "translate"
QTYPE_IDENTIFY: str = "identify"

QTYPES: list[str] = [
    QTYPE_FREE_RESPONSE,
    QTYPE_MULTIPLE_CHOICE,
    QTYPE_TRANSLATE,
    QTYPE_IDENTIFY,
]

# Validator-level qtype for generated arithmetic. Deliberately NOT part of
# QTYPES: that enum describes stored bank questions, whereas arithmetic is
# ephemeral and never persisted to the questions table. validate_answer
# (C-007) recognizes this string to take the numeric-comparison branch.
QTYPE_ARITHMETIC: str = "arithmetic"

# C-005: Operator scalar configuration.
# Per the layering resolution, CONFIG holds only the scalar data shared
# across operators (the operand-range defaults below) and the enabled-symbol
# list. The per-operator records -- which bind those scalars together with
# the eval callable and operand strategy -- live as OPERATOR_DEFINITIONS in
# LOGIC (C-006), because a record carrying callables is not pure scalar data.
#
# A single record per operator (OPERATOR_DEFINITIONS) replaced the earlier
# split across OPERATOR_CONFIG + _OPERATOR_EVAL_FUNCTIONS +
# _OPERATOR_OPERAND_GENERATORS plus hidden `if symbol == "-"` branches: one
# operator's definition was scattered across four structures joined by the
# symbol string as an implicit foreign key. See OPERATOR_DEFINITIONS in LOGIC
# for the record shape.
#
# OPERATOR_SYMBOLS lists which operators are enabled by default. Every symbol
# here must have a record in OPERATOR_DEFINITIONS; C-006 validates this at the
# time it builds the operator table.

# Shared operand-range defaults, named so the repetition across operators is
# a declared shared default rather than coincidentally-equal magic numbers.
# (_min, _max) inclusive. Addition/subtraction draw from the default range;
# multiplication/division from the narrower multiplicative range (kept small
# so products and dividends stay UI-tractable).
_DEFAULT_OPERAND_RANGE = (1, 20)
_MULTIPLICATIVE_OPERAND_RANGE = (2, 12)
# Exponent's right operand (the power) draws from its OWN narrow range, kept
# small so results stay integer and UI-tractable (e.g. 12^3 = 1728 is already
# near the ceiling of comfortable mental arithmetic). Per the per-operand-range
# decision, exponent declares its own base + power ranges on its record and its
# own strategy reads them, rather than a generic indexed override.
_EXPONENT_POWER_RANGE = (2, 3)

# Operators enabled by default, by symbol. Used when a session config does
# not specify a custom operator set. Every entry must match a record in
# OPERATOR_DEFINITIONS (validated in C-006).
OPERATOR_SYMBOLS: list[str] = ["+", "-", "*", "/", "%", "^"]

# #5 nested-expression generation config. These are MODULE CONSTANTS, not
# function parameters: generate_expression's signature does not change (Lens 3/4
# consensus -- a depth parameter with no concrete caller is speculative; #2 adds
# the parameter together with its real difficulty caller). They govern nesting
# the same way OPERATOR_SYMBOLS governs the operator set: module-level data.
#
# _MAX_OPERATOR_DEPTH -- ceiling on OPERATOR DEPTH, where a leaf is depth 0 and
#   an internal node is 1 + max(child depths). A flat single-operator node has
#   depth 1. _MAX_OPERATOR_DEPTH == 1 reproduces the flat #4 generator EXACTLY
#   (no operand is ever a subtree); >= 2 permits nesting. Provisional default 2.
#   Depth is a STRUCTURAL knob, not a difficulty score (2 + 3 + 4 is easier than
#   7 * 8 yet deeper); #2 owns difficulty and weighs depth among several inputs.
# _RECURSE_PROBABILITY -- per-operand, independent Bernoulli probability that a
#   composable operator's operand is itself a subtree (vs an integer leaf), when
#   depth budget remains. The two operands flip independently; this is NOT a
#   distribution and need not sum to anything. 0 reproduces flat generation; 1
#   always recurses until the depth floor forces leaves. Provisional default 0.5.
# _MAX_GENERATION_ATTEMPTS -- bounded-retry ceiling for the redraw loops. Hitting
#   it raises RuntimeError (a generation bug signal, matching the generator's
#   existing "fail loudly" stance), never hangs. Normal generation never nears
#   it; the property test pins that constraints are satisfiable in practice.
_MAX_OPERATOR_DEPTH = 2
_RECURSE_PROBABILITY = 0.5
_MAX_GENERATION_ATTEMPTS = 1000

# _MAX_RESULT_VALUE -- optional global ceiling on the evaluated result of EVERY
# assembled node (not just the root). DEFAULT None == OFF: the feasibility check
# is a no-op and behavior is identical to the no-ceiling generator. The
# mechanism ships DARK in #5 so #2 can flip a value with zero plumbing. When
# set, build_subtree checks value(left) <op> value(right) <= ceiling at node
# assembly -- both child values are already in hand (bottom-up), so the check is
# LOCAL: on failure the node's operands are redrawn (counting against
# _MAX_GENERATION_ATTEMPTS), never the whole tree, co-locating the cost away from
# the worst case (a root-level whole-tree reject discards the most work exactly
# when trees are largest). No backtracking / subtree-memoization. ADR frames the
# ceiling as a DIFFICULTY-relevant knob #2 may turn, not a fixed sanity guard.
_MAX_RESULT_VALUE = None


# --- #2 difficulty model: scalar rung -> per-operator config (ADR-038) -------
#
# Difficulty is a SCALAR rung the caller dials (one knob); INTERNALLY it expands
# into the PER-OPERATOR structural config the generator already exposes. This is
# shape C with the per-operator correction the #2 design thread earned (handoff
# section 2, the consensus attack): a uniform operand-range multiplier is
# INCOHERENT against this generator, because the operators do not share one
# range semantics -- + and - draw operands directly, * and / use a narrower
# range whose meaning differs (/ DERIVES its dividend as divisor*quotient), %
# carries a separate divisor range, and ^ carries a separate power range with
# almost no magnitude headroom (12^3 = 1728 is already at the UI ceiling,
# ADR-028). So each rung declares the values PER OPERATOR, read from the same
# record fields the operator's own strategy reads (operand_min/max, plus
# divisor_min/max for %, exponent_min/max for ^). A rung carries NO callables;
# it is scalar data only (ADR-008 -- CONFIG holds scalars, LOGIC holds the
# callables that consume them).
#
# "Reliably harder" is operationalized PER OPERATOR-MIX, in two regimes
# (handoff Q1, S7), because leaf_count -- the structural difficulty proxy --
# only moves for some mixes:
#   - COORDINATION regime (mixes containing a composable operator + - *): higher
#     rungs raise operator_depth and recurse_probability, so the tree grows more
#     leaves; leaf_count is monotone non-decreasing across rungs. This is the
#     near-dominant structural feature that earns shape C for the common case.
#   - MAGNITUDE regime (leaf-only mixes / % ^, which cannot nest): leaf_count is
#     a CONSTANT point mass (always 2 -- measured, not assumed), so difficulty
#     rides operand MAGNITUDE instead (wider ranges), pinned by a separate
#     magnitude-monotonicity assertion.
#
# HONESTY CAVEAT (stated so a future reader does not over-trust the number): a
# rung is a heuristic over STRUCTURAL features, not a validated measure of
# cognitive load, and it is NOT a cross-mix cardinal scale -- 7 % 3 and 2 ^ 3
# both have leaf_count 2 and are not commensurable by it. A higher rung produces
# reliably harder questions ON AVERAGE WITHIN a given operator mix.
#
# Each rung record:
#   rung               -- the human-facing scalar label (1..N, ascending = harder)
#   operator_depth     -- _MAX_OPERATOR_DEPTH override for this rung (>= 1; 1 is
#                         flat, reproducing the #4 generator)
#   recurse_probability-- _RECURSE_PROBABILITY override (0.0..1.0)
#   max_result_value   -- _MAX_RESULT_VALUE override (None = no ceiling) (ADR-039)
#   operator_ranges    -- per-operator scaled range fields, keyed by symbol. Each
#                         value is a dict of the SAME field names the operator's
#                         record/strategy reads. Composable + - * and the / base
#                         use operand_min/max; % adds divisor_min/max; ^ adds
#                         exponent_min/max. A rung need not list every operator;
#                         an operator omitted from a rung keeps its OPERATOR_DEFINITIONS
#                         default range (so a rung only states what it CHANGES).
#
# WHAT C-D2a DECLARES vs WHAT LATER COMMITS CONSUME: this commit defines the
# atom (leaf_count) and the SHAPE/VALUES of this table, and validates the table
# is internally consistent at import. The generator does NOT yet read it --
# generate_expression is unchanged until C-D2b threads operator_depth/recurse
# (the weld), C-D2d applies operator_ranges, and C-D2e turns on max_result_value
# (the deliberate red). Values below are grounded in a throwaway headroom probe
# (handoff P3/T2: sample generate_expression at N=5000 per operator-mix), not
# guessed: rung 2 reproduces today's dark defaults (depth 2, p 0.5, no ceiling,
# baseline ranges) so the existing live behavior maps onto a named rung; rung 1
# is the flat anchor; rungs 3-4 add coordination (depth/recurse) and magnitude
# (wider ranges) with a ceiling engaged at the top to keep * results tractable.
DIFFICULTY_RUNGS: list[dict] = [
    {
        "rung": 1,
        "operator_depth": 1,
        "recurse_probability": 0.0,
        "max_result_value": None,
        # Flat, smallest magnitudes: narrow every operator toward its floor.
        "operator_ranges": {
            "+": {"operand_min": 1, "operand_max": 10},
            "-": {"operand_min": 1, "operand_max": 10},
            "*": {"operand_min": 2, "operand_max": 6},
            "/": {"operand_min": 2, "operand_max": 6},
            "%": {
                "operand_min": 1,
                "operand_max": 10,
                "divisor_min": 2,
                "divisor_max": 6,
            },
            "^": {
                "operand_min": 2,
                "operand_max": 8,
                "exponent_min": 2,
                "exponent_max": 2,
            },
        },
    },
    {
        "rung": 2,
        # Today's dark defaults, named. depth 2 / p 0.5 / no ceiling / the
        # baseline OPERATOR_DEFINITIONS ranges -- so difficulty=2 is the current
        # live distribution (Q6 anchor: the no-parameter path stays separate and
        # byte-identical, but rung 2 deliberately MATCHES it as the mid anchor).
        "operator_depth": 2,
        "recurse_probability": 0.5,
        "max_result_value": None,
        "operator_ranges": {
            "+": {"operand_min": 1, "operand_max": 20},
            "-": {"operand_min": 1, "operand_max": 20},
            "*": {"operand_min": 2, "operand_max": 12},
            "/": {"operand_min": 2, "operand_max": 12},
            "%": {
                "operand_min": 1,
                "operand_max": 20,
                "divisor_min": 2,
                "divisor_max": 12,
            },
            "^": {
                "operand_min": 2,
                "operand_max": 12,
                "exponent_min": 2,
                "exponent_max": 3,
            },
        },
    },
    {
        "rung": 3,
        # More coordination (higher recurse) AND wider magnitude for the leaf-only
        # operators that depth cannot reach. ^ holds its baseline range (no
        # headroom: 12^3 already near the UI ceiling, Q2/ADR-039).
        "operator_depth": 2,
        "recurse_probability": 0.7,
        "max_result_value": None,
        "operator_ranges": {
            "+": {"operand_min": 5, "operand_max": 40},
            "-": {"operand_min": 5, "operand_max": 40},
            "*": {"operand_min": 3, "operand_max": 15},
            "/": {"operand_min": 3, "operand_max": 15},
            "%": {
                "operand_min": 10,
                "operand_max": 50,
                "divisor_min": 3,
                "divisor_max": 15,
            },
            "^": {
                "operand_min": 2,
                "operand_max": 12,
                "exponent_min": 2,
                "exponent_max": 3,
            },
        },
    },
    {
        "rung": 4,
        # Deepest coordination + widest magnitude, with the global result ceiling
        # ENGAGED so deep * trees stay tractable (the probe showed * reaching
        # ~8.8e7 at depth 3 uncapped). The ceiling bounds RESULTS, not leaves
        # (S2/ADR-035): operand magnitude is still capped by the ranges, so the /
        # derived dividend cannot collide with the ceiling into infeasibility --
        # the joint (ranges, ceiling) satisfiability is PROVEN per mix in C-D2e.
        "operator_depth": 3,
        "recurse_probability": 0.7,
        "max_result_value": 100000,
        "operator_ranges": {
            "+": {"operand_min": 10, "operand_max": 60},
            "-": {"operand_min": 10, "operand_max": 60},
            "*": {"operand_min": 3, "operand_max": 18},
            "/": {"operand_min": 3, "operand_max": 18},
            "%": {
                "operand_min": 20,
                "operand_max": 99,
                "divisor_min": 3,
                "divisor_max": 18,
            },
            "^": {
                "operand_min": 2,
                "operand_max": 12,
                "exponent_min": 2,
                "exponent_max": 3,
            },
        },
    },
]


def _check_difficulty_rungs_consistency() -> None:
    """Raise at import if DIFFICULTY_RUNGS is internally inconsistent (C-D2a).

    Mirrors the migration-version guard's fail-at-import discipline: a typo in
    the rung table is a programming error caught at module load, not a malformed
    question served at request time. Checks:
      - rung labels are the strictly ascending, gap-free sequence 1..N;
      - operator_depth >= 1 and recurse_probability in [0, 1];
      - max_result_value is None or a positive int;
      - every operator named in any rung's operator_ranges is a real operator
        (exists in OPERATOR_SYMBOLS), and every range field it declares is one
        the operator actually reads -- so a rung cannot scale a field the
        strategy ignores (e.g. divisor_min on +). The required-field set per
        operator mirrors OPERATOR_DEFINITIONS / the strategy docstrings.

    OPERATORS is not yet built at this point in module load order, so this
    validates against OPERATOR_SYMBOLS (the enabled set) and the known per-symbol
    range-field shape, both of which are defined above in CONFIG.
    """
    rung_labels = [rung_record["rung"] for rung_record in DIFFICULTY_RUNGS]
    expected_labels = list(range(1, len(DIFFICULTY_RUNGS) + 1))
    if rung_labels != expected_labels:
        raise RuntimeError(
            "DIFFICULTY_RUNGS rung labels must be the gap-free ascending "
            "sequence " + repr(expected_labels) + "; got " + repr(rung_labels)
        )

    # The range fields each operator symbol legitimately carries. A rung may
    # scale any subset of these for an operator, but no others.
    allowed_range_fields = {
        "+": {"operand_min", "operand_max"},
        "-": {"operand_min", "operand_max"},
        "*": {"operand_min", "operand_max"},
        "/": {"operand_min", "operand_max"},
        "%": {"operand_min", "operand_max", "divisor_min", "divisor_max"},
        "^": {"operand_min", "operand_max", "exponent_min", "exponent_max"},
    }

    for rung_record in DIFFICULTY_RUNGS:
        rung_label = rung_record["rung"]
        operator_depth = rung_record["operator_depth"]
        if not isinstance(operator_depth, int) or operator_depth < 1:
            raise RuntimeError(
                "DIFFICULTY_RUNGS rung "
                + str(rung_label)
                + " operator_depth must be an int >= 1; got "
                + repr(operator_depth)
            )
        recurse_probability = rung_record["recurse_probability"]
        if not (0.0 <= recurse_probability <= 1.0):
            raise RuntimeError(
                "DIFFICULTY_RUNGS rung "
                + str(rung_label)
                + " recurse_probability must be in [0, 1]; got "
                + repr(recurse_probability)
            )
        max_result_value = rung_record["max_result_value"]
        if max_result_value is not None and (
            not isinstance(max_result_value, int) or max_result_value <= 0
        ):
            raise RuntimeError(
                "DIFFICULTY_RUNGS rung "
                + str(rung_label)
                + " max_result_value must be None or a positive int; got "
                + repr(max_result_value)
            )
        for symbol, ranges in rung_record["operator_ranges"].items():
            if symbol not in OPERATOR_SYMBOLS:
                raise RuntimeError(
                    "DIFFICULTY_RUNGS rung "
                    + str(rung_label)
                    + " names unknown operator "
                    + repr(symbol)
                )
            unexpected = set(ranges.keys()) - allowed_range_fields[symbol]
            if unexpected:
                raise RuntimeError(
                    "DIFFICULTY_RUNGS rung "
                    + str(rung_label)
                    + " operator "
                    + repr(symbol)
                    + " declares range fields its strategy does "
                    "not read: " + ", ".join(sorted(unexpected))
                )


_check_difficulty_rungs_consistency()


# Default on-disk database filename. The server may override this at startup.
DEFAULT_DATABASE_PATH: str = "drill.db"

# Data definition language for every table in the schema (spec section 4.1).
# All timestamp columns are TEXT storing ISO 8601 strings (item 8). Foreign
# keys are declared; PRAGMA foreign_keys is enabled per connection.
SCHEMA_STATEMENTS: list[str] = [
    """
    CREATE TABLE IF NOT EXISTS schema_version (
        version INTEGER NOT NULL,
        applied TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS categories (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        name        TEXT NOT NULL UNIQUE,
        description TEXT,
        config      TEXT NOT NULL DEFAULT '{}'
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS banks (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        name        TEXT NOT NULL,
        language    TEXT,
        source      TEXT NOT NULL,
        metadata    TEXT NOT NULL DEFAULT '{}',
        created     TEXT NOT NULL,
        FOREIGN KEY (category_id) REFERENCES categories (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS questions (
        id           INTEGER PRIMARY KEY AUTOINCREMENT,
        bank_id      INTEGER NOT NULL,
        qtype        TEXT NOT NULL,
        question     TEXT NOT NULL,
        answer       TEXT NOT NULL,
        alternatives TEXT NOT NULL DEFAULT '[]',
        distractors  TEXT NOT NULL DEFAULT '[]',
        hints        TEXT NOT NULL DEFAULT '[]',
        media_url    TEXT,
        tags         TEXT NOT NULL DEFAULT '[]',
        difficulty   INTEGER,
        created      TEXT NOT NULL,
        FOREIGN KEY (bank_id) REFERENCES banks (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sessions (
        id          INTEGER PRIMARY KEY AUTOINCREMENT,
        category_id INTEGER NOT NULL,
        bank_id     INTEGER,
        config      TEXT NOT NULL DEFAULT '{}',
        started     TEXT NOT NULL,
        ended       TEXT,
        FOREIGN KEY (category_id) REFERENCES categories (id),
        FOREIGN KEY (bank_id) REFERENCES banks (id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS responses (
        id            INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id    INTEGER NOT NULL,
        question_id   INTEGER,
        question_text TEXT NOT NULL,
        answer_text   TEXT NOT NULL,
        user_input    TEXT NOT NULL,
        correct       INTEGER NOT NULL,
        elapsed_ms    INTEGER,
        answered      TEXT NOT NULL,
        FOREIGN KEY (session_id) REFERENCES sessions (id),
        FOREIGN KEY (question_id) REFERENCES questions (id)
    )
    """,
]


def _migrate_2_add_questions_metadata(connection: sqlite3.Connection) -> None:
    """v2 (D1): add questions.metadata, a per-question structured-extras column.

    Additive, NOT NULL DEFAULT '{}' so every pre-existing row backfills to an
    empty JSON object with no data loss (the .db file is the user's only copy).
    The runner owns the transaction and stamps schema_version: this fn performs
    ONLY the schema change and must not commit, rollback, or touch the version.

    banks.metadata already exists in the v1 baseline; questions had no metadata
    column, so this fills that gap (ADR-D1). It is a deliberately uncommitted
    extras hatch: later threads (difficulty tuning, SM2 scheduling state, new
    drill types) can prototype per-question state here before any of them earns
    a dedicated, typed column.

    DEFERRED -- grading_kind: the original D1 brief paired a grading_kind column
    with this one. It is intentionally NOT added here. grading_kind would be a
    persisted *grading-policy* axis, but its only real consumer is adaptive
    selection / SM2 (roadmap #7 -> Phase 4), which consumes grading *results*,
    not policy, and whose own shape is still open ("two notions of a review").
    Forward-only migrations make a wrong guess unrollable, so the column waits
    for that real caller. RECONSIDER when #7 lands: decide then whether a
    grading axis belongs on questions, and fold it in with the SM2 scheduling
    fields as a single later migration. See llm/decisions.md ADR-D1.
    """
    connection.execute(
        "ALTER TABLE questions ADD COLUMN metadata TEXT NOT NULL DEFAULT '{}'"
    )


def _migrate_3_add_response_difficulty(connection: sqlite3.Connection) -> None:
    """v3 (#2): add responses.difficulty and responses.leaf_count.

    Two NULLABLE INTEGER columns recording, per answered arithmetic question,
    the difficulty rung served and the generated expression's leaf_count. Both
    follow the elapsed_ms precedent (a nullable collected-but-optional column on
    responses): additive, NULL-by-default, so every pre-existing row backfills to
    NULL with no data loss (the .db file is the user's only copy). The runner
    owns the transaction and stamps schema_version; this fn performs ONLY the
    schema change and must not commit, rollback, or touch the version.

    Why NULLABLE and not NOT NULL DEFAULT: these facts only exist for arithmetic
    responses generated under the #2 difficulty path. Bank-question responses and
    every response recorded before this migration have no rung and no expression
    tree, so NULL is the honest "not applicable / not recorded" value -- a numeric
    default (e.g. 0) would be a fake rung and a fake leaf count that the stats
    breakdown (C-D2i) would then have to special-case anyway.

    Why TWO columns (the questions.metadata hatch is NOT used): arithmetic
    responses carry question_id NULL (generated questions are never stored), so
    there is no questions row to hang metadata on -- the uncommitted extras hatch
    is unreachable for exactly the rows that need these facts. Honest recording
    therefore requires real columns on responses (ADR-040). difficulty is the
    served rung (mutable label -- re-means if a later thread retunes the rung
    table); leaf_count is the NON-DRIFTING structural fact (recomputable from
    question_text by re-parsing), which is why the C-D2i breakdown groups by it
    (ADR-038 S11 resolution) rather than by the rung.
    """
    connection.execute("ALTER TABLE responses ADD COLUMN difficulty INTEGER")
    connection.execute("ALTER TABLE responses ADD COLUMN leaf_count INTEGER")


# Forward-only schema migrations, in ascending version order. Each entry is
# (version, description, migrate) where migrate(connection) performs the schema
# change for that version. The runner (run_migrations) applies every entry whose
# version is greater than the database's current version, each inside its own
# all-or-nothing transaction (see _apply_one).
#
# This list is the ONE place a schema change is expressed from now on. To add a
# migration, a later thread appends a single (version, description, migrate)
# tuple here and bumps SCHEMA_VERSION to match -- it does NOT edit the runner.
#
# v2 (D1) is the first real entry: questions.metadata. Version 1 (today's
# baseline) is produced by init_db, not by an entry here. v3 (#2) adds the
# responses difficulty + leaf_count columns; it is added together with the
# SCHEMA_VERSION bump to 3 so the import-time consistency guard stays satisfied
# (adding one without the other raises -- the guard-weld).
MIGRATIONS: list[tuple[int, str, object]] = [
    (2, "add questions.metadata", _migrate_2_add_questions_metadata),
    (3, "add responses.difficulty and leaf_count", _migrate_3_add_response_difficulty),
]


# Consistency guard, checked at import: the highest migration version must equal
# SCHEMA_VERSION, so the constant and the registry cannot silently drift. With
# an empty MIGRATIONS this holds only when SCHEMA_VERSION is the init_db baseline
# (1); once migrations exist, the top entry's version IS the current version.
def _check_migration_version_consistency() -> None:
    """Raise at import if MIGRATIONS and SCHEMA_VERSION disagree.

    Two ways they can drift, both caught here:
      - a migration is added without bumping SCHEMA_VERSION (top > constant), or
        SCHEMA_VERSION is bumped without adding the migration (constant > top);
      - migration versions are not the strictly ascending 2..N that the runner's
        ordered, gap-free forward walk assumes.
    """
    versions = [version for version, _description, _migrate in MIGRATIONS]
    if versions != sorted(versions) or len(set(versions)) != len(versions):
        raise RuntimeError(
            "MIGRATIONS versions must be strictly ascending and unique: "
            + repr(versions)
        )
    # Migrations layer on top of the init_db baseline (version 1): an empty
    # registry means the DB never advances past 1, so SCHEMA_VERSION must be 1;
    # a non-empty registry must be the gap-free sequence 2..SCHEMA_VERSION with
    # its top entry equal to SCHEMA_VERSION. Both arms reduce to: versions ==
    # range(2, SCHEMA_VERSION + 1). Checking that single equality also catches a
    # constant bumped without a matching migration (and vice versa), including
    # the empty-registry case the earlier per-arm form let slip through.
    expected = list(range(2, SCHEMA_VERSION + 1))
    if versions != expected:
        raise RuntimeError(
            "SCHEMA_VERSION ("
            + str(SCHEMA_VERSION)
            + ") and MIGRATIONS disagree: migrations layer on the version-1 "
            + "init_db baseline, so MIGRATIONS versions must be the gap-free "
            + "sequence "
            + repr(expected)
            + "; got "
            + repr(versions)
            + " (bump SCHEMA_VERSION and add the migration together)"
        )


_check_migration_version_consistency()


# --- DATABASE ---
# Functions that take a sqlite3.Connection and return dicts or lists. IO
# only: no business logic, no HTTP. init_db is the one place in this section
# allowed to read the clock, because it must stamp the schema_version row
# and the seed timestamps (item 8).


def utc_now_iso() -> str:
    """Return the current UTC time as an ISO 8601 string.

    This is the single clock-reading helper for the DATABASE layer. Only
    init_db (here) and the HTTP layer (later commits) may call it; LOGIC
    receives timestamps as string parameters and never reads the clock.
    """
    return datetime.now(timezone.utc).isoformat()


def connect(database_path: str = DEFAULT_DATABASE_PATH) -> sqlite3.Connection:
    """Open a SQLite connection with row access by name and FKs enforced.

    The connection uses sqlite3.Row so that DATABASE functions can convert
    rows to plain dicts before returning them across the layer boundary.
    Foreign key enforcement is enabled per connection (SQLite defaults off).
    """
    connection = sqlite3.connect(database_path)
    connection.row_factory = sqlite3.Row
    connection.execute("PRAGMA foreign_keys = ON")
    return connection


def get_schema_version(connection: sqlite3.Connection) -> int | None:
    """Return the highest recorded schema version, or None if unstamped.

    Returns None when the schema_version table does not yet exist or holds
    no rows, which indicates a fresh, uninitialized database.
    """
    try:
        cursor = connection.execute(
            "SELECT MAX(version) AS version FROM schema_version"
        )
    except sqlite3.OperationalError:
        # schema_version table does not exist yet.
        return None
    row = cursor.fetchone()
    if row is None or row["version"] is None:
        return None
    return int(row["version"])


def _apply_one(
    connection: sqlite3.Connection,
    version: int,
    description: str,
    migrate,
    now: str,
) -> None:
    """Apply a single migration inside one explicit, all-or-nothing transaction.

    migrate -- a callable taking the connection; it performs the schema change
               (DDL and/or data backfill) for this version. It MUST NOT commit,
               rollback, or stamp schema_version itself: this function owns the
               transaction boundary and records the version row on success.

    Why an explicit BEGIN/COMMIT/ROLLBACK rather than relying on the
    connection's implicit handling: Python's legacy sqlite3 isolation mode
    (the default for connect()) does NOT open a transaction before a DDL
    statement such as ALTER TABLE, so a DDL change autocommits and SURVIVES a
    later rollback(). That would make a half-finished migration permanent --
    the opposite of the forward-only, last-good-version guarantee. Issuing
    BEGIN ourselves puts the DDL inside a transaction we control, so any
    failure (in the migrate callable or the version stamp) rolls the whole
    step back and leaves the database at its prior version, not half-migrated.

    On failure the original exception is re-raised unchanged after rollback,
    so the caller sees the real error; the caller is responsible for the
    operator-facing "migration N failed" framing.
    """
    connection.execute("BEGIN")
    try:
        migrate(connection)
        connection.execute(
            "INSERT INTO schema_version (version, applied) VALUES (?, ?)",
            (version, now),
        )
        connection.execute("COMMIT")
    except Exception:
        connection.execute("ROLLBACK")
        raise


def run_migrations(
    connection: sqlite3.Connection,
    now: str,
    target_version: int = None,
    migrations: list = None,
) -> dict:
    """Apply every pending migration in order, each in its own transaction.

    Forward-only and idempotent: applies the registry entries whose version is
    greater than the database's current version and not greater than the
    target, in ascending order, via _apply_one (which owns each transaction so
    a failure rolls that step back and stops the walk at the last good version).
    Running this against an already-current database selects nothing and is a
    safe no-op.

    Parameters:
      now             -- ISO timestamp string stamped into each applied
                         migration's schema_version row. Injected by the caller
                         (MAIN reads the clock; DATABASE does not) so this layer
                         stays clock-free and tests are deterministic.
      target_version  -- highest version to migrate to; defaults to
                         SCHEMA_VERSION. Lets a caller stop short of the latest.
      migrations      -- the (version, description, migrate) registry; defaults
                         to the module MIGRATIONS. Injectable so a test can run
                         the real loop over a deliberately-failing migration
                         without touching the shipped registry.

    Returns an operator-facing dict the caller can report from:
      {"from_version": int, "to_version": int, "applied": [(version, desc), ...]}
    "from_version" is the version before this run (0 when the database is not
    yet baselined, i.e. get_schema_version returned None); "to_version" is the
    version after; "applied" lists what ran, in order. On a no-op, "applied" is
    empty and from_version == to_version.

    This function reads and selects but performs no commit/rollback itself: all
    transactional writes happen inside _apply_one, one per migration.
    """
    if target_version is None:
        target_version = SCHEMA_VERSION
    if migrations is None:
        migrations = MIGRATIONS

    current_raw = get_schema_version(connection)
    # None means no baseline is stamped yet (table absent or empty). The wired
    # path always runs init_db first (which stamps the version-1 baseline), so
    # this layer treats a missing baseline as 0 purely to compute the selection;
    # with migrations layered on version 1, that still skips nothing it should
    # not, and an empty registry makes it a no-op regardless.
    current = 0 if current_raw is None else current_raw

    pending = [
        (version, description, migrate)
        for version, description, migrate in migrations
        if current < version <= target_version
    ]
    pending.sort(key=lambda entry: entry[0])

    applied = []
    for version, description, migrate in pending:
        # On failure _apply_one rolls back this step and re-raises; the loop
        # stops here, leaving the database at the last successfully applied
        # version. The partial "applied" list reflects what did commit.
        _apply_one(connection, version, description, migrate, now)
        applied.append((version, description))

    to_version = applied[-1][0] if applied else current
    return {
        "from_version": current,
        "to_version": to_version,
        "applied": applied,
    }


def seed_categories(connection: sqlite3.Connection) -> None:
    """Insert the seed categories that are not already present.

    Idempotent: uses INSERT OR IGNORE against the UNIQUE name constraint, so
    running it repeatedly never duplicates a category and never overwrites a
    category whose description or config was later edited.
    """
    connection.executemany(
        "INSERT OR IGNORE INTO categories (name, description, config) "
        "VALUES (?, ?, '{}')",
        SEED_CATEGORIES,
    )


# C-010 support: category readers. The commit plan defines no dedicated
# category-CRUD commit (categories are seeded in C-002 and otherwise fixed in
# v1), but the GET /api/categories handler needs to read them, so the minimal
# read functions live here. Same plain-dict-out pattern as the other readers.


def _category_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a categories row to a plain dict with config parsed."""
    return {
        "id": row["id"],
        "name": row["name"],
        "description": row["description"],
        "config": _load_json(row["config"], {}),
    }


def list_categories(connection: sqlite3.Connection) -> list[dict]:
    """Return all categories as a list of dicts, ordered by id (seed order)."""
    cursor = connection.execute("SELECT * FROM categories ORDER BY id")
    return [_category_row_to_dict(row) for row in cursor.fetchall()]


def get_category(connection: sqlite3.Connection, category_id: int) -> dict | None:
    """Return a single category dict by id, or None if no such category."""
    cursor = connection.execute(
        "SELECT * FROM categories WHERE id = ?",
        (category_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _category_row_to_dict(row)


def init_db(connection: sqlite3.Connection) -> None:
    """Create the schema if needed, stamp the version, and seed categories.

    Idempotent and safe to call on every startup. Creates all tables with
    IF NOT EXISTS, stamps the BASELINE_SCHEMA_VERSION (1) the first time the
    database is initialized, and seeds any missing categories. init_db builds
    only the baseline; the migration runner advances it to SCHEMA_VERSION. If
    the database already has a version row, it is left untouched (stamp-once).
    """
    for statement in SCHEMA_STATEMENTS:
        connection.execute(statement)

    existing_version = get_schema_version(connection)
    if existing_version is None:
        connection.execute(
            "INSERT INTO schema_version (version, applied) VALUES (?, ?)",
            (BASELINE_SCHEMA_VERSION, utc_now_iso()),
        )

    seed_categories(connection)
    connection.commit()


# C-003: Bank and question CRUD.
# These functions accept and return plain Python structures. The JSON-typed
# columns (config/metadata as objects; alternatives/distractors/hints/tags
# as arrays) are serialized to text on write and parsed back to Python lists
# and dicts on read, so callers never handle raw JSON strings. This
# marshalling is IO at the layer edge, not business logic.


def _dump_json(value: object) -> str:
    """Serialize a Python value to a compact JSON string for storage.

    Used to write the JSON-typed columns. Compact separators keep the
    stored text small and stable for inspection.
    """
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))


def _load_json(text: str | None, default: object) -> object:
    """Parse a JSON string from a column, returning default when empty.

    The schema defaults JSON columns to '[]' or '{}' and marks them NOT
    NULL, so text is normally present; default guards the None case
    defensively without raising at the layer boundary.

    If a stored value is present but not valid JSON -- which should not happen
    through this application's writes, but can occur if the .db file is
    hand-edited (the spec encourages direct SQLite inspection and file-copy
    backups) -- this raises ValueError with a clear message rather than
    letting an opaque JSONDecodeError surface from inside row conversion.
    """
    if text is None or text == "":
        return default
    try:
        return json.loads(text)
    except json.JSONDecodeError as error:
        raise ValueError(
            "stored JSON column is corrupt (not valid JSON): "
            + repr(text[:80])
            + " ("
            + str(error)
            + ")"
        )


def _bank_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a banks row to a plain dict with metadata parsed to an object."""
    return {
        "id": row["id"],
        "category_id": row["category_id"],
        "name": row["name"],
        "language": row["language"],
        "source": row["source"],
        "metadata": _load_json(row["metadata"], {}),
        "created": row["created"],
    }


def _question_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a questions row to a plain dict with JSON columns parsed.

    The four array columns become Python lists; metadata becomes a dict; other
    scalar and nullable columns pass through unchanged. The result is the
    canonical question dict shape that LOGIC and HTTP operate on.

    metadata (added in v2/D1) is the per-question structured-extras object,
    parsed from its JSON text to a dict (default {} for the backfilled rows).
    It is surfaced at the READER level here so get_question/list_questions
    return it; it is deliberately NOT forwarded into build_question_payload's
    client payload (that allowlist guards the frozen section-6 contract). When
    a real consumer needs it client-side or at grading time -- e.g. SM2 /
    adaptive selection, roadmap #7 -- that thread threads it through the
    payload and validation seam. See llm/decisions.md ADR-D1.
    """
    return {
        "id": row["id"],
        "bank_id": row["bank_id"],
        "qtype": row["qtype"],
        "question": row["question"],
        "answer": row["answer"],
        "alternatives": _load_json(row["alternatives"], []),
        "distractors": _load_json(row["distractors"], []),
        "hints": _load_json(row["hints"], []),
        "media_url": row["media_url"],
        "tags": _load_json(row["tags"], []),
        "difficulty": row["difficulty"],
        "metadata": _load_json(row["metadata"], {}),
        "created": row["created"],
    }


def list_banks(
    connection: sqlite3.Connection,
    category_id: int | None = None,
) -> list[dict]:
    """Return banks as a list of dicts, optionally filtered by category.

    When category_id is None, all banks are returned. Results are ordered by
    name for stable, predictable listing in the bank selector UI.
    """
    if category_id is None:
        cursor = connection.execute("SELECT * FROM banks ORDER BY name")
    else:
        cursor = connection.execute(
            "SELECT * FROM banks WHERE category_id = ? ORDER BY name",
            (category_id,),
        )
    return [_bank_row_to_dict(row) for row in cursor.fetchall()]


def get_bank(connection: sqlite3.Connection, bank_id: int) -> dict | None:
    """Return a single bank dict by id, or None if no such bank exists."""
    cursor = connection.execute(
        "SELECT * FROM banks WHERE id = ?",
        (bank_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _bank_row_to_dict(row)


def insert_bank(
    connection: sqlite3.Connection,
    category_id: int,
    name: str,
    source: str,
    created: str,
    language: str | None = None,
    metadata: dict | None = None,
) -> int:
    """Insert a bank and return its new id.

    The caller supplies the created timestamp as an ISO 8601 string (the
    HTTP layer reads the clock; this layer does not). metadata defaults to
    an empty object. source is one of "manual", "import", or "ai_generated"
    per the data model; this layer stores it verbatim without validating.
    """
    cursor = connection.execute(
        "INSERT INTO banks "
        "(category_id, name, language, source, metadata, created) "
        "VALUES (?, ?, ?, ?, ?, ?)",
        (
            category_id,
            name,
            language,
            source,
            _dump_json(metadata if metadata is not None else {}),
            created,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def delete_bank(connection: sqlite3.Connection, bank_id: int) -> int:
    """Delete a bank and its questions, returning the number of banks removed.

    Questions reference banks by foreign key, so the bank's questions are
    deleted first to satisfy referential integrity. Returns 0 when the bank
    does not exist.
    """
    connection.execute(
        "DELETE FROM questions WHERE bank_id = ?",
        (bank_id,),
    )
    cursor = connection.execute(
        "DELETE FROM banks WHERE id = ?",
        (bank_id,),
    )
    connection.commit()
    return cursor.rowcount


def list_questions(
    connection: sqlite3.Connection,
    bank_id: int,
) -> list[dict]:
    """Return all questions in a bank as a list of dicts, ordered by id."""
    cursor = connection.execute(
        "SELECT * FROM questions WHERE bank_id = ? ORDER BY id",
        (bank_id,),
    )
    return [_question_row_to_dict(row) for row in cursor.fetchall()]


def get_question(
    connection: sqlite3.Connection,
    question_id: int,
) -> dict | None:
    """Return a single question dict by id, or None if no such question."""
    cursor = connection.execute(
        "SELECT * FROM questions WHERE id = ?",
        (question_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _question_row_to_dict(row)


def insert_questions_bulk(
    connection: sqlite3.Connection,
    bank_id: int,
    questions: list[dict],
    created: str,
) -> int:
    """Insert many questions into one bank, returning the count inserted.

    Each question dict supplies the required keys question and answer and
    may supply qtype and the optional fields; missing optional fields fall
    back to sensible defaults (free_response qtype, empty arrays, null media
    and difficulty). All rows share the one created timestamp passed in.
    This is the bulk path used by the import endpoint (parse in C-008 feeds
    this in C-010). Inserts run in a single transaction.
    """
    rows = []
    for question in questions:
        rows.append(
            (
                bank_id,
                question.get("qtype", QTYPE_FREE_RESPONSE),
                question["question"],
                question["answer"],
                _dump_json(question.get("alternatives", [])),
                _dump_json(question.get("distractors", [])),
                _dump_json(question.get("hints", [])),
                question.get("media_url"),
                _dump_json(question.get("tags", [])),
                question.get("difficulty"),
                created,
            )
        )
    connection.executemany(
        "INSERT INTO questions "
        "(bank_id, qtype, question, answer, alternatives, distractors, "
        "hints, media_url, tags, difficulty, created) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        rows,
    )
    connection.commit()
    return len(rows)


# C-004: Session and response tracking.
# Sessions bracket a run of drilling; responses record each answered
# question within a session. As with C-003, these functions accept and
# return plain Python structures and read no clock -- timestamps arrive as
# ISO 8601 string parameters from the HTTP layer. The responses.correct
# column is stored as INTEGER 0/1 but exposed to callers as a Python bool;
# the correct/incorrect judgment itself is a LOGIC output (C-007) that this
# layer only stores.


def _session_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a sessions row to a plain dict with config parsed to an object."""
    return {
        "id": row["id"],
        "category_id": row["category_id"],
        "bank_id": row["bank_id"],
        "config": _load_json(row["config"], {}),
        "started": row["started"],
        "ended": row["ended"],
    }


def _response_row_to_dict(row: sqlite3.Row) -> dict:
    """Convert a responses row to a plain dict with correct as a bool.

    The stored INTEGER 0/1 becomes a Python bool; elapsed_ms and question_id
    remain nullable and pass through unchanged.
    """
    return {
        "id": row["id"],
        "session_id": row["session_id"],
        "question_id": row["question_id"],
        "question_text": row["question_text"],
        "answer_text": row["answer_text"],
        "user_input": row["user_input"],
        "correct": bool(row["correct"]),
        "elapsed_ms": row["elapsed_ms"],
        "answered": row["answered"],
    }


def start_session(
    connection: sqlite3.Connection,
    category_id: int,
    started: str,
    bank_id: int | None = None,
    config: dict | None = None,
) -> int:
    """Insert a session row and return its new id.

    The caller supplies the started timestamp as an ISO 8601 string. bank_id
    is optional (a category-wide session, e.g. generated arithmetic, has no
    bank). ended is left NULL until end_session is called. config defaults
    to an empty object.
    """
    cursor = connection.execute(
        "INSERT INTO sessions (category_id, bank_id, config, started, ended) "
        "VALUES (?, ?, ?, ?, NULL)",
        (
            category_id,
            bank_id,
            _dump_json(config if config is not None else {}),
            started,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def end_session(
    connection: sqlite3.Connection,
    session_id: int,
    ended: str,
) -> int:
    """Stamp a session's ended timestamp, returning the number of rows updated.

    The caller supplies the ended timestamp as an ISO 8601 string. Returns 0
    when the session does not exist. Already-ended sessions are overwritten
    with the new timestamp; guarding against re-ending is a logic concern,
    not enforced here.
    """
    cursor = connection.execute(
        "UPDATE sessions SET ended = ? WHERE id = ?",
        (ended, session_id),
    )
    connection.commit()
    return cursor.rowcount


def get_session(
    connection: sqlite3.Connection,
    session_id: int,
) -> dict | None:
    """Return a single session dict by id, or None if no such session."""
    cursor = connection.execute(
        "SELECT * FROM sessions WHERE id = ?",
        (session_id,),
    )
    row = cursor.fetchone()
    if row is None:
        return None
    return _session_row_to_dict(row)


def insert_response(
    connection: sqlite3.Connection,
    session_id: int,
    question_text: str,
    answer_text: str,
    user_input: str,
    correct: bool,
    answered: str,
    question_id: int | None = None,
    elapsed_ms: int | None = None,
    difficulty: int | None = None,
    leaf_count: int | None = None,
) -> int:
    """Insert a response row and return its new id.

    question_id is NULL for generated arithmetic questions, which are not
    persisted to the questions table; question_text always carries the
    rendered question so the response is self-describing regardless. The
    correct bool is stored as INTEGER 0/1. answered is an ISO 8601 string
    supplied by the caller. elapsed_ms is optional (column reserved for the
    future timed-rounds feature).

    C-D2g: difficulty and leaf_count are optional (the v3 columns, C-D2f). Both
    default to None -- the honest "not applicable / not recorded" value for bank
    responses, the no-rung arithmetic path, and any caller that does not supply
    them. They are written verbatim; the HTTP layer (post_answer) is responsible
    for validating the echoed values before passing them here.
    """
    cursor = connection.execute(
        "INSERT INTO responses "
        "(session_id, question_id, question_text, answer_text, user_input, "
        "correct, elapsed_ms, answered, difficulty, leaf_count) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            session_id,
            question_id,
            question_text,
            answer_text,
            user_input,
            1 if correct else 0,
            elapsed_ms,
            answered,
            difficulty,
            leaf_count,
        ),
    )
    connection.commit()
    return int(cursor.lastrowid)


def list_responses(
    connection: sqlite3.Connection,
    session_id: int,
) -> list[dict]:
    """Return all responses in a session as a list of dicts, ordered by id."""
    cursor = connection.execute(
        "SELECT * FROM responses WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    return [_response_row_to_dict(row) for row in cursor.fetchall()]


def get_session_correctness(
    connection: sqlite3.Connection,
    session_id: int,
) -> list[bool]:
    """Return the ordered sequence of correct/incorrect for a session.

    C-011 support (pulled forward from the C-019 stats work): returns just
    the correct flags in answer order, as a list of bools. Computing the
    summary (total, accuracy, streak) from this sequence is a LOGIC concern
    (summarize_correctness), keeping the streak logic out of SQL. The broader
    category- and time-windowed stats query is get_responses_for_stats below
    (added in C-019a), summarized by summarize_stats.
    """
    cursor = connection.execute(
        "SELECT correct FROM responses WHERE session_id = ? ORDER BY id",
        (session_id,),
    )
    return [bool(row["correct"]) for row in cursor.fetchall()]


def get_responses_for_stats(
    connection: sqlite3.Connection,
    category_id: int | None = None,
    since: str | None = None,
) -> list[dict]:
    """Return response rows for the durable stats view, newest-first.

    C-019a: the broad, cross-session counterpart to get_session_correctness.
    Joins responses -> sessions -> categories so each row carries the owning
    category (the stats view groups by category). This is a pure reader: it
    only filters and returns rows; all aggregation (totals, accuracy, the
    per-category breakdown) is a LOGIC concern (summarize_stats), keeping
    computation out of SQL exactly as the C-011 correctness split does.

    Filters (both optional, AND-combined):
        category_id -- restrict to responses whose session belongs to this
                       category; None means all categories.
        since       -- an ISO 8601 timestamp lower bound (inclusive) compared
                       against responses.answered; None means all time. The
                       caller (HTTP) computes this cutoff from the clock and
                       the requested day window; DATABASE never reads the clock.

    Each returned dict carries: correct (bool), elapsed_ms (int|None),
    answered (str), category_id (int), category_name (str). elapsed_ms is
    SELECTed so the data is available to a future timing feature; v1's
    summarize_stats ignores it. Ordered by answered DESC, id DESC so the most
    recent activity leads (the view renders newest-first).
    """
    clauses = []
    params: list[object] = []
    if category_id is not None:
        clauses.append("s.category_id = ?")
        params.append(category_id)
    if since is not None:
        clauses.append("r.answered >= ?")
        params.append(since)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""

    cursor = connection.execute(
        "SELECT r.correct AS correct, r.elapsed_ms AS elapsed_ms, "
        "r.answered AS answered, c.id AS category_id, c.name AS category_name "
        "FROM responses r "
        "JOIN sessions s ON r.session_id = s.id "
        "JOIN categories c ON s.category_id = c.id"
        + where
        + " ORDER BY r.answered DESC, r.id DESC",
        params,
    )
    return [
        {
            "correct": bool(row["correct"]),
            "elapsed_ms": row["elapsed_ms"],
            "answered": row["answered"],
            "category_id": row["category_id"],
            "category_name": row["category_name"],
        }
        for row in cursor.fetchall()
    ]


# --- LOGIC ---
# Pure functions only. No IO, no DB access, no HTTP. Functions take plain
# data (numbers, strings, dicts, lists) and return plain data. Randomness
# is the one impurity tolerated here: generation draws from the random
# module, which the spec's generator inherently requires.


# C-006: Operator table, expression generation, evaluation, rendering.
#
# The operator table combines the scalar config from CONFIG (C-005) with the
# callables defined here. Per the layering resolution, the callables live in
# LOGIC and the table is assembled here, once, as a module-level constant.
#
# Expression tree shape (spec section 4.3, runtime only -- never stored):
#   internal node: {"op": str, "left": node, "right": node}
#   leaf:          a plain int
# A node's "op" is an operator symbol; left and right are themselves nodes
# or int leaves, allowing nested expressions.


# Operand-generation strategies. Each takes the operator's record and returns
# a (left, right) pair. A strategy OWNS its forbidden-identity referent -- i.e.
# what forbid_identity is checked against -- and declares it via the record's
# forbid_identity_referent field, so a new operator cannot silently inherit
# the wrong meaning. (forbid_identity historically meant raw operands for the
# standard strategy but the derived quotient for division; that ambiguity is
# now explicit in the record, not implicit in which strategy reads it.)


def _generate_operands_standard(
    operator_record: dict,
) -> tuple[int, int]:
    """Generate a (left, right) operand pair for a non-division operator.

    Draws both operands from the record's inclusive [operand_min, operand_max]
    range and rejects pairs whose RAW OPERANDS hit a forbidden-identity value
    (forbid_identity_referent == "operands", ADR-007).

    When the record declares result_constraint == "non_negative" (subtraction),
    the strategy enforces that ONE intent with both its mechanics together:
    it orders the operands so left >= right (result never negative) AND rejects
    equal operands (x - x = 0 is the trivial result). Declaring the invariant
    rather than two independent knobs prevents a future editor from setting
    them inconsistently (e.g. ordering without equal-rejection, leaking 0).
    Rejection-resamples until a valid pair is found.
    """
    minimum = operator_record["operand_min"]
    maximum = operator_record["operand_max"]
    forbidden = operator_record["forbid_identity"]
    non_negative = operator_record.get("result_constraint") == "non_negative"
    while True:
        left_value = random.randint(minimum, maximum)
        right_value = random.randint(minimum, maximum)
        if non_negative and left_value < right_value:
            left_value, right_value = right_value, left_value
        # Referent is the raw operands: reject if either is a forbidden
        # identity value.
        if left_value in forbidden or right_value in forbidden:
            continue
        # The non_negative intent also rejects equal operands, whose result
        # (0) is the trivial case for subtraction.
        if non_negative and left_value == right_value:
            continue
        return left_value, right_value


def _generate_operands_division(
    operator_record: dict,
) -> tuple[int, int]:
    """Generate a (dividend, divisor) pair guaranteeing an integer quotient.

    Picks the divisor and quotient from the record's range, then derives the
    dividend as divisor * quotient (ADR-007). This guarantees exact division
    without post-hoc filtering. The forbidden-identity referent is the derived
    QUOTIENT (forbid_identity_referent == "quotient"): a quotient of 1 makes
    x / x, a trivial identity, so it is rejected.
    """
    minimum = operator_record["operand_min"]
    maximum = operator_record["operand_max"]
    forbidden = operator_record["forbid_identity"]
    while True:
        divisor = random.randint(minimum, maximum)
        quotient = random.randint(minimum, maximum)
        if quotient in forbidden:
            continue
        dividend = divisor * quotient
        return dividend, divisor


def _generate_operands_modulo(
    operator_record: dict,
) -> tuple[int, int]:
    """Generate a (left, divisor) pair for modulo.

    The left operand is drawn from the record's [operand_min, operand_max]
    range; the divisor is drawn from a SECOND range (divisor_min..divisor_max,
    >= 2) declared on the record. left < divisor IS allowed -- a % b == a is a
    legitimate non-trivial case. The forbidden-identity referent is the DIVISOR
    (forbid_identity_referent == "divisor"): a divisor of 1 makes x % 1 == 0
    for every x, a trivial result, so it is rejected.
    """
    left_minimum = operator_record["operand_min"]
    left_maximum = operator_record["operand_max"]
    divisor_minimum = operator_record["divisor_min"]
    divisor_maximum = operator_record["divisor_max"]
    forbidden = operator_record["forbid_identity"]
    while True:
        left_value = random.randint(left_minimum, left_maximum)
        divisor = random.randint(divisor_minimum, divisor_maximum)
        if divisor in forbidden:
            continue
        return left_value, divisor


def _generate_operands_exponent(
    operator_record: dict,
) -> tuple[int, int]:
    """Generate a (base, exponent) pair for exponentiation.

    Mirrors the division strategy's two-range shape: the base is drawn from the
    record's [operand_min, operand_max] range, and the exponent from a SECOND
    narrow range (exponent_min..exponent_max) declared on the record, keeping
    results integer and UI-tractable. The forbidden-identity referent is the
    EXPONENT (forbid_identity_referent == "exponent"): exponent 0 (x^0 == 1)
    and exponent 1 (x^1 == x) are trivial, so both are rejected.
    """
    base_minimum = operator_record["operand_min"]
    base_maximum = operator_record["operand_max"]
    exponent_minimum = operator_record["exponent_min"]
    exponent_maximum = operator_record["exponent_max"]
    forbidden = operator_record["forbid_identity"]
    while True:
        base = random.randint(base_minimum, base_maximum)
        exponent = random.randint(exponent_minimum, exponent_maximum)
        if exponent in forbidden:
            continue
        return base, exponent


# Per-operator records. One record fully defines an operator: the earlier
# split across OPERATOR_CONFIG + _OPERATOR_EVAL_FUNCTIONS +
# _OPERATOR_OPERAND_GENERATORS plus hidden `if symbol == "-"` branches is
# collapsed here, removing the symbol-string-as-foreign-key join.
#
# Record fields:
#   symbol      -- rendered operator string; also the table key
#   name        -- human-readable operator name
#   arity       -- operand count (all current operators binary)
#   operand_min, operand_max -- inclusive operand range (interpreted by the
#                  strategy; division treats it as the divisor/quotient range)
#   forbid_identity -- values rejected at generation to avoid trivial results
#                  (ADR-007)
#   forbid_identity_referent -- WHAT forbid_identity is checked against:
#                  "operands" (raw operands), "quotient" (derived, division),
#                  "divisor" (modulo), or "exponent" (the power). Each strategy
#                  declares its own; see strategy docstrings.
#   result_constraint -- declared invariant the strategy must uphold, or None.
#                  "non_negative" (subtraction) bundles ordering + equal
#                  rejection as one intent.
#   nestable    -- whether this operator may have SUBTREE children (#5). True
#                  for the composable operators (+ - *); False for the leaf-only
#                  operators (/ % ^), whose operands stay integer leaves. NOTE:
#                  nestable governs whether an operator may have subtree
#                  CHILDREN; it does NOT govern whether the operator's node may
#                  itself BE a child -- a / % ^ node is a valid subtree child of
#                  a composable parent.
#   precedence  -- explicit integer binding tier (#5): + - => 1, * / % => 2,
#                  ^ => 3. Compared with < by the renderer to decide
#                  parenthesization. Represented, not inferred from list order.
#   associativity -- "left" or "right" (#5): + - * / % are left-associative;
#                  ^ is right-associative. Drives same-tier wrong-side
#                  parenthesization in the renderer.
#   eval_fn     -- stdlib operator callable; full namespace, no alias
#   operand_strategy -- the generator producing this operator's operand pair
# Some operators carry a SECOND range as extra record fields read only by their
# own strategy (not a generic override -- see the per-operand-range decision):
#   modulo:   divisor_min, divisor_max  (the divisor's range, >= 2)
#   exponent: exponent_min, exponent_max  (the power's range)
OPERATOR_DEFINITIONS: list[dict] = [
    {
        "symbol": "+",
        "name": "addition",
        "arity": 2,
        "operand_min": _DEFAULT_OPERAND_RANGE[0],
        "operand_max": _DEFAULT_OPERAND_RANGE[1],
        "forbid_identity": [0],
        "forbid_identity_referent": "operands",
        "result_constraint": None,
        "nestable": True,
        "precedence": 1,
        "associativity": "left",
        "eval_fn": operator.add,
        "operand_strategy": _generate_operands_standard,
    },
    {
        "symbol": "-",
        "name": "subtraction",
        "arity": 2,
        "operand_min": _DEFAULT_OPERAND_RANGE[0],
        "operand_max": _DEFAULT_OPERAND_RANGE[1],
        "forbid_identity": [0],
        "forbid_identity_referent": "operands",
        # One intent: non-negative, non-trivial result. The standard strategy
        # implements both mechanics (order left >= right; reject equal).
        "result_constraint": "non_negative",
        "nestable": True,
        "precedence": 1,
        "associativity": "left",
        "eval_fn": operator.sub,
        "operand_strategy": _generate_operands_standard,
    },
    {
        "symbol": "*",
        "name": "multiplication",
        "arity": 2,
        "operand_min": _MULTIPLICATIVE_OPERAND_RANGE[0],
        "operand_max": _MULTIPLICATIVE_OPERAND_RANGE[1],
        "forbid_identity": [0, 1],
        "forbid_identity_referent": "operands",
        "result_constraint": None,
        "nestable": True,
        "precedence": 2,
        "associativity": "left",
        "eval_fn": operator.mul,
        "operand_strategy": _generate_operands_standard,
    },
    {
        "symbol": "/",
        "name": "division",
        "arity": 2,
        # The range bounds the divisor and quotient; the dividend is derived
        # as divisor * quotient (ADR-007). Range [2..12] matches the spec.
        "operand_min": _MULTIPLICATIVE_OPERAND_RANGE[0],
        "operand_max": _MULTIPLICATIVE_OPERAND_RANGE[1],
        "forbid_identity": [1],
        # Referent is the derived quotient, not the raw operands: a quotient
        # of 1 makes x / x, a trivial identity.
        "forbid_identity_referent": "quotient",
        "result_constraint": None,
        "nestable": False,
        "precedence": 2,
        "associativity": "left",
        # Floor division (operator.floordiv) is always EXACT here: the dividend
        # is a guaranteed multiple of the divisor (ADR-007), so there is no
        # remainder to floor away; the divisor is never zero (positive range).
        "eval_fn": operator.floordiv,
        "operand_strategy": _generate_operands_division,
    },
    {
        "symbol": "%",
        "name": "modulo",
        "arity": 2,
        # Left operand spans the default range; the divisor has its own range
        # (>= 2) below. left < divisor is allowed -- a % b == a is a valid,
        # non-trivial case.
        "operand_min": _DEFAULT_OPERAND_RANGE[0],
        "operand_max": _DEFAULT_OPERAND_RANGE[1],
        "divisor_min": _MULTIPLICATIVE_OPERAND_RANGE[0],
        "divisor_max": _MULTIPLICATIVE_OPERAND_RANGE[1],
        "forbid_identity": [1],
        # Referent is the divisor: a divisor of 1 makes x % 1 == 0 for every x.
        "forbid_identity_referent": "divisor",
        "result_constraint": None,
        "nestable": False,
        "precedence": 2,
        "associativity": "left",
        "eval_fn": operator.mod,
        "operand_strategy": _generate_operands_modulo,
    },
    {
        "symbol": "^",
        "name": "exponent",
        "arity": 2,
        # Base from the multiplicative range; the power from its own narrow
        # range (_EXPONENT_POWER_RANGE) below, keeping results UI-tractable.
        "operand_min": _MULTIPLICATIVE_OPERAND_RANGE[0],
        "operand_max": _MULTIPLICATIVE_OPERAND_RANGE[1],
        "exponent_min": _EXPONENT_POWER_RANGE[0],
        "exponent_max": _EXPONENT_POWER_RANGE[1],
        "forbid_identity": [0, 1],
        # Referent is the exponent: x^0 == 1 and x^1 == x are trivial.
        "forbid_identity_referent": "exponent",
        "result_constraint": None,
        "nestable": False,
        "precedence": 3,
        "associativity": "right",
        # Right-associativity (2^2^3) is a #5 concern; the flat v1 generator
        # never associates, so it is a non-issue here.
        "eval_fn": operator.pow,
        "operand_strategy": _generate_operands_exponent,
    },
]

# Required keys every record must carry; _build_operator_table validates
# completeness against this set rather than re-joining separate structures.
_OPERATOR_RECORD_REQUIRED_KEYS = frozenset(
    {
        "symbol",
        "name",
        "arity",
        "operand_min",
        "operand_max",
        "forbid_identity",
        "forbid_identity_referent",
        "result_constraint",
        "nestable",
        "precedence",
        "associativity",
        "eval_fn",
        "operand_strategy",
    }
)

# Known forbid-identity referents; a record declaring anything else is a typo
# or an unimplemented strategy contract.
_KNOWN_FORBID_IDENTITY_REFERENTS = frozenset(
    {"operands", "quotient", "divisor", "exponent"}
)


def _build_operator_table() -> dict:
    """Index OPERATOR_DEFINITIONS by symbol, validating record completeness.

    Returns a dict mapping each operator symbol to its record. Because each
    record is now self-contained, this no longer joins four structures; it
    validates that every record is COMPLETE (all required keys present, eval_fn
    and operand_strategy callable, referent known) and that every enabled
    symbol in OPERATOR_SYMBOLS has a record. Raises ValueError at import time
    on any failure -- catching typos early rather than at request time.
    """
    table: dict = {}
    for record in OPERATOR_DEFINITIONS:
        missing = _OPERATOR_RECORD_REQUIRED_KEYS - record.keys()
        if missing:
            raise ValueError(
                "operator record "
                + repr(record.get("symbol", "<no symbol>"))
                + " is missing required keys: "
                + ", ".join(sorted(missing))
            )
        symbol = record["symbol"]
        if not callable(record["eval_fn"]):
            raise ValueError(
                "operator record " + repr(symbol) + " has a non-callable eval_fn"
            )
        if not callable(record["operand_strategy"]):
            raise ValueError(
                "operator record "
                + repr(symbol)
                + " has a non-callable operand_strategy"
            )
        if record["forbid_identity_referent"] not in _KNOWN_FORBID_IDENTITY_REFERENTS:
            raise ValueError(
                "operator record "
                + repr(symbol)
                + " has unknown forbid_identity_referent "
                + repr(record["forbid_identity_referent"])
            )
        if symbol in table:
            raise ValueError("duplicate operator record for symbol " + repr(symbol))
        table[symbol] = record

    for symbol in OPERATOR_SYMBOLS:
        if symbol not in table:
            raise ValueError(
                "enabled operator symbol "
                + repr(symbol)
                + " has no record in OPERATOR_DEFINITIONS"
            )
    return table


# Built once at import. Module-level constant; not rebuilt per request.
OPERATORS: dict = _build_operator_table()


def _draw_composable_leaf(operator_record: dict) -> int:
    """Draw a single integer leaf for a composable operator's operand.

    Bottom-up construction builds each operand of a composable (+ - *) node
    INDEPENDENTLY, so it needs a single-operand draw rather than the paired
    leaf strategy (which bakes in ordering/forbid logic for the flat case). The
    leaf is drawn from the operator's own [operand_min, operand_max] range; the
    forbidden-identity and ordering rules are applied UNIFORMLY afterward by the
    caller against the operand's VALUE (a leaf is its own value), so they cover
    subtree operands too. The composable leaf ranges already start above their
    forbidden values (+ - from 1, * from 2), so a leaf never hits a forbidden
    identity on its own -- the value check only ever rejects a SUBTREE operand
    that happens to evaluate to a forbidden value (e.g. (9 % 3) == 0 under +).
    """
    return random.randint(
        operator_record["operand_min"], operator_record["operand_max"]
    )


def _build_composable_operand(
    symbols: list[str],
    remaining_depth: int,
    operator_record: dict,
    recurse_probability: float,
    operator_table: dict,
    max_result_value: int | None,
) -> dict | int:
    """Build ONE operand of a composable node: a subtree or an integer leaf.

    With depth budget remaining (remaining_depth >= 2, so a child can be at
    least a flat node), flip an independent Bernoulli(recurse_probability): on
    success recurse into build_subtree with the budget decremented; otherwise
    draw an integer leaf. With no budget remaining, always a leaf -- this is the
    depth floor that bounds operator_depth at the caller's depth budget.

    C-D2b: recurse_probability is a PLAIN-DATA PARAMETER threaded from the caller.
    C-D2d: operator_table is threaded so a recursing subtree draws its own
    operator from the same (possibly rung-scaled) table the parent used.
    C-D2e: max_result_value is threaded onward to the recursing build_subtree so
    the whole tree enforces one consistent ceiling (a leaf never needs the
    ceiling -- a bare integer leaf is its own value and was drawn within range).
    """
    if remaining_depth >= 2 and random.random() < recurse_probability:
        return build_subtree(
            symbols,
            remaining_depth - 1,
            recurse_probability,
            operator_table,
            max_result_value,
        )
    return _draw_composable_leaf(operator_record)


def _result_within_ceiling(
    operator_record: dict,
    left_value: int,
    right_value: int,
    max_result_value: int | None,
) -> bool:
    """Local feasibility check for the optional result ceiling (C-D2e).

    Returns True (always feasible) when max_result_value is None -- the default
    (difficulty=None and the lower rungs that declare no ceiling), making this a
    no-op so the generator is identical to the no-ceiling version. Otherwise
    returns whether THIS node's evaluated result is within the ceiling.

    The check is LOCAL and bottom-up: both operand values are already in hand, so
    it evaluates only this node's operator over the two known child values, not
    the whole subtree again. Because a parent only ACCEPTS children whose own
    results already passed this same check, the local bound transitively bounds
    every subtree result -- so a tree assembled entirely from accepted nodes has
    every node result (hence the final result) within the ceiling. ADR-035: the
    ceiling bounds RESULTS, not leaves; operand magnitude is still governed by the
    per-operator ranges, so a too-small ceiling makes a node INFEASIBLE (it can
    never satisfy) rather than merely rare, which the bounded-retry guard turns
    into a loud RuntimeError instead of an infinite loop.

    C-D2e: max_result_value is now a PLAIN-DATA PARAMETER threaded from the
    caller (generate_expression passes the rung's max_result_value, or None on
    the no-rung path), replacing the read of the module-global _MAX_RESULT_VALUE.
    The module constant remains as the documented dark default but is no longer
    read here.
    """
    if max_result_value is None:
        return True
    return operator_record["eval_fn"](left_value, right_value) <= max_result_value


def build_subtree(
    symbols: list[str],
    remaining_depth: int,
    recurse_probability: float = _RECURSE_PROBABILITY,
    operator_table: dict | None = None,
    max_result_value: int | None = None,
) -> dict:
    """Build an expression subtree (an internal node) bottom-up.

    INTERNAL helper for generate_expression (#5). Calls random.* directly -- no
    rng parameter (threading an rng is speculative seedability; tests seed the
    global RNG instead). Returns an {op, left, right} node whose operator_depth
    is at most remaining_depth (>= 1).

    Construction is BOTTOM-UP: for a composable operator (+ - *), each operand
    is built first (subtree or leaf) so its integer VALUE is known, then the
    operator's constraints are checked against those values and the node is
    assembled -- a built subtree is never mutated to fit a parent; on a
    constraint failure the whole node is redrawn. Leaf-only operators (/ % ^)
    keep their existing paired leaf strategy unchanged (their invariants are
    statements about LEAVES -- divisor >= 2, derived quotient, exponent power
    range -- and must not be lifted to values). A leaf-only operator may still
    be CHOSEN here (it is a valid subtree child of a composable parent); it just
    never grows subtree children of its own (nestable=False).

    remaining_depth <= 1 forces a flat node: no operand recurses, reproducing
    the #4 generator exactly. Each redraw counts against _MAX_GENERATION_ATTEMPTS
    and raises RuntimeError on exhaustion rather than looping forever.

    C-D2b (THE WELD): recurse_probability is a PLAIN-DATA PARAMETER (door D1
    opened with its real caller, generate_expression). It defaults to the module
    constant _RECURSE_PROBABILITY so existing direct callers and the
    difficulty=None path are byte-identical to before; a difficulty rung passes
    the rung's recurse_probability instead. operator_depth is threaded as the
    EXISTING remaining_depth parameter (generate_expression chooses its starting
    value from the rung or the module _MAX_OPERATOR_DEPTH).

    C-D2d: operator_table is the (possibly rung-scaled) operator table to draw
    records from. None -> the module-global OPERATORS (the default ranges,
    byte-identical to before). generate_expression overlays a rung's per-operator
    ranges onto a COPY via _apply_rung_ranges and passes that table here, so a
    rung changes operand MAGNITUDE. The table is threaded onward to
    _build_composable_operand so recursing subtrees use the same scaled records.

    C-D2e: max_result_value is the rung's result ceiling (None -> no ceiling, the
    default and the lower rungs). Threaded into every _result_within_ceiling call
    and onward to recursing subtrees. Because the check is local and bottom-up
    and a parent only accepts ceiling-passing children, the whole tree's results
    stay within the ceiling. A ceiling too low for an operator's minimum result
    makes that operator infeasible; the bounded-retry guard then raises
    RuntimeError rather than looping (the joint (ranges, ceiling) satisfiability
    is asserted per rung in the C-D2e tests).
    """
    if operator_table is None:
        operator_table = OPERATORS
    attempts = 0
    while True:
        attempts += 1
        if attempts > _MAX_GENERATION_ATTEMPTS:
            raise RuntimeError(
                "build_subtree exceeded "
                + str(_MAX_GENERATION_ATTEMPTS)
                + " attempts; operator constraints appear unsatisfiable for "
                "symbols " + repr(symbols)
            )
        symbol = random.choice(symbols)
        operator_record = operator_table[symbol]

        # Leaf-only (/ % ^): integer leaves via the existing paired strategy,
        # invariants unchanged. Also the only path when no depth budget remains
        # for a composable operator (handled below by the leaf-only operand
        # builder), but a leaf-only operator takes this branch regardless.
        if not operator_record["nestable"]:
            left_value, right_value = operator_record["operand_strategy"](
                operator_record
            )
            if not _result_within_ceiling(
                operator_record, left_value, right_value, max_result_value
            ):
                continue
            return {"op": symbol, "left": left_value, "right": right_value}

        # Composable (+ - *). At the depth floor (remaining_depth <= 1) no
        # operand may recurse, so use the existing paired strategy verbatim --
        # this is what makes operator_depth == 1 reproduce flat #4 exactly.
        if remaining_depth <= 1:
            left_value, right_value = operator_record["operand_strategy"](
                operator_record
            )
            if not _result_within_ceiling(
                operator_record, left_value, right_value, max_result_value
            ):
                continue
            return {"op": symbol, "left": left_value, "right": right_value}

        # Budget remains: build each operand independently (subtree or leaf),
        # then apply the value-based constraints (constraint lifting). The
        # per-tree recurse_probability is threaded into each operand build.
        left = _build_composable_operand(
            symbols,
            remaining_depth,
            operator_record,
            recurse_probability,
            operator_table,
            max_result_value,
        )
        right = _build_composable_operand(
            symbols,
            remaining_depth,
            operator_record,
            recurse_probability,
            operator_table,
            max_result_value,
        )
        left_value = evaluate_expression(left)
        right_value = evaluate_expression(right)

        # Subtraction: order by EVALUATED value (left >= right) and reject equal
        # (result 0 is trivial). Swapping the operand POSITIONS is arrangement,
        # not mutation of a built node.
        if operator_record.get("result_constraint") == "non_negative":
            if left_value < right_value:
                left, right = right, left
                left_value, right_value = right_value, left_value
            if left_value == right_value:
                continue

        # Forbidden-identity lifted to VALUE for + (forbid 0) and * (forbid
        # 0 and 1): a * (subtree evaluating to 1) is the trivial identity.
        forbidden = operator_record["forbid_identity"]
        if left_value in forbidden or right_value in forbidden:
            continue

        # Optional result ceiling: redraw this node's operands if the assembled
        # result would exceed the ceiling. Local: only this node's children are
        # discarded, not the whole tree. None -> no ceiling (the default path).
        if not _result_within_ceiling(
            operator_record, left_value, right_value, max_result_value
        ):
            continue

        return {"op": symbol, "left": left, "right": right}


def _resolve_difficulty_rung(difficulty: int) -> dict:
    """Resolve a scalar difficulty rung to its DIFFICULTY_RUNGS record (C-D2b).

    Pure lookup by the rung label. Raises ValueError on an unknown rung -- this
    is a PROGRAMMING-ERROR guard, not user-input handling: the HTTP layer
    validates ?difficulty= against the known rung range and returns a 400 before
    calling generate_expression (mirroring how ?operators= is validated against
    OPERATORS up front). Reaching here with a bad rung therefore means an
    internal caller passed an out-of-range value, so fail loudly rather than
    silently falling back to a default rung.

    Returns the full rung record; in C-D2b only operator_depth and
    recurse_probability are CONSUMED (the shape knobs). operator_ranges and
    max_result_value are present on the record but not yet applied -- C-D2d and
    C-D2e wire those.
    """
    for rung_record in DIFFICULTY_RUNGS:
        if rung_record["rung"] == difficulty:
            return rung_record
    known = [rung_record["rung"] for rung_record in DIFFICULTY_RUNGS]
    raise ValueError(
        "unknown difficulty rung "
        + repr(difficulty)
        + "; known rungs are "
        + repr(known)
    )


def _apply_rung_ranges(rung_record: dict, base_table: dict) -> dict:
    """Overlay a rung's per-operator range fields onto a base operator table (C-D2d).

    PURE: returns a NEW operator table (a fresh dict of fresh record dicts);
    base_table and its records are never mutated, so the module-global OPERATORS
    stays the canonical default and is safe to reuse across requests. This is the
    magnitude lever -- the rung's operator_ranges replace ONLY the range fields
    each operator's strategy reads (operand_min/max for all; divisor_min/max for
    %; exponent_min/max for ^), leaving every other record field (eval_fn,
    operand_strategy, nestable, forbid_identity, precedence, ...) untouched. So
    the generator's behavior is identical except for the magnitudes it draws.

    A rung need not list every operator: an operator absent from operator_ranges
    keeps its base-table range verbatim (the rung "only states what it CHANGES",
    per the DIFFICULTY_RUNGS docstring). A field absent from a listed operator's
    range dict likewise keeps its base value -- the overlay is field-level, not
    record-replacement, so e.g. a rung that scales only operand_min/max for %
    leaves that operator's divisor_min/max at the base.

    The import-time guard (_check_difficulty_rungs_consistency) has already
    proven every declared field is one the operator legitimately reads, so this
    overlay never introduces a field a strategy ignores.
    """
    new_table = {}
    for symbol, base_record in base_table.items():
        overrides = rung_record["operator_ranges"].get(symbol)
        if not overrides:
            # Operator not scaled by this rung: reuse the base record as-is.
            # Safe because we never mutate records; the new table just points at
            # the same immutable-by-convention record object.
            new_table[symbol] = base_record
            continue
        # Field-level overlay onto a COPY, so the base record is untouched.
        scaled_record = dict(base_record)
        for field_name, field_value in overrides.items():
            scaled_record[field_name] = field_value
        new_table[symbol] = scaled_record
    return new_table


def generate_expression(
    enabled_symbols: list[str] | None = None,
    difficulty: int | None = None,
) -> dict:
    """Generate an arithmetic expression tree, possibly nested (#5, #2).

    Picks operators at random from enabled_symbols (defaulting to the module
    OPERATOR_SYMBOLS) and builds a tree bottom-up via build_subtree. Composable
    operators (+ - *) may have subtree children; leaf-only operators (/ % ^)
    keep integer leaves.

    DIFFICULTY (C-D2b): difficulty is an optional scalar rung. When None (the
    default), generation is BYTE-IDENTICAL to before -- it uses the module
    constants _MAX_OPERATOR_DEPTH and _RECURSE_PROBABILITY, so an existing caller
    that passes no difficulty (the no-parameter live endpoint path, Q6) sees no
    behavior change. When a rung is given, it is resolved against DIFFICULTY_RUNGS
    to per-rung operator_depth and recurse_probability, which are threaded as
    plain-data parameters into build_subtree (door D1, opened with its real
    caller per ADR-034). operator_depth == 1 reproduces the flat #4 generator
    exactly.

    SCOPE NOTE (C-D2e completes the generator response): a rung now changes tree
    depth, nesting probability, per-operator operand magnitude (C-D2d), AND
    applies its result ceiling (max_result_value) -- the full generator-side
    difficulty response. A rung with max_result_value None has no ceiling. The
    tree shape feeds evaluate_expression and render_expression unchanged.
    """
    # Distinguish "omitted" (None -> use the default set) from "given but
    # empty" ([] -> an error). Treating [] as falsy and silently falling back
    # to all operators would mask a caller that meant to restrict generation
    # and produced an empty set (e.g. a query string that parsed to no valid
    # symbols).
    symbols = OPERATOR_SYMBOLS if enabled_symbols is None else enabled_symbols
    if not symbols:
        raise ValueError("generate_expression requires at least one operator symbol")
    unknown = [symbol for symbol in symbols if symbol not in OPERATORS]
    if unknown:
        # A caller passed a symbol with no operator-table entry. HTTP already
        # validates ?operators= against OPERATORS, so reaching here means a
        # programming error rather than bad user input -- fail loudly.
        raise ValueError(
            "generate_expression got unknown operator symbols: "
            + ", ".join(repr(symbol) for symbol in unknown)
        )

    # difficulty=None: the module-constant defaults, byte-identical to today.
    # A rung: resolve to its shape knobs (depth + recurse), overlay its
    # per-operator ranges (magnitude, C-D2d), AND apply its result ceiling
    # (C-D2e). A rung whose max_result_value is None has no ceiling.
    if difficulty is None:
        operator_depth = _MAX_OPERATOR_DEPTH
        recurse_probability = _RECURSE_PROBABILITY
        operator_table = OPERATORS
        max_result_value = _MAX_RESULT_VALUE
    else:
        rung_record = _resolve_difficulty_rung(difficulty)
        operator_depth = rung_record["operator_depth"]
        recurse_probability = rung_record["recurse_probability"]
        operator_table = _apply_rung_ranges(rung_record, OPERATORS)
        max_result_value = rung_record["max_result_value"]

    return build_subtree(
        symbols, operator_depth, recurse_probability, operator_table, max_result_value
    )


def evaluate_expression(node: dict | int) -> int:
    """Evaluate an expression tree to an integer result.

    Recursively evaluates internal nodes by applying the operator's eval
    function to its evaluated operands; integer leaves return themselves.
    Pure and deterministic: the same tree always evaluates to the same
    result.
    """
    if isinstance(node, int):
        return node
    if not isinstance(node, dict) or "op" not in node:
        raise ValueError(
            "evaluate_expression expected an int leaf or an {op,left,right} "
            "node, got " + repr(node)
        )
    if node["op"] not in OPERATORS:
        raise ValueError("evaluate_expression got unknown operator " + repr(node["op"]))
    operator_record = OPERATORS[node["op"]]
    left_value = evaluate_expression(node["left"])
    right_value = evaluate_expression(node["right"])
    return operator_record["eval_fn"](left_value, right_value)


def leaf_count(node: dict | int) -> int:
    """Count the integer leaves in an expression tree (C-D2a, ADR-038).

    The structural difficulty proxy for the #2 model: an integer leaf is one
    minimal input the solver must hold, so leaf_count is the element-
    interactivity / minimal-input analog. A flat node (two int leaves) has
    leaf_count 2; each level of nesting adds leaves. It is a pure function of
    TREE SHAPE only -- it does not depend on operator_depth, operand magnitude,
    or which operators appear (a deep all-+ tree and a deep all-* tree of the
    same shape have the same leaf_count). That independence is exactly why it is
    the COORDINATION-regime feature (handoff Q1/S7): for composable-containing
    mixes it moves monotonically with the rung's depth/recurse knobs, while for
    leaf-only mixes (/ % ^, which cannot nest) it is a CONSTANT 2 and difficulty
    must ride magnitude instead.

    It is also the NON-DRIFTING fact stored on responses (ADR-040): recomputable
    from question_text by re-parsing, unlike the rung label, which re-means if a
    later thread re-tunes the rung table. Recurses over the same {op,left,right}
    shape as evaluate_expression; an int leaf is 1, an internal node is the sum
    of its children's leaf counts.
    """
    if isinstance(node, int):
        return 1
    if not isinstance(node, dict) or "op" not in node:
        raise ValueError(
            "leaf_count expected an int leaf or an {op,left,right} node, got "
            + repr(node)
        )
    return leaf_count(node["left"]) + leaf_count(node["right"])


def _child_needs_parentheses(parent_record: dict, child: dict | int, side: str) -> bool:
    """Decide whether a rendered child operand must be parenthesized.

    The renderer is the SOLE owner of correct printing (#5): the tree shape is
    the grouping truth, and the rendered string must, read under standard
    precedence and associativity, parse back to THIS tree. evaluate_expression
    never consults precedence -- a wrong parenthesization silently makes the
    displayed question and the stored answer disagree.

    A child is wrapped IFF it is an INTERNAL node AND either
      - its operator binds LESS tightly than the parent
        (child.precedence < parent.precedence), or
      - it binds EQUALLY tightly but sits on the associativity-WRONG side:
        the right child of a left-associative parent, or the left child of a
        right-associative parent. (On the associativity-correct side, equal
        precedence needs no parens: a - b + c is (a-b)+c with no wrapping.)
    An integer leaf is never wrapped.
    """
    if not isinstance(child, dict):
        return False
    child_record = OPERATORS[child["op"]]
    if child_record["precedence"] < parent_record["precedence"]:
        return True
    if child_record["precedence"] == parent_record["precedence"]:
        parent_associativity = parent_record["associativity"]
        wrong_side = "right" if parent_associativity == "left" else "left"
        if side == wrong_side:
            return True
    return False


def render_expression(node: dict | int) -> str:
    """Render an expression tree as a human-readable infix string.

    Integer leaves render as their digits. Internal nodes render as
    "left symbol right", with each child parenthesized only when the tree's
    grouping would otherwise be lost under standard precedence/associativity
    (see _child_needs_parentheses). A flat single-operator expression (the v1
    case) has int leaves, so it produces no parentheses. The rendered string is
    what gets stored in responses.question_text.
    """
    if isinstance(node, int):
        return str(node)
    parent_record = OPERATORS[node["op"]]
    left_text = render_expression(node["left"])
    right_text = render_expression(node["right"])
    if _child_needs_parentheses(parent_record, node["left"], "left"):
        left_text = "(" + left_text + ")"
    if _child_needs_parentheses(parent_record, node["right"], "right"):
        right_text = "(" + right_text + ")"
    return left_text + " " + node["op"] + " " + right_text


# C-007: Answer validation.
# Pure functions. Two public functions: normalize_text (the text
# normalization pipeline) and validate_answer (the dispatcher across qtypes).
# free_response, translate, and identify share one normalized-text path;
# multiple_choice does an exact comparison of server-generated strings;
# arithmetic parses the input as a number and compares within a tolerance.


# Punctuation stripped during normalization. Deliberately excludes hyphens
# and apostrophes: "well-known" vs "wellknown" and "don't" vs "dont" are
# real distinctions in vocabulary drills (decision in C-007 feedback).
_STRIP_PUNCTUATION = ",.!?:;"

# Quote and bracket characters stripped only from the outer edges of the
# text (surrounding quotes and parentheses), not from the interior.
_STRIP_OUTER_CHARACTERS = "\"'()"

# Matches any run of whitespace, for collapsing internal whitespace to a
# single space.
_WHITESPACE_RUN = re.compile(r"\s+")


def normalize_text(text: str) -> str:
    """Normalize free-text for lenient answer comparison.

    Pipeline: lowercase; remove the defined interior punctuation set
    (commas, periods, exclamation/question marks, colons, semicolons);
    collapse internal whitespace runs to single spaces; trim outer
    whitespace; strip surrounding quotes and parentheses from the ends.

    Does NOT strip hyphens, apostrophes, or Unicode accents -- these carry
    meaning in language drills (decision in C-007 feedback). Accent
    sensitivity means an answer written with accents must be typed with
    them; a per-bank accent_insensitive flag is a possible future addition.
    """
    lowered = text.lower()
    without_punctuation = "".join(
        character for character in lowered if character not in _STRIP_PUNCTUATION
    )
    collapsed = _WHITESPACE_RUN.sub(" ", without_punctuation).strip()
    return collapsed.strip(_STRIP_OUTER_CHARACTERS).strip()


def _validate_numeric(given: str, expected: str, tolerance: float | None) -> bool:
    """Compare a numeric answer to the expected value within a tolerance.

    Parses both sides as floats. A tolerance of None (or 0) requires exact
    equality; a positive tolerance accepts answers within that absolute
    difference (for future float-producing operators). Non-numeric input
    (e.g. letters typed for a math question) is simply an incorrect answer,
    returning False rather than raising.

    A non-numeric tolerance (e.g. a stray string from a client) is treated as
    no tolerance (exact match) rather than raising, so a malformed optional
    field cannot crash the validator.
    """
    try:
        given_value = float(given.strip())
        expected_value = float(str(expected).strip())
    except (ValueError, AttributeError):
        return False

    numeric_tolerance: float | None
    try:
        numeric_tolerance = None if tolerance is None else float(tolerance)
    except (ValueError, TypeError):
        numeric_tolerance = None

    if numeric_tolerance is None or numeric_tolerance == 0:
        return given_value == expected_value
    return abs(given_value - expected_value) <= numeric_tolerance


def validate_answer(
    expected: str,
    given: str,
    qtype: str,
    alternatives: list[str] | None = None,
    tolerance: float | None = None,
) -> bool:
    """Return whether the user's answer is correct for the given qtype.

    Dispatch by qtype:
      free_response / translate / identify -- normalize both sides and check
        given against [expected] + alternatives, returning True on the first
        normalized match. These three share one path in v1; identify and
        free_response are presently identical, with qtype kept in the
        signature so the paths can diverge later without a signature change.
      multiple_choice -- exact string comparison of given against expected.
        Both strings are server-generated (the server builds the shuffled
        options and the user submits the chosen option's text), so no
        normalization is needed.
      arithmetic -- parse given as a number and compare to expected within
        tolerance.

    An unrecognized qtype returns False rather than raising, so a bad qtype
    can never be silently scored correct.
    """
    if qtype == QTYPE_ARITHMETIC:
        return _validate_numeric(given, expected, tolerance)

    if qtype == QTYPE_MULTIPLE_CHOICE:
        return given == expected

    if qtype in (QTYPE_FREE_RESPONSE, QTYPE_TRANSLATE, QTYPE_IDENTIFY):
        normalized_given = normalize_text(given)
        acceptable = [expected] + (alternatives or [])
        for candidate in acceptable:
            if normalize_text(candidate) == normalized_given:
                return True
        return False

    return False


# C-008: Import parsing (JSON Lines and CSV).
# Pure functions that turn raw uploaded text into a list of canonical
# question dicts ready for DATABASE.insert_questions_bulk (C-003). JSONL is
# the canonical format (ADR-004); CSV is a convenience adapter that produces
# the identical dict shape. Both routes converge through
# _normalize_question_dict, which is the single place that validates required
# fields and fills optional defaults -- so the bulk insert can assume valid
# dicts (decision in C-003).

# Within a CSV cell, array-valued fields (alternatives, distractors, hints,
# tags) are pipe-separated, because the comma is the CSV column delimiter and
# would collide. Example: a tags cell "capital|europe|france" becomes
# ["capital", "europe", "france"].
_CSV_ARRAY_SEPARATOR = "|"

# The array-valued optional fields, handled uniformly by both parsers.
_ARRAY_FIELDS = ("alternatives", "distractors", "hints", "tags")


class ImportParseError(ValueError):
    """Raised when import text cannot be parsed into valid question dicts.

    Carries a human-readable message naming the offending line or field so
    the HTTP layer can report which row of an upload failed.
    """


def _coerce_difficulty(value: object) -> int | None:
    """Coerce a difficulty value to an int in 1..5, or None.

    Accepts None, empty string, or a parseable integer. Returns None for
    absent/empty input. Raises ImportParseError for a present but invalid
    value (non-integer, or out of the 1..5 range from the data model).
    """
    if value is None or value == "":
        return None
    try:
        difficulty = int(value)
    except (ValueError, TypeError):
        raise ImportParseError("difficulty must be an integer 1-5, got " + repr(value))
    if difficulty < 1 or difficulty > 5:
        raise ImportParseError(
            "difficulty must be between 1 and 5, got " + repr(difficulty)
        )
    return difficulty


def _normalize_question_dict(raw: dict) -> dict:
    """Validate and normalize one raw record into a canonical question dict.

    Required fields: question and answer, both non-empty after stripping.
    qtype defaults to free_response and, if present, must be one of QTYPES.
    The four array fields default to empty lists. media_url defaults to None.
    difficulty is coerced to an int 1..5 or None. The returned dict has
    exactly the keys insert_questions_bulk consumes.

    Raises ImportParseError naming the problem when a record is invalid.
    """
    question = raw.get("question")
    answer = raw.get("answer")
    if question is None or str(question).strip() == "":
        raise ImportParseError("record is missing a non-empty 'question'")
    if answer is None or str(answer).strip() == "":
        raise ImportParseError("record is missing a non-empty 'answer'")

    qtype = raw.get("qtype") or QTYPE_FREE_RESPONSE
    if qtype not in QTYPES:
        raise ImportParseError(
            "qtype must be one of " + repr(QTYPES) + ", got " + repr(qtype)
        )

    normalized = {
        "qtype": qtype,
        "question": str(question),
        "answer": str(answer),
        "media_url": raw.get("media_url") or None,
        "difficulty": _coerce_difficulty(raw.get("difficulty")),
    }
    for field in _ARRAY_FIELDS:
        value = raw.get(field)
        if value is None or value == "":
            normalized[field] = []
        elif isinstance(value, list):
            normalized[field] = [str(item) for item in value]
        else:
            raise ImportParseError(
                "field " + repr(field) + " must be a list, got " + repr(value)
            )
    return normalized


def parse_jsonl(text: str) -> list[dict]:
    """Parse JSON Lines import text into a list of canonical question dicts.

    One JSON object per line (ADR-004). Blank lines and lines that are only
    whitespace are skipped, so trailing newlines are harmless. Each object is
    normalized and validated. Raises ImportParseError naming the line number
    (1-based) when a line is not valid JSON or fails validation.
    """
    questions = []
    for line_number, line in enumerate(text.splitlines(), start=1):
        if line.strip() == "":
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise ImportParseError(
                "line " + str(line_number) + " is not valid JSON: " + str(error)
            )
        if not isinstance(raw, dict):
            raise ImportParseError("line " + str(line_number) + " is not a JSON object")
        try:
            questions.append(_normalize_question_dict(raw))
        except ImportParseError as error:
            raise ImportParseError("line " + str(line_number) + ": " + str(error))
    return questions


def parse_csv(text: str) -> list[dict]:
    """Parse CSV import text into a list of canonical question dicts.

    Expects a header row naming columns; question and answer columns are
    required, the rest optional. Array-valued columns (alternatives,
    distractors, hints, tags) hold pipe-separated values within a single
    cell, since the comma is the column delimiter. Empty cells become absent
    fields (handled as defaults by normalization). Produces the same dict
    shape as parse_jsonl. Raises ImportParseError naming the row number
    (1-based, excluding the header) when a row fails validation.
    """
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return []

    questions = []
    for row_number, row in enumerate(reader, start=1):
        # Split pipe-separated array cells into lists before normalizing.
        prepared: dict = {}
        for key, value in row.items():
            if key is None:
                continue
            if key in _ARRAY_FIELDS:
                if value is None or value.strip() == "":
                    prepared[key] = []
                else:
                    prepared[key] = [
                        item.strip()
                        for item in value.split(_CSV_ARRAY_SEPARATOR)
                        if item.strip() != ""
                    ]
            else:
                prepared[key] = value
        try:
            questions.append(_normalize_question_dict(prepared))
        except ImportParseError as error:
            raise ImportParseError("row " + str(row_number) + ": " + str(error))
    return questions


def parse_import(text: str, file_format: str) -> list[dict]:
    """Dispatch import parsing by format string ("jsonl" or "csv").

    The HTTP layer determines the format from the upload's file extension or
    an explicit format parameter and passes it here. Both formats yield the
    same canonical list of question dicts. Raises ImportParseError for an
    unrecognized format.
    """
    if file_format == "jsonl":
        return parse_jsonl(text)
    if file_format == "csv":
        return parse_csv(text)
    raise ImportParseError(
        "unknown import format " + repr(file_format) + "; expected 'jsonl' or 'csv'"
    )


# C-011 support: session stats summary (pure). Takes the ordered correctness
# sequence from DATABASE.get_session_correctness and computes the summary the
# UI stats bar shows. Streak is the count of consecutive correct answers
# ending at the most recent response (a current run), which is natural in
# Python and awkward in SQL -- hence the split.


def summarize_correctness(correctness: list[bool]) -> dict:
    """Summarize an ordered correct/incorrect sequence for the stats bar.

    Returns a dict with:
        total    -- number of answers
        correct  -- number marked correct
        accuracy -- correct / total as a float, or 0.0 when total is 0
        streak   -- length of the current run of consecutive correct answers
                    counting backward from the most recent answer (0 if the
                    most recent answer was incorrect or there are none)
    Pure and deterministic.
    """
    total = len(correctness)
    # An empty sequence (a session with no answers yet -- the very first
    # question, or a freshly started session) yields zeros and a 0.0 accuracy
    # rather than a division error. This is the time-zero case for every new
    # session and must be handled, not asserted away.
    correct_count = sum(1 for is_correct in correctness if is_correct)
    accuracy = (correct_count / total) if total > 0 else 0.0

    streak = 0
    for is_correct in reversed(correctness):
        if not is_correct:
            break
        streak += 1

    return {
        "total": total,
        "correct": correct_count,
        "accuracy": accuracy,
        "streak": streak,
    }


def summarize_stats(rows: list[dict]) -> dict:
    """Summarize durable cross-session stats for the stats view (C-019a).

    Pure counterpart to the DATABASE reader get_responses_for_stats. Takes the
    response rows it returns (each with at least `correct` and the owning
    `category_id`/`category_name`) and produces the text-only summary the view
    renders (section 9 -- no charts in v1):

        total      -- number of responses in the window/filter
        correct    -- number marked correct
        accuracy   -- correct / total as a float, or 0.0 when total is 0
        categories -- per-category breakdown, a list of
                      {category_id, category_name, total, correct, accuracy},
                      ordered by descending total then category name, so the
                      most-practiced category leads

    The empty case (a fresh database, or a window/filter with no responses)
    yields total 0, accuracy 0.0, and an empty categories list rather than a
    division error -- the time-zero case, handled like summarize_correctness.

    elapsed_ms is deliberately IGNORED in v1: timing collection began at C-018c
    but the timing FEATURE (any per-answer or aggregate timing metric) is a
    deferred future commit. The rows carry elapsed_ms so that feature can use
    it later without a new query; this summary simply does not read it.

    Pure and deterministic (the category ordering is total/name, not input
    order, so the same rows always summarize identically).
    """
    total = len(rows)
    correct_count = sum(1 for row in rows if row.get("correct"))
    accuracy = (correct_count / total) if total > 0 else 0.0

    # Group by category, preserving each category's id and display name.
    grouped: dict[int, dict] = {}
    for row in rows:
        category_id = row.get("category_id")
        bucket = grouped.get(category_id)
        if bucket is None:
            bucket = {
                "category_id": category_id,
                "category_name": row.get("category_name"),
                "total": 0,
                "correct": 0,
            }
            grouped[category_id] = bucket
        bucket["total"] += 1
        if row.get("correct"):
            bucket["correct"] += 1

    categories = []
    for bucket in grouped.values():
        bucket_total = bucket["total"]
        bucket["accuracy"] = (
            (bucket["correct"] / bucket_total) if bucket_total > 0 else 0.0
        )
        categories.append(bucket)

    # Most-practiced first; name as a stable tiebreak so the order is
    # deterministic regardless of dict/input ordering. (name may be None only
    # for malformed data; coerce to "" for a total-safe sort key.)
    categories.sort(key=lambda entry: (-entry["total"], entry["category_name"] or ""))

    return {
        "total": total,
        "correct": correct_count,
        "accuracy": accuracy,
        "categories": categories,
    }


# C-012: bank question selection and payload assembly (pure LOGIC).
# pick_next_question chooses one question dict from a list of candidates
# (fetched by HTTP from DATABASE -- LOGIC never queries the DB). v1 uses
# simple random selection with a soft avoid-recent rule; adaptive selection
# is explicitly out of scope (ADR-005, section 9). build_question_payload
# turns a stored question dict into the client-facing payload, including the
# shuffled options list for multiple_choice (the C-007 options contract).


def pick_next_question(
    candidates: list[dict],
    history: list[int] | None = None,
) -> dict | None:
    """Choose the next question from candidates, softly avoiding recent ids.

    candidates is a list of question dicts (as returned by DATABASE). history
    is a list of recently served question ids, most-recent-last. Returns one
    chosen question dict, or None when candidates is empty.

    Policy (v1, non-adaptive): prefer a uniformly random pick from the
    candidates whose id is not in the recent-history window; if that filtered
    set is empty (e.g. the bank is smaller than the window, or every
    candidate was recently seen), fall back to a uniformly random pick from
    all candidates. This avoids immediate repeats when the bank is large
    enough without ever failing to return a question.
    """
    if not candidates:
        return None

    recent = set(history or [])
    fresh = [question for question in candidates if question.get("id") not in recent]
    pool = fresh if fresh else candidates
    return random.choice(pool)


def build_question_payload(question: dict) -> dict:
    """Build the client-facing question payload from a stored question dict.

    The payload mirrors the shape the arithmetic branch returns, so the
    client handles both uniformly and echoes it back to /api/answer:
        qtype, question_text, expected, question_id, alternatives, media_url
    For multiple_choice, an additional "options" list is included: the
    correct answer plus the question's distractors, shuffled, so the UI can
    render choices. The user submits the chosen option's text, which
    validate_answer exact-matches against expected (C-007 contract). For
    non-multiple_choice types, alternatives carries the also-acceptable
    answers and no options list is present.
    """
    required_keys = ("qtype", "question", "answer", "id")
    missing = [key for key in required_keys if key not in question]
    if missing:
        # A question dict reaching here always comes from DATABASE row
        # conversion, which always supplies these keys. Missing keys mean a
        # programming error upstream, so fail loudly rather than emitting a
        # payload with null question_text/expected that the client would
        # silently mis-grade against.
        raise ValueError(
            "build_question_payload got a question missing required keys: "
            + ", ".join(missing)
        )
    payload = {
        "qtype": question["qtype"],
        "question_text": question["question"],
        "expected": question["answer"],
        "question_id": question["id"],
        "alternatives": question.get("alternatives") or [],
        "media_url": question.get("media_url"),
    }
    # ---- C-018b scaffold: deferred "Option A" (per-question language) -------
    # TTS (C-018a) needs a language code to pronounce a prompt. It currently
    # resolves one CLIENT-SIDE from the selected bank (banks.language, already
    # sent by GET /api/banks), so this payload deliberately carries NO
    # "language" field and the backend stays frozen.
    #
    # The future, more general path ("Option A") is to thread language THROUGH
    # this payload instead. That would matter when language is a property of
    # the QUESTION rather than the bank -- e.g. a single mixed-language bank,
    # or per-row language overrides -- which the client's bank-level lookup
    # cannot express. Shipping it would mean, in rough order:
    #   1. carry a language up to here -- either as question["language"] (new
    #      per-question column or metadata key, a schema/import change) or by
    #      passing the owning bank's language in as a parameter, e.g.
    #          def build_question_payload(question, *, bank_language=None)
    #      and setting payload["language"] = question.get("language")
    #      or bank_language;
    #   2. have the bank-question handler below fetch the bank row (it already
    #      has bank_id) and pass bank_language=bank["language"] (see the
    #      matching comment at the call site);
    #   3. update the section-6 payload contract + the frontend to prefer
    #      payload.language over the client bank lookup when present.
    #
    # This is intentionally NOT built here: it changes the frozen backend and
    # the API contract, so per the working agreement it needs its own spec
    # amendment and commit. Until then, build_question_payload stays a pure
    # function of the question dict alone. See DECISIONS C-018b.
    # -------------------------------------------------------------------------
    if question["qtype"] == QTYPE_MULTIPLE_CHOICE:
        options = [question["answer"]] + list(question.get("distractors") or [])
        random.shuffle(options)
        payload["options"] = options
    return payload


# --- HTTP ---
# Thin Bottle route handlers. Each handler parses the request, calls into
# DATABASE and LOGIC, and formats the JSON response. No business logic lives
# here: an if-statement that is not about request parsing or response
# formatting belongs in LOGIC. HTTP is the only layer that reads the clock
# and the only glue between DATABASE output and LOGIC input.
#
# All endpoints from spec section 6 are implemented, including GET /api/stats
# (C-019a). Handlers open a SQLite connection per request and close it in a
# finally block. Integer fields from the request are parsed through _require_int / _optional_int so malformed values yield a
# 400 rather than an unhandled exception, and database integrity conflicts
# (e.g. a referenced id deleted in another tab) are caught and returned as a
# 400 with a clear message.

# Directory of this module, used to locate the index.html served at root.
_MODULE_DIRECTORY = os.path.dirname(os.path.abspath(__file__))

# The Bottle application. Routes are attached to this app object rather than
# the module-global default, so the server is explicit and testable.
app = bottle.Bottle()

# Database path the handlers open per request. MAIN may override this at
# startup; handlers read it here so tests can point at a temporary database.
DATABASE_PATH = DEFAULT_DATABASE_PATH


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


@app.get("/")
def serve_index():
    """Serve the single-page frontend (index.html). [stub -> C-013]"""
    return bottle.static_file("index.html", root=_MODULE_DIRECTORY)


@app.get("/api/categories")
def get_categories():
    """List all categories as JSON.

    C-010: opens a connection, reads categories via DATABASE.list_categories,
    returns them under a "categories" key.
    """
    connection = connect(DATABASE_PATH)
    try:
        categories = list_categories(connection)
    finally:
        connection.close()
    return {"categories": categories}


@app.get("/api/banks")
def get_banks():
    """List banks as JSON, optionally filtered by category_id.

    C-010: reads the optional category_id query parameter, validates it as an
    integer when present, and returns matching banks via DATABASE.list_banks.
    """
    category_id_raw = bottle.request.query.get("category_id")
    category_id = None
    if category_id_raw is not None and category_id_raw != "":
        try:
            category_id = int(category_id_raw)
        except ValueError:
            return _json_error("category_id must be an integer", status=400)
    connection = connect(DATABASE_PATH)
    try:
        banks = list_banks(connection, category_id)
    finally:
        connection.close()
    return {"banks": banks}


@app.get("/api/question")
def get_question_endpoint():
    """Get the next question. Branches on category: arithmetic vs bank.

    C-011 implements the arithmetic branch. The bank branch is C-012.

    Arithmetic (category=arithmetic): generates an expression, evaluates it,
    and returns a question payload the client echoes back to /api/answer.
    Optional query parameter operators is a comma-separated list of operator
    symbols to restrict generation (e.g. operators=+,-); absent means all
    enabled operators. Optional query parameter difficulty is a scalar rung
    (see DIFFICULTY_RUNGS); absent means the no-rung default path (byte-
    identical to pre-#2). The payload's qtype is the validator-level
    "arithmetic" so /api/answer takes the numeric-comparison branch, and
    question_id is null because generated questions are never stored.

    C-D2c: the arithmetic payload now also carries the SERVED difficulty rung
    and the generated expression's leaf_count, so the client can echo both back
    on /api/answer for recording (the capture side is C-D2g, gated on the v3
    migration C-D2f). difficulty is null on the no-rung path; leaf_count is
    always present (it is a fact about the served tree regardless of rung).
    """
    category = bottle.request.query.get("category")
    if not category:
        return _json_error("missing required parameter: category", status=400)

    if category == "arithmetic":
        # Optional operator restriction from the query string.
        operators_raw = bottle.request.query.get("operators")
        enabled_symbols = None
        if operators_raw:
            requested = [
                symbol.strip()
                for symbol in operators_raw.split(",")
                if symbol.strip() != ""
            ]
            # operators= present but containing only separators/whitespace
            # parses to an empty set. That is a malformed restriction, not
            # "use all operators" -- report it rather than silently widening.
            if not requested:
                return _json_error(
                    "operators parameter is empty; omit it for all operators "
                    "or list one or more symbols",
                    status=400,
                )
            unknown = [s for s in requested if s not in OPERATORS]
            if unknown:
                return _json_error(
                    "unknown operator symbols: " + ", ".join(unknown),
                    status=400,
                )
            enabled_symbols = requested

        # Optional difficulty rung. Absent/empty -> None (the default path).
        # Present -> must parse to an int that is a KNOWN rung label. We
        # validate here (user input) and 400 on a bad value, mirroring the
        # operators= unknown-symbol 400; generate_expression's own ValueError
        # guard then only ever fires on an internal programming error.
        difficulty_raw = bottle.request.query.get("difficulty")
        difficulty = None
        if difficulty_raw is not None and difficulty_raw != "":
            try:
                difficulty = int(difficulty_raw)
            except ValueError:
                return _json_error("difficulty must be an integer", status=400)
            known_rungs = [record["rung"] for record in DIFFICULTY_RUNGS]
            if difficulty not in known_rungs:
                return _json_error(
                    "unknown difficulty rung "
                    + str(difficulty)
                    + "; known rungs are "
                    + ", ".join(str(rung) for rung in known_rungs),
                    status=400,
                )

        expression = generate_expression(enabled_symbols, difficulty=difficulty)
        rendered = render_expression(expression)
        result = evaluate_expression(expression)
        return {
            "qtype": QTYPE_ARITHMETIC,
            "question_text": rendered,
            "expected": str(result),
            "question_id": None,
            "alternatives": None,
            "media_url": None,
            # C-D2c echo carriers: the served rung (null on the default path)
            # and the tree's structural leaf_count. The client returns both on
            # /api/answer; capture into responses is C-D2g (needs the v3 cols).
            "difficulty": difficulty,
            "leaf_count": leaf_count(expression),
        }

    # Bank-based question path (C-012). For any non-arithmetic category, draw
    # from a specific bank identified by the required bank_id parameter.
    bank_id_raw = bottle.request.query.get("bank_id")
    if bank_id_raw is None or bank_id_raw == "":
        return _json_error("missing required parameter: bank_id", status=400)
    try:
        bank_id = int(bank_id_raw)
    except ValueError:
        return _json_error("bank_id must be an integer", status=400)

    # Optional recent-history to softly avoid immediate repeats. Accepts a
    # comma-separated list of recently served question ids from the client.
    history_raw = bottle.request.query.get("recent")
    history: list[int] = []
    if history_raw:
        for piece in history_raw.split(","):
            piece = piece.strip()
            if piece == "":
                continue
            try:
                history.append(int(piece))
            except ValueError:
                return _json_error(
                    "recent must be a comma-separated list of integer ids",
                    status=400,
                )

    connection = connect(DATABASE_PATH)
    try:
        candidates = list_questions(connection, bank_id)
    finally:
        connection.close()

    chosen = pick_next_question(candidates, history)
    if chosen is None:
        return _json_error("bank " + str(bank_id) + " has no questions", status=404)
    # C-018b scaffold (deferred Option A): if per-question-language TTS is ever
    # built, this is where the bank's language enters the request. We already
    # have bank_id; the handler would fetch the bank row (get_bank / a
    # language lookup in DATABASE) and pass it down, e.g.
    #     bank = get_bank(connection, bank_id)   # inside the try above
    #     return build_question_payload(chosen, bank_language=bank["language"])
    # Not done now: it touches the frozen backend and the section-6 payload
    # contract, so it is its own future commit + spec amendment. C-018a sources
    # language on the client from the already-fetched bank instead. See the
    # longer note in build_question_payload and DECISIONS C-018b.
    return build_question_payload(chosen)


@app.post("/api/answer")
def post_answer():
    """Validate a submitted answer, log the response, return feedback.

    C-010: the request body echoes back the question context the client was
    served, so the server can validate and log without server-side per-
    question state. Expected JSON fields:
        session_id    (int, required)   the active session
        qtype         (str, required)   drives validation dispatch
        question_text (str, required)   rendered question, stored verbatim
        expected      (str, required)   the correct answer to compare against
        user_input    (str, required)   what the user submitted
        alternatives  (list, optional)  also-acceptable answers (text qtypes)
        question_id   (int, optional)   NULL for generated arithmetic
        elapsed_ms    (int, optional)   reserved for future timed rounds
        difficulty    (int, optional)   served rung echoed from the question
                                        payload; NULL for bank/no-rung (C-D2g)
        leaf_count    (int, optional)   expression leaf_count echoed from the
                                        question payload; NULL for non-arithmetic
        tolerance     (float, optional) numeric tolerance for arithmetic
    Returns {"correct": bool, "expected": str, "user_input": str,
    "session_stats": {total, correct, accuracy, streak}} so the client can
    show feedback (including the right answer on a miss) and refresh the
    stats bar without a separate GET /api/stats call.
    """
    body = _request_json()
    required_fields = ("session_id", "qtype", "question_text", "expected", "user_input")
    for field in required_fields:
        if field not in body:
            return _json_error("missing required field: " + field, status=400)

    try:
        session_id = _require_int(body.get("session_id"), "session_id")
        question_id = _optional_int(body.get("question_id"), "question_id")
        elapsed_ms = _optional_int(body.get("elapsed_ms"), "elapsed_ms")
        # C-D2g: capture the rung + leaf_count the client echoes from the served
        # question payload (C-D2c). Type-checked as optional ints (malformed ->
        # 400), then recorded verbatim. We do NOT reject an out-of-range rung
        # here: the question endpoint already validated ?difficulty= on the way
        # out, and this field is recording-only (the C-D2i breakdown groups by
        # leaf_count, not the rung label). Honestly storing what the client
        # claimed is the right behavior for this single-user local tool; over-
        # policing the echo would add a second rung-range source of truth.
        difficulty = _optional_int(body.get("difficulty"), "difficulty")
        leaf_count = _optional_int(body.get("leaf_count"), "leaf_count")
    except _BadParameter as bad:
        return _json_error(bad.message, status=400)

    # Trust assumption: this single-user local tool trusts the client-supplied
    # question context (expected, qtype, alternatives). The server re-runs
    # validation rather than trusting a client verdict, but it does not verify
    # that "expected" matches a stored question. A future multi-user version
    # should look the question up by question_id and grade against the DB's
    # stored answer, ignoring the client's "expected" field.
    correct = validate_answer(
        expected=str(body["expected"]),
        given=str(body["user_input"]),
        qtype=str(body["qtype"]),
        alternatives=body.get("alternatives"),
        tolerance=body.get("tolerance"),
    )

    connection = connect(DATABASE_PATH)
    try:
        insert_response(
            connection,
            session_id=session_id,
            question_text=str(body["question_text"]),
            answer_text=str(body["expected"]),
            user_input=str(body["user_input"]),
            correct=correct,
            answered=utc_now_iso(),
            question_id=question_id,
            elapsed_ms=elapsed_ms,
            difficulty=difficulty,
            leaf_count=leaf_count,
        )
        # Tack the running session stats onto the response so the UI updates
        # its stats bar without a separate GET /api/stats call per question
        # (keeps the drill hot path to two calls: POST answer, GET question).
        correctness = get_session_correctness(connection, session_id)
    except sqlite3.IntegrityError as error:
        # e.g. session_id (or a non-null question_id) does not exist, perhaps
        # because the session/bank was deleted in another tab. Report cleanly.
        return _json_error(_integrity_message(error), status=400)
    finally:
        connection.close()
    session_stats = summarize_correctness(correctness)
    return {
        "correct": correct,
        "expected": str(body["expected"]),
        "user_input": str(body["user_input"]),
        "session_stats": session_stats,
    }


@app.post("/api/session/start")
def post_session_start():
    """Begin a session and return its id.

    C-010: required field category_id; optional bank_id and config. The
    started timestamp is read from the clock here (HTTP is the clock-reader).
    Returns {"session_id": int}.
    """
    body = _request_json()
    if "category_id" not in body:
        return _json_error("missing required field: category_id", status=400)
    try:
        category_id = _require_int(body.get("category_id"), "category_id")
        bank_id = _optional_int(body.get("bank_id"), "bank_id")
    except _BadParameter as bad:
        return _json_error(bad.message, status=400)
    connection = connect(DATABASE_PATH)
    try:
        session_id = start_session(
            connection,
            category_id=category_id,
            started=utc_now_iso(),
            bank_id=bank_id,
            config=body.get("config"),
        )
    except sqlite3.IntegrityError as error:
        # category_id or bank_id does not reference an existing row.
        return _json_error(_integrity_message(error), status=400)
    finally:
        connection.close()
    return {"session_id": session_id}


@app.post("/api/session/end")
def post_session_end():
    """End a session by stamping its ended timestamp.

    C-010: required field session_id. The ended timestamp is read here.
    Returns {"ended": bool} indicating whether a session row was updated.
    A session_id that does not exist updates no row and returns ended=false
    (not an error -- ending an unknown or already-cleaned-up session is a
    harmless no-op for this tool).
    """
    body = _request_json()
    if "session_id" not in body:
        return _json_error("missing required field: session_id", status=400)
    try:
        session_id = _require_int(body.get("session_id"), "session_id")
    except _BadParameter as bad:
        return _json_error(bad.message, status=400)
    connection = connect(DATABASE_PATH)
    try:
        updated = end_session(
            connection,
            session_id=session_id,
            ended=utc_now_iso(),
        )
    finally:
        connection.close()
    return {"ended": updated > 0}


@app.get("/api/stats")
def get_stats():
    """Durable cross-session stats, optionally filtered by category and window.

    C-019a (spec section 6, the one sanctioned post-freeze backend addition).
    Query parameters (both optional):
        category_id -- restrict to one category; omitted means all categories.
        days        -- a positive integer window; only responses answered
                       within the last N days are counted. Omitted means all
                       time. days <= 0 is a 400 (a zero/negative window is a
                       malformed request, not "all time" -- omit the param for
                       all time).

    The day-window cutoff is computed HERE from the clock (HTTP is the only
    clock-reader alongside init_db); the cutoff is passed to DATABASE as an ISO
    string so neither DATABASE nor LOGIC reads the clock. Rows come from
    get_responses_for_stats; the summary is the pure summarize_stats. Returns:
        {total, correct, accuracy, categories:[{category_id, category_name,
         total, correct, accuracy}], window:{category_id, days, since}}
    where window echoes the effective filter (since is the ISO cutoff or null).
    """
    query = bottle.request.query
    try:
        category_id = _optional_int(query.get("category_id"), "category_id")
        days = _optional_int(query.get("days"), "days")
    except _BadParameter as bad:
        return _json_error(bad.message, status=400)

    since = None
    if days is not None:
        if days <= 0:
            return _json_error(
                "days must be a positive integer (omit it for all time)",
                status=400,
            )
        # Cutoff = now - days, emitted in the same ISO 8601 UTC format as
        # responses.answered so the DATABASE comparison is string-vs-string in
        # one consistent format. utc_now_iso() is the shared clock helper.
        cutoff = datetime.fromisoformat(utc_now_iso()) - timedelta(days=days)
        since = cutoff.isoformat()

    connection = connect(DATABASE_PATH)
    try:
        rows = get_responses_for_stats(
            connection,
            category_id=category_id,
            since=since,
        )
    finally:
        connection.close()

    summary = summarize_stats(rows)
    summary["window"] = {
        "category_id": category_id,
        "days": days,
        "since": since,
    }
    return summary


@app.post("/api/banks/import")
def post_banks_import():
    """Import a JSONL or CSV question bank into a new bank.

    C-010 (item 6): wires the import route by combining LOGIC.parse_import
    (C-008) with DATABASE.insert_bank and insert_questions_bulk (C-003).

    Accepts a multipart upload with a "file" part, plus form fields:
        category_id (int, required)  the category the new bank belongs to
        name        (str, optional)  bank name; defaults to the upload's
                                      filename without extension
        format      (str, optional)  "jsonl" or "csv"; if absent, inferred
                                      from the upload's file extension
        language    (str, optional)  ISO 639-1 code stored on the bank
    The bank's source is recorded as "import". The created timestamp is read
    here. On a parse failure, returns 400 with the row-naming message from
    ImportParseError and creates no bank. Returns
    {"bank_id": int, "imported": int} on success.
    """
    upload = bottle.request.files.get("file")
    if upload is None:
        return _json_error("missing uploaded file part 'file'", status=400)

    form = bottle.request.forms
    category_id_raw = form.get("category_id")
    if category_id_raw is None or category_id_raw == "":
        return _json_error("missing required field: category_id", status=400)
    try:
        category_id = int(category_id_raw)
    except ValueError:
        return _json_error("category_id must be an integer", status=400)

    # Infer format from the explicit field or the filename extension.
    file_format = form.get("format")
    if not file_format:
        _, extension = os.path.splitext(upload.filename or "")
        file_format = extension.lstrip(".").lower()

    # Default the bank name to the uploaded filename without its extension.
    bank_name = form.get("name")
    if not bank_name:
        base = os.path.basename(upload.filename or "imported")
        bank_name = os.path.splitext(base)[0] or "imported"

    language = form.get("language") or None

    # Read and decode the upload, then parse via LOGIC. Parsing happens
    # before any DB write so a bad file creates no empty bank.
    raw_bytes = upload.file.read()
    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        return _json_error("uploaded file must be UTF-8 encoded", status=400)
    try:
        questions = parse_import(text, file_format)
    except ImportParseError as error:
        return _json_error(str(error), status=400)

    connection = connect(DATABASE_PATH)
    try:
        created = utc_now_iso()
        bank_id = insert_bank(
            connection,
            category_id=category_id,
            name=bank_name,
            source="import",
            created=created,
            language=language,
        )
        imported = insert_questions_bulk(connection, bank_id, questions, created)
    except sqlite3.IntegrityError as error:
        # category_id does not reference an existing category.
        return _json_error(_integrity_message(error), status=400)
    finally:
        connection.close()
    return {"bank_id": bank_id, "imported": imported}


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
    global DATABASE_PATH

    host = os.environ.get("DRILL_HOST", "127.0.0.1")
    database_path = os.environ.get("DRILL_DB", DEFAULT_DATABASE_PATH)

    port_raw = os.environ.get("DRILL_PORT", "8080")
    try:
        port = int(port_raw)
    except ValueError:
        raise SystemExit("DRILL_PORT must be an integer (got: " + repr(port_raw) + ")")

    # Publish the chosen path so request handlers (which read the module
    # global) open the same database this startup initialized.
    DATABASE_PATH = database_path

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
    connection = connect(DATABASE_PATH)
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

    # Friendly startup line so the operator knows the exact URL to open.
    # (Bottle also prints its own banner.)
    print(
        "drill: serving on http://" + host + ":" + str(port) + "/"
        " (database: " + DATABASE_PATH + ")"
    )

    app.run(host=host, port=port)


if __name__ == "__main__":
    main()
