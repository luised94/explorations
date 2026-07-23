LLM PLAYBOOK
============

A self-contained toolkit of conventions, protocols, and preference
documents for running stateless LLM chat threads against projects.
Everything a thread needs arrives through documents; nothing is
assumed remembered. All files here are ASCII only.

VERSION: see the VERSION file. Every rendered context document
carries a stamp derived from it.

TRANSPORT TIERS (how these documents reach a chat)
  Tier A: the model has repository access; point it at file paths.
  Tier B: the model can fetch URLs; use the raw URLs in MANIFEST.md.
  Tier C: plain chat; paste whole documents.

DOCUMENT INDEX
  MANIFEST.md is the sole authoritative index: per-role ordered
  required-read lists with token budgets, and each document's load
  class. Directory names are shelving only; never cite a document
  by its directory.

TRANSPORT (getting content INTO a chat)
  scripts/pack-repo.sh (arrives at commit T-015b) packs a chosen
  file set at a recorded commit SHA and echoes the SHA. Two modes:
  archive (git archive --format=tar.gz to /tmp) and paste (the same
  set composed to a /tmp temp file). It writes ONLY to scratch space
  and reads ONLY committed files, so a render must be committed
  before it is packed. It never materializes a second on-disk copy
  of the repository; the earlier sparse-checkout bootstrap was
  retired for this reason (ADR-021).

CHECKS AND HOOK INSTALLATION
  scripts/check.sh enforces line budgets, token estimates, and
  containment (no upward path references, no parent-repository
  name in prose). Install as a pre-commit hook from the repository
  root with this one line:

    ln -s "$PWD/llm_playbook/scripts/check.sh" .git/hooks/pre-commit

LITE MODE
  A task small enough to describe completely in one paragraph with
  no design fork may skip the full pipeline: state the task, cite
  the style contract, land it. Anything larger enters through the
  entry file.

ROLE ROUTING
  Threads declare one role: DESIGN, IMPLEMENTATION, or CAPTURE.
  The entry file entry/ENTRY.md (arrives at commit T-014) carries
  the common invariants and the three role sections.
