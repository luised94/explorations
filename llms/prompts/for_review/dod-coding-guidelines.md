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

```
# Code Style Guidelines - Phased by Priority

## Phase 1: Non-Negotiable (Enforce from first line)

These constraints affect code structure and data flow. Retrofitting is painful. Enforce in every commit from the start.

### Structural Constraints
- **No classes**: No `class` keyword anywhere. Use plain functions and data containers (lists, tuples, dicts).
- **No hidden state**: Functions receive inputs as arguments, return outputs. No reading/writing module-level mutable state inside functions. Module-level constants are acceptable.
- **No input mutation**: Functions must not modify their input parameters unless that's the explicit, documented purpose. Build new data structures instead.

### Import Style
- **No aliases**: Always `import module`, never `import module as alias`
- **No direct imports**: Always `import module`, never `from module import item`
- **Full qualification**: All call sites use `module.function()`, `module.CONSTANT`
- Apply uniformly to all code: project modules, standard library, third-party packages

### Type Safety
- **Type hints on all function signatures**: Parameters and return types must be annotated
- **Type hints on major bindings**: Use for complex data structures and important variables
- **Type aliases for structured data**: Document with docstrings explaining keys, types, and invariants

### Control Flow
- **Early returns over nesting**: Handle error/invalid cases first with early returns. Main logic path at lowest indentation level.
- **Explicit control flow**: No reliance on short-circuit evaluation, ternary nesting, or implicit truthiness for logic that matters

---

## Phase 2: Strongly Encouraged (Apply during implementation)

These improve readability and maintainability but are refactorable without changing logic. Apply when possible, fix in review if missed.

### Naming
- **Full descriptive names**: No abbreviations. `activation_data` not `act_data`, `layer_index` not `li`
- **Positive boolean naming**: `is_ready`, `has_data`, `should_continue` - avoid `is_not_ready`, `has_no_data`
- **Names read as plain English**: A reader unfamiliar with the domain should understand intent

### Explicitness
- **Explicit comparisons**: `if value is not None:` not `if value:`, `if count > 0:` not `if count:`
- **One operation per line in hot paths**: No stacked or chained method calls. Each line does one legible thing.
- **No clever tricks**: If a reader has to pause to understand an expression, rewrite it

### Code Organization
- **Minimal variable scope**: Declare variables immediately before first use, not at function start
- **Module organization (top-to-bottom)**:
 ÿ1. Docstring
 ÿ2. Imports (stdlib, third-party, local)
 ÿ3. Module-level constants
 ÿ4. Type aliases with docstrings
 ÿ5. Functions in dependency order (helpers before callers)
 ÿ6. Main execution (if script)

### Loop Style
- **Prefer explicit `for` loops over comprehensions**: Unless the comprehension is trivial one-line mapping with no readability cost
- **If horizontal scanning needed, use a loop**: Reader shouldn't have to parse nested logic in comprehension

### Return Conventions
- **Single optional value**: `function() -> Type | None`
- **Multiple values**: `function() -> tuple[Type1, Type2, Type3]` with descriptive type hint
- **Success/failure with value**: `function() -> tuple[bool, Type]` - bool flag first

---

## Phase 3: Refinement (After working implementation)

These require judgment about the problem domain. Defer until you have working code and understand the full context.

### Naming Refinement
- **Perfect word choice**: Finding the exactly right term for the domain
- **Consistency across module**: Ensuring parallel concepts use parallel names

### Decomposition
- **Optimal function boundaries**: Is this one function or three? Should these merge?
- **Extract or inline**: Compression-oriented - don't decompose until you feel pain
- **Helper function necessity**: Does this helper clarify or just add indirection?

### Constants
- **Extract when semantic meaning**: `HTTP_TIMEOUT_SECONDS: int = 30` - value might change or has domain meaning
- **Inline when arithmetic**: `buffer_size = file_size * 2` - one-off calculation
- **Decision criteria**: Will this value change? Does it have semantic meaning? Is it used multiple times?

### Documentation
- **Comment the "why" not "what"**: Explain reasoning, invariants, non-obvious behavior
- **Data structure invariants**: Document required keys, value constraints, ordering requirements
- **Edge case documentation**: Why certain checks exist, what failure modes they prevent

### Consistency Polish
- **Parallel structures**: Similar operations should look similar
- **Formatting consistency**: Spacing, alignment, visual grouping
- **Error message quality**: Clear, actionable, consistent tone

---

## Implementation Protocol

**Each commit must:**
- Satisfy all Phase 1 constraints (non-negotiable)
- Attempt Phase 2 constraints (strongly encouraged, fix if missed)
- Defer Phase 3 (refinement pass after module works)

**After full module implementation:**
- Review pass asking Phase 3 questions
- Refinement commit addressing decomposition, naming, documentation

**LLM instruction:**
```

Phase 1: Enforce in every response - these are non-negotiable Phase 2: Apply when they don't conflict with getting code working Phase 3: Defer to refinement pass after initial implementation
---
`# BASH_SCRIPT_OPTIMIZATION v1.1 ## STRUCTURE - Shebang + header: script purpose, usage, requirements - Config/Settings section first - Main logic with hierarchical comment banners - Self-contained: only bash + coreutils/curl ## NAMING_RULES - FULL_NAMES_NO_ABBREVIATIONS - CONSTANTS_IN_CAPS - snake_case_variables ## CODING_CONSTRAINTS ? No functions/abstractions  Linear procedural flow  Explicit control structures ## DEBUGGING - Strategic prints for: - Flow tracking - Key variable values - Post-computation assertions - Basic error checking ## ERROR_HANDLING - Validate assumptions - Enforce invariants - Fail early pattern`

**Problem Analysis**  
**Quick Take**: Faithful compression of bash scripting constraints()  
**Deep Analysis**: Preserve structural requirements while optimizing token usage through symbol shorthand and merged categories

**Solution Delivery**

- **Token Reduction**: ~65%
    
- **Preserved**:
    
    - Script structure hierarchy
        
    - Naming conventions
        
    - Procedural mandate()
        
    - Debugging/error handling
        
- **Removed**:
    
    - Redundant "include" directives
        
    - Explanatory clauses
        
    - Duplicate "strategic" mentions
        

**Verification**

1. Are all critical constraints maintained?
    
2. Does the structure follow configlogic flow?
    
3. Are debugging requirements explicit?
    

**Scalability**

1. How does this handle complex scripting needs?
    
2. Can constraints adapt to advanced error handling?
    

**Improvement**

1. Add version compatibility guidelines()
    

1. [programming.code_style](https://www.perplexity.ai/search/programming.code_style)
    
2. [programming.bioinformatics](https://www.perplexity.ai/search/programming.bioinformatics)
    

# BASH_SCRIPTING_PROTOCOL v1.0

[STRUCTURE]

- Shebang + header (basic info/instructions)
    
- Hierarchical comment banners per section
    
- Config/settings  main logic organization
    
- Self-contained (bash + common tools like curl only)
    

[NAMING_CONVENTIONS]

- Full intention-revealing names (no abbreviations)[1]
    
- CONSTANTS_IN_CAPS
    
- snake_case_for_all_variables
    
- Descriptive variable names with clear purpose
    

[CODE_STYLE]

- Straightforward procedural programming (no functions/abstractions)[1]
    
- Sequential execution flow
    
- No dependencies beyond bash/common utilities
    

[DEBUGGING_SUPPORT]

- Strategic print statements for flow tracking
    
- Variable value printing for key computations
    
- Progress indicators throughout execution
    

[ERROR_HANDLING]

- Basic error handling for assumptions
    
- Post-computation assertions
    
- Invariant checks after critical operations
    
- Catch and specify error conditions
    

[EXECUTION_PATTERN]

1. Header documentation
    
2. Configuration section
    
3. Main logic with progress tracking
    
4. Assertions after computations
    
5. Error handling throughout
---
`# Change Verification Checklist ## Structure Validation 1. Directory hierarchy compliance 2. File naming convention adherence 3. Implementation pattern consistency 4. Cross-cutting concern separation ## Code Quality 1. Function length limits 2. Assertion density 3. Error handling patterns 4. Documentation completeness ## Next Files for Review 1. Primary candidates: - Files with mixed responsibilities - Complex error handling - Unclear naming patterns 2. Secondary candidates: - Documentation updates - Test coverage gaps - Configuration inconsistencies`
---
`# Repository Quality Guidelines ## Naming Conventions **File Pattern** - Format: <domain>_<action>.<extension> - Domain: Primary concept (genome, experiment) - Action: Primary operation (process, analyze) - Extension: Implementation (.R, .sh) **Function Categories** - Processors: transform_data(), process_sequence() - Validators: validate_input(), verify_result() - Handlers: manage_resource(), handle_error() ## Directory Organization **Core Layers** - meta/: Code generation, templates - core/: Domain implementation - infrastructure/: Technical components - interface/: External APIs - aspects/: Cross-cutting concerns **Implementation Rules** - 70-line limit per function - Two assertions minimum - Explicit error handling - No dynamic allocation ## Quality Standards **Documentation** - Purpose and context - Input/output contracts - Error conditions - Usage examples **Testing Requirements** - Unit tests for pure functions - Integration tests for workflows - Property tests for invariants - Exhaustive edge cases`
---
\## Directory Organization lab_utils/ ÃÄÄ R/ ³ ÃÄÄ core/ # Core functionality ³ ÃÄÄ modules/ # Analysis modules ³ ÀÄÄ config/ # Configurations ÃÄÄ bash/ ³ ÃÄÄ core/ # Core scripts ³ ÃÄÄ modules/ # Processing scripts ³ ÀÄÄ config/ # Environment settings ÀÄÄ tests/ # Validation tests ## Naming Conventions 1. Functions - verb_noun_object format - domain prefix for modules - consistent plurality 2. Files - <domain>_<action>_<type>.<ext> - consistent separators - version tracking if needed
---
\### 3. Reference Standards (reference_standards.md) ```markdown # Academic Code Standards ## Directory Organization lab_utils/ ÃÄÄ R/ ³ ÃÄÄ core/ # Core functionality ³ ÃÄÄ modules/ # Analysis modules ³ ÀÄÄ config/ # Configurations ÃÄÄ bash/ ³ ÃÄÄ core/ # Core scripts ³ ÃÄÄ modules/ # Processing scripts ³ ÀÄÄ config/ # Environment settings ÀÄÄ tests/ # Validation tests ## Naming Conventions 1. Functions - verb_noun_object format - domain prefix for modules - consistent plurality 2. Files - <domain>_<action>_<type>.<ext> - consistent separators - version tracking if needed ## State Management - Track active files - Maintain context - Log state changes - Handle interruptions
---
Break down the following into more atomic functions:

Always implement explicit input validation using appropriate methods (stopifnot() for R, parameter checking for Bash). ÿExplicit control flow statements. Clear error handling mechanisms. Type checking where applicable. For R code: Use snake_case for functions/variables, UPPER_CASE for constants, explicit verb prefixes (get_, set_, calc_), and avoid dot.case. Enforce strict domain boundaries and clear separation of concerns. Avoid clever optimizations in favor of clear, maintainable and robust solutions. Follow industrial-grade practices.
---
Break down the following into more atomic functions:  
Always implement explicit input validation using appropriate methods (stopifnot() for R, parameter checking for Bash). Explicit control flow statements. Clear error handling mechanisms. Type checking where applicable. For R code: Use snake_case for functions/variables, UPPER_CASE for constants, explicit verb prefixes (get_, set_, calc_), and avoid dot.case. Enforce strict domain boundaries and clear separation of concerns. Avoid clever optimizations in favor of clear, maintainable and robust solutions. Follow industrial-grade practices.
---
# Building R code requirements for prompts

No abbreviations. Use intention-revealing descriptive nouns.

Prefer base R.

Use standard portable ASCII characters in messages if necessary.

See:
---
For R scripts:

1. Include a header comment at the top of the script with:
    
    - Script name/title
        
    - Brief description of purpose
        
    - Author name
        
    - Date created/last modified
        
    - Usage instructions
        
2. Use roxygen2-style comments to document functions, including:
    
    - @title
        
    - @description
        
    - @param for each parameter
        
    - @return to describe the output
        
3. Use meaningful variable and function names that describe their purpose.
    
4. Add comments before code blocks to explain their purpose.
    
5. Consider organizing related functions into separate files or even creating an R package.
    
6. Use consistent formatting and indentation.
    

For bash scripts:

1. Start with a shebang line (e.g. #!/bin/bash)
    
2. Include a header comment with:
    
    - Script description
        
    - Author
        
    - Date
        
    - Usage instructions
        
3. Document functions with comments describing:
    
    - Purpose
        
    - Parameters
        
    - Return value
        
4. Use meaningful variable and function names.
    
5. Add comments to explain complex logic or non-obvious code.
    
6. Consider using a style guide like Google's Shell Style Guide.
    
7. Use shellcheck to catch potential issues.
    

General tips for both:

- Keep documentation up-to-date as code changes
    
- Use version control like git
    
- Consider using a documentation generator tool
    
- Be consistent in your documentation style
    
- Focus on explaining "why" not just "what" the code does
---
For R scripts:  
If you create a new file, include a header with the sections for script name/title, Brief description of purpose, author name, Date created/last modified, Usage instructions.

Use roxygen2-style comments to document functions, including @title, @description, @param for each parameter, @return to describe the output. Use meaningful variable and function names that describe their purpose.

For bash scripts:  
If you create a new file, include a header with the sections for script name/title, Brief description of purpose, author name, Date created/last modified, Usage instructions.

Document functions with comments describing Purpose, Parameters, Return value. Use meaningful variable and function names. Consider using a style guide like Google's Shell Style Guide.
---
Naming Conventions Improvements:

1. Use consistent verb-noun patterns:
    
    - `organize_fastq_files`ÿ good (verb_noun_plural)
        
    - `safe_remove`ÿ considerÿ`remove_files_safely`
        
    - `cleanup_downloaded_data`ÿ considerÿ`clean_experiment_data`
        
2. Domain-specific prefixes:
    
    - `bmc_`ÿprefix for BMC-specific functions
        
    - `fastq_`ÿprefix for FASTQ operations
        
    - `fs_`ÿprefix for filesystem operations
        
3. File naming:
    
    - Use underscores consistently
        
    - Group related functions in domain-specific files
        
    - Consider version numbers for major changes
---
