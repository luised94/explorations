# Launch brief: #2 difficulty UI selector (implementation thread)

This is the LAUNCH BRIEF the next thread starts from. It is self-contained: read
this, then the two attached docs, then begin. The backend and data path for #2
are complete and green; this thread adds the ONE missing piece -- a UI control
that sets the difficulty rung -- and nothing else.

================================================================================
0. BOOTSTRAP (do this first, exactly)
================================================================================
- SHA pin: <SHA-PLACEHOLDER>  (the user supplies the real SHA in the launch
  message; do NOT guess it, and verify the clone matches it before any work).
- Sparse-clone just drill/, verify the SHA, then establish the safety net:
    git clone --depth 1 --filter=blob:none --sparse <REPO_URL> /tmp/repo
    cd /tmp/repo && git sparse-checkout set drill && cd drill
    git -C /tmp/repo rev-parse HEAD     # MUST equal the pinned SHA exactly
    uv sync --group test
    npm install jsdom --no-save         # Node 18+ (repo built on v22)
    bash tests/run.sh                   # invoke with bash, not sh
- EXPECTED at this SHA on a clean clone: 282 green (backend 196, frontend 86 =
  drill 10 / speech 21 / timing 19 / stats 30 / stats.integration 6), ending
  "ALL GREEN". If it is NOT 282 green at the verified SHA, STOP and report
  (collection/import/syntax errors count as red). Do not start building on a
  non-green baseline.
- ASCII only in all outputs and files. Single-user assumption holds.

================================================================================
1. DELIVERY DISCIPLINE (non-negotiable)
================================================================================
- NO push credentials. Do not push, open PRs, or modify the remote. Deliver each
  commit as a git-apply-able PATCH (paths rooted at drill/...), verified to apply
  cleanly in a FRESH clone at the pinned SHA.
- Verify the green COUNT, not just the "ALL GREEN" banner, after every commit. A
  truncated patch once printed the banner at the wrong count in this project;
  count-checking is how that was caught. State the before/after counts each time.
- Present patches as downloadable files (the user cannot reliably copy from the
  console). One patch per commit; keep commits small and independently green.
- Commit-message style: a `type(scope): subject` line, an indented bulleted body
  explaining what + why, a final line noting the suite delta (e.g.
  "Suite 282 -> N green ..."), and the commit tag (e.g. C-2U-b). Match the
  existing messages in this project's history.

================================================================================
2. ATTACH TO THIS THREAD
================================================================================
- llm/handoffs/handoff-2-implementation-to-ui.md  -- the full spec for this work
  (current state, what is done, the gap, the open decisions, the commit plan,
  the guardrails). READ IT; this brief does not repeat its detail.
- llm/decisions.md  -- ADR-038..047 are the settled #2 design + as-built record.
  ADR-047 is the open item this thread closes. Do not re-litigate 038..046.
- index.html and drill.py for reference. Expect to touch index.html (and, only
  if D-UI-1 = the read endpoint, a thin slice of drill.py).

================================================================================
3. SCOPE (what to build)
================================================================================
A difficulty rung selector, arithmetic-only, wired to the already-present
state.difficulty (default null = the pre-#2 default path). When the user picks a
rung, set state.difficulty and fetch the next question; questionQuery() already
serializes it. "Default" must clear it back to null. See the handoff section 4
for the precise behavior and section 6 for the suggested commit plan.

PRE-DECIDED (the user has resolved the handoff's open decision D-UI-1):
- D-UI-1 = expose a tiny read endpoint. Add GET /api/difficulty-rungs returning
  the rung labels from DIFFICULTY_RUNGS (shape: {"rungs": [{"rung": int,
  "label": str}, ...]}), and populate the selector from it. This keeps the
  client honest if the rung table grows, and it is the only justified backend
  touch. Keep it a pure read (no params, no writes); thin HTTP + one test.
- D-UI-2 (affordance) and D-UI-3 (persistence) remain the implementing thread's
  call within the handoff's recommendations (a <select> with an explicit
  "Default" option; no cross-reload persistence). Choose, note the choice, move on.

================================================================================
4. GUARDRAILS (must still hold at the end)
================================================================================
- difficulty=None / absent MUST remain byte-identical to the pre-#2 path. The
  selector defaults to "Default" (null), never to a rung.
- Bank questions never carry a rung; do not append &difficulty= for them. Mirror
  the existing arithmetic-only gating.
- The generator, schema, stats reader, and breakdown are SETTLED. If the work
  starts editing the generator, the migration, or summarize_stats, that is scope
  drift -- stop. The server already accepts and records everything this needs.
- Do not change the S11 grouping key (leaf_count), the rung table values, the
  ceiling, or the ranges.

================================================================================
5. DONE LOOKS LIKE
================================================================================
- A user can pick a difficulty in the UI; the next arithmetic question reflects
  it; "Default" restores the unparameterized path.
- The selector is populated from GET /api/difficulty-rungs.
- Frontend test (jsdom): picking a rung sets state.difficulty and the next
  /api/question URL carries &difficulty=; "Default" clears it. Backend test: the
  new endpoint returns the rung list.
- Suite green with a stated count >= 282 (new tests add to it); ends "ALL GREEN".
- ADR-047 updated from [OPEN] to closed in decisions.md as the final docs commit,
  once the code is real (the project lands ADRs after the code, never before).
- Everything delivered as clean-room-verified patches.
