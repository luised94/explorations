PRECEDENCE
==========
date: 2026-07
scope: who wins when rules conflict. There are TWO separate chains;
confusing them was the original defect this document repairs. A
stateless model cannot arbitrate a chain whose lower links it never
sees, so the long chain is resolved by the human BEFORE the model is
involved, and the model is left a chain of exactly two links.

CHAIN 1: RENDER-TIME AND AUTHORING-TIME (resolved by the HUMAN)
  live human > project instance > playbook > model defaults
  Applied whenever a render is built or a document is written: the
  human composing CONTEXT.md resolves every conflict between a
  project instance rule and a playbook rule in the instance's
  favor, and the render emits ONLY the winner. The losing rule
  never reaches the model. Model defaults sit at the bottom: a
  render or document may explicitly override a model's habitual
  behavior, and silence means the default stands.

CHAIN 2: RUNTIME (the only chain a model arbitrates)
  live human message > whatever was rendered. Full stop.
  The model never re-resolves chain 1, because the render already
  collapsed it: from inside a thread, the render is a single
  consistent authority, and the only thing that outranks it is the
  human speaking now. A model that starts weighing "playbook vs
  instance" mid-thread is answering a question that was closed
  before kickoff.

WORKED EXAMPLE (walks both chains)
  A project instance rule says "commit messages carry no plan ids"
  while the playbook commit-prefix rule (naming.md) expects them.
  Chain 1: the human building that project's CONTEXT.md resolves
  instance-over-playbook; the render states the no-plan-id rule
  and omits the playbook form entirely. Chain 2: mid-thread, the
  human writes "actually, include plan ids from now on." The live
  message wins over the render immediately; the model complies for
  the rest of the thread, and the change is filed as a refinement
  entry (RF-PROJ-NNN, naming.md) in the project's refinements
  file. The regenerated render serves the NEXT thread; this one
  runs to completion on the live correction alone.

FLAG, DO NOT FOLLOW
  When a rendered or written rule conflicts with observed reality,
  the model flags the conflict and follows reality; it neither
  silently complies with the wrong document nor silently ignores
  it. Origin incident: a handoff instructed use of a command-line
  flag that did not exist in the code; the correct move is to say
  so and proceed against the real interface, recording the
  correction as a finding. Documents are leads; the repository is
  ground truth.

READ-ONLY CHECKOUT
  The playbook checkout a thread runs against is read-only from
  that thread's point of view (ADR-004). A precedence loss is
  never repaired by editing the playbook mid-thread: fixes travel
  as live human messages now and refinement entries for later, and
  reach the playbook only through a human editorial pass.
