# rep: status

date: 2026-09-30
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
            (this commit)                             docs: close M2
BASE_SHA    for the next thread: this commit's full SHA, from
            `git rev-parse HEAD` after it lands

## Build state

| Milestone | State |
|---|---|
| docs (PLAN, STATUS, CONVENTIONS) | landed, c7a57f3 |
| M0 skeleton | landed, aef91db; verified on the person's machine |
| M1 FSRS transplant, event record, fold | landed, b1aadfe; verified on the person's machine |
| M2 grammar, stamp, add, lint, writer lock, events loader | landed, 01ba3ea..a64d51f; each commit verified on the person's machine; stamp and add run there against a throwaway data root |
| M3 sessions, review, views, rep.lua | next (thread 3) |
| use week | pending |
| M4 language-model seam | pending |
| M5, M6 | pending, ordered by the use week |

## Baseline (unchanged by this documentation-only commit)

BASELINE_TOTAL      156 passed
BASELINE_BREAKDOWN  tests/test_cli.py            1
                    tests/test_events.py        28
                    tests/test_library.py       72
                    tests/test_machine.py       16
                    tests/test_memory_model.py   3
                    tests/test_smoke.py         21
                    tests/test_storage.py       15
TYPE_CHECK          pyright strict: 0 errors, 0 warnings
SETUP_COMMANDS      cd rep && uv lock --check && uv sync
                    uv run pytest | tail -1      (prints "156 passed in ...")
                    uv run pyright | tail -1
                    uv tool install --editable .   (puts `rep` on PATH)
                    pyproject.toml already adds -q; a second -q hides the
                    count line, so do not add one.
TOOL_VERSIONS       uv 0.11.1, uv_build >=0.11.1,<0.12.0, CPython 3.12
                    (3.12.12 on the person's machine, 3.12.13 in the build
                    sandbox), pytest 9.1.1, pyright 1.1.414,
                    hypothesis 6.168.3, fsrs 6.3.2 (dev only: the oracle)
BISECT              every commit 01ba3ea..a64d51f passes pytest and pyright
                    on its own (48, 58, 58, 100, 112, 125, 128, 153, 156)

uv.lock is a generated file: it is delivered whole, never as a patch, and
`uv lock --check` confirms it matches pyproject.toml. The thread-2 pack had
no uv.lock; `uv lock --check` passed on the person's machine. Include it in
the next pack.

## Deviations pending approval

Made while building M2, where PLAN.md and CONVENTIONS.md were silent or
left the choice open. Each is recorded where it lives; approve or send back.

1. Exit code 1 joins the command contract: the input has problems (stamp,
   add) or lint found an error. 2 stays "rep cannot run". (cli.py)
2. `rep add` files items under `library/<citekey>.md` from their shared
   source; `--to NAME` otherwise. `rep stamp --path` names the buffer in
   messages. (cli.py)
3. rep never creates the data root; stamp, add and lint ask for
   `mkdir -p` instead, so a mistyped REP_DATA_ROOT cannot create a folder
   that never syncs. (storage.py, cli.py)
4. The writer lock refuses rather than waits, and each command holds it
   only while it writes. `rep stamp` with the lock held stamps nothing,
   since ids without their item_stamped events would drop E1 data; the
   next save retries. (storage.py S5; the session question is in PLAN.md
   section 9)
5. Ids: `q-` form also for questions of only common words; non-ASCII
   dropped after NFKD; English common-word list only. (CONVENTIONS.md IDs)
6. Errors exclude an item from sessions and are limited to what breaks a
   session; source, tags, unknown fields, citekeys and id form are
   warnings. Lint lists `?:` lines as notes. (CONVENTIONS.md)
7. `item_stamped` holds only the item id; its source is read from the
   library when capture is measured. (events.py)
8. Locations are not validated beyond having no spaces. (CONVENTIONS.md)
9. `rep add` prints errors, not warnings; warnings appear in lint.

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
- rep.lua does not exist yet, so the stamp, add and lint contracts are
  tested from Python and the shell, never from nvim.
- At the end of M2 the kbd bib on disk still had 13 malformed keys (a
  stale export); they are fixed in Zotero and wait for a re-export.
- Hypothesis: `from_regex` and category-filtered character strategies are
  slow on a fresh checkout (1.75 s for the first); the library tests use
  sampled alphabets instead.

## Kickoff for thread 3 (M3)

Attach a pack of rep/ at BASE_SHA, including uv.lock. First message:
  "Read rep/PLAN.md, rep/CONVENTIONS.md and rep/STATUS.md. Run the
   clone-and-verify baseline (156 passed, pyright 0 errors) before changing
   anything. Then build M3 as PLAN.md section 7 lists it, one commit per
   turn, in implement mode."
Co-load set for M3: PLAN.md (D8, D9, D10, D12, D20 with its two
constraints on M3, I4, I6, I7, I10, section 8, section 9), CONVENTIONS.md,
src/rep/library.py (Item, check_source_item, NUMERIC_KEY_PATTERN),
src/rep/events.py, src/rep/memory_model.py, src/rep/storage.py,
src/rep/cli.py.
Binding on M3 (D20, critical): `typed_answer` stores the raw typed text
before any normalization; the item fingerprint covers at least the
question, `A:`, `criteria:` and `check:`.
Open choices M3 must make and record: the nvim key prefix; the writer
lock's scope during a session (section 9); the fingerprint's exact
definition; the exact and numeric comparison (D20 fixes the rule);
leech threshold and default preset numbers; the `rep due --brief`
snapshot.
