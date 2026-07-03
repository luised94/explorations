# Study Curriculum + Coding-Conventions Formalization (parallel track)

Purpose: the operating doc for the PARALLEL work that runs alongside the feature
threads (roadmap #3, study curriculum, plus the JS/Python/HTML/CSS conventions
formalization). It is NOT a standalone phase and NOT a reason to pause feature
work -- it is the comprehension THROTTLE: features ship at LLM speed, this forces
human-speed reading of what shipped. ADR-054 fixed this as parallel.

ASCII only. Single-user.

================================================================================
0. WHAT THIS TRACK IS (and what it is not)
================================================================================
Two intertwined outputs, produced together so each disciplines the other:
  1. STUDY CURRICULUM (roadmap #3): the codebase-as-textbook -- "read this
     layer, here's the principle it demonstrates, now extend it yourself."
     Raw material: the commit history, the ADRs, the layered structure.
  2. CODING CONVENTIONS: explicit JS/Python/HTML/CSS guidelines, DERIVED from
     what the code actually does (ratify or consciously override each pattern),
     not written in the abstract and retrofitted. Home: CODING_CONVENTIONS.md.

The method: walk the modules in dependency order and, per module, (a) UNDERSTAND
it (concern, patterns, why these seams) and (b) INTERROGATE each pattern against
the audit axes (Section 2). Each answer becomes a ratified rule, a flagged
deviation-to-fix, or a curriculum entry. The guide writes itself from evidence;
the study produces an artifact instead of evaporating.

Anti-avoidance rule (ADR-054): pure study is off the table. This track only
advances by auditing REAL code -- ideally each feature thread's FRESH code, which
teaches more per hour than re-reading code already understood from a prior
thread.

================================================================================
1. THE CRITICAL DISTINCTION: SEMANTICS (facts) vs CONVENTIONS (choices)
================================================================================
Keep these in SEPARATE sections of any guide. A style guide governs conventions;
it must RESPECT semantics but cannot legislate them. Writing a "rule" for a
semantic is wasted effort or, worse, an unfollowable rule.

SEMANTICS = runtime rules you cannot change, only design around. The ES-module
ones this project has already hit (record in knowledge-capture.md, which already
has the S7/ESM entries; reference from the guide, do not restate as "rules"):
  - Single-evaluation / caching: a module's top-level runs ONCE per identity;
    every importer shares the SAME exported instance (why `state` is a shared
    singleton; the design lever is singleton-vs-factory, not caching on/off).
  - Module identity = resolved URL: `./x.js` and `./x.js?b=1` are DIFFERENT
    modules (the cache-bust divergence; lever: reset state, don't re-import).
  - Live bindings + hoisting + TDZ: imports are live references; `function`
    declarations are hoisted (so cross-cycle calls resolve mid-eval), but reading
    another module's const/let at eval time throws (why the drill<->session cycle
    is safe: cross-refs are hoisted functions inside bodies -- ADR-053).
  - Bare globals resolve to the HOST: bare `performance`/`document` resolve to
    Node's global under the option-(b) harness, not window (why nowMs reads
    global.performance).
  - Module scripts defer + jsdom does not execute them (why option (b) exists).

CONVENTIONS = choices you make about code you write. Examples already surfaced:
  - Encapsulation & invocation boundaries (the drafted rule -- Section 3).
  - `for` loop vs `forEach` for straightforward iteration (prefer `for` for
    readability/debuggability; forEach's inability to break/continue/await and
    its sparse-array skipping are ADDITIONAL reasons, not the primary one -- and
    note those edge cases brush against semantics).
  - Naming, error handling, comment density, import direction, DOM lookup vs
    mutation, async patterns.

TEST for which bucket: "If I wrote the opposite rule, would the runtime stop me?"
Yes -> semantic (don't legislate it; document the fact). No -> convention.

================================================================================
2. THE PER-FILE AUDIT AXES (the checklist -- run every module through these)
================================================================================
Sketch the axis SET before going file-by-file so file 1 and file 10 get the same
scrutiny. Each axis: the question it forces + where a "yes/deviation" answer goes
(ratify / fix-backlog / curriculum entry). A "SEMANTICS TOUCHED" flag per finding
keeps facts and choices separated as you go (Section 1).

  A. ENCAPSULATION & INVOCATION -- is each function/IIFE/block justified, or
     wrapper-by-habit? (Section 3 is the drafted rule.) One-shot startup should
     be top-level statements or a {} block; a function only for privacy,
     deferral, reuse, or a named pure unit.
  B. NAMING -- do names say what the thing is/does? Any single name serving two
     meanings (the complection tell)? JS-side naming debt (sel/cat historically)?
  C. ERROR HANDLING -- fail loud vs silent; are error paths explicit and at the
     right layer? (e.g. build_question_payload fails loudly on missing keys.)
  D. IMPORT DIRECTION / DEPENDENCY -- one-way DAG respected? Any cross-boundary
     read that should be a seam? (The ownership guard enforces the el side.)
  E. DOM LOOKUP vs MUTATION -- lookups behind el; mutations behind stage helpers?
     Is any DOM touched at import time (ADR-049; guard check D)? (The thin DOM-
     MUTATION seam is still deferred -- a known candidate this audit will surface.)
  F. ASYNC PATTERNS -- await vs fire-and-forget; are async lifecycles (speech
     cancel, load transitions) correct and observable?
  G. STATE OWNERSHIP -- single master (state) with DOM rendering FROM it, never
     read back (adversarial lens 9)? Any state stashed in the DOM?
  H. COMMENT DENSITY / LOCALITY -- can you understand the thing by reading the
     thing (locality of behavior), or must you chase files? Are comments carrying
     decisions that belong in an ADR?
  I. AFFORDANCE TRUTH (UI files) -- perceived state = real state ([hidden] guard);
     semantic elements so the tag reads the affordance.
  SEMANTICS-TOUCHED (flag, not an axis): does this finding actually concern a
     runtime fact (Section 1)? If so it is documentation, not a rule.

SCOPE guidance (do not formalize four languages equally): go DEEP on JS (highest
uncertainty; the modularization churned it). Do a LIGHTER pass on Python
(conventions are largely settled and inherited from the backend-split ADRs) to
capture what is already implicit. Treat HTML/CSS as a SHORT appendix (smaller
surface; the CODING_CONVENTIONS HTML/CSS section flagged at the modularization
close-out lives here). Trying to do all four comprehensively at once yields a
large low-density document.

================================================================================
3. DRAFTED RULE: ENCAPSULATION & INVOCATION BOUNDARIES (axis A)
================================================================================
DEFAULT (JS and Python): code that executes exactly once, at startup, and does
not need a private scope to protect external names, is written as DIRECT
STATEMENTS -- not wrapped in a function. A wrapper adds indirection (jump to
definition, jump back); prefer linear top-level flow unless a concrete reason
forces indirection.

A wrapper (function or IIFE) is justified ONLY when:
  - a return value must be kept PRIVATE from the enclosing scope (a closure over
    a cache), OR
  - it is called MULTIPLE times (reuse), OR
  - it must run at a specific LATER time (event handler, callback, DOM-ready), OR
  - it defers SIDE EFFECTS that must wait (DOM queries depending on readiness),
    OR
  - it is a pure, reusable, named unit worth documenting/testing.
If none apply, inline it (a comment names the block; no wrapper for naming alone).

PATTERNS:
  - IIFE returning a value: OK if privacy is required (closure over cache);
    else a {} block with let/const, or plain top-level statements.
  - Named function defined then immediately called: AVOID (an IIFE with a
    needless name) -- extract-and-call if reusable, else inline. EDGE CASE (to
    ratify): a NAMED genuine IIFE where the name documents a non-obvious
    construction -- allowed or not? (el.js's buildEl -- see audit result below.)
  - Plain {} block for scoping: PREFERRED when you only need to confine let/const.
  - Top-level statements: for all startup that needs no private scope.
  - Factory returning an object with private state: OK when state must be
    encapsulated; name it, call once if singleton.

AUDIT RESULT (first pass, all ten JS modules -- the rule HOLDS, two edge cases):
  - el.js IIFE (buildEl, lines ~63-78): JUSTIFIED -- returns getters closing over
    a private `cache`; the "privacy required" exception. EDGE: it has a name on
    the IIFE. Ratify the "named genuine IIFE" question in the guide.
  - boot.js boot-guard (if document.readyState...): JUSTIFIED -- top-level
    statements (not a wrapper) that DEFER execution; the "later time" exception.
  - speech.js speechAvailable (top-level const from window): fine by the rule
    (one-shot, no wrapper) BUT interacts with the single-evaluation SEMANTIC
    (frozen at first import -- why the speech-absent test needed re-evaluation).
    Curriculum entry: "compute-once at top level vs single-evaluation."
  - All other modules: clean -- no IIFE-by-habit, no named-then-called
    antipattern, zero stray top-level statements outside boot.

================================================================================
4. HOW THE CURRICULUM ACCRETES (the parallel loop)
================================================================================
Per feature thread that lands:
  1. Read the thread's DIFF and its commit messages/ADRs at human speed.
  2. Run the touched files through the axes (Section 2); record ratified rules
     into CODING_CONVENTIONS.md, deviations into a fix-backlog, semantics into
     knowledge-capture.md.
  3. Write the curriculum entry: "this thread demonstrates <principle>; read
     <files>; now extend it by <exercise>." (e.g. N.1 hints demonstrates the
     el-ownership + guard workflow for adding a UI node; N.2 timing-stats
     demonstrates the pure-summary + render split.)
  4. Comprehension checkpoint: can you explain the thread's change WITHOUT the
     diff in front of you? If not, that is the signal to audit deeper before
     moving on.

The fix-backlog feeds an eventual deferred-cleanup thread (the DOM-mutation seam,
leaf-test consolidation, any convention deviations found). Do not refactor
inline during the audit -- record, batch, and schedule.

================================================================================
5. DOCUMENTS THIS TRACK UPDATES
================================================================================
  - CODING_CONVENTIONS.md -- PRIMARY: the ratified rules + the JS-SPECIFIC block
    + the HTML/CSS section (still to be written). Keep a "Runtime semantics
    (facts, not choices)" part clearly separated, OR reference knowledge-capture.
  - knowledge-capture.md -- the semantics facts (already has S7/ESM; add as
    found).
  - decisions.md -- a new ADR only when the audit produces a DECISION (e.g.
    "named IIFEs allowed when they name a non-obvious construction"). Do not
    pre-write; let the audit generate them.
  - STATUS.md -- a marker while this track is active (already noted under NEXT
    as the parallel track).
  - roadmap.md -- mark #3 progress; do not close until the curriculum exists.
  - This file -- the running index of audit findings + curriculum entries.
