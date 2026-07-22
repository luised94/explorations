PLAN EDITS -- PLAYBOOK-DESIGN-002
==================================
date: 2026-07
companion to: consolidation-PLAYBOOK-DESIGN-002.md
applies to: implementation-plan.md (the renamed r3 plan)
how to use: each edit is LOCATE (find this text) / REPLACE WITH (swap
  for this). Applied during Stage A Commit 2. After applying, scrub any
  "explorations" these introduce -> "the parent monorepo". Each edit
  traces to one ADR (cited).

NOTE on placement: keep this file OUTSIDE llm_playbook/ (it quotes the
parent-repo name in old plan text). Repo root or drill/llm/.

------------------------------------------------------------------------
EDIT 1 -- T-007 CONTEXT.md location and verb (ADR-020)
------------------------------------------------------------------------
LOCATE:
  Render targets in priority order: (1) CONTEXT.md at project root
  -- pointed at in repo-access chats, pasted whole in others;
REPLACE WITH:
  Render targets in priority order: (1) CONTEXT.md located at
  <project>/llm/CONTEXT.md (ADR-020) -- authored/updated BY HAND from
  the sources (no automated generator in v0.1; the stamp is the only
  mechanical step), committed as instance state, pointed at in
  repo-access chats and packed whole in others;

ALSO LOCATE (T-007 Accept line):
  hand-rendering CONTEXT.md from T-005/T-006 reproduces
REPLACE WITH:
  hand-authoring <project>/llm/CONTEXT.md from T-005/T-006 reproduces

------------------------------------------------------------------------
EDIT 2 -- T-007b retire local checkout (ADR-021)
------------------------------------------------------------------------
LOCATE (T-007b title + body):
  T-007b [S] scripts/bootstrap.sh (new in r3; before G-1 so the gate
  tests the real channel)
  Takes project name plus optional SHA (defaults to current main,
  recording whatever it resolves). Performs one clone of
  explorations with sparse-checkout of TOOLKIT/ plus the project
  directory AT the recorded SHA -- this makes the recorded SHA
  ground truth rather than forensic decoration (AF6). Writes the
  SHA and render stamp into a kickoff skeleton stub; prints the
  paste-ready block for Tier C chats.
  Accept: running it twice with the same SHA is idempotent; the
  printed block contains the stamp.
REPLACE WITH:
  T-007b [S] scripts/pack helper (RETIRES the sparse-checkout bootstrap
  per ADR-021; before G-1 so the gate tests the real channel)
  Transport is archive-or-paste, scratch-only, committed-read. Archive
  mode: git archive --format=tar.gz of a chosen (possibly SUBSET) file
  set at HEAD, echoing the SHA. Paste mode: same set composed to a /tmp
  temp file, opened in nvim under --edit/-e. Writes ONLY to /tmp, never
  the git tree. Reads ONLY committed files -- CONTEXT.md must be
  committed before packing. Composition is cheap, idempotent,
  reproducible.
  Accept: running twice at the same SHA is byte-idempotent; the printed
  block carries the stamp; packing before committing CONTEXT.md is
  caught (documented gotcha).

------------------------------------------------------------------------
EDIT 3 -- T-015b two-increment staging (ADR-022)
------------------------------------------------------------------------
LOCATE:
  pack-repo.sh wraps git archive / tar for private repos with no
  remote, producing a chat-ready artifact.
REPLACE WITH:
  pack-repo.sh implements transport in TWO increments (ADR-022 staging,
  W4 scope-counteraction): (1) archive-or-paste of a chosen file set;
  (2) base-plus-overlay COMPOSITION at pack time -- playbook base
  (including the layers.md base-context items, ADR-025) with each
  project's CONTEXT.md as overlay, item-id shadowing per ADR-008. Do
  not bundle the two increments.

------------------------------------------------------------------------
EDIT 4 -- WORKING METHOD delivery mechanic (ADR-023)
------------------------------------------------------------------------
LOCATE target is ENTRY.md/kickoff text, not the plan; already applied in the IMPL-003 kickoff.
  In either mode deliver each commit as a git-am-able patch.
REPLACE WITH:
  In either mode the AUTHOR commits locally (ADR-023): for a NEW file,
  the model supplies complete file content + target path + a suggested
  commit message; for an EDIT, a git apply-able unified diff + a
  suggested commit message. Not git-am patches (archive transport
  carries no history).

------------------------------------------------------------------------
EDIT 5 -- T-014 ENTRY.md ask-the-task invariant (ADR-025)
------------------------------------------------------------------------
LOCATE:
  role line, FILL-IN block, instincts, render stamp statement, and the
  SCOPE RULE (W4):
REPLACE WITH:
  role line, FILL-IN block, instincts, render stamp statement, the
  ASK-THE-TASK invariant (ADR-025: state the thread's task; if unclear,
  ask before proceeding), and the SCOPE RULE (W4):

------------------------------------------------------------------------
EDIT 6 -- T-005 layers.md base-context items (ADR-025)
------------------------------------------------------------------------
LOCATE:
  Persona / Constraint / Criteria / Convention layers extracted
  from knowledge-capture.md.
REPLACE WITH:
  Persona / Constraint / Criteria / Convention layers extracted from
  knowledge-capture.md, PLUS toolkit base-context items (ADR-025):
  user-identity facts as Persona items, workflow ground truth W1-W8 as
  Constraint/Convention items, each with a LAYER-NNN id, forming the
  base layer for composition. Watch the 200-line budget.

------------------------------------------------------------------------
EDIT 7 -- G-1 split into G-1a / G-1b (ADR-020..023; the split)
------------------------------------------------------------------------
LOCATE (the G-1 gate block):
  G-1 EARLY-USE GATE (no further commits until done)
  Render CONTEXT.md for ONE live project via the real channel (run
  bootstrap.sh, paste or point per tier) and run one real thread.
  File findings as refinement entries in the project. Purpose:
  break the meta-work attractor; test the render path while the
  repo is cheap.
  FAILURE BRANCH: reopen T-005..T-007b only.
REPLACE WITH:
  G-1 EARLY-USE GATE, two parts (no further commits until both done):
  G-1a TRANSPORT/RENDER: re-land the T-007/T-007b/T-015b refactors;
    author and COMMIT <project>/llm/CONTEXT.md; pack it via archive-or-
    paste. The refactor IS the test -- it exercises the corrected
    transport path (committed-read, scratch-only, idempotent compose).
    Findings -> refinements.
  G-1b REAL THREAD: run one real thread (the bitwise-arithmetic task
    from drill's feature-backlog-2026-07.md) through the packed context.
    Tests whether the rendered context carries preferences into working
    code.
  Both must pass to close G-1. FAILURE BRANCH: reopen T-005..T-007b
  only. Purpose unchanged: break the meta-work attractor; test the
  render path while the repo is cheap.

------------------------------------------------------------------------
TERSE LANDED-MARKS (ADR-029; applied in Commit 1, listed here for
completeness)
------------------------------------------------------------------------
Prefix these plan items in-place:
  [LANDED] T-001, T-002, T-003, T-004, T-005, T-006, T-007b
  [LANDED][REOPENED->PLAYBOOK-IMPL-003] T-007
  [LANDED][REOPENED->PLAYBOOK-IMPL-003] T-007b
(T-007b appears twice above intentionally: it landed in IMPL-001 and is
being reworked in IMPL-003. Keep one line, both marks.)
