"""The nvim plugin (rep/nvim, PLAN.md D43), run headless against the installed `rep`.

Each test writes a Lua scenario, runs it in `nvim --headless -u NONE` (so the
person's config never enters), and reads back what the scenario recorded as
JSON. nvim must be on PATH: these tests are skipped without it, so the
baseline names how many ran.
"""

import json
import os
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

PLUGIN_DIRECTORY = Path(__file__).resolve().parent.parent / "nvim"
NVIM_EXECUTABLE = shutil.which("nvim")
pytestmark = pytest.mark.skipif(NVIM_EXECUTABLE is None, reason="nvim is not on PATH")


# Any: the scenario's JSON is whatever the Lua recorded; each test asserts
# the exact values it expects.
def run_nvim_scenario(home_directory: Path, lua_scenario: str) -> dict[str, Any]:
    """Run lua_scenario with the plugin on the runtime path; it fills the Lua
    table `results`, which comes back decoded. Notifications are recorded in
    results.notifications instead of shown."""
    rep_executable = shutil.which("rep")
    assert rep_executable is not None, "rep is not on PATH; run the tests with `uv run pytest`"
    assert NVIM_EXECUTABLE is not None
    result_path = home_directory / "nvim-results.json"
    script_path = home_directory / "scenario.lua"
    script_path.write_text(
        "local results = { notifications = {} }\n"
        "vim.notify = function(message) table.insert(results.notifications, message) end\n"
        + lua_scenario
        + f"\nvim.fn.writefile({{ vim.json.encode(results) }}, {json.dumps(str(result_path))})\n"
        "vim.cmd('qall!')\n",
        encoding="utf-8",
    )
    environment = dict(os.environ)
    environment["HOME"] = str(home_directory)
    for variable in ("REP_DATA_ROOT", "XDG_CONFIG_HOME", "XDG_STATE_HOME", "XDG_DATA_HOME"):
        environment.pop(variable, None)
    completed = subprocess.run(
        [NVIM_EXECUTABLE, "--headless", "-u", "NONE", "-i", "NONE", "-n",
         "--cmd", f"set runtimepath^={PLUGIN_DIRECTORY}", "-c", f"luafile {script_path}"],
        env=environment, capture_output=True, timeout=20, check=False,
    )  # fmt: skip
    assert result_path.exists(), completed.stderr.decode()
    return json.loads(result_path.read_text(encoding="utf-8"))


def make_home(home_directory: Path) -> Path:
    config_directory = home_directory / ".config" / "rep"
    config_directory.mkdir(parents=True)
    (config_directory / "local.toml").write_text('device_id = "6a2ah35zhe"\n', encoding="utf-8")
    (home_directory / "learning" / "library").mkdir(parents=True)
    (home_directory / "notes").mkdir()
    return home_directory / "learning"


def stamped_item_ids(data_root: Path) -> list[str]:
    events_path = data_root / "events" / "6a2ah35zhe.jsonl"
    if not events_path.exists():
        return []
    return [
        event["item"]
        for event in (json.loads(line) for line in events_path.read_text(encoding="utf-8").splitlines())
        if event["kind"] == "item_stamped"
    ]


def test_save_stamps_by_insertion_only_and_reports_problems_in_quickfix(tmp_path: Path) -> None:
    data_root = make_home(tmp_path)
    library_directory = data_root / "library"
    (library_directory / "a.md").write_text(
        "### Q: Old item\nid: old-item-aaaa\nA: x\n\n### Q: New item\nA: y\n\n### Q: Third item\nA: z\n",
        encoding="utf-8",
    )
    (library_directory / "broken.md").write_text("### Q: a\nA: y\nA: z\n", encoding="utf-8")
    (tmp_path / "notes" / "b.md").write_text("### Q: Not in the library\nA: y\n", encoding="utf-8")
    results = run_nvim_scenario(
        tmp_path,
        "require('rep').setup({})\n"
        f"vim.cmd('edit ' .. {json.dumps(str(library_directory / 'a.md'))})\n"
        # The cursor and a mark on the new item's answer, which the id line
        # will push down by one: replacing the buffer would lose both. Two
        # insertions, so their order of application matters.
        "vim.api.nvim_win_set_cursor(0, { 6, 0 })\n"
        "vim.cmd('normal! ma')\n"
        "vim.cmd('write')\n"
        "results.stamped_lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)\n"
        "results.mark_line = vim.api.nvim_buf_get_mark(0, 'a')[1]\n"
        "results.cursor_line = vim.api.nvim_win_get_cursor(0)[1]\n"
        f"vim.cmd('edit ' .. {json.dumps(str(tmp_path / 'notes' / 'b.md'))})\n"
        "vim.cmd('write')\n"
        "results.outside_lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)\n"
        f"vim.cmd('edit ' .. {json.dumps(str(library_directory / 'broken.md'))})\n"
        "vim.cmd('write')\n"
        "results.broken_lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)\n"
        "results.quickfix = vim.tbl_map(function(entry)\n"
        "  return { vim.api.nvim_buf_get_name(entry.bufnr), entry.lnum, entry.type, entry.text }\n"
        "end, vim.fn.getqflist())\n",
    )
    stamped_lines: list[str] = results["stamped_lines"]
    new_item_ids = stamped_item_ids(data_root)
    assert len(new_item_ids) == 2 and new_item_ids[0].startswith("new-item-") and new_item_ids[1].startswith("third-item-")
    assert stamped_lines == [
        "### Q: Old item", "id: old-item-aaaa", "A: x", "",
        "### Q: New item", f"id: {new_item_ids[0]}", "A: y", "",
        "### Q: Third item", f"id: {new_item_ids[1]}", "A: z",
    ]  # fmt: skip
    assert (library_directory / "a.md").read_text(encoding="utf-8") == "\n".join(stamped_lines) + "\n"
    assert results["mark_line"] == 7 and results["cursor_line"] == 7
    assert results["outside_lines"] == ["### Q: Not in the library", "A: y"]
    assert results["broken_lines"] == ["### Q: a", "A: y", "A: z"]
    assert results["quickfix"] == [
        [str(library_directory / "broken.md"), 3, "e", "field 'A' appears twice; the first, at line 2, is kept"]
    ]
    assert results["notifications"] == ["rep: nothing stamped; the problems are in the quickfix list (:copen)"]


def test_capture_opens_the_source_file_with_an_item_and_the_save_stamps_it(tmp_path: Path) -> None:
    data_root = make_home(tmp_path)
    library_directory = data_root / "library"
    (tmp_path / "notes" / "reading.md").write_text("## @Smith2020??\n\nSome reading notes.\n", encoding="utf-8")
    (tmp_path / "notes" / "plain.md").write_text("No heading here.\n", encoding="utf-8")
    results = run_nvim_scenario(
        tmp_path,
        "require('rep').setup({})\n"
        f"vim.cmd('edit ' .. {json.dumps(str(tmp_path / 'notes' / 'reading.md'))})\n"
        "vim.api.nvim_win_set_cursor(0, { 3, 0 })\n"
        "vim.cmd('RepCapture')\n"
        "results.first_name = vim.api.nvim_buf_get_name(0)\n"
        "results.first_template = vim.api.nvim_buf_get_lines(0, 0, -1, false)\n"
        "results.first_cursor = vim.api.nvim_win_get_cursor(0)\n"
        "vim.api.nvim_buf_set_lines(0, 0, 2, false, { '### Q: What is X?', 'A: Y' })\n"
        "vim.cmd('write')\n"
        "vim.cmd('wincmd p')\n"
        "vim.cmd('RepCapture')\n"
        "results.second_lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)\n"
        "results.second_cursor = vim.api.nvim_win_get_cursor(0)\n"
        "vim.cmd('bwipeout!')\n"
        f"vim.cmd('edit ' .. {json.dumps(str(tmp_path / 'notes' / 'plain.md'))})\n"
        "vim.cmd('RepCapture')\n"
        "results.no_heading_buffer = vim.api.nvim_buf_get_name(0)\n"
        "vim.cmd('RepCapture topic.md')\n"
        "results.named_name = vim.api.nvim_buf_get_name(0)\n"
        "results.named_template = vim.api.nvim_buf_get_lines(0, 0, -1, false)\n",
    )
    captured_path = library_directory / "Smith2020.md"
    assert results["first_name"] == str(captured_path)
    assert results["first_template"] == ["### Q: ", "A: ", "source: @Smith2020??"]
    assert results["first_cursor"] == [1, 7]
    new_item_ids = stamped_item_ids(data_root)
    assert len(new_item_ids) == 1
    assert captured_path.read_text(encoding="utf-8") == (
        f"### Q: What is X?\nid: {new_item_ids[0]}\nA: Y\nsource: @Smith2020??\n"
    )
    assert results["second_lines"] == [
        "### Q: What is X?", f"id: {new_item_ids[0]}", "A: Y", "source: @Smith2020??",
        "", "### Q: ", "A: ", "source: @Smith2020??",
    ]  # fmt: skip
    assert results["second_cursor"] == [6, 7]
    assert results["no_heading_buffer"] == str(tmp_path / "notes" / "plain.md")
    assert results["notifications"] == ["rep: no `## @citekey` above the cursor; name the file: :RepCapture <name>"]
    assert results["named_name"] == str(library_directory / "topic.md")
    assert results["named_template"] == ["### Q: ", "A: "]


def test_a_missing_rep_is_reported_once_and_saves_still_work(tmp_path: Path) -> None:
    make_home(tmp_path)
    (tmp_path / "notes" / "b.md").write_text("text\n", encoding="utf-8")
    results = run_nvim_scenario(
        tmp_path,
        "require('rep').setup({ command = 'rep-is-not-installed' })\n"
        f"vim.cmd('edit ' .. {json.dumps(str(tmp_path / 'notes' / 'b.md'))})\n"
        "vim.cmd('write')\n"
        "vim.cmd('write')\n"
        "results.written = vim.fn.filereadable(vim.api.nvim_buf_get_name(0))\n",
    )
    notifications: list[str] = results["notifications"]
    assert len(notifications) == 1
    assert notifications[0].startswith("rep: `rep-is-not-installed where --data-root` failed")
    assert results["written"] == 1
