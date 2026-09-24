CLOSE PLAYBOOK-DESIGN-007_preferences-split-and-harness
=======================================================
date:     2026-09
type:     close
baseline: playbook 58ca75d04e04af5c433b385bcf81a21aeb955d63
          project  58ca75d04e04af5c433b385bcf81a21aeb955d63  same repo
model:    began on a model the author reports as Opus 4.8; closed on
          claude-opus-5-5. Recorded as a trial of RF-PLAYBOOK-013.
scope:    looking back at a DESIGN thread that split the pasted working
          defaults into a standing text plus method prompts, explored
          the harness and interface in parallel branches, and then --
          only at the end -- read this tree and triaged its own output
          against it. Writes in llm_playbook only.

TERMINAL STATE: LANDED when the author applies commits 0001-0004.
0005 and 0006 touch preferences/ and are GATED (see GATE below); the
close is accurate whether or not they have been applied yet.

  NO KICKOFF OPENED THIS THREAD. It began as an ordinary chat about a
  preferences document and became a playbook thread later. It
  therefore had no render, no declared role and no baseline until its
  last turns, and it carried the id PLAYBOOK-DESIGN-007 only at close.
  VERIFY-FIRST: the id assumes no thread took 007 after
  PLAYBOOK-DESIGN-006. If one did, rename this thread's four llm/
  files and the citations to them in one pass, after searching for
  the token in prose as well as paths (S30).


WHAT LANDED

  0001  llm/handoff/PLAYBOOK-DESIGN-007_harness-interface-and-build.md
          the two branch records merged into one design record, with
          the Dennis et al. citation corrected
        llm/handoff/PLAYBOOK-DESIGN-007_interface-sketch-seed.md
          the editor seed, "tree" corrected to the open graph shape
        llm/handoff/PLAYBOOK-DESIGN-007_invocation-drafts.md
          four method drafts, byte-identical, not promoted
  0002  refinements.md  RF-PLAYBOOK-013, -014, -015 opened. -015 is on
          its second occurrence and is a promotion candidate.
  0003  settled.md, rewritten whole. Three rulings: modes as the
          in-thread form of roles; triage, never placement; prompts
          keep their reasoning. ONE THREAD AT A TIME recorded as
          observed not holding. Three OPEN entries: the Preferences
          field as an uncomposed second authority, its unmeasured
          decay, and rule TWO's trade between accretion and collapse.
  0004  this file, and
        llm/handoff/PLAYBOOK-DESIGN-007_data-model-and-tooling.md
  0005  GATED. preferences/working-defaults.md added -- the standing
          text, corrected; working-defaults-merged-prose.md (its
          ancestor) and working-defaults-merged-layered.md (a second
          paste form with no consumer) retired; README inventory and
          settled.md updated to match.
  0006  GATED. layers.md and style-contract.md: the items the July
          reset and PLAYBOOK-DESIGN-006 found superseded are repaired
          or retired -- CONSTRAINT-005 and S26 to baseline fidelity,
          CONVENTION-002 retired, L3 retired, L1's dead citation
          removed, the version: field dropped from both.

  Not landed, by decision: SETUP.md. Its loading notes duplicate
  README HOW TO USE; the parts that were new -- the decay probe and the
  Preferences field's place in precedence -- are OPEN entries in
  settled.md instead.


GATE
  preferences/ was serialized behind DRILL-IMPL-002's C-101 in July
  (PLAYBOOK-DESIGN-006 kickoff, OUT): render.sh resolves a render's
  source SHA from the last commit touching llm_playbook/preferences,
  so ANY commit there moves the SHA every existing render cites. This
  thread could not learn whether DRILL-IMPL-002 is still open. Apply
  0005 and 0006 only once it has closed, or accept that drill's
  CONTEXT.md will then cite a stale source SHA. After 0006 lands,
  drill's CONTEXT.md is stale in CONTENT too -- it carries the old
  CONSTRAINT-005 -- and should be recomposed and re-stamped.


DISCREPANCIES, AND HOW EACH WAS RESOLVED

  This is the section that does not survive in the diff.

  1  THE THREAD DESIGNED TOWARD THE PLAYBOOK WITHOUT THE TREE. Most of
     its turns built what the tree already held (RF-PLAYBOOK-014 lists
     each overlap). Found only when the author attached the pack.
     COST: the bulk of the thread's design effort, and one turn of
     triage. Resolved by the triage; recorded so the next thread
     starts with the pack.

  2  A DELIVERED FILE CONTRADICTED A SETTLED DECISION AND WENT LIVE.
     The standing block's Delivery section keyed delivery form on
     operation type, which settled.md records as rejected in favor of
     R12. The author had pasted it into the browser Preferences field.
     The same file also said every commit is "independently valid",
     the exact phrase PLAYBOOK-DESIGN-006 found colliding with R6's
     deliberate-red exception. Both corrected in 0005's
     working-defaults.md. Until the author re-pastes it, every chat
     still receives the old text.

  3  THE verbalized-sampling "AMENDMENT" WAS A REPLACEMENT. Decision
     [6] said to amend an existing invocation; the thread never saw an
     original and wrote a new one. No original exists in this tree.
     The history search that would settle whether one ever existed
     (git log --all -i -G'verbali[sz]ed') had not been run at close.
     If it finds one, its content should be compared against the
     draft before the draft is ever promoted.

  4  BOTH BRANCH RECORDS OVERSTATED THE PAPER. "Beat the orchestrator
     on every quality metric" held under the Claude judge only; under
     GPT-4.1 it was 11 of 15, and the records omitted the tested model
     and the 1.3-1.4x cost. Corrected in the merged design record,
     finding 2.

  5  THE INTERFACE SEED PRESUMED A TREE while the build record left the
     graph shape open. The build record was right. Corrected on filing.

  6  THE HANDOFF'S STEP 3 WAS ALREADY DONE. It planned to consolidate
     "scattered" thread-id, project-id and commit-style rules. The
     July reset had already consolidated them into protocol.md
     IDENTITY AND NAMING. Dropped from the forward sequence
     (CONSTRAINT-015).

  7  FOUR MENU ENTRIES HAD NO BODY ANYWHERE. The standing block listed
     combinatorial-analysis, quantitative-decision-analysis,
     topological-sort and dimensional-analysis as pasteable files; no
     body was found in the conversation or this tree. Two are covered
     by the tree (CRITERIA-002; commit-planning step 4). All four are
     removed from the menu in 0005, which now lists the eight prompts
     in prompts/ and the four drafts. If the history search finds a
     body, restore that entry.

  8  THE THREAD'S FILES WERE NEARLY LOST (RF-PLAYBOOK-015). The browser
     stopped offering branch navigation mid-thread. Recovered from the
     session's output folder. The seven files this thread delivered
     matched the sha256 it printed at delivery; the two branch records
     and the seed matched the copies the author re-attached. The
     source files this thread's llm/ files were built from, sha256,
     first 16 hex digits:
       branch-record-harness-and-build.md       987d526449da348f
       findings-harness-interface-grammar.md    b2751e353b6486af
       interface-sketch-seed.md                 c834c2e96a3eab6c
       standing-block.md                        1926b8b97c1741a8
       SETUP.md                                 a1a886a648e71dfd
       handoff-sequence-and-next-steps.md       94003c46dd604cf0

  9  THE PLAN WAS AGREED, THEN REVERSED. "Place the files together,
     then consolidate" was accepted a turn before the tree was read,
     and reversed on reading it. COST: one turn. The reversal was put
     to the author as a decision rather than made silently, and
     accepted.

  10 CLAIMS FROM THE EARLIER MODEL THAT DID NOT SURVIVE THE SWITCH. A
     stated knowledge cutoff (January 2026) was the earlier model's.
     Decision [9] -- that models handle cross-language variance
     without anchoring -- was a bet placed on the earlier model and
     never observed on the later one. Neither is load-bearing in
     anything that landed. RF-PLAYBOOK-013.

  11 TWO SLIPS IN THIS THREAD'S OWN CLOSING WORK, both caught before
     commit by re-reading and by executing rather than asserting.
     RF-PLAYBOOK-015 first said "eleven files"; the recovered folder
     held ten. And the checksum list in item 8 was first typed by hand,
     abbreviated, with one tail wrong; it is now generated from the
     files. A checksum typed by hand is not a checksum.


DEFERRED

  Each has a home and no owner yet.

  The thread and artifact data model, and the tooling built on it.
    llm/handoff/PLAYBOOK-DESIGN-007_data-model-and-tooling.md carries
    it forward with a lean.
  The workflow dump, which closes the design record's open questions A
    and B. Same handoff.
  The ONE THREAD AT A TIME set (settled.md), revisited with question A.
  CONSTRAINT-008 and -009 describe a chat-only world. This thread ran
    in a session with a sandbox, a shell and file tools. Whether those
    two items are narrowed, and how a thread states which environment
    it has, was deferred by the author to the next thread.
  CONVENTION-001 assumes concurrent threads with disjoint id ranges,
    which CONSTRAINT-010 forbids. Left untouched in 0006 because it
    belongs to the same set as ONE THREAD AT A TIME.
  render.sh verify is blind to source-SHA drift. Carried from
    PLAYBOOK-DESIGN-006, still the root cause it named.
  Promotion of RF-PLAYBOOK-015, and of any invocation draft on its
    first real use.
  Which documents evolve by whole rewrite and which by itemized delta
    (settled.md OPEN, rule TWO).


REJECTED

  Placing the thread's files beside the tree (settled.md).
  Decision [8], rationale-free prompt bodies, for prompts/ (settled.md).
  SETUP.md as a committed file (WHAT LANDED).
  A second paste form of the preferences (0005).


HANDOFFS PRODUCED

  llm/handoff/PLAYBOOK-DESIGN-007_data-model-and-tooling.md
    the next thread's starting point
  llm/handoff/PLAYBOOK-DESIGN-007_harness-interface-and-build.md
  llm/handoff/PLAYBOOK-DESIGN-007_interface-sketch-seed.md
  llm/handoff/PLAYBOOK-DESIGN-007_invocation-drafts.md
