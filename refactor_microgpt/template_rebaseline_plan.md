Here are the remaining steps in the plan: 
[paste steps 8 onward].
Here is the current script: [paste file]. 
Identify which remaining steps have already been fully or partially implemented. For any that are already done, mark them as skip. For any partially done, describe what remains. Output a revised list of only the steps that still require changes.
## Phase 3: Generate the Transformation Plan

Produce a numbered sequence of atomic transformation steps. Each step simulates a single git commit - a minimal, self-contained edit that moves the codebase toward data-oriented style.

**Constraints on each step:**
- One to two sentences only. Use precise, domain-specific language (e.g., "flatten," "separate," "hoist," "inline," "replace indirection with offset," "convert AoS to SoA").
- Describe the *what* and *why* of the edit, not the code.
- Each step must leave the program functionally equivalent - output remains identical.
- Steps are ordered by dependency: later steps may depend on earlier ones, never the reverse.
- Group steps under labeled phases if natural groupings emerge.
- Each step must conform to the Code Style Invariants above. If a step introduces new functions or variables, the commit description should use the full descriptive names that will appear in the code.

**Do not write any code.** The output of this phase is the plan, not the implementation.

## Phase 4: Expert Review and Refinement

After generating the plan, simulate a single round of review from three experts. Each expert reads the full plan from Phase 3 and provides brief, pointed feedback - not a rewrite, but specific critiques, reorderings, or missing steps. The experts are:

**Mike Acton** (Data-Oriented Design, Insomniac/Unity)
Focus: Are the data layout decisions correct? Does the plan actually solve for the real access patterns, or does it just reorganize abstractions? Does any step introduce indirection or allocation that shouldn't be there? Is the hot path truly flat and linear by the end?

**John Carmack** (id Software, Oculus, practical engineering clarity)
Focus: Is the plan pragmatic? Are there steps that add complexity without measurable benefit in this context (pure Python, pedagogical, tiny model)? Is the code going to be *simpler* and more readable at the end, or just differently complex? Would he cut or merge any steps?

**Casey Muratori** (Handmade Hero, compression-oriented programming)
Focus: Does the plan follow a natural compression sequence - start with the straightforward version, then compress repeated patterns? Are there steps that prematurely abstract or over-structure? Should any steps be deferred because the pattern hasn't been proven yet?

After the three reviews, produce a **revised plan** that incorporates the feedback. Annotate any changes with a brief note indicating which reviewer's feedback motivated the change.
