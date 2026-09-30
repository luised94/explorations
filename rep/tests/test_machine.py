"""Behavior of resolve_machine_context at its contract: paths, identity, errors.

Every test passes its own home directory and environment, so nothing here
reads or writes the real ~/.config or ~/learning.
"""

from pathlib import Path

import pytest

from rep.machine import DEVICE_ID_PATTERN, MachineContextError, resolve_machine_context


def test_default_data_root_is_learning_under_home(tmp_path: Path) -> None:
    machine_context = resolve_machine_context(None, {}, tmp_path)
    assert machine_context["data_root"] == tmp_path / "learning"
    assert machine_context["data_root_source"] == "default"
    assert machine_context["data_root_exists"] is False


def test_flag_beats_environment_beats_default(tmp_path: Path) -> None:
    environment = {"REP_DATA_ROOT": str(tmp_path / "from_environment")}
    from_environment = resolve_machine_context(None, environment, tmp_path)
    assert from_environment["data_root"] == tmp_path / "from_environment"
    assert from_environment["data_root_source"] == "environment"
    from_flag = resolve_machine_context(str(tmp_path / "from_flag"), environment, tmp_path)
    assert from_flag["data_root"] == tmp_path / "from_flag"
    assert from_flag["data_root_source"] == "flag"


def test_empty_environment_value_falls_back_to_default(tmp_path: Path) -> None:
    machine_context = resolve_machine_context(None, {"REP_DATA_ROOT": ""}, tmp_path)
    assert machine_context["data_root_source"] == "default"


def test_resolving_never_creates_the_data_root(tmp_path: Path) -> None:
    resolve_machine_context(None, {}, tmp_path)
    assert not (tmp_path / "learning").exists()


def test_first_run_creates_identity_and_later_runs_keep_it(tmp_path: Path) -> None:
    first_context = resolve_machine_context(None, {}, tmp_path)
    local_config_path = tmp_path / ".config" / "rep" / "local.toml"
    assert first_context["local_config_path"] == local_config_path
    assert DEVICE_ID_PATTERN.match(first_context["device_id"]) is not None
    bytes_after_first_run = local_config_path.read_bytes()
    second_context = resolve_machine_context(None, {}, tmp_path)
    assert second_context["device_id"] == first_context["device_id"]
    # M2: rep never rewrites local.toml once it exists.
    assert local_config_path.read_bytes() == bytes_after_first_run
    # The temporary file used for the atomic create is gone.
    leftover_files = [path.name for path in local_config_path.parent.iterdir()]
    assert leftover_files == ["local.toml"]


def test_existing_local_config_is_read_with_home_expanded(tmp_path: Path) -> None:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text(
        'device_id = "abcdefghjk"\n'
        'bib_path = "/data/zotero_library.bib"\n'
        'kbd_root = "~/kbd"\n',
        encoding="utf-8",
    )
    machine_context = resolve_machine_context(None, {"HOME": str(tmp_path)}, tmp_path)
    assert machine_context["device_id"] == "abcdefghjk"
    assert machine_context["bib_path"] == Path("/data/zotero_library.bib")
    # expanduser reads the real process HOME, not our environment mapping, so
    # only assert what is independent of it: the result is absolute.
    kbd_root = machine_context["kbd_root"]
    assert kbd_root is not None and kbd_root.is_absolute() and kbd_root.name == "kbd"


def test_malformed_local_config_names_the_file(tmp_path: Path) -> None:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text("device_id = \n", encoding="utf-8")
    with pytest.raises(MachineContextError, match="local.toml"):
        resolve_machine_context(None, {}, tmp_path)


@pytest.mark.parametrize(
    "bad_device_line",
    [
        'device_id = "short"',
        'device_id = "ABCDEFGHJK"',  # uppercase is outside the alphabet
        'device_id = "abcdefghil"',  # i and l are excluded from the alphabet
        "device_id = 12345",
        "# no device_id at all",
    ],
)
def test_invalid_device_id_is_rejected(tmp_path: Path, bad_device_line: str) -> None:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text(bad_device_line + "\n", encoding="utf-8")
    with pytest.raises(MachineContextError, match="device_id"):
        resolve_machine_context(None, {}, tmp_path)


def test_relative_optional_path_is_rejected(tmp_path: Path) -> None:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text(
        'device_id = "abcdefghjk"\nbib_path = "kbd/zotero_library.bib"\n', encoding="utf-8"
    )
    with pytest.raises(MachineContextError, match="bib_path must be an absolute path"):
        resolve_machine_context(None, {}, tmp_path)


def test_unknown_key_is_a_warning_not_an_error(tmp_path: Path) -> None:
    config_directory = tmp_path / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text(
        'device_id = "abcdefghjk"\ncolour = "blue"\n', encoding="utf-8"
    )
    machine_context = resolve_machine_context(None, {}, tmp_path)
    assert len(machine_context["warnings"]) == 1
    assert "colour" in machine_context["warnings"][0]


def test_xdg_directories_are_respected_and_relative_ones_ignored(tmp_path: Path) -> None:
    absolute_environment = {
        "XDG_CONFIG_HOME": str(tmp_path / "xdg_config"),
        "XDG_STATE_HOME": str(tmp_path / "xdg_state"),
    }
    machine_context = resolve_machine_context(None, absolute_environment, tmp_path)
    assert machine_context["config_directory"] == tmp_path / "xdg_config" / "rep"
    assert machine_context["state_directory"] == tmp_path / "xdg_state" / "rep"
    relative_environment = {"XDG_CONFIG_HOME": "relative/config", "XDG_STATE_HOME": "relative/state"}
    fallback_context = resolve_machine_context(None, relative_environment, tmp_path)
    assert fallback_context["config_directory"] == tmp_path / ".config" / "rep"
    assert fallback_context["state_directory"] == tmp_path / ".local" / "state" / "rep"


def test_machine_local_files_inside_data_root_are_refused_before_writing(tmp_path: Path) -> None:
    # A data root of the home directory would contain ~/.config/rep and sync it.
    with pytest.raises(MachineContextError, match="inside the data root"):
        resolve_machine_context(str(tmp_path), {}, tmp_path)
    assert not (tmp_path / ".config" / "rep" / "local.toml").exists()
