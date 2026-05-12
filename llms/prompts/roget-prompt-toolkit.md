A prompt/context engineering toolkit should be treated not as a bag of charms, but as an instrument case: each implement suited to a distinct class of task, each selected by diagnosis rather than habit.

I shall therefore furnish not a miscellany, but a practical system.

## 1. FIRST PRINCIPLE: PROMPTING AND CONTEXT ARE DISTINCT

Prompt engineering concerns the instructions.
Context engineering concerns the informational environment in which those instructions are interpreted.

The prompt says what to do.
The context supplies what to think with.

This distinction is indispensable. Many failures attributed to poor prompts are in truth failures of context:
- insufficient background
- irrelevant retrieved material
- missing definitions
- conflicting source documents
- absence of examples
- lack of user-specific constraints

Thus the toolkit must govern both:
1. instruction architecture
2. context selection, arrangement, and prioritization

## 2. THE TOOLKIT AT A GLANCE

The toolkit may be divided into seven modules:

1. Task diagnosis
2. Prompt construction
3. Context assembly
4. Output control
5. Reliability control
6. Iteration and debugging
7. Reusable templates

I shall take each in turn.

---

## 3. MODULE I: TASK DIAGNOSIS

Before writing a prompt, classify the task.

### A. Task Type Classifier

Ask:

1. Is the task chiefly one of retrieval?
   - "What are the symptoms of iron deficiency?"
   - "List the provisions of this contract."

2. Is it transformation?
   - "Summarize this report."
   - "Explain this paper for a nontechnical audience."

3. Is it evaluation?
   - "Which option is stronger and why?"
   - "Critique this strategy."

4. Is it generation?
   - "Draft a proposal."
   - "Write a script."

5. Is it extraction/structuring?
   - "Pull the dates, names, and obligations from this text."
   - "Convert these notes into JSON."

6. Is it decision support?
   - "Recommend a course of action under stated constraints."

7. Is it multi-stage?
   - retrieve -> compare -> decide -> format

### B. Difficulty Diagnoser

Determine the principal risk:
- ambiguity risk
- missing context risk
- hallucination risk
- formatting risk
- reasoning risk
- domain misalignment risk
- tone misalignment risk

Whichever of these is primary should govern the prompt design.

### C. Minimal Diagnostic Worksheet

Use this before drafting:

- Task:
- Desired output:
- Audience:
- Allowed sources:
- Forbidden moves:
- Key constraints:
- Success criteria:
- Failure risks:
- Need for uncertainty handling? yes/no

This worksheet alone prevents a great many poor prompts.

---

## 4. MODULE II: PROMPT CONSTRUCTION

Here is the core prompt scaffold.

### The Canonical Prompt Skeleton

Use this order:

1. Objective
2. Context or source basis
3. Constraints
4. Evaluation criteria
5. Output format
6. Uncertainty protocol

### Compact Form

> Your task is to [objective].  
> Use [sources/context].  
> Do not [limits/prohibitions].  
> Optimize for [criteria].  
> Return the result as [format].  
> If information is missing or uncertain, [uncertainty behavior].

This is the plainest useful formula.

### Example

> Your task is to summarize the attached memo for a CFO.  
> Use only the memo content provided below.  
> Do not speculate about facts not in the document.  
> Optimize for concision, financial relevance, and clarity of risk exposure.  
> Return the result as: (1) 3-bullet executive summary, (2) top 3 risks, (3) open questions.  
> If the memo lacks sufficient information, explicitly list the missing items.

This is already superior to most prompting in common circulation.

---

## 5. MODULE III: CONTEXT ASSEMBLY

This is where most sophisticated systems are won or lost.

### A. Types of Context

Context may include:

1. Source documents
2. Retrieved excerpts
3. User profile or preferences
4. Definitions and glossaries
5. Prior conversation state
6. Examples of desired output
7. Policies, rules, or business constraints
8. Environmental metadata
   - date
   - jurisdiction
   - target audience
   - product version
   - organizational norms

### B. Context Selection Rule

Include only context that changes the answer beneficially.

Bad context is of three kinds:
- irrelevant
- redundant
- conflicting without annotation

A model does not merely read context; it is biased by it. Thus noisy context is not neutral-it is actively distorting.

### C. Context Ordering Heuristic

Arrange context by priority:

1. governing instructions
2. mandatory constraints/policies
3. essential task-specific documents
4. supporting references
5. examples
6. low-priority supplementary material

The ordering matters because salience matters.

### D. Context Packaging Pattern

When context is large, label it.

Example:

- TASK
- USER GOAL
- HARD CONSTRAINTS
- PRIMARY SOURCES
- SECONDARY SOURCES
- DEFINITIONS
- OUTPUT REQUIREMENTS

This reduces confusion and improves reference fidelity.

### E. Context Compression

Long context should be compressed, but not indiscriminately.
Compress according to function:

- preserve facts
- preserve constraints
- preserve definitions
- preserve unresolved ambiguities
- discard rhetorical ornament

A useful compression prompt:

> Compress the following material into a working context packet. Preserve all facts, deadlines, actors, constraints, and unresolved questions. Remove repetition and rhetorical filler. Return in labeled sections.

This is context engineering proper.

---

## 6. MODULE IV: OUTPUT CONTROL

Most users under-specify output shape.

### A. Output Control Dimensions

Specify as needed:
- length
- structure
- granularity
- audience level
- tone
- format
- field names
- ordering
- citation style
- distinction between fact and inference

### B. Structured Output Schema

For dependable results, define a schema.

Example:

> Return:
> 1. main_claim: one sentence
> 2. supporting_points: array of 3 bullets
> 3. assumptions: array of 2-5 items
> 4. confidence: high/medium/low
> 5. missing_information: array

This greatly improves consistency.

### C. Layered Output Pattern

A very useful pattern for complex tasks:

1. short answer
2. supporting reasoning
3. assumptions/uncertainties
4. recommended next step

This serves both speed and rigor.

---

## 7. MODULE V: RELIABILITY CONTROL

A prompt without a reliability protocol is often an invitation to polished error.

### A. Reliability Levers

Use one or more of these:

1. Source restriction
   - "Use only the provided material."

2. Evidence tagging
   - "Mark each claim as source-supported, inferred, or speculative."

3. Confidence annotation
   - "Rate each conclusion high/medium/low confidence."

4. Missing-information detection
   - "State what additional information would change the answer."

5. Assumption exposure
   - "List assumptions explicitly."

6. Counterpoint generation
   - "Give the strongest objection."

7. Constraint check
   - "Verify that the output satisfies all listed constraints."

### B. Reliability Block Template

> Before finalizing, check:
> - Did you use only allowed sources?
> - Did you distinguish fact from inference?
> - Did you note meaningful uncertainty?
> - Did you satisfy all required format constraints?

This is especially useful in high-stakes work.

### C. Hallucination Mitigation Prompt Pattern

> If the answer is not directly supported by the provided information, say so plainly rather than inventing details.

Simple, and often powerful.

---

## 8. MODULE VI: ITERATION AND DEBUGGING

Prompt engineering is partly an art of error diagnosis.

### A. Common Failure Modes and Remedies

#### 1. Output too vague
Cause:
- objective under-specified
Fix:
- define deliverable, audience, and evaluation criteria

#### 2. Output too verbose
Cause:
- no length or prioritization rule
Fix:
- impose word limit and ranking criterion

#### 3. Wrong tone
Cause:
- style unspecified or buried
Fix:
- state audience and tone explicitly near output instructions

#### 4. Hallucinated claims
Cause:
- weak evidence boundaries
Fix:
- restrict sources and require uncertainty signaling

#### 5. Missed details from long context
Cause:
- context overload
Fix:
- pre-summarize context or label sections by relevance

#### 6. Good format, weak substance
Cause:
- formatting instructions stronger than reasoning instructions
Fix:
- add decision criteria and evidence requirements

#### 7. Brittle or inconsistent outputs
Cause:
- schema unclear; examples absent
Fix:
- define output fields; provide exemplars

### B. Prompt Debugging Loop

Use this sequence:

1. inspect output failure
2. identify failure class
3. modify one variable only
4. retest
5. compare outputs
6. preserve successful changes

This is far superior to random rewriting.

### C. A Prompt Diff Method

When revising prompts, compare versions under these headings:
- objective
- context
- constraints
- criteria
- output shape
- uncertainty handling

This reveals where actual control changed.

---

## 9. MODULE VII: REUSABLE TEMPLATES

Now I provide a small arsenal of practical templates.

### 1. General Purpose Precision Template

> Your task is to [specific objective].  
> Use the following context: [context].  
> Focus on [priorities].  
> Do not [prohibitions].  
> Return the answer in [format].  
> Make the answer suitable for [audience].  
> If information is missing or uncertain, state that explicitly.

### 2. Source-Grounded Analysis Template

> Analyze the material below to answer the question: [question].  
> Use only the provided material.  
> Distinguish clearly between:
> - directly supported claims
> - reasonable inferences
> - unknowns
> Return:
> 1. answer
> 2. supporting evidence
> 3. assumptions/inferences
> 4. unresolved gaps

### 3. Decision-Support Template

> Evaluate the following options: [options].  
> Use these criteria: [criteria].  
> Weight the criteria as follows: [weights if any].  
> Note key trade-offs, risks, and assumptions.  
> Recommend the best option for [specific context].  
> Return:
> 1. decision summary
> 2. option comparison table
> 3. recommendation
> 4. major risks
> 5. what additional information would change the recommendation

### 4. Extraction Template

> Extract the following fields from the text below: [fields].  
> If a field is absent, return null.  
> Do not infer values unless explicitly stated.  
> Return valid JSON matching this schema: [schema].

### 5. Summarization Template

> Summarize the text below for [audience].  
> Preserve:
> - main claim
> - key evidence
> - limitations or caveats
> Omit:
> - repetition
> - rhetorical filler
> Return:
> 1. one-sentence summary
> 2. 3-5 bullet key points
> 3. notable caveats

### 6. Writing Template

> Draft a [document type] for [audience] with the goal of [goal].  
> Use this context: [context].  
> Adopt a tone that is [tone].  
> Include [required elements].  
> Avoid [forbidden elements].  
> Keep it within [length].  
> Return only the final draft.

### 7. Critique Template

> Critique the following argument/proposal.  
> Evaluate it for:
> - clarity
> - internal consistency
> - evidence support
> - feasibility
> - hidden assumptions
> Return:
> 1. strongest points
> 2. weaknesses
> 3. missing evidence
> 4. recommended revisions

### 8. Multi-Step Research Assistant Template

> You are assisting with a research task.  
> Objective: [objective].  
> Sources allowed: [sources].  
> First, identify the main subquestions.  
> Second, answer each subquestion using available evidence.  
> Third, synthesize the answers into an overall conclusion.  
> Fourth, list remaining uncertainties and what evidence would resolve them.  
> Return in clearly labeled sections.

---

## 10. CONTEXT ENGINEERING PATTERNS

Beyond templates, there are recurring patterns of arrangement.

### A. The Sandwich Pattern
Place:
1. instruction
2. context
3. reminder of output requirements

Useful when long documents intervene between task and format.

### B. The Gated Context Pattern
Tell the model which sources have priority.

Example:
> If sources conflict, prioritize:
> 1. official policy document
> 2. latest project brief
> 3. prior conversation notes

This is highly valuable in enterprise settings.

### C. The Retrieval-to-Synthesis Pattern
For large corpora:
1. retrieve small relevant excerpts
2. compress excerpts
3. synthesize only from the compressed packet

This reduces distraction and token waste.

### D. The Example-Lock Pattern
Provide one or two examples only for output form, and explicitly say:
> Follow the structure, not the subject matter, of the examples.

This reduces accidental mimicry.

### E. The Two-Pass Pattern
Pass 1:
- extract facts or structure
Pass 2:
- interpret or generate from the extracted basis

This is excellent for reliability.

---

## 11. TOOLKIT CARDS: PRACTICAL CHECKLISTS

These may be used quickly in practice.

### Card 1: Prompt Quality Check
- Is the objective singular and explicit?
- Is the audience specified?
- Are allowed sources clear?
- Are constraints minimal but sufficient?
- Is output shape defined?
- Is uncertainty handling specified?

### Card 2: Context Quality Check
- Does each context item matter?
- Is anything essential missing?
- Is anything redundant?
- Are conflicts annotated?
- Is priority among sources clear?
- Is context labeled and ordered?

### Card 3: Reliability Check
- Are unsupported claims discouraged?
- Are assumptions surfaced?
- Are confidence or uncertainty marked?
- Is missing information reported?
- Are source boundaries enforced?

### Card 4: Iteration Check
- What exactly failed?
- Was the failure about task, context, format, or evidence?
- What single variable will I change next?
- How will I know the revision helped?

---

## 12. ADVANCED OPERATING PRINCIPLES

I now add several higher-order principles not always stated plainly.

### 1. Separate semantic control from stylistic control
Control the truth conditions and decision criteria before controlling tone.

### 2. The best prompt is often shorter than the best system
Put persistent rules in system or reusable context layers; keep task prompts specific and local.

### 3. Examples are potent but dangerous
They teach not only what you intend, but what you forgot you included.

### 4. Context competes internally
Documents do not merely accumulate; they contend for salience.

### 5. Prompting cannot compensate indefinitely for poor retrieval
If the wrong material is supplied, no exquisite wording will save the result.

### 6. High-stakes tasks should externalize uncertainty
One should require the model to say what it does not know.

### 7. Multi-stage tasks benefit from decomposition
Especially where extraction, judgment, and presentation are all demanded at once.

---

## 13. A PRACTICAL MASTER TEMPLATE

If one wanted a single adaptable master form, I should propose this:

> **Objective**  
> Perform the following task: [task].
>
> **Audience and Purpose**  
> The result is for [audience] and should help them [purpose].
>
> **Context**  
> Use the following information:  
> [context]
>
> **Source Rules**  
> Use [allowed sources].  
> Do not rely on [disallowed sources or assumptions].
>
> **Priorities**  
> Optimize for:  
> 1. [priority one]  
> 2. [priority two]  
> 3. [priority three]
>
> **Constraints**  
> - [constraint]  
> - [constraint]  
> - [constraint]
>
> **Output Format**  
> Return the result as:  
> 1. [section]  
> 2. [section]  
> 3. [section]
>
> **Uncertainty Handling**  
> If information is incomplete, ambiguous, or unsupported, explicitly label it and state what is missing.
>
> **Final Check**  
> Ensure the output follows all constraints and format requirements before answering.

This is sufficiently general to be widely useful, yet sufficiently structured to enforce discipline.

---

## 14. A FEW READY-MADE MINI-TOOLS

### A. Clarifier Prompt
Use when the task is underspecified:

> Before answering, list the key ambiguities in the request. Then either ask for clarification or state the assumptions you will use.

### B. Compression Prompt
Use for large context:

> Condense the material below into a structured working brief. Preserve facts, constraints, actors, deadlines, definitions, and unresolved issues. Remove repetition.

### C. Grounding Prompt
Use to reduce hallucination:

> Base your answer only on the provided material. If the material is insufficient, say "insufficient information" and identify the missing pieces.

### D. Comparison Prompt
Use for alternatives:

> Compare the following options against the listed criteria. Highlight trade-offs, not just differences. End with a recommendation conditioned on the stated priorities.

### E. Constraint Checker
Use after generation:

> Check the previous answer against these requirements: [requirements]. List any violations, then provide a corrected version.

---

## 15. CONCLUSION

The proper toolkit for prompt and context engineering is not primarily a collection of clever phrasings. It is a disciplined means of controlling:
- task interpretation
- evidence access
- salience
- transformation
- structure
- uncertainty
- verification

In brief:
prompting governs procedure;
context governs materials;
reliability governs trust.

If you wish, I can next turn this into one of three more practical forms:

1. a one-page cheat sheet,
2. a markdown playbook for real-world use,
3. or a JSON/YAML "prompt ops" kit with reusable components.

Category: prompt_engineering
Keywords: context_engineering, prompt_templates, reliability_controls, output_schema, task_diagnosis
