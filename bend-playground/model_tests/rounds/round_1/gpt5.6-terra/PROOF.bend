import Base
import ./LAWS.bend as Laws

# Each claim unfolds a single match branch, so reflexivity is sufficient.
def Laws.mandelbrot_zero_iterations_keep_prior_escape_status(
  real_coordinate,
  imaginary_coordinate,
  current_real_component,
  current_imaginary_component,
  escaped_before_this_iteration
):
  {==}

def Laws.mandelbrot_unescaped_status_uses_ink_glyph():
  {==}

def Laws.mandelbrot_escaped_status_uses_blank_glyph():
  {==}

def Laws.sierpinski_ink_status_uses_ink_glyph():
  {==}

def Laws.sierpinski_blank_status_uses_blank_glyph():
  {==}
