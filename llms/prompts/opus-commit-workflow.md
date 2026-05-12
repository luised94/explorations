# COMMIT WORKFLOW

Deliver work as sequential, atomic commits. Begin with commit one.

## Each Commit Contains

### 1. Purpose
One sentence: what this commit accomplishes and why.

### 2. Implementation
Choose the appropriate delivery method:

- **New file**  provide full artifact
- **Edit to existing file**  provide anchored instructions:
File: <path>
Find: <unique line or pattern to locate>
Action: INSERT BELOW | INSERT ABOVE | REPLACE | DELETE
Content:
<exact text>

css
Copy code
Multiple edits per file listed in top-to-bottom order.

### 3. Verification
Shell commands to run + expected output or success criteria.
$ <command>
<expected output or description of passing state>

markdown
Copy code

### 4. Commit Message
Conventional format: `<type>: <concise description>`

Types: `feat`, `fix`, `docs`, `refactor`, `test`, `chore`, `style`

## Rules
- One logical change per commit-buildable and verifiable in isolation
- Never combine unrelated changes
- Edits use enough anchor context to be unambiguous (prefer unique lines over line numbers)
- Wait for user confirmation before proceeding to next commit
