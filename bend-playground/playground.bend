import Base

# ============================================================
#   BEND PARALLEL PLAYGROUND  (Bend 2, WSL / CPU)
#   Mandelbrot + Sierpinski.
#   Parallelism via `a b = f(x) g(y)` parallel calls.
#   Termination via a Nat "fuel" argument counted down by match.
# ============================================================

# ---------- Configuration (kept as U32 / Nat values) ----------

def image_width() -> U32:
  80

def image_height() -> U32:
  40

def image_width_nat() -> Nat:
  80n

def image_height_nat() -> Nat:
  40n

def max_iterations() -> Nat:
  60n

def plane_min_real() -> F32:
  -2.0

def plane_max_real() -> F32:
  0.5

def plane_min_imag() -> F32:
  -1.25

def plane_max_imag() -> F32:
  1.25

def triangle_rows_nat() -> Nat:
  30n

def triangle_cols_nat() -> Nat:
  60n

# ---------- Palette: iteration count -> one ASCII glyph ----------
# Matched on Nat literals. The wildcard `_` is the default.

def palette(iteration: Nat) -> String:
  match iteration:
    case 0n: " "
    case 1n: "."
    case 2n: ","
    case 3n: ":"
    case 4n: ";"
    case 5n: "!"
    case 6n: "|"
    case 7n: "*"
    case 8n: "#"
    case 9n: "%"
    case _:  "@"

# ---------- Mandelbrot: one pixel ----------
# Coordinates come in as U32; the fuel is a Nat so the
# termination checker sees a structurally smaller argument.

def mandelbrot_pixel(column: U32, row: U32) -> String:
  palette(mandelbrot_orbit(max_iterations(), 0n, 0.0, 0.0,
                           mapped_real(column), mapped_imag(row)))

def mapped_real(column: U32) -> F32:
  let w = U32.to_f32(image_width())
  let c = U32.to_f32(column)
  (plane_min_real()
    + (plane_max_real() - plane_min_real()) * c / w : F32)

def mapped_imag(row: U32) -> F32:
  let h = U32.to_f32(image_height())
  let r = U32.to_f32(row)
  (plane_min_imag()
    + (plane_max_imag() - plane_min_imag()) * r / h : F32)

# -- The orbit. Fuel is the decreasing Nat; everything else is free. --
# We cannot `match` on a computed Bool, so the escape test is passed
# to `orbit_decide`, which matches on it as a parameter.

def mandelbrot_orbit(fuel: Nat, count: Nat,
                     zr: F32, zi: F32, cr: F32, ci: F32) -> Nat:
  match fuel:
    case 0n:
      count
    case 1n+p:
      let mag_sq = (zr * zr + zi * zi : F32)
      orbit_decide(p, count, zr, zi, cr, ci, F32.is_gt(mag_sq, 4.0))

def orbit_decide(fuel: Nat, count: Nat,
                 zr: F32, zi: F32, cr: F32, ci: F32,
                 has_escaped: Bool) -> Nat:
  match has_escaped:
    case True{}:
      count
    case False{}:
      let next_zr = (zr * zr - zi * zi + cr : F32)
      let next_zi = (2.0 * zr * zi + ci : F32)
      mandelbrot_orbit(fuel, Nat.add(count, 1n), next_zr, next_zi, cr, ci)

# ---------- Mandelbrot: one row, parallel over columns ----------
# `+row` and `+col` because the parallel call uses each twice.

def render_mandelbrot_row(+row: U32, cols_left: Nat, +col: U32) -> String:
  match cols_left:
    case 0n:
      "\n"
    case 1n+p:
      let ch rest = mandelbrot_pixel(col, row)
                    render_mandelbrot_row(row, p, U32.add(col, 1))
      ch ++ rest

# ---------- Mandelbrot: whole image, parallel over rows ----------

def render_mandelbrot(rows_left: Nat, +row: U32) -> String:
  match rows_left:
    case 0n:
      ""
    case 1n+p:
      let this rest = render_mandelbrot_row(row, image_width_nat(), 0)
                       render_mandelbrot(p, U32.add(row, 1))
      this ++ rest

# ---------- Sierpinski: one cell ----------
# Lucas's theorem: C(n,k) mod 2 == 1  <=>  (k & n) == k.
# The Bool result is passed to a helper that matches on it.

def sierpinski_cell(col: U32, row: U32) -> String:
  sierpinski_cell_decide(U32.is_eq(U32.and(col, row), col))

def sierpinski_cell_decide(is_filled: Bool) -> String:
  match is_filled:
    case True{}:  "*"
    case False{}: " "

# ---------- Sierpinski: one row, parallel over columns ----------

def render_sierpinski_row(+row: U32, cols_left: Nat, +col: U32) -> String:
  match cols_left:
    case 0n:
      "\n"
    case 1n+p:
      let ch rest = sierpinski_cell(col, row)
                    render_sierpinski_row(row, p, U32.add(col, 1))
      ch ++ rest

# ---------- Sierpinski: whole triangle, parallel over rows ----------

def render_sierpinski(rows_left: Nat, +row: U32) -> String:
  match rows_left:
    case 0n:
      ""
    case 1n+p:
      let this rest = render_sierpinski_row(row, triangle_cols_nat(), 0)
                       render_sierpinski(p, U32.add(row, 1))
      this ++ rest

# ---------- Main ----------

def header() -> String:
  "============================================================\n"
  ++ "  BEND PARALLEL PLAYGROUND  (Bend 2, WSL / CPU)\n"
  ++ "============================================================\n\n"
  ++ "--- 1. Mandelbrot Set ---\n"

def separator() -> String:
  "\n--- 2. Sierpinski Triangle ---\n"

def footer() -> String:
  "\n--- Done. Rows and columns forked via parallel calls. ---\n"

def render_everything() -> String:
  header()
  ++ render_mandelbrot(image_height_nat(), 0)
  ++ separator()
  ++ render_sierpinski(triangle_rows_nat(), 0)
  ++ footer()

def main() -> IO(Unit):
  do IO<Unit>:
    IO.print(render_everything())
    return Unit{}
