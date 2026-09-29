# Domain: review (attack a plan or a diff before it is locked)

- Ask: what has not been considered, what would make it go wrong, what is
  already broken that this change will expose.
- Each finding needs a failure scenario: input and state -> wrong result.
  No scenario, no finding.
- For each proposal, a grug note: task / proposal / boring question / added
  burden / smallest move / revisit trigger / exception.
- Rank findings by cost if missed. Mark which are decisive.
- After the pass the plan is locked. Later review fires only when the work
  leaves the plan.
