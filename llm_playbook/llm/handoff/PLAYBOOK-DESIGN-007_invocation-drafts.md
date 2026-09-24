INVOCATION DRAFTS PLAYBOOK-DESIGN-007_invocation-drafts
=======================================================
date:  2026-09
type:  design
scope: four method prompts drafted in PLAYBOOK-DESIGN-007 and NOT
       promoted into prompts/. Held here so they live in the repository
       rather than only in a chat, which is how this thread's files were
       nearly lost (refinements.md RF-PLAYBOOK-015).

  WHY THESE ARE NOT IN prompts/
    None has been used on a real project. README accretion rule ONE
    lets the tree take a method when it is IN USE (find-the-isomorph
    was captured that way); these were designed by deliberation, in a
    thread that did not have this repository attached
    (RF-PLAYBOOK-014). Much of their ground is already covered:
      boundary-discipline   style-contract S12, S13, S28, S29, and the
                            COMPLECTION heuristic in adversarial-review
                            (its test is word for word the same one)
      representation-fit    find-the-isomorph PART ONE items 1-3, and
                            CRITERIA-005 and -006. Its one new step --
                            map the ideal structure onto the target
                            language's available constructs and state
                            the cost of the gap -- is the candidate
                            addition, if any of this is promoted.
      data-lifecycle        find-the-isomorph PART ONE item 4
      verbalized-sampling   nothing in the tree. It WAS in use before
                            this thread, as a menu entry in the pasted
                            working defaults; no original body has been
                            found (close artifact, discrepancy 3).

  PROMOTE ONE BY REWRITING IT INTO prompts/ FORM when a real project
  uses it: type: prompt, a BINDS HERE line, USE THIS WHEN, and its
  origin incident. The drafts follow this thread's decision [8] --
  bodies carry no rationale -- which contradicts the tree's prompt form
  and was NOT adopted (settled.md). Promotion drops [8].

  Each draft below is byte-identical to the file delivered in the
  thread, between its BEGIN and END markers, so it can still be pasted
  alone.


%%%%% BEGIN verbalized-sampling.md  sha256 b386fb2e81c6dd3f007b00747a04fcb2a609eec3baf666d9d100eb816ffde290
# verbalized-sampling

Paste when the modal first answer is a risk and the spread of genuinely distinct
good answers is what you want to choose from.

## Steps

1. Before generating anything, state how many genuinely distinct good answers
   the problem admits, and why. This cardinality justification must come first.
   A number stated after generating is the magic-number failure in disguise --
   it rationalizes whatever count fell out rather than deriving the count from
   the problem.

2. Generate that many candidates, each genuinely distinct -- different in
   approach or structure, not the same answer reworded.

3. Stop at that number. If pushed past it, generate more but mark the exact
   point where genuine distinctness ends and padding begins.

4. Choose from the spread.

No fixed candidate count appears anywhere in this invocation. The count is
derived per problem in step 1.

## Composition with the standing options rule

The standing block requires ranking alternatives, scoring, one-line rationales,
one recommendation. This invocation sets the candidate population; the standing
rule orders that population. Padding generated past the distinctness cutoff (step
3) is excluded from the recommendation set -- it may be listed and marked, but it
does not compete for the recommendation.
%%%%% END verbalized-sampling.md

%%%%% BEGIN boundary-discipline.md  sha256 9c5e654636c5e637ca6cd33dd2f95d7246ac410c3c68f6ccd949a332292d9897
# boundary-discipline

Paste at implement or specification, when placing seams in code for real. The
standing block carries the one-question test; this carries the rest. Trimmed to
the rule plus the rationale needed to apply it -- worked justification and
rejected alternatives stay in chat, not here.

## The unit and its boundary

A unit is a data representation plus all the operations that know its internals.
This is data-oriented: the representation is the design, and boundaries are
drawn around data, not around conceptual actors or responsibilities. (Memory
layout and access patterns are a separate concern, out of scope here; this
governs where boundaries go, not how data is laid out behind them.)

A boundary exists where the representation goes opaque and only a
representation-independent contract crosses it. The same test applies at every
scale -- function, module, subsystem: split where one unit stops knowing
another's internals. Resolve ambiguity about where a boundary falls with one
question: does one change force both sides to change? If yes, they are one unit;
if no, the boundary is real.

## Which test to apply: representation vs responsibility

The primary partition test is the data representation, because the work is
data-oriented. But when a piece of work is shaped by a responsibility spanning
several small representations, and the representation test would scatter it,
name that and flip to a responsibility boundary for that piece. Do not silently
apply the wrong test. The flip is the exception; the representation test is the
default, and every use of the flip is stated as such.

## Procedural residue

Code belonging to no unit -- procedural residue with no representation of its
own -- binds on the call graph instead: keep it flat and inline until a second
real call site exists, then lift it.

## Fitted structure is not premature abstraction

Two things get confused; separated, the rules pull apart cleanly. Choosing the
representation that fits the problem's shape now is recognizing the shape, and
it is required: pure computation is a function, accumulation by key is a dict or
counter, parsing is a tree or state machine, a hot inner loop may want
struct-of-arrays. Adding indirection for a caller that does not yet exist is
premature abstraction and is forbidden. The test: justified by what is here now,
or only by what might arrive later. The second-call-site rule governs the second
case only; it never blocks reaching for the structure the present problem
already has.

## Hot-path cross-boundary reaches

A hot-path reach across a boundary into another representation's internals is
permitted as an annotated exception: the boundary still stands, and the reach is
marked with its constraint, its reason, and the coupling it creates, so it warns
rather than hides. An unmarked cross-representation reach is a defect; a marked
one is a stated trade-off.
%%%%% END boundary-discipline.md

%%%%% BEGIN representation-fit.md  sha256 3e45a4d6f6df815d7d62d34552bde48925e3d41099db39b3ce15337f4b9cefb8
# representation-fit

Paste on data work where a structure is being chosen. Operational: run the steps,
emit the one output structure below. The reasoning about why constrained-language
representation matters stays in chat, not here.

## Steps

1. Name the data's shape from its operations: what is looked up, accumulated,
   iterated, joined, mutated. The shape is dictated by what the code does to the
   data, not by what the data is called.

2. State the naive reach -- the list, string, dict, or table grabbed without
   thinking.

3. State the ideal structure for this shape, language aside -- the structure a
   veteran reaches for given these operations (record, keyed accumulator, tree,
   state machine, struct-of-arrays, and so on).

4. Name the target language's available construct set. Do not assume a fixed
   language. Read which language is in play from the code or the request, then
   list the constructs that language actually provides for this shape.

5. Map the ideal structure to the closest available construct in that language.

6. State the cost of the gap: what the ideal has that the available construct
   lacks, what must be hand-rolled, what invariant is now unenforced, what the
   language forces you to give up. If the gap is zero, say so.

7. Normalization check, in-memory scope only: is anything stored that is
   derivable, is one fact represented in two places that can disagree. Fix or
   flag. This step covers in-memory redundancy only; persistent-schema or
   serialized-format normalization is out of scope for this invocation -- when
   the data crosses into storage or wire format, announce the gap and invoke a
   dedicated normalization pass separately rather than half-covering it here.

## Output structure (fixed)

One block per data structure under consideration, each block:

    shape:            <operations that define it>
    naive reach:      <the lazy grab>
    ideal structure:  <language-aside veteran reach>
    target language:  <read from context>
    mapped construct: <closest available>
    cost of gap:      <what is lost or hand-rolled; "none" if zero>
    normalization:    <in-memory redundancy found and resolved, or "clean";
                       plus any out-of-scope persistent-schema gap announced>

No per-call structure argument: this invocation always emits the block above,
never a caller-specified format.
%%%%% END representation-fit.md

%%%%% BEGIN data-lifecycle.md  sha256 3ceac040785109bd5af7f14dda22e0a178d54677cbffd62a98a831f52bf71dc7
# data-lifecycle

Paste on data work where a datum moves, is copied, or is shared. Operational:
run the trace, emit the one output structure below. Reasoning about why
copy/reference semantics differ across languages stays in chat, not here.

## Steps

1. Pick the datum to trace. One datum (or one closely bound cluster) per trace,
   not the whole program state at once.

2. Find its origin: where it enters -- literal, input, read, computed.

3. Walk it forward stage by stage to disposal. At each stage record: the
   representation it is in now, the operation applied, and whether that
   operation copies, mutates in place, or takes a new reference to the same
   underlying object.

4. For copy-vs-reference, name the target language's semantics rather than
   assuming. Read which language is in play, then state what the operation does
   in that language -- some languages copy values on assignment, some share
   references, some copy on modify, some have no reference concept at all. The
   answer is a property of the language and the operation together.

5. Absorb the ownership/aliasing question into the same walk, as annotation, not
   a separate graph. At each stage flag: is this datum now shared (more than one
   name reaches it), aliased (a mutation here is visible elsewhere), and who owns
   its lifetime (who is responsible for it ending). These are columns on the
   trace, not a second output.

6. Find disposal: where it dies -- goes out of scope, is freed, is overwritten,
   is persisted and abandoned. A datum with no disposal stage is a leak or an
   unbounded lifetime; flag it.

## Output structure (fixed)

One trace, one row per stage, origin at top, disposal at bottom:

    stage | representation | operation | copy/ref/mutate | shared? | aliased? | lifetime owner

Followed by one line naming any leak, unbounded lifetime, or surprising alias
the trace exposed, or "clean" if none.

A linear trace is the single output structure. The shared/aliased/owner flags
ride as columns on that trace; this invocation never emits a separate ownership
graph. No per-call structure argument.
%%%%% END data-lifecycle.md
