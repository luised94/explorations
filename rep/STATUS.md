# rep: status

date: 2026-09-30
purpose: the numbers a build thread fills into clone-and-verify before it
changes anything. Updated in the same commit as the change it describes.

## Repository

REPO        ~/personal_repos/explorations (local; the rep/ subtree)
BRANCH      main
DOCS_SHA    c7a57f3856c7c5772b5113b1c67a81dca6160b47
M0_SHA      aef91db (full SHA to be recorded from `git rev-parse HEAD~1`
            after this commit lands)
SUBTREE     rep/

## Build state

| Milestone | State |
|---|---|
| docs (PLAN, STATUS, CONVENTIONS) | landed, c7a57f3 |
| M0 skeleton | landed, aef91db; verified on the person's machine |
| M1 FSRS transplant, event record, fold | this commit |
| M2 grammar, stamp, add, lint, writer lock | next |
| M3 sessions, review, views, rep.lua | pending |
| use week | pending |
| M4 language-model seam | pending |
| M5, M6 | pending, ordered by the use week |

## Baseline after this commit

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

## Measured after the plan was locked (fold into PLAN.md section 3 at its next edit)

- Clipboard: UTF-8 converted to UTF-16LE with a byte-order mark, piped into
  clip.exe, pastes correctly in a Windows browser (`cafe-with-acute lambda`
  arrived intact). This settles the D11 clipboard route for M4.
- The sandbox ran CPython 3.12.3; the person's machine runs uv-managed
  3.12.12. M0 passed on both.
- Transplant versus fsrs 6.3.2: exact floating-point equality of stability,
  difficulty and interval at every step, on 20,000 random histories (gaps
  mixing same-day, the one-day boundary and up to 400 days) and on 20,000
  fuzz cases. The suite runs 100 of each; the 20,000 run was one-off.
- Fold speed (sandbox): decoding and folding 36,500 attempt events over
  2,000 items took 0.66 s (decode 0.25 s, fold 0.41 s). Inside D1's 1 s
  revisit trigger, but `rep due --brief` (target under 100 ms, PLAN.md
  section 8) cannot replay the full history: M3 needs a derived snapshot for
  that command, rebuilt from events, never the source of truth.
- The property test on canonical times found that glibc strftime writes year
  999 as "999", breaking fixed width; the formatter now uses isoformat and
  asserts its postcondition.

## Deviations from PLAN.md, surfaced for approval

From M0 (no answer yet):
- The single-writer lock moves from M0 to M2, the first commit with a writer.
- `rep where` was added in M0 as its observable and smoke-test target.

From M1:
- The version field is `format_version`, not `v` as written in D10: the
  naming rule forbids single-letter names, and the field is data a person
  will read in the events file.
- Every event carries an `id`. D10 did not list it, but amend and undo need
  a target to point at, so D10 implied it.
- Only the five kinds the fold reads exist so far (attempt, amend, undo,
  suspend, unsuspend). session_start, session_end and item_stamped are
  added with their writers (M2, M3), so their fields are designed against a
  real caller.
- The fold reports problems (dangling references, undo of an undo,
  duplicate ids) as data and keeps going, instead of refusing the history.
  An undo of an undo is refused: the session never needs redo, and allowing
  it makes "is this event in effect" depend on a chain.

## Known blind spots

- The sandbox runs Linux, not WSL2. M0 has since run on WSL2; M1 has not.
- Nothing yet exercises concurrent first runs; the hard-link creation is
  correct by construction, not by test.
- No events file is read or written yet: decode and encode are tested on
  strings. The file loader (truncated last line, several device files) lands
  with its first caller.
