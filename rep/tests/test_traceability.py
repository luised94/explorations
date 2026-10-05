"""Decisions in PLAN.md and the code that enforces them stay linked (BUILDING.md section 5).

Code names a decision as "PLAN.md D<n>", or "PLAN.md D<n>, D<m>" for
several. Line numbers are never stored anywhere: they are derived with
`grep -rn "PLAN.md D" src`, so they cannot go stale.
"""

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DECISION_HEADING_PATTERN = re.compile(r"^D(\d+)\. (.*)$", re.MULTILINE)
DECISION_REFERENCE_PATTERN = re.compile(r"PLAN\.md (D\d+(?:, D\d+)*)")
# A decision made by a build milestone carries it in its heading:
# "D23. Item ids (M2)." or "(M2; ...)" or "(M2, ...)". The parenthesis is
# required, so prose such as "waits for M5" does not count. Decisions from
# M2 on must each be enforced somewhere in the code; the earlier ones are
# about scope and process and have no single enforcement point, so only the
# references to them are checked.
MILESTONE_MARKER_PATTERN = re.compile(r"\(M(\d+)[,;)]")
# "(M3, pending)": approved before its code exists. It must have no
# enforcement point yet, and the commit that adds one changes the marker
# to "(M3)", so a decision is never enforced while marked pending, nor
# marked done while unenforced (PLAN.md section 5, before D31).
PENDING_MARKER_PATTERN = re.compile(r"\(M\d+, pending\)")
FIRST_TRACED_MILESTONE = 2


def test_every_cited_decision_exists_and_every_milestone_decision_is_cited() -> None:
    plan_text = (REPOSITORY_ROOT / "PLAN.md").read_text(encoding="utf-8")
    defined_numbers: set[int] = set()
    traced_numbers: set[int] = set()
    pending_numbers: set[int] = set()
    for number_text, heading_text in DECISION_HEADING_PATTERN.findall(plan_text):
        defined_numbers.add(int(number_text))
        milestone_match = MILESTONE_MARKER_PATTERN.search(heading_text)
        if PENDING_MARKER_PATTERN.search(heading_text) is not None:
            pending_numbers.add(int(number_text))
        elif milestone_match is not None and int(milestone_match.group(1)) >= FIRST_TRACED_MILESTONE:
            traced_numbers.add(int(number_text))
    # Guards the pattern itself: if it stopped matching, the test would pass
    # while tracing nothing.
    assert set(range(20, 31)) <= traced_numbers, f"milestone markers not found: {sorted(traced_numbers)}"

    cited_numbers_by_file: dict[str, set[int]] = {}
    # Code that enforces decisions lives in src, and since D56 and D57 also
    # in the tools, the shell helpers and the nvim loaders.
    enforcing_paths = [
        *sorted((REPOSITORY_ROOT / "src" / "rep").glob("*.py")), *sorted((REPOSITORY_ROOT / "tools").glob("*.py")),
        *sorted((REPOSITORY_ROOT / "shell").glob("*.sh")), *sorted((REPOSITORY_ROOT / "nvim").rglob("*.lua")),
    ]  # fmt: skip
    for source_path in enforcing_paths:
        for reference_list in DECISION_REFERENCE_PATTERN.findall(source_path.read_text(encoding="utf-8")):
            for reference in reference_list.split(", "):
                cited_numbers_by_file.setdefault(source_path.name, set()).add(int(reference.removeprefix("D")))

    undefined_citations = {
        file_name: sorted(numbers - defined_numbers)
        for file_name, numbers in cited_numbers_by_file.items()
        if numbers - defined_numbers
    }
    assert undefined_citations == {}, f"code cites decisions PLAN.md does not define: {undefined_citations}"
    all_cited_numbers: set[int] = set()
    for cited_numbers in cited_numbers_by_file.values():
        all_cited_numbers |= cited_numbers
    uncited_decisions = sorted(traced_numbers - all_cited_numbers)
    assert uncited_decisions == [], f"milestone decisions with no enforcement point in src, tools, shell or nvim: {uncited_decisions}"
    enforced_pending_decisions = sorted(pending_numbers & all_cited_numbers)
    assert enforced_pending_decisions == [], (
        f"decisions enforced in src but still marked pending; change '(M<n>, pending)' to '(M<n>)': "
        f"{enforced_pending_decisions}"
    )
