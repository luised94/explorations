import Base
import ./playground.bend as Playground

# These claims stop at definitional boundaries because the supplied Base does
# not provide F32 algebraic laws sufficient to prove Mandelbrot-set membership.
law mandelbrot_zero_iterations_keep_prior_escape_status:
  for real_coordinate: F32
  for imaginary_coordinate: F32
  for current_real_component: F32
  for current_imaginary_component: F32
  for escaped_before_this_iteration: Bool
  {Playground.Mandelbrot.escape_status(
    0n,
    real_coordinate,
    imaginary_coordinate,
    current_real_component,
    current_imaginary_component,
    escaped_before_this_iteration
  ) == escaped_before_this_iteration : Bool}

law mandelbrot_unescaped_status_uses_ink_glyph:
  {Playground.Mandelbrot.glyph_for_escape_status(False{}) == "#" : String}

law mandelbrot_escaped_status_uses_blank_glyph:
  {Playground.Mandelbrot.glyph_for_escape_status(True{}) == " " : String}

law sierpinski_ink_status_uses_ink_glyph:
  {Playground.Sierpinski.glyph_for_ink(True{}) == "#" : String}

law sierpinski_blank_status_uses_blank_glyph:
  {Playground.Sierpinski.glyph_for_ink(False{}) == " " : String}
