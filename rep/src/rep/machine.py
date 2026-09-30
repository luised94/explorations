"""Machine context: where this machine keeps rep's data, and which device it is.

REPRESENTATION
  MachineContext (TypedDict), built once per process by resolve_machine_context:
    data_root            absolute path of the synced data folder (PLAN.md D3)
    data_root_source     the rule that chose it: "flag", "environment", "default"
    data_root_exists     whether that folder exists right now
    config_directory     machine-local, never synced: $XDG_CONFIG_HOME/rep
    local_config_path    config_directory / "local.toml"
    state_directory      machine-local, never synced: $XDG_STATE_HOME/rep
    device_id            DEVICE_ID_LENGTH characters of DEVICE_ID_ALPHABET
    bib_path             absolute path, or None when not set
    kbd_root             absolute path, or None when not set
    warnings             human-readable problems that do not stop the program

INVARIANTS
  M1  device_id matches DEVICE_ID_PATTERN.
  M2  local.toml is created at most once, atomically, and rep never rewrites
      it afterwards, so a device keeps its identity (and its events file).
  M3  config_directory and state_directory are not inside data_root: those
      files must never reach the other device through folder sync.
  M4  Every path in the context is absolute.

Problems the person must fix raise MachineContextError with the path involved.
Programmer bugs are asserts.
"""

import os
import re
import secrets
import tomllib
from collections.abc import Mapping
from pathlib import Path
from typing import TypedDict


# Lowercase Crockford base32: no i, l, o, u, so an ID read aloud or typed by
# hand cannot confuse 1/l or 0/o. The same alphabet is used for item IDs (M2).
DEVICE_ID_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
# 10 characters = 50 bits: collision between two devices is not a real risk.
DEVICE_ID_LENGTH = 10
DEVICE_ID_PATTERN = re.compile(r"^[0-9abcdefghjkmnpqrstvwxyz]{10}$")

LOCAL_CONFIG_KNOWN_KEYS = ("device_id", "bib_path", "kbd_root")


class MachineContextError(Exception):
    """A problem in the machine's setup that the person has to fix."""


class MachineContext(TypedDict):
    data_root: Path
    data_root_source: str
    data_root_exists: bool
    config_directory: Path
    local_config_path: Path
    state_directory: Path
    device_id: str
    bib_path: Path | None
    kbd_root: Path | None
    warnings: list[str]


def resolve_machine_context(
    data_root_flag: str | None,
    environment: Mapping[str, str],
    home_directory: Path,
) -> MachineContext:
    """Resolve paths and device identity, creating local.toml on first run.

    PRE   home_directory is absolute. environment is the process environment
          (passed in, not read from os.environ, so tests control it).
    POST  the returned context satisfies M1-M4. local.toml exists. Nothing
          under data_root has been created or changed.
    """
    assert home_directory.is_absolute(), "home_directory must be absolute"

    # --- data root: flag, then REP_DATA_ROOT, then ~/learning (PLAN.md D3) ---
    # Relative values are taken against the current directory, the way any
    # command-line path is; "~" is expanded because a quoted "~/x" reaches us
    # unexpanded from the shell.
    environment_data_root = environment.get("REP_DATA_ROOT", "")
    if data_root_flag is not None and data_root_flag != "":
        data_root = Path(data_root_flag).expanduser().absolute()
        data_root_source = "flag"
    elif environment_data_root != "":
        data_root = Path(environment_data_root).expanduser().absolute()
        data_root_source = "environment"
    else:
        data_root = home_directory / "learning"
        data_root_source = "default"

    # --- machine-local directories, following the XDG base directory spec ---
    # The spec says an empty or relative XDG value must be ignored.
    xdg_config_home = environment.get("XDG_CONFIG_HOME", "")
    if xdg_config_home != "" and Path(xdg_config_home).is_absolute():
        config_directory = Path(xdg_config_home) / "rep"
    else:
        config_directory = home_directory / ".config" / "rep"
    xdg_state_home = environment.get("XDG_STATE_HOME", "")
    if xdg_state_home != "" and Path(xdg_state_home).is_absolute():
        state_directory = Path(xdg_state_home) / "rep"
    else:
        state_directory = home_directory / ".local" / "state" / "rep"
    local_config_path = config_directory / "local.toml"

    # M3: checked before anything is written, so a misconfigured data root
    # never receives a device identity that would then sync to the other
    # machine.
    for machine_local_directory in (config_directory, state_directory):
        if machine_local_directory.is_relative_to(data_root):
            raise MachineContextError(
                f"{machine_local_directory} is inside the data root {data_root}; "
                "machine-local files would sync to the other device. "
                "Move the data root or set XDG_CONFIG_HOME / XDG_STATE_HOME."
            )

    # --- first run: create local.toml exactly once (M2) ---
    # Written to a temporary file, then hard-linked into place: os.link fails
    # if the target exists, so two processes starting together cannot both
    # install an identity. The loser discards its file and reads the winner's.
    if not local_config_path.exists():
        config_directory.mkdir(parents=True, exist_ok=True)
        # Each random byte picks one character. 256 is a multiple of the
        # 32-character alphabet, so the modulo keeps every character equally
        # likely.
        assert 256 % len(DEVICE_ID_ALPHABET) == 0, "alphabet size must divide 256"
        new_device_id = "".join(
            DEVICE_ID_ALPHABET[random_byte % len(DEVICE_ID_ALPHABET)]
            for random_byte in secrets.token_bytes(DEVICE_ID_LENGTH)
        )
        assert DEVICE_ID_PATTERN.match(new_device_id), "generated device id is malformed"
        first_run_text = (
            "# rep machine-local settings. Never synced. Written once on first run.\n"
            "# device_id names this machine's events file; do not change it.\n"
            f'device_id = "{new_device_id}"\n'
            "\n"
            "# Uncomment and edit when M2 needs them:\n"
            '# bib_path = "~/personal_repos/usb-repos/kbd/zotero_library.bib"\n'
            '# kbd_root = "~/personal_repos/usb-repos/kbd"\n'
        )
        temporary_path = config_directory / f".local.toml.{os.getpid()}.tmp"
        temporary_path.write_text(first_run_text, encoding="utf-8")
        try:
            os.link(temporary_path, local_config_path)
        except FileExistsError:
            pass
        finally:
            temporary_path.unlink()

    # --- read local.toml: one path for both first run and later runs ---
    try:
        with local_config_path.open("rb") as local_config_file:
            local_config = tomllib.load(local_config_file)
    except tomllib.TOMLDecodeError as decode_error:
        raise MachineContextError(f"{local_config_path}: {decode_error}") from decode_error

    warnings: list[str] = []
    for key in local_config:
        if key not in LOCAL_CONFIG_KNOWN_KEYS:
            warnings.append(f"{local_config_path}: unknown key '{key}' ignored")

    device_id = local_config.get("device_id")
    if not isinstance(device_id, str) or DEVICE_ID_PATTERN.match(device_id) is None:
        raise MachineContextError(
            f"{local_config_path}: device_id must be {DEVICE_ID_LENGTH} characters "
            f"from '{DEVICE_ID_ALPHABET}', found {device_id!r}"
        )

    # bib_path and kbd_root are optional; when present they must be strings
    # naming absolute paths after "~" expansion (M4). A relative path would
    # silently mean different files depending on where rep was started.
    optional_paths: dict[str, Path | None] = {"bib_path": None, "kbd_root": None}
    for key in optional_paths:
        raw_value = local_config.get(key)
        if raw_value is None:
            continue
        if not isinstance(raw_value, str):
            raise MachineContextError(f"{local_config_path}: {key} must be a string")
        expanded_path = Path(raw_value).expanduser()
        if not expanded_path.is_absolute():
            raise MachineContextError(
                f"{local_config_path}: {key} must be an absolute path or start with ~, "
                f"found {raw_value!r}"
            )
        optional_paths[key] = expanded_path

    return {
        "data_root": data_root,
        "data_root_source": data_root_source,
        "data_root_exists": data_root.is_dir(),
        "config_directory": config_directory,
        "local_config_path": local_config_path,
        "state_directory": state_directory,
        "device_id": device_id,
        "bib_path": optional_paths["bib_path"],
        "kbd_root": optional_paths["kbd_root"],
        "warnings": warnings,
    }
