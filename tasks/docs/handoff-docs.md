# tsk -- Handoff Document
## Thread: Commits 01-08 (Phase 0, Threads A-D convergence)
## Date: 2026-05-28
---
## Completed Commits
| #  | Level  | Thread | Summary |
|----|--------|--------|---------|
| 01 | haiku  | A,B,C  | Directory structure and scaffold script |
| 02 | sonnet | A      | Record parser (parse_records, parse_file) |
| 03 | haiku  | A      | Record writer (format_record, write_file) |
| 04 | haiku  | A      | Parser round-trip verification (--verify-parser) |
| 05 | haiku  | B      | ID generation (generate_id) |
| 06 | haiku  | B      | Prefix matching (find_records_by_prefix) |
| 07 | haiku  | C      | Usage logging (inlined at dispatch level) |
| 08 | sonnet | D      | tsk add command (exemplar mutation command) |
---
## Deviations from Spec and Commit Plan
### 1. Usage logging inlined at dispatch level
**Plan said:** extract log_usage as a function, call from each handler.
**Implementation:** inlined in try/finally block at dispatch level. One call
site in phase 0, so the function extraction rule prohibits extraction.
**Impact on later commits:** none. Logging is automatic for all commands
routed through the dispatch table. No handler code needed.
### 2. find_records_by_prefix returns list, not record-or-exit
**Plan said:** return single match, exit on no-match or ambiguous.
**Implementation:** returns list of matching records. Caller checks length.
**Impact on later commits:** commits 12 (done), 13 (retire), 14 (edit)
must check len(matches) and handle 0/1/2+ cases with domain-specific
error messages. Pattern:
```python
matches = find_records_by_prefix(active_records, search_prefix)
if len(matches) == 0:
    print(f"error: no record found matching: {search_prefix}", file=sys.stderr)
    sys.exit(1)
if len(matches) > 1:
    matching_ids = ", ".join(r["id"] for r in matches)
    print(f"error: ambiguous prefix '{search_prefix}', matches: {matching_ids}", file=sys.stderr)
    sys.exit(1)
target_record = matches[0]
```
### 3. generate_id returns None on exhaustion, not exit
**Plan said:** print error, exit 1.
**Implementation:** returns None. Caller checks and handles.
**Impact on later commits:** commits 09-11 must check for None.
### 4. parse_flags introduced as shared utility
**Not in original plan.** Commit 08's plan described argument parsing inline.
Extracted because 4+ callers in phase 0 (add, goal, habit, event).
parse_flags calls sys.exit(1) on missing flag value -- acceptable because
it runs before any state is read and the dispatch try/finally still logs.
### 5. validate_priority -- single caller assumption
**Extracted** with [ASSUME: handle_goal (09) will also validate priority].
If goal does not validate priority, inline back into handle_add at phase
end review.
### 6. Continuation indentation normalized to 2 spaces
**Spec said:** preserve internal indentation relative to first continuation.
**Implementation:** normalizes to 2 spaces on write. Round-trip defined as
semantic equivalence: parse(write(parse(x))) == parse(x).
### 7. Record field ordering via FIELD_ORDER constant
**Not in spec.** Added as implementation detail. Multi-line fields (prep,
notes) written last for readability.
---
## Patterns Established (for next thread to follow)
### Mutation command pattern (exemplar: handle_add)
1. Parse arguments via parse_flags(arguments, FLAG_DICT)
2. Validate positional args (summary required)
3. Validate flag values (priority range, date format)
4. Read source file via parse_file
5. Collect existing IDs, generate new ID
6. Check generate_id result for None
7. Build record dict with auto fields + flag fields
8. Append to records list
9. Write via write_file
10. Print confirmation: "added: {id} {summary}"
### Flag definition pattern
```python
COMMAND_FLAGS = {
    "--long": "field_name", "-x": "field_name",
}
```
### Error output pattern
- Validation errors: print to stderr, sys.exit(1)
- Confirmation: print to stdout
- Format: "error: {what went wrong}" then optionally "usage: tsk ..."
---
## Shared Functions Available
| Function | Call sites in phase 0 | Location |
|----------|----------------------|----------|
| parse_records(text) | parse_file | PARSER section |
| parse_file(filepath) | handle_add, handle_goal, handle_habit, handle_event, handle_done, handle_edit, handle_today, handle_list | PARSER section |
| format_record(record) | write_file | WRITER section |
| write_file(filepath, records) | handle_add, handle_goal, handle_habit, handle_event, handle_done, handle_edit | WRITER section |
| verify_parser() | --verify-parser dispatch | VERIFICATION section |
| generate_id(prefix, ids) | handle_add, handle_goal, handle_habit, handle_event | DATA UTILITIES |
| find_records_by_prefix(records, prefix) | handle_done, handle_retire, handle_edit | DATA UTILITIES |
| parse_flags(arguments, definitions) | handle_add, handle_goal, handle_habit, handle_event | DATA UTILITIES |
| validate_priority(value) | handle_add, handle_goal (assumed) | DATA UTILITIES |
| validate_date_format(value) | handle_add, handle_event | DATA UTILITIES |
---
## Next Thread Scope: Commits 09-16
Recommended grouping:
- **Batch 1 (09, 10, 11):** goal, habit, event -- thin wrappers following add exemplar. Three haiku-level commits, safe to batch.
- **Batch 2 (12, 13):** done, retire -- lifecycle commands. Sonnet + haiku, can batch.
- **Batch 3 (14):** edit -- sonnet, standalone (temp file + $EDITOR interaction).
- **Batch 4 (15, 16):** today, list -- view commands (exemplar for view pattern). Two sonnets, may need separate treatment.
Then commits 17-19 (wiring, placeholders, bash alias) are three haiku to close phase 0.
---
## Current File State
The full tasks.py artifact (id: tasks-py) is the source of truth.
Paste it into the next thread's opening prompt along with this handoff,
the spec, and the workflow rhythm document.
---
# Addendum: Post-Handoff Decisions
Produced after the handoff document. Apply these before starting commit 09.
---
## 1. Usage log now tracks outcome (ok/error)
The dispatch block in tasks.py gains an outcome field. Apply this change
to the existing dispatch block before any new commits.
### Current dispatch block (replace entirely):
python
dispatch_start_time = time.time()
dispatch_exit_code = 0
try:
    COMMANDS[command_name](arguments)
except SystemExit as exit_error:
    dispatch_exit_code = exit_error.code
    raise
except Exception:
    dispatch_exit_code = 1
    raise
finally:
    outcome = "ok" if dispatch_exit_code == 0 else "error"
    elapsed_seconds = time.time() - dispatch_start_time
    primary_arg = arguments[0] if arguments else "-"
    log_timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M:%S")
    log_line = f"{log_timestamp} {command_name} {primary_arg} {elapsed_seconds:.2f}s {outcome}\n"
    try:
        with open(USAGE_LOG_FILE, "a", encoding="utf-8") as usage_log:
            usage_log.write(log_line)
    except OSError:
        pass

### Spec section 4 usage log format update:
Old format:

YYYY-MM-DDTHH:MM:SS <command> <primary_arg_or_dash> <duration_seconds>

New format:

YYYY-MM-DDTHH:MM:SS <command> <primary_arg_or_dash> <duration_seconds> <outcome>

Old examples:

2026-05-22T14:30:22 add T0522a 0.03s
2026-05-22T18:00:12 done T0522a 0.02s

New examples:

2026-05-22T14:30:22 add T0522a 0.03s ok
2026-05-22T14:31:05 done X999 0.01s error
2026-05-22T18:00:12 done T0522a 0.02s ok

### What this catches:
- Handler validation failures (sys.exit(1)) -> "error"
- Handler success (normal return) -> "ok"
- Handler idempotent exits (sys.exit(0), e.g. habit already logged) -> "ok"
- Unexpected exceptions (bugs) -> "error" (plus stack trace to stderr)
### What this does NOT catch:
- Pre-dispatch exits (unknown command, missing data dir) -- these exit
  before the try block. Acceptable gap: these are environment/typo
  errors, not workflow friction.
---
## 2. Design discussion: cross-project error logging
Discussed but deferred. Decision: each tool logs locally to its own
directory. Aggregation across projects is a future read-layer concern,
not a write-layer concern. No cross-project dependencies between tsk,
lw, friction, etc.
No code changes needed for this -- it is a strategic decision that
prevents future coupling.
---
