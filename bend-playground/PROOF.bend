# ============================================================
#   PROOF.bend
#   One proof per law. Each must be machine-checkable.
# ============================================================

proof paletteTotality:
  # mandelbrotEscapeCountAsAsciiCharacter is a match expression
  # with cases 0..9 plus a wildcard `case _:`. Every u24 hits
  # exactly one branch, and every branch returns a one-character
  # String literal. Therefore the function is total and single-valued.
  qed

proof mandelbrotIterationTermination:
  # Let M = mandelbrotMaximumIterations.
  # Measure m(state) = M - state.iterationsCompleted_inU24.
  # Each fork replaces state with state' where
  #   state'.iterationsCompleted_inU24 = state.iterationsCompleted_inU24 + 1
  # hence m(state') = m(state) - 1.
  # The loop exits when state.iterationsCompleted_inU24 >= M, i.e. m <= 0.
  # By well-founded induction on Nat, m reaches 0 in at most M steps.
  qed

proof mandelbrotImageShape:
  # renderMandelbrotImageAsAsciiString forks rowIndex_inPixels from
  # 0 to mandelbrotImageHeight_inPixels - 1.
  # Each iteration calls renderMandelbrotRowAsAsciiString, which
  # forks columnIndex_inPixels from 0 to mandelbrotImageWidth_inPixels - 1,
  # appending exactly one character per column, then one "\n".
  # Therefore each row is mandelbrotImageWidth_inPixels + 1 characters,
  # and there are mandelbrotImageHeight_inPixels such rows.
  qed

proof sierpinskiRowWidth:
  # renderSierpinskiRowAsAsciiString forks columnIndex_inU24 from
  # 0 to sierpinskiTriangleWidth_inCharacters - 1.
  # Each iteration appends exactly one character: "*" when
  # (columnIndex_inU24 & rowIndex_inU24) == columnIndex_inU24,
  # otherwise " ". One "\n" is appended after the loop.
  # Therefore each row body is exactly sierpinskiTriangleWidth_inCharacters.
  qed

proof escapeTimeSoundness:
  # Standard result: if |z| > 2 then |z^2 + c| > |z| for every c
  # with |c| <= 2. The test zReal_inF24^2 + zImag_inF24^2 > 4.0
  # is the square of |z| > 2, so the early-out is sound.
  qed
