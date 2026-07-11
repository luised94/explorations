# Authoring guide: choosing qtypes and writing questions
Status: practical reference for the use period. Written alongside the
use-period plan (use-period-plan-2026-07.md), which this guide serves --
the three use cases here are that doc's Q2 use cases, and the recall
discipline below is what its Q5/E3 measure.

## The one rule that resolves almost every "which qtype"

Ask: CAN THE CORRECT ANSWER BE TYPED UNAMBIGUOUSLY?
- Yes, one clean string (with a listable set of spellings) -> a MATCHED
  qtype (free_response / translate / identify / multiple_choice). The
  drill auto-grades.
- No -- the answer is a paragraph, a concept, or something you would
  phrase three different ways -> RECALL. You self-grade at session end
  against the revealed answer.

Corollary: if you will TYPE the answer, list every acceptable spelling in
`alt`; if you CANNOT enumerate the acceptable answers, it is a recall
card. Forcing paragraph-answers through free_response is the false-leech
trap (ADR-059): you type a correct-in-spirit answer, the matcher rejects
it, and the scheduler buries a card you actually know.

## What each qtype actually does (matching behavior, verified)

- free_response / translate / identify: share ONE matcher. It lowercases,
  removes interior punctuation (, . ! ? : ;), collapses whitespace, and
  checks your input against [answer] + alternatives. It KEEPS accents,
  apostrophes, and hyphens (they carry meaning in language drills), so an
  accented answer must be typed WITH its accent -- an unaccented spelling
  will not match unless you list it in `alt`. List variants in `alt`.
- multiple_choice: EXACT match, but on server-generated options -- the
  server shuffles answer + distractors and you click one, so your typing
  never reaches the matcher. Your job is writing tempting distractors.
- arithmetic: numeric, within tolerance. Generated content, not authored.
- recall: NEVER matches. Prompt shown, you attempt (typed, effortful),
  submit advances with no reveal; at session end each attempt is shown
  with the criterion revealed and you press pass/fail. Grading feeds the
  scheduler exactly as a matched boolean would.

## Buffer mechanics (the authoring editor)

(NOTE: this repo doc is ASCII-only per the style contract, so the alphabet
examples below WRITE OUT the non-Latin characters as "<the Cyrillic letter
Zhe>" etc. The authoring buffer and the database themselves accept full
Unicode -- paste the actual glyph when you author.)


Many blocks per buffer, separated by a BLANK LINE. `q` and `a` are on
SEPARATE lines. Array fields (alt, distractors, hint, tags) put all values
on ONE line joined by ' | '. Aliases: q->question, a->answer,
alt->alternatives, type->qtype, hint->hints. The template's commented
worked example (qol-1) shows every field. For bulk generation, the
JSONL/CSV import path exists; in CSV the array fields pipe-separate within
a cell. When a question fights the format, record it verbatim in the
observations log BEFORE bending it to fit -- the fight is data (E2).

## Case 1: MA driving-test knowledge exam (test-shaped)

Match the real exam's form: it is multiple-choice, so drill recognition
under the same format. Lean multiple_choice; source phrasing from the RMV
driver's manual.

Rule recognition -- multiple_choice with TEMPTING distractors (E7 tracks
whether questions are answerable by elimination alone; avoid throwaway
distractors):

    q: A solid yellow line on your side of the center line means
    a: You may not pass
    distractors: You may pass when safe | You may pass only at night | The lane is ending
    type: multiple_choice
    tags: driving | ma-permit | rules

Numeric rules with one exact value -- free_response, but list format
variants (the matcher will not forgive "10 ft" vs "10 feet" on its own):

    q: Within how many feet of a fire hydrant is parking prohibited?
    a: 10 feet
    alt: 10 ft | 10 | ten feet
    type: free_response
    tags: driving | ma-permit | distances

## Case 2: Russian and Greek alphabets (three skills, three forms)

Author Russian and Greek as SEPARATE banks (per-alphabet accuracy in
drill stats; no cross-script interleaving before either is solid). Each
DIRECTION is a separate card -- this is the E6 split.

Letter recognition (see letter, name it) -- identify. Paste the actual
Unicode character; list romanization variants you might type:

    q: <paste the Cyrillic letter Zhe here>
    a: zhe
    alt: zh | zhuh
    type: identify
    tags: russian | alphabet | letter-to-sound

Letter production (hear name, produce letter) -- the reverse card, and it
hits the input-method wall (Q13): typing the letter needs an IME layout
switch. Two options, author a few each way and let E6 decide:

  (a) translate/identify, accept the IME switch:

    q: Cyrillic letter "zhe" (produces the zh sound)
    a: <the Cyrillic letter Zhe>
    type: translate
    tags: russian | alphabet | sound-to-letter

  (b) RECALL -- picture or handwrite the letter, reveal, self-grade. No
      IME switching, no romanization fights. Recommended for production:

    q: Write the Cyrillic letter for the "zh" sound
    a: <the Cyrillic letter Zhe> (zhe)
    type: recall
    tags: russian | alphabet | production

Greek: same structure -- identify for letter-to-name, recall or translate
for name-to-letter.

## Case 3: work-readings trivia (biology, biochem, genetics, mol-bio)

Mostly RECALL -- concept answers are phrased differently every time and no
matcher can grade them. Author the QUESTION tight and the ANSWER as an
honest, specific grading criterion:

    q: What does the Na+/K+ ATPase move, in which directions, and at what stoichiometry?
    a: 3 Na+ out, 2 K+ in, per ATP hydrolyzed; against their gradients
    type: recall
    hint: count the ions | think about the charge imbalance it creates
    tags: biochem | membrane-transport | pumps

THE key habit (Wozniak's minimum-information principle; Q5/E3): make each
criterion specific enough that honest pass/fail is EASY. "3 out, 2 in,
per ATP" is a crisp checklist -- you recalled it or you did not. "Explain
the sodium-potassium pump" is a paragraph you can always half-remember and
generously pass. When you HESITATE at grading time ("was that close
enough?"), the criterion was too broad -- split the card into narrower
ones. That hesitation, logged, is the E3 measurement.

Where a concept has a clean factual answer, drop to multiple_choice /
free_response for auto-grading, saving the self-assessment budget for the
genuinely open cards:

    q: Which base pairs with adenine in DNA?
    a: Thymine
    distractors: Uracil | Guanine | Cytosine
    type: multiple_choice
    tags: genetics | base-pairing

## Tags carry the subject axis (all cases)

Put the subject in `tags` (biochem, genetics, russian, driving...), NOT in
the bank or category name. One "work readings" bank can span subjects;
stats and future filtering key on tags. This is the ADR-060 decision you
are validating for real -- if the tag axis chafes in practice, that is
Q7/naming data for the reflection thread.
