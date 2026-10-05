# rep: plan of record

date: 2026-10-01
status: LOCKED. Design review fires only when work contradicts or exceeds this
file. A change to a decision edits this file in its own commit, with the
reason, before any code depends on it. Revisions are listed in section 12.
companions: CONVENTIONS.md (the library grammar), STATUS.md (where the build
is, and how to verify it), BUILDING.md (how a build thread works: delivery,
verification tactics, known hazards, code habits), FINDINGS.md (what was
found wrong in neighbouring code rep does not own)

Read this file first in every build thread. It is the handoff: the design
conversation that produced it is not available to later threads, so anything
a later thread needs is written here.

--------------------------------------------------------------------------------
## 1. What rep is
--------------------------------------------------------------------------------

A personal learning system for one person, run from the terminal and nvim on
WSL2. It turns readings (non-fiction, academic articles, math, language
books) into atomic retrieval items, schedules them with FSRS, runs short
focused sessions, and records every attempt as data. Language models are a
component that proposes; the person verifies. The goal is capability that
grows unassisted: automaticity on foundations, so harder material has
something to attach to.

The design follows from one claim (the "absorption bound"): past a low
threshold, access to information is not the constraint on learning. The
constraints are the structure already in the learner's head, practice with
feedback just past the current level, and judgment passed on by people who
have it. rep operationalizes the parts a program can own:

- Retrieval practice, not re-reading (testing effect; Roediger and Karpicke;
  Dunlosky et al. 2013).
- Spacing, scheduled by FSRS.
- Successive relearning: within a session, a missed item returns until
  recalled (Rawson and Dunlosky).
- New material blocked to criterion first, then interleaved (Skycak).
- Commit before reveal, so a grade is evidence, not an impression.
- Minimum information: one fact or skill per item (Wozniak).
- Automaticity is speed plus accuracy, so answer latency is recorded
  (Skycak).
- A wall is usually prerequisite debt (Skycak). This drives the M5 concept
  layer.
- Learning and performance differ (Soderstrom and Bjork). Metrics come from
  delayed, unassisted attempts.
- You can safely offload only what you can verify. Model output is always a
  proposal.

Inspiration the person named: code (Mike Acton, John Carmack, Casey Muratori,
Yehonathan Sharvit), interface (Bret Victor, James J. Gibson, Ryan Fleury),
learning (Justin Skycak, Piotr Wozniak, Andy Matuschak). The four working
stances: the inspectable craftsperson, the humble verifier, the situated
bricoleur, the convivial instrument.

--------------------------------------------------------------------------------
## 2. Scope
--------------------------------------------------------------------------------

In scope: capture, the library grammar, the FSRS memory model, sessions,
post-session review, lint, views (`why`, `forecast`, `stats`), the nvim
integration file, the language-model seam and item generation, and later the
concept layer and diagnostics.

Out of scope: sync (the person's own module; rep only stays compatible with
it, see D18), a GUI or browser renderer, multiple users, mobile, typeset math,
images and audio, the FSRS optimizer until enough history exists, formal
verification, and writing to kbd.

--------------------------------------------------------------------------------
## 3. Measured facts (with how they were measured)
--------------------------------------------------------------------------------

Environment, from the person's machine (2026-09-29/30):
- WSL2, kernel 5.15.167.4-microsoft-standard-WSL2. Home is ext4.
- uv 0.11.1. Python: uv-managed CPython 3.12.12; system 3.10.12. Target 3.12.
- `$EDITOR` is nvim. Leader is Space. `<Space>r` is taken ("runner: run
  current file", my_config/nvim/init.lua:330).
- `~/personal_repos/explorations` HEAD 624f6a8127f1274670bd73488cdc66e7a24cf25a,
  clean. rep lives in `explorations/rep/`.
- `rep` is not an existing command on the machine.
- kbd: `~/personal_repos/usb-repos/kbd` (env `KBD_LOCAL_DIR`, optional
  `KBD_MOUNT_POINT`). `kbd/recall/` holds three unused files; nothing to import.
- Bib: `kbd/zotero_library.bib`, 25,420,707 bytes, 62,062 lines starting with
  `@`, zero `@comment`. BetterBibTeX export.
- `clip.exe` garbles UTF-8: piping `cafe-with-acute lambda` produced
  CP437 mojibake. The manual transport must not pipe raw UTF-8 into clip.exe
  (see D11).
- Single-key input: `tty.setcbreak` on stdin returned the key with no Enter.
- API keys (OpenRouter, Anthropic) are loaded by hand from a USB script; they
  are not in the environment by default.

Libraries, measured in a sandbox:
- `fsrs` 6.3.2 (PyPI), MIT, runtime dependency only `typing-extensions`.
  `scheduler.py` is 858 lines: the memory math is about 170 of them, and a
  280-line state machine handles same-day learning steps.
- Fuzz uses the unseeded global `random()`: two replays with fuzz on and
  different seeds differed; with fuzz off they were identical.
- With `learning_steps=()`, `relearning_steps=()`, `enable_fuzzing=False`,
  every review stays in `State.Review` with whole-day intervals, and same-day
  reviews go through FSRS-6 short-term stability (a Good 15 minutes after an
  Again moved stability 0.7751 -> 0.8282). This makes the library a
  well-posed oracle for a pure memory model.
- Replay speed through the library's objects: 40,000 reviews in 0.40 s, about
  10 microseconds each. A heavy year is about 36,500 reviews.
- `fsrs[optimizer]` pulls torch, numpy, pandas, tqdm.
- `rich` 15.0.0 pulls markdown-it-py, mdurl and pygments, about 13 MB.
- Citekey extraction by regex from a synthetic 22 MB bib with 62,062 entries:
  191 ms (about 220 ms expected at 25 MB).

Measured while building M0 and M1:
- Clipboard: UTF-8 converted to UTF-16LE with a byte-order mark, piped into
  clip.exe, pastes intact in a Windows browser (`cafe-with-acute lambda`).
- M0 passed on the person's machine (WSL2, uv-managed CPython 3.12.12) and in
  the sandbox (CPython 3.12.3). M1 passed on both.
- The FSRS transplant equals fsrs 6.3.2 exactly (floating-point equality of
  stability, difficulty and interval) at every step of 20,000 random
  histories and 20,000 fuzz cases, in a one-off deep run; the suite runs 100
  of each.
- Decoding and folding 36,500 attempt events over 2,000 items (a heavy year):
  0.66 s (decode 0.25 s, fold 0.41 s). A full replay cannot meet the 100 ms
  target of `rep due --brief`.
- glibc strftime writes year 999 as "999"; canonical times are formatted with
  isoformat, which always pads the year to four digits.

Measured while starting M2 (sandbox, CPython 3.12.13):
- Binary floats misgrade a tolerance boundary: abs(0.4 - 0.1) is
  0.30000000000000004, so 0.4 fails `0.1 +- 0.3`; with Decimal it is 0.3 and
  passes. A 1% boundary on 6.022e23 fails with floats, passes with Decimal.
- `Decimal("Infinity")` and `Decimal("NaN")` parse, so the number syntax must
  be checked by pattern before Decimal sees it.
- `str.splitlines` also splits on U+2028, U+0085 and form feed, which nvim
  does not treat as line ends; line numbers for lint and the lines stamp
  preserves must come from splitting on "\n" only.
- Lint's parts at a heavy year (sandbox): bib key extraction from a 27.7 MB
  synthetic bib with 62,062 entries, 174 ms median of 5; parse and check of
  2,000 items, 26 ms; load and fold of 36,500 events, 215 ms. `rep lint`
  end to end on that data, through the installed command: 0.53 to 0.57 s
  (3 runs), the rest being interpreter start and imports. Library parse
  alone: 27 ms at 2,000 items, 130 ms at
  10,000 (stamp and add read the whole library on every call).
- The person's bib (2026-09-30, before a re-export): 13 entry keys held ":"
  or "?" (dates pulled into BetterBibTeX keys, one lost accent). They are
  data errors, fixed in Zotero; the grammar does not accommodate them, and
  such keys are simply never matched.
- On the person's machine (WSL2, 2026-09-30): `rep stamp` kept a CRLF line
  ending on the inserted id line and wrote one `item_stamped` event; `rep
  add` filed an item under its citekey with its event; the bib reader took
  112 ms for 62,062 keys of the real 25.4 MB export.
- Text-mode stdin on Linux does not translate "\r\n"; under the C locale
  it decodes with surrogateescape, so invalid UTF-8 would pass. Commands
  that must hand input back exactly read bytes. subprocess text mode does
  translate "\r\n" when reading output.

Measured while starting M3 (thread 3, 2026-10-01):
- Startup: `rep --version` through the entry point takes 70 ms; a bare
  interpreter takes 11 ms (sandbox, 3 runs each). `python -X importtime`:
  importing rep.cli costs 57 ms, of which importlib.metadata (imported
  only for `--version`) is 39 ms. That is most of the 100 ms target of
  `rep due --brief` before any event is read.
- The fold counted a lapse for a new item graded Again, Again, Good in its
  first session (lapse_count 1), so same-session relearning was counted as
  forgetting (D38).
- uv's CPython 3.12.13 builds readline on libedit ("EditLine wrapper").
- Decimal's default context rounds arithmetic to 28 significant digits:
  |1e30 + 0.00001 - 0| <= 1e30 is True under it (a false Good) and False
  with unlimited precision. Exact arithmetic costs time with the decimal
  places the operands span: 1e999999 against 1e-999999 took 1.7 ms,
  1e99999999 against 1 took 92 ms (D34).
- Terminal spike (sandbox, a pseudo-terminal, keys sent with human-like
  pauses): one key read in cbreak mode without Enter; a line read by
  input() with libedit, where "abc", left arrow, "X", Enter gave "abXc";
  UTF-8 kept in a line; no bytes left over between modes; Ctrl-D at a line
  gave EOFError; Ctrl-C in cbreak gave KeyboardInterrupt with the terminal
  restored. A key sent in the same write as the Enter before it was lost:
  not libedit, but tty.setcbreak's default TCSAFLUSH, which discards
  pending input; with TCSANOW it was kept. The session flushes on purpose
  instead, before each prompt (D35).
- The fold counted elapsed time in whole 24-hour periods while the plan
  serves by local day. Six daily Goods on one item, through the M1 fold:
  with each session 30 minutes earlier than the day before (23.5 hours
  apart) stability ended at 2.31 days and the next interval at 2; with
  each 30 minutes later (24.5 hours apart), 24.76 days and 25. Every
  review under 24 hours after the last was folded as a same-day review
  (D44).
- Same-day practice (2026-10-03, the fold with default parameters): a
  new item's stability after 2, 6 or 12 Goods on one day is 2.31 days
  each time, due two days later; Again then five Goods leaves 0.41. A
  same-day Good does not raise stability past the first, and a miss
  lowers it (D50).
- A new pseudo-terminal reports 0 columns and 0 rows until TIOCSWINSZ
  sets a size; pyutils then lays content out to width 0 (FINDINGS.md F21).
  A real terminal always reports its size. Nor is a new pseudo-terminal
  the controlling terminal of a process started on it, so Ctrl-C typed
  into it delivers no SIGINT; the terminal tests make it the controlling
  terminal (a new session, then TIOCSCTTY), as a person's terminal is.
- pyutils imports from its editable install with or without
  src/pyutils/__init__.py (without, it is a namespace package). With no
  py.typed, pyright strict reports a missing stub at the import and still
  infers and checks every call from the source (D46).

Measured for D42's startup cost (thread 3, 2026-10-02, sandbox):
- `rep stamp` through the installed command, on one already stamped
  item (no write), 30 runs: median 75 ms (min 69) with
  importlib.metadata imported for `--version`, 52 ms (min 47) with it
  imported only when `--version` is given. `python -X importtime -c
  "import rep.cli"`, 15 runs: median 54 ms before, 32 ms after.

Measured after the session in rounds landed (thread 3, f0c1b06, 2026-10-02):
- The session in the person's terminal (Windows Terminal on WSL2, nvim
  0.11.6, a throwaway data root): two new items over two rounds, nvim
  opening the sheet after each round, then `rep review`; the review sheet
  showed the four grades as entered, and saving it unchanged wrote nothing.
- A new item's round-1 grade sets most of its first interval; its round-2
  grade, the same day, only adjusts it. Two attempts on one scheduling day
  through the fold (default parameters, retention 0.9), as (round 1, round
  2): stability in days, and due day from 2026-10-02:
    (Good, Good)   2.31  10-04      (Good, Easy)   3.95  10-08
    (Easy, Good)   8.30  10-12      (Hard, Good)   1.34  10-03
    (Easy, Easy)  13.05  10-17      (Again, Good)  0.25  10-03
  FSRS's first rating picks the initial stability, and a same-day review
  multiplies it by a factor; Anki's first rating weighs the same way. Kept
  as computed (the person, 2026-10-02); R4 (section 9) checks it against
  observed recall.
- nvim 0.11.4 runs headless in the build sandbox (release tarball from
  GitHub); the person runs nvim 0.11.6. The person's locale is C.UTF-8.
- The explorations root .gitignore ignored uv.lock (line 20, `uv.lock`). A
  `!uv.lock` in rep/.gitignore re-includes it: a nested .gitignore outranks
  root rules (`uv.lock`, `*.lock`, `**/uv.lock`, `rep/uv.lock` were tried)
  and a global excludes file. Tracked since 57559e3.

Sources read:
- OpenRouter FAQ: free models allow 50 requests a day, 1,000 a day after
  buying at least $10 of credits. The person accepts that free providers may
  train on prompts.
- Skycak, "Individualized Spaced Repetition in Hierarchical Knowledge
  Structures": FIRe uses its own memory model (repNum, memory), not FSRS;
  credit flows down to encompassed topics on success, penalties flow up on
  failure; task selection covers several due reviews at once.
- Matuschak, "How to write good prompts": the rubric for item generation (M4).

--------------------------------------------------------------------------------
## 4. Architecture
--------------------------------------------------------------------------------

Functional core, imperative shell. The core is pure functions over plain
records. All input and output (files, terminal, clock, network, editor) is in
a thin shell. Every external capability has exactly one seam.

Data root (synced by the person's module; default `~/learning`):
```
config.toml               synced preferences: retention targets, session
                          presets, day start hour, model names
library/<name>.md         items (CONVENTIONS.md)
inbox/<time>--<task>.md   model proposals awaiting triage
events/<device_id>.jsonl  append-only history, one writer per file
llm/<time>--<task>.*      every prompt and response, as files
```

Machine-local, never synced:
```
~/.config/rep/local.toml  device_id, bib_path, kbd_root
~/.local/state/rep/lock   single-writer lock
```

Data flow:
```
capture (nvim key, rep add) --stamp ids--> library/*.md
reading notes + excerpt --model--> inbox/*.md --you edit--> rep accept --> library/*.md
library + events --parse, check, fold--> item states
item states + preset + now --plan (pure)--> ordered queue, each slot with its reason
session --one event per action--> events/<device>.jsonl
rep review --amend events--> events/<device>.jsonl
```

--------------------------------------------------------------------------------
## 5. Decisions
--------------------------------------------------------------------------------

Each decision: choice, reason, what was rejected (score out of 10), the
trade-off accepted, and what would make us revisit it.

D1. Text files are the source of truth.
  Choice: markdown library files and JSONL event logs. No database in v1.
  Reason: editable in nvim, greppable, diffable, syncable by folder, readable
  by any later tool (pandas, a GUI). Replay is fast enough (section 3).
  Rejected: SQLite as truth with nvim export/import (6); SQLite only (5).
  Trade-off: no transactions; no ad-hoc SQL until an index exists.
  Revisit: a real query need, or startup replay over 1 s. The fix is a
  derived SQLite index rebuilt from the files, never written directly.

D2. Events are append-only JSONL, one file per device.
  Every line carries `format_version` and a unique `id`. Each event is one
  complete line, written and flushed at once; a truncated last line is
  reported and skipped.
  One writer process per machine, enforced by the machine-local lock.
  Rejected: shared log (conflicts under folder sync); lock in the data root
  (it would sync and lock out the other device).

D3. Paths and identity.
  Data root: `--data-root`, then `REP_DATA_ROOT`, then `~/learning`.
  device_id: random, generated on first run, stored in
  `~/.config/rep/local.toml`. Rejected: hostname (6; two WSL machines can
  share one); a device name in synced config (2).
  Trade-off: one more file to set up per machine.

D4. The library grammar is CONVENTIONS.md.
  Reuses four kbd conventions: `@citekey:location`, indented `>` blocks,
  `?:`, `#tag`. An item is a `### Q:` heading; only question and answer are
  required. Unknown fields warn and are kept. Content UTF-8, NFC on read.
  Rejected: TOML (7, stdlib cannot write it); JSON (5); YAML (4); the old
  `@@@` recall format (not markdown: no folding or outline in nvim).
  Trade-off: coupled to those four kbd conventions. If kbd changes one, this
  grammar changes with it.

D5. IDs are generated from the question and never typed.
  A stem of up to three question words plus four random base32 characters.
  Immutable after first review. Rejected: slugs written by hand (5, capture
  friction); fully random (6, unreadable).
  Trade-off: an ID can stop matching its question after rewording.

D6. Flat items. Each item is scheduled on its own.
  No `requires:`, no variant pools, no node layer in v1. Supersedes the first
  proposal (schedule a node, sample from an item pool).
  Revisit: pools return with generated problems (the drill/ port); structure
  returns as the M5 concept layer.

D7. FSRS memory math is transplanted, with the library as a test oracle.
  About 200 lines of FSRS-6 math (21 parameters) written into rep in its own
  data model. `fsrs==6.3.2` is a dev dependency only, configured with empty
  learning and relearning steps and fuzz off. A property test requires our
  fold to match the oracle on random histories, including same-day
  sequences. Our fuzz is deterministic, keyed on (item id, review index).
  Same-session relearning attempts enter the history as same-day reviews.
  Rejected: fsrs as a runtime dependency (7).
  Trade-off: we own numerical code; an FSRS upgrade is a manual re-transplant
  that the oracle test checks.
  Revisit: a new FSRS version, or enough history to run the optimizer.
  Revised in M3 (thread 3), by D44: the fold counts elapsed days in
  scheduling days recorded on each attempt, not in 24-hour periods; the
  transplanted math is unchanged.

D8. Grading.
  In session: commit before reveal (`recall`: press a key; `typed`: type the
  answer). Then single keys, no Enter: `y` Good, `n` Again, `?` attempt
  recorded without a grade, `u` undo (an event), `s` suspend (an event), `e`
  edit (opens nvim at the item's line, then returns), `q` quit (nothing is
  lost). `check: exact` and `numeric` grade automatically.
  After the session, `rep review`: amend to Hard or Easy, mark slip or
  misconception, flag a bad item, grade `?` attempts (the model may suggest,
  you confirm).
  Rejected: model grades automatically (4, silently corrupts the history);
  self-rating with no commit (lenient; "I knew that").
  Trade-off: slower sessions, especially typed ones.
  Revised in M3 (thread 3): `u` corrects the last grade with an amend
  instead of undoing the attempt (D35); `e` and `?` drop the item from the
  rest of the session (D35); `rep review` changes grades only, and marking
  slips, misconceptions and bad items is deferred (D41).
  Revised again in M3 (2026-10-02), by D45: every attempt is typed, and
  the reveal and the grade come at the end of each round, in a grading
  sheet; the session keys are gone.

D9. Sessions.
  A session is a preset (data in config.toml), a plan and an event trace.
  The plan is a pure function of the library, the history, the preset and
  the time; each slot records why it is there (due, new, relearn, probe).
  The trace starts with `session_start` (holding a copy of the preset) and
  ends with `session_end` (with the reason). State is a left fold over events.
  Rules: new items are blocked until recalled once after other items came
  between, then interleaved; new items enter in file order, capped per day,
  and the cap shrinks as review load grows; accepted is not introduced; a
  backlog is capped and served lowest-retrievability first; the day starts at
  a configured local hour (default 4).
  Plain `rep` starts today's default session and shows its size first.
  Revised in M3 (thread 3): the preset is a constant in code, not data in
  config.toml (D39); the two caps are one budget (D36); new items across
  files are ordered by capture time (D37); the queue during a session is a
  fold over the session's events (D31). The `probe` reason waits for M5.

D10. Event record (as built in M1, src/rep/events.py).
  Common fields: `format_version` (1), `id` (12 characters of the device-id
  alphabet; the handle amend and undo point at), `at` (canonical UTC,
  `YYYY-MM-DDTHH:MM:SS.ffffffZ`, fixed width so string order is time order),
  `device`, `kind`.
  Kinds built: `attempt` (session, item, rating 1-4 or null for "?",
  latency_milliseconds from prompt shown to answer committed, typed_answer,
  fingerprint of the item text), `amend` (target attempt, rating), `undo`
  (target), `suspend` and `unsuspend` (item).
  Kinds added with their writers: `item_stamped` (M2: item creation time,
  measures capture), `session_start` and `session_end` (M3).
  Fold rules: sorted by (at, id), so input order and device files do not
  matter; undo removes its target; an undo of an undo is refused; the latest
  amend sets an attempt's rating at the attempt's own time; an ungraded
  attempt changes no memory; bad references are returned as problems, never
  raised.
  Rule: what an item is lives in the library; what happened lives in events.
  Events for items no longer in the library are skipped and reported.
  Rejected: single-letter field `v` (naming rule).
  Extended in M3 (thread 3): session_start and session_end (D40); what
  counts as a lapse (D38); `day` on every attempt (D44).

D11. Language models are a seam with two transports.
  One function, `complete(task, prompt_text) -> response_text`.
  Manual transport: rep writes the prompt file; you move it to a browser chat
  and paste the reply into a file nvim opens. HTTP transport: OpenRouter's
  OpenAI-compatible endpoint through stdlib `urllib` (free models while
  plumbing; Claude models later are a model-name change).
  Every exchange is saved in `llm/`. Output is asked for in the CONVENTIONS
  grammar and goes through the same parser and checks as your own writing.
  Proposals land in `inbox/`, at most about 15 per file. Triage is editing
  the file; `rep accept` stamps IDs, writes `by:`, appends to the library,
  and reports accepted and edited counts (the evaluation data). Generation
  input: your kbd source-notes `## @citekey` section plus the excerpt, so
  what matters is decided by you.
  Clipboard (measured): raw UTF-8 into clip.exe is garbled; UTF-16LE with a
  byte-order mark through iconv into clip.exe works. That is the route.
  Rejected: Anthropic SDK (5, one provider); Simon Willison's llm (6, second
  abstraction); litellm or pydantic-ai (4); JSON-schema output (6, free
  models vary; needs conversion for triage).

D12. nvim integration is one Lua file in this repo.
  `rep/nvim/rep.lua`, returning `{keymaps, autocmds, commands}` like kbd.lua,
  so the person's extension loader loads it. Contents: capture key (opens a
  template split; inside a kbd `## @citekey` section it fills `source:`;
  saving sends the text to `rep add --stdin`); stamp on save in library files
  (runs `rep stamp` with vim.system and replaces the buffer only on success);
  lint into quickfix. Lint output is `path:line:col: message`.
  Key prefix: a single constant, to be chosen in M3; `<Space>r` is taken.
  Reason for this repo: the Lua changes whenever the CLI contract changes, so
  by the boundary test they are one unit.
  Revised in M3 (thread 3), by D43: the same boundary test puts the key
  bindings on the other side. rep ships a plugin directory for lazy.nvim;
  the person's lazy spec binds the keys, so rep chooses no key prefix. The
  extension-loader shape above is superseded.

D13. Dependencies.
  Runtime at M0: none. `rich` is added at its first real consumer (tables,
  trees or rendered markdown, likely M5 or M6).
  Dev: pytest, hypothesis, pyright, fsrs==6.3.2 (oracle).
  Later and optional: sympy for math answer checking; torch through
  `fsrs[optimizer]` in a separate uv dependency group, run occasionally,
  writing 21 numbers into config.toml; the runtime never imports it.
  Practice for borrowed code: transplant the function, keep the license
  notice, pin the original as a differential test oracle.
  Rejected: networkx (cannot represent hyperedges), typer (hides control
  flow), prompt_toolkit (plain input loops suffice).

D14. Code reads like a proof.
  Records are TypedDicts (plain dicts at runtime, JSON-native, checked by
  pyright strict). The parser is the only validation boundary: it produces
  typed records only after checks pass. Each module opens with its data
  representation and invariants. Each function states PRE and POST.
  `check_*` functions return violations as data and run on load and before
  every write. `assert` marks programmer bugs; never run with `python -O`.
  Hypothesis properties: parse(render(x)) == x; replay is deterministic;
  stamp is idempotent and changes nothing but `id:` lines; transplanted FSRS
  matches the oracle. Style: the person's preferences (flat procedural inside
  a unit, no single-call-site helpers, full names, comments say why, ASCII).
  Rejected: frozen dataclasses (7, conversion at every file boundary).

D15. Install: `uv tool install --editable ~/personal_repos/explorations/rep`
  puts `rep` on PATH for the shell and nvim, and follows code changes.

D16. kbd is read, never written.
  rep reads the bib (citekey checks) and source-notes (generation input).
  Items do not live in kbd. Rejected: everything in kbd/recall (6);
  items in kbd, events in rep (5, splits one unit).
  kbd.lua findings (duplicate sections past line 500, unquoted bib path,
  telescope guard disabling unrelated keys, isolate buffer that discards
  edits, deprecated nvim_buf_get_option) belong to kbd_code, not this repo.
  They are listed with fixes in FINDINGS.md (F15), with what thread 3
  found in the nvim config.

D17. How the build runs.
  Sequential threads in a sandbox that can execute code. Each thread takes
  one milestone, starts from a pinned commit with a green baseline
  (clone-and-verify), delivers one commit per turn as a patch built by
  diffing real files, verified by applying it to a clean copy, with
  checksums. Parallel threads only for research reads and prompt text.
  Rejected: plain chat threads (6, cannot run anything); one shot (4);
  parallel build (3, the grammar and event schema are shared sync points).

D18. Sync compatibility (sync itself is out of scope).
  Two devices, Syncthing planned, USB git meanwhile. Per-device event files
  never conflict. Lint reports `*.sync-conflict-*` files. Do not sync a
  `.git` directory that both devices commit to. The lock and local.toml stay
  outside the data root.

D19. The concept layer waits for M5; atomic items start now.
  Framing (from memory, verify before M5): concepts are latent skills, items
  are observations, an item can test several concepts (a hyperedge; FIRe's
  encompassing weights are its weights), concepts have prerequisites. This is
  a Q-matrix (Tatsuoka) with cognitive diagnostic scoring, and knowledge space
  theory's adaptive assessment (ALEKS). Resources propose concepts and
  prerequisites; items and attempts check them. Concepts without items are
  reported gaps. Scheduler links: new items from the fringe, implicit credit,
  prerequisite probes after failures, a diagnostic session choosing items
  near 50% predicted recall.
  What matters now: atomic items (a compound item cannot tell which concept
  failed) and stable IDs with full history. Both are in v1.
  Untested: feeding synthetic Good reviews into FSRS for implicit credit has
  no failure path; FIRe also sends penalties upward. Spike before building.

D20. Grading keys for `check: exact` and `check: numeric` (M2, from section 9).
  Governing asymmetry: an automatic grade fails in two ways. A false Again is
  visible at once (the session shows the typed answer beside the key) and is
  fixed in `rep review` by an amend. A false Good is invisible and corrupts
  the history, the reason D8 refuses model auto-grading. Every leniency turns
  some false Agains into false Goods, and rep cannot know which difference an
  item is testing. So the keys are strict wherever a difference can carry a
  fact, and lenient only where it cannot.
  Exact, choice: the typed answer and the `A:` text are compared after NFC,
  removing leading and trailing whitespace, and replacing each run of inner
  whitespace with one space. Case, accents and punctuation all count.
  Reason: whitespace never carries a fact in a one-line answer; case does
  (German nouns: "Haus"), accents do ("si" and "si-with-acute" differ in
  meaning), letters do ("Strasse" and "Strasse-with-eszett").
  Rejected: plus casefold (6: "paris" would pass, but so would "haus" and
  "strasse", and casefold rules are not predictable to the person); plus
  accent and punctuation stripping (3: erases the fact in language items);
  per-item leniency such as `check: exact-nocase` (7: the right shape if the
  need is real, but grammar before evidence); alternatives in one key,
  `A: colour | color` (6: `|` is ordinary answer text, and alternatives blur
  minimum information).
  Trade-off: more false Agains on case slips ("paris" for "Paris"). Each
  costs one relearning repeat in the session and one amend in review.
  Revisit: if the use week shows more than about 1 in 10 exact attempts
  amended from Again to Good for case or punctuation alone, add a per-item
  leniency value to `check:`.
  Numeric, choice: the `A:` of a numeric item is a number, optionally
  followed by `+-` and a tolerance that is absolute or a percentage of the
  key: `A: 9.81`, `A: 9.81 +- 0.01`, `A: 6.022e23 +- 0.1%`. A number is an
  optional sign, digits with an optional decimal point (`.5` allowed), and an
  optional exponent (`e` or `E`, optional sign, digits); a tolerance is the
  same without a sign. Nothing else: no thousands separators, decimal commas,
  fractions, units, `inf` or `nan`. Keys and typed answers are read with the
  same syntax, as exact decimals (Python `Decimal`), never binary floats.
  Without a tolerance the typed value must equal the key as a number
  (`9.810` equals `9.81`, `1e3` equals `1000`). With one, it passes when
  |typed - key| <= tolerance, or <= |key| * percentage / 100; the boundary
  passes. A typed answer that is not a number in this syntax does not match.
  Reason: `+-` is the ASCII spelling of the physicist's value-plus-uncertainty,
  typeable on any keyboard, and it keeps the tolerance on the line it
  qualifies, so the item stays one fact on one line. Decimal makes the
  boundary exact: with floats, 0.4 against `0.1 +- 0.3` fails, because
  0.4 - 0.1 is 0.30000000000000004 (measured, section 3). Equality rather
  than implied precision because implied precision is invisible in the file
  and ambiguous for trailing zeros ("1000": one significant figure or four).
  Rejected: a separate `tolerance:` field (6: one fact split over two
  fields); the character plus-minus (5: not typeable, and markers are ASCII);
  implied precision from significant figures (5: invisible, ambiguous);
  units in the key (4: needs a unit library; the question names the unit,
  "in m/s^2"); floats (4: wrong at the boundary); expressions through sympy
  (later, D13).
  Trade-off: fractions, thousands separators and decimal commas are refused
  in keys and in typed answers, so the question must state the form and the
  unit; without a tolerance "9.8" fails against "9.81".
  Revisit: math items that need expressions (sympy, D13), or use-week amends
  caused by number format rather than by recall.
  Checks that follow (M2, on load and before every write): `exact` and
  `numeric` need an inline `A:`, since a block answer cannot be typed on one
  line; `numeric` needs `A:` in the syntax above; an explicit
  `attempt: recall` together with `exact` or `numeric` is an error, since
  both imply `typed`. The comparison itself is written with its first caller,
  the session (M3).
  Status: approved by the person on 2026-09-30, provisionally. Critical.
  Why critical: these keys are the only grades rep writes without the person
  deciding, and grades are the history everything else is computed from
  (FSRS state, due dates, E2, E4, E5). A wrong rule does not fail loudly; it
  biases the schedule of every exact and numeric item.
  What contains the damage: the log keeps the evidence, so a revised rule
  can regrade past attempts with amend events instead of discarding them.
  That holds only if two constraints bind M3, the writer of attempts:
  (1) `typed_answer` stores the raw typed text, before any normalization,
  so any later rule can be applied to it; (2) the item fingerprint covers at
  least the question, `A:`, `criteria:` and `check:`, so a regrade can tell
  whether the key changed since the attempt. A regrade is exact only where
  the fingerprint still matches the current item; the other attempts are
  reported, never regraded against a key they were not answered against.
  Rule for revising D20: the revision comes with a regrade over the log, or
  with a stated reason to leave past grades as they are. The regrade command
  is built when a revision first needs it, not before.
  Watch in the use week: amends on exact and numeric attempts, by cause
  (case, punctuation, number format, recall).

D21. Library parsing (M2).
  Choice: lines split on "\n" only; each classified by its first
  characters; a state machine with three states (outside an item, in an
  item, collecting a ">" block). Inside an item, a line that is not a
  field, block line, `?:` or blank is an error. A blank line ends a block.
  One space after ">" is the separator; more is content. NFC once before
  splitting; a leading byte-order mark is dropped.
  Reason: an unclassified line inside an item is text that would silently
  drop out of an answer; lint's line numbers must be nvim's.
  Rejected: str.splitlines (3: also splits on U+2028, U+0085 and form feed,
  moving every later line number); unknown lines in items as notes (4:
  silent loss); a block continued across a blank line (5: guesses which
  field the text belongs to).
  Trade-off: stricter than markdown; a stray line makes its item an error
  until fixed.
  Revisit: use-week errors from habits the grammar should absorb.

D22. Errors and warnings (M2).
  Choice: an error excludes the item from sessions (I10) and is used only
  for what breaks a session: a parse error, no id or an unusable one, no
  answer, a check or attempt value rep cannot run, a key that cannot be
  graded, an id another item uses. Everything else is a warning: unknown
  fields, source, tags, citekeys, an id not in rep's form. Readers of files
  set the severity of what they skip. Lint lists `?:` lines as notes and
  exits 1 only on errors.
  Reason: excluding an item over metadata costs practice and protects
  nothing; severity is decided where the reason is known.
  Rejected: all problems errors (5: a tag typo removes an item from
  practice); all warnings (3: a session would run items it cannot grade);
  lint inferring severity from message text (4: rewording a message would
  change it).
  Trade-off: metadata problems never force a fix; they show only in lint.
  Revisit: warnings left unfixed for weeks in the use week.

D23. Item ids (M2).
  Choice: the stem is the first three words of the question that are not
  common English words, after NFKD, keeping ASCII letters and digits; a
  question with no ASCII letter or no remaining word gets `q-` and six
  alphabet characters, others get four. Ids are unique across the whole
  library (I1): a drawn suffix already used anywhere is drawn again. An id
  not in rep's form is a warning; an id that cannot work (a block, a
  space, non-ASCII) is an error.
  Reason: readable handles with no dependency; I1 is library-wide; an id
  written by hand may already carry history.
  Rejected: a transliteration table (6: arbitrary coverage of languages);
  unidecode (4: a runtime dependency, D13); the three longest words (5:
  loses reading order); a non-rep id as an error (5: would exclude an item
  that has history under it).
  Trade-off: "Strasse" written with sharp s gives "strae"; questions in
  other languages keep their function words.
  Revisit: ids the person finds unreadable in `rep why` output (M3).

D24. Stamping (M2).
  Choice: stamp inserts `id:` lines at line offsets in the text as written
  and never re-renders it; any parse error returns the input unchanged
  (I9); warnings and check errors do not block. `rep stamp` reads and
  writes bytes and, on every refusal, writes back the exact input. New ids
  and their item_stamped events are written together or not at all; the
  lock is taken only when there is something to stamp.
  Reason: I3 and I9; E1 needs every capture; text-mode stdin under the C
  locale accepts invalid UTF-8 (measured, section 3).
  Rejected: re-rendering the file (3: loses layout, CRLF, NFD text, a
  missing final newline); ids without events when the lock is held (5:
  silent E1 loss); text-mode standard streams (4).
  Trade-off: a file with one parse error gets no new ids until it is
  fixed; every stamp reads the whole library (130 ms at 10,000 items).
  Revisit: stamp latency noticeable on save in nvim.

D25. Sources and the bib (M2).
  Choice: a citekey is anything BibTeX allows in a key except ":", "?",
  whitespace and BibTeX delimiters; a location is any text without spaces
  and is never read; `??` marks a key not yet in the bib; `@llm:` sources
  are exempt (section 9). Lint warns on a key missing from the bib and on
  a `??` key that has reached it. Bib keys are read by a bytes pattern over
  entry lines, excluding @comment, @string and @preamble; no cache.
  Reason: kbd uses location forms beyond its six specifiers; BetterBibTeX
  keys can hold punctuation; one bad byte must not hide the bib; the real
  bib reads in 112 ms (section 3).
  Rejected: an allow-list of citekey characters (5); validating the six
  location forms (5: a warning on every verse reference); a cache keyed on
  file time (5: a second copy of the keys that can drift, for 0.1 s).
  Trade-off: a key holding ":" can never be cited as written; a typo in a
  location is never caught.
  Revisit: section 9 (lint over 1 s; `@llm:` decided).

D26. Events files and item_stamped (M2).
  Choice: the loader turns every unusable line into a problem with a
  severity: a last line with no ending is skipped as a warning (it may be
  being written); other bad lines are errors. Files not named
  <device id>.jsonl, sync conflict copies among them, are reported and not
  read. An event found in another device's file is kept and reported.
  Appends write whole lines in one call, write "\n" first when the file
  does not end in one, and fsync the file and, when it is new, its
  directory. Event-id uniqueness is checked within a batch; across the log
  it rests on 60 random bits and the fold reports duplicates. item_stamped
  holds only the item id, and the fold skips it.
  Reason: D2; a fragment cut by a crash must not swallow the next event; a
  conflict copy would replay events already in the real file; D10's rule
  that what an item is lives in the library.
  Rejected: raising on a bad line (3); checking id uniqueness against the
  whole file on every append (5: reads the file per append for a risk
  below one in a million); item_stamped carrying the source (5: a copy of
  the library that can disagree with it).
  Trade-off: fsync costs milliseconds per append.
  Revisit: session latency per action in M3.

D27. Writer lock (M2).
  Choice: flock, exclusive and non-blocking, on <state directory>/lock;
  each command holds it only while it writes (`rep add` from its library
  read to its last write); the holder's pid is in the file for the
  refusal message only.
  Reason: I7; the kernel releases flock when the process dies, crash
  included (tested with SIGKILL).
  Rejected: a create-exclusive pidfile (5: stale after a crash); POSIX
  fcntl locks (6: released when any descriptor to the file is closed);
  waiting for the lock (6: hides contention; M3 may add a bounded wait).
  Trade-off: two commands at the same instant: one fails and is rerun.
  flock is reliable only on a Linux filesystem, so the state directory
  must stay off /mnt/c.
  Revisit: the session's lock scope (section 9).

D28. rep never creates the data root (M2).
  Choice: writers create events/ and library/ without parents; commands
  that need the data root check it and print `mkdir -p <data root>`.
  Reason: a mistyped REP_DATA_ROOT would otherwise create a folder that
  never syncs, and captures would vanish into it.
  Rejected: creating it on first write (5).
  Trade-off: one mkdir on first use.
  Revisit: none expected.

D29. Capture with `rep add` (M2).
  Choice: items go to library/<citekey>.md from the one source they share,
  or to `--to NAME`; a name holding "/" or starting with "." is refused.
  plan_library_append decides the exact appended text: the file's line
  endings, one blank line of separation, and a check by reparsing the
  combined file that the old items are unchanged and each new item checks
  to the same record it did alone. The lock is held from the library read
  to the last write; the library is written before the events. Only errors
  are printed.
  Reason: CONVENTIONS.md's one-file-per-source rule, in one place for the
  shell and rep.lua; context can change meaning in more ways than a list
  of cases would cover; a stop between the two writes costs one E1 count,
  never an event for an item that does not exist.
  Rejected: `--to` always required (7: the file rule would live in Lua);
  one capture file (4: breaks one file per source); predicting context
  effects case by case (5).
  Trade-off: warnings in captured items show only in lint.
  Revisit: M4, where `rep accept` appends through the same planner.

D30. Command contract (M2; what rep.lua binds to, D12).
  Choice: exit 0 on success (lint: no errors), 1 when the input has
  problems or lint found an error, 2 when rep cannot run. Problems are
  `path:line:col: severity: message`, on stderr for stamp and add, on
  stdout for lint, with absolute paths, ordered by path and line number.
  `rep stamp --path` names the buffer; lint takes no lock and prints a
  summary on stderr.
  Reason: quickfix (D12); rep.lua must tell "fix the file" from "try
  again".
  Rejected: one non-zero code (5: a busy lock would look like a broken
  file); relative paths (6: they depend on nvim's working directory).
  Trade-off: long lines.
  Revisit: M3, when rep.lua is written against it.

Decisions D31-D43 were approved by the person in thread 3, before any M3
code, with the amendments of the plan-lock pass (section 12). A heading
marked "(M3, pending)" has no enforcement point yet; the commit that adds
its code changes the marker to "(M3)", and tests/test_traceability.py
checks both states (BUILDING.md section 5).

D31. Session state is a fold over the session's events (M3).
  Choice: the plan is computed once, at session start, as a pure function
  of the library, the history, the preset and the time (D9). The queue at
  any moment is a pure function of the plan and this session's events,
  with undo and amend applied exactly as the fold applies them (events.py
  E3, E4); the code that decides which events are in effect is shared with
  fold_events. Every key writes its event first; the queue is then
  recomputed.
  Reason: D9 already says state is a left fold; a correction is an event,
  so there is no rollback code; replaying a session's events reproduces
  its queue, which a property test checks.
  Rejected: a mutable queue with an undo stack beside it (6: a second copy
  of the state that can disagree with the log).
  Trade-off: the queue is recomputed on every key, over fewer than about
  200 events.
  Revised by D45: the fold computes rounds (an item's k-th attempt in the
  session belongs to round k) instead of a queue with a relearn gap.
  Revisit: none expected.

D32. Writer lock during a session (M3).
  Choice: the session takes the lock around each append only. When it is
  busy, the session retries for 2 seconds, then names the holder and keeps
  waiting; Ctrl-C ends the session and loses only the pending action.
  `rep stamp` and `rep add` still refuse at once (D27).
  Reason: section 9's choice. `e` opens nvim, whose save runs `rep stamp`;
  capture from another terminal must keep working during a session; an
  attempt must never be dropped because `rep add` held the lock for 50 ms.
  Rejected: hold the lock for the session and release it while nvim is
  open (5: two lock states, and capture elsewhere is refused for the whole
  session); hold it for the whole session (2: stamp is refused, so items
  written through `e` get no id).
  Trade-off: two sessions at once on one machine are not prevented; each
  append is safe, but an item can be served twice in a day.
  Revisit: an item seen served twice on one machine.

D33. Item fingerprint (M3). Critical (D20 constraint 2).
  Choice: "f1:" followed by the first 16 hexadecimal digits of the sha256
  of the UTF-8 encoding of the JSON array [question, answer, criteria,
  check, attempt], as json.dumps writes it with ensure_ascii=False and
  separators (",", ":"), taken from the checked Item (NFC values; the effective
  attempt, so an exact item reads "typed"). Not included: id, source,
  tags, by, open questions, line.
  Reason: D20 needs to know whether the key changed since an attempt. A
  hash of what is asked, rather than of the text as written, does not
  change when stamp inserts an id, fields are reordered or metadata is
  edited. The "f1:" tag keeps a future definition distinguishable from
  this one instead of making every item look edited.
  Rejected: a hash of the item's text as written (3: every stamp and tag
  edit would mark items edited); including the source (6: fixing a typo in
  a location would mark the item edited); an untagged hash (5).
  Trade-off: an edit outside the five fields is invisible to "edited since
  review", by design. 64 bits: an accidental collision is not a concern.
  Revisit: a new item field that changes what is asked.
  What contains the damage: the fingerprint is stored on every attempt and
  never recomputed, so a wrong definition can be replaced by "f2:" and
  past attempts compared under the old one.

D34. Typed answers: reading and grading (M3). Critical (D20).
  Choice: a typed answer is read with input() and readline (libedit in
  uv's CPython, section 3), so arrow keys edit the line. A session refuses
  to start unless standard input decodes as UTF-8, and asks again when an
  answer holds a lone surrogate. typed_answer stores the string input()
  returned, before NFC or trimming (D20 constraint 1). The D20 comparison
  is one pure function in library.py beside NUMERIC_KEY_PATTERN: a change
  to the key syntax changes both, so they are one unit. Its arithmetic
  runs in a Decimal context with unlimited precision and the Inexact
  signal trapped, so no step rounds; before any arithmetic, an answer
  whose operands span more than 1000 decimal places does not match.
  Reason: in the terminal's line mode an arrow key enters escape bytes
  into the answer, a false Again on every exact item it touches; under a
  non-UTF-8 locale stdin decodes with surrogateescape (section 3) and the
  append would fail after the person had typed.
  Rejected: bytes from the terminal in line mode (5: no arrow keys, and
  the escapes reach the answer); prompt_toolkit (D13). For the arithmetic:
  Decimal's default context (2: rounds to 28 digits, a measured false
  Good, section 3); fractions.Fraction (6: exact too, but departs from
  D20's Decimal and has the same unbounded cost).
  readline's automatic history is off, so the up arrow cannot bring back
  an earlier answer (this removes the trade-off first accepted here).
  Trade-off: the locale must be UTF-8 (C.UTF-8 on the person's machine,
  section 3); an
  answer spanning more than 1000 decimal places against its key (such as
  1e99999999 for 1 +- 1) is an Again, amended in review if it was right.
  Revisit: libedit behaving differently in the person's terminal.

D35. Session keys (M3). Revises D8.
  Choice: commit with any key (recall) or Enter (typed). After the reveal:
  `y` Good, `n` Again, `?` no grade, `s` suspend, `e` edit, `q` quit, `u`
  correct. `u` after a grade reopens it, and the new grade is written as
  an amend of that attempt; this includes an automatic exact or numeric
  grade. `u` after `s` writes an undo of the suspend. `e` records the
  attempt as `?` if it has no grade, opens $EDITOR at the item's line, and
  drops the item from the rest of the session; it returns next session
  under its new fingerprint. `?` also drops the item: it cannot be graded
  before `rep review`.
  Reason: D8's undo removed the attempt and showed the item again after
  its answer had been seen, so a failure could be erased and replaced by a
  success. An amend keeps the attempt and records the correction, which E2
  counts.
  Rejected: undo and show again (3: retry until correct); no `u` (5: a
  mistyped key costs a trip to `rep review`).
  Built (thread 3, from the terminal spike and its tests): every prompt
  first discards keys pressed before it was shown, then shows itself; a
  key counts only once what it answers is on screen, so a grade cannot
  precede the answer and a latency cannot be near zero. The flush comes
  before the prompt, not after: after it, a key pressed in the instant
  between seeing the prompt and the flush was lost (found by the smoke
  test). `u` works at every key prompt and once more when the session
  completes. `s` writes a suspend and no attempt. `e` records `?` even for
  an automatic grade: pressing `e` says the item is wrong, so a grade
  against its key is suspect, and the typed answer is kept for review.
  Rejected: keeping keys typed ahead (4: a grade given before the answer
  is on screen is an impression, D8, and a typed-ahead commit records a
  latency near zero, corrupting E5).
  Trade-off: every correction is visible in the history as an amend; a
  key pressed while a prompt is being drawn, within milliseconds, is
  dropped and must be pressed again.
  Revisit: none expected.
  Superseded by D45 (2026-10-02), except the flush before each prompt,
  which stays for the answer line: the keys are replaced by one typed
  answer per item and a grading sheet per round, where a correction is an
  edit, `e` is `gF` on the item's path:line and `s` is the word suspend.

D36. The plan (M3). Revises D9's two caps into one budget.
  Choice: due items are error-free, unsuspended items with a memory state
  whose due day (D44) is today or earlier, today being the scheduling day
  of the session's start. Reviews are taken lowest retrievability first
  (ties: due day, then id), at most `session_budget`. New items are error-free, unsuspended
  items with no graded review. New today = min(new_per_day minus items
  introduced today, (session_budget minus reviews) // new_item_cost),
  where introduced today means a first attempt of any kind on today's
  scheduling day. Order:
  reviews, then new items (D37). In the session: an Again returns after
  `relearn_gap` other items (at the end when fewer remain); a new item's
  first showing always returns after the gap; an item leaves the session
  on a Good that is not a new item's first showing. Default preset (D39):
  session_budget 60, new_per_day 10, new_item_cost 3, relearn_gap 3,
  day_start_hour 4, desired retention 0.9. Approved by the person.
  Reason: one budget gives both of D9's rules, the backlog cap and new
  intake shrinking as review load grows; 60 attempts is about 12 minutes,
  inside E2's prediction; reviews first, so a session cut short costs new
  material rather than review debt (Skycak); D9's blocking rule.
  Rejected: separate review and new caps (6: two numbers that interact);
  new items mixed among reviews (6: Anki's default; a short session then
  leaves debt).
  Trade-off: relearning attempts are not counted in the budget, so a bad
  day runs past 60; with one item left, the gap cannot be kept.
  Revised by D45: relearning runs in rounds; an item leaves after a round
  in which it met the criterion above, and relearn_gap is retired.
  Revisit: E2 session length and E3 in the use week.

D37. Order of new items (M3).
  Choice: within a file, by line; between files, by the earliest
  item_stamped time among each file's new items; items without an
  item_stamped event come last, by path and line.
  Reason: D9's "file order" is undefined across files. Inside a file the
  order is the reading order (CONVENTIONS.md); across files, the reading
  begun first is finished first. Capture times are already recorded (E1).
  Rejected: file-name order (5: alphabetical by citekey means nothing);
  one global capture order (6: contradicts CONVENTIONS.md inside a file).
  Trade-off: an item with a hand-written id has no capture time.
  Revisit: the use week.

D38. What counts as a lapse (M3).
  Choice: a lapse is an Again on an item with a memory state, at least one
  scheduling day (D44) after its previous graded review: exactly where
  memory_model.py applies its post-lapse stability formula instead of the
  same-day one. Only lapse_count changes; memory does not, so the oracle
  test is unaffected.
  Reason: section 11 defines a lapse as a failed review of a learned item.
  Successive relearning makes repeated Agains in one day normal; the old
  rule counted them (measured, section 3). Counting a lapse where the
  model treats the Again as forgetting keeps the two from disagreeing, and
  the fold needs no record of sessions.
  Rejected: an Again on an item's first graded attempt in a session (7,
  the plan-lock choice: the fold must track sessions, and two sessions on
  one day, such as two devices before a sync, count two lapses); every
  Again on an item with a memory state (3, the M1 rule). Revised on
  2026-10-01 with D44, before any code: the 24-hour floor that ruled out
  the elapsed-day rule is gone.
  Trade-off: an item learned and failed again later on the same
  scheduling day is relearning, not a lapse.
  Revisit: the leech threshold (M3b).

D39. The preset is a constant (M3). Revises D9.
  Choice: one default preset, a constant in the session code. Each
  session_start event records a copy (D40).
  Reason: config.toml would add a reader, validation and a file format for
  numbers tuned a handful of times; the event keeps the history
  self-describing either way.
  Rejected: config.toml now (6).
  Trade-off: tuning means editing a constant and committing; both devices
  get it through git.
  Revisit: a second preset, or two devices needing different values.

D40. Session events (M3). Extends D10.
  Choice: session_start carries `preset`, an object of the D39 values; its
  event id is the session id that attempts carry. session_end carries
  `session` and `reason`: completed (the queue emptied), quit (`q`) or
  interrupted (Ctrl-C, end of input). A session without a session_end was
  abandoned (terminal closed, crash). At start, the session warns when the
  clock is earlier than the newest event in the log; recorded times are
  never corrected.
  Reason: D9, E2, E3; no second id space. WSL2's clock can fall behind
  after the host sleeps, and a time behind the log sorts new events before
  old ones.
  Rejected: a separate session id (5: a second id space); counts in
  session_end (5: derived data that can disagree with the log).
  Trade-off: an abandoned session has no end time; E2 measures it to its
  last attempt.
  Revisit: M3b stats.

D41. `rep review` (M3). Revises D8.
  Choice: `rep review` writes a file in the state directory with one line
  per attempt of this device's last session, plus every attempt still
  without a grade: a grade word (again, hard, good, easy, ?), the attempt
  event id, then text for reading only (item id, the question on one line,
  the typed answer, the key). Only the first two words of a line are read,
  as in `git rebase -i`. It opens $EDITOR. On exit 0 and a file that
  parses, it writes one amend per changed grade, under the lock; a file
  that does not parse is reported and reopened; a non-zero editor exit
  writes nothing. Grades only: marking slips, misconceptions and bad items
  is deferred (a bad item gets a `?:` line, which lint lists).
  Reason: triage by editing a file, as D11 chose for the inbox, so there
  is no second terminal interface and the whole session is in view. D20's
  watch of amends by cause (case, punctuation, number format) needs no
  recorded cause: the cause can be computed from the raw typed answer and
  the key. Attempts ungraded in older sessions would otherwise never be
  graded.
  Rejected: an interactive key loop (6); `rep amend ATTEMPT GRADE` (4:
  event ids must be looked up and typed).
  Trade-off: no slip or misconception labels in the use-week data; a grade
  cannot be amended back to `?` (an amend needs a grade).
  Revisit: M5 or M6 asking for labels.
  Revised by D45: the same sheet grades each round of a session; `rep
  review` opens it for attempts still ungraded. Lines carry the item's
  path:line, so `gF` opens the item; the grade words are again, hard,
  good, easy, ? and suspend.
  Built (thread 3): the ungraded attempts listed are those of every device
  and session (session.py V1). An attempt whose item is in no library file,
  or has an error, is left off: with no key there is nothing to grade
  against, and lint lists both. An entry whose item changed since the
  answer (its fingerprint differs, D33) carries a note that the key shown
  is today's. `rep review` waits for the writer lock as a session does
  (D32) instead of refusing as stamp and add do (D27): a refusal would
  discard grades the person had just written.

D42. `rep why`, `rep unsuspend`, startup cost (M3).
  Choice: `rep why ID` prints where the item is (path:line), its state
  (stability, difficulty, retrievability now, due day, reviews, lapses,
  suspended), its attempts with their grades and whether each attempt's
  fingerprint matches the item now, and whether and why today's plan
  includes it. `rep unsuspend ID` writes one unsuspend event (D10 has the
  kind; nothing wrote it). importlib.metadata is imported only for
  `--version`. `rep due --brief` is not built in M3: it is the shell cue,
  which E3 names as the remedy when sessions are skipped, and plain `rep`
  already shows the session's size. When E3's guardrail calls for it, it
  is built as a full replay first, with a snapshot only if that measures
  over 100 ms (D25's argument against caches before measured need).
  Reason: the scheduler must be inspectable during the use week; without
  unsuspend, a suspend is permanent; `--version` costs 39 of 57 ms of
  import on every command (section 3), and stamp on save (D43) runs rep
  on every save of a library file.
  Rejected: `rep due --brief` in M3 (6: code for a remedy before its
  guardrail fires); the snapshot now (5); `rep stats` and `rep forecast`
  now (5: views designed against synthetic histories; they move to M3b,
  built on the use week's events).
  Trade-off: no shell cue in the use week, and section 8's `rep due
  --brief` time has nothing to measure until the cue exists.
  Revisit: E3 under 4 sessions in 7 days.
  Built (thread 3, in parts): `--version` is a plain flag, handled
  right after parsing and before the machine context, as
  action="version" was; it imports importlib.metadata only then
  (section 3: stamp end to end 75 to 52 ms). A test checks that stamp
  and lint never load importlib.metadata. Trade-off: `rep --version
  add` now reports add's missing --stdin instead of the version
  (action="version" stopped parsing at the flag).
  `rep why ID` prints facts only: place, memory state, recall now, due
  day, reviews and lapses, suspended, whether today's plan has it and
  as what (due or new), and each attempt with its grade, typed text and
  whether the item changed since. It does not say why an item is left
  out of today's plan: that would be a second copy of plan_session's
  rules, which could disagree with it. The state lines show the reason
  (suspended, a due day ahead, shown today) except for the two caps
  (budget, new items per day). Anki's card info makes the same cut.
  `rep unsuspend ID` writes nothing for an item that is not suspended,
  and waits for the writer lock as review does (D41 Built): it is one
  quick event, and a session holds the lock only per append. Both
  share the session's library and events read, in the same branch.
  An unknown id exits 2 (a bad argument, D30).

D43. nvim plugin (M3). Revises D12.
  Choice: rep/nvim/ is a plugin directory on the runtime path:
  lua/rep/init.lua with setup(), the command :RepCapture, and stamp on
  save for <data root>/library/*.md. Lint needs no plugin code: nvim's
  :make with makeprg set to `rep lint` and an errorformat for D30's
  `path:line:col: severity: message` fills quickfix, and the plugin's
  documentation gives those two settings. Key bindings live in the
  person's lazy.nvim spec ({ dir = ".../rep/nvim", keys = ... }), so rep
  chooses no key prefix. The data root comes from `rep where --data-root`,
  asked once per nvim session. Stamp on save inserts only the lines stamp
  added (from vim.diff indices) and never replaces the buffer. rep.lua is
  tested headless with nvim in the build sandbox.
  Reason: the boundary test: the Lua that runs rep changes with the
  command contract, the keys do not. The person is moving to lazy.nvim
  and archiving the extension loader. Stamp only inserts lines (library.py
  L6), so applying the inserts is exact and keeps the cursor, marks and
  folds. D3 has one implementation.
  Rejected: D12's {keymaps, autocmds, commands} file (5: targets the
  loader being archived); D3's rules copied into Lua (6: two copies that
  can drift); replacing the whole buffer (4: loses cursor, marks, folds);
  a :RepLint command (6: re-implements :make and errorformat, which nvim
  has built in).
  Trade-off: no keys until the person adds the lazy spec; the commands
  work without it.
  Revisit: the person's nvim config rework.
  Built (thread 3): rep/nvim/lua/rep/init.lua and rep/nvim/README.md
  (the lazy spec, and lint through :make). Stamp on save runs for
  files directly in the library directory, compared by real path; it
  applies stamp's output as the insertions vim.diff finds, refuses
  output that changes a line, and on a refusal saves the file as
  written with the problems in quickfix. The data root is asked on
  the first .md save or capture, not at startup, so nvim starts
  without running rep; a failure to ask is reported once per session.
  Capture changed from D12's template split piped to `rep add
  --stdin`, made by the build for the person's review: :RepCapture
  opens library/<citekey>.md (citekey from the nearest `## @citekey`
  above the cursor, the grammar's source section, or a name given)
  with an item template at the end, and the ordinary save stamps it.
  Reason: one write path instead of two, and stamp problems land in
  quickfix at the real file's lines, where `rep add`'s are at
  <stdin> lines with no buffer to jump to; about half the Lua.
  Rejected: D12's split piped to `rep add` (6: a second write path
  with its own error mapping and buffer lifecycle, for checks stamp
  and lint already make). Trade-off: a captured item is written into
  the library file even when it has problems (stamp refuses its id,
  quickfix lists it, lint finds it), where `rep add` refused to write
  it at all; and the template's `source:` line repeats the citekey on
  every item. `rep where --data-root` prints only the path; its flag
  has its own argparse destination, because the global --data-root
  PATH has the same name and argparse would overwrite one with the
  other. Tested headless with nvim 0.11.6 (tests/test_nvim.py, which
  is skipped when nvim is not on PATH).

D44. Elapsed time is counted in scheduling days (M3). Revises
D7's elapsed days and D36's due rule; approved by the person on 2026-10-01
after the plan lock, before any code depends on it.
  Choice: every attempt event carries `day`, the scheduling day the
  answer was committed in: the local calendar date of that moment moved
  back by day_start_hour (D36, 04:00), as YYYY-MM-DD, computed by the
  writer from the machine's time zone and never recomputed. The fold's
  elapsed days between two graded reviews are the difference of their
  days; an item is due on a day (the day of its last graded review plus
  the fuzzed interval). memory_model.py does not change: it takes elapsed
  days as a number, and the oracle test (I5) supplies its own.
  Reason: measured (section 3): the plan serves by day, and a review
  served today but under 24 hours after the last one was folded as a
  same-day review, so the interval barely grew (six daily Goods: 2.31
  days of stability against 24.76, depending only on whether each session
  was earlier or later in the day than the one before). Anki, whose review
  logs fitted FSRS's default parameters, counts elapsed days by its
  rollover day the same way. The day is recorded, not derived from `at`,
  because `at` does not hold the time zone and rollover in effect when
  the person answered.
  What the day stands for: the rollover hour is meant to fall while the
  person sleeps, so a day boundary approximates one night of sleep
  between two retrievals. Sleep is when declarative memories consolidate
  (Diekelmann and Born 2010), and with the time between sessions held at
  12 hours, a night of sleep between learning and relearning halved the
  trials needed to relearn and left more retained at one week and six
  months than a waking 12 hours (Mazza et al. 2016). Elapsed days in FSRS
  thus carry two quantities: time, over which retrievability decays, and
  sleeps, across which a review counts as long-term. day_start_hour is
  the hour the person is most surely asleep, not a clock convention.
  Rejected: whole 24-hour periods (2: the measured stall); the day
  computed in the fold from the current time zone (7: travel or a second
  machine in another zone would re-date past reviews near the rollover);
  due by exact time instead of by day (5: a session a little earlier
  than yesterday's would push items a whole day later, again and again).
  Trade-off: an attempt carries a value that `at` usually implies; a
  review after midnight and before 04:00 belongs to the day before;
  changing day_start_hour does not re-date past attempts.
  Revisit: the person's sleep regularly crossing 04:00 (move the hour);
  sleep data becoming available (the boundary could be an observed sleep
  rather than a clock hour; section 9).

D45. Rounds: every answer typed, graded per round (M3).
Revises D8, D31, D35, D36, D41; approved by the person on 2026-10-02
after the first real session.
  Choice: every attempt is typed. The question is shown, the person types
  what came to mind (a cue is enough) and presses Enter; nothing is
  revealed. The attempt is written at once with its raw text, latency,
  fingerprint and day: ungraded for a self-graded item; for an exact or
  numeric item, with its automatic grade (D20), still not shown until the
  sheet, so that changing it there is a recorded correction, which D20's
  watch and E2 count (refined while building, 2026-10-02: written
  ungraded, every automatic grade would need an amend, and accepting it
  could not be told from overriding it). When every item of the round has an
  attempt, rep writes the round's grading sheet (D41's file) and opens
  $EDITOR: one line per attempt, the typed text beside the key; exact and
  numeric lines come graded by D20, self-graded lines come as `?`. Saving
  writes one amend per graded line and a suspend per `suspend` line; lines
  left `?` stay ungraded and wait for `rep review`. Round 1 is the plan;
  round r+1 holds the items of round r that have not met D36's criterion;
  the session ends when a round is empty. Ctrl-D at the answer prompt
  stops showing items, opens the sheet for what was answered, then ends
  the session (reason quit); Ctrl-C ends it at once (interrupted; its
  attempts stay ungraded for `rep review`).
  Reason: the first real session (2026-10-02, the person's terminal):
  single-letter keys, two input modes (a key for recall items, a line for
  typed ones) and no separation between items made it jarring, and it was
  unclear which inputs were answers. Now there is one input mode, and every
  retrieval leaves a written record, so a self-grade compares that record
  with the key instead of an impression of having known it; giving people
  the correct answer as a standard is how research on self-scoring has
  improved its accuracy (Dunlosky, Hartwig, Rawson and Lipko 2011,
  "Improving college students' evaluation of text learning using idea-unit
  standards"; title and listing checked, full text not read). Grading
  happens in nvim, where the person works, with the round in view, and
  `gF` on a line's path:line opens the item to fix it. Feedback at the end
  of a round, not after each item: for adults, delayed and immediate
  feedback gave the same final performance once the delay to the final
  test was equal (Metcalfe, Kornell and Finn 2009). Successive relearning
  (D9) keeps its shape, test, feedback, retest of the misses until
  recalled; the rest of the round is the gap between two showings, so
  relearn_gap is retired from the preset.
  Event model: unchanged. Self-graded attempts are written with rating
  null and graded by amends (E4). An item's k-th attempt in the session belongs to round k,
  so replay reproduces the rounds (D31) with no new event kind (for a
  finished session, with the cutoff under "Replay" below).
  Rejected: per-item reveal and grading on a clearer screen (7: immediate
  feedback, but two input modes and a grading menu to build); the M3 loop
  as first built (5, the person's verdict); a full-screen terminal
  interface (4: a dependency or several hundred lines for what nvim does).
  Trade-off: every item is typed, so sessions are slower, most for long
  answers (D8's trade-off on every item; E2 measures it). Latency now
  includes typing, so E5 compares an item with itself over time, not items
  with each other. A miss stays uncorrected until its round ends. A crash
  during grading leaves the round for `rep review`. A round of one item
  shows it right after its feedback.
  Revisit: E2 sessions over 15 minutes; grading sheets the person finds
  slow.
  Built (thread 3, with the session loop): the rounds fold looks at most
  one round past the last graded one (session.py R5). The events cannot
  say when a sheet was saved (saved unchanged, it writes nothing), so the
  loop counts graded rounds; without the bound, a round's ungraded answers
  decided the next round and self-graded items left before their sheet
  (found by the terminal test, not by the pure tests, whose helper graded
  every answer as it was given). The sheet is a file in the state
  directory, removed once read. A sheet with problems is reopened with
  each problem as a comment right above its line; the person's edits stay.
  An editor that exits non-zero or cannot be run applies nothing, and the
  session goes on as the automatic grades decide. Each card shows its
  place in the round, why the item is there (new, due, retest) and, for an
  exact or numeric item, its check, since that answer is compared as typed.
  The sheet shows a typed answer or key that spans lines (an answer
  written in $EDITOR through Esc v, D47; a block key) one comment line per
  line, indented under the first; before, a second line would have read
  as an entry and stopped the sheet (found by the D47 measurement).
  Cards after round 1 say "retest", not "again" as first built: in the
  person's first session in rounds, "again" read as the grade Again on
  an item just graded Easy (approved 2026-10-02).
  Replay (approved by the person on 2026-10-02, after f0c1b06): a finished
  session's rounds are rebuilt from its events counting only the amends
  written before its session_end. A later `rep review` grade on an answer
  left `?` would otherwise send that item into a round it never had: in
  the session it left after that round (R3). Any reader of past sessions
  (M3b's stats, the research questions in section 9) applies the cutoff.
  An abandoned session has no session_end, so its cutoff is unknown: such
  a reader reports those sessions apart instead of guessing.
  Rejected, for the bound and for this rule: a round_graded event written
  at each saved sheet (6: everything needed to rebuild a session would
  then be in the log, the event-sourcing rule; not decisive, since nothing
  rebuilds a session part-way, there being no resume). Trade-off: the rule
  lives in readers, not in the events. Revisit: resuming a session, which
  makes round_graded necessary. (Thread 3 reported this rejection as
  recorded with f0c1b06; it was not, and is recorded here.)

D46. The session's display uses pyutils.terminal_output (M3).
Revises D13.
  Choice: the session and `rep review` draw through the person's pyutils
  package (explorations/pyutils, module terminal_output): a card per
  question, labeled separators between items and rounds, wrapped text.
  pyutils is a path dependency of rep (a uv source, ../pyutils, editable),
  imported only inside the session and review branches, so stamp, add,
  lint and where never load it. The library's own detection turns styling
  off for NO_COLOR or a non-terminal; the terminal tests set NO_COLOR.
  Reason: the person's tools should share one look, and a change to that
  look should reach rep: by the boundary test the presentation layer is
  shared, not rep's to copy. Contained: a fault in it cannot break the
  commands nvim runs on save.
  Rejected: copying the needed functions into rep (6: two looks that drift
  apart); plain print with ASCII separators (5: a second visual language);
  rich (5: a third-party dependency of about 13 MB, D13).
  Trade-off: rep's runtime now needs the sibling pyutils directory (both
  machines clone explorations); uv.lock changes; pyutils keeps module
  state (layout, color), which the session sets once.
  Verified (thread 3, in the code commit): pyutils/pyproject.toml names
  pyutils, requires Python 3.10 or later and builds with setuptools from
  src/; `uv sync` and `uv tool install --editable` both resolve the path
  source, and uv.lock records it as editable ../pyutils (section 3).
  Built: only the session draws through pyutils; `rep review` prints one
  plain summary line, so it does not import it (narrower than the choice,
  nothing to draw). Prompts that input() writes, and plain lines, start at
  the column emit() gives a card, found with pyutils' own align_text. A
  test runs stamp and lint in a fresh interpreter and checks pyutils was
  never imported. pyutils has no py.typed, so the import silences
  pyright's missing-stub rule there; the calls are still type-checked
  (FINDINGS.md F22). The terminal tests set NO_COLOR and a 100-column size
  (F21).
  Revisit: pyutils leaving explorations, or a second consumer needing a
  different look.

D47. Vi-mode editing at the answer prompt (M3). Revises D34's line
editing; approved by the person on 2026-10-03.
  Choice: the session switches readline to vi mode itself (libedit's
  `bind -v`, or GNU readline's `set editing-mode vi`), so no dotfile is
  needed. Esc gives normal mode (h l w b e 0 $ x cw cc dw u A); Esc v
  opens the answer in $EDITOR and what is saved there becomes the
  answer, several lines included. Tab inserts a tab.
  Reason: the person edits in nvim; the answer prompt should use the
  same modal editing. Measured on uv's CPython (libedit), on a
  pseudo-terminal: the motions and operators above work, and v hands the
  line to $EDITOR and returns its text.
  Rejected: ~/.editrc (7: no code, but a setting the person must know to
  make, and it changes every libedit program); the whole session in nvim
  (6: full nvim, but a protocol and a second interface; revisit after
  the use week); nvim opened for every answer (4: a screen switch per
  question); prompt_toolkit (4, D13).
  Trade-off: libedit has no text objects (ciw), no visual mode and no
  mode indicator, and the arrow keys, Home and End do nothing useful in
  insert mode: its Esc cannot be both the mode switch and the first byte
  of an arrow's sequence (binding the sequences broke Esc, measured).
  GNU readline has a timeout for this; uv's CPython does not ship it.
  The session shows the keys on screen (D51).
  Revisit: the use week finding the prompt too limited (then the session
  in nvim).

D48. Later rounds in a fresh order (M3). Revises D45's round order;
approved by the person on 2026-10-03.
  Choice: round 1 keeps plan order; each later round shows its items
  ordered by sha256 of (session id, round number, item id) (session.py
  R6). Which items a round holds does not change.
  Reason: the person: meeting items in the same order is a cue, and
  "weird". Round 2 repeated round 1's order only because it was the
  simplest code. A hash, not random.shuffle: the random module promises
  the same sequence across Python versions only for random() itself, so
  a replay on a later Python could reorder a past session.
  Rejected: shuffling round 1 too (6: mixes reviews and new items, but
  loses P3, the most-forgotten first so a session cut short loses the
  least, and D37's reading order for a reading's new items; a deck's
  file is shuffled once instead, CONVENTIONS.md Decks); a per-session
  random seed recorded in the events (5: a new field for what the
  session id already provides).
  Trade-off: round 1 of a reading still follows the file's order, by
  design.

D49. A session records what cannot be recovered later (M3). Revises
D40; approved by the person on 2026-10-03.
  Choice: session_start also carries utc_offset (the machine's offset
  when the session started, +HH:MM or -HH:MM), plan (the items it started
  with, in plan order, each with its reason) and rep_source (12 hex digits
  of sha256 over rep's source files). All three are optional when read,
  so sessions written before them still read; every new session writes
  them.
  Reason: the person wants the time of day, the size of a session and
  the version of the session as a whole tracked. Measured against the
  events: the order and round of every attempt can already be derived
  (times, and an item's k-th attempt is round k, D45, still true under
  D48); the local hour cannot, since `at` is UTC; the plan cannot be
  recomputed once the library changes; the code that ran was recorded
  nowhere, the package version being always 0.0.0.
  Rejected: a version number bumped by hand (6: readable, but a bump
  forgotten once makes two different codes look the same); the git
  commit (5: rep runs from an editable install with no promise of a
  clean tree); the time zone name (5: the offset is what converts `at`
  to local time; a name is only needed to predict future offsets).
  Trade-off: a source hash says "different code", not what changed; the
  commit that matches a hash is found by hashing commits.
  Revisit: R3 needing the zone name, or sessions needing the plan's
  reasons beyond due and new (drill, D50).

D50. Drill: practise chosen items, as often as wanted (M3). Approved by
the person on 2026-10-03.
  Choice: `rep drill [DECK] [--tag TAG] [--count N]`. A deck is a library
  file (its name without .md); --tag narrows to items with that tag;
  --count draws at most N at random. No deck means every deck. Suspended
  items are left out. The items are ordered by sha256 of (session id,
  item id), then run in rounds exactly like a session (D45): the same
  sheet, the same grading, new items returning once (D36). An item never
  graded before is "new"; one seen before is "drill". Attempts are
  ordinary attempts; session_start records the plan (D49) and the
  selection as given. Before Enter, the drill says what it chose: "N of
  the M items in DECK tagged TAG", how many suspended were left out, how
  many have never been seen (from today they are on the schedule). A deck
  or tag that matches nothing is answered with the decks, or the deck's
  tags, that exist, with their counts.
  Reason: the person wants to go through the permit questions several
  times a day before the test, and to choose a session's content (a deck,
  a topic before an interview). Measured (section 3): after a first Good,
  further Goods the same day leave stability where it was (2.31 days
  after 2, 6 or 12 Goods), and an Again lowers it; so drill attempts can
  be ordinary attempts, and the scheduler stays honest without a special
  case. A file as the deck, tested on the person's two decks: --tag permit
  would have selected 7 of the 53 permit items, since #permit meant "about
  the permit"; the file selects all 53 and cannot put an item in two decks.
  Rejected: attempts that do not count (6: Anki's cram that leaves the
  schedule alone; it throws away real retrievals); a tag as the deck (5:
  measured above, a topic word read as membership); a deck field or a
  reserved #deck_ tag (4: repeats the file, and can drift from it); a
  separate tool (2).
  Trade-off: drilling new items puts them all on the schedule at once,
  past new_per_day (the drill says so before it starts); a drill
  has no budget, so --count is the person's limit.
  Revisit: the use week's drills crowding out scheduled sessions (E3).

D51. The session shows what the person would otherwise hold in mind
(M3). Approved by the person on 2026-10-03 ("prevent the user from having
to hold state, interface, units, domain, format, order, sequence").
  Choice: each screen states what it depends on.
  Start: the session's decks with their due and new counts, about how
  many answers it takes (R4: reviews once, new items twice), and the
  keys (typing, Esc vi keys, Esc v editor). A drill says what it chose
  (D50).
  Each round: its number and size ("round 2: 4 to retest") and one line
  of keys, Ctrl-D and Ctrl-C included.
  Each card: its deck, why it is there (new, due, drill, retest) and, for
  an exact or numeric item, how the answer is compared, in words ("as
  written", "a number").
  The sheet: what each grade word means, and that a new item's first
  grade sets most of its first interval (good about 2 days, easy a week
  or more; section 3).
  The end: when this session's items come back.
  Nothing to practise: when the next item is due, and `rep drill` with
  the decks that exist.
  Reason: what a screen does not show, the person must remember (Krug's
  "don't make me think"); the schedule is otherwise invisible (Victor:
  show the consequence where the decision is made). In the first
  sessions the person met each of these as a question: what "again"
  meant on a card (now "retest"), why a second `rep` said nothing, what
  easy would do.
  Rejected: a help screen or a `?` key (5: help the person must think to
  ask for); a full-screen status bar (4: a terminal interface, D45).
  Trade-off: more lines on screen, each read once; the key line repeats
  every round. Units stay in the question (CONVENTIONS.md): rep does not
  know an answer's unit.
  Revisit: the person finding the screens noisy.

D52. The same question twice is refused by add, warned by lint (M3).
Approved by the person on 2026-10-05 (after the trial).
  Choice: `rep add` refuses, writing nothing, an item whose question is
  already in the library; lint warns on every later copy of a question,
  naming the first. Questions are compared with spaces collapsed and case
  folded.
  Reason: the trial root grew to five copies of each deck (1,255 items
  from 251) because one command block, re-run, added the decks again;
  nothing said so. Refusing makes re-running an add harmless.
  Rejected: refusing in lint, or excluding duplicates from sessions (5:
  two sources may ask the same thing on purpose; a warning keeps both);
  comparing answers too (4: the same question with a corrected answer is
  still a duplicate).
  Trade-off: an item reworded only in case or spacing is refused; reword
  it, or add it by hand and accept lint's warning.

D53. `rep status`: the state of everything on one screen (M3). Approved
by the person on 2026-10-05 ("maybe a rep status or something").
  Choice: `rep status` prints the data root and the rule that chose it,
  today's scheduling day and its rollover hour, each deck's items, new,
  due now, suspended and next due day, the answers still without a
  grade, and today's sessions and drills. Read-only, no terminal needed.
  A missing data root's message names the rule that chose it and how to
  choose another.
  Reason: in the trial, `rep review` after `unset REP_DATA_ROOT` said
  only "data root ~/learning does not exist", which reads like lost
  data; and after a session there was no way to see what was due, by
  deck, without running one.
  Rejected: `rep decks` alone (6: decks without the root and the
  waiting answers misses both trial confusions); folding it into `rep
  where` (5: where answers "which files", status answers "what now").
  Trade-off: one more command.

D54. A session explains its own rules where they act (M3). Revises
D51; approved by the person on 2026-10-05, after the trial.
  Choice: a retest card says why it is back: "retest, missed" (graded
  again) or "retest, second look" (a new item's first showing, D36), and
  each later round says so in one line. When a saved sheet still has
  answers left ?, rep says they will leave the session without a retest
  (R3) and offers the sheet again with only those answers (Enter), or
  leaves them for `rep review` (n). The sheet opens with "the sheet is
  where you learn the answer". The end lists what to do next: `rep
  review` when answers wait, `rep drill` with the decks, `rep status`.
  Reason: the trial: "the retest happened and I don't think it's clear
  why"; seven self-graded answers were saved as ? and dropped out of the
  session unnoticed ("I forgot that I should take the time to grade
  myself"); and after the session the next step was unclear. On the
  person's question of when to study unseen material (the permit deck,
  manual unread): trying first and reading the key right after is how
  the sheet already works, and an attempt that fails before feedback
  improves learning of that feedback (the pretesting effect: Richland,
  Kornell and Kao 2009; Kornell, Hays and Bjork 2009). Getting it right
  in round 2, minutes later, is not yet evidence of learning; tomorrow's
  review is.
  Rejected: forbidding ? on a round's sheet (5: some answers truly cannot
  be judged then); grading them automatically as again (4: a grade the
  person did not give).
  Trade-off: one more prompt after a sheet with ? left; the person can
  always answer n.

D55. The run log: the program measures itself (M3). Approved by the
person on 2026-10-05 ("we have to measure", after Mike Acton).
  Choice: every run of rep appends one JSON line to
  <state directory>/runs.jsonl: the command and arguments, the time in
  each phase (read_library, load_events, fold, plan; read_library and
  stamp for stamp), counts (library items, events, planned items,
  stamped items), the duration, the exit code, the traceback when an
  exception ended the run, the source hash (D49) and the Python version.
  rep/src/rep/run_log.py does it and imports only the standard library
  and nothing from rep (a test enforces it), so it can be copied into
  another project unchanged. main() wraps the command; a failure to
  write the log is reported on stderr and changes nothing else.
  Reason: the events record what the person did; nothing recorded what
  rep did: how long its phases take at the person's real sizes (D42's
  100 ms target for stamp on save), how often each command runs, and
  every crash with its traceback, which the person would otherwise have
  to copy from the screen. Machine-local, beside the writer lock: it
  describes this machine's runs and must not sync.
  Rejected: structlog, OpenTelemetry or a hosted error tracker (5: each
  is code or a service for what one appended line does; the person
  offered two or three dependencies for this task, and none earns its
  place at this size); logging inside the events (3: one source per
  fact, D1; the events are the person's history, not the program's).
  Trade-off: about 2 ms per run (stamp on save: median 59 ms without,
  61 ms with, 30 runs each); a run that fails before the state directory
  is known (bad setup, bad arguments) is not logged; argparse already
  shows those.
  Revisit: the week's run log showing a phase worth optimizing.

D56. The week's instruments: notes, the body form, the report (M3).
Approved by the person on 2026-10-05.
  Choice: rep/shell/rep.sh and rep/shell/body.sh hold the shell side,
  sourced or symlinked by the person (their bashrc sources a directory),
  never written into ~/.bashrc: `rep-notes` opens today's section of
  <data root>/notes.md (the person's convention: "## YYYY-MM-DD", then
  "- Type: note" lines, types optional; templates/notes.md states it);
  `body` opens today's body form; `rep-screen` saves the tmux pane with
  its scrollback to a file; `rep-nvim` starts nvim with the plugin;
  `rep-week` and `rep-tour` run the tools. Functions are defined as
  `function name {`, which an alias of the same name cannot break. The
  nvim side loads on demand with `--cmd "luafile ..."` (nvim/load.lua,
  nvim/body.lua), so the person's config is untouched until lazy.nvim.
  Templates live in rep/templates, versioned with the code. The body form
  records what was drunk (ounces, ABV, kind) and the report converts it;
  the report flags clock times that read as a slip (bed at 12:00, a drink
  at 3:00). tools/week_report.py computes cards E1-E5, sessions by time
  of day, the body forms and the run log, asks the person about each
  card and seven fixed questions, and writes one file,
  <data root>/reports/week-<day>.md, with the week's notes copied in, for
  the next thread.
  Reason: in the trial, a function and an alias of one name broke the
  person's .bashrc; the first body form asked for standard drinks, which
  needs arithmetic and an ABV the person may not know ("is the amount the
  units of the standard, or the volume?"); "bed: 12:00" meant midnight;
  the screen was copied by hand from tmux. The next thread needs numbers
  and the person's answers in one place, gathered the same way each week.
  Rejected: a `rep report` command (6: a weekly tool in the program the
  person runs daily; a script costs no command surface); a database for
  the analysis, duckdb or polars (5: a week's events are a few thousand
  lines; the standard library reads them in milliseconds); writing into
  ~/.bashrc or ~/.config/nvim (3: the person's config is their own, and
  the first try broke it).
  Trade-off: the shell files assume bash, tmux and GNU date; the report's
  conversions use typical strengths and caffeine per kind, marked as
  estimates where used.

D57. The code tour: the person reviews the code through a form (M3).
Approved by the person on 2026-10-05.
  Choice: tools/code_tour.py writes a tour of the code as a form, opened
  in nvim by `rep-tour`: each stop names why it was chosen, gives its
  path:line for gF (larger blocks of a long function as sections), and
  three lines to answer: Understand (in one line, what does it do?),
  Style (what would you write differently?), Change (would you change it
  with confidence?). Stops: first every module's contract (its docstring),
  then three rankings taking turns: functions enforcing the most
  decisions (`PLAN.md D<n>`), the most lines changed in recent commits
  (git blame), and the longest; whole files for non-Python code. It reads
  Python with ast and imports nothing from rep, so it copies into another
  Python codebase unchanged.
  Reason: the person wants to gauge their understanding of the code and
  find style and guideline updates without reading it line by line. A
  form in nvim is how rep already asks for judgement (the grading sheet,
  the body form); the answers come back as a file the next thread reads.
  Understand answers compared with the docstrings show where the code or
  its comments fail to explain themselves. On rep itself the first tour
  shows run_command at 996 lines enforcing 26 decisions: one function
  holding every command (D13 chose that for one readable control flow;
  whether it still is readable is the question the tour puts to the
  person).
  Rejected: tree-sitter (6: language-independent, the right tool once a
  second language's code is toured; for Python alone it is a dependency
  that ast makes unnecessary); quickfix lists with :cnext (6: native
  navigation, but no place to write answers beside each stop); reading
  by git history alone (5: misses old code that matters).
  Trade-off: Python functions only, others as whole files; the rankings
  are proxies for importance, and the reader may skip any stop.

D58. Every command explains itself before it acts (M3). Approved by
the person on 2026-10-05, from going through the commands one by one.
  Choice: `rep --help` lists the commands in the order of the daily loop
  and ends with the loop and a first-time example (an item, and the add
  command). `rep today` names plain `rep`. `rep stamp` and `rep add` with
  nothing piped in (a terminal on stdin), and `rep add` without --stdin,
  print how to use them, with an example, and exit 2. `rep why` and `rep
  unsuspend` take an id or words from the question; several matches list
  their ids. An empty `rep review` says why it is empty and what to run.
  Reason: the person, going through the help in order, met each of these
  as a dead end: stamp waited silently for input until Ctrl-C; add said
  only that --stdin is required; "ID of what?"; "Nothing to review. What
  does that mean?"; and reached for `rep today` before reading that plain
  `rep` runs the session.
  Rejected: a separate tutorial command (5: help the person must know to
  ask for; the help and the empty states are where a first-time person
  already is); dropping stdin for a file argument (6: friendlier, but it
  changes D29's default deck, the items' citekey, and nvim's capture uses
  stdin; open for thread 4).
  Trade-off: longer help; a search that matches several items needs more
  words or an id.

D59. A session's screens give the reason for every number (M3). Revises
D51 and D54; approved by the person on 2026-10-05 ("peruse and address
all", after the first day on the real data root).
  Choice: plan_session returns its slots with P4's terms (started today,
  left today, room in the budget, waiting), and the start screen says
  them: "3 new: up to 10 new a day, 7 started earlier today (drills
  count); 241 more wait, deck by deck in the order added". The typing
  line says exact and numeric cards are checked as typed and a cue is
  enough only on self-graded ones. The start says stopping is fine
  (Ctrl-D grades what was answered). A retest round gives its counts and
  why: missed ones return until recalled once; new ones return for a
  second look, recalled after others came between. The sheet says how to
  jump between ungraded answers in plain nvim (/^? then n). With nothing
  planned, a day whose scheduled session completed says "Today's session
  is done", and why no new items remain. A drill of every deck lists its
  decks; one over 50 items gives its length and the --count way out
  before Enter, and every drill says its grades update the schedule and
  that stopping loses nothing. Deck lists name at most 3 decks. The
  limits are named constants in cli.py.
  Reason: on day one the person asked "why three new? why only permit?"
  (the drill had used 7 of the day's 10, and decks are introduced in the
  order added, D37: neither was shown); typed arithmetic under "a cue is
  enough"; started a 251-item drill with no sign of its length; read
  "nothing to practise" after finishing as if nothing had been done; and
  found "(D36)" meaningless.
  Rejected: a second copy of P4's arithmetic in the screen (4: two copies
  of a rule drift; the plan returns its own terms); a confirmation prompt
  for long drills (5: Enter already confirms; the length beside it is
  the missing fact); a configurable preset now (6: the right fix for "can
  I add more for tomorrow", but it is a decision about where settings
  live, for thread 4; `rep drill DECK --count N` covers it this week).
  Trade-off: the start screen grows by three lines; the long-drill line
  estimates at 10 seconds an answer.

D60. `rep status` says the clock and the day's plan; `rep where` says what
each place is for (M3). Revises D53; approved by the person on 2026-10-05.
  Choice: status adds the local time and what is left of the scheduling
  day ("now 13:35, 14 h 25 min left"); a session line, from plan_session
  itself: "done", "N due and M new waiting: rep", or "nothing planned";
  and the new-item allowance: up to new_per_day, how many started today
  (drills count), how many left, how many not yet seen. where adds the
  run log; each part of the data root (library, events, body, notes.md,
  reports, screens) with whether it exists and its purpose and writer;
  and the checkout this code runs from, with the whole paths of the shell
  helpers and the nvim loader, ready to copy.
  Reason: the person read "today 2026-10-05" without a time, reached for
  `rep today` to learn what was left, could not tell that ~/learning was
  rep's or what its folders held, and asked for the shell and Lua helpers
  to be part of what rep reports.
  Rejected: detecting whether the shell helpers are sourced (4: a child
  process cannot see its shell's functions; the paths are what it can
  give); a README written into the data root (5: rep never creates files
  in the data root it was not asked to, D28); renaming the default data
  root (5: it holds the body form and notes too, and REP_DATA_ROOT
  already chooses another).
  Trade-off: where prints the checkout only when installed editable from
  it, which is how rep is installed.

D61. The week report knows which week it is and is a form (M3). Revises
D56; approved by the person on 2026-10-05.
  Choice: the week is seven scheduling days from the first day practised
  (the first attempt), or from --start; after those, the next seven. Run
  before the week's last day, the report says "day N of 7 of week W
  (first to last)" and writes nothing, unless --partial, which reports
  the days so far. The file is reports/week-<first day>.md. The questions
  are no longer asked with input(): the report ends with a form, each
  card and question under its own heading with an `answer: ` line, and
  rep-week opens it in nvim. A rerun recomputes the numbers and keeps
  the answers already written (a card's answer by its id, E1..E5, since
  its numbers change). Each card's number is shown beside its target
  (section 8), called a target, not a prediction. The questions each ask
  for one concrete thing.
  Reason: on day one the report covered the seven days before it, which
  held nothing; "what explains this?" under each card left nothing to
  answer ("terrible"); questions asked one at a time could not be
  revised, and Ctrl-C ended in a traceback. Forms in nvim are already
  how the person grades, logs the body and reviews the code.
  Rejected: a calendar week, Monday to Sunday (5: the use week started
  on a Monday by chance; a week from the first practice holds for any
  start); keeping input() with Ctrl-C caught (4: fixes the traceback,
  not the one-shot answers); refusing to overwrite an answered report
  (6: safe, but a rerun for fresh numbers is wanted mid-week).
  Trade-off: an answer is kept up to its first blank line.

--------------------------------------------------------------------------------
## 6. Invariants (each enforced where it is introduced)
--------------------------------------------------------------------------------

I1  Every item has a unique ID across the library.            lint, load
I2  An ID with review history never changes.                  lint (orphans)
I3  rep never rewrites a file you author: it creates or appends. code review
    (The editor may change its own buffer through `rep stamp`.)
I4  Replaying the same events gives the same states.          property test
I5  Transplanted FSRS equals fsrs 6.3.2 with empty steps.     property test
I6  All stored times are UTC; day boundaries use local time
    and the configured start hour.                            unit tests
I7  One writer process per machine.                           lock
I8  Model output never reaches the library without passing
    through the inbox and `rep accept`.                       code path
I9  Stamp is idempotent and only inserts `id:` lines; on any
    parse problem it returns its input unchanged and exits
    non-zero.                                                 property test
I10 A broken item excludes only itself from a session.        unit test
I11 Every event line has format_version and a unique id.      check on write

--------------------------------------------------------------------------------
## 7. Milestones
--------------------------------------------------------------------------------

| Thread | Milestone | Delivers | Proves |
|---|---|---|---|
| 1 | docs | PLAN.md, STATUS.md, CONVENTIONS.md | applies cleanly |
| 1 | M0 | uv project, pyright strict, pytest, data root and local.toml resolution, device_id, `rep where`, `rep --help` | smoke test through the installed `rep` entry point (done, aef91db) |
| 1 | M1 | FSRS transplant, event record, fold | oracle property test, deterministic replay (done, b1aadfe) |
| 2 | M2 | parser (line-classifying state machine), checks, `rep stamp`, `rep add`, `rep lint`, NFC, citekey check, single-writer lock, events file loader and appender, `item_stamped` event | round-trip and stamp properties; checks red on injected violations; lock refuses a second writer (done, a64d51f) |
| 3 | M3 | planner, session loop, `session_start`/`session_end` events, scheduling days, `rep review`, `rep why`, `rep unsuspend`, the nvim plugin (D31-D44) | real session end to end |
| - | use week | daily use on one real reading; then a session porting drill/ | instrumentation (section 8) |
| after the use week | M3b | `rep stats`, `rep forecast`, the leech threshold, built on the use week's events; `rep due --brief` when E3's guardrail calls for the shell cue (D42) | the E-cards of section 8 answered from real data |
| 4 | M4 | LLM seam (manual, OpenRouter), inbox, `rep accept`, generation from source-notes | manual transport end to end |
| 5, 6 | M5, M6 | M5 concept layer and diagnostics; M6 tutor (Socratic), leech doctor, graph builder | ordered by the use week: prerequisite pain first means M5, comprehension pain first means M6 |
| later | - | generated items (drill/ port), optimizer, rich views, GUI renderer, cloze; research questions R1-R3 tested offline (section 9) | each by the section 9 protocol |

Every milestone ends with a smoke test through the real installed command,
because unit tests import functions directly and never touch that path.

--------------------------------------------------------------------------------
## 8. Instrumentation: how we find out
--------------------------------------------------------------------------------

The only way to know is to use it. Instruments are the event log itself
(kbd principle: metrics are passive), read by `rep stats`, plus a written
friction log in the person's existing friction module. Each experiment card
is written before the use week; Result and Decision are filled after.

Use-week content (the person, 2026-10-02): the planned reading, plus two
control decks. Country capitals: short answers with unambiguous keys, a
clean baseline for E4 and E5. The Massachusetts learner's permit test:
applied material with a deadline and an outside result, pass or fail
within weeks, against which rep's predictions can be checked. Its items
are written by the person from the RMV driver's manual (minimum
information); the real test is multiple choice, so free recall is the
harder condition.

E1 Capture friction
  Question: is capture cheap enough to happen while reading?
  Prediction: at least 5 items captured on each reading day.
  Measure: `item_stamped` events per day and per source; friction log notes.
  Guardrail: if under 2 a day, fix capture before M4.
  Result / Decision / Limit: after the use week.

E2 Commit before reveal
  Question: does committing make grades honest without making sessions a
  chore?
  Prediction: amendments in `rep review` under 15% of attempts; median
  session under 15 minutes.
  Measure: amends of attempts that already had a grade, over attempt
  events (from D45 a self-graded attempt gets its first grade by amend,
  which is grading, not correcting); session_start to session_end.
  Guardrail: if sessions are skipped, shorten the preset before changing the
  rule.

E3 Consistency
  Question: does the default session happen daily?
  Prediction: sessions on at least 5 of 7 days.
  Measure: days with a session_end of reason `completed`.
  Guardrail: if under 4, cut the preset length; check whether the shell cue
  helps.

E4 Scheduler calibration (weeks, not days)
  Question: is true recall near the 0.9 target?
  Measure: pass rate on due reviews older than 1 day, by interval bucket.
  Limit: needs a few hundred reviews before it means anything.

E5 Automaticity
  Question: which correct items are still slow?
  Measure: latency on passing attempts, per item, over time.
  Decision: slow items become candidates for more practice, not just spacing.

The events record everything these cards need from M3 on; the views that
read them (`rep stats`, `rep forecast`) are built in M3b, after the use
week, against its data (section 7). Amends on exact and numeric attempts
are classified by cause from the raw typed answer and the key (D41).

Always visible (from M3b): leeches (lapse count over a threshold), items edited after
their first review, suspended items, model-written versus self-written pass
rates (`by:`), forecast versus actual load, `rep due --brief` time once the
shell cue exists (target under 100 ms, D42).

--------------------------------------------------------------------------------
## 9. Open items and pending spikes
--------------------------------------------------------------------------------

- nvim key prefix: decided in M3, none in rep (D43). The person's lazy.nvim
  spec binds the keys; `<leader>p` is free on the person's machine
  (2026-10-01).
- Writer lock scope in a session: decided in M3, around each append (D32).
- `rep due --brief` and its snapshot: deferred to E3's guardrail (D42).
  If a snapshot is ever built: a small derived file in machine-local
  state, rebuilt from events when any events file is newer; never a
  source of truth.
- Research questions (deferred until the data can answer them). Each is a
  question about the memory model, not a feature; none changes the
  scheduler until it passes the protocol below.
  Protocol: after the use week, and only once the optimizer has enough
  history to run (D7), replay the person's log offline through FSRS-6
  and through the candidate, training on older reviews and testing on
  newer ones (a time-series split), and compare log loss, RMSE(bins) and
  AUC, the metrics of the open-spaced-repetition srs-benchmark. A
  candidate is adopted only if it predicts held-out recall better, and
  then as a decision in section 5 with its numbers. A single person's
  log is small: a candidate with more free parameters must win by more
  than noise, so prefer one added input over several.
  Data rule: rep records retrieval, nothing else. Other measurements
  (sleep from a wearable, a logged bedtime) stay in their own source and
  are joined to attempts by the exact UTC `at` when a question is
  tested; rep never copies them into the events (one source per fact,
  D1). So nothing needs recording in rep today, and no migration follows
  later: each attempt already carries `at`, `day` (D44),
  latency_milliseconds and the fingerprint.
  R1 Sleeps and hours. Elapsed days carry two quantities, time (decay)
     and nights of sleep (consolidation), and FSRS models them as one
     (D44; Diekelmann and Born 2010; Mazza et al. 2016). Does a model
     with sleeps between reviews and hours since the last review as
     separate inputs predict recall better than scheduling days? Needs:
     sleep times for the weeks being tested. The person's choice
     (2026-10-02): a manual log, one line per night (date, lights out,
     wake), in a plain file outside rep, started after the use week so
     its daily cost does not touch E2 and E3. No code.
  R2 Latency. FSRS ignores how long a correct answer took; E5 records it
     to find slow items. Does latency on a passing attempt predict the
     next recall beyond FSRS's state, for example a slow Good acting
     like a Hard? Needs: nothing new; testable on the log alone.
  R3 State at review time. Do time of day, or sleep in the night before
     the session, change recall on that day (performance) as opposed to
     retention later (learning; Soderstrom and Bjork)? This bears on when
     sessions should run rather than on the model. Needs: the R1 data.
  R4 First-showing grades. A new item's round-1 grade sets most of its
     first interval (section 3: Easy then Good gives 10 days, Good then
     Good 2). At an item's first scheduled review, is recall near the
     target retention (0.9) for each first grade, or are Easy first
     showings trusted too far? Needs: nothing new; group first reviews by
     the item's first grade and compare predicted with observed recall
     (the protocol's RMSE(bins), per group). Once there is enough history
     the optimizer refits the initial stabilities (D7); until then the
     grades keep the weight FSRS gives them (the person, 2026-10-02).
  R5 Alcohol. Does alcohol, by amount and by its timing relative to a
     session and to sleep, change recall (performance) or retention
     (learning)? Alcohol suppresses REM sleep mostly in the first half
     of the night (Ebrahim et al. 2013, a review), and one naturalistic
     study found better recall of material learned before drinking
     (Carlyle et al. 2017), so the time of each drink is the
     measurement, not a daily total. Needs: the body form below.
  The body form (the person's choice, 2026-10-03, started then, before
  the use week, which revises R1's later start). One file a day,
  <data root>/body/YYYY-MM-DD.md, named by the scheduling day (D44:
  rolls over at 04:00, so a drink at 01:30 belongs to the evening
  before), started from <data root>/templates/body.md by an nvim
  BufNewFile autocmd and opened by a shell alias (`body`). Fields are
  `key: value` lines, the library's own form: bed, wake, quality (1 to
  5), then one `drink: HH:MM N` (standard drinks) or `coffee: HH:MM N`
  line per occasion, and note. No rep code: rep never reads it until a
  question is tested (the data rule above). Extending it is editing the
  template; a day without a field simply lacks it. Trade-offs, chosen
  over an append-only log with automatic timestamps: when a value was
  written is not recorded (a value typed next morning looks like one
  typed live, as in any sleep diary), and a past day can be edited; a
  daily snapshot outside the synced folder would freeze past days if
  that ever matters.
- Slip and misconception labels, and flagging items in `rep review`:
  deferred until M5 or M6 asks for them (D41).
- Findings about neighbouring code (the person's nvim config, kbd.lua, the
  explorations .gitignore) are kept in FINDINGS.md, outside this plan, for
  the person's nvim config rework.
- FIRe-style credit with penalties versus synthetic FSRS reviews (M5, D19).
- Bib citekey cache: decided in M2, none. Lint reads the bib in 174 ms of
  about 0.55 s (section 3); a cache would add a second copy of the keys that
  can drift from the bib, to save that on a command run on demand. Revisit
  if lint takes over 1 s on the person's machine, or if rep.lua runs lint on
  every save.
- `@llm:<id>` sources (kbd's LLM-thread citations): an open hole. Today
  `@llm:867:p15` parses as citekey `llm`, location `867:p15`, and lint
  exempts citekey `llm` from the bib check. Its meaning waits on how model
  conversations are stored (files, or a local database from API use). No
  migration is needed when it is decided: the text is the source of truth
  and is re-parsed on every load.
- OpenRouter $10 credit: the person's call; tutor sessions need it more than
  generation does.
- Default preset numbers: set in M3 (D36), tuned by the use week. Leech
  threshold: M3b, with lapses counted as D38 says.
- The drill/ repo: attach in thread 4. The question is whether its
  generated exercises (arithmetic and the like) become a kind of rep item
  with `rep drill --count` as the control, or whether rep starts over with
  what the use week teaches; the person asked for both to be weighed.
- Languages (the person, 2026-10-05; the person speaks Spanish). rep
  should serve language learning. Open: typing in another alphabet
  (Russian, Greek) without switching the system keyboard, and showing
  the alphabet laid over the keyboard. First look: nvim ships keymaps
  (`:set keymap=russian-jcukenwin`, `greek_utf-8`; Ctrl-^ toggles), which
  serve answers written through Esc v with no code; the prompt itself
  (libedit) has no keymaps; a keyboard map could be printed on the card
  (D51's rule). Switching the Windows input method from WSL is outside
  what a terminal program controls.
- Multimodal (deferred by the person): images in questions (Windows
  Terminal draws sixel), audio prompts, spoken answers. Belongs with the
  session inside nvim (D47's revisit), after the use week.
- run_command (cli.py) is 996 lines enforcing 26 decisions (the first
  code tour, D57). D13 chose one function for one readable control
  flow; the person's tour answers decide whether it still is.

--------------------------------------------------------------------------------
## 10. Rejected, so no thread proposes them again
--------------------------------------------------------------------------------

SQLite as the source of truth; YAML, JSON or TOML for authoring; hand-written
slugs; opaque random IDs; node layer with item pools in v1; `requires:` in v1;
items inside kbd; model auto-grading; rich at M0; Anthropic SDK; llm library;
litellm; pydantic-ai; typer; prompt_toolkit; networkx; a lock or device name
inside the synced folder; hostname as device ID; one-shot or parallel builds;
an HTML/JS/CSS interface before the core works (the old drill/ lesson: too
many moving parts too early).

--------------------------------------------------------------------------------
## 11. Terms
--------------------------------------------------------------------------------

item          one question with its answer or criteria; the unit scheduled
attempt       one try at an item in a session, committed before reveal
grade         Again, Hard, Good or Easy: automatic Good or Again for an
              exact or numeric item, any of the four on the grading sheet
              (D45)
stability     FSRS: days until recall probability falls to 90%
difficulty    FSRS: how hard the item is to raise in stability (1 to 10)
retrievability FSRS: current probability of recall
lapse         a failed review of an item that had been learned
leech         an item that keeps lapsing; a sign of a bad item or a gap
fold          computing state by applying events in order
replay        running the fold over the whole history again, as rep does
              on every start, to rebuild every item's state; nothing is
              shown to the person again (I4)
preset        the session settings, one constant (D39)
plan          the ordered queue a session will serve, each slot with a reason
stamp         assigning IDs to items that lack one
inbox         proposals from a model, waiting for your triage
transport     how a prompt reaches a model: manual or HTTP
data root     the synced folder holding config, library, inbox, events, llm
device        one machine; owns exactly one events file
review debt   future reviews created by past new items
concept       (M5) a latent skill that items test
fringe        (M5) concepts whose prerequisites are all known
source item   an item as written, from the parser, before its meaning is
              checked (library.py SourceItem)
checked item  an item a session may use: built only when no error remains
              (library.py Item, PLAN.md D22)
problem       a finding about a file or item, as data: line, column,
              severity (error, warning; lint also lists notes) and message
capture       creating an item; recorded as an item_stamped event (E1)
budget        the most attempts a plan serves before the retry rounds:
              reviews first, then new items at new_item_cost each (D36)
scheduling day the local date an attempt belongs to, rolling over at
              day_start_hour; recorded on each attempt (D44)
round         one showing of each of its items; round 1 is the plan, each
              later round the items the last one's grades send back (D45)
grading sheet the text file a round's or review's answers are graded in,
              in $EDITOR: one read line per answer (D41, D45)
relearn gap   retired by D45: the rest of a round is the gap (D36)
retest        an item's showing in a round after the first, and its
              card's label: it returns by D36's criterion, which a new
              item meets on its first showing whatever its grade (D45)
fingerprint   a hash of what an item asks, stored on each attempt, so a
              later reader can tell whether the item changed since (D33)
session       one run of plain `rep`: a session_start event, attempts that
              carry its id, and a session_end unless it was abandoned (D40)
abandoned     a session with no session_end (terminal closed, crash)
pending       a decision approved before its code exists: "(M3, pending)"
              in its heading until the commit that enforces it (section 5)
history       the events about an item
refusal       a command declines, returns its input and writes nothing

--------------------------------------------------------------------------------
## 12. Revisions
--------------------------------------------------------------------------------

2026-09-30  Locked (commit c7a57f3).
2026-09-30  After M0 and M1, approved by the person: the writer lock moves to
            M2, its first caller; `rep where` added in M0; event field
            `format_version` instead of `v`; every event has an `id`; event
            kinds are added with their writers; an undo of an undo is
            refused. Also: D10 latency corrected to "prompt shown to answer
            committed" (it said "reveal to commit", which is backwards: the
            answer is revealed after the commit); clipboard route settled;
            facts measured during M0 and M1 added to section 3.
2026-09-30  M2 (thread 2), before any code depends on it: D20 records the
            grading keys section 9 left open (exact-match normalization,
            numeric tolerance syntax); the item leaves section 9; the float
            boundary failure is added to section 3. Awaiting the person's
            approval; the checks commit is the first code to depend on it.
2026-09-30  D20 approved by the person, provisionally, and marked critical:
            its grades are written without a person deciding. Added the two
            constraints on M3 that keep it revisable (raw `typed_answer`; a
            fingerprint covering the key) and the rule that a revision comes
            with a regrade or a stated reason.
2026-09-30  M2: bib citekey cache decided against (section 9, measured in
            section 3); `@llm:` sources recorded as an open hole, exempt
            from the bib check, by the person's decision.
2026-09-30  M2 landed (thread 2, 01ba3ea..a64d51f). Approved in the thread:
            D20, provisionally and marked critical; `@llm:` as an open
            hole; no bib cache. Made by the build and listed in STATUS.md
            as pending the person's approval: exit code 1 in the command
            contract; `rep add` files by citekey, `--to` and `--path`
            options; rep never creates the data root; the writer lock
            refuses rather than waits, and is held per command; how ids
            are formed (`q-` for questions of only common words, non-ASCII
            after NFKD dropped); errors versus warnings, and lint notes;
            `item_stamped` holds only the item id; locations not validated;
            `rep add` shows errors, not warnings.
2026-09-30  The person approved the nine build decisions above; they are
            numbered D21-D30 in section 5, with reasons and rejections, and
            the code names them where it enforces them. A test fails if
            code cites an undefined decision or an M2 decision has no
            enforcement point.
2026-09-30  End of thread 2: BUILDING.md added as a companion, holding the
            practice the thread used but no file stated (delivery and
            verification mechanics, tool hazards, code habits, working with
            the person). Section 11 gains the terms M2 introduced. The
            traceability test now finds the decisions it must see enforced
            from their headings, "(M2)" or later, instead of a fixed list.
2026-10-01  Thread 3 (M3), plan lock, before any M3 code. Approved by the
            person: M3 scope cut to the session path, with `rep stats`,
            `rep forecast`, the leech threshold and the due snapshot moved
            to M3b after the use week (section 7); review by editing a
            file, grades only; the preset as a constant; the eight open
            choices as recommended; the preset numbers (D36). Amended by
            the plan-lock pass and accepted: `u` amends instead of undoing
            (D35); typed answers through readline with a UTF-8 check
            (D34); review also lists older ungraded attempts (D41);
            `rep unsuspend` added (D42); the nvim integration becomes a
            lazy.nvim plugin directory with the keys in the person's
            config (D43). Also: a lapse redefined (D38), with the
            measurement that found the old rule wrong; the decisions are
            numbered D31-D43 and marked pending until enforced. Facts
            measured at the start of thread 3 added to section 3.
2026-10-01  Thread 3, after commit ef7b978, approved by the person before
            any dependent code: D44 (elapsed time in scheduling days,
            recorded on each attempt), found by measuring the fold against
            the plan's due rule; D36 and D38 revised to it (a lapse is now
            where the memory model applies its lapse formula); `rep due
            --brief` deferred to E3's guardrail (D42); :RepLint dropped
            for nvim's :make (D43). Section 9 records what a day stands
            for as an open question.
2026-10-02  Section 9: research questions R1-R3 (sleeps and hours,
            latency, state at review time), with one protocol (offline
            replay, time-series split, log loss, RMSE(bins) and AUC as the
            srs-benchmark measures them) and one data rule (other sources
            joined by `at`, never copied into the events). At the person's
            request, so the ideas wait for data instead of shaping the
            scheduler now.
2026-10-02  Thread 3, session loop: after a pseudo-terminal spike showed the
            standard library suffices (no terminal-interface dependency),
            D35 gains how keys are read (flush, then prompt) and what `e`
            records, and D34 turns readline's history off; both are
            refinements inside the approved decisions, listed here for the
            person's review.
2026-10-02  After the first real session (e43bf50, in the person's
            terminal), approved by the person before any code: D45, rounds
            with every answer typed and grading at the end of each round in
            a sheet in nvim (revising D8, D31, D35, D36, D41); D46, the
            display through the person's pyutils.terminal_output (revising
            D13), to be verified against pyutils' packaging before use.
            Section 8 gains the use-week content (two control decks);
            section 9 records R1's data source (a manual sleep log).
2026-10-02  Building D45's rounds and sheet: exact and numeric attempts are
            written with their automatic grade (an override in the sheet is
            a recorded correction), and E2 counts corrections as amends of
            attempts that already had a grade. Both keep the measures D20
            and E2 depend on; listed here for the person's review.
2026-10-02  Thread 3, the session in rounds (the CLI commit): D46 verified
            and enforced. Found while building and listed for the person's
            review: the rounds fold takes the last graded round plus one,
            since nothing in the events marks a saved sheet (D45 Built);
            sheet problems are shown above their lines; `rep review` waits
            for the lock (D41 Built); session_queue and relearn_gap are
            removed. Terms: round and grading sheet added; preset and
            budget brought up to date.
2026-10-02  Thread 3 continued in a new chat at f0c1b06: the first had grown
            too long to work in. BUILDING.md section 6 now says when to
            start a new chat and how to hand over. Approved by the person
            after reviewing f0c1b06 and its first real session: a new
            item's first-showing grade keeps the weight FSRS gives it
            (section 3, measured; R4 tests it once there is history); cards
            after round 1 are labelled "retest" instead of "again", which
            read as the grade Again (D45; the code follows in the next
            commit); a finished session's rounds are replayed counting only
            the amends before its session_end (D45 Replay, with the
            round_graded rejection that f0c1b06 had not recorded). Terms:
            replay added, grade brought up to date.
2026-10-02  The rest of M3 built in one turn at the person's request
            ("less ceremony"): `--version` imported lazily, `rep why`
            (facts only) and `rep unsuspend` (D42 Built), the nvim
            plugin and `rep where --data-root` (D43 Built). Listed for
            the person's review: capture opens the library file
            instead of piping a split to `rep add` (D43 Built);
            `rep why` does not explain an item left out by the plan's
            caps (D42 Built).
2026-10-03  After the person's review of M3 and their two control decks,
            before the trial session, approved by the person: D47 (vi
            mode at the prompt, rep turns it on itself), D48 (later
            rounds in a fresh order), D49 (session_start records offset,
            plan, source hash), D50 (`rep drill`, a deck is a library
            file), D51 (every screen states what it depends on); the
            multi-line sheet fix (D45); R5 alcohol and the body form
            (section 9), with the body form starting now. Measured for
            them: vi mode on uv's CPython and its arrow-key limit;
            same-day Goods leave stability unchanged (section 3); --tag
            permit would select 7 of 53 permit items.
2026-10-05  After the person's trial session (2026-10-04, on 0031-0037)
            and their notes, approved by the person: D52 (the same
            question twice: add refuses, lint warns), D53 (`rep status`),
            D54 (a session explains its rules where they act), D55 (the
            run log), D56 (the week's instruments: notes, body form,
            report, shell and nvim helpers outside the person's config),
            D57 (the code tour). Section 9 gains languages, multimodal,
            the drill/ question and run_command's size. M3 closes here;
            KICKOFF.md starts thread 4 after the use week.
