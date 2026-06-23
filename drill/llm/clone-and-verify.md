SETUP -- do this before anything else, and STOP if any check fails.
Report results back to me at each numbered step before proceeding.

0. PRECONDITIONS (fill these in; if any are still placeholders, STOP and ask me):
   - REPO_URL : <https://github.com/YOURUSER/YOURREPO.git>   (public, read-only)
   - BRANCH   : <BRANCH>
   - SHA      : <FULL-40-CHAR-SHA>      (not a prefix -- exact match required)
   You have NO push credentials: do not push, open PRs, or modify the remote
   in any way.

1. Sparse-clone just the drill/ directory:
   git clone --depth 1 --filter=blob:none --sparse REPO_URL /tmp/repo
   cd /tmp/repo && git sparse-checkout set drill && cd drill
   NOTE: cone-mode sparse-checkout also materializes ROOT-level files
   (README.md, .gitignore). That is expected -- it is NOT "the rest of the
   repo." Only top-level *directories* other than drill/ would be a problem.

2. Verify you have the right code, and report all four back to me before
   proceeding:
   - `ls -la /tmp/repo`     (confirm the only top-level DIRECTORY is drill/)
   - `ls -laR .`            (the drill/ working tree)
   - `git -C /tmp/repo rev-parse HEAD`            (must equal SHA exactly)
   - `git -C /tmp/repo log -1 --oneline --decorate` (must show HEAD -> BRANCH)
   If HEAD != SHA or the branch is wrong, STOP and tell me -- do not work
   against the wrong tree.

3. Establish the safety net is green BEFORE you change anything:
   - uv sync --group test
   - npm install jsdom --no-save          (needs Node 18+; verify `node -v`)
   - bash tests/run.sh
   Expected baseline: 159 assertions green -- backend 84 (logic 35, http 40,
   db 7, property 2), frontend 75 (6/21/19/23/6), ending "ALL GREEN".
   If the baseline is NOT 159 green on a clean clone at the verified SHA, STOP
   and report what failed -- including collection/import/syntax errors, which
   count as red even though pytest reports "errors" not "failures." That is a
   problem with the STARTING STATE (a bug in the pinned commit), not something
   to work around or patch silently. Wait for my go-ahead.
   PORTABILITY: tests/run.sh and helpers assume bash. If a command of mine
   uses bash-only syntax (e.g. ${PIPESTATUS[...]}), invoke it with `bash`, not
   `sh`; `$?` on the immediately-following line is the portable fallback.

SCOPE for this thread (do not touch files outside this list; if you think you
need to, STOP and ask):
   - <list the exact files/dirs this thread may modify, e.g.
      drill/<module>.py, drill/tests/<file>, drill/llm/decisions.md>
   - decisions.md is ALWAYS in scope for recording a decision, even when the
      code change is elsewhere.
