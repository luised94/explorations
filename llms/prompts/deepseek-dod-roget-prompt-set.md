Below is a systematic prompt set built from the Roget-style lexical analysis. Each variant is a deliberate composition that shifts the language model's response along latent dimensions-intensity, formality, abstraction, emotional valence, and urgency. The baseline prompt serves as the neutral origin (0,0). All other prompts are crafted to move the model into a distinct semantic region, using far more than a single-word swap.

---

### 1. Baseline Prompt (Neutral Reference Point)
**Prompt**  
`Adopt data-oriented procedural-with-strategic-functional programming perspective. Read, analyze, and summarize the following:`  
*This is the original, unaltered prompt. It occupies coordinate (0,0) in the map-moderate intensity, moderate formality, moderate abstraction, neutral valence, and default urgency.*

---

### 2. Prompt Variants with Latent Steering

#### Variant A: **examine**
**Full prompt**  
`Take a data-oriented procedural-with-strategic-functional programming perspective. Calmly read, examine, and summarize the following, offering a balanced, descriptive overview without strong judgments.`

- **Alternative word:** examine  
- **Primary latent dimension(s) modulated:** Low intensity / Low abstraction / Neutral valence  
- **Steering mechanism:** The adjectives "calmly" and "balanced, descriptive overview" flatten the emotional pitch and reduce analytical drive. The instruction to avoid "strong judgments" suppresses evaluative language, pulling the model into a more passive, explanatory register.

---

#### Variant B: **scrutinize**
**Full prompt**  
`Adopt a data-oriented procedural-with-strategic-functional programming perspective. Read, scrutinize, and summarize the following with a forensic, fault-finding eye. Your summary must flag every inconsistency, weakness, or hidden error. Be unsparing.`

- **Alternative word:** scrutinize  
- **Primary latent dimension(s) modulated:** High intensity / Negative valence / Elevated urgency  
- **Steering mechanism:** "Forensic, fault-finding eye," "flag every inconsistency," and "be unsparing" dial up the adversarial and urgent tone. The prompt primes the model to adopt a prosecutorial stance, skewing its output toward critique and defect detection.

---

#### Variant C: **dissect**
**Full prompt**  
`Using a data-oriented procedural-with-strategic-functional programming lens, read, dissect, and summarize the following. Break it down into its constituent parts with surgical precision. Present the structural decomposition in clean, anatomical layers; subordinate interpretation to the architecture.`

- **Alternative word:** dissect  
- **Primary latent dimension(s) modulated:** High intensity / High formality / Moderate abstraction (structural focus)  
- **Steering mechanism:** "Surgical precision," "anatomical layers," and "subordinate interpretation to the architecture" impose a clinical, almost laboratory style. The model is pushed away from synthesis and meaning-making toward a meticulous, value-neutral disassembly.

---

#### Variant D: **parse**
**Full prompt**  
`Adopt a data-oriented procedural-with-strategic-functional programming perspective. Read, parse, and summarize the following by delineating its syntactic or logical structure, as you would when generating a formal parse tree or a grammar. Maintain a cold, academic register; avoid any interpretive commentary.`

- **Alternative word:** parse  
- **Primary latent dimension(s) modulated:** High formality / High abstraction / Low emotional valence  
- **Steering mechanism:** "Formal parse tree," "syntactic or logical structure," and "cold, academic register" elevate both formality and abstraction. The explicit ban on interpretive commentary forces the model to operate at the level of symbolic or grammatical structure, yielding output that is schematic and dispassionate.

---

#### Variant E: **deconstruct**
**Full prompt**  
`Embrace a data-oriented procedural-with-strategic-functional programming perspective, and simultaneously apply a deconstructive lens. Read, deconstruct, and summarize the following text to expose the hidden assumptions, binary oppositions, and ideological tensions that hold it together. Let the summary reveal the instability of its apparent meanings.`

- **Alternative word:** deconstruct  
- **Primary latent dimension(s) modulated:** High abstraction / Negative valence (critical) / Moderate intensity  
- **Steering mechanism:** "Deconstructive lens," "hidden assumptions," "binary oppositions," and "instability of meaning" explicitly invoke post-structuralist analysis. The model is steered toward interrogating philosophical and political underpinnings, producing a humanities-style critique rather than a technical summary.

---

#### Variant F: **inspect**
**Full prompt**  
`Adopt a data-oriented procedural-with-strategic-functional programming perspective. Read, inspect, and summarize the following against an implicit compliance checklist. Itemize how each component adheres to (or deviates from) the expected standards; keep the output orderly, official, and audit-ready.`

- **Alternative word:** inspect  
- **Primary latent dimension(s) modulated:** High formality / Low abstraction / Slightly negative valence (audit mindset)  
- **Steering mechanism:** "Compliance checklist," "itemize," "adheres to standards," and "audit-ready" invoke bureaucratic oversight. The prompt forces a rigid, tick-box assessment, suppressing fluid interpretation and making the response feel procedural and impersonal.

---

#### Variant G: **probe**
**Full prompt**  
`Adopt a data-oriented procedural-with-strategic-functional programming perspective. Read, probe, and summarize the following by asking penetrating questions that go beneath the surface. Your summary should be inquisitive, tentative, and exploratory-revealing what is not immediately visible and leaving some tensions open rather than resolving them.`

- **Alternative word:** probe  
- **Primary latent dimension(s) modulated:** High intensity / Positive-curiosity valence / High urgency / Moderate abstraction  
- **Steering mechanism:** "Penetrating questions," "beneath the surface," "inquisitive, tentative, exploratory," and "leaving tensions open" cultivate a detective-like, questioning posture. The model is likely to produce hypothesis-rich text with a sense of forward motion and unresolved possibilities.

---

#### Variant H: **evaluate**
**Full prompt**  
`Adopt a data-oriented procedural-with-strategic-functional programming perspective. Read, evaluate, and summarize the following by assigning a clear judgment of quality, value, or significance. Rank the elements from most to least important and justify your evaluations with conviction.`

- **Alternative word:** evaluate  
- **Primary latent dimension(s) modulated:** High intensity / Low abstraction / Strong positive valence (or clear polarity) / Moderate urgency  
- **Steering mechanism:** "Assigning a clear judgment," "rank the elements," and "justify with conviction" shift the task from neutral description to explicit appraisal. The model will produce a value-laden, hierarchy-conscious output that reads as a recommendation or critique.

---

### 3. Summary Matrix: Prompt Latent Coordinates

All values are expressed **relative to the baseline** (0 = same as baseline moderate setting). Scale roughly from -2 (very low) to +2 (very high). Valence sign indicates direction: + = positive/affirming, - = negative/critical.

| Prompt Variant | Intensity | Formality | Abstraction | Valence | Urgency |
|----------------|-----------|-----------|-------------|---------|---------|
| **Baseline (analyze)** | 0 | 0 | 0 | 0 | 0 |
| **examine** | -1 | 0 | -1 | 0 (neutral) | -1 |
| **scrutinize** | +2 | +1 | 0 | -1 (critical) | +1 |
| **dissect** | +2 | +2 | +1 | 0 (clinical) | 0 |
| **parse** | +1 | +2 | +2 | 0 (neutral) | 0 |
| **deconstruct** | +1 | 0 | +2 | -1 (skeptical) | 0 |
| **inspect** | +1 | +2 | -1 | -0.5 (audit) | 0 |
| **probe** | +2 | 0 | +1 | +0.5 (curious) | +1 |
| **evaluate** | +2 | 0 | -1 | +1 (judgmental) | 0 |

**Usage:** To select a prompt variant, decide which response signature you need-e.g., for a dry, structural breakdown, choose **parse** or **dissect**; for an adversarial critique, choose **scrutinize**; for an open-minded exploration, pick **probe**. Each full prompt text has been engineered to enforce those coordinates through framing, register, and explicit tonal instructions, not just lexical substitution.
