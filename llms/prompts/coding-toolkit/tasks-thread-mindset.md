อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: thread_mindset_tsk.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
Thread Mindset: tsk Design
VERSION: 1
UPDATED: 2026-05-27
Accumulated domain knowledge, strategies, heuristics, and
decision patterns from the tsk design thread. Project-specific.
Paste into tsk implementation and refinement threads to preserve
contextual judgment.

Domain model understanding
This system manages personal commitments across four entity types
- tasks, goals, habits, and events - unified by a common data
format but distinguished by lifecycle. The key insight that
shaped the design: tasks die (created  done), goals persist
and need periodic review, habits never complete (they track
consistency), and events pass with time. These lifecycle
differences drive every structural decision.
The system lives in a personal tool ecosystem where modules
(kbd, lw, tasks, friction) are siblings connected by convention
- shared tag vocabularies, cross-references by ID, consistent
file formats - not by code imports or shared libraries. This
loose coupling is deliberate and should be maintained.
Decision heuristics that emerged
"Would a veteran track this?" Applied when evaluating whether
a field, feature, or metric should exist. If the answer is "yes,
but only after they've been burned by not having it," include
the field in the data model now even if the processing logic is
deferred. Capture data early, analyze later.
"Does the data carry the routing?" Preferred over command
hierarchy nesting. Instead of tsk habit done, use tsk done H001
and let the H prefix determine behavior. Data-driven dispatch
over structural dispatch.
"Two-speed, not one-speed." Any input pathway should have a
fast mode (CLI flags, minimal friction) and a thorough mode
(editor, full template). Forcing everything through one speed
punishes the other use case.
"Same file, different type field." When entity types share 80%+
of their fields and the same parser can handle them, they belong
in the same file distinguished by a type field. Separate files
only when entities have fundamentally different write patterns,
query patterns, or volume characteristics (e.g., habit_log.txt
is separated because it's high-volume append-only).
"Sections only if they have content." Display commands hide
empty sections. The user should never see a header with nothing
under it.
Architecture patterns locked in

Field-agnostic parser. The CCL-style parser reads any
key=value pairs. It doesn't know what entities are. Validation
is a separate pass in command logic. New fields never require
parser changes. This was a deliberate choice to allow data
model evolution without code changes to the foundation.
Round-trip fidelity. Parse a file, write it back, get
identical output. Records that aren't modified preserve their
original text. This matters for git diffs and for not surprising
the user.
Dispatch table at module level. Dictionary of command names
to handler functions. No main(). No class hierarchy. Adding a
command is one function definition plus one dictionary entry.
Usage logging as first-class infrastructure. Every command
invocation is logged with timestamp, command, primary argument,
and duration. This is not debug logging - it's empirical data
for measuring how the tool is actually used. Collected from day
one, analyzed later.

Coding choices and their reasons

Single file (tasks.py): all logic in one file until it
exceeds ~2000 lines. Keeps the project greppable, foldable
in nvim, and eliminates import/packaging overhead.
No argparse at top level: dispatch is a dict lookup on
sys.argv[1]. Individual handlers parse their own args. This
keeps each handler self-contained and avoids argparse's
subparser complexity.
Separate read/transform/write phases: every mutation command
follows read file  parse  modify data  write file. These
phases should be visually distinct in the code (separate
function calls or inline markers), never interleaved.
Confirmation output to stdout, errors to stderr: the user
always sees what happened. Silent success is forbidden.

Risks and failure modes identified

Stale task graveyard: the most common failure mode for
personal task systems. Mitigated by: stale task detection
(deferred command), goal review cadence reminders, and
usage metrics that track completion rates.
Scope creep during implementation: the spec is already
ambitious for a personal tool. Phase boundaries are strict.
Finish phase 0, live with it two weeks, then decide what's
next based on real usage data.
Journal format contamination: any tooling that reads kbd
journal should adapt to the journal's existing format, not
require the journal to change. The journal input format is
sacred.
Over-coupling between modules: if tasks needs to import
from kbd or vice versa, the architecture has failed. Connection
is through data conventions only.

Strategies that worked in this thread

"Feedback first, then questions" as an opening pattern
gave the LLM freedom to react before interrogating. Produced
better initial feedback than pure Q&A.
Isolating topics ("let's focus on tasks only") prevented
scope bleed between config language, tasks, and workflow
discussions.
Asking for naive-then-veteran consistently produced deeper
analysis than asking for recommendations directly. The act of
articulating and discarding naive approaches forced the LLM
to go beyond surface-level suggestions.
Requesting latent knowledge explicitly surfaced prep vs
notes field separation, habit completion logging design, and
round-trip fidelity - none of which were in the original
problem statement.
