import Base
import ./LAWS.bend as Laws
import ./playground.bend as Playground

# playground.bend is imported here as well as in LAWS.bend because an import
# alias is local to the importing file and is not re-exported: there is no
# Laws.Playground.x to write the rewrite motives with.

# Specialised to List<&2, String> rather than written over Kind(a). The picture
# laws are the only call sites and both are lists of strings; a polymorphic
# version would add quantity arguments to every occurrence in every motive below
# for no gain.
#
# Oriented Nat.add(..) == List.length(List.append(..)), not the other way round:
# %e : P rewrites the goal's `b` position to `a`, and the goal has the
# List.length(List.append(..)) side, so that side must be `b`. Stating it the
# natural way round would cost an Equal.sym at every use.
#
# Both parameters are `+`: each is read once for the induction hypothesis and
# again in the motive.
def Proof.list_append_length(+left: List<&2, String>, +right: List<&2, String>)
  -> {Nat.add(List.length(&2, String, left), List.length(&2, String, right))
    == List.length(&2, String, List.append(&2, String, left, right)) : Nat}:
  match left:
    # Nat.add(0n, n) is n by reduction and List.append(Nil{}, ys) is ys, so both
    # sides are already the same term.
    case Nil{}:
      {==}
    case list_head <> list_tail:
      %Proof.list_append_length(list_tail, right) :
        {1n+Nat.add(List.length(&2, String, list_tail),
          List.length(&2, String, right)) == 1n+_ : Nat}
      {==}

# Row length. Induction on the column count alone. String.length only inspects
# the string's constructor, so the Char sitting in each head may stay stuck
# forever -- which is precisely why this law survives F32 being a primitive.
def Laws.mandelbrot_row_length(columns_remaining, row_index, column_index,
  line_tail):
  match columns_remaining:
    case 0n:
      {==}
    case 1n+columns_remaining_pred:
      %Laws.mandelbrot_row_length(columns_remaining_pred, row_index,
        U32.add(column_index, 1), line_tail) :
        {1n+String.length(Playground.Mandelbrot.row(columns_remaining_pred,
          row_index, U32.add(column_index, 1), line_tail)) == 1n+_ : Nat}
      {==}

def Laws.sierpinski_row_length(columns_remaining, row_index, column_index,
  line_tail):
  match columns_remaining:
    case 0n:
      {==}
    case 1n+columns_remaining_pred:
      %Laws.sierpinski_row_length(columns_remaining_pred, row_index,
        U32.add(column_index, 1), line_tail) :
        {1n+String.length(Playground.Sierpinski.row(columns_remaining_pred,
          row_index, U32.add(column_index, 1), line_tail)) == 1n+_ : Nat}
      {==}

# No induction: Mandelbrot.line unfolds to exactly the Mandelbrot.row call the
# row law is stated over, and String.length(Text.newline()) reduces to 1n, so
# the row law at line_tail = Text.newline() already has the claimed type.
def Laws.mandelbrot_line_length(width, row_index):
  Laws.mandelbrot_row_length(width, row_index, 0, Playground.Text.newline())

def Laws.sierpinski_line_length(width, row_index):
  Laws.sierpinski_row_length(width, row_index, 0, Playground.Text.newline())

# Picture row count. Three rewrites in the step case, in this order:
#   1. the append lemma, turning the length of the joined list into the sum of
#      the two halves' lengths;
#   2. the induction hypothesis on the upper half;
#   3. the induction hypothesis on the lower half, after which both sides are
#      the same term.
# The two halves are written out in full in every motive because a motive is a
# syntactic template, not an inferred one.
#
# This is the proof that has to see through a parallel let: the goal only
# reduces to a List.append if `upper_rows lower_rows = .. ..` is transparent to
# the checker. Semantically it is two lets, but I have no attestation either way.
def Laws.mandelbrot_picture_row_count(depth, first_row_index, half_row_count):
  match depth:
    # One leaf, one row: List.length of a single Con is 1n+0n, and
    # Picture.row_count(0n) is 1n. Same term.
    case 0n:
      {==}
    case 1n+depth_pred:
      %Proof.list_append_length(
        Playground.Mandelbrot.picture(depth_pred, first_row_index,
          U32.shr(half_row_count)),
        Playground.Mandelbrot.picture(depth_pred,
          U32.add(first_row_index, half_row_count), U32.shr(half_row_count))) :
        {_ == Nat.add(Playground.Picture.row_count(depth_pred),
          Playground.Picture.row_count(depth_pred)) : Nat}
      %Laws.mandelbrot_picture_row_count(depth_pred, first_row_index,
        U32.shr(half_row_count)) :
        {Nat.add(
          List.length(&2, String,
            Playground.Mandelbrot.picture(depth_pred, first_row_index,
              U32.shr(half_row_count))),
          List.length(&2, String,
            Playground.Mandelbrot.picture(depth_pred,
              U32.add(first_row_index, half_row_count),
              U32.shr(half_row_count))))
          == Nat.add(_, Playground.Picture.row_count(depth_pred)) : Nat}
      %Laws.mandelbrot_picture_row_count(depth_pred,
        U32.add(first_row_index, half_row_count), U32.shr(half_row_count)) :
        {Nat.add(
          List.length(&2, String,
            Playground.Mandelbrot.picture(depth_pred, first_row_index,
              U32.shr(half_row_count))),
          List.length(&2, String,
            Playground.Mandelbrot.picture(depth_pred,
              U32.add(first_row_index, half_row_count),
              U32.shr(half_row_count))))
          == Nat.add(
            List.length(&2, String,
              Playground.Mandelbrot.picture(depth_pred, first_row_index,
                U32.shr(half_row_count))), _) : Nat}
      {==}

def Laws.sierpinski_picture_row_count(depth, first_row_index, half_row_count):
  match depth:
    case 0n:
      {==}
    case 1n+depth_pred:
      %Proof.list_append_length(
        Playground.Sierpinski.picture(depth_pred, first_row_index,
          U32.shr(half_row_count)),
        Playground.Sierpinski.picture(depth_pred,
          U32.add(first_row_index, half_row_count), U32.shr(half_row_count))) :
        {_ == Nat.add(Playground.Picture.row_count(depth_pred),
          Playground.Picture.row_count(depth_pred)) : Nat}
      %Laws.sierpinski_picture_row_count(depth_pred, first_row_index,
        U32.shr(half_row_count)) :
        {Nat.add(
          List.length(&2, String,
            Playground.Sierpinski.picture(depth_pred, first_row_index,
              U32.shr(half_row_count))),
          List.length(&2, String,
            Playground.Sierpinski.picture(depth_pred,
              U32.add(first_row_index, half_row_count),
              U32.shr(half_row_count))))
          == Nat.add(_, Playground.Picture.row_count(depth_pred)) : Nat}
      %Laws.sierpinski_picture_row_count(depth_pred,
        U32.add(first_row_index, half_row_count), U32.shr(half_row_count)) :
        {Nat.add(
          List.length(&2, String,
            Playground.Sierpinski.picture(depth_pred, first_row_index,
              U32.shr(half_row_count))),
          List.length(&2, String,
            Playground.Sierpinski.picture(depth_pred,
              U32.add(first_row_index, half_row_count),
              U32.shr(half_row_count))))
          == Nat.add(
            List.length(&2, String,
              Playground.Sierpinski.picture(depth_pred, first_row_index,
                U32.shr(half_row_count))), _) : Nat}
      {==}
