## The Prompt

```markdown
You've just helped me design this system and we've
arrived at an implementation plan. 

Now I need you to become a CONTEXT COMPILER.

For each Haiku-level task in our plan, generate a
self-contained execution packet:

## Task [N]: [one-line description]

### Thread
Which parallel thread this belongs to, and position in sequence.

### Files To Modify
Exact current content of files being changed.
(Or "NEW FILE" if creating)

### Interface Context
Only the type signatures and function signatures
this task interacts with. Not implementations.
Include shared contracts from Step 0.

### Task Description
2-3 sentences max. What to do and why.
Reference a pattern in the provided code if possible:
"Follow the same pattern as [existing function]."

### Concrete Example
Input  Expected output, or before  after snippet.

### Constraints & Gotchas
Anything non-obvious that came up in our conversation
that is relevant to THIS specific task.
Things we decided against and why, IF the model
might naturally drift toward that wrong choice.

### Verification
How to know this task is done correctly.

---

CRITICAL INSTRUCTIONS:
- Each packet must stand ALONE. The executing model
  has ZERO knowledge of our conversation.
- Include ONLY context relevant to THIS task.
- If two tasks share context, duplicate it. 
  Don't reference other packets.
- Err toward explicit. What's obvious to us after
  this long conversation is NOT obvious to a fresh model.
