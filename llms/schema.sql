-- ============================================================
-- schema.sql - LLM conversation archive
-- ============================================================
-- Stores imported conversation threads from multiple LLM
-- providers (claude, chatgpt, deepseek, qwen) with full-text
-- search via FTS5. Deduplication is handled at the index level
-- so reimports are idempotent (INSERT OR IGNORE).
--
-- Timestamps: ISO 8601 strings, UTC where available.
-- Provider-specific unix timestamps are converted on import.
--
-- Versions:
--   1  Initial schema (messages, prompts, access_log, metadata)
--   2  Added conversations table; conversation_id FK on messages
-- ============================================================

-- ============================================================
-- conversations - one row per conversation per provider
-- ============================================================
-- Groups messages into their source conversation. Title and
-- summary are provider-supplied and may be NULL.
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,               -- claude | chatgpt | deepseek | qwen
    source_conversation_id TEXT NOT NULL,  -- provider's original ID (uuid or similar)
    title TEXT,                            -- provider-supplied conversation title
    summary TEXT,                          -- provider-supplied summary (claude only currently)
    created_at TEXT,                       -- conversation creation time (ISO 8601)
    updated_at TEXT,
    imported_at TEXT NOT NULL              -- when we ingested this record (ISO 8601)
);

-- Reimporting the same conversation from the same provider is a no-op.
CREATE UNIQUE INDEX idx_conv_dedup ON conversations (provider, source_conversation_id);

-- ============================================================
-- messages - individual turns within a conversation
-- ============================================================
-- Each row is one turn (human or assistant). For providers with
-- tree-structured conversations (chatgpt, deepseek), position
-- is assigned via DFS walk order so all nodes get a unique
-- position within their conversation.
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,                -- denormalized from conversations for query convenience
    model TEXT,                            -- LLM model identifier; NULL for human turns and claude
    source_conversation_id TEXT NOT NULL,  -- denormalized; matches conversations.source_conversation_id
    conversation_id INTEGER,              -- FK to conversations.id; NULL only if inserted outside normal import
    role TEXT NOT NULL,                    -- human | assistant | system | tool
    content TEXT NOT NULL,                -- message body; for deepseek, may include <thinking> tags
    position INTEGER NOT NULL,            -- 0-indexed turn order (array index or DFS order for trees)
    parent_message_id TEXT,               -- provider's parent node ID for tree conversations; NULL for flat (claude)
    prompt_id INTEGER,                    -- FK to prompts.id if message is linked to a managed prompt
    created_at TEXT,                       -- message timestamp (ISO 8601)
    imported_at TEXT NOT NULL,             -- when we ingested this record (ISO 8601)
    FOREIGN KEY (conversation_id) REFERENCES conversations (id),
    FOREIGN KEY (prompt_id) REFERENCES prompts (id)
);

-- Dedup: same provider + conversation + position + content = same message.
-- INSERT OR IGNORE makes reimports idempotent.
CREATE UNIQUE INDEX idx_dedup ON messages (provider, source_conversation_id, position, content);

-- FTS5 index mirrors messages.content for full-text search.
-- Kept in sync by the insert/delete triggers below.
CREATE VIRTUAL TABLE messages_fts USING fts5 (
    content,
    content='messages',
    content_rowid='id'
);

CREATE TRIGGER messages_fts_insert AFTER INSERT ON messages BEGIN
    INSERT INTO messages_fts (rowid, content) VALUES (new.id, new.content);
END;

CREATE TRIGGER messages_fts_delete AFTER DELETE ON messages BEGIN
    INSERT INTO messages_fts (messages_fts, rowid, content) VALUES ('delete', old.id, old.content);
END;

-- ============================================================
-- prompts - managed system prompts and templates
-- ============================================================
-- Stores reusable prompts with versioning. content_hash (sha256)
-- prevents duplicate content. Prompts can form version chains
-- via parent_prompt_id.
CREATE TABLE prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'system_prompt',  -- system_prompt | template | (extensible)
    version INTEGER NOT NULL DEFAULT 1,
    parent_prompt_id INTEGER,             -- previous version of this prompt, if any
    tags TEXT,                             -- comma-separated tags for filtering
    notes TEXT,
    content_hash TEXT NOT NULL,            -- sha256 hex digest of content
    created_at TEXT NOT NULL,              -- ISO 8601
    FOREIGN KEY (parent_prompt_id) REFERENCES prompts (id)
);

-- Same content = same prompt, regardless of name/tags.
CREATE UNIQUE INDEX idx_prompt_dedup ON prompts (content_hash);

-- FTS5 index across name, content, tags, and notes.
CREATE VIRTUAL TABLE prompts_fts USING fts5 (
    name, content, tags, notes,
    content='prompts',
    content_rowid='id'
);

CREATE TRIGGER prompts_fts_insert AFTER INSERT ON prompts BEGIN
    INSERT INTO prompts_fts (rowid, name, content, tags, notes)
    VALUES (new.id, new.name, new.content, new.tags, new.notes);
END;

CREATE TRIGGER prompts_fts_delete AFTER DELETE ON prompts BEGIN
    INSERT INTO prompts_fts (prompts_fts, rowid, name, content, tags, notes)
    VALUES ('delete', old.id, old.name, old.content, old.tags, old.notes);
END;

-- ============================================================
-- access_log - audit trail for CLI commands
-- ============================================================
CREATE TABLE access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,              -- ISO 8601
    command TEXT NOT NULL,                -- subcommand name (init, import, search, etc.)
    args TEXT,                            -- JSON-encoded arguments for reproducibility
    result_count INTEGER                  -- number of results returned, if applicable
);

-- ============================================================
-- metadata - key-value store for schema version and config
-- ============================================================
CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO metadata (key, value) VALUES ('schema_version', '2');
