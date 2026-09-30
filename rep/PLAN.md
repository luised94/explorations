# rep: plan of record

date: 2026-09-30
status: LOCKED. Design review fires only when work contradicts or exceeds this
file. A change to a decision edits this file in its own commit, with the
reason, before any code depends on it. Revisions are listed in section 12.
companions: CONVENTIONS.md (the library grammar), STATUS.md (where the build
is, and how to verify it)

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
| 2 | M2 | parser (line-classifying state machine), checks, `rep stamp`, `rep add`, `rep lint`, NFC, citekey check, single-writer lock, events file loader and appender, `item_stamped` event | round-trip and stamp properties; checks red on injected violations; lock refuses a second writer |
| 3 | M3 | planner, session loop, `session_start`/`session_end` events, `rep review`, `rep why`, `rep forecast`, `rep stats`, `rep due --brief` (from a derived snapshot), rep.lua | real session end to end; `rep due --brief` wall time |
| - | use week | daily use on one real reading; then a session porting drill/ | instrumentation (section 8) |
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

Always visible: leeches (lapse count over a threshold), items edited after
their first review, suspended items, model-written versus self-written pass
rates (`by:`), forecast versus actual load, `rep due --brief` time (target
under 100 ms).

--------------------------------------------------------------------------------
## 9. Open items and pending spikes
--------------------------------------------------------------------------------

- nvim key prefix for rep.lua (M3). `<Space>r` is taken.
- `rep due --brief` snapshot (M3): a small derived file in machine-local
  state, rebuilt from events when any events file is newer; never a source
  of truth.
- FIRe-style credit with penalties versus synthetic FSRS reviews (M5, D19).
- Bib citekey cache keyed on file time, only if lint feels slow (M2).
- OpenRouter $10 credit: the person's call; tutor sessions need it more than
  generation does.
- Leech threshold and default preset numbers: set in M3, tuned by the use
  week.
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
