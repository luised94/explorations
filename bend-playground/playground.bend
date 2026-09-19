import Base

# ============================================================
#   BEND PARALLEL PLAYGROUND  (Bend 2, CPU)
#
#   Renders an ASCII Mandelbrot set and an ASCII Sierpinski
#   triangle, both split by halving so that the two sides of
#   every parallel call carry the same amount of work.
# ============================================================

# ---------- Configuration ----------

# Both renderers divide their extent in half at each step, so every extent is
# a power of two and is declared as its exponent. The U32 counts below must
# stay equal to two raised to the matching depth; nothing in the language
# checks that for us, so they are kept adjacent to make a mismatch visible.

def mandelbrot_width_depth() -> Nat:
  6n

def mandelbrot_width_columns() -> U32:
  64

def mandelbrot_height_depth() -> Nat:
  5n

def mandelbrot_height_rows() -> U32:
  32

# The Sierpinski cell test is "column AND row equals column", which can only
# hold when every bit of the column index is also set in the row index. A
# grid wider than it is tall therefore has a permanently blank right side, so
# the triangle is kept square.
def sierpinski_width_depth() -> Nat:
  5n

def sierpinski_height_depth() -> Nat:
  5n

def max_iterations() -> Nat:
  60n

# Bend has no unary minus, so a negative literal is a subtraction from zero.
def plane_minimum_real_part() -> F32:
  F32.sub(0.0, 2.0)

def plane_maximum_real_part() -> F32:
  0.5

def plane_minimum_imaginary_part() -> F32:
  F32.sub(0.0, 1.25)

def plane_maximum_imaginary_part() -> F32:
  1.25

# Squared, so the escape test never needs a square root.
def escape_threshold_squared() -> F32:
  4.0

# ---------- Palette ----------

def palette(iteration_count: Nat) -> String:
  match iteration_count:
    case 0n: " "
    case 1n: "."
    case 2n: ","
    case 3n: ":"
    case 4n: ";"
    case 5n: "!"
    case 6n: "|"
    case 7n: "*"
    case 8n: "#"
    case 9n: "%"
    case _:  "@"

# ---------- Complex plane mapping ----------

# Every arithmetic step is its own annotated group bound to a name. The guide
# does not specify operator precedence, so a single chained expression like
# "a + b - a * c / w" would be resting on an assumption that is not written
# down anywhere.

def mandelbrot_real_part_for_column(column_index: U32) -> F32:
  column_count_as_float = U32.to_f32(mandelbrot_width_columns())
  column_index_as_float = U32.to_f32(column_index)
  column_fraction = (column_index_as_float / column_count_as_float : F32)
  real_part_span = (plane_maximum_real_part() - plane_minimum_real_part() : F32)
  real_part_offset = (real_part_span * column_fraction : F32)
  (plane_minimum_real_part() + real_part_offset : F32)

def mandelbrot_imaginary_part_for_row(row_index: U32) -> F32:
  row_count_as_float = U32.to_f32(mandelbrot_height_rows())
  row_index_as_float = U32.to_f32(row_index)
  row_fraction = (row_index_as_float / row_count_as_float : F32)
  imaginary_part_span = (plane_maximum_imaginary_part() - plane_minimum_imaginary_part() : F32)
  imaginary_part_offset = (imaginary_part_span * row_fraction : F32)
  (plane_minimum_imaginary_part() + imaginary_part_offset : F32)

# ---------- Mandelbrot orbit ----------

# Two language rules shape this loop. Mutual recursion is forbidden, so the
# escape decision cannot be delegated to a helper that calls back. And a
# match inspects a parameter, never a computed value, so the result of the
# escape test cannot be matched where it is calculated. Both are satisfied by
# testing the state that is about to be handed over and passing the answer as
# a parameter of the next call, where match can reach it.
#
# remaining_fuel is the first parameter because the termination checker reads
# a recursive call's arguments left to right and needs the shrinking one
# before any other; everything after it is then unconstrained.
def mandelbrot_orbit_step(remaining_fuel: Nat, has_escaped: Bool,
                          iteration_count: Nat,
                          +orbit_real_part: F32,
                          +orbit_imaginary_part: F32,
                          +constant_real_part: F32,
                          +constant_imaginary_part: F32) -> Nat:
  match remaining_fuel has_escaped:
    case 0n True{}:
      iteration_count
    case 0n False{}:
      iteration_count
    case 1n+fuel_after_this_step True{}:
      iteration_count
    case 1n+fuel_after_this_step False{}:
      real_part_squared = (orbit_real_part * orbit_real_part : F32)
      imaginary_part_squared = (orbit_imaginary_part * orbit_imaginary_part : F32)
      squared_difference = (real_part_squared - imaginary_part_squared : F32)
      +next_orbit_real_part = (squared_difference + constant_real_part : F32)
      cross_term = (orbit_real_part * orbit_imaginary_part : F32)
      doubled_cross_term = (2.0 * cross_term : F32)
      +next_orbit_imaginary_part = (doubled_cross_term + constant_imaginary_part : F32)
      next_real_part_squared = (next_orbit_real_part * next_orbit_real_part : F32)
      next_imaginary_part_squared = (next_orbit_imaginary_part * next_orbit_imaginary_part : F32)
      next_magnitude_squared = (next_real_part_squared + next_imaginary_part_squared : F32)
      next_has_escaped = F32.is_gt(next_magnitude_squared, escape_threshold_squared())
      mandelbrot_orbit_step(fuel_after_this_step, next_has_escaped,
                            Nat.add(iteration_count, 1n),
                            next_orbit_real_part, next_orbit_imaginary_part,
                            constant_real_part, constant_imaginary_part)

# The starting point is not always the origin: LAWS.bend hands this function
# an orbit that is already outside the escape radius and expects a count of
# zero back. So the first escape test belongs here, before the loop, rather
# than being assumed false by the pixel renderer.
def mandelbrot_orbit(fuel: Nat, iteration_count: Nat,
                     +orbit_real_part: F32, +orbit_imaginary_part: F32,
                     constant_real_part: F32, constant_imaginary_part: F32) -> Nat:
  initial_real_part_squared = (orbit_real_part * orbit_real_part : F32)
  initial_imaginary_part_squared = (orbit_imaginary_part * orbit_imaginary_part : F32)
  initial_magnitude_squared = (initial_real_part_squared + initial_imaginary_part_squared : F32)
  initial_has_escaped = F32.is_gt(initial_magnitude_squared, escape_threshold_squared())
  mandelbrot_orbit_step(fuel, initial_has_escaped, iteration_count,
                        orbit_real_part, orbit_imaginary_part,
                        constant_real_part, constant_imaginary_part)

def mandelbrot_pixel(column_index: U32, row_index: U32) -> String:
  surviving_iterations = mandelbrot_orbit(max_iterations(), 0n, 0.0, 0.0,
                                          mandelbrot_real_part_for_column(column_index),
                                          mandelbrot_imaginary_part_for_row(row_index))
  palette(surviving_iterations)

# ---------- Mandelbrot rendering ----------

# The span is halved rather than peeled one cell at a time. Peeling forks one
# pixel against the whole remainder of the row, and the scheduler hands a task
# to a core once and never moves it, so the short side finishes immediately
# and its core sits idle. Halving keeps both sides the same size.
def render_mandelbrot_row_segment(+column_depth: Nat, +row_index: U32,
                                  +first_column_index: U32) -> String:
  match column_depth:
    case 0n:
      mandelbrot_pixel(first_column_index, row_index)
    case 1n+smaller_column_depth:
      half_column_span = (1 << smaller_column_depth : U32)
      second_half_first_column_index = U32.add(first_column_index, half_column_span)
      left_half right_half = render_mandelbrot_row_segment(smaller_column_depth, row_index, first_column_index)
                             render_mandelbrot_row_segment(smaller_column_depth, row_index, second_half_first_column_index)
      left_half ++ right_half

def render_mandelbrot_rows(+row_depth: Nat, +first_row_index: U32) -> String:
  match row_depth:
    case 0n:
      row_text = render_mandelbrot_row_segment(mandelbrot_width_depth(), first_row_index, 0)
      row_text ++ "\n"
    case 1n+smaller_row_depth:
      half_row_span = (1 << smaller_row_depth : U32)
      second_half_first_row_index = U32.add(first_row_index, half_row_span)
      top_half bottom_half = render_mandelbrot_rows(smaller_row_depth, first_row_index)
                             render_mandelbrot_rows(smaller_row_depth, second_half_first_row_index)
      top_half ++ bottom_half

# ---------- Sierpinski ----------

# A match cannot inspect a computed value, so the result of the membership
# test has to travel through a parameter to be matched on. That is the only
# reason this is a separate definition.
def sierpinski_glyph(is_filled: Bool) -> String:
  match is_filled:
    case True{}:  "*"
    case False{}: " "

# column_index is read twice, once by the bitwise and and once by the
# comparison, so it must be marked reusable.
def sierpinski_cell(+column_index: U32, row_index: U32) -> String:
  sierpinski_glyph(U32.is_eq(U32.and(column_index, row_index), column_index))

def render_sierpinski_row_segment(+column_depth: Nat, +row_index: U32,
                                  +first_column_index: U32) -> String:
  match column_depth:
    case 0n:
      sierpinski_cell(first_column_index, row_index)
    case 1n+smaller_column_depth:
      half_column_span = (1 << smaller_column_depth : U32)
      second_half_first_column_index = U32.add(first_column_index, half_column_span)
      left_half right_half = render_sierpinski_row_segment(smaller_column_depth, row_index, first_column_index)
                             render_sierpinski_row_segment(smaller_column_depth, row_index, second_half_first_column_index)
      left_half ++ right_half

def render_sierpinski_rows(+row_depth: Nat, +first_row_index: U32) -> String:
  match row_depth:
    case 0n:
      row_text = render_sierpinski_row_segment(sierpinski_width_depth(), first_row_index, 0)
      row_text ++ "\n"
    case 1n+smaller_row_depth:
      half_row_span = (1 << smaller_row_depth : U32)
      second_half_first_row_index = U32.add(first_row_index, half_row_span)
      top_half bottom_half = render_sierpinski_rows(smaller_row_depth, first_row_index)
                             render_sierpinski_rows(smaller_row_depth, second_half_first_row_index)
      top_half ++ bottom_half

# ---------- Main ----------

def header() -> String:
  "============================================================\n"
  ++ "  BEND PARALLEL PLAYGROUND  (Bend 2, CPU)\n"
  ++ "============================================================\n\n"
  ++ "--- 1. Mandelbrot Set ---\n"

def separator() -> String:
  "\n--- 2. Sierpinski Triangle ---\n"

def footer() -> String:
  "\n--- Done. Rows and columns split in half at every fork. ---\n"

def render_everything() -> String:
  header()
  ++ render_mandelbrot_rows(mandelbrot_height_depth(), 0)
  ++ separator()
  ++ render_sierpinski_rows(sierpinski_height_depth(), 0)
  ++ footer()

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(render_everything())
