# playground.bend
# Draws an ASCII Mandelbrot set, then an ASCII Sierpinski triangle.
#
# All custom defs are snake_case with no dots. The dotted names the previous
# version used (Sierpinski.row and friends) produced the resolver error
# "expected : a defined name, observed : Sierpinski.row" even though the def
# was declared earlier in the file. Flattening removes every "one def name is
# a prefix of another def name" relationship and every dotted prefix that is
# not itself a def, which is the class of names the resolver seemed to
# misread.
#
# Parallelism: the fork tree comes from mandelbrot_render_lines_remaining.
# Each level of that recursion splits one remaining-rows job into two: the
# next two rows are computed by a parallel let, and the recursion over the
# rest of the rows is the tail of the same job. The tree is a chain of
# binary forks, one per two rows. Row work is uniform (same width, same
# budget per pixel), so the two sides of each fork finish together and the
# scheduler does not stall on a slow branch. Sierpinski is left sequential:
# its rows are one bitwise test per cell, so fork overhead would dominate
# the work.

import Base

# --- Shared helpers ---

# count is first because the termination checker reads the self-call's
# arguments left to right: each must be passed unchanged until one is a
# strict subterm. With count first, rest is the first argument and it
# shrinks. The alternative, building the string with String.append, would
# need an append-length lemma before any length law could be stated, and
# Base does not supply one.
def repeat_character(count: Nat, +character: Char) -> String:
  match count:
    case 0n:
      SNil{}
    case 1n+rest:
      SCon{character, repeat_character(rest, character)}

# --- Printing ---

# One IO.print per line, sequenced with bind. A recursive helper is forced
# because Bend has no loop syntax; a fold would need the whole list built
# before any line could print, which the affine checker would then have to
# keep alive across every step.
def print_lines(lines: List<&2, String>) -> IO(Unit):
  match lines:
    case Nil{}:
      IO.pure(Unit, Unit{})
    case head <> tail:
      IO.bind(Unit, Unit, IO.print(head), ignored_result => print_lines(tail))

# --- Mandelbrot ---

# A leading minus on a numeric literal is not accepted by the lexer, so the
# negative real bound goes through F32.neg. The Mandelbrot set lives in real
# [-2.0, 0.5], imaginary [-1.25, 1.25]; those bounds are chosen so the
# picture fits the terminal without cropping. The map is linear, so one
# multiply and one add per axis is enough.
def mandelbrot_real_coordinate(column_index: Nat, width: Nat) -> F32:
  F32.add(
    F32.neg(2.0),
    F32.mul(2.5, F32.div(F32.from_nat(column_index), F32.from_nat(width)))
  )

def mandelbrot_imaginary_coordinate(row_index: Nat, height: Nat) -> F32:
  F32.sub(
    1.25,
    F32.mul(2.5, F32.div(F32.from_nat(row_index), F32.from_nat(height)))
  )

# The escape decision is a pure function of the final iteration count, so it
# is split out. The alternative, inlining the comparison in the row builder,
# would force a match on a computed value, which Bend rejects.
def mandelbrot_pick_character(in_set: Bool) -> Char:
  match in_set:
    case True{}:
      '*'
    case False{}:
      ' '

# remaining_iterations is first because the termination checker reads the
# self-call's arguments left to right. With the escape flag first, the first
# argument of the self-call was the computed value F32.is_gt(...), which is
# neither passed unchanged nor a subterm, so the checker rejected the call.
# The escape flag is a parameter rather than a match on F32.is_gt(...), which
# Bend rejects as a match on a computed value, and a helper def that calls
# back into this one would be mutual recursion, which the termination
# checker also rejects. A single two-scrutinee match keeps the scrutinees in
# binder order.
def mandelbrot_escape_iterations(
  remaining_iterations: Nat,
  point_has_escaped: Bool,
  +real_part: F32,
  +imaginary_part: F32,
  +real_constant: F32,
  +imaginary_constant: F32
) -> Nat:
  match remaining_iterations point_has_escaped:
    case 0n _:
      0n
    case 1n+rest True{}:
      0n
    case 1n+rest False{}:
      +new_real_part = F32.add(
        F32.sub(
          F32.mul(real_part, real_part),
          F32.mul(imaginary_part, imaginary_part)
        ),
        real_constant
      )
      +new_imaginary_part = F32.add(
        F32.mul(2.0, F32.mul(real_part, imaginary_part)),
        imaginary_constant
      )
      +new_magnitude_squared = F32.add(
        F32.mul(new_real_part, new_real_part),
        F32.mul(new_imaginary_part, new_imaginary_part)
      )
      1n+mandelbrot_escape_iterations(
        rest,
        F32.is_gt(new_magnitude_squared, 4.0),
        new_real_part,
        new_imaginary_part,
        real_constant,
        imaginary_constant
      )

# max_iterations is marked + because it is read twice: once as the budget
# passed into mandelbrot_escape_iterations and once again in the is_eq that
# decides whether the point stayed in the set.
def mandelbrot_character_at(
  column_index: Nat,
  row_index: Nat,
  width: Nat,
  height: Nat,
  +max_iterations: Nat
) -> Char:
  +real_coordinate = mandelbrot_real_coordinate(column_index, width)
  +imaginary_coordinate = mandelbrot_imaginary_coordinate(row_index, height)
  +iteration_count = mandelbrot_escape_iterations(
    max_iterations,
    False{},
    0.0,
    0.0,
    real_coordinate,
    imaginary_coordinate
  )
  mandelbrot_pick_character(Nat.is_eq(iteration_count, max_iterations))

# column_count is first because the termination checker reads the self-call's
# arguments left to right. With start_column first, the first argument of the
# self-call grew (1n+start_column), which the checker rejects. With
# column_count first, rest is the first argument and it shrinks. start_column
# still has to be carried because the two parallel halves of a row cannot see
# each other's state; without it the right half would need to know how many
# characters the left half produced, which would serialise the two halves.
def mandelbrot_render_row_segment(
  column_count: Nat,
  +start_column: Nat,
  +row_index: Nat,
  +width: Nat,
  +height: Nat,
  +max_iterations: Nat
) -> String:
  match column_count:
    case 0n:
      SNil{}
    case 1n+rest:
      SCon{
        mandelbrot_character_at(
          start_column,
          row_index,
          width,
          height,
          max_iterations
        ),
        mandelbrot_render_row_segment(
          rest,
          1n+start_column,
          row_index,
          width,
          height,
          max_iterations
        )
      }

# Splitting the row in half is what gives the CPU or GPU two independent
# tasks per row. Without it, one row is one task and every other lane sits
# idle. half_width is a parameter rather than Nat.div(width, 2n) because
# matching on the result of Nat.divmod would be a match on a computed value.
def mandelbrot_render_row(
  +row_index: Nat,
  +half_width: Nat,
  +width: Nat,
  +height: Nat,
  +max_iterations: Nat
) -> String:
  left_half right_half = mandelbrot_render_row_segment(
    half_width, 0n, row_index, width, height, max_iterations
  ) mandelbrot_render_row_segment(
    half_width, half_width, row_index, width, height, max_iterations
  )
  String.append(left_half, right_half)

# Rows are processed two at a time so a parallel let can compute them at
# once. The two rows have identical shape and cost, so they finish together
# and the join does not stall. The recursion inside the parallel let is on
# after_second, a strict subterm of remaining_rows, so the termination
# checker accepts it without an @unsafe marker.
def mandelbrot_render_lines_remaining(
  remaining_rows: Nat,
  +start_row: Nat,
  +half_width: Nat,
  +width: Nat,
  +height: Nat,
  +max_iterations: Nat
) -> List<&2, String>:
  match remaining_rows:
    case 0n:
      Nil{}
    case 1n+after_first:
      match after_first:
        case 0n:
          mandelbrot_render_row(
            start_row, half_width, width, height, max_iterations
          ) <> Nil{}
        case 1n+after_second:
          first_line second_line = mandelbrot_render_row(
            start_row, half_width, width, height, max_iterations
          ) mandelbrot_render_row(
            1n+start_row, half_width, width, height, max_iterations
          )
          first_line <> second_line
            <> mandelbrot_render_lines_remaining(
              after_second,
              2n+start_row,
              half_width,
              width,
              height,
              max_iterations
            )

def mandelbrot_render_lines(
  +height: Nat,
  width: Nat,
  half_width: Nat,
  max_iterations: Nat
) -> List<&2, String>:
  mandelbrot_render_lines_remaining(
    height, 0n, half_width, width, height, max_iterations
  )

# --- Sierpinski ---

def sierpinski_pick_character(in_set: Bool) -> Char:
  match in_set:
    case True{}:
      '*'
    case False{}:
      ' '

# The classic Sierpinski triangle is Pascal's triangle mod 2: cell
# (column, row) is filled exactly when column is a bitwise submask of row.
# That is one AND and one EQ per cell, which is why this picture does not
# need a parallel let. column_index is + because it is read twice: once in
# U32.and and once as the right side of U32.is_eq.
def sierpinski_character_at(+column_index: Nat, actual_row: Nat) -> Char:
  sierpinski_pick_character(
    U32.is_eq(
      U32.and(U32.from_nat(column_index), U32.from_nat(actual_row)),
      U32.from_nat(column_index)
    )
  )

# remaining_columns is first for the same reason as in
# mandelbrot_render_row_segment: the self-call must pass a shrinking argument
# as its first argument, and current_column grows by one each step.
def sierpinski_render_row_segment(
  remaining_columns: Nat,
  +current_column: Nat,
  +actual_row: Nat
) -> String:
  match remaining_columns:
    case 0n:
      SNil{}
    case 1n+rest:
      SCon{
        sierpinski_character_at(current_column, actual_row),
        sierpinski_render_row_segment(rest, 1n+current_column, actual_row)
      }

def sierpinski_render_row(actual_row: Nat, width: Nat) -> String:
  sierpinski_render_row_segment(width, 0n, actual_row)

# Rows are drawn from the widest (height - 1) down to the narrowest (0), so
# the triangle sits point-up on the terminal. Nat.sub clamps at zero, which
# is why no guard is needed on the last step.
def sierpinski_render_lines_remaining(
  remaining_rows: Nat,
  +current_actual_row: Nat,
  +width: Nat
) -> List<&2, String>:
  match remaining_rows:
    case 0n:
      Nil{}
    case 1n+rest:
      sierpinski_render_row(current_actual_row, width)
        <> sierpinski_render_lines_remaining(
          rest, Nat.sub(current_actual_row, 1n), width
        )

def sierpinski_render_lines(+height: Nat, width: Nat) -> List<&2, String>:
  sierpinski_render_lines_remaining(height, Nat.sub(height, 1n), width)

# --- Main ---

def main() -> IO(Unit):
  do IO<Unit>:
    print_lines(mandelbrot_render_lines(32n, 64n, 32n, 50n))
    IO.print("")
    print_lines(sierpinski_render_lines(16n, 32n))
