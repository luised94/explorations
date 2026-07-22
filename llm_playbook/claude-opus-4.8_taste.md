- diffs: copy the file, edit the copy, `diff -u` the pair, and
  round-trip-verify the patch applies before sending; never
  hand-author hunk headers, line counts, or offsets
- patches: prefer plain `git apply`; `--recount` masks real context
  drift, so keep it as a manual fallback, not the standard mechanism
- edits-without-git: when the sandbox has no `.git` (e.g. a
  `git archive` export), use `diff -u` on two real copies to get
  correct offsets rather than estimating them, or deliver the
  complete updated file and let the author's real repo produce the patch
- verification: treat a patch as unverified until it has been applied
  to a clean copy and diffed against the intended result
- shell/sandbox-git: after git init on a scratch repo, set user.email and user.name in the same command chain before any commit; verify patches with git apply --check, and use only POSIX sh constructs (no <(...)).
