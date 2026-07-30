# Repair Note: ASCII-Only Constraint

Date: 2026-07-30
Scope: conv.sh, conv.lua, all locally saved content

## Constraint

All code and locally saved content must use ASCII only (0x00-0x7F).
No Unicode box-drawing, arrows, em-dashes, curly quotes, or multi-byte characters.

## Rationale

- Terminal portability: not all fonts/locales render Unicode consistently.
- grep/diff/sort reliability: multi-byte characters break byte-oriented tools.
- Copy-paste integrity: Unicode mangles across clipboard boundaries.
- Data-oriented principle: the representation must not depend on the
  rendering environment. One byte per character. No hidden dependencies.

## What changed

### conv.sh

| Before (non-ASCII)         | After (ASCII)            |
|----------------------------|--------------------------|
| Section dividers: ÄÄ       | Section dividers: --     |
| (no other non-ASCII found) |                          |

### conv.lua

| Before (non-ASCII)         | After (ASCII)            |
|----------------------------|--------------------------|
| TREE_BRANCH_CHAR = "ÃÄÄ "  | TREE_BRANCH_CHAR = "\|-- " |
| TREE_LAST_CHILD_CHAR = "ÀÄÄ " | TREE_LAST_CHILD_CHAR = "`-- " |
| TREE_VERTICAL_CHAR = "³   " | TREE_VERTICAL_CHAR = "\|   " |
| "" in format strings     | "->" in format strings   |
| syn match /[ÃÀ³Ä]/        | syn match /[\|`-]/       |

### Tree rendering style

Before (Unicode):
    b001 [user] First thought...
    ÃÄÄ b002 [user] Second thought...
    ³   ÀÄÄ b003 [user] Third thought...
    ÀÄÄ b004 [user] Alternate thread...

After (ASCII, classic tree-command style):
    b001 [user] First thought...
    |-- b002 [user] Second thought...
    |   `-- b003 [user] Third thought...
    `-- b004 [user] Alternate thread...

## Verification

    # Check a file for non-ASCII bytes:
    grep -Pn '[^\x00-\x7F]' conv.sh conv.lua

    # Should return nothing. If it returns lines, those lines
    # contain non-ASCII characters that need replacement.

## General rule going forward

Before saving any file locally, run:
    grep -Pn '[^\x00-\x7F]' <filename>
Zero matches = compliant.
