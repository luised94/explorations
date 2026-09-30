"""Library files: the line grammar of CONVENTIONS.md, read into source records and written back.

REPRESENTATION
  A library file is a sequence of lines, split on "\\n" only; a trailing "\\r"
  goes with the rest of the trailing whitespace. Each line is classified by
  its first characters into one line kind (CONVENTIONS.md "Line kinds");
  nothing else is structure. The parser is a state machine over those kinds:
  outside an item, inside an item, or collecting the ">" block of a marker
  (a `### Q:` or `key:` line with nothing after the colon).

  SourceItem: one `### Q:` item as written, before its meaning is checked.
    line               1-based line of the `### Q:` heading
    section_heading    text of the nearest `## ` heading above, or None
    question           inline text, or the block's lines joined with "\\n"
    question_is_block  whether the question was written as a block
    fields             key -> Field, in file order; when a key repeats, the
                       first is kept and the repeat is a problem
    open_questions     the `?:` lines, as Fields with key "?", in file order
    problems           syntax problems of this item. Any error excludes the
                       item and only the item (PLAN.md I10).
  Field: key, value (inline text, or block lines joined with "\\n", where a
  line holding only ">" is ""), is_block, line.
  Problem: 1-based line and column, severity, message; lint prints it as
  path:line:col (PLAN.md D12).

  A block value is kept as one string, not a list of lines: no line can
  contain "\\n", so joining is lossless, and every consumer but criteria
  wants text.

INVARIANTS
  L1  parse_library_text is total: any string gives a list of items; it
      never raises.
  L2  Every value, question and heading is NFC and has no "\\n" inside a
      line and no trailing whitespace on any line; inline values and
      headings have no leading whitespace either.
  L3  For items without problems that satisfy L2,
      parse_library_text(render_library_items(items)) equals items apart
      from line numbers.
  L4  Line numbers count "\\n" only, as nvim does. str.splitlines also splits
      on U+2028, U+0085 and form feed, which would move every later line
      number and put lint's quickfix entries on the wrong line.

Meaning (required fields, allowed values, citekeys, IDs) is checked on these
records separately; the parser only says what each line is.
"""

import re
import unicodedata
from typing import Literal, TypedDict


class Problem(TypedDict):
    line: int
    column: int
    severity: Literal["error", "warning"]
    message: str


class Field(TypedDict):
    key: str
    value: str
    is_block: bool
    line: int


class SourceItem(TypedDict):
    line: int
    section_heading: str | None
    question: str
    question_is_block: bool
    fields: dict[str, Field]
    open_questions: list[Field]
    problems: list[Problem]


# Checked in this order; the first match decides. Every pattern is anchored
# at column 0, so an indented `A:` is not a field (it would be a silent
# second answer otherwise) and "#### x" is not an item-level heading.
ITEM_HEADING_PATTERN = re.compile(r"^### Q:(.*)$")
OTHER_ITEM_LEVEL_HEADING_PATTERN = re.compile(r"^###(?:[ \t].*)?$")
SECTION_HEADING_PATTERN = re.compile(r"^##(?:[ \t](.*))?$")
BLOCK_CONTENT_PATTERN = re.compile(r"^[ \t]+>(.*)$")
OPEN_QUESTION_PATTERN = re.compile(r"^\?:(.*)$")
# Whitespace or the end of the line must follow the colon: "https://x" in an
# item is then an unrecognized line to report, not a field named "https".
FIELD_PATTERN = re.compile(r"^([A-Za-z][A-Za-z0-9_]*):(?:[ \t]+(.*))?$")

# Stands for the question while its block is collected. It cannot collide
# with a field key, which FIELD_PATTERN limits to letters, digits and "_".
QUESTION_MARKER = "### Q:"
BLOCK_INDENT = "    "


def parse_library_text(text: str) -> list[SourceItem]:
    """Classify every line and return the items, each with its own problems.

    PRE   text is the decoded content of one library file (any string).
    POST  L1, L2, L4. Text outside items (free notes, kbd excerpts, other
          headings) produces nothing. An item with an error is still
          returned, so lint can report it and a session can skip it.
    """
    # NFC once, before splitting: it never adds or removes "\n", so line
    # numbers are those of the file as written (PLAN.md D4).
    normalized_text = unicodedata.normalize("NFC", text)
    if normalized_text.startswith("\ufeff"):
        normalized_text = normalized_text[1:]
    raw_lines = normalized_text.split("\n")

    items: list[SourceItem] = []
    section_heading: str | None = None
    current_item: SourceItem | None = None
    # The marker whose ">" block is being collected (QUESTION_MARKER or a
    # field key), the line it was on, and the block lines so far.
    pending_block_key: str | None = None
    pending_block_line = 0
    pending_block_lines: list[str] = []

    # One step past the last line stands for the end of the file, so the end
    # closes a pending block and the open item by the same code a heading does.
    for line_index in range(len(raw_lines) + 1):
        at_end_of_file = line_index == len(raw_lines)
        line_number = line_index + 1
        line_text = "" if at_end_of_file else raw_lines[line_index].rstrip()
        block_match = None if at_end_of_file else BLOCK_CONTENT_PATTERN.match(line_text)

        # --- collecting a block: take block lines, close it on anything else ---
        if pending_block_key is not None:
            assert current_item is not None, "a pending block always belongs to an item"
            if block_match is not None:
                block_content = block_match.group(1)
                # One space after ">" is the separator; more is content (an
                # indented line of code or math inside the block).
                if block_content.startswith(" "):
                    block_content = block_content[1:]
                pending_block_lines.append(block_content)
                continue
            if len(pending_block_lines) == 0:
                if pending_block_key == QUESTION_MARKER:
                    empty_message = (
                        "the question is empty: write it after '### Q:' "
                        "or as an indented '>' block below it"
                    )
                else:
                    empty_message = (
                        f"'{pending_block_key}:' has no value: write it after the colon "
                        "or as an indented '>' block below it"
                    )
                current_item["problems"].append(
                    {"line": pending_block_line, "column": 1, "severity": "error", "message": empty_message}
                )
            elif pending_block_key == QUESTION_MARKER:
                current_item["question"] = "\n".join(pending_block_lines)
                current_item["question_is_block"] = True
            elif pending_block_key in current_item["fields"]:
                first_line = current_item["fields"][pending_block_key]["line"]
                current_item["problems"].append(
                    {
                        "line": pending_block_line,
                        "column": 1,
                        "severity": "error",
                        "message": f"field '{pending_block_key}' appears twice; the first, at line {first_line}, is kept",
                    }
                )
            else:
                current_item["fields"][pending_block_key] = {
                    "key": pending_block_key,
                    "value": "\n".join(pending_block_lines),
                    "is_block": True,
                    "line": pending_block_line,
                }
            pending_block_key = None
            pending_block_lines = []
            # Fall through: this line has not been classified yet.

        # --- headings and the end of the file close the open item ---
        item_heading_match = None if at_end_of_file else ITEM_HEADING_PATTERN.match(line_text)
        section_heading_match = None if at_end_of_file else SECTION_HEADING_PATTERN.match(line_text)
        is_other_heading = (
            not at_end_of_file
            and item_heading_match is None
            and OTHER_ITEM_LEVEL_HEADING_PATTERN.match(line_text) is not None
        )
        if at_end_of_file or item_heading_match is not None or section_heading_match is not None or is_other_heading:
            if current_item is not None:
                items.append(current_item)
                current_item = None
            if item_heading_match is not None:
                inline_question = item_heading_match.group(1).strip()
                current_item = {
                    "line": line_number,
                    "section_heading": section_heading,
                    "question": inline_question,
                    "question_is_block": False,
                    "fields": {},
                    "open_questions": [],
                    "problems": [],
                }
                if inline_question == "":
                    pending_block_key = QUESTION_MARKER
                    pending_block_line = line_number
            elif section_heading_match is not None:
                heading_text = section_heading_match.group(1)
                section_heading = "" if heading_text is None else heading_text.strip()
            continue

        # --- outside an item every other line is free notes ---
        if current_item is None or line_text == "":
            continue

        open_question_match = OPEN_QUESTION_PATTERN.match(line_text)
        if open_question_match is not None:
            open_question_text = open_question_match.group(1).strip()
            if open_question_text == "":
                current_item["problems"].append(
                    {"line": line_number, "column": 1, "severity": "warning", "message": "'?:' with no question after it"}
                )
            else:
                current_item["open_questions"].append(
                    {"key": "?", "value": open_question_text, "is_block": False, "line": line_number}
                )
            continue

        field_match = FIELD_PATTERN.match(line_text)
        if field_match is not None:
            field_key = field_match.group(1)
            inline_value = field_match.group(2)
            if inline_value is None or inline_value.strip() == "":
                pending_block_key = field_key
                pending_block_line = line_number
            elif field_key in current_item["fields"]:
                first_line = current_item["fields"][field_key]["line"]
                current_item["problems"].append(
                    {
                        "line": line_number,
                        "column": 1,
                        "severity": "error",
                        "message": f"field '{field_key}' appears twice; the first, at line {first_line}, is kept",
                    }
                )
            else:
                current_item["fields"][field_key] = {
                    "key": field_key,
                    "value": inline_value.strip(),
                    "is_block": False,
                    "line": line_number,
                }
            continue

        if block_match is not None:
            # A block ends at its first non-block line, blank lines included,
            # so this line was cut off from its marker; guessing which marker
            # it continues could attach text to the wrong field.
            unattached_message = (
                "'>' line not under a marker: a blank line ends a block; "
                "use a line with only '>' for a paragraph break"
            )
            current_item["problems"].append(
                {"line": line_number, "column": 1, "severity": "error", "message": unattached_message}
            )
            continue

        # Anything else inside an item would be silently dropped text (a
        # second answer line without '>', an indented field), so it is an
        # error, not a note.
        current_item["problems"].append(
            {
                "line": line_number,
                "column": 1,
                "severity": "error",
                "message": "not an item line: expected 'key: value', an indented '>' block, '?: text' or a blank line",
            }
        )

    return items


def render_library_items(items: list[SourceItem]) -> str:
    """Write items in the canonical layout of CONVENTIONS.md.

    PRE   no item has problems; values, questions and headings satisfy L2;
          inline values and inline questions are not empty; field keys match
          FIELD_PATTERN; once an item has a section heading, every later item
          has one (a file cannot return to having no section).
    POST  L3. Items are separated by one blank line; a `## ` heading is
          written when the section changes; blocks are indented four spaces.
    """
    rendered_lines: list[str] = []
    previous_section_heading: str | None = None
    for item in items:
        assert item["problems"] == [], "rendering an item with problems would hide them"
        if item["section_heading"] != previous_section_heading:
            assert item["section_heading"] is not None, "a file cannot leave a section"
            # rstrip: an empty heading is written "##", not "## ", so the
            # output has no trailing whitespace (L2 applies to our own output).
            rendered_lines.append(f"## {item['section_heading']}".rstrip())
            rendered_lines.append("")
            previous_section_heading = item["section_heading"]

        if item["question_is_block"]:
            rendered_lines.append(QUESTION_MARKER)
            for question_line in item["question"].split("\n"):
                rendered_lines.append(f"{BLOCK_INDENT}> {question_line}".rstrip())
        else:
            assert item["question"] != "", "an empty inline question reads back as a block marker"
            rendered_lines.append(f"{QUESTION_MARKER} {item['question']}")

        for field in item["fields"].values():
            if field["is_block"]:
                rendered_lines.append(f"{field['key']}:")
                for value_line in field["value"].split("\n"):
                    rendered_lines.append(f"{BLOCK_INDENT}> {value_line}".rstrip())
            else:
                assert field["value"] != "", "an empty inline value reads back as a block marker"
                rendered_lines.append(f"{field['key']}: {field['value']}")
        for open_question in item["open_questions"]:
            rendered_lines.append(f"?: {open_question['value']}")
        rendered_lines.append("")
    return "\n".join(rendered_lines)
