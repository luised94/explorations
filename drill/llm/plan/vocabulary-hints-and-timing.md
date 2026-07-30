# Thread N -- Commit-by-Commit Plan (surface hints + timing stats + ADR index)

STATUS: REVIEWED -- adversarial-review + spike-and-verify + commit-planning +
plan-review complete against the actual code at the reassessment baseline. No
code landed yet. This is the EXECUTABLE plan. ASCII only. Single-user.

Baseline: the tip of the roadmap-reassessment docs commit (ADR-054). A launch
message pins the exact SHA. Verify HEAD == SHA and confirm 539 green ("ALL
GREEN": backend 203, frontend 336) on a clean clone before any work.
Deps: `uv sync --group test` then `npm install jsdom acorn --no-save` (ONE
command; two separate --no-save installs prune each other). Delivery is
git-apply-able patches, one per commit; no push. Each commit states before/after
counts and re-verifies in a fresh clone (green COUNT, not just the banner).

================================================================================
0. HOW THIS THREAD WAS SCOPED (read before executing -- the scope is narrow ON
   PURPOSE)
================================================================================
The reassessment (ADR-054) put "vocab/language features" as the next thread.
Running the workflow prompts against the real code NARROWED it hard:

- adversarial-review (lens 3 REAL vs SPECULATIVE): "vocab features" was too
  vague -- architecture for an imagined consumer. The census forced concrete
  gaps instead.
- spike-and-verify produced three load-bearing facts (Section 4 records them):
  * SPIKE 1: questions STORE `hints` (a list) and the importer accepts them, but
    build_question_payload does NOT forward them -> surfacing hints is a real,
    additive gap (payload line + UI). No schema, no migration.
  * SPIKE 2: NO test asserts the payload's exact key SET (the only payload-
    adjacent test checks metadata is NOT forwarded, which stays true) -> adding
    keys is backward-compatible; added keys redden nothing.
  * LANGUAGE CENSUS: per-question-language-in-payload is NOT a missing
    capability -- C-018a already sources language from the bank on the client,
    a documented working design. Threading it into the payload would be
    redundancy with no present consumer -> DEMOTED to the futures note
    (llm/vocab-language-futures.md), not built here.
- Richer vocab (direction L1<->L2, decks, SRS-for-vocab): NO decided consumer
  exists -> captured as docs in the futures note, NOT scaffolded in code
  (forward-only migrations make speculative schema unrollable; same discipline
  that rejected language-in-payload).

Net: Thread N is ONE real feature (surface hints) + TWO quick wins (timing
stats, ADR index). That is the whole thread. Do not re-expand it without a
decided consumer and a fresh adversarial-review.

================================================================================
1. THE EXECUTABLE LIST (sorted; lead with the meatier work per user steer)
================================================================================
Legend: type = HAIKU/SONNET; each row states the goal, the dependency edges,
what proves it green, and the CO-LOAD SET.

Sort rationale (plan-review verdict): the three items are mutually INDEPENDENT
(no cross-item edges), so any order lands green. The user chose to lead with the
meatier work while context is freshest. plan-review lens 3 (blast radius) noted
hints is the only shared-assumption item (it touches the el registry + ownership
guard), so the MITIGATION is an intra-commit ordering: land the tiny registry/
guard piece FIRST inside N.1, verify the guard green at the new node count, then
build payload + UI on top. This front-loads the ripple while context is fresh
AND de-risks the blast-radius item early, without splitting the el node from its
first use (which would momentarily create the dead-key the guard flags).

--------------------------------------------------------------------------------
N.1 -- SONNET -- Surface stored hints (the real vocab-learning feature)
--------------------------------------------------------------------------------
GOAL: questions already store a `hints` LIST (imported via JSONL/CSV) that never
reaches the user. Add a progressive "reveal hint" affordance: forward hints in
the payload, and render a reveal control that shows hints one at a time (handle
0, 1, and many -- SPIKE 1 note: hints is a list at N, not N=1).

DO NOT overload the existing `answerHint` node (el.js:45, owner:"stage"): it
carries the empty-submit nudge, cleared on input/transition (drill.js
175/216/388/474). Overloading it complects two meanings (adversarial lens 2 /
Hickey). Add a NEW el node for the hint-reveal area instead.

INTRA-COMMIT ORDER (the mitigation):
  (a) Add the new el node to EL_REGISTRY (id + owner). Decide owner: the reveal
      belongs to the drill loop (it renders per-question and clears on
      transition), so owner:"drill" is the natural choice -- which AVOIDS a new
      CROSS_OWNER_READS row (drill reading a drill-owned node). Update
      ownership.guard.test.js: registry count 26 -> 27; the owner-declares check
      (B) requires drill.js to reference the node; the no-dead-keys check (A)
      requires it to be read somewhere. Land these together and confirm the
      guard is GREEN at 27 before proceeding (do NOT leave a dead key).
  (b) Backend: build_question_payload adds `"hints": question.get("hints") or []`
      (additive; SPIKE 2 says nothing reddens). Keep it OFF validate_answer's
      dispatch (guardrail: columns FEED grading, hints are display-only).
  (c) Frontend: render the reveal control in the drill question flow (drill.js),
      show hints progressively, clear on question transition (mirror the
      answerHint lifecycle but on the new node). Reveal must be truthful
      (adversarial lens 10 AFFORDANCE): if there are 0 hints, no control shows.

DEPENDENCY EDGES: (c) needs (b) [UI reads payload.hints]; (a),(b),(c) are one
welded movement -- the registry entry + owner reference + guard expectation move
together or the guard reddens (correctly ONE sonnet, not split).

WHAT PROVES IT GREEN:
  - ownership.guard.test.js GREEN at 27 nodes (checks A/B/C/D + RED-proofs).
  - backend: a test in test_db.py (or test_logic.py) asserts the payload carries
    `hints` for a question with hints, and `[]` for one without.
  - frontend: a test (drill.test.js or a new one) drives the reveal -- 0 hints
    shows no control; N hints reveal one-by-one; transition clears.
CO-LOAD SET (largest in the thread -- watch context budget, plan-review lens 6):
  build_question_payload + its test; el.js registry + ownership.guard.test.js;
  drill.js render/clear region + the DOM fixture (_harness.js) + one frontend
  test. If this feels heavy at execution, the ONLY safe split is (a) alone
  (node+guard, tiny) then (b)+(c) -- but (a) alone leaves a dead key UNLESS the
  guard expectation is staged too; prefer to keep whole and re-load carefully.

--------------------------------------------------------------------------------
N.2 -- SONNET -- Timing stats (compute + display median elapsed_ms)
--------------------------------------------------------------------------------
GOAL: elapsed_ms is collected on every answer (since C-018c) but summarize_stats
DELIBERATELY IGNORES it (logic.py ~1344: "the timing FEATURE is a deferred
future commit; rows carry elapsed_ms so that feature can use it later"). This is
that commit. Add a timing aggregate to the stats summary and render it.

DESIGN CALL (adversarial lens 1 DATA-at-N): use MEDIAN, not mean. Response times
are right-skewed (a few long pauses); the mean misleads, the median is the
honest central figure. Compute over rows with non-null elapsed_ms only; the
time-zero/empty case yields no timing figure (mirror summarize_stats' existing
empty handling -- total 0 yields no division).

BACKEND: summarize_stats(rows) adds e.g. `median_elapsed_ms` (null when no row
has elapsed_ms). Pure + deterministic (keep the function's stated purity).
FRONTEND: renderStatsPanel(summary) adds a figure() for the timing value when
present (suppress when null, like the single-category/single-bucket suppression
already there, C-D2i-3).

DEPENDENCY EDGES: frontend needs backend [render reads summary.median_elapsed_ms].
No el-registry/guard interaction (no new node) -> simpler than N.1. No cross-
item edge to N.1.

WHAT PROVES IT GREEN:
  - backend: test in test_logic.py asserts median over seeded rows INCLUDING
    some null elapsed_ms (null-skipping is the subtle case); asserts null result
    on all-null / empty.
  - frontend: stats.test.js (or stats.module.test.js) asserts the figure renders
    when present and is absent when null.
CO-LOAD SET: summarize_stats + its test; renderStatsPanel + one stats test.
Moderate.

--------------------------------------------------------------------------------
N.3 -- HAIKU -- ADR index (close the last #20 loop)
--------------------------------------------------------------------------------
GOAL: #20 (docstring/status-drift + ADR index) is WIP; STATUS + conventions are
done, only the ADR index remains (STATUS.md:206). Write a navigable index of
ADR-001..054 (id -> one-line subject -> status DECIDED/SUPERSEDED/DEFERRED).
Either a new llm/adr-index.md or a top-of-file index block in decisions.md.

DEPENDENCY EDGES: none. Independent; lands anytime. Sequenced last as the
closing easy win.
WHAT PROVES IT GREEN: docs only; suite unchanged. Verify the index matches the
actual ADRs in decisions.md (grep the ADR- headers; no missing/extra ids).
Mark #20 DONE in STATUS.md + roadmap.md.
CO-LOAD SET: decisions.md ADR headers only.

================================================================================
2. SUITE PROJECTION
================================================================================
539 -> 539 + (new asserts: a few per commit). Order N.1 -> N.2 -> N.3, each
green independently in a fresh clone. N.1 changes the guard's node count
(26 -> 27); N.2 adds a backend + frontend assertion; N.3 is docs-only.

================================================================================
3. WORKFLOW CONTRACT (same as prior threads)
================================================================================
Per commit: edit in-sandbox, `bash tests/run.sh`, commit in-sandbox, then
deliver the triple -- (a) summary + files list; (b) downloadable patch via
present_files, verified applying in a FRESH clone at baseline with prior
Thread-N patches re-applied, suite re-run (green COUNT); (c) house-format commit
message inline. Set a git identity before the first commit. One patch per
commit; no push.

================================================================================
4. SPIKE FACTS CARRIED IN AS GIVENS (do not re-derive; verify if in doubt)
================================================================================
- build_question_payload sets qtype, question_text, expected, question_id,
  alternatives, media_url (+ options for MC). `hints` is ABSENT -> N.1 adds it.
- NO test asserts the payload key SET; test_db.py's metadata test only asserts
  metadata is NOT forwarded (still true after adding hints).
- summarize_stats IGNORES elapsed_ms today (logic.py ~1344); rows already carry
  it -> N.2 needs no new query, just a read.
- answerHint (el.js:45) is stage-owned and busy with the empty-submit nudge ->
  N.1 uses a NEW node (owner:"drill" to avoid a cross-owner allowlist row).
- get_bank(connection, bank_id) exists (db.py:381) -- relevant only to the
  DEMOTED language-in-payload work (futures note), not this thread.
- ownership.guard.test.js reads EL_REGISTRY (26 nodes) and enforces A unique/
  owned/no-dead-keys, B owner-declares, C cross-owner allowlist (9 rows), D
  no-DOM-at-import (boot readyState exempt). Adding a node touches A + B.

================================================================================
5. WHAT IS EXPLICITLY NOT IN THIS THREAD (demoted / deferred; see futures note)
================================================================================
- Per-question language in the payload (redundant with C-018a; no consumer).
- Direction (L1<->L2), vocab decks, SRS-for-vocab, importers -> no decided
  consumer; docs-only in llm/vocab-language-futures.md.
- SM2 scheduling fields -> Thread N+1 (ADR-025 reserves the migration there).
