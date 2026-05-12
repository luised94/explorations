# Data-Oriented Refactoring Pipeline

## Global Instructions

Apply the following rules in every step:

* Analyze the implementation strictly in terms of concrete data movement and transformation.
* Ignore abstractions unless they materially affect data flow.
* Treat classes, inheritance, naming conventions, patterns, and module boundaries as secondary representations, not ground truth.
* Distinguish clearly between:

  * **Constitutive facts**: correctness-critical invariants. Violating them changes or invalidates the computation.
  * **Contingent facts**: implementation choices, conventions, or organizational decisions that could change without affecting correctness.
* Do not invent architecture prematurely. Derive structure from the actual dependency graph.
* Prefer explicitness over elegance.
* When uncertain whether something is constitutive or contingent, justify the classification.

---

# Step 1 - REFERENCE MODEL

Read the script through a purely data-oriented lens.

Produce a flat reference model describing:

1. **Concrete data structures**

   * Exact types and shapes
   * Field/key relationships
   * Ownership and lifetime relationships
   * Mutable vs immutable data

2. **Concrete transformations**

   * Every transformation applied to the data
   * Input  output relationships
   * State transitions
   * Derived values

3. **True dependency order**

   * The actual execution/data dependency graph
   * What must exist before something else can be computed
   * Hidden dependencies and implicit coupling

4. **Invariant classification**
   For every important structural fact, classify it as:

   * **Constitutive**: logically/mathematically required for correctness
   * **Contingent**: replaceable without affecting correctness

Constraints:

* No refactoring proposals.
* No design critique.
* No code generation.
* Describe only what the implementation actually computes.

Output format:

* Flat, implementation-grounded description.
* No abstractions unless they correspond directly to concrete computation.

---

# Step 2 - DISENTANGLE

Compare the implementation structure against the Step 1 reference model.

Identify every place where the organization of the code misrepresents, obscures, or tangles the underlying data flow.

Specifically identify:

1. **Dislocated state**

   * State initialized in one location and consumed far away
   * Hidden state propagation
   * Implicit dependencies

2. **Conflated transformations**

   * Functions/methods performing logically independent operations
   * Mixed responsibilities at the data-transformation level
   * Coupled transformations that should vary independently

3. **Misaligned boundaries**

   * Class/module/function boundaries that do not correspond to data-flow boundaries
   * Organizational units that cut across dependency lines

4. **Misleading representations**

   * Naming that implies incorrect structure or ownership
   * APIs that conceal actual inputs/outputs
   * Control flow masking data flow

Constraints:

* No code.
* No redesign yet.
* Diagnostic only.
* Ground every observation in concrete data flow.

---

# Step 3 - DECOMPLECT

Using the Step 2 diagnostic, decompose the implementation into logically independent units.

A unit is independent if:

* It performs one coherent transformation.
* Its inputs and outputs are explicit.
* Its correctness depends only on its stated contract.
* Its internal implementation could change without requiring changes to other units.

Derive units from the data flow itself - do not impose architectural patterns.

For each unit, specify:

1. Purpose of the transformation
2. Explicit inputs
3. Explicit outputs
4. Required invariants on inputs
5. Side effects, if unavoidable
6. Upstream dependencies
7. Downstream dependents

Constraints:

* No code.
* No implementation details.
* No speculative abstractions.
* Keep units minimal but semantically complete.

---

# Step 4 - GENOCRIZE + ARCHITAXIZE

Take the units from Step 3 and formalize them into a strict dependency-ordered interface specification.

For every unit:

1. Classify all assumptions as either:

   * **Constitutive**: correctness-critical
   * **Contingent**: configurable or replaceable

2. Identify:

   * Parameters
   * Structural assumptions
   * Data-layout assumptions
   * Ordering assumptions
   * State assumptions

3. Arrange all units in strict dependency order:

   * Nothing appears before its prerequisites.
   * Reading order must match execution dependency order.

Produce:

* Function signatures only
* Typed arguments
* Explicit return types
* No implementations
* No hidden state
* No implicit dependencies

The resulting outline should read like a linearized computation graph.

---

# Step 5 - SYNHERIZE

Produce the fully refactored implementation.

Requirements:

1. Every unit from Step 4 becomes a pure or near-pure function.
2. All inputs are explicit function arguments.
3. All outputs are explicit return values.
4. No hidden state.
5. No mutation of external scope.
6. No implicit dependencies.
7. Persistent state must exist only as transparent data structures passed explicitly between functions.
8. The top-level program flow must visibly match the dependency order from Step 4.

Additional constraints:

* Preserve behavioral equivalence.
* Preserve numerical equivalence where applicable.
* Remove organizational structure that does not correspond to data flow.
* Favor transparent data pipelines over encapsulation.
* Keep transformations local and inspectable.

Output:

* Complete runnable code.

---

# Step 6 - PRESUPPOSE

Perform a recursive presuppositional analysis of the Step 5 implementation.

For every function:

1. Enumerate every assumption about:

   * Types
   * Shapes/dimensions
   * Value ranges
   * Key existence
   * Ordering
   * Nullability
   * Mutability
   * Device placement
   * Encoding/format
   * Resource availability
   * Any other implicit contract

2. Trace assumptions transitively:

   * If function A calls function B, then A inherits B's assumptions unless it validates them.

3. Classify every assumption as:

   * **Explicitly checked**

     * Guard/assertion exists.
   * **Implicitly assumed**

     * Violations cause confusing runtime failure.
   * **Invisibly baked in**

     * Violations silently produce incorrect results.

For every assumption include:

* The assumption itself
* Where it originates
* Where it propagates
* Failure mode if violated

Prioritize identifying silent correctness failures.

---

# Step 7 - HARDEN

Modify the Step 5 implementation using the findings from Step 6.

Requirements:

1. Add targeted assertions for all constitutive invariants.
2. Add lightweight guards for implicit assumptions.
3. Add warnings or configurable validation for contingent assumptions.
4. Ensure failures occur:

   * Early
   * Locally
   * With precise error messages

Constraints:

* Do not add heavy runtime overhead.
* Do not obscure the data flow.
* Assertions should clarify contracts, not clutter implementation.
* Preserve behavior for valid inputs.

Output:

* Final hardened implementation.

---

# Step 8 - SELF-EVALUATE

Critically evaluate the entire 7-step process.

Do not defend the methodology. Evaluate whether it actually improved the result.

Answer the following exactly:

### A. Reference model usage

Did the Step 1 reference model materially influence later steps?

* Identify specific downstream decisions it changed.
* If it did not meaningfully affect later work, state that directly.

### B. Constitutive vs contingent accuracy

List every fact classified as constitutive.
For each:

* Was it truly correctness-critical?
* Or was it actually a convention/design choice misclassified as essential?

Reclassify anything incorrect.

### C. Invisible assumptions audit

List every assumption classified as invisibly baked in.
For each:

* What concrete input violates it?
* What specifically happens?

  * Silent corruption
  * Wrong result
  * Crash
  * Benign handling

Demote any assumptions that were overstated.

### D. Cross-step coherence

Did later steps faithfully build on earlier analysis?
Identify:

* Where drift occurred
* Why it occurred

  * Forgetting
  * Context pressure
  * Revised understanding
  * Convenience

### E. Highest-value insight

Identify the single most valuable insight produced by the pipeline that would likely have been missed by a direct refactoring request.

If none exists, state that directly.

### F. Pipeline blind spots

Identify issues a skilled developer would likely catch manually that this process failed to surface.
Examples:

* Performance issues
* Operational concerns
* Edge cases
* Ergonomic problems
* Testing concerns
* Numerical stability
* Concurrency hazards

### G. Overhead verdict

Choose exactly one:

1. Clearly worth it
2. Marginally worth it
3. Not worth it

Justify the verdict directly and concretely.

Constraints:

* No hedging.
* No diplomatic language.
* No defending prior output.
* Prioritize accuracy over consistency.
* If a step added no value, say so plainly.
