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

def Laws.orbit_immediate_escape():
  # The initial magnitude squared is 200, above the threshold of 4, so the
  # orbit enters the loop already escaped and returns on the first match,
  # before any iteration is counted.
  {==}

def Laws.orbit_origin_never_escapes():
  # The magnitude squared stays 0, the escape flag is never set, and fuel
  # runs from 60n down to 0n with the count incremented on every step.
  {==}
