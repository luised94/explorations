# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""Manifest-driven calls. Each TSV line pairs a filepath with a prompt; one
LLM call and one response file per entry. Lines starting with # are comments,
empty lines are skipped, and a line with no tab gets the default prompt."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import httpx

from llm_config import PROVIDERS, call_llm

DEFAULT_PROMPT = "Analyze this file."

# --- CONFIG ---


def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the manifest pattern."""
    parser = argparse.ArgumentParser(
        description="Send per-file prompts to an LLM as listed in a TSV manifest."
    )
    parser.add_argument(
        "manifest_path", help="Path to a TSV manifest: filepath<TAB>prompt per line"
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


# --- TRANSFORM ---
# No open(), no print(), no httpx. Strings/dicts in, strings/dicts out.


def parse_manifest(manifest_text: str) -> list[dict]:
    """Parse TSV manifest text into a list of {"filepath": str, "prompt": str} dicts."""
    entries = []
    for line in manifest_text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "\t" in stripped:
            filepath, prompt = stripped.split("\t", 1)
            entries.append(
                {
                    "filepath": filepath.strip(),
                    "prompt": prompt.strip() or DEFAULT_PROMPT,
                }
            )
        else:
            entries.append({"filepath": stripped, "prompt": DEFAULT_PROMPT})
    return entries


def build_messages(prompt: str, filename: str, file_text: str) -> list[dict]:
    """Assemble the single user message: prompt text followed by the delimited file block."""
    content = (
        f"{prompt}\n\n--- BEGIN {filename} ---\n{file_text}\n--- END {filename} ---"
    )
    return [{"role": "user", "content": content}]


# --- MAIN ---


def main() -> None:
    """Read manifest -> parse -> for each entry: read -> transform -> call -> write."""
    args = parse_args()

    manifest_path = Path(args.manifest_path)
    try:
        manifest_text = manifest_path.read_text()
    except FileNotFoundError:
        print(f"File not found: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    entries = parse_manifest(manifest_text)
    if not entries:
        print(f"No entries in manifest: {manifest_path}", file=sys.stderr)
        sys.exit(1)

    total = len(entries)
    written = 0
    skipped = 0

    for index, entry in enumerate(entries, start=1):
        input_path = Path(entry["filepath"])
        try:
            file_text = input_path.read_text()
        except FileNotFoundError:
            print(f"File not found: {input_path}", file=sys.stderr)
            sys.exit(1)

        messages = build_messages(entry["prompt"], input_path.name, file_text)
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
