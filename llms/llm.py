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
    print(f"error: provider '{args.provider}' not yet implemented", file=sys.stderr)
    sys.exit(1)
else:
    parser.print_help()
    sys.exit(1)
