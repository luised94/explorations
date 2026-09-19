# ============================================================
#   LAWS.bend
#   Invariants the program must never violate.
#   If any proof in PROOF.bend fails to discharge its law,
#   the compiler refuses to build playground.bend.
# ============================================================

law paletteTotality:
  "for every iterationIndex_inU24, mandelbrotEscapeCountAsAsciiCharacter
   returns exactly one character"
  # No pixel may ever render as empty or as more than one glyph.

law mandelbrotIterationTermination:
  "for every complexPlaneReal_inF24 and complexPlaneImag_inF24,
   mandelbrotEscapeCount halts within mandelbrotMaximumIterations"
  # The render loop is finite for every point in the plane.

law mandelbrotImageShape:
  "renderMandelbrotImageAsAsciiString emits exactly
   mandelbrotImageHeight_inPixels lines, each of
   mandelbrotImageWidth_inPixels characters, each followed by newline"
  # Output is a well-formed rectangular image.

law sierpinskiRowWidth:
  "every call to renderSierpinskiRowAsAsciiString emits exactly
   sierpinskiTriangleWidth_inCharacters characters, then one newline"
  # Rows align; the triangle does not shear.

law escapeTimeSoundness:
  "for every iteration state with zReal_inF24^2 + zImag_inF24^2 > 4.0,
   the orbit diverges"
  # The |z|^2 > 4 early-out is mathematically correct.
