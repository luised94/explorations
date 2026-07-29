# Handoff: roadmap #1 -- modularization (PLAN REVIEWED; THREAD ONE = PHASE 0 + BACKEND)

Status: the modularization design was reviewed and the sorted plan was reviewed
(C-MOD-review). This hands off to the FIRST EXECUTION thread. Predecessor
handoff 1-to-implementation.md launched the review thread (its "PLAN UNREVIEWED
-- review it first" job is DONE); it is kept for history. This document launches
thread one of the two-thread execution split.

THIS THREAD (thread one): Phase 0 (guards + lazy-el) + the BACKEND package split
(config, db, logic, http-in-two, main). STOP at the backend/frontend seam; the
frontend build-alongside + atomic cutover + close-out is THREAD TWO, launched
separately so the cutover stays whole in a clean context.

Baseline to verify in-thread: SHA 6e5850bd1e183d01ad8d023c5fecb6a7facd540e on
main. Suite 311 green (backend 197, frontend 114: drill 10 / speech 21 /
timing 19 / stats 30 / stats.integration 6 / difficulty 20 / import 8), ends
"ALL GREEN". Node v22, uv, ruff. NOTE ON VERSIONS: the design spikes ran at an
earlier SHA with jsdom 26.1.1; a clean clone today resolved jsdom 29.1.1 and
311 still held. Record whatever jsdom the clean room resolves. ruff may need
installing (not required until C0.2).

REPO URL: https://github.com/luised94/explorations.git
ASCII only. Single-user assumption holds. This is a BEHAVIOR-PRESERVING refactor:
no schema, no HTTP contract, no UI behavior change. The suite is the proof --
same tests green before and after each commit (plus new guard tests).

================================================================================
0. THE ONE-PARAGRAPH SUMMARY
================================================================================
Front-load two guards and one data change (Phase 0), then split drill.py into a
package by pure transcription of a verified one-way DAG (Phase 1). C0.1 is a
scope-aware AST boundary-purity guard on the still-monolithic drill.py (green on
clean code, red on an injected clock call in LOGIC). C0.2 lands ruff import-
direction config + adopts `uv format`. C0.3 makes the frontend `el` lazy + adds
the ownership registry with owner tags (frontend, but Phase 0 because it
unblocks option (b) later; the inline script stays authoritative, 311 stays
green). Then extract config, db, logic, http (split across TWO cuts -- 638-line
region), main -- each importing only already-extracted predecessors. Backend has
ZERO naming debt, so per-module "style" commits COLLAPSE into their cut unless
the check finds something. Stop before any frontend module extraction.

================================================================================
1. READ THESE FIRST (the reviewed plan -- do not re-derive)
================================================================================
- llm/STATUS.md -- single source of truth; the modularization block records the
  reviewed status and the thread split.
- llm/roadmap-1-modularization-commit-plan.md SECTION R -- THE EXECUTABLE PLAN
  (classified, sorted, thread-split, co-load sets). The C/D/E sections below R
  are design rationale, SUPERSEDED by R for sequencing.
- llm/roadmap-1-modularization-findings.md -- S1-S5 (design facts) + S6-S9
  (review addenda). For thread one the load-bearing ones are S2 (clean backend
  DAG), S4 (both guards proven), S8 (analyzer false positives -> guards must be
  scope-aware/symbol-based), S9 (backend naming debt is zero).
- llm/decisions.md ADR-049..053 -- all DECIDED. ADR-050 is the backend guard
  contract; ADR-053 (the cycle) is thread-two material but read it for context.
- llm/CODING_CONVENTIONS.md -- the standard the (mostly empty) backend style
  pass conforms to; the Python layering invariant is the split's contract.
- llm/prompts/{clone-and-verify,commit-planning}.md -- the workflow you run.
  (adversarial-review, spike-and-verify, plan-review are DONE for this design;
  re-open one only if execution surfaces a NEW gating fact.)

================================================================================
2. THE COMMIT SEQUENCE (from SECTION R -- thread one only)
================================================================================
C0.1 SONNET  AST boundary-purity guard on the MONOLITH (scope-aware, symbol-
             based, policy table). GREEN on drill.py; prove RED on an injected
             datetime.now() in a LOGIC function (both-directions rule). 311->312.
             Co-load: drill.py, tests/test_boundary_purity.py, conventions.
C0.2 HAIKU   ruff TID251 banned-api + per-file-ignores in pyproject.toml; adopt
             `uv format`. Inert pre-split. 312 unchanged. Co-load: pyproject.toml.
C0.3 SONNET  make `el` LAZY + registry with owner tags (DATA). Inline script
             stays authoritative; 311/312 green. This is an ADJUSTMENT (eager->
             lazy timing), not pure relocation -- the suite is the guard. It is
             the highest-blast Phase-0 commit (28 nodes / ~149 reads); it lands
             before any extraction. Co-load: index.html, frontend tests.
D1   SONNET  cut config.py (leaf: scalars, QTYPES, DIFFICULTY_RUNGS, SCHEMA_*,
             MIGRATIONS, OPERATOR_DEFINITIONS).
D2   SONNET  cut db.py (imports config).
D3   SONNET  cut logic.py (imports config; purity guard now per-file enforceable).
D4a  SONNET  cut http.py PART A: request-helper preamble (_json_error,
             _integrity_message, _request_json, _BadParameter, _require_int,
             _optional_int) + app object + simple read routes (/, categories,
             banks, difficulty-rungs). Imports db+logic.
D4b  SONNET  cut http.py PART B: heavy routes (question, answer, stats,
             session/start, session/end, banks/import). Split from D4a to keep
             each co-load set <= sonnet.
D5   HAIKU   cut main.py (imports db+http).
Backend "style": emit a separate HAIKU per module ONLY if the naming/docstring
check finds work; expected empty (S9). No ceremony commits.

Target package (import direction is the contract, enforced by C0.1+C0.2):
  config <- db <- logic <- http ; main wires. NOTHING imports http.

================================================================================
3. MUST NOT BE REOPENED (binding)
================================================================================
- BEHAVIOR-PRESERVING: no endpoint contract, payload shape, or UI behavior
  change. Every commit 311(+guards) green, same tests.
- A split that breaks the one-way import direction is a FAILED split. The
  layering invariant is the POINT of the exercise.
- Extraction is a CUT (relocation + import/export plumbing), never a rewrite. If
  a diff carries new logic, it is two changes -- split it.
- Delivery: git-apply-able PATCHES rooted at drill/..., verified to apply in a
  FRESH clone at the pinned SHA with the full suite re-run there. NO push.
  Verify the green COUNT, not just the banner. One patch per commit.
- The guard (C0.1) and ruff (C0.2) re-run every backend commit. Post-split the
  guard's layer-of-symbol switches from line-range to "the file it lives in"
  (policy table unchanged).
- STOP at the backend/frontend seam. Do NOT begin frontend extraction; that is
  thread two, and the atomic cutover must stay whole in its own context.
- DEFERRED, do NOT fold in: the thin DOM seam; bulk-import bounding (inert
  scaffold-comment only if a cut touches the import code); functional DOM-state
  threading (rejected).

================================================================================
4. THREAD-TWO HANDOFF (what thread one must leave clean)
================================================================================
When thread one closes, hand off to thread two with:
- the new baseline SHA (backend fully split, 312+ green);
- the C0.1 test as the TEMPLATE for thread two's E10 ownership guard (scope-
  aware AST -- the same discipline, applied to frontend module ownership);
- a note to re-confirm F1 (jsdom does not run type=module) against thread two's
  clean-room jsdom version;
- confirmation that C0.3 (lazy el + registry with owner tags) is in place, since
  every frontend module depends on it.

================================================================================
5. WORKFLOW CONTRACT (standing; unchanged)
================================================================================
At each commit boundary: edit in-sandbox, run bash tests/run.sh (bash, not sh),
COMMIT in-sandbox with the agreed message, then deliver the TRIPLE:
  (a) SUMMARY ending with a "files modified" list;
  (b) PATCH = git diff <prev_sha> HEAD, paths rooted at drill/..., delivered as
      a DOWNLOADABLE file, verified to apply in a fresh clone at the pinned SHA;
  (c) COMMIT MESSAGE: type(scope): imperative subject; indented bulleted body
      (what + why); a final suite-delta line; the commit tag (e.g. C-MOD-...).
Verify the green COUNT before/after every commit. One patch per commit; keep
commits small and independently green.

================================================================================
6. STATE AT HANDOFF
================================================================================
- Design + spikes + BOTH reviews complete. Plan is classified, sorted, thread-
  split (SECTION R). Docs cemented (STATUS, findings S6-S9, ADR-051/052 resolved
  + ADR-053 added, knowledge-capture ESM fact).
- Nothing extracted yet; drill.py and index.html are untouched monoliths.
- Suite 311 green at 6e5850bd. First action: clone-and-verify, confirm 311, then
  C0.1.
