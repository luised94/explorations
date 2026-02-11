#!/usr/bin/env -S uv run
# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///

import argparse
import sqlite3
import sys
from pathlib import Path

DATABASE_PATH = Path(__file__).parent / "llm.db"
SCHEMA_PATH = Path(__file__).parent / "schema.sql"


def initialize_database(database_path):
    connection = sqlite3.connect(database_path)
    cursor = connection.cursor()

    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='metadata'")
    if cursor.fetchone() is not None:
        print(f"Database already initialized: {database_path}")
        connection.close()
        return

    schema_sql = SCHEMA_PATH.read_text()
    connection.executescript(schema_sql)
    connection.commit()
    connection.close()
    print(f"Database initialized: {database_path}")


def main():
    parser = argparse.ArgumentParser(description="LLM thread archive")
    subparsers = parser.add_subparsers(dest="command")

    subparsers.add_parser("init", help="Initialize the database")

    args = parser.parse_args()

    if args.command == "init":
        initialize_database(DATABASE_PATH)
    else:
        parser.print_help()
        sys.exit(1)


if __name__ == "__main__":
    main()
