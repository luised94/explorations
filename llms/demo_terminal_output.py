#!/usr/bin/env python3
"""Demo script for terminal_output.py - executable documentation.

Sections:
    1. Config
    2. Primitives
    3. Existing styling functions
    4. New styling functions
    5. Output functions
    6. Integration scene (mock review session)
    7. Edge cases
"""
import time
import terminal_output

# ============================================================================
# Section 1: Config
# ============================================================================
print("=== SECTION 1: Config ===")
print()

print("--- set_verbosity() ---")
print(f"Default verbosity: {terminal_output.VERBOSITY}")
terminal_output.set_verbosity(4)
print(f"After set_verbosity(4): {terminal_output.VERBOSITY}")
terminal_output.set_verbosity(3)
print(f"Reset to default: {terminal_output.VERBOSITY}")
print()

print("--- set_layout(): left-aligned (default) ---")
terminal_output.set_layout(max_width=60, align="left")
terminal_output.emit("Left-aligned content at max_width=60.")
terminal_output.emit("Second line, same left edge.")
print()

print("--- set_layout(): centered ---")
terminal_output.set_layout(max_width=60, align="center")
terminal_output.emit("Centered content at max_width=60.")
terminal_output.emit("Second line, same left edge.")
print()

terminal_output.set_layout(max_width=80, align="left")
print("(Layout reset to defaults: max_width=80, align='left')")
print()

# ============================================================================
# Section 2: Primitives
# ============================================================================
print("=== SECTION 2: Primitives ===")
print()

print("--- get_terminal_width() ---")
detected_width = terminal_output.get_terminal_width()
print(f"Detected terminal width: {detected_width}")
print(f"Second call (cached):    {terminal_output.get_terminal_width()}")
print()

print("--- measure_width() ---")
plain_text = "hello"
bold_text = terminal_output.apply_style("hello", terminal_output.STYLE_BOLD)
dim_text = terminal_output.apply_style("hello", terminal_output.STYLE_DIM)
cyan_text = terminal_output.apply_style("hello", terminal_output.STYLE_CYAN)
print(f"Plain 'hello':                      {terminal_output.measure_width(plain_text)}  (expect 5)")
print(f"Bold styled 'hello':                {terminal_output.measure_width(bold_text)}  (expect 5)")
print(f"Dim styled 'hello':                 {terminal_output.measure_width(dim_text)}  (expect 5)")
print(f"Cyan styled 'hello':                {terminal_output.measure_width(cyan_text)}  (expect 5)")
print(f"Multi-line 'short\\nthis is longer': {terminal_output.measure_width('short' + chr(10) + 'this is longer')}  (expect 14)")
print(f"ANSI-only string:                   {terminal_output.measure_width(terminal_output.STYLE_BOLD + terminal_output.STYLE_RESET)}  (expect 0)")
print(f"Empty string:                       {terminal_output.measure_width('')}  (expect 0)")
print()

print("--- align_text() ---")
block = "short\na medium line\nthe longest line here"
print("Left (no-op):")
print(terminal_output.align_text(block, "left", 80))
print()
print("Center in 80 chars:")
print(terminal_output.align_text(block, "center", 80))
print()
print("Right in 80 chars:")
print(terminal_output.align_text(block, "right", 80))
print()
styled_block = (
    terminal_output.apply_style("bold line", terminal_output.STYLE_BOLD)
    + "\n"
    + terminal_output.apply_style("dim line, same visible length", terminal_output.STYLE_DIM)
)
print("Styled multi-line centered (ANSI-aware padding):")
print(terminal_output.align_text(styled_block, "center", 80))
print()
print("Block wider than target (returned unchanged):")
print(terminal_output.align_text("this line is definitely wider than forty chars", "center", 40))
print()

# ============================================================================
# Section 3: Existing Styling Functions
# ============================================================================
print("=== SECTION 3: Existing Styling Functions ===")
print()

print("--- apply_style() ---")
print(f"STYLE_BOLD:        {terminal_output.apply_style('important text', terminal_output.STYLE_BOLD)}")
print(f"STYLE_DIM:         {terminal_output.apply_style('secondary info', terminal_output.STYLE_DIM)}")
print(f"STYLE_RED:         {terminal_output.apply_style('error-like', terminal_output.STYLE_RED)}")
print(f"STYLE_YELLOW:      {terminal_output.apply_style('warning-like', terminal_output.STYLE_YELLOW)}")
print(f"STYLE_CYAN:        {terminal_output.apply_style('info-like', terminal_output.STYLE_CYAN)}")
print(f"STYLE_GRAY:        {terminal_output.apply_style('debug-like', terminal_output.STYLE_GRAY)}")
print(f"STYLE_GREEN:       {terminal_output.apply_style('success-like', terminal_output.STYLE_GREEN)}")
print(f"STYLE_BOLD_YELLOW: {terminal_output.apply_style('highlighted', terminal_output.STYLE_BOLD_YELLOW)}")
print(f"No style:          {terminal_output.apply_style('plain text', '')}")
print()

print("--- format_highlight() ---")
result_text = "Understanding neural networks and neural architectures"
highlighted = result_text.replace("neural", terminal_output.format_highlight("neural"))
print(f"Search 'neural': {highlighted}")
print()

print("--- format_label() ---")
print(f"{terminal_output.format_label('dry-run')} Showing preview only")
print(f"{terminal_output.format_label('model', 'claude-sonnet-4-20250514')}")
print(f"{terminal_output.format_label('tokens', '850 in / 320 out')}")
print()

print("--- format_separator() ---")
print(terminal_output.format_separator())
print(terminal_output.format_separator("=", 60))
print(terminal_output.format_separator("~", 40))
print()

print("--- format_token_counts() ---")
print(f"Small: {terminal_output.format_token_counts(150, 80)}")
print(f"Large: {terminal_output.format_token_counts(4500, 1200)}")
print()

print("--- format_cost() ---")
print(f"Tiny:   {terminal_output.format_cost(0.0008)}")
print(f"Small:  {terminal_output.format_cost(0.0032)}")
print(f"Medium: {terminal_output.format_cost(0.125)}")
print(f"Large:  {terminal_output.format_cost(3.45)}")
print()

print("--- format_block() ---")
api_request = "POST /v1/messages\nmodel: claude-sonnet-4-20250514\nmax_tokens: 1024"
print(terminal_output.format_block("API Request", api_request))
print()

print("--- wrap_text() ---")
long_text = "This is a very long line of text that will definitely exceed the typical terminal width and needs to be wrapped to multiple lines for readability."
print("Wrapped to 60 chars:")
print(terminal_output.wrap_text(long_text, width=60))
print()
print("Wrapped to 60 chars with 4-space indent:")
print(terminal_output.wrap_text(long_text, indent=4, width=60))
print()

# ============================================================================
# Section 4: New Styling Functions
# ============================================================================
print("=== SECTION 4: New Styling Functions ===")
print()

print("--- format_duration() ---")
test_values: list[float] = [-3, 0, 1, 3, 6, 7, 10, 14, 21, 30, 45, 60, 90, 180, 365, 730]
for days in test_values:
    result = terminal_output.format_duration(days)
    print(f"  {days:>6} -> {result}")
print()
print("Float rounding:")
print(f"  6.4  -> {terminal_output.format_duration(6.4)}")
print(f"  6.6  -> {terminal_output.format_duration(6.6)}")
print(f"  13.5 -> {terminal_output.format_duration(13.5)}")
print()

print("--- format_choices() ---")
standard_choices: list[tuple[str, str]] = [("0", "failed"), ("1", "passed"), ("2", "easy")]
print("Horizontal:")
print(terminal_output.format_choices(standard_choices))
print()
print("Vertical:")
print(terminal_output.format_choices(standard_choices, layout="vertical"))
print()
long_label_choices: list[tuple[str, str]] = [
    ("1", "completely forgot"),
    ("2", "wrong but close"),
    ("3", "correct with effort"),
    ("4", "correct with hesitation"),
    ("5", "perfect recall"),
    ("6", "too easy to count"),
]
print("Auto-fallback (6 long labels overflow horizontal -> vertical):")
print(terminal_output.format_choices(long_label_choices))
print()

print("--- format_card() ---")
terminal_output.set_layout(max_width=76, align="center")
print("Full card via emit():")
terminal_output.emit(terminal_output.format_card(
    header_left=terminal_output.apply_style("[3 / 47]", terminal_output.STYLE_BOLD),
    header_right="geography",
    body="What is the capital city of Japan?",
    footer="0 = failed   1 = hard   2 = good   3 = easy",
))
print()
print("No footer:")
terminal_output.emit(terminal_output.format_card(
    header_left=terminal_output.apply_style("[1 / 10]", terminal_output.STYLE_BOLD),
    header_right="vocabulary",
    body="Define: ephemeral",
))
print()
print("Long body (wrapping):")
terminal_output.emit(terminal_output.format_card(
    header_left=terminal_output.apply_style("[7 / 20]", terminal_output.STYLE_BOLD),
    header_right="machine learning",
    body="Explain the difference between supervised and unsupervised learning, including two examples of each and when you would choose one approach over the other.",
    footer="Answer in your own words before revealing.",
))
print()
print("Styled body (ANSI codes must not break border alignment):")
styled_body = (
    "Capital: " + terminal_output.apply_style("Tokyo", terminal_output.STYLE_BOLD)
    + "\nPopulation: " + terminal_output.apply_style("13.96 million", terminal_output.STYLE_CYAN)
)
terminal_output.emit(terminal_output.format_card(
    header_left=terminal_output.apply_style("[4 / 47]", terminal_output.STYLE_BOLD),
    header_right="geography",
    body=styled_body,
))
print()
terminal_output.set_layout(max_width=80, align="left")

# ============================================================================
# Section 5: Output Functions
# ============================================================================
print("=== SECTION 5: Output Functions ===")
print()

print("--- emit() vs print() ---")
terminal_output.set_layout(max_width=60, align="center")
print("emit() -- layout applied (centered, capped at 60):")
terminal_output.emit("This line goes through emit().")
print("print() -- raw, no layout:")
print("This line goes through print().")
print()
terminal_output.set_layout(max_width=80, align="left")

print("--- clear_screen() ---")
print("Screen will clear in 2 seconds...")
time.sleep(2)
terminal_output.clear_screen()
print("Screen cleared. Demo continues.")
print()

print("--- msg_* with layout alignment ---")
print("(msg_* to stderr, emit() to stdout -- both centered at max_width=60)")
terminal_output.set_layout(max_width=60, align="center")
terminal_output.emit(terminal_output.format_separator())
terminal_output.msg_error("Something failed")
terminal_output.msg_warn("Watch out")
terminal_output.msg_info("Status update")
terminal_output.set_verbosity(4)
terminal_output.msg_debug("Internal detail")
terminal_output.set_verbosity(3)
terminal_output.msg_success("All good")
terminal_output.emit(terminal_output.format_separator())
print()
terminal_output.set_layout(max_width=80, align="left")

print("--- Verbosity levels ---")
print("verbosity=1 (error only):")
terminal_output.set_verbosity(1)
terminal_output.msg_error("Shown")
terminal_output.msg_warn("Suppressed")
terminal_output.msg_info("Suppressed")
print()
print("verbosity=0 (silent):")
terminal_output.set_verbosity(0)
terminal_output.msg_error("Suppressed")
print("(nothing on stderr)")
print()
print("verbosity=5 (trace -- shows caller name):")
terminal_output.set_verbosity(5)
terminal_output.msg_info("Trace mode active")
print()
terminal_output.set_verbosity(3)

# ============================================================================
# Section 6: Integration Scene -- Mock Review Session
# ============================================================================
print("=== SECTION 6: Integration Scene ===")
print()
print("Mock review session starting in 2 seconds...")
time.sleep(2)
terminal_output.clear_screen()

terminal_output.set_layout(max_width=76, align="center")

terminal_output.emit(terminal_output.format_card(
    header_left=terminal_output.apply_style("[12 / 47]", terminal_output.STYLE_BOLD),
    header_right="history",
    body="In what year did the Berlin Wall fall?",
    footer="Think before revealing the answer.",
))
print()

terminal_output.emit(terminal_output.format_choices([
    ("0", "failed"),
    ("1", "hard"),
    ("2", "good"),
    ("3", "easy"),
]))
print()

terminal_output.msg_success(
    "Passed. Next review in "
    + terminal_output.apply_style(
        terminal_output.format_duration(6.0),
        terminal_output.STYLE_BOLD
    )
    + "."
)
print()
terminal_output.set_layout(max_width=80, align="left")

# ============================================================================
# Section 7: Edge Cases
# ============================================================================
print("=== SECTION 7: Edge Cases ===")
print()

print("--- Empty strings ---")
print(f"measure_width(''): {terminal_output.measure_width('')}")
print(f"align_text('', 'center', 80): '{terminal_output.align_text('', 'center', 80)}'")
print(f"format_duration(0.0): {terminal_output.format_duration(0.0)}")
print(f"format_choices([]): '{terminal_output.format_choices([])}'")
print()

print("--- Narrow layout (max_width=30) ---")
terminal_output.set_layout(max_width=30, align="center")
terminal_output.emit("Short line fits fine.")
terminal_output.emit(terminal_output.format_separator())
terminal_output.emit(terminal_output.format_card(
    header_left=terminal_output.apply_style("[1/5]", terminal_output.STYLE_BOLD),
    header_right="test",
    body="Body wraps tightly at narrow width.",
))
print()
terminal_output.set_layout(max_width=80, align="left")

print("--- Content wider than max_width ---")
terminal_output.set_layout(max_width=30, align="center")
wide_content = "This line is much longer than the configured max_width of 30 chars."
terminal_output.emit(wide_content)
print("(content passes through unchanged, no truncation)")
print()
terminal_output.set_layout(max_width=80, align="left")

print("--- Multi-line ANSI content through align_text ---")
multiline_ansi = "\n".join([
    terminal_output.apply_style("line one bold", terminal_output.STYLE_BOLD),
    terminal_output.apply_style("line two dim and longer", terminal_output.STYLE_DIM),
    terminal_output.apply_style("line three cyan", terminal_output.STYLE_CYAN),
])
print("Centered (padding computed from widest visible line):")
print(terminal_output.align_text(multiline_ansi, "center", 80))
print()

print("--- Empty message guard ---")
terminal_output.set_verbosity(3)
terminal_output.msg_info("")
terminal_output.msg_info("   ")
print("(two warnings about empty messages on stderr)")
print()

# Reset to clean state
terminal_output.set_verbosity(3)
terminal_output.set_layout(max_width=80, align="left")
