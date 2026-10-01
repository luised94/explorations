# rep: how a build thread works

date: 2026-09-30
status: practice, written down after thread 2 (M2). Read with PLAN.md,
CONVENTIONS.md and STATUS.md at the start of every build thread.
precedence: the person's working defaults (preferences) come first, then
PLAN.md, then this file. Where this file seems to contradict either, they
win and the conflict is a finding to report. This file holds only what
they do not say: the mechanics, tactics, hazards and habits this project
has settled on, so a new thread does not rediscover them.

--------------------------------------------------------------------------------
## 1. Setting up the sandbox (clone-and-verify)
--------------------------------------------------------------------------------

- The pack is a tar of rep/ at BASE_SHA. It may arrive without .git. Make
  a local git repository whose first commit is exactly the pack (nothing
  added), so every patch can be built by diffing two real commits. Keep
  uv.lock out of that commit if the pack lacked it.
- A sandbox SHA exists only in the sandbox. Never cite one to the person;
  cite the person's SHAs, which they paste back after each commit.
- Match the recorded toolchain before running anything:
  `pip install uv==0.11.1`, `uv python install 3.12`, `uv sync`. Run the
  baseline per file (`uv run pytest tests/<file>.py | tail -1`) and compare
  with STATUS.md's breakdown, not only the total.
- The shell's working directory can reset between calls: use absolute
  paths in every command.

--------------------------------------------------------------------------------
## 2. One commit per turn
--------------------------------------------------------------------------------

The loop, in order:

1. Read the code the change touches, and its callers. Documented shape is
   evidence, not ground truth.
2. Write the change. A decision the plan does not already make is
   recorded first (PLAN.md section 5, in its own commit, or in the same
   commit when it only describes the code being added), numbered, and
   tagged in the code (section 5 of this file).
3. ASCII gate (section 4): `LC_ALL=C grep -nP '[^\x00-\x7F]' <files>`
   must print nothing.
4. `uv run pytest` and `uv run pyright`, both clean.
5. Planted bugs (section 3) for every new behavior.
6. Commit with a message file: why, not what; say "Documentation only" or
   "comment-only" when true; end with the attribution lines the session
   gives.
7. Build the patch with `git diff --full-index HEAD~1 HEAD`. Never write a
   patch by hand; never shape it for `git am`.
8. Verify the whole series, not only this patch: extract the pack into a
   clean directory, `git apply --check` then `git apply` every patch in
   order, `diff -r` against the working tree, then `uv sync`, remove
   `.hypothesis`, and run pytest and pyright there.
9. Deliver the .patch and the .msg as files, with sha256 of both and of
   every file the patch touches, as the person will have them afterwards.

Order commits by dependency: a decision is written down before the code
that depends on it; a shared piece of code is extracted when its second
real caller arrives, in that caller's commit, and the message says so.

--------------------------------------------------------------------------------
## 3. Verification tactics
--------------------------------------------------------------------------------

- Planted bugs. A test that passes on its first run proves nothing until
  a deliberate bug turns it red. Copy the tree to a scratch directory,
  change one line, run the tests against the copy. Two traps, both hit:
  - The editable install imports the original src/, not the copy. Put the
    copy first: `PYTHONPATH=<copy>/src`.
  - Tests of the installed command run `rep` from PATH. Put a shim first on
    PATH that runs `python -c "import sys; sys.path.insert(0, '<copy>/src');
    from rep.cli import main; sys.exit(main())"`.
  Run the unmutated copy through the same harness first: if it is not
  green, the mutants mean nothing.
- No hedged assertions (`x == a or x == []`). A test asserts one outcome.
- A probabilistic test is not a test of a rule. When the behavior depends
  on random draws, run main() in-process and fix the draws
  (tests/test_cli.py shows how).
- Measure end to end, through the installed command, before recording a
  timing. Summing parts under-counted lint by a quarter (interpreter start
  and imports). Record the method and the number in PLAN.md section 3.
- On the person's machine, every write check uses a throwaway data root:
  `T=$(mktemp -d) && ... REP_DATA_ROOT="$T" rep ...; rm -rf "$T"`. Never
  write test captures into ~/learning: they would count in E1.
- At the close of a milestone: install with
  `UV_TOOL_DIR=<scratch> UV_TOOL_BIN_DIR=<scratch> uv tool install
  --editable .` and run the milestone's flow through that binary; and run
  pytest and pyright at every commit of the series (`git worktree`), so
  the series bisects.
- A change that should touch comments only is proved so: parse every
  module before and after, remove docstrings, compare `ast.dump`.

--------------------------------------------------------------------------------
## 4. Known hazards
--------------------------------------------------------------------------------

- The file-writing tools turn `\uXXXX` escapes into the literal characters,
  even inside a quoted heredoc. Run the ASCII gate before every commit and
  convert with a script (character -> `\uXXXX` or `\UXXXXXXXX`). In
  comments, name the character instead ("Strasse written with sharp s").
- pyproject.toml already passes `-q` to pytest. `uv run pytest | tail -1`
  prints the count; a second `-q` removes the count line.
- Hypothesis: `from_regex` costs about 1.75 s on its first use in a fresh
  checkout and fails the too_slow health check. Use sampled alphabets.
  Inside `@given`, use `tempfile`, not the `tmp_path` fixture (it is shared
  by every example). Delete `.hypothesis` to test as a fresh checkout.
- Python text streams: under the C locale stdin decodes with
  surrogateescape (invalid UTF-8 passes silently); subprocess text mode
  turns "\r\n" into "\n" when reading output. Commands that hand input back
  exactly, and the tests that check them, use bytes.
- `secrets` is one shared module: monkeypatching `cli.secrets.token_bytes`
  also reaches the first-run device id in machine.py. Write local.toml
  before such a test, and make the fake refuse draw sizes it did not plan.
- local.toml's comment line contains the word device_id. Anchor it:
  `grep '^device_id'`.
- flock is reliable only on a Linux filesystem. The state directory must
  stay off /mnt/c.

--------------------------------------------------------------------------------
## 5. Code habits established in M2
--------------------------------------------------------------------------------

These add to the person's code style and to PLAN.md D14.

- Each module opens with REPRESENTATION and INVARIANTS. Invariants carry
  local ids (library L1-L8, storage S1-S5, events E1-E6, machine M1-M4)
  that tests, comments and messages cite.
- Decisions are traced, not remembered. A decision is `D<n>. <name> (M<k>).`
  in PLAN.md section 5, in the plan's form: choice, reason, rejected with
  scores out of 10, trade-off, revisit. The code that enforces it says
  `PLAN.md D<n>` (several: `PLAN.md D<n>, D<m>`). tests/test_traceability.py
  requires every decision marked (M2) or later to have one such reference,
  and every reference to name a defined decision. Line numbers are never
  stored: `grep -rn "PLAN.md D" rep/src`.
- Problems are data, never exceptions: a record with line, column,
  severity and message. The reader that skips something decides its
  severity (PLAN.md D22); consumers never infer it from message text.
- Refusal means the input comes back unchanged and nothing is written: a
  failed stamp prints the exact input bytes; a refused add writes neither
  library nor events.
- Two record stages for library items: SourceItem (what was written, from
  the parser) and Item (what a session may use, from check_source_item,
  only when no error remains).
- Messages say what to do next ("create it with: mkdir -p ...", "delete
  this id line to get a new one").
- Tests: one file per unit; test_smoke.py runs the installed command in a
  subprocess with its own HOME, bytes in and out; test_cli.py runs main()
  in-process where draws must be fixed.

--------------------------------------------------------------------------------
## 6. Working with the person
--------------------------------------------------------------------------------

- The person works on WSL2 and receives files in Windows Downloads. Every
  COMMANDS block starts from:
  `D="$(wslpath "$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')")/Downloads"; cd ~/personal_repos/explorations`
  then: check the hashes of the delivered files; `git status --short`
  (expect no output); `git apply --check` and `git apply`; hashes of the
  touched files; tests and pyright; `git commit -q -F "$D/<n>.msg"`;
  `git log --oneline`. Patch paths are `rep/...`, applied from the
  explorations root.
- The person runs the commands and pastes the output. Nothing is assumed
  run until that output arrives; compare every hash and count before the
  next turn.
- A decision the person must make goes in the STATE "you" slot, with
  options ranked and scored. Work that does not depend on it continues;
  work that does waits.
- Approvals are recorded in PLAN.md section 12, which is chronological:
  append at the end.
- A decision whose failure would corrupt history silently is marked
  critical (D20 is the pattern): say what contains the damage and what
  binds later milestones.
- Mistakes found in delivered or in-progress work are reported in the
  reply that finds them: what, where, the fix.
- Other threads may work on kbd or Zotero at the same time. Data read from
  kbd (the bib) can be stale; ask before concluding.

--------------------------------------------------------------------------------
## 7. Working vocabulary
--------------------------------------------------------------------------------

Domain terms are in PLAN.md section 11. Process terms used in threads:

planted bug       a deliberate one-line fault that a test must catch
clean series      every patch of the thread applied in order to a fresh
                  extract of the pack, identical to the working tree
ASCII gate        the non-ASCII grep that must print nothing before a commit
throwaway root    a mktemp data root for checks on the person's machine
enforcement point the code that carries out a decision, tagged PLAN.md D<n>
refusal           a command declines, returns its input, writes nothing
