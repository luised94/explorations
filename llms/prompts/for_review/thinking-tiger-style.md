<thinking>
The user is asking me to act as LLMLingua2 and compress the attached text. LLMLingua2 is a prompt compression technique that frames compression as a token classification problem to maintain faithfulness to the original prompt while reducing token count.

Looking at the document, it's "TigerStyle" - a comprehensive coding style guide for TigerBeetle. The document is quite long and covers:
1. Philosophy of style
2. Design goals (safety, performance, developer experience)
3. Simplicity and elegance
4. Technical debt policy
5. Detailed safety guidelines
6. Performance considerations
7. Developer experience best practices
8. Dependencies and tooling

To compress this effectively while maintaining essential information, I should:
- Preserve the core principles and philosophy
- Maintain the hierarchical structure
- Keep critical rules and guidelines
- Remove redundant examples and elaborations
- Condense verbose explanations
- Retain actionable directives

Let me create a compressed version that captures all essential information while significantly reducing token count.
</thinking>

# TigerStyle [Compressed]

## Core Philosophy
Style = Design. Goals: Safety > Performance > Developer Experience. Style advances these goals.

## Principles
- **Simplicity**: Hard-won through iteration, not first attempt. Requires discipline.
- **Zero Technical Debt**: Fix problems when found. Do it right first time.
- **Upfront Thinking**: Design hour saves production months.

## Safety Rules
- **Control Flow**: Simple, explicit. No recursion. Minimal abstractions.
- **Limits**: Bound everything - loops, queues. Fail-fast.
- **Types**: Use explicit sizes (u32), avoid usize.
- **Assertions**:
  - Assert all arguments, returns, pre/postconditions
  - Minimum 2 assertions/function
  - Pair assertions for critical properties
  - Assert positive AND negative space
  - Split compound assertions
- **Memory**: Static allocation only. No dynamic allocation after init.
- **Scope**: Minimize variables, smallest scope, 70-line function limit.
- **Warnings**: Strictest compiler settings.
- **External Events**: Run at own pace, not reactive.
- **Error Handling**: Handle all errors (92% failures from poor error handling).

## Performance
- Design-phase optimization for 1000x wins
- Back-of-envelope sketches: Network > Disk > Memory > CPU
- Batch everything
- Extract hot loops to standalone functions
- Be explicit, don't rely on compiler

## Developer Experience

### Naming
- Perfect nouns/verbs capturing essence
- snake_case everywhere
- No abbreviations (except loop counters)
- Units last: `latency_ms_max`
- Same-length related names
- Descriptive commits

### Code Organization
- Main function first
- Big-endian naming
- Avoid overloaded terminology
- Pass large structs as `*const`
- In-place initialization for large structs
- Minimize variable scope
- Group allocation/deallocation

### Technical
- 4-space indent, 100-column limit
- Always use braces unless single-line
- Show division intent: @divExact/@divFloor
- Zero dependencies policy
- Zig-only tooling

### Comments
- Explain why AND how
- Complete sentences with punctuation
- Document surprising invariants

## Key Practices
- Calculate near usage (avoid POCPOU)
- Simpler return types (void > bool > u64 > ?u64)
- Complete function execution without suspending
- Guard against buffer bleeds
- Index/count/size distinctions

"It's called TigerBeetle - fast AND small!"
