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
  counts as a lapse (D38).

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

D31. Session state is a fold over the session's events (M3, pending).
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
  Revisit: none expected.

D32. Writer lock during a session (M3, pending).
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

D33. Item fingerprint (M3, pending). Critical (D20 constraint 2).
  Choice: "f1:" followed by the first 16 hexadecimal digits of the sha256
  of the UTF-8 encoding of the JSON array [question, answer, criteria,
  check, attempt], taken from the checked Item (NFC values; the effective
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

D34. Typed answers: reading and grading (M3, pending). Critical (D20).
  Choice: a typed answer is read with input() and readline (libedit in
  uv's CPython, section 3), so arrow keys edit the line. A session refuses
  to start unless standard input decodes as UTF-8, and asks again when an
  answer holds a lone surrogate. typed_answer stores the string input()
  returned, before NFC or trimming (D20 constraint 1). The D20 comparison
  is one pure function in library.py beside NUMERIC_KEY_PATTERN: a change
  to the key syntax changes both, so they are one unit.
  Reason: in the terminal's line mode an arrow key enters escape bytes
  into the answer, a false Again on every exact item it touches; under a
  non-UTF-8 locale stdin decodes with surrogateescape (section 3) and the
  append would fail after the person had typed.
  Rejected: bytes from the terminal in line mode (5: no arrow keys, and
  the escapes reach the answer); prompt_toolkit (D13).
  Trade-off: the up arrow recalls earlier answers of the session; the
  locale must be UTF-8 (C.UTF-8 on the person's machine, section 3).
  Revisit: libedit behaving differently in the person's terminal.

D35. Session keys (M3, pending). Revises D8.
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
  Trade-off: every correction is visible in the history as an amend.
  Revisit: none expected.

D36. The plan (M3, pending). Revises D9's two caps into one budget.
  Choice: due items are error-free, unsuspended items with a memory state
  whose due_at is before the end of today's local day (day start hour,
  I6). Reviews are taken lowest retrievability first (ties: due_at, then
  id), at most `session_budget`. New items are error-free, unsuspended
  items with no graded review. New today = min(new_per_day minus items
  introduced today, (session_budget minus reviews) // new_item_cost),
  where introduced today means a first attempt of any kind today. Order:
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
  Revisit: E2 session length and E3 in the use week.

D37. Order of new items (M3, pending).
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

D38. What counts as a lapse (M3, pending).
  Choice: a lapse is an Again on an item's first graded attempt in a
  session, when the item had a memory state before that session. Only
  lapse_count changes; memory does not, so the oracle test is unaffected.
  Reason: section 11 defines a lapse as a failed review of a learned item.
  Successive relearning makes repeated Agains in one session normal; the
  old rule counted them (measured, section 3).
  Rejected: an Again at least one elapsed day after the last review (6:
  FSRS floors elapsed time to whole 24-hour periods, so a one-day item
  reviewed early the next morning could never lapse); every Again on an
  item with a memory state (3, the M1 rule).
  Trade-off: an item failed in two sessions on one day (two devices before
  a sync) counts two lapses.
  Revisit: the leech threshold (M3b).

D39. The preset is a constant (M3, pending). Revises D9.
  Choice: one default preset, a constant in the session code. Each
  session_start event records a copy (D40).
  Reason: config.toml would add a reader, validation and a file format for
  numbers tuned a handful of times; the event keeps the history
  self-describing either way.
  Rejected: config.toml now (6).
  Trade-off: tuning means editing a constant and committing; both devices
  get it through git.
  Revisit: a second preset, or two devices needing different values.

D40. Session events (M3, pending). Extends D10.
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

D41. `rep review` (M3, pending). Revises D8.
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

D42. `rep why`, `rep due --brief`, `rep unsuspend` (M3, pending).
  Choice: `rep why ID` prints where the item is (path:line), its state
  (stability, difficulty, retrievability now, due, reviews, lapses,
  suspended), its attempts with their grades and whether each attempt's
  fingerprint matches the item now, and whether and why today's plan
  includes it. `rep due --brief` computes the plan from a full replay and
  prints `<due> due, <new> new`, or nothing when both are 0; there is no
  snapshot. importlib.metadata is imported only for `--version`.
  `rep unsuspend ID` writes one unsuspend event (D10 has the kind; nothing
  wrote it).
  Reason: the scheduler must be inspectable during the use week. The
  snapshot is a cache whose need is measurable and not yet here, D25's
  argument against the bib cache. `--version` costs 39 of 57 ms of import
  on every command (section 3). Without unsuspend, a suspend is
  permanent.
  Rejected: the snapshot now (5); `rep stats` and `rep forecast` now (5:
  views designed against synthetic histories; they move to M3b, built on
  the use week's events).
  Trade-off: `rep due --brief` grows with the history, about 18
  microseconds per event (section 3), estimated to reach 100 ms near 4,000
  events.
  Revisit: `rep due --brief` over 100 ms through the installed command on
  the person's machine: build the snapshot then.

D43. nvim plugin (M3, pending). Revises D12.
  Choice: rep/nvim/ is a plugin directory on the runtime path:
  lua/rep/init.lua with setup(), the commands :RepCapture and :RepLint,
  and stamp on save for <data root>/library/*.md. Key bindings live in the
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
  can drift); replacing the whole buffer (4: loses cursor, marks, folds).
  Trade-off: no keys until the person adds the lazy spec; the commands
  work without it.
  Revisit: the person's nvim config rework.

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
| 3 | M3 | planner, session loop, `session_start`/`session_end` events, `rep review`, `rep why`, `rep due --brief` (full replay), `rep unsuspend`, the nvim plugin (D31-D43) | real session end to end; `rep due --brief` wall time |
| - | use week | daily use on one real reading; then a session porting drill/ | instrumentation (section 8) |
| after the use week | M3b | `rep stats`, `rep forecast`, the leech threshold, built on the use week's events; the `rep due --brief` snapshot only if it measured over 100 ms | the E-cards of section 8 answered from real data |
| 4 | M4 | LLM seam (manual, OpenRouter), inbox, `rep accept`, generation from source-notes | manual transport end to end |
| 5, 6 | M5, M6 | M5 concept layer and diagnostics; M6 tutor (Socratic), leech doctor, graph builder | ordered by the use week: prerequisite pain first means M5, comprehension pain first means M6 |
| later | - | generated items (drill/ port), optimizer, rich views, GUI renderer, cloze | - |

Every milestone ends with a smoke test through the real installed command,
because unit tests import functions directly and never touch that path.

--------------------------------------------------------------------------------
## 8. Instrumentation: how we find out
--------------------------------------------------------------------------------

The only way to know is to use it. Instruments are the event log itself
(kbd principle: metrics are passive), read by `rep stats`, plus a written
friction log in the person's existing friction module. Each experiment card
is written before the use week; Result and Decision are filled after.

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
  Measure: amend events over attempt events; session_start to session_end.
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
rates (`by:`), forecast versus actual load, `rep due --brief` time (target
under 100 ms).

--------------------------------------------------------------------------------
## 9. Open items and pending spikes
--------------------------------------------------------------------------------

- nvim key prefix: decided in M3, none in rep (D43). The person's lazy.nvim
  spec binds the keys; `<leader>p` is free on the person's machine
  (2026-10-01).
- Writer lock scope in a session: decided in M3, around each append (D32).
- `rep due --brief` snapshot: deferred with a measured trigger (D42). When
  built: a small derived file in machine-local state, rebuilt from events
  when any events file is newer; never a source of truth.
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
- The drill/ repo: attach in the session after M3.

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
grade         Again, Hard, Good or Easy; in session only Good or Again
stability     FSRS: days until recall probability falls to 90%
difficulty    FSRS: how hard the item is to raise in stability (1 to 10)
retrievability FSRS: current probability of recall
lapse         a failed review of an item that had been learned
leech         an item that keeps lapsing; a sign of a bad item or a gap
fold          computing state by applying events in order
preset        named session settings in config.toml
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
budget        the most attempts a plan serves before relearning: reviews
              first, then new items at new_item_cost each (D36)
relearn gap   how many other items come between two showings of an item
              in one session (D36)
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
