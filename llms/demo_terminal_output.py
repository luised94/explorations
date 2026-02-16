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

# Direct styling - no wrapper functions
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
# Practical Usage Patterns
# ============================================================================

print("=== Practical Usage Patterns ===")

# Headers and emphasis
header = terminal_output.apply_style("Configuration Settings", terminal_output.STYLE_BOLD)
print(header)
print(f"This is {terminal_output.apply_style('critical', terminal_output.STYLE_BOLD)} information")
print(f"{terminal_output.apply_style('Status:', terminal_output.STYLE_BOLD)} Active")

# Separators and metadata
separator = terminal_output.apply_style("-" * 40, terminal_output.STYLE_DIM)
metadata = terminal_output.apply_style("Last updated: 2025-02-14", terminal_output.STYLE_DIM)
note = terminal_output.apply_style("(optional parameter)", terminal_output.STYLE_DIM)
print(separator)
print(metadata)
print(note)

# Composed output
section_title = terminal_output.apply_style("API Response", terminal_output.STYLE_BOLD)
section_border = terminal_output.apply_style("=" * 50, terminal_output.STYLE_DIM)
print(section_border)
print(section_title)
print(section_border)
print()


# ============================================================================
# format_highlight() - Semantic Highlighting
# ============================================================================

print("=== format_highlight() ===")

# Search result highlighting (primary use case)
search_query = "neural"
result_text = "Understanding neural networks and neural architectures"
highlighted_result = result_text.replace("neural", terminal_output.format_highlight("neural"))
print(f"Search for '{search_query}':")
print(f"  {highlighted_result}")

# Multiple highlights in same line
multi_match = "The neural network uses neural pathways"
multi_highlighted = multi_match.replace("neural", terminal_output.format_highlight("neural"))
print(f"  {multi_highlighted}")
print()


# ============================================================================
# format_label() - Structured Labels
# ============================================================================

print("=== format_label() ===")

# Labels without values
print(f"{terminal_output.format_label('dry-run')} Showing preview only")
print(f"{terminal_output.format_label('cached')} Using stored response")
print(f"{terminal_output.format_label('experimental')} Feature in testing")

# Labels with values
print(f"{terminal_output.format_label('model', 'claude-sonnet-4-20250514')}")
print(f"{terminal_output.format_label('tokens', '850 in / 320 out')}")
print(f"{terminal_output.format_label('cost', '$0.0032')}")
print(f"{terminal_output.format_label('status', 'success')}")

# Combined in context
print(f"\n{terminal_output.format_label('request')} API call to {terminal_output.format_label('model', 'sonnet')}")
print()


# ============================================================================
# format_separator() - Separator Lines
# ============================================================================

print("=== format_separator() ===")

# Default separator (hyphen, terminal width)
print(terminal_output.format_separator())

# Custom character
print(terminal_output.format_separator("="))

# Custom width
print(terminal_output.format_separator("-", 30))

# Different characters for different purposes
print(terminal_output.format_separator("=", 60))
print("Section Header")
print(terminal_output.format_separator("=", 60))
print()
print(terminal_output.format_separator("-", 60))
print("Subsection")
print(terminal_output.format_separator("-", 60))
print()
