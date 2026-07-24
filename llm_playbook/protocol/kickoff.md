KICKOFF
=======
date: 2026-07
type: kickoff
scope: the KICKOFF and HANDOFF templates. A kickoff opens a thread
and states what binds it; a handoff closes one and states what the
next thread inherits. Both were previously retyped as prose per
thread, which is why the binding sentence could go missing without
anyone noticing (ADR-030).

WHY THIS FILE EXISTS
  ADR-020 fixed WHERE the render lives. Nothing made a thread READ
  it. G-1b gave a design thread the whole drill archive -- 115
  files, on the order of 400k tokens -- and it never opened
  CONTEXT.md; it found and followed the project's own competing
  style document instead, by its own initiative. Six of seven style
  checks still passed, sourced from that document and from the
  surrounding code, so the pass rate concealed a render with zero
  influence. Placement is not salience. A kickoff must NAME the
  render and SAY that it binds.

  render.md refers to a "kickoff skeleton" that requires the model
  to state the stamp it sees. That skeleton had no definition
  anywhere in the playbook. This file is that definition.

--------------------------------------------------------------------
KICKOFF TEMPLATE
--------------------------------------------------------------------
Fill every FILL-IN. Delete no line: a line with nothing to say is
answered with "none", not removed. The binding sentence and the
stamp statement are NOT optional in either delivery mode.

  THREAD <PROJ-ROLE-NNN>
  date:  <YYYY-MM>
  type:  kickoff
  role:  <DESIGN | IMPL | CAPTURE>
  scope: <one or two sentences: what this thread does, and the
         boundary it must not cross>

  WHAT BINDS YOU
    <project>/llm/CONTEXT.md is the rendered context for this
    thread and it BINDS you. It is the single authority here; the
    only thing that outranks it is me speaking now. Read it FIRST,
    before any other file in this repository, and before you plan
    anything.

    Other documents in this repository may look like they govern
    style, process, or conventions. They do not. Where any document
    disagrees with the render, the render wins and you flag the
    disagreement rather than following it silently.

    [ARCHIVE MODE] The archive is attached. Unpack it and read
    <project>/llm/CONTEXT.md before anything else.
    [PASTE MODE] The render is in the block below, first, ahead of
    all other pasted material.

  STATE THE STAMP
    Before your first substantive answer, quote line 2 of the
    render -- the stamp line -- back to me, and confirm the file
    you read it from. If you cannot find the render, STOP and say
    so; do not proceed on general knowledge or on another document
    you found instead.

  READ NEXT
    <STATUS.md for live status; the governing plan; anything the
    task specifically needs. Everything here is subordinate to the
    render.>

  TASK
    <the actual work, in the plan's commit-id grammar where a plan
    exists>

  OUT OF SCOPE
    <what this thread must not touch; what is already decided and
    is not reopened here>

NOTES ON USE
  - One kickoff opens one thread; a thread declares its id in its
    first message (rule R13, thread-protocol.md).
  - The binding sentence is one sentence and it is load-bearing.
    Shortening it to "context is attached" reproduces exactly the
    failure this file exists to prevent.
  - Do NOT move the binding instruction into pack-repo.sh. Transport
    moves bytes and did its job correctly throughout G-1; making the
    packer emit prompts couples transport to protocol, so every
    later protocol change would require a packer change (ADR-030).

--------------------------------------------------------------------
HANDOFF TEMPLATE
--------------------------------------------------------------------
Filename: <FROM>-to-<TO>.md in the project's handoff/ directory,
where FROM is the sending thread id in full form and TO is the
receiving thread id if known, else the receiving ROLE word
(naming.md). The directory carries the classification, so the
filename does not repeat it; the type field below keeps the file
self-describing when it is read away from its directory. One
handoff, one file; a revision supersedes in place.

  HANDOFF -- <FROM> to <TO>
  date: <YYYY-MM>
  type: handoff
  from: <sending thread id> (<role>; <gate or plan position>)
  to:   <receiving thread id or ROLE> (<what it may and may not do>)
  why a <ROLE> thread: <why this role and not another. If the work
    needs decisions recorded before execution, say so: an
    implementation thread would have to invent the design silently,
    which the deviation rule forbids.>

  READ FIRST
    <the two or three documents this handoff assumes and does not
    restate, each with one line on what it contains>

  STATE
    <where things actually stand: what passes, what fails, what is
    shut and why. Name the gate if one is open.>

  WORK, IN DEPENDENCY ORDER
    <numbered items. Where one item unblocks another, say which and
    why doing them out of order wastes a run.>

  WHAT NOT TO DO
    <the paths that look reasonable and are wrong, each with the
    reason. A bare prohibition gets re-litigated; a reason does
    not.>

  WHAT IS SOUND AND SHOULD NOT BE REDONE
    <what is verified and must not be rebuilt, so the next thread
    does not spend its budget re-deriving settled work>

  OPEN ITEMS
    <O-numbered, each with: what it is, why it is still open, and
    whether anything is blocked on it>

NOTES ON USE
  - The close artifact (close-<THREAD-ID>.md, naming.md) records the
    terminal state; the handoff records what the NEXT thread needs.
    They overlap and are not the same document.
  - A handoff that only lists what was done is not a handoff. The
    dependency order and the WHAT NOT TO DO section are the parts
    that survive contact with the next thread.
  - Corrections belong in the handoff that carries them forward: if
    a draft of this handoff was wrong, say so in it and say what
    the correct reading is, rather than quietly fixing it.
