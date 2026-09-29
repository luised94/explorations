# grug.py was written under the old Preferences code style

Date: 2026-09-28
Checked: 2026-09-28
Tags: harness, style, provenance
Source: design session that built the harness, not a run
Scope: grug.py and test_smoke.py as first delivered; not the method files
Revisit: when a batch of runs uses core.md in place of the Preferences, or when grug.py is next rewritten

Observed: the harness was built in a chat whose Preferences demanded flat
procedural code, full names, no single-call helpers, functions only at unit
boundaries, ASCII only, and one concern per commit. The code follows them.
Some are stricter than grug: grug would allow a helper that names an idea.
Decided: keep the style. domains/code.md carries the same rules in grug form,
so the style is now part of what the experiment tests rather than a hidden
influence on it.
Evidence: baseline/preferences.md "Code style" and "Naming"; domains/code.md
"Shape" and "Names and comments".
