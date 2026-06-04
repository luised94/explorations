# LLM PERSONAL TOOLKIT - PROJECT HANDOFF

This document combines design work from two separate threads into a single continuation point. One thread developed prompt engineering methodology and a systems-oriented view of LLM interaction. The other thread developed data-oriented models for prompts and threads as data structures. Both converge on the same project: a personal code module for interacting with LLMs.

---

## 1. GOVERNING PHILOSOPHY

Two frameworks govern this project. They reinforce each other.

**Data-Oriented Programming.** Data is plain, generic structures - maps, vectors, lists. Code operates on data; data carries no behavior. Immutability is the default. Validation is explicit and separate. Let the data guide the code, not the reverse.

**Deanthropomorphized LLM view.** LLMs are stateless functions. They predict tokens. They do not think, remember, or understand. A "conversation" is a client-side assembly strategy for constructing API payloads. A "prompt" is a composed artifact, not a string. The model receives a fully-constructed input every call and retains nothing between calls. Every design decision follows from this.

These two frameworks produce the same conclusion: **own your data, treat the model as a pure function, and make composition explicit.**

---

## 2. PROJECT SCOPE AND CURRENT STATE

The user is building a personal LLM interaction toolkit. Four components, ordered by current status:

| Component | Status | Complexity | Notes |
|-----------|--------|------------|-------|
| **Simple scripts** (batch file processing, pipelines, objective loops) | Not started | Low | Highest immediate value. Establishes API interaction patterns. |
| **Nvim conversation-as-buffer** | Considering | Medium | Natural fit - buffers are text, conversations are text. Format and plugin design needed. |
| **TUI/CLI multi-turn** | Attempted, shelved | High | Too complex as a starting point. Revisit after simpler tools prove the data model. |
| **Prompt management system** | Design phase | High | Requires correct data modeling. Two design explorations completed (see Section 4). |

---

## 3. DECISIONS AND REJECTIONS

### Decided

| Decision | Rationale |
|----------|-----------|
| Model is stateless; thread exists only client-side | Ground truth of proprietary API interaction. No server-side state to rely on. Thread data is owned entirely by the user. |
| Prompts are structured data (maps), not strings | Strings are the serialization format. The source of truth is a structured payload: messages (role + content) + config (model, temperature, max_tokens) + optional tools/format constraints. |
| Threads are append-only logs of request/response pairs with provenance | Each turn stores the full request payload, the full response, token counts, latency, model ID, and finish reason. The thread is a record of what happened, not just what was said. |
| Config is co-located with messages | Temperature, model, and max_tokens are part of the prompt's identity. Different config on identical messages produces different outputs. |
| Content supports structured types | `:content` can be a string or a vector of typed content parts (text, image, tool result). Tagged union, not string interpolation. |
| Roles are explicit data fields, not string prefixes | Enables programmatic filtering, validation, and migration. |
| Data-oriented: no classes, no mutable builders, no method-bearing objects | Functions take data in, produce data out. Data is serializable, diffable, hashable. |

### Rejected

| Rejected approach | Why |
|-------------------|-----|
| String-based templates as primary representation | Strings are lossy. Parsing structured meaning from a string is fragile. Structured data renders to strings trivially; the reverse does not. |
| Object-oriented prompt builders | Mutable state, method chaining, and implicit context violate DOP. Harder to serialize, diff, and reason about. |
| Assuming server-side thread storage | Proprietary and ephemeral. Data should outlive any single API provider. |
| Over-abstracting into a generic "LLM interface" | Premature. Start with concrete data shapes for the models actually used. Factor common patterns after they emerge. |
| Thread-first design (prompts derived from threads) | Inverts the reuse relationship. Blocks and prompts exist independent of any thread - they are the reusable library. Threads consume them. |
| Tree-structured blocks (instead of flat ordered list) | Prompt composition is nearly always linear: system  instructions  context  input. Trees solve a problem that rarely exists. May revisit for multi-agent orchestration. |
| Storing only resolved strings, deriving blocks lazily | Destroys sub-prompt retrieval and reuse. Fine-grained data exists first; the assembled string is a derived view. |
| TUI/CLI as starting point | Too much interface complexity before the data model is proven. Build simpler tools first; graduate to TUI when the underlying patterns are stable. |

---

## 4. TWO DESIGN EXPLORATIONS - RECONCILIATION

Two separate design sessions produced models at different abstraction levels. They are not contradictory - they represent different points on a complexity spectrum.

### Model A: Block-based composition (veteran view)

Atoms are **blocks** - typed, parameterized, versioned fragments with metadata (tags, model affinities, lineage). Prompts are **molecules** - ordered compositions of blocks with bindings. Threads have **assembly policies** governing how context windows are constructed (full history, sliding window, summarization, relevance selection).

Strengths: maximum reusability, A/B testing at block level, retrieval by function. Enables a prompt library with search, versioning, and performance tracking.

Complexity cost: block registry, content-hash IDs, lineage tracking, policy engine for assembly. Significant infrastructure before first use.

### Model B: Plain-data maps (intermediate view)

Prompts are **maps** with messages + config. Threads are **append-only logs** of request/response pairs. Functions operate on these structures directly. Clojure-flavored, minimal indirection.

Strengths: immediately implementable, easy to reason about, serializes to JSON/EDN trivially. No infrastructure overhead.

Limitation: reuse is manual. No block sharing across prompts. No assembly policy - context window management is ad-hoc.

### Reconciliation: start with B, evolve toward A

Build on Model B's simplicity. The data shapes are correct and sufficient for the simple-scripts and nvim-buffer components. When prompt reuse becomes painful (the same system instruction copy-pasted into many prompts, the same output-format constraint duplicated), factor those repeated elements into blocks. Let friction drive the migration, not upfront architecture.

**Concrete evolution path:**
1. Start: prompts as maps, threads as logs, files on disk.
2. First friction: duplicated instructions across prompts  extract shared blocks, reference by ID.
3. Second friction: context window overflow  add assembly policy to thread construction.
4. Third friction: "which version of this prompt worked best?"  add metadata, annotations, lineage.

Each step is motivated by a real problem. No step is speculative.

---

## 5. CONCRETE NEXT STEPS

Ordered by dependency and complexity. Each step produces a usable tool.

### Step 1: Core data shapes + single-call script

Define the data structures for prompt and response. Build one function that takes a prompt map, calls an API, and returns a response map. This is the foundation everything else sits on.

```
prompt    call_llm(prompt)    response
```

Deliverable: a module with `make_prompt`, `call_llm`, `save_response`. File-based storage (JSON or YAML). No database.

### Step 2: Batch file processing script

Take a directory of files, apply a prompt to each, collect results. This is the "calling LLM on a bunch of files one by one" use case.

```
for file in directory:
    prompt = make_prompt(system_instruction, file.content)
    response = call_llm(prompt)
    save(file.name, response)
```

Deliverable: a CLI script. Input: directory path + prompt template. Output: directory of results.

### Step 3: Simple pipeline

Chain two or more LLM calls. Output of step N feeds into the prompt of step N+1.

```
result_1 = call_llm(prompt_1(input))
result_2 = call_llm(prompt_2(result_1))
```

Deliverable: a pipeline runner that accepts a list of prompt templates and pipes output forward. File-based intermediate storage for inspection.

### Step 4: Objective loop

Run an LLM call in a while loop until some condition is met - a quality check, a self-evaluation, or a fixed iteration count.

```
result = call_llm(initial_prompt)
while not done(result):
    result = call_llm(refine_prompt(result))
```

Deliverable: a loop runner with configurable exit conditions. Store each iteration for review.

### Step 5: Nvim conversation-as-buffer

Design a buffer format that is both human-readable and machine-parseable. One conversation per buffer. Structured enough to reconstruct API payloads; readable enough to edit by hand.

Proposed format:

```markdown
---
model: claude-sonnet-4-20250514
temperature: 0.7
system: |
  You are a data-oriented programming assistant.
---

## user
What is a prompt as a data structure?

## assistant
A prompt is a structured map containing...

## user
How does that differ from the naive view?
```

YAML frontmatter carries config. Markdown headers with role names delimit messages. A parser converts this buffer to the API payload format from Step 1. A plugin sends the payload, appends the response as a new `## assistant` block, and positions the cursor for the next `## user` input.

Key design questions to resolve:
- [ASSUME: single file per conversation - simplest model, matches buffer-per-conversation metaphor]
- [GAP: how to handle tool calls and structured content in the buffer format - these don't render naturally as markdown]
- [GAP: plugin architecture - Lua-based nvim plugin vs. external process communicating via stdin/stdout vs. nvim's built-in terminal]
- [GAP: how to handle context window limits - truncation policy needs a UI affordance, maybe a marker line the user can move]

### Step 6: Prompt management (deferred design)

Build the block-based composition system from Model A when Steps 1-5 reveal the actual reuse patterns. Do not build this first. Specific triggers for starting this work:

- You find yourself copy-pasting the same system instruction into more than three prompt files.
- You want to compare two versions of a prompt and can't diff them meaningfully because the whole string changed.
- You want to find "the prompt fragment that produces structured JSON" and have no way to search for it.

Until at least two of these triggers fire, file-based prompt storage with a directory convention is sufficient.

---

## 6. RELEVANT METHODOLOGY FROM PROMPT ENGINEERING THREAD

The prompt engineering thread produced several artifacts directly applicable to this project:

**Processing Protocol (Lean version).** A minimal system prompt structure: scratchpad, ASSUME/GAP markers, three modes (DESIGN/EXECUTE/COMPILE), probing questions, corrections, metadata. Can be stored as a prompt template in the toolkit and used as the default system prompt for design-oriented LLM interactions.

**Prompt Transformer.** A meta-prompt that refines other prompts through a six-step pipeline (analyze  deabstract  restructure  compress  harden  validate). Directly useful as a tool in the pipeline system (Step 3): pipe a draft prompt through the transformer before using it.

**Prompt Refinement Imperatives.** The methodology document. Governs how prompts are written and refined. Key principles applicable to the toolkit:
- Every instruction in a prompt should map to one observable output change.
- Structural affordances (formats to fill) outperform behavioral requests (dispositions to adopt).
- Test-driven hardening: add rules only for observed failures.
- Prompts are configuration for a token prediction system, not conversation with a thinking entity.

**Cross-model testing methodology.** Five test cases that probe compliance: trivial query, underspecified query, false premise, missing context, domain-specific. Automatable as a script in the toolkit - run the suite against any new prompt to evaluate its robustness.

**State Handoff Document Generator.** A prompt that produces handoff documents like this one. Useful for serializing conversation state when switching threads or archiving completed design sessions.

---

## 7. DESIGN RECOMMENDATIONS

**Start with data shapes, not interfaces.** Define the prompt map and response map structures first. Everything else - scripts, nvim plugin, prompt management - is functions over those structures. If the data shapes are right, the code is straightforward. If the data shapes are wrong, no amount of clever code fixes them.

**File-based storage first.** JSON or YAML files in a directory tree. No database until the file system fails you. A directory convention (`prompts/`, `threads/`, `responses/`, `pipelines/`) provides organization. Git provides versioning. `grep` provides search. These tools are free and sufficient until they aren't.

**One language, one calling convention.** Pick the language for the core module and commit. The scripts, pipeline runner, loop runner, and nvim plugin should all call the same `call_llm` function with the same data shapes. No wrapper libraries, no framework. Plain functions over plain data.

**Design the nvim buffer format carefully.** The buffer format is a user interface AND a data format. It must be pleasant to read and write by hand AND parseable by the plugin. YAML frontmatter + markdown role headers is a reasonable starting point. Validate the format by writing three sample conversations by hand before building the parser.

**Defer prompt management.** The block-based composition system is the correct eventual architecture. Building it before you have 50+ prompts and clear reuse patterns is premature optimization. The file-based approach from Steps 1-4 will reveal which abstractions are actually needed.

---

## 8. OPEN THREADS

| # | Thread | What remains | Completion criteria |
|---|--------|-------------|---------------------|
| 1 | Core data shapes | Define prompt, response, turn, and thread structures in the target language. | Structures defined, serialization to/from JSON verified, one round-trip API call working. |
| 2 | Batch processing script | Build the file-processing loop from Step 2. | Script processes a directory of files, produces output files, handles API errors gracefully. |
| 3 | Nvim buffer format | Resolve the three GAPs: tool calls in markdown, plugin architecture, context window UI. | Format spec written, three sample conversations validated, parser implemented. |
| 4 | Pipeline and loop runners | Build Steps 3 and 4. | Pipeline chains two calls with intermediate storage. Loop runs with configurable exit. |
| 5 | Prompt management design | Finalize block-based model when reuse friction triggers. | Deferred. Triggers defined in Step 6 above. |
| 6 | Prompt engineering artifacts | Test the lean processing protocol and prompt transformer on diverse inputs. | Five-case test suite run on at least two models. Compliance compared to full version. |

---

## 9. USAGE

Paste this document at the start of a fresh thread. State which open thread (Section 8) you are continuing, or which step (Section 5) you are working on.

Attach artifacts as needed:
- **Working on scripts/pipelines (Steps 1-4)**  no additional artifacts needed; this document contains the data shapes and design.
- **Working on nvim plugin (Step 5)**  attach sample conversation files in the proposed buffer format.
- **Working on prompt management (Step 6)**  attach the Prompt Refinement Imperatives and the block-based design from Document 1 in this conversation.
- **Refining prompts for use in the toolkit**  attach the Prompt Transformer and the Processing Protocol (lean version).

[COMPRESSED: The full prompt engineering conversation history, including intermediate protocol versions (v4.0 through v4.3), raw cross-model test outputs, and the Socratic probing module are omitted. The methodology, decisions, and findings are captured in Sections 6 and the Prompt Refinement Imperatives artifact. Attach the full test results if continuing thread 6.]

## 10. Search
```thinking
The user is saying:
1. They're ready for the veteran block-based prompt model (Model A from the design docs)
2. They're already managing many threads and prompts - the friction triggers have already fired
3. They want resources, tactics to reduce implementation friction, and veteran advice
4. They still want to do simple scripts and nvim first (ordering preserved)

So they're not deferring Step 6 anymore - they're committing to it, but sequencing it after the simpler tools. They want me to:
1. Provide resources to read (books, papers, projects, code)
2. Anticipate friction during implementation
3. Give veteran advice
4. Tactics to reduce friction

Let me think about what resources are actually relevant:

**Data-Oriented Programming:**
- "Data-Oriented Programming" by Yehonathan Sharvit - the DOP book, Clojure-influenced
- Rich Hickey's talks - "Simple Made Easy", "The Value of Values", "Maybe Not" (on schemas)
- "Designing Data-Intensive Applications" by Martin Kleppmann - overkill for a personal project but the data modeling chapters are gold

**Prompt Engineering / Management:**
- Anthropic's prompt engineering docs
- OpenAI's prompt engineering guide
- LangChain and LlamaIndex - not as libraries to use (they're anti-DOP: heavy OOP, lots of abstraction) but as reference for what problems they solve and what data shapes they use
- Simon Willison's blog and `llm` CLI tool - closest to what the user is building
- fabric by Daniel Miessler - pattern-based prompt management, similar block concept

**Nvim + LLM integration:**
- Existing nvim LLM plugins (avante.nvim, codecompanion.nvim, llm.nvim) - study their approaches, don't necessarily use them
- Tim Pope's plugin design philosophy - minimal, composable

**Implementation friction I can anticipate:**

1. **Block granularity decisions** - What's a block? How big? When to split? This is the #1 friction point. Too granular = overhead. Too coarse = no reuse. The answer: start with the reuse patterns you already have. If you're copy-pasting a system instruction, that's a block. If you're copy-pasting an output format constraint, that's a block. Don't decompose further until you need to.

2. **ID strategy** - Content-hash vs UUID vs human-readable names. Content-hash is elegant but means any edit creates a new block. UUID is stable but opaque. Human-readable names are fragile but useful. Best approach: human-readable slug as primary key, content-hash as integrity check. You want to be able to say `blocks/json_output_format` not `blocks/a7f3b2c1`.

3. **Storage format** - JSON, YAML, TOML, EDN, SQLite. For a personal project with git versioning, flat files win. YAML for prompts (human-readable, supports multiline strings), JSON for API payloads (native format), SQLite only if you need querying beyond grep.

4. **Template engine** - Parameterized blocks need variable substitution. Don't build a template engine. Use an existing one (Mustache, Jinja2, or even simple string interpolation). The template syntax should be the simplest thing that works.

5. **Versioning** - Git already versions files. Don't build a versioning system. Use git commits. If you need to track which version of a block was used in a specific thread, store the content-hash of the block at call-time in the turn record. That's enough to reconstruct.

6. **Metadata creep** - The temptation to add fields to block metadata is strong (tags, ratings, model affinities, usage counts, lineage, created_at, updated_at...). Start with: id, kind, content, parameters, tags. Add fields when you catch yourself wanting to query by a dimension you can't.

7. **Assembly complexity** - The assembly policy is the hardest part to implement well. Start with the simplest policy: "concatenate system blocks + full history." Add sliding window when you hit context limits. Add summarization when sliding window loses important context. Don't build a policy engine - build three specific functions and pick one per thread.

8. **Nvim buffer  block mapping** - How does the nvim conversation buffer relate to the block system? The buffer IS a prompt assembled from blocks, rendered to markdown. The parser converts the buffer back to API payload format. The block system lives underneath; the buffer is a view. This separation matters - don't couple them.

**Veteran advice:**

1. **The filesystem IS your database.** For a personal project, `~/prompts/blocks/`, `~/prompts/composed/`, `~/threads/` is a better starting point than SQLite. You can grep, diff, version with git, edit with nvim. When this breaks down (and it might not), migrate to SQLite.

2. **Don't abstract the API client.** Write a function that takes a map and POSTs it. Don't build a "provider-agnostic LLM interface." When you need a second provider, write a second function. Factor common patterns only after you see them.

3. **Log everything.** Every API call: full request, full response, timestamps, token counts, cost. You will want this data later and you can't reconstruct it. Disk is cheap. Store the raw JSON.

4. **Build the tools you actually use.** If you're not going to A/B test prompts, don't build A/B testing infrastructure. If you're not going to track lineage, don't track lineage. Let your actual workflow dictate features.

5. **The block system is a library, not a framework.** It's functions you call, not a runtime that calls you. You should be able to use blocks in a one-off script without importing the full system.

Let me search for the specific tools and resources worth mentioning.
</thinking>Good. Here's the full picture - resources, friction map, and veteran advice.

---

## Resources

**Study, don't adopt.** Read these to steal ideas and understand design tradeoffs. Do not adopt any of these as dependencies - they are reference material, not foundations for your project.

### Data-Oriented Programming

Yehonathan Sharvit's *Data-Oriented Programming* (Manning) is the foundational text. Four principles: separate code from data, represent data with generic structures, data is immutable, separate data schema from data representation. The book uses JavaScript examples but the principles are language-agnostic. If you've internalized DOP already, skim Part 1 and focus on Part 2 (implementation) and Part 3 (evolution - writing your own data manipulation toolset, specifying data shapes).

**Rich Hickey talks** - watch three in this order: "The Value of Values" (why immutable data), "Simple Made Easy" (complecting vs composing), "Maybe Not" (schema design without rigidity). These are the philosophical backbone of everything in the block-based design. Free on YouTube; each is ~40 minutes.

### Existing LLM CLI Tools

**Simon Willison's `llm`** - a CLI tool and Python library for interacting with LLMs from multiple providers, both remote APIs and local models. The most relevant reference for your project. Study three specific design decisions:

1. `llm` automatically stores all results in a SQLite database - this is the "log everything" principle implemented. You get queryable history for free.
2. The template system allows saving and reusing prompts - this is a simple version of the block concept. Templates are YAML files with system prompts and variable interpolation.
3. LLM 0.26 added tool support - you can define tools as Python functions or bundle them in plugins. This shows how tool use integrates into a CLI-first workflow.

**Don't adopt `llm` as a dependency.** Study its storage schema, template format, and plugin architecture. Then build your own with the data shapes you've already designed. Your prompt-as-composed-blocks model is more sophisticated than `llm`'s flat templates - you'd be constrained by its abstractions.

**Fabric by Daniel Miessler** - an AI orchestration framework that organizes prompts into reusable, version-controlled patterns that encapsulate specific tasks. Patterns are markdown files developed to provide detailed descriptions of what each pattern should do. Fabric's "patterns" are close to your "blocks" - reusable prompt fragments stored as files, composable via CLI piping. Fabric also supports "stitches" which chain multiple patterns together into a single automated pipeline.

Study Fabric's pattern directory structure and its stitching mechanism. These solve two problems you'll face: how to organize blocks on disk, and how to chain them. The pattern library itself (140+ patterns) is also a source of well-crafted prompt blocks you can decompose and study.

### Nvim + LLM Integration

**CodeCompanion.nvim** - the chat interaction harnesses a buffer to allow direct conversation with the LLM. The inline interaction allows for output from the LLM to be written directly into a pre-existing Neovim buffer. This is the closest existing implementation to your conversation-as-buffer concept. The debug window (`gd`) allows the user to see the full contents of the messages table which will be sent to the LLM on the next turn. The message history can be modified in the debug window. This is the "own your data" principle in action - you can see and edit the actual API payload. Study CodeCompanion's chat buffer design before building your own.

**Magenta.nvim** - a tool-use-focused LLM plugin with a VDOM-like system for rendering text into a buffer, making view code declarative. It exposes raw tool use requests and responses, as well as stop reasons and usage info from interactions with each model. More experimental than CodeCompanion, but its architecture of exposing raw API data aligns with your DOP approach.

Avante is the right tool when you want to see a diff before touching your buffer. CodeCompanion is better for in-flow questions - the @lsp and @buffers context variables are useful. Both are worth installing to feel the interaction patterns before building your own buffer format.

---

## Friction Map

Anticipated friction points, ordered by when you'll hit them. Each includes the friction, why it happens, and a tactic to reduce it.

### 1. Block granularity

**The friction:** "Is this one block or three?" You'll agonize over whether a system prompt should be one block or decomposed into persona + instructions + format constraints. Every decomposition choice is a bet on future reuse that you can't verify yet.

**Why it happens:** DOP says "let the data guide the code," but early on you have limited data about your own reuse patterns.

**Tactic:** Start coarse. One block per natural unit - "the system prompt I use for code review" is one block, even if it contains persona, instructions, and format. Split only when you find yourself wanting to reuse a sub-part independently. Keep a simple log of every time you copy-paste part of a block into another. When the log shows three copy-pastes of the same fragment, that fragment becomes its own block. The log is your data; let it guide the split.

### 2. ID and naming strategy

**The friction:** Content-hashing gives you integrity but means every edit creates a new ID. UUIDs are stable but opaque. Human-readable slugs collide and drift from content.

**Tactic:** Use human-readable slugs as primary identifiers (`json-output-format`, `code-review-system`). Store a content-hash alongside as an integrity/versioning check, not as the primary key. You want to say `blocks/json-output-format`, not `blocks/a7f3b2c1`. When you need to know if a block changed, compare hashes. When you need to find a block, use the slug. Git handles the version history.

### 3. Template variable syntax

**The friction:** You need parameterized blocks (`"Respond in {{format}} format"`), which means choosing a template syntax, a substitution engine, and handling edge cases (what if the variable isn't provided? what if the content contains the delimiter?).

**Tactic:** Use the simplest substitution that works. Double-brace `{{variable}}` with Python's `str.replace` or equivalent. Don't import Jinja2 or Mustache until you need conditionals or loops inside templates - and you probably won't. If a variable is missing, fail loudly with a clear error naming the missing variable. Don't silently leave the `{{placeholder}}` in the output.

### 4. Assembly policy complexity

**The friction:** The assembly policy (how to construct the next API payload from thread history) is the hardest part of the veteran model. Full history works until it doesn't. Sliding window loses important context. Summarization requires an extra LLM call. Relevance selection requires embeddings.

**Tactic:** Build three concrete functions, not a policy engine:

```
assemble_full(thread)            all messages, no truncation
assemble_window(thread, n)       system blocks + last n turns
assemble_truncate(thread, max)   system blocks + as many recent turns as fit in max tokens
```

Pick one per thread. Hardcode the choice. Don't build a policy configuration system until you have three threads that each need different strategies and you're tired of editing the function call manually. The "policy" concept from the veteran design is the destination, not the starting point.

### 5. Storage format transition

**The friction:** You start with flat files (YAML/JSON), which is correct. At some point - probably around 100+ blocks - `grep` stops being sufficient for retrieval. You feel the pull toward SQLite or a database.

**Tactic:** Delay the transition by making your file-based storage queryable. A manifest file (`blocks/index.yaml`) that lists every block's slug, kind, and tags gives you structured search without a database. Regenerate the manifest from the filesystem with a script. When the manifest approach breaks (complex queries, cross-referencing blocks with thread outcomes, performance), migrate to SQLite. The migration is a one-time script that reads your existing files - no data loss, no format change in the blocks themselves.

### 6. Nvim buffer  block mapping

**The friction:** The nvim conversation buffer is a view rendered from composed blocks. But you'll want to edit the buffer directly (it's nvim - of course you will). Now the buffer's content has diverged from the block composition. Which is authoritative?

**Tactic:** The buffer is authoritative during a conversation. The block system feeds into buffer creation (composing the initial prompt) but doesn't own the buffer's content once the conversation starts. Think of blocks as ingredients and the buffer as the cooked dish - you don't decompose the dish back into ingredients after cooking. If you edit the buffer, the edit stands. If you want to extract a reusable block from a conversation, do it explicitly with a command (`:ExtractBlock` or equivalent) that pulls a selection into a new block file.

### 7. Metadata creep

**The friction:** Every week you'll want one more field on blocks: tags, then ratings, then model affinities, then usage counts, then lineage, then performance notes, then cost tracking...

**Tactic:** Start with four fields: `id`, `kind`, `content`, `tags`. Add a field only when you catch yourself wanting to query or filter by a dimension you can't. Write down each time you wanted a field you didn't have. After a month, review the list. Add the fields that appeared three or more times. Discard the rest. Your usage log is, again, the data that guides the code.

---

## Veteran Advice

**The filesystem is your database.** `~/llm/blocks/`, `~/llm/threads/`, `~/llm/pipelines/`. Git provides versioning. `grep` and `find` provide search. A manifest file provides structured queries. These tools are free and proven. SQLite is the first upgrade when they fail - not Postgres, not a custom database, not an ORM.

**Log every API call in full.** Request payload, response body, timestamps, token counts, model ID, latency, cost. Store raw JSON. Disk is cheap. You will want this data six months from now for questions you can't anticipate today. Simon Willison's `llm` logs to SQLite automatically - this is the single best feature to steal from that project.

**Don't abstract the API client.** Write a function that takes a map and POSTs it. When you need a second provider, write a second function. Factor common patterns after you see them, not before. "Provider-agnostic LLM interface" is the abstraction that every framework builds and every user regrets. Your data shapes (prompt map, response map) already provide the abstraction - the API call is just plumbing.

**Build tools you actually use every day.** If you're not A/B testing prompts this week, don't build A/B testing infrastructure. If you're not tracking block lineage this week, don't track lineage. Build the thing you'll use tomorrow. The veteran model describes the destination; you reach it by building only what each day demands.

**Study CodeCompanion's buffer, then build your own.** CodeCompanion already solved the conversation-as-buffer problem with good engineering. Install it, use it for a week, pay attention to where it constrains you. Your custom buffer format should solve those constraints. Building from scratch without studying existing solutions means re-discovering problems they already solved.

**The block system is a library, not a framework.** You should be able to call `compose_prompt(blocks, bindings)` from a one-off script without importing the entire system. If using a single block requires initializing a registry, loading config, and connecting to storage - you've built a framework. Frameworks call you; libraries serve you. For a personal project, every line of framework code is debt.

**Version blocks through git, not through a custom system.** Git already tracks who changed what, when, and why. Don't build a `version: int` field with increment logic. If you need to know which version of a block was used in a specific thread, store the block's content-hash in the turn record at call-time. That's one field, computed once, and it gives you perfect reconstruction.

Category: [project_management] | Keywords: [llm_toolkit, block_system, friction_reduction, data_oriented_programming, nvim, resource_guide, veteran_advice]
