"""Terminal output utility - styling and messaging for CLI scripts.

Architecture (four layers):

  CONFIG LAYER
    set_verbosity(level)       -- filter msg_* output
    set_layout(max_width, align) -- content width and alignment (commit 03)

  PRIMITIVE LAYER  (pure functions, no I/O)
    get_terminal_width()       -- cached column detection, default 80
    measure_width(text)        -- ANSI-aware visible character count
    align_text(text, align, width) -- block alignment (commit 02)

  STYLING LAYER  (pure functions, return strings, no I/O)
    apply_style(text, style_code)
    format_highlight(text)
    format_label(name, value)
    format_separator(character, width)
    format_token_counts(tokens_in, tokens_out)
    format_cost(cost_dollars)
    format_block(header, content)
    wrap_text(text, indent, width)

  OUTPUT LAYER  (write to stderr unless noted)
    msg_error(message)
    msg_warn(message)
    msg_info(message)
    msg_debug(message)
    msg_success(message)

All messaging goes to stderr. Data output goes to stdout (caller's responsibility).
"""
import os
import re
import sys
import textwrap

# ============================================================================
# Section 1: Constants (determined at module import)
# ============================================================================

STDERR_IS_TERMINAL: bool = sys.stderr.isatty()

VERBOSITY: int = 3  # default: show error, warn, info

# ANSI escape codes (empty strings if stderr is not a terminal)
STYLE_RESET: str      = "\033[0m"    if STDERR_IS_TERMINAL else ""
STYLE_BOLD: str       = "\033[1m"    if STDERR_IS_TERMINAL else ""
STYLE_DIM: str        = "\033[2m"    if STDERR_IS_TERMINAL else ""
STYLE_RED: str        = "\033[31m"   if STDERR_IS_TERMINAL else ""
STYLE_YELLOW: str     = "\033[33m"   if STDERR_IS_TERMINAL else ""
STYLE_CYAN: str       = "\033[36m"   if STDERR_IS_TERMINAL else ""
STYLE_GRAY: str       = "\033[90m"   if STDERR_IS_TERMINAL else ""
STYLE_GREEN: str      = "\033[32m"   if STDERR_IS_TERMINAL else ""
STYLE_BOLD_YELLOW: str = "\033[1;33m" if STDERR_IS_TERMINAL else ""

# ============================================================================
# Section 2: Module Configuration
# ============================================================================

_layout_max_width: int = 80
_layout_align: str = "left"


def set_layout(max_width: int = 80, align: str = "left") -> None:
    """Set content width and alignment for all output functions.

    Establishes the two-width model: content is constrained to max_width,
    then positioned within the full terminal width via align_text.

    max_width is clamped to (terminal_width - 4) on narrow terminals to
    prevent content touching terminal edges. If the terminal is narrower
    than max_width, content fills the terminal (padding = 0).

    If set_layout() is never called, defaults are max_width=80 and
    align="left" -- identical to previous module behavior.

    Args:
        max_width: Maximum content width in characters (default: 80).
        align: "left", "center", or "right" (default: "left").
    """
    global _layout_max_width, _layout_align
    terminal_width: int = get_terminal_width()
    if terminal_width > max_width:
        _layout_max_width = min(max_width, terminal_width - 4)
    else:
        _layout_max_width = terminal_width
    _layout_align = align


def _get_max_width() -> int:
    return _layout_max_width


def _get_align() -> str:
    return _layout_align


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
# Section 3: Primitive Layer
# ============================================================================

_cached_terminal_width: int | None = None

_ANSI_PATTERN: re.Pattern = re.compile(r'\033\[[0-9;]*m')

def get_terminal_width() -> int:
    """Return terminal column count, cached after first call.

    Detects once via os.get_terminal_size(). Falls back to 80 if detection
    fails (piped output, non-terminal environments).

    Returns:
        Integer column count.
    """
    global _cached_terminal_width
    if _cached_terminal_width is None:
        try:
            _cached_terminal_width = os.get_terminal_size().columns
        except OSError:
            _cached_terminal_width = 80
    return _cached_terminal_width


def measure_width(text: str) -> int:
    """Return visible character count, ignoring ANSI SGR escape sequences.

    Strips all ANSI color/style codes before measuring. For multi-line
    input, returns the width of the longest line.

    Constraints:
        - ASCII and Latin-1 only. No CJK double-width character support.
        - Empty string returns 0.
        - String with only ANSI codes returns 0.

    Args:
        text: String, possibly containing ANSI escape codes and newlines.

    Returns:
        Visible character width as integer.
    """
    stripped: str = _ANSI_PATTERN.sub('', text)
    if '\n' not in stripped:
        return len(stripped)
    lines: list[str] = stripped.split('\n')
    maximum_width: int = 0
    for line in lines:
        line_width: int = len(line)
        if line_width > maximum_width:
            maximum_width = line_width
    return maximum_width

def align_text(text: str, align: str = "left", width: int | None = None) -> str:
    """Position a text block within a target width by prepending spaces.

    Computes padding from the widest line and applies it uniformly to all
    lines (block alignment). This preserves internal relative alignment.

    Does NOT right-pad. Trailing spaces cause wrapping artifacts and
    interfere with copy-paste.

    Args:
        text: Input string, may contain ANSI codes, may be multi-line.
        align: "left" (no-op), "center", or "right".
        width: Target width in characters. Defaults to get_terminal_width().

    Returns:
        Text with uniform left padding applied, or original text unchanged
        if align is "left", width <= 0, or content fills/overflows width.
    """
    if align == "left":
        return text
    if width is None:
        width = get_terminal_width()
    if width <= 0:
        return text
    lines: list[str] = text.split("\n")
    maximum_width: int = 0
    for line in lines:
        line_visible_width: int = measure_width(line)
        if line_visible_width > maximum_width:
            maximum_width = line_visible_width
    if maximum_width >= width:
        return text
    if align == "center":
        padding: int = (width - maximum_width) // 2
    elif align == "right":
        padding = width - maximum_width
    else:
        return text
    prefix: str = " " * padding
    padded_lines: list[str] = []
    for line in lines:
        padded_lines.append(prefix + line)
    return "\n".join(padded_lines)


# ============================================================================
# Section 4: Styling Functions (pure - no I/O)
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
        width: Line width (default: terminal width)

    Returns:
        Dim-styled line of repeated characters
    """
    if width is None:
        width = get_terminal_width()
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


def format_duration(days: float) -> str:
    """Convert a numeric day count to a human-readable relative duration.

    Threshold evaluation is top-to-bottom, first match wins. Input is
    float because scheduling algorithms produce float intervals; round()
    is applied immediately before threshold checks.

    Returns plain string with no styling. Caller applies styling as needed.

    Args:
        days: Number of days as float (may be negative for overdue items).

    Returns:
        Human-readable string: "overdue", "today", "tomorrow", "6 days",
        "1 week", "3 months", "2 years", etc.
    """
    day_count: int = round(days)
    if day_count < 0:
        return "overdue"
    if day_count == 0:
        return "today"
    if day_count == 1:
        return "tomorrow"
    if day_count < 7:
        return str(day_count) + " days"
    if day_count < 14:
        return "1 week"
    if day_count < 30:
        week_count: int = round(day_count / 7)
        return str(week_count) + " weeks"
    if day_count < 60:
        return "1 month"
    if day_count < 365:
        month_count: int = round(day_count / 30)
        if month_count == 1:
            return "1 month"
        return str(month_count) + " months"
    year_count: int = round(day_count / 365)
    if year_count == 1:
        return "1 year"
    return str(year_count) + " years"


def wrap_text(text: str, indent: int = 0, width: int | None = None) -> str:
    """Wrap text to specified width with optional indentation.

    Preserves existing paragraph breaks (double newlines).
    Each paragraph is wrapped independently and rejoined.

    Args:
        text: Text to wrap (may contain newlines)
        indent: Number of spaces to indent wrapped lines (default: 0)
        width: Maximum line width (default: terminal width)

    Returns:
        Wrapped text as single string with newlines

    Example:
        wrap_text("This is a very long line that needs wrapping", indent=2, width=20)
        produces lines indented by 2 spaces, max 20 chars wide
    """
    if width is None:
        width = get_terminal_width()
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
# Section 5: Output Functions (perform I/O)
# ============================================================================

def emit(text: str) -> None:
    """Write layout-aware content to stdout.

    Applies alignment from set_layout() before printing. Use this for all
    formatted content (cards, choices, etc.). Use plain print() only for
    raw piped data where layout should not be applied.

    Does not filter by verbosity -- content output is unconditional.

    Args:
        text: String to emit, may be multi-line, may contain ANSI codes.
    """
    aligned: str = align_text(text, align=_get_align(), width=get_terminal_width())
    print(aligned)

# ============================================================================
# Section 6: Messaging Functions (write to stderr)
# ============================================================================

def _write_message(level: str, priority: int, style_code: str, message: str) -> None:
    """Write a styled, leveled message to stderr.

    This is the core messaging primitive. All public msg_* functions call this.

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
    _write_message("ERROR", 1, STYLE_RED, message)


def msg_warn(message: str) -> None:
    """Write a warning message to stderr. Shown at verbosity >= 2."""
    _write_message("WARN", 2, STYLE_YELLOW, message)


def msg_info(message: str) -> None:
    """Write an info message to stderr. Shown at verbosity >= 3."""
    _write_message("INFO", 3, STYLE_CYAN, message)


def msg_debug(message: str) -> None:
    """Write a debug message to stderr. Shown at verbosity >= 4."""
    _write_message("DEBUG", 4, STYLE_GRAY, message)


def msg_success(message: str) -> None:
    """Write a success message to stderr. Shown at verbosity >= 3.

    Same priority as info - informational, just styled differently.
    """
    _write_message("OK", 3, STYLE_GREEN, message)
