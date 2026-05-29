Peruse the attached documents. Cross-reference for:

1. Contradictions -- where do documents disagree on behavior, status
   values, field names, file targets, or command semantics? Name both
   sides and which should be authoritative.
2. Format mismatches -- are there data files with different formats
   that share consumers? Does every reader have a parser for the
   format it actually encounters?
3. Call site audit -- for every function the plan introduces, name
   its callers in this phase. Flag extractions with < 2 callers.
4. Redundant work -- are any commits already accomplished by earlier
   commits? Can any be absorbed into adjacent commits?
5. Unspecified behavior -- what must the code decide that no document
   addresses? (sort order for missing fields, default values, edge
   cases at boundaries)
6. Decisions to make -- list open design choices. For each, state the
   options, your recommendation, and what breaks if chosen wrong.

Verbalize suggested reconciliation for each finding. Organize by
severity: contradictions first, then design decisions, then
ambiguities, then minor issues. The goal is [SCOPE] and then
handoff to [TARGET].
