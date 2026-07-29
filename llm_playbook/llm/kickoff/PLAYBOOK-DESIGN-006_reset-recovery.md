THREAD PLAYBOOK-DESIGN-006_reset-recovery
date:     2026-07
from:     DRILL-IMPL-002_llm-corpus-consolidation, authored at its S1
          stop. 005 bounced and its number is not reused.
role:     DESIGN
baseline: playbook e19174f4dc07dbdc8ac9063aa64a84246fc817ce
          project  e19174f4dc07dbdc8ac9063aa64a84246fc817ce  same repo
          pre-reset 42298a27ad4abec49aa4dc12976b5c466b62f097
scope:    recover the four items the July 2026 reset removed that have
          a LIVE consumer, and amend R6. Writes in llm_playbook only.
          Does NOT touch preferences/ -- see OUT, that boundary is
          load-bearing and a collision, not a preference.

Unpack the attached archive, skim the tree, then read this file before
anything else. Restate the task in one sentence, state your strategy
and approach, and give your feedback, before planning anything.

  THERE IS NO RENDER FOR THIS PROJECT, AND THAT IS AN ABSENCE DECLARED
  UNDER R11 RATHER THAN AN OMISSION. The playbook has no CONTEXT.md of
  its own; every consumer project has one, composed from
  preferences/. Composing one for llm_playbook would require touching
  preferences/, which is OUT. So the kickoff template's binding
  sentence and stamp request cannot be satisfied here, and inventing a
  substitute would be worse than saying so.

  What binds you instead, in this order:
    1. the live human
    2. llm_playbook/protocol.md
    3. preferences/layers.md and preferences/style-contract.md, read
       DIRECTLY -- with two known contradictions listed under FINDINGS
       that you must NOT repair, because they are Wave B
    4. this file

  Where any of those disagree with the repository, the repository wins
  and you say so in the same breath (R1). Do not silently comply and
  do not silently ignore.

  THE ABSENCE OF A PLAYBOOK RENDER IS ITSELF A FINDING. Record it; do
  not fix it here.


TASK
  Five items. Four are recoveries from 42298a27; one is an amendment.
  Each is listed with its live consumer, because a recovery with no
  consumer is accretion and README's rule ONE forbids it.

  ALL FOUR RECOVERIES ARE SECTIONS, NOT RULES, AND THE AMENDMENT
  REPLACES R6 IN PLACE. THE TWELVE-RULE CAP DOES NOT FIRE. Do not
  spend a turn discovering this.

  T-1  CHAIN 1, INTO protocol.md PRECEDENCE.
       protocol.md today carries chain 2 only -- live human outranks
       the render, the render outranks everything else. The four-link
       compose-time chain is gone:

         live human > project instance > playbook > model defaults

       Recover it WITH the emission clause, which is the operative
       half: "the render emits ONLY the winner. The losing rule never
       reaches the model." And with the bottom link, "model defaults
       sit at the bottom: silence means the default stands."
       SOURCE   42298a27:llm_playbook/protocol/precedence.md, sections
                CHAIN 1 and CHAIN 2, plus the WORKED EXAMPLE.
       CONSUMER DRILL-IMPL-002 C-101a, blocked on this exact text.
       NOTE     scripts/render.sh lines 4-7 already cite "protocol.md,
                PRECEDENCE" for this rule. The citation is live and
                broken. This lands the text the script already claims
                exists.

  T-2  THE READ-ONLY CHECKOUT RULE, INTO protocol.md.
       "The playbook checkout a thread runs against is read-only from
       that thread's point of view. A precedence loss is never
       repaired by editing the playbook mid-thread: fixes travel as
       live human messages now and refinement entries for later, and
       reach the playbook only through a human editorial pass."
       SOURCE   42298a27:llm_playbook/protocol/precedence.md, section
                READ-ONLY CHECKOUT.
       CONSUMER every cross-project thread boundary. DRILL-IMPL-002's
                scope line restates it by hand because it has nowhere
                to cite. Its DEC-D5 and DEC-D8 rest on it entirely.
       NOTE     the pre-reset text credits ADR-004 for this. ADR-004
                does not say it; precedence.md does. Land the rule,
                drop the misattribution.

  T-3  THE type: VOCABULARY, INTO protocol.md IDENTITY AND NAMING.
       Twelve values, recovered verbatim:
         toolkit-rules      rules governing how the toolkit is used
         preference-source  the item sets a render composes from
         instance-rules     one project's rules: PROJECT.md
         prompt             a method, never an authority
         design plan handoff kickoff close    thread artifacts
         decisions refinements render         records and output
       Keep the distinction the source draws: toolkit-rules and
       preference-source differ because one governs authoring and the
       other is the material composed into a render.
       SOURCE   42298a27:llm_playbook/protocol/naming.md, section
                FRONTMATTER FIELDS, the type entry.
       CONSUMER eleven files in the current tree carry type: with no
                defined value set. DRILL-IMPL-002 C-118a and C-117
                assign types from this vocabulary and are blocked.
       DO NOT RECOVER the status field, the supersedes field, or the
       from/to/role handoff fields. The reset removed those
       deliberately and correctly -- see FINDINGS item 6.

  T-4  THE RF-PROJ-NNN GRAMMAR, INTO protocol.md IDENTITY AND NAMING.
       "Form: RF-PROJ-NNN, assigned in the project's refinements.md at
       entry time, zero-padded, never reused. A refinement entry that
       targets a preference item cites that item's id in its body.
       Example: RF-DRILL-012."
       SOURCE   42298a27:llm_playbook/protocol/naming.md, section
                REFINEMENT IDS.
       CONSUMER refinements.md states only its own RF-PLAYBOOK
                instance of a general rule. DRILL-IMPL-002 C-113c
                assigns RF-DRILL-001.. with no authority for the form.

  T-5  AMEND R6 WITH THE DELIBERATE-RED EXCEPTION.
       R6 today: "One concern each, each independently valid, the
       series bisects." CONVENTION-013 says the same. Neither admits a
       deliberately red commit.

       Three prompts already do:
         commit-planning.md   a whole section, "LET IT GO RED (a
                              deliberate tool, not sloppiness)"
         plan-review.md       "is it ONE commit or a DELIBERATE noted
                              red -- decided on purpose, not by
                              accident"
         spike-and-verify.md  a guard "must be GREEN on the clean code
                              AND RED on an injected violation"

       settled.md: "Where one appears to contradict a rule, the rule
       wins and the conflict is a finding." So today the allowance is
       forbidden by R6 and three prompts are findings against
       themselves.

       drill has ruled, in a real project: a deliberately-red commit
       IS permitted, because it confirms a test actually catches what
       it claims to catch. That is the second occurrence in a real
       project, which is the bar README's accretion rule ONE sets.

       Amend R6 to admit a red intermediate that is DECIDED ON PURPOSE
       AND NOTED IN THE MESSAGE, and never as a way to skip green
       discipline. This REPLACES R6's text; it does not add R13.
       CONSUMER DRILL-IMPL-002 P-4, whose residue this is.

  ANCILLARY, same thread, because each is one line and each is a live
  broken citation:
    a  README.md cites RESET-2026-07.md at the tree root, twice; it is
       at docs/. settled.md repeats the error once. README's WHAT IS
       HERE inventory has no docs/ entry at all.
    b  prompts/clone-and-verify.md cites transport.md, ADR-032 and
       ADR-021. transport.md's content is in README under TRANSPORT;
       ADR-032's substance is in settled.md as "reading is a pack,
       executing is a checkout"; ADR-021's is in README TRANSPORT.
       Repoint or drop; do not restore the ADR record.
    c  refinements.md RF-PLAYBOOK-004 takes a SECOND OCCURRENCE note.
       See FINDINGS item 2. Record it ON the existing entry, per that
       file's own rule; do not open a new id.
    d  settled.md gains three entries: the protocol.md size ruling
       (see STOPS S2), the narrowing in FINDINGS item 5, and the
       correction in FINDINGS item 4.

  DO NOT MODIFY scripts/pack-repo.sh. It cites ADR-021 and ADR-022 in
  its header and both are retired, so the citations dangle. Record
  that and leave the file alone: RESET-2026-07.md keeps it "untouched
  here precisely because that record is its value."


STOPS
  S1  THE RECOVERY INVENTORY, BEFORE ANY EDIT. One row per item T-1
      to T-5 plus the four ancillaries: the exact source lines at
      42298a27, the exact destination section, and the line delta.
      Deliver that table and wait. This is the whole first turn.
  S2  THE protocol.md SIZE RULING. protocol.md is 236 lines against a
      stated 150-line target that settled.md already concedes is a
      guess. T-1 through T-4 add roughly 110 lines. The reset
      consolidated six files into this one; putting four sections back
      is how it becomes six again. Rule on absorb-into-protocol.md
      versus restoring a second file, and record it in settled.md.
      DRILL-IMPL-002's lean is absorb, labelled a lean.
  S3  AFTER protocol.md IS REWRITTEN AND BEFORE THE ANCILLARIES.
      Accretion rule TWO: a change to a document REWRITES the
      document. protocol.md is delivered whole, not patched, and the
      whole-document re-read is the point of the rule.
  S4  DELIVERY. Answer R7's three delivery questions, and one more:
      does anything recovered here lack a live consumer? If so it is
      accretion and it comes back out.


DELIVERY FORM -- STATED BECAUSE IT HAS FAILED TWICE
  Two consecutive threads lost work to this. An eight-commit drill
  series was built as git-am patches against a sandbox SHA that does
  not exist in the author's repository, and was lost entirely; the
  content was correct and byte-verified. See FINDINGS item 2.

  You will receive a tar pack, which carries no .git. R12 sends a tar
  pack at a known SHA to a patch series, but README GOTCHAS says a
  patch built from that tarball cannot be git am'd, and accretion rule
  TWO says a document change rewrites the document. For prose files
  those resolve to:

    - deliver COMPLETE rewritten files with their paths
    - a git-apply-able unified diff is welcome ALONGSIDE, never
      instead, and never shaped for git am
    - state the baseline you built against
    - the author applies and commits locally against real HEAD

  Never cite a SHA from your own sandbox as a baseline.


HAVE
  llm_playbook/                    the post-reset tree, 17 files
  extracts/precedence-extract.txt  42298a27 CHAIN 1, CHAIN 2, WORKED
                                   EXAMPLE, READ-ONLY CHECKOUT
  extracts/naming-extract.txt      42298a27 FRONTMATTER FIELDS (type),
                                   REFINEMENT IDS, PREFERENCE ITEM IDS
  this file, whose FINDINGS section is verified evidence -- cite it,
  do not re-derive it


REQUEST
  The pre-reset tree is NOT packed. It is 36 files and about 84,000
  tokens, roughly half of it llm_playbook/llm/, and packing it would
  spend the context this thread needs to think. A read-only worktree
  is at /tmp/playbook-pre-reset (42298a27). Ask for a file BY NAME
  under R11 rather than working around its absence.

  Drill is NOT packed and is not this thread's business. If you think
  you need a drill file, that is a scope error -- say so instead.


OUT
  preferences/layers.md AND preferences/style-contract.md. This is the
  hard boundary and it is a COLLISION, not a preference.
  DRILL-IMPL-002's C-101 re-renders drill's CONTEXT.md from those two
  files; render.sh resolves its stamp SHA from
  git log -1 -- llm_playbook/preferences and nothing else. settled.md
  DECLARED ASSUMPTIONS: one thread at a time is load-bearing, and "the
  render hash is checked at KICKOFF only, because nothing can change
  the render mid-thread." Two threads editing preferences/ and a
  render built from it is exactly the case it forbids. Everything in
  preferences/ is Wave B and is serialized BEHIND DRILL-IMPL-002's
  C-101. Findings items 5, 6 and 7 name what is wrong in there; record
  them, change nothing.

  scripts/pack-repo.sh. Untouched by design.

  Any drill file, and any re-litigation of the reset. A disagreement
  with the reset is a finding for the handoff, not a change made here.

  Restoring any deleted file wholesale. Four sections have live
  consumers; the other 30-odd files do not, and git holds them all.

  ONE ACCEPTED BREACH, DECLARED. T-1 and T-5 rewrite PRECEDENCE and
  R6, which BIND the open DRILL-IMPL-002 thread. settled.md says a hot
  fix reaches an open thread through the live human channel only. The
  human is that channel. This is a real breach of the one-thread-at-a-
  time assumption and is recorded as one rather than assumed harmless.


FINDINGS -- VERIFIED, CITE RATHER THAN RE-DERIVE
  Produced by DRILL-IMPL-002 by execution against the tree.

  1  THE STALE-RENDER CHECK IS BLIND TO THE DRIFT IT EXISTS TO CATCH.
     drill's CONTEXT.md stamps preferences at 2d5ec7f1; preferences/
     last moved at a78e54e (2026-07-28). render.sh verify returns
     "stamp matches" anyway: it recomputes the body hash and compares
     it to line 2, and never re-resolves the SHA it prints. It detects
     hand-editing only. Every other finding in this list went
     unnoticed behind that green checkmark. Three lines inside verify
     would close it, and it rides a habit that already runs at every
     kickoff. NOT IN SCOPE HERE -- scripts/ beyond this is a separate
     call -- but it is the root cause and it should be next.

  2  RF-PLAYBOOK-004 HAS A SECOND OCCURRENCE, AND IT COST A WHOLE
     SERIES. An eight-commit drill consolidation was delivered as
     "git checkout e3aabfb; git am patches/*.patch". e3aabfb is a
     sandbox commit and does not exist in the author's repository:
     git rev-parse on it returns "Invalid revision range". The
     patches were verified byte-identical in the sandbox and were
     undeliverable. The fallback document, the ten replacement files,
     and the reasoning behind one reversed decision were all pasted
     into a chat and lost. ADR-023 predicted this exactly, and S27
     states the rule. Record on RF-PLAYBOOK-004; do not open a new id.

  3  llm_playbook HAS NO llm/ DIRECTORY AND protocol.md STILL
     REQUIRES ONE. RESET-2026-07.md deleted llm_playbook/llm/;
     protocol.md still specifies thread files at
     llm/<kickoff|handoff|close|plan>/<id>_<subject>.md. So THIS
     THREAD has nowhere to file its own kickoff or close artifact,
     and R9 makes the close artifact a thread's only durable trace.
     Rule on it at S1: recreate llm_playbook/llm/, or amend
     protocol.md to say where a playbook thread's own artifacts go.

  4  settled.md's ADR-022 ENTRY IS WRONG IN ONE SENTENCE. It says
     "this session decided the opposite before knowing ADR-022
     existed." ADR-009 lines 153-155 already said "the render pass
     composes public plus overlay". Render-time composition was
     decided at ADR-009 and ADR-022 overturned it silently. The reset
     RESTORED an earlier decision rather than overruling a settled
     one blind. That strengthens the entry; the sentence is still
     false. Correct it (R2).

  5  THE RESET'S REMOVAL LIST IS TOO BROAD ON ONE PHRASE. It retires
     "stable-forever ids". That is right for thread and document ids,
     where git holds the old numbers. It is wrong for PREFERENCE ITEM
     ids, which are cited from every committed render, and for
     REFINEMENT ids -- refinements.md already argues exactly this for
     its own ids. layers.md L1 is therefore CORRECT and must not be
     "fixed". Narrow the claim in settled.md instead.

  6  THE REMOVED FRONTMATTER FIELDS WERE THE ACCRETED ONES, AND THE
     RESET DID NOT KNOW IT. ADR-033 fixed a permitted set of six --
     date, type, scope, from, to, version -- with the closure rule "a
     field this list does not name is a finding, not an exception".
     naming.md ended with nine: status, role and supersedes were
     added later, to a list whose whole point was that additions are
     findings. The reset removed exactly those three. It un-accreted
     ADR-033's set without knowing that is what it was doing. It then
     added baseline: without noting it. Worth recording: the closure
     rule is the part with no home, not the list.

  7  preferences/ CONTRADICTS protocol.md IN TWO PLACES. WAVE B --
     RECORD ONLY, CHANGE NOTHING.
     a  layers.md CONSTRAINT-005 and style-contract.md S26/S27 give
        delivery form BY OPERATION TYPE -- new, edit, move, delete.
        That is ADR-023's text. settled.md records that exact rule as
        rejected and replaced by R12's baseline-fidelity test.
        Neither source carries R12's generated-file exception, so a
        render composed from them today instructs delivering a render
        as a diff, which is RF-PLAYBOOK-009's documented failure.
     b  layers.md CONVENTION-002 still mandates append-only records,
        [DECIDED]/[NOTE]/[FIX]/[OPEN] tags, superseded-entry markers
        and version-stamped status lines. The reset's removal list
        names three of those four.
     Also in Wave B: version: 0.1.0 survives in both preference
     sources, which is where drill's stale "v0.1.0" stamp came from
     and which render.sh argues against in prose; CONVENTION-001
     assumes concurrent threads that CONSTRAINT-010 forbids; and L3
     describes a private-overlay mechanism that was DESIGNED, never
     implemented, and never given a location in either tree. L3's
     clause is a deletion candidate, not a recovery.

  8  F-18's RESIDUE IS TWO ITEMS, NOT SEVEN. Drill's
     llm-thread-protocol.md was thought to hold seven things with no
     home. Five have landed: inlined ground truth, verified
     signatures and instincts-labelled-as-instincts are all in
     protocol.md HANDOFF; the STOP-points slot is the kickoff
     template's STOPS line; the sparse-clone recipe is
     clone-and-verify.md lines 51-53. Two remain with no home
     anywhere:
       i   do not paste committed docs unless they are unpushed, and
           if you do, say they are unpushed
       ii  never improve a shipped policy (grading, scheduling) by
           taste instead of by a metric named in advance
     Both are candidates, not obligations. Rule at S1 whether either
     has cost anything twice; if not, they wait in refinements.md.


STATE and COMMANDS blocks end every response (R10). At thread end,
add NEXT THREAD. The thread that follows this one is
DRILL-IMPL-002_llm-corpus-consolidation, resuming at its Phase 0.

CARRY-OVER NOTES FOR PLAYBOOK-DESIGN-006_reset-recovery
=======================================================
date:   2026-07
type:   handoff
from:   the reset-authoring session (PLAYBOOK-DESIGN-005, bounced)
scope:  what the session that BUILT the reset knows and the kickoff
        does not carry. Navigation of 42298a27, the surface that was
        never read, and the errors that produced the recovery. Not a
        second kickoff: the kickoff's FINDINGS are verified evidence
        and are not restated here.

  THIS FILE HAS NO HOME IN THE TREE. protocol.md specifies thread
  artifacts at llm/<kickoff|handoff|close|plan>/ and llm_playbook has
  no llm/ directory. That is the kickoff's FINDINGS item 3 and it is
  my error, not a discovery. Park this wherever S1 rules.


READ THIS FIRST: MY CLAIMS ARE VERIFY-FIRST

  The applied tree DIVERGED from the tree I delivered. Confirmed in
  at least one place: I delivered RESET-2026-07.md at the tree root
  and the kickoff reports it at docs/. My README citations were
  correct when written and broke when the file moved. Ancillary (a)
  is therefore a divergence, not a bug I introduced, and there may be
  others I cannot see.

  Every file path, line count and section name below is from the
  SANDBOX at 42298a27 or from the tree as DELIVERED. Check against
  the real repository before relying on any of it (R1).


NAVIGATING 42298a27 -- THE PART THAT IS EXPENSIVE TO REDERIVE

  Full inventory, 36 files, 335,968 bytes, ~84,000 tokens.

  The two files the recoveries come from are SMALL. Read them whole
  rather than extracting; there is no economy in slicing them.
    protocol/precedence.md    3,777 bytes. Sections: CHAIN 1, CHAIN 2,
                              WORKED EXAMPLE, READ-ONLY CHECKOUT.
                              T-1 and T-2 are the entire file minus
                              its frontmatter.
    protocol/naming.md       12,054 bytes, 241 lines. T-3 is under
                              FRONTMATTER FIELDS, the type entry.
                              T-4 is under REFINEMENT IDS. Adjacent
                              section PREFERENCE ITEM IDS is what
                              FINDINGS item 5 is about.

  decisions/era-2026-q3.md is 43,987 bytes and has a TWO-PART shape
  that is not obvious and cost me a wrong judgment:
    lines ~18-58   an INDEX: one title line per ADR, no reasoning
    lines ~61-770  the BODY: full entries with Context, Decision,
                   Alternatives, and later Amendment notes
  I read the index and judged the bodies from it. That is how ADR-009
  was missed (FINDINGS item 4) and how ADR-033's closure rule was
  missed (FINDINGS item 6). To locate one entry:
    grep -n "^ADR-0NN" decisions/era-2026-q3.md
  The first hit is the index line; the second is the body. Amendment
  notes are appended INSIDE an entry, sometimes years of reasoning
  after the original, so reading the first paragraph of an entry is
  the same mistake at smaller scale. ADR-012 is the example: its
  archive/ clause is REVERSED in an amendment, with reasoning that is
  the reset's own reasoning.

  llm/ is 158,701 bytes, ~40,000 tokens, half the pre-reset tree.
  Never pack it. Everything in it that had durable value has already
  been promoted -- I verified this for the one discrepancies section
  that exists, in llm/close/PLAYBOOK-IMPL-004, where D5 became
  RF-PLAYBOOK-007 and D2 became CONSTRAINT-013.


THE UNREAD SURFACE -- WHERE A FIFTH SALVAGE WOULD HIDE

  The recovery exists because I judged files from summaries. Four
  salvages have come out of two passes. This is the remaining
  exposure, ranked by how likely it is to hold something live. If
  S1's inventory has room for one speculative read, take the first.

  1  llm/plan/PLAYBOOK-DESIGN-002_r3-plan-locate-replace-edits.md
     7,624 bytes. NEVER OPENED. The title is edit-delivery mechanics,
     which is the exact domain where two threads have now lost work
     (RF-PLAYBOOK-004's second occurrence, kickoff FINDINGS item 2).
     If a general locate-and-replace delivery rule was ever written
     down, it is here. Highest-value unread file in the tree.

  2  ADR-013, ADR-011, ADR-031, ADR-027, ADR-029. Bodies never read.
     013 is "render priority: CONTEXT.md first; CORRECTED PREDICTION"
     -- a recorded wrong prediction, which is the shape of thing that
     earns its place. 011 is "lite mode", a concept with no trace in
     the reset tree at all. 031 is "render ceiling is tier-dependent"
     and drill's plan assigns model tiers, so it may have a live
     consumer.

  3  llm/plan/implementation-plan.md, 37,664 bytes, the largest
     unread file. Marked outdated and probably is, but it is
     referenced by ADR-012's amendment for a project skeleton at
     T-011, so it is cited by something.

  4  Three close artifacts read only at their heads: DESIGN-002
     (10,716), IMPL-003 (8,789), DESIGN-004 (4,194). Only IMPL-004's
     DISCREPANCIES section was read. protocol.md itself argues that
     section is the one thing that cannot be reconstructed later, so
     the argument for reading the other three is protocol.md's own.
     Counter-argument, and the reason I rank it fourth: the one I did
     read had already been fully promoted.

  5  Three handoffs read only at their heads: DESIGN-002-to-IMPL-003,
     DESIGN-004-to-IMPL, IMPL-003-to-DESIGN-004.

  If a read produces nothing, SAY SO. A negative result here is worth
  recording, because it is what lets a later thread stop looking.


WHAT I GOT WRONG, SO IT IS NOT REDISCOVERED AS A MYSTERY

  1  protocol.md's size was misreported. I stated 177 lines against a
     150 target when the file was first written, then rewrote it much
     larger and never re-measured. It is 236. S2 rules against 236.
     The 150 was my guess and I would not defend it: it was the same
     kind of hand-set number as the check.sh budgets the reset
     retired, and settled.md already concedes that.

  2  I deleted llm_playbook/llm/ while leaving protocol.md requiring
     it. FINDINGS item 3. Straightforward oversight.

  3  I judged 20-odd ADRs from their index titles. FINDINGS items 4
     and 6 are both consequences. The specific failure: reading a
     summary line and treating it as the content.

  4  R12 was written to send everything through a patch after a tar
     pack. RF-PLAYBOOK-009 says a generated file cannot be. The hole
     was found only because refinements.md was read on its way to
     deletion. R12 now carries the exception; the near-miss is why
     the kickoff's DELIVERY FORM section exists.

  5  I handed over a command sequence containing rm -rf against a
     tracked tree with no preceding status check. That is
     RF-PLAYBOOK-007's shape and it is logged there as a second
     occurrence.


ON THE KICKOFF ITSELF

  It is better than the one it replaces and I have two notes.

  T-5's evidence is the strongest item in the set and is worth
  stating that way in the close. Three prompts already permit a
  deliberate red, settled.md makes each of them a finding against
  itself, and drill then ruled in a real project. That is the
  accretion rule ONE bar met exactly as designed -- first occurrence
  sitting unpromoted, second occurrence in real use licensing the
  change. It is the first time the mechanism has fired on its own
  terms, and that is worth recording independently of the amendment.

  S2's framing understates the case for absorbing. "Putting four
  sections back is how it becomes six again" is true of file COUNT
  and not of the failure the reset addressed. Six files failed
  because they cross-referenced and contradicted each other -- the
  close-artifact filename stated three times and wrong twice. Four
  sections inside one file cannot do that, because the whole-document
  rewrite rule forces a re-read of all of them. The number that
  should decide S2 is whether protocol.md still gets read end to end
  at 350 lines, not whether it is longer than a target I invented.


UNTESTED MECHANISMS -- THIS THREAD IS THEIR FIRST REAL EXERCISE

  I wrote RECOVERING WITH GIT and never ran any of it against the
  real repository. All of it was written from knowledge, which is the
  thing R3 exists to stop. Specifically untested:
    git worktree add /tmp/playbook-pre-reset 42298a27
    git show 42298a27:llm_playbook/<path>
    git log -S'<phrase>' -- llm_playbook
  The kickoff says a worktree is already at /tmp/playbook-pre-reset,
  so the first has now been exercised by the author. If any of the
  three misbehaves, that is a finding against README and it is worth
  more than the recovery itself, because the entire licence to delete
  30 files rests on those commands working.

  Also untested by me: pack-repo.sh in any mode. Its interface is
  documented in README TRANSPORT, recovered from the pre-reset
  transport.md, and I have run neither.
