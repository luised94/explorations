RUNBOOK -- PLAYBOOK-DESIGN-002 HANDOFF
=======================================
date: 2026-07
what this is: a self-contained, numbered checklist to (Stage A) update
  the repo in two commits, then (handoff) start the Stage B refactor
  thread. Each STEP is independently followable. Do them in order.
companions (all should be committed in STEP A0):
  - consolidation-PLAYBOOK-DESIGN-002.md   (decisions record)
  - plan-edits-PLAYBOOK-DESIGN-002.md      (verbatim LOCATE/REPLACE)
  - kickoff-PLAYBOOK-IMPL-003.md           (Stage B start prompt)
placement rule: keep these three companions + this runbook OUTSIDE
  llm_playbook/ (they quote the parent-repo name). Put them at repo root
  or in drill/llm/.
ground truth SHA at handoff: f7a320b2900550e472facb39565e1b200b983a5d
  (if you have moved past this, substitute your current HEAD everywhere
  and re-pack in the Stage B bootstrap.)

========================================================================
STAGE A -- UPDATE THE REPO (two commits: C1 then C2)
========================================================================

------------------------------------------------------------------------
STEP A0 -- preconditions (do once, no commit)
------------------------------------------------------------------------
[ ] A0.1  In the parent monorepo, on branch main.
[ ] A0.2  git status is clean (or only the intended new files present).
[ ] A0.3  Confirm HEAD:  git rev-parse HEAD
[ ] A0.4  Place these 4 files at repo root (or drill/llm/):
            runbook-PLAYBOOK-DESIGN-002.md   (this file)
            consolidation-PLAYBOOK-DESIGN-002.md
            plan-edits-PLAYBOOK-DESIGN-002.md
            kickoff-PLAYBOOK-IMPL-003.md
[ ] A0.5  The r3 plan file is currently UNTRACKED. Know where it is; you
          will move + rename it in C1.
NOTE: the pre-commit hook is NOT installed, so no check.sh rule blocks
  any commit below. Scrubs/ASCII are done by hand.

------------------------------------------------------------------------
COMMIT C1 -- add the plan, landed-marked and containment-clean
------------------------------------------------------------------------
message:
  playbook: add implementation-plan.md, landed-marked and containment-clean

[ ] C1.1  Move + rename the plan into the playbook:
            (place/rename the untracked plan file to)
            llm_playbook/implementation-plan.md
[ ] C1.2  Add frontmatter as the very first lines of that file:
            revision: r3
            status: current
            governs: llm_playbook and its consumer projects
[ ] C1.3  Apply the TERSE landed-marks (from plan-edits file, last
          section). Prefix in place:
            [LANDED]  on T-001, T-002, T-003, T-004, T-005, T-006
            [LANDED][REOPENED->PLAYBOOK-IMPL-003]  on T-007
            [LANDED][REOPENED->PLAYBOOK-IMPL-003]  on T-007b
[ ] C1.4  Scrub the parent-repo name throughout the plan:
            "explorations" -> "the parent monorepo"
          (find them all:  grep -n explorations llm_playbook/implementation-plan.md)
[ ] C1.5  Verify pure ASCII:
            LC_ALL=C grep -nP "[^\x09\x20-\x7e]" llm_playbook/implementation-plan.md
          (expect no output)
[ ] C1.6  Verify no upward path refs:
            grep -n "\.\./" llm_playbook/implementation-plan.md
          (expect none; if any, they are a finding -- stop)
[ ] C1.7  Stage + commit ONLY this file:
            git add llm_playbook/implementation-plan.md
            git commit -m "playbook: add implementation-plan.md, landed-marked and containment-clean"

------------------------------------------------------------------------
COMMIT C2 -- add ADR-020..029 and apply the seven plan edits
------------------------------------------------------------------------
message:
  playbook: add ADR-020..029 and apply plan edits

edit file 1: llm_playbook/decisions/era-2026-q3.md
[ ] C2.1  Append ADR-020..029 (ten lines) to the ADR LIST block.
[ ] C2.2  Append the ten ADR bodies after ADR-019. (Full text in
          consolidation-PLAYBOOK-DESIGN-002.md PART 2, one line each;
          expand each to the Context/Decision/Alternatives form used by
          the existing ADRs. If you kept the full-body drafts from the
          chat, paste those.)
[ ] C2.3  Mark supersessions in place:
            on ADR-004 add: SUPERSEDED IN PART by ADR-021 (checkout
              mechanism); SHA-pinning principle stands.
            on ADR-013 add: SUPERSEDED IN PART by ADR-020 (path);
              priority stands.
[ ] C2.4  On ADR-012 add the one-line note:
            Sharding trigger: decisions shard now ~410 lines; revisit
            sharding + index.md at next era boundary or check.sh rework.
[ ] C2.5  Update the header input-artifact reference:
            toolkit-v1-plan-r3.md -> implementation-plan.md

edit file 2: llm_playbook/implementation-plan.md
[ ] C2.6  Apply plan Edits E1..E7 verbatim from
          plan-edits-PLAYBOOK-DESIGN-002.md (each is LOCATE/REPLACE).
[ ] C2.7  Scrub any "explorations" the edits introduced:
            grep -n explorations llm_playbook/implementation-plan.md
          -> replace with "the parent monorepo"
[ ] C2.8  ASCII re-check both files:
            LC_ALL=C grep -nP "[^\x09\x20-\x7e]" \
              llm_playbook/decisions/era-2026-q3.md \
              llm_playbook/implementation-plan.md
          (expect no output)

[ ] C2.9  STOP CHECK (naming.md N5): implementation-plan.md and
          era-2026-q3.md are both classifiable by naming.md.
          implementation-plan.md = lowercase, dateless, hyphenated,
          descriptive -> conformant. ADR ids -> conformant. OK.
[ ] C2.10 Stage + commit the two files:
            git add llm_playbook/decisions/era-2026-q3.md \
                    llm_playbook/implementation-plan.md
            git commit -m "playbook: add ADR-020..029 and apply plan edits"

------------------------------------------------------------------------
COMMIT C0-companions -- (optional, recommended) commit the handoff files
------------------------------------------------------------------------
message:
  playbook: add PLAYBOOK-DESIGN-002 handoff artifacts
[ ] CC.1  Stage the four files placed in A0.4 (at repo root or drill/llm/):
            git add <paths to the 4 handoff files>
[ ] CC.2  git commit -m "playbook: add PLAYBOOK-DESIGN-002 handoff artifacts"
  (do this commit whenever convenient -- before C1, between, or after.
   It has no dependency on C1/C2. Kept separate so history is clean.)

========================================================================
STAGE A DONE -- VERIFY, THEN HAND OFF
========================================================================
[ ] V.1  git log --oneline -4   shows C1 and C2 (and companions).
[ ] V.2  ADR-020..029 present:
           grep -c "ADR-02[0-9]" llm_playbook/decisions/era-2026-q3.md
         (expect >= 10 in the LIST + bodies)
[ ] V.3  Plan renamed and marked:
           ls llm_playbook/implementation-plan.md
           grep -n "LANDED" llm_playbook/implementation-plan.md
[ ] V.4  Record the new HEAD SHA (post-C2) -- this is the base the
         Stage B thread bootstraps from:
           git rev-parse HEAD

========================================================================
HANDOFF -- START STAGE B (do NOT continue in the old chat)
========================================================================
[ ] H.1  Open a FRESH chat.
[ ] H.2  Paste the contents of kickoff-PLAYBOOK-IMPL-003.md as the first
         message (it is the start-of-thread prompt).
[ ] H.3  When it asks you to bootstrap, run:
           git archive --format=tar.gz -o /tmp/impl003.tgz HEAD llm_playbook drill
           git rev-parse HEAD
         upload /tmp/impl003.tgz, and report the SHA.
[ ] H.4  That thread (PLAYBOOK-IMPL-003) executes Stage B = G-1a:
         re-land T-007/T-007b/T-015b(incr.1), author+commit
         drill/llm/CONTEXT.md, pack + verify, close. It STOPS at end of
         G-1a.
[ ] H.5  Stage C (G-1b, the bitwise thread) is a SEPARATE later thread,
         started only after G-1a passes. See consolidation PART 5.

========================================================================
QUICK REFERENCE -- WHAT LANDS WHERE
========================================================================
C1  -> llm_playbook/implementation-plan.md (new, renamed, marked, scrubbed)
C2  -> llm_playbook/decisions/era-2026-q3.md (ADR-020..029, supersessions)
    -> llm_playbook/implementation-plan.md (E1..E7 applied)
CC  -> 4 handoff files at repo root or drill/llm/
B   -> (Stage B thread) render.md, transport.md, pack-repo.sh,
       drill/llm/CONTEXT.md, drill/llm/g1-findings.md,
       close-PLAYBOOK-IMPL-003.md
G-1 closes only after Stage B (G-1a) AND the later bitwise thread (G-1b).
Original range T-008+ opens after G-1 closes.
