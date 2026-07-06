# Feature Backlog 2026-07 -- New Candidates (captured before they're lost)

STATUS: CAPTURE + quantitative scoring. These are ideas raised while planning
after Thread N. Each is scored on the EXISTING six-axis model (roadmap.py,
CANDIDATES_2026_07 block; weights unchanged) and framed qualitatively here. This
doc is the writeup the code comments point to. Nothing here is committed to a
thread yet -- it is a ranked, reasoned backlog to fold into the roadmap.

Run `python3 roadmap.py` for the live table; scores below are from that model.

================================================================================
0. THE ORGANIZING INSIGHT: GENERABLE vs AUTHORED
================================================================================
Almost every idea here sorts onto one of two existing rails, and WHICH rail is
the main scoping decision:

  GENERABLE -- a generator emits infinite instances. This is the ARITHMETIC
    rail. Verified code fact: the expression EVALUATOR and RENDERER already
    recurse over nested operator trees; the OPERATOR TABLE is data-driven. So a
    new integer operator (bitwise, etc.) is a data-row + eval-rule addition that
    REUSES the whole tree machinery. Grading is numeric/exact.

  AUTHORED/STATIC -- a finite set of hand-picked (or imported) problems, stored
    and recall-scheduled. This is the SM2/BANK rail (Docs C + E). No generator;
    the value is CONTENT. Grading is identify/free_response/MC (all exist).

The user's own instincts matched this precisely: "word problems ... more SM2
type," "calculus ... only as expressions not problems," "trivia ... general
trivia type." The dividing question for each item is: can a small generator
emit correct instances with a checkable answer? Yes -> arithmetic rail. No (or
only with a CAS / templating / curation) -> authored rail.

A THIRD axis cuts across both: GRADING MODE. Several generable items are blocked
not by generation but by grading -- they need a numeric-within-epsilon mode
(geometry/trig, units) or a symbolic/canonical mode (algebra solve-for-x). The
epsilon-grading seam is a small, reusable unlock that several items share.

================================================================================
1. RANKED CANDIDATES (from roadmap.py, tiers by the same cutoffs)
================================================================================
TIER 1 (>=3.70 -- do-soon candidates, competitive with the current top tier):
  4.04  Bitwise arithmetic (AND/OR/XOR/NOT/shifts)
  3.90  Sets & boolean logic (merge with roadmap #9 discrete-structures)
  3.72  Pre-algebra/algebra solve-for-x (linear first)

TIER 2 (3.20-3.69):
  3.50  Multimodal: images in questions (cross-cutting enabler)
  3.36  Number-base conversion (bin/oct/hex/dec)
  3.32  Textbook word problems (authored, SM2)
  3.28  UI/QOL: keyboard-first flow + shortcuts
  3.26  Geometry/trig: evaluate-the-expression (needs epsilon grading)
  3.26  Unit / dimensional-analysis drill

TIER 3 (2.70-3.19):
  3.04  Calculus / advanced-math (authored; generation deferred)
  3.04  Field trivia (biochem/genetics; authored/imported)
  2.90  UI/QOL: session review screen
  2.78  UI/QOL: responsive + mobile-friendly layout

TIER 4 (<2.70 -- defer/note):
  2.68  Multimodal: audio prompts (exploit existing TTS first; defer stored audio)

================================================================================
2. THE GENERABLE ITEMS (arithmetic rail -- cheapest, highest LEARN)
================================================================================
BITWISE ARITHMETIC (4.04, T1) -- the standout.
  Yes, "bit arithmetic" is the right idea; the usual name is bitwise operations.
  It is exactly your instinct: tree-based generation with different operators.
  &, |, ^ are binary; ~ is unary; <<, >> are binary with a shift operand. All
  are integer operators -> add operator-table rows (eval rule, precedence,
  operand strategy) and the existing generator/evaluator/renderer handle the
  rest. The ONLY real new work is DISPLAY: showing operands and the expected
  answer in binary or hex (a base toggle), because bitwise drills are pointless
  in decimal. LEARN is maximal (two's complement, bit width, C-like precedence).
  RECOMMENDATION: strong Tier-1 candidate; the cheapest new drill with the most
  teaching. Design Q's: operand base display (bin/hex/dec), fixed bit width vs
  arbitrary, whether ~ needs a declared width to be well-defined.

SETS & BOOLEAN LOGIC (3.90, T1) -- MERGE with roadmap #9.
  Set ops are bitwise over a universe; boolean logic is bitwise over one bit.
  This overlaps the existing #9 (logic/deduction: truth tables, syllogisms,
  3.80). RECOMMENDATION: do NOT add as a separate item -- fold into a single
  "discrete structures" drill (boolean eval + set ops + truth tables) sharing a
  small generator, adjacent to bitwise. High LEARN, no UI novelty.

PRE-ALGEBRA / ALGEBRA: SOLVE-FOR-X (3.72, T1) -- start linear.
  Generating an equation is easy (pick integer roots, expand). The HARD part is
  grading a symbolic answer. RECOMMENDATION: ship LINEAR first (x = a single
  number -> grades exactly like arithmetic, no new grading tech), constrain to
  integer/rational roots so the answer is exact-matchable, and DEFER quadratic/
  symbolic (multiple roots, factored forms) until a canonical-answer grading
  mode exists. This makes a Tier-1-value item accessible at arithmetic-level
  effort by scoping to the easy half.

NUMBER-BASE CONVERSION (3.36, T2).
  Generable but NOT via the tree engine -- it is a single-value transform, not an
  expression. A tiny standalone generator (pick n, pick base pair). Natural
  SIBLING of bitwise; fold into that thread as a second qtype for near-free.

GEOMETRY / TRIG: EVALUATE-THE-EXPRESSION (3.26, T2) -- the epsilon-grading unlock.
  Per your instinct: generable only as EXPRESSIONS to compute (sin(30)=?, area
  of a triangle, hypotenuse from legs), NOT as proofs/constructions (those are
  authored/multimodal). The blocker is GRADING: float answers need a
  numeric-within-tolerance mode. That epsilon-grading seam is small and REUSABLE
  (units, any future decimal answer want it), so this item's real value is partly
  the seam it forces. Design Q: exact-value trig (sin30 = 1/2, exact-matchable)
  vs decimal-with-tolerance.

UNIT / DIMENSIONAL ANALYSIS (3.26, T2).
  Generable; numeric grading; reuses the epsilon seam from geometry. A practical
  sibling of base-conversion. Modest but clean.

================================================================================
3. THE AUTHORED ITEMS (SM2/bank rail -- content, not engine; Docs C + E)
================================================================================
CALCULUS / ADVANCED MATH (3.04, T3) -- DEFER generation; enable via authoring.
  Your read is exactly right: generable "only as expressions, unclear how hard."
  Generating a well-formed derivative/integral WITH a checkable answer is a
  symbolic-math (CAS) problem -- genuinely hard, RISK 2, EFFORT 2 for true
  generation. RECOMMENDATION: do NOT build a generator. Enable calculus as
  AUTHORED static problems on the SM2/bank path (finite, hand-picked, recall-
  scheduled). Then it costs almost nothing beyond writing problems, and the
  high LEARN is realized through curation rather than code. This is the clearest
  case of "authored beats generated."

FIELD TRIVIA -- biochem, genetics, etc. (3.04, T3) -- authored/imported.
  General-trivia-shaped: static Q/A, gradable via identify/free_response/MC (all
  exist). No new engine; value is CONTENT. Overlaps roadmap #23 (trivia
  importers). Belongs to Doc D (import) + Doc E (author) + SM2 scheduling. The
  "different fields" framing does not need per-field code -- it needs per-field
  content in banks/categories, which already model this.

TEXTBOOK WORD PROBLEMS (3.32, T2) -- authored; the difference IS the generation.
  You asked what makes them different from arithmetic. The answer: the
  GENERATION. A rich multi-step word problem is not template-generable without
  templating/NLG tech (adjacent to AI-content #27). So they are AUTHORED static
  problems, SM2-scheduled, graded free_response/numeric -- which is exactly why
  your "more SM2-type" instinct is correct. The distinction you sensed is real
  and it is precisely the generable/authored line.

================================================================================
4. MULTIMODAL (cross-cutting enabler -- gates several items above)
================================================================================
IMAGES IN QUESTIONS (3.50, T2) -- warrants its OWN design doc.
  Verified: media_url ALREADY exists in the question payload and schema (present
  but under-used). Rendering an <img> is small. The real work is AUTHORING/
  STORAGE: where do image bytes live for a single-user local tool? -- filesystem
  refs vs data URIs vs a media table -- and how the import format carries them.
  FOUND 3 because it unblocks geometry DIAGRAMS, image trivia, alphabet/
  handwriting, geography. RECOMMENDATION: a MINIMAL first cut (render an image
  from a path/URL already in media_url; no new authoring) proves the render path
  cheaply; the storage/authoring expansion is a separate, design-heavy step.
  This is the item most worth a dedicated design doc, because its storage
  decision constrains everything downstream.

AUDIO PROMPTS (2.68, T4) -- exploit existing TTS first.
  Harder than images (storage + playback + authoring). BUT: speech SYNTHESIS
  already exists (speech.js). So "listen to a synthesized word, type it" is
  cheap and needs NO stored audio -- it reuses TTS. RECOMMENDATION: split this:
  (a) TTS-driven listening drills = near-free, worth doing with images;
  (b) stored-audio clips = expensive, defer. Enables pronunciation/listening and
  music (#30) drills down the line.

================================================================================
5. UI / QUALITY OF LIFE (value rises with SM2 + multimodal + content)
================================================================================
KEYBOARD-FIRST FLOW + SHORTCUTS (3.28, T2) -- best QOL value.
  A drill tool lives or dies on input friction. Enter-to-submit exists; add
  grade-keys (for the SM2 0/1/2 prompt when it lands), skip, reveal-hint (N.1).
  Cheap, high daily value, RISK 5. Its value RISES once SM2 adds a grade step,
  so it pairs naturally with Thread C. A good quick-win bundle with other QOL.

RESPONSIVE / MOBILE LAYOUT (2.78, T3) -- pair with the CSS conventions doc.
  The HTML/CSS convention section is still unwritten (flagged at modularization
  close-out; the study track owns it). A responsive pass + writing those
  conventions together is a natural pairing -- do the work and codify it at once.
  Value rises with multimodal (images/media need layout rules). So SEQUENCE this
  AFTER or WITH images, not before.

SESSION REVIEW SCREEN (2.90, T3) -- depends on Doc A.
  An end-of-session recap (what you got, what to review) built on the stats seams
  Doc A adds (most-missed, over-time). Low risk; a nice capstone to stats-depth.
  Do it after Doc A lands.

================================================================================
6. RECOMMENDATIONS -- what to promote, what to defer
================================================================================
PROMOTE toward the near-term roadmap (high value, low cost, reuse proven seams):
  - BITWISE ARITHMETIC (4.04): the single best new item. A "math-fields" thread
    could bundle bitwise + number-base + (linear) algebra as generable siblings
    on the arithmetic rail -- one thread, three drills, all data+eval additions.
  - Fold SETS & BOOLEAN into roadmap #9 as one discrete-structures drill.
  - The EPSILON-GRADING seam (needed by geometry/trig + units) is a small
    reusable unlock worth doing once, then both items are cheap.

DEFER but NOTE (recorded here + in roadmap.py so they are not lost):
  - CALCULUS generation (do it authored via SM2 instead).
  - AUDIO stored clips (do TTS-driven listening first).
  - RESPONSIVE layout until multimodal defines the layout needs.

DESIGN-DOC-FIRST (decision-heavy, do not build blind):
  - MULTIMODAL IMAGES -- its storage/authoring decision is foundational; give it
    a design doc like the B/C/D/E handoffs. It interacts with Doc E (authoring
    format must carry media) and Doc D (converters may emit media refs).

DEPENDENCY EDGES (for sequencing):
  - epsilon-grading --unblocks--> geometry/trig + units.
  - multimodal-images (storage decision) --unblocks--> geometry DIAGRAMS,
    image trivia, alphabet, geography; --interacts-with--> Doc E authoring format.
  - SM2 (Doc C) --raises-value-of--> keyboard grade-keys + authored calculus/
    trivia/word-problems (they are the content SM2 schedules).
  - Doc A stats --unblocks--> session-review screen.
  - HTML/CSS conventions (study track) --pairs-with--> responsive layout.

HOW THIS FOLDS INTO THE EXISTING PLAN:
  - The generable math items (bitwise/base/algebra) are a clean NEW THREAD that
    is arithmetic-rail work -- low risk, high learn, independent of SM2. It could
    slot BEFORE or ALONGSIDE the SM2 line (Doc C), and is a good "re-warm-up"
    thread of the kind ADR-054 favored.
  - The authored items (calculus/trivia/word-problems) need Docs C + E first;
    they are content, so they arrive FOR FREE once the SM2/authoring rail exists.
  - Multimodal + UI/QOL are cross-cutting; schedule images (design-doc-first)
    near the content work, QOL keyboard-flow near SM2, the rest as capstones.
