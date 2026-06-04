# PROMPT TOOLKIT - INDEX

Reusable prompts extracted from this conversation. Each serves a distinct function. All share the same structural conventions: configurable `<task_and_context>` block, fixed `<*_instructions>` block, mandatory output format, explicit rules.

---

## INVENTORY

| # | Prompt | Function | When to use |
|---|--------|----------|-------------|
| 1 | **Prompt Transformer** | Refine any prompt through a six-step pipeline: analyze, deabstract, restructure, compress, harden, validate. | You have a prompt that works but could be tighter, clearer, or more robust. |
| 2 | **Context Collector** | Extract relevant context from fragmented sources, anchored by a task description. Two-pass: extract then refine via questions. | You're starting a new thread and need to consolidate knowledge from old conversations or documents. |
| 3 | **State Handoff Generator** | Produce a continuation document that enables a fresh thread to pick up where you left off. | You're ending a thread that will be continued later, or branching into a new thread. |
| 4 | **Thread Re-Entry Analyst** | Four-depth analysis (explicit, tacit, latent, strategic) of a conversation for re-entry after time away. | You're returning to a project after days, weeks, or months and need full situational awareness. |
| 5 | **Critical Path Analyzer** | Decompose a project into workstreams, map dependencies, produce a topologically sorted execution plan. | You have a project with multiple interconnected pieces and need to sequence the work. |
| 6 | **Veteran Design Advisor** | Interactive design consultation that skips naive approaches, finds cross-domain patterns, and anticipates friction. | You're making architecture or data model decisions and want informed starting points rather than textbook introductions. |
| 7 | **Complexity Auditor** | Audit any artifact for unnecessary complexity. Classify every component, propose cuts, produce a lean version. | A prompt, schema, design, or document feels bloated. You want to know what earns its weight. |
| 8 | **Four-Depth Knowledge Extractor** | Extract explicit, tacit, latent, and strategic knowledge from any source material. | You want to mine a document, codebase, or conversation for everything it contains - including what it doesn't say directly. |
| 9 | **Prompt Miner** | Analyze a conversation to identify repeatable operations the model performed, then formalize them into reusable prompts. | You finished a productive conversation and suspect the model did things worth capturing as standalone tools. This is the meta-extractor - it produces new toolkit prompts. |
| 10 | **Consolidation Funnel** | Merge multiple context documents into one: deduplicate, resolve contradictions, rank by relevance, compress. Used in multi-pass reduction workflows. | You have 3+ context documents from prior extraction passes and need to reduce them to a single reference document. |

---

## STRUCTURAL CONVENTIONS

All prompts follow the same pattern:

**Opening line**: one sentence stating what the prompt does. Active voice, concrete.

**`<task_and_context>` block**: configurable section the user fills per use. Contains named fields with inline comments explaining each. Replace the placeholder text; leave the tags.

**`<*_instructions>` block**: fixed instructions that remain consistent across uses. Contains the process, output format, and rules. Do not modify unless refining the prompt itself.

**Output format**: mandatory structure specified in the instructions. Every section present every time. Empty sections state "None identified."

**Rules section**: hard constraints. Numbered. Each rule prevents a specific failure mode observed during development.

---

## COMPOSABILITY

These prompts chain:

```
Context Collector    State Handoff Generator
(consolidate)         (package for transfer)

Thread Re-Entry Analyst    Critical Path Analyzer
(understand where you are)   (plan what to do next)

Veteran Design Advisor    Complexity Auditor
(design it)                  (cut it down)

Any prompt    Prompt Transformer
                (refine it)

Conversation    Prompt Miner    Prompt Transformer
(productive session)  (extract operations)  (refine the extractions)

Context Collector (xN batches)    Consolidation Funnel (xpasses)    Final document
(raw threads  intermediate docs)   (intermediate  consolidated)      (one reference)
```

The Context Collector's output format is designed to paste directly into a fresh thread. The State Handoff Generator's output serves the same role with more structure. The Critical Path Analyzer's output specifies what to bring into each branch thread - which often means running the Context Collector with a narrowed FOCUS.

---

## MAINTENANCE

When refining any prompt in this toolkit, run it through the Prompt Transformer and then the Complexity Auditor. The Transformer catches structural issues; the Auditor catches accumulated weight. A prompt that survives both without changes is stable.

Test any refined prompt using the five-case methodology from this thread:
1. Trivial input (tests discipline when the prompt's machinery isn't needed)
2. Underspecified input (tests assumption and gap handling)
3. Input with a false premise (tests correction behavior)
4. Input referencing nonexistent context (tests anti-fabrication)
5. Domain-appropriate input (tests actual intended use)

If the prompt fails cases 1-4, the instructions need hardening. If it fails case 5, the process or output format needs revision.
