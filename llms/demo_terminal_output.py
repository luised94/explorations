#!/usr/bin/env python3
"""Demo script for terminal_output.py - executable documentation."""

import terminal_output as term


def demo_constants() -> None:
    """Show module constants and terminal detection."""
    print("=== Module Constants ===")
    print(f"stderr is terminal: {term.STDERR_IS_TERMINAL}")
    print(f"terminal width: {term.TERMINAL_WIDTH}")
    print(f"verbosity level: {term.VERBOSITY}")
    print()


def demo_apply_style() -> None:
    """Demonstrate core styling function."""
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


def main() -> None:
    demo_constants()
    demo_apply_style()


if __name__ == "__main__":
    main()
