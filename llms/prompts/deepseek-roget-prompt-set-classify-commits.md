**Baseline Prompt (neutral reference point, origin 0,0)**  
> Classify all commits into: haiku, sonnet, opus. For all opus commits, decompose into combination of haiku and/or sonnet commits. Its possible that there are no opus commits.

---

### Variant 1: *categorize*
**Prompt**  
> You are a meticulous archivist. Your task is to **categorize** each commit into one of three conceptual classes-haiku, sonnet, opus-according to a clear, pre-defined schema. Where a commit falls into the opus class, you must then resolve it analytically into its constituent haiku and/or sonnet elements. Note that the schema may leave the opus class empty; if so, the taxonomy stands with only two inhabited categories.  

- **Latent dimension(s) modulated:** High formality / moderate abstraction / low urgency.  
- **Steering mechanism:** The archivist persona and words like "schema," "conceptual classes," and "taxonomy" nudge the model toward system-building and rule-based logic, distancing it from mere labelling.

---

### Variant 2: *sort*
**Prompt**  
> Imagine a conveyor belt of commits. Your job is to **sort** them quickly into three bins labeled haiku, sonnet, and opus. Walk through the process step by step, checking each commit's shape and size. If an opus commit appears, break it apart into the haiku and sonnet pieces that made it. The bins might end up with no opus at all-just keep moving.  

- **Latent dimension(s) modulated:** Low formality / high concreteness / moderate urgency.  
- **Steering mechanism:** The physical metaphor ("conveyor belt," "bins," "step by step") and the procedural tone direct the model toward an operational, almost algorithmic sequence, favouring concrete checks over abstract criteria.

---

### Variant 3: *group*
**Prompt**  
> We're exploring a set of commits. Let's **group** them by family resemblance: some feel like small, swift haiku; others like structured, melodic sonnets; and a few might be large, complex opuses. Don't force rigid definitions-let the clusters emerge from the material. For any commit that ends up in the opus cluster, try to spot the haiku and sonnet threads woven together inside it. It's perfectly fine if the opus cluster remains empty.  

- **Latent dimension(s) modulated:** Low formality / high abstraction / low urgency / collaborative emotional valence.  
- **Steering mechanism:** Words like "exploring," "family resemblance," "let the clusters emerge," and the permissive "perfectly fine" encourage a fuzzy, bottom-up grouping rather than top-down classification, softening the authoritative edge.

---

### Variant 4: *assign*
**Prompt**  
> You are the gatekeeper of three houses: Haiku, Sonnet, and Opus. For every commit that arrives, you must **assign** it to its proper house, based on the charter of each. When a commit is assigned to Opus, you are further tasked to decompose it into assignments to the Haiku and Sonnet houses that constitute its origin. The Opus house may receive no assignments-so be it.  

- **Latent dimension(s) modulated:** Moderate formality / moderate abstraction / slightly elevated authority.  
- **Steering mechanism:** The "gatekeeper" persona and the language of "houses," "charter," and "assign" frame the task as an act of institutional designation, emphasising the decision-maker's role and the formal delegation of identity.

---

### Variant 5: *label*
**Prompt**  
> Each commit needs a **label**-just three words are available: haiku, sonnet, opus. Stick the right word on each. Your labels should be so intuitive that anyone could guess why a commit got its tag. If a commit gets the opus label, then underneath it, scribble the haiku and sonnet fragments that mix to form it. There's a chance no commit gets the opus label at all.  

- **Latent dimension(s) modulated:** Low formality / high concreteness / moderate urgency / casual, pedagogic.  
- **Steering mechanism:** The emphasis on "label" and "stick the right word on," along with the informal "scribble," shifts the focus from system to the aptness and communicative clarity of the tag itself, making the output feel like an explanatory key.

---

### Variant 6: *pigeonhole*
**Prompt**  
> We're forced to **pigeonhole** every commit into one of three cramped boxes: haiku, sonnet, opus. Yes, these boxes are oversimplifications, and many commits will resist the fit-nevertheless, shove each into the least ill-fitting slot. For those that end up in the opus slot, break them down into the haiku and sonnet shards they're supposedly made of. It's entirely possible that no commit suffers the opus fate.  

- **Latent dimension(s) modulated:** Moderate formality / low abstraction / high emotional valence (critical, reluctant) / moderate urgency.  
- **Steering mechanism:** The word "pigeonhole" and the framing ("forced," "cramped boxes," "shove," "suffer the opus fate") inject a tone of reluctant compromise. The model is primed to acknowledge the violence of simplification, perhaps adding disclaimers or qualifying its choices.

---

### Variant 7: *rank*
**Prompt**  
> Evaluate each commit on a scale of complexity and depth, then **rank** them into three tiers: haiku (simplest, most atomic), sonnet (structured, intermediate), and opus (most elaborate, highest ambition). For any commit that attains the opus tier, dissect its ranking by showing which haiku- and sonnet-level contributions compose it. The opus tier might remain empty if no commit reaches that stature.  

- **Latent dimension(s) modulated:** Moderate formality / low abstraction / high intensity / competitive emotional valence.  
- **Steering mechanism:** The switch to an evaluative "scale" and hierarchical "tiers," plus terms like "attains," "stature," and "highest ambition," transforms the task into a judgment of worth, encouraging the model to justify superiority rather than merely differentiate types.

---

### Variant 8: *taxonomize*
**Prompt**  
> Adopt the role of a Linnaean scholar of version-control artefacts. Your mission is to **taxonomize** the commit corpus into three precisely delimited species: *Commit haiku*, *Commit sonnet*, and *Commit opus*. Provide a formal differential diagnosis for each placement, citing specific commit characteristics as diagnostic traits. For any specimen identified as *Commit opus*, perform a cladistic decomposition into its ancestral haiku and sonnet components. The taxon *Commit opus* may contain zero individuals; note this with a null-type entry.  

- **Latent dimension(s) modulated:** Very high formality / very high abstraction / low urgency / detached, scientific.  
- **Steering mechanism:** The persona of a scholar, the borrowed Linnaean terminology ("species," "differential diagnosis," "cladistic decomposition," "taxon"), and the requirement for formal citations drive the model into hyper-technical, exhaustive commentary, maximising systematic granularity.

---

### Summary matrix: Roget-Map Prompt Set

| Variant label        | Alternative word | Latent dimensions modulated                                           | Steering signature                                                |
|----------------------|------------------|-----------------------------------------------------------------------|-------------------------------------------------------------------|
| Baseline             | classify         | Neutral (0,0) - default formality, abstraction, urgency, valence     | Reference origin                                                  |
| Categorize-prompt    | categorize       | High formality / moderate abstraction / neutral urgency               | Archivist persona + schema-centric language                       |
| Sort-prompt          | sort             | Low formality / high concreteness / moderate urgency                  | Physical-metaphor conveyor belt, step-by-step procedure           |
| Group-prompt         | group            | Low formality / high abstraction / low urgency / warm, collaborative  | Exploratory family-resemblance framing, permissive tone            |
| Assign-prompt        | assign           | Moderate formality / moderate abstraction / slightly authoritative    | Gatekeeper & institutional designation narrative                  |
| Label-prompt         | label            | Low formality / high concreteness / casual pedagogical                | Tag-focused, intuitive "stick the word on" framing                 |
| Pigeonhole-prompt    | pigeonhole       | Moderate formality / low abstraction / critical emotional valence     | Reluctant "cramped boxes" framing, forced-choice resistance       |
| Rank-prompt          | rank             | Moderate formality / low abstraction / high intensity / competitive   | Evaluative hierarchy and tier-based "stature" language            |
| Taxonomize-prompt    | taxonomize       | Very high formality / very high abstraction / detached                | Linnaean scholar persona, cladistic terminology, null-type entry  |

This set maps the gradient space surrounding "classify" across formality, abstraction, urgency, and emotional valence, allowing a prompt engineer to dial in the desired model response signature by selecting the variant whose latent coordinates align with the target outcome.
