import Base

# ASCII Mandelbrot set and ASCII Sierpinski triangle, printed to stdout.
#
# Shape of the fork tree: Mandelbrot.picture and Sierpinski.picture recurse on a
# Nat depth, splitting into two halves per level with a parallel let, so depth 5n
# is a perfectly balanced binary tree with 2^5 = 32 leaves, one leaf per output
# row. Balance is structural rather than hoped for: each subtree holds exactly
# half the rows of its parent, so the two siblings of every parallel call are the
# same size. That is the second promise a parallel call makes to the compiler
# ("they run in roughly the same time"); the first, independence, is free here
# because Bend is pure and affine.
#
# Each leaf is a flat constructor recursion over the columns, which is the only
# serial part of the work. The joins are List.append, which is O(rows) at the
# root and therefore the known non-ideality of this shape. Rejected alternative:
# appending Strings pairwise up the tree, which copies O(n log n) characters
# instead of O(n) cons cells.
#
# No `!` anywhere. A bang requires a .gpu artifact beside the binary plus Metal
# or CUDA at run time, and the work here is allocation-heavy list building, which
# the shaders guide places on the CPU pool. A parallel let in a compiled binary
# already runs on every core.

# Figure dimensions as defs rather than parameters: the guide's note that a
# parameter rides in every task applies to a constant threaded through a fork
# tree, and these are threaded through every level of picture.
def Mandelbrot.width() -> Nat:
  64n

def Sierpinski.width() -> Nat:
  32n

# Fixed, not an escape-time bound. An early-out would make the interior of the
# set (full iteration count) and the far exterior (two or three steps) siblings
# of wildly different cost in the same parallel call, which is exactly what the
# fork contract asks you not to do. The price is that every cell pays the worst
# case.
def Mandelbrot.iteration_limit() -> Nat:
  24n

# A String literal escape is unattested anywhere in Base, while the char literal
# '\n' is (String.lines). Going through a def also gives the line-length proof a
# syntactically identical term to apply the row-length law at.
def Text.newline() -> String:
  SCon{'\n', SNil{}}

# No Bool.pick freezing z after escape: once z overflows to infinity, inf - inf
# is NaN and every F32 comparison against NaN is false, so still_inside stays
# false for the remaining iterations on its own. Two fewer calls per iteration
# per cell.
def Mandelbrot.escape_count(iterations_remaining: Nat, +real_c: F32, +imag_c: F32,
  +real_z: F32, +imag_z: F32, inside_steps: U32) -> U32:
  match iterations_remaining:
    case 0n:
      inside_steps
    # The shrinking parameter comes first because the termination checker reads
    # the arguments of a recursive call left to right and stops at the first one
    # that is a smaller part of its parameter.
    case 1n+iterations_remaining_pred:
      +real_squared = F32.mul(real_z, real_z)
      +imag_squared = F32.mul(imag_z, imag_z)
      still_inside = F32.is_lt(F32.add(real_squared, imag_squared), 4.0)
      Mandelbrot.escape_count(iterations_remaining_pred, real_c, imag_c,
        F32.add(F32.sub(real_squared, imag_squared), real_c),
        F32.add(F32.mul(2.0, F32.mul(real_z, imag_z)), imag_c),
        U32.add(inside_steps, Bool.to_u32(still_inside)))

# The 24 here is Mandelbrot.iteration_limit(): a cell that never escaped scores
# the full count. They are separate literals because the limit is a Nat and the
# score is a U32, and Base has no cross-type comparison.
def Mandelbrot.shade(+inside_steps: U32) -> Char:
  Bool.pick(Char, U32.is_ge(inside_steps, 24), '#',
    Bool.pick(Char, U32.is_ge(inside_steps, 12), '+',
      Bool.pick(Char, U32.is_ge(inside_steps, 6), ':',
        Bool.pick(Char, U32.is_ge(inside_steps, 3), '.', ' '))))

# The offsets are applied with F32.sub rather than written as negative literals:
# a leading '-' would have to parse as the subtraction operator, which the guide
# says needs spaces on both sides.
#
# The lets are `+` because escape_count takes these as `+` parameters and an
# affine variable cannot be handed to one. Base promotes the same way
# (`+s2 = {U32{s} : U32}` in U32.divmod.go.shl).
def Mandelbrot.cell(row_index: U32, column_index: U32) -> Char:
  +real_c = F32.sub(F32.mul(U32.to_f32(column_index), 0.046875), 2.2)
  +imag_c = F32.sub(F32.mul(U32.to_f32(row_index), 0.0774), 1.2)
  Mandelbrot.shade(
    Mandelbrot.escape_count(Mandelbrot.iteration_limit(), real_c, imag_c,
      0.0, 0.0, 0))

# The whole figure is the single identity (row AND column) == 0. No recursion and
# no state, which is why the Sierpinski leaves are far cheaper than the
# Mandelbrot ones; the two pictures are never siblings in one parallel call, so
# the imbalance costs nothing.
def Sierpinski.cell(row_index: U32, column_index: U32) -> Char:
  Bool.pick(Char, U32.is_zero(U32.and(row_index, column_index)), '*', ' ')

# line_tail rather than appending a newline afterwards: it makes the length law
# provable by induction alone, with no String.append lemma and no second rewrite.
# row_index and column_index are `+` because each is read once for the cell and
# once again for the rest of the row.
def Mandelbrot.row(columns_remaining: Nat, +row_index: U32, +column_index: U32,
  line_tail: String) -> String:
  match columns_remaining:
    case 0n:
      line_tail
    case 1n+columns_remaining_pred:
      SCon{Mandelbrot.cell(row_index, column_index),
        Mandelbrot.row(columns_remaining_pred, row_index,
          U32.add(column_index, 1), line_tail)}

def Sierpinski.row(columns_remaining: Nat, +row_index: U32, +column_index: U32,
  line_tail: String) -> String:
  match columns_remaining:
    case 0n:
      line_tail
    case 1n+columns_remaining_pred:
      SCon{Sierpinski.cell(row_index, column_index),
        Sierpinski.row(columns_remaining_pred, row_index,
          U32.add(column_index, 1), line_tail)}

# row_index is `+` only because Mandelbrot.row demands a `+` argument, not
# because it is read twice here.
def Mandelbrot.line(width: Nat, +row_index: U32) -> String:
  Mandelbrot.row(width, row_index, 0, Text.newline())

def Sierpinski.line(width: Nat, +row_index: U32) -> String:
  Sierpinski.row(width, row_index, 0, Text.newline())

# The row count the fork tree promises, stated in the doubling form
# Nat.add(count, count) rather than Nat.double(count): the append lemma used by
# the picture laws produces a Nat.add, and matching it term for term saves two
# further lemmas.
def Picture.row_count(+depth: Nat) -> Nat:
  match depth:
    case 0n:
      1n
    case 1n+depth_pred:
      Nat.add(Picture.row_count(depth_pred), Picture.row_count(depth_pred))

# half_row_count carries 2^(depth-1) down the tree instead of the lower half
# computing it from depth_pred. The guide's pow2 example is the only evidence
# that a Nat predecessor may be used twice, and the two recursive calls already
# spend both uses; a third would be a guess.
def Mandelbrot.picture(+depth: Nat, +first_row_index: U32, +half_row_count: U32)
  -> List<&2, String>:
  match depth:
    case 0n:
      Mandelbrot.line(Mandelbrot.width(), first_row_index) <> Nil{}
    case 1n+depth_pred:
      upper_rows lower_rows =
        Mandelbrot.picture(depth_pred, first_row_index, U32.shr(half_row_count))
        Mandelbrot.picture(depth_pred, U32.add(first_row_index, half_row_count),
          U32.shr(half_row_count))
      List.append(&2, String, upper_rows, lower_rows)

def Sierpinski.picture(+depth: Nat, +first_row_index: U32, +half_row_count: U32)
  -> List<&2, String>:
  match depth:
    case 0n:
      Sierpinski.line(Sierpinski.width(), first_row_index) <> Nil{}
    case 1n+depth_pred:
      upper_rows lower_rows =
        Sierpinski.picture(depth_pred, first_row_index, U32.shr(half_row_count))
        Sierpinski.picture(depth_pred, U32.add(first_row_index, half_row_count),
          U32.shr(half_row_count))
      List.append(&2, String, upper_rows, lower_rows)

# Depth 5n is 32 rows, so the top-level half_row_count is 16. These three
# arguments are the only place the figure height is fixed.
def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(String.concat(Mandelbrot.picture(5n, 0, 16)))
    IO.print(String.concat(Sierpinski.picture(5n, 0, 16)))
