# playground.bend
# Draws an ASCII Mandelbrot set, then an ASCII Sierpinski triangle.
#
# Parallelism: the fork tree comes from Mandelbrot.lines_remaining. Each
# level of that recursion splits one remaining-rows job into two: the next
# two rows are computed by a parallel let, and the recursion over the rest
# of the rows is the tail of the same job. The tree is a chain of binary
# forks, one per two rows. Row work is uniform (same width, same budget per
# pixel), so the two sides of each fork finish together and the scheduler
# does not stall on a slow branch. Sierpinski is left sequential: its rows
# are one bitwise test per cell, so fork overhead would dominate the work.

import Base

# --- Shared helpers ---

# Recursion on count gives a chain of cons cells; the checker sees count
# shrink at each call, so the helper passes termination without a fuel
# argument. The alternative, building the string with String.append, would
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

# The Mandelbrot set lives in real [-2.0, 0.5], imaginary [-1.25, 1.25];
# those bounds are chosen so the picture fits the terminal without cropping.
# The map is linear, so one multiply and one add per axis is enough.
def Mandelbrot.real_coordinate(column_index: Nat, width: Nat) -> F32:
  F32.add(
    -2.0,
    F32.mul(2.5, F32.div(F32.from_nat(column_index), F32.from_nat(width)))
  )

def Mandelbrot.imaginary_coordinate(row_index: Nat, height: Nat) -> F32:
  F32.sub(
    1.25,
    F32.mul(2.5, F32.div(F32.from_nat(row_index), F32.from_nat(height)))
  )

# The escape decision is a pure function of the final iteration count, so it
# is split out. The alternative, inlining the comparison in the row builder,
# would force a match on a computed value, which Bend rejects.
def Mandelbrot.pick_character(in_set: Bool) -> Char:
  match in_set:
    case True{}:
      '*'
    case False{}:
      ' '

# The escape test is carried as a Boolean parameter rather than produced by
# a match on a computed value. Bend rejects "match F32.is_gt(...)", and the
# natural workaround, a helper that recurses back into this def, is mutual
# recursion, which the termination checker also rejects. Passing the bit
# forward keeps one def calling itself, which is allowed.
def Mandelbrot.escape_iterations(
  remaining_iterations: Nat,
  +real_part: F32,
  +imaginary_part: F32,
  +real_constant: F32,
  +imaginary_constant: F32,
  point_has_escaped: Bool
) -> Nat:
  match point_has_escaped:
    case True{}:
      0n
    case False{}:
      match remaining_iterations:
        case 0n:
          0n
        case 1n+rest:
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
          1n+Mandelbrot.escape_iterations(
            rest,
            new_real_part,
            new_imaginary_part,
            real_constant,
            imaginary_constant,
            F32.is_gt(new_magnitude_squared, 4.0)
          )

def Mandelbrot.character_at(
  column_index: Nat,
  row_index: Nat,
  width: Nat,
  height: Nat,
  max_iterations: Nat
) -> Char:
  +real_coordinate = Mandelbrot.real_coordinate(column_index, width)
  +imaginary_coordinate = Mandelbrot.imaginary_coordinate(row_index, height)
  +iteration_count = Mandelbrot.escape_iterations(
    max_iterations,
    0.0,
    0.0,
    real_coordinate,
    imaginary_coordinate,
    False{}
  )
  Mandelbrot.pick_character(Nat.is_eq(iteration_count, max_iterations))

# row_segment carries an explicit starting column because the two parallel
# halves of a row cannot see each other's state. Without that parameter the
# right half would need to know how many characters the left half produced,
# which would serialise the two halves.
def Mandelbrot.row_segment(
  start_column: Nat,
  column_count: Nat,
  row_index: Nat,
  width: Nat,
  height: Nat,
  max_iterations: Nat
) -> String:
  match column_count:
    case 0n:
      SNil{}
    case 1n+rest:
      SCon{
        Mandelbrot.character_at(
          start_column,
          row_index,
          width,
          height,
          max_iterations
        ),
        Mandelbrot.row_segment(
          1n+start_column,
          rest,
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
def Mandelbrot.row(
  row_index: Nat,
  half_width: Nat,
  width: Nat,
  height: Nat,
  max_iterations: Nat
) -> String:
  left_half right_half = Mandelbrot.row_segment(
    0n, half_width, row_index, width, height, max_iterations
  ) Mandelbrot.row_segment(
    half_width, half_width, row_index, width, height, max_iterations
  )
  String.append(left_half, right_half)

# Rows are processed two at a time so a parallel let can compute them at
# once. The two rows have identical shape and cost, so they finish together
# and the join does not stall. The recursion inside the parallel let is on
# after_second, a strict subterm of remaining_rows, so the termination
# checker accepts it without an @unsafe marker.
def Mandelbrot.lines_remaining(
  remaining_rows: Nat,
  start_row: Nat,
  half_width: Nat,
  width: Nat,
  height: Nat,
  max_iterations: Nat
) -> List<&2, String>:
  match remaining_rows:
    case 0n:
      Nil{}
    case 1n+after_first:
      match after_first:
        case 0n:
          Mandelbrot.row(start_row, half_width, width, height, max_iterations)
            <> Nil{}
        case 1n+after_second:
          first_line second_line = Mandelbrot.row(
            start_row, half_width, width, height, max_iterations
          ) Mandelbrot.row(
            1n+start_row, half_width, width, height, max_iterations
          )
          first_line <> second_line
            <> Mandelbrot.lines_remaining(
              after_second,
              2n+start_row,
              half_width,
              width,
              height,
              max_iterations
            )

def Mandelbrot.lines(
  height: Nat,
  width: Nat,
  half_width: Nat,
  max_iterations: Nat
) -> List<&2, String>:
  Mandelbrot.lines_remaining(
    height, 0n, half_width, width, height, max_iterations
  )

# --- Sierpinski ---

def Sierpinski.pick_character(in_set: Bool) -> Char:
  match in_set:
    case True{}:
      '*'
    case False{}:
      ' '

# The classic Sierpinski triangle is Pascal's triangle mod 2: cell
# (column, row) is filled exactly when column is a bitwise submask of row.
# That is one AND and one EQ per cell, which is why this picture does not
# need a parallel let.
def Sierpinski.character(column_index: Nat, actual_row: Nat) -> Char:
  Sierpinski.pick_character(
    U32.is_eq(
      U32.and(U32.from_nat(column_index), U32.from_nat(actual_row)),
      U32.from_nat(column_index)
    )
  )

def Sierpinski.row_segment(
  current_column: Nat,
  remaining_columns: Nat,
  actual_row: Nat
) -> String:
  match remaining_columns:
    case 0n:
      SNil{}
    case 1n+rest:
      SCon{
        Sierpinski.character(current_column, actual_row),
        Sierpinski.row_segment(1n+current_column, rest, actual_row)
      }

def Sierpinski.row(actual_row: Nat, width: Nat) -> String:
  Sierpinski.row_segment(0n, width, actual_row)

# Rows are drawn from the widest (height - 1) down to the narrowest (0), so
# the triangle sits point-up on the terminal. Nat.sub clamps at zero, which
# is why no guard is needed on the last step.
def Sierpinski.lines_remaining(
  remaining_rows: Nat,
  current_actual_row: Nat,
  width: Nat
) -> List<&2, String>:
  match remaining_rows:
    case 0n:
      Nil{}
    case 1n+rest:
      Sierpinski.row(current_actual_row, width)
        <> Sierpinski.lines_remaining(
          rest, Nat.sub(current_actual_row, 1n), width
        )

def Sierpinski.lines(height: Nat, width: Nat) -> List<&2, String>:
  Sierpinski.lines_remaining(height, Nat.sub(height, 1n), width)

# --- Main ---

def main() -> IO(Unit):
  do IO<Unit>:
    print_lines(Mandelbrot.lines(32n, 64n, 32n, 50n))
    IO.print("")
    print_lines(Sierpinski.lines(16n, 32n))
