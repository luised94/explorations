Break this implementation plan into atomic commits,
where each commit is "Haiku-level complexity" - meaning:
- A simpler, less capable model could execute it
- Single clear purpose
- Minimal context dependency
- No architectural judgment required
- Could be described in 1-2 sentences

Then execute each one with full Sonnet-level care:
- Proper error handling
- Edge case awareness  
- Idiomatic style
- Thoughtful naming
For each task in your decomposition, mark it:

?? HAIKU-LEVEL - Simple, atomic, execute with confidence
?? SONNET-LEVEL - Needs judgment but well-scoped  
?? OPUS-LEVEL - Flag for deeper review before executing

If you mark something ??, explain:
- Why it can't be decomposed further
- What decision needs to be made first
- What the downstream consequences are

Most tasks should be ??. A ?? appearing often means
the overall plan may need rethinking, not just
the individual task.
