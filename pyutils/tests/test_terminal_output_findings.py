"""Fixes for findings F18 and F19 (rep/FINDINGS.md) in terminal_output.

Every test sets the module state it needs through monkeypatch, so the
state is restored afterwards and the order of tests does not matter.
"""

import io
import sys

import pytest

from pyutils import terminal_output


def keep_module_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Register the module globals that set_layout and set_color change, so
    monkeypatch restores them after the test."""
    for name in ("_layout_max_width", "_layout_align", "_layout_was_set", "STDERR_IS_TERMINAL", *terminal_output._ANSI_CODES):
        monkeypatch.setattr(terminal_output, name, getattr(terminal_output, name))


def test_default_width_fits_a_narrow_terminal_without_set_layout(monkeypatch: pytest.MonkeyPatch) -> None:
    # F18: on a 60-column terminal the default of 80 made 80-column
    # separators and cards, which wrapped into broken borders.
    keep_module_state(monkeypatch)
    monkeypatch.setattr(terminal_output, "_cached_terminal_width", 60)
    monkeypatch.setattr(terminal_output, "_layout_was_set", False)
    monkeypatch.setattr(terminal_output, "_layout_max_width", 80)
    assert terminal_output.measure_width(terminal_output.format_separator()) == 60
    card_lines = terminal_output.format_card("1/12", "due", "Capital of France?").split("\n")
    assert {terminal_output.measure_width(line) for line in card_lines} == {60}


def test_default_width_is_unchanged_without_a_terminal(monkeypatch: pytest.MonkeyPatch) -> None:
    # The fallback width is 80 (piped output, tests): the default stays 80.
    keep_module_state(monkeypatch)
    monkeypatch.setattr(terminal_output, "_cached_terminal_width", 80)
    monkeypatch.setattr(terminal_output, "_layout_was_set", False)
    monkeypatch.setattr(terminal_output, "_layout_max_width", 80)
    assert terminal_output.measure_width(terminal_output.format_separator()) == 80


def test_set_layout_behaves_as_before(monkeypatch: pytest.MonkeyPatch) -> None:
    keep_module_state(monkeypatch)
    monkeypatch.setattr(terminal_output, "_cached_terminal_width", 120)
    terminal_output.set_layout(max_width=76, align="center")
    assert terminal_output.measure_width(terminal_output.format_separator()) == 76
    monkeypatch.setattr(terminal_output, "_cached_terminal_width", 50)
    terminal_output.set_layout(max_width=76)
    assert terminal_output.measure_width(terminal_output.format_separator()) == 50


def test_set_color_none_refreshes_the_stderr_terminal_check(monkeypatch: pytest.MonkeyPatch) -> None:
    # F19: STDERR_IS_TERMINAL was read once at import; after stderr was
    # redirected, clear_screen() still wrote escape codes into it.
    keep_module_state(monkeypatch)
    redirected_stderr = io.StringIO()
    monkeypatch.setattr(sys, "stderr", redirected_stderr)
    monkeypatch.setattr(terminal_output, "STDERR_IS_TERMINAL", True)
    terminal_output.set_color(None)
    assert terminal_output.STDERR_IS_TERMINAL is False
    terminal_output.clear_screen()
    assert "\033" not in redirected_stderr.getvalue()


def test_forcing_color_leaves_the_stderr_terminal_check_alone(monkeypatch: pytest.MonkeyPatch) -> None:
    # set_color(True/False) forces styling only; terminal detection belongs
    # to set_color(None).
    keep_module_state(monkeypatch)
    monkeypatch.setattr(terminal_output, "STDERR_IS_TERMINAL", True)
    terminal_output.set_color(False)
    assert terminal_output.STDERR_IS_TERMINAL is True
