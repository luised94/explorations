# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
"""One CLI, six interaction patterns for sending prompts and files to LLM APIs.
Subcommands: single, append, batch, manifest, loop, interactive.
Run with: uv run llm.py <subcommand> ...
"""

import argparse
import os
import sys
from datetime import datetime
from pathlib import Path
import httpx

try:
    import readline  # noqa: F401  -- arrow keys / history for input() REPLs
except ImportError:
    pass  # not available on some platforms; input() still works, just bare
# --- CONFIG ---
# Constants, provider dict, argparse.
MAX_TOKENS = 4096
TIMEOUT_SECONDS = 120.0
DEFAULT_MANIFEST_PROMPT = "Analyze this file."


# Provider transform/extract functions live here, next to the dict that
# references them, because the dict is built at import time and needs them
# defined first. They are pure (data in, data out) like everything in
# TRANSFORM, but they are part of the provider table, not toolkit logic.
def anthropic_transform_messages(system: str | None, messages: list[dict]) -> dict:
    """Return Anthropic's body fragment: chat messages plus a top-level system field."""
    body: dict = {"messages": messages}
    if system is not None:
        body["system"] = system
    return body


def anthropic_extract_response(data: dict) -> str:
    """Concatenate the text blocks from an Anthropic messages-API response."""
    return "".join(
        block["text"] for block in data["content"] if block["type"] == "text"
    )


def openai_transform_messages(system: str | None, messages: list[dict]) -> dict:
    """Return OpenAI's body fragment: system rides in the messages array."""
    if system is not None:
        messages = [{"role": "system", "content": system}, *messages]
    return {"messages": messages}


def openai_extract_response(data: dict) -> str:
    """Pull the response text from an OpenAI chat-completions response."""
    return data["choices"][0]["message"]["content"]


def gemini_transform_messages(system: str | None, messages: list[dict]) -> dict:
    """Reshape messages into Gemini's contents/parts format with role mapping."""
    contents = []
    if system is not None:
        contents.append({"role": "user", "parts": [{"text": f"[System] {system}"}]})
    for m in messages:
        role = "model" if m["role"] == "assistant" else m["role"]
        contents.append({"role": role, "parts": [{"text": m["content"]}]})
    return {"contents": contents}


def gemini_extract_response(data: dict) -> str:
    """Pull the response text from a Gemini generateContent response."""
    return data["candidates"][0]["content"]["parts"][0]["text"]


# To add a new provider: add an entry here following the pattern below.
# Then add its env var name. Each entry needs ALL of these fields (use
# lambda-returning-{} for auth mechanisms the provider doesn't use):
#   url_template       POST endpoint; may contain a {model} placeholder
#   env_key            environment variable holding the API key
#   auth_header        function: api_key -> header dict ({} if auth is not header-based)
#   auth_params        function: api_key -> query-param dict ({} if auth is not query-based)
#   extra_headers      static provider-required headers ({} if none)
#   body_extras        function: model -> dict merged into the body (model name,
#                      token limits -- whatever the provider wants top-level)
#   transform_messages function: (system or None, messages list) -> provider body fragment
#   extract_response   function: response JSON -> response text
#   default_model      model string used when --model is not given
PROVIDERS: dict = {
    "anthropic": {
        "url_template": "https://api.anthropic.com/v1/messages",
        "env_key": "ANTHROPIC_API_KEY",
        "auth_header": lambda api_key: {"x-api-key": api_key},
        "auth_params": lambda api_key: {},
        "extra_headers": {"anthropic-version": "2023-06-01"},
        "body_extras": lambda model: {"model": model, "max_tokens": MAX_TOKENS},
        "transform_messages": anthropic_transform_messages,
        "extract_response": anthropic_extract_response,
        "default_model": "claude-sonnet-4-20250514",
    },
    "openai": {
        "url_template": "https://api.openai.com/v1/chat/completions",
        "env_key": "OPENAI_API_KEY",
        "auth_header": lambda api_key: {"Authorization": f"Bearer {api_key}"},
        "auth_params": lambda api_key: {},
        "extra_headers": {},
        "body_extras": lambda model: {"model": model, "max_tokens": MAX_TOKENS},
        "transform_messages": openai_transform_messages,
        "extract_response": openai_extract_response,
        "default_model": "gpt-4o",
    },
    "gemini": {
        "url_template": (
            "https://generativelanguage.googleapis.com/v1beta/"
            "models/{model}:generateContent"
        ),
        "env_key": "GEMINI_API_KEY",
        "auth_header": lambda api_key: {"x-goog-api-key": api_key},
        "auth_params": lambda api_key: {},
        "extra_headers": {},
        "body_extras": lambda model: {
            "generationConfig": {"maxOutputTokens": MAX_TOKENS}
        },
        "transform_messages": gemini_transform_messages,
        "extract_response": gemini_extract_response,
        "default_model": "gemini-2.0-flash",
    },
}


def parse_args() -> argparse.Namespace:
    """Build the subcommand CLI and parse arguments."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--provider",
        default="anthropic",
        choices=sorted(PROVIDERS),
        help="Provider name (default: anthropic)",
    )
    common.add_argument(
        "--model", default=None, help="Model string (default: provider's default_model)"
    )
    common.add_argument(
        "--output",
        default=".",
        help="Directory for output files (default: current directory)",
    )
    common.add_argument("--system", default=None, help="System prompt text")
    common.add_argument(
        "--system-file",
        default=None,
        help="Path to a file containing the system prompt",
    )
    parser = argparse.ArgumentParser(
        description="Send prompts and files to LLM APIs: six interaction patterns."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser(
        "single", parents=[common], help="One prompt, one file, one call"
    )
    p.add_argument("prompt", help="Prompt text, sent before the file content")
    p.add_argument("filepath", help="Path to the file to attach")
    p.set_defaults(func=cmd_single)
    p = sub.add_parser(
        "append", parents=[common], help="One prompt, many files appended into one call"
    )
    p.add_argument("prompt", help="Prompt text, sent before the file blocks")
    p.add_argument("filepath", nargs="*", help="Paths to files to attach")
    p.add_argument("--dir", default=None, help="Directory to glob for input files")
    p.add_argument(
        "--ext", default=None, help="Filter --dir files by extension, e.g. .py"
    )
    p.set_defaults(func=cmd_append)
    p = sub.add_parser(
        "batch",
        parents=[common],
        help="Same prompt sent once per file, one response file each",
    )
    p.add_argument("prompt", help="Prompt text, sent before each file's content")
    p.add_argument("filepath", nargs="*", help="Paths to files to process")
    p.add_argument("--dir", default=None, help="Directory to glob for input files")
    p.add_argument(
        "--ext", default=None, help="Filter --dir files by extension, e.g. .py"
    )
    p.set_defaults(func=cmd_batch)
    p = sub.add_parser(
        "manifest",
        parents=[common],
        help="TSV manifest of filepath<TAB>prompt pairs, one call each",
    )
    p.add_argument("manifest_path", help="Path to the TSV manifest")
    p.set_defaults(func=cmd_manifest)
    p = sub.add_parser(
        "loop", parents=[common], help="Iterative refinement over N fresh calls"
    )
    p.add_argument("initial_prompt", help="Prompt text used in every iteration")
    p.add_argument(
        "filepath",
        nargs="?",
        default=None,
        help="Optional file included in the first iteration only",
    )
    p.add_argument(
        "--iterations", type=int, default=3, help="Number of iterations (default: 3)"
    )
    p.add_argument(
        "--interactive",
        action="store_true",
        help="Print each response and prompt for refinement instructions",
    )
    p.set_defaults(func=cmd_loop)
    p = sub.add_parser(
        "interactive", parents=[common], help="Multi-turn conversation REPL"
    )
    p.add_argument(
        "filepath",
        nargs="?",
        default=None,
        help="Optional file included as context in the first message",
    )
    p.set_defaults(func=cmd_interactive)
    return parser.parse_args()


# --- TRANSFORM ---
# All pure functions: message builders, delimiter wrapping, manifest parsing,
# conversation formatting. No open(), no print(), no httpx.
def file_block(filename: str, text: str) -> str:
    """Wrap text in the toolkit's BEGIN/END delimiter convention."""
    return f"--- BEGIN {filename} ---\n{text}\n--- END {filename} ---"


def build_user_content(prompt: str, files: list[tuple[str, str]]) -> str:
    """Assemble user message content: prompt text, then each (filename, text) as a block."""
    return "\n\n".join([prompt, *(file_block(name, text) for name, text in files)])


def build_iteration_content(
    prompt: str,
    iteration: int,
    total: int,
    previous_response: str | None,
    files: list[tuple[str, str]],
    refinement: str | None,
) -> str:
    """Assemble the user message content for one iteration of the refinement loop."""
    if iteration == 1:
        return build_user_content(prompt, files)
    parts = [prompt, file_block("previous_response", previous_response)]
    if refinement:
        parts.append(refinement)
    parts.append(f"Iteration {iteration} of {total}. Refine your previous response.")
    return "\n\n".join(parts)


def parse_manifest(manifest_text: str) -> tuple[list[tuple[str, str]], list[str]]:
    """Parse TSV manifest text into ((filepath, prompt) tuples, warning strings).

    Warnings flag lines that contain spaces but no tab: almost certainly a
    manifest authored with spaces (or tab-converted by an editor), which would
    silently become a bogus filepath with the default prompt.
    """
    entries = []
    warnings = []
    for lineno, line in enumerate(manifest_text.splitlines(), start=1):
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if "\t" in stripped:
            filepath, prompt = stripped.split("\t", 1)
            entries.append(
                (filepath.strip(), prompt.strip() or DEFAULT_MANIFEST_PROMPT)
            )
        else:
            if " " in stripped:
                warnings.append(
                    f"line {lineno}: no tab but contains spaces -- treating the whole "
                    f"line as a filepath ({stripped!r}); use a TAB between filepath "
                    f"and prompt"
                )
            entries.append((stripped, DEFAULT_MANIFEST_PROMPT))
    return entries, warnings


def combine_responses(responses: list[str]) -> str:
    """Concatenate iteration responses under '## Iteration {i}' headers."""
    sections = [
        f"## Iteration {i}\n\n{text}" for i, text in enumerate(responses, start=1)
    ]
    return "\n\n".join(sections)


def format_conversation(history: list[dict]) -> str:
    """Format the conversation history as a markdown transcript string."""
    sections = [
        f"## {message['role'].upper()}\n{message['content']}" for message in history
    ]
    return "\n\n".join(sections) + "\n"


# --- IO ---
# call_llm, file reading, file writing. Collision avoidance lives in
# write_response (not TRANSFORM) because checking for an existing file
# is a filesystem read.
def call_llm(
    provider_name: str, model: str | None, system: str | None, messages: list[dict]
) -> str:
    """POST system + messages to the named provider and return the response text."""
    provider = PROVIDERS[provider_name]
    api_key = os.environ.get(provider["env_key"])
    if api_key is None:
        print(
            f"Missing API key: set the {provider['env_key']} environment variable.",
            file=sys.stderr,
        )
        sys.exit(1)
    model = model or provider["default_model"]
    url = provider["url_template"].format(model=model)
    body = {
        **provider["transform_messages"](system, messages),
        **provider["body_extras"](model),
    }
    headers = {
        "content-type": "application/json",
        **provider["auth_header"](api_key),
        **provider["extra_headers"],
    }
    try:
        response = httpx.post(
            url,
            params=provider["auth_params"](api_key),
            json=body,
            headers=headers,
            timeout=TIMEOUT_SECONDS,
        )
    except httpx.HTTPError as exc:
        # Transport-level failure: no network, DNS, timeout, broken connection.
        # Same contract as the status-error path below: print here, raise so
        # the caller decides exit vs skip.
        print(f"Request failed ({type(exc).__name__}): {exc}", file=sys.stderr)
        raise
    if response.status_code >= 400:
        # Print here so error formatting lives in one place; raise so the
        # caller decides whether to exit (single-call commands) or skip and
        # continue (batch-style commands).
        print(f"HTTP {response.status_code}: {response.text}", file=sys.stderr)
        response.raise_for_status()
    return provider["extract_response"](response.json())


class FileReadError(Exception):
    """Raised by read_file after the error is printed to stderr.

    Mirrors call_llm's contract: formatting lives in one place here; the
    caller decides whether to exit (single-call commands) or skip and
    continue (batch-style commands).
    """


def read_file(path: Path, encoding: str | None = None) -> str:
    """Read a text file; print an error to stderr and raise FileReadError on failure."""
    try:
        text = path.read_text(encoding=encoding)
    except FileNotFoundError as exc:
        print(f"File not found: {path}", file=sys.stderr)
        raise FileReadError(str(path)) from exc
    except IsADirectoryError as exc:
        print(f"Is a directory, not a file: {path}", file=sys.stderr)
        raise FileReadError(str(path)) from exc
    except UnicodeDecodeError as exc:
        print(f"Not readable as text (binary file?): {path}", file=sys.stderr)
        raise FileReadError(str(path)) from exc
    except OSError as exc:
        print(f"Cannot read {path}: {exc}", file=sys.stderr)
        raise FileReadError(str(path)) from exc
    if not text:
        # C11: an empty block still gets sent and billed; the model will
        # gamely analyze nothing. Warn but proceed.
        print(f"Warning: {path} is empty", file=sys.stderr)
    return text


def collect_paths(
    positional: list[str], dir_arg: str | None, ext: str | None
) -> list[Path]:
    """Combine positional paths with a directory glob, deduplicate, sort alphabetically."""
    paths = [Path(p) for p in positional]
    if dir_arg is not None:
        if ext is not None and not ext.startswith("."):
            ext = f".{ext}"  # C2: '--ext py' means '*.py', not '*py' (which matches 'copy')
        pattern = f"*{ext}" if ext else "*"
        paths.extend(p for p in Path(dir_arg).glob(pattern) if p.is_file())
    # C6: dedupe on the resolved path so ./a.py and a.py collapse; keep the
    # original (shorter) spelling for display and output-filename stems.
    unique: dict[Path, Path] = {}
    for p in paths:
        unique.setdefault(p.resolve(), p)
    return sorted(unique.values())


def write_response(output_dir: str, filename: str, text: str) -> Path:
    """Write text to output_dir/filename, appending _2, _3, ... if the path exists."""
    path = Path(output_dir) / filename
    stem, suffix = path.stem, path.suffix
    counter = 2
    while True:
        try:
            # C24: exclusive create is atomic, so two concurrent runs landing on
            # the same name can't clobber each other (exists()-then-write could).
            with open(path, "x") as f:
                f.write(text)
            return path
        except FileExistsError:
            path = Path(output_dir) / f"{stem}_{counter}{suffix}"
            counter += 1


# --- COMMANDS ---
# One function per subcommand. Each sequences: read -> transform -> call -> write.
# These are the only functions that mix IO and transforms.
def cmd_single(args: argparse.Namespace, system: str | None) -> None:
    """One prompt, one file, one call, one response file."""
    input_path = Path(args.filepath)
    try:
        content = build_user_content(
            args.prompt, [(input_path.name, read_file(input_path))]
        )
    except FileReadError:
        sys.exit(1)  # read_file already printed the error to stderr
    messages = [{"role": "user", "content": content}]
    try:
        response_text = call_llm(args.provider, args.model, system, messages)
    except httpx.HTTPError:
        sys.exit(1)  # call_llm already printed the error to stderr
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = write_response(
        args.output, f"{input_path.stem}_response_{timestamp}.md", response_text
    )
    print(f"Wrote {out}")


def cmd_append(args: argparse.Namespace, system: str | None) -> None:
    """Many files appended into one user message, one call, one response file."""
    input_paths = collect_paths(args.filepath, args.dir, args.ext)
    if not input_paths:
        print("No input files: pass file paths and/or --dir.", file=sys.stderr)
        sys.exit(1)
    try:
        files = [(p.name, read_file(p)) for p in input_paths]
    except FileReadError:
        sys.exit(
            1
        )  # read_file already printed the error; a partial append would mislead
    content = build_user_content(args.prompt, files)
    messages = [{"role": "user", "content": content}]
    try:
        response_text = call_llm(args.provider, args.model, system, messages)
    except httpx.HTTPError:
        sys.exit(1)  # call_llm already printed the error to stderr
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = write_response(
        args.output, f"appended_response_{timestamp}.md", response_text
    )
    print(f"Wrote {out}")


def run_entries(
    entries: list[tuple[Path, str]], args: argparse.Namespace, system: str | None
) -> None:
    """Call the LLM once per (path, prompt) entry; skip unreadable files and
    failed calls, but abort immediately on auth errors (401/403)."""
    total = len(entries)
    written = 0
    skipped = 0
    for index, (input_path, prompt) in enumerate(entries, start=1):
        try:
            content = build_user_content(
                prompt, [(input_path.name, read_file(input_path))]
            )
        except FileReadError:
            skipped += 1  # read_file already printed the error to stderr
            continue
        messages = [{"role": "user", "content": content}]
        try:
            response_text = call_llm(args.provider, args.model, system, messages)
        except httpx.HTTPStatusError as exc:
            # call_llm already printed the error to stderr.
            if exc.response.status_code in (401, 403):
                # C14c: auth failure is not per-entry -- every remaining call
                # would fail identically, one wasted round trip each. Abort.
                print(
                    "Auth error: aborting batch (remaining entries would all fail).",
                    file=sys.stderr,
                )
                sys.exit(1)
            skipped += 1
            continue
        except httpx.HTTPError:
            skipped += 1  # call_llm already printed the error to stderr
            continue
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = write_response(
            args.output, f"{input_path.stem}_response_{timestamp}.md", response_text
        )
        written += 1
        print(f"[{index}/{total}] {input_path} -> {out}")
    print(f"Processed {total} files, wrote {written} responses to {args.output}")
    if skipped:
        print(f"Skipped {skipped} files due to errors", file=sys.stderr)
        sys.exit(1)


def cmd_batch(args: argparse.Namespace, system: str | None) -> None:
    """Same prompt sent once per file; one response file per input."""
    input_paths = collect_paths(args.filepath, args.dir, args.ext)
    if not input_paths:
        print("No input files: pass file paths and/or --dir.", file=sys.stderr)
        sys.exit(1)
    run_entries([(p, args.prompt) for p in input_paths], args, system)


def cmd_manifest(args: argparse.Namespace, system: str | None) -> None:
    """TSV manifest drives per-file prompts; one call and one response file per entry."""
    manifest_path = Path(args.manifest_path)
    try:
        manifest_text = read_file(manifest_path, encoding="utf-8-sig")
    except FileReadError:
        sys.exit(1)  # read_file already printed the error to stderr
    entries, warnings = parse_manifest(manifest_text)
    for warning in warnings:
        print(f"Manifest warning, {warning}", file=sys.stderr)
    if not entries:
        print(f"No entries in manifest: {manifest_path}", file=sys.stderr)
        sys.exit(1)
    # C19: relative entries resolve against the manifest's directory, so a
    # manifest can live next to its files; absolute entries pass through
    # unchanged (Path '/' with an absolute right side returns the right side).
    run_entries(
        [(manifest_path.parent / Path(fp), prompt) for fp, prompt in entries],
        args,
        system,
    )


def cmd_loop(args: argparse.Namespace, system: str | None) -> None:
    """Iterative refinement: each iteration is a fresh call carrying the previous response."""
    files = []
    name_prefix = "loop"  # C8: distinguish runs over different inputs
    if args.filepath is not None:
        input_path = Path(args.filepath)
        try:
            files = [(input_path.name, read_file(input_path))]
        except FileReadError:
            sys.exit(1)  # read_file already printed the error to stderr
        name_prefix = f"loop_{input_path.stem}"
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    total = args.iterations
    responses: list[str] = []
    previous_response = None
    refinement = None
    failed = False
    try:
        for iteration in range(1, total + 1):
            content = build_iteration_content(
                args.initial_prompt,
                iteration,
                total,
                previous_response,
                files,
                refinement,
            )
            messages = [{"role": "user", "content": content}]
            try:
                response_text = call_llm(args.provider, args.model, system, messages)
            except httpx.HTTPError:
                failed = True  # call_llm already printed the error to stderr
                break
            responses.append(response_text)
            previous_response = response_text
            refinement = None
            out = write_response(
                args.output,
                f"{name_prefix}_iter{iteration}_{timestamp}.md",
                response_text,
            )
            print(f"Wrote {out}")
            if args.interactive:
                print(response_text)  # C25: also shown for the final iteration
                if iteration < total:
                    try:
                        answer = input(
                            f"[iteration {iteration}/{total}] Enter refinement "
                            f"instructions (empty to continue, q to quit): "
                        ).strip()
                    except EOFError:
                        print()
                        break  # Ctrl-D at the prompt == q: stop, write combined file
                    if answer == "q":
                        break
                    if answer:
                        refinement = answer
    except KeyboardInterrupt:
        # C9: Ctrl-C stops iterating but still writes the combined file below,
        # matching cmd_interactive's transcript-on-interrupt behavior.
        print()
    if responses:
        out = write_response(
            args.output,
            f"{name_prefix}_combined_{timestamp}.md",
            combine_responses(responses),
        )
        print(f"Wrote {out}")
    if failed:
        sys.exit(1)


def cmd_interactive(args: argparse.Namespace, system: str | None) -> None:
    """Multi-turn REPL; full history sent each call; transcript written on exit."""
    files = []
    if args.filepath is not None:
        input_path = Path(args.filepath)
        try:
            files = [(input_path.name, read_file(input_path))]
        except FileReadError:
            sys.exit(1)  # read_file already printed the error to stderr
    history: list[dict] = []
    last_failed: str | None = None  # C23: failed prompt, resendable via empty Enter
    try:
        while True:
            text = input("> ").strip()
            if text in ("quit", "exit", "q"):
                break
            if not text:
                if last_failed is None:
                    continue
                text = last_failed
                print(f"(retrying: {text})")
            content = build_user_content(text, files) if not history else text
            attempt = history + [{"role": "user", "content": content}]
            try:
                response_text = call_llm(args.provider, args.model, system, attempt)
            except httpx.HTTPError:
                # call_llm already printed the error to stderr.
                last_failed = text
                print("(LLM call failed -- press Enter to retry, or type a new prompt)")
                continue
            last_failed = None
            history = attempt + [{"role": "assistant", "content": response_text}]
            print(f"\n{response_text}\n")
    except (KeyboardInterrupt, EOFError):
        print()
    if history:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = write_response(
            args.output, f"interactive_{timestamp}.md", format_conversation(history)
        )
        print(f"Wrote {out}")


# --- MAIN ---
def main() -> None:
    """Parse arguments, resolve the system prompt, dispatch to the subcommand."""
    args = parse_args()
    if args.system is not None and args.system_file is not None:
        print("Pass --system or --system-file, not both.", file=sys.stderr)
        sys.exit(1)
    system = args.system
    if args.system_file:
        try:
            system = read_file(Path(args.system_file))
        except FileReadError:
            sys.exit(1)  # read_file already printed the error to stderr
    # C7: create the output directory up front -- discovering it's missing
    # after a successful (paid) API call would lose the response.
    Path(args.output).mkdir(parents=True, exist_ok=True)
    args.func(args, system)


if __name__ == "__main__":
    main()
