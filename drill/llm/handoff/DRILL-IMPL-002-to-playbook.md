HANDOFF -- DRILL-IMPL-002 to the next playbook thread
=====================================================
date:  2026-07
type:  handoff
from:  DRILL-IMPL-002_llm-corpus-consolidation
to:    unassigned; a playbook thread, and a drill thread for the
       deferred half
scope: what the next thread inherits, what is settled, and what is
       open. Findings only -- this thread wrote no byte in
       llm_playbook.

VERIFIED GROUND TRUTH (verify-first; copied from the files, not from
memory)

  llm_playbook last-touch SHA     6ad14830a21a6122c5abc8ead036f8eccffb61a5
  drill last-touch SHA            8ff47f7d074bd4a8c7031aa2d8d86496cbadf895
  (both from git log -1 --format=%H -- <path>; these are last-touch
  per subtree, NOT a baseline. The kickoff's baseline: field wants
  git rev-parse HEAD and HEAD:drill/llm. That distinction cost a turn
  here.)

  style-contract.md defines S1..S30 and D1..D3.
  protocol.md defines R1..R12.
  llm_playbook holds 18 files. RESET-2026-07.md records 17 and
  settled.md reasons from "seventeen"; llm/ came back with a close
  artifact after that count was written. The DRILL-IMPL-002 kickoff
  says 16. Three numbers in circulation for one tree.

  The pre-reset playbook is recoverable at 42298a27, cited nine times
  across the committed corpus.

SETTLED -- do not reopen

  The reset's removals hold. No supersedes field, no status
  vocabulary, no append-only requirement, no rename ceremony. The
  five-tier prompt standing is not recovered and is not coming back;
  any contract clause asserting prompt-versus-playbook precedence is
  void rather than merely unsourced.

  git does not store renames. Verified by execution: git mv and
  mv + git add produce byte-identical trees, log --follow works
  either way, and -M reports the rename from content similarity. No
  history rewriting is needed for any move, and none should be done:
  ten committed documents cite SHAs.

  Drill's handoff filenames have four coexisting shapes and no
  governing form. This is deliberate, logged upstream as
  RF-PLAYBOOK-010, unpromoted.

FINDINGS FOR THE PLAYBOOK

  1. RF-PLAYBOOK-004's fix never landed. The diagnosis is precise --
     the missing rule is "never cite a SHA the author's repository
     does not contain," and its stated home is "the kickoff
     template's delivery paragraph." There is no delivery paragraph
     in the kickoff template. The diagnosis landed; the fix did not.

     The second occurrence it describes is now filed rather than
     homeless: drill/llm/plan/consolidation-patch-series-record.md,
     which instructs a reader to git checkout e3aabfb -- a sandbox
     commit the author's repository does not contain.

  2. render.sh verify aborts on a git guard it does not use.
     WORKTREE_ROOT is set ahead of the case statement and referenced
     only in the stamp branch, so verify -- a pure local hash
     comparison -- is blocked by a precondition irrelevant to it.
     Running it against a pack returns "not inside a git repository"
     and exit 1.

  3. render.sh verify cannot detect staleness, only post-stamp
     editing. drill's CONTEXT.md verifies clean while carrying a
     pre-reset stamp format (a v0.1.0 segment the current stamp mode
     does not emit). verify parses with sed 's/.*content-hash //',
     which is format-agnostic and swallows it. settled.md already
     says staleness detection lives in the reading model; worth
     stating in render.sh's own header, since the exit code reads as
     a clean bill of health.

  4. The landed DRILL-IMPL-002 kickoff carries no type: kickoff,
     against a template that requires it and a rule that says
     frontmatter and not path carries classification. Its baseline:
     field is the unfilled placeholder <SHA-AFTER-RESET-COMMIT>.

  5. settled.md:61 says instance rules "append to or supersede a
     section." protocol.md's WORKED EXAMPLE resolves at rule level --
     one commit-message rule beats one playbook rule, and the render
     omits the playbook form entirely. The two disagree about the
     granularity chain 1 operates at. This thread's position is rule
     level: protocol.md is the newer consolidated authority and
     settled.md:61 is a line that survived consolidation without
     being reconciled. Not ruled by the author; it only gates C-101,
     which is deferred.

  6. The status vocabulary was removed more completely than intended.
     The author's report: it was doing useful work and the reset
     overdid it. Because archive/ had already been retired on the
     reasoning that frontmatter would carry supersession, its removal
     left no mechanism at all for marking a document retired. Drill
     is proving a restored contract locally first, in PROJECT.md
     under chain 1 -- which is the accretion rule running forwards
     rather than a workaround. Promote on evidence, not on this note.

  7. The playbook still has no render of its own. Deliberate, but it
     means a playbook thread's kickoff cannot carry the binding
     sentence or the stamp request its own template requires.

  8. The twelve-value type: vocabulary is playbook-shaped and does
     not fit a project corpus. Against drill's root, roughly eight of
     thirty-eight mapped cleanly. With the closure clause -- "a value
     this list does not name is a finding, not an exception" -- the
     literal reading yields twenty findings rather than twenty
     assignments. Drill's answer is to extend the vocabulary in
     PROJECT.md under chain 1. If a second project reaches the same
     conclusion, the closure clause is what needs revisiting.

OPEN, WITH THIS THREAD'S LEAN LABELLED AS A LEAN

  a. verification-practices.md is cited three times in drill --
     CODING_CONVENTIONS.md:159, thread-launch-kit.md:63 and :335 --
     and exists nowhere in drill or the playbook.
     LEAN: it is llm_playbook/prompts/runtime-verification.md under
     an older name. That is a guess and was deliberately not acted
     on.

  b. CONTEXT.md cites precedence.md; PROJECT.md cites precedence.md
     and naming.md. All deleted by the reset.
     LEAN: CONTEXT.md's is C-101's to fix; PROJECT.md's is two lines
     and should go in whenever PROJECT.md is next opened.

  c. CONTEXT.md's CONVENTION-002 mandates append-only living records
     with superseded entries marked rather than deleted. The reset
     removed exactly that. It is a layers.md item, so it is a
     playbook-side conflict as well as a chain-1 conflict C-101 must
     resolve.
     LEAN: the reset wins and CONVENTION-002 should be rewritten
     upstream, not overridden per-project.

  d. Whether the DONE-annotated blocks in thread-launch-kit.md are
     live kit entries or records of prompts already sent. This thread
     treated them as live and rewrote their paths.
     LEAN: live. The annotation was appended to a kit entry rather
     than written as history.

WHAT THE NEXT DRILL THREAD INHERITS

  The deferred commits are listed in the close artifact with the
  reason each was not taken. The order this thread would take them:
  P-5's frontmatter contract in PROJECT.md, then the classification
  pass (C-117/C-118/C-119), then C-104's STATUS.md rewrite, then
  C-101 once the granularity question is answered.

  C-123 is nearly free now: decisions.md is the only non-ASCII file
  left, the other having been retired.
