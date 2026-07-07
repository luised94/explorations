# /// script
# requires-python = ">=3.11"
# dependencies = ["pytest"]
# ///
"""Tests for terminal_output. Color state pinned per test -- no test depends
on what kind of terminal runs the suite (the disease that motivated
set_color).

Run: uv run test_terminal_output.py
 or: python -m pytest test_terminal_output.py -q
"""

import pytest

from pyutils import terminal_output as to


@pytest.fixture(autouse=True)
def color_off():
    """Default every test to color-off; tests that want color set it."""
    to.set_color(False)
    yield
    to.set_color(False)


# =============================================================================
# COLOR STATE (the set_color injection point)
# =============================================================================


def test_set_color_toggles_all_constants():
    to.set_color(True)
    assert to.STYLE_RED == "\033[31m" and to.STYLE_RESET == "\033[0m"
    to.set_color(False)
    assert to.STYLE_RED == "" and to.STYLE_RESET == ""


def test_no_color_env_disables_detection(monkeypatch):
    monkeypatch.setenv("NO_COLOR", "1")
    to.set_color(None)
    assert to.STYLE_RED == ""


def test_apply_style_respects_current_state():
    to.set_color(True)
    assert to.apply_style("x", to.STYLE_RED) == "\033[31mx\033[0m"
    to.set_color(False)
    assert to.apply_style("x", to.STYLE_RED) == "x"


# =============================================================================
# PRIMITIVES
# =============================================================================


def test_measure_width_strips_ansi_and_takes_longest_line():
    assert to.measure_width("\033[1;33mhello\033[0m") == 5
    assert to.measure_width("ab\ncdef\nx") == 4
    assert to.measure_width("") == 0
    assert to.measure_width("\033[31m\033[0m") == 0


def test_align_text_center_and_right_block_alignment():
    assert to.align_text("ab\ncdef", "center", 8) == "  ab\n  cdef"
    assert to.align_text("ab\ncdef", "right", 8) == "    ab\n    cdef"
    assert to.align_text("ab", "left", 8) == "ab"
    assert to.align_text("abcdefgh", "center", 8) == "abcdefgh"  # fills width


def test_align_text_never_right_pads():
    for line in to.align_text("ab\ncdef", "center", 20).split("\n"):
        assert line == line.rstrip()


# =============================================================================
# FORMATTERS
# =============================================================================


@pytest.mark.parametrize(
    "days, expected",
    [
        (-1, "overdue"),
        (0, "today"),
        (1, "tomorrow"),
        (3, "3 days"),
        (7, "1 week"),
        (15.6, "2 weeks"),
        (30, "1 month"),
        (90, "3 months"),
        (365, "1 year"),
        (800, "2 years"),
    ],
)
def test_format_duration_thresholds(days, expected):
    assert to.format_duration(days) == expected


def test_format_label():
    assert to.format_label("dry-run") == "[dry-run]"
    assert to.format_label("model", "sonnet") == "[model: sonnet]"


def test_format_cost_precision_scales():
    assert to.format_cost(0.0032) == "$0.0032"
    assert to.format_cost(0.125) == "$0.125"
    assert to.format_cost(3.456) == "$3.46"


def test_format_card_lines_all_same_visible_width_with_color_on():
    """The border-flush guarantee must hold WITH ANSI codes present."""
    to.set_color(True)
    card = to.format_card("1 / 5", "drive", "Some body text.", footer="crit", width=40)
    widths = {to.measure_width(line) for line in card.split("\n")}
    assert widths == {40}


def test_format_choices_horizontal_falls_back_to_vertical_when_wide():
    choices = [(str(i), "a very long label " * 3) for i in range(4)]
    out = to.format_choices(choices)
    assert "\n" in out  # fell back to vertical


def test_wrap_text_preserves_blank_lines_and_indents():
    out = to.wrap_text("one two three four\n\nfive", indent=2, width=12)
    lines = out.split("\n")
    assert lines[0].startswith("  ") and "" in lines


if __name__ == "__main__":
    import sys

    sys.exit(pytest.main([__file__, "-q"]))
