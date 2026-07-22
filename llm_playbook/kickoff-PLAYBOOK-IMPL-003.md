THREAD KICKOFF -- id: PLAYBOOK-IMPL-003
ROLE: implementation. You execute a fixed plan. You do not redesign.
SPEC: implementation-plan.md (the renamed r3 plan), plus
consolidation-PLAYBOOK-DESIGN-002.md and
plan-edits-PLAYBOOK-DESIGN-002.md, all self-contained and
authoritative. Where the plan says TOOLKIT, read llm_playbook/.

CONTEXT: this thread is G-1a (the transport/render half of the split
G-1 gate, ADR-020..023, plan Edit 7). Predecessor PLAYBOOK-DESIGN-002
produced ADR-020..029 and the plan edits; Stage A (two commits) landed
the plan and the ADRs. This thread RE-LANDS the reopened commits in
their new form and produces the first CONTEXT.md. My original range
(T-008+) does NOT open until G-1a AND G-1b both pass.

BOOTSTRAP (first action, MODE A default): from the parent monorepo,
branch main, pack the subset and upload:
  git archive --format=tar.gz -o /tmp/impl003.tgz HEAD llm_playbook drill
  git rev-parse HEAD   # record; report this SHA in your first reply
Confirm Stage A landed (ADR-020..029 present in
decisions/era-2026-q3.md; plan renamed to implementation-plan.md with
[LANDED] marks) before drafting.

SCOPE (stop at end of G-1a; do NOT start G-1b or T-008):
  B2a  T-007 re-land: preferences/render.md -> CONTEXT.md at
       <project>/llm/, hand-authored verb (ADR-020).
  B2b  T-007b re-land: retire bootstrap.sh sparse-checkout; add the
       archive-or-paste pack helper, scratch-only, committed-read
       (ADR-021).
  B2c  T-015b increment 1 ONLY: preferences/transport.md +
       scripts/pack-repo.sh, archive-or-paste. NO composition yet
       (ADR-022 staging -- composition is increment 2, later).
  B4   Author drill/llm/CONTEXT.md BY HAND from layers.md +
       style-contract.md + the new base-context items; stamp it;
       COMMIT it (must precede B5).
  B5   Pack drill's context via pack-repo.sh (archive mode). Verify:
       writes only to /tmp; requires CONTEXT.md committed first;
       run twice -> byte-identical. Record these as G-1a findings in
       a temporary drill/llm/g1-findings.md (drill's skeleton
       refinements.md does not exist until D-101).
  B6   Close: close-PLAYBOOK-IMPL-003.md.

DELIVERY (ADR-023, supersedes git-am): one commit per exchange, plan
order, never ahead. For a NEW file: supply complete file content +
exact target path + a suggested commit message. For an EDIT: supply a
git apply-able unified diff + a suggested commit message. The AUTHOR
commits locally. Suggested commit messages follow naming.md COMMIT
PREFIXES: "playbook: <plan-id> <summary>" (or "drill: ..." for drill
files).

CLOSED FORKS: F1 PROJ-ROLE-NNN. F2 llm_playbook. F3 llm/. F4 ENTRY
invariants + minimal kickoff. F5 frontmatter dates (era shards
excepted). F6 LAYER-NNN item ids, never reused.

NAMING CHECK (N5) at each STOP: every artifact this thread creates or
renames must be classifiable by naming.md alone. Flag nonconformance as
a finding, not an exception. New files this thread: transport.md,
pack-repo.sh, drill/llm/CONTEXT.md, drill/llm/g1-findings.md,
close-PLAYBOOK-IMPL-003.md -- confirm each conforms.

DEVIATION RULE: genuine plan defect -> stop, propose ADR, wait. No
silent fixes.

CONFIRM FIRST (before drafting B2a): restate the scope list, the
delivery mechanic, the bootstrap SHA once obtained, and confirm Stage A
landed. Then draft B2a.

NOTE the pre-commit hook is NOT installed (ADR-028); check.sh will not
fire automatically. You may run it manually, but do not assume it gates.
