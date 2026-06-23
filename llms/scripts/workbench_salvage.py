"""Salvaged reference material from workbench.py.

workbench.py was an earlier, standalone conversational REPL (Anthropic SDK,
SQLite-logged, cost-tracked). It is not being maintained as a runnable program.
This file preserves the parts worth keeping -- the data model, the SQLite schema
and its migration pattern, the per-model cost table, and the pure transforms --
in a self-contained, documented form so they can be reused or referenced without
resurrecting the whole script.

Nothing here performs IO at import time. The schema constants are plain strings;
the functions are pure. The one IO helper (init_calls_table) is provided as a
reference implementation and only touches a database when called explicitly.

Relationship to the rest of the toolkit:
  - The pure transforms mirror llm.py / llm_config conventions (e.g. the
    ~4-chars-per-token estimate matches llm.py's estimate_tokens).
  - MODELS (cost rates) is workbench's concern; llm.py logs token counts but not
    cost. If a second tool ever needs cost math, this table is the thing to lift
    into a shared module (the same two-consumers threshold that justified sharing
    the provider table between llm.py and llm_config).
  - The 'calls' schema is independent of llm.py's JSONL usage log on purpose:
    workbench logged full message content (private), whereas llm.py's log is
    metadata-only and shareable. Two stores, two privacy contracts.
"""

import sqlite3


# =====================================================================
# DATA MODEL
# =====================================================================
# messages       -- list[dict] with keys: role (system|user|assistant), content
# response_data  -- dict the loop built per turn: response_text, tokens_in,
#                   tokens_out, stop_reason  (the original also carried the
#                   provider-echoed model string, which was never read)
# calls table    -- append-only, one row per turn, full conversation snapshot in
#                   messages_json, grouped by conversation_id
#
# Note on stop_reason: the original stored the provider's raw stop-reason string
# (e.g. "end_turn", "max_tokens", "stop_sequence"). llm_config.call_llm collapses
# this to a truncated bool (ADR-12), so a tool built on call_llm would either
# store "max_tokens"/"end_turn" synthesized from the bool (lossy) or change the
# column's meaning to a truncated flag. Recorded here as a known design seam.


# =====================================================================
# SCHEMA -- SQLite 'calls' table and its additive migration pattern
# =====================================================================

CREATE_CALLS_TABLE = """
CREATE TABLE IF NOT EXISTS calls (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    model TEXT NOT NULL,
    messages_json TEXT NOT NULL,
    response_text TEXT NOT NULL,
    tokens_in INTEGER,
    tokens_out INTEGER,
    notes TEXT,
    conversation_id TEXT,
    stop_reason TEXT
)
"""

# Additive migrations: each ALTER is wrapped so a re-run on an up-to-date table
# is a no-op. New columns added to an existing database land here, never as edits
# to CREATE_CALLS_TABLE (so old databases upgrade in place). The pattern is the
# salvage-worthy idea, not the specific columns.
MIGRATIONS = [
    "ALTER TABLE calls ADD COLUMN conversation_id TEXT",
    "ALTER TABLE calls ADD COLUMN stop_reason TEXT",
]

INSERT_CALL = """
INSERT INTO calls (timestamp, model, messages_json, response_text,
                   tokens_in, tokens_out, notes, conversation_id, stop_reason)
VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
"""


def init_calls_table(connection: sqlite3.Connection) -> None:
    """Reference implementation: create the calls table and apply migrations.

    Idempotent. CREATE IF NOT EXISTS handles a fresh database; each migration is
    tried and its 'duplicate column' error swallowed so an already-current table
    is left unchanged. The only IO in this module; call it explicitly.
    """
    with connection:
        connection.execute(CREATE_CALLS_TABLE)
    for statement in MIGRATIONS:
        try:
            with connection:
                connection.execute(statement)
        except sqlite3.OperationalError:
            pass  # column already exists


# =====================================================================
# COST DATA -- per-model rates (USD per 1,000,000 tokens)
# =====================================================================

MODELS = {
    "sonnet": {"id": "claude-sonnet-4-20250514", "cost_in": 3.00, "cost_out": 15.00},
    "haiku": {"id": "claude-haiku-4-5-20251001", "cost_in": 0.80, "cost_out": 4.00},
    "opus": {"id": "claude-opus-4-6", "cost_in": 15.00, "cost_out": 75.00},
}

DEFAULT_MODEL = "haiku"


# =====================================================================
# TRANSFORM -- pure functions: data in, data out, no IO
# =====================================================================


def estimate_tokens(text: str) -> int:
    """Rough token estimate from character count (~4 chars/token).

    Matches llm.py's estimate_tokens heuristic. Undercounts for code and
    non-English text; callers prefix the result with '~' accordingly.
    """
    return len(text) // 4


def estimate_messages_tokens(messages: list[dict]) -> int:
    """Sum the rough token estimate across every message's content."""
    return sum(estimate_tokens(m["content"]) for m in messages)


def compute_cost(tokens_in: int, tokens_out: int, model_config: dict) -> float:
    """USD cost for one call from token counts and the model's per-1M rates.

    cost_in/cost_out are dollars per 1,000,000 tokens. Pass tokens_out=0 to cost
    only the input side (as the dry-run estimate did).
    """
    input_cost = (tokens_in / 1_000_000) * model_config["cost_in"]
    output_cost = (tokens_out / 1_000_000) * model_config["cost_out"]
    return input_cost + output_cost


def split_system(messages: list[dict]) -> tuple[str | None, list[dict]]:
    """Separate a system message from the chat list.

    workbench stored the system prompt as a {"role": "system"} entry inside the
    messages list; the API call needed it separated out. This is the extraction
    that step performed. Returns (system_or_None, non_system_messages). Note that
    llm_config.call_llm instead takes system as an explicit parameter (ADR-11),
    so a tool built on it would keep system out of the list from the start and
    not need this.
    """
    system = None
    chat = []
    for message in messages:
        if message["role"] == "system":
            system = message["content"]
        else:
            chat.append(message)
    return system, chat
