# Domain: code

## Shape
- Flat procedural inside a unit. A unit is a data representation plus every
  operation that knows its internals. Boundary test: does one change force
  both sides to change? Yes -> one unit. No -> real boundary; split there.
- No helper, wrapper or indirection with one call site. Inline it.
- Fit the structure to the problem on sight, and say the naive reach, the
  fitted reach, and why they differ: pure computation -> function; accumulate
  by key -> dict or counter; parsing -> tree or state machine, not string
  poking; stable rules -> data table; stateful steps -> state machine.
- Name intermediate conditions so a debugger or a reader can see them.

## Names and comments
- No abbreviations. No single-letter names, loop variables included.
- Names carry domain meaning: WORKTREE_ROOT, not ROOT. Two things, two names.
- Comments say why: the constraint, the failure prevented, the alternative
  rejected, the platform detail. Not what the line does.
- ASCII only.
- Renaming: check prose, messages and format strings too. Rerun the tests.

## Tests
- Test behavior at stable boundaries. Keep one small end-to-end smoke path.
- Assertion means programmer bug: stop. Bad input is normal: handle it.
- Performance: state input sizes, measure before optimizing.

## Concurrency and distribution
- Who can change this at the same time? Write down what must be atomic.
- Across machines: timeout, retry, duplicate handling, request id in logs.

## Change and delivery
- One concern per commit. Each commit parses and runs. Message says why.
- Deliver changes that apply mechanically: a diff made from real files, or
  whole files with paths. Never a snippet to splice by hand.
- Diff against the exact bytes given. Files not shown may still exist; ask
  before creating one you are unsure about. Never cite a commit hash the
  human's repository does not contain.
