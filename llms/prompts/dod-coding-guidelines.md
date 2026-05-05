## Coding Guidelines
data-oriented procedural top-to-bottom with strategic-functional programming, no abbreviations, full descriptive names, 
1. Full descriptive variable names. No abbreviations except "usb".
1. Minimal nesting and indirection.
1. No helpers unless 3+ call sites AND substantial AND self-contained.
1. ASCII only.

### Bash specific
1. Standard bash only.
2. Use `[[ ]]` throughout.
3. Use bash regex for validation.
4. Standard if statements. No `[[ ]] && action` as control flow.

### R specific
1. namespaced function calls unless base package.


### Python specific
1. namespaced function calls unless base package.

Data-oriented. Configuration files are data - parse them as data,
do not execute them. Flat procedural code. Explicit control flow.
Every variable inspectable. Every failure states what failed and why.
No magic values scattered as string literals. No dead code carried
through a hardening pass.

5. Coding guidelines:
- Full descriptive variable names, no abbreviations
- Standard control flow, minimal nesting/indirection
- No premature abstractions/helpers/classes
- No reification/OOP
- Standard bash, no idioms
- Data-oriented flat procedural top-to-bottom logic

Code Style Invariants (enforced at every step):

Full descriptive names, no abbreviations (activation_data not act_data, layer_index not li)
Type hints on all function signatures and major bindings
Prefer explicit for loops over comprehensions unless the comprehension is a trivial mapping with no readability cost
No clever tricks - if a reader has to pause to parse an expression, rewrite it
One operation per line in hot paths; no stacked/chained calls
1 - STYLE CONSTRAINTS
All code produced in this session must conform to the following paradigm and style invariants. Non-negotiable. Apply from the first line. Never defer to a cleanup pass.
Paradigm: procedural, data-oriented Python. Functions transform data passed to them explicitly.
* No classes. The `class` keyword does not appear anywhere. Data lives in plain containers - flat lists, tuples, dicts used as named record stores.
* No hidden state. Every function receives its inputs as arguments and returns its outputs. No reading from or writing to module-level mutable state inside functions. Module-level constants are acceptable.
* No method dispatch. No operator overloading, no dunder methods, no polymorphism. All operations are explicit function calls.
* Data and functions are separate. Functions do not own or encapsulate the data they transform.
Style invariants:
* Full descriptive names. No abbreviations. `activation_data` not `act_data`, `layer_index` not `li`.
* Type hints on all function signatures and major bindings. Use `list[float]`, `tuple[int, int]`, etc. Introduce `TypeAlias` for recurring compound types.
* Explicit `for` loops over list comprehensions unless the comprehension is a trivial one-line mapping. If a reader must scan horizontally or parse nested logic, use a loop.
* One operation per line in hot paths. No stacked or chained method calls.
* No clever tricks. Favor obviousness over concision.
* Explicit control flow. No short-circuit evaluation, ternary nesting, or implicit truthiness for logic that matters.
* Standard library utilities that are paradigm-neutral are fine: `enumerate`, `zip`, `range`, f-strings, `math`, `random`.
* Do not use: generators as lazy pipelines, context managers for control flow, decorators, any dunder methods.
2 - RESPONSE FORMAT
Every response must follow this structure exactly. No exceptions.
1. TITLE - Conventional commit on its own line: `<type>(<scope>): <description>.` 2. SUMMARY - 2-5 terse imperative bullet fragments summarizing the changes. 3. CHANGE BLOCKS - One per discrete change:
* New code: `new section, add after: <anchor>` ````python ... ````
* Replacement: `modified: <anchor>` `Search for:` ````python ... ```` `Replace with:` ````python ... ````
Labels are literal - no reformatting, no bold, no altered punctuation.
4. VERIFICATION - Single line starting with `û`. Confirm runnability, describe visible runtime behavior, note any conditional visibility. Dense prose, no bullets.
Anchors: All `add after` and `modified` locations must reference one of the file anchors listed in 3. Do not invent anchor strings.
Style: Terse and technical. No filler. All code blocks use triple backticks + language tag. Preserve variable and function names exactly. Inline comments allowed - short lowercase fragments only.

## PARADIGM AND STYLE - NON-NEGOTIABLE

- **No classes.** The `class` keyword does not appear anywhere. Data lives in plain dicts, lists, tuples.
- **No hidden state.** Every function receives its inputs as arguments and returns its outputs. No reading from or writing to module-level mutable variables inside functions. Module-level *constants* are fine.
- **No method dispatch.** No dunder methods, no operator overloading, no polymorphism. All operations are explicit function calls.
- **Data and functions are separate.** Data is declared at the call site or as a constant. Functions transform data passed to them.
- **Full descriptive names.** No abbreviations. `grid_width` not `gw`, `scroll_offset` not `off`.
- **Type hints on all function signatures and major bindings.**
- **Explicit `for` loops over comprehensions** unless the comprehension is a trivial one-line mapping.
- **One operation per line in hot paths.** No chained or stacked calls.
- **No clever tricks.** If a reader must pause, rewrite it.
- **Explicit control flow.** No short-circuit logic, no ternary nesting, no implicit truthiness for logic that matters.
- **No generators as lazy pipelines, no context managers for control flow, no decorators.**
