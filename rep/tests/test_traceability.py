"""Decisions in PLAN.md and the code that enforces them stay linked.

Code names a decision as "PLAN.md D<n>", or "PLAN.md D<n>, D<m>" for
several. Line numbers are never stored anywhere: they are derived with
`grep -rn "PLAN.md D" src`, so they cannot go stale.
"""

import re
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parent.parent
DECISION_HEADING_PATTERN = re.compile(r"^D(\d+)\. ", re.MULTILINE)
DECISION_REFERENCE_PATTERN = re.compile(r"PLAN\.md (D\d+(?:, D\d+)*)")
# The decisions M2 made: each must be enforced somewhere in the code. Older
# decisions (D1-D20) are mostly about scope, process or later milestones and
# have no single enforcement point, so only the references to them are
# checked, not their presence.
M2_DECISION_NUMBERS = range(21, 31)


def test_every_cited_decision_exists_and_every_m2_decision_is_cited() -> None:
    plan_text = (REPOSITORY_ROOT / "PLAN.md").read_text(encoding="utf-8")
    defined_numbers = {int(number) for number in DECISION_HEADING_PATTERN.findall(plan_text)}
    assert set(M2_DECISION_NUMBERS) <= defined_numbers, "an M2 decision is missing from PLAN.md section 5"

    cited_numbers_by_file: dict[str, set[int]] = {}
    for source_path in sorted((REPOSITORY_ROOT / "src" / "rep").glob("*.py")):
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
    uncited_m2_decisions = sorted(set(M2_DECISION_NUMBERS) - all_cited_numbers)
    assert uncited_m2_decisions == [], f"M2 decisions with no enforcement point in src: {uncited_m2_decisions}"
