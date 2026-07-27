PLAYBOOK REPOSITORY CONSOLIDATION -- EXECUTION PLAN
====================================================
date: 2026-07
type: plan
scope: everything to be changed in llm_playbook in this thread -- the
  naming grammar amendments, the frontmatter field set and status
  vocabulary, the lifecycle directories, the retirement of archive/,
  the check.sh rework, the repair harness, the two missing documents,
  and MANIFEST. Covers the WHOLE repository, not the toolkit layer
  only. Does NOT cover drill; drill inherits the decisions here
  through a handoff and is a separate thread.
status: current
supersedes: the earlier "PLAYBOOK execution plan" drafted against a
  17-file baseline

--------------------------------------------------------------------------
BASELINE
--------------------------------------------------------------------------

The earlier plan recorded 17 files, 1609 lines, and checksum
48d4bd9681bc5671cb8d607d3acee581. That is not this repository. The
pack was deliberately extended to the full tree so the cleanup could
be comprehensive, so the baseline is restated here rather than worked
around.

  files  33
  lines  4465

  md5 of the sorted md5sums, as the earlier plan measured it:
    find . -type f | sort | xargs md5sum | md5sum
    6af5c4938a9fea79047ace5994917011

  PREFERRED baseline identifier -- content-addressed by git, immune to
  find(1) ordering and to the path prefix the earlier measurement
  depended on. Run from the real repository root:

    git rev-parse HEAD:llm_playbook
    efe72488bde7af27ef43b8cd5613f4ef997275a7

  If the second command disagrees, the working tree is not the tree
  these patches were built against and nothing below should be applied
  until the difference is understood. File modes are part of this hash;
  scripts/check.sh and scripts/pack-repo.sh are mode 100755.

--------------------------------------------------------------------------
DECISIONS -- do not reopen
--------------------------------------------------------------------------

Carried in from the prior design session:

  DEC-1  Frontmatter carries a document's classification. Directories
         are shelving.
  DEC-2  The frontmatter field set is fixed: date, type, scope, status,
         from, to, supersedes, role, version. Retired: revision (git
         has it), purpose (that is scope), governs (that is scope),
         thread (that is from, or the filename).
  DEC-3  Genre prefixes are dropped from filenames in all cases,
         close artifacts included. The type field carries the genre.
  DEC-4  An id-named file takes a descriptive segment after an
         UNDERSCORE: <ID>_<descriptive>.md. Underscore and not hyphen,
         because ids already contain hyphens and a hyphenated suffix
         leaves no parseable boundary. This decides the separator
         ADR-026 left open.
  DEC-5  Descriptiveness test: NAME THE SUBJECT, NOT THE GENRE OR THE
         PHASE.
  DEC-6  The playbook gets its own llm/ lifecycle directory, because it
         is itself a project. The toolkit directories (preferences/,
         protocol/, scripts/) are unchanged and remain shelving.

Decided in this session:

  DEC-7  The "keep this file OUTSIDE llm_playbook/" placement rule
         carried by runbook-, plan-edits-, and consolidation- is
         RETIRED. Those documents fold into llm/. The rule's stated
         reason -- they quote the parent-repository name -- is answered
         by DEC-8 instead of by exile.
  DEC-8  Containment is SCOPED TO THE TOOLKIT LAYER. llm/ is exempt
         from both the upward-path grep and the parent-name grep. The
         rule is narrowed, not deleted: ADR-002 records that it exists
         to keep promotion to a standalone repository cheap, and that
         reason applies to the documents that travel as the toolkit,
         not to this project's own thread history.
  DEC-9  archive/ is RETIRED REPO-WIDE. This includes the project
         skeleton at implementation-plan.md T-011 and therefore drill.
         Superseded and outdated documents stay where they are and
         declare their state in frontmatter; moving a file to signal
         supersession states the same fact twice and breaks references
         for no content gain, which is the failure DEC-1 exists to
         prevent. A document that is truly removed is DELETED; git
         holds the history, which is what archive/ was standing in for.
  DEC-10 The status vocabulary is three values:
           current      governs now
           superseded   does not govern; follow the named successor
           outdated     does not govern; there is no successor
         historical is DROPPED. status answers "does this bind me?".
         A close artifact is status: current -- it is an accurate
         record that has not been corrected -- and gets its
         non-authority from type: close, not from its status. A close
         artifact later found wrong becomes superseded by the
         correction.
  DEC-11 check.sh line ceilings and REQREAD token budgets demote from
         FAIL to WARN. Containment and the ASCII rule remain hard
         fails. Nothing has been systematically benchmarked, so a
         calibrated-looking number would be invented authority;
         ADR-028 explicitly refused to delete the budgets because they
         are a real accretion countermeasure, so they are kept and
         stripped of false force rather than removed.
  DEC-12 check.sh identifiers are renamed to style-contract.md S1.
  DEC-13 The repair harness consolidates into llm/refinements.md as
         RF-PLAYBOOK-NNN entries, promoted by editorial pass into
         layers.md and style-contract.md. It reuses the existing id
         grammar and the existing promotion path rather than inventing
         a home.
  DEC-14 default_system_prompt.md becomes GENERATED render.md R-C
         output. The rules it carries that the render sources do not
         are back-filled into layers.md and style-contract.md first,
         so the file can be generated rather than maintained.
  DEC-15 protocol/thread-protocol.md is written against
         implementation-plan.md T-009, which specifies it, rather than
         reconstructed from drill's copy.
  DEC-16 Delivery follows ADR-023 MODE A. See DELIVERY below.
  DEC-18 A KICKOFF IS A HANDOFF -- a member of the category, not a
         separate genre. Same directory, same <FROM>-to-<TO>.md form,
         same from and to fields; it differs by type, and that
         difference is load-bearing, because type: kickoff is what
         obliges the document to carry the binding sentence and the
         stamp statement (ADR-030). The two documents on one edge do
         not collide: TO is the ROLE word before the receiving id is
         known and the id after. Closes the kickoff half of OPEN-1
         without a fifth lifecycle directory.
  DEC-17 The era-sharding trigger in ADR-012 has fired and is
         DEFERRED with the trigger recorded. Sharding mid-effort is
         what ADR-012's own note warns against, and this thread
         appends to era-2026-q3.md repeatedly.

--------------------------------------------------------------------------
FINDINGS
--------------------------------------------------------------------------

Each verified against the tree at the baseline above.

F-01  BASELINE MISMATCH. 33 files and 4465 lines, not 17 and 1609. The
      prior plan's verify command fails. Corrected above.

F-02  THE REPOSITORY IS RED, ON FIVE COUNTS, AND NOT GATED.
        upward-path grep: implementation-plan.md,
          consolidation-PLAYBOOK-DESIGN-002.md. All three occurrences
          are prose quoting the literal "../" while describing
          check.sh itself. This is open item O2 in
          close/PLAYBOOK-DESIGN-004.md.
        parent-name grep: runbook-PLAYBOOK-DESIGN-002.md,
          plan-edits-PLAYBOOK-DESIGN-002.md,
          consolidation-PLAYBOOK-DESIGN-002.md all contain the parent
          repository name. These do not fire in a sandbox whose root
          is named something else; they fire in the real repository.
      NOT BLOCKING: ADR-028 records that the pre-commit hook is not
      installed and that checks are run manually and do not gate. An
      earlier statement in this thread that the red blocked every
      commit was wrong and is corrected here.

F-03  ADR-028 ALREADY AUTHORIZES THE REWORK. Its decision text names
      the exact work: recalibrate ceilings against measured document
      sizes, narrow the containment grep, install the hook as part of
      that rework. The check.sh work below is a landed decision coming
      due, not new scope.

F-04  THE CONTAINMENT RULE HAS A RECORDED REASON. ADR-002: promotion to
      a standalone repository is a copy or a filter-repo run precisely
      because the tree is self-contained, and "one upward reference
      would otherwise fail silently until promotion day." This is why
      DEC-8 narrows the rule instead of deleting it.

F-05  ADR-033 ASSERTS THE PREMISE DEC-1 REVERSES. Its index line reads
      "handoff filenames: the directory carries the classification."
      Amending naming.md and kickoff.md while leaving the decision
      record asserting the old premise reproduces the drift this
      thread exists to remove.

F-06  implementation-plan.md IS status: outdated. The prior plan
      recorded it as status: current and derived urgency from a name
      collision with drill's live plan. The collision argument is
      weaker than stated. See OPEN-2.

F-07  naming.md HAS REFLOW DAMAGE IN THE SECTIONS THIS THREAD EDITS.
      Lines 58, 60, 62, 64 and 96 are 312, 384, 241, 982 and 445
      characters in a file otherwise wrapped near 68. Those are the
      handoff-filename rules, the directory-carries-classification
      paragraph, the frontmatter field set, and the workflow-prompt
      rule -- every section P1 through P3 touches.

F-08  implementation-plan.md CARRIES BLIND-SUBSTITUTION RESIDUE.
      "the parent repo repo" (line 14), "directory-in-the parent repo
      placement" (304), "in-the parent repo" (529). A prior scrub
      substituted the repository name by pattern without reading the
      surrounding prose. Recorded, not repaired -- see OUT OF SCOPE.

F-09  THE TWO claude-opus-4.8_ FILES ARE ONE DOCUMENT IN TWO FORMS.
      repair-notes is prose, taste is the same material as bullets:
      diff and patch discipline, sandbox git identity, POSIX sh. They
      are a repair harness, not thread artifacts. Zero inbound
      references.

F-10  decisions/adr-proposals.md IS SPENT. It proposes ADR-030, 031 and
      032; all three are landed in era-2026-q3.md with full prose. Its
      own header says append-then-decide. Zero inbound references.

F-11  thread-protocol.md IS SPECIFIED, NOT MERELY MISSING.
      implementation-plan.md T-009 gives R1-R10 generalized, R11
      drift-repair at STOP, R12 four terminal states, R13 thread
      identity, plus accept criteria; line 248 records the mapping
      from drill's llm-thread-protocol.md. R12 and R13 as specified
      match the citations in naming.md and kickoff.md exactly.

F-12  check.sh VIOLATES THE REPOSITORY'S OWN STYLE CONTRACT.
        check.sh      ROOT PB FLAG BUDGETS UP TAB PARENT
                      pat ceil f n c p rel err
        pack-repo.sh  WORKTREE_ROOT HEAD_OBJECT_NAME
                      RESOLVED_ANCESTOR_DIRECTORY EXPANDED_FILE_SET
                      NORMALIZED_TARGET PACKED_FILE_COUNT ...
      style-contract.md S1 mandates full descriptive names. Two
      scripts in one directory, one conformant and one not, and the
      conformant one is a worked example of the target state.

F-13  archive/README.md CONTRADICTS IN-PLACE SUPERSESSION, AND SO DOES
      ADR-012. ADR-012 is a bundled record: era sharding, archive from
      birth, index deferred to shard two. Only the middle clause is
      reversed by DEC-9. It needs a clause-level amendment, not a
      blanket supersede.

F-14  ADR-012's SHARDING TRIGGER HAS FIRED. Its note: "revisit sharding
      plus index.md creation at the next era boundary or the check.sh
      rework (ADR-028), whichever comes first." This thread does the
      check.sh rework. era-2026-q3.md was around 410 lines when that
      note was written and is 601 now.

F-15  check.sh DOES NOT IMPLEMENT ADR-031, AND LARGELY CANNOT. ADR-031
      landed the render ceiling as binding for paste delivery and
      advisory for archive delivery, with check.sh enforcing it "where
      it binds." check.sh enforces 250 lines unconditionally on any
      staged CONTEXT.md, with no tier input. Delivery tier is a
      property of how a render is SENT, not of the commit, so a
      pre-commit hook cannot know it. The obvious fix -- a tier: line
      in the render header -- is blocked by a real detail: render.md
      fixes the hashed body as line 3 onward, so inserting a header
      line invalidates every existing stamp.

F-16  default_system_prompt.md IS A RENDER TARGET, HAND-AUTHORED.
      render.md R-C is "the platform settings block: a condensed
      extract (persona and constraint items only) pasted once into a
      chat platform's standing-preferences setting." That is what this
      file is. But it cannot be generated today, because its content
      is not in the sources. Missing from layers.md and
      style-contract.md: respond with understanding and strategy
      before writing code; adversarial pass over an agreed plan;
      ranked-and-scored options ending in one recommendation; flat
      procedural with no single-call-site helpers; no abbreviations or
      single-letter names; never trust blind pattern substitution on a
      rename; state what is out of scope; verify by executing and show
      the output; commit-by-commit bisectable history.
      AND ONE DIRECT CONFLICT: style-contract.md S23 and
      layers.md CONSTRAINT-005 require the COMPLETE file with a patch
      only on request; default_system_prompt.md prefers a PATCH SERIES
      with the complete file as fallback. Inverted defaults on the
      same question. This is a merge conflict of substance and is
      resolved, not averaged.

F-17  naming.md WILL LAND NEAR ITS CEILING IN THE THREAD THAT REWORKS
      CEILINGS. It is 104 lines. Re-wrapping F-07's five squashed
      lines adds roughly 30; the three rule commits add roughly 55.
      That is near 190 against a ceiling of 200. Under DEC-11 it warns
      instead of failing, which is a further argument for DEC-11.

F-18  THE REQREAD TOKEN BUDGETS HAVE NEVER FIRED ONCE. MANIFEST's
      document table is empty, so the DESIGN 10000 / IMPL 6000 /
      CAPTURE 6000 budgets have never been evaluated. Populating the
      table in the last commit switches on three uncalibrated budgets
      at the end of the thread. DEC-11 covers them.

F-19  RETIRING archive/ REACHES THE SKELETON AND DRILL.
      implementation-plan.md T-011 lists archive/README.md as part of
      the consumer-project skeleton, and line 154 documents archive/
      as the destination for superseded toolkit documents. DEC-9 is
      repo-wide, so both change, and drill inherits it by handoff.

F-20  ADR-023 ALREADY SPECIFIES DELIVERY. See DELIVERY below; the
      question of patch form was decided, with reasons, and those
      reasons still hold.

F-21  THE RENAME COST IS CONCENTRATED IN ONE FILE. Inbound references
      to each file this thread touches, counted across all .md and .sh
      in the repository:

        implementation-plan             31  (runbook 18,
                                             consolidation 7,
                                             kickoff 2, era 2,
                                             plan-edits 1, close 1)
        close-PLAYBOOK-IMPL-003          7
        consolidation-PLAYBOOK-DESIGN-002 5
        plan-edits-PLAYBOOK-DESIGN-002    4
        kickoff-PLAYBOOK-IMPL-003         3
        runbook-PLAYBOOK-DESIGN-002       0
        adr-proposals                     0
        default_system_prompt             0
        claude-opus-4.8                   0
        llm_playbook_dir                  0 (and the file does not
                                             exist; the prior plan
                                             told us to delete it)

      naming.md's own CLASSIFICATION NOTE says renames "break
      references for zero content gain" and are never done in bulk.
      Thirty-one references to a status: outdated document is the case
      that rule was written for. See OPEN-2.

F-22  TWO DOCUMENT TYPES HAVE NO HOME IN THE SCHEME.
        KICKOFFS. naming.md's type list includes kickoff and DEC-2
        reserves the role field for kickoffs only, but the lifecycle
        directories are design/, plan/, handoff/, close/.
        kickoff-PLAYBOOK-IMPL-003.md has nowhere conformant to go.
        R-C OUTPUT. render.md gives R-A and R-B a location
        (<project>/llm/) and gives R-C none -- it is described only by
        where it is pasted. DEC-14 makes default_system_prompt.md an
        R-C artifact, which needs a path.
      See OPEN-1.

F-23  THE ADR-034 INDEX ENTRY WAS DAMAGED IN CONTENT. It dropped "is
      built" from the title and carried an appended fragment about
      transport.md where a title continuation belongs. Found only
      because the 1203-character line beside it was rewrapped. Fixed
      in its own commit, separate from the no-op rewraps.

F-24  F-17'S PROJECTION WAS LOW, AND naming.md IS NOW OVER ITS
      CEILING. Projected ~190; actual 229 against a ceiling of 200.
      The rewrap alone took it from 104 to 145, not the ~134
      estimated. Under DEC-11 this warns rather than fails and is
      recorded, not hidden. Whether naming.md should be SPLIT is a
      real question and is deliberately not answered here -- see
      OPEN-4.

F-25  THE TREE DOES NOT GO GREEN AT C-06, AS THIS PLAN CLAIMED. The
      five containment failures are on files that are correct to keep
      and merely wrong to place; the llm/ exemption clears them only
      once they are moved. Green arrives at C-08. Verified by dry
      run: with the five moved into llm/, check.sh reports clean and
      exits 0.

F-26  THE UNNAMED-FIELD PROBLEM WAS THREE TIMES LARGER THAN COUNTED.
      This plan listed six live findings against naming.md's fixed
      field set. The five close and handoff artifacts alone carried
      nine: thread, gate, predecessor, bootstrap SHA, purpose,
      governs, "what this is", "companion to", "applies to", "how to
      use", plus revision and the placement rule. All were real
      content, so none was discarded: they moved into the document
      body as THREAD RECORD or WHAT THIS WAS blocks, where they are
      content rather than classification.

F-27  kickoff.md's OWN HANDOFF TEMPLATE EMITS AN UNNAMED FIELD. The
      template's header block includes "why a <ROLE> thread:", which
      the fixed field set does not name. Now that role: exists, that
      line is the justification for role: and belongs in the body.
      The template is NOT fixed in C-07 or C-08 -- it is a separate
      concern in a file two earlier commits already touched. OWED.

F-28  A CLOSE ARTIFACT CARRIES NO from:. The field set scopes from
      and to to the handoff category, and a close artifact's thread
      id is its filename -- which is exactly the reasoning DEC-2 gave
      for retiring thread:. Discovered while writing the frontmatter,
      not while designing the field set.

--------------------------------------------------------------------------
ADVERSARIAL PASS
--------------------------------------------------------------------------

What would make this go wrong, and what the change will expose.

A-1  ORDER. The check.sh rework must land before the file moves, so
     that a green tree is established once and then held. Moving
     documents into llm/ also clears containment under DEC-8, so
     either order ends green -- but fixing the ruler first means every
     later commit is measured, and fixing it second means the ruler is
     wrong for most of the thread.

A-2  DO NOT INSTALL THE HOOK MID-SERIES. ADR-028 makes hook
     installation part of the rework. Installing it early turns every
     subsequent commit into a gate before the tree is green. Install
     it LAST, as the final commit, once the tree passes cleanly.

A-3  naming.md IS EDITED BY THREE CONSECUTIVE COMMITS. Each must leave
     the file coherent and each must independently satisfy N5 -- "every
     artifact this thread created or renamed is classifiable as
     conformant using naming.md alone." The F-07 re-wrap should be its
     own commit, landed FIRST and labelled explicitly as a no-op, so
     that the three semantic diffs are readable instead of buried in
     reflow noise.

A-4  RENAMES BREAK REFERENCES AND THE SWEEP MUST PRECEDE THE RENAME.
     F-21 is that sweep. It was run before any rename was proposed,
     and it is the reason OPEN-2 exists rather than a rename being
     assumed.

A-5  DELETING archive/README.md MAKES A LIVE DOCUMENT WRONG.
     implementation-plan.md T-011 will still list it. That document is
     status: outdated, which licenses it to be stale about its own
     plan, but the skeleton it describes is the one drill adopts. The
     amendment must be explicit in the handoff, not left for drill to
     notice.

A-6  CHANGING layers.md OR style-contract.md INVALIDATES EVERY RENDER.
     They are render sources. drill has a CONTEXT.md built from them
     and stamped with a content hash. The DEC-14 back-fill and the
     F-16 conflict resolution both force a drill re-render. This is a
     cross-repository consequence of a commit that looks local, and it
     belongs in the handoff.

A-7  THE WARN DEMOTION MUST NOT TOUCH THE FAILURE FLAG. check.sh gates
     on a flag file and exits 1 if it exists. A warn that still calls
     err() is not a warn. The distinction has to be structural, not
     cosmetic, or DEC-11 delivers nothing.

A-8  EMPTY DIRECTORIES VANISH WITHOUT COMMENT. git does not track them,
     so the top-level close/, handoff/ and archive/ disappear as their
     contents move or delete. That is the desired outcome, but it means
     "delete the now-empty directory" is not a step anyone can perform
     or verify; it happens or it does not.

A-9  THE F-16 CONFLICT CANNOT BE DEFERRED PAST DEC-14. Generating
     default_system_prompt.md from sources that contradict it produces
     a file that contradicts the working defaults it replaces. The
     patch-versus-complete-file question is decided in the same commit
     that back-fills, or the back-fill is not done.

A-10 plan-edits-PLAYBOOK-DESIGN-002.md IS ALREADY APPLIED. Its header
     says the edits were applied during Stage A Commit 2, and
     implementation-plan.md is the result. Under DEC-9 a spent
     document is deleted rather than shelved. But it carries four
     inbound references and it is the record of what changed and why.
     See OPEN-3.

--------------------------------------------------------------------------
DELIVERY
--------------------------------------------------------------------------

ADR-023 decided this, and its reasoning holds: a patch generated from a
throwaway git init has a fabricated unrelated root, so git am on the
real side either rejects it or applies against the wrong base and
corrupts provenance. The sandbox repository built for this thread is
exactly such a throwaway. So:

  MOVES AND DELETIONS -- explicit commands, not patches.
    git mv old new
    git rm path
    Rename detection in a diff is a heuristic; a command is not.

  EDITS -- unified diff, git apply-able, generated by diffing two real
    files rather than hand-authored, and verified with git apply
    --check against a clean copy of the baseline before it is sent.

  NEW AND HEAVILY REWRITTEN FILES -- complete file content plus the
    exact target path. check.sh under DEC-11 and DEC-12 is a rewrite,
    not an edit, and is delivered whole.

  EVERY COMMIT -- a complete suggested commit message following the
    commit-prefix grammar in naming.md: "playbook: <summary>", or
    "playbook: <plan-id> <summary>" once this plan's ids exist.

  THE AUTHOR COMMITS, in the real repository, against real HEAD.

  Each patch states the baseline it was built against, by the
  content-addressed subtree hash at the top of this document, so a
  mismatch is caught before application rather than after.

--------------------------------------------------------------------------
COMMIT SEQUENCE
--------------------------------------------------------------------------

One concern per commit; each parses, runs, and bisects.

  C-01  naming.md: re-wrap the five squashed lines. NO-OP -- no
        semantic change, formatting only. Landed first so the rule
        diffs that follow are readable.
  C-02  naming.md + kickoff.md + era-2026-q3.md: frontmatter carries
        the classification; ADR-033's premise amended (DEC-1, F-05).
  C-03  naming.md: frontmatter field set and the three-value status
        vocabulary (DEC-2, DEC-10).
  C-04  naming.md + era-2026-q3.md: N6-N8 descriptive segment; ADR-026
        closed (DEC-4, DEC-5).
  C-05  era-2026-q3.md + archive/README.md: retire archive/ repo-wide;
        amend ADR-012's middle clause only; record that its sharding
        trigger fired and is deferred (DEC-9, DEC-17, F-13, F-14).
  C-06  scripts/check.sh: full rewrite. Containment scoped to the
        toolkit layer; ceilings and token budgets demoted to warn;
        identifiers to S1; ADR-031's partial implementation recorded
        in a comment with the stamp-boundary reason (DEC-8, DEC-11,
        DEC-12, F-15). Tree green after this commit.
  C-07  create llm/{design,plan,handoff,close}/; move the close
        artifacts and handoffs in with descriptive segments; delete
        the emptied top-level close/ and handoff/.
  C-08  move the remaining root thread artifacts into llm/; add
        frontmatter to each (DEC-7).
  C-09  delete decisions/adr-proposals.md -- spent, zero references
        (F-10).
  C-10  consolidate the two claude-opus-4.8_ files into
        llm/refinements.md as RF-PLAYBOOK-NNN (DEC-13, F-09).
  C-11  back-fill layers.md and style-contract.md with the rules
        default_system_prompt.md carries and the sources lack; resolve
        the S23 / CONSTRAINT-005 conflict explicitly (DEC-14, F-16,
        A-9).
  C-12  regenerate default_system_prompt.md as R-C output; mark it
        generated (DEC-14).
  C-13  write protocol/thread-protocol.md against T-009, preserving
        R12 and R13 as cited (DEC-15, F-11).
  C-14  MANIFEST.md: document table and REQREAD lists.
  C-15  install the pre-commit hook; ADR-028 closed (A-2).

  C-01 through C-06 are rules and rulers. Nothing is renamed under a
  rule that has not landed, and nothing is measured by a ruler that is
  known wrong.

--------------------------------------------------------------------------
OUT OF SCOPE -- named, and staying out
--------------------------------------------------------------------------

  Drill. Not in this pack. It inherits DEC-8, DEC-9, DEC-10 and the
    A-6 re-render obligation through a handoff written at the end of
    this thread.
  The F-08 substitution residue in implementation-plan.md. Recorded,
    not repaired; the document is status: outdated and repairing prose
    inside it is a separate concern.
  The workflow-contract reconciliation against commit-planning.md. It
    needs the eleven drill documents, which are not here.
  Era sharding and index.md. Triggered, deferred, recorded (DEC-17).
  Recalibrating ceilings against measured data. There is no benchmark;
    DEC-11 is the honest response, and inventing numbers is not.

--------------------------------------------------------------------------
OPEN -- decide before the commits they gate
--------------------------------------------------------------------------

OPEN-1  (gates C-12) Where does render.md's R-C output live? render.md
        gives R-A and R-B a path (<project>/llm/) and gives R-C none;
        it is described only by where it is pasted. DEC-14 makes
        default_system_prompt.md an R-C artifact, which needs one.
        The kickoff half of this question is closed by DEC-18.

OPEN-4  (gates nothing; decide when convenient) naming.md is 229 lines
        against a 200-line ceiling (F-24). Split it, accept the warn,
        or recalibrate the ceiling once there is data? Splitting is
        out of scope for this thread and is not done unilaterally.

OPEN-2  (gates C-08) implementation-plan.md: rename or keep the name?

          1  Move to llm/plan/, KEEP the filename. Record the N6
             nonconformance with its reason. naming.md's own
             CLASSIFICATION NOTE covers this exactly: nonconformance
             of a pre-grammar artifact is recorded, not repaired.
             31 references survive. The name-collision argument for
             renaming assumed status: current, which F-06 disproves.
          2  Rename to llm/plan/playbook-toolkit-buildout.md and fix
             all 31 references. Conformant, and 18 of the 31 sit in a
             spent runbook, so most of the churn buys nothing.
          3  Rename and leave the references stale. Cheapest now,
             wrong later.

        RECOMMENDATION: 1.

OPEN-3  (gates C-08) plan-edits-PLAYBOOK-DESIGN-002.md is spent (A-10).
        Delete under DEC-9, or move to llm/plan/ with status: outdated?
        It has four inbound references and is the record of what Stage
        A changed. RECOMMENDATION: move, status: outdated -- DEC-9
        deletes what is removed, and this is superseded, not removed.
