# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""Multi-turn conversation REPL. Full history is sent with every call. An
optional file is folded into the first user message as delimited context.
On exit, the transcript is written to interactive_<timestamp>.md."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import httpx

from llm_config import PROVIDERS, call_llm

# --- CONFIG ---


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the interactive pattern."""
    parser = argparse.ArgumentParser(
        description="Hold a multi-turn conversation with an LLM."
    )
    parser.add_argument(
        "filepath",
        nargs="?",
        default=None,
        help="Optional file included as context in the first message",
    )
    parser.add_argument(
        "--provider",
        default="anthropic",
        choices=sorted(PROVIDERS),
        help="Provider name from llm_config.PROVIDERS",
    )
    parser.add_argument(
        "--model", default=None, help="Model string (default: provider's default_model)"
    )
    parser.add_argument(
        "--output",
        default=".",
        help="Directory for the transcript file (default: current directory)",
    )
    return parser.parse_args()


# --- TRANSFORM ---
# No open(), no print(), no httpx. Strings/dicts in, strings/dicts out.


def build_first_content(text: str, filename: str | None, file_text: str | None) -> str:
    """Combine the user's first input with optional delimited file context."""
    if filename is None:
        return text
    return f"{text}\n\n--- BEGIN {filename} ---\n{file_text}\n--- END {filename} ---"


def format_conversation(history: list[dict]) -> str:
    """Format the conversation history as a markdown transcript string."""
    sections = [
        f"## {message['role'].upper()}\n{message['content']}" for message in history
    ]
    return "\n\n".join(sections) + "\n"


# --- MAIN ---


def main() -> None:
    """REPL: read input -> append -> call with full history -> print -> repeat."""
    args = parse_args()

    filename = None
    file_text = None
    if args.filepath is not None:
        input_path = Path(args.filepath)
        try:
            file_text = input_path.read_text()
        except FileNotFoundError:
            print(f"File not found: {input_path}", file=sys.stderr)
            sys.exit(1)
        filename = input_path.name

    history: list[dict] = []

    try:
        while True:
            text = input("> ").strip()
            if text in ("quit", "exit"):
                break
            if not text:
                continue

            if not history:
                content = build_first_content(text, filename, file_text)
            else:
                content = text

            attempt = history + [{"role": "user", "content": content}]
            try:
                response_text = call_llm(args.provider, args.model, attempt)
            except httpx.HTTPStatusError:
                # call_llm already printed the HTTP error to stderr.
                print("(LLM call failed, try again)")
                continue

            history = attempt + [{"role": "assistant", "content": response_text}]
            print(f"\n{response_text}\n")
    except (KeyboardInterrupt, EOFError):
        print()

    if history:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(args.output) / f"interactive_{timestamp}.md"
        output_path.write_text(format_conversation(history))
        print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
