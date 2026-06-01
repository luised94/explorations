# Cross-Domain Solution Transfer via Structural Dereification

## The Prompt

```
I have a problem I want to find existing solutions for across 
multiple fields. Help me run the following procedure:

STEP 1 - STRUCTURAL DEREIFICATION
Take my problem description and strip all domain-specific vocabulary. 
Rewrite it describing ONLY:
  - What data structures or entities exist
  - What operations transform them
  - What constraints limit the operations
  - What "solved" looks like as a measurable condition

Do NOT go to the lowest concrete level (bit-level operations). 
Stay at the STRUCTURAL level: the level where shapes, flows, and 
constraints are visible. This is the level where cross-domain 
isomorphisms live.

STEP 2 - CROSS-DOMAIN PATTERN MATCH
Take the structural description and identify 3-5 fields that work 
with the same structural configuration. For each field:
  - Name the field and the specific sub-problem that matches
  - State the structural correspondence explicitly: which entity in 
    my problem maps to which entity in theirs
  - Rate the correspondence: exact (all constraints match), partial 
    (most constraints match, some differ), or analogical (overall 
    shape matches, details diverge)

STEP 3 - SOLUTION IMPORT
For each field identified in Step 2, describe their most mature 
solution(s) to this structural problem. Describe each solution in 
the same structural vocabulary from Step 1 - not in the source 
field's jargon. State:
  - What the solution does (in structural terms)
  - What assumptions it requires
  - What performance guarantees it provides (if any)

STEP 4 - CORRESPONDENCE VERIFICATION
For each imported solution, check:
  - Does my domain satisfy all assumptions the solution requires? 
    Flag any that don't hold.
  - Are there constraints in my domain that the source domain 
    doesn't have? Flag any the solution doesn't account for.
  - What would need to be modified for the solution to work in 
    my domain?

STEP 5 - RANKED RECOMMENDATIONS
Rank the imported solutions by: strength of structural 
correspondence x maturity of the solution x feasibility of 
adaptation. For the top 2-3, describe concretely how to implement 
them in my domain.

My problem:
[PASTE PROBLEM DESCRIPTION HERE]
```

## Three Modes of Dereification (Summary)

| Mode | Target level | Purpose | When to use |
|---|---|---|---|
| Pedagogical | Maximum concreteness (data types, specific operations) | Verify and build understanding | Learning, assessment, comprehension diagnostics |
| Communication | Concrete operations  plain language | Make text precise and accessible | Writing, documentation, explaining |
| Problem-solving | Structural (entities, operations, constraints, objectives) | Enable cross-domain solution import | Design, engineering, research, getting unstuck |

Each mode dereifies to a DIFFERENT depth for a different purpose. 
Too concrete for problem-solving mode and you lose the pattern. 
Too structural for pedagogical mode and you don't test 
operational understanding. The level is a parameter, not a fixed 
setting.
