"""CONFIG layer -- constants and scalar configuration only (D1 extraction).

Extracted verbatim from drill.py's CONFIG section (roadmap #1 modularization,
commit D1). This is the leaf of the backend DAG: config <- db <- logic <- http;
main wires. config imports nothing (internal or third-party) beyond the
__future__ annotations import the annotated assignments need.

No callables live here (the operator-table layering tension is resolved by
keeping the operator TABLE in LOGIC -- see S10b / ADR notes): config holds only
scalars, the QTYPE names, the operator SYMBOL list, operand-range scalars, the
DIFFICULTY_RUNGS data + its import-time consistency guard, the schema version
constants, the default DB path, and the baseline SCHEMA_STATEMENTS DDL.

The migration functions + MIGRATIONS registry + version-consistency guard are
NOT here despite historically sitting in the CONFIG region: they are DATABASE
operations (they run DDL) and move to db.py in D3 (S10a). SCHEMA_VERSION stays
here; db.py imports it for the guard-weld.

Behavior-preserving: every name below is identical to its pre-split definition;
drill.py now imports these from here. The suite (backend 202 / frontend 114) is
the proof.
"""

from __future__ import annotations


# Constants and scalar configuration only. No callables (resolution to the
# operator-table layering tension: the operator table is built in LOGIC in
# C-006, not here). Operator definitions are intentionally absent from C-002.

# Current schema version: the highest version the code knows about, reached by
# init_db (the baseline) plus every migration in MIGRATIONS. v2 (D1) adds
# questions.metadata via the runner; init_db builds the baseline and
# run_migrations layers v2..N on top of it.
SCHEMA_VERSION: int = 4

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

# C3 (SM2 review mode, roadmap #7): daily budgets for the review path. A
# maximum of NEW_QUESTIONS_PER_DAY_MAXIMUM never-reviewed questions enter the
# schedule per day across all banks, with NEW_QUESTIONS_PER_BANK_MINIMUM slots
# guaranteed per bank that still has headroom (the floor pass), so one large
# bank cannot starve the others. REVIEWS_PER_SESSION_MAXIMUM caps how much of
# a due backlog one session serves (ordered by relative overdueness, so the
# capped set is the most at-risk subset). Values carried over from sm2's
# proven daily rhythm.
NEW_QUESTIONS_PER_DAY_MAXIMUM: int = 9
NEW_QUESTIONS_PER_BANK_MINIMUM: int = 1
REVIEWS_PER_SESSION_MAXIMUM: int = 100

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
