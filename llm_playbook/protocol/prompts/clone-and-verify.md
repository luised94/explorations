PROMPT: CLONE AND VERIFY
========================
date: 2026-07
type: prompt
scope: establishing a trustworthy working tree and a green baseline
BEFORE any change, for a thread that must EXECUTE against a live
tree. Not a transport mechanism.

WHEN TO USE THIS
  Use it when the thread must RUN something -- a test suite, a build,
  a server -- against a real working tree. Reading and reasoning does
  NOT need this: that is a pack (transport.md, ADR-032). Rule of
  thumb: reading is a pack, executing is a checkout.

  Five of the six steps below are VERIFICATION, not transport: pin an
  exact SHA, confirm the branch, establish a green baseline before
  changing anything, distinguish collection and import errors from
  failures, and declare an explicit file scope. Only step 1 resembles
  transport. ADR-021 retired the sparse-checkout BOOTSTRAP as a way
  of getting context INTO a chat; it did not retire checkouts, and it
  did not retire this discipline.

SETUP -- do this before anything else, and STOP if any check fails.
Report results back at each numbered step before proceeding.

0. PRECONDITIONS (fill these in; if any are still placeholders, STOP
   and ask):
   - REPO_URL  : <public, read-only clone URL>
   - BRANCH    : <BRANCH>
   - SHA       : <FULL-40-CHAR-SHA>   (not a prefix -- exact match)
   - SUBTREE   : <the directory this thread works in, if the repo is
                  a monorepo; otherwise the repo root>
   - BASELINE_TOTAL     : <N>  (expected green assertion count at SHA)
   - BASELINE_BREAKDOWN : <per-suite counts, so a shortfall names the
                           suite that moved rather than a total that
                           dropped>
   - SETUP_COMMANDS     : <the project's dependency-install and
                           test-run commands, and any runtime version
                           they require>
   These are FILLED IN PER THREAD from the project's STATUS.md, never
   hardcoded in this prompt -- that is what keeps the prompt from
   going stale, and what lets it be applied by hand or substituted by
   a small script.
   Assume NO push credentials: do not push, open PRs, or modify the
   remote in any way.

1. Clone at the pinned SHA. For a monorepo where the thread needs one
   subtree, a sparse checkout is appropriate:
     git clone --depth 1 --filter=blob:none --sparse REPO_URL /tmp/repo
     cd /tmp/repo && git sparse-checkout set SUBTREE && cd SUBTREE
   NOTE: cone-mode sparse-checkout ALSO materializes root-level FILES
   (README, .gitignore). That is expected and is not "the rest of the
   repo". Only top-level DIRECTORIES other than SUBTREE would be a
   problem.

2. Verify you have the right code, and report all four back before
   proceeding:
   - `ls -la /tmp/repo`      (confirm the only top-level DIRECTORY is
                              SUBTREE)
   - `ls -laR .`             (the working tree)
   - `git -C /tmp/repo rev-parse HEAD`             (must equal SHA)
   - `git -C /tmp/repo log -1 --oneline --decorate` (must show
                                                     HEAD -> BRANCH)
   If HEAD does not equal SHA, or the branch is wrong, STOP and say
   so. Do not work against the wrong tree.

3. Establish that the safety net is GREEN BEFORE changing anything.
   Run SETUP_COMMANDS, then the suite.
   Expected: BASELINE_TOTAL green, matching BASELINE_BREAKDOWN.
   If the baseline does NOT match on a clean clone at the verified
   SHA, STOP and report what failed. This includes COLLECTION,
   IMPORT, and SYNTAX errors, which count as red even where the
   runner reports them as "errors" rather than "failures" -- a suite
   that never ran is not a suite that passed. A mismatch is a problem
   with the STARTING STATE, not something to work around or patch
   silently. Wait for a go-ahead.
   PORTABILITY: if the project's scripts assume a specific shell,
   invoke them with that shell explicitly rather than relying on the
   default.

4. SCOPE for this thread. Do not touch files outside this list; if
   you think you need to, STOP and ask:
   - <the exact files and directories this thread may modify>
   - the project's decisions record is ALWAYS in scope for recording
     a decision, even when the code change is elsewhere.

WHY THE BASELINE COMES FIRST
  A green count established AFTER a change cannot distinguish "my
  change is fine" from "this was already broken". The baseline is the
  only thing that makes a later green count evidence of anything.
