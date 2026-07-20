NAMING
======
date: 2026-07
scope: the naming grammar for thread ids, commit prefixes, handoff
filenames, refinement ids, close-artifact filenames, preference item
ids, and the playbook's own artifacts. DEFERRED, out of scope here:
an optional keyword/tag or descriptive-name segment appended to ids
or filenames (separator undecided); candidate future thread.

GENERAL RULES
  N1. ASCII only; UPPERCASE id components; hyphen "-" is the only
      separator inside ids and filenames. Filenames are lowercase,
      except SENTINEL files, fixed-name files whose name is their
      role: README.md, LICENSE, VERSION, MANIFEST.md, PROJECT.md,
      STATUS.md, CONTEXT.md, CLAUDE.md, AGENTS.md, ENTRY.md. New
      sentinels are not invented ad hoc; the set is exactly the
      names listed in this grammar and the project skeleton.
  N2. Dates live in frontmatter, never in filenames. Sole
      exception: decisions era shards (era-YYYY-qN.md), whose era
      IS the filename.
  N3. Ids are stable forever and never reused after retirement of
      the thing they name.
  N4. NO PATTERN MATCHING: a name is conformant because it follows
      a rule written here, not because it resembles a neighbor.
      Drift example, preserved as a caution: the drill project's
      handoffs directory accreted four coexisting shapes
      (1-to-implementation.md, handoff-2-to-implementation.md,
      handoff-D1-to-arithmetic.md, launch-2-ui-selector.md) because
      each new file imitated whichever neighbor its author saw
      last. Imitation compounds drift; rules do not.
  N5. NAME CHECK AT STOP: the commit/STOP checklist includes one
      line -- "every artifact this thread created or renamed is
      classifiable as conformant using naming.md alone." A file
      this document cannot classify is a finding, not an exception.

THREAD IDS
  Form: PROJ-ROLE-NNN
    PROJ  project code, UPPERCASE, 2-12 chars, letters and digits,
          chosen once per project and recorded in its PROJECT.md
          (e.g. DRILL). The playbook's own project code is
          PLAYBOOK.
    ROLE  one of DESIGN, IMPL, CAPTURE.
    NNN   zero-padded 3-digit counter per PROJ, over all roles
          (one shared counter, so ids also totally order threads
          within a project).
  Declared in the first message of the conversation (rule R13,
  thread-protocol.md). Example: DRILL-IMPL-004, PLAYBOOK-IMPL-001.

COMMIT PREFIXES
  Form: <proj>: <plan-id> <summary>   when a plan document exists,
        <proj>: <summary>             otherwise.
  <proj> is the lowercase project code; <plan-id> is the commit id
  from the governing plan (T-001, D-101, ...). Example:
  "playbook: T-003 naming grammar". Plan ids follow the plan's own
  grammar (phase letter, hyphen, number) and are never renumbered.

HANDOFF FILENAMES
  Form: handoff-<FROM>-to-<TO>.md   in the project's llm/handoffs/
    FROM  the sending thread id, full form.
    TO    the receiving thread id if known, else the receiving
          ROLE word.
  Example: handoff-DRILL-DESIGN-007-to-IMPL.md. One handoff, one
  file; a revised handoff supersedes in place (git keeps history).

REFINEMENT IDS
  Form: RF-PROJ-NNN, assigned in the project's refinements.md at
  entry time, zero-padded, never reused. A refinement entry that
  targets a preference item cites that item's id (see below) in its
  body. Example: RF-DRILL-012.

CLOSE-ARTIFACT FILENAMES
  Form: close-<THREAD-ID>.md   in the project's llm/ directory.
  Example: close-DRILL-IMPL-004.md. Required for terminal states
  landed, bounced, abandoned; a parked thread's existing design
  artifacts count as its close artifact and only the STATUS line
  flips (rule R12, thread-protocol.md).

PREFERENCE ITEM IDS
  Form: LAYER-NNN
    LAYER  one of PERSONA, CONSTRAINT, CRITERIA, CONVENTION.
    NNN    zero-padded 3-digit counter per layer.
  Stable forever; never reused after retirement (a retired item's
  entry remains in layers.md marked RETIRED, holding the id).
  A private overlay item bearing the same id shadows the public
  item whole (ADR-008). Example: CONSTRAINT-004.

PLAYBOOK ARTIFACTS
  Own files: lowercase, dateless (N2), hyphenated when multiword
  (style-contract.md, thread-protocol.md). Decisions era shards:
  era-YYYY-qN.md. Version tags on the shared repository:
  playbook-vX.Y.Z (prefixed; repo-wide tags must not collide with
  project tags). Renders at a project root: CONTEXT.md, plus
  generated CLAUDE.md / AGENTS.md; never any other name.

CLASSIFICATION NOTE
  Existing artifacts predating this grammar are classifiable
  against it and most are NONCONFORMANT (the drill handoffs above;
  dated filenames like use-period-plan-2026-07.md). Nonconformance
  of a pre-grammar artifact is recorded, not repaired, unless the
  artifact is touched for another reason; renames are never done
  in bulk (they break references for zero content gain).
