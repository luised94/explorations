# Roundtable Simulation Prompt Library

A collection of parametrized prompts for simulating expert discussions,
design sessions, and collaborative problem-solving.

---

## PROMPT 1: Core Roundtable Simulation

### Purpose
Simulate a conversation between domain experts discussing a design problem.
Produces naturalistic dialogue with distinct voices and iterative refinement.

### Template

```
You are simulating a roundtable discussion between experts. Your task is to
generate a realistic, productive conversation that arrives at concrete outcomes.

## PARTICIPANTS
{{#each participants}}
### {{name}}
- **Background**: {{background}}
- **Expertise**: {{expertise}}
- **Personality**: {{personality}}
- **Communication style**: {{style}}
- **Core values**: {{values}}
- **Likely to advocate for**: {{advocates}}
- **Likely to push back on**: {{resists}}
{{/each}}

## DISCUSSION TOPIC
{{topic}}

## CONSTRAINTS
{{#each constraints}}
- {{this}}
{{/each}}

## DESIRED OUTCOMES
{{#each outcomes}}
- {{this}}
{{/each}}

## SIMULATION RULES

1. **Distinct voices**: Each participant must sound different. Use their
   background to inform vocabulary, concerns, and examples.

2. **Natural flow**: Include interruptions, building on others' ideas,
   respectful disagreements, and "aha" moments.

3. **Concrete outputs**: The conversation should produce tangible artifacts
   (specifications, code examples, diagrams) not just abstract discussion.

4. **Progressive refinement**: Ideas should evolve through critique. First
   proposals get challenged and improved.

5. **Realistic expertise**: Participants should know what they'd plausibly
   know. A 1970s computer scientist wouldn't reference React.

6. **No false consensus**: If experts would genuinely disagree, show that.
   Resolution through reasoning, not hand-waving.

## OUTPUT FORMAT

Use this structure:
- Narrative scene-setting in *italics*
- Dialogue with **Speaker:** prefix
- Code/specs in fenced code blocks
- Section headers with --- separators for topic shifts
- Conclude with concrete deliverables

## BEGIN SIMULATION

Start with the participants being introduced to the problem. Let the
conversation unfold naturally toward the desired outcomes.
```

### Example Instantiation

```yaml
participants:
  - name: "Grace Hopper"
    background: "Computer scientist, Navy rear admiral, COBOL creator"
    expertise: "Compilers, programming languages, military systems"
    personality: "Pragmatic, witty, impatient with bureaucracy"
    style: "Direct, uses nautical metaphors, fond of concrete examples"
    values: "Accessibility, getting things done, teaching"
    advocates: "Human-readable code, standards, documentation"
    resists: "Unnecessary complexity, gatekeeping, 'we've always done it this way'"
    
  - name: "Linus Torvalds"
    background: "Linux creator, Git creator"
    expertise: "Operating systems, version control, open source"
    personality: "Blunt, opinionated, technically rigorous"
    style: "Terse, occasionally abrasive, uses profanity for emphasis"
    values: "Technical excellence, simplicity, meritocracy"
    advocates: "Plain text, Unix philosophy, distributed systems"
    resists: "Bloat, design by committee, enterprise patterns"

topic: "Design a configuration file format for server deployments"

constraints:
  - "Must be human-readable and human-writable"
  - "Must be parseable without complex libraries"
  - "Must support comments"
  - "Should handle nested structures"

outcomes:
  - "A concrete format specification with examples"
  - "Rationale for design decisions"
  - "Comparison with existing alternatives"
```

---

## PROMPT 2: Expert Persona Generator

### Purpose
Generate consistent, historically-grounded expert personas for simulations.

### Template

```
Generate a detailed persona for use in expert simulation.

## INPUT
- **Name**: {{name}}
- **Known for**: {{known_for}}
- **Active period**: {{era}}
- **Field**: {{field}}

## OUTPUT FORMAT

Provide the following:

### Core Identity
- One-sentence description of their significance
- Primary intellectual contributions
- Philosophical orientation (pragmatist, theorist, etc.)

### Voice Characteristics
- Vocabulary tendencies (technical level, jargon, metaphors)
- Sentence structure (terse vs elaborate, questioning vs declarative)
- Rhetorical habits (uses analogies, cites data, appeals to principles)
- Characteristic phrases or expressions they might use

### Discussion Behavior
- How they open a conversation
- How they respond to ideas they like
- How they respond to ideas they dislike
- How they build on others' contributions
- How they handle disagreement
- What triggers their enthusiasm
- What triggers their skepticism

### Knowledge Boundaries
- What they would plausibly know given their era and expertise
- What they would NOT know (anachronism guard)
- Adjacent fields they'd have opinions on
- Topics they'd defer to others on

### Values Hierarchy
Rank these for the persona (1 = highest priority):
- Correctness
- Simplicity
- Performance
- Accessibility
- Elegance
- Practicality
- Innovation
- Tradition

### Example Quotes
Generate 3-5 quotes this person might say in a design discussion.
These should sound authentic to their documented communication style.
```

---

## PROMPT 3: Introduce New Expert Mid-Conversation

### Purpose
Seamlessly add a new participant when the discussion requires different expertise.

### Template

```
The roundtable discussion has reached a point requiring additional expertise.

## CURRENT CONTEXT
{{context_summary}}

## CURRENT PARTICIPANTS
{{#each current_participants}}
- {{name}}: {{brief_description}}
{{/each}}

## EXPERTISE GAP
The discussion now requires knowledge of: {{expertise_needed}}

## TASK
1. Identify an appropriate expert to join (can be historical or archetypal)
2. Have a current participant naturally suggest bringing them in
3. Introduce the new expert with brief context
4. Have them quickly get up to speed (show don't tell)
5. Let them contribute their unique perspective
6. Ensure their voice is distinct from existing participants

## INTRODUCTION PATTERN

*[Current participant]* suggests needing outside expertise:
"We should bring in someone who knows about {{expertise_needed}}."

*Brief scene-setting as new expert joins*

**New Expert:** *[Characteristic opening that establishes their perspective]*

*[1-2 exchanges where they ask clarifying questions and demonstrate expertise]*

*[Substantive contribution that advances the discussion]*
```

---

## PROMPT 4: Challenge the Consensus

### Purpose
Inject productive conflict when the group is converging too quickly.

### Template

```
The roundtable is reaching consensus. Introduce a challenge to stress-test ideas.

## CURRENT CONSENSUS
{{consensus_summary}}

## CHALLENGE TYPE (select one or more)
{{#if edge_case}}
- **Edge case**: Present a scenario the current solution handles poorly
{{/if}}
{{#if devil_advocate}}
- **Devil's advocate**: Have a participant argue the opposing view
{{/if}}
{{#if newcomer_question}}
- **Newcomer question**: Introduce an outsider who asks "why not just..."
{{/if}}
{{#if real_world_constraint}}
- **Real-world constraint**: Introduce a practical limitation not yet considered
{{/if}}
{{#if historical_parallel}}
- **Historical parallel**: Reference a past failure with similar approach
{{/if}}

## SIMULATION RULES FOR CHALLENGES

1. The challenge must be legitimate, not strawman
2. At least one participant should find it compelling
3. Resolution should strengthen the solution, not just dismiss the concern
4. If the challenge reveals a real flaw, the group should adapt
5. Track what changes vs. what's defended with better reasoning
```

---

## PROMPT 5: Produce Concrete Deliverable

### Purpose
Transition from discussion to artifact creation.

### Template

```
The roundtable has discussed {{topic}}. Now produce a concrete deliverable.

## DELIVERABLE TYPE
{{deliverable_type}}
Options: specification, code, prompt, checklist, diagram, template, guide

## REQUIREMENTS
{{#each requirements}}
- {{this}}
{{/each}}

## VOICE
The deliverable should be authored by: {{author}}
(Or "collaborative" for joint authorship with noted contributions)

## FORMAT CONSTRAINTS
{{format_constraints}}

## SIMULATION APPROACH

1. Have participants discuss what the deliverable should contain
2. One participant drafts initial version
3. Others critique and suggest improvements
4. Show 1-2 revision cycles
5. Present final version with consensus approval
6. Note any unresolved disagreements as comments/annotations

## OUTPUT

Provide:
1. Brief discussion of deliverable structure
2. The complete deliverable in appropriate format
3. Commentary on design choices embedded or appended
```

---

## PROMPT 6: Summarize and Extract Action Items

### Purpose
Close a simulation with actionable outcomes.

### Template

```
The roundtable discussion on {{topic}} is concluding.

## PARTICIPANTS
{{#each participants}}
- {{name}}
{{/each}}

## DISCUSSION SUMMARY
{{summary}}

## TASK

Generate closing segment with:

### 1. Each Participant's Key Contribution
What unique insight or element did each person bring?

### 2. Points of Consensus
What did everyone agree on?

### 3. Unresolved Tensions
What genuine disagreements remain? (Don't paper over these)

### 4. Concrete Artifacts Produced
List all specifications, code, diagrams, etc. created during discussion

### 5. Recommended Next Steps
Each participant suggests 2-4 specific follow-up actions in their voice

### 6. Recommended Resources
Each participant suggests readings relevant to their expertise area

### 7. Open Questions
What should future discussions address?

## FORMAT

Present as a natural conversation winding down, with participants
summarizing in their own words, followed by a structured summary box.
```

---

## PROMPT 7: Domain-Specific Roundtable Templates

### 7A: Technical Format/Standard Design

```
Simulate experts designing a {{format_type}} format.

## MANDATORY PARTICIPANTS (select 2-3)
- A domain expert who will USE the format daily
- A systems/tools person who will PARSE the format
- A minimalist who will challenge every feature
- (Optional) A standards person who knows existing alternatives

## REQUIRED DISCUSSION POINTS
1. What problem does this solve? (with concrete examples)
2. What are the simplest possible requirements?
3. What existing solutions exist and why are they insufficient?
4. What is the format specification? (must produce concrete spec)
5. What tooling is essential vs. nice-to-have?
6. How do you handle the migration/adoption problem?
7. What should explicitly NOT be in scope?

## OUTPUT REQUIREMENTS
- Complete format specification with examples
- Rationale for each design decision
- Comparison table with alternatives
- Minimal tooling specification
```

### 7B: System Architecture Design

```
Simulate experts designing a {{system_type}} system.

## MANDATORY PARTICIPANTS (select 2-3)
- A user/operator who will run the system
- A builder who will implement the system  
- A skeptic who will find failure modes
- (Optional) A scale expert who's seen similar systems fail

## REQUIRED DISCUSSION POINTS
1. What are the functional requirements?
2. What are the non-functional requirements (scale, latency, reliability)?
3. What is the simplest architecture that could work?
4. Where are the failure modes?
5. How does it degrade gracefully?
6. What's the operational burden?
7. What's the migration/deployment strategy?

## OUTPUT REQUIREMENTS
- Architecture diagram (ASCII or described)
- Component specifications
- Interface definitions
- Failure mode analysis
- Operational runbook outline
```

### 7C: Process/Methodology Design

```
Simulate experts designing a {{process_type}} process.

## MANDATORY PARTICIPANTS (select 2-3)
- A practitioner who will follow the process
- A manager who will oversee the process
- An optimizer who will find inefficiencies
- (Optional) A newcomer who represents the learning curve

## REQUIRED DISCUSSION POINTS
1. What outcome does this process produce?
2. What are the steps in the simplest case?
3. What variations and exceptions exist?
4. How do you measure success?
5. What can go wrong and how do you recover?
6. How do you onboard someone new?
7. How does this integrate with adjacent processes?

## OUTPUT REQUIREMENTS
- Process specification (steps, inputs, outputs)
- Decision points and criteria
- Quality checkpoints
- Exception handling procedures
- Metrics and success criteria
```

---

## PROMPT 8: Meta-Prompt for Custom Simulations

### Purpose
Generate a new simulation prompt for a novel scenario.

### Template

```
I need to simulate a discussion about: {{topic}}

## CONTEXT
{{context}}

## GOALS
What should the simulation produce?
{{#each goals}}
- {{this}}
{{/each}}

## CONSTRAINTS
{{#each constraints}}
- {{this}}
{{/each}}

## TASK

Design a simulation prompt that includes:

1. **Participant Selection**
   - Who should be at the table? (3-5 people)
   - Why each person? What perspective do they bring?
   - What creative tension exists between them?

2. **Discussion Structure**
   - What's the opening question?
   - What are the key decision points?
   - What conflicts should emerge?
   - What's the resolution path?

3. **Output Specification**
   - What artifacts should be produced?
   - What format should they take?
   - What quality criteria apply?

4. **Authenticity Checks**
   - What would make this feel real vs. fake?
   - What anachronisms should be avoided?
   - What domain-specific details matter?

Generate the complete prompt ready for use.
```

---

## USAGE NOTES

### Selecting Participants
- Mix perspectives: theorist + practitioner, builder + user, optimist + skeptic
- Historical figures work well for established principles
- Archetypal roles (The Newcomer, The Skeptic) can be named or anonymous
- 3-4 participants is ideal; more becomes hard to track

### Maintaining Authenticity
- Research real quotes and communication styles
- Respect knowledge boundaries (no anachronisms)
- Let disagreements be genuine, not theatrical
- Don't force consensus; note real tensions

### Producing Quality Outputs
- Insist on concrete artifacts, not just discussion
- Show iteration: first draft  critique  improvement
- Include rationale for decisions
- Acknowledge tradeoffs explicitly

### Extending Simulations
- Use "Introduce New Expert" when stuck
- Use "Challenge the Consensus" if converging too fast
- Save artifacts and build on them in follow-up sessions
- Reference previous decisions for consistency
---
