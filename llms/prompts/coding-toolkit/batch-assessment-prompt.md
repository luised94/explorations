Determine if commits [N through M] can be batched into a single
response. Assess:
- Combined complexity: would the batch require opus-level judgment?
- Cross-dependencies: does a later commit's design depend on seeing
  the earlier commit's implementation first, or are they mechanical
  extensions of established patterns?
- Shared concerns: do the commits touch the same code sections in
  ways that make isolated review harder than combined review?

If the batch is safe (sonnet or below), produce all commits together.
If it would be opus, batch only the largest sequential non-opus subset
starting from the first commit. State the assessment in one line
before producing code.
