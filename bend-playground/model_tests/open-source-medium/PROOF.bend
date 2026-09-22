# PROOF.bend
# Discharges every law in LAWS.bend. Each def has the same name as the law
# it proves; bend refuses to run a PROOF.bend that sits beside a LAWS.bend
# without importing it.

import Base
import ./playground.bend as Playground
import ./LAWS.bend as Laws

# Induction on count. The base case is SNil{}, whose length is 0n by
# computation. The step rewrites the tail's length with the induction
# hypothesis and closes by computation.
def Laws.repeat_character_length(count, character):
  match count:
    case 0n:
      {==}
    case 1n+rest:
      %Laws.repeat_character_length(rest, character) :
        {1n+String.length(Playground.repeat_character(rest, character))
          == 1n+_ : Nat}
      {==}

# Split on remaining_iterations because that is the first scrutinee of the
# two-scrutinee match inside escape_iterations. In the 0n branch the first
# pattern "0n _" matches regardless of the second scrutinee, so the whole
# call reduces to 0n. In the 1n+rest branch the second scrutinee is True{},
# so the case "1n+rest True{}" matches and the call reduces to 0n. Neither
# branch needs to look at an F32 value, which is why {==} closes both.
def Laws.mandelbrot_escaped_returns_zero(
  remaining_iterations,
  real_part,
  imaginary_part,
  real_constant,
  imaginary_constant
):
  match remaining_iterations:
    case 0n:
      {==}
    case 1n+rest:
      {==}

# The first pattern of the inner match is "0n _", so the call reduces to 0n
# before either escape-flag branch can matter. The split on point_has_escaped
# is there so the checker sees a concrete Bool in each branch; if the checker
# already reduces "0n _" without it, the split is harmless.
def Laws.mandelbrot_zero_iterations_returns_zero(
  real_part,
  imaginary_part,
  real_constant,
  imaginary_constant,
  point_has_escaped
):
  match point_has_escaped:
    case True{}:
      {==}
    case False{}:
      {==}

# Induction on remaining_rows. The nested match on after_first is forced by
# the function's own shape: it distinguishes the one-row tail from the
# two-rows-plus-rest case. In the two-rows case the goal unfolds to
# 1n + 1n + length of the recursive list, and the hypothesis rewrites the
# tail's length to after_second.
def Laws.mandelbrot_lines_remaining_length(
  remaining_rows,
  start_row,
  half_width,
  width,
  height,
  max_iterations
):
  match remaining_rows:
    case 0n:
      {==}
    case 1n+after_first:
      match after_first:
        case 0n:
          {==}
        case 1n+after_second:
          %Laws.mandelbrot_lines_remaining_length(
            after_second,
            2n+start_row,
            half_width,
            width,
            height,
            max_iterations
          ) :
            {1n+1n+List.length(
              &2,
              String,
              Playground.Mandelbrot.lines_remaining(
                after_second,
                2n+start_row,
                half_width,
                width,
                height,
                max_iterations
              )
            ) == 1n+1n+_ : Nat}
          {==}

# Induction on remaining_rows, one row per step. The base case is Nil{} and
# the step rewrites the tail's length with the hypothesis.
def Laws.sierpinski_lines_remaining_length(
  remaining_rows,
  current_actual_row,
  width
):
  match remaining_rows:
    case 0n:
      {==}
    case 1n+rest:
      %Laws.sierpinski_lines_remaining_length(
        rest, Nat.sub(current_actual_row, 1n), width
      ) :
        {1n+List.length(
          &2,
          String,
          Playground.Sierpinski.lines_remaining(
            rest, Nat.sub(current_actual_row, 1n), width
          )
        ) == 1n+_ : Nat}
      {==}
