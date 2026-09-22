import Base
import ./playground.bend as Playground
import ./LAWS.bend as Laws

# ---------------------------------------------------------------------------
# Every proof here is {==}: both sides of each law reduce by structural
# computation to the same constructor.  The checker normalises
# U32.and / U32.is_eq through 32 levels of Word recursion on concrete
# literals, and the Bool / Char matches reduce in one step.  No induction,
# no rewrite, no Equal.sym needed.
# ---------------------------------------------------------------------------

# 0 AND 0 = 0; U32.is_eq(0, 0) = True{}.
def Laws.sierpinski_apex_is_filled():
  {==}

# 0 AND 1 = 0; U32.is_eq(0, 0) = True{}.
def Laws.sierpinski_row_one_left_is_filled():
  {==}

# 1 AND 1 = 1; U32.is_eq(1, 1) = True{}.
def Laws.sierpinski_row_one_right_is_filled():
  {==}

# 1 AND 2 = 0; U32.is_eq(0, 1) = False{}.
def Laws.sierpinski_row_two_middle_is_empty():
  {==}

# 1 AND 3 = 1; U32.is_eq(1, 1) = True{}.
def Laws.sierpinski_row_three_second_is_filled():
  {==}

# 2 AND 3 = 2; U32.is_eq(2, 2) = True{}.
def Laws.sierpinski_row_three_third_is_filled():
  {==}

# match True{} -> Chr{42}.
def Laws.sierpinski_filled_cell_is_asterisk():
  {==}

# match False{} -> Chr{32}.
def Laws.sierpinski_empty_cell_is_space():
  {==}

# match True{} -> Chr{32}.
def Laws.mandelbrot_in_set_is_space():
  {==}

# match False{} -> Chr{35}.
def Laws.mandelbrot_escaped_is_hash():
  {==}
