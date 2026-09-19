import Base
import ./playground.bend as P

# Every claim below is a fact we want the compiler to enforce.
# Each must be discharged by a `def Laws.<name>` in PROOF.bend.

law palette_zero:
  {P.palette(0n) == " " : String}

law palette_one:
  {P.palette(1n) == "." : String}

law palette_nine:
  {P.palette(9n) == "%" : String}

law palette_default:
  {P.palette(10n) == "@" : String}

law sierpinski_origin_is_filled:
  {P.sierpinski_cell(0, 0) == "*" : String}

law sierpinski_second_col_is_empty:
  {P.sierpinski_cell(1, 0) == " " : String}

law sierpinski_row0_all_filled:
  {P.sierpinski_cell(0, 0) ++ P.sierpinski_cell(1, 0)
     ++ P.sierpinski_cell(2, 0) == "** " : String}

law orbit_immediate_escape:
  # A point far outside the disk escapes on the very first test.
  {P.mandelbrot_orbit(60n, 0n, 10.0, 10.0, 0.0, 0.0) == 0n : Nat}

law orbit_origin_never_escapes:
  # The origin is in the set; with 60 fuel iterations we get 60 back.
  {P.mandelbrot_orbit(60n, 0n, 0.0, 0.0, 0.0, 0.0) == 60n : Nat}

law mapped_real_at_left_edge:
  {P.mapped_real(0) == P.plane_min_real() : F32}
