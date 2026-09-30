import Base
import ./playground.bend as Playground

# Why these six laws and not others.
#
# Every F32 operation in Base is a bare `law` with no def: a primitive with a
# runtime implementation and no computational content the checker can reduce.
# So no claim about a Mandelbrot value -- membership, escape count, which shade
# a cell gets -- is provable here, by anyone, ever. Everything below is
# therefore structural: it constrains the shape of the output and says nothing
# about the numbers in it. That is not a weakness of the choice, it is the
# boundary of what F32-as-a-law leaves provable.
#
# Also excluded: the Sierpinski bit identity ("column zero is all stars"). It
# needs U32.and(row, 0) to reduce, which needs the literal 0 to unfold into a
# 32-deep Word of False. Nothing in Base ever forces a U32 literal to unfold --
# U32.add_comm inducts over Word variables, never literals -- so whether the
# checker does it is unknown, and a deliverable is not the place to find out.
#
# What survives is worth having. The row laws say the frame is rectangular no
# matter what the shading does, which is exactly the property that holds even
# though the cell contents are opaque. The picture laws say the fork tree emits
# precisely the rows it promises: each branch of every parallel call contributes
# exactly half, with nothing dropped or duplicated by the split. That is the one
# claim here that is actually about the parallelism.

# Quantities: every index is `+` because the proofs read it once for the
# induction hypothesis and again to write out the rewrite motive. The Nat being
# inducted on stays affine -- it is only ever matched.

law mandelbrot_row_length:
  for columns_remaining: Nat
  for +row_index: U32
  for +column_index: U32
  for +line_tail: String
  {String.length(Playground.Mandelbrot.row(columns_remaining, row_index,
    column_index, line_tail))
    == Nat.add(columns_remaining, String.length(line_tail)) : Nat}

law sierpinski_row_length:
  for columns_remaining: Nat
  for +row_index: U32
  for +column_index: U32
  for +line_tail: String
  {String.length(Playground.Sierpinski.row(columns_remaining, row_index,
    column_index, line_tail))
    == Nat.add(columns_remaining, String.length(line_tail)) : Nat}

# Nat.add(width, 1n) rather than 1n+width: Nat.add reduces on its first
# argument, so with a variable width the sum is stuck, and 1n+width would be a
# different (unprovable without a further lemma) claim.
law mandelbrot_line_length:
  for width: Nat
  for +row_index: U32
  {String.length(Playground.Mandelbrot.line(width, row_index))
    == Nat.add(width, 1n) : Nat}

law sierpinski_line_length:
  for width: Nat
  for +row_index: U32
  {String.length(Playground.Sierpinski.line(width, row_index))
    == Nat.add(width, 1n) : Nat}

# depth is `+` because Picture.row_count itself takes a `+` argument, and the
# proof inducts by calling itself twice on the predecessor, once per half.
law mandelbrot_picture_row_count:
  for +depth: Nat
  for +first_row_index: U32
  for +half_row_count: U32
  {List.length(&2, String,
    Playground.Mandelbrot.picture(depth, first_row_index, half_row_count))
    == Playground.Picture.row_count(depth) : Nat}

law sierpinski_picture_row_count:
  for +depth: Nat
  for +first_row_index: U32
  for +half_row_count: U32
  {List.length(&2, String,
    Playground.Sierpinski.picture(depth, first_row_index, half_row_count))
    == Playground.Picture.row_count(depth) : Nat}
