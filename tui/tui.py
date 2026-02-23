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

    terminal_size: os.terminal_size = os.get_terminal_size()
    terminal['width']  = terminal_size.columns
    terminal['height'] = terminal_size.lines

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

def row_has_changed(
    current_cells:  list,
    previous_cells: list,
    row_start:      int,
    row_end:        int,
) -> bool:
    for index in range(row_start, row_end):
        if current_cells[index] != previous_cells[index]:
            return True
    return False


def flush_diff(
    current_cells:  list,
    previous_cells: list,
    width:          int,
    height:         int,
    style_cache:    dict,
) -> None:
    # style delta register: tracks what the terminal currently has applied.
    # sentinel -1 forces a style emit on the very first changed cell.
    register_fg:   int = -1
    register_bg:   int = -1
    register_mods: int = -1

    output: io.BytesIO = io.BytesIO()

    for row in range(height):
        row_start: int = row * width
        row_end:   int = row_start + width

        if not row_has_changed(current_cells, previous_cells, row_start, row_end):
            # nothing written to terminal; style register remains accurate.
            continue

        cursor_at_column: int = -1   # unknown until first emit in this row

        for column in range(width):
            cell_index:    int  = row_start + column
            current_cell:  Cell = current_cells[cell_index]
            previous_cell: Cell = previous_cells[cell_index]

            if current_cell == previous_cell:
                cursor_at_column = -1   # gap: cursor position now unknown
                continue

            symbol:    str = current_cell[0]
            fg_color:  int = current_cell[1]
            bg_color:  int = current_cell[2]
            modifiers: int = current_cell[3]

            if cursor_at_column != column:
                # rows and columns are 1-based in ANSI escape sequences
                output.write(f'\033[{row + 1};{column + 1}H'.encode('ascii'))

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
            cursor_at_column = column + 1   # terminal cursor auto-advances after emit

    # reset SGR at end of frame
    output.write(b'\033[0m')
    os.write(1, output.getvalue())

    # swap: previous now matches what was written to the terminal
    previous_cells[:] = current_cells[:]


def test_diff() -> None:
    import sys as _sys

    width:  int = 4
    height: int = 3
    count:  int = width * height

    color_a: int = COLOR_TAG_IDX | 196
    color_b: int = COLOR_TAG_IDX | 12

    cell_a: Cell = ('A', color_a, COLOR_DEFAULT, MOD_BOLD)
    cell_b: Cell = ('B', color_b, COLOR_DEFAULT, 0)

    pass_count: int = 0
    fail_count: int = 0

    def report(label: str, passed: bool) -> None:
        nonlocal pass_count, fail_count
        status: str = 'PASS' if passed else 'FAIL'
        _sys.stderr.write(f'test_diff: {status}: {label}\n')
        if passed:
            pass_count += 1
        else:
            fail_count += 1

    # --- row_has_changed tests -----------------------------------------------

    all_a: list = [cell_a] * count
    all_b: list = [cell_b] * count

    report(
        'row_has_changed: identical rows returns False',
        row_has_changed(all_a, all_a, 0, width) is False,
    )
    report(
        'row_has_changed: all-different row returns True',
        row_has_changed(all_a, all_b, 0, width) is True,
    )

    mixed_current:  list = list(all_a)
    mixed_previous: list = list(all_a)
    mixed_current[width + 2] = cell_b   # only one cell in row 1 differs

    report(
        'row_has_changed: unchanged row 0 returns False',
        row_has_changed(mixed_current, mixed_previous, 0, width) is False,
    )
    report(
        'row_has_changed: changed row 1 returns True',
        row_has_changed(mixed_current, mixed_previous, width, width * 2) is True,
    )
    report(
        'row_has_changed: unchanged row 2 returns False',
        row_has_changed(mixed_current, mixed_previous, width * 2, count) is False,
    )

    # --- flush_diff swap postcondition ---------------------------------------

    current_cells:  list = [cell_a if (i % 2 == 0) else cell_b for i in range(count)]
    previous_cells: list = [BLANK_CELL] * count
    style_cache:    dict = build_style_cache()

    # redirect fd 1 to a pipe so the escape output does not disturb the screen
    read_fd: int
    write_fd: int
    read_fd, write_fd = os.pipe()
    saved_fd: int = os.dup(1)
    os.dup2(write_fd, 1)
    os.close(write_fd)

    flush_diff(current_cells, previous_cells, width, height, style_cache)

    os.dup2(saved_fd, 1)
    os.close(saved_fd)
    captured_bytes: bytes = os.read(read_fd, 65536)
    os.close(read_fd)

    report(
        'flush_diff: previous_cells == current_cells after swap',
        previous_cells == current_cells,
    )

    # --- no-op frame: identical current and previous -------------------------

    read_fd, write_fd = os.pipe()
    saved_fd = os.dup(1)
    os.dup2(write_fd, 1)
    os.close(write_fd)

    flush_diff(current_cells, previous_cells, width, height, style_cache)

    os.dup2(saved_fd, 1)
    os.close(saved_fd)
    noop_bytes: bytes = os.read(read_fd, 65536)
    os.close(read_fd)

    report(
        'flush_diff: identical grid emits only SGR reset',
        noop_bytes == b'\033[0m',
    )

    # --- summary -------------------------------------------------------------
    _sys.stderr.write(
        f'test_diff: {pass_count} passed, {fail_count} failed\n'
    )
    if fail_count > 0:
        _sys.exit(1)


# ==============================================================================
# REGIONS
# ==============================================================================
def scroll_region(region: dict, delta: int) -> None:
    max_offset: int = max(0, len(region['lines']) - region['height'])
    new_offset: int = region['scroll_offset'] + delta
    if new_offset < 0:
        new_offset = 0
    if new_offset > max_offset:
        new_offset = max_offset
    region['scroll_offset'] = new_offset

def page_region(region: dict, direction: int) -> None:
    # direction: +1 = page down, -1 = page up
    delta: int = (region['height'] - 1) * direction
    scroll_region(region, delta)

def render_region(
    region:        dict,
    current_cells: list,
    grid_width:    int,
    default_style: tuple[int, int, int],
) -> None:
    grid_height: int = len(current_cells) // grid_width

    region_top:    int  = region['top']
    region_left:   int  = region['left']
    region_width:  int  = region['width']
    region_height: int  = region['height']
    scroll_offset: int  = region['scroll_offset']
    lines:         list = region['lines']

    fg_color:  int = default_style[0]
    bg_color:  int = default_style[1]
    modifiers: int = default_style[2]

    for display_row in range(region_height):
        grid_row: int = region_top + display_row
        if grid_row < 0:
            continue
        if grid_row >= grid_height:
            break   # rows only increase; no further row can be in bounds

        source_line_index: int = display_row + scroll_offset

        line: str = ''
        if source_line_index >= 0:
            if source_line_index < len(lines):
                line = lines[source_line_index]

        for column in range(region_width):
            grid_col: int = region_left + column
            if grid_col < 0:
                continue
            if grid_col >= grid_width:
                break   # columns only increase; no further column can be in bounds

            cell_index: int = grid_row * grid_width + grid_col

            symbol: str
            if column < len(line):
                symbol = line[column]
            else:
                symbol = ' '

            current_cells[cell_index] = (symbol, fg_color, bg_color, modifiers)


# ==============================================================================
# INPUT / KEY PARSING
# ==============================================================================
import select


def write_events_to_ring(raw_bytes: bytes, app_state: dict) -> None:
    if RAW_LOG_PATH:
        log_file = open(RAW_LOG_PATH, 'ab')
        log_file.write(raw_bytes)
        log_file.close()

    ring:        list = app_state['event_ring']
    write_index: int  = app_state['ring_write_index']

    byte_index: int = 0
    while byte_index < len(raw_bytes):
        byte_value: int = raw_bytes[byte_index]

        if byte_value == 0x1B:
            # parse_escape_sequence controls how many bytes it consumes
            result_event: dict | None
            result_event, byte_index = parse_escape_sequence(raw_bytes, byte_index)
            if result_event is not None:
                ring[write_index] = result_event
                write_index = (write_index + 1) % RING_BUFFER_CAPACITY
            continue

        # for all non-escape bytes: advance past the current byte before classifying
        byte_index += 1
        event: dict | None = None

        if byte_value == 0x0D:
            # checked before ctrl range: 0x0D is inside 0x01-0x1A
            event = {
                'kind':      'enter',
                'char':      '',
                'raw':       bytes([byte_value]),
                'modifiers': 0,
            }
        elif byte_value == 0x7F:
            event = {
                'kind':      'backspace',
                'char':      '',
                'raw':       bytes([byte_value]),
                'modifiers': 0,
            }
        elif 0x20 <= byte_value <= 0x7E:
            # printable ASCII fast path
            event = {
                'kind':      'char',
                'char':      chr(byte_value),
                'raw':       bytes([byte_value]),
                'modifiers': 0,
            }
        elif 0x01 <= byte_value <= 0x1A:
            # ctrl+key: 0x01=ctrl+a ... 0x1A=ctrl+z
            # adding 0x60 maps to the lowercase letter: 0x01+0x60=0x61='a'
            event = {
                'kind':      'char',
                'char':      chr(byte_value + 0x60),
                'raw':       bytes([byte_value]),
                'modifiers': MOD_KEY_CTRL,
            }
        # other bytes: unrecognised, skip

        if event is not None:
            ring[write_index] = event
            write_index = (write_index + 1) % RING_BUFFER_CAPACITY

    app_state['ring_write_index'] = write_index

def read_event_from_ring(app_state: dict) -> dict | None:
    read_index:  int = app_state['ring_read_index']
    write_index: int = app_state['ring_write_index']

    if read_index == write_index:
        return None

    event: dict = app_state['event_ring'][read_index]
    app_state['ring_read_index'] = (read_index + 1) % RING_BUFFER_CAPACITY
    return event


def parse_escape_sequence(
    raw_bytes:   bytes,
    start_index: int,
) -> tuple[dict | None, int]:
    # start_index points to 0x1B.
    # returns (event_or_None, next_unprocessed_index).
    # caller must use the returned index, not advance independently.

    index: int = start_index + 1   # advance past 0x1B

    if index >= len(raw_bytes):
        # bare escape: nothing follows in this read
        event: dict = {
            'kind':      'escape',
            'char':      '',
            'raw':       b'\033',
            'modifiers': 0,
        }
        return event, index

    next_byte: int = raw_bytes[index]
    if next_byte == ord('O'):
        # SS3 sequence: \033 O <final>  (application cursor key mode)
        index += 1
        if index >= len(raw_bytes):
            return None, index
        ss3_final: int = raw_bytes[index]
        index += 1
        ss3_kind: str = ''
        if ss3_final == ord('A'):
            ss3_kind = 'arrow_up'
        elif ss3_final == ord('B'):
            ss3_kind = 'arrow_down'
        elif ss3_final == ord('C'):
            ss3_kind = 'arrow_right'
        elif ss3_final == ord('D'):
            ss3_kind = 'arrow_left'
        if not ss3_kind:
            return None, index
        ss3_event: dict = {
            'kind':      ss3_kind,
            'char':      '',
            'raw':       raw_bytes[start_index:index],
            'modifiers': 0,
        }
        return ss3_event, index

    if next_byte != ord('['):
        # not a CSI sequence; emit escape, leave next_byte for next iteration
        event = {
            'kind':      'escape',
            'char':      '',
            'raw':       b'\033',
            'modifiers': 0,
        }
        return event, index   # do not consume next_byte

    index += 1   # consume '['

    # collect parameter bytes: digits and semicolons
    param_chars: list = []
    while index < len(raw_bytes):
        current_byte: int = raw_bytes[index]
        is_digit:     bool = ord('0') <= current_byte <= ord('9')
        is_semicolon: bool = current_byte == ord(';')
        if is_digit or is_semicolon:
            param_chars.append(chr(current_byte))
            index += 1
        else:
            break

    if index >= len(raw_bytes):
        # incomplete CSI sequence; skip consumed bytes
        return None, index

    final_byte: int = raw_bytes[index]
    index += 1

    param_string: str = ''.join(param_chars)
    params: list = param_string.split(';') if param_string else []

    # decode XTerm modifier parameter from second field if present.
    # XTerm encodes: modifier_value = (shift<<0)|(alt<<1)|(ctrl<<2)|(super<<3), then +1.
    # our MOD_KEY_* bits differ from XTerm bit positions so we map explicitly.
    modifiers: int = 0
    if len(params) >= 2:
        modifier_param: int = 0
        try:
            modifier_param = int(params[1])
        except ValueError:
            pass
        xterm_bits: int = modifier_param - 1
        if xterm_bits & 1:
            modifiers = modifiers | MOD_KEY_SHIFT
        if xterm_bits & 2:
            modifiers = modifiers | MOD_KEY_ALT
        if xterm_bits & 4:
            modifiers = modifiers | MOD_KEY_CTRL
        if xterm_bits & 8:
            modifiers = modifiers | MOD_KEY_SUPER

    first_param: str = params[0] if params else ''
    raw_slice:   bytes = raw_bytes[start_index:index]

    kind: str = ''

    if final_byte == ord('A'):
        kind = 'arrow_up'
    elif final_byte == ord('B'):
        kind = 'arrow_down'
    elif final_byte == ord('C'):
        kind = 'arrow_right'
    elif final_byte == ord('D'):
        kind = 'arrow_left'
    elif final_byte == ord('H'):
        kind = 'home'
    elif final_byte == ord('F'):
        kind = 'end'
    elif final_byte == ord('~'):
        if first_param == '1' or first_param == '7':
            kind = 'home'
        elif first_param == '4' or first_param == '8':
            kind = 'end'
        elif first_param == '5':
            kind = 'page_up'
        elif first_param == '6':
            kind = 'page_down'

    if not kind:
        # unrecognised CSI sequence; skip
        return None, index

    event = {
        'kind':      kind,
        'char':      '',
        'raw':       raw_slice,
        'modifiers': modifiers,
    }
    return event, index


# ==============================================================================
# APPLICATION STATE AND EVENT LOOP
# ==============================================================================

def handle_input_submit(app_state: dict) -> None:
    # stub: called when enter is pressed in MODE_INPUT
    submitted: str = app_state['input_buffer']
    app_state['input_buffer'] = ''
    app_state['mode'] = MODE_NORMAL
    _ = submitted   # placeholder until commit 10 wires this up

def handle_command(command: str, app_state: dict) -> None:
    # stub: called when enter is pressed in MODE_COMMAND
    app_state['command_buffer'] = ''
    app_state['mode'] = MODE_NORMAL
    _ = command   # placeholder until commit 11 wires this up

def cycle_focus(app_state: dict) -> None:
    region_order: list = app_state['region_order']
    if not region_order:
        return
    current_id: int = app_state['focused_region_id']
    # clear is_focused on the previously focused region
    if current_id != NO_REGION:
        if current_id in app_state['regions']:
            app_state['regions'][current_id]['is_focused'] = False
    # find current position and advance
    next_id: int = region_order[0]
    found_index: int = -1
    for list_index in range(len(region_order)):
        if region_order[list_index] == current_id:
            found_index = list_index
            break
    if found_index != -1:
        next_index: int = (found_index + 1) % len(region_order)
        next_id = region_order[next_index]
    app_state['focused_region_id'] = next_id
    app_state['regions'][next_id]['is_focused'] = True

ACTION_TABLE: dict[str, callable] = {
    # populated in commit 12
}


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
    default_style: tuple[int, int, int] = (COLOR_TAG_IDX | 15, COLOR_DEFAULT, 0)
    header_lines: list = ['[ TUI ] arrows scroll  /=command  q=quit  scroll=0 focused=1']
    content_lines: list = []
    for line_number in range(1, 51):
        content_lines.append(f'line {line_number:02d}  ' + ('- ' * 20))
    header_region_id:  int = 0
    content_region_id: int = 1
    header_region: dict = {
        **DEFAULT_REGION,
        'region_id':  header_region_id,
        'name':       'header',
        'top':        0,
        'left':       0,
        'width':      grid_width,
        'height':     1,
        'lines':      header_lines,
        'is_focused': False,
    }
    content_region: dict = {
        **DEFAULT_REGION,
        'region_id':  content_region_id,
        'name':       'content',
        'top':        1,
        'left':       0,
        'width':      grid_width,
        'height':     grid_height - 1,
        'lines':      content_lines,
        'is_focused': True,
    }

    debug_lines: list = ['tab debug: waiting...']
    debug_region_height: int = 4
    debug_region: dict = {
        **DEFAULT_REGION,
        'region_id':  2,
        'name':       'tab_debug',
        'top':        grid_height - debug_region_height,
        'left':       0,
        'width':      grid_width,
        'height':     debug_region_height,
        'lines':      debug_lines,
        'is_focused': False,
    }
    # shrink content region to leave room for debug region
    content_region['height'] = grid_height - 1 - debug_region_height

    app_state: dict = {
        'mode':              MODE_NORMAL,
        'focused_region_id': content_region_id,
        'regions':           {
            header_region_id:  header_region,
            content_region_id: content_region,
            2:                 debug_region,
        },
        'region_order':      [header_region_id, content_region_id, 2],
        'input_buffer':      '',
        'command_buffer':    '',
        'pending_action':    '',
        'style_cache':       build_style_cache(),
        'event_ring':        [None] * RING_BUFFER_CAPACITY,
        'ring_write_index':  0,
        'ring_read_index':   0,
        'last_event_kind':   'none',
        'last_event_mods':   0,
        'last_event_char':   '',
        'tab_debug_log':     debug_lines,
    }

    stdin_fd: int = sys.stdin.fileno()
    while True:
        ready_fds: list
        ready_fds, _, _ = select.select([sys.stdin], [], [], 0.05)
        if ready_fds:
            raw_bytes: bytes = os.read(stdin_fd, 256)
            write_events_to_ring(raw_bytes, app_state)
        event: dict | None = read_event_from_ring(app_state)
        while event is not None:
            current_mode: str = app_state['mode']
            event_kind:   str = event['kind']
            event_char:   str = event['char']
            event_mods:   int = event['modifiers']
            focused_id:   int = app_state['focused_region_id']
            app_state['last_event_kind'] = event_kind
            app_state['last_event_mods'] = event_mods
            app_state['last_event_char'] = event_char

            if current_mode == MODE_NORMAL:
                is_q:      bool = event_kind == 'char' and event_char == 'q' and event_mods == 0
                is_ctrl_c: bool = event_kind == 'char' and event_char == 'c' and event_mods == MOD_KEY_CTRL
                if is_q or is_ctrl_c:
                    app_state['mode'] = MODE_QUITTING
                elif event_kind == 'arrow_up' and event_mods == 0:
                    if focused_id != NO_REGION:
                        scroll_region(app_state['regions'][focused_id], -1)
                elif event_kind == 'arrow_down' and event_mods == 0:
                    if focused_id != NO_REGION:
                        scroll_region(app_state['regions'][focused_id], 1)
                elif event_kind == 'page_up' and event_mods == 0:
                    if focused_id != NO_REGION:
                        page_region(app_state['regions'][focused_id], -1)
                elif event_kind == 'page_down' and event_mods == 0:
                    if focused_id != NO_REGION:
                        page_region(app_state['regions'][focused_id], 1)
                elif event_kind == 'home' and event_mods == 0:
                    if focused_id != NO_REGION:
                        scroll_region(app_state['regions'][focused_id], -50000)
                elif event_kind == 'end' and event_mods == 0:
                    if focused_id != NO_REGION:
                        scroll_region(app_state['regions'][focused_id], 50000)
                elif event_kind == 'char' and event_char == 'i' and event_mods == MOD_KEY_CTRL:
                    # Tab arrives as ctrl+i (0x09) through the ctrl range classifier
                    before_id: int = app_state['focused_region_id']
                    cycle_focus(app_state)
                    after_id: int = app_state['focused_region_id']
                    tab_entry: str = (
                        f'tab: before={before_id} after={after_id}'
                        f'  order={app_state["region_order"]}'
                        f'  is_focused='
                        + str({
                            rid: app_state['regions'][rid]['is_focused']
                            for rid in app_state['region_order']
                        })
                    )
                    app_state['tab_debug_log'].append(tab_entry)
                elif event_kind == 'char' and event_char == '/' and event_mods == 0:
                    app_state['mode'] = MODE_COMMAND
            elif current_mode == MODE_QUITTING:
                pass   # drain remaining events; outer check breaks the main loop
            elif current_mode == MODE_INPUT:
                pass   # stub; wired in commit 10
            elif current_mode == MODE_COMMAND:
                pass   # stub; wired in commit 11
            elif current_mode == MODE_CONFIRM:
                pass   # stub; wired in commit 12
            event = read_event_from_ring(app_state)
        if app_state['mode'] == MODE_QUITTING:
            break

        # update header diagnostic before render
        focused_region_id_now: int = app_state['focused_region_id']
        scroll_offset_now: int = 0
        if focused_region_id_now != NO_REGION:
            scroll_offset_now = app_state['regions'][focused_region_id_now]['scroll_offset']
        last_kind: str = app_state['last_event_kind']
        last_mods: int = app_state['last_event_mods']
        last_char: str = app_state['last_event_char']
        header_lines[0] = (
            f'[ TUI ] q=quit  scroll={scroll_offset_now}'
            f'  evt={last_kind} ch={last_char!r} mod={last_mods}'
        )

        # render pass: clear grid, render each region, flush diff
        for cell_index in range(cell_count):
            grid['current'][cell_index] = BLANK_CELL
        for region_id in app_state['region_order']:
            region: dict = app_state['regions'][region_id]
            render_region(region, grid['current'], grid_width, default_style)
        flush_diff(
            grid['current'],
            grid['previous'],
            grid_width,
            grid_height,
            app_state['style_cache'],
        )
    restore_terminal(terminal)
    print("ok")

if __name__ == '__main__':
    test_diff()
    main()
