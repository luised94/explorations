# llm.py Cheatsheet

## Setup

```bash
uv run llm.py init
uv run llm.py import raw/claude/ --provider claude
```

Reimport is idempotent - safe to run again after new exports.


## Core Commands

```bash
# Search
uv run llm.py search "sqlite"
uv run llm.py search "sqlite" --provider claude --limit 10

# List conversations
uv run llm.py list
uv run llm.py list --sort messages --limit 10      # longest conversations
uv run llm.py list --sort oldest --provider claude

# Show full conversation
uv run llm.py show 867                              # by internal id
uv run llm.py show 301727d0                         # by UUID prefix
```


## FTS5 Search Syntax

```bash
# Implicit AND - all terms must appear in the message
uv run llm.py search "sqlite schema migration"

# Exact phrase
uv run llm.py search '"full text search"'

# OR
uv run llm.py search "sqlite OR postgres"

# NOT
uv run llm.py search "sqlite NOT migration"

# Prefix match - finds python, pythonic, etc.
uv run llm.py search "python*"

# NEAR - terms within N words of each other (default 10)
uv run llm.py search "NEAR(sqlite schema)"
uv run llm.py search "NEAR(sqlite schema, 5)"

# Combine operators
uv run llm.py search '"error handling" OR "try except"'
uv run llm.py search "async NOT javascript"
```


## Pipeline Patterns

```bash
# Pipe search to grep for secondary filtering
uv run llm.py search "python" | grep -i "fastapi"

# Page through long conversations
uv run llm.py show 867 | less -R

# Save a conversation to file
uv run llm.py show 867 > /tmp/conv-867.md

# Open in editor
uv run llm.py show 867 > /tmp/conv.md && nvim /tmp/conv.md

# Count search hits (result count goes to stderr)
uv run llm.py search "python" 2>/dev/null | grep -c "^\["

# Search then show (one-liner)
ID=$(uv run llm.py search "schema design" --limit 1 2>/dev/null | grep -oP 'conv \K\d+' | head -1) && uv run llm.py show $ID

# Pipe to fuzzy finder.
uv run llm.py list | fzf
uv run llm.py search "python" | fzf
```


## Direct SQL Queries

### Conversation stats
```bash
# Total counts
sqlite3 llm.db "SELECT provider, COUNT(*) FROM conversations GROUP BY provider"
sqlite3 llm.db "SELECT provider, COUNT(*) FROM messages GROUP BY provider"

# Longest conversations
sqlite3 llm.db "
  SELECT c.id, c.title, COUNT(m.id) AS msgs
  FROM conversations c
  JOIN messages m ON m.conversation_id = c.id
  GROUP BY c.id ORDER BY msgs DESC LIMIT 10"

# Conversations by month
sqlite3 llm.db "
  SELECT SUBSTR(created_at, 1, 7) AS month, COUNT(*) AS convs
  FROM conversations
  GROUP BY month ORDER BY month"
```

### Message-level queries
```bash
# Search only human messages (questions you asked)
sqlite3 llm.db "
  SELECT m.id, c.title, SUBSTR(m.content, 1, 120)
  FROM messages_fts
  JOIN messages m ON m.id = messages_fts.rowid
  JOIN conversations c ON c.id = m.conversation_id
  WHERE messages_fts MATCH 'sqlite' AND m.role = 'human'
  LIMIT 10"

# Search only assistant responses
sqlite3 llm.db "
  SELECT m.id, c.title, SUBSTR(m.content, 1, 120)
  FROM messages_fts
  JOIN messages m ON m.id = messages_fts.rowid
  JOIN conversations c ON c.id = m.conversation_id
  WHERE messages_fts MATCH 'sqlite' AND m.role = 'assistant'
  LIMIT 10"

# Find messages near a date
sqlite3 llm.db "
  SELECT c.id, c.title, m.role, SUBSTR(m.content, 1, 100)
  FROM messages m
  JOIN conversations c ON c.id = m.conversation_id
  WHERE m.created_at BETWEEN '2025-10-01' AND '2025-10-31'
    AND m.role = 'human'
  ORDER BY m.created_at
  LIMIT 20"

# Messages containing code (heuristic: look for common patterns)
sqlite3 llm.db "
  SELECT c.id, c.title, m.position
  FROM messages_fts
  JOIN messages m ON m.id = messages_fts.rowid
  JOIN conversations c ON c.id = m.conversation_id
  WHERE messages_fts MATCH 'def OR class OR import OR function'
    AND m.role = 'assistant'
  LIMIT 20"
```

### Cross-conversation patterns
```bash
# Conversations where you discussed the same topic across providers
sqlite3 llm.db "
  SELECT DISTINCT c.provider, c.id, c.title
  FROM messages_fts
  JOIN messages m ON m.id = messages_fts.rowid
  JOIN conversations c ON c.id = m.conversation_id
  WHERE messages_fts MATCH 'sqlite'
  ORDER BY c.provider, c.created_at DESC"

# Your most common opening questions (first human message)
sqlite3 llm.db "
  SELECT SUBSTR(m.content, 1, 80), COUNT(*) AS freq
  FROM messages m
  WHERE m.role = 'human' AND m.position = 0
  GROUP BY SUBSTR(m.content, 1, 80)
  HAVING freq > 1
  ORDER BY freq DESC LIMIT 20"
```


## Access Log Analysis

```bash
# Command frequency
sqlite3 llm.db "SELECT command, COUNT(*) FROM access_log GROUP BY command"

# Average response time by command
sqlite3 llm.db "SELECT command, COUNT(*), AVG(elapsed_ms), MAX(elapsed_ms) FROM access_log GROUP BY command"

# Recent activity
sqlite3 llm.db "SELECT timestamp, command, result_count, elapsed_ms FROM access_log ORDER BY id DESC LIMIT 20"

# Search queries you've run (what are you looking for most?)
sqlite3 llm.db "
  SELECT json_extract(args, '$.query') AS query, COUNT(*) AS runs
  FROM access_log WHERE command = 'search'
  GROUP BY query ORDER BY runs DESC LIMIT 15"
```


## Performance Diagnostics

```bash
# Check query plans (look for SEARCH = good, SCAN on real tables = investigate)
sqlite3 llm.db "EXPLAIN QUERY PLAN
  SELECT messages.id FROM messages_fts
  JOIN messages ON messages.id = messages_fts.rowid
  WHERE messages_fts MATCH 'sqlite' LIMIT 20"

# Database size
ls -lh llm.db

# Table sizes (approximate)
sqlite3 llm.db "
  SELECT name, SUM(pgsize) / 1024 AS size_kb
  FROM dbstat GROUP BY name ORDER BY size_kb DESC"

# Index sizes
sqlite3 llm.db "
  SELECT name, SUM(pgsize) / 1024 AS size_kb
  FROM dbstat WHERE name LIKE 'idx_%' GROUP BY name"
```


## Database Reset

```bash
# Full rebuild (safe while DB is disposable cache)
rm llm.db
uv run llm.py init
uv run llm.py import raw/claude/ --provider claude
# add other providers as implemented
```


## Knowledge Base References

```
@llm:UUID              conversation by unique id
@llm:867              conversation by internal id
@llm:867:p15          specific message position
@llm:867:pp12-18      message range
```

Verify: `uv run llm.py show 867`
