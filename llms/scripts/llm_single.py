# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""One prompt, one file. Read the file, send prompt + delimited file content
as a single user message, write the response to <stem>_response_<timestamp>.md."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import httpx

from llm_config import PROVIDERS, call_llm

# --- CONFIG ---


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the single-file pattern."""
    parser = argparse.ArgumentParser(
        description="Send one prompt and one file to an LLM."
    )
    parser.add_argument("prompt", help="Prompt text, sent before the file content")
    parser.add_argument("filepath", help="Path to the file to attach")
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
        help="Directory for the response file (default: current directory)",
    )
    return parser.parse_args()


# --- TRANSFORM ---
# No open(), no print(), no httpx. Strings/dicts in, strings/dicts out.


def build_messages(prompt: str, filename: str, file_text: str) -> list[dict]:
    """Assemble the single user message: prompt text followed by the delimited file block."""
    content = (
        f"{prompt}\n\n--- BEGIN {filename} ---\n{file_text}\n--- END {filename} ---"
    )
    return [{"role": "user", "content": content}]


# --- MAIN ---


def main() -> None:
    """Read -> transform -> call -> write."""
    args = parse_args()

    input_path = Path(args.filepath)
    try:
        file_text = input_path.read_text()
    except FileNotFoundError:
        print(f"File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    messages = build_messages(args.prompt, input_path.name, file_text)
    try:
        response_text = call_llm(args.provider, args.model, messages)
    except httpx.HTTPStatusError:
        sys.exit(1)  # call_llm already printed the HTTP error to stderr

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output) / f"{input_path.stem}_response_{timestamp}.md"
    output_path.write_text(response_text)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
