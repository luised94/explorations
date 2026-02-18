#!/usr/bin/env python3
"""Demo script for terminal_output.py - executable documentation."""
import terminal_output

# ============================================================================
# Module Constants
# ============================================================================
print("=== Module Constants ===")
print(f"stderr is terminal: {terminal_output.STDERR_IS_TERMINAL}")
print(f"verbosity level: {terminal_output.VERBOSITY}")
print()

# ============================================================================
# set_layout() and emit() - Layout Config and Stdout Output
# ============================================================================
print("=== set_layout() and emit() ===")

terminal_output.set_layout(max_width=60, align="center")
print("set_layout(max_width=60, align='center') -- content capped at 60, centered in terminal")
print()

terminal_output.emit("This line is emitted via emit() -- centered in terminal.")
terminal_output.emit("Short line.")
terminal_output.emit("A slightly longer line to show block alignment.")
print()

multiline_content = "First line of emitted block.\nSecond line, same left edge.\nThird line."
print("Multi-line emit() -- all lines share identical left padding:")
terminal_output.emit(multiline_content)
print()

print("Resetting to defaults: set_layout(max_width=80, align='left')")
terminal_output.set_layout(max_width=80, align="left")
terminal_output.emit("With default layout, emit() behaves like print().")
print()

# ============================================================================
# get_terminal_width() - Cached Column Detection
# ============================================================================
print("=== get_terminal_width() ===")
detected_width = terminal_output.get_terminal_width()
print(f"Detected terminal width: {detected_width}")
print(f"Calling again (cached): {terminal_output.get_terminal_width()}")
print("(resize terminal, restart demo to see re-detection on fresh run)")
print()

# ============================================================================
# measure_width() - ANSI-Aware Visible Width
# ============================================================================
print("=== measure_width() ===")

plain_text = "hello"
styled_text = terminal_output.apply_style("hello", terminal_output.STYLE_BOLD)
plain_width = terminal_output.measure_width(plain_text)
styled_width = terminal_output.measure_width(styled_text)
print(f"Plain string 'hello':        measure_width = {plain_width}")
print(f"Bold styled 'hello':         measure_width = {styled_width}  (should match plain)")

dim_text = terminal_output.apply_style("world", terminal_output.STYLE_DIM)
cyan_text = terminal_output.apply_style("world", terminal_output.STYLE_CYAN)
print(f"Dim styled 'world':          measure_width = {terminal_output.measure_width(dim_text)}")
print(f"Cyan styled 'world':         measure_width = {terminal_output.measure_width(cyan_text)}")
print()

multiline_text = "short\nthis is longer"
multiline_width = terminal_output.measure_width(multiline_text)
print(f"Multi-line 'short\\nthis is longer': measure_width = {multiline_width}  (should be 14)")
print()

ansi_only = terminal_output.STYLE_BOLD + terminal_output.STYLE_RESET
ansi_only_width = terminal_output.measure_width(ansi_only)
print(f"String with only ANSI codes: measure_width = {ansi_only_width}  (should be 0)")

empty_width = terminal_output.measure_width("")
print(f"Empty string:                measure_width = {empty_width}  (should be 0)")
print()

# ============================================================================
# align_text() - Block Alignment Primitive
# ============================================================================
print("=== align_text() ===")

three_line_block = "short\na medium line\nthe longest line here"
print("Left-aligned in 80 chars (no change):")
print(terminal_output.align_text(three_line_block, "left", 80))
print()
print("Centered in 80 chars:")
print(terminal_output.align_text(three_line_block, "center", 80))
print()
print("Right-aligned in 80 chars:")
print(terminal_output.align_text(three_line_block, "right", 80))
print()

styled_block = (
    terminal_output.apply_style("bold line", terminal_output.STYLE_BOLD)
    + "\n"
    + terminal_output.apply_style("dim line, same visible length", terminal_output.STYLE_DIM)
)
print("Styled multi-line block centered in 80 chars (ANSI-aware padding):")
print(terminal_output.align_text(styled_block, "center", 80))
print()

wide_block = "this line is definitely wider than forty chars"
print("Block wider than target width (returned unchanged):")
print(terminal_output.align_text(wide_block, "center", 40))
print()

# ============================================================================
# apply_style() - Core Styling Primitive
# ============================================================================
print("=== apply_style() with STYLE_* constants ===")
print(f"Bold: {terminal_output.apply_style('important text', terminal_output.STYLE_BOLD)}")
print(f"Dim: {terminal_output.apply_style('secondary info', terminal_output.STYLE_DIM)}")
print(f"Red: {terminal_output.apply_style('error-like', terminal_output.STYLE_RED)}")
print(f"Yellow: {terminal_output.apply_style('warning-like', terminal_output.STYLE_YELLOW)}")
print(f"Cyan: {terminal_output.apply_style('info-like', terminal_output.STYLE_CYAN)}")
print(f"Gray: {terminal_output.apply_style('debug-like', terminal_output.STYLE_GRAY)}")
print(f"Green: {terminal_output.apply_style('success-like', terminal_output.STYLE_GREEN)}")
print(f"Bold yellow: {terminal_output.apply_style('highlighted', terminal_output.STYLE_BOLD_YELLOW)}")
print(f"No style: {terminal_output.apply_style('plain text', '')}")
print()

# ============================================================================
# format_highlight() - Semantic Highlighting
# ============================================================================
print("=== format_highlight() ===")
search_query = "neural"
result_text = "Understanding neural networks and neural architectures"
highlighted_result = result_text.replace("neural", terminal_output.format_highlight("neural"))
print(f"Search for '{search_query}':")
print(f"  {highlighted_result}")
print()

# ============================================================================
# format_label() - Structured Labels
# ============================================================================
print("=== format_label() ===")
print(f"{terminal_output.format_label('dry-run')} Showing preview only")
print(f"{terminal_output.format_label('model', 'claude-sonnet-4-20250514')}")
print(f"{terminal_output.format_label('tokens', '850 in / 320 out')}")
print()

# ============================================================================
# format_separator() - Separator Lines
# ============================================================================
print("=== format_separator() ===")
print(terminal_output.format_separator())
print(terminal_output.format_separator("=", 60))
print()

# ============================================================================
# format_token_counts() - Token Count Formatting
# ============================================================================
print("=== format_token_counts() ===")
print(f"Small: {terminal_output.format_token_counts(150, 80)}")
print(f"Medium: {terminal_output.format_token_counts(850, 320)}")
print(f"Large: {terminal_output.format_token_counts(4500, 1200)}")
print()

# ============================================================================
# format_cost() - Cost Formatting
# ============================================================================
print("=== format_cost() ===")
print(f"Tiny: {terminal_output.format_cost(0.0008)}")
print(f"Small: {terminal_output.format_cost(0.0032)}")
print(f"Medium: {terminal_output.format_cost(0.125)}")
print(f"Large: {terminal_output.format_cost(3.45)}")
print()

# ============================================================================
# format_block() - Block Formatting
# ============================================================================
print("=== format_block() ===")
simple_block = terminal_output.format_block("Simple Block", "This is the content inside the block.")
print(simple_block)
print()

api_request = "POST /v1/messages\nmodel: claude-sonnet-4-20250514\nmax_tokens: 1024"
print(terminal_output.format_block("API Request", api_request))
print()

tokens = terminal_output.format_token_counts(850, 320)
cost = terminal_output.format_cost(0.0032)
summary_content = f"Tokens: {tokens}\nCost: {cost}\nStatus: Success"
print(terminal_output.format_block("Request Summary", summary_content))
print()

config_lines = [
    terminal_output.format_label('model', 'sonnet'),
    terminal_output.format_label('temperature', '1.0'),
    terminal_output.format_label('max_tokens', '2048'),
]
print(terminal_output.format_block("Configuration", "\n".join(config_lines)))
print()

# ============================================================================
# format_choices() - User Selection Choices
# ============================================================================
print("=== format_choices() ===")

standard_choices: list[tuple[str, str]] = [("0", "failed"), ("1", "passed"), ("2", "easy")]

print("Horizontal (default):")
print(terminal_output.format_choices(standard_choices))
print()

print("Vertical (explicit):")
print(terminal_output.format_choices(standard_choices, layout="vertical"))
print()

print("Horizontal via emit() -- centered in terminal:")
terminal_output.set_layout(max_width=76, align="center")
terminal_output.emit(terminal_output.format_choices(standard_choices))
terminal_output.set_layout(max_width=80, align="left")
print()

long_label_choices: list[tuple[str, str]] = [
    ("1", "completely forgot"),
    ("2", "wrong but close"),
    ("3", "correct with effort"),
    ("4", "correct with hesitation"),
    ("5", "perfect recall"),
    ("6", "too easy to count"),
]
print("Auto-fallback: 6 long-label choices overflow horizontal -> vertical:")
print(terminal_output.format_choices(long_label_choices))
print()

print("Forced vertical for same choices:")
print(terminal_output.format_choices(long_label_choices, layout="vertical"))
print()

# ============================================================================
# format_duration() - Human-Readable Day Counts
# ============================================================================
print("=== format_duration() ===")

test_values: list[float] = [-3, 0, 1, 3, 6, 7, 10, 14, 21, 30, 45, 60, 90, 180, 365, 730]
for days in test_values:
    result = terminal_output.format_duration(days)
    print(f"  days={days:>5} -> {result}")
print()

print("Float input (round() applied before thresholds):")
print(f"  days=6.4  -> {terminal_output.format_duration(6.4)}")
print(f"  days=6.6  -> {terminal_output.format_duration(6.6)}")
print(f"  days=13.5 -> {terminal_output.format_duration(13.5)}")
print()

print("Styled usage example:")
styled_duration = terminal_output.apply_style(
    terminal_output.format_duration(6.0),
    terminal_output.STYLE_BOLD
)
print(f"  Next review in {styled_duration}")
print()

# ============================================================================
# wrap_text() - Text Wrapping
# ============================================================================
print("=== wrap_text() ===")
long_text = "This is a very long line of text that will definitely exceed the typical terminal width and needs to be wrapped to multiple lines for readability. It demonstrates how the wrap_text function handles text that is too long for a single line."
print("Wrapped to 60 chars:")
print(terminal_output.wrap_text(long_text, width=60))
print()
print("Wrapped to 60 chars with 4-space indent:")
print(terminal_output.wrap_text(long_text, indent=4, width=60))
print()

multi_paragraph = "First paragraph is here and it is quite long so it will wrap.\n\nSecond paragraph is also long and will wrap independently of the first paragraph."
print("Multi-paragraph wrapped to 50 chars:")
print(terminal_output.wrap_text(multi_paragraph, width=50))
print()

# ============================================================================
# set_verbosity() - Module Configuration
# ============================================================================
print("=== set_verbosity() ===")
print(f"Current verbosity: {terminal_output.VERBOSITY}")
terminal_output.set_verbosity(4)
print(f"After set_verbosity(4): {terminal_output.VERBOSITY}")
terminal_output.set_verbosity(3)
print(f"Reset to default: {terminal_output.VERBOSITY}")
print()

# ============================================================================
# Messaging Functions - Default Verbosity (3)
# ============================================================================
print("=== Messaging at default verbosity (3) ===")
print("(messages go to stderr)")
terminal_output.msg_error("API call failed: rate limited")
terminal_output.msg_warn("Approaching monthly budget limit")
terminal_output.msg_info("Model: claude-sonnet-4-20250514")
terminal_output.msg_debug("Full context: 4832 characters")
terminal_output.msg_success("Response received, 320 tokens")
print("(debug suppressed - verbosity 3 < debug priority 4)")
print()

# ============================================================================
# Messaging Functions - Verbosity 4 (adds debug)
# ============================================================================
print("=== Messaging at verbosity 4 (adds debug) ===")
terminal_output.set_verbosity(4)
terminal_output.msg_error("API call failed: rate limited")
terminal_output.msg_warn("Approaching monthly budget limit")
terminal_output.msg_info("Model: claude-sonnet-4-20250514")
terminal_output.msg_debug("Full context: 4832 characters")
terminal_output.msg_success("Response received, 320 tokens")
print("(all five messages visible)")
print()

# ============================================================================
# Messaging Functions - Verbosity 1 (error only)
# ============================================================================
print("=== Messaging at verbosity 1 (error only) ===")
terminal_output.set_verbosity(1)
terminal_output.msg_error("API call failed: rate limited")
terminal_output.msg_warn("This warn is suppressed")
terminal_output.msg_info("This info is suppressed")
terminal_output.msg_debug("This debug is suppressed")
terminal_output.msg_success("This success is suppressed")
print("(only error shown)")
print()

# ============================================================================
# Messaging Functions - Verbosity 0 (silent)
# ============================================================================
print("=== Messaging at verbosity 0 (silent) ===")
terminal_output.set_verbosity(0)
terminal_output.msg_error("This error is suppressed")
terminal_output.msg_warn("This warn is suppressed")
terminal_output.msg_info("This info is suppressed")
print("(nothing on stderr)")
print()

# ============================================================================
# Messaging Functions - Verbosity 5 (trace)
# ============================================================================
print("=== Messaging at verbosity 5 (trace) ===")
terminal_output.set_verbosity(5)
terminal_output.msg_info("Trace mode shows caller function name")
terminal_output.msg_debug("Useful for debugging message origins")
print()

# ============================================================================
# Messaging Functions - Empty Message Guard
# ============================================================================
print("=== Empty message guard ===")
terminal_output.set_verbosity(3)
terminal_output.msg_info("")
terminal_output.msg_info("   ")
print("(two warnings about empty messages)")
print()

# Reset verbosity for any subsequent use
terminal_output.set_verbosity(3)
