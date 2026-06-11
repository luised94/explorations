# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""Iterative refinement. Each iteration is a fresh single-message call; the
only carried context is the previous response embedded in the next prompt.
Optionally interactive: the user can steer each iteration or quit early."""

import argparse
import sys
from datetime import datetime
from pathlib import Path

import httpx

from llm_config import PROVIDERS, call_llm

# --- CONFIG ---

def parse_args() -> argparse.Namespace:
    """Parse command-line arguments for the loop pattern."""
    parser = argparse.ArgumentParser(
        description="Iteratively refine an LLM response over N fresh calls.")
    parser.add_argument("initial_prompt", help="Prompt text used in every iteration")
    parser.add_argument("filepath", nargs="?", default=None,
                        help="Optional file included as context in the first iteration only")
    parser.add_argument("--iterations", type=int, default=3,
                        help="Number of iterations (default: 3)")
    parser.add_argument("--interactive", action="store_true",
                        help="Print each response and prompt for refinement instructions")
    parser.add_argument("--provider", default="anthropic", choices=sorted(PROVIDERS),
                        help="Provider name from llm_config.PROVIDERS")
    parser.add_argument("--model", default=None,
                        help="Model string (default: provider's default_model)")
    parser.add_argument("--output", default=".",
                        help="Directory for the response files (default: current directory)")
    return parser.parse_args()


# --- TRANSFORM ---
# No open(), no print(), no httpx. Strings/dicts in, strings/dicts out.

def build_iteration_messages(prompt: str, iteration: int, total: int,
                             previous_response: str | None = None,
                             filename: str | None = None,
                             file_text: str | None = None,
                             refinement: str | None = None) -> list[dict]:
    """Assemble the user message for one iteration of the refinement loop."""
    parts = [prompt]
    if iteration == 1:
        if filename is not None:
            parts.append(f"--- BEGIN {filename} ---\n{file_text}\n--- END {filename} ---")
    else:
        parts.append(f"--- BEGIN previous_response ---\n{previous_response}\n"
                     f"--- END previous_response ---")
        parts.append(f"Iteration {iteration} of {total}. Refine your previous response.")
        if refinement:
            parts.append(refinement)
    return [{"role": "user", "content": "\n\n".join(parts)}]


def combine_responses(responses: list[str]) -> str:
    """Concatenate iteration responses under '## Iteration {i}' headers."""
    sections = [f"## Iteration {i}\n\n{text}" for i, text in enumerate(responses, start=1)]
    return "\n\n".join(sections)


# --- MAIN ---

def main() -> None:
    """Loop: build iteration message -> call -> write -> (optionally) ask user."""
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

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = Path(args.output)
    total = args.iterations

    responses: list[str] = []
    previous_response = None
    refinement = None
    failed = False

    for iteration in range(1, total + 1):
        messages = build_iteration_messages(
            args.initial_prompt, iteration, total,
            previous_response=previous_response,
            filename=filename, file_text=file_text,
            refinement=refinement)
        try:
            response_text = call_llm(args.provider, args.model, messages)
        except httpx.HTTPStatusError:
            failed = True  # call_llm already printed the HTTP error to stderr
            break

        responses.append(response_text)
        previous_response = response_text
        refinement = None

        iter_path = output_dir / f"loop_iter{iteration}_{timestamp}.md"
        iter_path.write_text(response_text)
        print(f"Wrote {iter_path}")

        if args.interactive and iteration < total:
            print(response_text)
            try:
                answer = input(f"[iteration {iteration}/{total}] Enter refinement "
                               f"instructions (empty to continue, q to quit): ").strip()
            except EOFError:
                print()
                break  # Ctrl-D at the prompt == q: stop, write combined file
            if answer == "q":
                break
            if answer:
                refinement = answer

    if responses:
        combined_path = output_dir / f"loop_combined_{timestamp}.md"
        combined_path.write_text(combine_responses(responses))
        print(f"Wrote {combined_path}")

    if failed:
        sys.exit(1)


if __name__ == "__main__":
    main()
