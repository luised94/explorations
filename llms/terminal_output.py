"""Terminal output utility - styling and messaging for CLI scripts.

Two layers:
1. Styling functions - pure transforms, no I/O
2. Messaging functions - write leveled output to stderr

All messaging goes to stderr. Data output goes to stdout (caller's responsibility).
"""

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


def format_highlight(text: str) -> str:
    """Format text as a highlight (bold yellow).
    
    Semantic function - encodes the meaning "this is highlighted content"
    rather than just "make this bold yellow". Primary use: FTS search
    match highlighting.
    
    Args:
        text: Plain string to highlight
        
    Returns:
        Highlighted string (or plain if terminal styling disabled)
    """
    return apply_style(text, STYLE_BOLD_YELLOW)


def format_label(name: str, value: str | None = None) -> str:
    """Format a bracketed label with optional value.
    
    Builds structured label syntax used throughout CLI output.
    
    Args:
        name: Label name (e.g., "dry-run", "model")
        value: Optional value to display after colon
        
    Returns:
        "[name]" or "[name: value]", styled in cyan
        
    Examples:
        format_label("dry-run") -> "[dry-run]"
        format_label("model", "sonnet") -> "[model: sonnet]"
    """
    if value is None:
        label_text = f"[{name}]"
    else:
        label_text = f"[{name}: {value}]"
    return apply_style(label_text, STYLE_CYAN)


def format_separator(character: str = "-", width: int | None = None) -> str:
    """Generate a separator line of repeated characters.
    
    Args:
        character: Single character to repeat (default: "-")
        width: Line width (default: TERMINAL_WIDTH)
        
    Returns:
        Dim-styled line of repeated characters
    """
    if width is None:
        width = TERMINAL_WIDTH
    separator_line = character * width
    return apply_style(separator_line, STYLE_DIM)


def format_token_counts(tokens_in: int, tokens_out: int) -> str:
    """Format token input/output counts with total.
    
    Produces standard token count display format used in API call reporting.
    No styling applied - caller decides context.
    
    Args:
        tokens_in: Input token count
        tokens_out: Output token count
        
    Returns:
        Formatted string: "850 in / 320 out (1170 total)"
    """
    total_tokens = tokens_in + tokens_out
    return f"{tokens_in} in / {tokens_out} out ({total_tokens} total)"


def format_cost(cost_dollars: float) -> str:
    """Format monetary cost with appropriate precision.
    
    Uses precision based on magnitude to keep small costs readable:
    - Under $0.01: 4 decimal places
    - Under $1.00: 3 decimal places
    - Otherwise: 2 decimal places
    
    No styling applied - caller decides context.
    
    Args:
        cost_dollars: Cost in dollars
        
    Returns:
        Formatted cost string: "$0.0032", "$0.032", "$1.24"
    """
    if cost_dollars < 0.01:
        return f"${cost_dollars:.4f}"
    elif cost_dollars < 1.00:
        return f"${cost_dollars:.3f}"
    else:
        return f"${cost_dollars:.2f}"
