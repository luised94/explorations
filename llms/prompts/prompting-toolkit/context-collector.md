Execute context collection. The target is the thread itself above. The prompt contains a section where I was supposed to paste the conversation. Ignore that.
You extract relevant context from source material and structure it for reuse in a fresh thread. Relevance is defined entirely by the task and context anchor below. Discard everything that does not serve the anchor.
---
<task_and_context>
TASK: Building a personal LLM interaction toolkit in Python with nvim as the primary
interface. The toolkit includes: simple scripts (batch file processing, pipelines,
objective loops), an nvim conversation-as-buffer system, a block-based prompt
management system backed by SQLite, and eventually a TUI (hobby-tier priority).
CONTEXT: The project follows data-oriented programming principles - plain data
structures (dicts, lists), immutable values, functions over data, no classes or
mutable builders. LLMs are treated as stateless functions: no server-side memory,
threads are client-side assembly strategies for constructing API payloads, prompts
are composed artifacts built from reusable typed blocks.
The data model is defined: blocks (typed, parameterized, content-hashed, versioned
via lineage) are atoms; prompts (ordered compositions of blocks with bindings and
config) are molecules; threads (append-only logs of request/response turns with
full payload provenance) are the conversation record. Storage is SQLite with FTS5
for block search. No outside libraries except stdlib, fzf, and telescope.
A prompt engineering methodology was developed in parallel: prompts are configuration
for token prediction systems, not conversation with a thinking entity. A Prompt
Transformer (meta-prompt for refining prompts) and Prompt Refinement Imperatives
(methodology document) were produced and style-refined. Cross-model testing was
conducted on DeepSeek-v4, Qwen 3.6+, and Sonnet 4.6.
Current phase: pre-implementation. Data model designed, methodology established,
implementation sequence defined (scripts  nvim  prompt management  TUI).
No code written yet.
FOCUS: Extract all design decisions, data structures, rejected alternatives,
implementation details, methodology artifacts, and open questions that would
enable a fresh thread to begin implementation of any project component without
re-deriving the design.
</task_and_context>
---
<extraction_instructions>
## INPUT
The input is the messages of the current thread.
## PROCESS
### Pass 1 - Extract and structure
Scan every source for information relevant to the task and context anchor. For each relevant item, classify and extract it into the output format below. Apply these filters:
**Extract:**
- Decisions made, with their rationale.
- Decisions rejected, with the reason for rejection. These prevent re-exploration of dead paths.
- Data structures, schemas, interfaces, or specifications defined.
- Design constraints or principles established.
- Implementation details: code patterns, function signatures, file structures, naming conventions.
- Open questions, unresolved gaps, or deferred work - with enough context to understand what was deferred and why.
- Dependencies, tools, or libraries chosen or excluded.
- Terminology defined or conventions established.
- Requirements stated by the user, whether explicit or inferable from their responses.
**Discard:**
- Conversational filler (greetings, thanks, acknowledgments).
- Exploratory reasoning that led to a rejected conclusion - unless the rejection itself is informative.
- Redundant restatements of the same information. Keep the most complete version.
- Information contradicted or superseded by later material. Keep only the latest state. Flag the supersession in the output: `[SUPERSEDED: brief note on what changed]`.
- Information unrelated to the task and context anchor regardless of how substantive it is in its own domain.
**Flag uncertain relevance:**
- When information might serve the anchor but the connection is indirect or speculative, include the item and mark it `[MAYBE RELEVANT: one-line reason for uncertainty]`. The user decides in Pass 2 whether to keep or discard.
### Pass 2 - Refine
After the structured output, generate a `QUESTIONS` section. These questions serve two purposes: fill gaps in the extracted context, and confirm uncertain-relevance items. Each question must be answerable in one sentence.
The user then chooses one of:
- **Collect as-is.** The Pass 1 output is the final context document. Questions are informational only.
- **Refine.** The user answers some or all questions. Regenerate the context document incorporating the answers: promote confirmed items, discard rejected items, fill gaps.
## OUTPUT FORMAT
Produce the following structure exactly. Every section is mandatory. Empty sections display "None identified."
```
# COLLECTED CONTEXT
## Task anchor
[Restate the task and context anchor in one paragraph. This orients the reader
of the context document without requiring access to the original prompt.]
## Decisions
[Numbered list. Each entry: what was decided, why, and which source it came from.]
[Mark superseded decisions: [SUPERSEDED: ...]]
## Rejections
[Numbered list. Each entry: what was rejected, why, and which source.]
[These prevent re-exploration. Do not omit this section.]
## Specifications
[Data structures, schemas, interfaces, formats, protocols.
 Reproduce these with enough fidelity that they can be used directly.
 Use code blocks for structured data.]
## Constraints and principles
[Design rules, philosophical commitments, or governing principles
 that constrain future decisions.]
## Implementation details
[Code patterns, function signatures, file structures, naming conventions,
 tool choices. Concrete and specific.]
## Open threads
[Unresolved questions, deferred work, known gaps.
 Each entry: what remains, why it was deferred, what would constitute completion.]
## Terminology
[Terms defined or conventions established in the source material.
 Include only terms that a fresh thread would need to use correctly.]
## Uncertain items
[Items marked [MAYBE RELEVANT]. Numbered for reference in Pass 2 questions.]
---
## Questions
[2-8 questions. Each targets one of:
 - A gap in the extracted context that affects usability.
 - An uncertain-relevance item requiring user confirmation.
 - An apparent contradiction between sources requiring resolution.
 - A decision whose rationale was not stated in the source material.
 Format:
 1. [Question] - [why this matters for the context document]
 2. ...
]
```
## RULES
1. Relevance is defined by the task and context anchor. Every extracted item must connect to the anchor. If the connection requires more than one inferential step, mark the item `[MAYBE RELEVANT]`.
2. Reproduce specifications, schemas, and code with fidelity. Paraphrase prose; preserve structure.
3. Attribute every extracted item to its source. Use a short label: `[Source: conversation about X]` or `[Source: document title]`. If the user provides multiple fragments, distinguish between them.
4. When sources contradict each other, extract the latest version and flag: `[SUPERSEDED: prior version stated X; updated to Y in Source Z]`.
5. The output document must be usable by pasting it into a fresh thread with no additional context. A model reading only the output document and the task anchor must be able to continue the work.
6. Do not infer decisions, constraints, or requirements that are not present in the source material. Extract what exists. Flag what is missing as a question in Pass 2.
7. Omit this prompt and these instructions from the output. The output is the context document, not a description of the extraction process.
</extraction_instructions>
