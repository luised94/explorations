# Debugger
VERSION: 1
UPDATED: 2026-05-27

Prompt for diagnosing and fixing code bugs. Direct and focused -
find the problem, explain why, provide the fix.

---

## When to use

- Code produces wrong output
- Code crashes with an error
- Code behaves unexpectedly
- A verification command from a commit doesn't match expected output

## Prompt

```
Debug this. Here is the relevant code, the command I ran, the
actual output, and the expected output.

CODE:
[paste relevant section - not the entire file unless necessary]

COMMAND:
[exact command run]

ACTUAL OUTPUT:
[paste exactly what happened, including any error messages]

EXPECTED OUTPUT:
[what should have happened]

Find the root cause. Explain why it happens in 1-3 sentences.
Provide the fix as a precise substitution: old code  new code.
If the bug reveals a missing invariant or error handling gap,
state what should be added to prevent recurrence.
```

## Compact form

For obvious/simple bugs:

```
Bug. Code: [paste]. Got: [actual]. Expected: [expected]. Fix it.
```

## Conventions

- Paste the minimal relevant code, not the whole file
- Include the exact error message or wrong output, not a summary
- The fix should be a precise substitution, not "restructure the
  function" - if restructuring is needed, say so and provide the
  full replacement
- If the bug reveals a design flaw (not just a typo), say so
  explicitly: "This is a design issue, not just a bug: [explanation]"
- If the root cause is ambiguous from the provided context, state
  what additional information would disambiguate rather than guessing
