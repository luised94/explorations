# rep: status

date: 2026-09-30
purpose: the numbers a build thread fills into clone-and-verify before it
changes anything. Updated in the same commit as the change it describes.

## Repository

REPO        ~/personal_repos/explorations (local; the rep/ subtree)
BRANCH      main
BASE_SHA    c7a57f3 (docs commit; full 40-character SHA to be recorded from
            `git rev-parse HEAD` on the person's machine)
SUBTREE     rep/

## Build state

| Milestone | State |
|---|---|
| docs (PLAN, STATUS, CONVENTIONS) | landed, c7a57f3 |
| M0 skeleton | this commit |
| M1 FSRS transplant and fold | next |
| M2 grammar, stamp, add, lint, writer lock | pending |
| M3 sessions, review, views, rep.lua | pending |
| use week | pending |
| M4 language-model seam | pending |
| M5, M6 | pending, ordered by the use week |

## Baseline after this commit

BASELINE_TOTAL      19 passed
BASELINE_BREAKDOWN  tests/test_machine.py  16
                    tests/test_smoke.py     3
TYPE_CHECK          pyright strict: 0 errors, 0 warnings
SETUP_COMMANDS      cd rep && uv lock --check && uv sync
                    uv run pytest
                    uv run pyright
                    uv tool install --editable .   (puts `rep` on PATH)
TOOL_VERSIONS       uv 0.11.1, uv_build >=0.11.1,<0.12.0, CPython 3.12,
                    pytest 9.1.1, pyright 1.1.414 (pinned by uv.lock)

uv.lock is a generated file: it is delivered whole, never as a patch, and
`uv lock --check` confirms it matches pyproject.toml.

## Measured after the plan was locked (fold into PLAN.md section 3 at its next edit)

- Clipboard: UTF-8 converted to UTF-16LE with a byte-order mark, piped into
  clip.exe, pastes correctly in a Windows browser (`cafe-with-acute lambda`
  arrived intact). This settles the D11 clipboard route for M4.
- The sandbox ran CPython 3.12.3; the person's machine runs uv-managed
  3.12.12.

## Deviations from PLAN.md, surfaced for approval

- The single-writer lock moves from M0 to M2, the first commit with a
  writer (`rep add` appends to the library and writes item_stamped events).
  In M0 it would be code with no caller.
- `rep where` was added in M0: it prints every resolved path and the device
  ID, the observable for M0 and the target of the smoke test.

## Known blind spots

- The sandbox runs Linux, not WSL2. Behavior of os.link on the person's
  ext4 home is expected to match but is only confirmed once `rep where`
  runs there.
- Nothing yet exercises concurrent first runs; the hard-link creation is
  correct by construction, not by test.
