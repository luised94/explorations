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
            (this commit)                             docs: fold M0/M1 revisions
                                                      into PLAN.md
BASE_SHA    for the next thread: this commit's full SHA, from
            `git rev-parse HEAD` after it lands

## Build state

| Milestone | State |
|---|---|
| docs (PLAN, STATUS, CONVENTIONS) | landed, c7a57f3 |
| M0 skeleton | landed, aef91db; verified on the person's machine |
| M1 FSRS transplant, event record, fold | landed, b1aadfe; verified on the person's machine |
| M2 grammar, stamp, add, lint, writer lock, events loader | next (thread 2) |
| M3 sessions, review, views, rep.lua | pending |
| use week | pending |
| M4 language-model seam | pending |
| M5, M6 | pending, ordered by the use week |

## Baseline (unchanged by this documentation-only commit)

BASELINE_TOTAL      48 passed
BASELINE_BREAKDOWN  tests/test_events.py        26
                    tests/test_machine.py       16
                    tests/test_memory_model.py   3
                    tests/test_smoke.py          3
TYPE_CHECK          pyright strict: 0 errors, 0 warnings
SETUP_COMMANDS      cd rep && uv lock --check && uv sync
                    uv run pytest
                    uv run pyright
                    uv tool install --editable .   (puts `rep` on PATH)
TOOL_VERSIONS       uv 0.11.1, uv_build >=0.11.1,<0.12.0, CPython 3.12,
                    pytest 9.1.1, pyright 1.1.414, hypothesis 6.168.3,
                    fsrs 6.3.2 (dev only: the oracle)

uv.lock is a generated file: it is delivered whole, never as a patch, and
`uv lock --check` confirms it matches pyproject.toml.

## Deviations pending approval

None. The six from M0 and M1 were approved and are recorded in PLAN.md
section 12.

## Kickoff for thread 2 (M2)

Attach a pack of rep/ at BASE_SHA. First message:
  "Read rep/PLAN.md, rep/CONVENTIONS.md and rep/STATUS.md. Run the
   clone-and-verify baseline (48 passed, pyright 0 errors) before changing
   anything. Then build M2 as PLAN.md section 7 lists it, one commit per
   turn, in implement mode."
Co-load set for M2: PLAN.md (D1-D5, D10, D14, I1-I3, I7, I9-I11),
CONVENTIONS.md, src/rep/machine.py (paths, device id, alphabet),
src/rep/events.py (record types, encode/decode), src/rep/cli.py.
Open choices M2 must make and record: exact-match normalization and numeric
tolerance syntax; whether to cache bib citekeys (only if lint is slow).

## Known blind spots

- Nothing yet exercises concurrent first runs; the hard-link creation is
  correct by construction, not by test.
- No events file is read or written yet: decode and encode are tested on
  strings. The loader (truncated last line, several device files) is M2.
