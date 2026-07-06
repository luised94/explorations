"""Spike verification: parse/render round-trip, error reporting, and
equivalence with drill's canonical JSONL path."""

import json
from author import author_parse, author_render, author_template
from logic import ImportParseError, parse_jsonl

BUFFER = """\
# capitals bank additions
q: Capital of France?
a: Paris
alt: paris | Paris, France
tags: geo | europe

q: 7 * 8
a: 56
type: translate
difficulty: 2

q: Which planet is largest?
a: Jupiter
type: multiple_choice
distractors: Saturn | Neptune | Earth
hint: It is a gas giant
"""

failures = 0


def check(name, condition):
    global failures
    print(("PASS  " if condition else "FAIL  ") + name)
    if not condition:
        failures += 1


records = author_parse(BUFFER)
check("parses three blocks", len(records) == 3)
check("aliases resolve (q/a/alt/hint/type)",
      records[0]["question"] == "Capital of France?"
      and records[0]["alternatives"] == ["paris", "Paris, France"]
      and records[2]["hints"] == ["It is a gas giant"]
      and records[1]["qtype"] == "translate")
check("difficulty coerced", records[1]["difficulty"] == 2)
check("defaults filled (canonical keys)",
      records[0]["qtype"] == "free_response"
      and records[0]["media_url"] is None
      and records[0]["distractors"] == [])

# Equivalence with the canonical JSONL path: same dicts either way.
jsonl_text = "\n".join(json.dumps(record) for record in records)
check("identical to parse_jsonl of own JSON", parse_jsonl(jsonl_text) == records)

# Round-trip: render -> parse is identity on canonical dicts.
check("render->parse round-trip", author_parse(author_render(records)) == records)

# Template parses to nothing but comments + empty blocks fail usefully.
try:
    author_parse(author_template(1))
    check("template alone raises (missing q/a)", False)
except ImportParseError as error:
    check("template alone raises (missing q/a)", "question" in str(error))

# Error paths name block/line.
for name, bad in [
    ("missing answer names block", "q: orphan question\ntags: x"),
    ("unknown key named with line", "q: x\na: y\nbogus: z"),
    ("bare line rejected", "q: x\na: y\nno colon here at all &&&"),
    ("duplicate key in block", "q: x\nq: again\na: y"),
    ("bad qtype rejected", "q: x\na: y\ntype: essay"),
]:
    try:
        author_parse(bad)
        check(name, False)
    except ImportParseError as error:
        check(name, ("line" in str(error)) or ("block" in str(error))
              or ("qtype" in str(error)))

print("\n%d failure(s)" % failures)
raise SystemExit(1 if failures else 0)
