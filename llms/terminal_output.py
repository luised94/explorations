import sys
import shutil

# ============================================================================
# Section 1: Constants (determined at module import)
# ============================================================================

STDERR_IS_TERMINAL: bool = sys.stderr.isatty()
TERMINAL_WIDTH: int = shutil.get_terminal_size().columns if STDERR_IS_TERMINAL else 80
VERBOSITY: int = 3  # default: show error, warn, info


# ANSI escape codes (empty strings if stderr is not a terminal)
STYLE_RESET: str = "\033[0m" if STDERR_IS_TERMINAL else ""
STYLE_BOLD: str = "\033[1m" if STDERR_IS_TERMINAL else ""
STYLE_DIM: str = "\033[2m" if STDERR_IS_TERMINAL else ""
STYLE_RED: str = "\033[31m" if STDERR_IS_TERMINAL else ""
STYLE_YELLOW: str = "\033[33m" if STDERR_IS_TERMINAL else ""
STYLE_CYAN: str = "\033[36m" if STDERR_IS_TERMINAL else ""
STYLE_GRAY: str = "\033[90m" if STDERR_IS_TERMINAL else ""
STYLE_GREEN: str = "\033[32m" if STDERR_IS_TERMINAL else ""
STYLE_BOLD_YELLOW: str = "\033[1;33m" if STDERR_IS_TERMINAL else ""


# Level-to-style mapping
MESSAGE_LEVELS: dict[str, dict[str, int | str]] = {
    "ERROR": {"priority": 1, "style": STYLE_RED},
    "WARN": {"priority": 2, "style": STYLE_YELLOW},
    "INFO": {"priority": 3, "style": STYLE_CYAN},
    "DEBUG": {"priority": 4, "style": STYLE_GRAY},
}


# ============================================================================
# Section 3: Styling Functions (pure - no I/O)
# ============================================================================

def apply_style(text: str, style_code: str) -> str:
    """Apply an ANSI style code to text.
    
    This is the only function that concatenates ANSI codes.
    All other styling functions call this.
    
    Args:
        text: Plain string to style
        style_code: One of the STYLE_* constants
        
    Returns:
        Styled string if style_code is non-empty, otherwise plain text
    """
    if not style_code:
        return text
    return f"{style_code}{text}{STYLE_RESET}"
