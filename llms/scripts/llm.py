# /// script
# requires-python = ">=3.10"
# dependencies = ["httpx"]
# ///
# Local module required: llm_config.py must sit in the same directory as this
# file. PEP 723 above declares only PyPI deps; it cannot declare a local-file
# dependency, so the requirement is enforced by the guarded import below and
# documented here where anyone running `uv run llm.py` will see it. The two
# files travel together (see ADR-1): copying llm.py alone will fail loudly.
"""One CLI, six interaction patterns for sending prompts and files to LLM APIs.
Subcommands: single, append, batch, manifest, loop, interactive.
Run with: uv run llm.py <subcommand> ...

Requires llm_config.py alongside this file: it owns the provider table and the
shared call_llm (transport + the (text, truncated, usage) triple). This file
owns the interaction patterns, file IO, and usage telemetry, and wraps
llm_config.call_llm to add its truncation marker and JSONL usage log.
"""

import argparse
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
import httpx

try:
    import llm_config
except ImportError:
    sys.exit(
        "llm.py requires llm_config.py in the same directory; copy both files "
        "together (see ADR-1). Missing or unimportable: llm_config.py"
    )

try:
    import readline  # noqa: F401  -- arrow keys / history for input() REPLs
except ImportError:
    pass  # not available on some platforms; input() still works, just bare
# --- CONFIG ---
# llm.py-specific constants. The shared MAX_TOKENS and TIMEOUT_SECONDS live in
# llm_config (single source of truth); reference them as llm_config.MAX_TOKENS
# where needed (e.g. the --max-tokens argparse default).
PAYLOAD_WARN_TOKENS = 100_000  # C20: warn (not refuse) above this estimated input size
# One JSONL line per API call -- metadata only, never message content, so the
# log is safe to share when analyzing usage. Set LLM_NO_USAGE_LOG=1 to disable.
USAGE_LOG_PATH = Path.home() / ".llm_usage.jsonl"
DEFAULT_MANIFEST_PROMPT = "Analyze this file."


# Provider table and the shared call_llm live in llm_config.py (imported
# above). llm.py references them as llm_config.PROVIDERS / llm_config.call_llm.
# To add a provider, edit llm_config.py (see its field documentation); no
# change is needed here.


def parse_args() -> argparse.Namespace:
    """Build the subcommand CLI and parse arguments."""
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument(
        "--provider",
        default="anthropic",
        choices=sorted(llm_config.PROVIDERS),
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
    common.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Show message summary and estimated tokens without calling the API",
    )
    common.add_argument(
        "--max-tokens",
        type=int,
        default=llm_config.MAX_TOKENS,
        help=f"Response token limit (default: {llm_config.MAX_TOKENS})",
    )
    parser = argparse.ArgumentParser(
        description="Send prompts and files to LLM APIs: six interaction patterns."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser(
        "single", parents=[common], help="One prompt, one file, one call"
    )
    p.add_argument("prompt", help="Prompt text, sent before the file content")
    p.add_argument("filepath", help='Path to the file to attach ("-" reads stdin)')
    p.set_defaults(func=cmd_single)
    p = sub.add_parser(
        "append", parents=[common], help="One prompt, many files appended into one call"
    )
    p.add_argument("prompt", help="Prompt text, sent before the file blocks")
    p.add_argument(
        "filepath", nargs="*", help='Paths to files to attach ("-" reads stdin)'
    )
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
    """Wrap text in the toolkit's BEGIN/END delimiter convention.

    Known limitation: content that itself contains '--- BEGIN ' / '--- END '
    lines (e.g. transcripts produced by this tool, or this tool's own source)
    can mislead the model about where the file ends. Callers warn via
    warn_if_delimiter_collision; the delimiters are not escaped.
    """
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


def metadata_header(
    args: argparse.Namespace, system: str | None, prompt: str | None, generated: str
) -> str:
    """HTML-comment block recording what produced an output file.

    Without this, a directory of *_response_*.md files gives no way to
    reconstruct which prompt/model/provider made each one. Pure: the caller
    supplies the timestamp string. Prompt/system are collapsed to one line
    and truncated so they can't break the comment block.
    """
    model = args.model or llm_config.PROVIDERS[args.provider]["default_model"]
    lines = [
        "<!--",
        f"  generated: {generated}",
        f"  command: {args.command}",
        f"  provider: {args.provider}",
        f"  model: {model}",
        f"  max_tokens: {args.max_tokens}",
    ]
    if prompt is not None:
        lines.append(f"  prompt: {' '.join(prompt.split())[:200]}")
    if system is not None:
        lines.append(f"  system: {' '.join(system.split())[:200]}")
    lines.append("-->")
    return "\n".join(lines) + "\n\n"


def usage_record(
    generated: str,
    command: str | None,
    provider: str,
    model: str,
    max_tokens: int,
    payload_chars: int,
    latency_ms: int,
    outcome: str,
    input_tokens: int | None,
    output_tokens: int | None,
    pid: int,
) -> dict:
    """Build one usage-log record. Pure: the caller supplies timestamp,
    latency, and pid. Metadata only -- no message content ever goes in.

    outcome is one of: ok, truncated, http_<status>, transport, non_json,
    shape. pid groups calls from one process (e.g. a batch run) without
    threading a run id through every signature.
    """
    return {
        "generated": generated,
        "command": command,
        "provider": provider,
        "model": model,
        "max_tokens": max_tokens,
        "payload_chars": payload_chars,
        "estimated_input_tokens": estimate_tokens(payload_chars),
        "latency_ms": latency_ms,
        "outcome": outcome,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "pid": pid,
    }


def contains_delimiter(text: str) -> bool:
    """True if any line in text collides with the file-block delimiters."""
    return any(
        line.startswith(("--- BEGIN ", "--- END ")) for line in text.splitlines()
    )


def estimate_tokens(char_count: int) -> int:
    """Rough token estimate from a character count (~4 chars per token).

    Undercounts for code and non-English text; the report prefixes it with
    '~' accordingly. Shared by dry_run_report and (later) the payload guard.
    """
    return char_count // 4


def dry_run_report(system: str | None, messages: list[dict]) -> str:
    """Format a dry-run summary: message count, estimated tokens, content preview."""
    entries = [(m["role"], m["content"]) for m in messages]
    if system is not None:
        entries.insert(0, ("system", system))
    total_chars = sum(len(content) for _, content in entries)
    lines = [
        f"Messages: {len(messages)}"
        + (" (+ system prompt)" if system is not None else ""),
        f"Estimated tokens: ~{estimate_tokens(total_chars)}",
        f"Content preview ({total_chars} chars):",
    ]
    for role, content in entries:
        preview = content[:200]
        if len(content) > 200:
            preview += "..."
        lines.append(f"  [{role}] {preview}")
    return "\n".join(lines)


# --- IO ---
# call_with_logging (the logging observer), file reading, file writing.
# Collision avoidance lives in
# write_response (not TRANSFORM) because checking for an existing file
# is a filesystem read.
def append_usage(record: dict) -> None:
    """Append one JSONL record to the usage log; never interfere with the call.

    Telemetry is strictly sidecar: a full disk or unwritable home directory
    must not break (or noisily accompany) an otherwise-working API call, so
    failures are deliberately swallowed -- the one exception to the
    print-at-detection rule, justified because there is no action the user
    should take mid-call. LLM_NO_USAGE_LOG=1 disables logging entirely.
    """
    if os.environ.get("LLM_NO_USAGE_LOG"):
        return
    try:
        with open(USAGE_LOG_PATH, "a") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass


def record_call(
    command: str | None,
    provider_name: str,
    model: str,
    max_tokens: int,
    payload_chars: int,
    started: float,
    outcome: str,
    usage: dict | None = None,
) -> None:
    """Assemble and append a usage record for one call_llm exit path."""
    usage = usage or {}
    append_usage(
        usage_record(
            datetime.now().isoformat(timespec="seconds"),
            command,
            provider_name,
            model,
            max_tokens,
            payload_chars,
            int((time.monotonic() - started) * 1000),
            outcome,
            usage.get("input_tokens"),
            usage.get("output_tokens"),
            os.getpid(),
        )
    )


def apply_truncation_marker(text: str, truncated: bool, max_tokens: int) -> str:
    """Append the truncation marker to text when the response was cut short.

    ADR-12: a truncated response still carries useful partial output, so we keep
    the text and make the truncation visible in the written file. The matching
    stderr warning is emitted by call_with_logging at call time. Kept separate
    from logging because it transforms the returned text, not the usage record.
    """
    if not truncated:
        return text
    return text + f"\n\n> [warning: response truncated at max_tokens={max_tokens}]"


def call_with_logging(
    command: str | None,
    provider_name: str,
    model: str | None,
    system: str | None,
    messages: list[dict],
    max_tokens: int = None,
) -> str:
    """Call llm_config.call_llm, append exactly one usage record, return the text.

    This is the single logging locus for the toolkit (ADR-14): llm_config.call_llm
    is logging-free transport, and this observer turns each outcome -- success,
    truncated, transport failure, HTTP status, or response_error -- into one JSONL
    record via the pure usage_record builder and the swallowing append_usage writer.
    On success the truncation marker (ADR-12) is applied here before returning, so
    the marker and the truncated flag stay adjacent. Errors are logged and re-raised
    unchanged so each command keeps deciding exit-vs-skip. command labels which
    subcommand made the call; it never affects the request.
    """
    if max_tokens is None:
        max_tokens = llm_config.MAX_TOKENS
    # Recomputed here (not threaded from call_llm) because logging is decoupled
    # from transport: the observer derives what it needs from its own inputs.
    payload_chars = sum(len(m["content"]) for m in messages) + len(system or "")
    resolved_model = model or llm_config.PROVIDERS[provider_name]["default_model"]

    payload_tokens = estimate_tokens(payload_chars)
    if payload_tokens > PAYLOAD_WARN_TOKENS:
        # C20: oversized payloads otherwise fail server-side with an opaque
        # provider error (or quietly cost a lot). Warn, but let it through --
        # large-context models may handle it.
        print(
            f"Warning: payload is ~{payload_tokens} estimated tokens; "
            f"the provider may reject or truncate it.",
            file=sys.stderr,
        )

    started = time.monotonic()
    try:
        text, truncated, usage = llm_config.call_llm(
            provider_name, model, system, messages, max_tokens
        )
    except httpx.HTTPStatusError as exc:
        # Status error: llm_config already printed "HTTP <status>: ..." to stderr.
        record_call(
            command, provider_name, resolved_model, max_tokens, payload_chars,
            started, f"http_{exc.response.status_code}",
        )
        raise
    except httpx.HTTPError:
        # Transport failure (no network, DNS, timeout): already printed by llm_config.
        record_call(
            command, provider_name, resolved_model, max_tokens, payload_chars,
            started, "transport",
        )
        raise
    except llm_config.ResponseError:
        # Non-JSON or unexpected 2xx shape: llm_config already printed the raw
        # payload. ADR-14: the old non_json/shape split is gone because the
        # exception alone can't distinguish them; response_error is the honest
        # label for "a 2xx we could not turn into text".
        record_call(
            command, provider_name, resolved_model, max_tokens, payload_chars,
            started, "response_error",
        )
        raise

    if truncated:
        print(
            f"Warning: response truncated at max_tokens={max_tokens}; "
            f"re-run with a larger --max-tokens.",
            file=sys.stderr,
        )
    record_call(
        command, provider_name, resolved_model, max_tokens, payload_chars,
        started, "truncated" if truncated else "ok", usage,
    )
    return apply_truncation_marker(text, truncated, max_tokens)


def warn_if_delimiter_collision(filename: str, text: str) -> None:
    """Print a stderr warning when file content collides with the block delimiters."""
    if contains_delimiter(text):
        print(
            f"Warning: {filename} contains '--- BEGIN/END' delimiter lines; "
            f"the model may mis-read where the file ends.",
            file=sys.stderr,
        )


class FileReadError(Exception):
    """Raised by read_file after the error is printed to stderr.

    Mirrors call_llm's contract: formatting lives in one place here; the
    caller decides whether to exit (single-call commands) or skip and
    continue (batch-style commands).
    """


def read_file(path: Path, encoding: str | None = None) -> str:
    """Read a text file; print an error to stderr and raise FileReadError on failure.

    The conventional "-" reads stdin instead, making the tool pipeable:
    git diff | llm.py single "review this" -
    """
    try:
        if str(path) == "-":
            text = sys.stdin.read()
        else:
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
    input_name = "stdin" if args.filepath == "-" else input_path.name
    try:
        file_text = read_file(input_path)
    except FileReadError:
        sys.exit(1)  # read_file already printed the error to stderr
    warn_if_delimiter_collision(input_name, file_text)
    content = build_user_content(args.prompt, [(input_name, file_text)])
    messages = [{"role": "user", "content": content}]
    if args.dry_run:
        print(dry_run_report(system, messages))
        return
    try:
        response_text = call_with_logging(
            args.command,
            args.provider,
            args.model,
            system,
            messages,
            args.max_tokens,
        )
    except (httpx.HTTPError, llm_config.ResponseError):
        sys.exit(1)  # the failed call already printed the error to stderr
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out_stem = "stdin" if args.filepath == "-" else input_path.stem
    out = write_response(
        args.output,
        f"{out_stem}_response_{timestamp}.md",
        metadata_header(args, system, args.prompt, timestamp) + response_text,
    )
    print(f"Wrote {out}")


def cmd_append(args: argparse.Namespace, system: str | None) -> None:
    """Many files appended into one user message, one call, one response file."""
    input_paths = collect_paths(args.filepath, args.dir, args.ext)
    if not input_paths:
        print("No input files: pass file paths and/or --dir.", file=sys.stderr)
        sys.exit(1)
    try:
        files = [
            ("stdin" if str(p) == "-" else p.name, read_file(p)) for p in input_paths
        ]
    except FileReadError:
        sys.exit(
            1
        )  # read_file already printed the error; a partial append would mislead
    for name, text in files:
        warn_if_delimiter_collision(name, text)
    content = build_user_content(args.prompt, files)
    messages = [{"role": "user", "content": content}]
    if args.dry_run:
        print(dry_run_report(system, messages))
        return
    try:
        response_text = call_with_logging(
            args.command,
            args.provider,
            args.model,
            system,
            messages,
            args.max_tokens,
        )
    except (httpx.HTTPError, llm_config.ResponseError):
        sys.exit(1)  # the failed call already printed the error to stderr
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    out = write_response(
        args.output,
        f"appended_response_{timestamp}.md",
        metadata_header(args, system, args.prompt, timestamp) + response_text,
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
            file_text = read_file(input_path)
        except FileReadError:
            skipped += 1  # read_file already printed the error to stderr
            continue
        warn_if_delimiter_collision(input_path.name, file_text)
        content = build_user_content(prompt, [(input_path.name, file_text)])
        messages = [{"role": "user", "content": content}]
        if args.dry_run:
            print(f"[{index}/{total}] {input_path}")
            print(dry_run_report(system, messages))
            print()
            continue
        try:
            response_text = call_with_logging(
                args.command,
                args.provider,
                args.model,
                system,
                messages,
                args.max_tokens,
            )
        except httpx.HTTPStatusError as exc:
            # the failed call already printed the error to stderr.
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
        except (httpx.HTTPError, llm_config.ResponseError):
            skipped += 1  # the failed call already printed the error to stderr
            continue
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        out = write_response(
            args.output,
            f"{input_path.stem}_response_{timestamp}.md",
            metadata_header(args, system, prompt, timestamp) + response_text,
        )
        written += 1
        print(f"[{index}/{total}] {input_path} -> {out}")
    if not args.dry_run:
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
        warn_if_delimiter_collision(input_path.name, files[0][1])
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
            if args.dry_run:
                print(f"[iteration {iteration}/{total}]")
                print(dry_run_report(system, messages))
                print()
                # Placeholder keeps the loop's message shape visible for every
                # iteration; later token estimates understate a real run, where
                # previous_response would be a full model reply.
                previous_response = "(dry run -- no response)"
                responses.append(previous_response)
                continue
            try:
                response_text = call_with_logging(
                    args.command,
                    args.provider,
                    args.model,
                    system,
                    messages,
                    args.max_tokens,
                )
            except (httpx.HTTPError, llm_config.ResponseError):
                failed = True  # the failed call already printed the error to stderr
                break
            responses.append(response_text)
            previous_response = response_text
            refinement = None
            out = write_response(
                args.output,
                f"{name_prefix}_iter{iteration}_{timestamp}.md",
                metadata_header(args, system, args.initial_prompt, timestamp)
                + response_text,
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
    if responses and not args.dry_run:
        out = write_response(
            args.output,
            f"{name_prefix}_combined_{timestamp}.md",
            metadata_header(args, system, args.initial_prompt, timestamp)
            + combine_responses(responses),
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
        warn_if_delimiter_collision(input_path.name, files[0][1])
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
            if args.dry_run:
                print(dry_run_report(system, attempt))
                print()
                history = attempt + [{"role": "assistant", "content": "(dry run)"}]
                continue
            try:
                response_text = call_with_logging(
                    args.command,
                    args.provider,
                    args.model,
                    system,
                    attempt,
                    args.max_tokens,
                )
            except (httpx.HTTPError, llm_config.ResponseError):
                # the failed call already printed the error to stderr.
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
            args.output,
            f"interactive_{timestamp}.md",
            metadata_header(args, system, None, timestamp)
            + format_conversation(history),
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
