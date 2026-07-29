PROTOCOL
========
date: 2026-07
type: toolkit-rules
scope: how a thread runs. Identity, roles, naming, precedence, the
  twelve rules, and the three templates. This is the whole protocol;
  there is no second file.

RULE CAP: TWELVE. A thirteenth requires naming the rule it replaces,
in prose, in the same edit. Answering is mandatory; the outcome is
not -- "this is the thirteenth and here is why" is valid, recorded in
settled.md. The cap is a guess. Its value is not that twelve is right
but that it forces the comparison, which a size warning never did.


PRECEDENCE
  There are TWO chains, and confusing them was the defect this
  section exists to repair. A stateless model cannot arbitrate a
  chain whose lower links it never sees, so the long chain is
  resolved by the human BEFORE the model is involved, and the model
  is left a chain of exactly two links.

  CHAIN 1 -- AUTHORING AND RENDER TIME, resolved by the HUMAN

    live human > project instance > playbook > model defaults

  Applied whenever a render is built or a document is written. The
  human composing CONTEXT.md resolves every conflict between a
  project instance rule and a playbook rule in the instance's
  favor, and THE RENDER EMITS ONLY THE WINNER. The losing rule never
  reaches the model. Model defaults sit at the bottom: a render or a
  document may explicitly override a model's habitual behavior, and
  silence means the default stands.

  CHAIN 2 -- RUNTIME, the only chain a model arbitrates

    live human message > whatever was rendered. Full stop.

  A thread never re-resolves chain 1, because the render already
  collapsed it: from inside a thread the render is a single
  consistent authority, and the only thing that outranks it is the
  human speaking now. A thread that starts weighing "playbook versus
  instance" mid-thread is answering a question that was closed before
  kickoff. Where the render disagrees with observed reality, follow
  reality and say so (R1).

  This is still TWO runtime tiers, not four. Chain 1 is not a live
  hierarchy; it is a composition the human already performed, and it
  leaves nothing behind for a thread to weigh.

  WORKED EXAMPLE, walking both chains
    A project instance rule says "commit messages carry no plan ids"
    while the playbook commit form below expects them. Chain 1: the
    human building that project's CONTEXT.md resolves instance over
    playbook; the render states the no-plan-id rule and omits the
    playbook form entirely. Chain 2: mid-thread the human writes
    "actually, include plan ids from now on." The live message beats
    the render immediately, the thread complies for the rest of its
    life, and the change is filed as a refinement entry (RF-PROJ-NNN)
    in the project's refinements file. The regenerated render serves
    the NEXT thread; this one runs to completion on the live
    correction alone.


READ-ONLY CHECKOUT
  The playbook checkout a thread runs against is read-only from that
  thread's point of view. A precedence loss is never repaired by
  editing the playbook mid-thread: fixes travel as live human
  messages now and refinement entries for later, and reach the
  playbook only through a human editorial pass.


IDENTITY AND NAMING
  Thread id      PROJ-ROLE-NNN_descriptive. One shared counter per
                 project across all roles, so ids totally order
                 threads. PROJ is uppercase and must not be DESIGN,
                 IMPL or CAPTURE. The descriptive segment exists so
                 the id can be READ: it goes in the chat title.
                   PLAYBOOK-DESIGN-005_protocol-reset
  Roles          DESIGN, IMPL, CAPTURE. A thread plays exactly one.
  Filenames      lowercase, dateless, hyphenated, naming the SUBJECT
                 -- never the genre, never the position in a process,
                 both of which go stale. Where the name is an id, the
                 subject follows an underscore; one split on "_"
                 recovers the id.
  Thread files   llm/<kickoff|handoff|close|plan>/<id>_<subject>.md.
                 A cross-project slot carries the project code; an
                 unqualified one is self-referencing.
                 <id> IS THE THREAD THAT WROTE THE FILE. A close or a
                 handoff carries the sender's id; a kickoff carries
                 the RECEIVER's, because a kickoff is a handoff
                 written at the receiving end. So one listing of
                 llm/ finds everything a given thread authored,
                 which is the property the id is in the name for.
  Commits        <proj>: <summary>, or <proj>: <plan-id> <summary>
                 where a plan exists.

  Git holds provenance. No supersedes field, no status vocabulary, no
  append-only requirement, no rename ceremony: rewrite the file and
  let history carry what it said before (README, RECOVERING WITH GIT).

  THE type FIELD. Every document here carries type: in its
  frontmatter rather than taking its classification from its
  directory, because THE PATH DOES NOT SURVIVE TRANSPORT: these
  documents are packed into an archive or pasted whole into a chat,
  and a file classified by its directory arrives with no
  classification at all. The directory is shelving; the frontmatter
  is the claim. README.md carries no type: -- its name is its role.

    toolkit-rules      rules governing how the toolkit is used:
                       protocol.md
    preference-source  the item sets a render composes from:
                       layers.md, style-contract.md
    instance-rules     one project's rules: PROJECT.md
    prompt             a method, never an authority
    design plan handoff kickoff close    thread artifacts
    decisions refinements render         records and output

  toolkit-rules and preference-source are distinguished because one
  governs authoring and the other is the material composed into a
  render -- a difference in kind, not in shelving. A value this list
  does not name is a finding, not an exception.

  REFINEMENT IDS. Form RF-PROJ-NNN, assigned in the project's
  refinements.md at entry time, zero-padded, never reused. A
  refinement entry that targets a preference item cites that item's
  id in its body. Example: RF-DRILL-012.


BASELINE
  Every kickoff records the SHA of BOTH repositories, separately,
  even when they are currently the same repository. They will not
  stay that way: worktrees, and a playbook shared with projects
  outside one tree, are the expected direction, and a single
  unlabelled SHA becomes unrecoverable the moment that happens.

    baseline  playbook <sha>  project <sha>  [same repo | separate]

  A thread that cannot verify a SHA says so under R11 rather than
  assuming the two moved together.


THE RULES

  R1  REPO WINS. The repository is ground truth; documents are leads.
      Where a document and the tree disagree, follow the tree and say
      so in the same breath. Neither comply silently nor ignore
      silently.

  R2  CORRECTIONS ARE FINDINGS. A correction to the plan, the docs or
      a prior thread's work is reported plainly, including your own
      and including work already delivered. No apology spiral.

  R3  SPIKE BEFORE SPEC. Prove a risky assumption with the cheapest
      experiment before writing it into a plan. The spike's output is
      a handoff artifact and travels with the plan; an unrecorded
      spike is a measurement that will be taken twice.

  R4  DECISION-FRAMED DOCS. Where a document makes a choice, it
      carries the alternatives, ranked and scored, one line of
      rationale each, and a single recommendation. Never an unranked
      list; never a decision taken silently.

  R5  DOCS LAND FIRST. The governing document is amended before the
      code that departs from it, not after.

  R6  ONE COMMIT AT A TIME. One concern each, the series bisects, and
      the message states WHY. A comment-only or no-op commit says so.
      A commit MAY be red where the red is decided on purpose and
      said so in the message: a welded pair that cannot split into
      two green commits, or a change landed to watch a guard fire
      before it is fixed, which is the only evidence that the guard
      catches what it claims to catch. The repair follows in the very
      next commit, so a deliberate red spans one commit and a bisect
      skips it rather than reporting it. Never as a way to skip green
      discipline.

  R7  STOP POINTS. Pre-declared checkpoints where the thread
      summarizes what landed, surfaces deviations, asks the open
      questions, and waits. Undecided forks go here; deciding them
      silently is the failure mode. Drift between the plan and the
      tree is REPAIRED at a stop, not noted and worked around.
      At a DELIVERY stop, answer three more: did anything called
      design smuggle in an implementation decision; did a decidable
      fork stay open out of caution; is there a materially simpler
      design that gets 80 percent of the value.

  R8  ADVERSARIAL PASS. After a plan is agreed and before it is
      implemented, a separate turn attacks it: what is unconsidered,
      what would make this go wrong, what is already broken that this
      change will expose.

  R9  IDENTITY AND TERMINAL STATE. A thread declares its id in its
      first message and its terminal state in its last: landed,
      bounced, parked or abandoned. The conversation is ephemeral;
      the close artifact is its only durable trace. Absence is never
      a signal -- a thread that stopped appearing is unrecorded.

  R10 STATE THE TURN. Every response ends with the STATE and COMMANDS
      blocks below. Where the human must act, give the exact command
      and the output that means success -- never a description of a
      command. Nothing is assumed run, picked up by tooling, or
      received until a human reports it.

  R11 DECLARE ABSENCE. Nothing material is left unstated. An empty
      slot says "none" rather than being omitted, because an omission
      reads as forgotten and cannot be told apart from an oversight.
      Three cases: a section with nothing in it; background data,
      assumptions or reasoning the reader cannot see; and a missing
      input -- for which say what is missing, why the thread cannot
      proceed, and exactly how to supply it. Do not guess, work
      around, or proceed on a plausible substitute and label it in
      passing.

  R12 DELIVERY FORM FOLLOWS BASELINE FIDELITY. A patch is correct
      exactly when the exact bytes are held: after a tar pack at a
      known SHA, deliver a git-apply-able series covering creates,
      edits, renames and deletes alike, stating the baseline. After a
      paste, a partial file set, or any doubt about drift, deliver
      whole files with their paths. Operation type does not decide
      this -- git apply handles all four. One exception, regardless of
      fidelity: a GENERATED file is never delivered as a patch. Its
      base is its SOURCES, not its previous text, so both sides can
      differ correctly in a provenance line and the diff conflicts
      there. Deliver its body plus the command that regenerates it.
      When unsure which case you are in, that is an absence: declare
      it under R11 and ask.


THE STATE AND COMMANDS BLOCKS
  End every response. No prose inside them.

    STATE
      done     <n> of <n>
      next     <the next unit of work>
      blocked  <what on, or none>
      need     <files to paste or attach, or none>
      you      <the decision required, or nothing>

    COMMANDS
      <exact command>
      # expect: <the output that means it worked>

  COMMANDS says "none" when there are none. That is the point of it:
  a missing block cannot be told apart from a forgotten one (R11).

  At thread end, add:

    NEXT THREAD
      title    <the thread id to paste into the chat title>
      pack     <the exact pack-repo.sh invocation>
      attach   <the handoff file>
      say      "unpack, skim the tree, read the kickoff"

  THE EXEMPLARS IN THIS FILE ARE FORMS, NOT JUDGMENTS. Every filled
  example here is a shape to copy. There is deliberately no example
  close artifact, design or decision: anchoring on a form aids
  consistency, while anchoring on someone else's reasoning replaces
  your own.

    STATE
      done     4 of 11
      next     fold the residue items into the kickoff template
      blocked  none
      need     none
      you      rule on item 7 before the close artifact can be named

    COMMANDS
      none


KICKOFF
  A kickoff opens a thread. It is a handoff written at the receiving
  end, and it is the only document that may bind.

    THREAD <PROJ-ROLE-NNN_descriptive>
    date:     <YYYY-MM>
    type:     kickoff
    from:     <sending thread id, or none>
    role:     <DESIGN | IMPL | CAPTURE>
    baseline: playbook <sha>  project <sha>  [same repo | separate]
    scope:    <what this thread does, and the boundary it must not
              cross>

    Unpack the attached archive, skim the tree, then read this file
    before anything else. Quote line 2 of <render path>, restate the
    task in one sentence, state your strategy and approach, and give
    your feedback, before planning anything. If you cannot find the
    render, STOP and say so.

    <render path> BINDS you. Other documents may look like they
    govern style or process; they do not. Where one disagrees with
    the render, the render wins and you flag it rather than following
    it silently.

    TASK    <the work, or the handoff that carries it>
    STOPS   <the pre-declared stop points, R7>
    HAVE    <what is in the pack; "this file only" if that is all>
    REQUEST <documents that may be needed and are NOT packed. Ask for
             one by name under R11 rather than working around it>
    OUT     <what is out of scope>

  The binding sentence and the stamp request are not optional. They
  exist because a design thread once received a whole archive, never
  opened the render, and followed the project's competing style
  document instead -- and most of its style checks still passed, so
  the pass rate concealed a render with zero influence. Placement is
  not salience.

  A PROJECT WITH NO RENDER cannot satisfy those two lines. It says so
  under R11, in the kickoff, and names what binds instead and in what
  order. It does not invent a substitute render, which would be a
  document with the authority of a render and none of the
  composition.


HANDOFF
  Written at close, looking forward. What the next thread inherits;
  the verified ground truth it starts from (exact signatures and
  facts copied from the code, labelled verify-first, never from
  memory); what is settled and must not be reopened; and the open
  questions with the sender's lean labelled as a lean.


CLOSE
  Written at close, looking back. Terminal state (R9); what landed,
  as artifacts a reader can go and look at; the discrepancies and how
  each was resolved, including the thread's own mistakes and what
  they cost; what was deferred and what was rejected, kept distinct;
  and the handoffs produced, by full path.

  The discrepancies section is the one that does not survive in the
  diff and cannot be reconstructed later. It is the reason this
  document exists.
