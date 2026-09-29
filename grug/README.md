# grug

An experimental replacement for the llm_playbook and the chat Preferences
text. It holds a short method (core.md), domain rules, memory notes and a
return contract as plain files, packs them with a task into one packet, and
records what comes back so the method can be judged by data.

The files are the system of record. grug.py is a replaceable view over them.

## Layout

    core.md          the constant method (the thing under test)
    contract.md      the return block every reply ends with
    domains/         code, math, writeup, research, review: pick per task
    memory/          dated lessons, one per file, promoted from runs
    tasks/           task files; a line "Mode: design" or "Mode: build"
    baseline/        the old Preferences, as the method of the baseline arm
    runs/            packets, replies, log.jsonl (gitignored: this is data)
    grug.py          pack, call, record, notes, promote, report
    test_smoke.py    end-to-end check against a throwaway copy of the store

Python 3.12+, standard library only. uv reads the version from the script
header: `uv run grug.py ...`. An alias helps:

    alias grug='uv run ~/personal_repos/explorations/grug/grug.py'

## The loop

    grug pack TASK --interface api|sandbox|chat [--domain code] [--evidence FILE ...] [--memory NOTE]
    # api:          grug call RUN
    # sandbox/chat: paste runs/RUN/packet.md, save the whole reply, grug record RUN REPLY_FILE
    grug record RUN --verdict pass|partial|fail --note "why"      # after you check the work
    grug pack TASK ... --repair RUN --evidence error.txt          # if it failed
    grug promote RUN --tags a,b                                   # if the lesson was earned
    grug notes KEYWORD                                            # find leads for the next pack
    grug report

The three interfaces get the same packet bytes; only the transport differs.
Evidence is inlined, so nothing needs uploading separately.

API: `call` posts to an OpenAI-compatible `/chat/completions`. Defaults to
OpenRouter; set `OPENROUTER_API_KEY` (or `GRUG_API_KEY`), and pick the model
with `pack --model` or `GRUG_MODEL`. `GRUG_BASE_URL` points it elsewhere, for
example a local server. To list free OpenRouter models (not run from the
build sandbox, which cannot reach openrouter.ai):

    curl -s https://openrouter.ai/api/v1/models | python3 -c "import json,sys; [print(m['id']) for m in json.load(sys.stdin)['data'] if m['id'].endswith(':free')]"

Preferences field (a fourth view, no code): paste the output of
`cat core.md contract.md domains/code.md` into the chat Preferences field to
run the method as the ambient system text instead of per packet.

## Experiment protocol

Decide before running, write it down (a memory note works), and do not change it
midway:

1. Arms. `--method core` (default), `--method baseline/preferences.md`, and
   `--method none` (bare: task, evidence and contract only).
2. Ambient. In browser chat the Preferences field is always loaded. Pass
   `--ambient` with what it held (none, preferences, grug) and change the
   field only between batches, never within one.
3. Sample size and archive rule. For example: 10 build tasks per arm on one
   model; archive grug if core does not beat bare on first-try passes, or
   costs more attempts than the baseline for no gain.
4. Verdicts are yours, after checking the work. The model's `status` is a
   self-report; the report shows where the two disagree.

Known confounds: every arm gets the contract, whose `verified:` field nudges
verification; the packet header tells every arm that fenced text is data.

## Where the old Preferences went

| Preferences section            | Now                                                      |
|--------------------------------|----------------------------------------------------------|
| Modes, plan-lock, implement    | core.md Mode (task line), domains/review.md (the pass)   |
| End of turn STATE / COMMANDS   | contract.md return block (one block for human and parser)|
| Options and recommendations    | core.md Choosing                                         |
| Code style, Naming             | domains/code.md Shape, Names and comments                |
| Scope                          | core.md Before work                                      |
| Verification and honesty       | core.md Evidence and honesty                             |
| Delivery                       | domains/code.md Change and delivery (compressed)         |
| Method prompts menu            | domains/ (from the thread; playbook bodies not yet read) |

core.md is 2181 bytes against 12532 for the Preferences text.

Not folded yet: the llm_playbook/prompts bodies (find-the-isomorph,
survey-the-space, commit-planning, clone-and-verify, runtime-verification,
and the drafts). Fold one only when a run shows it is missed.

## Not here, on purpose

Automatic retries or repair loops, tool use, test execution, repository
indexing, relevance ranking, embeddings, prompt caching, streaming. Add one
when a recorded run shows the simple packet failed for lack of it.

## Check

    uv run test_smoke.py
    # expect: last line "smoke: all checks passed"
