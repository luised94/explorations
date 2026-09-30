# Draft issue: guide statements that sent AI models wrong

Status: DRAFT, not filed. Written against the `bend guide` and `bend base`
output of bend 2.0.16. By 2.0.32 the guide may have changed.

## Before filing

1. Regenerate the docs: `uv run bendlab.py prompt` writes the current
   `bend guide` and `bend base` into `prompt.md`.
2. For each item, search `prompt.md` for the quoted text. Strip markdown
   emphasis and backticks first: a plain search once missed "checked
   \*live\*". Drop items whose quote is gone or already fixed. Update quotes
   whose wording changed.
3. Check the issue tracker for duplicates.
4. Item 6 says the demos use `case 1n++p:`. That comes from your own reading
   of the demos, not from anything in this directory; confirm it in the
   repo before filing.
5. Keep the discussion about laws (`upstream-discussion.md`) separate. That is
   an argument about the thesis; this is a list of documentation bugs, and
   mixing them gets the bugs ignored.

---

## Title

Guide: nine statements that led AI models into compiler errors (evidence from a 5-model test)

## Body

I asked five models (three proprietary, two open-weight) to write the same
small Bend program: an ASCII Mandelbrot and Sierpinski renderer, plus
`LAWS.bend` and `PROOF.bend`. They got `bend guide` and `bend base` as their
only reference, on bend 2.0.16, and could not run the compiler; I pasted each
error back. All five eventually reached "All terms check." The errors
clustered on a few passages of the guide. Each item below gives the passage,
what went wrong, and a suggested wording. One run per model, so read the
counts as indicative.

### 1. "mutual recursion is not allowed", but Base does it

> Termination is mandatory and mutual recursion is not allowed.

Base forward-declares a function with a `law` and fills it with a `def` below
a helper that calls it: `Word.adc` / `Word.adc.con`, `String.trim_start` /
`String.trim_start.if`, `U32.show.go` / `U32.show.fin`, `Map.put` /
`Map.put.bit`. One model copied that shape in its own file and got
"an unfilled law is a dead claim: live code cannot use it", then fell back to
the guide's selector-argument advice without learning what made Base's
version legal. In all four Base instances the shrinking parameter comes first
in the law's `for` list; in the model's version it came third. That may or
may not be the difference.

Suggested: state whether user code may use the law-forward-declaration
pattern and under what conditions, or say that it is Base-only.

### 2. Define-before-use is stated only for templates

> A template may call only templates declared above it.

Plain defs have the same restriction: a call to a def defined further down
the file fails with "expected : a defined name". One model hit it and fixed it
by reordering; a second reported the same error in its own session notes.
Because
the only ordering sentence in the guide is scoped to templates, it reads as
if defs were unordered.

Suggested, in Recursion and Termination: "A def must be defined above any def
that calls it; only a def's own self-call may refer to it before its
definition ends."

### 3. "Binder order" is never defined, and its diagnostic does not mention order

> Scrutinees follow binder order, and a `let` may not precede a `match` on a parameter.

One model read "binder order" as "the order in which the match binds its
pattern variables", which makes the rule vacuous. Two models matched a later
parameter before an earlier one and received "a match on a parameter or field
(this name is a def or a consumed binder: give the value its own def)",
which sent both looking for a consumption problem. Every multi-scrutinee match
in the guide and in Base happens to follow parameter order, so no example
shows a violation.

Suggested: "Scrutinees follow the order of the parameters in the def's own
signature: with `(fuel: Nat, stop: Bool)`, write `match fuel stop:` or nest
`match fuel:` then `match stop:`; matching `stop` first is rejected." If
possible, the diagnostic could name the ordering.

### 4. The termination rule has no counterexample

> The check reads the arguments of a recursive call from left to right: each must be passed unchanged until one is a smaller part of its parameter, and the ones after it are free.

Correct and precise, but every recursive example puts the shrinking parameter
first, so the constraint is invisible by example. Two models placed a changing
argument before the shrinking one (`go(row, col + 1, rest)`). One read the
rule as "some argument shrinks somewhere". The compiler's own wording, "each
passed unchanged until one shrinks", was clearer to them than the guide's.

Suggested: one rejected/accepted pair next to the rule.

### 5. Affinity: "used" reads as runtime consumption

> Bend, by default, is *affine*, meaning variables must be used, at most, once.

Four of five models hit "consumed more than once", usually for a name that
appears as two arguments of one call, or in a let and again in a self-call.
The guide has no example of a function that reads a parameter twice and needs
`+`, and does not show the diagnostic.

Suggested: "Each occurrence of a variable in a def body counts as a use: every
call argument and every operand. `U32.is_eq(U32.and(a, b), a)` uses `a`
twice, so it must be bound as `+a`. The error reads `a (consumed more than
once)`."

### 6. A matched parameter's quantity carries to its binders, and `1n+p` is a constructor pattern

> Matching a `+` value hands out `+` fields; on a plain one, write `+r` in the pattern to make a field reusable.

This is the rule, but nothing connects it to the `1n+p` Nat sugar, which is
where models needed it. One model bound `case 1n+smaller:` on a plain `Nat`,
used `smaller` in four parallel calls, and got "consumed more than once";
another designed around the question. The demos use `case 1n++p:`, which the
guide never shows.

Suggested: add "The `1n+p` sugar is a constructor pattern: on a `+` parameter
`p` is reusable; on a plain one write `case 1n++p:`."

### 7. No unary minus

> Operators need spaces on both sides.

This is the only nearby sentence. `-2.0` fails with "expected : a term,
observed : '-'". One model hit it, and another avoided it only by inference.

Suggested, in the Syntax Reference: "There is no unary minus: `-2.0` does not
parse. Write `F32.neg(2.0)` or `(0.0 - 2.0 : F32)`."

### 8. The rule on which occurrences count is only in "Under the Hood"

> Code that runs is checked *live*; types, erased arguments and equations are checked *dead*.

This sentence decides whether a variable used inside a type, an erased
argument or a rewrite motive spends a use. It sits in Under the Hood, far from
Quantities. One model re-derived it from error messages; another listed it as
missing from the guide entirely.

Suggested: a one-sentence cross-reference in Quantities.

### 9. The shaders guide does not say where its numbers apply

> Aim for 4^7 leaves per bang, one per lane

Every model that was asked (four of four) said the shaders guide pulled their
text-output program the wrong way. One built 4,096 two-character leaves;
another skipped `!` because 48 leaves looked absurd beside 16,384; another
wrote GPU-divergence justifications for a 32x78 grid computed once. The
structural advice (one fork tree, balanced siblings, flat leaves) was right
for them; the numbers were not.

Suggested: "These numbers describe a 1920x1200 rasterizer at 120 FPS. Below a
few thousand leaves the shape advice still holds and the lane-count numbers do
not."

---

Happy to share the full data: the five models' files at every attempt, the
compiler output, and a written report.
