# LAWS.bend
# Claims about playground.bend. Each law is an open claim; PROOF.bend fills
# it in with a def of the same name.
#
# Every law parameter that the corresponding proof def reads twice carries
# "+". The proof defs pass some parameters both to the recursive call and
# into the rewrite's P term, which is two reads; without "+" on the law
# parameter the proof body would violate the affine rule.

import Base
import ./playground.bend as Playground

# character is + because the proof def reads it in the recursive call and
# again inside the rewrite's P term.
law repeat_character_length:
  for count: Nat
  for +character: Char
  {String.length(Playground.repeat_character(count, character)) == count : Nat}

law mandelbrot_escaped_returns_zero:
  for remaining_iterations: Nat
  for real_part: F32
  for imaginary_part: F32
  for real_constant: F32
  for imaginary_constant: F32
  {Playground.mandelbrot_escape_iterations(
    remaining_iterations,
    True{},
    real_part,
    imaginary_part,
    real_constant,
    imaginary_constant
  ) == 0n : Nat}

law mandelbrot_zero_iterations_returns_zero:
  for real_part: F32
  for imaginary_part: F32
  for real_constant: F32
  for imaginary_constant: F32
  for point_has_escaped: Bool
  {Playground.mandelbrot_escape_iterations(
    0n,
    point_has_escaped,
    real_part,
    imaginary_part,
    real_constant,
    imaginary_constant
  ) == 0n : Nat}

# start_row, half_width, width, height and max_iterations are each + because
# the proof def passes them to the recursive call and then mentions them
# again inside the rewrite's P term.
law mandelbrot_lines_remaining_length:
  for remaining_rows: Nat
  for +start_row: Nat
  for +half_width: Nat
  for +width: Nat
  for +height: Nat
  for +max_iterations: Nat
  {List.length(
    &2,
    String,
    Playground.mandelbrot_render_lines_remaining(
      remaining_rows, start_row, half_width, width, height, max_iterations
    )
  ) == remaining_rows : Nat}

# current_actual_row and width are each + for the same reason: recursive
# call plus P term.
law sierpinski_lines_remaining_length:
  for remaining_rows: Nat
  for +current_actual_row: Nat
  for +width: Nat
  {List.length(
    &2,
    String,
    Playground.sierpinski_render_lines_remaining(
      remaining_rows, current_actual_row, width
    )
  ) == remaining_rows : Nat}
