import Base

# ---------------------------------------------------------------------------
# FORK TREE SHAPE AND PARALLELISM
#
# Both renderers use a balanced binary fork tree over rows.  At depth d the
# row range splits via a parallel let into two sub-trees of depth d-1,
# yielding 2^d leaves.  Each leaf renders one row as a flat tail-recursive
# loop over columns (a Nat fuel counts down).  This is the shader guide's
# recommended shape: "one fork tree that ends in flat loops."  The tree is
# balanced so every fork level has equal work per branch and no lane finishes
# early.  Mandelbrot uses depth 5 (32 rows, 60 cols); Sierpinski uses depth 4
# (16 rows, 32 cols).  The two images are themselves computed in a top-level
# parallel let, so the root forks into two independent sub-trees.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Sierpinski triangle
# ---------------------------------------------------------------------------

# Lucas' theorem: C(row, col) is odd iff col is a submask of row, i.e.
# (col AND row) == col.  Chosen over recursive geometric subdivision because
# U32 bitwise AND is structurally defined in Base (Word.and recurses on the
# Nat length index), making this predicate provable by induction on Word.
# Recursive subdivision would require Nat subtraction proofs that add
# complexity without insight.
def sierpinski_is_filled(row: U32, +col: U32) -> Bool:
  U32.is_eq((col .&. row : U32), col)

# Character for one Sierpinski cell.  '*' (code 42) when filled,
# ' ' (code 32) when empty.  Flat: one match on the parameter, no helper
# needed because the Bool arrives as a parameter, not a computed value.
def sierpinski_character_for_cell(filled: Bool) -> Char:
  match filled:
  case True{}:
    Chr{42}
  case False{}:
    Chr{32}

# Render one Sierpinski row terminated by a newline.
# Parameter order is forced by the termination checker: it reads arguments
# left to right and requires each to be unchanged until one shrinks.
# columns_remaining (Nat) must precede col (U32) because col is incremented
# in the recursive call; if col came first the checker would see a non-
# shrinking, non-unchanged argument before reaching the Nat.
def sierpinski_render_row_go(+row: U32, columns_remaining: Nat, +col: U32) -> String:
  match columns_remaining:
  case 0n:
    SCon{Chr{10}, SNil{}}
  case 1n+rest:
    SCon{sierpinski_character_for_cell(sierpinski_is_filled(row, col)),
         sierpinski_render_row_go(row, rest, (col + 1 : U32))}

# Entry point: render one row of the given column count.
def sierpinski_render_row(row: U32, column_count: Nat) -> String:
  sierpinski_render_row_go(row, column_count, 0)

# Balanced binary fork tree over rows.  depth comes first because the
# termination checker requires the shrinking argument before any argument
# that changes (first_row is offset in the lower branch).
def sierpinski_render_rows(+depth: Nat, +first_row: U32, +column_count: Nat) -> String:
  match depth:
  case 0n:
    sierpinski_render_row(first_row, column_count)
  case 1n+remaining_depth:
    upper_rows lower_rows = sierpinski_render_rows(remaining_depth, first_row, column_count)
                            sierpinski_render_rows(remaining_depth, (first_row + U32.pow(2, remaining_depth) : U32), column_count)
    upper_rows ++ lower_rows

# ---------------------------------------------------------------------------
# Mandelbrot set
# ---------------------------------------------------------------------------

# Map a column index to the real-axis coordinate in [-2.0, 1.0).
# F32 arithmetic is used because the Mandelbrot iteration requires real
# numbers; Nat or U32 fixed-point would introduce rounding that shifts the
# set boundary.  All F32 ops are opaque laws in Base, so no algebraic
# property of this mapping is provable.
def mandelbrot_pixel_to_real(col: U32, image_width: U32) -> F32:
  F32.add(F32.neg(2.0), F32.mul(3.0, F32.div(U32.to_f32(col), U32.to_f32(image_width))))

# Map a row index to the imaginary-axis coordinate in [-1.5, 1.5).
def mandelbrot_pixel_to_imag(row: U32, image_height: U32) -> F32:
  F32.add(F32.neg(1.5), F32.mul(3.0, F32.div(U32.to_f32(row), U32.to_f32(image_height))))

# One Mandelbrot iteration loop.  The escaped Bool is a PARAMETER, not a
# computed value matched inline: this satisfies the rule that match inspects
# only parameters.  The next escaped value is computed at the recursive call
# site and passed as an argument, which is legal.  This structure avoids
# mutual recursion (a helper that calls back into this def), which the guide
# forbids.  fuel (Nat) is the structurally decreasing witness and must
# precede any argument that changes.
def mandelbrot_escape_go(+point_real: F32, +point_imag: F32, fuel: Nat,
                         +current_real: F32, +current_imag: F32,
                         iteration_count: U32, escaped: Bool) -> U32:
  match escaped fuel:
  case True{} _:
    iteration_count
  case False{} 0n:
    iteration_count
  case False{} 1n+remaining_fuel:
    +real_squared = F32.mul(current_real, current_real)
    +imag_squared = F32.mul(current_imag, current_imag)
    next_real = F32.add(F32.sub(real_squared, imag_squared), point_real)
    next_imag = F32.add(F32.mul(F32.mul(2.0, current_real), current_imag), point_imag)
    mandelbrot_escape_go(point_real, point_imag, remaining_fuel, next_real, next_imag,
                         (iteration_count + 1 : U32),
                         F32.is_gt(F32.add(real_squared, imag_squared), 4.0))

# Entry point for the escape iteration at a given complex coordinate.
# Initial z = 0, so |z|^2 = 0 which is not > 4: escaped starts False{}.
def mandelbrot_escape_depth(point_real: F32, point_imag: F32, max_iterations: Nat) -> U32:
  mandelbrot_escape_go(point_real, point_imag, max_iterations, 0.0, 0.0, 0, False{})

# Character selection: space (32) for points in the set, '#' (35) for
# escaped points.  Flat match on the parameter.
def mandelbrot_branch_on_membership(in_set: Bool) -> Char:
  match in_set:
  case True{}:
    Chr{32}
  case False{}:
    Chr{35}

# Determine the character for a given escape depth.  The helper below is
# forced by the match-on-computed-value rule: U32.is_eq(depth, max_depth)
# is computed, so the resulting Bool must arrive as a parameter to the
# function that matches on it.
def mandelbrot_character_for_depth(depth: U32, max_depth: U32) -> Char:
  mandelbrot_branch_on_membership(U32.is_eq(depth, max_depth))

# Render one Mandelbrot row terminated by a newline.  columns_remaining
# precedes col for the same termination-checker reason as in the Sierpinski
# row renderer.
def mandelbrot_render_row_go(+row: U32, columns_remaining: Nat, +col: U32,
                             +image_width: U32, +image_height: U32,
                             +max_iterations: Nat) -> String:
  match columns_remaining:
  case 0n:
    SCon{Chr{10}, SNil{}}
  case 1n+rest:
    SCon{mandelbrot_character_for_depth(
           mandelbrot_escape_depth(
             mandelbrot_pixel_to_real(col, image_width),
             mandelbrot_pixel_to_imag(row, image_height),
             max_iterations),
           U32.from_nat(max_iterations)),
         mandelbrot_render_row_go(row, rest, (col + 1 : U32),
                                  image_width, image_height, max_iterations)}

# Entry point: render one Mandelbrot row.
def mandelbrot_render_row(row: U32, column_count: Nat,
                          image_width: U32, image_height: U32,
                          max_iterations: Nat) -> String:
  mandelbrot_render_row_go(row, column_count, 0, image_width, image_height,
                           max_iterations)

# Balanced binary fork tree over Mandelbrot rows.  depth first for the
# termination checker, same reasoning as sierpinski_render_rows.
def mandelbrot_render_rows(+depth: Nat, +first_row: U32, +column_count: Nat,
                           +image_width: U32, +image_height: U32,
                           +max_iterations: Nat) -> String:
  match depth:
  case 0n:
    mandelbrot_render_row(first_row, column_count, image_width, image_height,
                          max_iterations)
  case 1n+remaining_depth:
    upper_rows lower_rows = mandelbrot_render_rows(remaining_depth, first_row, column_count, image_width, image_height, max_iterations)
                            mandelbrot_render_rows(remaining_depth, (first_row + U32.pow(2, remaining_depth) : U32), column_count, image_width, image_height, max_iterations)
    upper_rows ++ lower_rows

# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------

# Compute both images in a parallel let (two independent sub-trees), then
# concatenate with a separator newline.  The parallel let at this level
# means the two fork trees run concurrently.
def playground_render_all() -> String:
  mandelbrot_image sierpinski_image = mandelbrot_render_rows(5n, 0, 60n, 60, 32, 50n)
                                      sierpinski_render_rows(4n, 0, 32n)
  mandelbrot_image ++ SCon{Chr{10}, SNil{}} ++ sierpinski_image

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(playground_render_all())
