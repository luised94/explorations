# ============================================================
#   BEND PARALLEL PLAYGROUND v3
#   Explicit names. Data-oriented. Law-verified.
#   Target: WSL on Windows, CPU only (no CUDA).
# ============================================================
#   bend run   playground.bend    # interpreter (debugging)
#   bend run-c playground.bend    # C backend, all cores (recommended)
# ============================================================

# ------------------------------------------------------------
#   Compile-time configuration
#   (kept as zero-argument functions so names read as values)
# ------------------------------------------------------------

def mandelbrotImageWidth_inPixels():        return 100
def mandelbrotImageHeight_inPixels():       return 40
def mandelbrotMaximumIterations():          return 60

def mandelbrotComplexPlaneMinimumReal():    return -2.5
def mandelbrotComplexPlaneMaximumReal():    return  1.0
def mandelbrotComplexPlaneMinimumImag():    return -1.2
def mandelbrotComplexPlaneMaximumImag():    return  1.2

def sierpinskiTriangleHeight_inRows():      return 30
def sierpinskiTriangleWidth_inCharacters(): return 60

# Hoisted loop-invariant scale factors (computed once, reused per pixel).
def mandelbrotComplexPlaneStepRealPerPixel():
  return (mandelbrotComplexPlaneMaximumReal() - mandelbrotComplexPlaneMinimumReal())
         / (mandelbrotImageWidth_inPixels() + 0.0)

def mandelbrotComplexPlaneStepImagPerPixel():
  return (mandelbrotComplexPlaneMaximumImag() - mandelbrotComplexPlaneMinimumImag())
         / (mandelbrotImageHeight_inPixels() + 0.0)

# ------------------------------------------------------------
#   Flat, unboxed iteration state for the Mandelbrot orbit.
#   Data-oriented: three primitives, no tag, no pointer.
# ------------------------------------------------------------
type MandelbrotIterationState:
  MandelbrotIterationState {
    zReal_inF24:            f24,
    zImag_inF24:            f24,
    iterationsCompleted:    u24
  }

# ------------------------------------------------------------
#   Palette: iteration count -> one ASCII glyph.
#   Inlined into the pixel function below; kept as a separate
#   name here only so LAWS.bend can refer to it symbolically.
# ------------------------------------------------------------
def mandelbrotEscapeCountAsAsciiCharacter(iterationCount_inIterations):
  match iterationCount_inIterations:
    case 0: return " "
    case 1: return "."
    case 2: return ","
    case 3: return ":"
    case 4: return ";"
    case 5: return "!"
    case 6: return "|"
    case 7: return "*"
    case 8: return "#"
    case 9: return "%"
    case _: return "@"

# ------------------------------------------------------------
#   MANDELBROT  --  one pixel, fully inlined.
#
#   Fuses into a single function body:
#     * complexPlane mapping        (from pixel coordinates)
#     * the z = z^2 + c iteration   (via bend + fork)
#     * the escape-time test        (|z|^2 > 4.0)
#     * the palette lookup          (inlined match)
# ------------------------------------------------------------
def renderMandelbrotPixelAsAsciiCharacter(
  pixelColumnIndex_inPixels,
  pixelRowIndex_inPixels
):
  let complexPlaneReal_inF24 =
    mandelbrotComplexPlaneMinimumReal()
      + mandelbrotComplexPlaneStepRealPerPixel() * (pixelColumnIndex_inPixels + 0.0)

  let complexPlaneImag_inF24 =
    mandelbrotComplexPlaneMinimumImag()
      + mandelbrotComplexPlaneStepImagPerPixel() * (pixelRowIndex_inPixels + 0.0)

  let initialIterationState = MandelbrotIterationState {
    zReal_inF24:        0.0,
    zImag_inF24:        0.0,
    iterationsCompleted: 0
  }

  bend iterationState = initialIterationState:
    when iterationState.iterationsCompleted < mandelbrotMaximumIterations():
      let zRealSquared_inF24 = iterationState.zReal_inF24 * iterationState.zReal_inF24
      let zImagSquared_inF24 = iterationState.zImag_inF24 * iterationState.zImag_inF24
      if zRealSquared_inF24 + zImagSquared_inF24 > 4.0:
        match iterationState.iterationsCompleted:
          case 0: return " "
          case 1: return "."
          case 2: return ","
          case 3: return ":"
          case 4: return ";"
          case 5: return "!"
          case 6: return "|"
          case 7: return "*"
          case 8: return "#"
          case 9: return "%"
          case _: return "@"
      else:
        let nextZReal_inF24 =
          zRealSquared_inF24 - zImagSquared_inF24 + complexPlaneReal_inF24
        let nextZImag_inF24 =
          2.0 * iterationState.zReal_inF24 * iterationState.zImag_inF24
            + complexPlaneImag_inF24
        let nextIterationState = MandelbrotIterationState {
          zReal_inF24:        nextZReal_inF24,
          zImag_inF24:        nextZImag_inF24,
          iterationsCompleted: iterationState.iterationsCompleted + 1
        }
        return fork(nextIterationState)
    else:
      return "@"

# ------------------------------------------------------------
#   One Mandelbrot row, accumulator style.
# ------------------------------------------------------------
def renderMandelbrotRowAsAsciiString(
  pixelRowIndex_inPixels,
  imageWidth_inPixels
):
  bend columnAccumulator = 0, stringAccumulator = "":
    when columnAccumulator < imageWidth_inPixels:
      let pixelColumnIndex_inPixels = columnAccumulator
      let pixelGlyphAsString = renderMandelbrotPixelAsAsciiCharacter(
        pixelColumnIndex_inPixels,
        pixelRowIndex_inPixels
      )
      return fork(
        columnAccumulator + 1,
        stringAccumulator + pixelGlyphAsString
      )
    else:
      return stringAccumulator + "\n"

# ------------------------------------------------------------
#   Full Mandelbrot image, one row per fork.
# ------------------------------------------------------------
def renderMandelbrotImageAsAsciiString(
  imageWidth_inPixels,
  imageHeight_inPixels
):
  bend rowAccumulator = 0, stringAccumulator = "":
    when rowAccumulator < imageHeight_inPixels:
      let pixelRowIndex_inPixels = rowAccumulator
      let rowAsAsciiString = renderMandelbrotRowAsAsciiString(
        pixelRowIndex_inPixels,
        imageWidth_inPixels
      )
      return fork(
        rowAccumulator + 1,
        stringAccumulator + rowAsAsciiString
      )
    else:
      return stringAccumulator

# ------------------------------------------------------------
#   SIERPINSKI  --  Lucas's theorem, one cell inlined.
#   C(n, k) mod 2 == 1  <=>  (k & n) == k.
# ------------------------------------------------------------
def renderSierpinskiCellAsAsciiCharacter(
  triangleColumnIndex_inU24,
  triangleRowIndex_inU24
):
  if (triangleColumnIndex_inU24 & triangleRowIndex_inU24)
       == triangleColumnIndex_inU24:
    return "*"
  else:
    return " "

def renderSierpinskiRowAsAsciiString(
  triangleRowIndex_inU24,
  triangleWidth_inCharacters
):
  bend columnAccumulator = 0, stringAccumulator = "":
    when columnAccumulator < triangleWidth_inCharacters:
      let triangleColumnIndex_inU24 = columnAccumulator
      let cellAsAsciiCharacter = renderSierpinskiCellAsAsciiCharacter(
        triangleColumnIndex_inU24,
        triangleRowIndex_inU24
      )
      return fork(
        columnAccumulator + 1,
        stringAccumulator + cellAsAsciiCharacter
      )
    else:
      return stringAccumulator + "\n"

def renderSierpinskiTriangleAsAsciiString(
  triangleHeight_inRows,
  triangleWidth_inCharacters
):
  bend rowAccumulator = 0, stringAccumulator = "":
    when rowAccumulator < triangleHeight_inRows:
      let triangleRowIndex_inU24 = rowAccumulator
      let rowAsAsciiString = renderSierpinskiRowAsAsciiString(
        triangleRowIndex_inU24,
        triangleWidth_inCharacters
      )
      return fork(
        rowAccumulator + 1,
        stringAccumulator + rowAsAsciiString
      )
    else:
      return stringAccumulator

# ------------------------------------------------------------
#   MAIN
# ------------------------------------------------------------
def main():
  let imageWidth_inPixels        = mandelbrotImageWidth_inPixels()
  let imageHeight_inPixels       = mandelbrotImageHeight_inPixels()
  let triangleHeight_inRows      = sierpinskiTriangleHeight_inRows()
  let triangleWidth_inCharacters = sierpinskiTriangleWidth_inCharacters()

  let headerAsAsciiString =
    "============================================================\n"
    + "  BEND PARALLEL PLAYGROUND v3\n"
    + "  Explicit names. Data-oriented. Law-verified.\n"
    + "============================================================\n\n"
    + "--- 1. Mandelbrot Set (inlined palette, hoisted scale) ---\n"

  let mandelbrotImageAsAsciiString = renderMandelbrotImageAsAsciiString(
    imageWidth_inPixels,
    imageHeight_inPixels
  )

  let separatorAsAsciiString =
    "\n--- 2. Sierpinski Triangle (inlined Lucas test) ---\n"

  let sierpinskiTriangleAsAsciiString = renderSierpinskiTriangleAsAsciiString(
    triangleHeight_inRows,
    triangleWidth_inCharacters
  )

  let footerAsAsciiString =
    "\n--- Done. Every row forked in parallel by HVM2 on WSL. ---\n"

  return headerAsAsciiString
    + mandelbrotImageAsAsciiString
    + separatorAsAsciiString
    + sierpinskiTriangleAsAsciiString
    + footerAsAsciiString
