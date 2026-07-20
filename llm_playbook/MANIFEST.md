MANIFEST
========

The sole authoritative grouping of playbook documents into load
classes, with per-role ordered required-read lists and token
budgets. Directory placement carries no semantics.

No documents are indexed yet; entries accrue as commits land.

MACHINE-READABLE BLOCK FORMAT (parsed by scripts/check.sh)
  Required-read lists are declared one per line, anywhere in this
  file, in the form:

    REQREAD <ROLE> <token_budget>: <path> <path> ...

  Paths are relative to the repository root. Token estimate is
  total characters divided by 4. Roles and budgets planned:
  DESIGN 10000, IMPLEMENTATION 6000, CAPTURE 6000.

LOAD CLASSES
  load-always | load-per-role | on-demand

DOCUMENT TABLE
  (empty)

RAW URLS
  (empty; populated at tag time, T-016)
