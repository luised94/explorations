# Consolidated Prompts

## Prompt 1: Discovery and Experimentation (Pre-Design)

```
I'm about to design a system that [brief description]. 
Before I commit to an approach, I need to surface what I 
don't know.

Part 1 - Unknown unknowns: What am I not considering? 
What fields, systems, or research have solved structurally 
similar problems under different names? What assumptions 
am I making that might be wrong? What would make this 
approach completely wrong? Generate search queries I 
should run for recent work I wouldn't know to look for.

Part 2 - Experiments: Based on the unknowns surfaced 
above, propose experiments to resolve the critical ones 
before I commit to a design. For each experiment:
  - Question it answers
  - Smallest thing to build/run to get the answer
  - Success/failure criterion
  - Consequence for design if it fails
  - Consequence for design if it succeeds
Order by: which unknowns, if answered wrong, would 
invalidate the most downstream decisions.

Part 3 - Terminology expansion: What are all the names 
for the core concepts in this system across computer 
science, cognitive science, library science, systems 
engineering, and any other relevant field? Give me 
vocabulary I'm missing.
```

## Prompt 2: Research, Model, and Narrate (Investigation of Existing Systems)

```
Research [system/concept names] thoroughly.

Phase 1 - Structural model: Model each system as a 
data-oriented engineering artifact. Define core data 
structures (what is stored, what shape, what references 
what), algorithms and transformations (what operations 
mutate or query the data, inputs/outputs, triggers), 
and interfaces/boundaries (where human input enters, 
where output is consumed, external state). Use: type 
definitions first, then operations on those types, then 
data flow in arrow notation (input  transform  output). 
No prose in this phase.

Phase 2 - Mentor narrative: Rewrite the structural model 
as a readable walkthrough. For each major component: the 
problem it solves, how the data design addresses it, 
failure modes when the design is violated, and then 
surface implicit knowledge - assumptions about cognition, 
prerequisites never stated, presuppositions about usage 
patterns, expectations only visible through long-term use 
or failure. Write as someone advising a practitioner who 
is data-oriented, builds minimal personal tools, avoids 
premature abstraction, and will implement this as a 
procedural pipeline.

Phase 3 - What I'm missing: Given the systems you just 
modeled, what related work, alternative approaches, or 
critical discoveries am I likely unaware of? What 
terminology would unlock further research? What would 
a veteran practitioner of these systems tell me that 
isn't in any tutorial?

End each component section with "what nobody tells you" - 
the latent knowledge that surfaces only through experience 
or failure.
```

---

## How These Two Prompts Relate

**Prompt 1** is for *your own system* - when you're about to build something and need to de-risk before designing.

**Prompt 2** is for *studying existing systems* - when you want to deeply understand something external before deciding what to adopt, adapt, or reject.

They share the same DNA: structural understanding first, then narrative deepening, then surfacing what's hidden. But Prompt 1 is oriented toward action (experiments, decisions), while Prompt 2 is oriented toward comprehension (modeling, learning, discovering adjacent knowledge).

Both deploy the unknown-unknowns strategies: counterfactual probing ("what would make this wrong"), domain bridging ("what fields solved this differently"), terminology expansion ("what vocabulary am I missing"), and frame-breaking ("what would a veteran say that isn't in any tutorial").
