# THREAD BRANCHES - CRITICAL PATH (Revised)

This thread produced design, methodology, strategy, and data modeling across multiple domains. Below are the follow-up threads, topologically sorted by dependency, incorporating the full scope: working points, graph evolution, typed composition, and knowledge consolidation workflow.

---

## DEPENDENCY GRAPH

```
[A] Context consolidation (multi-pass funnel)
 ³
 ÃÄÄ [B] Schema + core module (WP1-WP2)
 ³     ³
 ³     ÃÄÄ [C] Scripts (fan-out, pipeline, loop)
 ³     ³     ³
 ³     ³     ÀÄÄ [F] Prompt management + telescope (WP3)
 ³     ³
 ³     ÃÄÄ [D] Nvim conversation-as-buffer
 ³     ³     ³
 ³     ³     ÀÄÄ [F] Prompt management + telescope (WP3)
 ³     ³
 ³     ÀÄÄ [E] Import pipeline (weekly cadence)
 ³
 ³   [F] Prompt management + telescope (WP3)
 ³     ³
 ³     ÃÄÄ [I] Typed composition + validation (WP3+)
 ³     ³
 ³     ÃÄÄ [J] Extracts + lineage (WP4-WP5)
 ³     ³     ³
 ³     ³     ÀÄÄ [K] Knowledge graph / edges (WP6)
 ³     ³
 ³     ÀÄÄ - [G] TUI (hobby, experiential dep on F)
 ³
 [H] Prompt engineering methodology (independent, ongoing)
```

---

## [A] CONTEXT CONSOLIDATION

**Purpose:** Funnel fragmented threads from prior LLM codebase work into a single unified context document. This document becomes the shared reference for all branches.

**Process:** Multi-pass reduction. The user runs the context collector on batches of 3-4 threads, producing intermediate context documents. Intermediate documents are then consolidated in a second pass (or third if needed) until one document remains.

**Bring:**
- Consolidation Funnel prompt (below)
- Prior conversation transcripts (exported or copy-pasted)
- Context from this thread (the project handoff, veteran design guide, and this branch plan)

**Depends on:** Nothing.

**Unblocks:** Everything.

**Scope:** Multiple short sessions. One batch of 3-4 threads per session. Then one consolidation session per 3-4 intermediate documents. Estimate: if you have 12 prior threads, that's 3 batch sessions  3 intermediate docs  1 consolidation session  1 final document.

**Completion criteria:** A single context document exists that covers all prior design decisions, code, data models, and insights about the LLM toolkit. A fresh thread can read it and proceed without asking what was already decided.

---

## [B] SCHEMA + CORE MODULE (WP1-WP2)

**Purpose:** Create the SQLite database and implement foundational functions. Targets Working Points 1 and 2: store-and-call, then search-and-annotate.

**Bring:**
- Final consolidated context document from [A]
- Schema from this thread (six core tables + FTS + scaffolded nullable columns for future WPs)
- Ten most-wanted queries (write at session start as schema validation)
- Working point definitions: WP1 = call + store turns, WP2 = FTS search + annotations

**Depends on:** [A].

**Unblocks:** [C], [D], [E].

**Scope:** 1-2 sessions.

**Scaffolding to include:**
- `turns.prompt_hash` (nullable) - activated at WP3
- `turns.quality`, `turns.notes` (nullable) - activated at WP2
- `blocks.parent_hash` (nullable) - activated at WP5
- `blocks.param_types` (nullable JSON) - activated at WP3+ for typed composition

**Completion criteria:**
- WP1: `call_llm` returns a response, turn stored in SQLite, round-trip verified.
- WP2: `search_turns` returns results via FTS5, `annotate_turn` updates quality/notes.

**Feedback gate  WP3:** Am I copy-pasting the same system instructions across calls?

---

## [C] SCRIPTS

**Purpose:** Build four script patterns: fan-out, fan-in, pipeline, loop.

**Bring:** Context document from [A], core module from [B].

**Depends on:** [B] (WP1 minimum).

**Unblocks:** [F] (reveals reuse patterns). Generates first real usage data.

**Scope:** 2 sessions for all four.

**Order:** Fan-out  pipeline  fan-in  loop.

**Completion criteria:** Each script processes real files, all calls logged in SQLite with full payloads.

---

## [D] NVIM CONVERSATION-AS-BUFFER

**Purpose:** Buffer format, parser, send/receive, payload preview split with token estimate.

**Bring:** Context document from [A], core module from [B], two-buffer design from this thread.

**Depends on:** [B] (WP1 minimum).

**Unblocks:** [F] (telescope picker is an nvim integration).

**Scope:** Multiple sessions. Decomposition:
1. Buffer format spec + 3 hand-written sample conversations
2. Parser (buffer  API payload) + serializer (response  buffer append)
3. Send keybind: parse  call_llm  save_turn  append
4. Payload preview split (read-only, with token estimate)
5. Payload preview writable mode (ephemeral overrides)

**Open GAPs:** Tool calls in buffer format, plugin architecture (Lua vs. external process), context window truncation UI.

**Completion criteria:** Write `## user` message, keybind, `## assistant` appears. Turn stored. Payload preview visible in split.

---

## [E] IMPORT PIPELINE

**Purpose:** Per-provider import scripts. One per week.

**Bring:** Context document from [A], core module from [B], provider export files.

**Depends on:** [B] (WP1 minimum).

**Unblocks:** Historical data for search and analysis.

**Scope:** 1 session per provider. Weekly cadence.

**Order:** Claude  OpenAI  others.

**Completion criteria per provider:** Historical turns in SQLite, queryable. High-value artifacts saved as files.

---

## [F] PROMPT MANAGEMENT + TELESCOPE (WP3)

**Purpose:** Block CRUD, prompt composition, telescope picker for block search.

**Bring:** Context document from [A], core module from [B], reuse patterns from [C] and [D].

**Depends on:** [B] (schema). Experiential dependency on [C] and [D] - build this when copy-paste friction fires.

**Unblocks:** [I] (typed composition), [J] (extracts), [G] (TUI benefits from blocks).

**Scope:** Multiple sessions. Decomposition:
1. Block CRUD: `create_block`, `revise_block`, `search_blocks`
2. Prompt composition: `assemble_prompt` with template expansion
3. Telescope picker: fuzzy search blocks, insert reference
4. Migration: extract repeated instructions from scripts/conversations into blocks

**Completion criteria:** Keybind  search blocks  select  insert reference. Prompts assembled from blocks produce correct API payloads. `turns.prompt_hash` populated for new calls.

**Feedback gate  WP3+:** Am I putting the wrong value into a template slot? Am I wanting to validate that a prompt has all required block kinds?

---

## [I] TYPED COMPOSITION + VALIDATION (WP3+)

**Purpose:** Add type checking to block composition. Typed template parameters, composition validation rules, functional annotations on blocks.

**Bring:** Block system from [F], typed composition design from this thread (term algebra, AST perspective).

**Depends on:** [F]. Build when composition errors motivate it.

**Scope:** 1-2 sessions.

**What to build:**
1. Typed parameters: `param_types` field on blocks - `{name, type, allowed_values}`
2. Composition validator: prompt must have ò1 system/instruction block, ó1 input block, constraints before input
3. Assembly-time validation: reject prompts with unfilled required slots or type-mismatched bindings
4. Optional: `function` annotation field on blocks - what the block does to model behavior

**Completion criteria:** `assemble_prompt` rejects a prompt with an unfilled required slot. Telescope picker shows valid completions for typed parameter slots.

**Design references from this thread:** term algebras, algebraic data types, linguistic pragmatic layer, operad-like composition typing.

---

## [J] EXTRACTS + LINEAGE (WP4-WP5)

**Purpose:** Knowledge extraction from threads + block version history.

**Bring:** Core module from [B], block system from [F], context collector prompt.

**Depends on:** [F] (blocks must exist for lineage to be meaningful).

**Unblocks:** [K] (extracts become graph nodes).

**Scope:** 1-2 sessions.

**What to build:**
- WP4: `create_extract`, `search_extracts`, manual extraction workflow
- WP5: `revise_block` activates `parent_hash`, `block_history` query

**Completion criteria:** Extracts stored and searchable. Block revision creates new row with lineage pointer. `block_history("json_format")` returns ordered version list.

---

## [K] KNOWLEDGE GRAPH / EDGES (WP6)

**Purpose:** Typed relationships between any entities. The content-addressable store becomes a knowledge graph.

**Bring:** Everything from [B] through [J]. Edge table design and starter relation vocabulary from this thread.

**Depends on:** [J] (extracts and lineage should exist as nodes before adding edges between them).

**Unblocks:** Cross-entity queries, cluster discovery, "why was this revised?" provenance.

**Scope:** 1 session for schema + CRUD. Ongoing for edge creation.

**What to build:**
1. `edges` table with typed relations
2. `add_edge`, `edges_from`, `edges_to`, `related` functions
3. Start with three relation types: `related_to`, `motivated_by`, `supersedes`

**Completion criteria:** Can express "block X was revised because of annotation on turn Y." Can query "everything related to authentication" across entity types.

---

## [G] TUI (hobby)

**Purpose:** Interactive terminal interface.

**Depends on:** [B] minimally. Benefits from [F].

**Unblocks:** Nothing.

**Scope:** Open-ended.

**Design note:** Should reflect deanthropomorphized philosophy - structured payload editor, not chat messenger.

---

## [H] PROMPT ENGINEERING METHODOLOGY (independent)

**Purpose:** Refine and test processing protocol, prompt transformer, refinement imperatives.

**Depends on:** Nothing.

**Unblocks:** Better prompts across all workstreams. Methodology artifacts become blocks when [F] is built.

**Key open items:** Test lean protocol on two models. Test prompt transformer on diverse inputs. Validate five-case test methodology.

---

## EXECUTION TIMELINE

```
Week 1:      [A] Context consolidation (2-3 batch sessions + 1 consolidation)
Week 1-2:    [B] Schema + core module (WP1-WP2)
Week 2-3:    [C] Scripts (fan-out, pipeline, fan-in, loop)
Week 3+:     [D] Nvim buffer format + send/receive
Weekly:      [E] Import one provider
When ready:  [F] Prompt management (after friction from C and D)
After F:     [I] Typed composition (after composition errors motivate it)
After F:     [J] Extracts + lineage
After J:     [K] Knowledge graph / edges
Anytime:     [G] TUI, [H] Methodology
```

## CROSS-BRANCH RISKS

| Risk | Branches involved |
|------|------------------|
| Buffer format design in [D] depends on the prompt data structure from [B]. If [B]'s structure changes, [D]'s parser breaks. | [B]  [D] |
| Telescope picker in [F] needs nvim integration from [D]. Build [F]'s search functions independently; wire to telescope after [D] is stable. | [D]  [F] |
| Typed composition in [I] may want schema changes to `blocks`. Scaffold `param_types` column at [B] to avoid migration. | [B]  [I] |
| Edge creation in [K] depends on having enough entities to connect. If [J] (extracts) is sparse, edges add little value. Wait for 30+ extracts. | [J]  [K] |
