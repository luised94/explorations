# LAWS.bend
# Claims about playground.bend. Each law is an open claim; PROOF.bend fills
# it in with a def of the same name.

import Base
import ./playground.bend as Playground

# The length of a repeated character run must equal the requested count.
# This is the only law that exercises a real induction; it mirrors the
# add_zero example from the guide.
law repeat_character_length:
  for count: Nat
  for character: Char
  {String.length(Playground.repeat_character(count, character)) == count : Nat}

# A point that has already escaped costs no further iterations, whatever the
# remaining budget is. The escape flag is the first argument to match the
# parameter order of escape_iterations, which the checker requires.
law mandelbrot_escaped_returns_zero:
  for remaining_iterations: Nat
  for real_part: F32
  for imaginary_part: F32
  for real_constant: F32
  for imaginary_constant: F32
  {Playground.Mandelbrot.escape_iterations(
    True{},
    remaining_iterations,
    real_part,
    imaginary_part,
    real_constant,
    imaginary_constant
  ) == 0n : Nat}

# A zero budget returns zero regardless of the escape flag. Without this the
# checker would have to reason about the F32 constants, which Base does not
# support.
law mandelbrot_zero_iterations_returns_zero:
  for real_part: F32
  for imaginary_part: F32
  for real_constant: F32
  for imaginary_constant: F32
  for point_has_escaped: Bool
  {Playground.Mandelbrot.escape_iterations(
    point_has_escaped,
    0n,
    real_part,
    imaginary_part,
    real_constant,
    imaginary_constant
  ) == 0n : Nat}

# The row list has exactly as many lines as rows requested. Stated over
# remaining_rows rather than over a pair count so that the induction step
# stays a plain 1n + 1n + IH without needing Nat.mul lemmas that Base does
# not have.
law mandelbrot_lines_remaining_length:
  for remaining_rows: Nat
  for start_row: Nat
  for half_width: Nat
  for width: Nat
  for height: Nat
  for max_iterations: Nat
  {List.length(
    &2,
    String,
    Playground.Mandelbrot.lines_remaining(
      remaining_rows, start_row, half_width, width, height, max_iterations
    )
  ) == remaining_rows : Nat}

# The Sierpinski row list has exactly as many lines as rows requested.
# Sierpinski rows are cheap and sequential, so the induction is the plain
# one-row-at-a-time shape.
law sierpinski_lines_remaining_length:
  for remaining_rows: Nat
  for current_actual_row: Nat
  for width: Nat
  {List.length(
    &2,
    String,
    Playground.Sierpinski.lines_remaining(
      remaining_rows, current_actual_row, width
    )
  ) == remaining_rows : Nat}
