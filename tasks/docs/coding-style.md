# Coding Style Enforcement Rules
VERSION: 1
UPDATED: 2026-05-28
Standalone style rules for LLM-assisted implementation.
Paste into any implementation thread. Project-agnostic.
---
## Philosophy
Code is read top-to-bottom. Every indirection (function call, abstraction,
named helper) forces the reader to jump elsewhere and hold context across
the gap. Indirection earns its existence by being used more than once.
A long function that does one thing in sequence is not a problem -- it is
the ideal. The enemy is not length. The enemy is unnecessary jumps.
Data-oriented programming: define data shapes, write functions that
transform them. No classes, no OOP, no inheritance hierarchies. Libraries
with class-based APIs are fine to use -- the constraint is on code you write,
not code you call.
---
## Function Extraction
A function earns its definition by having **2+ call sites in the current
phase**, or by being a **dispatch target** (command handler, callback).
- Length alone does not justify extraction. A 300-line function performing
  one irreducible top-to-bottom sequence is correct. Do not split it.
- I/O boundaries do not justify extraction on their own.
- "It might be reused later" is not a call site. Extract when the second
  caller appears, not before.
- Default posture: inline. Extract only when forced by the second caller.
### Audit pattern
Before writing a new def, answer:
1. Name every call site in this phase. Write them down.
2. Count >= 2, or is it a dispatch target? If no: inline.
3. If extracting with only 1 known caller, mark: [ASSUME: will have N
   callers: {name them}]. If the assumed caller never materializes,
   inline at phase-end review.
---
## Higher-Order Function Patterns
Do not write a function (named, nested, or lambda) solely to pass to
sorted(), map(), filter(), or similar. Build the result directly
with a list comprehension, explicit loop, or direct construction.
**Exception:** genuine comparison-based sorting on data where the order
is not already known at code-write time (sorting records by a date field,
sorting by a numeric priority). In this case, an inline tuple key or
simple expression in sorted() is acceptable.
**The test:** if you already have the ordering defined somewhere (a list
constant, a known sequence, an enum), walk it directly. Do not convert
a known order into sort keys.
### Examples
python
# WRONG: order is known (FIELD_ORDER exists), converted to sort keys
sorted_names = sorted(record.keys(), key=lambda k: FIELD_ORDER.index(k))
# RIGHT: walk the known order directly
known_names = [name for name in FIELD_ORDER if name in record]
unknown_names = sorted(name for name in record if name not in FIELD_ORDER)
all_names = known_names + unknown_names
# ACCEPTABLE: genuine comparison, order not known until runtime
sorted_tasks = sorted(task_records, key=lambda r: (r.get("priority", "4"), r.get("due", "9999-99-99")))

---
## Variable Naming
Use domain vocabulary combined with structural role. If the name would
make sense in any program regardless of domain, it is too generic.
| Too generic | Domain-specific |
|-------------|-----------------|
| key         | field_name      |
| value       | field_value     |
| item        | task_record     |
| data        | active_records  |
| result      | matching_ids    |
| blocks      | formatted_records |
| path        | source_file_path |
| val         | existing_content |
| lst         | habit_log_entries |
Structural suffixes (_name, _value, _list, _path, _index,
_count) are fine when they clarify shape or role.
### Pairs and opposites
When two variables represent two sides of something, their names should
make the relationship obvious:
python
# CLEAR: field_name / field_value, search_prefix / matching_records
# UNCLEAR: k / v, prefix / results

---
## Intermediate Variables
Prefer naming a computed result before returning or using it. The
variable name documents intent and makes debugging easier.
python
# PREFER
position_in_order = FIELD_ORDER.index(field_name)
return (position_in_order, field_name)
# AVOID
return (FIELD_ORDER.index(field_name), field_name)

This applies especially to:
- Return values from function calls used in conditionals
- Expressions passed as arguments to other function calls
- Index expressions used more than once
---
## Function Docstrings
**Stateful functions** (modify files, print output, change data structures):
say what the function reads, what it transforms, and what it changes.
python
def handle_add(arguments: list[str]) -> None:
    """Create a new task record in active.txt.
    Reads active.txt for existing IDs, generates next available ID,
    builds record from summary + flags, appends to active.txt, writes file.
    Prints confirmation with new ID and summary to stdout.
    """

**Pure functions** (return a value, no side effects): say what goes in
and what comes out, in domain terms.
python
def generate_id(type_prefix: str, existing_record_ids: list[str]) -> str | None:
    """Generate the next available ID for a given type prefix and today's date.
    Reads existing_record_ids to find used suffixes for this prefix + date
    combination. Returns the next available ID in format {prefix}{MMDD}{a-z},
    or None if all 26 suffix letters are exhausted.
    """

---
## Control Flow
- Strict procedural. No classes, no OOP, no main() function pattern.
- Flat control flow. Minimize nesting depth.
- Full descriptive names. Abbreviations only when they have become nouns
  in the domain (usb, cli, nvim, url, api).
- Standard ASCII only in all code, comments, output, and documentation.
---
## Silent-Fill Failures to Catch
When an LLM implements code, watch for these patterns that violate the
above rules without explicitly marking them:
- Extracting a function without verifying 2+ call sites exist in the
  current phase. Mark with [ASSUME: will have N callers] and name them,
  or inline.
- Using a higher-order function pattern (sorted + key function, map +
  lambda) without checking whether direct construction is simpler. Mark
  with [ASSUME: sorting/mapping is necessary because...] or build directly.
- Using generic variable names (key, value, item, data, result) without
  domain context.
- Splitting a function for length alone when the logic is one irreducible
  sequence.
- Creating a nested function or closure when a flat loop with local
  variables would work.
---
