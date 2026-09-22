import Base
import ./playground.bend as Playground

# This law constrains only the number of rows returned by
# Mandelbrot.render_rows. It says nothing about the contents of any row.
# A wrong implementation that returns the correct number of empty strings,
# ignoring the Mandelbrot set entirely, would satisfy it. The alternative
# rejected: a law about the exact pixels, which would require a proof
# about floating-point arithmetic and would be far harder to discharge.
law Mandelbrot.row_count:
  for remaining_rows: Nat
  for total_rows: Nat
  for current_row: Nat
  for total_columns: Nat
  for maximum_iterations: Nat
  { remaining_rows == List.length(&2, String, Playground.Mandelbrot.render_rows(remaining_rows, total_rows, current_row, total_columns, maximum_iterations)) : Nat }

# This law constrains only the number of rows returned by
# Sierpinski.render_rows. It says nothing about which cells are filled.
# A wrong implementation that returns the correct number of empty strings,
# ignoring the Sierpinski pattern entirely, would satisfy it. The
# alternative rejected: a law about the exact star positions, which would
# require a proof about bitwise arithmetic and would be far harder to
# discharge.
law Sierpinski.row_count:
  for remaining_rows: Nat
  for total_rows: Nat
  for current_row: Nat
  for total_columns: Nat
  { remaining_rows == List.length(&2, String, Playground.Sierpinski.render_rows(remaining_rows, total_rows, current_row, total_columns)) : Nat }
