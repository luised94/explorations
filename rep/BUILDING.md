# rep: how a build thread works

date: 2026-10-02
status: practice, written down after thread 2 (M2), extended in thread 3. Read with PLAN.md,
CONVENTIONS.md and STATUS.md at the start of every build thread.
precedence: the person's working defaults (preferences) come first, then
PLAN.md, then this file. Where this file seems to contradict either, they
win and the conflict is a finding to report. This file holds only what
they do not say: the mechanics, tactics, hazards and habits this project
has settled on, so a new thread does not rediscover them.

--------------------------------------------------------------------------------
## 1. Setting up the sandbox (clone-and-verify)
--------------------------------------------------------------------------------

- The packs are tars of rep/ and of pyutils/ (rep's install needs the
  sibling, PLAN.md D46) at the commit the thread starts from; section 6
  has how they are made. They arrive without .git. Make a local git
  repository whose first commit is exactly the packs (nothing added),
  so every patch can be built by diffing two real commits, with paths
  rep/... and pyutils/... as in the person's repository. Keep uv.lock
  out of that commit if the pack lacked it. `git get-tar-commit-id` on
  each pack prints the commit it was made from: it must be the HEAD
  the person reported.
- A sandbox SHA exists only in the sandbox. Never cite one to the person;
  cite the person's SHAs, which they paste back after each commit.
- Match the recorded toolchain before running anything:
  `pip install uv==0.11.1`, `uv python install 3.12`, `uv sync`. Run the
  baseline per file (`uv run pytest tests/<file>.py | tail -1`) and compare
  with STATUS.md's breakdown, not only the total.
- The shell's working directory can reset between calls: use absolute
  paths in every command.
- nvim for the plugin's tests (PLAN.md D43): the release tarball from
  GitHub (nvim-linux-x86_64.tar.gz) runs headless in the sandbox. Match
  the person's version (0.11.6 on 2026-10-01) and run tests with
  `nvim --headless -u NONE`, so the person's config never enters them.
  tests/test_nvim.py needs nvim on PATH and is skipped without it; put
  the tarball's bin/ first on PATH before running the suite. A plugin
  that raises leaves headless nvim at a prompt: the tests time out at
  20 s rather than hang.

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
- Startup cost: `python -X importtime -c "import rep.cli"` names what each
  import costs. A command with a time target is measured this way before
  anything is cached.
- Planted-bug harness, as run in thread 3: copy src and tests to a
  scratch directory, apply one exact-text replacement (refuse if the
  anchor is not found exactly once), run with PYTHONPATH=<copy>/src, and
  read only `^FAILED` and `^[0-9]+ (passed|failed)` lines. Three traps
  met: test_smoke.py runs the installed `rep`, so without the PATH shim
  the unmodified copy already fails (leave smoke out, or use the shim);
  adding -q to pyproject's -q hides the count line; Hypothesis's
  explanation text can contain the word "failed", so unanchored greps
  report it as a result.
- Write the expected value independently of the code under test: the
  fingerprint test spells its JSON out by hand, so a changed definition
  cannot pass by agreeing with itself.
- A test's own arithmetic can carry the bug it guards against: the
  numeric boundary property first computed a boundary outside the exact
  Decimal context and rounded it. Compute expected values under the same
  discipline as the code.
- When a formula would only be restated, test what the mechanism is for:
  fuzz is tested by twenty items reviewed alike spreading over several
  due days, which caught a fold that dropped fuzz (an M1 gap).
- Before a code commit, look for the strongest objection to the next step
  and measure the composition of decisions with the real code. Thread 3
  found D44 this way: two sound decisions (py-fsrs's 24-hour floor, the
  plan's due-by-day rule) that stalled intervals together.
- Terminal tests (tests/test_smoke.py): the installed `rep` on a
  pseudo-terminal, scripted as (text to wait for, keys to send). Send keys
  only after their own prompt has appeared, never on earlier text: the
  session discards keys typed before a prompt (PLAN.md D35), and a script
  that types early fails at random (thread 3: 1 run in 3). Repeat new
  terminal tests 20 times before trusting them.
- A planted bug must change behavior: check that the mutated line is
  really different code. Thread 3 met two that were not (a dict literal
  whose duplicated keys were overridden; a module still imported under
  another name), which would have "passed" or "failed" for nothing.
  (The PATH shim for planted bugs in the installed command is in the
  first entry of this section.)
- Terminal behavior (line input, Ctrl-D, Ctrl-C, the editor) is tested
  under a pseudo-terminal (the `pty` module), never by assuming the
  person's terminal; the person then confirms with a real session on a
  throwaway root. Make the pseudo-terminal look like a real one, or the
  test measures the harness: set its size (TIOCSWINSZ; a new one reports
  0 columns and pyutils lays out to 0, FINDINGS.md F21), make it the
  controlling terminal (start_new_session=True and TIOCSCTTY in
  preexec_fn; otherwise Ctrl-C delivers nothing), and set NO_COLOR so the
  output is plain text to search.
- Flows through $EDITOR are tested with a scripted editor: EDITOR names
  `<python> editor.py passes.json`; each call is one pass that logs the
  file as it found it, edits it as the pass says and exits with the pass's
  code. The log shows what the person would have seen on each opening
  (tests/test_smoke.py, scripted_editor).
- A pure test's helper must follow the protocol's timing, not a
  convenient one. The rounds helper wrote every grade with its answer, so
  the pure tests never met a round answered and not yet graded; the
  terminal test did, and self-graded items left before their sheet
  (session.py R5, found in thread 3 before delivery).

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
- The explorations root .gitignore ignores uv.lock (line 20); rep/.gitignore
  re-includes it with `!uv.lock`. A sandbox repository has no such root
  rule, so add `uv.lock` to its .git/info/exclude to reproduce the
  person's ignore state before testing anything about tracked files.
- Python's Decimal rounds arithmetic to 28 significant digits in its
  default context; exact comparison needs a local context with unlimited
  precision and Inexact trapped (library.py grade_typed_answer).
- tty.setcbreak and tty.setraw default to TCSAFLUSH, which discards input
  already typed. rep no longer reads single keys (PLAN.md D45); code that
  does must pass TCSANOW and flush on purpose, before each prompt, as rep
  still does before each answer line.
- pyutils has no py.typed: pyright strict reports a missing stub at its
  import. rep's one import line silences that rule (FINDINGS.md F22).
- An `# expect:` line that does not match is a stop, not a detail: chain
  dependent commands with `&&` so a wrong assumption halts before a
  commit. (Thread 3: `git status` showed nothing where `?? rep/uv.lock`
  was expected; the chain stopped `git add` and nothing was committed.)

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
- A decision whose parts land in several commits leaves pending at its
  first enforcement point (D34's grading before its reading, D35's queue
  rule before its keys); the commit message says which part landed.
- A decision approved before its code is written is marked
  `(M<k>, pending)`. It must have no enforcement point; the commit that
  adds one changes the marker to `(M<k>)` in the same commit. The test
  enforces both directions (thread 3, from D31).
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
- The person's nvim config (init.lua, plugins.lua, the extensions) is due
  for a rework toward lazy.nvim and changes independently. Do not build on
  its details; what is found wrong in it is written down for the rework,
  not fixed from here.
- The person's machine (2026-10-01): nvim 0.11.6, locale C.UTF-8.
- Threads are bounded by length, not by milestone. Thread 3 grew too
  long to work in halfway through M3, after thirteen commits (seven of
  them code) and the documents read at its start. Start a new chat at
  a commit boundary after about six commits, or sooner when the person
  finds the chat long; tune the number from experience. The handoff:
  1. Once the last commit is verified and committed, the person packs
     both directories at HEAD, each under its own name (one name for
     both makes the second archive overwrite the first):
       H=$(git rev-parse --short HEAD)
       git archive --format=tar.gz -o "$D/pack-$H-rep.tar.gz" HEAD rep/
       git archive --format=tar.gz -o "$D/pack-$H-pyutils.tar.gz" HEAD pyutils/
  2. The new chat gets both packs, the old chat's last response and
     the output of its commands, and says which mode it opens in:
     "implement mode" to continue an agreed series; without it,
     design mode applies (the person's working defaults).
  3. The new thread runs section 1 (clone-and-verify): the tar commit
     ids, then the tests file by file against STATUS.md's breakdown.
     Its first commit records in STATUS.md where the new chat began.
  What the old chat knew and the files do not say is lost, so it goes
  into these files before the handoff, as at any thread's end.

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
