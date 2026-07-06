"""Quantitative decision-analysis model for the drill-tool roadmap.

Weighted additive scoring across six axes. Each item is scored 1-5 per axis;
the weighted sum gives a priority score. Weights encode the user's stated goals
(learning the underlying tech/cs/math, extending arithmetic, modularization,
adding drills, SM2 consolidation) balanced against engineering value.

Axes (and why each is weighted as it is):
  USER  user-stated priority / alignment with what they said matters most.
        Highest weight -- they explicitly said "prioritize the things I think
        are important then balance."
  LEARN learning value: how much building it teaches the underlying tech,
        math, and cs. Second highest -- a stated primary goal of the project.
  FOUND foundational leverage: does it unblock or de-risk many later items?
        (A high score means lots of downstream work depends on it.)
  EFFORT inverse effort: 5 = trivial, 1 = large multi-week. (Already inverted
        so higher is better, consistent with the other axes.)
  QUAL  code/product quality: correctness, robustness, maintainability,
        documentation -- the "is this a quality codebase" axis.
  RISK  inverse risk: 5 = safe, well-understood, low chance of derailment;
        1 = architecturally invasive or research-y with real failure modes.

All weights sum to 1.0. Scores are the author's estimates grounded in a read
of the actual code (clean layering, data-driven operator table, swappable
pick_next_question, existing difficulty/elapsed_ms columns, env-overridable
host, etc.), which materially raised several EFFORT/RISK scores.
"""

WEIGHTS = {
    "USER": 0.28,
    "LEARN": 0.22,
    "FOUND": 0.18,
    "EFFORT": 0.14,
    "QUAL": 0.10,
    "RISK": 0.08,
}
assert abs(sum(WEIGHTS.values()) - 1.0) < 1e-9, "weights must sum to 1.0"

# item: (USER, LEARN, FOUND, EFFORT, QUAL, RISK)
# Scores 1-5. EFFORT and RISK are pre-inverted (higher = less effort / safer).
ITEMS = {
    # --- Engineering-quality items I'm adding (not in the user's list) ---
    "Automated test suite checked into the repo": (3, 4, 5, 3, 5, 5),
    "Module docstring/status drift cleanup + ADR index": (2, 2, 3, 5, 4, 5),
    "Assertion/invariant pass (boundary + pre/postconditions)": (2, 4, 3, 4, 5, 5),
    "Structured logging + error envelope audit": (2, 3, 3, 4, 4, 5),
    "Schema migration runner (version-aware ALTER)": (3, 4, 4, 3, 4, 4),
    "JSONL export/backup endpoint + button": (3, 2, 3, 4, 4, 5),
    # --- User's stated priorities ---
    "Extend arithmetic: operators (^, mod, etc.)": (5, 4, 3, 5, 4, 5),
    "Extend arithmetic: difficulty (digits/#ops/operators)": (5, 5, 4, 4, 4, 4),
    "Generalize expression generation (nested trees)": (5, 5, 3, 4, 4, 4),
    "Adaptive question selection (swap pick_next_question)": (4, 5, 4, 3, 3, 4),
    "Study curriculum from the codebase": (5, 5, 4, 3, 4, 5),
    "Modularize: extract JS modules + split Python": (5, 5, 5, 3, 5, 3),
    "Consolidate SM2 (spaced repetition) engine": (5, 5, 4, 2, 3, 3),
    # --- Adding the other drills ---
    "Typing/text-entry speed drill": (4, 3, 3, 4, 3, 4),
    "Logic/deduction drill (truth tables, syllogisms)": (4, 5, 3, 3, 3, 4),
    "Code drill (what does this output?)": (4, 4, 3, 4, 3, 4),
    "Geography visual mode (point-to on a map)": (3, 3, 2, 2, 3, 3),
    "Music interval/rhythm drill": (2, 3, 2, 2, 3, 3),
    "Alphabet/romanization drill": (3, 3, 2, 4, 3, 4),
    "Grammar exercises (fill-in / reorder)": (3, 4, 2, 3, 3, 3),
    # --- Timing / speed (plumbing already exists) ---
    "Timed-round / speed-drill mode (use elapsed_ms)": (4, 3, 3, 4, 3, 4),
    "Timing stats (compute/display elapsed_ms)": (3, 3, 2, 4, 3, 5),
    # --- Content / data pipelines ---
    "Trivia importers (OpenTriviaDB/QA, Freebase)": (3, 2, 3, 3, 3, 4),
    "Vocabulary importers (CodingFriends, doozan)": (3, 2, 3, 3, 3, 4),
    "wordfreq frequency ranking integration": (2, 3, 2, 3, 3, 4),
    "AI-generated content (server-side API)": (3, 3, 2, 3, 2, 2),
    "Dictionary/encyclopedia dump pipeline": (2, 3, 2, 1, 2, 2),
    # --- Stats / UX depth ---
    "Stats depth: most-missed, over-time, per-bank": (3, 3, 3, 3, 3, 4),
    "Chart.js rendering in stats view": (2, 2, 1, 4, 3, 4),
    "Dashboard (live stats beside drill, Mode C)": (3, 3, 2, 3, 3, 3),
    "Mastery map / explorable space (Mode D)": (4, 4, 3, 1, 3, 2),
    "In-browser bank editor": (2, 2, 2, 2, 3, 3),
    "Handwriting canvas (CJK/Arabic/Devanagari)": (2, 3, 1, 1, 2, 2),
    # --- Infrastructure ---
    "Document 0.0.0.0/WSL binding (already env-overridable)": (2, 1, 2, 5, 3, 5),
    "Pronunciation via SpeechRecognition (deferred)": (1, 2, 1, 2, 2, 1),
    "Multi-user / auth / pooling (out of scope)": (1, 2, 1, 1, 2, 1),
}


def score(vals):
    keys = ["USER", "LEARN", "FOUND", "EFFORT", "QUAL", "RISK"]
    return sum(WEIGHTS[k] * v for k, v in zip(keys, vals))


ranked = sorted(ITEMS.items(), key=lambda kv: score(kv[1]), reverse=True)

print("%-2s %-52s %5s  %s" % ("#", "Item", "Score", "U L F E Q R"))
print("-" * 86)
for i, (name, vals) in enumerate(ranked, 1):
    print("%-2d %-52s %5.2f  %d %d %d %d %d %d" % (i, name[:52], score(vals), *vals))

# Emit a compact CSV-ish block for the writeup table.
print("\n--- TIERS (by score) ---")
for name, vals in ranked:
    s = score(vals)
    tier = "1" if s >= 3.7 else "2" if s >= 3.2 else "3" if s >= 2.7 else "4"
    print("%s\t%.2f\tT%s" % (name, s, tier))


# ===========================================================================
# CANDIDATE BACKLOG 2026-07 (user-suggested, post-Thread-N)  -- see
# llm/feature-backlog-2026-07.md for the qualitative writeup of each.
# ===========================================================================
# New candidates raised while planning after Thread N. Scored on the SAME six
# axes / weights (unchanged). Grounded in the code survey facts already in this
# file, plus these additional verified facts about the arithmetic engine:
#   - The expression EVALUATOR and RENDERER already recurse over nested operator
#     trees; only the GENERATOR shape and the OPERATOR TABLE define what exists.
#     A new BINARY/UNARY operator over integers is a data-row + eval-rule add,
#     reusing the whole tree machinery. (This is why bit-arithmetic is cheap.)
#   - qtypes are data-driven (translate/identify/free_response/multiple_choice);
#     a "static expression/problem" that is stored+graded like a bank question
#     needs NO new generator -- it is content on the SM2/bank path.
# The dividing line that recurs below: GENERABLE (a generator emits infinite
# instances -> arithmetic-style, tree engine) vs AUTHORED/STATIC (a finite set
# of stored problems -> SM2/bank path, Doc C + authoring Doc E). Which side an
# idea lands on is the main scoping question, and it is called out per item.
CANDIDATES_2026_07 = {
    # --- GENERABLE: reuse the arithmetic tree engine (operator-table adds) ---
    "Bitwise arithmetic drill (AND/OR/XOR/NOT/shifts)": (
        (4, 5, 3, 4, 4, 4), None,
        "GENERABLE. Bitwise ops are integer binary/unary operators: add rows to "
        "the operator table (&, |, ^, ~, <<, >>) with eval rules + precedence, "
        "reuse the existing tree generator/evaluator/renderer. LEARN 5 (two's "
        "complement, bit representation, operator precedence in C-like langs). "
        "EFFORT 4 (data + a display mode toggle for binary/hex; the tree machinery "
        "is free). Main design Q: show operands in binary/hex vs decimal, and how "
        "to render the expected answer's base. CHEAP HIGH-VALUE -- top new item."),
    "Number-base conversion drill (bin/oct/hex/dec)": (
        (3, 4, 2, 4, 4, 4), None,
        "GENERABLE but NOT via the tree engine -- it is a single-value transform, "
        "not an expression. A small standalone generator (pick n, pick base pair, "
        "ask for the converted value). Pairs naturally with bitwise. EFFORT 4. "
        "LEARN 4 (positional notation). Modest but clean; fold into the bitwise "
        "thread as a sibling qtype."),
    "Sets & boolean logic drill (union/intersection/truth eval)": (
        (4, 5, 3, 3, 4, 4), None,
        "PARTLY GENERABLE and adjacent to bitwise (set ops ARE bitwise over a "
        "universe; boolean logic IS bitwise over 1 bit). Overlaps roadmap #9 "
        "(logic/deduction: truth tables, syllogisms, score 3.80). Recommend "
        "MERGING with #9 rather than a separate item: one 'discrete-structures' "
        "drill covering boolean eval + set ops + truth tables, sharing a small "
        "generator. LEARN 5. EFFORT 3 (new generator + eval, but no UI novelty)."),
    "Pre-algebra / algebra: solve-for-x (linear, quadratic)": (
        (4, 5, 3, 3, 3, 3), None,
        "GENERABLE with real work. Generating an equation is easy (pick roots, "
        "expand); the hard part is GRADING a symbolic answer (x = 3, or a factored "
        "form) rather than a numeric one -- needs a new grading mode (symbolic or "
        "canonicalized-numeric-solution). Start with linear (numeric solution, "
        "grades like arithmetic), defer symbolic. LEARN 5. EFFORT 3 (linear) / "
        "much lower for symbolic. Design Q: constrain to integer/rational roots so "
        "the answer is exact-matchable."),
    "Geometry / trig: evaluate-the-expression (not prove-the-theorem)": (
        (3, 5, 2, 3, 3, 3), None,
        "GENERABLE only as EXPRESSIONS, per user's own instinct: 'sin(30)=?', "
        "'area of a 3-4-5 triangle', 'hypotenuse given legs' -- a value to compute, "
        "which the arithmetic path can grade. NOT geometric PROOF/construction "
        "(that is authored/multimodal, out of the generator). Needs float grading "
        "with tolerance (a new grading mode: numeric-within-epsilon) -- a genuinely "
        "useful seam that also unblocks any future float answer. LEARN 5. EFFORT 3. "
        "Design Q: exact-value trig (sin30=1/2) vs decimal-with-tolerance."),
    "Unit / dimensional-analysis drill (convert & compute)": (
        (3, 4, 2, 4, 3, 4), None,
        "GENERABLE. Pick a quantity + unit pair, ask for the converted/derived "
        "value. Numeric grading (reuses the epsilon-grading seam from geometry). "
        "EFFORT 4. Practical, modest LEARN. A sibling of base-conversion."),
    # --- AUTHORED/STATIC: SM2/bank path, need Doc C + authoring Doc E ---
    "Calculus / advanced-math problems (authored expressions)": (
        (3, 5, 2, 2, 3, 2), None,
        "MOSTLY AUTHORED. User's instinct is right: generable 'only as expressions "
        "not problems, and unclear how hard.' Generating a WELL-FORMED derivative/"
        "integral drill with a checkable answer is a symbolic-math problem (needs a "
        "CAS or a curated instance set). RECOMMEND: authored static problems on the "
        "SM2/bank path (finite, hand-picked, recall-scheduled) rather than a "
        "generator. LEARN 5 but EFFORT 2 / RISK 2 for true generation -> DEFER "
        "generation; ENABLE via authored content (Doc C/E) at low cost."),
    "Field trivia / knowledge (biochem, genetics, etc.)": (
        (3, 3, 2, 4, 3, 4), None,
        "AUTHORED/IMPORTED. User is right that this is general-trivia-shaped: "
        "static Q/A on the bank path, gradable as identify/free_response/MC (all "
        "exist). NO new engine. Value is CONTENT, not code. Overlaps roadmap #23 "
        "(trivia importers, 2.86). EFFORT 4 (it is import + author, both built/"
        "planned). Belongs to Doc D (import) + Doc E (author) + SM2 scheduling."),
    "Textbook word problems (substantial, multi-step)": (
        (4, 4, 2, 3, 3, 3), None,
        "AUTHORED. User asked what makes them different from arithmetic: it is the "
        "GENERATION, exactly -- a rich word problem is not template-generable "
        "without templating tech (roadmap-adjacent to AI content #27). So they are "
        "AUTHORED static problems, SM2-scheduled, graded free_response/numeric. "
        "The 'more SM2-type' instinct is correct: finite, authored, recall-worthy. "
        "Doc C/E path. LEARN 4 (modeling), EFFORT 3 as content."),
    # --- MULTIMODAL (cross-cutting; gates several of the above) ---
    "Multimodal content: images in questions (render + author)": (
        (4, 4, 3, 3, 3, 3), None,
        "CROSS-CUTTING ENABLER. media_url ALREADY exists in the question payload "
        "and schema (surfaced but under-used). Rendering an <img> is small; the "
        "real work is AUTHORING/STORING media (where do image bytes live for a "
        "single-user local tool -- filesystem refs vs data URIs vs a media table) "
        "and the import format carrying them. FOUND 3: unblocks geometry diagrams, "
        "trivia with images, alphabet/handwriting, geography. Design-heavy; "
        "warrants its OWN design doc before build. Recommend a MINIMAL first cut "
        "(render an image from a URL/path already in media_url) then expand."),
    "Multimodal content: audio prompts (listen-and-answer)": (
        (3, 3, 2, 2, 3, 3), None,
        "CROSS-CUTTING, harder than images. Enables pronunciation/listening/music "
        "(#30) drills. Storage + playback + authoring. Speech SYNTHESIS already "
        "exists (speech.js) for TTS prompts -- so 'listen to synthesized word, "
        "type it' is cheap and needs NO stored audio; stored-audio clips are the "
        "expensive part. RECOMMEND: exploit existing TTS first (near-free), defer "
        "stored-audio. Split this row in the writeup accordingly."),
    # --- UI / QOL (value depends on multimodal + content growth) ---
    "UI/QOL: keyboard-first flow + shortcuts (submit, grade, skip)": (
        (4, 2, 2, 4, 4, 5), None,
        "QOL. A drill tool lives or dies on input friction. Keyboard shortcuts "
        "(enter submit exists; add grade-keys for an SM2 0/1/2 prompt, skip, "
        "reveal-hint) are cheap and high daily value. EFFORT 4, RISK 5. Rises in "
        "value once SM2 adds a grade step. Low LEARN. Good quick-win bundle."),
    "UI/QOL: responsive + mobile-friendly layout": (
        (3, 2, 2, 3, 4, 4), None,
        "QOL. The HTML/CSS convention section is still unwritten (flagged at "
        "modularization close-out). A responsive pass + writing those conventions "
        "together is a natural pairing. Value rises with multimodal (images/media "
        "need layout rules). EFFORT 3. Fold the CSS-conventions doc into it."),
    "UI/QOL: session review screen (end-of-session summary)": (
        (3, 3, 2, 3, 3, 4), None,
        "QOL. An end-of-session recap (what you got, what to review) using the "
        "stats seams Doc A builds. Reuses most-missed/over-time. EFFORT 3, low "
        "risk. Depends on Doc A landing. Nice capstone to the stats-depth work."),
}


# ===========================================================================
# REASSESSMENT 2026-07 (post-modularization)  -- ADR-054
# ===========================================================================
# The ITEMS scores above are the ORIGINAL model (C-MOD-design era), preserved
# as history. This block recomputes priorities for the REMAINING (not-DONE)
# items with axis scores updated to reflect what a fresh code survey found
# after roadmap #1 (modularization) shipped. The weights are UNCHANGED -- the
# user's priorities are stable; only the code reality (and thus EFFORT / RISK /
# FOUND for items that plug into now-proven seams) moved.
#
# DONE since the original model (dropped from the active ranking):
#   #1 Modularize (C-MOD-*, roadmap #1 COMPLETE)
#   #2 Extend arithmetic: difficulty control
#   #4 Extend arithmetic: more operators
#   #5 Generalize expression generation (nested trees)
#   #8 Automated test suite
#   #11 Schema migration runner
#
# SURVEY FACTS that moved scores (all verified against the shipped code):
#   - pick_next_question(candidates, history) is a single PURE swappable
#     function; history is already threaded through http_layer. -> SM2 and
#     adaptive selection get +EFFORT / +RISK (cheaper, safer to slot in).
#   - The migration runner (run_migrations/get_schema_version) is DONE and
#     battle-tested; elapsed_ms + difficulty columns already exist. -> anything
#     needing a new migration or timing data is de-risked.
#   - A full JSONL/CSV import pipeline (parse_import, post_banks_import) and the
#     translate/identify/free_response qtypes + bank-language plumbing already
#     exist. -> "vocab/language features" is mostly CONTENT + small extension of
#     built seams, not net-new: high USER, good EFFORT, low RISK.
#   - Typing has NO infrastructure beyond an empty "typing" config category
#     stub. -> genuinely net-new (drill.js phase machine + timing.js + likely a
#     new module); EFFORT stays moderate, LEARN rises (real-time input model).
#   - The stats pipeline is modular and elapsed_ms is collected but not yet
#     summarized. -> timing-stats and stats-depth are render-additions against
#     existing data: +EFFORT (quick wins).
#   - Modularization banked its foundational leverage: items whose FOUND was
#     "unblocks the refactor" (curriculum, adaptive) lose that credit now.

# item: ((USER,LEARN,FOUND,EFFORT,QUAL,RISK), original_score_or_None, why)
REASSESS_2026_07 = {
    "Study curriculum from the codebase": (
        (5, 5, 3, 3, 4, 5), 4.44,
        "FOUND 4->3: its 'teach from modular code' precondition is now met, so "
        "it no longer unblocks other work -- pure capstone value. Run in "
        "PARALLEL (user decision), so it does not consume a 'next thread' slot."),
    "Consolidate SM2 (spaced repetition) engine": (
        (5, 5, 4, 3, 3, 4), 4.04,
        "EFFORT 2->3, RISK 3->4: pick_next_question is a proven pure swappable "
        "seam; the migration runner is DONE; elapsed_ms exists. The SM2 schema "
        "fields remain the main build, but plugging the policy in is low-risk."),
    "Vocab/language features (extend existing qtypes/banks/import)": (
        (5, 4, 3, 4, 3, 4), None,
        "NEW (user-suggested). Survey: translate/identify/free_response qtypes, "
        "bank-language plumbing, and JSONL/CSV import ALL exist -> mostly content "
        "+ small extensions on built seams. LEARN 4 (data modeling/import), not "
        "5 (little new tech). RECOMMENDED next thread (leads with product "
        "movement on proven seams; safe re-warm-up after modularization)."),
    "Adaptive question selection (swap pick_next_question)": (
        (4, 5, 3, 4, 3, 4), 3.98,
        "EFFORT 3->4: contained swap of one pure fn (history already threaded). "
        "FOUND 4->3: modularization banked its leverage. Natural SM2 companion."),
    "Logic/deduction drill (truth tables, syllogisms)": (
        (4, 5, 3, 3, 3, 4), 3.80, "Unchanged. High LEARN (new generator+eval)."),
    "Code drill (what does this output?)": (
        (4, 4, 3, 4, 3, 4), 3.72, "Unchanged."),
    "Typing / text-entry speed drill": (
        (4, 4, 3, 3, 3, 4), 3.50,
        "LEARN 3->4: net-new real-time input-capture + WPM/accuracy model. "
        "EFFORT stays 3 (no typing infra beyond a config stub). A deliberate "
        "later test of whether the modular seams absorb a NEW qtype cleanly."),
    "Timed-round / speed-drill mode (use elapsed_ms)": (
        (4, 3, 3, 4, 3, 4), 3.50, "Unchanged-ish. Pairs with typing + timing."),
    "Assertion/invariant pass (boundary + pre/postconditions)": (
        (2, 4, 3, 4, 5, 5), 3.44, "Unchanged."),
    "Timing stats (compute/display elapsed_ms)": (
        (3, 3, 2, 5, 3, 5), 3.12,
        "EFFORT 4->5: stats pipeline + elapsed_ms exist; render-only addition. "
        "QUICK WIN -- folds into the vocab thread."),
    "Stats depth: most-missed, over-time, per-bank": (
        (3, 3, 3, 4, 3, 4), 3.08, "EFFORT 3->4: modular stats; additive queries."),
    "JSONL export/backup endpoint + button": (
        (3, 2, 3, 4, 4, 5), 3.18, "Unchanged; mirrors the existing import path."),
    "Module docstring/status drift cleanup + ADR index": (
        (2, 2, 3, 5, 4, 5), 3.04,
        "WIP: STATUS + conventions done; only the ADR index remains -> trivial. "
        "QUICK WIN -- folds into the vocab thread."),
    "Alphabet/romanization drill": ((3, 3, 2, 4, 3, 4), 3.04, "Unchanged."),
    "Grammar exercises (fill-in / reorder)": ((3, 4, 2, 3, 3, 3), 3.04, "Unchanged."),
    "Vocabulary importers (CodingFriends, doozan)": (
        (3, 2, 3, 3, 3, 4), 2.86, "Feeds the vocab/language direction w/ content."),
}


def _fmt_delta(new, orig):
    if orig is None:
        return " (new)"
    d = round(new - orig, 2)
    return " (%+.2f)" % d


reassessed = sorted(
    REASSESS_2026_07.items(), key=lambda kv: score(kv[1][0]), reverse=True
)
print("\n\n=== REASSESSMENT 2026-07 (post-modularization, remaining items) ===")
print("%-2s %-58s %5s  %s" % ("#", "Item", "Score", "delta-vs-original"))
print("-" * 90)
for i, (name, (vals, orig, _why)) in enumerate(reassessed, 1):
    s = score(vals)
    print("%-2d %-58s %5.2f %s" % (i, name[:58], s, _fmt_delta(s, orig)))

if __name__ == "__main__":
    # --- CANDIDATE BACKLOG 2026-07 ranking (user-suggested new items) ---
    print("\n\n=== CANDIDATE BACKLOG 2026-07 (new, user-suggested) ===")
    print("%-2s %-56s %5s  %s" % ("#", "Item", "Score", "Tier"))
    print("-" * 78)
    cand_ranked = sorted(
        CANDIDATES_2026_07.items(), key=lambda kv: score(kv[1][0]), reverse=True
    )
    for i, (name, (vals, _o, _w)) in enumerate(cand_ranked, 1):
        s = score(vals)
        tier = "1" if s >= 3.7 else "2" if s >= 3.2 else "3" if s >= 2.7 else "4"
        print("%-2d %-56s %5.2f  T%s" % (i, name[:56], s, tier))

    # Recommended sequence (ADR-054): score + user constraints (study is
    # parallel; want product movement + comprehension; avoid a second brutal
    # thread right after modularization) => lead with the safe, mostly-built
    # vocab feature, bank two quick wins, then the heavier lifts.
    print("\n--- RECOMMENDED SEQUENCE (ADR-054) ---")
    for line in [
        "Thread N   : Vocab/language features + timing-stats + ADR index",
        "             (product movement on proven seams; two quick wins folded in)",
        "Thread N+1 : SM2 consolidation (+ adaptive selection; same seam)",
        "Thread N+2 : Typing drill (deliberate net-new qtype stress test)",
        "Parallel   : Study curriculum (feeds on each thread's fresh code)",
    ]:
        print("  " + line)
