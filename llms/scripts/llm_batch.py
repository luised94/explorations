# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""Many files, many calls. Same prompt sent once per file, one response file
per input. Sequential. HTTP failures skip the file and continue; if any were
skipped, exit 1 after the summary."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import httpx

from llm_config import PROVIDERS, call_llm

# --- CONFIG ---


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the batch pattern."""
    parser = argparse.ArgumentParser(
        description="Send the same prompt to an LLM once per input file."
    )
    parser.add_argument("prompt", help="Prompt text, sent before each file's content")
    parser.add_argument(
        "filepath", nargs="*", help="Paths to files to process (zero or more)"
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
        help="Directory for the response files (default: current directory)",
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


def build_messages(prompt: str, filename: str, file_text: str) -> list[dict]:
    """Assemble the single user message: prompt text followed by the delimited file block."""
    content = (
        f"{prompt}\n\n--- BEGIN {filename} ---\n{file_text}\n--- END {filename} ---"
    )
    return [{"role": "user", "content": content}]


# --- MAIN ---


def main() -> None:
    """Collect -> for each file: read -> transform -> call -> write. Then summarize."""
    args = parse_args()

    input_paths = collect_paths(args.filepath, args.dir, args.ext)
    if not input_paths:
        print("No input files: pass file paths and/or --dir.", file=sys.stderr)
        sys.exit(1)

    total = len(input_paths)
    written = 0
    skipped = 0

    for index, input_path in enumerate(input_paths, start=1):
        try:
            file_text = input_path.read_text()
        except FileNotFoundError:
            print(f"File not found: {input_path}", file=sys.stderr)
            sys.exit(1)

        messages = build_messages(args.prompt, input_path.name, file_text)
        try:
            response_text = call_llm(args.provider, args.model, messages)
        except httpx.HTTPStatusError:
            skipped += 1  # call_llm already printed the HTTP error to stderr
            continue

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_path = Path(args.output) / f"{input_path.stem}_response_{timestamp}.md"
        output_path.write_text(response_text)
        written += 1
        print(f"[{index}/{total}] {input_path} -> {output_path}")

    print(f"Processed {total} files, wrote {written} responses to {args.output}")
    if skipped:
        print(f"Skipped {skipped} files due to errors", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
