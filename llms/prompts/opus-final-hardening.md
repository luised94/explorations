To perform final hardening, run the following analyses in order.
Each must produce zero or more concrete actions 
(assertion | error_handling | comment | documentation | test | refactor):

1. Prerequisite analysis - What must be true before entry?
2. Assumption analysis - What do we believe but never validate?
3. Presupposition analysis - What does the code silently depend on?
4. Invariant analysis - What must hold true at all times during execution?
5. Entailment analysis - What downstream truths does this code force?
6. Boundary/edge case analysis - What inputs or states were under-considered?
7. Failure mode analysis - How does this fail, and is the failure graceful?
8. Bug encounter review - What broke during implementation that could recur?
9. Cognitive decay analysis - What will the next reader 
   (or future you) fail to understand?

Collect all actions. Deduplicate. Group by file. Apply.
