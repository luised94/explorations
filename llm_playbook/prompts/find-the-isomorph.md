PROMPT: FIND THE ISOMORPH
=========================
date: 2026-07
type: prompt
scope: abstracting a problem to its structure and matching that
  structure against other fields, to surface what is already known
  about its shape. A THINKING tool and a response anchor. It may lead
  to retrieval (survey-the-space.md) and often does not need to.

BINDS HERE: R4 decision-framed docs, R11 declare absence. A prompt is
a method; these rules are the authority.


USE THIS WHEN
  You can state what you want but not what CLASS of thing it is. The
  obvious design has no obvious failure mode. You are reaching for an
  analogy and cannot name what it is an analogy TO. Or you want the
  model's latent knowledge surfaced against a shape rather than
  against a keyword, which is what this prompt is mostly for: a
  keyword retrieves the domain you are already stuck in, a structure
  retrieves every domain that shares it.

  Do NOT use it on a problem whose shape you already know. That is
  design, and this phase will produce elegant irrelevance.


PART ONE -- NORMALIZE

  Strip the domain vocabulary and describe what is actually there.
  Answer all five; a skipped one is where the wrong analogy gets in.

  1. ENTITIES. What are the things? Not what they are called -- what
     they are. Documents, agents, claims, obligations, tokens, slots.

  2. OPERATIONS. What can be done to them, and by whom. Which are
     cheap, which are expensive, which are irreversible.

  3. STRUCTURE. How are they related? Set, sequence, tree, graph,
     lattice, partition, bipartite matching, queue. Name it as a
     structure, not as a picture.

  4. LIFECYCLE. Where do they come from, what states do they pass
     through, what ends them. Which transitions are one-way. What
     accumulates and what is bounded.

  5. INVARIANTS AND PRESSURES. What must stay true. What force acts
     on the system continuously, in one direction, whether or not
     anyone is watching. This is usually the real problem and usually
     not the one you were asked about.

  Write the result as one paragraph containing NO word from the
  original domain. If you cannot, you have not abstracted yet.


PART TWO -- MATCH

  Ask which other fields have this same normalized structure. Reach
  deliberately across distance: the useful match is rarely the
  adjacent field, because the adjacent field shares your blind spot.

  Sweep at least these, and say which you rejected and why:
    physical and safety-critical  aviation, medicine, nuclear, rail
    institutional                 law, regulation, standards bodies,
                                  accounting, bureaucracy
    biological                    ecology, immunology, evolution,
                                  metabolism
    formal                        type systems, databases, control
                                  theory, information theory,
                                  compilers, distributed systems
    social and economic           markets, commons, urban planning,
                                  organizational behaviour
    craft and archival            editing, cartography, libraries,
                                  museums, translation

  For each candidate, state the mapping ELEMENT BY ELEMENT against
  part one. A match that cannot be written as a mapping is a metaphor
  and does not survive.

  Say explicitly where the mapping BREAKS. The break is the most
  informative thing this prompt produces: it is where the other
  field's solution will not transfer, and it is usually the thing
  that makes your problem yours.


OUTPUT
  The normalized paragraph. Then the candidate fields, ranked, with
  the element-by-element mapping and the break for each, and one
  recommendation for which to pursue (R4). Then, explicitly: the
  fields swept and rejected, so the next thread does not sweep them
  again.

  Anything asserted about another field from memory is marked
  UNVERIFIED (R11). That mark is what decides whether this hands off
  to survey-the-space.md or stops here. An unverified analogy stated
  confidently is worse than no analogy, because nothing in the next
  turn can falsify it.


WORKED EXAMPLE, ABBREVIATED
  Problem as posed: "our workflow documents keep growing and start
  contradicting each other."
  Normalized: a corpus of binding rules, append-mostly, edited by the
  same party that consumes it, under continuous one-directional
  growth pressure, with no external party whose failure signals which
  rules are load-bearing.
  Matched: aviation checklists, clinical guidelines, regulatory
  one-in-one-out, Lehman's laws of software evolution, Zettelkasten.
  Mapping breaks: aviation has an external regulator and a crash;
  this corpus has neither, so nothing prunes it from outside. That
  break is why a warning threshold was never going to work here.
  Rejected: immunology (no self/non-self distinction in the corpus),
  markets (no competing agents).
