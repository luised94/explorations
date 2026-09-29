# How to run a task through the use cycle

This how-to takes one task from framing to a decision, and shows what each
step you take writes into the data. For why it works this way, see
explanation.md.

## Before you start

- The patch series is applied, and `uv run grug/test_smoke.py` ends with
  `smoke: all checks passed`.
- The chat Preferences field holds exactly the text of grug/ambient.md.
  Chat memory and search of past chats are off.
- An alias is set, and the commands below run from the repository root:

      alias grug='uv run ~/personal_repos/explorations/grug/grug.py'

## The two cycles side by side

Your cycle runs down the left. The data it leaves behind runs down the
right. The outer loop at the bottom is where the data changes the method.

    YOUR CYCLE                     WHAT IT WRITES
    ----------                     --------------
    1  frame the task         -->  tasks/NAME.md
    2  find leads             <--  memory/*.md (read only)
    3  pack                   -->  runs/ID/packet.md, log: pack event
    4  paste or call
    5  continue the thread    -->  runs/ID2/packet.md, log: pack event (after ID)
    6  record the reply       -->  runs/ID/reply.md, log: reply event
    7  check and judge        -->  log: verdict event
    8  repair if it failed    -->  new thread, log: pack event (repair ID)
    9  promote a lesson       -->  memory/DATE-SLUG.md, log: promote event
    ---------------------------------------------------------------
    10 report                 <--  log folded into arms
    11 decide                 -->  core.md or domains/*.md edited: a new arm

## 1. Frame the task

Write one file per task in grug/tasks/. Put the mode on its first line and
say what done means:

    Mode: build

    # Merge overlapping intervals
    ...
    Done means: the function, a test file, and the output of running it.

Use `Mode: design` when a wrong choice would be expensive to undo; the
method then forbids code and asks for ranked options and one pick.

Writes: a task file. Commit it; the task is part of the experiment.

## 2. Find leads

    grug notes intervals

Pass a note to the pack only if it bears on this task. A note flagged
`EDIT` is an unfinished draft; one flagged `VERIFY` has not been checked
against the code for 90 days.

Writes: nothing.

## 3. Pack

    grug pack grug/tasks/merge.md --interface chat --domain code \
        --evidence src/intervals.py --model "opus-5.5 web"

Use `--interface sandbox` for a browser session that can run code, and
`--interface api` for `call`. Add `--memory NOTE` for each lead from step
2. For a baseline-arm run, add `--method grug/baseline/preferences.md`; for
a bare-arm run, `--method none`.

Writes: runs/ID/packet.md and a pack event holding the hash of every input
file, the hash of ambient.md, the arm, the mode and the packet size. The
command prints the run ID and the next command to type.

## 4. Send it

- **Browser:** open a new chat, paste runs/ID/packet.md as the first
  message (or attach the file), and let it work.
- **API:** `grug call ID`. The reply, the raw response.json and the parsed
  return block are stored at once; skip step 6.

Writes: nothing yet for the browser; for the API, everything in step 6
plus a call event with latency and token usage.

## 5. Continue the thread

When the thread needs another turn you want recorded, write the follow-up
as a task file and pack it after the previous turn:

    grug pack grug/tasks/merge-edge-cases.md --after ID --evidence test-output.txt

The follow-up inherits method, interface and model, and does not resend
the method. Paste it into the same chat. For a quick reply that needs no
packet, just type in the chat; only packed turns become data.

Record each turn's reply (step 6) before packing the next one.

Writes: a new node linked to ID, with its turn number and thread.

## 6. Record the reply

Save the whole reply to a file, then:

    grug record ID reply.md

Or paste it straight in with `grug record ID -`, then Ctrl-D. The output
shows the parsed return block. `parsed no` means the reply has no return
block, which is itself data: in a long thread it marks where the method
stopped holding.

Writes: runs/ID/reply.md and a reply event holding the parsed fields.

## 7. Check and judge

Check the work yourself: run the commands the return block lists and
compare against its `expect` lines. Then:

    grug record ID --verdict pass --note "5 tests pass, touching case included"

Judge the work, not the reply's tone or its claims. Your verdict is the
only thing the report counts as a pass.

Writes: a verdict event. A later verdict on the same run replaces the
earlier one in the report, while both stay in the log.

## 8. Repair when it failed

Decide between continuing and restarting:

- **Continue** (step 5) when the thread is on the right track and needs
  the error: `pack --after ID --evidence error.txt`.
- **Repair** when the thread has gone wrong and fresh context would help:

      grug pack grug/tasks/merge.md --interface chat --domain code \
          --model "opus-5.5 web" --repair ID --evidence error.txt

  This starts a new thread from a summary of the failed one plus your
  verdict note. Give it the same flags as the first pack; a repair is a new
  thread and inherits nothing, so different flags put it in a different
  arm. A warning at the third attempt means question the idea,
  not the code.

Writes: a new root thread linked to ID by a repair edge. The report credits
the whole chain to the task's first packet.

## 9. Promote a lesson

Only if the run's `lesson` would save work on a later task:

    grug promote ID --tags intervals,testing

Open the new note in memory/ and replace both `FILL` lines: where the
lesson holds, and what would make it a question again. Commit it.

Writes: a memory note and a promote event. The next pack can pass it with
`--memory`.

## 10. Report

    grug report

Read it one group at a time. A group is one arm on one interface, model,
ambient and mode.

## 11. Decide

At the end of a batch, compare the arms against the rule you fixed before
you started, and choose:

- **Refine:** edit core.md or a domain file and commit it. The file's hash
  changes, so later runs are distinguishable from earlier ones in the log.
  Say in the commit message what the data showed.
- **Archive:** stop, tar runs/ with the commit hash of the method it
  tested, and write down what the data showed.
- **Neither yet:** the batch was too small to decide. Run more; do not
  change the method mid-batch.

Writes: the next version of the method, or an archive. Either way, back
to step 1.

## When something goes wrong

- **`missing ambient.md`:** browser packs need it. Restore it with
  `git checkout grug/ambient.md`.
- **`inherits --method, --interface and --model`:** drop those flags from a
  follow-up turn; the thread's values apply.
- **`packed for chat`:** `call` only sends API packs. Pack again with
  `--interface api`.
- **`follow-up turns are browser-only`:** API threads are not built. Start
  each API task as its own packet.
- **`HTTP 429`:** a rate limit, logged as data. No reply was stored, so wait
  and run `grug call ID` again.
- **The reply was pasted incompletely:** `grug record ID fixed.md --replace`.
