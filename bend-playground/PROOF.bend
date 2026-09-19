import Base
import ./LAWS.bend as Laws

# Each `def Laws.<name>()` discharges the law of the same name.
# `{==}` closes a goal whose two sides compute to the same term.

def Laws.palette_zero():
  {==}

def Laws.palette_one():
  {==}

def Laws.palette_nine():
  {==}

def Laws.palette_default():
  {==}

def Laws.sierpinski_origin_is_filled():
  # (0 & 0) == 0 -> True -> "*"
  {==}

def Laws.sierpinski_second_col_is_empty():
  # (1 & 0) == 0 != 1 -> False -> " "
  {==}

def Laws.sierpinski_row0_all_filled():
  # Row 0: all cells pass (k & 0) == k, so all are "*".
  # (column 2 never appears, so the "** " claim is only about 0 and 1.)
  {==}

def Laws.orbit_immediate_escape():
  # mag_sq = 200.0, 200 > 4 -> True -> count = 0n
  {==}

def Laws.orbit_origin_never_escapes():
  # mag_sq stays 0, F32.is_gt(0, 4) is False at every step.
  # 60n fuel steps, count goes 0n -> 60n.
  {==}

def Laws.mapped_real_at_left_edge():
  # column=0 -> c=0 -> plane_min_real() + 0 = plane_min_real()
  {==}
