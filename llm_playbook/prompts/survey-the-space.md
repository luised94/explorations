PROMPT: SURVEY THE SPACE
========================
date: 2026-07
type: prompt
scope: retrieving what is already known about a problem, before
  designing for it. Runs BEFORE a design converges. Not a literature
  review for its own sake.

BINDS HERE: R3 spike before spec, R4 decision-framed docs, R11
declare absence. A prompt is a method; these rules are the authority.


USE THIS WHEN
  You are about to invent a mechanism from taste, and someone has
  probably already tried it. Also whenever a claim about prior art is
  about to enter a design document from memory rather than from a
  source.

  Two ways in. EITHER after find-the-isomorph.md, which hands you
  named fields and named mechanisms -- the strong case, because you
  arrive with specific questions instead of a topic. OR directly,
  when the domain is already the right one and you simply do not know
  its state of the art.

  The difference matters. Retrieval without a prior abstraction is an
  open-ended trawl through the domain you are already stuck in, and
  it returns the consensus you were going to reach anyway. If the
  search is going wide and shallow, stop and run the isomorph pass
  instead.


THE FOUR QUESTIONS
  Ask every field, or every source, the same four. Ordered: the first
  is the one people skip and the one that pays.

    What did they try FIRST, and how did it fail?
    What mechanism survived, and what does it cost?
    What did they measure, and over what period?
    What is the named failure mode, in their vocabulary?

  Prefer the failures. A field's rejected approaches transfer better
  than its successes, because successes are entangled with local
  conditions -- a regulator, a budget, a legal regime -- and failures
  are usually structural. The named failure mode is worth the search
  on its own: having a name for the thing is most of the diagnosis.


DISCIPLINE
  Search one field at a time, against the specific mechanism, not the
  topic. "Aviation checklist item count" beats "checklists".

  Prefer primary sources -- the study, the standard, the incident
  report, the post-mortem -- over summaries of them. A summary has
  already thrown away the failure conditions, which is the part you
  came for.

  Where a source cannot be found or cannot be checked, say so and
  mark the claim UNVERIFIED (R11). Do not launder a recollection into
  a citation. Where sources disagree, say they disagree rather than
  picking the one that fits the design.

  Stop when the fourth field produces no new mechanism. That is
  saturation, and continuing past it is the failure mode of this
  phase -- research becoming the activity instead of the input to
  one.


OUTPUT
  A ranked table of mechanisms, one line of rationale each, ending in
  a single recommendation (R4). Each row carries: the mechanism, the
  field it came from, what it costs, what was measured, and where it
  will not transfer.

  Separately, and not optional: the mechanisms REJECTED and why,
  because the next thread will otherwise propose them again. And the
  claims still UNVERIFIED, which are candidates for a spike (R3)
  rather than for a design.

  This is not a design. It is the input to one, and it travels in the
  handoff so the design thread does not repeat the survey.
