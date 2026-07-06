# Drill Tool -- Coding Conventions

The enforceable coding standard for this project. The spec already mandates the
spirit ("full variable names", "docstrings on every function"); this file makes
it specific and checkable. New code conforms; code touched during refactors is
brought into conformance as it is touched (especially during modularization,
where each extracted module gets a style pass for free).

Lineage: adapted from TigerBeetle's TigerStyle and NASA's Power of Ten rules for
safety-critical code. Those guides target a Zig systems database; this is a
single-user Python + SQLite + vanilla-JS practice tool. Where a rule does not
transfer (static allocation, zero dependencies beyond a toolchain, a hard
function-length ceiling), this file keeps the SPIRIT and says so explicitly
rather than copying the letter. Design goals, in order: SAFETY (correctness +
defense in depth), then PERFORMANCE, then DEVELOPER EXPERIENCE. Readability is
table stakes, not the goal -- the goal is code that works and keeps working.

ASCII only, in code and in prose.

================================================================================
SHARED (apply to both drill.py and index.html)
================================================================================

NAMES
- Great names capture what a thing IS or DOES, with enough domain information to
  build a correct mental model from the name alone. Names are the essence of the
  code; spend effort here.
- FULL descriptive names. No abbreviations or truncations EXCEPT established
  domain terms that behave like nouns and are universally read as whole words:
  USB, URL, ID, HTTP, HTML, CSS, SQL, JSON, CSV, TTS, UTC, API, DOM, UI. When in
  doubt, write it out (`response` not `resp`, `connection` not `conn`,
  `category` not `cat`, `index` not `idx`).
- Related names use the SAME length where natural, so they line up in the source
  and read as a set (source/target, first/final, before/after). Do not overload
  one name with context-dependent meanings.
- A helper called by exactly one function is prefixed with that caller's name to
  show the call history (e.g. parse_import -> parse_import_row). This makes the
  call graph legible from names alone.
- Booleans read as assertions (is_arithmetic, has_banks); collections read as
  plurals (rungs, categories).

CONTROL FLOW
- Standard, boring control flow. No clever or idiomatic tricks UNLESS a measured
  performance or memory need demands it -- and then a comment states the need.
  Optimize for the reader who has never seen the code, not for brevity or
  cleverness. (DX is a design goal; cleverness is usually its enemy.)
- Handle the empty / zero / absent case explicitly; never assert it away. (The
  established pattern: summaries return zeros and empty lists, never divide by
  zero.)
- Recursion IS allowed when the problem is naturally recursive (the expression
  evaluator, renderer, and generator all recurse over operator trees -- that is
  the right shape for the domain). This is a deliberate DEVIATION from the
  TigerStyle/NASA no-recursion rule, which exists to bound stack growth
  statically in safety-critical systems; here the trees are small, depth is
  config-bounded (operator_depth), and the recursive form mirrors the data.
- NO hard function-length ceiling (another deliberate deviation -- TigerStyle's
  ~70-line rule is a screen-real-estate heuristic, not a correctness rule).
  Prefer short, single-purpose functions as a matter of taste, but do not split
  a coherent function just to hit a number.

LIMITS AND SAFETY
- Put a limit on everything that can grow; everything has a limit. Bounds and
  ceilings are explicit and named (max_result_value, operator_depth,
  _EXPONENT_POWER_RANGE), not implicit.
- Parse and validate at the boundary; trust the parsed value inside. Bad EXTERNAL
  input is an expected operating condition and gets a clean error to the caller
  (HTTP 400), never a crash and never an assertion.
- Be honest about WHY a change is made (safety / performance / legibility /
  correctness). Do not dress a legibility change as an optimization.
- Zero-technical-debt in spirit: when a real problem is found, fix it now while
  the code is hot, rather than deferring -- but record deliberate deferrals (the
  inert-scaffold-comment pattern) so they are visible, not silent.

ABSTRACTION
- No premature abstraction. Build the concrete case; extract a shared seam only
  after two real uses reveal the shape. No classes / DAOs / service layers /
  dependency injection / ABCs unless a present, concrete duplication forces it.
  Prefer module-level functions over plain data. (This is the project's standing
  stance and the local equivalent of TigerStyle's minimal-surface-area rule.)

DOCS AND COMMENTS
- A docstring on every function: what it does, why it exists, and any non-obvious
  invariant. Comment the WHY, not the WHAT.
- Mark changed regions with their commit-ID (C-0xx). Correct a stale comment that
  the current commit invalidates; flag (do not silently fix) unrelated stale
  comments elsewhere.
- Live status lives in STATUS.md only; never restate it in code comments or other
  docs (link instead).

================================================================================
PYTHON-SPECIFIC (drill.py, tests/*.py)
================================================================================
- Keep the layering invariant: CONFIG = scalars only; DATABASE = IO over a
  connection, no logic; LOGIC = pure (no IO/DB/HTTP); HTTP = thin glue and the
  ONLY layer that reads the clock; MAIN = startup. Data crosses boundaries as
  plain dicts/lists/scalars. Import direction enforces it: http imports db+logic;
  logic imports config; db imports config; nothing imports http.
- `assert` is for PROGRAMMER-error invariants only (a state the code believes is
  impossible). NEVER use `assert` for input validation or control flow -- Python
  run with -O strips asserts, so a validating assert is a security/correctness
  hole. External validation goes through the _optional_int / _BadParameter ->
  400 pattern.
- Prefer splitting compound assertions: assert(a); assert(b) over assert(a and b)
  so a failure points at the exact clause. (TigerStyle assertion hygiene that
  does transfer.)
- Modern type hints on function signatures; docstrings on every function.
- Module-level constants are UPPER_SNAKE (DIFFICULTY_RUNGS, SCHEMA_VERSION);
  module-private helpers are _leading_underscore.
- The clock is read only in HTTP (and init_db); pass timestamps into LOGIC /
  DATABASE as ISO-8601 strings and compare them lexicographically.
- Quarantine any awkward external dependency behind a tiny wrapper that is the
  only code touching it.

================================================================================
JS-SPECIFIC (index.html, tests/frontend/*.js)
================================================================================
- Vanilla JS, no framework, no build step. After modularization: ES modules
  loaded via <script type="module">; state is a single shared object imported
  where needed (never a store/observable).
- `state` is the single source of in-memory truth; do not duplicate state into
  the DOM and read it back. Render FROM state.
- Live in-session state and durable DB history are separate sources that never
  share a render path (the stats-bar vs stats-view rule).
- A toggleable element that sets an explicit `display` MUST carry the matching
  `.x[hidden] { display: none; }` guard in the same commit -- otherwise the
  explicit display overrides the [hidden] attribute and the element will not
  hide. (This convention was violated once, by the import panel; the fix is the
  reason it is stated this sharply.)
- A read endpoint that feeds a UI control returns STRUCTURAL FACTS; the client
  composes the user-facing label from them. The server owns what exists and its
  shape; the presentation layer owns the words.
- A new DOM node in the el registry is owned by the module that is its DOMINANT
  MANIPULATOR, not by where it visually sits. When exactly one module reads the
  node, set owner == that module: no CROSS_OWNER_READS row is needed and the
  ownership guard stays green with no policy change. Prefer this owner==sole-
  reader shape when adding a UI node; reach for a cross-owner row only when a
  second module genuinely must read a node another module owns. (Ratified from
  the Thread N.1 hint-reveal node, which is drill-owned because drill both
  renders and clears it.)
- No browser storage (localStorage/sessionStorage) and no persistence across
  reloads unless it is a deliberate, app-wide feature -- "reload is a clean
  slate" is the current model.
- jsdom (the test harness) does NOT model the CSS cascade for [hidden] vs an
  explicit display, and its performance.now is a read-only getter. Tests assert
  DOM structure, attributes, and stylesheet RULE TEXT -- never cascade-resolved
  visual layout, and never concatenated textContent where structure is the point.

================================================================================
HOW THIS IS CHECKED
================================================================================
- Today: by review and by the test suite (every commit ships a real test and
  reports the green count, not just the banner).
- RUNTIME VERIFICATION: green tests + a followed spec are NOT sufficient for
  changes to how code loads, packages, starts, routes, or crosses the
  client/server boundary. For those, smoke-test the REAL path end to end before
  "done" (start the server, open the URL, confirm every asset the page pulls
  returns 2xx with the right content type). This convention exists because the
  E10 cutover shipped 555 green tests and still broke the app -- the tests
  bypassed the one path the cutover changed. See llm/verification-practices.md
  for the failure, the practice, and a cutover/load-path checklist.
- Planned (modularization thread): AST-level guards that make the conventions
  structural rather than disciplinary -- a boundary-purity check (no
  bottle/connection/clock Call nodes inside LOGIC), and where expressible, a
  naming/idiom lint. The principle: any convention that keeps getting missed is
  converted into a check rather than a sterner reminder.
