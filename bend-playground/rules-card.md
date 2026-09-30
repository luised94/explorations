# Bend rules card

Evidence-graded. Built from the i00 experiment (five models, bend 2.0.16,
2026-09-22) and three later open-source-medium sessions. Re-check after
any compiler upgrade: 2.0.32 changed how errors are displayed, and some rules
below may have changed with it.

Grades:
- VERIFIED - a compiler run in this project confirmed it: an error that the
  stated fix cleared, or a construct inside code that passed the checker.
- STATED - written in `bend guide` or `bend base`, not exercised here.
- UNVERIFIED - inferred, or reported by one session and not confirmed.
- FALSE - a claim that circulated and is contradicted by passing code.
  Listed so nobody re-derives it.

---

## A. Limits that shape every program

From the upstream limitations list (as of late September 2026; re-read
the README for the current list):

- Bend 2 is not Bend 1 or HVM; nothing carries over.
- Everything is annotated; nothing is inferred.
- Values are affine: closures and arrays cannot be shared.
- Recursion must terminate (`@unsafe` disables the check and the guarantees).
- `match f(x)` on a computed value is not supported; there is no if-then-else.
- Numbers are `Nat`, `U32` and `F32` only.
- F32 is axiomatic: nothing about floating point can be proven.
- Strings are linked lists of characters, so text processing is slow.
- Base is small; expect to write helpers.
- Parallelism requires balanced calls.
- Error messages are terse; there is no test framework.

---

## B. Rules that bite

**R1. Affinity counts occurrences in the body.** A name without `+` may occur
at most once in a def body. Every call argument and every operand counts.
VERIFIED: four of five i00 models hit it.

    def cell_is_filled(row_index: U32, column_index: U32) -> Bool:    # rejected
      U32.is_eq((column_index .&. row_index : U32), column_index)     # column_index twice
    def cell_is_filled(row_index: U32, +column_index: U32) -> Bool:   # accepted

`+` needs a `Data` type: never a function, an `Array` or an IO handle.

**R2. A match hands its binders the matched parameter's quantity.** On a `+`
parameter, `case 1n+smaller_depth:` binds a reusable `smaller_depth`; on a
plain parameter it binds an affine one. VERIFIED (terra's first error; opus's
`+depth` used its predecessor twice and passed). The guide also allows
`+binder` inside the pattern itself, spelled `case 1n++smaller_depth:`
(STATED form; the spelling is UNVERIFIED here).

**R3. The shrinking parameter comes first.** A self-call's arguments are read
left to right: each passes unchanged until one is a strict subterm of its
parameter, and everything after it is free. VERIFIED (large, medium).

    def row_text(+row_index: U32, +column_index: U32, columns_left: Nat)   # rejected:
      ... row_text(row_index, (column_index + 1 : U32), rest)              # changes before the shrink
    def row_text(columns_left: Nat, +row_index: U32, +column_index: U32)   # accepted
      ... row_text(rest, row_index, (column_index + 1 : U32))

**R4. Match parameters in signature order.** For `(fuel: Nat, stop: Bool)`:
`match fuel stop:`, or `match fuel:` with `match stop:` nested inside. Matching
`stop` first is rejected with "a match on a parameter or field (this name is a
def or a consumed binder)". The message does not mention order. VERIFIED
(large, medium).

**R5. A computed value is matched through a helper, and the helper must not
call back.** A helper that returns a value is fine. A helper that decides
whether to recurse and then calls the recursive def is mutual recursion.
STATED, and VERIFIED as a failure mode (large's first design).

**R6. Early-exit loops: the flag is a parameter.** Put the fuel first and a
`Bool` flag computed by the caller for the state it hands over; match fuel,
then flag. One def, no helper, early exit preserved. VERIFIED (sonnet, large
and medium all converged on it, none having seen a reference):

    def escape_count(remaining: Nat, has_escaped: Bool, +z_real: F32, ...) -> Nat:
      match remaining has_escaped:
        case 0n _:
          0n
        case 1n+rest True{}:
          0n
        case 1n+rest False{}:
          ... 1n+escape_count(rest, F32.is_gt(new_magnitude, 4.0), new_real, ...)

Test the NEW z in the flag you hand forward. Testing the current z detects
escape one step late (large's final code).

**R7. Define before use.** A def must appear above any def that calls it;
self-recursion is the only exception. The error is "expected : a defined name".
VERIFIED (sonnet fixed it by reordering; medium hit it again later). The guide
states this only for templates ("A template may call only templates declared
above it"), which reads as if plain defs were unordered. They are not.

**R8. Mutual recursion: prefer R6.** Base does build mutual recursion with a
`law` forward declaration that a later `def` fills (`Word.adc`,
`String.trim_start`, `U32.show.go`, `Map.put`). In a user file the same shape
failed: "an unfilled law is a dead claim: live code cannot use it" (sonnet).
What makes Base's version work is UNVERIFIED. In all four Base instances the
shrinking parameter is first in the law's `for` list, and sonnet's was third.

**R9. No unary minus.** `-2.0` does not parse ("expected : a term, observed :
'-'"). Write `F32.neg(2.0)` or `(0.0 - 2.0 : F32)`. VERIFIED (medium; F32.neg
passed in sonnet, large and medium).

**R10. A balanced fork recurses on a depth and halves the span.** VERIFIED:
opus, sonnet and large all passed with this shape, in this layout:

    def picture(+depth: Nat, +first_row_index: U32, +half_row_count: U32) -> List<&2, String>:
      match depth:
        case 0n:
          line(first_row_index) <> Nil{}
        case 1n+depth_predecessor:
          upper_rows lower_rows =
            picture(depth_predecessor, first_row_index, U32.shr(half_row_count))
            picture(depth_predecessor, U32.add(first_row_index, half_row_count),
              U32.shr(half_row_count))
          List.append(&2, String, upper_rows, lower_rows)

Peeling one or two rows against the rest gives a linear chain: it compiles and
barely forks (medium). Two sides of one parallel let should do similar work.
Pairing a Mandelbrot against a Sierpinski is about 100:1 (large).

**R11. Modules.** `import ./LAWS.bend as Laws`; PROOF.bend fills `law name`
with `def Laws.name(params):`. VERIFIED (all five). Aliases are not
re-exported, so PROOF.bend also imports playground.bend to name its defs; this
passed (opus, sonnet), but whether it is required is UNVERIFIED. A non-Base
import without `as` is reported rejected (medium's notes quote the message):
UNVERIFIED.

**R12. Dotted names need no declared type.** `Mandelbrot.width`,
`Picture.row_count` and `Sierpinski.cell.from_shared_bits` all passed with no
`type Mandelbrot`, `Picture` or `Sierpinski` in the file. VERIFIED (opus,
sonnet).

**R13. `do` blocks.** Consecutive IO steps: VERIFIED (opus, two `IO.print`
steps). A parallel let at def level, above the `do`: VERIFIED (large;
medium's last session). Destructuring `(a, b) = v` where `v` is a parameter:
VERIFIED (terra). `x : T = v` inside `do`: STATED in the guide, reported
failing once (medium), so UNVERIFIED either way. Keep such lets above the
`do` until you have checked.

**R14. Literals and operators.** Char literals `'#'`, `' '` and `'\n'`, `Chr{42}`,
and the string `"\n"`: all VERIFIED. Typed operators `(a + b : U32)`: VERIFIED
(large). Operators need spaces on both sides: STATED.

**R15. Indentation is structure.** A `case` must stay indented under its
`match`. Pasting a lone branch without its enclosing def lost that
indentation and produced "expected : 'def', 'type' or 'law'" (terra).
VERIFIED. When repairing, send whole defs, not fragments.

---

## C. Laws and proofs

**L1. F32 never reduces in a proof.** Every F32 operation in Base is a `law`
with no body: it runs, but the checker cannot evaluate it. No law about a
float result can be discharged. STATED (Base; upstream README). `--verdict`
(2.0.32) does not yet accept axiomatic F32.

**L2. U32 and Nat operations do reduce.** They are ordinary defs, so a ground
law such as `cell_is_filled(2, 1) == False{}`, going through `U32.and` and
`U32.is_eq`, closes with `{==}`. VERIFIED (large: ten such laws, "All terms
check.").

**L3. Induct on the argument the def recurses on.** The recursive call is the
induction hypothesis, and a `%e : P` rewrite applies it. VERIFIED (opus,
sonnet, medium). A law about a def containing a parallel let still
discharges: VERIFIED (opus).

**L4. A law checks exactly what it says.** A row-count or length law is
satisfied by an implementation that duplicates every row (opus and sonnet
each retracted such a claim). In every law's comment, name one wrong
implementation the law rejects and one it still accepts. If you cannot name
one it rejects, the law is decoration.

**L5. Types, erased arguments and equations are checked "dead"** and do not
spend a variable's uses. STATED, in "Under the Hood", far from the Quantities
section; consistent with sonnet reusing variables inside rewrite motives. Code
that runs, including proof code, is checked live: proofs are not exempt from
affinity.

**L6. A `{==}` failure that prints two constructor values** (expected
`True{}`, observed `False{}`) means both sides reduced. The law is most
likely false as written, not stuck. UNVERIFIED inference; test a base case
before defending the law.

**L7. Whether `+` on a law's `for` clause carries over to a filling def in
another file** is UNVERIFIED. Sonnet worked around it with local `+` lets.

---

## D. Claims known to be false

- "A Nat countdown cannot give a balanced fork." See R10.
- "U32.and does not reduce in proofs." See L2.
- "`Foo.bar` needs a declared type `Foo`." See R12.
- "Proof code is exempt from affine tracking." See L5; sonnet hit four
  affinity errors believing it.
- "Mutual recursion is impossible." The guide says so, but Base does it. See R8.

---

## E. Error decoder

The display changed in 2.0.32 ("errors underline the exact code"), so match on
the phrase, not the layout.

| Message contains | Class | Rule | Usual fix |
|---|---|---|---|
| `X (consumed more than once)` | E-AFFINE | R1, R2 | `+` on the binding or on the matched parameter |
| `a decreasing self-call` | E-TERMINATION | R3 | shrinking parameter first |
| `a match on a parameter or field` / `consumed binder` | E-SCRUTINEE | R4, R5 | match in signature order; helper for computed values |
| `a defined name` | E-UNDEFINED | R7 | move the def above its caller |
| `an unfilled law is a dead claim` | E-UNFILLED-LAW | R8 | thread a flag parameter (R6) |
| `expected : a term`, `observed : '-'` | E-PARSE | R9 | `F32.neg` |
| `expected : 'def', 'type' or 'law'` | E-PARSE | R15 | restore indentation |
| `expected : a pattern` | E-PARSE | R13 | move the statement out of the `do` |
| `expected : an import` | E-PARSE | R11 | `import <path> as <Name>` |
| two constructor values in a PROOF.bend error | E-OTHER | L6 | test a base case; suspect the law |
