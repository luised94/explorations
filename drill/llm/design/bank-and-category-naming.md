# Naming options: "bank", "category", and the missing grading axis
Status: OPTIONS PROPOSED, decision deferred to the human (R5/R8).
Origin: the QoL + recall-qtype thread (July 2026), from the human's
critique that the seeded categories are not parallel and that "bank" and
"category" are weak names. Companion to ADR-060's category-taxonomy
re-grain, which stays DEFERRED to post-use planning.

## Scope line (drawn per the handoff and the human's instruction)

This document is NAMES ONLY. Two changes are distinguished:

1. PURE RENAME: labels, strings, docs, and (optionally) identifiers, with
   no change to what keys scheduling/coverage. Deferred UNLESS it can be
   executed mechanically and deterministically (sed/awk or nvim headless).
   Verdict below: it cannot, so it too waits.
2. STRUCTURAL RE-GRAIN: changing what the coarse grouping MEANS (grading/
   session domain vs subject). Schema- and consumer-touching. Explicitly
   deferred to post-use planning (ADR-060); usage data should pick it.

Mechanical-rename feasibility check: "bank" appears in schema column names
(bank_id on questions/sessions/question_schedule), API payload fields,
function names (get_schedule_for_bank, resolve_author_bank, ...), CLI
flags (--bank), JS state fields, and prose. "category" likewise
(category_id, --category, SEED_CATEGORIES, /api/categories). A blind
sed would rewrite SQL, the HTTP contract, and the on-disk schema together;
the schema part is a migration, not a substitution. NOT mechanically safe.
Therefore: no rename executes in this thread; this doc records the options
so the post-use thread decides once, with usage data, and renames (if at
all) alongside the re-grain migration it will already be making.

## The diagnosis (why the current names chafe)

The seeded categories (arithmetic, vocabulary, trivia, geography, logic,
typing, code) mix three axes:
- SUBJECT (what it is about): geography, code, vocabulary.
- FORMAT/ACTIVITY (what you do): typing, arithmetic-generation.
- GRADING-KIND (how correctness is decided): string-match, numeric
  tolerance, multiple-choice -- and now recall/self-assessment.
"trivia" is the tell: geography and code questions can BE trivia, so the
set is not a partition. ADR-060 already points the way: SUBJECT belongs in
tags (fine axis, list-valued, free); the coarse axis should be
grading/session-shaped. The missing named concept is exactly GRADING-KIND,
and the recall qtype being built this thread is its first explicit member.

## Options for each level

Level A -- the coarse grouping (today: "category"):
- "track"    -- session-shaped, implies a routine you run; short; no
                collision in the codebase. RECOMMENDED CANDIDATE.
- "domain"   -- accurate but overloaded (sm2 had domains; DNS/math baggage).
- "mode"     -- grading-shaped but collides with the existing HTTP
                practice/review "mode" field. REJECT.
- "subject-area" -- wrong by design: subject is the TAGS axis. REJECT.
- keep "category" -- viable; its real problem is the non-parallel seed
                SET, which the re-grain fixes regardless of the word.

Level B -- the mid grouping (today: "bank"):
- "set"        -- short, natural ("question set"); slightly generic;
                  collides with JS Set in prose only. RECOMMENDED CANDIDATE.
- "collection" -- clear but long; fine as prose, clumsy as a flag.
- "pack"       -- connotes distribution/downloads more than authoring.
- "list"       -- too weak; implies order that does not exist.
- "deck"       -- REJECTED EARLIER (human); avoid.
- keep "bank"  -- viable; unambiguous in-codebase; the human's dislike is
                  aesthetic, which is a legitimate reason but cheap to
                  revisit at re-grain time.

Level C -- the new explicit axis (grading-kind), whatever it is stored as:
- values today implied by qtype: exact/alternatives match, numeric
  tolerance, multiple-choice, translate; NEW: self-assessed recall.
- naming candidates for the axis itself: "grading" (plain, direct;
  RECOMMENDED CANDIDATE), "grading_kind" (the D1-deferred column name --
  see _migrate_2's DEFERRED note in db.py, which anticipated this),
  "check" (short but vague).

## Recommendation (for the post-use thread to confirm or overrule)

Adopt at re-grain time, as one decision: category -> track (grading/
session-shaped coarse axis), bank -> set, subject -> tags (already true),
and a "grading" axis whose first non-implicit member is recall. If usage
shows the current words never actually confused anyone in practice, keep
"bank"/"category" and do only the seed-set re-grain -- the words are
cheaper to keep than the taxonomy is to leave mixed.

Evidence that would change the answer (R5): observation-log entries during
the use period showing which word misled in the moment (e.g. reaching for
"--category" when meaning a subject), or none doing so.
