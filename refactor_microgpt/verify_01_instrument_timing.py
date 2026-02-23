"""
verify_01_instrument_timing.py

Verifies COMMIT 1: INSTRUMENT flag and phase timing.

PASS criteria:
  1. With INSTRUMENT=True, each step prints a timing line containing
     "fwd:", "bwd:", and "adam:" substrings.
  2. All three timing values parse as non-negative floats.
  3. The training loss line ("step ... | loss ...") is still present
     and unchanged in format.
  4. With INSTRUMENT=False (default), no timing line is printed.

Usage:
  python verify_01_instrument_timing.py
"""

import subprocess
import sys
import re
import os

SOURCE_FILE: str = 'refactor_microgpt.py'
TEMP_FILE: str = '_verify_temp_01.py'
STEPS_TO_CHECK: int = 3


def run_gpt(instrument_enabled: bool, num_steps: int) -> list[str]:
    """Run SOURCE_FILE with the given INSTRUMENT setting and return stdout lines."""
    patch_instrument: str = "True" if instrument_enabled else "False"
    patch_steps: str = str(num_steps)

    with open(SOURCE_FILE, 'r') as source_file:
        source_text: str = source_file.read()

    patched_text: str = re.sub(
        r'^INSTRUMENT:\s*bool\s*=\s*(True|False)',
        f'INSTRUMENT: bool = {patch_instrument}',
        source_text,
        flags=re.MULTILINE
    )
    patched_text = re.sub(
        r'^num_steps:\s*int\s*=\s*\d+',
        f'num_steps: int = {patch_steps}',
        patched_text,
        flags=re.MULTILINE
    )

    with open(TEMP_FILE, 'w') as temp_file:
        temp_file.write(patched_text)

    result: subprocess.CompletedProcess = subprocess.run(
        [sys.executable, TEMP_FILE],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("FAIL: script exited with non-zero return code.")
        print(result.stderr)
        sys.exit(1)

    return result.stdout.splitlines()


def extract_step_lines(lines: list[str]) -> list[str]:
    """Return only lines matching the training step loss format."""
    step_lines: list[str] = []
    for line in lines:
        if re.match(r'^\s*step\s+\d+\s*/\s*\d+\s*\|\s*loss\s+[\d.]+', line):
            step_lines.append(line)
    return step_lines


def extract_timing_lines(lines: list[str]) -> list[str]:
    """Return only lines that contain timing output."""
    timing_lines: list[str] = []
    for line in lines:
        if 'fwd:' in line or 'bwd:' in line or 'adam:' in line:
            timing_lines.append(line)
    return timing_lines


def check_timing_line(line: str) -> None:
    """Assert a timing line contains fwd/bwd/adam and all values are non-negative floats."""
    assert 'fwd:' in line, f"FAIL: 'fwd:' not found in timing line: {line!r}"
    assert 'bwd:' in line, f"FAIL: 'bwd:' not found in timing line: {line!r}"
    assert 'adam:' in line, f"FAIL: 'adam:' not found in timing line: {line!r}"

    float_pattern: re.Pattern = re.compile(r'(fwd|bwd|adam):\s*([\d.]+(?:e[+-]?\d+)?)')
    matches: list[tuple[str, str]] = float_pattern.findall(line)

    assert len(matches) == 3, (
        f"FAIL: expected 3 timing values, found {len(matches)} in: {line!r}"
    )

    for label, value_str in matches:
        parsed_value: float = float(value_str)
        assert parsed_value >= 0.0, (
            f"FAIL: timing value for '{label}' is negative ({parsed_value}) in: {line!r}"
        )


def main() -> None:
    print("--- verify_01_instrument_timing ---")

    # Test 1: INSTRUMENT=True produces timing lines
    print(f"\n[1] Running {STEPS_TO_CHECK} steps with INSTRUMENT=True ...")
    lines_on: list[str] = run_gpt(instrument_enabled=True, num_steps=STEPS_TO_CHECK)

    step_lines_on: list[str] = extract_step_lines(lines_on)
    timing_lines_on: list[str] = extract_timing_lines(lines_on)

    assert len(step_lines_on) == STEPS_TO_CHECK, (
        f"FAIL: expected {STEPS_TO_CHECK} step lines, got {len(step_lines_on)}"
    )
    print(f"  step lines found: {len(step_lines_on)} [OK]")

    assert len(timing_lines_on) == STEPS_TO_CHECK, (
        f"FAIL: expected {STEPS_TO_CHECK} timing lines, got {len(timing_lines_on)}"
    )
    print(f"  timing lines found: {len(timing_lines_on)} [OK]")

    for timing_line in timing_lines_on:
        check_timing_line(timing_line)
    print("  all timing values are non-negative floats [OK]")

    # Test 2: INSTRUMENT=False produces no timing lines
    print(f"\n[2] Running {STEPS_TO_CHECK} steps with INSTRUMENT=False ...")
    lines_off: list[str] = run_gpt(instrument_enabled=False, num_steps=STEPS_TO_CHECK)

    timing_lines_off: list[str] = extract_timing_lines(lines_off)
    assert len(timing_lines_off) == 0, (
        f"FAIL: expected 0 timing lines with INSTRUMENT=False, got {len(timing_lines_off)}"
    )
    print(f"  no timing lines printed [OK]")

    step_lines_off: list[str] = extract_step_lines(lines_off)
    assert len(step_lines_off) == STEPS_TO_CHECK, (
        f"FAIL: expected {STEPS_TO_CHECK} step lines with INSTRUMENT=False, "
        f"got {len(step_lines_off)}"
    )
    print(f"  step lines still present: {len(step_lines_off)} [OK]")

    # Test 3: Loss lines are identical between INSTRUMENT=True and INSTRUMENT=False
    print("\n[3] Checking loss line consistency across INSTRUMENT settings ...")
    for index in range(STEPS_TO_CHECK):
        assert step_lines_on[index] == step_lines_off[index], (
            f"FAIL: step line mismatch at step {index + 1}:\n"
            f"  INSTRUMENT=True:  {step_lines_on[index]!r}\n"
            f"  INSTRUMENT=False: {step_lines_off[index]!r}"
        )
    print("  loss lines identical [OK]")

    print("\n--- PASS ---")

    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)


if __name__ == '__main__':
    main()
