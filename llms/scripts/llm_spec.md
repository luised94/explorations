# llm.py - Maintenance Specification

This document is the contract for maintaining, modifying, or extending
`llm.py`. It describes what the code IS as of this writing. When the spec and
the code disagree, the code is wrong or this spec is stale - say so before
changing either.

## 1. Purpose and scope

`llm.py` is a personal CLI (run via `uv run llm.py`, sole PyPI dependency
`httpx`) for sending prompts and text files to LLM chat APIs (Anthropic,
OpenAI, Gemini) through six interaction patterns: `single` (one prompt + one
file), `append` (one prompt + many files in one call), `batch` (one prompt x
N files, one call each), `manifest` (TSV-driven per-file prompts), `loop`
(iterative refinement over fresh calls), and `interactive` (a REPL). It writes
responses as markdown files with metadata headers and appends a metadata-only
usage record per API call to `~/.llm_usage.jsonl`. It is NOT a library, an
agent, or a service: no tool calling, no streaming, no async, no retries, no
web search. Its paramount design value is that the whole program fits in one
head in one read; every convention below serves that.

The tool is two files that travel together: `llm.py` (interaction patterns,
file IO, usage telemetry) and `llm_config.py` (the provider table and the
shared `call_llm`). `llm_config.py` is a local module, not a PyPI dependency --
the dependency story is unchanged (`httpx` only). See ADR-1 for why the split
exists and the "Files" section below for the invariants that keep it safe.

### Files

- **`llm.py`** -- the CLI. Owns the six commands, file reading/writing, the
  JSONL usage log, and `call_with_logging` (the single logging locus that wraps
  the shared call). Run this; it carries the PEP 723 `uv` metadata.
- **`llm_config.py`** -- shared module. Owns `PROVIDERS`, the provider
  transform/extract functions, the empty marker `ResponseError`, and
  `call_llm` (transport + the `(text, truncated, usage)` triple; no logging,
  no truncation marker -- those are caller policy). Imported as
  `import llm_config`; referenced qualified (`llm_config.call_llm`,
  `llm_config.PROVIDERS`).

Invariants:
- **Travel together.** Both files must sit in the same directory. `llm.py`
  enforces this with a fail-loud guarded import that exits with a one-line
  message (not a traceback) if `llm_config.py` is missing. The requirement is
  also stated in a comment under `llm.py`'s PEP 723 block, since PEP 723 cannot
  declare a local-file dependency.
- **Import-safety.** Importing `llm_config` has no side effects: module top
  level is constants, pure functions, and the `PROVIDERS` dict only -- no
  argparse, IO, network, prints, or env reads. Environment is read inside
  `call_llm`. This is what lets `llm.py` (and any future second consumer)
  import it cleanly.

## 2. Data shapes

All structures are plain dicts, lists, and tuples - there are no data
classes anywhere.

### 2.1 Provider table entry (`PROVIDERS[key]`)

Nine fields, all required for every provider. Degenerate mechanisms are
filled with `lambda ...: {}`, never omitted.

| field | type | role |
|---|---|---|
| `url_template` | str | POST endpoint; may contain `{model}` (only Gemini uses it) |
| `env_key` | str | environment variable holding the API key |
| `auth_header` | `api_key -> dict` | auth headers; `{}` if auth is query-based |
| `auth_params` | `api_key -> dict` | auth query params; `{}` if header-based (exactly one of these two is non-empty) |
| `extra_headers` | dict (static) | provider-required headers, e.g. `anthropic-version` |
| `body_extras` | `(model, max_tokens) -> dict` | merged top-level into the body: model name and token limit wherever the provider wants them |
| `transform_messages` | `(system: str\|None, messages: list[dict]) -> dict` | body fragment holding the conversation |
| `extract_response` | `dict -> (text: str, truncated: bool, usage: dict)` | text errors must raise (KeyError/IndexError/TypeError); truncated and usage must NEVER raise - usage is read with `.get` chains and yields `{"input_tokens": int\|None, "output_tokens": int\|None}` |
| `default_model` | str | used when `--model` absent |

Example (the OpenAI entry):

```python
"openai": {
    "url_template": "https://api.openai.com/v1/chat/completions",
    "env_key": "OPENAI_API_KEY",
    "auth_header": lambda api_key: {"Authorization": f"Bearer {api_key}"},
    "auth_params": lambda api_key: {},
    "extra_headers": {},
    "body_extras": lambda model, max_tokens: {"model": model, "max_tokens": max_tokens},
    "transform_messages": openai_transform_messages,
    "extract_response": openai_extract_response,
    "default_model": "gpt-4o",
},
```

### 2.2 Generic messages list

What all commands build and `call_llm` consumes. Plain dicts, two keys, two
roles. The system prompt is NOT in this list - it travels as a separate
`call_llm` parameter and each provider transform places it (Anthropic:
top-level `system` field; OpenAI: prepended `{"role": "system", ...}`
message; Gemini: prepended `[System] ...` user part).

```python
[
    {"role": "user", "content": "Review this\n\n--- BEGIN a.py ---\n...\n--- END a.py ---"},
    {"role": "assistant", "content": "Looks fine except..."},
    {"role": "user", "content": "what about line 9"},
]
```

File content is embedded in user content via `file_block`:
`--- BEGIN {filename} ---\n{text}\n--- END {filename} ---`, joined to the
prompt with blank lines by `build_user_content`. Stdin input is labeled
`stdin`.

### 2.3 Command effects

Every command function takes `(args, system)` and returns `None`. Its
effects are:

| command | files written | stdout | exit code |
|---|---|---|---|
| `single` | `{stem}_response_{ts}.md` | `Wrote {path}` | 0; 1 on any failure |
| `append` | `appended_response_{ts}.md` | `Wrote {path}` | same |
| `batch`/`manifest` | one `{stem}_response_{ts}.md` per success | `[i/n] {in} -> {out}` per file, then `Processed N files, wrote M responses to {dir}` | 0 if no skips; 1 if any skipped (after processing all) or aborted on 401/403 |
| `loop` | `loop[_{stem}]_iter{i}_{ts}.md` per iteration + `loop[_{stem}]_combined_{ts}.md` | `Wrote {path}` per file; response text printed in `--interactive` | 1 if any call failed |
| `interactive` | `interactive_{ts}.md` transcript on exit | REPL responses, `Wrote {path}` | 0 |

All `.md` outputs begin with an HTML-comment metadata header (generated-at,
command, provider, resolved model, max_tokens, one-line prompt/system
truncated to 200 chars). `--dry-run` prints a report instead and writes no
files - except `interactive`, which still writes its transcript (containing
`(dry run)` placeholder turns). Every real API call additionally appends one
JSONL record (section 2.6).

Channel rule: stdout = product (paths, progress, reports, REPL text).
stderr = diagnostics (every error and warning). Exit 1 = something failed;
warnings alone never change the exit code.

### 2.4 Manifest format

TSV, read as `utf-8-sig` (BOM-tolerant). `parse_manifest` returns
`(entries, warnings)` - entries are `(filepath, prompt)` tuples.

```
# comment lines and blank lines are skipped
report.txt	Summarize the key findings
notes.md	            <- tab + empty prompt -> default "Analyze this file."
plain.txt               <- no tab -> default prompt
data file.txt observe   <- no tab but spaces -> WARNING (likely meant a tab), whole line treated as filepath
```

Relative filepaths resolve against the manifest's own directory, not the
CWD. Absolute paths pass through.

### 2.5 Conversation history (interactive) / loop state

Interactive history is the generic messages list (section 2.2), rebound (never
mutated in place) each turn: `history = attempt + [{"role": "assistant",
"content": response_text}]`. The file block rides only in the first user
message. Loop mode keeps no message history - each iteration is a fresh
single-message call whose content embeds the previous response as
`file_block("previous_response", ...)` plus, in order: prompt, previous
response, optional user refinement, then the boilerplate "Iteration i of N.
Refine your previous response."

### 2.6 Usage log record

One JSON line per API call, metadata only (never content), to
`USAGE_LOG_PATH` (`~/.llm_usage.jsonl`). `LLM_NO_USAGE_LOG=1` disables.

```json
{"generated": "2026-06-11T07:02:13", "command": "batch", "provider": "anthropic",
 "model": "claude-sonnet-4-20250514", "max_tokens": 4096, "payload_chars": 18243,
 "estimated_input_tokens": 4560, "latency_ms": 2310, "outcome": "ok",
 "input_tokens": 4471, "output_tokens": 512, "pid": 41873}
```

`outcome` ? `ok | truncated | http_<status> | transport | non_json | shape`.
`pid` groups calls from one process (a batch run) in lieu of a run id.

## 3. Coding guidelines

### Section layout

Fixed order: `CONFIG`, `TRANSFORM`, `IO`, `COMMANDS`, `MAIN`, marked by
`# --- NAME ---` banners.

- **CONFIG**: constants (UPPER_SNAKE), provider transform/extract functions,
  the `PROVIDERS` dict, `parse_args`. The provider functions live here (not
  TRANSFORM) by documented exception: the table is built at import time.
- **TRANSFORM**: pure functions only. Forbidden: `open()`, `print()`,
  `httpx`, clocks, environment. If a transform must surface a warning,
  return it (see `parse_manifest`); if it needs a timestamp, take it as a
  parameter (see `metadata_header`, `usage_record`).
- **IO**: anything touching filesystem, network, environment, or stderr.
  Marker exception classes live adjacent to the functions that raise them.
- **COMMANDS**: one `cmd_*` per subcommand plus `run_entries`. The ONLY
  place that mixes IO and transforms (the read -> transform -> call -> write
  sequencing).
- **MAIN**: `main()` and the `__main__` guard.

Any placement that bends the taxonomy must carry a justifying comment in
the existing style.

### Function extraction rule

Extract when the logic is (a) pure and independently testable, (b) called
from >=2 sites, or (c) a policy that must stay identical everywhere
(`write_response`, `estimate_tokens`, `metadata_header`). Leave inline:
single-use sequencing, trivial glue, and short idioms even when repeated -
the timestamp line, the `except FileReadError: sys.exit(1)` guard, and the
dry-run guards are deliberately pasted at each site with their conventional
comment. There is no line-count threshold; the historical direction is that
thin wrappers get deleted (`prepend_system` was removed when it stopped
paying), not accumulated. Never introduce a single-caller wrapper.

### Error handling

One contract, stated in `call_llm`'s comments and the `FileReadError` /
`ResponseError` docstrings: **print the formatted error to stderr at the
detection site, raise a marker exception, let the caller pick policy.**
Catch sites never print messages - they carry the comment
`# call_llm/read_file already printed the error to stderr`.

Policy is bimodal, in COMMANDS only: single-call commands translate any
marker (`FileReadError`, `ResponseError`, `httpx.HTTPError`) into
`sys.exit(1)`; `run_entries` translates them into skip-and-count, except
401/403 which aborts immediately (every remaining entry would fail
identically - note 429 deliberately does NOT abort). A positive skip count
still exits 1 after the run. Exceptions caught are always the narrowest
class that covers the surface (`httpx.HTTPError`, never bare `Exception`).
Two sanctioned deviations, both comment-documented: `call_llm` exits
directly on a missing API key (identical precondition for every caller),
and `append_usage` silently swallows `OSError` (telemetry must never break
a working call).

### Naming

`cmd_<subcommand>` (signature `(args, system) -> None`, wired via
`set_defaults(func=...)`); `build_*` pure content assemblers; `format_*`
pure presentation; `parse_*` text -> structure; `<provider>_transform_messages`
/ `<provider>_extract_response` as a rigid pair; `warn_if_*` for
stderr-warning helpers; `contains_*` for predicates; verbs first elsewhere.
Variables are full words (`response_text`, `input_path`,
`previous_response`); `out` is the accepted short name for a written path;
`index`/`iteration`, never `i`. Modern type hints (`str | None`,
`tuple[str, bool, dict]`) and a docstring on every function. Non-obvious
changes carry their change-id tag in a comment (`# C20: ...`); continue the
scheme with a session prefix if needed.

### Deliberate absences (prohibitions)

- **No classes for behavior** - only empty marker exceptions. No
  `LLMClient`, no ABC/Protocol. (Polymorphism = the provider table.)
- **No per-provider branching** - never `if provider_name == "gemini"`
  outside the table. Variation is table data; new capability = new table
  field documented in the schema comment, uniform across all entries.
- **No dependencies beyond httpx.** No click/rich/pydantic/tenacity.
- **No logging module** - `print(..., file=sys.stderr)` only.
- **No retry/backoff** - a failed call fails once. (One narrow 429-retry
  exception has been discussed but NOT approved; do not add it
  unilaterally.)
- **No async/parallelism** - sequential batch is a feature under rate
  limits.
- **No streaming** - whole responses in memory.
- **No config files / dotenv** - environment variables only.
- **No typed containers** (dataclass/TypedDict/NamedTuple) - plain dicts
  matching the wire format.
- **No broad `except Exception`** anywhere.
- **No mutation of shared state** - transforms return new lists
  (`[new, *messages]`); history is rebound, never appended in place. Only
  IO and COMMANDS functions may have side effects; TRANSFORM and the
  provider transform/extract functions must be pure.
- **No self-modification** - tooling that helps add providers outputs
  editing instructions for a human, never a patched file.

### Output convention

Files go to `--output` (default `.`, created via
`mkdir(parents=True, exist_ok=True)` in `main` BEFORE any paid call).
Names: `{stem}_response_{YYYYmmdd_HHMMSS}.md` and variants per section 2.3.
Collision avoidance is atomic: `write_response` loops `open(path, "x")`,
appending `_2, _3, ...` on `FileExistsError`. Every write is confirmed on
stdout as `Wrote {path}`. All diagnostics - including the six warning types
(empty file, delimiter collision, truncation, payload size, manifest
format, skip summary) - go to stderr.

## 4. Architecture decision records

**ADR-1: Single file, later split to two.**
Context: six interaction patterns could be six scripts or a package.
Original decision: one `llm.py` with subcommands and inline `uv` script
metadata. Alternatives: a package (rejected: install/import ceremony for a
personal tool); separate scripts (rejected: would duplicate the provider table
and error contract six times). Consequences: the file is long and the banner
sections substitute for module boundaries.

Revised: the provider table and `call_llm` now live in `llm_config.py`, which
`llm.py` imports. The trigger was a second consumer -- salvaged workbench logic
and any future tool wanting the same provider table -- which is the same
two-consumers threshold the function-extraction rule names; below it, a second
file is pure cost. The single-file value (ships by copying) becomes "ships by
copying two files that travel together", guarded so the invariant cannot break
silently: a fail-loud import in `llm.py`, a PEP 723-adjacent comment, and the
"Files" section in Section 1. `llm_config.py` is a local module, not a new
dependency -- `httpx` is still the only PyPI dependency. The "fits in one head"
value is preserved: each file is independently readable, and the seam between
them (a qualified `import llm_config`) is narrow and one-directional.

**ADR-2: Provider differences as a data table with function-valued fields.**
Context: three providers differ in URL, auth, body shape, response shape.
Decision: `PROVIDERS` dict, nine uniform fields, `call_llm` as the sole
generic interpreter. Alternatives: explicit `if provider == X` branches in
`call_llm` (rejected after explicit review - comparable line count and
arguably more readable per-provider, but the most likely future change is
"add a provider," which the table makes a fill-in-the-fields exercise; this
was a judged trade-off, not an obvious win). Consequences: a comment block
serves as the table's user manual and MUST be kept in sync; degenerate
fields are `lambda: {}`; nothing outside the table may inspect provider
identity.

**ADR-3: Errors print-at-detection then raise marker exceptions.**
Context: single-call commands should die on failure; batch should skip and
continue; both need identical formatting.
Decision: `call_llm` / `read_file` print to stderr at the detection site
and raise (`httpx` errors re-raised; `FileReadError` / `ResponseError` as
empty markers); COMMANDS choose exit-vs-skip. Alternatives: returning
`(ok, value, error)` tuples (rejected: infects every signature); letting
callers format errors (rejected: N copies of formatting drift apart);
exceptions carrying display messages (rejected: invites double-printing).
Consequences: catch sites are message-free with a conventional comment;
adding a failure mode means one print + one raise + a policy line per
caller class.

**ADR-4: `read_file` extracted, and its contract reversed once.**
Context: originally a thin wrapper that printed and `sys.exit(1)` on
missing files - which silently gave batch runs die-on-first-bad-file
semantics that contradicted `run_entries`' skip-counting code.
Decision: keep the extraction (it owns a real policy: full failure surface
- missing, directory, binary/encoding, permissions - plus empty-file
warning and the stdin `-` case), but change it to raise `FileReadError` per
ADR-3.
Alternatives: inlining `path.read_text()` (rejected: six sites would each
need four except branches); keeping exit-on-error (rejected: poisons batch
semantics). Consequences: it is the canonical example that "wrapper vs.
policy-holder" is judged by content, not call count - it earned its
existence only when it owned the whole error surface.

**ADR-5: `run_entries` shared by batch and manifest.**
Context: both run "one call per (file, prompt) entry" with identical
progress, skip, and summary logic (~25 lines).
Decision: extract; callers shape their inputs into `(Path, prompt)` tuples.
Alternatives: two explicit loops (rejected: real divergence risk in skip
semantics - exactly the bug class ADR-4 fixed). Consequences: both call
sites pay a small tuple-shaping tax; this was acknowledged as a close call
and kept because the compression happened after two concrete uses existed.

**ADR-6: Collision avoidance lives in IO (`write_response`).**
Context: where does "find a free filename" belong?
Decision: in `write_response`, because checking existence is a filesystem
read - TRANSFORM may not touch the disk. Later hardened from
`exists()`-then-write to an atomic `open(path, "x")` retry loop
(TOCTOU-safe between concurrent runs). Alternatives: pure name-candidate
generator + IO prober (rejected: two functions for one policy).
Consequences: filename policy and atomicity live in one function;
timestamps in names are belt-and-braces, the `_2` suffix is the real
guarantee.

**ADR-7: `body_extras` as a table field.**
Context: Anthropic/OpenAI put `model` and `max_tokens` in the body; Gemini
puts the model in the URL and the limit in `generationConfig`.
Decision: a `(model, max_tokens) -> dict` field merged top-level into the
body, paired with the optional `{model}` URL placeholder. Alternatives:
normalizing all providers to one body shape (impossible - the APIs
genuinely differ); special-casing Gemini in `call_llm` (violates ADR-2).
Consequences: honest admission that the providers are differently shaped;
the field signature grew once (gaining `max_tokens`) and any further growth
must change all three entries and the schema comment together.

**ADR-8: Gemini auth - query parameter, then reversed to header.**
Context: Gemini documents `?key=` auth; keys in URLs leak via proxy logs
and any future URL-printing error path.
Decision: originally `auth_params` (query); deliberately reversed to the
`x-goog-api-key` header during hardening. Alternatives: embedding the key
in `url_template` (rejected: format-string injection of secrets, and it
breaks the one-URL-template-per-provider shape). Consequences:
`auth_params` is now `{}` for all three providers but the field REMAINS in
the schema - the mechanism is kept for future providers that only support
query auth.

**ADR-9: `--dry-run` shows estimated tokens (chars / 4), not exact counts.**
Context: exact counting needs a tokenizer dependency per provider.
Decision: a shared `estimate_tokens` heuristic, displayed with `~`,
admitted to undercount code and non-English text. The divisor 4 is
arbitrary. Alternatives: tiktoken et al. (rejected: violates the
single-dependency rule for a preview feature). Consequences: estimates are
directional only; the usage log records BOTH estimate and provider-reported
actuals so the constant can eventually be fitted from real data. Related
sub-decisions: a dry run writes no files and exits 1 if it found unreadable
inputs (it doubles as a validator); `loop --dry-run` threads a placeholder
previous-response so every iteration's message shape is visible (its later
token estimates are knowingly meaningless); `interactive --dry-run` still
writes its transcript - the transcript records what the user typed, unlike
loop's would-be file of placeholders.

**ADR-10: `q` as an exit word in interactive.**
Context: `loop --interactive`'s refinement prompt already used `q`; the
REPL accepted only `quit`/`exit`.
Decision: add `q` to the REPL's exit words. Alternatives: none seriously -
this is convergence, not design. Consequences: the two interactive surfaces
share an exit vocabulary; the REPL additionally treats Ctrl-C/Ctrl-D as
exits and `loop` was later taught to write its combined file on Ctrl-C to
match.

**ADR-11: System prompt as an explicit `call_llm` parameter.**
Context: originally the system prompt was prepended into the generic
messages list (`prepend_system`) only for Anthropic's transform to split it
back out - a thread-in-then-fish-out round trip flagged independently by
both review lenses.
Decision: `call_llm(provider, model, system, messages, ...)`; each
transform receives `system` and places it natively; `prepend_system`
deleted. Alternatives: keeping the generic-list convention (rejected: the
"generic" format was really OpenAI's format wearing a disguise).
Consequences: `"system"` is not a valid role in the generic messages list;
any new provider transform must handle `system: str | None` explicitly.

**ADR-12: Truncation surfaced from the `truncated` bool; marker applied by the caller.**
Context: silent truncation at the old hard 4096 limit was judged the #1
long-term pain point.
Decision: extractors return a `truncated` bool from each provider's own
stop-reason signal as part of the `(text, truncated, usage)` triple;
`--max-tokens` exposed. The stderr warning and the appended
`> [warning: response truncated at max_tokens=N]` marker are emitted by
`llm.py`'s `call_with_logging` (one site), not by the shared `call_llm`:
appending the marker transforms the returned text, which is caller policy, so
the shared transport stays free of it (see ADR-16). `apply_truncation_marker`
holds the append logic so it is stated once. Alternatives: per-command handling
(rejected: six sites); refusing to write truncated output (rejected: partial
output is still useful); keeping the marker inside the shared `call_llm`
(rejected: it would force one text-mutation policy on every consumer). 
Consequences: extractor return shape is a tuple and all three must change in
lockstep; `truncated` carries only "was it cut at max_tokens", not the specific
stop reason (a tool needing the raw reason must read it itself).

**ADR-13: Delimiter collision - documented limitation, not a sentinel
protocol.**
Context: content containing `--- BEGIN/END` lines (e.g. transcripts this
tool produced) can mislead the model about file boundaries.
Decision: keep fixed delimiters; document the limitation on `file_block`;
warn at input time via a line-anchored `contains_delimiter` check at all
five file-input paths. Alternatives: per-run random sentinels (rejected as
architecture-changing for a personal tool: breaks transcript comparability
and requires telling the model the delimiter each run). Consequences:
line-anchored detection deliberately ignores mid-line occurrences (source
code mentioning the strings does not warn; an embedded transcript does);
the model can still be confused by adversarial content - accepted.

**ADR-14: Usage telemetry is a swallowing sidecar keyed by pid.**
Context: development priorities should come from real usage, but telemetry
must never degrade the tool.
Decision: one metadata-only JSONL line per API call from every exit path; pure
`usage_record` + IO `append_usage` that silently swallows `OSError`;
`LLM_NO_USAGE_LOG=1` opt-out; `pid` stands in for a run id; `command` is
threaded as an explicit parameter rather than a module global. The single
logging locus is `llm.py`'s `call_with_logging`, which wraps the shared
`call_llm` (transport stays logging-free, see ADR-16) and classifies each
outcome -- `ok`, `truncated`, `http_<status>`, `transport`, `response_error` --
from what the call returned or raised. Alternatives: logging inside `call_llm`
(rejected: welds telemetry to transport and forces it on every consumer); a
run-id threaded through every signature (rejected: heavy for grouping pid
approximates); a global context (rejected: no shared mutable state); logging
message content (rejected: the log must be shareable).
Consequences: the ONE sanctioned silent-failure path in the codebase; two log
lines can share a pid across different days (disambiguate with timestamps); and
the former `non_json` and `shape` outcomes are merged into `response_error`,
because the shared `call_llm` raises one `ResponseError` for both and the
observer cannot (and need not) distinguish them -- both already print full
detail to stderr at the raise site.

**ADR-15: Provider extension via a two-stage prompt pack, outside the
tool.**
Context: adding providers requires current API knowledge the maintainer may
lack.
Decision: stage 1 (research prompt -> strict JSON against the table schema,
with mandatory confidence notes), stage 2 (fill prompt + skeleton -> numbered
editing instructions with insertion anchors and a five-step verification
that proves the truncation and usage mappings specifically). The tool never
modifies itself; instructions, not patched files. Consequences: the prompts
duplicate the schema and MUST be updated when the table schema changes
(they already encode the `(text, truncated, usage)` triple).

**Minor recorded decisions:** manifest paths resolve against the manifest's
directory; manifests (only) are read `utf-8-sig`; `--ext py` is normalized
to `.py` (bare `*py` would match `copy`); path dedup keys on `resolve()`
but displays the original spelling; batch aborts on 401/403 but NOT 429;
payload-size guard warns (at an arbitrary 100k estimated tokens) rather
than refusing; output filenames in `loop` include the input stem; metadata
headers are HTML comments (invisible in rendered markdown) with prompts
newline-collapsed and truncated to an arbitrary 200 chars; `interactive`
preserves a failed prompt for empty-Enter retry; stdin via `-` is labeled
`stdin` only in `single` and `append` (the REPL owns stdin in
`interactive`).

**ADR-16: Provider machinery extracted to `llm_config`; transport split from caller policy.**
Context: the provider table, the provider transform/extract functions, and
`call_llm` were inline in `llm.py`. A second consumer wanted the same provider
table, and the original `call_llm` welded three concerns together -- transport,
usage logging, and the truncation-marker text mutation.
Decision: move `PROVIDERS`, the transforms/extractors, `ResponseError`, and
`call_llm` into `llm_config.py` (ADR-1 revised). The shared `call_llm` owns only
transport and turning the response into the `(text, truncated, usage)` triple,
including the shape guard; it does no logging and appends no marker. `llm.py`
wraps it in `call_with_logging`, which owns the usage log (ADR-14) and the
truncation marker (ADR-12). Alternatives: keeping `call_llm` monolithic and
having `llm.py` call it directly (rejected: a second consumer would inherit
`llm.py`'s telemetry, or telemetry would scatter to six sites); a context
manager around each call (rejected: hides the success/error classification in
`__exit__`); re-extracting usage in each caller (rejected: defeats the shared
call). Consequences: `call_llm`'s return widened from `str` to the triple so a
caller can meter cost/truncation; callers unpack `text, _, _` when they want
only text; the qualified `import llm_config` makes the boundary visible at every
call site; and the pure `usage_record` builder + swallowing `append_usage`
writer are unchanged -- only the calls to them moved out of transport.

## 5. Extension guide

### Adding a provider

Provider machinery now lives in `llm_config.py` (ADR-16). All edits in this
recipe are to `llm_config.py`; `llm.py` does not change.

1. Run the two-stage prompt pack (`provider_research_prompt.md` -> 
   `provider_fill_prompt.md` + `provider_skeleton.py`) or fill the skeleton
   by hand from the API docs.
2. Write `<key>_transform_messages(system, messages) -> dict` and
   `<key>_extract_response(data) -> (text, truncated, usage)` in
   `llm_config.py` after `gemini_extract_response`. Honor the contract: text errors raise;
   truncated/usage never raise.
3. Add the nine-field entry to `PROVIDERS` (in `llm_config.py`) after the
   gemini entry. Exactly
   one of `auth_header`/`auth_params` is non-empty; include `"model": model`
   in `body_extras` only if the model is NOT in the URL.
4. Export `<KEY>_API_KEY`.
5. Verify in order, exercising both files together: `py_compile llm.py
   llm_config.py`; `python -c "import llm_config"` (import-safety); a
   `--dry-run` call through `llm.py`; one cheap real call; a `--max-tokens 16`
   call whose output file must end with the truncation marker; `tail -1
   ~/.llm_usage.jsonl` must show integer token counts and outcome `truncated`.

### Adding a subcommand

1. Write `cmd_<name>(args, system) -> None` in COMMANDS, sequencing
   read -> transform -> call -> write. Reuse `read_file` (+ per-site
   `except (httpx.HTTPError, llm_config.ResponseError): sys.exit(1)` or
   skip), `build_user_content`, then
   `call_with_logging(args.command, provider, model, system, messages,
   args.max_tokens)` (the logging wrapper around `llm_config.call_llm`),
   `metadata_header`, `write_response`.
2. Register in `parse_args`: `sub.add_parser("<name>", parents=[common],
   help=...)`, positionals, `set_defaults(func=cmd_<name>)`.
3. Honor the inherited flags: a `--dry-run` guard after messages are built
   and before the call; output files start with `metadata_header`.
4. Pure assembly logic the command needs goes in TRANSFORM; anything
   touching disk/network goes in IO; the command itself is the only mixer.

### Adding a shared flag

1. `common.add_argument(...)` in `parse_args` - every subcommand inherits.
2. If it needs one-time resolution or validation, do it in `main()` before
   dispatch (pattern: the `--system`/`--system-file` mutual exclusion uses
   `is not None`, not truthiness; the resolved value is passed as a second
   positional arg to commands).
3. Per-call values thread as explicit parameters with defaults through
   `call_with_logging` (and on to `llm_config.call_llm`) -- pattern:
   `max_tokens`, `command` -- never module globals.
4. Update section 2.3 and this guide if the flag changes command effects.

## 6. Known limitations and debts

Identified and deliberately not fixed; do not "fix" these in passing
without a decision.

- **`anthropic-version: 2023-06-01`** is a pinned, aging API version
  string. It works; updating it is a one-line change that should be
  verified against a real call, not done blind.
- **OpenAI `max_tokens` vs `max_completion_tokens`**: newer OpenAI models
  reject the legacy `max_tokens` body field in favor of
  `max_completion_tokens`. The table uses `max_tokens`, which works for the
  pinned default (`gpt-4o`) but will 400 on some newer model strings. Fix
  is one `body_extras` lambda; deferred until it actually bites, and the
  C15 shape/HTTP guards will make the failure loud and attributable.
- **Default model strings age.** All three defaults are snapshots; expect
  to bump them. Same one-line treatment.
- **Token estimation is chars / 4** (ADR-9): directional only, undercounts
  code. The usage log accumulates the data to fit a better constant; nobody
  has done the fitting yet.
- **No retry logic** - a 429 mid-batch skips that entry. The narrow
  retry-once-on-429 exception was proposed and explicitly parked pending
  usage data showing it matters.
- **Stem collisions in batch**: `a/report.txt` and `b/report.txt` in one
  batch both want `report_response_{ts}.md`; the atomic `_2` suffix
  prevents data loss but the names don't say which is which. The metadata
  header's prompt line is the disambiguator. Accepted.
- **TOCTOU in collision avoidance is FIXED** (atomic `open(path, "x")`,
  ADR-6) - listed here because earlier analyses flagged it; do not re-flag.
- **Binary files are handled** (clean `FileReadError`, ADR-4) but not
  *supported* - there is no PDF/image extraction and none is planned; this
  is a text tool.
- **Delimiter strings in user content** (ADR-13): warned about, not
  prevented. Line-anchored detection misses mid-line occurrences by design.
- **Loop dry-run token estimates** for iterations >=2 are knowingly
  meaningless (placeholder previous-response, ADR-9).
- **`pid` as run grouping** can collide across days (ADR-14); group on
  `(pid, generated-date)` when analyzing.
- **`interactive` cannot attach files after the first turn**, and a
  dry-run REPL session writes a transcript of placeholder turns (ADR-9).
- **Empty `--system ""`** is accepted and sent as an empty system prompt
  (the mutual-exclusion check uses `is not None` deliberately).
- **Payload warning threshold (100k tokens) and preview truncation
  (200 chars) are arbitrary** round numbers, candidates for tuning from
  usage data.
- **No live-API test has ever run in development** - all verification used
  a stubbed transport down to request-assembly level. The first action in
  any session that touches the wire format is one cheap real call per
  affected provider.
- **Parked feature decisions requiring explicit approval**: server-side web
  search (design exists: a tenth `search_tool` table field), client-side
  tool calling (fable-scale, changes the tool's identity), the usage
  dashboard (waiting on accumulated log data), 429 retry (above).
- **Sibling files in the toolkit, not part of llm.py's contract.**
  `llm_config.py` IS part of the contract (ADR-1, ADR-16) and travels with
  `llm.py`. The others are independent and llm.py does not depend on them:
  `terminal_output.py` is a presentation library used by other tools (three
  formatter functions -- `format_labeled_separator`, `format_metadata_inline`,
  `format_tree` -- were added when a consumer referenced them but they were
  missing from the module; that reconciliation is recorded here so the gap is
  not re-introduced). `workbench.py` was a standalone SDK-based REPL, now
  retired rather than ported; its durable parts (the SQLite `calls` schema and
  its additive-migration pattern, the per-model cost table, and the pure
  cost/estimate transforms) were salvaged into `workbench_salvage.py` as a
  reference. Salvage over port was a deliberate call: the loop wiring would have
  needed reconciling against `llm_config.call_llm`'s truncated-bool (which drops
  the raw stop_reason workbench logged), and the program was not going to be
  used. See `workbench_salvage.py` for the harvested material and the recorded
  stop_reason seam.
