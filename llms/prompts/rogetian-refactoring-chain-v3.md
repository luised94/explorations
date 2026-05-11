Sir, I have reviewed your sequential apparatus. It is, at its core, a magnificent piece of cognitive engineering. You have essentially constructed a mechanical loom for the principles of Rich Hickey (decomplecting) and Mike Acton (data-first transformations). 

By forcing the machine to delay writing code until Prompt 5, you brilliantly starve its natural inclination to hallucinate premature abstractions.

However, as your Epistemological Triage Surgeon, I must note a severe localized pathology: **Neologism Toxicity**. 

What in the name of the Royal Society are *Genocrize*, *Architaxize*, and *Synherize*? These are linguistic chimeras-franken-words that will confuse the LLM's semantic associations, pulling its attention toward Greek root-word dictionaries rather than computer science theory. We must purge them and replace them with rigorous, standard taxonomical nomenclature. 

Furthermore, we must tether this chain explicitly to our newly forged **Ascetic Data-Oriented Coding Manifesto**. If we do not remind the machine of our style invariants at the moment of generation (Prompt 5), it will revert to its default, bloated OOP habits.

Here is the purified, domain-agnostic refactoring chain. I have renamed the phases to reflect their true mechanical nature and embedded the necessary stylistic constraints.

***

### ?? THE ROGETIAN REFACTORING CHAIN (v3.0)

**Usage Protocol:** 
1. Open a new, clean LLM thread. 
2. (Optional but recommended): Paste the **Ascetic Data-Oriented Coding Manifesto** as the System Prompt or first message to lock the paradigm.
3. Feed these prompts sequentially. Do not proceed to the next prompt until the machine has perfectly executed the current one.

---

### Phase I: Ontological Extraction (The Data Reality)
> **Directive:** Read the following script strictly through a Data-Oriented lens. Set aside all current abstractions (classes, inheritance, design patterns, naming conventions). Your sole objective is to identify the physical reality of the data.
> 
> **Output a Reference Model detailing:**
> 1. The concrete data structures (their types, shapes, and lifecycles).
> 2. The concrete mathematical/logical transformations applied to that data.
> 3. The true dependency order of these transformations.
> 4. Classify structural facts as either **Constitutive** (mathematically/logically necessary for correctness) or **Contingent** (arbitrary design choices that can be discarded).
> 
> *Do not write code. Output only the ontological reference model.*
> 
> **[PASTE RAW SCRIPT HERE]**

---

### Phase II: The Structural Audit (Disentanglement)
> **Directive:** Compare your Phase I Reference Model against the actual implementation in the script. 
> 
> **Output a Diagnostic Report identifying:**
> 1. Where the current organizational structure (class boundaries, method groupings, state management) obscures or tangles the true data flow.
> 2. State that is initialized in one location but consumed in a distant, logically unrelated location (hidden coupling).
> 3. Methods/functions that conflate logically independent transformations.
> 4. Naming conventions that lie about what is actually being computed.
> 
> *Do not write code. Output only the diagnostic report.*

---

### Phase III: Procedural Decomposition (Decomplecting)
> **Directive:** Based on your Phase II diagnostic, decompose the implementation into logically independent units (Pure Functions). A unit is independent if it performs a single data transformation, and altering its internals does not break any other unit (provided the input-output contract is maintained).
> 
> **For each unit, explicitly state:**
> 1. The exact data it receives (Inputs).
> 2. The exact data it produces (Outputs).
> 3. The Invariants (what must be true about the inputs for it to succeed).
> 
> *Do not predetermine these units based on the old code-derive them strictly from the data flow. Do not write code. Output only the decomposition.*

---

### Phase IV: Dependency Stratification (Topological Sort)
> **Directive:** Take the separated units from Phase III. Strip away all **Contingent** assumptions. Arrange all units into a strict topological dependency order (nothing may appear before the data it relies upon). 
> 
> **Output a Sequential Outline:**
> Provide function signatures with fully typed argument lists and return types. The reading order of these signatures must exactly match the execution pipeline. 
> 
> *Do not write implementation bodies. Output only the typed signatures in strict sequential order.*

---

### Phase V: The Ascetic Synthesis (Code Generation)
> **Directive:** Produce the full refactored script based on the Phase IV outline. 
> 
> **Critical Constraints:**
> * You must adhere strictly to the rules of Ascetic Data-Oriented Procedural Programming.
> * The `class` keyword (and all OOP paradigms) is strictly forbidden. 
> * All units must be pure functions. Data is passed explicitly; results are returned explicitly. No hidden state. No module-level mutation.
> * Use full, descriptive names. No abbreviations.
> * The top-level execution flow must read as a linear, flat procedural pipeline matching your Phase IV outline.
> 
> *Output the full, runnable code.*

---

### Phase VI: Vulnerability Mapping (Recursive Presupposition)
> **Directive:** Take the code you generated in Phase V and perform a recursive presuppositional analysis. 
> 
> **Trace the Implicit Contracts:**
> For every function, list the assumptions it makes about its inputs (shapes, types, value ranges, key existence, ordering). Trace these transitively (if Function A calls Function B, A inherits B's assumptions).
> 
> **Classify each assumption as:**
> 1. *Explicitly Checked* (A guard/assertion already exists).
> 2. *Implicitly Assumed* (Violation causes a loud runtime crash).
> 3. *Invisibly Baked-In* (Violation silently produces mathematically/logically incorrect data).
> 
> *Do not write code. Enumerate the findings, paying special attention to Category 3.*

---

### Phase VII: The Hardening Pass (Guard Implementation)
> **Directive:** Apply targeted guard clauses to the Phase V code to address the vulnerabilities identified in Phase VI.
> 
> **Hardening Constraints:**
> * Follow the "Fail Fast" rule: Place guards at the absolute top of the logic section.
> * For **Constitutive** invariants, hard assertions or strict errors are mandatory.
> * For **Contingent** assumptions, use warnings or configurable checks.
> * Keep assertions lightweight. They must not add algorithmic complexity or ruin the performance of hot paths. Every failure must explicitly state *what* failed and *why*.
> 
> *Output the final, hardened script.*

***

### The Titration Continues

Notice how Phase V now explicitly bans OOP and demands descriptive names, syncing perfectly with our Manifesto. Notice how Phase VII invokes the "Fail Fast" rule we formalized earlier. 

Your toolkit is becoming a unified ecosystem. 

What remains in your archives, Sir? Do we have guidelines for version control, database schemas, or perhaps the structuring of terminal outputs? Bring them to the table. Let us process them through the machine.
