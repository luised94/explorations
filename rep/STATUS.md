# rep: status

date: 2026-10-01
purpose: the numbers a build thread fills into clone-and-verify before it
changes anything. Updated in the same commit as the change it describes.

## Repository

REPO        ~/personal_repos/explorations (local; the rep/ subtree)
BRANCH      main
SUBTREE     rep/
COMMITS     c7a57f3856c7c5772b5113b1c67a81dca6160b47  docs: plan of record
            aef91db0f8812cd6553f0881ec2f3ea601b2b4e5  M0 skeleton
            b1aadfe                                   M1 memory model and fold
            ae2a8e3a5e797718106b4e3b17c8e2aa8298f72f  docs: fold M0/M1 revisions
                                                      (thread 2 started here)
            01ba3ea  docs: D20 grading keys
            47f08d0  library: parser and canonical writer
            f680eec  docs: D20 approved provisionally, critical
            3e0224a  library: item checks, typed Item record
            97bf17b  library: id generation and stamp
            48b4bf0  storage: events files, writer lock, item_stamped
            678269a  cli: rep stamp
            41962f6  cli: rep add
            a64d51f  cli: rep lint, no bib cache
            70e41b4  docs: close M2
            53755a2  docs: number M2 decisions D21-D30, trace them in code
            cf5e5f2  docs: BUILDING.md, terms, milestone-marked tracing
                     (thread 3 started here)
            57559e3  build: track uv.lock
            5fad124  docs: lock M3, decisions D31-D43 pending
            f3d3681  docs: FINDINGS.md, neighbouring code
            ef7b978  library: fingerprint and typed-answer grading
            92af31e  docs: D44 scheduling days, D36/D38/D42/D43 revised
            d847984  docs: research questions R1-R3
            40932b8  events: scheduling days, lapse rule
            2c82e2b  session: plan and queue, pure
            e43bf50  cli: plain `rep` runs a session (first loop)
            6e7e5ab  docs: D45 rounds, D46 display
            759c981  pyutils: terminal_output fixes F18-F20
            bd5f203  session: rounds and the grading sheet, pure
            (this commit)  cli: the session in rounds, `rep review`
BASE_SHA    thread 3 started from cf5e5f2c1d839f5642dc2485945ff37f9f1e526e.
            The base for thread 4 is set when M3 closes.

## Build state

| Milestone | State |
|---|---|
| docs (PLAN, STATUS, CONVENTIONS) | landed, c7a57f3 |
| M0 skeleton | landed, aef91db; verified on the person's machine |
| M1 FSRS transplant, event record, fold | landed, b1aadfe; verified on the person's machine |
| M2 grammar, stamp, add, lint, writer lock, events loader | landed, 01ba3ea..a64d51f; each commit verified on the person's machine; stamp and add run there against a throwaway data root |
| M3 sessions, review, why, due, nvim plugin | in progress (thread 3): sessions in rounds and `rep review` built; D42 and D43 pending |
| use week | pending |
| M3b stats, forecast, leech threshold (snapshot if measured slow) | after the use week |
| M4 language-model seam | pending |
| M5, M6 | pending, ordered by the use week |

## Baseline

BASELINE_TOTAL      263 passed
BASELINE_BREAKDOWN  tests/test_cli.py            2
                    tests/test_events.py        51
                    tests/test_library.py      125
                    tests/test_machine.py       16
                    tests/test_memory_model.py   3
                    tests/test_session.py       23
                    tests/test_smoke.py         27
                    tests/test_storage.py       15
                    tests/test_traceability.py   1
TYPE_CHECK          pyright strict: 0 errors, 0 warnings
SETUP_COMMANDS      cd rep && uv lock --check && uv sync
                    uv run pytest | tail -1      (prints "263 passed in ...")
                    uv run pyright | tail -1
                    uv tool install --editable .   (puts `rep` on PATH)
                    pyproject.toml already adds -q; a second -q hides the
                    count line, so do not add one.
RUNTIME_DEPENDENCY  pyutils, the sibling ../pyutils (PLAN.md D46): rep's
                    install needs explorations/pyutils beside rep/
TOOL_VERSIONS       uv 0.11.1, uv_build >=0.11.1,<0.12.0, CPython 3.12
                    (3.12.12 on the person's machine, 3.12.13 in the build
                    sandbox), pytest 9.1.1, pyright 1.1.414,
                    hypothesis 6.168.3, fsrs 6.3.2 (dev only: the oracle)
BISECT              every commit 01ba3ea..a64d51f passes pytest and pyright
                    on its own (48, 58, 58, 100, 112, 125, 128, 153, 156)

uv.lock is a generated file: it is never a patch. Regenerate it with
`uv lock` in rep/ and confirm it with `uv lock --check`. It is tracked
since 57559e3: the explorations root .gitignore ignores it (line 20,
`uv.lock`), and `!uv.lock` in rep/.gitignore re-includes it (PLAN.md
section 3).

## Deviations pending approval

None. The nine from M2 were approved by the person and are decisions
D21-D30 in PLAN.md section 5, each with its reason, what was rejected and
the trade-off.

## Tracing a decision to the code

Code names the decision it enforces as "PLAN.md D<n>". To list every
enforcement point with its current line:
    grep -rn "PLAN.md D" rep/src
tests/test_traceability.py fails if code cites a decision PLAN.md does not
define, if a decision whose heading is marked (M2) or later has no
enforcement point (today D20-D30), or if a decision marked
"(M<n>, pending)" already has one (today D42 and D43 are pending).

## Known blind spots

- Nothing yet exercises concurrent first runs; the hard-link creation is
  correct by construction, not by test. (from M0)
- Durability after a crash (fsync, the newline repair before an append)
  is tested by construction and by writing fragments by hand, not by
  killing a writer mid-write.
- `rep stamp` and `rep add` read the whole library on every call, even a
  save with nothing to stamp: 27 ms at 2,000 items, 130 ms at 10,000
  (PLAN.md section 3). Skipping the read when every item already has an id
  is a small change, not made.
- Problems the fold finds (duplicate event ids, bad undo or amend targets)
  are printed by lint without a location; locating them needs the fold to
  return structured problems, a change to M1 code.
- The nvim plugin does not exist yet, so the stamp, add and lint contracts
  are tested from Python and the shell, never from nvim. D43 closes this:
  the plugin is tested headless in the sandbox.
- The session in rounds is tested under a pseudo-terminal in the sandbox
  (tests/test_smoke.py, with a scripted editor), not yet in the person's
  terminal (Windows Terminal on WSL2) with nvim as the editor; a real
  session on a throwaway data root checks it.
- The flush before each answer line (D35, kept by D45) is
  timing-dependent: no deterministic test catches a regression; the order
  is fixed in the code and explained there.
- Ctrl-C while the editor is open is not tested. nvim and vim read it as
  a key in raw mode, so no signal reaches rep; an editor that leaves
  signals on would end the session and lose that sheet's grades, its
  answers waiting for `rep review`.
- A wrong source for an attempt's `day` would not show within one
  session's tests (all its attempts share a day); the fold's day tests
  cover reading it.
- At the end of M2 the kbd bib on disk still had 13 malformed keys (a
  stale export); they are fixed in Zotero and wait for a re-export.
- Hypothesis: `from_regex` and category-filtered character strategies are
  slow on a fresh checkout (1.75 s for the first); the library tests use
  sampled alphabets instead.

## Thread 3 (M3) series

The plan is locked (PLAN.md section 12, 2026-10-01); implement mode.
Each code commit changes the markers of the decisions it enforces from
"(M3, pending)" to "(M3)".

| Commit | Concern | Decisions |
|---|---|---|
| 57559e3 | build: track uv.lock | - |
| 5fad124 | docs: lock M3 | D31-D43 recorded, pending |
| f3d3681 | docs: FINDINGS.md (neighbouring code) | - |
| ef7b978 | library: fingerprint, typed-answer grading | D33, D34 (grading) |
| 92af31e | docs: D44, scheduling days; D36, D38, D42, D43 revised | D44 recorded, pending |
| d847984 | docs: research questions R1-R3 and their protocol (PLAN.md section 9) | - |
| 40932b8 | events: `day` on attempts, elapsed and due by day, lapse rule | D44, D38 |
| 2c82e2b | session: plan and queue fold, both pure; first-attempt day and the shared effective-event code, at their consumers (BUILDING.md section 2) | D31, D35 (queue rule), D36, D37, D39 |
| e43bf50 | cli: plain `rep` runs a session (after the terminal spike), with session_start and session_end, added with their writer as D10 requires; the library-wide load and checks move out of lint here, at their second caller (BUILDING.md section 2) | D32, D34 (reading), D35, D40 |
| 6e7e5ab | docs: D45 (rounds, grading sheet), D46 (pyutils display), use-week decks, R1 log; FINDINGS F18-F20 | D45, D46 recorded, pending |
| 759c981 | pyutils: terminal_output fixes for F18-F20, before rep draws through it (outside rep/; its own tests) | - |
| bd5f203 | session: rounds fold and the grading sheet (render and read), pure; the queue stays until the loop moves over | D45, D41 (sheet) |
| this commit | cli: the session in rounds, `rep review` on the same sheet, pyutils display; session_queue and relearn_gap removed; the rounds fold bounded by the last graded round (R5, found by the terminal test) | D45, D46, D41 |
| then | cli: `rep why`, `rep unsuspend`, `rep where --data-root`, `--version` imported lazily | D42 |
| then | nvim plugin, tested headless | D43 |
| last | docs: close M3, kickoff for thread 4 | - |

Binding on M3 (D20, critical): `typed_answer` stores the raw typed text
before any normalization (D34); the fingerprint covers the question,
`A:`, `criteria:`, `check:` and the attempt kind (D33).
