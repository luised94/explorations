-- ============================================================
-- conversations table
-- ============================================================
CREATE TABLE conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    source_conversation_id TEXT NOT NULL,
    title TEXT,
    summary TEXT,
    created_at TEXT,
    updated_at TEXT,
    imported_at TEXT NOT NULL
);

CREATE UNIQUE INDEX idx_conv_dedup ON conversations (provider, source_conversation_id);

-- ============================================================
-- messages
-- ============================================================
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    provider TEXT NOT NULL,
    model TEXT,
    source_conversation_id TEXT NOT NULL,
    conversation_id INTEGER,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    position INTEGER NOT NULL,
    parent_message_id TEXT,
    prompt_id INTEGER,
    created_at TEXT,
    imported_at TEXT NOT NULL,
    FOREIGN KEY (conversation_id) REFERENCES conversations (id),
    FOREIGN KEY (prompt_id) REFERENCES prompts (id)
);

CREATE UNIQUE INDEX idx_dedup ON messages (provider, source_conversation_id, position, content);

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
-- prompts 
-- ============================================================
CREATE TABLE prompts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    content TEXT NOT NULL,
    type TEXT NOT NULL DEFAULT 'system_prompt',
    version INTEGER NOT NULL DEFAULT 1,
    parent_prompt_id INTEGER,
    tags TEXT,
    notes TEXT,
    content_hash TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (parent_prompt_id) REFERENCES prompts (id)
);

CREATE UNIQUE INDEX idx_prompt_dedup ON prompts (content_hash);

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
-- access_log, metadata 
-- ============================================================
CREATE TABLE access_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    command TEXT NOT NULL,
    args TEXT,
    result_count INTEGER
);

CREATE TABLE metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

INSERT INTO metadata (key, value) VALUES ('schema_version', '2');
