THREAD DRILL-IMPL-002_llm-corpus-consolidation
date:     2026-07
from:     PLAYBOOK-DESIGN-005_protocol-reset (bounced; superseded by
          the playbook reset, see llm_playbook/RESET-2026-07.md)
role:     IMPL
baseline: playbook <SHA-AFTER-RESET-COMMIT>  project <SAME-SHA>  same repo
scope:    execute the drill llm/ corpus consolidation against the RESET
          playbook. Writes in drill/ only. Does not write a byte in
          llm_playbook -- a playbook change this work implies is
          reported as a finding and travels in the handoff.

Unpack the attached archive, skim the tree, then read this file before
anything else. Quote line 2 of drill/llm/CONTEXT.md, restate the task
in one sentence, state your strategy and approach, and give your
feedback, before planning anything. If you cannot find the render,
STOP and say so.

drill/llm/CONTEXT.md BINDS you. Other documents may look like they
govern style or process; they do not. Where one disagrees with the
render, the render wins and you flag it rather than following it
silently.

  THE RENDER IS KNOWN STALE. It was generated under the pre-reset
  playbook. Verify it and report, do not repair it silently:

    ./llm_playbook/scripts/render.sh verify drill/llm/CONTEXT.md

  A stale render that is flagged is workable. An unflagged one is the
  failure that put the binding sentence in this template.


TASK
  Execute drill/llm/plan/llm-corpus-consolidation.md, RECONCILED
  against the reset playbook first.

  The plan predates the reset and is partly void. Its drill-internal
  work -- moves, renames, ADR consolidation, the STATUS.md rewrite,
  spike retirement, frontmatter, the ASCII sweep -- is sound and is
  most of it. Its couplings to the old playbook are not. Known-broken,
  non-exhaustive, verify each against the tree (R1):

    C-101       re-render per render.md, and the hand-computed stamp.
                Void: render.sh does this and the stamp format
                changed. Phase 0 is PRE-WORK now, not a commit.
    C-118c      gated on PLAYBOOK-DESIGN-005 landing R1-R10 upstream.
                That thread bounced; the reset landed R1-R12 in
                llm_playbook/protocol.md instead. The gate's CONDITION
                is void; its QUESTION is not. Check what
                llm-thread-protocol.md still uniquely holds against
                protocol.md, and delete only what is genuinely covered.
    C-124, P-4  handback and residue ruling aimed at a bounced thread.
                Re-aim or drop, and say which.
    DEC-D8      cites ADR-004 and precedence.md for the thread
                boundary. Both gone, and ADR-004 never said it. The
                boundary is now the plain scope line above.
    C-118a/b    frontmatter carrying status: and supersedes:. Both
                retired by the reset; frontmatter shrinks accordingly.
    F-11        discharged. All three files it concerned are deleted.
    N3          renumbering prohibition. Void: git holds old numbers.

  Anything else in the plan citing naming.md, thread-protocol.md,
  kickoff.md, close.md, precedence.md, MANIFEST.md, render.md,
  check.sh, VERSION or the ADR record is citing a deleted file.


STOPS
  S1  THE RECONCILIATION, BEFORE ANY COMMIT LANDS. Walk the plan
      commit by commit and mark each LIVE, AMENDED or VOID, with one
      line of reason. Deliver that table and wait. This is the whole
      first turn; do not begin executing.
  S2  After the last Phase 1 commit.
  S3  Before any move or rename lands, because every rename breaks
      inbound references and the plan's A-3 says the fix ships in the
      same commit.
  S4  Delivery.


HAVE
  llm_playbook/                     the reset tree, 16 files
  drill/llm/plan/llm-corpus-consolidation.md
  drill/llm/llm-thread-protocol.md  the file C-118c may delete
  drill/llm/CONTEXT.md              the stale render
  drill/llm/PROJECT.md              drill's instance rules

REQUEST
  The rest of drill/llm is NOT packed: roughly 50 markdown files, and
  packing them with the plan and the playbook would spend the context
  this thread needs to think. Ask for files BY NAME as the plan
  reaches them, under R11. Expect to need STATUS.md, decisions.md,
  spec.md and roadmap.md early.

OUT
  Any write inside llm_playbook. Any re-litigation of the reset: it is
  recorded in RESET-2026-07.md and settled.md, and a disagreement with
  it is a finding for the handoff, not a change this thread makes.
  thread-launch-kit.md versus the playbook kickoff template: named in
  the plan as out of scope, and it stays out.
