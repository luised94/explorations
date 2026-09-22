import Base
import ./playground.bend as Playground

# ---------------------------------------------------------------------------
# Laws over playground.bend
#
# Every law here targets a function whose body reduces entirely by
# structural computation (U32 bitwise ops, Bool matches, Char constructors).
# F32 operations are opaque laws in Base, so no law can mention the
# Mandelbrot iteration's numeric behaviour.  The Sierpinski predicate uses
# only U32.and and U32.is_eq, both defined structurally over Word, so
# ground instances reduce to constructors.  The character-selection helpers
# are single Bool matches, trivially reducible.
#
# Laws I rejected and why:
# - "For all row, sierpinski_is_filled(row, 0) == True{}" requires proving
#   U32.and(x, 0) == 0 by induction on Word(32n), a 32-level recursion
#   through Equal.sym rewrites.  High risk of checker friction for modest
#   insight.  Kept as a stretch goal, not included.
# - Any law about Mandelbrot escape depth: F32 ops are axioms, undischargable.
# - String length laws: would require induction over the row builder and
#   String.append, adding proof complexity without testing new language
#   features beyond what the ground-term laws already exercise.
# ---------------------------------------------------------------------------

# The apex (row 0, col 0): 0 AND 0 = 0, and 0 == 0, so filled.
law sierpinski_apex_is_filled:
  {Playground.sierpinski_is_filled(0, 0) == True{} : Bool}

# Row 1, col 0: 0 AND 1 = 0, 0 == 0, filled.
law sierpinski_row_one_left_is_filled:
  {Playground.sierpinski_is_filled(1, 0) == True{} : Bool}

# Row 1, col 1: 1 AND 1 = 1, 1 == 1, filled.
law sierpinski_row_one_right_is_filled:
  {Playground.sierpinski_is_filled(1, 1) == True{} : Bool}

# Row 2, col 1: 1 AND 2 = 0, 0 != 1, empty.
# This is the first interior hole of the triangle; proving it empty
# confirms the predicate is not trivially True.
law sierpinski_row_two_middle_is_empty:
  {Playground.sierpinski_is_filled(2, 1) == False{} : Bool}

# Row 3, col 1: 1 AND 3 = 1, 1 == 1, filled.
# Row 3 is fully filled (all submasks of 3 are <= 3), confirming the
# predicate recovers the dense row after a hole.
law sierpinski_row_three_second_is_filled:
  {Playground.sierpinski_is_filled(3, 1) == True{} : Bool}

# Row 3, col 2: 2 AND 3 = 2, 2 == 2, filled.
law sierpinski_row_three_third_is_filled:
  {Playground.sierpinski_is_filled(3, 2) == True{} : Bool}

# A filled cell renders as '*' (Chr{42}).
law sierpinski_filled_cell_is_asterisk:
  {Playground.sierpinski_character_for_cell(True{}) == Chr{42} : Char}

# An empty cell renders as ' ' (Chr{32}).
law sierpinski_empty_cell_is_space:
  {Playground.sierpinski_character_for_cell(False{}) == Chr{32} : Char}

# A point in the Mandelbrot set renders as ' ' (Chr{32}).
law mandelbrot_in_set_is_space:
  {Playground.mandelbrot_branch_on_membership(True{}) == Chr{32} : Char}

# A point that escaped renders as '#' (Chr{35}).
law mandelbrot_escaped_is_hash:
  {Playground.mandelbrot_branch_on_membership(False{}) == Chr{35} : Char}
