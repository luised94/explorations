CONSOLIDATION -- PLAYBOOK-DESIGN-002
=====================================
date: 2026-07
thread: PLAYBOOK-DESIGN-002 (a design thread; it produced decisions and
        plan edits, not plan-id commits)
purpose: freeze every gain and decision from this thread so none of it
         depends on the chat surviving. This IS the thread's close
         artifact (R12: a design thread's artifacts are its close).
governs the immediate work: Stage A (repo update), Stage B (the G-1
         refactor = PLAYBOOK-IMPL-003), Stage C (the two G-1 tests).

------------------------------------------------------------------------
PART 1. WHAT THIS THREAD ESTABLISHED (the story)
------------------------------------------------------------------------
The kickoff assumed T-001..T-007b landed and G-1 was applied, so the
next action was T-008. Running bootstrap.sh disproved that: its stub
reported "no render found at drill/CONTEXT.md", and inspection showed
the render path and transport mechanic were wrong for the actual
workflow. G-1 therefore FAILED FORWARD -- it did its job, surfacing
findings that reopen T-005..T-007b before any T-008 work.

Five original findings, plus five more that emerged while resolving
them, became ADR-020..029. None of my original commit range (T-008+)
has begun; it opens only after G-1 truly closes.

------------------------------------------------------------------------
PART 2. DECISIONS (ADR-020..029), one line each
------------------------------------------------------------------------
ADR-020  CONTEXT.md is a hand-authored, committed file at
         <project>/llm/CONTEXT.md (NOT project root; "render" = manual
         authoring, not automation). Supersedes path half of ADR-013.
ADR-021  Transport is archive-or-paste; scratch-only (/tmp, never the
         git tree); committed-read (git archive sees HEAD, so
         CONTEXT.md must be committed before packing). Retires the
         sparse-checkout bootstrap. Supersedes mechanism half of
         ADR-004; SHA-as-ground-truth principle stands (packer records
         and echoes the SHA).
ADR-022  Base-plus-overlay composition happens at PACK time. Staged
         (W4): archive-or-paste first, composition second. Do not
         bundle.
ADR-023  MODE A delivery = author commits locally. New file: model
         gives full content + path + suggested commit message. Edit:
         model gives a git apply-able unified diff + suggested message.
         NOT git-am patches (archive carries no history). Supersedes
         the kickoff WORKING METHOD line.
ADR-024  drill's naming-options-2026-07.md logged as convention-
         adoption EVIDENCE in the T-002 record (a thread reinventing
         precedence/identity/deferral for lack of a standard). Not a
         task; stays parked in drill.
ADR-025  Toolkit base context = layer ITEMS in layers.md (user facts ->
         PERSONA items; workflow ground truth W1-W8 -> CONSTRAINT/
         CONVENTION items; LAYER-NNN ids), forming the base layer under
         each project's CONTEXT.md overlay. The "state the task, ask if
         unclear" instruction goes to ENTRY.md (T-014), not here.
ADR-026  naming.md has a DESCRIPTIVENESS gap: a name can be structurally
         valid yet semantically empty (plan.md). Filenames should carry
         domain/semantic information. Cross-references the deferred
         keyword/tag id-segment fork (separator undecided). Rule text
         deferred; gap recorded.
ADR-027  Commit grammar has no form for meta-work ON the plan document
         (no plan-id exists for editing the plan itself). Accepted the
         plan-id-less summary form for now; revisit if it recurs.
ADR-028  check.sh budgets (200/150/250) are PROVISIONAL placeholders
         pending real line-count data; the containment grep is
         aggressive (case-insensitive parent-name match) and may need
         narrowing. Rework DEFERRED. Note: the hook is NOT currently
         installed, so no check.sh rule bites at present.
ADR-029  Implementation-status convention: the PLAN marks landed
         plan-ids TERSELY ([LANDED]); STATUS.md (once T-011 lands)
         carries live state and points to the plan; close artifacts
         hold per-thread detail. Until T-011, terse plan marks are the
         sole record. Prevents plan bloat while keeping ADR<->plan-id
         references intact.
NOTE on ADR-012: the decisions shard is growing (231 -> ~410 lines with
         ADR-020..029). Do NOT shard now. Revisit sharding + index.md
         creation at the next era boundary or the check.sh rework.

------------------------------------------------------------------------
PART 3. STAGE A -- UPDATE THE REPO (do this first; two commits)
------------------------------------------------------------------------
Preconditions: on the parent monorepo, branch main, at
f7a320b2900550e472facb39565e1b200b983a5d (or later; if later, re-pack
and report the new SHA). The plan file is currently UNTRACKED.

COMMIT 1 -- "playbook: add implementation-plan.md, landed-marked and
             containment-clean"
  a. Place the plan at llm_playbook/implementation-plan.md.
  b. Add frontmatter atop the file:
        revision: r3
        status: current
        governs: llm_playbook and its consumer projects
  c. Mark completed commits TERSELY (ADR-029): prefix T-001..T-007b
     with [LANDED]; additionally mark T-007 and T-007b
     [REOPENED->PLAYBOOK-IMPL-003]. No verbose DONE paragraphs.
  d. Scrub the parent-repo name: replace "explorations" ->
     "the parent monorepo" throughout the plan (recommended; the hook
     is off so it is not forced, but it protects the promotion path).
  e. Verify pure ASCII and no "../" upward path references.
  f. git add llm_playbook/implementation-plan.md ; commit.

COMMIT 2 -- "playbook: add ADR-020..029 and apply plan edits"
  a. In decisions/era-2026-q3.md: append ADR-020..029 to the ADR LIST
     block and their bodies after ADR-019; add "SUPERSEDED IN PART"
     lines to ADR-004 (by 021) and ADR-013 (by 020); add the sharding-
     trigger note to ADR-012; update header input-artifact reference
     to implementation-plan.md.
  b. In implementation-plan.md: apply plan Edits 1-7 (below). Scrub any
     "explorations" these introduce.
  c. git add the two files ; commit.

PLAN EDITS 1-7 (summarized; full LOCATE/REPLACE text was produced in
thread and is reproduced in PART 6):
  E1 T-007: CONTEXT.md at <project>/llm/, hand-authored verb.
  E2 T-007b: retire sparse-checkout; archive-or-paste pack helper.
  E3 T-015b: two-increment staging (archive-or-paste, then compose).
  E4 WORKING METHOD: local-commit delivery, not git-am.
  E5 T-014 ENTRY.md: add the ask-the-task invariant.
  E6 T-005 layers.md: add base-context items (ADR-025).
  E7 G-1: split into G-1a (transport/render) and G-1b (real thread).

STAGE A STOP CHECK (N5): implementation-plan.md and era-2026-q3.md are
both classifiable by naming.md. implementation-plan.md is conformant
(lowercase, dateless, hyphenated, descriptive). ADR ids conformant.

------------------------------------------------------------------------
PART 4. STAGE B -- THE REFACTOR = G-1 (thread PLAYBOOK-IMPL-003)
------------------------------------------------------------------------
This IS G-1a. New thread, new chat, id PLAYBOOK-IMPL-003, role IMPL.
Transport: git archive "llm_playbook drill" at HEAD, upload, report SHA.
Delivery: ADR-023 (full file or diff + suggested commit message), one
commit per exchange, author commits locally.

Commits to re-land (increment 1 only for transport -- NO composition
yet, ADR-022 staging):
  B2a  T-007 re-land: preferences/render.md -> llm/CONTEXT.md path +
       hand-authored verb.
  B2b  T-007b re-land: retire bootstrap.sh sparse-checkout; add the
       archive-or-paste pack helper (scratch-only, committed-read).
  B2c  T-015b increment 1: preferences/transport.md + scripts/
       pack-repo.sh (archive-or-paste).
  B4   Author drill/llm/CONTEXT.md BY HAND from layers.md +
       style-contract.md + the new base-context items; stamp it;
       COMMIT it (must precede B5, committed-read rule).
  B5   Pack drill's context via pack-repo.sh (archive mode). Verify:
       writes only to /tmp; requires CONTEXT.md committed first; run
       twice -> byte-identical (idempotent). These verifications ARE
       the G-1a findings. File them in a temporary
       drill/llm/g1-findings.md (drill's skeleton refinements.md does
       not exist until D-101).
  B6   Close: close-PLAYBOOK-IMPL-003.md. G-1a passes when the refactor
       is committed and packs cleanly.

------------------------------------------------------------------------
PART 5. STAGE C -- THE REAL THREAD = G-1b (thread DRILL-IMPL-NNN)
------------------------------------------------------------------------
New thread, role IMPL, project DRILL. Task: bitwise arithmetic
(scored 4.04, Tier 1) from drill's feature-backlog-2026-07.md -- a real,
top-ranked, bounded task (operator-table rows + binary/hex display; the
tree machinery already exists).
  - Drill predates the id grammar; pick its first conformant thread
    number from drill PROJECT.md (decision at kickoff).
  - Transport: pack via pack-repo.sh INCLUDING the committed
    drill/llm/CONTEXT.md. If the chat is paste-friendly, use paste mode
    -> free opportunistic coverage of the paste path (NOT a required
    G-1 criterion; W4 -- do not make paste a gate).
  - Test: does the rendered context carry preferences into working
    bitwise code. Findings -> refinements -> editorial -> toolkit v0.2.
G-1 CLOSES when both G-1a (B5) and G-1b (C2) pass. Only then does the
original range (T-008 onward) open and the plan resumes.

------------------------------------------------------------------------
PART 6. OPEN ITEMS / DECISIONS STILL PENDING
------------------------------------------------------------------------
  - "explorations" scrub in Commit 1: recommended, confirm or defer.
  - ADR-026 descriptiveness rule TEXT is deferred (gap only recorded);
    decide alongside the keyword/tag id-segment fork.
  - check.sh rework (ADR-028) deferred; install the pre-commit hook at
    some point (T-001 accept criterion) -- currently absent.
  - Sharding (ADR-012) to revisit at next era boundary / check.sh
    rework.
  - drill's first conformant thread number (Stage C kickoff).
  - Full LOCATE/REPLACE text of plan Edits 1-7 lives in the
    PLAYBOOK-DESIGN-002 chat; if that text did not get transcribed into
    this file before commit, re-derive from the ADRs (each edit traces
    to one ADR).
