# PROOF.bend -- discharges every law in LAWS.bend.

import Base
import ./playground.bend as Playground
import ./LAWS.bend as Laws

# Helper lemma, not one LAWS.bend states: List.append and List.length are
# Base's own, not playground.bend's, so a human writing LAWS.bend would
# have no reason to claim a fact about them -- it exists only because
# render_rows_count's step case needs it to combine two halves' lengths.
# Structural induction on first_list; the same one-rewrite-per-arm shape
# as "bend guide"'s own add_zero walkthrough, since Nat.add(0n, b) and
# List.append/List.length's Con cases all unfold by definition alone, with
# nothing to invent for the base case and exactly one rewrite for the step.
# +second_list: referenced twice in the step case below (once building the
# recursive call, once inside that call's own rewrite-target type
# annotation) -- the same class of double-use LAWS.bend's laws needed +
# for. first_list is only ever the match scrutinee itself (its head/tail
# are what get reused, not first_list as a whole), so it stays plain.
law List.append_length:
  for -element_type: Data
  for first_list: List<&2, element_type>
  for +second_list: List<&2, element_type>
  {List.length(&2, element_type, List.append(&2, element_type, first_list, second_list))
    == Nat.add(List.length(&2, element_type, first_list), List.length(&2, element_type, second_list))
    : Nat}

def List.append_length(element_type, first_list, second_list):
  match first_list:
    case Nil{}:
      {==}
    case head <> tail:
      %List.append_length(element_type, tail, second_list)
        : {1n+List.length(&2, element_type,
              List.append(&2, element_type, tail, second_list)) == 1n+_ : Nat}
      {==}

# Discharges Sierpinski.render_row_length: induction on the fuel argument
# render_row itself recurses on (remaining_columns), the same structure as
# add_zero's induction on its Nat argument. Base case: render_row(0n
# columns) is SNil{}, String.length of that is 0n by definition, matching
# the fuel of 0n by definition too -- no rewrite needed. Step case: one
# rewrite by the induction hypothesis, exactly add_zero's shape.
def Laws.Sierpinski.render_row_length(row_index, remaining_columns, column_index):
  match remaining_columns:
    case 0n:
      {==}
    case 1n+columns_left:
      %Laws.Sierpinski.render_row_length(row_index, columns_left, U32.inc(column_index))
        : {1n+String.length(Playground.Sierpinski.render_row(
              row_index, columns_left, U32.inc(column_index))) == 1n+_ : Nat}
      {==}

# Discharges Sierpinski.render_rows_count: induction on level, the same
# argument render_rows itself forks on.
#
# Base case (level = 0n): render_rows produces the one-row list built by
# the flat loop; its length is 1n by definition, matching rows_count(0n)
# = 1n by definition -- no rewrite needed.
#
# Step case (level = 1n+levels_left): the goal, after both sides unfold by
# definition, is
#   length(append(left_rows, right_rows)) == add(rows_count(p), rows_count(p))
# built here as one composed equality rather than a chain of rewrite
# statements (there is a worked example of composing Equal.trans and
# Equal.cong -- U32.add_comm, Word.add_comm.arm -- but none of chaining
# several %rewrite statements in one proof body, so this leans on the
# pattern already known to work):
#   lengths_step   : length(append(left,right)) == add(length(left), length(right))
#     -- List.append_length above, applied to this call's own two halves.
#   left_matches_count, right_matches_count : each induction hypothesis,
#     lifted into the sum by Equal.cong on one argument of Nat.add at a
#     time (the same one-argument-at-a-time congruence Word.add_comm.arm
#     uses to lift an equality under a constructor).
#   counts_combine : the two lifted equalities chained by Equal.trans.
#   the final Equal.trans chains lengths_step with counts_combine, giving
#     exactly the goal above.
def Laws.Sierpinski.render_rows_count(level, row_start, total_columns):
  match level:
    case 0n:
      {==}
    case 1n+levels_left:
      # row_start and total_columns are each read four times below (both
      # halves' render_rows calls, both halves' induction-hypothesis
      # calls). Marking them + in LAWS.bend's law did not carry through to
      # this cross-file def -- the checker still reported total_columns
      # "consumed more than once" at this def's own signature, unlike
      # row_offset's identical problem below (a same-file let), which +
      # did fix. Re-binding each to a fresh + let here, the same
      # mechanism already proven to work twice in this file, sidesteps
      # the question of whether that's a real cross-file inheritance gap
      # or just this checker reporting one offending binder per run.
      +row_start_reusable = row_start
      +total_columns_reusable = total_columns
      # Read twice below: once building right_rows, once again inside
      # right_matches_count's induction-hypothesis call. Same class of
      # error as above.
      +row_offset = U32.pow(2, levels_left)
      left_rows = Playground.Sierpinski.render_rows(levels_left, row_start_reusable, total_columns_reusable)
      right_rows = Playground.Sierpinski.render_rows(levels_left, U32.add(row_start_reusable, row_offset), total_columns_reusable)
      rows_per_half = Playground.Sierpinski.rows_count(levels_left)
      lengths_step = List.append_length(String, left_rows, right_rows)
      left_matches_count = Equal.cong(Nat, Nat,
        count => Nat.add(count, List.length(&2, String, right_rows)),
        List.length(&2, String, left_rows), rows_per_half,
        Laws.Sierpinski.render_rows_count(levels_left, row_start_reusable, total_columns_reusable))
      right_matches_count = Equal.cong(Nat, Nat,
        count => Nat.add(rows_per_half, count),
        List.length(&2, String, right_rows), rows_per_half,
        Laws.Sierpinski.render_rows_count(levels_left, U32.add(row_start_reusable, row_offset), total_columns_reusable))
      counts_combine = Equal.trans(Nat,
        Nat.add(List.length(&2, String, left_rows), List.length(&2, String, right_rows)),
        Nat.add(rows_per_half, List.length(&2, String, right_rows)),
        Nat.add(rows_per_half, rows_per_half),
        left_matches_count, right_matches_count)
      Equal.trans(Nat,
        List.length(&2, String, List.append(&2, String, left_rows, right_rows)),
        Nat.add(List.length(&2, String, left_rows), List.length(&2, String, right_rows)),
        Nat.add(rows_per_half, rows_per_half),
        lengths_step, counts_combine)
