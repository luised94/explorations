"""The command shell's own logic, run in-process where a subprocess cannot control it.

The smoke tests (test_smoke.py) prove the installed command works end to end;
they cannot fix the random source, so a check that depends on which id is
drawn is made here through main() with the draws chosen by the test.
"""

import io
import os
import subprocess
import sys
from pathlib import Path

import pytest

from rep import cli
from rep.machine import DEVICE_ID_ALPHABET


def test_stamp_redraws_an_id_used_in_another_library_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    library_directory = tmp_path / "learning" / "library"
    library_directory.mkdir(parents=True)
    (library_directory / "other.md").write_text("### Q: Km?\nid: km-aaaa\nA: x\n", encoding="utf-8")

    # secrets is one shared module, so the patch below also reaches the
    # first-run device id in machine.py; an existing local.toml keeps that
    # draw from happening at all.
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text('device_id = "6a2ah35zhe"\n', encoding="utf-8")

    # The first suffix drawn is the one another file already uses; the second
    # is free. Twelve-byte draws are event ids; any other size is a draw this
    # test did not plan for, and fails loudly.
    suffix_draws = ["aaaa", "bbbb"]

    def chosen_token_bytes(count: int) -> bytes:
        if count == 12:
            return bytes(range(12))
        assert count == 4, f"unexpected draw of {count} bytes"
        return bytes(DEVICE_ID_ALPHABET.index(character) for character in suffix_draws.pop(0))

    monkeypatch.setattr(cli.secrets, "token_bytes", chosen_token_bytes)
    monkeypatch.setenv("HOME", str(tmp_path))
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        monkeypatch.delenv(variable, raising=False)
    standard_output = io.BytesIO()
    monkeypatch.setattr(sys, "stdin", io.TextIOWrapper(io.BytesIO(b"### Q: Km?\nA: y\n")))
    monkeypatch.setattr(sys, "stdout", io.TextIOWrapper(standard_output))

    exit_code = cli.main(["stamp"])
    sys.stdout.flush()
    assert exit_code == 0
    assert standard_output.getvalue() == b"### Q: Km?\nid: km-bbbb\nA: y\n"
    assert suffix_draws == []


def test_the_commands_nvim_runs_never_load_the_display_package(tmp_path: Path) -> None:
    # PLAN.md D46: pyutils is imported by the session and review only, so a
    # fault in it cannot break stamp on save or lint through :make. A fresh
    # interpreter, so no other test's imports count.
    (tmp_path / "learning").mkdir()
    script = (
        "import io, sys\n"
        "from rep.cli import main\n"
        "sys.stdin = io.TextIOWrapper(io.BytesIO(b'### Q: q\\nA: x\\n'))\n"
        "exit_codes = [main(['stamp']), main(['lint'])]\n"
        "print(exit_codes, 'pyutils' in sys.modules, file=sys.stderr)\n"
    )
    environment = {**os.environ, "HOME": str(tmp_path)}
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME"):
        environment.pop(variable, None)
    result = subprocess.run([sys.executable, "-c", script], env=environment, capture_output=True, check=False)
    assert result.stderr.decode().splitlines()[-1] == "[0, 0] False", result.stderr
