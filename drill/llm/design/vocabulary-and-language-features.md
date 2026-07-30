# Vocab / Language -- Future Directions (docs, not scaffold)

Purpose: capture richer vocab/language features that are NOT being built now, so
the thinking is preserved without committing speculative code or schema. This is
the project's established "prepare as docs, not structure" pattern (cf. the
C-018b payload scaffold comment and ADR-025's reserved grading_kind): record the
seam each feature would plug into and what is deferred, and let a real consumer
dictate the shape when one exists.

Discipline (why nothing here is code): migrations are FORWARD-ONLY and the .db is
the user's only copy, so a schema field added speculatively is unrollable. An
interface designed before its caller is usually wrong (adversarial-review lens 4).
Every item below stays a doc until it has a DECIDED consumer that dictates its
interface; at that point, run adversarial-review against THAT shape.

ASCII only. Single-user.

--------------------------------------------------------------------------------
DEMOTED FROM THREAD N: per-question language in the payload
--------------------------------------------------------------------------------
STATUS: DEFERRED (no present consumer). Was a candidate Thread N item; the
spike-and-verify census demoted it.

FINDING (spike, verified against the code): language is currently a property of
the BANK, resolved CLIENT-SIDE (speech.js activeBankLanguage(), C-018a). The
question payload carries NO language field, and that is a documented WORKING
design, not a gap. Threading language into the payload would be REDUNDANT with
the client path -- robustness only, with no feature that needs it.

THE SEAM (already written, in-place, ready when a consumer appears):
  - logic.py build_question_payload -- the C-018b comment specifies the exact
    change: signature becomes build_question_payload(question, *,
    bank_language=None) and it sets payload["language"] = question.get("language")
    or bank_language.
  - http_layer.py (the bank-question handler, ~line 357) already has bank_id and
    a connection; get_bank(connection, bank_id) EXISTS (db.py:381). The handler
    would fetch the bank row and pass bank_language=bank["language"].
  - The frontend would prefer payload.language over the client bank lookup when
    present.
REVIVE WHEN: a real consumer exists -- e.g. per-question-language TTS (a question
whose language differs from its bank), or mixed-language banks. Until then the
client-side bank lookup is sufficient and simpler.

--------------------------------------------------------------------------------
DIRECTION (L1 <-> L2): prompt-language vs answer-language
--------------------------------------------------------------------------------
IDEA: a language deck can be drilled in either direction -- show the L2 word and
answer in L1 (comprehension), or show L1 and answer in L2 (production). A real
language-learning affordance.

WHY NOT NOW: no decided consumer, and it is a bigger change than it looks -- it
touches question SELECTION/generation semantics (a question and its "reverse"
are two prompts over one pair) and grading (production is harder; may want the
grading_kind axis ADR-025 reserved). Speculating the data model now risks a
wrong schema guess.
THE SEAM WHEN REAL: likely a per-attempt "direction" chosen at selection time
(not a stored column on the question -- the pair is symmetric), rendered by the
drill loop, with validate_answer unchanged (it already normalizes both sides).
Run adversarial-review on the data shape (is direction an attempt property or a
deck setting?) before building.

--------------------------------------------------------------------------------
VOCAB DECKS / GROUPING
--------------------------------------------------------------------------------
IDEA: group vocab into decks (a lesson, a frequency band, a chapter) drillable as
a unit, separate from the bank.
WHY NOT NOW: banks + tags already provide coarse grouping; no evidence the finer
"deck" concept is needed yet. Adding a decks table is speculative structure.
THE SEAM WHEN REAL: questions already carry `tags` (a list, imported). A deck may
be expressible as a tag filter over existing data (no new table) -- try that
before a schema change. pick_next_question(candidates, history) is the selection
seam; a deck is a candidate-set filter feeding it.

--------------------------------------------------------------------------------
SRS FOR VOCAB (spaced repetition applied to language items)
--------------------------------------------------------------------------------
IDEA: schedule vocab review by recall strength (the classic language use-case for
SM2).
WHY NOT NOW: this is roadmap #6 (SM2), sequenced as Thread N+1, and it applies to
ALL drill types, not just vocab -- it is not a vocab-specific feature. ADR-025
reserves the grading_kind decision and the SM2 scheduling-fields migration for
that thread.
THE SEAM: pick_next_question is the pure swappable selection function; SM2 is a
scheduling policy that replaces the current recency policy there, plus per-item
scheduling state (ease/interval/next_review) added AS ONE migration WITH SM2
(ADR-025), not before.

--------------------------------------------------------------------------------
VOCABULARY IMPORTERS (external sources)
--------------------------------------------------------------------------------
IDEA: importers for external vocab sources (e.g. frequency lists, existing decks)
to populate banks quickly.
WHY NOT NOW: the JSONL/CSV import pipeline (parse_jsonl/parse_csv,
post_banks_import) already accepts the full question shape (alternatives,
distractors, hints, tags, media_url, language). External sources can be converted
to that format OFFLINE today; a bespoke in-app importer is unjustified until a
specific source's friction is felt.
THE SEAM: the existing import endpoint + parse functions. A new importer is a
format adapter that emits the canonical dict shape -- no core change.

--------------------------------------------------------------------------------
ALPHABET / ROMANIZATION and GRAMMAR drills
--------------------------------------------------------------------------------
IDEA: alphabet/romanization recognition; grammar fill-in / reorder exercises.
Both are on the roadmap (Tier 3).
WHY NOT NOW: content + a possible new qtype each; lower priority than the ranked
items. Grammar reorder may need a new grading path (order-sensitive), which is a
real design question (the grading_kind axis again).
THE SEAM: validate_answer's qtype dispatch is the extension point; a new qtype
FEEDS it (does not fork it -- project guardrail). Alphabet/romanization likely
reuse translate/identify normalization; grammar-reorder likely needs a new
grading branch -> adversarial-review it.

--------------------------------------------------------------------------------
POINTER
--------------------------------------------------------------------------------
When any item here gains a decided consumer, it graduates to a real design pass
(adversarial-review -> spike -> commit-plan). Record the graduation in
decisions.md and update roadmap.py's model if the priority shifts.
