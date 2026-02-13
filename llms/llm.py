#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import argparse
import sqlite3
import sys
import time
from pathlib import Path
import json
from datetime import datetime, timezone

# --- constants ---

DATABASE_PATH = Path(__file__).parent / "llm.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"

# Terminal formatting - ANSI codes when stdout is a tty, empty strings otherwise
SNIPPET_MARKER_START = "\x01"
SNIPPET_MARKER_END = "\x02"
USE_COLOR = sys.stdout.isatty()
COLOR_BOLD = "\033[1m" if USE_COLOR else ""
COLOR_DIM = "\033[2m" if USE_COLOR else ""
COLOR_BOLD_YELLOW = "\033[1;33m" if USE_COLOR else ""
COLOR_RESET = "\033[0m" if USE_COLOR else ""

# --- argument parsing ---

parser = argparse.ArgumentParser(description="LLM thread archive")
subparsers = parser.add_subparsers(dest="command")

subparsers.add_parser("init", help="Initialize the database")
import_parser = subparsers.add_parser("import", help="Import conversations from provider export")
import_parser.add_argument("path", type=Path, help="Export file or directory")
import_parser.add_argument("--provider", required=True,
                           choices=["claude", "chatgpt", "deepseek", "qwen"],
                           help="Source provider format")

search_parser = subparsers.add_parser("search", help="Full-text search across messages")
search_parser.add_argument("query", type=str, help="FTS5 search query")
search_parser.add_argument("--limit", type=int, default=20,
                           help="Maximum number of results (default: 20)")
search_parser.add_argument("--provider",
                           choices=["claude", "chatgpt", "deepseek", "qwen"],
                           help="Filter results to a single provider")

show_parser = subparsers.add_parser("show", help="Display a full conversation thread")
show_parser.add_argument("conversation", type=str,
                         help="Conversation ID (integer) or source UUID prefix")

list_parser = subparsers.add_parser("list", help="Browse conversations")
list_parser.add_argument("--limit", type=int, default=50,
                         help="Maximum number of conversations (default: 50)")
list_parser.add_argument("--provider",
                         choices=["claude", "chatgpt", "deepseek", "qwen"],
                         help="Filter to a single provider")
list_parser.add_argument("--sort",
                         choices=["recent", "oldest", "messages"],
                         default="recent",
                         help="Sort order (default: recent)")

args = parser.parse_args()
cmd_start = time.monotonic()
result_count = 0

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
    result_count = stats["msgs"]
    print(f"{args.provider} import complete:", file=sys.stderr)
    print(f"  conversations: {stats['convs']} processed, {stats['convs_skip']} skipped", file=sys.stderr)
    print(f"  messages:      {stats['msgs']} imported, {stats['msgs_dupe']} duplicates, {stats['msgs_skip']} skipped", file=sys.stderr)
    if stats["msgs_skip"]:
        print(f"  note: {stats['msgs_skip']} messages skipped (empty text)", file=sys.stderr)
    if warnings:
        print(f"  warnings ({len(warnings)}):", file=sys.stderr)
        for w in warnings:
            print(f"    {w}", file=sys.stderr)

elif args.command == "search":
    if not DATABASE_PATH.exists():
        print("error: database not found - run 'init' first", file=sys.stderr)
        sys.exit(1)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.row_factory = sqlite3.Row

    # Build WHERE clause - always has FTS MATCH, optionally filtered by provider
    where_parts: list[str] = ["messages_fts MATCH ?"]
    where_parameters: list = [args.query]

    if args.provider:
        where_parts.append("messages.provider = ?")
        where_parameters.append(args.provider)

    where_parameters.append(args.limit)

    # snippet() extracts a ~48-token window around each match with markers for highlighting.
    # Parameters are bound left-to-right: snippet markers first, then WHERE params, then LIMIT.
    search_sql = f"""
        SELECT
            messages.id,
            messages.provider,
            messages.role,
            messages.position,
            messages.created_at,
            messages.conversation_id,
            snippet(messages_fts, 0, ?, ?, '.', 48) AS matched_snippet,
            conversations.title,
            conversations.source_conversation_id
        FROM messages_fts
        JOIN messages ON messages.id = messages_fts.rowid
        LEFT JOIN conversations ON conversations.id = messages.conversation_id
        WHERE {" AND ".join(where_parts)}
        ORDER BY messages_fts.rank
        LIMIT ?
    """

    # Snippet marker params come first (they appear in SELECT before WHERE)
    all_parameters: list = [SNIPPET_MARKER_START, SNIPPET_MARKER_END] + where_parameters

    try:
        search_results = connection.execute(search_sql, all_parameters).fetchall()
    except sqlite3.OperationalError as error:
        print(f"error: search failed: {error}", file=sys.stderr)
        connection.close()
        sys.exit(1)

    result_count = len(search_results)

    if result_count == 0:
        print("No results.", file=sys.stderr)
    else:
        for index, row in enumerate(search_results):
            # Fetch the preceding message in this conversation for context
            # (e.g. the human question that prompted a matching assistant answer).
            # Uses MAX(position < current) to handle gaps from skipped empty messages.
            preceding_message = None
            if row["conversation_id"] is not None:
                preceding_message = connection.execute(
                    """SELECT role, content FROM messages
                       WHERE conversation_id = ? AND position < ?
                       ORDER BY position DESC LIMIT 1""",
                    (row["conversation_id"], row["position"]),
                ).fetchone()

            # Format header fields
            conversation_title = row["title"] or "(untitled)"
            message_date = row["created_at"][:10] if row["created_at"] else "no date"

            # Replace snippet markers with ANSI highlighting or plain-text brackets
            snippet_text = row["matched_snippet"]
            if USE_COLOR:
                snippet_text = snippet_text.replace(SNIPPET_MARKER_START, COLOR_BOLD_YELLOW)
                snippet_text = snippet_text.replace(SNIPPET_MARKER_END, COLOR_RESET)
            else:
                snippet_text = snippet_text.replace(SNIPPET_MARKER_START, ">>")
                snippet_text = snippet_text.replace(SNIPPET_MARKER_END, "<<")

            # Print result block
            separator = "-" * 60
            print(f"\n{COLOR_DIM}{separator}{COLOR_RESET}")
            print(f"{COLOR_BOLD}[{index + 1}/{result_count}]{COLOR_RESET} {conversation_title}")
            print(f"  {COLOR_DIM}{row['provider']} -> {row['source_conversation_id']} | {message_date} -> message #{row['position']} -> conv {row['conversation_id']}{COLOR_RESET}")

            if preceding_message:
                preceding_text = preceding_message["content"]
                if len(preceding_text) > 200:
                    preceding_text = preceding_text[:200] + "."
                preceding_text = preceding_text.replace("\n", " ")
                preceding_role = preceding_message["role"]
                print(f"  {COLOR_DIM}[{preceding_role}] {preceding_text}{COLOR_RESET}")

            print(f"  [{row['role']}] {snippet_text}")

        # Summary to stderr so piped output stays clean
        print(f"\n{COLOR_DIM}{'-' * 60}{COLOR_RESET}")
        print(f"{result_count} result{'s' if result_count != 1 else ''}", file=sys.stderr)

    connection.close()

elif args.command == "show":
    if not DATABASE_PATH.exists():
        print("error: database not found - run 'init' first", file=sys.stderr)
        sys.exit(1)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.row_factory = sqlite3.Row

    # Resolve the conversation: try integer id first, then UUID prefix match
    conversation_row = None
    identifier = args.conversation

    if identifier.isdigit():
        conversation_row = connection.execute(
            "SELECT * FROM conversations WHERE id = ?", (int(identifier),)
        ).fetchone()
    
    if conversation_row is None:
        # Prefix match on source_conversation_id (e.g. "301727d0" matches full UUID)
        matching_conversations = connection.execute(
            "SELECT * FROM conversations WHERE source_conversation_id LIKE ? || '%'",
            (identifier,),
        ).fetchall()

        if len(matching_conversations) == 1:
            conversation_row = matching_conversations[0]
        elif len(matching_conversations) > 1:
            print(f"error: '{identifier}' matches {len(matching_conversations)} conversations:", file=sys.stderr)
            for match in matching_conversations:
                title = match["title"] or "(untitled)"
                print(f"  {match['id']}: {title} ({match['provider']}, {match['source_conversation_id'][:12]}...)", file=sys.stderr)
            connection.close()
            sys.exit(1)

    if conversation_row is None:
        print(f"error: no conversation found for '{identifier}'", file=sys.stderr)
        connection.close()
        sys.exit(1)

    # Fetch all messages in position order
    messages = connection.execute(
        """SELECT role, content, position, created_at FROM messages
           WHERE conversation_id = ?
           ORDER BY position ASC""",
        (conversation_row["id"],),
    ).fetchall()

    result_count = len(messages)

    # Print conversation header
    conversation_title = conversation_row["title"] or "(untitled)"
    conversation_date = conversation_row["created_at"][:10] if conversation_row["created_at"] else "no date"
    separator = "=" * 60

    print(f"{COLOR_BOLD}{conversation_title}{COLOR_RESET}")
    print(f"{COLOR_DIM}{conversation_row['provider']} . {conversation_date} . {result_count} messages . id {conversation_row['id']}{COLOR_RESET}")
    print(f"{COLOR_DIM}{conversation_row['source_conversation_id']}{COLOR_RESET}")
    print(separator)

    # Print each message
    for message in messages:
        message_role = message["role"]
        message_time = message["created_at"][11:16] if message["created_at"] and len(message["created_at"]) > 16 else ""

        if message_role == "human":
            role_label = f"{COLOR_BOLD}[human]{COLOR_RESET}"
        else:
            role_label = f"[{message_role}]"

        time_stamp = f" {COLOR_DIM}{message_time}{COLOR_RESET}" if message_time else ""
        print(f"\n{role_label}{time_stamp}")
        print(message["content"])

    print(f"\n{separator}")
    connection.close()

elif args.command == "list":
    if not DATABASE_PATH.exists():
        print("error: database not found - run 'init' first", file=sys.stderr)
        sys.exit(1)

    connection = sqlite3.connect(DATABASE_PATH)
    connection.execute("PRAGMA journal_mode=WAL")
    connection.row_factory = sqlite3.Row

    # Sort order mapping
    sort_clauses = {
        "recent": "conversations.updated_at DESC",
        "oldest": "conversations.created_at ASC",
        "messages": "message_count DESC",
    }
    order_by = sort_clauses[args.sort]

    # Build WHERE clause
    where_parts: list[str] = []
    where_parameters: list = []

    if args.provider:
        where_parts.append("conversations.provider = ?")
        where_parameters.append(args.provider)

    where_clause = ("WHERE " + " AND ".join(where_parts)) if where_parts else ""

    where_parameters.append(args.limit)

    # Single query: conversation metadata + message count + first human message as preview
    list_sql = f"""
        SELECT
            conversations.id,
            conversations.provider,
            conversations.title,
            conversations.created_at,
            conversations.updated_at,
            COUNT(messages.id) AS message_count,
            (
                SELECT content FROM messages AS first_human
                WHERE first_human.conversation_id = conversations.id
                  AND first_human.role = 'human'
                ORDER BY first_human.position ASC
                LIMIT 1
            ) AS first_human_message
        FROM conversations
        LEFT JOIN messages ON messages.conversation_id = conversations.id
        {where_clause}
        GROUP BY conversations.id
        ORDER BY {order_by}
        LIMIT ?
    """

    conversation_rows = connection.execute(list_sql, where_parameters).fetchall()
    result_count = len(conversation_rows)

    if result_count == 0:
        print("No conversations found.", file=sys.stderr)
    else:
        for row in conversation_rows:
            conversation_title = row["title"] or "(untitled)"
            conversation_date = row["created_at"][:10] if row["created_at"] else "no date"
            message_count = row["message_count"]

            # Truncate preview: first human message, single line, ~100 chars
            preview = ""
            if row["first_human_message"]:
                preview = row["first_human_message"].replace("\n", " ").strip()
                if len(preview) > 100:
                    preview = preview[:100] + "..."

            print(f"{COLOR_BOLD}{row['id']:>4}{COLOR_RESET}  {conversation_title}")
            print(f"      {COLOR_DIM}{row['provider']} . {conversation_date} . {message_count} msgs{COLOR_RESET}")
            if preview:
                print(f"      {COLOR_DIM}{preview}{COLOR_RESET}")

        print(f"\n{result_count} conversation{'s' if result_count != 1 else ''}", file=sys.stderr)

    connection.close()

else:
    parser.print_help()
    sys.exit(1)

# --- access log ---
if DATABASE_PATH.exists():
    elapsed = int((time.monotonic() - cmd_start) * 1000)
    log_conn = sqlite3.connect(DATABASE_PATH)
    log_conn.execute(
        "INSERT INTO access_log (timestamp, command, args, result_count, elapsed_ms) VALUES (?, ?, ?, ?, ?)",
        (datetime.now(timezone.utc).isoformat(), args.command,
         json.dumps({k: str(v) for k, v in vars(args).items() if k != "command"}, default=str),
         result_count, elapsed),
    )
    log_conn.commit()
    log_conn.close()
