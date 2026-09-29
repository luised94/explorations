# Understanding grug

This is the explanation page: why grug is shaped the way it is. For the
steps of using it, see how-to-use-cycle.md.

## Two things under one name

grug is a method and a harness. The method is text: core.md, the domain
files and the return contract. It is the thing being tested, an attempt to
replace the llm_playbook and the long Preferences text with something
short. The harness is grug.py, which assembles the text into packets and
records what comes back.

The harness exists so the method can be judged by what happens when it is
used, not by how complete it looks. If the method fails, the harness has
done its job by showing that. If the harness itself grows past what it
earns, the method's own first rule applies to it. At 635 lines it is
already past the 100 to 200 its origin thread suggested, and that is an
open finding, not a settled design.

## The grug stance

Complexity is the demon: easy to let in, hard to see until a change in one
place breaks another. The response is not "simple at any cost". It is to
make every layer name the problem it solves now, and to wait for a second
real use before building for one. Rigor is spent where a wrong belief is
costly. A method that needs forty ceremonies has let the demon back in
wearing a grug costume, and core.md says so in its second line.

## The distinctions the harness enforces

A handful of distinctions from the origin thread do the real work. The
harness makes each one hard to blur by accident.

- **Method and task.** The method is constant across tasks; the task is
  what to do now. They are separate files and separate packet sections, so
  one can change while the other is held fixed.
- **Instruction and reference.** Method, domain, task and contract are
  instructions. Evidence, memory and repair summaries are data. Data sits
  inside a Markdown fence longer than any run of backticks it contains, so
  no file can close its own fence and pose as a new section. An earlier
  design refused files containing section markers; it was dropped because
  it would have refused grug.py itself, and working on the harness is the
  first use case.
- **Memory and authority.** A memory note is a lead to check, never a rule.
  Notes enter only by deliberate promotion of a lesson a run proposed, stay
  drafts until you fill in where they hold and when to revisit, and are
  flagged when nobody has checked them for 90 days.
- **Claim and check.** The model's `status` in its return block is a
  self-report. Your verdict is a separate event. The report counts where
  they disagree, because a model that says "done" on failing work is a
  finding about the method.
- **Ambient and packet.** The Preferences field holds only a loader
  (ambient.md) that says the method arrives with each thread. Chat memory
  and past-chat search stay off. Whatever reaches a thread is then either
  in the packet or in the loader, and the loader is identical in every arm,
  so it cancels in comparisons.

## Files are the record; the script is a view

Everything that matters is a plain file readable in any editor: the method,
tasks, notes, packets, replies. The run log is JSON Lines, one event per
line, append-only. A correction is a new event, never an edit, so the log
can be trusted as evidence. Listings such as `notes` are derived from the
files each time rather than kept as a second record that could drift.

If grug.py disappeared tomorrow, the files would still say what was tried,
with what inputs, and what came of it.

## One packet, several transports

The API, a browser with a sandbox, and plain browser chat differ in who
moves the bytes, not in what the bytes are. So there is one packet format.
The interface is recorded as data rather than changing the assembly. On the
API, the whole packet goes as one user message, the same bytes a paste
gives. Sending the method as a system prompt might be followed more
closely, but it would make an API run incomparable with a browser run.

Browser threads are multi-turn, and the chat keeps its own history, so a
follow-up turn made with `pack --after` does not resend the method. Whether
the method survives the thread is then something the data shows. The API
has no history of its own; rebuilding it is the plumbing left for later, so
`call` refuses follow-up turns rather than send them without context.

## The data model

### What is stored

Each packet is a node. A node records the exact version (sha256) of every
file that went into it, the packet, the reply, the parsed return block and
your verdict. A node may point to a parent in one of two ways:

- `after`: the next turn in the same thread, sharing its context.
- `repair`: a fresh thread that starts from a summary of a failed one.

A thread is a path of `after` links. A task is a chain of threads joined by
`repair` links. A plain series of turns is the case where every node has
one child, so storing a series today costs nothing if branching (an edited
message, a regenerated reply) shows up tomorrow. This is the same shape git
uses: commits with parent pointers, where a branch is a path.

### What it is an instance of

The tree is one view. The fuller object is a provenance graph, the shape
formalized in W3C PROV: entities (file versions, packets, replies) that
activities (pack, a model call, your review) use and generate. Each pack
event is a hyperedge that joins many typed inputs, the method, domain,
memory, evidence and task versions, into one packet. Each reply joins a
packet and a model into a response. The views the report prints are
projections of that graph:

- the tree: parent edges only
- an arm: nodes grouped by method, interface, model, ambient and mode
- decay: position along a thread against whether the return block survived

### What is being sampled

A model does not map a packet to a reply. It maps a packet to a
distribution over replies, and every run is one sample from it. You never
see the distribution, only samples and your measurements of them. Two
consequences follow:

- One run proves little. Differences between arms mean something only
  across many tasks, and a single reply's success or failure is weak
  evidence either way.
- Estimating spread needs repeated samples of the same inputs. The section
  hashes in each pack event identify identical inputs; the packet hash
  cannot, because the packet carries its run id. The report does not yet
  group repeat samples; the log already holds what it would need.

## The experiment

Three arms share everything except the method: `core` (grug),
`baseline/preferences.md` (the old Preferences), and `none` (task, evidence
and contract only). The report groups runs by what an experiment varies and
prints, for each group:

- **First try passed**: verdicts on a task's opening packet. The purest
  measure of the method, and the noisiest.
- **Tasks solved and mean attempts to pass**: whether a task got done in
  the end, and how many threads it took. This is where a method that is
  worse at first but better at repair would show.
- **Said done but not passed**: the self-grading gap.
- **Lost the return block, first at turn N**: how long the method's
  instructions survive in a thread.
- **Mean packet tokens**: what the method costs to send.

Known confounds, each the same in every arm: the contract's `verified:`
field nudges every arm toward verification, and the packet header tells
every arm that fenced text is data. Browser runs also carry claude.ai's own
system prompt, which no arm controls and API runs lack, so compare arms
within one interface, not across interfaces.

What the data cannot tell you: anything from a handful of runs; anything
about tasks unlike the ones you chose; anything your verdicts get wrong.
Fixing the sample size and the archive rule before a batch is what keeps
the data from confirming whatever you already believed.

## Absent on purpose

There are no automatic retries or repair loops, no tool use, no test
execution, no repository indexing, relevance ranking or embeddings, no
prompt caching and no streaming. Each would add failure modes before any
run showed it was needed. The rule for adding one is the method's own: a
recorded run where the simple packet failed for lack of it.

## Provenance

grug.py was written in a session still governed by the old Preferences, so
its code style (flat procedural, full names, no single-call helpers)
comes from them. memory/2026-09-28-harness-style-from-preferences.md
records this. domains/code.md carries the same rules in grug form, so the
style is part of what the experiment tests rather than a hidden influence.
