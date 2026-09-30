# bend-playground

A closed experiment in getting AI models to write correct Bend 2 programs.
Five models wrote the same small program (an ASCII Mandelbrot and Sierpinski
renderer, plus laws and proofs over it) from the Bend guide and Base alone. I
compiled their code, pasted the errors back, and measured what compiling
fixes and what it doesn't.

**Status:** closed 2026-09-30. Bend stays an occasional study-session topic.
The decision and its reasons are in `FINDINGS.md` section 0.

## Files

| File | What it is |
|---|---|
| `FINDINGS.md` | Start here: lessons that transfer beyond Bend, Bend knowledge, open questions, what to read next, study exercises |
| `report.md` | The full write-up of the five-model experiment (i00), with an addendum on later sessions and Bend 2.0.32 |
| `rules-card.md` | Bend rules, each graded VERIFIED / STATED / UNVERIFIED / FALSE, with an error decoder; built into every generated prompt |
| `prompts.md` | Every message a model receives: task, confirm, enumerate, sweep, bare, audit, diagnose, notes-preamble |
| `bendlab.py` | The tool: builds the prompt from the installed compiler; runs, measures and records model submissions |
| `history.tsv` | Every attempt: i00 and later sessions backfilled at the top, new runs appended |
| `upstream-issue.md` | Draft issue: nine guide passages that led models into errors (checklist inside; not filed) |
| `upstream-discussion.md` | Draft discussion post: models choose laws that pass rather than laws that constrain (not posted) |
| `playground.bend`, `LAWS.bend`, `PROOF.bend` | Reference solution: claude-opus-5's one-shot pass, unmodified. Verified on bend 2.0.16 only |
| `bend-installation.md` | Your installation notes |

The original experiment (`model_tests/`, all five models' files and
transcripts, the round-by-round results and the v1 shell harness) is in git
history at tag `bend-playground-i00`: `git checkout bend-playground-i00 -- model_tests`.

## Resuming in a study session

Needs `uv` and `bend`. `bendlab.py` uses only the Python standard library.

```
uv run bendlab.py prompt          # writes prompt.md from the live compiler
bend PROOF.bend && bend playground.bend
```

The second line re-checks the reference solution on whatever compiler is
installed now. It passed on 2.0.16; if a later version rejects it, working out
why is a good exercise.

If `bend` is missing, `bendlab.py` prints the install command. It installs
only with `--install-bend`, because installing pipes a remote script into
`sh` and always fetches the newest compiler, which changes what you are
testing.

## Testing a model

1. `uv run bendlab.py prompt`. The prompt is built fresh every time, because
   Bend's docs change within days; it records the compiler version and a
   materials fingerprint.
2. Open a **fresh chat with memory off**, or a temporary chat. Paste
   `prompt.md`.
3. When the model replies with a plan, send `Confirmed. Proceed.` (the
   `confirm` template), unchanged.
4. Save its three files, **from the copy or download buttons, not a transcript
   scrape**, into `work/<model_id>/`.
5. `uv run bendlab.py run`. For each model with new files, it snapshots them
   into `runs/<model_id>/aNN/`, runs both commands on the snapshot, classifies
   errors, measures the figures, and writes `paste.md` there: the next message
   to send.
6. Paste that `paste.md` into the same chat. Repeat from step 4. Once the
   code compiles, `paste.md` holds the audit questions: the only step that
   reaches the silent defects. Check the answers against the run before
   believing them.

`runs/latest-report.md` summarises the latest run; it's the file to share for
review. If you sent something other than the generated `paste.md`, record it:
`uv run bendlab.py run --strategy <what you sent>`.

## Records

- `runs/<model_id>/aNN/`: the three files as submitted, each command's output,
  `run.json` (the full record), `diff-from-previous.patch`, `paste.md`.
- `history.tsv`: one row per attempt and command. The `source` column says
  where each row came from. Backfilled rows are marked with their evidence,
  including one that rests only on a model's own notes.
- A new attempt is recorded only when the files or the compiler version
  change, so rerunning never invents attempts.
- Two checks can't be automated: whether each law is non-vacuous, and whether
  the fork tree is balanced. Fill in `done_manual` in `run.json` by hand.
- `work/` and `prompt.md` are scratch and can stay uncommitted (the prompt's
  fingerprint is in every run record). Commit `runs/` and `history.tsv` at the
  end of a session.

Not built, on purpose: an API adapter for testing models without the browser.
`run` only needs files in `work/<model_id>/`, so an adapter that writes them
there would plug in without changing anything else.
