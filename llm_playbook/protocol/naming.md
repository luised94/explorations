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
  Form: <FROM>-to-<TO>.md in the project's handoff/ directory.
    FROM  the sending thread id, full form.
    TO    the receiving thread id if known, else the receiving ROLE
          word.
  Example: handoff/DRILL-DESIGN-007-to-IMPL.md. One handoff, one
  file; a revised handoff supersedes in place (git keeps history).

  THE FRONTMATTER CARRIES THE CLASSIFICATION. A handoff- prefix on a
  file inside handoff/ restates what the type field already says, so
  the prefix is dropped. The classification lives in frontmatter and
  not in the path because the path does not survive transport: these
  documents are routinely packed into an archive or pasted whole into
  a chat (README, Tier C), and a file whose type is carried by its
  directory arrives in a chat with no type at all. The directory is
  shelving; the frontmatter is the claim.

  A KICKOFF IS A HANDOFF. Same directory, same filename form, same
  from and to fields; it differs only in type. A handoff is written by
  the sending thread at its close and looks back; a kickoff is written
  when the receiving thread opens, and it must additionally carry the
  binding sentence and the stamp statement (kickoff.md, ADR-030). The
  two documents on one edge do not collide, because TO is the ROLE
  word while the receiving id is unknown and the id once it is known:
    handoff, written at close  PLAYBOOK-DESIGN-004-to-IMPL.md
    kickoff, written at open   PLAYBOOK-DESIGN-004-to-IMPL-005.md
  A kickoff with no sending thread -- a project's first -- omits from
  and is named <TO>.md.

  Superseded form: handoff-<FROM>-to-<TO>.md in llm/handoffs/. Files
  already bearing that form are classifiable and are NOT renamed in
  bulk (see the classification note); they are brought to the current
  form only if touched for another reason.

FRONTMATTER FIELDS
  Frontmatter is the small fixed set below, and it is not extended
  ad hoc. A document carries the fields that apply to it and omits
  the rest; no field is invented at authoring time.
    date     YYYY-MM. Required on every playbook and instance
             document. Dates NEVER appear in filenames (N2); the
             sole exception is decisions era shards, whose era IS
             the filename.
    type     what kind of document this is: design, plan, handoff,
             kickoff, close, decisions, refinements, render, prompt,
             instance-rules. Required on every non-sentinel
             document, because the frontmatter and not the path is
             what carries the classification.
    scope    one line on what the document governs and what it
             does not. Required on playbook protocol and preference
             documents.
    status   current, superseded or outdated. Required on every
             non-sentinel document; see STATUS below.
    from     sending thread id. The handoff category only, and
             omitted by a project's first kickoff, which has no
             sending thread.
    to       receiving thread id or ROLE word. The handoff category
             only.
    role     the RECEIVING thread's role: DESIGN, IMPL or CAPTURE.
             The handoff category only. This is the same word the
             filename's TO slot holds while the receiving id is
             still unknown.
    supersedes
             the document this one replaces, by path. Required
             where a document replaces a named predecessor.
    version  semantic version, where the document is versioned
             independently of the playbook VERSION file.
  A field this list does not name is a finding, not an exception.

  STATUS answers exactly one question: DOES THIS DOCUMENT BIND ME?
    current     it governs now.
    superseded  it does not; follow the successor, which names this
                document in its supersedes field.
    outdated    it does not, and there is no successor.
  A document that does not say whether it is current is the drift
  this grammar exists to remove. status is orthogonal to type: a
  close artifact is status: current, because it is an accurate
  record that has not been corrected, and it takes its
  non-authority from type: close and not from its status. A close
  artifact later found wrong becomes superseded by the correction.

  RETIRED FIELDS, listed so a reader meeting one in an older file
  knows it was removed rather than forgotten:
    revision  git has it.
    purpose   that is scope.
    governs   that is scope.
    thread    that is from, or the filename.

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

  Workflow prompts: protocol/prompts/<verb-phrase>.md, lowercase,
  dateless, hyphenated (commit-planning.md, clone-and-verify.md).
  The name states WHAT THE PROMPT DOES, as a verb phrase, not the
  phase it belongs to -- a phase name goes stale when the process
  changes, a verb does not. Each carries type: prompt in
  frontmatter. A prompt is a METHOD and never an authority;
  precedence.md places it below the render and below project
  instance rules.

CLASSIFICATION NOTE
  Existing artifacts predating this grammar are classifiable
  against it and most are NONCONFORMANT (the drill handoffs above;
  dated filenames like use-period-plan-2026-07.md). Nonconformance
  of a pre-grammar artifact is recorded, not repaired, unless the
  artifact is touched for another reason; renames are never done
  in bulk (they break references for zero content gain).
