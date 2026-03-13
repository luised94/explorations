# Schema Migration Reference
## sm2.py - SQLite column additions

This document describes the pattern used in `initialize_database()` for adding
columns to existing tables without breaking databases created by earlier
versions of the tool.

---

## When this pattern applies

Use this pattern whenever you need to add a column to `items` or `review_log`
that did not exist in a prior version of the schema. It covers the case where
a user has a live database on disk and runs a new version of the tool for the
first time - the column must be added automatically without data loss.

It does not cover: renaming columns, dropping columns, changing column types,
or multi-table structural changes. Those require a more involved migration
strategy (versioned schema, explicit upgrade script) not yet needed here.

---

## How it works

SQLite's `CREATE TABLE IF NOT EXISTS` is idempotent - it only runs on a fresh
database. Existing databases skip it entirely. This means adding a column to
the `CREATE TABLE` statement alone is not enough for live databases; the column
must also be added via `ALTER TABLE` when it is missing.

The migration guard does exactly that:

1. Query `PRAGMA table_info(<table>)` to get the current column list.
2. Check whether the new column is present.
3. If absent, `ALTER TABLE ... ADD COLUMN` with the same default as in
   `CREATE TABLE`.
4. Commit immediately.

Fresh databases get the column from `CREATE TABLE` and the guard no-ops
naturally - `ALTER TABLE` is never called.

---

## Pattern

```python
# Step 1: query column names for the target table
# Use a separate PRAGMA call per table - do not reuse results across tables.
existing_<table>_columns: list[tuple] = database_connection.execute(
    "PRAGMA table_info(<table>)"
).fetchall()
<table>_column_names: set[str] = set()
for <table>_column_row in existing_<table>_columns:
    <table>_column_names.add(<table>_column_row[1])  # index 1 is the column name

# Step 2: add the column if absent
if "<new_column>" not in <table>_column_names:
    database_connection.execute(
        "ALTER TABLE <table> ADD COLUMN <new_column> <TYPE> DEFAULT <value>"
    )
    database_connection.commit()
```

The `DEFAULT` value in the `ALTER TABLE` statement must match the `DEFAULT`
in the `CREATE TABLE` statement. SQLite backfills existing rows with the
default value on `ALTER TABLE`, so both new and existing rows are consistent
after the guard runs.

---

## Concrete example - adding `source` to `items`

### 1. Add the column to `CREATE TABLE`

```python
database_connection.execute("""
    CREATE TABLE IF NOT EXISTS items (
        item_id           TEXT PRIMARY KEY,
        easiness_factor   REAL DEFAULT 2.5,
        interval_days     REAL DEFAULT 0.0,
        repetition_count  INTEGER DEFAULT 0,
        due_date          INTEGER,
        last_review       INTEGER DEFAULT 0,
        lapse_count       INTEGER DEFAULT 0,
        source            TEXT DEFAULT ''   -- added in F.01
    )
""")
```

### 2. Add the migration guard in `initialize_database()`

Place this block after all `review_log` migration guards, before
`return database_connection`. Keep the `PRAGMA table_info(items)` call
separate from the earlier `PRAGMA table_info(review_log)` call - do not
reuse that result set.

```python
existing_items_columns: list[tuple] = database_connection.execute(
    "PRAGMA table_info(items)"
).fetchall()
items_column_names: set[str] = set()
for items_column_row in existing_items_columns:
    items_column_names.add(items_column_row[1])
if "source" not in items_column_names:
    database_connection.execute(
        "ALTER TABLE items ADD COLUMN source TEXT DEFAULT ''"
    )
    database_connection.commit()
```

### 3. Add a validation assertion in `run_validation()`

Use a separate `PRAGMA table_info(items)` call - do not reuse the
`review_log` pragma result already present in `run_validation()`.

```python
items_pragma_rows: list[tuple] = validation_connection.execute(
    "PRAGMA table_info(items)"
).fetchall()
items_column_names: set[str] = set()
for items_pragma_row in items_pragma_rows:
    items_column_names.add(items_pragma_row[1])
if "source" not in items_column_names:
    print("FAIL: source column missing from items after initialize_database")
    failure_count = failure_count + 1
```

---

## Checklist for adding a new column

- [ ] Add column with `DEFAULT` to the `CREATE TABLE` statement
- [ ] Add migration guard in `initialize_database()` with matching `DEFAULT`
- [ ] Add validation assertion in `run_validation()` confirming column presence
- [ ] Add round-trip assertion in `run_validation()` if the column is written on INSERT
- [ ] Update `ParsedItem` / `ContentMap` type aliases if the column is sourced from exercise files
- [ ] Update `parse_exercises()` to parse the new field if it comes from exercise files
- [ ] Update `reconcile` INSERT to write the new value
- [ ] Update `run_validation()` synthetic items and content\_map unpack to include the new field

---

## Conventions

**One PRAGMA call per table.** `PRAGMA table_info()` returns rows for a single
table. If you are adding columns to both `items` and `review_log` in the same
phase, make two separate calls and store results in distinctly named variables.

**Immediate commits.** Each `ALTER TABLE` is committed before the next
migration guard runs. This matches the existing pattern and keeps the database
consistent if the process is interrupted mid-migration.

**Guards are cumulative when a live database exists.** Do not remove old guards
when adding new ones if users may be running databases from earlier versions.
Each guard protects a user who skipped one or more releases.

**Guards are optional on a fresh start.** If no live database exists (e.g. the
project has not yet entered daily use), migration guards can be omitted
entirely. All columns are guaranteed by `CREATE TABLE`; the guards would be
dead code. In this case, also remove the corresponding `run_validation()`
column-presence assertions - they were testing the guards, not the schema.

**Defaults must match.** The `DEFAULT` in `ALTER TABLE` and `CREATE TABLE`
must be identical. A mismatch means fresh databases and migrated databases
would produce different values for the same absent field.

**Source is write-once.** The `source` field is written on INSERT and never
updated by the review loop. If a `source:` value is corrected in an exercise
file, the database value does not follow. This is a known limitation - noted
in the deferred list - acceptable until content volume makes it a pain point.

---

## Deferred

- Column update on reconcile: currently fields written on INSERT (e.g. `source`)
  are not updated if the exercise file is later corrected. A reconcile UPDATE
  pass would fix this; defer until it becomes a real pain point.
- Multi-column additions in a single phase: the current pattern adds one column
  per guard block. If a future phase adds several columns at once, consider
  whether batching them into a single `ALTER TABLE` (not supported by SQLite -
  one column per statement) or a `CREATE TABLE / INSERT SELECT / DROP / RENAME`
  migration is warranted.
- Schema versioning: if migrations grow complex, a `schema_version` table with
  integer version numbers is cleaner than per-column guards. Not needed yet.
