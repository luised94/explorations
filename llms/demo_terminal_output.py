#!/usr/bin/env python3
"""Demo script for terminal_output.py - executable documentation."""

import terminal_output


# ============================================================================
# Module Constants
# ============================================================================

print("=== Module Constants ===")
print(f"stderr is terminal: {terminal_output.STDERR_IS_TERMINAL}")
print(f"terminal width: {terminal_output.TERMINAL_WIDTH}")
print(f"verbosity level: {terminal_output.VERBOSITY}")
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

# Simple block
simple_content = "This is the content inside the block."
simple_block = terminal_output.format_block("Simple Block", simple_content)
print(simple_block)
print()

# Multi-line content
api_request = "POST /v1/messages\nmodel: claude-sonnet-4-20250514\nmax_tokens: 1024"
request_block = terminal_output.format_block("API Request", api_request)
print(request_block)
print()

# Block with formatted content inside
tokens = terminal_output.format_token_counts(850, 320)
cost = terminal_output.format_cost(0.0032)
summary_content = f"Tokens: {tokens}\nCost: {cost}\nStatus: Success"
summary_block = terminal_output.format_block("Request Summary", summary_content)
print(summary_block)
print()

# Nested formatting - block containing labels
config_lines = [
    f"{terminal_output.format_label('model', 'sonnet')}",
    f"{terminal_output.format_label('temperature', '1.0')}",
    f"{terminal_output.format_label('max_tokens', '2048')}"
]
config_content = "\n".join(config_lines)
config_block = terminal_output.format_block("Configuration", config_content)
print(config_block)
print()


# ============================================================================
# wrap_text() - Text Wrapping
# ============================================================================

print("=== wrap_text() ===")

# Long single paragraph
long_text = "This is a very long line of text that will definitely exceed the typical terminal width and needs to be wrapped to multiple lines for readability. It demonstrates how the wrap_text function handles text that is too long for a single line."

print("No wrap (raw):")
print(long_text)
print()

print("Wrapped to 60 chars:")
wrapped_60 = terminal_output.wrap_text(long_text, width=60)
print(wrapped_60)
print()

print("Wrapped to 60 chars with 4-space indent:")
wrapped_indented = terminal_output.wrap_text(long_text, indent=4, width=60)
print(wrapped_indented)
print()

# Multiple paragraphs
multi_paragraph = "First paragraph is here and it is quite long so it will wrap.\n\nSecond paragraph is also long and will wrap independently of the first paragraph."

print("Multi-paragraph wrapped to 50 chars:")
wrapped_multi = terminal_output.wrap_text(multi_paragraph, width=50)
print(wrapped_multi)
print()

# Practical example: wrapping help text
help_text = "The --verbose flag increases output verbosity. Use -v for basic debug output, -vv for detailed trace output including function calls, or -vvv for maximum verbosity with all internal state."
print("Help text wrapped to 70 chars with 2-space indent:")
wrapped_help = terminal_output.wrap_text(help_text, indent=2, width=70)
print(wrapped_help)
print()
