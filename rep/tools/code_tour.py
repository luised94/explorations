"""A guided tour of a codebase, written as a form to fill in nvim
(rep/PLAN.md D57): the places worth reading, each with why it was chosen, its path:line
for gF, and three lines for the reader's answers. The answers show what the
reader understands, what they would write differently, and what they would
not dare to change; the next thread reads them.

Self-contained: the standard library and git, nothing from rep, so it can be
copied into another Python codebase unchanged. Python files are read with
ast; other files can be added as whole-file stops (--whole-file).

    uv run python tools/code_tour.py --output tour.md [--repository .]
        [--sources 'src/**/*.py'] [--decision-pattern 'PLAN\\.md D\\d+']
        [--recent-commits 10] [--stops 20] [--whole-file nvim/lua/rep/init.lua]

How stops are chosen, each place at most once, up to --stops: first the
map, every module that opens with a docstring (its contract); then three
rankings take turns: decisions (functions citing the most, by
--decision-pattern), churn (the most lines changed in the last
--recent-commits commits, by git blame) and size (the longest). Every
--whole-file comes last.
A function over 150 lines lists its larger top-level blocks as sections, so
a long function can be read in parts.
"""

import argparse
import ast
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import TypedDict


class FunctionFacts(TypedDict):
    path: Path
    name: str
    line: int
    length: int
    decisions: list[str]  # decision ids cited in its body, e.g. D45
    recent: int  # its lines last changed by a recent commit
    sections: list[tuple[int, int]]  # (first line, length) of its larger blocks


def main() -> int:
    argument_parser = argparse.ArgumentParser(description="A tour of a codebase, as a form to fill in.")
    argument_parser.add_argument("--repository", default=".", help="the git repository's directory (default: here)")
    argument_parser.add_argument("--sources", default="src/**/*.py", help="Python files to read, a glob from the repository")
    argument_parser.add_argument("--decision-pattern", default=r"PLAN\.md D\d+", help="regex for a cited design decision")
    argument_parser.add_argument("--recent-commits", type=int, default=10, help="commits counted as recent churn")
    argument_parser.add_argument("--stops", type=int, default=20, help="at most this many stops")
    argument_parser.add_argument("--whole-file", action="append", default=[], help="a non-Python file to read whole (repeatable)")
    argument_parser.add_argument("--output", required=True, help="the tour file to write")
    parsed_arguments = argument_parser.parse_args()
    repository = Path(parsed_arguments.repository).resolve()
    stop_limit: int = parsed_arguments.stops
    decision_pattern = re.compile(parsed_arguments.decision_pattern)
    decision_number_pattern = re.compile(r"D\d+")

    recent_commits = subprocess.run(
        ["git", "-C", str(repository), "log", f"-{parsed_arguments.recent_commits}", "--format=%H"],
        capture_output=True, text=True, check=True,
    ).stdout.split()  # fmt: skip

    # --- every module and function, with its decisions and recent lines ---
    modules: list[tuple[Path, int, str]] = []  # path, line count, first docstring line
    functions: list[FunctionFacts] = []
    for source_path in sorted(repository.glob(parsed_arguments.sources)):
        source_text = source_path.read_text(encoding="utf-8")
        source_lines = source_text.splitlines()
        tree = ast.parse(source_text)
        module_docstring = ast.get_docstring(tree)
        if module_docstring:
            modules.append((source_path, len(source_lines), module_docstring.splitlines()[0]))
        # Which recent commit last touched each line (git blame, porcelain).
        recent_line_numbers: set[int] = set()
        blame = subprocess.run(
            ["git", "-C", str(repository), "blame", "--porcelain", "--", str(source_path.relative_to(repository))],
            capture_output=True, text=True, check=False,
        ).stdout  # fmt: skip
        for blame_line in blame.splitlines():
            header = re.match(r"^([0-9a-f]{40}) \d+ (\d+)", blame_line)
            if header and header[1] in recent_commits:
                recent_line_numbers.add(int(header[2]))
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) or node.end_lineno is None:
                continue
            body_text = "\n".join(source_lines[node.lineno - 1 : node.end_lineno])
            sections: list[tuple[int, int]] = []
            if node.end_lineno - node.lineno > 150:
                for statement in node.body:
                    if isinstance(statement, (ast.If, ast.For, ast.While, ast.Try, ast.With)) and statement.end_lineno is not None:
                        if statement.end_lineno - statement.lineno >= 40:
                            sections.append((statement.lineno, statement.end_lineno - statement.lineno + 1))
            functions.append(
                {
                    "path": source_path, "name": node.name, "line": node.lineno, "length": node.end_lineno - node.lineno + 1,
                    "decisions": sorted(set(decision_number_pattern.findall(" ".join(decision_pattern.findall(body_text)))), key=lambda text: int(text[1:])),
                    "recent": sum(1 for line_number in range(node.lineno, node.end_lineno + 1) if line_number in recent_line_numbers),
                    "sections": sections,
                }
            )  # fmt: skip

    # --- choose the stops ---
    stops: list[tuple[str, int, str, str, list[tuple[int, int]]]] = []  # path, line, title, why, sections
    chosen: set[tuple[Path, str]] = set()
    for source_path, line_count, first_docstring_line in modules:
        stops.append((str(source_path), 1, f"{source_path.name}: the module's contract", f"the map: {first_docstring_line} ({line_count} lines in all; read the docstring)", []))
    # Three rankings take turns, so no one of them fills the tour alone
    # (on rep, decisions alone filled every place before churn or size).
    rankings: list[tuple[str, list[FunctionFacts]]] = [
        ("decisions", sorted((function for function in functions if function["decisions"]), key=lambda function: -len(function["decisions"]))),
        ("recent churn", sorted((function for function in functions if function["recent"]), key=lambda function: -function["recent"])),
        ("size", sorted(functions, key=lambda function: -function["length"])),
    ]
    ranking_positions = [0] * len(rankings)
    while len(stops) < stop_limit and any(position < len(ranking[1]) for position, ranking in zip(ranking_positions, rankings, strict=True)):
        for ranking_index, (why_text, ranked) in enumerate(rankings):
            while ranking_positions[ranking_index] < len(ranked) and (ranked[ranking_positions[ranking_index]]["path"], ranked[ranking_positions[ranking_index]]["name"]) in chosen:
                ranking_positions[ranking_index] += 1
            if ranking_positions[ranking_index] >= len(ranked) or len(stops) >= stop_limit:
                continue
            function = ranked[ranking_positions[ranking_index]]
            chosen.add((function["path"], function["name"]))
            reasons = [why_text]
            if function["decisions"]:
                decision_count = len(function["decisions"])
                reasons.append(f"{decision_count} decision{'s' if decision_count != 1 else ''} enforced here ({' '.join(function['decisions'])})")
            if function["recent"]:
                reasons.append(f"{function['recent']} lines changed in the last {len(recent_commits)} commits")
            title = f"{function['path'].name}:{function['line']} {function['name']} ({function['length']} lines)"
            stops.append((str(function["path"]), function["line"], title, "; ".join(reasons), function["sections"]))
    stops = stops[:stop_limit]
    for whole_file in parsed_arguments.whole_file:
        whole_path = (repository / whole_file).resolve()
        line_count = len(whole_path.read_text(encoding="utf-8").splitlines())
        stops.append((str(whole_path), 1, f"{whole_path.name} (whole file, {line_count} lines)", "not Python: read it whole", []))

    # --- the form ---
    total_lines = sum(function["length"] for function in functions if (function["path"], function["name"]) in chosen)
    tour: list[str] = [
        f"# Code tour of {repository.name}, {date.today().isoformat()}: {len(stops)} stops",
        "",
        "> How to use: on each stop, put the cursor on the path:line and press gF",
        "> to open the code there (Ctrl-^ comes back). Answer on the lines below",
        "> each stop, after the colon; leave a line empty to skip it. Short is fine.",
        ">   Understand: in one line, what does this do? (no peeking at comments first)",
        ">   Style: anything you would write differently, or a rule it breaks",
        ">   Change: would you change this with confidence? what would worry you?",
        f"> About {max(1, total_lines // 40)} minutes of reading at 40 lines a minute.",
        "",
    ]
    for stop_number, (stop_path, stop_line, title, why_text, sections) in enumerate(stops, start=1):
        tour += [f"## {stop_number}. {title}", "", f"why: {why_text}", f"{stop_path}:{stop_line}"]
        for section_line, section_length in sections:
            tour.append(f"  section: {stop_path}:{section_line} ({section_length} lines)")
        tour += ["", "- Understand: ", "- Style: ", "- Change: ", ""]
    output_path = Path(parsed_arguments.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text("\n".join(tour), encoding="utf-8")
    print(output_path)
    return 0


if __name__ == "__main__":
    sys.exit(main())
