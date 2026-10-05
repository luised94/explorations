"""tools/code_tour.py (PLAN.md D57) on a small git repository made here."""

import ast
import subprocess
import sys
from pathlib import Path

TOOL_PATH = Path(__file__).resolve().parent.parent / "tools" / "code_tour.py"


def git(repository: Path, *arguments: str) -> None:
    subprocess.run(["git", "-C", str(repository), *arguments], check=True, capture_output=True)


def test_the_tool_imports_only_the_standard_library() -> None:
    tree = ast.parse(TOOL_PATH.read_text(encoding="utf-8"))
    imported_modules = {alias.name.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.Import) for alias in node.names}
    imported_modules |= {node.module.split(".")[0] for node in ast.walk(tree) if isinstance(node, ast.ImportFrom) and node.module}
    assert imported_modules <= set(sys.stdlib_module_names), imported_modules


def test_the_tour_maps_modules_then_takes_turns_and_points_at_each_definition(tmp_path: Path) -> None:
    repository = tmp_path / "project"
    (repository / "src").mkdir(parents=True)
    git(repository, "init", "-q")
    git(repository, "config", "user.email", "x@example.com")
    git(repository, "config", "user.name", "x")
    long_body = "\n".join(f"        total += {index}" for index in range(160))
    (repository / "src" / "core.py").write_text(
        '"""Core: the representation and its operations."""\n\n\n'
        "def decided():\n    # PLAN.md D7 and PLAN.md D9\n    return 1\n\n\n"
        f"def long_one():\n    total = 0\n    for index in range(3):\n{long_body}\n    return total\n",
        encoding="utf-8",
    )
    (repository / "src" / "helpers.py").write_text("def churned():\n    return 1\n", encoding="utf-8")
    (repository / "notes.lua").write_text("-- lua\nreturn {}\n", encoding="utf-8")
    git(repository, "add", "-A")
    git(repository, "commit", "-qm", "first")
    for revision in range(12):  # make churned() the most recently changed
        (repository / "src" / "helpers.py").write_text(f"def churned():\n    return {revision}\n", encoding="utf-8")
        git(repository, "commit", "-qam", f"change {revision}")
    output_path = tmp_path / "tour.md"
    result = subprocess.run(
        [sys.executable, str(TOOL_PATH), "--repository", str(repository), "--sources", "src/*.py",
         "--recent-commits", "5", "--whole-file", "notes.lua", "--output", str(output_path)],
        capture_output=True, text=True, check=False,
    )  # fmt: skip
    assert result.returncode == 0, result.stderr
    tour = output_path.read_text(encoding="utf-8")
    titles = [line for line in tour.splitlines() if line.startswith("## ")]
    assert titles == [
        "## 1. core.py: the module's contract",
        "## 2. core.py:4 decided (3 lines)",
        "## 3. helpers.py:1 churned (2 lines)",
        "## 4. core.py:9 long_one (164 lines)",
        "## 5. notes.lua (whole file, 2 lines)",
    ]
    assert "why: decisions; 2 decisions enforced here (D7 D9)" in tour
    assert "why: recent churn; 1 lines changed in the last 5 commits" in tour
    assert f"{repository / 'src' / 'core.py'}:9\n  section: {repository / 'src' / 'core.py'}:11 (161 lines)" in tour
    assert tour.count("- Understand: \n- Style: \n- Change: ") == 5
