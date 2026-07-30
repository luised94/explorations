# Drill: step-by-step to production-grade version 1
## The complete execution guide, all threads, verified starting state

Companions (all authoritative, all in this handoff set):
consolidation-findings.md (design + evidence), refinements-and-wiring.md
(deferred policy, phase D), implementation-plan.md (commit-level spec for
phases D0/B/C/A), and the spike files. This document is the map ABOVE those:
the full route from today's repo to a version you would call done, with the
new backlog items (bitwise rail, epsilon path) prepped and their spike
findings folded in. On conflict inside phases 1-3, implementation-plan.md
wins; this guide governs ordering and everything after.

Definition of production-grade v1 for a single-user local tool:
  (a) every drill mode reachable, graded correctly, and covered by tests;
  (b) spaced repetition scheduling bank content with measured retention;
  (c) frictionless authoring from cli and nvim; content recoverable and
      diffable (export + git); schedule state recoverable (rebuild);
  (d) observability: stats that answer "is this working" and logs that
      answer "what happened";
  (e) boring operations: one command to run, one command to back up, a
      documented restore path, suite green, ADRs current.
Explicit non-goals for v1: multi-user, auth, sync, FSRS, minute-grain
learning steps, CAS-checked calculus, stored audio.

---

## Phase 0: coordination (do first, one sitting)

0.1 Apply/push the other session's patch series 0001-0007 (includes the
    feature backlog doc and roadmap.py scoring additions). Verify: fresh
    clone, suite green, backlog doc present in llm/.
0.2 Record the one cross-thread correction where it can be seen: the
    backlog's "keyboard-first pairs with SM2's grade step" is superseded --
    the consolidation design has NO grade prompt (binary
    derive_recall_quality, server-side). One line in the backlog doc or
    decisions.md.
0.3 Decide the three open forks now so no thread stalls: throttle floor key
    (recommended bank_id), cli home (recommended drill.py subcommands),
    sm2 retirement timing (recommended: immediately after content
    migration).

## Phase 1: adaptive selection (implementation-plan.md B1-B3)

Ships alone, no schema. Commits: stats reader; weighted pure core with
seeded distribution tests; strategy dispatch in HTTP. STOP: review.

## Phase 2: SM-2 consolidation (implementation-plan.md D0 + C1-C5)

D0 lands the three design docs in llm/. C1 migration 4 (question_schedule);
C2 scheduler pure core + ported invariant tests; C3 partition, overdueness,
throttle, rebuild; C4 review mode end to end + THE invariant test
(rebuild == stored over a simulated multi-week history); C5 retention,
elapsed_ms percentiles, terminal views. STOP: review. After this phase the
tool schedules, measures, and its state is a cache of its log.

## Phase 3: authoring (implementation-plan.md A1-A3)

A1 pure transform (flatten the nested close_block); A2 editor loop + stdin
filter (file:line: stderr contract = nvim quickfix integration); A3 one-off
sm2 exercises migration, archive sm2/. STOP: review. After this phase
adding content costs one buffer.

## Phase 4: the arithmetic rail (bitwise first) -- PREPPED, SPIKED

Evidence: test_bitwise_and_epsilon.py, all green through the REAL engine.

4.1 Bitwise operators. Add five rows to OPERATOR_DEFINITIONS -- &, |, xor,
    <<, >> -- plus one flat operand strategy for shifts (two-range shape,
    mirrors exponent). SPIKE FINDINGS TO HONOR:
    - SYMBOL COLLISION: "^" is exponent; xor must use another spelling
      (spike used the word "xor"). Decide the display glyph with the human.
    - PRECEDENCE IS CORRECTNESS, NOT STYLE: rows must carry conventional
      precedence (shifts 4, & 3, xor 2, | 1) or rendered questions
      disagree with stored answers under a reader's conventional parse.
      Caught live by the spike's render/re-eval check; port that check as
      a property test (500 seeded trees, render re-evaluated == answer).
    - RANGES: & | xor over 1..31 nest cleanly (185/200 nested at rung 4);
      shifts stay leaf-only, shift amount 1..4, >> left operand 8..255.
    - DISPLAY: decimal bitwise is pedagogically pointless. Land
      render_expression_in_base (pure display wrapper; spike version walks
      left/op/right -- CONFIRM the real node key shape against
      render_expression before landing) and a per-question base choice
      (binary default, hex rung for higher difficulty). Answer format
      decision for the human: accept decimal AND 0b/0x forms by
      normalizing in _validate_numeric (int(text, 0) handles all three) --
      recommended -- vs decimal only.
4.2 Number-base conversion drill: a generator producing "convert 0b10110
    to decimal / 0x2F to binary" pairs; reuses render_leaf_in_base and the
    int(text, 0) normalization from 4.1. Trivial after 4.1.
4.3 Discrete structures: boolean rows (and/or/not over 0..1) merged with
    roadmap #9 truth-table drill; xor already exists from 4.1. Same table,
    same engine.
Suite discipline unchanged: each step one commit, property tests seeded.

## Phase 5: the numeric/epsilon path for authored content -- PREPPED, SPIKED

Spike findings (all verified): _validate_numeric already exists with exact/
epsilon/malformed-tolerance semantics; validate_answer already routes
arithmetic qtype through it; the import funnel ALREADY ACCEPTS metadata --
so the remaining gap is exactly two edits:
5.1 Add importable qtype "numeric" to QTYPES (config) and one dispatch line
    in validate_answer routing it through _validate_numeric (feeds the
    single dispatch -- the ADR-025 clause -- never forks it).
5.2 The bank answer path in HTTP reads tolerance SERVER-SIDE from the
    stored question's metadata ({"tolerance": 0.001}) and passes it down;
    never trust a client-supplied tolerance for bank questions (the
    existing body tolerance stays for the generated-arithmetic path only).
This unlocks in one stroke: geometry/trig and units on the generated rail,
authored numeric banks (physics constants, mental math targets) on the SM2
rail -- scheduled, throttled, retention-measured for free.

## Phase 6: content pipeline completion

6.1 JSONL export (roadmap #15): deterministic render (canonical key order,
    ordered by id), endpoint + cli face; git commits the export = content
    version control (decided in findings section 13).
6.2 Importers (roadmap #23/#24): now SAFE -- the new-per-day throttle makes
    a 5000-question import inert by default. Import through the existing
    funnel; inspect via 6.1 diffs. One importer first (OpenTriviaDB),
    evaluate, then decide the second.
6.3 Authored banks for the authored-rail backlog items: word problems,
    calculus (curated, never generated), field trivia. Content sessions,
    not code.

## Phase 7: measurement depth and phase D wiring

From refinements-and-wiring.md, in order: S3 maturity breakdown +
mature-lapse rate (the scheduler-health number); F1 flag-this-question
(the one new write path, into questions.metadata; joins leeches in one
triage view feeding the authoring edit loop); W1 session summary; S4
forgetting curve (the FSRS-justifying evidence, via the rebuild fold);
S5 consistency if wanted. Only after S3 exists, consider R1/R2 scheduler
refinements -- metric first, tweak second.

## Phase 8: production hardening (the "boring operations" bar)

8.1 Structured logging + error-envelope audit (roadmap #17, boundary
    already defined: events at edges, never duplicate responses data).
8.2 Backup discipline: documented one-command backup (sqlite .backup or
    file copy while stopped, plus the 6.1 export) and a REHEARSED restore:
    restore db, run rebuild, invariant green. Write the runbook section in
    README.
8.3 Service packaging: one command to run (uv run / a systemd --user unit
    or equivalent), env-overridable host/port already exist; document.
8.4 Docs current: README refresh (modes, authoring, backup/restore),
    ADR index (roadmap #20 remainder, 30 minutes), STATUS.md closed out.
8.5 Multimodal design doc (design-first, per the backlog assessment):
    storage decision (recommended lean: filesystem refs relative to a
    media directory in media_url; no data URIs; no media table yet); TTS
    listening variant first (speech.js quarantine verified present) --
    implementation deferred past v1 unless the doc says otherwise.

## Version 1 acceptance checklist

[ ] Suite green including: SM-2 invariant tests, rebuild == stored,
    bitwise render/re-eval property, authoring round trip.
[ ] A bank question flows: authored in nvim -> imported -> scheduled ->
    reviewed -> retention visible -> flagged -> edited.
[ ] A generated session flows: bitwise at rung 4, binary display, graded
    with base-tolerant numeric parse.
[ ] Backup + restore rehearsed once, documented.
[ ] Export diffs cleanly in git after an authoring session.
[ ] decisions.md carries ADRs for every fork resolved above; STATUS.md
    reflects reality; zero new runtime dependencies (bottle remains alone).

## Suggested thread partitioning (each self-contained, docs pasted or read
## from llm/ after phase 0)

Thread 1: phases 0-1-2 (the consolidation thread, implementation-plan.md).
Thread 2: phase 3 (authoring; small, could fold into thread 1's tail).
Thread 3: phases 4-5 (arithmetic rail + epsilon; independent seams, can
          run in parallel with thread 1 if desired -- different files).
Thread 4: phases 6-7 (content + measurement; needs thread 1 landed).
Thread 5: phase 8 (hardening; needs everything, mostly writing and wiring).
