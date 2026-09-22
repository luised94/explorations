# playground.bend -- an ASCII Mandelbrot set, then an ASCII Sierpinski
# triangle, printed via IO.print.
#
# Fork tree shape: both images are rendered by the same two-layer
# recursion. The outer layer (*.render_rows) halves a level: Nat every
# step, exactly like pow2 in "bend guide" (the one parallel-call shape the
# guide's own examples exercise), so a request for 2^level rows becomes a
# balanced binary fork tree of depth level, each leaf handling exactly one
# row. The inner layer (*.render_row) is a flat, non-forking,
# tail-recursive walk across one row's columns, matching "bend guide
# shaders"'s rule that a leaf should end in a flat loop, not another fork.
# Rows are not forked per-pixel: the shader guide is explicit that "a fork
# per pixel drowns in scheduling," and a fork per cell (here, per row
# already gives 32 leaves) is the tradeoff its own reference rasterizer
# makes at its tile boundary.

import Base

# --- Sierpinski triangle -------------------------------------------------

# Sierpinski.cell (below) needs to branch on a *computed* Bool. "bend
# guide" is explicit that a match may only inspect a parameter or a
# variable bound by a pattern, never a computed value ("To match on a
# computed value, pass it to a helper that matches on its parameter.").
# This helper is forced by that rule, not chosen for style. It is defined
# ahead of its caller, not forward-declared via a law, because "a defined
# name" here means exactly that: unlike Mandel.escape_count/.branch below
# (a genuine call cycle, which does need a law), this helper never calls
# back into Sierpinski.cell, so plain define-before-use order is enough --
# and is in fact required, per the error this ordering originally produced.
def Sierpinski.cell.from_shared_bits(no_shared_bits: Bool) -> Char:
  match no_shared_bits:
    case True{}:
      '*'
    case False{}:
      ' '

# A cell is filled exactly where its row and column indices share no set
# bit -- the standard bitwise construction of Pascal's triangle mod 2,
# which is the Sierpinski triangle. Pure U32 arithmetic, no recursion, so
# it carries no termination obligation of its own.
def Sierpinski.cell(row_index: U32, column_index: U32) -> Char:
  Sierpinski.cell.from_shared_bits(U32.is_zero(U32.and(row_index, column_index)))

# One row's characters, left to right, with no trailing newline (added
# once, outside this def, by String.join over the row list -- so this
# def's own length is exactly remaining_columns; see LAWS.bend).
#
# Termination: row_index is unchanged across the recursive call (it sits
# before the parameter that shrinks, so "bend guide"'s left-to-right rule
# requires it to stay the same variable); remaining_columns is the
# structurally decreasing fuel (1n+columns_left -> columns_left); and
# column_index is free because it comes after the shrinking parameter, so
# incrementing it is allowed.
#
# +row_index and +column_index: each is read once to build this row's own
# character and once more to hand unchanged (or incremented) to the
# recursive call -- two uses of a Data value, so the checker needs + on
# both.
def Sierpinski.render_row(
  +row_index: U32, remaining_columns: Nat, +column_index: U32
) -> String:
  match remaining_columns:
    case 0n:
      SNil{}
    case 1n+columns_left:
      SCon{
        Sierpinski.cell(row_index, column_index),
        Sierpinski.render_row(row_index, columns_left, U32.inc(column_index))
      }

# The fork tree itself. level halves at every step, the one parallel-call
# shape "bend guide" actually verifies (pow2), so the row range
# [row_start, row_start + 2^level) splits into two equal, independent
# halves that recurse in parallel and are joined with List.append. At
# level 0 a single row is rendered by the flat loop above, with no
# further forking -- the shader guide's rule that a leaf ends in a flat
# loop, not another fork.
#
# +level: marking the matched parameter reusable hands + to the field the
# match extracts (levels_left), which is used three times below (the
# power, and both recursive calls) with no extra annotation needed on the
# pattern itself -- this mirrors pow2's own +n parameter exactly.
# +row_start and +total_columns are read once per branch of the parallel
# let (two branches, two reads each), so they need their own marks; that
# reuse is not inherited from anything.
def Sierpinski.render_rows(
  +level: Nat, +row_start: U32, +total_columns: Nat
) -> List<&2, String>:
  match level:
    case 0n:
      [Sierpinski.render_row(row_start, total_columns, 0)]
    case 1n+levels_left:
      row_offset = U32.pow(2, levels_left)
      left_rows right_rows =
        Sierpinski.render_rows(levels_left, row_start, total_columns)
        Sierpinski.render_rows(levels_left, U32.add(row_start, row_offset), total_columns)
      List.append(&2, String, left_rows, right_rows)

# Counts the rows Sierpinski.render_rows produces, by the identical
# doubling shape, so LAWS.bend's fork-tree law can equate the two with no
# Nat.pow unfolding lemma: matching shapes make the successor case close
# from List.append_length alone (see PROOF.bend) once lengths are
# substituted.
def Sierpinski.rows_count(+level: Nat) -> Nat:
  match level:
    case 0n:
      1n
    case 1n+levels_left:
      Nat.add(Sierpinski.rows_count(levels_left), Sierpinski.rows_count(levels_left))

# --- Mandelbrot set --------------------------------------------------------

def Mandel.plane_left() -> F32:
  F32.neg(2.5)

def Mandel.plane_right() -> F32:
  1.0

def Mandel.plane_top() -> F32:
  1.0

def Mandel.plane_bottom() -> F32:
  F32.neg(1.0)

def Mandel.max_iterations() -> Nat:
  30n

def Mandel.image_width() -> Nat:
  78n

def Mandel.image_height() -> Nat:
  32n

# Escape-time iteration z = z^2 + c, counting down a fuel argument instead
# of an unbounded loop (a loop bounded by an external stopping rule counts
# down a Nat fuel argument, per "bend guide"'s recursion section). Returns
# iterations_left at the moment of escape (small means it escaped late,
# i.e. close to the set; 0n both on the "ran out of fuel" path and as the
# smallest possible escape value, so it doubles as "probably inside the
# set" for Mandel.density_char with no special case needed).
#
# This def and Mandel.escape_count.branch call each other -- exactly the
# mutual pattern Base itself uses for Word.adc/Word.adc.con (Word.adc's
# Succ case calls Word.adc.con(p, ...), which calls back Word.adc(p, ...)
# with that same already-decremented p). "bend guide" says two ordinary
# defs cannot call each other; Base's own resolution, followed here, is to
# declare the callee-that-is-called-first via a law before the helper that
# forward-references it, then give the real def afterward.
law Mandel.escape_count:
  for +constant_real_part: F32
  for +constant_imaginary_part: F32
  for remaining_iterations: Nat
  for +iterate_real_part: F32
  for +iterate_imaginary_part: F32
  Nat

# +real/+imaginary parts: each is read twice on the not-escaped path (once
# inside the new z's arithmetic, once again passed on to the next
# iteration), so each needs +.
def Mandel.escape_count.branch(
  +constant_real_part: F32, +constant_imaginary_part: F32, iterations_left: Nat,
  +iterate_real_part: F32, +iterate_imaginary_part: F32, has_escaped: Bool
) -> Nat:
  match has_escaped:
    case True{}:
      iterations_left
    case False{}:
      Mandel.escape_count(
        constant_real_part, constant_imaginary_part, iterations_left,
        F32.add(
          F32.sub(F32.square(iterate_real_part), F32.square(iterate_imaginary_part)),
          constant_real_part),
        F32.add(
          F32.mul(2.0, F32.mul(iterate_real_part, iterate_imaginary_part)),
          constant_imaginary_part))

# remaining_iterations matches on a computed Bool (whether |z|^2 > 4) the
# same way Sierpinski.cell does above -- another instance of "bend
# guide"'s "match a computed value only through a helper" rule, this time
# also serving as the mutual-recursion escape hatch described above.
def Mandel.escape_count(
  constant_real_part, constant_imaginary_part, remaining_iterations,
  iterate_real_part, iterate_imaginary_part
):
  match remaining_iterations:
    case 0n:
      0n
    case 1n+iterations_left:
      Mandel.escape_count.branch(
        constant_real_part, constant_imaginary_part, iterations_left,
        iterate_real_part, iterate_imaginary_part,
        F32.is_gt(
          F32.add(F32.square(iterate_real_part), F32.square(iterate_imaginary_part)),
          4.0))

# "bend guide shaders" warns against generic Bool.pick on hot per-lane
# paths (it boxes and heats the type); this grid is 78x32 cells checked
# once each, not a per-frame shader loop, so the generic form's clarity is
# worth its cost here and there is no typed pick for Char to reach for
# instead.
def Mandel.density_char(+iterations_left: Nat, +max_iterations: Nat) -> Char:
  Bool.pick(Char, Nat.is_lt(iterations_left, Nat.div(max_iterations, 8n)), '@',
    Bool.pick(Char, Nat.is_lt(iterations_left, Nat.div(max_iterations, 4n)), '#',
      Bool.pick(Char, Nat.is_lt(iterations_left, Nat.div(max_iterations, 2n)), '+',
        Bool.pick(Char, Nat.is_lt(iterations_left, max_iterations), '.', ' '))))

def Mandel.cell(row_index: Nat, column_index: Nat, image_width: Nat, image_height: Nat) -> Char:
  constant_real_part = F32.add(Mandel.plane_left(),
    F32.mul(F32.sub(Mandel.plane_right(), Mandel.plane_left()),
      F32.div(F32.from_nat(column_index), F32.from_nat(image_width))))
  constant_imaginary_part = F32.add(Mandel.plane_top(),
    F32.mul(F32.sub(Mandel.plane_bottom(), Mandel.plane_top()),
      F32.div(F32.from_nat(row_index), F32.from_nat(image_height))))
  Mandel.density_char(
    Mandel.escape_count(constant_real_part, constant_imaginary_part, Mandel.max_iterations(), 0.0, 0.0),
    Mandel.max_iterations())

# Same shape and same termination argument as Sierpinski.render_row:
# row_index, image_width and image_height are unchanged across the call
# (so they sit before the shrinking parameter), remaining_columns is the
# fuel, column_index is free after it.
def Mandel.render_row(
  +row_index: Nat, +image_width: Nat, +image_height: Nat,
  remaining_columns: Nat, +column_index: Nat
) -> String:
  match remaining_columns:
    case 0n:
      SNil{}
    case 1n+columns_left:
      SCon{
        Mandel.cell(row_index, column_index, image_width, image_height),
        Mandel.render_row(row_index, image_width, image_height, columns_left, 1n+column_index)
      }

# Same fork shape as Sierpinski.render_rows, for the same reason: a
# balanced binary tree of depth level, joined with List.append.
def Mandel.render_rows(
  +level: Nat, +row_start: Nat, +image_width: Nat, +image_height: Nat
) -> List<&2, String>:
  match level:
    case 0n:
      [Mandel.render_row(row_start, image_width, image_height, image_width, 0n)]
    case 1n+levels_left:
      row_offset = Nat.pow(2n, levels_left)
      left_rows right_rows =
        Mandel.render_rows(levels_left, row_start, image_width, image_height)
        Mandel.render_rows(levels_left, Nat.add(row_start, row_offset), image_width, image_height)
      List.append(&2, String, left_rows, right_rows)

# --- Entry point -----------------------------------------------------------

# level = 5n gives 32 rows for both images (2^5): Sierpinski's own width
# is also chosen as 32 so the triangle is square; Mandelbrot's
# image_height constant above is set to the same 32 so its fork tree
# exactly covers its own image with no leftover or missing rows.
def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(String.join(Sierpinski.render_rows(5n, 0, 32n), "\n"))
    IO.print(String.join(
      Mandel.render_rows(5n, 0n, Mandel.image_width(), Mandel.image_height()), "\n"))
