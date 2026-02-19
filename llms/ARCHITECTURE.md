# Architecture

Personal CLI tool for importing, indexing, and searching LLM conversation history across providers. Single-file Python script backed by SQLite with FTS5 full-text search.

## Environment

- Linux, Python 3.12 via `uv run`, SQLite 3.37.2
- Standard library only - no external packages
- PEP 723 inline metadata in script shebang

## File layout

```
llms/
 llm.py                 # CLI entry point - all logic in one file
 llm.db                 # SQLite database (disposable, not committed)
 schema.sql             # Canonical schema - source of truth for DB structure
 ARCHITECTURE.md        # This file
 FRICTION.md            # Qualitative usage notes (created after first real use)
 raw/                   # Provider exports (not committed)
     claude/conversations.json
     chatgpt/conversations.json
     deepseek/conversations.json
     qwen/chat-export-*.json
```

## Code style

Flat procedural layout: constants at top, argparse next, inline dispatch. No classes, no unnecessary wrapper functions. Provider-specific logic lives in `if/elif` blocks within the import dispatch. This optimizes for top-to-bottom readability over abstraction.

## Schema overview

Five tables, two FTS virtual tables:

**`conversations`** - One row per conversation per provider. Groups messages. Deduped on `(provider, source_conversation_id)`.

**`messages`** - Individual messages. Linked to conversations via `conversation_id` FK. Deduped on `(provider, source_conversation_id, position, content)`. The `position` field is the original array index (or tree-walk order for tree-structured providers), preserving source ordering. Provider and source_conversation_id are denormalized onto messages alongside the FK to avoid joins on common queries like "all claude messages."

**`messages_fts`** - FTS5 virtual table over `messages.content`. Kept in sync by insert/delete triggers. (Update trigger not yet added - not needed while DB is disposable.)

**`prompts`** / **`prompts_fts`** - Prompt catalog with versioning and FTS. Schema exists but no features use it yet.

**`metadata`** - Key-value store. Currently holds `schema_version`.

**`access_log`** - Command invocation log for tracking usage patterns. Schema exists, not yet wired up.

## Import pipeline

```
raw JSON  provider-specific parser  INSERT OR IGNORE  conversations + messages
```

Each provider has its own parsing logic selected by `--provider` flag. All providers follow the same contract: read the export, iterate conversations, iterate messages, normalize to `(provider, role, content, position, created_at)`, insert with dedup.

**Role normalization** - All providers map to: `human`, `assistant`, `system`, `tool`.

**Timestamp normalization** - All `created_at` values stored as ISO 8601 strings. Providers using Unix timestamps (ChatGPT) must convert during import.

**Idempotency** - `INSERT OR IGNORE` against unique indexes. Reimporting the same file is a no-op.

### Provider status

| Provider | Status | Structure | Notes |
|----------|--------|-----------|-------|
| Claude | **Done** | Flat array | 860 convs, 9,057 msgs imported. 220 empty-text msgs skipped. |
| ChatGPT | Stubbed | Tree (`mapping`) | Shares tree format with DeepSeek. 144 convs, ~2,357 nodes. 293 system messages (likely duplicates - inspect before import). |
| DeepSeek | Stubbed | Tree (`mapping`) | 199 convs, ~1,866 nodes. Fragments (THINK/SEARCH/RESPONSE) concatenated with XML-style tags. |
| Qwen | Stubbed | Flat + `content_list` | 78 convs. Assistant content in `content_list[phase=="answer"].content`. |

### Tree linearization (ChatGPT, DeepSeek)

Both use identical `mapping` objects: nodes with `id`, `parent`, `children`, `message`. Design decision pending: import tree faithfully using `parent_message_id` (recommended - no duplication, schema supports it) vs. expand branches into separate conversations (simpler queries, duplicates shared prefixes). Claude exports flatten branches in the export itself, so this only applies to ChatGPT and DeepSeek.

## Design decisions

**Disposable-cache database.** Until features exist that write data not derived from raw exports (annotations, tags, manual prompt entries), the rebuild strategy is: `rm llm.db && uv run llm.py init && uv run llm.py import ...`. No migration files. Schema changes go directly into `schema.sql` and the DB is recreated. This makes schema evolution zero-risk.

**Denormalized provider/source IDs on messages.** `provider` and `source_conversation_id` exist on both `conversations` and `messages`. The FK (`conversation_id`) is the canonical link, but the denormalized fields avoid a join for common filtered queries. Worth the minor redundancy for a search tool.

**`position` is source-relative, not dense.** If messages are skipped during import (empty text), position still reflects the original array index. This preserves alignment with the source export for debugging.

**Standard library only.** No dependency management, no venv, no version conflicts. `uv run` with zero deps.

**WAL journal mode.** Set on every connection for concurrent read/write performance.

## Known limitations

**Claude `content` array not imported.** The import reads `text` (plain message body) but not `content` (structured array with tool_use/tool_result pairs). This means 837 artifacts, 147 web searches, and 61 thinking blocks are in the raw export but not in the database. The data includes full artifact text, MIME types, language, titles, and version UUIDs. A future extraction pass - likely a dedicated `artifacts` or `content_blocks` table - can capture this. The raw export preserves everything, and the disposable-cache property makes this a schema change + reimport.

**No FTS update trigger.** Insert and delete triggers exist; update does not. Not needed while the DB is disposable and content is never modified in place.

**Dedup index stores full content.** `idx_dedup` includes the `content` column, storing message text twice (table + B-tree). A planned improvement replaces `content` with `content_hash` (SHA-256) in the index.

**No read-path indexes beyond dedup.** Indexes for search/retrieval queries (by provider, by conversation, by date) will be added based on actual query patterns from `EXPLAIN QUERY PLAN`, not speculatively.

## Roadmap

**Phase 1 - Foundation** ?
Schema, Claude import, import pipeline proven.

**Phase 2 - Core read path**  current
`search`, `show`, `list` subcommands. Wire up `access_log`. Write `FRICTION.md` after first real use session.

**Phase 3 - Remaining providers**
ChatGPT + DeepSeek (shared tree walker). Qwen (content_list extraction).

**Phase 4 - Refinement (friction-log driven)**
Search filters, output formatting, content_hash dedup, read-path indexes, Claude content-array extraction.

**Phase 5 - Prompts and user-generated data**
Prompt catalog features. This is where the disposable-cache property ends - plan carefully.
