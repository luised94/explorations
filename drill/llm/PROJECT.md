DRILL -- PROJECT INSTANCE RULES
===============================
date: 2026-07
scope: the rules that are TRUE OF DRILL and are not generalizable to
other projects. Everything here is an INSTANCE rule: at render time it
wins conflicts with playbook items (precedence.md chain 1), and it
leads the rendered CONTEXT.md.

  PROJ code: DRILL   (naming.md; thread ids take the form
                      DRILL-ROLE-NNN, e.g. DRILL-IMPL-004)

WHAT THIS FILE IS NOT
  It is not a style document. General code style -- naming, control
  flow, limits, abstraction, docs, delivery -- lives in the playbook
  style contract and reaches a thread through the render, cited by
  clause id (S1..S25, D1..D3). Do not restate a style clause here.
  A rule belongs here only if it would be WRONG to apply to another
  project.

  It is not live status. What is done, what is next, and the current
  baseline live in drill/llm/STATUS.md and are never restated here
  (S21).

PROVENANCE OF THE STYLE DEVIATIONS
  Drill's style was adapted from TigerBeetle's TigerStyle and NASA's
  Power of Ten rules for safety-critical code. Those target a Zig
  systems database; drill is a single-user Python + SQLite +
  vanilla-JS practice tool. Three rules were deliberately NOT carried
  over, and the playbook records them as deviations D1-D3 without
  saying where they came from. The reasoning, so it is not
  re-litigated:
    - RECURSION is allowed (D1). The no-recursion rule exists to bound
      stack growth statically in safety-critical systems. Here the
      expression evaluator, renderer, and generator all recurse over
      operator trees; the trees are small, depth is config-bounded by
      operator_depth, and the recursive form mirrors the data.
    - NO FUNCTION-LENGTH CEILING (D2). TigerStyle's ~70-line rule is a
      screen-real-estate heuristic, not a correctness rule.
    - NO STATIC-ALLOCATION OR ZERO-DEPENDENCY MANDATE (D3).
      Dependencies pass through the quarantine rule (S14) instead.
  Design goals, in order: SAFETY (correctness + defense in depth),
  then PERFORMANCE, then DEVELOPER EXPERIENCE. Readability is table
  stakes, not the goal.

ARCHITECTURE -- THE LAYERING INVARIANT
  Five layers, and the import direction is what enforces them:
    CONFIG    scalars only. Operator data is scalar (symbol, name,
              arity, operand ranges, forbid_identity values, the
              enabled-by-default symbol list). No callables.
    DATABASE  IO over a connection. No logic.
    LOGIC     pure. No IO, no DB, no HTTP. Assembles the operator
              table once at import as the module-level constant
              OPERATORS, validating at build time that every enabled
              symbol has a config entry, an eval function, and an
              operand generator -- so a typo fails loudly at import.
    HTTP      thin glue, and the ONLY layer that reads the clock.
    MAIN      startup.
  Import direction: http imports db + logic; logic imports config; db
  imports config; NOTHING imports http. Data crosses boundaries as
  plain dicts, lists, and scalars. The join key between CONFIG and
  LOGIC is the operator symbol string.
  (Refined by drill's own ADR-008 [v2], which resolved the earlier
  tension of function-valued dicts sitting in a "pure data" CONFIG.)

VALIDATION AND BOUNDS
  - External input is validated through the _require_int /
    _optional_int -> _BadParameter -> HTTP 400 path. Those exception
    types carry error data, not behavior. Bad external input is an
    expected operating condition, never a crash and never an
    assertion (S9, S10 give the general rule; this names drill's
    concrete mechanism).
  - sqlite3.IntegrityError is caught at the boundary rather than
    escaping as a 500.
  - Named bounds in this project: operator_depth (recursion depth),
    max_result_value, _EXPONENT_POWER_RANGE.
  - The server is STATELESS per question: it holds no "current
    question". /api/question returns a payload the client echoes back
    to /api/answer, and the server re-runs validation on the echo
    rather than trusting it.

PYTHON CONVENTIONS SPECIFIC TO DRILL
  - Module-level constants are UPPER_SNAKE (DIFFICULTY_RUNGS,
    SCHEMA_VERSION); module-private helpers are _leading_underscore.
  - Modern type hints on function signatures.
  - Timestamps are passed into LOGIC and DATABASE as ISO-8601 strings
    and compared lexicographically; the clock is read only in HTTP
    (and init_db).

FRONTEND CONVENTIONS SPECIFIC TO DRILL
  - Vanilla JS. No framework, no build step. After modularization: ES
    modules loaded via <script type="module">; state is a single
    shared object imported where needed, never a store or observable.
  - Live in-session state and durable DB history are SEPARATE sources
    that never share a render path (the stats-bar vs stats-view rule).
  - A toggleable element that sets an explicit `display` MUST carry
    the matching `.x[hidden] { display: none; }` guard IN THE SAME
    COMMIT. Otherwise the explicit display overrides the [hidden]
    attribute and the element will not hide. Stated this sharply
    because it was violated once, by the import panel.
  - A new DOM node in the el registry is owned by the module that is
    its DOMINANT MANIPULATOR, not by where it visually sits. When
    exactly one module reads the node, set owner == that module: no
    CROSS_OWNER_READS row is needed and the ownership guard stays
    green with no policy change. Prefer this owner == sole-reader
    shape; reach for a cross-owner row only when a second module
    genuinely must read a node another module owns. (Ratified from
    the Thread N.1 hint-reveal node, which is drill-owned because
    drill both renders and clears it.)
  - No browser storage (localStorage / sessionStorage) and no
    persistence across reloads unless it becomes a deliberate,
    app-wide feature. "Reload is a clean slate" is the current model.

TEST HARNESS CONSTRAINTS
  jsdom does NOT model the CSS cascade for [hidden] versus an explicit
  display, and its performance.now is a read-only getter. Tests
  therefore assert DOM STRUCTURE, ATTRIBUTES, and stylesheet RULE
  TEXT -- never cascade-resolved visual layout, and never concatenated
  textContent where structure is the point.

DEFERRALS
  Zero-technical-debt in spirit: when a real problem is found, fix it
  while the code is hot rather than deferring. A deliberate deferral
  is recorded as an inert comment-block scaffold at the site where the
  code would live, stating what, why, and why deferred -- visible, not
  silent. (CONVENTION-006 gives the general pattern; the practice is
  standing policy here.)
