# Handoff: roadmap #1 -- modularization THREAD THREE (E10 atomic cutover + close-out)

Status: THREAD TWO (frontend build-alongside, E1-E9) is COMPLETE and green. All
ten frontend ES modules are extracted and proven in isolation; the index.html
inline script is still authoritative and every original test still passes (R1
duplicate-then-delete held throughout). This hands off to THREAD THREE: the ONE
atomic cutover commit (E10) and the roadmap-#1 close-out. Predecessor handoff
2-to-frontend-cutover.md launched thread two; it is kept for history.

Baseline for thread three: the tip of thread two (commit C-MOD-E8, boot). A
launch message pins the exact SHA. Verify the clone matches and confirm the
green COUNT (see Section 0) on a clean clone before any work.

ASCII only. Single-user assumption holds. Behavior-preserving refactor: no
schema, no HTTP contract, no UI behavior change. The suite is the proof.

================================================================================
0. WHAT THREAD TWO DELIVERED (verified) -- the E10 starting state
================================================================================
Ten frontend modules extracted as clean ES modules, each proven by an option-(b)
`.module.test.js` (real ESM import + drive), WITHOUT touching index.html. Nine
commits on top of the thread-two baseline (plus one naming tidy):

  C-MOD-E1        state.js        data leaf (STREAK_PIPS_MAX, RECENT_MAX, state, ZERO_STATS)
  C-MOD-E2        api.js          HTTP seam (readJson, apiGet, apiPost)
  C-MOD-E-naming  (tidy)          renamed state/api tests to <module>.module.test.js
  C-MOD-E3        timing.js       nowMs monotonic clock
  C-MOD-E4        el.js + stage.js  shared DOM leaf + ADR-053 relocation
  C-MOD-E5        speech.js       speechSynthesis quarantine
  C-MOD-E6        stats.js        stats bar, run log, cross-session panel
  C-MOD-E7        session.js + drill.js  the ADR-053 cycle pair (ONE commit)
  C-MOD-E8        boot.js         entry module (top of the DAG)

The as-built frontend DAG (imports point down; nothing imports boot):

  state.js      leaf (data)                        imports: --
  el.js         leaf (DOM registry + lazy accessor) imports: --
  api.js        leaf (fetch wrappers)               imports: --
  timing.js     leaf (clock)                        imports: --
  stage.js      shared DOM helpers                  imports: el
  speech.js     TTS quarantine                      imports: state, el
  stats.js      stats rendering                     imports: state, el, api
  session.js    session lifecycle + UI              imports: state, el, api, stage, stats, speech, drill
  drill.js      drill loop + phase machine          imports: state, el, api, stage, speech, timing, session
  boot.js       entry (wiring + boot-guard)         imports: state, el, api, stage, stats, speech, session, drill

Verified at thread-two close-out:
- Full suite 528 green, ends "ALL GREEN" (backend 203, frontend 325). Frontend =
  114 original classic asserts (7 files, UNCHANGED) + 211 across ten new
  *.module.test.js. Backend 203 unchanged throughout thread two.
- Every module byte-verbatim relocated (function bodies diffed IDENTICAL to the
  inline originals) except the sanctioned S9 renames: `sel`->`selection` in
  session.startSession and drill.questionQuery; `cat`->`catSpan` in
  stats.renderRunLog (CSS class strings "run-cat"/"stats-cat" UNCHANGED).
- The drill<->session cycle resolves green in BOTH import orders (S7 mechanism
  re-confirmed on the real modules): every cross-cycle call targets a hoisted
  function declaration; no module reads another's export at eval time.
- boot.js import fires the boot-guard -> boot() (the ONE module-scope statement,
  S7); clean under --unhandled-rejections=strict with a full fixture.
- index.html UNTOUCHED across all of E1-E9. R1 held: the inline script is still
  authoritative and all 7 classic tests pass against it.
- jsdom resolves 29.1.1 in the clean room; F1 re-confirmed (jsdom does NOT run
  type=module; classic scripts do run).

================================================================================
1. THREAD THREE'S JOB -- E10, the atomic cutover (ONE commit), then close-out
================================================================================
E10 is the single deliberate "let it go red, then green" commit. It MUST stay
WHOLE in one context -- do NOT begin it and pause. Read llm/roadmap-1-
modularization-commit-plan.md Section R (the E10 line) and the ADR-051 addendum
in decisions.md (the E10 guard design, load-bearing -- read it, not skim) before
starting.

E10 does five things in one commit:

  (a) FLIP THE SCRIPT TAG. In index.html, replace the single inline
      `<script>` (currently lines 906-2667, ~1761 lines) with:
          <script type="module" src="boot.js"></script>
      Loading boot.js pulls the whole DAG; the boot-guard starts the app.

  (b) DELETE THE INLINE SCRIPT. Remove the entire inline script body. The ten
      modules already hold verbatim copies, so this deletes the duplication R1
      created. After this, index.html has NO inline JS -- only the module tag.
      (Sanity: the modules were diffed byte-identical to these exact lines, so
      deletion loses nothing. Do a final diff of a couple of functions against
      their module copies before deleting, to be safe.)

  (c) MIGRATE THE 7 CLASSIC TESTS to option (b). The classic tests
      (difficulty, drill, import, speech, stats, stats.integration, timing --
      all runScripts:"dangerously" over the inline page) currently read leaked
      globals: win.state, win.questionQuery, win.submitAnswer, win.loadQuestion,
      win.endSession, win.endSessionOnUnload, win.activeBankLanguage,
      win.canSpeakCurrent, etc. After the cutover jsdom will NOT execute the
      module page (F1), so these globals vanish and all 7 go red. Migrate each to
      the option-(b) shape the ten *.module.test.js already model: build the DOM
      with runScripts:"outside-only", publish window+document (+ fetch /
      navigator / speech stubs as needed), then dynamic-import the real
      module(s) and drive them. The *.module.test.js files are the reference
      implementation of every harness detail (global.navigator publish, the
      speech stubs, the cache-bust re-import trick, the full DOM fixture).
      DECISION TO MAKE (small): the 7 classic tests and the 10 module tests now
      OVERLAP in coverage (e.g. classic drill.test.js vs drill.module.test.js).
      Options: (i) migrate the 7 to option (b) and KEEP them alongside the module
      tests (belt-and-suspenders; some redundancy); (ii) migrate by FOLDING each
      classic test's unique assertions into the corresponding module test and
      deleting the classic file (less redundancy, fewer files); (iii) keep the 7
      as thin behavioral/integration tests and let the module tests carry unit
      coverage. Recommend (ii) where a classic test is now fully subsumed, (i)
      where it exercises a genuinely different path (e.g. stats.integration
      drives a fuller page flow). Whatever you choose, the post-cutover suite
      must be >= the pre-cutover green COUNT and end "ALL GREEN"; state the new
      count and its composition in the commit message.

  (d) LAND THE OWNERSHIP GUARD (the four-check JS/acorn guard). Its exact
      semantics are DECIDED and written in the decisions.md ADR-051 addendum --
      implement to that spec, do not redesign:
        (A) registry integrity (unique ids, non-empty owner in the known-module
            set, no dead keys);
        (B) owner-declares (each node's owner module references the node);
        (C) cross-owner allowlist -- the CHECK WITH TEETH. Any lookup of node X
            by a non-owner module must be in an explicit CROSS_OWNER_READS table.
            The 13 genuine cross-owner reads enumerated during E1 are the initial
            rows; the stage<->drill rows are ABSENT because the E4 flip was
            reversed (choices/feedback stay drill-owned; stage's clearChoices/
            clearFeedback/clearAnd are allowlisted reads). Re-derive the current
            allowlist by attributing every el.<node> read to its module against
            the SHIPPED modules (the E1 attribution script is a model; the set
            may have shifted slightly as functions moved to their real homes --
            recompute, do not trust the old count blindly).
        (D) no DOM at import time (ADR-049) -- no module-scope getElementById /
            el.<key> / document.* outside a function body, with ONE named
            exemption: boot.js's readyState boot-guard. Every other module-scope
            document.* still reddens.
      Implementation surface: JS + acorn in a .test.js (acorn is already on disk
      via jsdom's dependency tree; zero new deps). Scope-aware / symbol-based,
      never a substring grep (S8): strip comments, resolve the receiver so
      member chains on non-el objects (sel.bankId, label.className,
      el.importPanel.textContent) are not counted.
      RED-proofs (mirror the backend C0.1 guard's inject/parse/assert/restore):
      (1) inject an undeclared cross-owner read (e.g. el.statsPanel into a speech
      function) -> check C reddens; (2) inject a module-scope
      document.getElementById into a NON-boot module -> check D reddens (a
      non-boot target so the boot-guard exemption cannot mask it). A guard that
      cannot fail is not a guard: prove GREEN on clean modules AND RED on each
      injection.

  (e) The guard is INTENDED-NOT-ENFORCED until this commit; E10 is where it goes
      live. Only E10's commit message may claim the ownership guard enforces.

After E10: the CLOSE-OUT (may be the same commit or a follow-up -- your call,
but if separate, keep E10 self-contained and green first):
  - Mark roadmap #1 DONE in STATUS.md (update the count; note the ten-module
    as-built DAG). roadmap.md #1 -> DONE.
  - As-built ADRs / knowledge-capture: the S7 ESM fact (cross-cycle hoisted-
    function calls resolve; no eval-time cross-module reads) is the headline
    capture. ADR-049..053 are already recorded; reconcile any "pending" markers.
  - Record the thread-two as-built deviations (Section 3 below) in the plan docs
    in passing if you touch them; otherwise STATUS + this handoff are
    authoritative.

================================================================================
2. WORKFLOW CONTRACT (STANDING -- read carefully; clarified during thread two)
================================================================================
At each commit boundary: edit in-sandbox, run `bash tests/run.sh` (bash, not
sh), COMMIT in-sandbox, then deliver ALL THREE of the following to the user:

  (a) SUMMARY + files-modified list.

  (b) PATCH, delivered as a DOWNLOADABLE FILE. Generate it with
      `git diff <prev_sha> HEAD > /tmp/C-MOD-E10.patch`, rooted at drill/...,
      and surface it to the user with the present_files tool (copy to
      /mnt/user-data/outputs) so they can download and `git apply` it on their
      own clone. The user applies patches to their local repo themselves; do NOT
      assume a shared filesystem. VERIFY the patch applies in a FRESH clone at
      the pinned baseline SHA with the FULL chain of prior thread-three patches
      re-applied, and re-run the suite there -- verify the green COUNT, not just
      the "ALL GREEN" banner.

  (c) COMMIT MESSAGE, provided INLINE IN THE CHAT (not only in git), so the user
      can reuse it verbatim on their clone. Use the project house format
      (see the C-MOD-E1..E8 messages and the thread-one close-out for models):

          type(scope): Subject line in sentence case (tag hint)

            - Bulleted body, "  - " indent, wrapped ~78 cols. Explain WHAT moved
              and WHY, call out any deviation from plan text, note verbatim-ness.
            - More bullets as needed.

            Suite: <before> -> <after> green (composition note). ALL GREEN.
            C-MOD-E10

      i.e. a `type(scope): subject` header; a blank line; "  - " bullets; a blank
      line; a "Suite: X -> Y green (...). ALL GREEN." line; then the bare commit
      tag on its own line. Keep it concise. The scope has been `drill` for the
      code commits. If a message is long, that is fine, but trim ceremony.

  ONE patch per commit; NO push. If E10 and close-out are separate commits,
  deliver the triple for EACH.

NOTE on git identity: the sandbox has no default git identity. Set one before
the first commit, e.g. `git config user.email "..." && git config user.name
"..."`, or `git commit` fails with "Author identity unknown".

================================================================================
3. AS-BUILT DEVIATIONS FROM PLAN TEXT (thread two) -- trust this over plan text
================================================================================
The plan/design docs predate execution. Where they conflict with this section
(and STATUS + decisions.md), this section wins.

E-1  TEN MODULES, NOT EIGHT/NINE. Section R lists nine frontend modules; the
     older C/D/E section lists eight. As built there are TEN: the plan's list
     plus el.js. el.js (EL_REGISTRY + the lazy accessor) was carved out at E4 as
     the shared DOM leaf because stage.js was the first module to need el and
     every later DOM module needs it too; el had no home module in the plan text.
     It is a leaf (imports nothing; no DOM at import time -- getElementById fires
     lazily inside the getter).

E-2  NAMING: option-(b) module-isolation tests are <module>.module.test.js, NOT
     <module>.test.js (C-MOD-E-naming). Four module names collide with the
     pre-existing classic tests (timing/speech/stats/drill), which are part of
     the authoritative suite and stay untouched under R1. The .module infix is
     collision-proof and self-documents the two test kinds. A DEFERRED,
     non-blocking tidy is recorded in Section R: the trivial leaf tests
     (state+api+timing) may later merge into one leaves.module.test.js -- take it
     post-E10 if convenient.

E-3  SESSION+DRILL LANDED AS ONE COMMIT (C-MOD-E7), covering the plan's E7 AND
     E8. The drill<->session cycle (S6) is a true bidirectional import; neither
     module is importable without the other, so there is no valid green
     intermediate with only one side. boot was therefore tagged C-MOD-E8 (not
     E9) to keep the tags contiguous. Net: the plan's E1-E9 map onto commit tags
     C-MOD-E1..E8 (+ E-naming). E10 keeps its name.

E-4  AS-BUILT IMPORT EDGES differ from Section R's one-line summaries:
     - speech imports state + el (Section R said "state, stage"); it calls zero
       stage functions.
     - session imports state, el, api, stage, stats, speech, drill (Section R
       said "state, stage, api, stats"); speech + drill (the cycle) are added.
     - drill imports state, el, api, stage, speech, timing, session.
     - boot imports from all eight non-boot modules.
     These are the measured edges; the DAG in Section 0 is authoritative.

E-5  E4 OWNER-FLIP REVERSED. The pre-E1 plan to flip choices/feedback owner
     drill->stage at E4 was SUPERSEDED after enumerating write sites: drill stays
     the dominant manipulator of both nodes, so the flip would only reverse a
     cross-owner edge and lengthen the allowlist. Tags stay owner:"drill"; stage's
     teardown verbs are allowlisted at E10. (Full rationale in decisions.md
     ADR-051 addendum.) Consequence honored: E4 touched no index.html.

E-6  E10 GUARD IS FOUR CHECKS + A BOOT EXEMPTION, in JS/acorn. Fully specified in
     the decisions.md ADR-051 addendum. The literal "only the owner may reference
     node X" reading is WRONG (13 genuine cross-owner reads exist by design); the
     guard uses an explicit CROSS_OWNER_READS allowlist instead. Check D exempts
     exactly boot.js's boot-guard.

================================================================================
4. DOWNSTREAM CONCERNS (not blocking E10, but track)
================================================================================
- The DEFERRED leaf-test consolidation (E-2) is sanctioned and non-blocking.
- The thin DOM seam (setText/show/hide/makeButton) that ADR-051's relabel notes
  as deferred is still deferred -- E10 lands the ownership (lookup) guard, not a
  DOM-mutation quarantine. Do not claim the DOM is fenced when only lookup is.
- CODING_CONVENTIONS HTML/CSS section (Section R close-out line) is still to be
  written if it matters to you; not required for a green E10.
- The two raw fetch() sites outside the api seam (endSessionOnUnload keepalive
  in session.js; onImportSubmit multipart in boot.js) are intentional (E2 flag).
  If the E10 guard ever grows a "fetch only in api" check, these two are the
  named exceptions -- but no such check is specced now.

================================================================================
5. QUICK-START CHECKLIST FOR THREAD THREE
================================================================================
1. Sparse-clone drill/ at the pinned SHA; verify HEAD == SHA and branch.
2. `uv sync --group test`; `npm install jsdom --no-save` (Node 18+; expect
   jsdom 29.1.1); `bash tests/run.sh` -> confirm 528 green, "ALL GREEN".
   (If the count differs on a clean clone at the pinned SHA, STOP and report --
   that is a bad starting state, not something to patch around.)
3. Read Section R's E10 line + the decisions.md ADR-051 addendum (guard spec) +
   S6/S7 in findings (the cycle) before writing anything.
4. Execute E10 WHOLE (do not pause mid-cutover): flip tag, delete inline script,
   migrate the 7 classic tests, land the ownership guard + no-DOM-at-import
   guard, prove GREEN + the RED-proofs. Keep the suite count >= 528-equivalent
   after accounting for whatever test-consolidation choice you make; end
   "ALL GREEN".
5. Deliver the triple (Section 2): summary, downloadable patch (present_files),
   inline house-format commit message.
6. Close out: STATUS.md (#1 DONE), roadmap.md, knowledge-capture (S7 ESM fact),
   reconcile ADR markers. Deliver its triple too if a separate commit.
