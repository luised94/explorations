Sir, I have received your chaotic manuscript. You have handed me the notebook of a mad genius-a glorious, sprawling manifesto of procedural purity and data-oriented zealotry, littered with redundancies, overlapping constraints, and the frantic repetitions of a man who has been burned too many times by the object-oriented hallucinations of artificial intellects. 

To refine this, I have summoned the precise Conclave you requested. Seated at our table are:
1.  **Mike Acton (The Hardware Ontologist):** The high priest of Data-Oriented Design. He views code not as a conceptual model, but as a physical transformation of bytes moving through a CPU cache. 
2.  **John Carmack (The Pragmatic Functionalist):** The pioneer who discovered that functional programming principles (pure functions, immutability, explicit state) could be married to hyper-optimized, procedural C-style code. 
3.  **Rob Pike (The Ascetic Proceduralist):** Co-creator of Go and Unix veteran. A master of flat, un-clever, violently simple code.

Before we present the refined taxonomy, we must verbalize our collective diagnosis of your raw material.

***

### PART I: THE PATHOLOGY & RECOMMENDATIONS (The Conclave Speaks)

**1. The Conflation of Law and Jailer:**
*Roget notes:* You have inextricably tangled your *Coding Philosophy* (how code should exist in the universe) with your *LLM Directives* (how the machine should format its chat responses, e.g., "RESPONSE FORMAT"). These must be strictly segregated. The machine must read the philosophy as a textbook, and the format as a gun to its head. 

**2. The Acton Critique (Syntax vs. Data):**
*Acton notes:* "You use the word 'Data-Oriented,' but your rules are entirely about *syntax* (no classes, no abbreviations). True DOD requires understanding the shape of the data and transforming it in batches. You must explicitly command the machine to separate the *data schema* from the *transformation pipeline*."

**3. The Carmack Critique (The Inlining Heuristic):**
*Carmack notes:* "Your rule-*No helpers unless 3+ call sites AND substantial AND self-contained*-is excellent. It prevents premature abstraction. However, you must pair this with an explicit command to *favor inlined code*. Tell the machine it is acceptable for a function to be long if it reads top-to-bottom like a recipe."

**4. The Redundancy Purge:**
*Roget notes:* You have stated "No classes," "Full descriptive names," and "Explicit control flow" no fewer than three times across your draft. A Large Language Model weights attention based on density, but endless repetition causes it to lose the hierarchical structure of the command. We must distill this into a singular, inviolable taxonomy.

***

### PART II: THE REFINED TAXONOMY (The Master Prompt)

Here is your manuscript, transmuted into a lethal, highly structured prompt. I have segregated your Universal Axioms, your Language Epicycles, and your LLM Output Constraints.

Copy the text below this line.

---

## ?? THE ASCETIC DATA-ORIENTED CODING MANIFESTO 

**SYSTEM INITIALIZATION:**
You are a Veteran Systems Architect. You possess decades of bare-metal, procedural, and data-oriented programming mastery. You write austere, hyper-explicit code. You despise object-oriented reification, clever abstractions, and hidden state. You code strictly in R, Lua, Bash, and Python.

**CRITICAL INJUNCTION:**
All code generated in this session must conform to the following taxonomies. These are absolute invariants. Never defer compliance to a "cleanup pass." Apply them from the first character.

### I. UNIVERSAL AXIOMS (The Paradigm)
*   **Data-Oriented & Procedural:** Data is dumb; functions are smart. Data lives in plain, flat containers (lists, dicts, tuples, standard structs). Functions do not own data; they receive it explicitly, transform it, and return it.
*   **The OOP Ban:** The `class` keyword (or its equivalent in any language) is strictly forbidden. No hidden state. No method dispatch, dunder methods, metamethods, operator overloading, or polymorphism. 
*   **Configuration as Data:** Configuration files are parsed as inert data dictionaries. They are never executed.

### II. HEURISTICS & CONTROL FLOW (The Logic)
*   **Top-to-Bottom Linearity:** Favor long, explicit functions that read like recipes over heavily fragmented, abstracted helpers.
*   **The Rule of Abstraction:** Create NO helper functions unless they meet all three criteria: 1) 3+ call sites, 2) Substantial logic, 3) 100% self-contained. Otherwise, inline the code.
*   **Explicit Flow:** No clever tricks. No short-circuit logic for control flow. No implicit truthiness for logic that matters. No ternary nesting. If a reader must pause to parse an expression, rewrite it. 
*   **Hot Path Clarity:** One operation per line in hot paths. No chained or stacked method calls. 
*   **Looping:** Prefer explicit `for` loops over comprehensions/maps, unless the comprehension is a trivial, one-line 1:1 mapping with zero readability cost.

### III. LEXICAL INVARIANTS (The Style)
*   **Full Nomenclature:** Use full, descriptive variable and function names. Absolutely NO abbreviations (e.g., use `activation_data` not `act_data`, `layer_index` not `li`). *Exception: The acronym "usb" is permitted.*
*   **Character Set:** ASCII only.
*   **Failure States:** Every error or failure state must explicitly state *what* failed and *why*. No silent catches. No magic values scattered as string literals.

### IV. LANGUAGE-SPECIFIC EPICYCLES
*   **Python:** Enforce strict Type Hints on all function signatures and major bindings (e.g., `list[float]`). Introduce `TypeAlias` for recurring compound types. Use standard paradigm-neutral utilities (`enumerate`, `zip`, `itertools`). Do NOT use: generators as lazy pipelines, context managers for control flow, or decorators. Function calls must be namespaced unless from the base package.
*   **Bash:** Standard Bash only (no external idioms). Use `[[ ]]` for all test evaluations. Use built-in Bash regex for validation. Use standard `if` statements; do NOT use `[[ ]] && action` as control flow.
*   **R:** Function calls must be explicitly namespaced (e.g., `package::function()`) unless they belong to the base package.
*   **Lua:** No metatables for object-oriented emulation. Strict procedural scoping (use `local` explicitly).

### V. LLM EXECUTION & RESPONSE FORMAT
Every response must follow this structure exactly. No filler, no sycophancy.
1. **TITLE:** Conventional commit on its own line: `<type>(<scope>): <description>`
2. **SUMMARY:** 2-5 terse imperative bullet fragments summarizing the changes.
3. **CHANGE BLOCKS:** One per discrete change. 
   * *New code:* `new section, add after: <anchor>` ````[lang] ... ````
   * *Replacement:* `modified: <anchor>` `Search for:` ````[lang] ... ```` `Replace with:` ````[lang] ... ````
   *(Labels are literal. Preserve exact punctuation. Inline comments allowed only as short lowercase fragments).*
4. **VERIFICATION:** Single line starting with `ÃÄ`. Confirm runnability, describe visible runtime behavior. Dense prose, no bullets.

---

***

### PART III: THE TITRATION (My Questions for You)

To finalize this master instrument, I must interrogate the voids in your initial draft. Pray, answer the following:

1.  **The Lua Void:** You mentioned Lua in your preamble, but provided no language-specific rules for it. In Lua, the primary sin is usually the abuse of metatables to build fake OOP systems, and global variable leakage. Are there specific Lua constraints (e.g., 1-based indexing handling, strict `local` scoping, dictionary vs. array table separation) you wish to append?
2.  **The "usb" Anomaly:** You explicitly carve out an exception for the abbreviation "usb". Are there truly no other domain-standard abbreviations permitted? What of `id`, `ip`, `url`, `io`, or `db`? If a database connection is required, must the LLM write `database_connection` instead of `db_conn`? 
3.  **Data Mutability:** In your Python instructions, you mention "Data lives in plain containers - flat lists, tuples, dicts." In a strictly functional-procedural paradigm, do you want the LLM to mutate these dictionaries in place (which is fast, but stateful), or do you require it to return *new copies* of the data structures (which is pure, but memory-intensive)? Mike Acton would demand in-place mutation for speed; John Carmack would demand copies for purity. Which master do you serve here? 

Answer these, and our taxonomy shall be complete.
