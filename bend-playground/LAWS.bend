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

# The F32 operations are host primitives with no reduction rule in the
# checker, so a law that pins the orbit to specific float coordinates cannot
# be closed: the escape test stays a stuck term and the match on it never
# picks a branch. The two laws below therefore quantify over the coordinates
# rather than instantiating them. Nothing about the floats needs to compute;
# what is being claimed is the control flow of the loop, which is where the
# bugs would live anyway.

law orbit_stops_once_escaped:
  for fuel: Nat
  for +count: Nat
  for +orbit_real_part: F32
  for +orbit_imaginary_part: F32
  for +constant_real_part: F32
  for +constant_imaginary_part: F32
  {P.mandelbrot_orbit_step(fuel, True{}, count,
                           orbit_real_part, orbit_imaginary_part,
                           constant_real_part, constant_imaginary_part) == count : Nat}

law orbit_returns_count_when_fuel_runs_out:
  for has_escaped: Bool
  for +count: Nat
  for +orbit_real_part: F32
  for +orbit_imaginary_part: F32
  for +constant_real_part: F32
  for +constant_imaginary_part: F32
  {P.mandelbrot_orbit_step(0n, has_escaped, count,
                           orbit_real_part, orbit_imaginary_part,
                           constant_real_part, constant_imaginary_part) == count : Nat}
