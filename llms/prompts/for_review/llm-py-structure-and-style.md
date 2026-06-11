# Conventions Observed in `llm.py` - Stated as Constraints

## 1. Section layout

The file is a single script in five banner sections, in fixed order: `CONFIG`, `TRANSFORM`, `IO`, `COMMANDS`, `MAIN`.

**CONFIG** holds constants (`MAX_TOKENS`, `TIMEOUT_SECONDS`, `PAYLOAD_WARN_TOKENS`, `DEFAULT_MANIFEST_PROMPT`), the provider transform/extract functions, the `PROVIDERS` dict, and `parse_args`. The provider functions live here by documented exception - the comment above them explains they're pure like TRANSFORM functions but belong to the provider table, which is built at import time and needs them defined first. *Constraint: anything that is a field of the provider table, or a constant, or argparse construction, goes in CONFIG - even if it's pure.*

**TRANSFORM** is governed by an explicit written rule in its banner comment: "All pure functions... No open(), no print(), no httpx." The section honors this strictly - when C12 needed manifest warnings, `parse_manifest` returned a `(entries, warnings)` tuple rather than printing; when C21 needed timestamps, `metadata_header` takes `generated` as a parameter rather than calling `datetime.now()`. *Constraint: a TRANSFORM function may not perform IO, print, make network calls, or read clocks. If a transform discovers something the user should hear about, it returns that information and the caller prints.*

**IO** holds `call_llm`, `read_file`, `collect_paths`, `write_response`, `warn_if_delimiter_collision`, and the two exception classes (`ResponseError`, `FileReadError`) adjacent to the functions that raise them. The banner comment justifies placement decisions ("Collision avoidance lives in write_response (not TRANSFORM) because checking for an existing file is a filesystem read"). *Constraint: a function goes in IO if it touches the filesystem, network, environment, or stderr - and exception classes live next to their raisers, not in CONFIG.*

**COMMANDS** holds one function per subcommand plus `run_entries`, and its banner states the boundary: "These are the only functions that mix IO and transforms." *Constraint: orchestration - the read  transform  call  write sequencing - happens only here. No helper outside COMMANDS may both transform and perform IO.*

**MAIN** is `main()` and the `__main__` guard only.

A meta-rule: when a placement looks like it breaks the taxonomy, the code carries a comment defending it. *Constraint: any boundary-bending placement must be accompanied by a justifying comment in the same style.*

## 2. Function extraction rule

The inferred rule: **logic is extracted when it is (a) pure and testable, (b) used from more than one site, or (c) a policy that must stay consistent across sites. Logic stays inline when it is single-use sequencing or trivial glue, even if repetitive.**

Extracted, with the reason visible: `file_block`/`build_user_content` (one delimiter convention, many callers), `run_entries` (real ~25-line dedup between `batch` and `manifest`), `estimate_tokens` (explicitly extracted so two consumers - `dry_run_report` and the C20 payload guard - share one heuristic), `write_response` (one collision policy), `metadata_header` (one header format, six call sites).

Deliberately inline, even though a typical developer might extract: the `timestamp = datetime.now().strftime(...)` line, repeated verbatim in five commands; the `try/except FileReadError: sys.exit(1)` guard, repeated at six sites; the `except (httpx.HTTPError, ResponseError): sys.exit(1)` pattern at four sites with the same comment pasted each time; the tuple-shaping at `run_entries`' two call sites; the dry-run guards, which are near-identical at five sites but were wired individually rather than hoisted into a decorator or helper. The historical record (`prepend_system` was deleted, not generalized, when it stopped earning its keep) confirms the direction: this codebase removes thin wrappers rather than accumulating them.

*Constraint: I will not extract a helper for repeated two-to-four-line sequencing patterns in COMMANDS. I will extract only pure multi-caller logic or single-point-of-truth policies, and I will prefer repeating a short idiom (with its conventional comment) over introducing indirection.*

## 3. Provider abstraction

The mechanism is a **single data table**, `PROVIDERS`, with a fixed nine-field schema documented in the comment block above it: `url_template`, `env_key`, `auth_header`, `auth_params`, `extra_headers`, `body_extras`, `transform_messages`, `extract_response`, `default_model`. Four fields are functions with documented signatures (e.g., `transform_messages: (system or None, messages list) -> body fragment`; `extract_response: response JSON -> (text, truncated bool)`). Degenerate mechanisms are filled with `lambda ...: {}` rather than omitted - every entry has every field. `call_llm` is the sole interpreter of the table; it composes the request generically and never inspects `provider_name`.

What would violate it: an `if provider_name == "gemini"` branch anywhere outside the table; a provider entry missing a field; provider-specific behavior leaking into TRANSFORM or COMMANDS; an extract function with a different return shape than its siblings; changing one transform's signature without changing all three and the schema comment. *Constraint: all provider variation is expressed as table data. If a new capability needs per-provider behavior, the table grows a field (with its comment-block documentation line and a uniform signature across all three entries) - `call_llm` and the commands stay provider-agnostic.*

## 4. Error handling pattern

The codebase has one error contract, stated in `call_llm`'s comment and replicated by both exception classes: **print the formatted error to stderr at the site that detects it; raise a marker exception; let the caller choose policy.** `FileReadError` and `ResponseError` docstrings both name this contract explicitly. The marker exceptions carry no message for display - the display already happened.

Policy is bimodal and lives in COMMANDS: single-call commands (`single`, `append`, `loop`, `interactive`, manifest-file read, `--system-file`) translate any marker exception into `sys.exit(1)`; the batch loop (`run_entries`) translates them into skip-and-count, with two carve-outs - 401/403 aborts immediately (every remaining entry would fail), and a positive `skipped` count still yields exit code 1 after the run completes. Each catch site carries the conventional comment `# call_llm already printed the error to stderr` (or the `read_file` equivalent) acknowledging that no message is needed there.

Channel discipline: **stdout** carries only product output - `Wrote {path}`, progress lines `[i/n]`, dry-run reports, REPL responses, the run summary. **stderr** carries everything diagnostic - errors, all warnings (empty files, delimiter collisions, truncation, payload size, manifest format), and the skip summary. `sys.exit(1)` for any failure; warnings never change the exit code on their own.

There is exactly one place where `call_llm` exits directly instead of raising - the missing API key - because that precondition failure is identical for every caller. *Constraint: new failure modes follow print-at-detection/raise-marker/policy-in-COMMANDS; new diagnostics go to stderr; I never print an error message at a catch site, only at the raise site.*

## 5. Naming conventions

Functions: `cmd_<subcommand>` for command entry points, matched 1:1 to subparser names and wired via `set_defaults(func=...)` with signature `(args, system)`. `build_*` for pure content assemblers returning strings (`build_user_content`, `build_iteration_content`). `format_*` for pure presentation of existing data (`format_conversation`). `parse_*` for text-to-structure (`parse_manifest`, `parse_args`). `<provider>_transform_messages` / `<provider>_extract_response` as a rigid pair per provider. Verb-first throughout (`collect_paths`, `write_response`, `estimate_tokens`, `warn_if_*` for stderr-warning helpers, `contains_*` for boolean predicates).

Variables: full words, no abbreviations - `response_text`, `input_path`, `previous_response`, `refinement`, `manifest_text`, `file_text`; loop counters `index`/`iteration` (never `i` except in display f-strings); `out` is the accepted short name for a written path. Constants: UPPER_SNAKE in CONFIG only. Exceptions: `<Noun>Error` with a contract-documenting docstring. Type hints on every signature using modern syntax (`str | None`, `list[dict]`, `tuple[str, bool]`); docstrings on every function, one-line imperative summaries, multi-paragraph only when documenting a contract or limitation. Comments referencing the change rationale carry their finding tag (`# C20: ...`, `# C24: ...`). *Constraint: I will follow each of these patterns, including tagging non-obvious changes with their commit identifier.*

## 6. What the code deliberately does NOT do

No classes for behavior - the only classes are two empty marker exceptions; provider polymorphism is a dict of functions, not an ABC or Protocol; there is no `LLMClient` object. No third-party dependencies beyond `httpx` - no `rich`, `click`, `pydantic`, `tenacity`; argparse, manual string formatting, and hand-rolled everything. No logging module - `print(..., file=sys.stderr)` exclusively. No retry/backoff machinery - a failed call fails once. No configuration files or dotenv - API keys come from the environment, period. No `dataclass`/`TypedDict`/`NamedTuple` for messages or entries - plain dicts with `role`/`content` keys and plain tuples, matching the wire format directly. No tests in the file and no test framework. No `async` - sequential blocking calls even in batch mode. No package structure, `setup.py`, or `__init__` - one file with inline script metadata for `uv run`. No truncation/streaming of responses - whole-response in memory. No mutation of shared state - transforms return new lists (`[new, *messages]`), and the one in-place idiom (`history = attempt + [...]`) rebinds rather than appends.

The why is consistent with the thread's verdict on the toolkit: it is a personal tool whose paramount value is that the whole program fits in one head in one read - every absence above trades a capability or a convention for direct legibility, and the file spends comments (the section banners, the provider-table manual, the contract docstrings) instead of structure to stay navigable. *Constraint: I will not introduce classes, dependencies, logging, retries, config files, typed containers, async, or file splits in any modification - and if a change seems to demand one of these, I will surface that tension to you rather than resolve it unilaterally.*

These twelve italicized constraints are the checklist I'll write against.
