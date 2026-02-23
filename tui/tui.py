# ==============================================================================
# CONSTANTS AND TYPE ALIASES
# ==============================================================================
from typing import TypeAlias

# --- color encoding -----------------------------------------------------------
COLOR_DEFAULT: int = 0x00_000000
COLOR_TAG_IDX: int = 0x01_000000
COLOR_TAG_RGB: int = 0x02_000000

# --- SGR modifier bitfield ----------------------------------------------------
MOD_BOLD:          int = 1 << 0
MOD_DIM:           int = 1 << 1
MOD_ITALIC:        int = 1 << 2
MOD_UNDERLINE:     int = 1 << 3
MOD_STRIKETHROUGH: int = 1 << 4
MOD_REVERSE:       int = 1 << 5
MOD_HIDDEN:        int = 1 << 6
MOD_BLINK:         int = 1 << 7

# --- key modifier bitfield ----------------------------------------------------
MOD_KEY_SHIFT: int = 1 << 0
MOD_KEY_CTRL:  int = 1 << 1
MOD_KEY_ALT:   int = 1 << 2
MOD_KEY_SUPER: int = 1 << 3

# --- mode strings -------------------------------------------------------------
MODE_NORMAL:   str = 'NORMAL'
MODE_INPUT:    str = 'INPUT'
MODE_COMMAND:  str = 'COMMAND'
MODE_CONFIRM:  str = 'CONFIRM'
MODE_QUITTING: str = 'QUITTING'

# --- sentinel values ----------------------------------------------------------
NO_REGION:            int = -1
RING_BUFFER_CAPACITY: int = 64

# --- blank cell ---------------------------------------------------------------
Cell: TypeAlias = tuple[str, int, int, int]
BLANK_CELL: Cell = (' ', COLOR_DEFAULT, COLOR_DEFAULT, 0)

# --- debug log path -----------------------------------------------------------
RAW_LOG_PATH: str = ''


# ==============================================================================
# TERMINAL SETUP / TEARDOWN
# ==============================================================================
import atexit
import os
import signal
import sys
import termios
import tty


def claim_foreground_process_group(terminal_file_descriptor: int) -> None:
    """Claim the foreground process group for the controlling terminal.

    When launched via a process manager such as uv, the Python process may
    reside in a background process group.  Terminal control operations like
    tcsetattr (called by tty.setraw) send SIGTTOU to background processes
    regardless of the TOSTOP flag, silently stopping them.

    We ignore SIGTTOU temporarily so that the tcsetpgrp call itself does
    not stop us while we are still in the background group, then restore
    the original SIGTTOU disposition once we own the foreground.
    """
    current_process_group: int = os.getpgrp()

    try:
        foreground_process_group: int = os.tcgetpgrp(terminal_file_descriptor)
    except OSError:
        # No controlling terminal - nothing to claim.
        return

    if current_process_group == foreground_process_group:
        return

    previous_sigttou_handler = signal.getsignal(signal.SIGTTOU)
    signal.signal(signal.SIGTTOU, signal.SIG_IGN)

    try:
        os.tcsetpgrp(terminal_file_descriptor, current_process_group)
    except OSError:
        # Could not claim foreground (e.g. different session).
        # Proceed anyway - writes may still work if TOSTOP is not set.
        pass

    signal.signal(signal.SIGTTOU, previous_sigttou_handler)


def enter_raw_mode(terminal: dict) -> None:
    file_descriptor: int = sys.stdin.fileno()

    # Must claim the foreground process group BEFORE tty.setraw().
    # tty.setraw() calls tcsetattr(), which sends SIGTTOU to any
    # background process unconditionally (TOSTOP is ignored for
    # terminal control functions).
    claim_foreground_process_group(file_descriptor)

    original_termios: list = termios.tcgetattr(file_descriptor)
    terminal['original_termios'] = original_termios

    new_width: int
    new_height: int
    new_height, new_width = os.get_terminal_size()
    terminal['width'] = new_width
    terminal['height'] = new_height

    # Enter alternate screen buffer, then hide cursor.
    os.write(1, b'\033[?1049h')
    os.write(1, b'\033[?25l')

    tty.setraw(file_descriptor)


def restore_terminal(terminal: dict) -> None:
    """Restore the terminal to its original state.

    Idempotent: after the first call, original_termios is set to None,
    so subsequent calls (from atexit, signal handlers, or explicit
    teardown) are no-ops.  This prevents double-restore issues when
    multiple exit paths converge.
    """
    saved_termios: list | None = terminal['original_termios']
    if saved_termios is None:
        return

    file_descriptor: int = sys.stdin.fileno()
    termios.tcsetattr(file_descriptor, termios.TCSADRAIN, saved_termios)

    # Disarm so atexit / signal handler calls are no-ops.
    terminal['original_termios'] = None

    # Show cursor, then exit alternate screen buffer.
    os.write(1, b'\033[?25h')
    os.write(1, b'\033[?1049l')


# ==============================================================================
# HOT PATH: 2D CELL GRID
# ==============================================================================

import io


def build_color_escape_fg(color: int) -> bytes:
    tag: int = color & 0xFF_000000
    value: int = color & 0x00_FFFFFF
    if tag == COLOR_DEFAULT:
        return b'\033[39m'
    if tag == COLOR_TAG_IDX:
        index: int = value & 0xFF
        return f'\033[38;5;{index}m'.encode('ascii')
    if tag == COLOR_TAG_RGB:
        red: int   = (value >> 16) & 0xFF
        green: int = (value >>  8) & 0xFF
        blue: int  =  value        & 0xFF
        return f'\033[38;2;{red};{green};{blue}m'.encode('ascii')
    return b'\033[39m'


def build_color_escape_bg(color: int) -> bytes:
    tag: int = color & 0xFF_000000
    value: int = color & 0x00_FFFFFF
    if tag == COLOR_DEFAULT:
        return b'\033[49m'
    if tag == COLOR_TAG_IDX:
        index: int = value & 0xFF
        return f'\033[48;5;{index}m'.encode('ascii')
    if tag == COLOR_TAG_RGB:
        red: int   = (value >> 16) & 0xFF
        green: int = (value >>  8) & 0xFF
        blue: int  =  value        & 0xFF
        return f'\033[48;2;{red};{green};{blue}m'.encode('ascii')
    return b'\033[49m'


def build_modifier_escape(modifiers: int) -> bytes:
    # always reset first, then re-apply requested attributes
    buf: io.BytesIO = io.BytesIO()
    buf.write(b'\033[0m')
    if modifiers & MOD_BOLD:
        buf.write(b'\033[1m')
    if modifiers & MOD_DIM:
        buf.write(b'\033[2m')
    if modifiers & MOD_ITALIC:
        buf.write(b'\033[3m')
    if modifiers & MOD_UNDERLINE:
        buf.write(b'\033[4m')
    if modifiers & MOD_BLINK:
        buf.write(b'\033[5m')
    if modifiers & MOD_REVERSE:
        buf.write(b'\033[7m')
    if modifiers & MOD_HIDDEN:
        buf.write(b'\033[8m')
    if modifiers & MOD_STRIKETHROUGH:
        buf.write(b'\033[9m')
    return buf.getvalue()


def build_style_cache() -> dict:
    # pre-builds nothing at startup; populated on first encounter of each
    # (fg_color, bg_color, modifiers) triple during flush
    # returns an empty dict; flush functions populate it lazily
    return {}


def get_style_bytes(
    fg_color:    int,
    bg_color:    int,
    modifiers:   int,
    style_cache: dict,
) -> bytes:
    cache_key: tuple[int, int, int] = (fg_color, bg_color, modifiers)
    if cache_key in style_cache:
        return style_cache[cache_key]
    buf: io.BytesIO = io.BytesIO()
    buf.write(build_modifier_escape(modifiers))
    buf.write(build_color_escape_fg(fg_color))
    buf.write(build_color_escape_bg(bg_color))
    result: bytes = buf.getvalue()
    style_cache[cache_key] = result
    return result


def flush_full(
    current_cells: list,
    width:         int,
    height:        int,
    style_cache:   dict,
) -> None:
    # style delta register - tracks what the terminal currently has applied
    # sentinel: -1 forces a style emit on the very first cell
    register_fg:   int = -1
    register_bg:   int = -1
    register_mods: int = -1

    output: io.BytesIO = io.BytesIO()

    for row in range(height):
        # move cursor to start of row (1-based)
        output.write(f'\033[{row + 1};1H'.encode('ascii'))

        for column in range(width):
            cell_index: int = row * width + column
            cell: Cell = current_cells[cell_index]

            symbol:    str = cell[0]
            fg_color:  int = cell[1]
            bg_color:  int = cell[2]
            modifiers: int = cell[3]

            style_changed: bool = (
                fg_color  != register_fg   or
                bg_color  != register_bg   or
                modifiers != register_mods
            )

            if style_changed:
                output.write(get_style_bytes(fg_color, bg_color, modifiers, style_cache))
                register_fg   = fg_color
                register_bg   = bg_color
                register_mods = modifiers

            output.write(symbol.encode('utf-8'))

    # reset SGR at end of frame
    output.write(b'\033[0m')
    os.write(1, output.getvalue())


# ==============================================================================
# REGIONS
# ==============================================================================


# ==============================================================================
# INPUT / KEY PARSING
# ==============================================================================


# ==============================================================================
# APPLICATION STATE AND EVENT LOOP
# ==============================================================================


# ==============================================================================
# ENTRY POINT
# ==============================================================================

SIGWINCH_RECEIVED: bool = False

DEFAULT_TERMINAL: dict = {
    'width':            0,
    'height':           0,
    'original_termios': None,
}

DEFAULT_GRID: dict = {
    'width':    0,
    'height':   0,
    'current':  [],
    'previous': [],
}

DEFAULT_REGION: dict = {
    'region_id':     0,
    'name':          '',
    'top':           0,
    'left':          0,
    'width':         0,
    'height':        0,
    'scroll_offset': 0,
    'lines':         [],
    'is_focused':    False,
}

def main() -> None:
    import time

    terminal: dict = {
        'width':            0,
        'height':           0,
        'original_termios': None,
    }

    atexit.register(restore_terminal, terminal)

    def _restore_on_signal(signal_number: int, frame: object) -> None:
        restore_terminal(terminal)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _restore_on_signal)
    signal.signal(signal.SIGHUP, _restore_on_signal)

    enter_raw_mode(terminal)

    grid_width:  int = terminal['width']
    grid_height: int = terminal['height']
    cell_count:  int = grid_width * grid_height

    grid: dict = {
        'width':    grid_width,
        'height':   grid_height,
        'current':  [BLANK_CELL] * cell_count,
        'previous': [BLANK_CELL] * cell_count,
    }

    style_cache: dict = build_style_cache()

    # checkerboard: two chars, two fg colors (one indexed, one RGB), one modifier
    color_a: int = COLOR_TAG_IDX | 196        # palette red
    color_b: int = COLOR_TAG_IDX | 12   # ANSI blue, index 12

    for row in range(grid_height):
        for column in range(grid_width):
            cell_index: int = row * grid_width + column
            is_even: bool = (row + column) % 2 == 0
            if is_even:
                grid['current'][cell_index] = ('A', color_a, COLOR_DEFAULT, MOD_BOLD)
            else:
                grid['current'][cell_index] = ('B', color_b, COLOR_DEFAULT, 0)

    flush_full(grid['current'], grid_width, grid_height, style_cache)
    time.sleep(2)

    restore_terminal(terminal)
    print("ok")

if __name__ == '__main__':
    main()
