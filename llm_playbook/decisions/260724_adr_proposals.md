ADR PROPOSALS FOR PLAYBOOK-DESIGN-004
=====================================
Drafted by PLAYBOOK-IMPL-003, NOT decided. An implementation thread
cannot adopt an ADR; these are the two decisions the G-1b failure
forces, written up so DESIGN-004 can accept, reject, or reshape them.
Append to decisions/era-2026-q3.md (index line plus prose) only after
that thread decides. Numbers are provisional -- take the next free ids.

--- INDEX LINES (if adopted) ---
  ADR-030 a kickoff names the render and states that it binds
  ADR-031 render ceiling is tier-dependent, not absolute
  ADR-032 pack is primary for reading; a checkout remains correct
          for executing (clarifies ADR-021)

--- ADR-030 (proposed) ---
ADR-030 a kickoff names the render and states that it binds
Context: ADR-020 placed the render at <project>/llm/CONTEXT.md and
stopped there. G-1b showed placement is not enough. A design thread
was given the whole drill archive -- 115 files, 1.7 MB, on the order
of 400k tokens -- and never opened the render. It found and followed
drill's own CODING_CONVENTIONS.md instead, by its own initiative. Six
of seven style checks still passed, sourced from that competing
document and from the surrounding code, so the pass rate concealed a
render with zero influence. An archive delivers everything and
signals nothing; a paste block buries the render mid-stream. The
defect is not transport, which worked correctly throughout, and not
render content, which was well-formed and within budget. Nothing told
the thread it was BOUND by anything.
Decision (proposed): every kickoff NAMES the render and states that it
binds the thread. One sentence, both delivery modes -- in paste mode
the render is in the block, in archive mode the kickoff says to unpack
and read it first. The recurring text becomes a playbook artifact
(protocol/kickoff.md) holding a KICKOFF template and a HANDOFF
template, rather than prose retyped per thread; handoff filenames
follow naming.md's handoff-<FROM>-to-<TO>.md.
Alternatives: a discoverability flag on pack-repo.sh (rejected: it
couples transport to protocol, so every later protocol change would
require a packer change, and it adds per-invocation configuration
that can be set wrongly or forgotten -- the packer moves bytes);
having the packer emit a prompt file (rejected for the same coupling);
relying on placement alone (rejected: this is what failed).
Consequence: threads must not be told they are being evaluated when
this is tested, and the diagnostic question ("what in your context
told you this -- quote it") replaces the checklist, since a checklist
cannot distinguish a render that landed from priors that happened to
agree.

--- ADR-031 (proposed) ---
ADR-031 render ceiling is tier-dependent, not absolute
Context: the 250-line render ceiling (T-007, enforced by check.sh on
staged CONTEXT.md) exists to bound a PASTED block, where the render
competes for a single context window. Archive delivery changes the
economics. The evaluating thread needed four separate regions of a
2431-line module and retrieved each in one targeted call; a 250-line
window would have forced repeated reconstruction or a lossy summary.
Authoring drill's render under the ceiling already meant compressing
288 lines of source into 198.
Decision (proposed): the ceiling becomes TIER-DEPENDENT -- binding for
paste delivery, advisory for archive delivery -- rather than absolute.
check.sh keeps enforcing it where it binds.
Alternatives: drop the ceiling entirely (rejected: it loses the
constraint exactly where it still bites, since paste mode cannot
exceed a context window); keep it absolute (rejected: it optimizes for
a delivery mode the sandbox makes unnecessary, at a real cost in
fidelity).
Open: this interacts with the unresolved question of whether the
render should be smaller and denser, or larger and complete. Decide
that first; the ceiling follows from it.

--- ADR-032 (proposed) ---
ADR-032 pack is primary for reading; a checkout remains correct for
executing (clarifies ADR-021)
Context: ADR-021 retired the sparse-checkout bootstrap in favour of
archive-or-paste. Its index line reads "transport is archive-or-paste,
scratch-only, committed-read", which is broader than the decision was:
the argument was that copying a tree merely to READ it is waste when
one thread runs at a time. IMPL-003 misread its own decision in a
first-draft handoff and called drill's clone-and-verify prompt
obsolete because it sparse-clones. That was wrong. Five of that
prompt's six steps are verification, not transport: pin an exact
40-char SHA, confirm branch decoration, establish a green test
baseline before any change with a hard stop on mismatch, separate
collection and import errors from failures, and declare an explicit
file scope. A thread that must RUN a suite needs a working tree, and
pack-repo.sh cannot supply one -- being scratch-only and
committed-read, it produces no tree by design. If the author of the
decision misread it within one thread, the wording invites the error.
Decision (proposed): record the division explicitly. THE PACKER IS
PRIMARY, since most work is read-and-reason and that is the common
case. A CHECKOUT IS CORRECT AND NOT DEPRECATED when a thread must
execute against a live tree. Neither supersedes the other. Rule of
thumb: reading is a pack, executing is a checkout. ADR-021's scope is
narrowed in wording, not in substance -- the sparse-checkout BOOTSTRAP
stays retired.
Alternatives: leave ADR-021 as written (rejected: it produced a real
misreading by the thread that implemented it, and would mislead a
reader promoting drill's prompts into the playbook); retire
clone-and-verify (rejected: it does a job nothing else does, and the
verification discipline it encodes is worth generalizing).
