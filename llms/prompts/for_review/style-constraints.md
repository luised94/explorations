# BLOCK S - STYLE CONSTRAINTS (Reusable)
# Inject this into any thread where code will be written or reviewed.
# Works at session start or mid-thread.

---

> All code produced in this session must conform to the following paradigm and style invariants. These are non-negotiable. They apply from the first line and are never deferred to a cleanup pass.
>
> **Programming paradigm: procedural, data-oriented Python.**
> The organizing principle is: functions transform data that is passed to them explicitly.
>
> - No classes. The `class` keyword does not appear anywhere. Data lives in plain containers - flat lists, tuples, dicts used as named record stores.
> - No hidden state. Every function receives its inputs as arguments and returns its outputs. No reading from or writing to module-level mutable state inside functions. Module-level constants and configuration are acceptable.
> - No method dispatch. No operator overloading, no dunder methods, no polymorphism. All operations are explicit function calls.
> - Data and functions are separate. Data is declared and laid out in one place. Functions that transform it are defined separately. They do not own or encapsulate the data.
>
> **Code style invariants:**
>
> - Full descriptive names. No abbreviations. `activation_data` not `act_data`, `layer_index` not `li`, `head_dimension` not `head_dim`. Names read as plain English.
> - Type hints on all function signatures and major bindings. Use `list[float]`, `tuple[int, int, int]`, etc. Introduce `TypeAlias` for recurring compound types when it aids clarity.
> - Prefer explicit `for` loops over list comprehensions unless the comprehension is a trivial one-line mapping with no readability cost. If a reader must scan horizontally or parse nested logic, use a loop.
> - One operation per line in hot paths. No stacked or chained method calls. Each line does one legible thing.
> - No clever tricks. If a reader must pause to understand an expression, rewrite it. Favor obviousness over concision.
> - Explicit control flow. No short-circuit evaluation, ternary nesting, or implicit truthiness for logic that matters.
> - Standard library utilities that are paradigm-neutral are fine: `enumerate`, `zip`, `range`, `f-strings`, `math`, `random`.
> - Do not use Python features that hide mechanism: no generators as lazy pipelines, no context managers for control flow, no decorators, no dunder methods. If a Python feature exists to abstract or hide, do not use it here.

---
---

# PROMPT - STYLE COMPLIANCE PASS
# Paste this (with Block S above it, or reference it) into the thread
# after the final integrated plan is produced, before triggering the handoff.

---

> Before we proceed to the handoff, perform a style compliance pass on the current plan and specification.
>
> Apply the style constraints defined in Block S. Your task is a targeted audit - find violations, propose the minimal fix for each. Do not redesign. Do not add commits. Do not restructure phases.
>
> For each violation found:
> - Identify the location (commit number, function name, data structure, or section).
> - State the violation in one sentence.
> - State the minimal fix in one sentence.
>
> After listing all violations, produce an updated version of any affected section - commit descriptions, function signatures, data structure definitions, or pseudocode - with the fixes applied inline.
>
> If a section of the plan is implementation-agnostic (process steps, phase descriptions, SQL schemas without Python) and contains no style violations, skip it.
>
> When complete, confirm: "Style compliance pass complete. Ready for handoff."
