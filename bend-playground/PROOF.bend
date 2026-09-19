import Base
import ./LAWS.bend as Laws

def Laws.palette_zero():
  {==}

def Laws.palette_one():
  {==}

def Laws.palette_nine():
  {==}

def Laws.palette_default():
  {==}

def Laws.sierpinski_origin_is_filled():
  # and(0,0) = 0, is_eq(0, 0) = True, "*"
  {==}

def Laws.sierpinski_second_col_is_empty():
  # and(1,0) = 0, is_eq(0, 1) = False, " "
  {==}

def Laws.sierpinski_off_axis_is_filled():
  # and(0,1) = 0, is_eq(0, 0) = True, "*"
  {==}

# Case analysis on fuel. The escape flag is already True, so both the
# exhausted arm and the step arm return the count untouched and neither one
# reaches the arithmetic. The orbit coordinates are never inspected.
def Laws.orbit_stops_once_escaped(fuel, count,
                                  orbit_real_part, orbit_imaginary_part,
                                  constant_real_part, constant_imaginary_part):
  match fuel:
    case 0n:
      {==}
    case 1n+fuel_after_this_step:
      {==}

# Case analysis on the escape flag. Fuel is already spent, so both arms
# return the count and the flag only decides which of the two identical
# exhausted branches is taken.
def Laws.orbit_returns_count_when_fuel_runs_out(has_escaped, count,
                                                orbit_real_part, orbit_imaginary_part,
                                                constant_real_part, constant_imaginary_part):
  match has_escaped:
    case True{}:
      {==}
    case False{}:
      {==}

