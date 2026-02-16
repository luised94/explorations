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
# apply_style() - Core Styling Primitive
# ============================================================================

print("=== apply_style() with STYLE_* constants ===")

# Direct styling - no wrapper functions
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

# Practical examples showing typical usage patterns
print("=== Practical Usage Patterns ===")

# Headers and emphasis
header = term.apply_style("Configuration Settings", term.STYLE_BOLD)
print(f"{header}")
print(f"This is {term.apply_style('critical', term.STYLE_BOLD)} information")
print(f"{term.apply_style('Status:', term.STYLE_BOLD)} Active")

# Separators and metadata
separator = term.apply_style("-" * 40, term.STYLE_DIM)
metadata = term.apply_style("Last updated: 2025-02-14", term.STYLE_DIM)
note = term.apply_style("(optional parameter)", term.STYLE_DIM)
print(separator)
print(metadata)
print(note)

# Composed output
section_title = term.apply_style("API Response", term.STYLE_BOLD)
section_border = term.apply_style("=" * 50, term.STYLE_DIM)
print(section_border)
print(section_title)
print(section_border)
print()
