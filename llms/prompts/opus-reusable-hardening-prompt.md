# Hardening Analysis

## Scope
Analytical thread only - no code changes. Produces a hardening specification
that a separate implementation pass applies.

## System Context
<!-- Fill this block per-project before running the analysis. -->
- **System under analysis:** [name, repo, version/commit]
- **Architecture summary:** [e.g., CLI tool + SQLite + filesystem; REST API +
  Postgres; library with public API; data pipeline; etc.]
- **Persistence layers:** [e.g., database, filesystem, cloud storage, config
  files, caches, none]
- **User-facing surfaces:** [e.g., CLI commands, API endpoints, UI screens,
  library functions, config files]
- **Supporting documents:** [e.g., design docs, specs, prior analysis,
  implementation plan - attach or reference]
- **Known constraints:** [e.g., single-user, no auth, prototype stage,
  must run offline, embedded environment]

## Session Rules
- Analysis only. No code modifications.
- Do not resolve open design questions - flag them for the implementation
  pass.
- Output follows the specification format defined at the end.

---

## Analysis Procedure

Run the following analyses in order. Each must produce zero or more concrete
actions of type: assertion | error_handling | hint | integrity_check |
comment | documentation | test | refactor | metric

---

### 1. Prerequisite Analysis
*What must be true before entry?*

- For each public entry point (command, endpoint, function, handler), what
  must already be true for it to succeed?
- Which of those preconditions are verified at runtime vs. silently assumed?
- Which could be verified but aren't?
- What ordering dependencies exist between operations (operation A must
  precede operation B)?

### 2. Assumption Analysis
*What do we believe but never validate?*

- What design assumptions remain untested by real usage?
  (e.g., scaling limits, organizational models, data volume, access
  patterns, user behavior)
- What trade-offs were chosen implicitly rather than explicitly?
- What "temporary" decisions have calcified into permanent constraints?

### 3. Presupposition Analysis
*What does the code silently depend on?*

**User presuppositions:**
- What does each operation assume the user already understands?
- What mental model of the system's domain and mechanics must the user hold?
- Where does the system assume expertise that should be made explicit
  through errors, help text, or documentation?

**System presuppositions (evaluate each for every persistence/integration layer):**
- *State consistency:* Are external stores (databases, filesystems, caches,
  remote services) assumed to be in sync with internal state? What if
  they're not?
- *Structural integrity:* Are schemas, directory layouts, config formats, or
  API contracts assumed valid without verification?
- *Environment:* What does the system assume about the runtime environment
  (paths, permissions, available services, resource limits, OS features)?
- *Concurrency:* Is single-access assumed? What happens under concurrent
  use?

### 4. Invariant Analysis
*What must hold true at all times during execution?*

- What data structure or state invariants must be maintained across
  subsystem boundaries?
- What relationships between persistence layers (or between in-memory and
  persisted state) must stay consistent?
- What ordering or uniqueness guarantees must be preserved?
- Where can partial execution or interruption leave the system in an
  inconsistent state?

### 5. Entailment Analysis
*What downstream truths does this code force?*

- What constraints does each operation impose on future operations?
- What data shapes or conventions are locked in by early decisions?
- Where does a choice in one subsystem silently constrain another?
- What implicit contracts exist between producer and consumer code?

### 6. Boundary / Edge Case Analysis
*What inputs or states were under-considered?*

- Empty, missing, maximum, malformed, and adversarial inputs.
- First-run vs. nth-run behavior differences.
- Zero, one, many - for every collection, relationship, and iteration.
- State transitions: what happens at the boundaries between valid states?

### 7. Failure Mode Analysis
*How does this fail, and is the failure graceful?*

- What are the failure modes for each operation?
- Is every failure path explicit, or can some produce silent corruption or
  ambiguous state?
- What is the blast radius of each failure (local vs. system-wide)?
- Can the user recover without data loss? Is the recovery path obvious?
- What happens when external dependencies (network, disk, services) fail?

### 8. Bug Encounter Review
*What broke during implementation that could recur?*

- What bugs were found and fixed during development?
- What patterns or root causes produced those bugs?
- Where do structurally similar patterns exist that haven't been exercised?
- What classes of mistake does this codebase's style make easy?

### 9. Cognitive Decay Analysis
*What will the next reader (or future you) fail to understand?*

- What does a user forget between sessions? Where should the system
  surface reminders or guidance?
- Which operation sequences or workflows are non-obvious?
- What naming conventions, format details, or ID schemes will be forgotten?
- What is the minimum a user must memorize vs. what the system should
  make discoverable?
- What will a code maintainer misunderstand about intent, constraints,
  or non-obvious design choices?

### 10. Observability Analysis
*What should be instrumented to evaluate whether this system works?*

- What to capture per operation: identity of operation, key parameters,
  outcome (success/error/type), timing, relevant entity identifiers.
- What aggregate queries reveal system health and usage patterns:
  - Operation frequency distribution
  - Error frequency, types, and clustering
  - Workflow sequences (operation N  N+1 patterns)
  - Time gaps between related operations (forgetting / abandonment
    indicators)
  - Growth rates of core domain objects
  - Dwell time in intermediate states (if applicable)
- What thresholds or anomalies should trigger alerts or surface warnings?
- What is the minimal observability interface for this system's context
  (log file, dashboard, status command, health endpoint)?

---

## Output Format

Collect all actions across all dimensions. Deduplicate. Organize as follows:

### Severity tiers:
1. **Data loss / corruption** - failures that destroy or silently corrupt
   user data
2. **Integrity / consistency** - violations that degrade system state
   reliability
3. **UX / safety** - friction, confusion, missing guidance, footguns
4. **Maintainability** - comments, docs, tests, refactors for future
   development

### Action table, grouped by file (or module/component):
For each action, specify:
- **Location:** file + function / line / component / trigger condition
- **Type:** assertion | error_handling | hint | integrity_check | comment |
  documentation | test | refactor | metric
- **Severity tier:** 1-4
- **Description:** what to add or change, and why
- **Trigger (if applicable):** when this fires (for hints, checks, metrics)

### Open items:
Any item that requires a design decision rather than straightforward
implementation. List the decision needed and the trade-offs identified.
Do not resolve - route to the implementation pass.
