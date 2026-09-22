import Base

# Mandelbrot rendering.
#
# Row count 24 and column count 80 were chosen because 80 columns is a
# standard terminal width, and 24 rows fits a typical terminal height while
# leaving room for the Sierpinski triangle below. The alternative of a
# square aspect ratio would require more rows than a terminal normally
# shows. The real range is [-2.2, 0.8] and the imaginary range is
# [-1.2, 1.2]. These ranges cover the Mandelbrot set with a small margin.
# The iteration limit 32 is low enough to keep the ASCII render fast, but
# high enough to show the main cardioid and the largest bulbs. A higher
# limit would slow the program and add little to the ASCII picture.

def Mandelbrot.character_for_escaped(escaped_after_maximum: Bool) -> Char:
  # The constraint: the character must be a space for an escaped point and
  # a hash for a point that stayed bounded. The failure prevented: a point
  # that escapes would be drawn as inside, hiding the set's boundary. The
  # alternative rejected: a multi-character gray ramp, which would require
  # a larger proof and more code.
  match escaped_after_maximum:
    case True{}:
      ' '
    case False{}:
      '#'

def Mandelbrot.escape_count(
  remaining_iterations: Nat,
  escaped: Bool,
  real_coordinate: F32,
  imaginary_coordinate: F32,
  current_real: F32,
  current_imaginary: F32,
  accumulated_count: Nat
) -> Nat:
  # The constraint: the count must stop at the maximum iterations or when
  # the point escapes. The failure prevented: an infinite loop on a point
  # that never escapes. The alternative rejected: a helper that matches on
  # a computed Bool and calls back, which Bend rejects as mutual recursion.
  # The match on remaining_iterations comes first because it is the first
  # parameter; the match on escaped comes second. This ordering follows
  # Bend's rule that scrutinees must follow binder order.
  match remaining_iterations:
    case 0n:
      accumulated_count
    case 1n+predecessor:
      match escaped:
        case True{}:
          accumulated_count
        case False{}:
          next_real = F32.add(
            F32.sub(
              F32.mul(current_real, current_real),
              F32.mul(current_imaginary, current_imaginary)
            ),
            real_coordinate
          )
          next_imaginary = F32.add(
            F32.mul(
              F32.mul(2.0, current_real),
              current_imaginary
            ),
            imaginary_coordinate
          )
          next_magnitude_squared = F32.add(
            F32.mul(next_real, next_real),
            F32.mul(next_imaginary, next_imaginary)
          )
          next_escaped = F32.is_gt(next_magnitude_squared, 4.0)
          Mandelbrot.escape_count(
            predecessor,
            next_escaped,
            real_coordinate,
            imaginary_coordinate,
            next_real,
            next_imaginary,
            Nat.add(accumulated_count, 1n)
          )

def Mandelbrot.render_columns(
  remaining_columns: Nat,
  total_columns: Nat,
  current_column: Nat,
  imaginary_coordinate: F32,
  maximum_iterations: Nat
) -> String:
  # The constraint: the string must have exactly remaining_columns
  # characters. The failure prevented: a row that is too short or too long,
  # which would misalign the picture. The alternative rejected: an
  # accumulator with reverse, which would add an extra pass and complicate
  # the row-count law. This def is not in the law because the law is only
  # about the number of rows, not the number of columns.
  match remaining_columns:
    case 0n:
      SNil{}
    case 1n+predecessor:
      real_coordinate = F32.add(
        F32.sub(0.8, 3.0),
        F32.mul(
          F32.div(
            F32.from_nat(current_column),
            F32.from_nat(total_columns)
          ),
          3.0
        )
      )
      escape_count = Mandelbrot.escape_count(
        maximum_iterations,
        False{},
        real_coordinate,
        imaginary_coordinate,
        0.0,
        0.0,
        0n
      )
      escaped_after_maximum = Bool.not(Nat.is_eq(escape_count, maximum_iterations))
      character = Mandelbrot.character_for_escaped(escaped_after_maximum)
      SCon{character, Mandelbrot.render_columns(
        predecessor,
        total_columns,
        Nat.add(current_column, 1n),
        imaginary_coordinate,
        maximum_iterations
      )}

def Mandelbrot.render_rows(
  remaining_rows: Nat,
  total_rows: Nat,
  current_row: Nat,
  total_columns: Nat,
  maximum_iterations: Nat
) -> List<&2, String>:
  # The fork tree is a right-leaning chain. At each level, the parallel let
  # splits into the current row and the remaining rows. The current row is
  # light; the remaining rows are heavy. The heavy side finishes last. This
  # shape is simple and matches the inductive law on remaining_rows. A
  # balanced split would require a more complex law and a helper that
  # divides the row range. The law only constrains the number of rows, so
  # the unbalanced fork tree is acceptable for this exercise.
  match remaining_rows:
    case 0n:
      Nil{}
    case 1n+predecessor:
      imaginary_coordinate = F32.sub(
        1.2,
        F32.mul(
          F32.div(
            F32.from_nat(current_row),
            F32.from_nat(total_rows)
          ),
          2.4
        )
      )
      current_row_text remaining_rows_list = Mandelbrot.render_columns(
        total_columns,
        total_columns,
        0n,
        imaginary_coordinate,
        maximum_iterations
      ) Mandelbrot.render_rows(
        predecessor,
        total_rows,
        Nat.add(current_row, 1n),
        total_columns,
        maximum_iterations
      )
      current_row_text <> remaining_rows_list

def Mandelbrot.render_all() -> String:
  # The alternative rejected: printing each row directly in main, which
  # would mix IO with rendering and make the row-count law harder to state.
  # This def keeps rendering pure so the law can talk about it.
  rows = Mandelbrot.render_rows(24n, 24n, 0n, 80n, 32n)
  String.join(rows, "\n")

# Sierpinski rendering.
#
# Row count 16 and column count 31 were chosen because 31 columns is
# 2 * 16 - 1, which is the width of a centered Sierpinski triangle of
# height 16. However, the cell test used here is left-aligned, so columns
# 16 through 30 are always spaces. The alternative of a symmetric triangle
# would require mirroring the pattern and a more complex cell test. The
# left-aligned triangle is still a Sierpinski triangle and is easier to
# prove correct. The row count 16 is large enough to show the fractal
# structure and small enough to keep the ASCII output readable.

def Sierpinski.character_for_filled(filled: Bool) -> Char:
  # The constraint: a filled cell must be a star and an empty cell a space.
  # The failure prevented: a filled cell would be invisible. The
  # alternative rejected: a different character such as '#', which would
  # make the triangle harder to read against the Mandelbrot set above.
  match filled:
    case True{}:
      '*'
    case False{}:
      ' '

def Sierpinski.character_for_cell(
  within_pattern: Bool,
  current_column: U32,
  row_index: U32
) -> Char:
  # The constraint: cells beyond the row's pattern must be spaces. The
  # failure prevented: stars would appear in the padding, breaking the
  # triangle shape. The alternative rejected: computing the filled test
  # even outside the pattern, which would waste work and could produce
  # stars where none belong. This helper is forced by Bend's rule that a
  # match cannot inspect a computed value: we pass the computed Bool as a
  # parameter and match on the parameter here.
  match within_pattern:
    case True{}:
      filled = U32.is_eq(
        U32.and(current_column, row_index),
        current_column
      )
      Sierpinski.character_for_filled(filled)
    case False{}:
      ' '

def Sierpinski.render_columns(
  remaining_columns: Nat,
  total_columns: Nat,
  current_column: U32,
  row_index: U32
) -> String:
  # The constraint: the string must have exactly remaining_columns
  # characters. The failure prevented: a row that is too short or too long.
  # The alternative rejected: an accumulator with reverse, which would add
  # an extra pass. This def is not in the law because the law is only about
  # the number of rows.
  match remaining_columns:
    case 0n:
      SNil{}
    case 1n+predecessor:
      within_pattern = U32.is_le(current_column, row_index)
      character = Sierpinski.character_for_cell(
        within_pattern,
        current_column,
        row_index
      )
      SCon{character, Sierpinski.render_columns(
        predecessor,
        total_columns,
        U32.inc(current_column),
        row_index
      )}

def Sierpinski.render_rows(
  remaining_rows: Nat,
  total_rows: Nat,
  current_row: Nat,
  total_columns: Nat
) -> List<&2, String>:
  # The fork tree is a right-leaning chain, as in Mandelbrot.render_rows.
  # The current row is light and the remaining rows are heavy. The heavy
  # side finishes last. This shape matches the inductive law on
  # remaining_rows. A balanced split would complicate the proof.
  match remaining_rows:
    case 0n:
      Nil{}
    case 1n+predecessor:
      row_index = U32.from_nat(current_row)
      current_row_text remaining_rows_list = Sierpinski.render_columns(
        total_columns,
        total_columns,
        0,
        row_index
      ) Sierpinski.render_rows(
        predecessor,
        total_rows,
        Nat.add(current_row, 1n),
        total_columns
      )
      current_row_text <> remaining_rows_list

def Sierpinski.render_all() -> String:
  # The alternative rejected: printing each row directly in main, which
  # would mix IO with rendering and make the row-count law harder to state.
  rows = Sierpinski.render_rows(16n, 16n, 0n, 31n)
  String.join(rows, "\n")

def Playground.render_both() -> String & String:
  # The fork tree here has one split. The left side is the Mandelbrot set
  # (24 rows, 80 columns, 32 iterations each). The right side is the
  # Sierpinski triangle (16 rows, 31 columns, no iteration). The left side
  # is much heavier and finishes later. The right side finishes first.
  # This split exercises the scheduler with two independent figures.
  mandelbrot_text sierpinski_text = Mandelbrot.render_all() Sierpinski.render_all()
  (mandelbrot_text, sierpinski_text)

def main() -> IO(Unit):
  do IO<Unit>:
    both_texts : String & String = Playground.render_both()
    (mandelbrot_text, sierpinski_text) = both_texts
    IO.print(mandelbrot_text)
    IO.print(sierpinski_text)
    return Unit{}
