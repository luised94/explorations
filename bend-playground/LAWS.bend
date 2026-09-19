import Base
import ./playground.bend as P

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

law sierpinski_off_axis_is_filled:
  {P.sierpinski_cell(0, 1) == "*" : String}

law orbit_immediate_escape:
  {P.mandelbrot_orbit(60n, 0n, 10.0, 10.0, 0.0, 0.0) == 0n : Nat}

law orbit_origin_never_escapes:
  {P.mandelbrot_orbit(60n, 0n, 0.0, 0.0, 0.0, 0.0) == 60n : Nat}
