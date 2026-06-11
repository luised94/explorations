# CLAUDE.md - assistant reference for llm.py

Read this before editing. The owner has strong, explicit structural rules; violating them is worse than leaving a feature unbuilt.

## What this is

One file, `llm.py`, ~520 lines. Six subcommands (single, append, batch, manifest, loop, interactive) sending prompts + files to LLM APIs. Flat procedural Python: dicts, lists, functions, explicit control flow. One dependency: httpx, declared via PEP 723. Run with `uv run llm.py <subcommand>`. No SDKs, no async, no retries, no streaming, no config files beyond the in-file PROVIDERS dict. Keys come from env vars only.

## Section layout (do not reorder)

```
# --- CONFIG ---     constants, provider transform/extract fns, PROVIDERS dict, parse_args
# --- TRANSFORM ---  pure functions only: no open(), no print(), no httpx
# --- IO ---         call_llm, read_file, collect_paths, write_response
# --- COMMANDS ---   cmd_* + run_entries: the ONLY functions that sequence IO and transforms
# --- MAIN ---       system-prompt resolution, dispatch
```

Provider transform/extract functions sit in CONFIG (not TRANSFORM) because the dict references them at import time. Collision avoidance sits in IO (write_response) because `exists()` is a filesystem read. Both placements are deliberate; don't "fix" them.

## Hard rules

- Provider differences are DATA. Never write `if provider == "x"` in calling code. New provider = one PROVIDERS entry + its transform_messages / extract_response pair + an env var. All nine schema fields are mandatory; unused auth mechanisms are `lambda api_key: {}` no-ops, never absent fields with `.get()` fallbacks in call_llm.
- A function earns existence by 2+ callers, or by separating a pure transform from IO. Single-caller three-line helpers get inlined. Do not add wrappers, registries, plugins, or "extensibility" beyond PROVIDERS.
- IO and transformation never mix outside COMMANDS. A function reads/writes the world, or computes on arguments and returns - not both.
- Catch only: FileNotFoundError (via read_file), missing API key (named env var to stderr), httpx.HTTPStatusError (call_llm prints, caller decides exit-vs-skip). Everything else crashes with a traceback. Never catch broad Exception.
- Every function: one-line docstring + type hints. Plain stdout/stderr, no rich output.

## Conventions

- File context: `--- BEGIN name ---\n...\n--- END name ---` via file_block(); prompt text always precedes file blocks.
- Output names: `<stem>_response_<YYYYMMDD_HHMMSS>.md` (single/batch/manifest), `appended_response_<ts>.md`, `loop_iter<i>_<ts>.md` + `loop_combined_<ts>.md`, `interactive_<ts>.md`. write_response appends `_2`, `_3` on collision.
- Error semantics differ by design: batch/manifest skip failed entries and exit 1 at the end; loop stops on failure but writes the combined file; interactive discards the failed exchange and continues. Don't unify these.
- System prompt: generic `{"role": "system"}` message prepended via prepend_system; each provider's transform handles placement (Anthropic top-level field, OpenAI in-array, Gemini `[System] `-prefixed user turn).
- Exit words: `q` at loop's refinement prompt; `quit`/`exit` (or Ctrl-C/Ctrl-D) in interactive. These are different on purpose and have confused the owner's muscle memory once already - don't change one without the other and a README update.

## Owner's standing decisions (don't relitigate)

- Duplication beats coupling: no llm_helpers.py, ever. Split PROVIDERS + call_llm into llm_config.py only if the file passes ~700 lines.
- Manifest paths resolve from the working directory, not the manifest's location.
- Stem collisions within one second are handled by write_response suffixes; no fancier scheme.
- anthropic-version header stays 2023-06-01 until something needs newer features.
- gpt-4o uses `max_tokens`; o-series models would need `max_completion_tokens` - a one-line body_extras change, flagged but intentionally not made.

## Testing without spending money

Monkeypatch `llm.call_llm` (module-level name; commands resolve it at call time) with a fake returning canned text, then drive `llm.main()` with `sys.argv`. The pure TRANSFORM functions and provider transform/extract pairs test directly against canned API-shaped dicts.
