# Scheduler refinements and observability wiring
## Companion to consolidation-findings.md

Status: analyzed and decided; NOTHING in this document blocks or belongs to
the core implementation plan except where explicitly marked LANDS WITH C.
Everything else is deferred policy or phase D wiring, recorded here so the
decisions are choices with reasoning, not future surprises.

Guiding principle carried over: add a write path only where a genuinely new
signal exists; derive everything else from data already written. Score:
across this entire document, new dependencies zero, new columns zero, new
write paths exactly one (the question flag, into an existing JSON column).

---

## Part 1: refinements to advance_schedule_state

All three are policy tweaks inside one pure function behind the existing
seam. DECIDED: v1 ports the classic contract exactly (pinned by the
4860-point equivalence spike and the ported invariant tests). No refinement
is adopted until the true-retention metric exists to arbitrate it; that is
the reason retention is in C's definition of done.

R1. Overdue-success bonus. Classic SM-2 multiplies the STORED interval on
success; but succeeding 10 days late demonstrates retention over
interval + 10 days. Refinement: the multiply step uses actual elapsed days
(review_date - last_review) instead of stored interval_days. Strictly more
data-driven, one line, preserves the rebuild invariant (elapsed days is
derivable from the log). COST: breaks field-identity with the original
sm2_update, so when adopted, retire the grid-equivalence test and let the
invariant tests carry the contract. STATUS: deferred, first candidate once
retention data exists.

R2. Gentler lapses. Classic resets a lapsed item's interval to 1 day --
harsh for a mature item nearly remembered. Refinement (Anki-style): new
interval = max(1.0, old interval * 0.5). One constant, same seam, same
rebuild caveat as R1. STATUS: deferred; adopt only if the mature-lapse
rate (Part 2, S3) shows mature items churning back through day-one.

R3. Early-review distortion: a non-refinement. Classic SM-2 overstates
growth when items are reviewed before due. In drill this is structurally
impossible in review mode -- the partition serves only due items -- and
practice mode never touches the schedule. The architecture prevents the
problem the algorithm ignores. STATUS: nothing to do; recorded so nobody
adds a correction for a case that cannot occur.

Kept as-is: the EF ceiling of 3.0 (a deliberate sm2 addition; classic has
none). The 90-day simulation showed well-known items pinning at 3.0 with
intervals near 165 days -- correct behavior, not a bug.

RISK for all of Part 1: adopting a tweak by taste instead of by metric.
The mitigation is procedural: any change to the policy inside
advance_schedule_state or derive_recall_quality requires (a) a retention
number motivating it and (b) a decided rebuild stance (rebuild applies
current policy retroactively -- consolidation-findings.md section 8).

---

## Part 2: statistics (pure SQL over existing tables; no schema)

Each lands as a db.py reader plus a stats.js render and/or terminal view.
Ordered by value.

S1. True retention: first-attempt-of-day accuracy. LANDS WITH C (already
in the plan, C5). Verified query in test_migration_and_simulation.py.

S2. elapsed_ms percentiles per qtype and per bank (median, p90; SQLite:
order + limit/offset or window functions, both stdlib). DOUBLE DUTY: these
trailing medians are exactly the per-qtype baselines the v2 timing-derived
derive_recall_quality needs. The stats render is quietly the prerequisite
for the timing grade policy -- build the measurement first, the policy
second. NULL elapsed_ms rows are simply excluded. LANDS WITH C (C5, small
addition).

S3. Scheduler health pair. Maturity breakdown: new / young / mature counts
with the conventional mature line at interval >= 21 days -- the one-glance
state of the collection. Mature-lapse rate: fraction of grade-0 outcomes
among mature-at-the-time items -- the single best scheduler-health number;
if mature items keep lapsing, intervals are too aggressive and R2 becomes
evidence-backed. Computable from responses joined to schedule state at
review time via the rebuild fold, or approximated from current schedule;
start with the approximation. PHASE D.

S4. Empirical forgetting curve: retention bucketed by interval length at
review time. Flat curve = calibrated scheduler; downward slope = the
evidence that would someday justify FSRS. Needs interval-at-review, which
the rebuild fold reconstructs from the log -- a debug-grade view, not a
write path. PHASE D.

S5. Consistency: distinct review days per week from responses timestamps.
Cheap; include in the session summary if wanted. No streak mechanics
beyond it. PHASE D.

---

## Part 3: feedback gathering (the one new write path)

F1. Flag-this-question during review. The only genuinely new signal in
this document: subjective card quality ("ambiguous", "typo", "too easy"),
not derivable from any stored data. Write path: append {"flag": {"reason":
..., "flagged": iso-timestamp}} into questions.metadata -- the ADR-024
hatch exists for exactly this shape of sparse annotation; no migration.
Surface: flagged questions join leeches in one triage view; both feed the
authoring edit loop (flag during review -> see in triage -> open in edit
buffer -> fix the card). This closes the quality loop: the scheduler finds
bad cards statistically (leeches), the human finds them subjectively
(flags), authoring is the repair path for both. PHASE D; requires the
authoring edit face and one small http endpoint plus one button.

---

## Part 4: session summary and operational logging

W1. Session summary: end-of-session aggregate (answered, correct, new
introduced, due remaining, tomorrow's forecast). Pure fold over the
session's responses plus one schedule query; the honest motivational
surface for a single-user tool. PHASE D (small; pairs naturally with
end_session which already exists in db.py).

W2. Operational logging: ALIGN WITH ROADMAP #17 (structured logging plus
error-envelope audit is already a planned thread) rather than inventing
here. Shape when that thread runs: one plain-dict-to-JSON line per notable
event (migration applied, review committed, import accepted or rejected,
rebuild run), emitted at the HTTP/MAIN edge, stderr or file, stdlib only.
EXPLICIT NON-GOAL: never log review outcomes as metrics -- responses IS
the metric log, append-only and queryable; a second copy in a log file is
drift waiting to happen. STATUS: deferred to roadmap #17; this document
only records the boundary (events at edges yes, data duplication no).

W3. Explicit omission: no schedule audit table (EF before/after per
review). Recomputable by replaying the log to any point via the rebuild
fold; inspection is a debug view, not a write path.

---

## Summary table

id  item                          when          new schema  new writes
R1  overdue-success bonus         deferred      no          no
R2  gentler lapses                deferred      no          no
R3  early-review (non-issue)      never         no          no
S1  true retention                lands with C  no          no
S2  elapsed_ms percentiles        lands with C  no          no
S3  maturity + mature-lapse rate  phase D       no          no
S4  forgetting curve              phase D       no          no
S5  consistency                   phase D       no          no
F1  flag-this-question            phase D       no          metadata JSON
W1  session summary               phase D       no          no
W2  operational logging           roadmap #17   no          log lines only
W3  schedule audit table          never         no          no
