<thinking>
The user wants me to decompose the TigerStyle document into a robust, reusable prompt chain. This means breaking down the comprehensive coding style guide into a series of interconnected prompts that can be used systematically to guide code development and review processes.

I should structure this as a chain where each prompt builds on previous ones and can be used independently or as part of the whole workflow. The chain should cover:

1. Initial design/architecture prompts
2. Safety verification prompts
3. Performance analysis prompts
4. Code quality/style prompts
5. Review and validation prompts

Each prompt should be actionable, specific, and reference the key principles from TigerStyle.
</thinking>

# TigerStyle Prompt Chain

## Chain Overview
A systematic prompt sequence for developing code that meets TigerBeetle's standards of safety, performance, and developer experience.

---

## Phase 1: Design & Architecture

### Prompt 1.1: Problem Definition
```
Define the problem you're solving:
1. What are the core nouns and verbs in this domain?
2. What are the physical limits (network, disk, memory, CPU)?
3. What invariants must always hold?
4. What could go wrong? List all failure modes.
5. Where is the control plane vs data plane boundary?

Output: Problem statement with domain model and constraints.
```

### Prompt 1.2: Simplicity Check
```
Review your design for simplicity:
1. Can this be solved with simpler control flow?
2. Are there unnecessary abstractions?
3. Can multiple concepts be unified into one "super idea"?
4. What would you remove if you had to "throw one away"?

Output: Simplified design with justification for each component.
```

### Prompt 1.3: Resource Sketching
```
Create back-of-envelope calculations:
1. Network bandwidth/latency requirements
2. Disk IOPS and throughput needs  
3. Memory usage (static allocation budget)
4. CPU cycles per operation
5. Identify the bottleneck resource

Output: Performance sketch with resource utilization estimates.
```

---

## Phase 2: Safety Implementation

### Prompt 2.1: Memory & Bounds Planning
```
Define all memory and bounds:
1. List every data structure with exact sizes
2. Define upper bounds for all loops
3. Define limits for all queues/buffers
4. Plan static allocation strategy
5. Identify what happens at each limit

Output: Memory map and bounds specification.
```

### Prompt 2.2: Assertion Strategy
```
Design your assertion coverage:
1. List all function preconditions
2. List all function postconditions  
3. Identify invariants that span functions
4. Find paired assertion points
5. Define positive space (valid) and negative space (invalid)

Target: Minimum 2 assertions per function.
Output: Assertion plan with coverage map.
```

### Prompt 2.3: Error Path Analysis
```
Map all error paths:
1. List every external interaction point
2. Define every possible error at each point
3. Design handling for each error
4. Ensure no error is ignored
5. Verify error handling doesn't violate invariants

Output: Complete error handling matrix.
```

---

## Phase 3: Performance Implementation

### Prompt 3.1: Batching Opportunities
```
Identify batching points:
1. Where can network calls be batched?
2. Where can disk operations be combined?
3. Where can memory accesses be grouped?
4. Where can CPU work be chunked?
5. What's the optimal batch size for each?

Output: Batching strategy with size rationale.
```

### Prompt 3.2: Hot Path Extraction
```
Optimize critical paths:
1. Identify the hot loops
2. Extract to standalone functions
3. Use only primitive arguments
4. Remove struct dependencies
5. Minimize memory indirection

Output: Refactored hot path functions.
```

---

## Phase 4: Code Quality

### Prompt 4.1: Naming Audit
```
Review all names:
1. Do nouns and verbs work together?
2. Are units included and positioned last?
3. Do related names have equal length?
4. Is each name's meaning unambiguous?
5. Are abbreviations eliminated?

Output: Naming improvements with justifications.
```

### Prompt 4.2: Function Structure
```
Validate function design:
1. Is each function ó70 lines?
2. Is control flow centralized in parent functions?
3. Are leaf functions pure?
4. Do functions complete without suspending?
5. Are callbacks last in parameter lists?

Output: Refactored functions meeting guidelines.
```

### Prompt 4.3: Scope Minimization
```
Minimize variable scope:
1. List each variable's lifetime
2. Move declarations to first use
3. Group related allocations with defers
4. Eliminate variable aliases
5. Calculate values near usage

Output: Scope-optimized code.
```

---

## Phase 5: Validation & Review

### Prompt 5.1: Safety Checklist
```
? No recursion used
? All loops bounded
? All memory statically allocated
? Assertions average 2+ per function
? All errors handled
? No dynamic allocation after init
? Compiler warnings addressed
? Buffer bleeds prevented
```

### Prompt 5.2: Performance Checklist
```
? Back-of-envelope calculations done
? Bottleneck resource identified
? Batching implemented
? Hot paths extracted
? External events decoupled
? Control/data plane separated
```

### Prompt 5.3: Style Checklist
```
? Functions ó70 lines
? Line length ó100 columns
? 4-space indentation
? snake_case naming
? Comments explain why
? Commit messages descriptive
? No dependencies added
? zig fmt applied
```

---

## Phase 6: Documentation

### Prompt 6.1: Technical Documentation
```
Document your implementation:
1. Why were design decisions made?
2. What invariants must be maintained?
3. What are the performance characteristics?
4. What are the failure modes?
5. How should this code evolve?

Output: Technical documentation covering rationale and constraints.
```

### Prompt 6.2: Assertion Documentation
```
Document critical assertions:
1. Why is each assertion necessary?
2. What bug would occur without it?
3. What paired assertions exist?
4. What positive/negative spaces are checked?

Output: Assertion rationale documentation.
```

---

## Usage Instructions

### Sequential Use
Work through each phase in order for new feature development.

### Targeted Use
Jump to specific prompts for:
- Bug fixes: Start with 2.3 (Error Path Analysis)
- Performance issues: Start with 3.1 (Batching Opportunities)
- Refactoring: Start with 4.1 (Naming Audit)

### Review Process
Use Phase 5 checklists for all code reviews.

### Iteration
After Phase 5, return to Phase 1 if significant issues found.

---

## Meta-Prompt: Chain Evaluation
```
After using this chain:
1. Which prompts provided most value?
2. What was missed?
3. Where did you deviate from guidance?
4. What would you add to the chain?

Use feedback to evolve the chain.
```
