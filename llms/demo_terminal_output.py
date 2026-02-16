#!/usr/bin/env python3
"""Demo script for terminal_output.py - executable documentation."""

import terminal_output as term

# ============================================================================
# Module Constants
# ============================================================================

print("=== Module Constants ===")
print(f"stderr is terminal: {term.STDERR_IS_TERMINAL}")
print(f"terminal width: {term.TERMINAL_WIDTH}")
print(f"verbosity level: {term.VERBOSITY}")
print()


# ============================================================================
# apply_style() - Core Styling Function
# ============================================================================

print("=== apply_style() ===")

# Basic styles
print(f"Bold: {term.apply_style('important text', term.STYLE_BOLD)}")
print(f"Dim: {term.apply_style('secondary info', term.STYLE_DIM)}")
print(f"Red: {term.apply_style('error-like', term.STYLE_RED)}")
print(f"Yellow: {term.apply_style('warning-like', term.STYLE_YELLOW)}")
print(f"Cyan: {term.apply_style('info-like', term.STYLE_CYAN)}")
print(f"Gray: {term.apply_style('debug-like', term.STYLE_GRAY)}")
print(f"Green: {term.apply_style('success-like', term.STYLE_GREEN)}")
print(f"Bold yellow: {term.apply_style('highlighted', term.STYLE_BOLD_YELLOW)}")

# Empty style code returns plain text
print(f"No style: {term.apply_style('plain text', '')}")
print()


# ============================================================================
# format_bold() and format_dim() - Common Styling Wrappers
# ============================================================================

print("=== format_bold() and format_dim() ===")

# format_bold examples
print(f"Header: {term.format_bold('Configuration Settings')}")
print(f"Emphasis: This is {term.format_bold('critical')} information")
print(f"Label: {term.format_bold('Status:')} Active")

# format_dim examples
print(f"Separator: {term.format_dim('-' * 40)}")
print(f"Metadata: {term.format_dim('Last updated: 2025-02-14')}")
print(f"Subdued: {term.format_dim('(optional parameter)')}")

# Combined usage
section_title = term.format_bold("API Response")
section_border = term.format_dim("=" * 50)
print(f"{section_border}")
print(f"{section_title}")
print(f"{section_border}")
print()
