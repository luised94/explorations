# Drill Tool -- Knowledge Capture (Layered)

A durable extraction of the wisdom, rules, patterns, and state developed across
this project, classified per the layer protocol. Each item sits in exactly one
layer, placed at its most persistent level (Persona > Constraint > Criteria >
Convention > Instruction > Context). Strategy, Skills, Principles, and Unsure
follow.

Companion artifacts (in outputs): THREAD_LAUNCH_KIT.md (reusable context +
per-thread prompts), PHASE0_PLAN.md (execution detail), ROADMAP.md +
roadmap_model.py (the scoring model), dependency_plan.mermaid (the DAG),
spec.md + decisions.md (the living project record).

ASCII only.

---

## PERSONA  (user preferences -- voice, depth, communication mode; rarely changed)

- Concise by default; lead with the answer, minimal preamble. Substance over
  hedging.
- No platitudes. When asked for critique or review, deliver real, specific,
  adversarial critique -- name the actual flaw and the fix, do not soften into
  generic advice.
- Surface tradeoffs and judgment calls explicitly; the user wants to see the
  reasoning and the places where reasonable people would disagree, not just the
  conclusion.
- Apprehensive of premature abstraction as a matter of taste, not just policy:
  prefer the concrete, the data-oriented, the legible. Treat indirection,
  reification, and generalization as costs that must be earned.
- The user values learning the underlying tech/math/cs, not just shipping. When
  relevant, explain the principle a piece of work demonstrates.
- All output ASCII only.

---

## CONSTRAINTS  (boundaries -- always/never; stable across projects)

- NEVER abstract, reify, or generalize prematurely. Build the concrete case;
  extract a seam only after two real uses reveal the shared shape. (Speculative
  generality is a defect.)
- NEVER introduce classes, DAOs, repositories, service layers, dependency
  injection, or ABCs unless a concrete, present duplication forces it. Prefer
  module-level functions over plain data (dicts, lists, scalars).
- ALWAYS keep the layering invariant: CONFIG = scalars only; DATABASE = IO over
  a connection, no logic; LOGIC = pure (no IO/DB/HTTP); HTTP = thin glue and the
  ONLY layer that reads the clock; MAIN = startup. Data crosses boundaries as
  plain dicts/lists/scalars.
- NEVER let DATABASE call LOGIC or HTTP; NEVER let LOGIC call DATABASE or HTTP.
  Enforced by import direction in the package form: http imports db+logic; logic
  imports config; db imports config; nothing imports http.
- NEVER silently edit a frozen backend. If a need exposes a real backend gap,
  raise it and amend the spec first.
- ALWAYS produce code only when explicitly asked, and only what the cited commit
  describes -- never anticipate future commits.
- ALWAYS produce the COMPLETE updated file when modifying existing code (not a
  diff/snippet).
- NEVER ship a commit without a real test verifying it; ALWAYS report pass/fail
  before the user accepts.
- Single-user ALWAYS: no concurrency, auth, multi-tenant, or connection-pooling
  concerns enter the design.
- ALL code and prose ASCII only.

---

## CRITERIA  (decision functions -- how to choose between options; stable across projects)

- Score and sequence are different questions. Rank by value (multi-axis), but
  ORDER by dependency and learning-leverage. It is correct for the highest-value
  item to be sequenced second (e.g. modularize is #1 by score but follows one
  arithmetic round, so you refactor code you understand cold).
- When prioritizing, use weighted multi-axis scoring (the roadmap_model.py
  pattern), then run a sensitivity check across alternate weightings; trust the
  ranking only where it is stable to reasonable re-weighting.
- Place the safety net before the change it protects: tests precede the work
  that stresses them (Carmack). A net built after the fall is worthless.
- Prefer the cheapest item that unblocks the most downstream work (foundational
  leverage) when two items score similarly.
- For a new feature, ask first: "is this a projection of the structure I already
  have?" Add a new representation only for the case that genuinely does not
  project (e.g. spatial answers), and carry that case in a JSON slot, not a new
  hierarchy.
- The varying axis is usually not the obvious one. (Across drill types, the prompt
  is not what varies -- the grading kind is. Find the real axis before modeling.)
- Modularization is a learning/maintainability win, not a performance or
  correctness win -- be honest about why a change is being made; do not dress a
  legibility change as an optimization.
- Effort score is necessary but not sufficient: weigh whether an item changes
  what the tool IS (Victor's lens -- a mastery map changes the user's relation
  to their knowledge) against whether it is merely cheap.
- When docs and code disagree, the docs lost -- treat drift as the documents
  lying to each other, and prefer structures that make drift impossible
  (link/transclude, never copy) over discipline that merely tries to prevent it.

---

## CONVENTIONS  (patterns to follow consistently -- naming, formatting, structure; within project)

- Commit-ID discipline: every change is a commit C-0xx; mark changed regions with
  commit-ID comments; threads own disjoint ID ranges to avoid collision.
- Maintain spec.md and DECISIONS.md as living records: append (do not rewrite)
  non-spec decisions and flags per commit, tagged [DECIDED]/[NOTE]/[FIX]/[OPEN].
  Version-stamp status lines ([v7], [v8], ...) and mark superseded notes rather
  than deleting history.
- Live project STATUS (what is done, what is next, the baseline + green count)
  lives in llm/STATUS.md and NOWHERE else: roadmap.md, knowledge-capture.md, the
  launch kit, and the handoffs LINK to it rather than restating it. When status
  changes, edit STATUS.md only. (This is the anti-drift discipline made
  structural -- duplicated status is what kept going stale.)
- Code follows llm/CODING_CONVENTIONS.md (TigerStyle/NASA-adapted: full
  descriptive names, no abbreviations bar noun-like domain terms, standard
  control flow, explicit limits, validate-at-boundary, assertions for
  programmer-error invariants only; recursion allowed where natural; no
  function-length ceiling). New code conforms; touched code is brought into
  conformance as it is touched.
- Stale status comments that a commit's existence invalidates ARE corrected in
  that commit (in scope); stale comments unrelated to the commit are flagged in
  DECISIONS but left untouched (out of scope). Hold this line explicitly.
- Backend file layout: one module per section (config/db/logic/http/main),
  names preserved, flat functions inside, no re-export hub in __init__.
- Frontend file layout: ES modules (state/api/drill/session/stats/speech/timing/
  boot) loaded via <script type="module">; no build step, no framework; state is
  a single shared object imported where needed (never a store/observable).
- Quarantine weird external dependencies behind a tiny wrapper that is the ONLY
  code touching them (the speechSynthesis precedent: speak/cancelSpeech).
- Clock is read only in HTTP (and init_db); pass timestamps into LOGIC/DATABASE
  as ISO strings; compare ISO-UTC strings lexicographically.
- Optional integer params parse through a shared helper that yields a 400 on bad
  input (the _optional_int / _BadParameter pattern), never a raw int() that 500s.
- Empty/time-zero is a handled case, never an asserted-away one: summaries return
  zeros and empty lists rather than dividing by zero.
- Live in-session state and durable DB history are SEPARATE sources that never
  share a render path (the stats bar vs. the stats view rule).
- Toggleable UI elements with an explicit display need the [hidden]{display:none}
  guard, folded into the commit that introduces them (the documented gotcha).
  [v-2U: this was VIOLATED -- the import panel shipped without it and silently
  would not close; caught and fixed in C-2U-d. Proof that the convention is
  right and that disciplinary conventions still get missed. A lint/grep check
  "every .X{display:...} toggleable rule has a matching .X[hidden]" would make
  it structural rather than disciplinary -- a candidate for the modularization
  thread, where the CSS is on the table.]
- A read endpoint that feeds a UI control returns STRUCTURAL FACTS, not
  user-facing copy: the server owns what exists and its shape, the client
  composes the human label from those facts. (C-2U: /api/difficulty-rungs
  returns {rung, depth, recurse, ceiling}; index.html builds "Rung N - nested,
  to CEILING".) Keeps presentation in the presentation layer and stops the two
  sides re-encoding each other's domain; also means the label can change without
  a server deploy. Prefer this over an endpoint that invents a label field the
  underlying config does not have.
- Deferred-but-real future paths are recorded as inert comment-block scaffolds at
  the site they would live, explaining what/why/how-deferred (the C-018b pattern).

---

## INSTRUCTIONS  (phase-specific behavior during particular work types)

- Starting a new thread: attach the standing four (spec.md, decisions.md, backend,
  frontend) + PHASE0_PLAN.md for design work; read the relevant spec/DECISIONS
  sections BEFORE coding so you match existing patterns rather than inventing.
- Before any file/code work: read the relevant skill/spec section first; do not
  start from memory of how the code probably looks -- verify against the file.
- When building a scheduler/policy: implement each one CONCRETELY with exactly
  the inputs it needs; do NOT design a generalized context object up front.
  Extract the shared seam only after two concrete policies exist (Muratori).
- When generating the curriculum: link into real code and DECISIONS by anchor;
  never copy/restate them (Nelson). Structure each module read -> explain
  (Feynman) -> extend (effortful retrieval).
- When extending arithmetic: operators are pure data additions (near-zero risk);
  the generator generalization is the real cs work. [v-2U: this is now DONE (#5)
  -- generate_expression recurses over operator trees; evaluator, renderer, AND
  generator all recurse, depth 1 reproducing the old flat form. The "only the
  generator is flat" note that used to live here is obsolete.] Difficulty is a
  pure params mapping on top. Use property-based tests for generator invariants.
- When doing a comment-only/docs commit: prove inertness by AST-equality against
  the prior file (only docstrings/comments may differ).
- When a change is frontend-only or backend-only: prove the other half is
  byte-identical and its test suite still passes.
- Adversarial review protocol: run candidate plans past operational lenses
  (Acton: where is the data, what shape, how hot; Carmack: is the safety net
  under the change, be honest about why; Muratori: is this speculative
  generality, build concrete then compress; Victor: where is the seeing, does it
  change what the tool is; Nelson: are these documents going to drift, link
  don't copy). Treat disagreements with the current plan as the signal; fold the
  resulting reprioritizations back in.

---

## CONTEXT  (project-specific knowledge and state; per-project handoff)

- The tool: single-user practice/drill app. Backend drill.py (Bottle, ~2250
  lines, sections CONFIG/DATABASE/LOGIC/HTTP/MAIN). Frontend index.html (~2380
  lines, one script block pre-modularization). Sample banks: trivia CSV,
  vocabulary JSONL.
- Status: see llm/STATUS.md, the single source of truth for what is done and
  what is next (this CONTEXT section deliberately does NOT restate live status,
  to stop the drift that kept recurring). At time of writing: roadmap #2/#4/#5/
  #8/#11 done, #20 in progress (this doc cleanup), modularization (#1) next.
- Architecture is genuinely extension-ready and this was verified, not assumed:
  operator table is data-driven (add dicts); pick_next_question is a single
  swappable selection seam; questions.difficulty and responses.elapsed_ms columns
  exist; expression evaluator, renderer, AND generator now all recurse over
  nested trees (the generator was generalized in #5; depth 1 is the flat form);
  server host is env-overridable (DRILL_HOST);
  sessions.config and banks.metadata are unused '{}' JSON slots ready for use;
  LOGIC verified to have zero DB/bottle references.
- Known gaps / next-phase foundations [MOSTLY CLOSED since archive, v-2U]: the
  three foundational gaps recorded at archive are now closed -- checked-in tests
  exist (the tests/ suite, 311 green; #8 done); the migration runner reads
  schema_version and applies ordered forward-only ALTERs (run_migrations +
  MIGRATIONS registry + import-time consistency guard; #11 done); and
  questions.metadata was added by the v2 migration (no longer a gap). The one
  stale drill.py header line ("MAIN/stats arrive with C-019") was fixed in
  C-019a. Remaining real gap: qtype still conflates prompt-kind with
  grading-kind (the data-model finding below), unaddressed.
- [v-2U] tests/run.sh discovers frontend tests via an EXPLICIT hand-maintained
  list (for t in drill.test.js speech.test.js ...), not a glob. Every new test
  file must be added to that list or it silently does not run -- a real papercut
  hit twice this thread (difficulty.test.js, import.test.js). Fix deferred to the
  modularization thread (where the test layout is on the table): replace the list
  with a glob over tests/frontend/*.test.js and a simple skip convention
  (leading-underscore files do not run) so adding a test is zero-config. Low
  risk, ~3 lines; deferred only to avoid test-infra surgery on a feature branch.
- [v-2U] roadmap #2 (difficulty control) is COMPLETE end to end as of C-2U-a..d:
  backend+data path (C-D2a..i) plus the UI selector, active-rung badge, and
  arithmetic-only gating. ADR-047 closed. Suite at 311 green (backend 197,
  frontend 114). The next core-thread step is modularization (#1 by score,
  sequenced after the arithmetic round per the score-vs-sequence criterion).
- Data-model finding: every drill type projects onto the general
  prompt->answer(+alternatives,distractors,hints,media,tags,difficulty) record
  EXCEPT geography point-on-map (spatial answer). The real axis is grading kind
  {string-equality, numeric, speed, spatial, set/order}; qtype currently
  conflates prompt-kind with grading-kind.
- Open item carried forward: the no-feedback "speed drill" mode (needs a
  pending-results buffer; changes the loop's feedback timing) -- always outside
  the initial plan; its own future commit.
- Deferred with reason: SpeechRecognition pronunciation (ADR-006, cloud/flaky);
  multi-user/auth (scope); Catalan-number tree sampling (overkill, attaches to
  the generator if ever wanted); handwriting canvas; AI-generated content.
- Launch order at archive: Wave 0 = TEST(C-020, first), MIGRATE(C-021),
  DOCS(C-022), ARITH operators(C-023), mistake-review(C-038), mastery grid(C-039).
  Full waves in THREAD_LAUNCH_KIT.md Section 2.

---

## STRATEGY

- Two active threads at a time is the human throughput sweet spot: keep one core
  thread (arithmetic, then modularize) and one orthogonal thread (data-model or a
  drill) going, chosen so they rarely touch the same files. "Parallel" = switch
  without blocking, not literally simultaneous.
- Sequence to refactor code you just touched: do a content round (arithmetic)
  before the structural round (modularize), so the seams are obvious and the
  refactor is of familiar code.
- Foundation-first within a phase even against raw score: tests and the migration
  runner precede feature work because every feature either stresses the logic
  (wants tests) or adds columns (wants migrations).
- Build concrete, then compress: write two real implementations before extracting
  any shared abstraction; let the seam reveal itself (applies to schedulers, and
  generally).
- Make drift structurally impossible rather than disciplining against it: link
  documents, single-source status, AST-prove inertness -- because discipline
  alone has already failed twice (stale status lines).
- Pull an identity-changing item forward even if cheap-on-paper undervalues it:
  a minimal mastery grid seeds the "seeing your knowledge" mode and is worth more
  than its effort score suggests.
- Keep the backend frozen between sanctioned changes; unfreeze deliberately for a
  single scoped commit (the C-019a precedent), then refreeze.

---

## SKILLS

- Verification harnesses (reusable patterns, recover into a tests/ dir):
  - Backend: load the real module against a temp DB, drive endpoints via the WSGI
    app (start_response must accept the optional exc_info third arg), assert on
    the JSON envelope. (test_c019a.py is the template.)
  - Frontend: jsdom with runScripts:"dangerously", stub fetch + speechSynthesis +
    sendBeacon, control performance.now via Object.defineProperty (jsdom's is a
    read-only getter), assert against DOM structure not concatenated textContent.
    (test_c018a/c.js, test_c019b.js are templates.)
    [v-2U: jsdom does NOT model the CSS cascade for [hidden] vs an explicit
    display rule -- it reports getComputedStyle().display === "none" for a hidden
    element whether or not the .X[hidden]{display:none} guard exists. So a
    "computed display" assertion CANNOT catch a missing-guard visibility bug; it
    passes either way. To test a cascade-dependent visibility fix, assert the
    STYLESHEET RULE is present (collect <style> textContent, regex the rule),
    which is the actual fix and is verified to fail without it. General rule:
    jsdom tests assert structure, attributes, and stylesheet text -- never
    cascade-resolved visual layout.]
  - Integration: drive the real frontend (jsdom) against the real backend handler
    (child-process WSGI over a seeded temp DB). (test_c019_integration.js.)
  - Inertness proof: ast.parse both file versions, strip the module docstring,
    compare ast.dump -- proves a change is comment/docstring-only.
  - Boundary purity check: walk the AST of a function, collect Call node names,
    assert no cross-layer calls (no bottle/connection/clock in LOGIC).
  - Property-based: hypothesis on the arithmetic generator invariants (integer
    result, no forbidden identity) -- one targeted high-value use, not blanket.
- Decision analysis: weighted additive multi-axis scoring with an explicit weight
  vector summing to 1.0, then a sensitivity sweep across alternate weightings to
  test rank stability. roadmap_model.py is the reusable engine -- SAVE IT and
  re-run / re-weight / re-score for any future prioritization (edit WEIGHTS and
  ITEMS; it prints the ranking and tiers; sensitivity.py shows stability).
- Topological planning: encode work as a dependency DAG (mermaid), compute launch
  waves by repeatedly emitting all nodes whose deps are satisfied; distinguish
  hard edges from soft (preference) edges.
- Operational-expert adversarial review: instantiate Acton/Carmack/Muratori/
  Victor/Nelson as no-platitude critique lenses (data shape / safety-net-first +
  honesty / anti-speculative-generality / does-it-change-what-it-is / anti-drift)
  and harvest concrete reprioritizations and missed features from where they
  disagree with the plan.
- ASCII-glyph technique: use HTML entities (e.g. &#9658;) to render symbols while
  keeping source ASCII-only.

---

## PRINCIPLES

- Data-oriented design: know where the data is, its shape, how much, how often
  touched; let access patterns drive structure. For tiny, cold structures,
  choose clarity deliberately (and say so).
- Pure core, IO at the edges: the testable, reasoned-about value lives in pure
  transformations; impurity is pushed to the boundary and quarantined.
- One-way dependency boundaries make a codebase legible and safely modularizable;
  the boundary is only real if it is enforced (import direction, purity checks).
- Speculative generality is a cost, not a virtue. The seam you design before you
  need it is usually the wrong seam. Compress out abstraction from concrete cases.
- The safety net belongs under the change before the change is made.
- Honesty about why: name the real reason for a change (learning, legibility,
  correctness, performance) and do not dress one as another.
- A model should be a projection of what things actually are; find the true axis
  of variation before adding representation, and add new representation only for
  what genuinely does not project.
- Make the right thing structural, not disciplinary: if a class of mistake keeps
  happening (drift), change the structure so it cannot, rather than trying harder.
- Tools can change what the user can SEE and therefore think (Victor); a feature
  that changes the user's relationship to their own knowledge outranks polish.
- Documents that restate each other will diverge; link/transclude instead
  (Nelson). Single-source every fact.
- Retrieval, spacing, interleaving, faded scaffolding, and desirable difficulty
  are the load-bearing mechanisms of learning; a curriculum is built from them,
  not from re-reading.

---

## UNSURE  (could not confidently place, or genuinely ambiguous)

- Exact effort estimates (the "~1-1.5 days" figures): useful as relative sizing,
  but they assume the user's pace and may not generalize -- treat as ordinal, not
  literal. (Leans Context, but it is really an assumption about the user.)
- Whether SM2 state belongs in the questions.metadata JSON slot or a dedicated
  review table: flagged in the plan as a decision to make AT implementation time
  with the SM2 source in hand -- deliberately left open, not yet a convention.
- The commit-ID numbering for the next phase (C-020..C-039): a suggestion for
  disjointness, not a fixed contract -- the user may renumber. (Leans Convention
  but is provisional.)
- Whether the mastery grid should stay minimal or grow toward full Mode D: the
  review pulled the minimal version forward, but the ceiling is a judgment the
  user should make once they see the seed in use.
