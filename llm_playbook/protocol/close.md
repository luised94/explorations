CLOSE
=====
date: 2026-07
type: toolkit-rules
scope: the CLOSE ARTIFACT template. A close artifact is the durable
  trace of a thread whose conversation is gone (R13). This file says
  what one must contain; naming.md says what it is called and
  thread-protocol.md R12 says when one is mandatory.
status: current

WHY THIS EXISTS
  R12 has made a close artifact mandatory for landed, bounced and
  abandoned threads since it was written, and no template was ever
  specified. The three close artifacts in this repository consequently
  have three different shapes, and not one of them records the
  discrepancies the thread hit or how they were resolved -- which is
  the part a later reader most often needs and the part no one
  reconstructs from a diff.

CLOSE TEMPLATE
  Fill every section. A section with nothing in it says "none" rather
  than being deleted: an absent section reads as forgotten, and R12's
  no-absence-as-signal rule applies to the artifact as well as to the
  status line.

  CLOSE -- <THREAD-ID>
  ====================
  date: <YYYY-MM>
  type: close
  scope: <one line: what this thread did, and that it governs nothing>
  status: current

  TERMINAL STATE
    <landed | bounced | parked | abandoned>, and confirmation that the
    matching state line has been flipped in the project's STATUS.md.
    The artifact is not the record; the STATUS line is. This section
    says the record was written.

  WHAT LANDED
    What was accomplished and implemented, as commits or artifacts a
    reader can go and look at. Not intentions.

  DISCREPANCIES AND HOW THEY WERE RESOLVED
    Every place the work did not match the plan, the documents, or the
    repository, and what was done about each. Include the thread's own
    mistakes and what they cost. This is the section that does not
    survive in the diff and cannot be reconstructed later.

  DECISIONS MADE
    Each decision and WHERE it is recorded -- an ADR id, a rule
    number, a refinement id. A decision recorded only here is a
    decision that will be re-litigated, because nobody reads a close
    artifact to find out what the current rules are.

  DEFERRED
    Ideas and features considered and not done, each with the reason.
    Distinguish deferred (worth doing, not now) from rejected (decided
    against), because the two invite opposite treatment on revival.

  WHAT IS SOUND AND MUST NOT BE REOPENED
    Work that is settled, so the next thread does not spend its
    context re-deriving it.

  NEXT STEPS
    What the next thread inherits, and the handoff artifacts produced,
    by filename. If the work continues, the handoff carries the
    detail and this section points at it; a close artifact and a
    handoff are different documents and neither substitutes for the
    other.

NOTES ON USE
  - A PARKED thread writes no new close artifact: its existing design
    artifacts ARE its close (R12), and the only ritual is the STATUS
    line. Promote to a full close artifact only on revival.
  - One thread, one close artifact. A revision supersedes in place;
    git keeps the history.
  - Filename and location: naming.md. It is llm/close/<THREAD-ID>_
    <descriptive>.md -- the id names the thread and the descriptive
    segment names the SUBJECT, never the genre (N6, N7).
  - The prompt that produces this, at close time, is: summarise what
    was accomplished and implemented, the discrepancies and issues
    encountered and how each was solved, the decisions made, anything
    deferred, and what the next thread needs. That prompt is the
    source of this template's sections, and the sections are the
    contract; the prompt is just a convenient way to ask for them.
