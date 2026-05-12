## Commit Classification, Execution, and Strategy

### Step 1: Classify

- **Haiku**: Single-concern, single-act. Includes deterministic 
  transformations regardless of file count (sed, regex, macro).
- **Sonnet**: Single-concern, sustained coherence. Multiple 
  interdependent edits, one logical intent.
- **Opus**: Multi-concern. Decompose before executing.

### Step 2: Specify

For each commit (or sub-commit after decomposition):

  Commit: <identifier> - <message>
  Classification: haiku | sonnet | opus
  Modality: command | single_edit | full_rewrite | patch
  Context needed: <files/symbols required>
  Verification: <command(s) that confirm correctness>
    e.g., "cargo build", "pytest tests/", "diff <(cmd) expected.txt"
  Verifiable: yes | no
    - yes: verification commands are sufficient, no diff review needed
    - no: requires human judgment (semantic review, UI, non-deterministic)

### Step 3: Decompose (opus only)

  Decomposition:
    1. [haiku|sonnet] - <description>
       Modality / Verification / Verifiable / Depends on

### Step 4: Execution Strategy

After decomposition, determine strategy based on composition:

  If ALL sub-commits are verifiable  batch
    Output: full sequence of patches + verification script
    Apply with: git apply, run verification at each step
    Fallback: if verification fails at step N, switch to incremental from N

  If SOME sub-commits are not verifiable  hybrid
    Batch the verifiable prefix/subsequences
    Pause before non-verifiable commits for human review

  If MOST sub-commits are not verifiable  incremental
    One commit at a time, review each before proceeding

  Strategy: batch | hybrid | incremental
  Pause points (if hybrid): [list commit #s requiring judgment]
