# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "anthropic",
# ]
# ///

"""Personal LLM Workbench -- Phase 1: One Working Loop.

Pipeline:
    PARSE    -- read CLI arguments, resolve model config
    INPUT    -- get prompt text from argument or stdin
    ASSEMBLE -- build messages array with optional system prompt
    DRY-RUN  -- if --dry-run, show context and cost estimate, then exit
    CALL     -- send to Anthropic API, unpack response to plain dict
    DISPLAY  -- print response text to stdout, metadata to stderr
    LOG      -- append call record to SQLite

Data contracts:
    messages      -- list[dict] with keys: role (system|user), content
    response_data -- dict with keys: response_text, tokens_in, tokens_out,
                    model, stop_reason
    calls table   -- append-only, one row per API call, full context
                    preserved in messages_json
"""

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

import anthropic
import terminal_output


# -- Constants ---------------------------------------------------------

DATABASE_PATH: str = str(Path(__file__).parent / "workbench.db")

MAX_RESPONSE_TOKENS: int = 4096

MODELS: dict[str, dict] = {
    "sonnet": {"id": "claude-sonnet-4-20250514", "cost_in": 3.00, "cost_out": 15.00},
    "haiku":  {"id": "claude-haiku-4-5-20251001", "cost_in": 0.80, "cost_out": 4.00},
    "opus":   {"id": "claude-opus-4-0-20250115", "cost_in": 15.00, "cost_out": 75.00},
}

DEFAULT_MODEL: str = "haiku"


# -- Argument Parsing --------------------------------------------------

parser = argparse.ArgumentParser(description="Personal LLM Workbench")

parser.add_argument("text", nargs="?", default=None,
                    help="Prompt text (reads stdin if omitted)")
parser.add_argument("--model", "-m", choices=MODELS.keys(), default=DEFAULT_MODEL,
                    help="Model to use (default: sonnet)")
parser.add_argument("--system", "-s", type=str, default=None,
                    help="System prompt text")
parser.add_argument("--dry-run", action="store_true",
                    help="Preview context and cost without calling the API")
parser.add_argument("--notes", "-n", type=str, default=None,
                    help="Freeform note stored with this call")
parser.add_argument("--prompt", type=Path, default=None,
                    help="(placeholder -- not yet implemented)")
parser.add_argument("--input", type=Path, default=None,
                    help="(placeholder -- not yet implemented)")
parser.add_argument("--verbose", "-v", action="count", default=3,
                    help="Increase verbosity (-v debug, -vv trace)")


# -- Procedural Flow ---------------------------------------------------

if __name__ == "__main__":

    # -- PARSE ---------------------------------------------------------

    parsed_arguments = parser.parse_args()
    terminal_output.set_verbosity(parsed_arguments.verbose)

    if parsed_arguments.prompt is not None:
        terminal_output.msg_warn("--prompt flag is not yet implemented. Ignoring.")
    if parsed_arguments.input is not None:
        terminal_output.msg_warn("--input flag is not yet implemented. Ignoring.")

    model_name: str = parsed_arguments.model
    model_config: dict = MODELS[model_name]

    # -- INPUT ---------------------------------------------------------

    if parsed_arguments.text is not None:
        user_input: str = parsed_arguments.text
    elif not sys.stdin.isatty():
        user_input = sys.stdin.read().strip()
    else:
        terminal_output.msg_error(
            "No input provided. Pass text as an argument or pipe via stdin."
        )
        sys.exit(1)

    # -- ASSEMBLE ------------------------------------------------------

    messages: list[dict[str, str]] = []
    if parsed_arguments.system is not None:
        messages.append({"role": "system", "content": parsed_arguments.system})
    messages.append({"role": "user", "content": user_input})

    # -- DRY-RUN -------------------------------------------------------

    if parsed_arguments.dry_run:
        estimated_input_tokens: int = 0
        for message in messages:
            estimated_input_tokens = estimated_input_tokens + len(message["content"]) // 4

        estimated_input_cost: float = (
            (estimated_input_tokens / 1_000_000) * model_config["cost_in"]
        )

        summary_lines: list[str] = [
            "Model: " + model_config["id"],
            "Messages: " + str(len(messages)),
            "Estimated input tokens: ~" + str(estimated_input_tokens),
            "Estimated cost: ~" + terminal_output.format_cost(estimated_input_cost),
        ]
        print(terminal_output.format_block("DRY RUN", "\n".join(summary_lines)))

        context_lines: list[str] = []
        for message in messages:
            role_label: str = terminal_output.format_label(message["role"])
            context_lines.append(role_label + " " + message["content"])
        print(terminal_output.format_block("CONTEXT", "\n\n".join(context_lines)))

        terminal_output.msg_info("No API call made.")
        sys.exit(0)

    # -- CALL ----------------------------------------------------------

    system_prompt: str | None = None
    api_messages: list[dict[str, str]] = []
    for message in messages:
        if message["role"] == "system":
            system_prompt = message["content"]
        else:
            api_messages.append(message)

    try:
        client = anthropic.Anthropic()
        if system_prompt is not None:
            api_response = client.messages.create(
                model=model_config["id"],
                max_tokens=MAX_RESPONSE_TOKENS,
                system=system_prompt,
                messages=api_messages,
            )
        else:
            api_response = client.messages.create(
                model=model_config["id"],
                max_tokens=MAX_RESPONSE_TOKENS,
                messages=api_messages,
            )
    except anthropic.APIError as api_error:
        terminal_output.msg_error("API call failed: " + str(api_error))
        sys.exit(1)

    # Unpack SDK response to plain data immediately
    response_data: dict = {
        "response_text": api_response.content[0].text,
        "tokens_in": api_response.usage.input_tokens,
        "tokens_out": api_response.usage.output_tokens,
        "model": api_response.model,
        "stop_reason": api_response.stop_reason,
    }

    # -- DISPLAY -------------------------------------------------------

    print(response_data["response_text"])

    tokens_in: int = response_data["tokens_in"]
    tokens_out: int = response_data["tokens_out"]
    input_cost: float = (tokens_in / 1_000_000) * model_config["cost_in"]
    output_cost: float = (tokens_out / 1_000_000) * model_config["cost_out"]
    total_cost: float = input_cost + output_cost

    terminal_output.msg_info(terminal_output.format_token_counts(tokens_in, tokens_out))
    terminal_output.msg_info("Cost: " + terminal_output.format_cost(total_cost))

    # -- LOG -----------------------------------------------------------

    timestamp: str = datetime.now(timezone.utc).isoformat()
    messages_json: str = json.dumps(messages)

    connection = sqlite3.connect(DATABASE_PATH)
    try:
        with connection:
            connection.execute("""
                CREATE TABLE IF NOT EXISTS calls (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    model TEXT NOT NULL,
                    messages_json TEXT NOT NULL,
                    response_text TEXT NOT NULL,
                    tokens_in INTEGER,
                    tokens_out INTEGER,
                    notes TEXT
                )
            """)
        with connection:
            connection.execute(
                """
                INSERT INTO calls (timestamp, model, messages_json, response_text,
                                   tokens_in, tokens_out, notes)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (timestamp, model_config["id"], messages_json,
                 response_data["response_text"], tokens_in, tokens_out,
                 parsed_arguments.notes),
            )
    except sqlite3.Error as database_error:
        terminal_output.msg_error("Database write failed: " + str(database_error))
        sys.exit(1)
    finally:
        connection.close()

    terminal_output.msg_success("Logged to " + DATABASE_PATH)
