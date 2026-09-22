import Base

# A 64-by-128 raster keeps stdout usable while two three-level four-way trees
# still create 4^6 balanced terminal fragments for each figure.
type TextFragmentTree is Data:
  TextFragmentLeaf{fragment_text: String}
  TextFragmentBranch{
    leftmost_fragment: TextFragmentTree,
    left_center_fragment: TextFragmentTree,
    right_center_fragment: TextFragmentTree,
    rightmost_fragment: TextFragmentTree
  }

type TextFragmentStack is Data:
  NoPendingTextFragments{}
  PendingTextFragment{
    next_text_fragment: TextFragmentTree,
    remaining_text_fragments: TextFragmentStack
  }

type TextRowTree is Data:
  TextRowLeaf{row_text: String}
  TextRowBranch{
    topmost_rows: TextRowTree,
    upper_middle_rows: TextRowTree,
    lower_middle_rows: TextRowTree,
    bottommost_rows: TextRowTree
  }

type TextRowStack is Data:
  NoPendingTextRows{}
  PendingTextRow{
    next_text_row: TextRowTree,
    remaining_text_rows: TextRowStack
  }

def Output.newline_text() -> String:
  SCon{'\n', SNil{}}

# The stack visits fragments right-to-left so each fixed two-character
# fragment can be prepended; appending to a growing left prefix was rejected
# because it repeatedly copies an increasingly long String.
#
# Fuel is first because opening a branch grows the stack, which cannot itself
# justify structural recursion under Bend's termination rule.
def TextFragmentTree.to_text.loop(
  remaining_work_steps: Nat,
  pending_text_fragments: TextFragmentStack,
  accumulated_text: String
) -> String:
  match remaining_work_steps:
    case 0n:
      accumulated_text
    case 1n+smaller_remaining_work_steps:
      match pending_text_fragments:
        case NoPendingTextFragments{}:
          accumulated_text
        case PendingTextFragment{
          next_text_fragment,
          remaining_text_fragments
        }:
          match next_text_fragment:
            case TextFragmentLeaf{fragment_text}:
              TextFragmentTree.to_text.loop(
                smaller_remaining_work_steps,
                remaining_text_fragments,
                String.append(fragment_text, accumulated_text)
              )
            case TextFragmentBranch{
              leftmost_fragment,
              left_center_fragment,
              right_center_fragment,
              rightmost_fragment
            }:
              TextFragmentTree.to_text.loop(
                smaller_remaining_work_steps,
                PendingTextFragment{
                  rightmost_fragment,
                  PendingTextFragment{
                    right_center_fragment,
                    PendingTextFragment{
                      left_center_fragment,
                      PendingTextFragment{
                        leftmost_fragment,
                        remaining_text_fragments
                      }
                    }
                  }
                },
                accumulated_text
              )

def TextFragmentTree.to_text(text_fragment_tree: TextFragmentTree) -> String:
  TextFragmentTree.to_text.loop(
    85n,
    PendingTextFragment{text_fragment_tree, NoPendingTextFragments{}},
    ""
  )

# Rows are also visited bottom-to-top so a completed fixed-width row can be
# prepended. Forward traversal with a growing accumulator was rejected because
# String.append would repeatedly traverse all prior rows.
def TextRowTree.to_text.loop(
  remaining_work_steps: Nat,
  pending_text_rows: TextRowStack,
  accumulated_text: String
) -> String:
  match remaining_work_steps:
    case 0n:
      accumulated_text
    case 1n+smaller_remaining_work_steps:
      match pending_text_rows:
        case NoPendingTextRows{}:
          accumulated_text
        case PendingTextRow{next_text_row, remaining_text_rows}:
          match next_text_row:
            case TextRowLeaf{row_text}:
              TextRowTree.to_text.loop(
                smaller_remaining_work_steps,
                remaining_text_rows,
                String.append(row_text, accumulated_text)
              )
            case TextRowBranch{
              topmost_rows,
              upper_middle_rows,
              lower_middle_rows,
              bottommost_rows
            }:
              TextRowTree.to_text.loop(
                smaller_remaining_work_steps,
                PendingTextRow{
                  bottommost_rows,
                  PendingTextRow{
                    lower_middle_rows,
                    PendingTextRow{
                      upper_middle_rows,
                      PendingTextRow{
                        topmost_rows,
                        remaining_text_rows
                      }
                    }
                  }
                },
                accumulated_text
              )

def TextRowTree.to_text(text_row_tree: TextRowTree) -> String:
  TextRowTree.to_text.loop(
    85n,
    PendingTextRow{text_row_tree, NoPendingTextRows{}},
    ""
  )

def Mandelbrot.real_coordinate(column_number: U32) -> F32:
  F32.div(
    F32.sub(F32.from_nat(U32.to_nat(column_number)), 64.0),
    32.0
  )

def Mandelbrot.imaginary_coordinate(row_number: U32) -> F32:
  F32.div(
    F32.sub(F32.from_nat(U32.to_nat(row_number)), 32.0),
    24.0
  )

def Mandelbrot.outside_radius(
  +real_component: F32,
  +imaginary_component: F32
) -> Bool:
  F32.is_gt(
    F32.add(
      F32.mul(real_component, real_component),
      F32.mul(imaginary_component, imaginary_component)
    ),
    4.0
  )

def Mandelbrot.next_real_component(
  +current_real_component: F32,
  +current_imaginary_component: F32,
  real_coordinate: F32
) -> F32:
  F32.add(
    F32.sub(
      F32.mul(current_real_component, current_real_component),
      F32.mul(current_imaginary_component, current_imaginary_component)
    ),
    real_coordinate
  )

def Mandelbrot.next_imaginary_component(
  current_real_component: F32,
  current_imaginary_component: F32,
  imaginary_coordinate: F32
) -> F32:
  F32.add(
    F32.mul(2.0, F32.mul(current_real_component, current_imaginary_component)),
    imaginary_coordinate
  )

# All cells take exactly 32 iterations. Early escape was rejected because it
# makes boundary cells much slower than exterior cells, breaking fork balance.
#
# The scalar updates remain sequential: forking tiny arithmetic expressions
# would add scheduling work instead of exposing useful terminal parallelism.
def Mandelbrot.escape_status(
  remaining_iteration_count: Nat,
  +real_coordinate: F32,
  +imaginary_coordinate: F32,
  +current_real_component: F32,
  +current_imaginary_component: F32,
  escaped_before_this_iteration: Bool
) -> Bool:
  match remaining_iteration_count:
    case 0n:
      escaped_before_this_iteration
    case 1n+smaller_remaining_iteration_count:
      +next_real_component = Mandelbrot.next_real_component(
        current_real_component,
        current_imaginary_component,
        real_coordinate
      )
      +next_imaginary_component = Mandelbrot.next_imaginary_component(
        current_real_component,
        current_imaginary_component,
        imaginary_coordinate
      )
      Mandelbrot.escape_status(
        smaller_remaining_iteration_count,
        real_coordinate,
        imaginary_coordinate,
        next_real_component,
        next_imaginary_component,
        Bool.or(
          escaped_before_this_iteration,
          Mandelbrot.outside_radius(
            next_real_component,
            next_imaginary_component
          )
        )
      )

# Bend rejects matching a computed Boolean, so pixel computation passes its
# result here and this helper matches its own bound parameter.
def Mandelbrot.glyph_for_escape_status(escape_status: Bool) -> String:
  match escape_status:
    case False{}:
      "#"
    case True{}:
      " "

def Mandelbrot.pixel(row_number: U32, column_number: U32) -> String:
  Mandelbrot.glyph_for_escape_status(
    Mandelbrot.escape_status(
      32n,
      Mandelbrot.real_coordinate(column_number),
      Mandelbrot.imaginary_coordinate(row_number),
      0.0,
      0.0,
      False{}
    )
  )

def Mandelbrot.two_columns(
  +row_number: U32,
  +first_column_number: U32
) -> String:
  String.append(
    Mandelbrot.pixel(row_number, first_column_number),
    Mandelbrot.pixel(row_number, U32.add(first_column_number, 1))
  )

# Each branch receives the same number of columns and each leaf computes two
# fixed-cost pixels, preserving the equal-duration promise of parallel lets.
def Mandelbrot.fragment_tree(
  remaining_fragment_subdivisions: Nat,
  +row_number: U32,
  +first_column_number: U32,
  column_block_width: U32
) -> TextFragmentTree:
  match remaining_fragment_subdivisions:
    case 0n:
      TextFragmentLeaf{
        Mandelbrot.two_columns(row_number, first_column_number)
      }
    case 1n+smaller_remaining_fragment_subdivisions:
      +child_column_block_width = U32.shrn(column_block_width, 2n)
      +second_fragment_first_column_number = U32.add(
        first_column_number,
        child_column_block_width
      )
      +third_fragment_first_column_number = U32.add(
        second_fragment_first_column_number,
        child_column_block_width
      )
      fourth_fragment_first_column_number = U32.add(
        third_fragment_first_column_number,
        child_column_block_width
      )
      leftmost_fragment_tree left_center_fragment_tree right_center_fragment_tree rightmost_fragment_tree =
        Mandelbrot.fragment_tree(
          smaller_remaining_fragment_subdivisions,
          row_number,
          first_column_number,
          child_column_block_width
        ) Mandelbrot.fragment_tree(
          smaller_remaining_fragment_subdivisions,
          row_number,
          second_fragment_first_column_number,
          child_column_block_width
        )
        Mandelbrot.fragment_tree(
          smaller_remaining_fragment_subdivisions,
          row_number,
          third_fragment_first_column_number,
          child_column_block_width
        ) Mandelbrot.fragment_tree(
          smaller_remaining_fragment_subdivisions,
          row_number,
          fourth_fragment_first_column_number,
          child_column_block_width
        )
      TextFragmentBranch{
        leftmost_fragment_tree,
        left_center_fragment_tree,
        right_center_fragment_tree,
        rightmost_fragment_tree
      }

# The first three fork levels distribute rows. The horizontal tree starts at
# each row leaf, rather than forcing unlike work into the first frontier.
def Mandelbrot.row_tree(
  remaining_row_subdivisions: Nat,
  +first_row_number: U32,
  row_block_height: U32
) -> TextRowTree:
  match remaining_row_subdivisions:
    case 0n:
      TextRowLeaf{
        String.append(
          TextFragmentTree.to_text(
            Mandelbrot.fragment_tree(3n, first_row_number, 0, 128)
          ),
          Output.newline_text()
        )
      }
    case 1n+smaller_remaining_row_subdivisions:
      +child_row_block_height = U32.shrn(row_block_height, 2n)
      +second_row_number = U32.add(
        first_row_number,
        child_row_block_height
      )
      +third_row_number = U32.add(
        second_row_number,
        child_row_block_height
      )
      fourth_row_number = U32.add(
        third_row_number,
        child_row_block_height
      )
      topmost_row_tree upper_middle_row_tree lower_middle_row_tree bottommost_row_tree =
        Mandelbrot.row_tree(
          smaller_remaining_row_subdivisions,
          first_row_number,
          child_row_block_height
        ) Mandelbrot.row_tree(
          smaller_remaining_row_subdivisions,
          second_row_number,
          child_row_block_height
        )
        Mandelbrot.row_tree(
          smaller_remaining_row_subdivisions,
          third_row_number,
          child_row_block_height
        ) Mandelbrot.row_tree(
          smaller_remaining_row_subdivisions,
          fourth_row_number,
          child_row_block_height
        )
      TextRowBranch{
        topmost_row_tree,
        upper_middle_row_tree,
        lower_middle_row_tree,
        bottommost_row_tree
      }

# Bend rejects matching the Boolean expression calculated for a cell, so the
# completed ink decision is received as a parameter before it is matched.
def Sierpinski.glyph_for_ink(cell_has_ink: Bool) -> String:
  match cell_has_ink:
    case False{}:
      " "
    case True{}:
      "#"

# Bounds and bit overlap are always evaluated to keep terminal work uniform.
# Out-of-range U32 subtraction is harmless because the false bounds result
# masks that overlap result; a branchy bounds test was rejected for imbalance.
def Sierpinski.cell(+row_number: U32, +column_number: U32) -> String:
  Sierpinski.glyph_for_ink(
    Bool.and(
      Bool.and(
        U32.is_ge(column_number, U32.sub(64, row_number)),
        U32.is_le(column_number, U32.add(64, row_number))
      ),
      U32.is_zero(
        U32.and(
          U32.sub(column_number, U32.sub(64, row_number)),
          U32.sub(U32.add(64, row_number), column_number)
        )
      )
    )
  )

def Sierpinski.two_columns(
  +row_number: U32,
  +first_column_number: U32
) -> String:
  String.append(
    Sierpinski.cell(row_number, first_column_number),
    Sierpinski.cell(row_number, U32.add(first_column_number, 1))
  )

def Sierpinski.fragment_tree(
  remaining_fragment_subdivisions: Nat,
  +row_number: U32,
  +first_column_number: U32,
  column_block_width: U32
) -> TextFragmentTree:
  match remaining_fragment_subdivisions:
    case 0n:
      TextFragmentLeaf{
        Sierpinski.two_columns(row_number, first_column_number)
      }
    case 1n+smaller_remaining_fragment_subdivisions:
      +child_column_block_width = U32.shrn(column_block_width, 2n)
      +second_fragment_first_column_number = U32.add(
        first_column_number,
        child_column_block_width
      )
      +third_fragment_first_column_number = U32.add(
        second_fragment_first_column_number,
        child_column_block_width
      )
      fourth_fragment_first_column_number = U32.add(
        third_fragment_first_column_number,
        child_column_block_width
      )
      leftmost_fragment_tree left_center_fragment_tree right_center_fragment_tree rightmost_fragment_tree =
        Sierpinski.fragment_tree(
          smaller_remaining_fragment_subdivisions,
          row_number,
          first_column_number,
          child_column_block_width
        ) Sierpinski.fragment_tree(
          smaller_remaining_fragment_subdivisions,
          row_number,
          second_fragment_first_column_number,
          child_column_block_width
        )
        Sierpinski.fragment_tree(
          smaller_remaining_fragment_subdivisions,
          row_number,
          third_fragment_first_column_number,
          child_column_block_width
        ) Sierpinski.fragment_tree(
          smaller_remaining_fragment_subdivisions,
          row_number,
          fourth_fragment_first_column_number,
          child_column_block_width
        )
      TextFragmentBranch{
        leftmost_fragment_tree,
        left_center_fragment_tree,
        right_center_fragment_tree,
        rightmost_fragment_tree
      }

def Sierpinski.row_tree(
  remaining_row_subdivisions: Nat,
  +first_row_number: U32,
  row_block_height: U32
) -> TextRowTree:
  match remaining_row_subdivisions:
    case 0n:
      TextRowLeaf{
        String.append(
          TextFragmentTree.to_text(
            Sierpinski.fragment_tree(3n, first_row_number, 0, 128)
          ),
          Output.newline_text()
        )
      }
    case 1n+smaller_remaining_row_subdivisions:
      +child_row_block_height = U32.shrn(row_block_height, 2n)
      +second_row_number = U32.add(
        first_row_number,
        child_row_block_height
      )
      +third_row_number = U32.add(
        second_row_number,
        child_row_block_height
      )
      fourth_row_number = U32.add(
        third_row_number,
        child_row_block_height
      )
      topmost_row_tree upper_middle_row_tree lower_middle_row_tree bottommost_row_tree =
        Sierpinski.row_tree(
          smaller_remaining_row_subdivisions,
          first_row_number,
          child_row_block_height
        ) Sierpinski.row_tree(
          smaller_remaining_row_subdivisions,
          second_row_number,
          child_row_block_height
        )
        Sierpinski.row_tree(
          smaller_remaining_row_subdivisions,
          third_row_number,
          child_row_block_height
        ) Sierpinski.row_tree(
          smaller_remaining_row_subdivisions,
          fourth_row_number,
          child_row_block_height
        )
      TextRowBranch{
        topmost_row_tree,
        upper_middle_row_tree,
        lower_middle_row_tree,
        bottommost_row_tree
      }

# Unit keeps the banged entry visibly argument-bearing because the supplied
# guide demonstrates banged calls with arguments, not a zero-argument bang.
#
# The figures are sequenced instead of placed in a parallel let: Mandelbrot's
# fixed F32 loop and Sierpinski's U32 test are not roughly equal-duration work.
def Playground.figure_trees(rendering_trigger: Unit) -> TextRowTree & TextRowTree:
  mandelbrot_row_tree = Mandelbrot.row_tree(3n, 0, 64)
  sierpinski_row_tree = Sierpinski.row_tree(3n, 0, 64)
  (mandelbrot_row_tree, sierpinski_row_tree)

def Playground.rendered_figures(
  figure_trees: TextRowTree & TextRowTree
) -> String & String:
  (mandelbrot_row_tree, sierpinski_row_tree) = figure_trees
  mandelbrot_text = TextRowTree.to_text(mandelbrot_row_tree)
  sierpinski_text = TextRowTree.to_text(sierpinski_row_tree)
  (mandelbrot_text, sierpinski_text)

def Playground.print_figures(
  rendered_figures: String & String
) -> IO(Unit):
  (mandelbrot_text, sierpinski_text) = rendered_figures
  do IO<Unit>:
    IO.print(String.append("Mandelbrot", Output.newline_text()))
    IO.print(mandelbrot_text)
    IO.print(String.append("Sierpinski triangle", Output.newline_text()))
    IO.print(sierpinski_text)

def main() -> IO(Unit):
  Playground.print_figures(
    Playground.rendered_figures(Playground.figure_trees!(Unit{}))
  )
