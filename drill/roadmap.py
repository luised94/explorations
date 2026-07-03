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
