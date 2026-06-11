# llm.py
Author: Fable 5, with Opus 4.6 feedback

A single-file CLI for sending prompts and files to LLM APIs (Anthropic, OpenAI, Gemini), with six interaction patterns as subcommands.

## Setup

Requires Python 3.10+ and [uv](https://docs.astral.sh/uv/). The httpx dependency is declared inline (PEP 723), so there is nothing to install - `uv run llm.py` handles it.

Set the API key for whichever provider you use (only that one is needed):

```sh
export ANTHROPIC_API_KEY=...   # default provider
export OPENAI_API_KEY=...      # --provider openai
export GEMINI_API_KEY=...      # --provider gemini
```

## Quick reference

```sh
# single: one prompt, one file
uv run llm.py single "Explain this code" app.py --output out/

# append: many files in one call (positional paths and/or --dir with --ext filter)
uv run llm.py append "Review these modules together" --dir src/ --ext .py --output out/

# batch: same prompt, one call per file, one response file each
uv run llm.py batch "Summarize this file" notes.md report.md --system "Be terse." --output out/

# manifest: TSV of filepath<TAB>prompt, one call per line
uv run llm.py manifest tasks.tsv --output out/

# loop: iterative refinement, each pass sees the previous response
uv run llm.py loop "Write a haiku about rivers" --iterations 3 --system "You are a poet." --output out/

# interactive: multi-turn REPL, optional file as first-message context
uv run llm.py interactive app.py --system-file persona.txt --output out/
```

All subcommands accept `--provider`, `--model`, `--output DIR`, and `--system TEXT` / `--system-file PATH` (mutually exclusive). Output filenames get `_2`, `_3`, ... suffixes instead of overwriting.

## Providers

| Provider    | Default model            | Env var           |
| ----------- | ------------------------ | ----------------- |
| `anthropic` | claude-sonnet-4-20250514 | ANTHROPIC_API_KEY |
| `openai`    | gpt-4o                   | OPENAI_API_KEY    |
| `gemini`    | gemini-2.0-flash         | GEMINI_API_KEY    |

## Adding a provider

Add three things to llm.py: an entry in the `PROVIDERS` dict (following the field list documented above it), a `transform_messages` / `extract_response` function pair referenced by that entry, and the environment variable holding its API key. `call_llm` reads everything else from the dict - no other code changes.

## Workflow recipes

```sh
# Code review: whole module set in one context, terse reviewer persona
uv run llm.py append "Review for bugs and unclear naming" --dir src/ --ext .py \
  --system "You are a strict code reviewer. Findings only, no praise." --output reviews/

# Document every script in a directory, one doc per file
uv run llm.py batch "Write a docstring-style summary of this file" --dir scripts/ --ext .py --output docs/

# Build a manifest from a git diff, then run it
git diff --name-only main | sed 's/$/\tSummarize what changed and why it might matter/' > changed.tsv
uv run llm.py manifest changed.tsv --output review/

# Draft, then steer each revision by hand
uv run llm.py loop "Draft a release announcement for v2.0" notes.md --iterations 4 --interactive --output drafts/

# Cheap model for bulk work, better model for the one that matters
uv run llm.py batch "One-line summary" --dir inbox/ --model claude-haiku-4-5-20251001 --output triage/
uv run llm.py single "Full analysis with recommendations" inbox/contract.md --output triage/

# Cross-provider comparison of the same question
for p in anthropic openai gemini; do
  uv run llm.py single "Explain this algorithm's complexity" sort.py --provider "$p" --output compare/
done
```

## Subcommand reference

**single** - Reads one file, sends one user message (prompt followed by the file wrapped in `--- BEGIN/END filename ---` delimiters), writes one response. Output: `<stem>_response_<timestamp>.md`.

**append** - Collects files from positional paths and/or `--dir` (filtered by `--ext`), deduplicates and sorts them, concatenates all of them after the prompt in a single message, makes one call. Output: `appended_response_<timestamp>.md`.

**batch** - Same file collection as append, but one call per file with the same prompt. Prints a `[i/N]` progress line per file. An HTTP failure skips that file and continues; if anything was skipped, exits 1 after the summary. Output per file: `<stem>_response_<timestamp>.md`.

**manifest** - Drives batch-style calls from a TSV file: each line is `filepath<TAB>prompt`. Lines starting with `#` and blank lines are skipped; a line with no tab gets the default prompt "Analyze this file." Paths resolve relative to the working directory. Same progress, skip, and exit behavior as batch. Output per entry: `<stem>_response_<timestamp>.md`.

**loop** - Runs `--iterations N` (default 3) fresh single-message calls. Iteration 1 sends the prompt plus the optional file; each later iteration sends the prompt, the previous response in delimiters, and a refinement instruction. With `--interactive`, each response is printed and you can type steering text for the next pass (empty continues, `q` quits, Ctrl-D quits). An HTTP failure stops the loop. Output: `loop_iter<i>_<timestamp>.md` per iteration plus `loop_combined_<timestamp>.md`.

**interactive** - Multi-turn REPL sending full history each call; an optional file is folded into the first message. `quit` or `exit` (or Ctrl-C / Ctrl-D) ends the session; a failed call prints a notice and lets you retry without polluting history. On exit, the transcript is written to `interactive_<timestamp>.md`.
