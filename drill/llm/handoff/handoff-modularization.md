# Handoff: roadmap #1 -- modularization (extract JS modules + split Python)

Forward-looking and prescriptive, in the project handoff format. Roadmap #2
(difficulty) is now COMPLETE (ADR-047 closed, C-2U-a..d); the next core-thread
step is #1, modularization -- the highest-scored item, deliberately sequenced
after the arithmetic round so you refactor code you understand cold (the
score-vs-sequence criterion in knowledge-capture).

This is a DESIGN-AND-IMPLEMENT thread that the user expects to run long and
wants kept focused. Some choices need to be made up front (below) before any
extraction. Do not let it sprawl into feature work.

================================================================================
0. BOOTSTRAP (do this first, exactly)
================================================================================
- SHA pin: the user supplies the real SHA in the launch message (it will be the
  commit AFTER C-2U-d + this docs commit land on main). Do NOT guess it; verify
  the clone matches before any work.
- Sparse-clone just drill/, verify the SHA, then establish the safety net:
    git clone --depth 1 --filter=blob:none --sparse <REPO_URL> /tmp/repo
    cd /tmp/repo && git sparse-checkout set drill && cd drill
    git -C /tmp/repo rev-parse HEAD     # MUST equal the pinned SHA exactly
    uv sync --group test
    npm install jsdom --no-save         # Node 18+ (repo built on v22)
    bash tests/run.sh                   # invoke with bash, not sh
- EXPECTED at this SHA on a clean clone: 311 green (backend 197, frontend 114 =
  drill 10 / speech 21 / timing 19 / stats 30 / stats.integration 6 /
  difficulty 20 / import 8), ending "ALL GREEN". If it is NOT 311 green at the
  verified SHA, STOP and report (collection/import/syntax errors count as red).
  Do not start building on a non-green baseline.
- ASCII only in all outputs and files. Single-user assumption holds.

================================================================================
1. DELIVERY DISCIPLINE (non-negotiable -- unchanged from the UI thread)
================================================================================
- NO push credentials. Deliver each commit as a git-apply-able PATCH (paths
  rooted at drill/...), verified to apply cleanly in a FRESH clone at the pinned
  SHA, with the full suite re-run there.
- Verify the green COUNT, not just the "ALL GREEN" banner, after every commit.
  State before/after counts each time.
- Present patches as downloadable files; one patch per commit; keep commits
  small and independently green.
- Commit-message style: type(scope): subject, indented bulleted body (what +
  why), a final suite-delta line, and the commit tag. Match the existing
  history.

================================================================================
2. ATTACH TO THIS THREAD
================================================================================
- drill.py and index.html (the two files being split).
- llm/STATUS.md -- the live state, baseline SHA, and the 311 green count to
  verify against. The single source of truth; read it first.
- llm/CODING_CONVENTIONS.md -- the coding standard (TigerStyle/NASA-adapted) the
  split must conform to as it touches each module. Folding the style pass into
  each extraction is an explicit goal of this thread.
- llm/roadmap.md -- Section 3/4 ALREADY contains the modularization plan (the
  target file set, why it is low-risk here, the sequencing rationale). READ IT;
  this handoff links to it rather than restating it (Nelson/anti-drift).
- llm/knowledge-capture.md -- the CONSTRAINTS (layering invariant, import
  direction), CONVENTIONS (backend/frontend file layout already specified), and
  the [v-2U] notes (the jsdom cascade rule; NOTE the run.sh papercut is already
  fixed in C-2U-e -- frontend tests glob-discover, so new test files are
  zero-config).
- llm/decisions.md -- the layering and boundary ADRs; append new ADRs for the
  split decisions AFTER the code lands (the project lands ADRs after code).
- llm/spec.md -- the architecture/data-model record.

================================================================================
3. SCOPE (what to build) -- see roadmap.md Section 3/4 for the full plan
================================================================================
Two extractions, mirroring the existing one-way section boundaries:
- FRONTEND: index.html's single <script> -> ES modules loaded via
  <script type="module"> (the convention names them: state, api, drill, session,
  stats, speech, timing, boot). No build step, no framework. state stays a single
  shared object imported where needed (never a store/observable).
- BACKEND: drill.py -> a small package (config, db, logic, http, main) mirroring
  the existing section comments. Import direction is the contract: http imports
  db+logic; logic imports config; db imports config; nothing imports http. This
  is unusually low-risk BECAUSE the sections already hold a strict one-way
  boundary (verified, not assumed -- LOGIC has zero db/bottle references).

ALREADY DONE (C-2U-e, before this thread): tests/run.sh DISCOVERS frontend tests
via a glob over tests/frontend/*.test.js with a leading-underscore skip
convention, replacing the hand-maintained list. So adding a test in this thread
is zero-config -- no run.sh edit needed per new test file.

================================================================================
4. DECISIONS TO MAKE UP FRONT (before extracting)
================================================================================
- D-MOD-1: extraction ORDER. Recommend FRONTEND FIRST -- it is the lower-risk
  half (no import-direction subtlety; jsdom already loads the real file), and it
  lets you validate the "split, re-run, green" rhythm before the backend, where
  a bad split can break import direction. Then backend.
- D-MOD-2: how the frontend tests load modules. Today each jsdom test reads the
  single index.html. After the split, index.html will <script type="module">
  the pieces -- confirm jsdom resolves the module graph from the real file (it
  should with the right runScripts + resources settings), or the tests need to
  load the entry module directly. PROVE this with ONE module extracted before
  splitting the rest, so the test harness change is validated cheaply.
- D-MOD-3: backend test imports. Tests currently load the whole module
  (load_drill / _support). After the package split, decide whether tests import
  the package or the submodules; keep the WSGI-app drive path working. The
  boundary-purity check (AST: no bottle/connection/clock in logic) becomes
  ENFORCEABLE per-module now -- add it as a real test (it was a SKILLS pattern,
  make it a guard).
- D-MOD-4: commit granularity. One module per commit, each independently green,
  is the safest path and matches the discipline. Resist a single big-bang split.

================================================================================
5. GUARDRAILS / INVARIANTS THAT MUST STILL HOLD
================================================================================
- BEHAVIOR-PRESERVING refactor: this is a legibility/maintainability change, NOT
  a feature or correctness change. Be honest about why (the knowledge-capture
  principle). No endpoint contract, no payload shape, no UI behavior changes.
  The suite is the proof: 311 green before and after each commit, same tests.
- The layering invariant and import direction are the POINT of the exercise; a
  split that breaks one-way dependency is a failed split, not progress.
- Do NOT fold in feature work, schema changes, or the migration runner -- those
  are separate roadmap items with their own threads.
- Keep "verify the count, not the banner"; deliver by clean-room patch; no push.

================================================================================
6. DONE LOOKS LIKE
================================================================================
- index.html loads ES modules; drill.py is a package; behavior is identical and
  the full suite is green at >= 311 (the same tests, possibly + the new boundary
  -purity guard and the run.sh glob).
- run.sh already discovers frontend tests by glob (C-2U-e); keep it that way.
- New ADRs record the split decisions (D-MOD-1..4 as resolved), landed after the
  code. roadmap.md #1 marked DONE (the item-8 / item-2 precedent).
- Everything delivered as clean-room-verified patches.

================================================================================
7. FINAL ADVICE FROM THE UI-SELECTOR THREAD (carry these in)
================================================================================
- The architecture is genuinely split-ready and this was RE-CONFIRMED this
  thread: the difficulty work threaded cleanly through every layer with no
  boundary violation, and the fetch path vs record path were already cleanly
  separated (the stats-safety finding). The boundaries are real; trust them but
  add the AST purity guard so they STAY real after the split.
- Make the recurring class of mistake structural, not disciplinary. Two examples
  this thread: the [hidden] guard convention was documented yet still missed
  (caught only by chance) -> add a grep/lint guard; the run.sh explicit list bit
  twice -> glob it. Every "remember to..." convention that gets missed is a
  candidate to convert into a check. The modularization thread is the right place
  to add these guards because it is already touching the structure.
- Prefer server-returns-facts / client-owns-copy at every read endpoint you
  touch while splitting api.js out (the /api/difficulty-rungs pattern). It keeps
  the api module thin and the presentation in the presentation module.
- Watch the jsdom cascade limitation (knowledge-capture SKILLS [v-2U]) when the
  frontend tests change: assert stylesheet rules and DOM structure, never
  cascade-resolved layout.
- Keep commits at or below sonnet complexity; if a module extraction looks like
  it would exceed that (the http split is the biggest), split it further rather
  than shipping one heavy commit.
