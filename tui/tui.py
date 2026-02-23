# ==============================================================================
# CONSTANTS AND TYPE ALIASES
# ==============================================================================

from typing import TypeAlias

# --- color encoding -----------------------------------------------------------
# color is a tagged 32-bit integer
# top byte is the discriminant tag; lower three bytes are the value

COLOR_DEFAULT: int = 0x00_000000   # terminal default color
COLOR_TAG_IDX: int = 0x01_000000   # palette index 0-255 in low byte
COLOR_TAG_RGB: int = 0x02_000000   # 0x00RRGGBB in low three bytes

# --- SGR modifier bitfield ----------------------------------------------------
# one bit per SGR attribute; compose with |, test with &

MOD_BOLD:          int = 1 << 0   # SGR 1
MOD_DIM:           int = 1 << 1   # SGR 2
MOD_ITALIC:        int = 1 << 2   # SGR 3
MOD_UNDERLINE:     int = 1 << 3   # SGR 4
MOD_STRIKETHROUGH: int = 1 << 4   # SGR 9
MOD_REVERSE:       int = 1 << 5   # SGR 7
MOD_HIDDEN:        int = 1 << 6   # SGR 8
MOD_BLINK:         int = 1 << 7   # SGR 5

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

NO_REGION:            int = -1   # no focused region
RING_BUFFER_CAPACITY: int = 64   # must be a power of two

# --- blank cell ---------------------------------------------------------------
# (symbol, fg_color, bg_color, modifiers)

Cell: TypeAlias = tuple[str, int, int, int]

BLANK_CELL: Cell = (' ', COLOR_DEFAULT, COLOR_DEFAULT, 0)

# --- debug log path -----------------------------------------------------------
# set to a file path to enable raw byte logging in write_events_to_ring

RAW_LOG_PATH: str = ''

# ==============================================================================
# TERMINAL SETUP / TEARDOWN
# ==============================================================================

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

# SIGWINCH_RECEIVED is the single permitted module-level mutable in this file.
# It exists solely because OS signal delivery has no other channel in Python.
# No other module-level mutable state is allowed anywhere.
SIGWINCH_RECEIVED: bool = False

DEFAULT_TERMINAL: dict = {
    'width':            0,
    'height':           0,
    'original_termios': None,
}

DEFAULT_GRID: dict = {
    'width':    0,
    'height':   0,
    'current':  [],   # list[Cell], size = width * height
    'previous': [],   # list[Cell], size = width * height
}

DEFAULT_REGION: dict = {
    'region_id':     0,
    'name':          '',    # debug label only; never used for lookup
    'top':           0,
    'left':          0,
    'width':         0,
    'height':        0,
    'scroll_offset': 0,
    'lines':         [],    # list[str]
    'is_focused':    False,
}


def main() -> None:
    print("ok")


if __name__ == '__main__':
    main()
