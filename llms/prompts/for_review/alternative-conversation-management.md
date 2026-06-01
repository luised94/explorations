# Alternative Conversation Merge Frameworks

---

## FRAMEWORK 1 - Bayesian Belief Updating
# Most honest about what actually happens in LLM conversation synthesis.
# Each branch is evidence. Merging is updating beliefs, not combining states.

### Core metaphor
Prior = what the trunk currently believes about a design decision.
Likelihood = how strongly the branch evidence supports or contradicts that belief.
Posterior = the updated belief after seeing the branch.
Uncertainty = decisions where evidence is weak or contradictory.

### Prompt set

**B1 - Prior Elicitation** *(run in trunk before looking at branch)*
> For each open design decision in this thread, state the current belief and its strength:
> - *Strong prior*: decided, well-reasoned, would take significant evidence to overturn.
> - *Weak prior*: tentative, held for convenience, open to revision.
> - *No prior*: genuinely undecided, waiting for evidence.
>
> Output as a flat list: [decision] - [strong / weak / none] - [one-line rationale].

**B2 - Likelihood Assessment** *(run after reading branch summary)*
> For each decision in the prior list, assess what the branch evidence says:
> - *Confirms*: branch reasoning supports the current belief.
> - *Weakens*: branch raises doubts but does not overturn.
> - *Contradicts*: branch reached the opposite conclusion.
> - *New evidence*: branch addresses a decision not in the prior list.
>
> Do not update beliefs yet. This is observation only.

**B3 - Posterior Update** *(run after likelihood assessment)*
> Update each prior belief based on the likelihood assessment.
>
> Rules:
> - Strong prior + confirms = unchanged, confidence increases.
> - Strong prior + weakens = flag for human review, do not auto-update.
> - Strong prior + contradicts = hard conflict, requires human resolution.
> - Weak prior + any evidence = update toward the evidence.
> - No prior + new evidence = adopt as weak prior.
>
> Output: updated belief list. Flag all human-resolution items separately.

**B4 - Uncertainty Map** *(run after posterior update)*
> Which decisions remain genuinely uncertain after this update?
> For each uncertain decision, state: what evidence would resolve it,
> and whether that evidence comes from reasoning, building, or using.

---

## FRAMEWORK 2 - Fuzzy Logic Integration
# Useful when design decisions are not binary - when "it depends" is the real answer.
# Decisions have degrees of truth, not just true/false.

### Core metaphor
Membership value = how true a decision is in this context, from 0.0 to 1.0.
Aggregation = combining membership values from multiple branches.
Defuzzification = converting fuzzy beliefs into crisp implementation decisions.
Hedge = a modifier that shifts membership ("very flat" vs "somewhat flat").

### Prompt set

**F1 - Membership Assessment** *(run at end of any branch)*
> For each design decision this branch evaluated, assign a membership value
> representing how true the decision holds in the context explored:
>
> 1.0 = completely true, no exceptions found
> 0.7 = mostly true, minor edge cases
> 0.5 = equally valid either way, genuinely context-dependent
> 0.3 = mostly false in this context, exceptions exist
> 0.0 = false, contradicted by evidence
>
> Output: [decision] - [value] - [what drives the value up or down].

**F2 - Aggregation** *(run in trunk when combining multiple branch assessments)*
> Multiple branches have assessed the same decisions with different membership values.
> Aggregate using the following rules:
>
> - *Conservative merge* (AND): take the minimum value across branches.
>   Use when: decisions must hold universally, failure is costly.
> - *Permissive merge* (OR): take the maximum value across branches.
>   Use when: decisions need to hold in at least one context.
> - *Weighted merge*: average values weighted by branch relevance.
>   Use when: branches explored different but equally valid contexts.
>
> State which rule applies to each decision and why. Output aggregated values.

**F3 - Defuzzification** *(run before implementation)*
> Convert fuzzy beliefs into crisp implementation decisions.
>
> For each decision with its aggregated membership value:
> - Value >= 0.7: apply as written, no qualification needed.
> - Value 0.4-0.69: apply with explicit scope limitation.
>   State: "This decision holds when [condition]."
> - Value < 0.4: do not apply as a general rule.
>   State: "Default to [alternative], revisit if [condition] arises."
>
> Output: implementation-ready decision list with scope qualifications.

**F4 - Hedge Detection** *(optional, run on any decision list)*
> Identify decisions that are currently stated as binary but should be fuzzy.
> A decision is a candidate for hedging if:
> - It contains words like "always," "never," "all," "none."
> - It was reached without considering scale or context variation.
> - Two reviewers agreed on it for different reasons.
>
> For each candidate: propose the hedged version with a membership function.
> Example: "always use flat lists"  "prefer flat lists (0.8), use nesting when
> depth > 1 and traversal is the primary operation (0.6)."

---

## FRAMEWORK 3 - Mycelium Network
# Organic, emergent, anti-hierarchical. No trunk. No merge. Only growth.
# For when the git metaphor feels too mechanical for what's actually happening.

### Core metaphor
Strand = a conversation thread carrying nutrients (insights, decisions, questions).
Nutrient = a unit of knowledge: a decision, constraint, pattern, or open question.
Anastomosis = when two strands fuse naturally because they carry compatible nutrients.
Network density = how many strands have explored a region of the design space.
Fruiting body = an artifact (spec, prompt, tool) that emerges when density is sufficient.
Mycelium mat = the full knowledge network across all threads.

### Prompt set

**M1 - Strand Characterization** *(run at end of any thread)*
> Characterize this thread as a mycelium strand.
>
> **Nutrients carried** - what knowledge does this strand hold?
> List as: [nutrient type] - [content]
> Types: decision / constraint / pattern / open question / rejected approach / insight
>
> **Terrain explored** - what region of the design space did this strand grow through?
> One sentence describing the domain, problem, or question space.
>
> **Strand health** - how viable is this strand?
> - *Vigorous*: rich nutrients, clear direction, ready to fuse or fruit.
> - *Sparse*: few nutrients, exploratory, needs more growth before fusing.
> - *Tangled*: contradictory nutrients, needs decomposition before fusing.
>
> **Compatible strands** - which other threads does this strand likely connect with?
> Name by topic or thread, not by formal ID.

**M2 - Anastomosis** *(run when two strands meet)*
> Two strands are meeting. Assess whether fusion is possible.
>
> **Shared terrain** - where do the two strands overlap in the design space?
>
> **Compatible nutrients** - list nutrients that can fuse directly
> (same decision, same constraint, complementary insights).
>
> **Incompatible nutrients** - list nutrients that cannot fuse
> (contradictory decisions, conflicting constraints).
> Note: incompatibility is not failure. Incompatible nutrients signal
> where the design space has genuine tension - record it, do not resolve it.
>
> **Fusion result** - what does the fused strand carry that neither strand
> carried alone? This is the emergent nutrient - knowledge that only exists
> at the intersection.

**M3 - Network Density Check** *(run periodically across all threads)*
> Survey the mycelium mat.
>
> For each region of the design space being explored:
> - How many strands have passed through it?
> - What nutrients appear repeatedly across strands? (High density = likely true)
> - What terrain has only one strand? (Low density = uncertain, needs more growth)
> - Where are the gaps - terrain no strand has explored?
>
> Output: density map. High density regions are ready to fruit.
> Low density and gap regions need more exploration before artifacts emerge.

**M4 - Fruiting Conditions** *(run when considering producing an artifact)*
> Assess whether the network is ready to fruit in this region.
>
> Fruiting requires:
> - Sufficient density (multiple strands have explored this terrain)
> - Nutrient stability (the same decisions appear consistently across strands)
> - No unresolved tangled strands in this region
>
> If conditions are met: name the artifact that should emerge and its nutrient sources.
> If not: name what growth is needed before fruiting is possible.
>
> A fruiting body is not a merge. It is a new thing that the network made possible.
> It does not replace the strands that produced it.

---

## Framework Character Comparison

```
FRAMEWORK    CHARACTER          BEST FOR                    TONE
---------    ---------          --------                    ----
Bayesian     Epistemic          Tracking belief strength    Precise
             (what we believe)  and evidence weight

Fuzzy        Evaluative         Decisions that are          Practical
             (how true)         context-dependent

Mycelium     Structural         Emergent insight across     Organic
             (how it grows)     many threads, no clear trunk
```
---
# Alternative Conversation Merge Frameworks
# Each framework is an analogical heuristic - it borrows vocabulary and
# structure from its source domain to organize reasoning about conversation
# synthesis. It does not implement that domain formally. Outputs are
# structured approximations, not rigorous formal results.

---

## FRAMEWORK 1 - Bayesian Belief Updating
# Analogical heuristic: borrows from Bayesian inference.
# What it approximates: how evidence from a branch should shift
#   confidence in existing design decisions.
# What it cannot claim: actual probability values, formal priors,
#   or likelihood functions. Numbers produced are confidence labels,
#   not probabilities.

### Core metaphor
Prior = what the trunk currently believes about a design decision.
Likelihood = how strongly the branch evidence supports or contradicts it.
Posterior = the updated belief after seeing the branch.
Uncertainty = decisions where evidence is weak or contradictory.

### Prompt set

**B1 - Prior Elicitation** *(run in trunk before looking at branch)*
> This prompt uses Bayesian updating as an analogical heuristic to
> organize reasoning about design decisions. It does not compute
> real probabilities - "strong," "weak," and "none" are confidence
> labels, not formal priors.
>
> For each open design decision in this thread, state the current
> belief and its strength:
> - *Strong*: decided, well-reasoned, needs significant evidence to revise.
> - *Weak*: tentative, held for convenience, open to revision.
> - *None*: genuinely undecided, waiting for evidence.
>
> Output as a flat list: [decision] - [strong / weak / none] - [one-line rationale].

**B2 - Likelihood Assessment** *(run after reading branch summary)*
> This prompt uses Bayesian updating as an analogical heuristic.
> "Confirms," "weakens," and "contradicts" are structured labels
> for organizing evidence - not computed likelihoods.
>
> For each decision in the prior list, assess what the branch evidence says:
> - *Confirms*: branch reasoning supports the current belief.
> - *Weakens*: branch raises doubts but does not overturn.
> - *Contradicts*: branch reached the opposite conclusion.
> - *New evidence*: branch addresses a decision not in the prior list.
>
> Do not update beliefs yet. This is observation only.

**B3 - Posterior Update** *(run after likelihood assessment)*
> This prompt uses Bayesian updating as an analogical heuristic.
> Updates are structured judgments, not computed posteriors.
>
> Update each prior belief based on the likelihood assessment:
> - Strong + confirms = unchanged, confidence increases.
> - Strong + weakens = flag for human review, do not auto-update.
> - Strong + contradicts = hard conflict, requires human resolution.
> - Weak + any evidence = update toward the evidence.
> - None + new evidence = adopt as weak prior.
>
> Output: updated belief list. Flag all human-resolution items separately.

**B4 - Uncertainty Map**
> Which decisions remain genuinely uncertain after this update?
> For each: what evidence would resolve it, and does that evidence
> come from reasoning, building, or using the system?

---

## FRAMEWORK 2 - Fuzzy Logic Integration
# Analogical heuristic: borrows from fuzzy set theory.
# What it approximates: the degree to which a design decision holds
#   across different contexts - capturing "it depends" more honestly
#   than binary true/false.
# What it cannot claim: real membership functions, formal fuzzy
#   operators, or computed aggregations. Values 0.0-1.0 are
#   structured confidence labels, not mathematical set memberships.

### Core metaphor
Membership value = how true a decision holds in this context (0.0-1.0 label).
Aggregation = combining confidence labels from multiple branches.
Defuzzification = converting graded beliefs into crisp implementation decisions.
Hedge = a qualifier that scopes when a decision holds.

### Prompt set

**F1 - Membership Assessment** *(run at end of any branch)*
> This prompt uses fuzzy logic as an analogical heuristic. Values
> 0.0-1.0 are structured confidence labels, not computed set
> memberships. Use them to make confidence explicit and comparable,
> not to imply mathematical precision.
>
> For each design decision this branch evaluated, assign a label:
> 1.0 = holds completely, no exceptions found
> 0.7 = holds mostly, minor edge cases exist
> 0.5 = genuinely context-dependent, neither direction dominates
> 0.3 = holds in edge cases only, mostly does not apply
> 0.0 = does not hold, contradicted by evidence in this context
>
> Output: [decision] - [value] - [what drives the value up or down].

**F2 - Aggregation** *(run in trunk when combining multiple branches)*
> This prompt uses fuzzy logic as an analogical heuristic. Aggregation
> rules here are structured judgment guides, not formal fuzzy operators.
>
> Multiple branches have assessed the same decisions with different values.
> Choose the aggregation approach that fits the decision's stakes:
>
> - *Conservative* (take the minimum): use when the decision must hold
>   universally and failure is costly.
> - *Permissive* (take the maximum): use when the decision needs to hold
>   in at least one important context.
> - *Weighted* (average by relevance): use when branches explored
>   different but equally valid contexts.
>
> State which applies to each decision and why. Output aggregated values.

**F3 - Defuzzification** *(run before implementation)*
> This prompt uses fuzzy logic as an analogical heuristic to convert
> graded beliefs into scoped implementation decisions. Output is
> structured judgment, not a computed crisp set.
>
> For each decision with its aggregated value:
> - >= 0.7: apply as written, no qualification needed.
> - 0.4-0.69: apply with explicit scope.
>   State: "This decision holds when [condition]."
> - < 0.4: do not apply as a general rule.
>   State: "Default to [alternative], revisit if [condition] arises."

**F4 - Hedge Detection**
> This prompt uses fuzzy logic as an analogical heuristic to find
> decisions currently stated as binary that should be scoped.
>
> A decision is a candidate for hedging if it contains words like
> "always," "never," "all," or "none" - or if two reviewers agreed
> on it for different reasons.
>
> For each candidate: propose the hedged version with an explicit
> scope condition. Example: "always use flat lists" 
> "prefer flat lists (strong), use nesting when depth exceeds one
> level and traversal is the primary operation (weak)."

---

## FRAMEWORK 3 - Mycelium Network
# Analogical heuristic: borrows from mycorrhizal network behavior.
# What it approximates: how knowledge accumulates and connects
#   across many threads without a single authoritative trunk -
#   emergent rather than assembled.
# What it cannot claim: actual biological network properties.
#   "Density," "nutrients," and "fruiting conditions" are
#   metaphorical labels for knowledge coverage and readiness,
#   not measurable quantities.

### Core metaphor
Strand = a conversation thread carrying knowledge.
Nutrient = a unit of knowledge: decision, constraint, pattern, question.
Anastomosis = when two strands connect because they carry compatible knowledge.
Network density = how thoroughly a region of the design space has been explored.
Fruiting body = an artifact that emerges when density is sufficient.
Emergent nutrient = knowledge that exists only at the intersection of two strands.

### Prompt set

**M1 - Strand Characterization** *(run at end of any thread)*
> This prompt uses mycelium network growth as an analogical heuristic
> to characterize what a conversation thread produced and how it
> connects to others. "Nutrients," "terrain," and "health" are
> structured labels for knowledge content and coverage, not
> biological measurements.
>
> **Nutrients carried** - list as: [type] - [content]
> Types: decision / constraint / pattern / open question /
>        rejected approach / insight
>
> **Terrain explored** - one sentence: what region of the design
> space did this thread move through?
>
> **Strand health:**
> - *Vigorous*: rich nutrients, clear direction, ready to connect or produce an artifact.
> - *Sparse*: few nutrients, needs more exploration before connecting.
> - *Tangled*: contradictory nutrients, needs decomposition first.
>
> **Compatible strands** - which other threads likely share terrain?

**M2 - Anastomosis** *(run when two strands meet)*
> This prompt uses mycelium network fusion as an analogical heuristic
> for synthesizing two threads. "Compatible" and "incompatible"
> nutrients are structured judgments about which knowledge can be
> directly combined and which cannot. Incompatibility is not failure -
> it marks where the design space has genuine unresolved tension.
>
> **Shared terrain** - where do the two threads overlap?
>
> **Compatible nutrients** - knowledge that combines directly.
>
> **Incompatible nutrients** - knowledge that conflicts. Record it.
> Do not resolve it here.
>
> **Emergent nutrient** - what does the intersection reveal that
> neither thread produced alone? This is the synthesis finding.

**M3 - Network Density Check** *(run periodically across all threads)*
> This prompt uses mycelium network density as an analogical heuristic
> to assess how thoroughly different regions of the design space have
> been explored. "Density" is a structured judgment about coverage,
> not a measured quantity.
>
> For each region of the design space under exploration:
> - How many threads have passed through it?
> - Which nutrients appear repeatedly? (High coverage = more reliable)
> - Which terrain has only one thread? (Low coverage = uncertain)
> - What terrain has no thread? (Gap = unexplored)
>
> High coverage regions are candidates for producing artifacts.
> Low coverage and gaps need more exploration first.

**M4 - Fruiting Conditions** *(run before producing an artifact)*
> This prompt uses mycelium fruiting as an analogical heuristic for
> assessing whether enough knowledge has accumulated to produce a
> reliable artifact. "Fruiting conditions" are structured readiness
> criteria, not biological triggers.
>
> Readiness requires:
> - Sufficient coverage (multiple threads have explored this terrain)
> - Nutrient stability (the same decisions appear consistently)
> - No unresolved tangled strands in this region
>
> If ready: name the artifact and its nutrient sources.
> If not: name what exploration is needed first.
>
> A fruiting body is not a merge. It is something new the network
> made possible. It does not replace the strands that produced it.

---

## Framework Character Comparison

```
FRAMEWORK    CHARACTER          BEST FOR                    PRECISION CLAIM
---------    ---------          --------                    ---------------
Bayesian     Epistemic          Tracking belief strength    Confidence labels,
             (what we believe)  and evidence weight         not probabilities

Fuzzy        Evaluative         Decisions that are          Graded judgment,
             (how true)         context-dependent           not membership math

Mycelium     Structural         Emergent insight across     Coverage metaphor,
             (how it grows)     many threads, no trunk      not biology
```
