# Handoff: roadmap #1 -- modularization (DESIGN + SPIKES DONE; PLAN UNREVIEWED)

Status: the modularization DESIGN thread is complete. Unlike the #5 handoff,
this one hands off a design + measured facts + a DRAFT commit plan that is NOT
yet adversarially reviewed or topologically sorted. That review IS the next
thread's first job (the design thread deliberately stopped before it, so the
review is done cold on a clean context). This document tells a fresh thread what
is settled, what is still open, what to read, and the sequence of workflow steps
to run.

Baseline to verify in-thread: SHA <FILL: the commit these C-MOD patches land at>
on main, sparse tree clean (only drill/ at top level). Suite 311 green (backend
197, frontend 114: drill 10 / speech 21 / timing 19 / stats 30 /
stats.integration 6 / difficulty 20 / import 8), ends "ALL GREEN". Node v22,
jsdom 26.1.1, uv (repo built on v22), ruff 0.15.20.

ASCII only. Single-user assumption holds. This is a BEHAVIOR-PRESERVING refactor:
no schema, no HTTP contract, no UI behavior change. The suite is the proof --
same tests green before and after each commit (plus new guard tests).

================================================================================
0. THE ONE-PARAGRAPH SUMMARY
================================================================================
Split drill.py into a package (config/db/logic/http/main) and index.html's
single inline script into ES modules (state/api/drill/session/stats/speech/
timing/boot), mirroring the existing one-way section boundaries, changing no
behavior. The backend is a verified clean one-way DAG, so its split is a pure
transcription. The frontend is harder: jsdom does not execute type=module, so
tests import modules directly via Node (option b), and because all 7 frontend
tests share the classic-script global-leak harness, the modular cutover is a
single atomic commit at the end -- modules are built alongside the untouched
inline script first. Guards (import-direction via ruff, call-purity via a
scope-aware AST test) and the lazy-el + DOM-ownership registry are front-loaded
before any extraction. Fold the CODING_CONVENTIONS style pass into each module's
second commit; `uv format` owns formatting so the pass is naming/docstrings/
asserts only.

================================================================================
1. READ THESE FIRST (the design output -- do not re-derive)
================================================================================
- llm/STATUS.md -- single source of truth; fill BASELINE_TOTAL (311) and the SHA
  into clone-and-verify from here.
- llm/roadmap-1-modularization-findings.md -- spikes S1-S5 as FACTS (settled;
  measured) vs JUDGMENTS (recommended; open to plan-review). The facts are
  givens; do not re-spike them unless a review surfaces a NEW gating assumption.
- llm/roadmap-1-modularization-commit-plan.md -- the DRAFT commit plan (phases,
  module order, R1 strategy, risk table). NOT reviewed/sorted yet.
- llm/decisions.md ADR-049..052 -- the design decisions. ADR-049/050 are DECIDED
  (facts). ADR-051/052 are DECIDED-pending-plan-review (judgments).
- llm/CODING_CONVENTIONS.md -- the standard the style pass conforms to.
- llm/prompts/{adversarial-review,spike-and-verify,commit-planning,plan-review,
  clone-and-verify}.md -- the workflow you will run (see section 5).

================================================================================
2. SETTLED (facts -- measured by spikes; do NOT reopen)
================================================================================
F1 jsdom 26.1.1 does NOT execute <script type=module> (inline or external).
   Frontend tests therefore use OPTION (b): jsdom builds the DOM
   (runScripts:"outside-only"), publish window+document as globals BEFORE
   import, then Node imports the real ES module and drives it -- the mirror of
   backend load_drill(). Works in a plain .test.js via async IIFE + dynamic
   import(); run.sh glob discovers it with no change. (ADR-049)
F2 Modules touch the DOM only INSIDE functions, never at import time (import-
   time getElementById throws under option b; fragile in-browser). (ADR-049)
F3 Backend is a clean one-way DAG: ZERO forward cross-section refs. The package
   split (config<-db<-logic<-http; main wires; nothing imports http) is a pure
   transcription. (ADR-050)
F4 Layering is enforced by TWO data-driven guards: ruff banned-api + per-file-
   ignores (import direction) AND a scope-aware AST purity test (call level --
   catches a function-local import that dodges a module-level ban). The AST
   guard must be scope-aware and assign layer by SYMBOL/file, not line range
   (the naive version gave 3 false positives). (ADR-050)
F5 Frontend `state` is a clean shared-data leaf (~22 concentrated writes). A
   top-level `el` object caches 156 DOM nodes AT IMPORT TIME -- it must become
   lazy before any frontend module is importable. (findings S3)
F6 All 7 frontend tests share the classic-script global-leak harness; flipping
   the tag to type=module breaks them ALL at once. Hence one atomic cutover.

================================================================================
3. RECOMMENDED (judgments -- attack these in adversarial-review; may change)
================================================================================
J1 DOM ownership via REGISTRY-WITH-OWNER-TAGS (el is already the registry), not
   module-prefixed IDs. No rename; a stale registry reddens the suite. (ADR-051)
J2 FRONTEND STRATEGY R1 duplicate-then-delete: build modules alongside the
   untouched inline script, prove each with a new option-(b) test, then ONE
   atomic cutover (flip tag, delete inline script, migrate the 7 tests, land
   frontend guards). R2 dual-load rejected as complection. (ADR-052)
J3 ORDER dependencies-first. Backend: config, db, logic, http, main. Frontend:
   state, api, timing, speech, stats, session, drill, boot; cutover last. Each
   module = 2 commits (cut, then style). Guards + lazy-el/registry front-loaded.
J4 The cutover is the one unavoidably-atomic, non-small commit -- a candidate
   for the "let it go red" tool; kept mechanical by R1.

================================================================================
4. MUST NOT BE REOPENED (from the original handoff, still binding)
================================================================================
- BEHAVIOR-PRESERVING: no endpoint contract, payload shape, or UI behavior
  change. Every commit 311 green (plus new guard tests), same tests.
- A split that breaks the one-way import direction is a FAILED split, not
  progress. The layering invariant is the POINT of the exercise.
- No feature work, schema changes, or the migration runner -- separate items.
- Delivery: git-apply-able PATCHES rooted at drill/..., verified to apply in a
  FRESH clone at the pinned SHA with the full suite re-run there. NO push.
  Verify the green COUNT, not just the banner. One patch per commit.
- Extraction is a CUT (relocation + import/export plumbing), never a rewrite.
  If a diff carries new logic, it is two changes -- split it. The style pass is
  its own second commit per module.
- DEFERRED, do NOT fold in: the thin DOM seam (Eskil quarantine -- setText/
  show/hide wrappers; its own post-modularization item, rewrites 156 sites);
  bulk-import bounding (inert scaffold-comment only when the split touches the
  import code); functional DOM-state threading (rejected outright).

================================================================================
5. THE THREAD'S SEQUENCE (workflow steps, in order)
================================================================================
1. clone-and-verify at the pinned SHA; confirm 311 green before anything.
2. adversarial-review the DESIGN. Facts (section 2) are givens; attack the
   JUDGMENTS (section 3) with the lenses -- especially DEPENDENCY QUARANTINE
   (is el-registry the right seam or a half-seam?), SIMPLICITY/STATE +
   COMPLECTION (does R1's transient duplication or the registry introduce a
   braid?), ENFORCED CONSTRAINT (are the guards really machine-checked where
   introduced?). If a lens overturns a judgment, revise before planning.
3. spike-and-verify: largely DONE (S1-S5). Re-spike ONLY if step 2 surfaces a
   new gating assumption (e.g. a chosen alternative to J1/J2 whose feasibility
   is unproven).
4. commit-planning on the surviving design: classify each commit HAIKU/SONNET/
   OPUS (split any opus -- does-X-and-also-Y); name dependency edges; grep blast
   radius; topologically sort; ASSIGN THE CO-LOAD SET per commit; decide the
   THREAD SPLIT. HYPOTHESIS to confirm against the real DAG: Phase 0 (guards +
   lazy-el/registry) + backend in ONE thread; frontend + atomic cutover +
   close-out in a SECOND thread, so the atomic cutover stays whole in one
   thread's context. Confirm or revise; do not assume.
5. plan-review the sorted plan (SEPARATE prompt): VERIFICATION-HONESTY (is each
   green claim true in a fresh clone?) and THREAD-SPLIT/SYNC-POINTS (does the
   boundary fall on a clean cut; is the cutover kept whole?) are the load-
   bearing lenses. An objection reaching the design goes back to step 2; a
   factual unknown goes back to step 3.
6. Execute commit-by-commit per the workflow contract (section 6). Front-load
   Phase 0 (C: guards + lazy-el/registry) exactly as the draft plan sequences.
7. Close-out: ADRs land AFTER code per project convention -- ADR-049..052 are
   pre-recorded; add as-built ADRs and resolve the pending-plan-review status on
   ADR-051/052. Update STATUS.md (new counts/layout), roadmap.md (#1 DONE),
   knowledge-capture.md ONLY for durable LLM/prompt facts (the jsdom fact is a
   candidate). Record the exact new green totals.

================================================================================
6. WORKFLOW CONTRACT (standing; unchanged)
================================================================================
At each commit boundary: edit in-sandbox, run bash tests/run.sh (bash, not sh),
COMMIT in-sandbox with the agreed message, then deliver the TRIPLE:
  (a) SUMMARY ending with a "files modified" list;
  (b) PATCH = git diff <prev_sha> HEAD, paths rooted at drill/..., delivered as
      a DOWNLOADABLE file, verified to apply in a fresh clone at the pinned SHA;
  (c) COMMIT MESSAGE: type(scope): imperative subject; indented bulleted body
      (what + why); a final suite-delta line; the commit tag (e.g. C-MOD-...).
Verify the green COUNT before/after every commit. One patch per commit; keep
commits small and independently green (or a DELIBERATE, noted red -- only the
cutover is a candidate, and R1 keeps even that mechanical).

================================================================================
7. STATE AT HANDOFF
================================================================================
- Design + spikes complete; workflow prompts refined (adversarial-review lenses,
  spike-and-verify, plan-review added; commit-planning co-load set; clone-and-
  verify baseline parameterized).
- Nothing extracted yet; drill.py and index.html are untouched monoliths.
- Suite 311 green at the handoff SHA. Fill the SHA into section-top + clone-and-
  verify BASELINE fields before starting.
- The commit plan is a DRAFT: unreviewed, unsorted. Step 2 is where it becomes
  real. Do not execute the draft plan as-is without running steps 2, 4, 5.
