## Commit Classification and Decomposition

### Step 1: Classification
Classify each commit into exactly one of three categories based on its scope and complexity:

- **Haiku**: An atomic, single-purpose change (e.g., a one-line bug fix, a variable rename, a single dependency update, a typo correction). It touches one concern and cannot be meaningfully broken down further.

- **Sonnet**: A small, cohesive change that addresses a single feature, fix, or refactor but involves coordinated edits across multiple lines or files (e.g., adding a new API endpoint with its route and handler, updating a function signature and all its call sites). It is larger than a haiku but still represents one logical unit of work.

- **Opus**: A large, multi-concern change that bundles two or more distinct logical changes into a single commit (e.g., a commit that simultaneously adds a new feature, refactors an existing module, and updates documentation for an unrelated component).

### Step 2: Decomposition (Opus commits only)
For each commit classified as **opus**, decompose it into the smallest set of independent **haiku** and/or **sonnet** sub-commits that, together, would reproduce the full effect of the original commit.

For each proposed sub-commit, specify:
1. **Label**: haiku or sonnet
2. **Description**: A concise summary of the single concern it addresses
3. **Scope**: Which files/functions/lines it would touch
4. **Ordering dependency**: Whether it must come before or after another sub-commit in the sequence (or if it is independent)

### Output Format
```
Commit: <hash or identifier> - <original commit message>
Classification: haiku | sonnet | opus

[If opus:]
Decomposition:
  1. [haiku|sonnet] - <description> (files: ...) [depends on: none | #N]
  2. [haiku|sonnet] - <description> (files: ...) [depends on: none | #N]
  ...
```

### Edge Cases
- If no commits qualify as opus, explicitly state: *"No opus commits identified."*
- If a commit is borderline between two categories, classify it as the **higher** category and note the ambiguity.
