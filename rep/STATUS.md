# rep: status

date: 2026-09-30
purpose: the numbers a build thread fills into clone-and-verify before it
changes anything. Updated in the same commit as the change it describes.

## Repository

REPO        ~/personal_repos/explorations (local; the rep/ subtree)
BRANCH      the person's working branch (not recorded yet)
BASE_SHA    624f6a8127f1274670bd73488cdc66e7a24cf25a (clean, before rep/)
SUBTREE     rep/

## Build state

| Milestone | State |
|---|---|
| docs (PLAN, STATUS, CONVENTIONS) | this commit |
| M0 skeleton | next |
| M1 FSRS transplant and fold | pending |
| M2 grammar, stamp, add, lint | pending |
| M3 sessions, review, views, rep.lua | pending |
| use week | pending |
| M4 language-model seam | pending |
| M5, M6 | pending, ordered by the use week |

## Baseline

BASELINE_TOTAL      0 (no code yet)
BASELINE_BREAKDOWN  none
SETUP_COMMANDS      none yet; M0 defines them:
                      cd rep && uv sync
                      uv run pytest
                      uv run pyright
                    runtime: CPython 3.12 (uv-managed)

## Known blind spots

- Nothing is exercised on the person's machine until M0 lands; the sandbox
  runs Linux, not WSL2.
