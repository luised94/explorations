# /// script
# requires-python = ">=3.12"
# dependencies = [
#     "anthropic",
# ]
# ///

"""Personal LLM Workbench -- Phase 1: One Working Loop.

Pipeline:
    PARSE    -- read CLI arguments, resolve model config, validate flags
    INPUT    -- get prompt text from argument or stdin (single-shot only)
    ASSEMBLE -- initialize messages array with optional system prompt
    DRY-RUN  -- if --dry-run, show context and cost estimate, then exit
    INIT     -- connect to SQLite, create/migrate table, create API client
    LOOP     -- read input, call API, display response, log to database
               (single-shot: one iteration; interactive: until /quit or Ctrl-C)
    CLEANUP  -- close database connection, print session summary

Data contracts:
    messages        -- list[dict] with keys: role (system|user|assistant), content
    response_data   -- dict with keys: response_text, tokens_in, tokens_out,
                       model, stop_reason
    calls table     -- append-only, one row per turn, full context in
                       messages_json, grouped by conversation_id
"""
# --- BRANCHING (Phase 2) ---
#
# The conversation is currently a linear list of messages. Phase 2
# changes this to a tree:
#
# Data model:
#   nodes = {
#       node_id: {
#           "role": "user" | "assistant",
#           "content": str,
#           "parent": node_id | None,
#           "children": [node_id, ...],
#       }
#   }
#   current_leaf = node_id
#
# The API always receives a linear messages list. To build it,
# walk from root to current_leaf:
#   path = []
#   node = current_leaf
#   while node is not None:
#       path.append(nodes[node])
#       node = nodes[node]["parent"]
#   messages = [{"role": n["role"], "content": n["content"]}
#               for n in reversed(path)]
#
# Branching occurs when the user edits a previous turn. The edit
# creates a new child of the edited node's parent, forking the tree.
#
# Prompt format:
#   Linear (current):    [model:turn]
#   Branched (Phase 2):  [model:turn bN]    (branch indicator)
#   Main branch shows no indicator -- backward compatible.
#
# Navigation commands (Phase 2):
#   /branches   -- display tree via terminal_output.format_tree()
#   /goto ID    -- switch current_leaf to node ID
#   /edit N     -- re-enter at turn N, creating a new branch
#   /back       -- move current_leaf to parent
#
# SQLite storage: conversation_id already groups turns. Branching
# adds parent_node_id column to calls table. Existing NULL parent
# rows are linear (no branches). Migration is additive.
#
# Tree display uses format_tree():
#   tree_nodes = [(id, content[:40], parent_id) for id, node in nodes.items()]
#   terminal_output.emit(terminal_output.format_tree(tree_nodes, current=current_leaf))

import argparse
import json
import os
import readline  # noqa: F401 -- enhances input() with line editing and history
import shutil
import sqlite3
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

import anthropic
import terminal_output


# -- Constants ---------------------------------------------------------

DATABASE_PATH: str = str(Path(__file__).parent / "workbench.db")

MAX_RESPONSE_TOKENS: int = 4096

MODELS: dict[str, dict] = {
    "sonnet": {"id": "claude-sonnet-4-20250514", "cost_in": 3.00, "cost_out": 15.00},
    "haiku":  {"id": "claude-haiku-4-5-20251001", "cost_in": 0.80, "cost_out": 4.00},
    "opus":   {"id": "claude-opus-4-6", "cost_in": 15.00, "cost_out": 75.00},
}

DEFAULT_MODEL: str = "haiku"


# -- Argument Parsing --------------------------------------------------

parser = argparse.ArgumentParser(description="Personal LLM Workbench")

parser.add_argument("text", nargs="?", default=None,
                    help="Prompt text (reads stdin if omitted)")
parser.add_argument("--model", "-m", choices=MODELS.keys(), default=DEFAULT_MODEL,
                    help="Model to use (default: haiku)")
parser.add_argument("--system", "-s", type=str, default=None,
                    help="System prompt text")
parser.add_argument("--interactive", "-i", action="store_true",
                    help="Start an interactive multi-turn conversation")
parser.add_argument("--dry-run", action="store_true",
                    help="Preview context and cost without calling the API")
parser.add_argument("--notes", "-n", type=str, default=None,
                    help="Freeform note stored with each turn")
parser.add_argument("--prompt", type=Path, default=None,
                    help="Read system prompt from file")
parser.add_argument("--input", type=Path, default=None,
                    help="(placeholder -- not yet implemented)")
parser.add_argument("--verbose", "-v", action="count", default=3,
                    help="Increase verbosity (-v debug, -vv trace)")


# -- Procedural Flow ---------------------------------------------------

if __name__ == "__main__":

    # -- PARSE ---------------------------------------------------------

    parsed_arguments = parser.parse_args()
    terminal_output.set_verbosity(parsed_arguments.verbose)

    if parsed_arguments.input is not None:
        terminal_output.msg_warn("--input flag is not yet implemented. Ignoring.")

    if parsed_arguments.prompt is not None and parsed_arguments.system is not None:
        terminal_output.msg_error(
            "Cannot use both --prompt and --system. Choose one."
        )
        sys.exit(1)

    interactive_mode: bool = parsed_arguments.interactive
    model_name: str = parsed_arguments.model
    model_config: dict = MODELS[model_name]
    # Derive short model name for prompt display
    model_short: str = model_config["id"].split("/")[-1]

    if len(model_short) > 20:
        model_short = model_short[:17] + "..."

    if parsed_arguments.dry_run and interactive_mode:
        terminal_output.msg_error("--dry-run is not compatible with --interactive.")
        sys.exit(1)

    if interactive_mode and not sys.stdin.isatty():
        terminal_output.msg_error(
            "Interactive mode requires a terminal (stdin is not a tty)."
        )
        sys.exit(1)

    # -- INPUT ---------------------------------------------------------

    user_input: str = ""
    has_initial_input: bool = False

    if parsed_arguments.text is not None:
        user_input = parsed_arguments.text
        has_initial_input = True
    elif not sys.stdin.isatty() and not interactive_mode:
        user_input = sys.stdin.read().strip()
        has_initial_input = True
    elif not interactive_mode:
        terminal_output.msg_error(
            "No input provided. Pass text as an argument or pipe via stdin."
        )
        sys.exit(1)

    # -- ASSEMBLE ------------------------------------------------------

    messages: list[dict[str, str]] = []

    system_prompt_text: str | None = None
    if parsed_arguments.prompt is not None:
        try:
            system_prompt_text = parsed_arguments.prompt.read_text()
        except (FileNotFoundError, PermissionError, OSError) as file_error:
            terminal_output.msg_error(
                "Failed to read prompt file: " + str(file_error)
            )
            sys.exit(1)
    elif parsed_arguments.system is not None:
        system_prompt_text = parsed_arguments.system

    if system_prompt_text is not None:
        messages.append({"role": "system", "content": system_prompt_text})

    # -- DRY-RUN -------------------------------------------------------

    if parsed_arguments.dry_run:
        dry_run_messages: list[dict[str, str]] = messages + [
            {"role": "user", "content": user_input}
        ]

        estimated_input_tokens: int = 0
        for message in dry_run_messages:
            estimated_input_tokens = (
                estimated_input_tokens + len(message["content"]) // 4
            )

        estimated_input_cost: float = (
            (estimated_input_tokens / 1_000_000) * model_config["cost_in"]
        )

        summary_lines: list[str] = [
            "Model: " + model_config["id"],
            "Messages: " + str(len(dry_run_messages)),
            "Estimated input tokens: ~" + str(estimated_input_tokens),
            "Estimated cost: ~" + terminal_output.format_cost(estimated_input_cost),
        ]
        print(terminal_output.format_block("DRY RUN", "\n".join(summary_lines)))

        context_lines: list[str] = []
        for message in dry_run_messages:
            role_label: str = terminal_output.format_label(message["role"])
            context_lines.append(role_label + " " + message["content"])
        print(terminal_output.format_block("CONTEXT", "\n\n".join(context_lines)))

        terminal_output.msg_info("No API call made.")
        sys.exit(0)

    # -- INIT ----------------------------------------------------------


connection = sqlite3.connect(DATABASE_PATH)
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
                notes TEXT,
                conversation_id TEXT,
                stop_reason TEXT
            )
        """)

    # Migrate: add conversation_id if table predates this column
    try:
        with connection:
            connection.execute(
                "ALTER TABLE calls ADD COLUMN conversation_id TEXT"
            )
    except sqlite3.OperationalError:
        pass  # column already exists

    # Migrate: add stop_reason if table predates this column
    try:
        with connection:
            connection.execute(
                "ALTER TABLE calls ADD COLUMN stop_reason TEXT"
            )
    except sqlite3.OperationalError:
        pass  # column already exists

    try:
        client = anthropic.Anthropic()
    except anthropic.APIError as api_error:
        terminal_output.msg_error(
            "Failed to initialize API client: " + str(api_error)
        )
        connection.close()
        sys.exit(1)


    conversation_id: str | None = None
    if interactive_mode:
        conversation_id = uuid4().hex[:12]
        terminal_output.msg_info(
            "Interactive mode ("
            + terminal_output.format_label("conversation_id", conversation_id)
            + ", "
            + terminal_output.format_label("model", model_config["id"])
            + "). /quit or Ctrl-C to exit."
        )

    # -- LAYOUT --------------------------------------------------------

    # Set centered layout for interactive terminal sessions only.
    # This is a data-routing decision (should output be centered?) not a
    # formatting decision (should ANSI codes be used?). The terminal_output
    # module handles its own ANSI detection via STDERR_IS_TERMINAL.
    # Single-shot and piped output stay left-aligned for tool compatibility.
    if interactive_mode and sys.stdout.isatty():
        terminal_output.set_layout(max_width=76, align="center")

    # -- CONVERSATION LOOP ---------------------------------------------

    turn_count: int = 0

    # Session accumulators for summary
    total_tokens_in: int = 0
    total_tokens_out: int = 0
    total_cost: float = 0.0

    while True:

        # Display turn separator
        terminal_output.emit(
            terminal_output.format_labeled_separator("turn " + str(turn_count + 1))
        )

        # Read input
        if turn_count == 0 and has_initial_input:
            pass  # user_input already set from argument or stdin
        else:
            try:
                if interactive_mode:
                    prompt_text: str = terminal_output.apply_style(
                        "[" + model_short + ":" + str(turn_count + 1) + "] > ",
                        terminal_output.STYLE_BOLD
                    )
                else:
                    prompt_text: str = "> "
                user_input = input(prompt_text)
            except (KeyboardInterrupt, EOFError):
                print()
                if turn_count > 0:
                    terminal_output.emit(
                        terminal_output.format_labeled_separator("session")
                    )
                    session_metadata: str = terminal_output.format_metadata_inline([
                        ("turns", str(turn_count)),
                        ("tokens", terminal_output.format_token_counts(
                            total_tokens_in, total_tokens_out)),
                        ("cost", terminal_output.format_cost(total_cost)),
                    ])
                    terminal_output.msg_info(session_metadata)
                break
            stripped_input: str = user_input.strip()

            if stripped_input == "":
                continue

            if stripped_input in ("/quit", "/exit"):
                if turn_count > 0:
                    terminal_output.emit(
                        terminal_output.format_labeled_separator("session")
                    )
                    session_metadata: str = terminal_output.format_metadata_inline([
                        ("turns", str(turn_count)),
                        ("tokens", terminal_output.format_token_counts(
                            total_tokens_in, total_tokens_out)),
                        ("cost", terminal_output.format_cost(total_cost)),
                    ])
                    terminal_output.msg_info(session_metadata)
                break

        messages.append({"role": "user", "content": user_input})

        # CALL
        system_prompt: str | None = None
        api_messages: list[dict[str, str]] = []
        for message in messages:
            if message["role"] == "system":
                system_prompt = message["content"]
            else:
                api_messages.append(message)

        try:
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
            messages.pop()  # remove the failed user message
            if not interactive_mode:
                connection.close()
                sys.exit(1)
            continue

        # Unpack SDK response to plain data immediately
        response_data: dict = {
            "response_text": api_response.content[0].text,
            "tokens_in": api_response.usage.input_tokens,
            "tokens_out": api_response.usage.output_tokens,
            "model": api_response.model,
            "stop_reason": api_response.stop_reason,
        }

        messages.append(
            {"role": "assistant", "content": response_data["response_text"]}
        )

        # DISPLAY
        if sys.stdout.isatty():
            wrapped_response: str = terminal_output.wrap_text(
                response_data["response_text"], width=80
            )
            terminal_height: int = shutil.get_terminal_size().lines
            response_line_count: int = wrapped_response.count("\n") + 1

            if response_line_count > terminal_height:
                pager_command: str = os.environ.get("PAGER", "less -R")
                pager_parts: list[str] = pager_command.split()

                with tempfile.NamedTemporaryFile(
                    mode="w", suffix=".md", delete=False
                ) as pager_file:
                    pager_file.write(wrapped_response)
                    pager_file_path: str = pager_file.name

                try:
                    subprocess.run(pager_parts + [pager_file_path])
                except (FileNotFoundError, OSError):
                    terminal_output.msg_warn(
                        "Pager not available, printing directly."
                    )
                    print(wrapped_response)
                finally:
                    os.unlink(pager_file_path)
            else:
                print(wrapped_response)
        else:
            print(response_data["response_text"])


        tokens_in: int = response_data["tokens_in"]
        tokens_out: int = response_data["tokens_out"]
        input_cost: float = (tokens_in / 1_000_000) * model_config["cost_in"]
        output_cost: float = (tokens_out / 1_000_000) * model_config["cost_out"]
        turn_cost: float = input_cost + output_cost

        # Update session accumulators
        total_tokens_in = total_tokens_in + tokens_in
        total_tokens_out = total_tokens_out + tokens_out
        total_cost = total_cost + turn_cost

        # Display turn metadata
        metadata_line: str = terminal_output.format_metadata_inline([
            ("tokens", terminal_output.format_token_counts(tokens_in, tokens_out)),
            ("cost", terminal_output.format_cost(turn_cost)),
        ])
        terminal_output.msg_info(metadata_line)

        stop_reason: str = response_data["stop_reason"]
        if stop_reason == "max_tokens":
            terminal_output.msg_warn("Stop reason: " + stop_reason + " (response truncated)")
        else:
            terminal_output.msg_debug("Stop reason: " + stop_reason)

        # LOG
        timestamp: str = datetime.now(timezone.utc).isoformat()
        messages_json: str = json.dumps(messages)

        try:
            with connection:
                connection.execute(
                    """
                    INSERT INTO calls (timestamp, model, messages_json,
                                       response_text, tokens_in, tokens_out,
                                       notes, conversation_id, stop_reason)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (timestamp, model_config["id"], messages_json,
                     response_data["response_text"], tokens_in, tokens_out,
                     parsed_arguments.notes, conversation_id, stop_reason),
                )
        except sqlite3.Error as database_error:
            terminal_output.msg_error(
                "Database write failed: " + str(database_error)
            )
            if not interactive_mode:
                connection.close()
                sys.exit(1)

        turn_count = turn_count + 1

        if not interactive_mode:
            break

    # -- CLEANUP -------------------------------------------------------

    connection.close()

    if interactive_mode and turn_count > 0:
        terminal_output.msg_info(
            "Session ended. " + str(turn_count) + " turns logged."
        )
    elif not interactive_mode and turn_count > 0:
        terminal_output.msg_success("Logged to " + DATABASE_PATH)
