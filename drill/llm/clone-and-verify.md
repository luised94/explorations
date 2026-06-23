SETUP - do this before anything else, and stop if a check fails.

1. Sparse-clone just the drill/ directory (public repo, read-only - you have
   no push credentials and must not attempt to push, open PRs, or modify the
   remote in any way):

   git clone --depth 1 --filter=blob:none --sparse https://github.com/YOURUSER/YOURREPO.git /tmp/repo
   cd /tmp/repo && git sparse-checkout set drill && cd drill

the repo is https://github.com/luised94/explorations.git

2. Verify you have the right code, and report all four back to me before
   proceeding:
   - `ls -la /tmp/repo`        (confirm ONLY drill/ materialized, not the rest of the repo)
   - `ls -laR .`               (the drill/ working tree)
   - `git -C /tmp/repo rev-parse HEAD`   (the commit SHA you are working from)
   - `git -C /tmp/repo log -1 --oneline --decorate`

   I expect HEAD to be on branch: <BRANCH>  at approximately SHA: <SHA-PREFIX>.
   If it does not match, STOP and tell me - do not work against the wrong tree.
   main at commit 21b5b57e13d31e8ffd07c708f4a85d98d04d90e2

3. Establish the safety net is green BEFORE you change anything:
   - uv sync --group test
   - npm install jsdom --no-save        (needs Node 18+)
   - bash tests/run.sh

   Expected baseline: 159 assertions green - backend 84 (logic 35, http 40,
   db 7, property 2), frontend 75 (6/21/19/23/6), ending "ALL GREEN".
   If the baseline is NOT 159 green on a clean clone, STOP and report - that
   is a problem with the starting state, not something to work around.

STANDING RULES for this thread (apply throughout):
- The C-020 suite is the safety net. Re-run `bash tests/run.sh` after every
  meaningful change. A red test is a REAL contract change to reconcile, not a
  merge artifact. If you deliberately change a pinned behavior, update the
  test AND note it in decisions.md in the same change.
- Cite the relevant ADR/decision in new code the way C-020 did (anchor
  comments referencing decisions.md), where one applies.
- Read decisions.md and phase0.md before designing; honor the existing
  data-oriented procedural style (plain dicts/lists across boundaries, the
  CONFIG/DATABASE/LOGIC/HTTP/MAIN section split, HTTP is the only clock-reader).
- ASCII only in all files and output.
- Do not touch files outside this thread's stated scope (below). If you think
  you need to, stop and ask.
- Report the final pass count when done.
