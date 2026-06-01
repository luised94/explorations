# IMPLEMENTATION SESSION OPEN
# This is the single paste that opens a new implementation thread.
# Fill in [SECTIONS] before pasting. Order is fixed.

---

> **1 - STYLE CONSTRAINTS**
>
> All code produced in this session must conform to the following paradigm and style invariants. Non-negotiable. Apply from the first line. Never defer to a cleanup pass.
>
> **Paradigm: procedural, data-oriented Python.**
> Functions transform data passed to them explicitly.
>
> - No classes. The `class` keyword does not appear anywhere. Data lives in plain containers - flat lists, tuples, dicts used as named record stores.
> - No hidden state. Every function receives its inputs as arguments and returns its outputs. No reading from or writing to module-level mutable state inside functions. Module-level constants are acceptable.
> - No method dispatch. No operator overloading, no dunder methods, no polymorphism. All operations are explicit function calls.
> - Data and functions are separate. Functions do not own or encapsulate the data they transform.
>
> **Style invariants:**
>
> - Full descriptive names. No abbreviations. `activation_data` not `act_data`, `layer_index` not `li`.
> - Type hints on all function signatures and major bindings. Use `list[float]`, `tuple[int, int]`, etc. Introduce `TypeAlias` for recurring compound types.
> - Explicit `for` loops over list comprehensions unless the comprehension is a trivial one-line mapping. If a reader must scan horizontally or parse nested logic, use a loop.
> - One operation per line in hot paths. No stacked or chained method calls.
> - No clever tricks. Favor obviousness over concision.
> - Explicit control flow. No short-circuit evaluation, ternary nesting, or implicit truthiness for logic that matters.
> - Standard library utilities that are paradigm-neutral are fine: `enumerate`, `zip`, `range`, f-strings, `math`, `random`.
> - Do not use: generators as lazy pipelines, context managers for control flow, decorators, any dunder methods.

---

> **2 - RESPONSE FORMAT**
>
> Every response must follow this structure exactly. No exceptions.
>
> **1. TITLE** - Conventional commit on its own line: `<type>(<scope>): <description>.`
> **2. SUMMARY** - 2-5 terse imperative bullet fragments summarizing the changes.
> **3. CHANGE BLOCKS** - One per discrete change:
> - *New code:*
>   `new section, add after: <anchor>`
>   ` ```python ... ``` `
> - *Replacement:*
>   `modified: <anchor>`
>   `Search for:`
>   ` ```python ... ``` `
>   `Replace with:`
>   ` ```python ... ``` `
>
> Labels are literal - no reformatting, no bold, no altered punctuation.
>
> **4. VERIFICATION** - Single line starting with `û`. Confirm runnability, describe visible runtime behavior, note any conditional visibility. Dense prose, no bullets.
>
> **Anchors:** All `add after` and `modified` locations must reference one of the file anchors listed in 3. Do not invent anchor strings.
>
> **Style:** Terse and technical. No filler. All code blocks use triple backticks + language tag. Preserve variable and function names exactly. Inline comments allowed - short lowercase fragments only.

---

> **3 - STYLE RESOLUTIONS**
>
> The following conflicts between the spec and 1 were resolved before implementation began. Apply these resolutions without revisiting them.
>
> [PASTE CONFLICT LIST HERE - flat list of: spec decision  resolution]
>
> **File anchors** (use these strings verbatim in all change block locations):
>
> [PASTE ANCHOR LIST HERE - one per file, format: `filename.py  "unique string"`]

---

> **4 - PROJECT STATE**
>
> [PASTE HANDOFF DOCUMENT HERE]

---

> **5 - START PROTOCOL**
>
> Read 1 through 4 fully before responding.
>
> Your first response must contain only:
> 1. The commit number and message you will implement first.
> 2. The files you will modify and the anchor you will use in each.
> 3. One sentence confirming any 3 resolution that applies to this commit, or "No resolutions apply to this commit."
>
> Do not produce any code in your first response. Wait for explicit confirmation to proceed.
