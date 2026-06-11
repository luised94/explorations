# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""Many files, one call. Collect files from positional args and/or --dir,
append them all into a single user message after the prompt, write one response
to appended_response_<timestamp>.md."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import httpx

from llm_config import PROVIDERS, call_llm

# --- CONFIG ---


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the append pattern."""
    parser = argparse.ArgumentParser(
        description="Send one prompt and many files to an LLM in a single message."
    )
    parser.add_argument("prompt", help="Prompt text, sent before the file blocks")
    parser.add_argument(
        "filepath", nargs="*", help="Paths to files to attach (zero or more)"
    )
    parser.add_argument(
        "--dir", default=None, help="Directory to glob for additional input files"
    )
    parser.add_argument(
        "--ext", default=None, help="Filter --dir files by extension, e.g. .py"
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
        help="Directory for the response file (default: current directory)",
    )
    return parser.parse_args()


# --- DATA ---


def collect_paths(
    positional: list[str], dir_arg: str | None, ext: str | None
) -> list[Path]:
    """Combine positional paths with a directory glob, deduplicate, sort alphabetically."""
    paths = [Path(p) for p in positional]
    if dir_arg is not None:
        pattern = f"*{ext}" if ext else "*"
        paths.extend(p for p in Path(dir_arg).glob(pattern) if p.is_file())
    return sorted(set(paths))


# --- TRANSFORM ---
# No open(), no print(), no httpx. Strings/dicts in, strings/dicts out.


def build_messages_multi(prompt: str, files: list[tuple[str, str]]) -> list[dict]:
    """Assemble one user message: prompt text, then each (filename, text) as a delimited block."""
    blocks = [
        f"--- BEGIN {filename} ---\n{file_text}\n--- END {filename} ---"
        for filename, file_text in files
    ]
    content = "\n\n".join([prompt, *blocks])
    return [{"role": "user", "content": content}]


# --- MAIN ---


def main() -> None:
    """Collect -> read -> transform -> call -> write."""
    args = parse_args()

    input_paths = collect_paths(args.filepath, args.dir, args.ext)
    if not input_paths:
        print("No input files: pass file paths and/or --dir.", file=sys.stderr)
        sys.exit(1)

    files = []
    for path in input_paths:
        try:
            files.append((path.name, path.read_text()))
        except FileNotFoundError:
            print(f"File not found: {path}", file=sys.stderr)
            sys.exit(1)

    messages = build_messages_multi(args.prompt, files)
    try:
        response_text = call_llm(args.provider, args.model, messages)
    except httpx.HTTPStatusError:
        sys.exit(1)  # call_llm already printed the HTTP error to stderr

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = Path(args.output) / f"appended_response_{timestamp}.md"
    output_path.write_text(response_text)
    print(f"Wrote {output_path}")


if __name__ == "__main__":
    main()
