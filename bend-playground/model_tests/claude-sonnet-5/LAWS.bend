# LAWS.bend -- laws over playground.bend.
#
# Scoped to the shape of the parallel computation (fuel-driven row width,
# and the fork tree's leaf count), not to Mandelbrot's float arithmetic or
# Sierpinski's bitwise geometry: Base declares F32's arithmetic ops via
# `law ... F32` with no accompanying def (no algebraic facts about them
# exist anywhere to build on), and no zero/successor-style lemma about
# U32.and exists either, so a law resting on either would be proven cold,
# with nothing in Base to lean on. These two laws instead mirror proof
# shapes Base or "bend guide" already carry out successfully: add_zero's
# one-rewrite induction, and a length fact by structural induction on the
# same fuel argument the function itself recurses on.
#
# Only the Sierpinski pipeline is covered, not Mandelbrot's: the fork-tree
# law below never inspects what the per-cell function computes, only how
# many constructors the tree builds, so the identical argument goes
# through for Mandel.render_row/render_rows unchanged. Re-deriving it a
# second time would be proof surface that buys nothing.

import Base
import ./playground.bend as Playground

# Every row Sierpinski.render_row builds has exactly as many characters as
# the fuel argument it was given: no column is dropped or duplicated by
# the walk.
law Sierpinski.render_row_length:
  for row_index: U32
  for remaining_columns: Nat
  for column_index: U32
  {String.length(
      Playground.Sierpinski.render_row(row_index, remaining_columns, column_index))
    == remaining_columns : Nat}

# Sierpinski.render_rows's fork tree produces exactly one row per leaf: no
# row is lost or doubled by the parallel split. Playground.Sierpinski.rows_count
# counts leaves by the identical doubling recursion render_rows itself
# forks on, so this is the statement that the fork tree's shape matches
# its own leaf count -- the fact this whole exercise is meant to
# demonstrate about the parallelism, not just the pictures it draws.
law Sierpinski.render_rows_count:
  for level: Nat
  for row_start: U32
  for total_columns: Nat
  {List.length(&2, String,
      Playground.Sierpinski.render_rows(level, row_start, total_columns))
    == Playground.Sierpinski.rows_count(level) : Nat}
