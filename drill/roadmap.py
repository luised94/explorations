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
