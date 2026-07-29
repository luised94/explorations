# Handoff: #2 difficulty implementation complete -> UI selector thread

Forward-looking and prescriptive. The BACKEND and DATA PATH for roadmap #2
(difficulty control) are COMPLETE, shipped, and green across C-D2a..C-D2i. The
ONE remaining piece is a UI control to SET the difficulty rung. The next thread
adds that control; it does not re-open the difficulty model, the generator, the
schema, or the stats breakdown -- all of which are settled and recorded as
ADR-038..047 in decisions.md.

================================================================================
1. CURRENT STATE
================================================================================
- #2 is implemented end to end EXCEPT the rung selector control. The full chain
  works and is tested: ?difficulty= -> generator (depth/recurse/ranges/ceiling)
  -> payload echo -> answer capture -> v3 columns -> stats reader -> leaf_count
  breakdown -> "By difficulty" panel section.
- Suite at the end of #2: 282 green (backend 196, frontend 86 =
  drill 10 / speech 21 / timing 19 / stats 30 / stats.integration 6), ending
  "ALL GREEN". This is the post-#2 end-state and the next thread's baseline.
- The cut point is a clean commit boundary. The C-D2i sub-commits (i-1 pure
  seam, i-2 wiring, i-3 render) are each independently green; nothing is
  half-done.
- The user manages the SHA/pin. The next thread is told the SHA by the user in
  the launch brief; do not assume or hard-code it.
- Delivery is by PATCH ONLY. The implementing thread has no push credentials and
  must not push, open PRs, or modify the remote. Each commit is delivered as a
  git-apply-able patch verified in a clean-room clone at the pinned SHA, and the
  green COUNT (not just the "ALL GREEN" banner) is confirmed per commit -- a
  truncated patch once reported the banner at the wrong count, so count-checking
  is mandatory.

================================================================================
2. WHAT THIS THREAD IS (scope, stated honestly)
================================================================================
This is a SMALL FRONTEND-ONLY feature: a difficulty rung selector wired to the
already-present state.difficulty, plus its frontend test. NO backend change is
needed or wanted -- the carrier, validation, capture, and breakdown are all
done. If the work starts reaching into drill.py, stop: that is a sign of scope
drift, because the server already accepts and records everything.

Out of scope (do NOT do here):
- Re-tuning the rung table (DIFFICULTY_RUNGS values), the ceiling, or the
  ranges. Those are ADR-039/043/044 and were probed; leave them.
- Changing the S11 grouping key (leaf_count). It is a one-line swap if ever
  wanted (ADR-046), but it is not this thread's call.
- A per-mix difficulty view, operator_set storage, or alt-A "fixed-mix scoping"
  (ADR-038 alternatives / ADR-041 note) -- those are a separate future thread
  with their own migration.
- Making / % ^ nestable, the dataclass promotion (still deferred, ADR-037
  disposition).

================================================================================
3. WHAT IS ALREADY DONE (do not redo)
================================================================================
- CONFIG: DIFFICULTY_RUNGS (4 rungs), per-operator ranges + ceiling, validated
  at import by _check_difficulty_rungs_consistency. (C-D2a)
- LOGIC generator: generate_expression(enabled_symbols, difficulty) resolves a
  rung to depth/recurse/ranges/ceiling and threads them; difficulty=None is
  byte-identical to pre-#2. leaf_count(node) is the structural metric. (C-D2b/d/e)
- DATABASE: v3 migration added responses.difficulty + responses.leaf_count
  (nullable); insert_response writes them; get_responses_for_stats surfaces
  them. (C-D2f/g/h)
- HTTP: /api/question parses + validates ?difficulty= (400 on bad rung) and
  echoes difficulty + leaf_count in the arithmetic payload; /api/answer captures
  the echoed values (type-checked). (C-D2c/g)
- LOGIC stats: breakdown_by pure seam; summarize_stats emits difficulty_breakdown
  grouped by leaf_count; /api/stats carries it. (C-D2i-1/2)
- FRONTEND (partial): state.difficulty (default null); questionQuery() appends
  &difficulty= when set; the answer body echoes difficulty + leaf_count;
  renderStatsPanel renders a "By difficulty" section with single-bucket
  suppression. (C-D2c/i-3)

================================================================================
4. THE ONLY GAP: no control sets state.difficulty (ADR-047)
================================================================================
state.difficulty is wired through but nothing in the UI changes it, so the rung
is always null (the default path) in shipped form. The selector must:
  (a) offer the user the known rungs. The rung labels are 1..N; the client can
      hard-code "1..4" OR fetch them. NOTE: there is currently NO endpoint that
      lists the rungs -- see the decision in section 5. The simplest correct
      option is to expose them.
  (b) set state.difficulty to the chosen rung (or null for "default/off").
  (c) re-fetch the next question so the choice takes effect; the existing
      questionQuery() already serializes state.difficulty, so no fetch-path
      change is needed beyond triggering a new question.
  (d) only apply to the arithmetic category. Bank questions ignore difficulty
      (the payload carries no rung for them). Mirror how the arithmetic-only UI
      is already gated.

================================================================================
5. DECISIONS THE NEXT THREAD MUST MAKE (and a recommendation)
================================================================================
D-UI-1: how does the client learn the rung set? Options:
  (a) hard-code 1..4 in index.html. Cheapest; drifts if DIFFICULTY_RUNGS grows.
  (b) add a tiny read endpoint (e.g. GET /api/difficulty-rungs) returning the
      rung labels (and optionally a human descriptor per rung). One server
      addition, but keeps the client truthful as the table evolves.
  RECOMMENDATION: (b), minimal -- return [{rung, label}] from DIFFICULTY_RUNGS.
  It is the only justified backend touch, and it keeps the selector honest
  without the client re-encoding the rung count. If the user prefers zero
  backend change, (a) is acceptable for a single-user tool.
D-UI-2: control affordance -- a <select>, segmented buttons, or a slider. A
  <select> with an explicit "Default" option (null) is the least surprising and
  matches the existing category/bank selector idiom. RECOMMENDATION: <select>.
D-UI-3: should the chosen rung persist across reloads? There is no client
  storage in this app today (sessionless reload resets state). RECOMMENDATION:
  do NOT add persistence; keep parity with the rest of the UI. Out of scope
  unless the user asks.

================================================================================
6. SUGGESTED COMMIT PLAN (small; adjust as the design firms up)
================================================================================
- C-2U-a (optional, only if D-UI-1=b): GET /api/difficulty-rungs read endpoint
  returning the rung labels from DIFFICULTY_RUNGS. Pure read; HTTP + a thin test.
- C-2U-b: the selector control in index.html -- populate from the endpoint (or
  hard-coded), bind change -> set state.difficulty -> fetch a new question;
  arithmetic-only gating. Frontend test (jsdom): selecting a rung sets
  state.difficulty and the next /api/question URL carries &difficulty=; choosing
  "Default" clears it.
- C-2U-c (optional): show the active rung somewhere unobtrusive (e.g. near the
  expression) so the user knows what they are drilling. Only if the user wants it.

================================================================================
7. GUARDRAILS / INVARIANTS THAT MUST STILL HOLD
================================================================================
- difficulty=None / absent MUST remain byte-identical to the pre-#2 path. Do not
  make the selector default to a rung; default to "Default" (null).
- Bank questions never carry a rung; do not send &difficulty= for them.
- The generator, schema, and breakdown are settled. A change there is a signal
  of scope drift, not progress.
- Keep the "verify the green COUNT, not just the banner" discipline; deliver by
  clean-room-verified patch; no push.
