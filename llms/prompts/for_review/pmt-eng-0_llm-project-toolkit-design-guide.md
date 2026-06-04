# VETERAN PROMPT MANAGEMENT - DESIGN GUIDE

For a personal LLM toolkit built in Python with nvim as the primary interface. No outside libraries except stdlib, fzf, and telescope. Sequencing: simple scripts  nvim conversation-as-buffer  prompt management system  TUI (hobby).

---

## 1. WHY THE VETERAN APPROACH NOW

The triggers defined in the prior design work have already fired:

- You manage many threads and prompts across conversations.
- You copy-paste system instructions between prompts.
- You cannot search for "the prompt fragment that produces structured JSON."
- You want to compose, version, and compare prompts programmatically.

The simple file-per-prompt model is already failing you. The block-based composition model addresses these failures directly. Building it will take more effort upfront; the payoff is that every subsequent prompt interaction becomes faster, searchable, composable, and auditable.

---

## 2. STDLIB MAP - WHAT YOU ALREADY HAVE

Every capability the veteran model requires exists in Python's standard library.

| Need | Stdlib module | Notes |
|------|--------------|-------|
| Block storage and retrieval | `sqlite3` | Ships with Python. Single-file database. Structured queries, full-text search (FTS5). No server, no setup. This is your primary storage backend. |
| Content hashing | `hashlib` | SHA-256 of block content gives content-addressable IDs. Deterministic, deduplicating. Git uses this model. |
| Template expansion | `string.Template` or `str.format` | Named slots with `${variable}` or `{variable}`. No Jinja2 needed for personal use. |
| Date and time | `datetime`, `zoneinfo` | `zoneinfo` is stdlib since 3.9. Covers timezone-aware timestamps. |
| JSON serialization | `json` | Prompts, responses, and API payloads are JSON. |
| HTTP requests | `urllib.request` | Stdlib. Works for API calls. If you already use `requests` or `httpx`, those are fine - they're high-value dependencies that earn their place. |
| File I/O and paths | `pathlib` | Clean path manipulation, glob patterns, directory traversal. |
| CLI argument parsing | `argparse` | Sufficient for scripts and pipeline runners. |
| UUID generation | `uuid` | For IDs where content-hashing isn't applicable (threads, turns). |
| Text search | `sqlite3` FTS5 | Full-text search over block content and metadata. Built into SQLite. |
| Subprocess / nvim integration | `subprocess`, `json` (for RPC) | Nvim's `--headless` mode and RPC interface. |

You do not need: an ORM, a migration framework, a template engine, a web framework, a CLI framework, or a database server.

---

## 3. THE DATA MODEL

### Blocks

A block is the atom. It carries one functional role in a prompt.

```sql
CREATE TABLE blocks (
    id          TEXT PRIMARY KEY,   -- SHA-256 of content, or UUID
    name        TEXT NOT NULL,      -- human-readable, searchable ("json_output_format")
    kind        TEXT NOT NULL,      -- system | instruction | context | input | exemplar | constraint | persona
    content     TEXT NOT NULL,      -- the actual text
    parameters  TEXT,               -- JSON list of slot names: ["format", "language"]
    parent_id   TEXT,               -- lineage: which block this was derived from
    created_at  TEXT NOT NULL,      -- ISO 8601
    tags        TEXT,               -- JSON list of flat strings: ["output", "json", "strict"]
    notes       TEXT                -- freeform: why this block exists, what it's for
);

CREATE VIRTUAL TABLE blocks_fts USING fts5(name, content, tags, notes);
```

Design decisions embedded in this schema:

**`id` is a content hash.** SHA-256 of the `content` field. Identical content produces identical IDs - deduplication is automatic. Editing a block creates a NEW row with a new hash. The old block persists. This is immutability by construction, not by discipline.

**`name` is a human label, not a unique key.** Multiple blocks can share a name - they are versions of the same logical block. "Latest version" is `SELECT * FROM blocks WHERE name = ? ORDER BY created_at DESC LIMIT 1`. This is Git's model: names (refs) point to hashes (objects). Names move; hashes don't.

**`kind` is a flat enum, not a hierarchy.** Seven kinds cover the functional roles in prompt composition. Each kind occupies a conventional position in the assembled prompt (system first, input last). The enum is a suggestion, not a constraint - add kinds as new patterns emerge.

**`parameters` is a JSON list of slot names.** A block with `["format"]` in its parameters contains `{format}` in its content. Bindings are supplied at composition time. No type system for parameters - strings in, strings out. Add typing only when a bug convinces you it's needed.

**`parent_id` enables lineage.** When you revise a block, the new block points to the old one. You can trace the evolution of any block through its lineage chain. You can answer "what did this block look like three iterations ago?"

**`tags` are flat strings in a JSON list.** No tag hierarchy, no tag table, no many-to-many join. Flat tags with FTS5 search cover the retrieval patterns that matter. If you need "all blocks tagged `output` and `json`," the FTS query handles it.

### Prompts

A prompt is a composition of blocks with bindings and a target configuration.

```sql
CREATE TABLE prompts (
    id          TEXT PRIMARY KEY,   -- SHA-256 of the composition (blocks + bindings + config)
    name        TEXT,               -- optional human label
    blocks      TEXT NOT NULL,      -- JSON: ordered list of {block_id, bindings: {slot: value}}
    config      TEXT NOT NULL,      -- JSON: {model, temperature, max_tokens, ...}
    resolved    TEXT,               -- cached: the flattened string after expansion
    created_at  TEXT NOT NULL,
    tags        TEXT,
    notes       TEXT
);
```

**`blocks` is an ordered list.** Order matters - system blocks first, input blocks last. Each entry references a block by ID and provides bindings for that block's parameters.

**`config` is co-located.** Model, temperature, and max_tokens are part of the prompt's identity. Different config on identical messages produces different outputs. The config travels with the composition.

**`resolved` is a derived cache.** Materialized by expanding templates and concatenating blocks. Regenerate it anytime from `blocks` + bindings. Never treat `resolved` as the source of truth.

### Threads and turns

```sql
CREATE TABLE threads (
    id          TEXT PRIMARY KEY,
    name        TEXT,
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    tags        TEXT,
    notes       TEXT
);

CREATE TABLE turns (
    id          TEXT PRIMARY KEY,
    thread_id   TEXT NOT NULL REFERENCES threads(id),
    index_num   INTEGER NOT NULL,
    prompt_id   TEXT REFERENCES prompts(id),
    request     TEXT NOT NULL,       -- JSON: full API payload (messages array)
    response    TEXT NOT NULL,       -- JSON: full API response
    input_tokens   INTEGER,
    output_tokens  INTEGER,
    latency_ms     INTEGER,
    model          TEXT,
    finish_reason  TEXT,
    annotations    TEXT,             -- JSON: {quality: rating, notes: string}
    created_at     TEXT NOT NULL
);
```

**Every turn stores the full request payload.** Not just the new message - the entire messages array that was sent to the API. This is expensive in storage; it is invaluable for debugging, cost analysis, and understanding what the model actually saw. Storage is cheap. Provenance is irreplaceable.

**`annotations` captures outcomes.** After you see a response, you can annotate it: quality rating, notes on what worked or failed. This links outcomes to specific block compositions, enabling "which blocks produce good results with this model?"

---

## 4. FRICTION POINTS AND PREEMPTIVE TACTICS

These are the points where implementation stalls or design regret accumulates. Each is drawn from the experience of building similar systems.

### Friction 1: Block granularity

**The problem.** Too fine-grained (every sentence is a block) and composition becomes tedious assembly of dozens of fragments. Too coarse (entire system prompts as blocks) and reusability vanishes.

**The tactic.** Each block performs one functional role in the prompt. A block answers one of these questions: "What persona should the model adopt?" (persona block). "What format should the output take?" (constraint block). "What task is being performed?" (instruction block). "What context does the model need?" (context block). If a block answers two questions, split it. If two blocks answer the same question, merge them.

**Expect this to be wrong initially.** Your first block decomposition will be too coarse. After a month of use, you'll notice that one "system instruction" block is actually doing three things. Split it then - not now. Let friction guide granularity.

### Friction 2: The ID scheme tension

**The problem.** Content-hash IDs guarantee immutability and deduplication. But editing a block creates a new ID, breaking references from existing prompts. UUID-based IDs allow mutation but lose content-addressability.

**The tactic.** Use content hashes for block IDs. Use `name` + `latest` queries for mutable references. When building a prompt interactively, reference blocks by name (resolved to latest hash at composition time). When storing a prompt for reproducibility, pin the specific hash. This is Git's model: branches (names) for convenience, commit hashes for precision.

**The function you'll write early:**
```python
def resolve_block(name: str, version: str = "latest") -> dict:
    """Resolve a block name to a specific block record."""
    if version == "latest":
        return db.execute(
            "SELECT * FROM blocks WHERE name = ? ORDER BY created_at DESC LIMIT 1",
            (name,)
        ).fetchone()
    else:
        return db.execute("SELECT * FROM blocks WHERE id = ?", (version,)).fetchone()
```

### Friction 3: Composition becomes boilerplate

**The problem.** Assembling a prompt from blocks requires writing the same composition logic repeatedly: resolve blocks, expand templates, concatenate, attach config.

**The tactic.** Build one `assemble_prompt` function early and never duplicate it. This function is the core of the entire system:

```python
def assemble_prompt(block_specs: list[dict], config: dict) -> dict:
    """
    block_specs: [{"name": "json_format", "bindings": {"format": "json"}}, ...]
    Returns: {"messages": [...], "config": {...}, "resolved": "..."}
    """
    messages = []
    for spec in block_specs:
        block = resolve_block(spec["name"])
        content = expand_template(block["content"], spec.get("bindings", {}))
        messages.append({"role": kind_to_role(block["kind"]), "content": content})
    resolved = "\n".join(m["content"] for m in messages)
    return {"messages": messages, "config": config, "resolved": resolved}
```

Everything else calls this function. The scripts call it. The nvim plugin calls it. The pipeline runner calls it.

### Friction 4: Search that actually works

**The problem.** You have 200 blocks. You need the one that constrains output to valid Python. You remember writing it but not what you named it.

**The tactic.** FTS5 on SQLite handles this. Build the search early:

```python
def search_blocks(query: str) -> list[dict]:
    return db.execute(
        "SELECT * FROM blocks WHERE id IN (SELECT rowid FROM blocks_fts WHERE blocks_fts MATCH ?)",
        (query,)
    ).fetchall()
```

Wire this to telescope. A telescope picker that calls `search_blocks` and returns the selected block's name or ID gives you fuzzy search over your entire block library from inside nvim. This is where fzf and telescope earn their place - they are the browse-and-select UI for the block registry.

### Friction 5: Context window management

**The problem.** Multi-turn threads grow. The full message history eventually exceeds the model's context window. You need a truncation or summarization strategy.

**The tactic.** Defer this. For Steps 1-4 (scripts and pipelines), context windows are rarely an issue - single calls or short chains. For Step 5 (nvim buffer), start with "send everything." When you hit the limit, implement the simplest strategy: count tokens (use `tiktoken` if targeting OpenAI - this is a high-value dependency that earns its place; otherwise estimate at ~4 chars per token), truncate oldest messages first, keep system blocks intact. Do not build summarization until truncation fails you.

### Friction 6: The urge to abstract prematurely

**The problem.** After building the block system, you'll want to generalize: a provider-agnostic API layer, a plugin system for block types, a configuration DSL. Each abstraction adds complexity that a single-user personal tool does not need.

**The tactic.** Write concrete code for the models you use. If you use Claude and OpenAI, write two `call_llm` functions - `call_claude` and `call_openai`. When the third provider arrives, factor the common pattern. Not before. The DOP principle: let the data reveal the abstraction. Three concrete instances show you what's actually common; two instances show you what might be coincidence.

---

## 5. RESOURCES TO READ

Each resource is listed because it informs a specific design decision in this project. Read in this order - each builds on the prior.

### Rich Hickey - "The Value of Values" (talk, ~30 min)

**What it is.** A talk arguing that immutable values are fundamentally superior to mutable objects for representing information. "Place-oriented programming" (mutating a variable in place) conflates identity with state. Values are stable, shareable, and testable.

**Why it matters here.** The block model is a value-oriented design. A block is an immutable value identified by its content hash. Editing creates a new value with lineage to the old one. This talk provides the philosophical foundation for why the content-hash ID scheme is correct and why mutable block records would be a mistake. It also clarifies why `resolved` is a derived cache (a computed value), not a source of truth (a stored fact).

**Where to find it.** Search "Rich Hickey The Value of Values" - multiple conference recordings exist. The InfoQ version is cleanest.

### Rich Hickey - "Simple Made Easy" (talk, ~35 min)

**What it is.** A talk distinguishing "simple" (not interleaved, low complexity) from "easy" (familiar, close at hand). Objects are easy; data is simple. ORMs are easy; SQL is simple. The argument: choose simple over easy because simple systems compose and easy systems calcify.

**Why it matters here.** The decision to use raw SQL over an ORM, raw dicts over dataclasses-with-methods, and flat tags over a taxonomy - these are all "simple over easy" choices. This talk provides the reasoning framework for making those choices consistently and resisting the pull toward familiar but complecting abstractions.

**Where to find it.** Search "Rich Hickey Simple Made Easy." The Strange Loop 2011 recording is the original.

### Git's object model (documentation, ~1 hour reading)

**What it is.** Git's internals documentation describing how Git stores data: blobs (content), trees (compositions of blobs), commits (snapshots with parent pointers). Everything is content-addressed via SHA-1 hashes. Names (branches, tags) are mutable pointers to immutable objects.

**Why it matters here.** The block model IS Git's object model applied to prompts. Blocks are blobs. Prompts are trees. Versions are commits with parent lineage. The `name`-as-mutable-ref / `id`-as-immutable-hash split mirrors branches and commit hashes. Understanding Git internals gives you the mental model for the entire storage layer. It also answers design questions before they arise: "should IDs be mutable?" (no - Git proved this), "how do I handle versioning?" (lineage pointers), "how do I handle naming?" (refs that move).

**Where to find it.** `git-scm.com/book/en/v2/Git-Internals-Git-Objects`. Chapter 10 of Pro Git. Read sections on objects, refs, and packfiles.

### SQLite as an application file format (documentation, ~20 min)

**What it is.** SQLite's documentation page arguing that SQLite databases are a superior alternative to custom file formats, XML, JSON files, and ad-hoc serialization for application data storage.

**Why it matters here.** Validates the choice of SQLite over file-per-block or JSON manifests. A single `.db` file replaces an entire directory tree. It supports structured queries, full-text search, transactions, and concurrent reads. It requires no server, no configuration, and no dependencies beyond Python's stdlib. It is the correct storage backend for a personal tool - more powerful than files, simpler than a database server.

**Where to find it.** `sqlite.org/appfileformat.html`.

### FTS5 - SQLite Full-Text Search (documentation, ~30 min)

**What it is.** Documentation for SQLite's full-text search extension. FTS5 indexes text columns and supports ranked search queries, phrase matching, prefix matching, and Boolean operators.

**Why it matters here.** Block retrieval depends on search quality. FTS5 turns `search_blocks("output format json strict")` into a ranked query over all block content, names, tags, and notes - without any external search engine. Combined with telescope/fzf for fuzzy selection, FTS5 gives you the retrieval layer the veteran model requires.

**Where to find it.** `sqlite.org/fts5.html`.

### "Data-Oriented Programming" by Yehonathan Sharvit (book, selective chapters)

**What it is.** A book formalizing DOP as a paradigm: separate code from data, represent data with generic structures, treat data as immutable, separate data schema from data representation.

**Why it matters here.** Chapters 1-5 provide the formal principles underlying every design decision in this project. Chapter 6 (on managing state) is relevant to the thread model (append-only log of immutable turns). The rest of the book applies DOP to larger systems and is less directly relevant to a personal tool.

**Where to find it.** Published by Manning. Available in print and digital.

---

## 6. VETERAN ADVICE (FROM BUILDING SIMILAR SYSTEMS)

**Log everything.** Every API call, every response, every token count, every latency measurement, every error. Store it in the `turns` table. Storage costs nothing at personal scale. This data is irreplaceable - it tells you which prompts work, what things cost, where time goes, and how models behave over time. You will be grateful for this data in six months; you cannot reconstruct it retroactively.

**Name blocks by function, not by content.** `json_output_strict` is findable. `block_a7f3c2e8` is not. Content hashes are IDs for machines; human names are for you. Both exist in the schema for this reason.

**Build the telescope picker in week one of the nvim work.** Once blocks are in SQLite, the telescope picker becomes the primary interface for prompt composition. You search, you select, you insert. This single integration point makes the block library feel native to your editor rather than an external system you have to context-switch into.

**Do not build a query language.** You are the only user. Write raw SQL. Wrap frequent queries in Python functions (`search_blocks`, `latest_block`, `blocks_by_tag`). A custom query language is months of work for a single-user tool that already has SQL.

**Store prompts as compositions, not as resolved strings.** The resolved string is a view, not the data. When you store `[block_id_1, block_id_2, block_id_3]` plus bindings, you can reconstruct, diff, search, and recompose. When you store only the flattened text, you lose all structure. Every time you're tempted to "just save the string," remember: you can always render the composition to a string, but you cannot parse the string back into a composition.

**Version via append, not via update.** When you improve a block, `INSERT` a new row. Set `parent_id` to the old block's ID. Your "latest" query handles retrieval; your lineage chain handles history. Never `UPDATE` a block's content - that destroys the immutability guarantee and breaks any prompt that referenced the old hash. If the schema uses content-hash IDs, `UPDATE` is literally impossible without changing the primary key. The schema enforces the discipline.

**Annotations are the feedback loop.** After a response, annotate the turn: did it work? What was good? What failed? These annotations, linked to specific block compositions, are the training data for your own prompt engineering. Without them, you're optimizing by memory and intuition. With them, you can query: "show me all prompts using block X where quality was rated high."

**Resist the multi-provider abstraction until the third provider.** Write `call_claude()` and `call_openai()` as separate functions. They share nothing except "send JSON, get JSON back." The request shapes differ, the auth differs, the response shapes differ. An abstraction layer hides these differences and makes debugging harder. When the third provider arrives, the common pattern becomes visible and the abstraction writes itself.

---

## 7. IMPLEMENTATION SEQUENCE (Revised)

The original step ordering from the handoff stands, with the prompt management system promoted from "deferred" to "build after nvim basics."

| Phase | What | Depends on | Estimated effort |
|-------|------|-----------|-----------------|
| 1 | Core data shapes + single API call | Nothing | A few hours |
| 2 | Batch file processing script | Phase 1 | A day |
| 3 | Pipeline runner (chain calls) | Phase 1 | A day |
| 4 | Objective loop | Phase 1 | A day |
| 5a | Nvim buffer format + parser | Phase 1 | Several days |
| 5b | Nvim plugin (send/receive/append) | Phase 5a | Several days |
| 6a | SQLite schema + block CRUD | Phase 1 | A day |
| 6b | Block search (FTS5) | Phase 6a | A few hours |
| 6c | Telescope picker for blocks | Phase 6b + nvim | A day |
| 6d | Prompt composition from blocks | Phase 6a | A day |
| 6e | Thread storage + annotations | Phase 6d | A day |
| 7 | TUI (hobby, ongoing) | Phase 6 | Open-ended |

Phases 1-4 produce standalone tools. Phase 5 produces the nvim workflow. Phase 6 produces the prompt management system. Each phase delivers a usable capability - nothing is infrastructure-only.
