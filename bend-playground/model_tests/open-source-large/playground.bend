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
# Nat length index), making this predicate provable by induction.  Recursive
# subdivision would require Nat subtraction proofs that add complexity
# without insight.
def sierpinski_is_filled(row: U32, col: U32) -> Bool:
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

# Render one Sierpinski row terminated by a newline.  The Nat
# columns_remaining is the structurally decreasing witness required by the
# termination checker; U32 col tracks position but cannot shrink
# structurally because U32 is Word(32n) with no inductive substructure.
# The alternative (recurse on U32) would fail the termination check.
def sierpinski_render_row_go(+row: U32, +col: U32, columns_remaining: Nat) -> String:
  match columns_remaining:
  case 0n:
    SCon{Chr{10}, SNil{}}
  case 1n+rest:
    SCon{sierpinski_character_for_cell(sierpinski_is_filled(row, col)),
         sierpinski_render_row_go(row, (col + 1 : U32), rest)}

# Entry point: render one row of the given column count.
def sierpinski_render_row(row: U32, column_count: Nat) -> String:
  sierpinski_render_row_go(row, 0, column_count)

# Balanced binary fork tree over rows.  At depth 0 one row is rendered (a
# flat loop over columns).  At depth d the range splits via a parallel let
# into two sub-trees of depth d-1, giving 2^d leaves.  The lower half is
# offset by 2^remaining_depth rows (U32.pow from Base).  The + annotations
# are required because first_row, remaining_depth, and column_count each
# appear in both branches of the parallel let.
def sierpinski_render_rows(+first_row: U32, +depth: Nat, +column_count: Nat) -> String:
  match depth:
  case 0n:
    sierpinski_render_row(first_row, column_count)
  case 1n+remaining_depth:
    upper_rows lower_rows = sierpinski_render_rows(first_row, remaining_depth, column_count)
                            sierpinski_render_rows((first_row + U32.pow(2, remaining_depth) : U32), remaining_depth, column_count)
    upper_rows ++ lower_rows

# ---------------------------------------------------------------------------
# Mandelbrot set
# ---------------------------------------------------------------------------

# Map a column index to the real-axis coordinate in [-2.0, 1.0).
# F32 arithmetic is used because the Mandelbrot iteration requires real
# numbers; Nat or U32 fixed-point would introduce rounding that shifts the
# set boundary and distorts the ASCII output.  All F32 ops are opaque laws
# in Base, so no algebraic property of this mapping is provable.
def mandelbrot_pixel_to_real(col: U32, image_width: U32) -> F32:
  F32.add(F32.neg(2.0), F32.mul(3.0, F32.div(U32.to_f32(col), U32.to_f32(image_width))))

# Map a row index to the imaginary-axis coordinate in [-1.5, 1.5).
def mandelbrot_pixel_to_imag(row: U32, image_height: U32) -> F32:
  F32.add(F32.neg(1.5), F32.mul(3.0, F32.div(U32.to_f32(row), U32.to_f32(image_height))))

# One Mandelbrot iteration step: z = z^2 + c.  The Nat fuel bounds the
# loop for the termination checker.  F32 is used for the actual arithmetic;
# these are opaque laws so the iteration count is not provable, but the
# structure (fuel decrease, branch on escape) is.
def mandelbrot_escape_go(+point_real: F32, +point_imag: F32, fuel: Nat,
                         +current_real: F32, +current_imag: F32,
                         iteration_count: U32) -> U32:
  match fuel:
  case 0n:
    iteration_count
  case 1n+remaining_fuel:
    +real_squared = F32.mul(current_real, current_real)
    +imag_squared = F32.mul(current_imag, current_imag)
    # Helper forced by the rule that match inspects only parameters or
    # pattern-bound variables, never computed values: the escape Bool is
    # computed from F32.is_gt, so it must be passed to a helper that
    # matches on its parameter.
    mandelbrot_escape_check(point_real, point_imag, remaining_fuel,
                            current_real, current_imag, iteration_count,
                            real_squared, imag_squared,
                            F32.is_gt(F32.add(real_squared, imag_squared), 4.0))

# Branch on the escape predicate.  This helper exists solely because the
# Bool is computed (from F32.is_gt) and cannot be matched inline.
def mandelbrot_escape_check(+point_real: F32, +point_imag: F32, fuel: Nat,
                            current_real: F32, current_imag: F32,
                            iteration_count: U32,
                            real_squared: F32, imag_squared: F32,
                            escaped: Bool) -> U32:
  match escaped:
  case True{}:
    iteration_count
  case False{}:
    # z_new = z^2 + c, expanded:
    #   real' = real^2 - imag^2 + c_real
    #   imag' = 2 * real * imag + c_imag
    next_real = F32.add(F32.sub(real_squared, imag_squared), point_real)
    next_imag = F32.add(F32.mul(F32.mul(2.0, current_real), current_imag), point_imag)
    mandelbrot_escape_go(point_real, point_imag, fuel, next_real, next_imag,
                         (iteration_count + 1 : U32))

# Entry point for the escape iteration at a given complex coordinate.
def mandelbrot_escape_depth(point_real: F32, point_imag: F32, max_iterations: Nat) -> U32:
  mandelbrot_escape_go(point_real, point_imag, max_iterations, 0.0, 0.0, 0)

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
# is computed, so the resulting Bool must arrive as a parameter.
def mandelbrot_character_for_depth(depth: U32, max_depth: U32) -> Char:
  mandelbrot_branch_on_membership(U32.is_eq(depth, max_depth))

# Render one Mandelbrot row terminated by a newline.  Nat columns_remaining
# is the termination witness; U32 col tracks position.
def mandelbrot_render_row_go(+row: U32, +col: U32, columns_remaining: Nat,
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
         mandelbrot_render_row_go(row, (col + 1 : U32), rest,
                                  image_width, image_height, max_iterations)}

# Entry point: render one Mandelbrot row.
def mandelbrot_render_row(row: U32, column_count: Nat,
                          image_width: U32, image_height: U32,
                          max_iterations: Nat) -> String:
  mandelbrot_render_row_go(row, 0, column_count, image_width, image_height,
                           max_iterations)

# Balanced binary fork tree over Mandelbrot rows, same shape as Sierpinski.
# Depth 5 gives 32 leaves (rows), each a flat loop over 60 columns with up
# to 50 F32 iterations per pixel.
def mandelbrot_render_rows(+first_row: U32, +depth: Nat, +column_count: Nat,
                           +image_width: U32, +image_height: U32,
                           +max_iterations: Nat) -> String:
  match depth:
  case 0n:
    mandelbrot_render_row(first_row, column_count, image_width, image_height,
                          max_iterations)
  case 1n+remaining_depth:
    upper_rows lower_rows = mandelbrot_render_rows(first_row, remaining_depth, column_count, image_width, image_height, max_iterations)
                            mandelbrot_render_rows((first_row + U32.pow(2, remaining_depth) : U32), remaining_depth, column_count, image_width, image_height, max_iterations)
    upper_rows ++ lower_rows

# ---------------------------------------------------------------------------
# Top level
# ---------------------------------------------------------------------------

# Compute both images in a parallel let (two independent sub-trees), then
# concatenate with a separator newline.  The parallel let at this level
# means the two fork trees run concurrently.
def playground_render_all() -> String:
  mandelbrot_image sierpinski_image = mandelbrot_render_rows(0, 5n, 60n, 60, 32, 50n)
                                      sierpinski_render_rows(0, 4n, 32n)
  mandelbrot_image ++ SCon{Chr{10}, SNil{}} ++ sierpinski_image

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(playground_render_all())
