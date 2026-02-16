"""Terminal output utility - styling and messaging for CLI scripts.

Two layers:
1. Styling functions - pure transforms, no I/O
2. Messaging functions - write leveled output to stderr

All messaging goes to stderr. Data output goes to stdout (caller's responsibility).
"""

import sys
import shutil
import textwrap


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
# Section 2: Module Configuration
# ============================================================================

def set_verbosity(level: int) -> None:
    """Set the module-level verbosity threshold.

    This is the only function that mutates module state. Called once at
    script startup, typically from a --verbose / --quiet CLI flag.

    Verbosity levels:
        0 = silent (nothing)
        1 = error only
        2 = error + warn
        3 = error + warn + info (default)
        4 = error + warn + info + debug
        5 = all + trace (includes caller function name)

    Args:
        level: Integer 0-5
    """
    global VERBOSITY
    VERBOSITY = level


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


def format_block(header: str, content: str) -> str:
    """Format a block with header and bordered content.

    Builds multi-line output with styled separators and header.
    Returns a single string with embedded newlines.

    Args:
        header: Block header text
        content: Block content (may contain multiple lines)

    Returns:
        Multi-line string with format:
        --- header ---
        content
        --------------

    Example:
        format_block("API Request", "POST /messages\\nmodel: sonnet")
        produces:
        --- API Request ---
        POST /messages
        model: sonnet
        -------------------
    """
    header_separator = apply_style(f"--- {header} ---", STYLE_DIM)
    header_length = len(f"--- {header} ---")
    footer_separator = apply_style("-" * header_length, STYLE_DIM)
    lines = [header_separator, content, footer_separator]
    return "\n".join(lines)


def wrap_text(text: str, indent: int = 0, width: int | None = None) -> str:
    """Wrap text to specified width with optional indentation.

    Preserves existing paragraph breaks (double newlines).
    Each paragraph is wrapped independently and rejoined.

    Args:
        text: Text to wrap (may contain newlines)
        indent: Number of spaces to indent wrapped lines (default: 0)
        width: Maximum line width (default: TERMINAL_WIDTH)

    Returns:
        Wrapped text as single string with newlines

    Example:
        wrap_text("This is a very long line that needs wrapping", indent=2, width=20)
        produces lines indented by 2 spaces, max 20 chars wide
    """
    if width is None:
        width = TERMINAL_WIDTH
    effective_width = width - indent
    if effective_width <= 0:
        effective_width = 1

    paragraphs = text.split("\n")
    wrapped_paragraphs = []
    for paragraph in paragraphs:
        if paragraph.strip() == "":
            wrapped_paragraphs.append("")
        else:
            wrapped = textwrap.fill(
                paragraph,
                width=effective_width,
                initial_indent=" " * indent,
                subsequent_indent=" " * indent
            )
            wrapped_paragraphs.append(wrapped)
    return "\n".join(wrapped_paragraphs)


# ============================================================================
# Section 4: Messaging Functions (write to stderr)
# ============================================================================

def _write_message(level: str, priority: int, style_code: str, message: str) -> None:
    """Write a styled, leveled message to stderr.

    This is the core messaging primitive - the Python equivalent of the
    bash _msg function. All public msg_* functions call this.

    Logic:
        1. Suppress if current VERBOSITY < priority
        2. Warn and return if message is empty
        3. At VERBOSITY >= 5, prepend caller function name (trace)
        4. Format: [LEVEL] {trace}{message}
        5. Write to stderr

    Args:
        level: Display label ("ERROR", "WARN", "INFO", "DEBUG", "OK")
        priority: Numeric threshold (1=error, 2=warn, 3=info, 4=debug)
        style_code: ANSI style constant for the entire line
        message: Text to display
    """
    if VERBOSITY < priority:
        return

    if not message or message.isspace():
        sys.stderr.write(
            f"{STYLE_YELLOW}[WARN ] empty message passed to _write_message{STYLE_RESET}\n"
        )
        return

    trace_prefix = ""
    if VERBOSITY >= 5:
        caller_name = sys._getframe(2).f_code.co_name
        trace_prefix = f"({caller_name}) "

    formatted_line = f"{style_code}[{level:<5}] {trace_prefix}{message}{STYLE_RESET}\n"
    sys.stderr.write(formatted_line)


def msg_error(message: str) -> None:
    """Write an error message to stderr. Shown at verbosity >= 1."""
    level_config = MESSAGE_LEVELS["ERROR"]
    _write_message("ERROR", level_config["priority"], level_config["style"], message)


def msg_warn(message: str) -> None:
    """Write a warning message to stderr. Shown at verbosity >= 2."""
    level_config = MESSAGE_LEVELS["WARN"]
    _write_message("WARN", level_config["priority"], level_config["style"], message)


def msg_info(message: str) -> None:
    """Write an info message to stderr. Shown at verbosity >= 3."""
    level_config = MESSAGE_LEVELS["INFO"]
    _write_message("INFO", level_config["priority"], level_config["style"], message)


def msg_debug(message: str) -> None:
    """Write a debug message to stderr. Shown at verbosity >= 4."""
    level_config = MESSAGE_LEVELS["DEBUG"]
    _write_message("DEBUG", level_config["priority"], level_config["style"], message)


def msg_success(message: str) -> None:
    """Write a success message to stderr. Shown at verbosity >= 3.

    Not in the bash system but useful for the workbench.
    Same priority as info - informational, just styled differently.
    """
    _write_message("OK", 3, STYLE_GREEN, message)
