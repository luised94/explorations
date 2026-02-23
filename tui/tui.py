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
    terminal: dict = {
        'width':            0,
        'height':           0,
        'original_termios': None,
    }

    # Register cleanup BEFORE enter_raw_mode so that if the process
    # is killed during setup, restore_terminal still runs.
    atexit.register(restore_terminal, terminal)

    def _restore_on_signal(signal_number: int, frame: object) -> None:
        restore_terminal(terminal)
        sys.exit(0)

    signal.signal(signal.SIGTERM, _restore_on_signal)
    signal.signal(signal.SIGHUP, _restore_on_signal)

    enter_raw_mode(terminal)

    # Prove the round-trip works: write to the alternate screen,
    # pause so the human can see it, then tear down.
    os.write(1, b"raw mode active -- you should see this on the alternate screen\r\n")
    os.write(1, b"restoring in 2 seconds...\r\n")

    import time
    time.sleep(2)

    restore_terminal(terminal)
    print("ok")


if __name__ == '__main__':
    main()
