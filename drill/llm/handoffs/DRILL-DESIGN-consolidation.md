HANDOFF -- drill/llm document consolidation
date: 2026-07
type: handoff
from: a playbook design thread that noticed the sprawl while closing an
      unrelated gate
to:   DRILL-DESIGN (a drill design thread; owns the keep/merge/retire
      calls)
self-contained: this handoff assumes ONLY the drill/llm directory. It
  references no external playbook. Every principle it relies on is
  stated inline below, because the intended way to act on it is to hand
  over drill/llm and nothing else. If you find yourself needing a
  document that is not in drill/llm to proceed, that is a finding to
  report, not a missing dependency to chase.

THE PROBLEM
  drill/llm holds roughly 51 markdown documents, and about 49 of them
  contain rule-like language -- "must", "never", "always", naming and
  convention statements, architectural constraints. This accumulated
  across many threads: roadmaps, findings, per-thread plans, launch
  kits, design notes, handoffs, and guides, several with dates in their
  filenames and several covering overlapping ground. One file even
  carries "conventions" in its name independent of the primary style
  document.
  Why this matters: when many documents state rules, no single document
  is authoritative, and a reader (human or thread) cannot tell which to
  follow. A recent incident made this concrete -- a thread handed the
  full directory followed a secondary document instead of the intended
  authority, and nobody noticed because the output still looked
  plausible. Sprawl is not just untidy; it silently redirects behavior.

THE APPROACH: MAP, THEN PLAN, THEN CONSOLIDATE
  Do these in order. Do not start merging files before the map exists;
  an unmapped merge is how duplication moves rather than disappears.

  1. MAP. Read every .md in drill/llm and build one table: filename,
     one-line purpose, category (live-status | decision-record | plan |
     handoff | guide | findings | rule-source | superseded), and
     "rules present? y/n". The map is the deliverable of this step --
     produce it and stop for review before planning. Expect to discover
     that several documents are stale snapshots of others.

  2. PLAN. From the map, assign each document one disposition:
       KEEP     -- a current, single-purpose authority. Name what it
                   is authoritative FOR.
       MERGE    -- fold into a KEEP target; record source and target.
       RETIRE   -- historical value only; move to an archive/ subtree
                   or reduce to a one-line pointer at the KEEP target.
                   Do not delete outright if it records a decision or
                   an incident -- history is worth keeping, just not in
                   the live set.
       SUPERSEDED -- already replaced; retire with a pointer.
     Produce the disposition table and stop for review before touching
     files. The keep/merge/retire calls are judgement and belong to the
     human, not to a blind pass.

  3. CONSOLIDATE. Execute the approved plan. The worked pattern to
     follow is a THREE-WAY SPLIT, which a prior consolidation used on a
     large style document: duplicated content is DROPPED (it already
     lives in the authority), genuinely specific content MOVES to the
     one file that should own it, and the emptied original is RETIRED
     to a pointer or archived. Apply the same discipline per document:
     nothing specific is lost, nothing duplicated is kept, and the
     original does not linger as a competing copy.

PRINCIPLES (stated inline so this handoff needs nothing external)
  - ONE AUTHORITY PER SUBJECT. For any given rule or fact, exactly one
    document is the place it lives. Others point to it; they do not
    restate it.
  - LIVE STATUS IN ONE PLACE. Whatever tracks current state (what is
    done, what is next, the test baseline) is the single source for
    that; no other document restates a status number, because two
    copies drift.
  - DATES BELONG IN THE DOCUMENT, NOT THE FILENAME. A filename with a
    date is a snapshot that invites a second dated snapshot beside it.
    Prefer a stable name plus a date inside the file. Existing
    date-named files are candidates to RETIRE or rename during
    consolidation.
  - HISTORY IS PRESERVED, NOT DELETED. Decisions and incident records
    are kept -- archived or pointed to -- so the reasoning survives even
    when the live set shrinks.
  - A DOCUMENT MUST CARRY ITS OWN AUTHORITY TO WHERE IT IS READ. If a
    file only makes sense alongside three others, either it states its
    own context or it is merged into the file it depends on. This is
    the lesson from the incident above.

WHAT NOT TO DO
  - Do not merge before the map and plan are reviewed. Unmapped merging
    hides duplication instead of removing it.
  - Do not delete anything that records a decision or an incident.
    Retire it; keep the history.
  - Do not create a NEW omnibus "conventions" document. The goal is
    fewer competing authorities, not one more.
  - Do not touch drill CODE or STATUS as part of this; this is a
    documentation consolidation, and the live status file stays the
    live status file.

OPEN QUESTION FOR THE HUMAN
  Where should retired documents live -- an archive/ subtree inside
  drill/llm, or pointers left in place? Decide at the PLAN step; it
  changes how RETIRE is executed.
