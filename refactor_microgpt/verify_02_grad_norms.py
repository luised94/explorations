"""
verify_02_grad_norms.py

Verifies COMMIT 2: tape node count and per-parameter gradient norm reporting.

PASS criteria:
  1. With INSTRUMENT=True, each step prints a grad norm line containing
     "tape nodes:" and "grad norms:" substrings.
  2. Gradient norms for "wte", "attn_wq", and "lm_head" are present
     in the output.
  3. All norm values parse as finite positive floats (no NaN, no Inf,
     no zero -- gradients must be flowing).
  4. The training loss line format is unchanged.
  5. With INSTRUMENT=False, no grad norm line is printed.

Usage:
  python verify_02_grad_norms.py
"""

import subprocess
import sys
import re
import os
import math

SOURCE_FILE: str = 'refactor_microgpt.py'
TEMP_FILE: str = '_verify_temp_02.py'
STEPS_TO_CHECK: int = 3

REQUIRED_PARAM_NAMES: list[str] = ['wte', 'attn_wq', 'lm_head']


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


def extract_grad_norm_lines(lines: list[str]) -> list[str]:
    """Return only lines that contain grad norm output."""
    grad_norm_lines: list[str] = []
    for line in lines:
        if 'tape nodes:' in line and 'grad norms:' in line:
            grad_norm_lines.append(line)
    return grad_norm_lines


def parse_norm_values(line: str) -> dict[str, float]:
    """Parse all name:value pairs from a grad norm line into a dict."""
    norm_pattern: re.Pattern = re.compile(r'([\w.]+):([\d.]+(?:e[+-]?\d+)?)')
    parsed: dict[str, float] = {}
    for name, value_str in norm_pattern.findall(line):
        parsed[name] = float(value_str)
    return parsed


def check_grad_norm_line(line: str) -> dict[str, float]:
    """Assert structure and return the parsed norm dict for further checks."""
    assert 'tape nodes:' in line, (
        f"FAIL: 'tape nodes:' not found in line: {line!r}"
    )
    assert 'grad norms:' in line, (
        f"FAIL: 'grad norms:' not found in line: {line!r}"
    )

    tape_node_match: re.Match = re.search(r'tape nodes:\s*(\d+)', line)
    assert tape_node_match is not None, (
        f"FAIL: could not parse tape node count from: {line!r}"
    )
    tape_node_count: int = int(tape_node_match.group(1))
    assert tape_node_count > 0, (
        f"FAIL: tape node count is zero in: {line!r}"
    )

    norm_values: dict[str, float] = parse_norm_values(line)
    return norm_values


def main() -> None:
    print("--- verify_02_grad_norms ---")

    # Test 1: INSTRUMENT=True produces grad norm lines with required params
    print(f"\n[1] Running {STEPS_TO_CHECK} steps with INSTRUMENT=True ...")
    lines_on: list[str] = run_gpt(instrument_enabled=True, num_steps=STEPS_TO_CHECK)

    grad_norm_lines: list[str] = extract_grad_norm_lines(lines_on)
    assert len(grad_norm_lines) == STEPS_TO_CHECK, (
        f"FAIL: expected {STEPS_TO_CHECK} grad norm lines, got {len(grad_norm_lines)}"
    )
    print(f"  grad norm lines found: {len(grad_norm_lines)} [OK]")

    # Test 2: Required parameter names appear in every grad norm line
    print(f"\n[2] Checking required parameter names appear in every step ...")
    for step_index, grad_norm_line in enumerate(grad_norm_lines):
        norm_values: dict[str, float] = check_grad_norm_line(grad_norm_line)
        for required_name in REQUIRED_PARAM_NAMES:
            found: bool = False
            for key in norm_values:
                if required_name in key:
                    found = True
                    break
            assert found, (
                f"FAIL: required param '{required_name}' not found in step "
                f"{step_index + 1} grad norm line: {grad_norm_line!r}"
            )
    print(f"  all required params present: {REQUIRED_PARAM_NAMES} [OK]")

    # Test 3: All norm values are finite and positive (gradients are flowing)
    print(f"\n[3] Checking all norm values are finite and positive ...")
    for step_index, grad_norm_line in enumerate(grad_norm_lines):
        norm_values: dict[str, float] = parse_norm_values(grad_norm_line)
        for param_name, norm_value in norm_values.items():
            assert math.isfinite(norm_value), (
                f"FAIL: norm for '{param_name}' is not finite ({norm_value}) "
                f"at step {step_index + 1}"
            )
            assert norm_value > 0.0, (
                f"FAIL: norm for '{param_name}' is zero or negative ({norm_value}) "
                f"at step {step_index + 1} -- gradients may not be flowing"
            )
    print("  all norm values are finite and positive [OK]")

    # Test 4: Loss line format is unchanged
    print(f"\n[4] Checking loss line format is unchanged ...")
    step_lines: list[str] = extract_step_lines(lines_on)
    assert len(step_lines) == STEPS_TO_CHECK, (
        f"FAIL: expected {STEPS_TO_CHECK} step lines, got {len(step_lines)}"
    )
    print(f"  step loss lines present: {len(step_lines)} [OK]")

    # Test 5: INSTRUMENT=False produces no grad norm lines
    print(f"\n[5] Running {STEPS_TO_CHECK} steps with INSTRUMENT=False ...")
    lines_off: list[str] = run_gpt(instrument_enabled=False, num_steps=STEPS_TO_CHECK)

    grad_norm_lines_off: list[str] = extract_grad_norm_lines(lines_off)
    assert len(grad_norm_lines_off) == 0, (
        f"FAIL: expected 0 grad norm lines with INSTRUMENT=False, "
        f"got {len(grad_norm_lines_off)}"
    )
    print(f"  no grad norm lines printed [OK]")

    print("\n--- PASS ---")

    if os.path.exists(TEMP_FILE):
        os.remove(TEMP_FILE)


if __name__ == '__main__':
    main()
