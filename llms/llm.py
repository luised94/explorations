#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import argparse
import sqlite3
import sys
from pathlib import Path
import json
from datetime import datetime, timezone

# --- constants ---

DATABASE_PATH = Path(__file__).parent / "llm.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# --- argument parsing ---

parser = argparse.ArgumentParser(description="LLM thread archive")
subparsers = parser.add_subparsers(dest="command")

subparsers.add_parser("init", help="Initialize the database")
import_parser = subparsers.add_parser("import", help="Import conversations from provider export")
import_parser.add_argument("path", type=Path, help="Export file or directory")
import_parser.add_argument("--provider", required=True,
                           choices=["claude", "chatgpt", "deepseek", "qwen"],
                           help="Source provider format")

args = parser.parse_args()

# --- command dispatch ---

if args.command == "init":
    connection = sqlite3.connect(DATABASE_PATH)
    cursor = connection.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'")

    if cursor.fetchone() is not None:
        print(f"Database already initialized: {DATABASE_PATH}")
    else:
        schema_sql = SCHEMA_PATH.read_text()
        connection.executescript(schema_sql)
        connection.commit()
        print(f"Database initialized: {DATABASE_PATH}")

    connection.close()

elif args.command == "import":
    path = args.path.resolve()
    if not path.exists():
        print(f"error: path not found: {path}", file=sys.stderr)
        sys.exit(1)
    if not DATABASE_PATH.exists():
        print(f"error: database not found - run 'init' first", file=sys.stderr)
        sys.exit(1)
    conn = sqlite3.connect(DATABASE_PATH)
    conn.execute("PRAGMA journal_mode=WAL")
    conn.execute("PRAGMA foreign_keys=ON")
    now = datetime.now(timezone.utc).isoformat()
    stats = {"convs": 0, "convs_skip": 0, "msgs": 0, "msgs_skip": 0, "msgs_dupe": 0}
    warnings = []

    if args.provider == "claude":
        filepath = path / "conversations.json" if path.is_dir() else path
        if not filepath.is_file():
            print(f"error: not a file: {filepath}", file=sys.stderr)
            sys.exit(1)
        with open(filepath) as f:
            convs = json.load(f)
        for conv in convs:
            cid = conv.get("uuid")
            if not cid:
                stats["convs_skip"] += 1
                warnings.append("conversation missing uuid, skipped")
                continue
            try:
                conn.execute(
                    """INSERT OR IGNORE INTO conversations
                       (provider, source_conversation_id, title, summary,
                        created_at, updated_at, imported_at)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    ("claude", cid, conv.get("name"), conv.get("summary"),
                     conv.get("created_at"), conv.get("updated_at"), now),
                )
                db_cid = conn.execute(
                    "SELECT id FROM conversations WHERE provider=? AND source_conversation_id=?",
                    ("claude", cid),
                ).fetchone()[0]
            except sqlite3.Error as e:
                stats["convs_skip"] += 1
                warnings.append(f"conv {cid}: db error: {e}")
                continue
            stats["convs"] += 1
            for pos, msg in enumerate(conv.get("chat_messages", [])):
                text = msg.get("text")
                sender = msg.get("sender")
                if not text or not text.strip():
                    stats["msgs_skip"] += 1
                    continue
                if sender not in ("human", "assistant"):
                    stats["msgs_skip"] += 1
                    warnings.append(f"conv {cid} msg[{pos}]: unknown sender '{sender}'")
                    continue
                try:
                    r = conn.execute(
                        """INSERT OR IGNORE INTO messages
                           (provider, model, source_conversation_id, conversation_id,
                            role, content, position, parent_message_id,
                            created_at, imported_at)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        ("claude", None, cid, db_cid, sender, text,
                         pos, None, msg.get("created_at"), now),
                    )
                    if r.rowcount:
                        stats["msgs"] += 1
                    else:
                        stats["msgs_dupe"] += 1
                except sqlite3.Error as e:
                    stats["msgs_skip"] += 1
                    warnings.append(f"conv {cid} msg[{pos}]: db error: {e}")
        conn.commit()
    else:
        conn.close()
        print(f"error: provider '{args.provider}' not yet implemented", file=sys.stderr)
        sys.exit(1)

    conn.close()
    print(f"{args.provider} import complete:", file=sys.stderr)
    print(f"  conversations: {stats['convs']} processed, {stats['convs_skip']} skipped", file=sys.stderr)
    print(f"  messages:      {stats['msgs']} imported, {stats['msgs_dupe']} duplicates, {stats['msgs_skip']} skipped", file=sys.stderr)
    if stats["msgs_skip"]:
        print(f"  note: {stats['msgs_skip']} messages skipped (empty text)", file=sys.stderr)
    if warnings:
        print(f"  warnings ({len(warnings)}):", file=sys.stderr)
        for w in warnings:
            print(f"    {w}", file=sys.stderr)
else:
    parser.print_help()
    sys.exit(1)
