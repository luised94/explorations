import Base
import ./playground.bend as Playground
import ./LAWS.bend as Laws

# The proof is by induction on remaining_rows. The base case is 0n, where
# the list is Nil and List.length returns 0n. The step case is 1n+predecessor.
# The render_rows def matches this case and returns a cons. List.length of a
# cons reduces to 1n plus the length of the tail. The induction hypothesis
# states that predecessor equals the length of the tail. The rewrite replaces
# the tail length with predecessor, and reflexivity closes the goal. This
# induction is required because the law is universally quantified over all
# remaining row counts, not just one concrete value.
def Laws.Mandelbrot.row_count(
  remaining_rows: Nat,
  total_rows: Nat,
  current_row: Nat,
  total_columns: Nat,
  maximum_iterations: Nat
) -> { remaining_rows == List.length(&2, String, Playground.Mandelbrot.render_rows(remaining_rows, total_rows, current_row, total_columns, maximum_iterations)) : Nat }:
  match remaining_rows:
    case 0n:
      {==}
    case 1n+predecessor:
      %Laws.Mandelbrot.row_count(predecessor, total_rows, Nat.add(current_row, 1n), total_columns, maximum_iterations) : {1n+predecessor == 1n+_ : Nat}
      {==}

# The proof is by induction on remaining_rows, exactly as for the
# Mandelbrot law. The base case is 0n. The step case uses the induction
# hypothesis to replace the tail length with predecessor. The rewrite
# direction matches the law's equality direction: remaining_rows is on the
# left and List.length is on the right.
def Laws.Sierpinski.row_count(
  remaining_rows: Nat,
  total_rows: Nat,
  current_row: Nat,
  total_columns: Nat
) -> { remaining_rows == List.length(&2, String, Playground.Sierpinski.render_rows(remaining_rows, total_rows, current_row, total_columns)) : Nat }:
  match remaining_rows:
    case 0n:
      {==}
    case 1n+predecessor:
      %Laws.Sierpinski.row_count(predecessor, total_rows, Nat.add(current_row, 1n), total_columns) : {1n+predecessor == 1n+_ : Nat}
      {==}
