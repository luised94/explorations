STYLE CONTRACT
==============
date: 2026-07
version: 0.1.0
scope: the diff-checkable coding standard. Every clause is written
so a reviewer can point at lines of a diff and say "this clause,
violated" -- no clause is a vibe. Project-specific invariants (for
example a project's module layering and import-direction rule) do
NOT live here; they belong in that project's PROJECT.md and reach
threads through the render.

LINEAGE
  Adapted from TigerBeetle's TigerStyle and NASA's Power of Ten
  rules for safety-critical code. Where a rule does not transfer
  to small single-author tools, this contract keeps the SPIRIT
  and marks the deviation explicitly (see DEVIATIONS). Design
  goals in order: safety (correctness plus defense in depth),
  then performance, then developer experience.

NAMES
  S1. FULL descriptive names. NEVER abbreviate or truncate,
      except established domain acronyms read universally as
      words: USB, URL, ID, HTTP, HTML, CSS, SQL, JSON, CSV, TTS,
      UTC, API, DOM, UI. When in doubt, write it out: response
      not resp, connection not conn, index not idx.
  S2. A helper called by exactly one function is prefixed with
      its caller's name (parse_import -> parse_import_row), so
      the call graph is legible from names alone.
  S3. Booleans read as assertions (is_ready, has_entries);
      collections read as plurals (entries, categories). NEVER
      overload one name with context-dependent meanings.
  S4. Related names take the same length where natural so they
      read as a set: source/target, first/final, before/after.

CONTROL FLOW
  S5. Standard, boring control flow. NEVER a clever or idiomatic
      trick unless a measured performance or memory need demands
      it -- and then a comment states the measured need.
  S6. The empty, zero, or absent case is handled explicitly:
      NEVER asserted away, NEVER a crash. Summaries return zeros
      and empty collections rather than dividing by zero.
  S7. NEVER split a coherent function only to satisfy a length
      number; NEVER forbid recursion where the data is naturally
      recursive (see DEVIATIONS for both).

LIMITS AND VALIDATION
  S8. Everything that can grow has a named, explicit limit
      (max_result_value, retry_ceiling). NEVER an implicit or
      unstated bound.
  S9. Parse and validate at the boundary; trust the parsed value
      inside. Bad EXTERNAL input is an expected operating
      condition: it gets a clean, typed error to the caller,
      NEVER a crash and NEVER an assertion.
  S10. Assertions are for PROGRAMMER-error invariants only --
      states the code believes impossible. NEVER use an
      assertion for input validation or control flow; in
      runtimes that can strip assertions (Python -O), a
      validating assert is a correctness hole.
  S11. Split compound assertions -- assert(a); assert(b) -- so a
      failure names the exact clause.

ABSTRACTION
  S12. NEVER abstract, reify, or generalize prematurely: build
      the concrete case and extract a seam only after two real
      uses reveal the shared shape.
  S13. NEVER introduce classes, DAOs, repositories, service
      layers, dependency injection, or abstract base classes
      unless a present, concrete duplication forces it. Prefer
      module-level functions over plain data (dicts, lists,
      scalars).
  S14. Quarantine an awkward external dependency behind a tiny
      wrapper that is the ONLY code touching it.

STATE AND BOUNDARIES
  S15. In-memory state has one source of truth; NEVER duplicate
      state into a UI surface and read it back -- render FROM
      state.
  S16. A read endpoint feeding a UI control returns STRUCTURAL
      FACTS; the presentation layer composes the human-facing
      words. NEVER have the server invent a label field the
      underlying data does not carry.
  S17. The clock is read at the designated boundary layer only;
      timestamps cross internal boundaries as ISO-8601 strings
      and compare lexicographically.

DOCS AND COMMENTS
  S18. A docstring on every function: what it does, why it
      exists, any non-obvious invariant. Comments state the WHY,
      never restate the WHAT.
  S19. Changed regions carry the governing plan's commit id in a
      comment where the file format admits comments.
  S20. A stale comment invalidated by the current commit is
      corrected in that commit; a stale comment unrelated to the
      commit is flagged in the decisions record, NEVER silently
      fixed and NEVER silently left.
  S21. Live status lives in the project's STATUS.md only; NEVER
      restated in code comments or other documents -- link
      instead.

DELIVERY
  S22. Code is produced only when explicitly asked, scoped to
      the cited commit or task; NEVER anticipating future
      commits.
  S23. A modified file is delivered COMPLETE (or as an applying
      patch when the human asks for patch form); NEVER a bare
      snippet the human must splice by hand.
  S24. Every commit ships with a real test and a reported
      pass/fail count; NEVER "should work".
  S25. All code and prose ASCII only.

DEVIATIONS (spirit kept, letter changed; each states its reason)
  D1. Recursion is allowed where the problem is naturally
      recursive. The TigerStyle/NASA no-recursion rule bounds
      stack growth statically in safety-critical systems; in
      small tools with config-bounded depth, the recursive form
      mirrors the data and is the legible choice.
  D2. No hard function-length ceiling. The ~70-line rule is a
      screen-real-estate heuristic, not a correctness rule;
      prefer short single-purpose functions as taste, but a
      coherent function is never split to hit a number.
  D3. No static-allocation or zero-dependency mandate; those
      target systems software. Dependencies instead pass through
      S14's quarantine rule.
