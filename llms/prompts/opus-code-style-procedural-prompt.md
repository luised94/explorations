
[DATA_ORIENTED_PROGRAMMING_DIRECTIVE]

When writing code, follow these procedural data-oriented principles:

CORE PHILOSOPHY:
- Data and its transformations are primary; abstractions are secondary
- Optimize for data locality and cache efficiency
- Write code that processes arrays of data, not individual objects
- Prefer explicit data flow over hidden state

IMPLEMENTATION RULES:
1. Use plain data structures (structs/records) without methods
2. Group functions by data transformation, not by "object type"
3. Prefer arrays/vectors over linked structures
4. Use Structure of Arrays (SoA) over Array of Structures (AoS) when beneficial
5. Make data dependencies explicit through function parameters
6. Avoid virtual functions, inheritance, and dynamic dispatch
7. Minimize pointer chasing and indirection
8. Process data in batches when possible

CODE STYLE:
- Functions take data as input and return transformed data
- No classes with private state - use modules with free functions
- Explicitly pass context/state as parameters
- Use simple for loops over functional abstractions when clearer
- Inline small functions for performance
- Prefer stack allocation over heap when feasible

AVOID:
- Deep inheritance hierarchies
- Getter/setter methods
- Design patterns that add indirection (Factory, Visitor, etc.)
- Unnecessary abstractions "for future flexibility"
- Object-oriented modeling of domain concepts
- Hidden dependencies and global state

EXAMPLE PATTERN:
Instead of: class Entity { update(); render(); }
Use: update_entities(Entity* entities, size_t count); render_entities(const Entity* entities, size_t count);

[PRESERVE_LOGICAL_FLOW]

Write code that follows the natural flow of logic without premature abstractions:

CORE PRINCIPLE:
- Code should tell a story from start to finish
- Don't break flow unless there's a genuine pattern to extract
- Abstractions should emerge from actual repetition, not speculation

WRITE INLINE FIRST:
- Keep sequential operations together
- Don't extract functions preemptively
- Let the logic unfold naturally in order
- Use comments to mark sections, not function boundaries
- Maintain narrative coherence in the code

WHEN NOT TO EXTRACT FUNCTIONS:
- When code is only used once
- When extraction would obscure the sequence of operations
- When the "function" would need many parameters to maintain context
- When you're just following "functions should be small" dogma
- When there's no clear, reusable pattern yet

VALID REASONS TO EXTRACT:
- Actual repeated code (not just similar structure)
- Complex algorithms that genuinely benefit from isolation
- Operations that form a clear, reusable abstraction
- When the main flow becomes clearer by extraction

GUIDELINE:
Start with everything inline. Extract only when you see the same logic appear multiple times, or when the extraction genuinely improves understanding of the main flow. Prefer code that can be read top-to-bottom without jumping around.
[AVOID_FUNCTION_DECOMPOSITION]

Write code in larger, cohesive blocks instead of many small functions:

INLINE CODE DIRECTLY:
- Write sequential operations in the same scope
- Don't extract code into functions unless truly reused
- Keep related logic together in one place
- Avoid "helper" functions for single-use operations
- Inline calculations rather than creating function abstractions

AVOID FUNCTIONAL PATTERNS:
- Don't use map/filter/reduce when loops are clearer
- No function composition or chaining
- Avoid higher-order functions
- Don't create functions that just wrap other functions
- Skip point-free style and partial application

WHEN TO USE FUNCTIONS:
- Only when code is genuinely reused multiple times
- For truly independent, substantial operations
- When recursion is mathematically necessary
- For module-level public interfaces only

PREFERRED STYLE:
- Long, procedural blocks that tell a complete story
- Variables to store intermediate results, not function returns
- Explicit loops with body logic inline
- Direct manipulation instead of abstracted operations
- 50-200+ line functions are acceptable and often preferred

EXAMPLE:
Instead of: 
  data = load_data()
  cleaned = clean_data(data)
  transformed = transform_data(cleaned)
  result = calculate_result(transformed)

Write:
  // All operations in one cohesive block
  data = read_from_file(...)
  // cleaning logic inline
  for i in 0..len { ... }
  // transformation logic inline  
  for item in data { ... }
  // calculation logic inline
  result = ...

[AVOID_OO_PARADIGM]

Do not use object-oriented programming or its methodologies:

FORBIDDEN PATTERNS:
- No classes with encapsulated state and methods
- No inheritance hierarchies
- No polymorphism or virtual dispatch
- No design patterns (Factory, Singleton, Observer, etc.)
- No getters/setters or property accessors
- No "objects" that model real-world entities

METHODOLOGY AVOIDANCE:
- Don't follow SOLID principles
- Don't create abstractions for future flexibility
- Don't use UML or object modeling
- Ignore "clean code" rules about small classes/methods
- Skip Agile/OO planning methods (user stories as objects, etc.)

ALTERNATIVE APPROACH:
- Use modules with free functions
- Pass data explicitly as parameters
- Use procedural decomposition
- Keep related functions in same file/module
- Make dependencies visible, not hidden

[DATA_ORIENTED_PROGRAMMING]

Follow these data-oriented programming principles:

DATA LAYOUT:
- Structure data for efficient access patterns
- Group data by how it's accessed together
- Use contiguous memory layouts (arrays/vectors)
- Consider Structure of Arrays (SoA) for hot data paths
- Align data to cache lines when performance critical

PROCESSING APPROACH:
- Think in terms of data transformations
- Process multiple elements per operation (batch processing)
- Make data flow explicit through function parameters
- Minimize random memory access patterns
- Prefer linear array traversal

DESIGN PRINCIPLES:
- Data shapes determine function design
- Separate data from logic
- Use plain data containers (POD types)
- Explicitly manage data lifetime
- Design around common access patterns

