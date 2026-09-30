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
    question_end_line  last line of the question: `line` when inline, the
                       last block line otherwise; stamp inserts `id:` after it
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

  Item: what a session can use, built by check_source_item only when the
  item has no errors (PLAN.md D14: typed records only after checks pass).
  Values stay JSON-native strings; a numeric key is kept as its validated
  text parts, which Decimal reads exactly and without failure.

SEVERITY
  An error excludes the item from sessions (I10), so errors are only what
  stops a session from using the item correctly: no id, no answer, a check
  or attempt value it cannot run, a numeric key it cannot read, a grading
  key that cannot be typed. Everything else (source, tags, unknown fields,
  an id not in the form rep writes) is a warning: excluding an item from
  practice over its metadata would cost learning and protect nothing.

Meaning is checked on the source records by check_source_item; the parser
only says what each line is.

STAMP
  stamp_library_text gives every item without an `id:` field an id, by
  inserting one `id:` line after its question. It works on the text as
  written, not on a re-rendered file: the person's layout, NFD text, CRLF
  endings and byte-order mark survive (PLAN.md I3, I9).
  L5  Idempotent: stamping stamped text changes nothing.
  L6  The output is the input plus inserted `id:` lines (each with a line
      ending, placed before the next line, or after a final line that had
      none); no other character changes.
  L7  If the parser reports any error, the input is returned unchanged with
      those errors, and nothing is inserted.
  L8  New ids match ITEM_ID_PATTERN and collide with no id in the text or in
      existing_item_ids.
"""

import re
import unicodedata
from collections.abc import Callable
from typing import Literal, TypedDict

from rep.machine import DEVICE_ID_ALPHABET


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
    question_end_line: int
    fields: dict[str, Field]
    open_questions: list[Field]
    problems: list[Problem]


class StampResult(TypedDict):
    text: str  # the input with `id:` lines inserted, or the input unchanged
    stamped_item_ids: list[str]  # the ids inserted, in file order
    problems: list[Problem]  # parser errors that stopped stamping; empty otherwise


class NumericKey(TypedDict):
    value: str  # matches NUMBER_PATTERN
    tolerance: str | None  # an unsigned number, or None for equality
    tolerance_is_percent: bool


class Item(TypedDict):
    id: str
    line: int
    question: str
    answer: str | None  # shown at reveal
    criteria: list[str] | None  # what a self-graded item is graded against
    check: Literal["self", "exact", "numeric"]
    attempt: Literal["recall", "typed"]  # effective: exact and numeric force typed
    numeric_key: NumericKey | None  # set exactly when check is numeric
    citekey: str | None  # explicit source, else the `## @citekey` above
    citekey_is_unverified: bool  # written with the kbd "??" suffix
    location: str | None
    tags: list[str]
    by: str | None
    open_questions: list[str]


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

KNOWN_FIELD_KEYS = ("id", "A", "criteria", "source", "tags", "check", "attempt", "by")

# PLAN.md D20. ASCII digits only ([0-9], not \d): \d also matches digits of
# other scripts, which Decimal accepts, so the syntax the person reads in
# CONVENTIONS.md would not be the syntax rep accepts. The pattern, not
# Decimal, is the gate: Decimal also parses "Infinity" and "NaN".
UNSIGNED_NUMBER = r"(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)(?:[eE][+-]?[0-9]+)?"
NUMBER_PATTERN = re.compile(rf"^[+-]?{UNSIGNED_NUMBER}$")
NUMERIC_KEY_PATTERN = re.compile(rf"^([+-]?{UNSIGNED_NUMBER})(?:[ \t]*\+-[ \t]*({UNSIGNED_NUMBER})(%)?)?$")

# The form rep writes (CONVENTIONS.md "IDs"): up to three lowercase ASCII
# words and four alphabet characters, or "q-" and six.
ITEM_ID_PATTERN = re.compile(
    rf"^(?:[a-z0-9]+-){{1,3}}[{DEVICE_ID_ALPHABET}]{{4}}$|^q-[{DEVICE_ID_ALPHABET}]{{6}}$"
)
# What an id must be to work at all: one word of printable ASCII, since it is
# the key of an item's whole history in the events (CONVENTIONS.md: IDs are
# ASCII). Failing ITEM_ID_PATTERN but passing this is only a warning, because
# the item may already have history under that id.
USABLE_ITEM_ID_PATTERN = re.compile(r"^[!-~]+$")

# A citekey is anything BibTeX allows in a key except ":" (the location
# separator) and "?" (the kbd unverified suffix). kbd's README notes that
# BetterBibTeX auto-keys can hold dots and other punctuation, so the class
# excludes rather than enumerates. The location is not checked beyond having
# no whitespace: kbd uses forms beyond its six specifiers (pinned-key verses
# such as John.3.16), and nothing in rep reads a location's structure.
SOURCE_PATTERN = re.compile(r"^@([^\s:?,{}%#~\\\"]+)(\?\?)?(?::(\S+))?$")
SECTION_SOURCE_PATTERN = re.compile(r"^@([^\s:?,{}%#~\\\"]+)(\?\?)?$")
# Dropped from id stems so the stem carries the words that name the item
# ("What does Km measure?" -> km-measure). English only: questions in other
# languages keep their function words, which costs readability, never
# correctness, since the id is an identity and not a title.
ID_STEM_STOPWORDS = frozenset(
    "a an the and or but if so not no of to in on at for by with from into about as than then "
    "is are was were be been being am do does did has have had can could would should will shall "
    "may might must what which who whom whose when where why how that this these those there "
    "it its i me my we our you your he she they them his her their".split()
)
ID_STEM_WORD_LIMIT = 3
ID_SUFFIX_LENGTH = 4  # 20 bits per stem: a collision is rare, and retried
ID_NO_WORDS_SUFFIX_LENGTH = 6  # "q-" ids share one stem, so they get 30 bits
ID_DRAW_LIMIT = 1000

# kbd README: lowercase and underscore-separated, acronyms uppercase; so each
# underscore-separated part is all lowercase or all uppercase.
TAG_PATTERN = re.compile(r"^#(?:[a-z0-9]+|[A-Z0-9]+)(?:_(?:[a-z0-9]+|[A-Z0-9]+))*$")

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
                # Block lines are contiguous from the line after the marker.
                current_item["question_end_line"] = pending_block_line + len(pending_block_lines)
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
                    "question_end_line": line_number,
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


def check_source_item(source_item: SourceItem) -> tuple[Item | None, list[Problem]]:
    """Check one item's meaning and build the record a session can use.

    PRE   source_item came from parse_library_text.
    POST  returns (item, problems): problems holds the parser's problems for
          this item followed by the meaning problems found here, in field
          order; item is None exactly when some problem is an error
          (SEVERITY in the module docstring). The source item is unchanged.
    """
    problems: list[Problem] = list(source_item["problems"])
    fields = source_item["fields"]
    item_line = source_item["line"]

    # D4: an unknown field is kept and warned about, so a future field needs
    # no migration. A case slip ("a:" for "A:") gets a hint, because the same
    # slip also produces the "no answer" error and the hint names the cause.
    for field in fields.values():
        if field["key"] in KNOWN_FIELD_KEYS:
            continue
        case_matches = [known for known in KNOWN_FIELD_KEYS if known.lower() == field["key"].lower()]
        hint = f"; did you mean '{case_matches[0]}:'?" if case_matches else ""
        problems.append(
            {
                "line": field["line"],
                "column": 1,
                "severity": "warning",
                "message": f"unknown field '{field['key']}' is kept but not used{hint}",
            }
        )

    # --- id ---
    item_id = ""
    id_field = fields.get("id")
    if id_field is None:
        problems.append(
            {
                "line": item_line,
                "column": 1,
                "severity": "error",
                "message": "no id: save the file in nvim or run `rep stamp` to add one",
            }
        )
    elif id_field["is_block"] or USABLE_ITEM_ID_PATTERN.match(id_field["value"]) is None:
        problems.append(
            {
                "line": id_field["line"],
                "column": 1,
                "severity": "error",
                "message": "id must be one word of printable ASCII on the 'id:' line",
            }
        )
    else:
        item_id = id_field["value"]
        if ITEM_ID_PATTERN.match(item_id) is None:
            problems.append(
                {
                    "line": id_field["line"],
                    "column": 1,
                    "severity": "warning",
                    "message": (
                        f"id '{item_id}' is not in the form rep writes; if the item has no "
                        "review history yet, delete the line and let `rep stamp` write one"
                    ),
                }
            )

    # --- answer and criteria ---
    answer_field = fields.get("A")
    criteria_field = fields.get("criteria")
    answer = None if answer_field is None else answer_field["value"]
    criteria: list[str] | None = None
    if criteria_field is not None:
        # Each non-blank line is one element of the checklist; a line with
        # only ">" separates groups and is not an element.
        criteria = [line.strip() for line in criteria_field["value"].split("\n") if line.strip() != ""]
        if criteria == []:
            problems.append(
                {"line": criteria_field["line"], "column": 1, "severity": "error", "message": "'criteria:' has no elements"}
            )
    if answer_field is None and criteria_field is None:
        problems.append(
            {
                "line": item_line,
                "column": 1,
                "severity": "error",
                "message": "no answer: write 'A:' or 'criteria:'",
            }
        )

    # --- check and attempt ---
    check_kind: Literal["self", "exact", "numeric"] = "self"
    check_field = fields.get("check")
    if check_field is not None:
        check_value = check_field["value"]
        if check_field["is_block"]:
            check_value = "(a block)"
        if check_value == "self":
            check_kind = "self"
        elif check_value == "exact":
            check_kind = "exact"
        elif check_value == "numeric":
            check_kind = "numeric"
        else:
            problems.append(
                {
                    "line": check_field["line"],
                    "column": 1,
                    "severity": "error",
                    "message": f"check must be self, exact or numeric, found '{check_value}'",
                }
            )

    attempt_kind: Literal["recall", "typed"] = "recall"
    attempt_field = fields.get("attempt")
    if attempt_field is not None:
        attempt_value = attempt_field["value"]
        if attempt_field["is_block"]:
            attempt_value = "(a block)"
        if attempt_value == "recall":
            attempt_kind = "recall"
        elif attempt_value == "typed":
            attempt_kind = "typed"
        else:
            problems.append(
                {
                    "line": attempt_field["line"],
                    "column": 1,
                    "severity": "error",
                    "message": f"attempt must be recall or typed, found '{attempt_value}'",
                }
            )

    numeric_key: NumericKey | None = None
    if check_kind == "exact" or check_kind == "numeric":
        # D20: both grade a typed answer against the key, so both imply typed;
        # an explicit recall is a contradiction the person should resolve,
        # not one rep should pick a side of.
        if attempt_field is not None and attempt_field["value"] == "recall":
            problems.append(
                {
                    "line": attempt_field["line"],
                    "column": 1,
                    "severity": "error",
                    "message": f"check: {check_kind} grades a typed answer; remove 'attempt: recall'",
                }
            )
        attempt_kind = "typed"
        if answer_field is None or answer_field["is_block"]:
            problems.append(
                {
                    "line": item_line if answer_field is None else answer_field["line"],
                    "column": 1,
                    "severity": "error",
                    "message": f"check: {check_kind} needs a one-line 'A:' to grade against (a block cannot be typed)",
                }
            )
        elif check_kind == "numeric":
            numeric_match = NUMERIC_KEY_PATTERN.match(answer_field["value"])
            if numeric_match is None:
                problems.append(
                    {
                        "line": answer_field["line"],
                        "column": 1,
                        "severity": "error",
                        "message": (
                            f"'A: {answer_field['value']}' is not a numeric key; write a number, optionally "
                            "with '+- tolerance' or '+- percent%', such as 9.81 +- 0.01 (PLAN.md D20)"
                        ),
                    }
                )
            else:
                numeric_key = {
                    "value": numeric_match.group(1),
                    "tolerance": numeric_match.group(2),
                    "tolerance_is_percent": numeric_match.group(3) is not None,
                }

    # --- source: the explicit field wins over the section heading ---
    citekey: str | None = None
    citekey_is_unverified = False
    location: str | None = None
    source_field = fields.get("source")
    section_heading = source_item["section_heading"]
    if source_field is not None:
        source_match = None if source_field["is_block"] else SOURCE_PATTERN.match(source_field["value"])
        if source_match is None:
            problems.append(
                {
                    "line": source_field["line"],
                    "column": 1,
                    "severity": "warning",
                    "message": "source must be @citekey, @citekey:location or @citekey??, with no spaces",
                }
            )
        else:
            citekey = source_match.group(1)
            citekey_is_unverified = source_match.group(2) is not None
            location = source_match.group(3)
    elif section_heading is not None and section_heading.startswith("@"):
        section_match = SECTION_SOURCE_PATTERN.match(section_heading)
        if section_match is None:
            problems.append(
                {
                    "line": item_line,
                    "column": 1,
                    "severity": "warning",
                    "message": (
                        f"the section heading '## {section_heading}' starts with '@' but is not "
                        "a citekey, so this item has no source"
                    ),
                }
            )
        else:
            citekey = section_match.group(1)
            citekey_is_unverified = section_match.group(2) is not None

    # --- tags ---
    tags: list[str] = []
    tags_field = fields.get("tags")
    if tags_field is not None:
        for tag in tags_field["value"].split():
            if TAG_PATTERN.match(tag) is None:
                problems.append(
                    {
                        "line": tags_field["line"],
                        "column": 1,
                        "severity": "warning",
                        "message": (
                            f"tag '{tag}' is not kbd form: '#' then lowercase or ACRONYM parts "
                            "joined by '_', such as #genome_stability or #ORC"
                        ),
                    }
                )
            else:
                tags.append(tag)

    # The format of by: belongs to its writer, `rep accept` (M4); until then
    # it is carried as written.
    by_field = fields.get("by")

    if any(problem["severity"] == "error" for problem in problems):
        return None, problems
    assert item_id != "", "no error was reported, so the id was read"
    assert (check_kind == "numeric") == (numeric_key is not None), "numeric key set exactly for numeric"
    item: Item = {
        "id": item_id,
        "line": item_line,
        "question": source_item["question"],
        "answer": answer,
        "criteria": criteria,
        "check": check_kind,
        "attempt": attempt_kind,
        "numeric_key": numeric_key,
        "citekey": citekey,
        "citekey_is_unverified": citekey_is_unverified,
        "location": location,
        "tags": tags,
        "by": None if by_field is None else by_field["value"],
        "open_questions": [open_question["value"] for open_question in source_item["open_questions"]],
    }
    return item, problems


def stamp_library_text(
    text: str,
    existing_item_ids: set[str],
    random_bytes: Callable[[int], bytes],
) -> StampResult:
    """Insert an `id:` line for every item that has no `id:` field (L5-L8).

    PRE   text is the decoded content of one library file. existing_item_ids
          holds the ids of the rest of the library (I1 is library-wide).
          random_bytes(count) returns count random bytes (the shell passes
          secrets.token_bytes; tests pass a seeded source).
    POST  L5-L8. stamped_item_ids lists the new ids in file order.
    """
    source_items = parse_library_text(text)
    # L7 (PLAN.md I9): with a parse error the item boundaries themselves may
    # be wrong, so an inserted line could land inside the wrong item.
    blocking_problems = [
        problem for source_item in source_items for problem in source_item["problems"] if problem["severity"] == "error"
    ]
    if blocking_problems:
        return {"text": text, "stamped_item_ids": [], "problems": blocking_problems}

    taken_item_ids = set(existing_item_ids)
    for source_item in source_items:
        if "id" in source_item["fields"]:
            taken_item_ids.add(source_item["fields"]["id"]["value"])

    # Offsets into the text as written. Parsing normalized to NFC and dropped
    # a byte-order mark, but neither changes which "\n" ends which line, so
    # the parser's line numbers index these lines exactly.
    raw_lines = text.split("\n")
    line_start_offsets: list[int] = []
    running_offset = 0
    for raw_line in raw_lines:
        line_start_offsets.append(running_offset)
        running_offset += len(raw_line) + 1
    file_line_ending = "\r\n" if "\r\n" in text else "\n"

    insertions: list[tuple[int, str]] = []
    stamped_item_ids: list[str] = []
    for source_item in source_items:
        if "id" in source_item["fields"]:
            continue

        # --- stem: up to three content words, lowercase ASCII ---
        # NFKD splits accents from letters (and full-width or ligature forms
        # into ASCII), then everything still outside ASCII is dropped; so
        # "Strasse" spelled with sharp s gives "strae". Accepted: the id is
        # an identity, not a transliteration, and a table of special cases
        # would cover some languages arbitrarily.
        ascii_question = (
            unicodedata.normalize("NFKD", source_item["question"]).encode("ascii", "ignore").decode("ascii").lower()
        )
        stem_words = [
            word
            for word in re.split(r"[^a-z0-9]+", ascii_question)
            if word != "" and word not in ID_STEM_STOPWORDS
        ][:ID_STEM_WORD_LIMIT]
        # No ASCII letter at all (CONVENTIONS.md), or only function words:
        # either way there is nothing readable to put in the stem.
        if re.search(r"[a-z]", ascii_question) is None or stem_words == []:
            id_stem = "q"
            suffix_length = ID_NO_WORDS_SUFFIX_LENGTH
        else:
            id_stem = "-".join(stem_words)
            suffix_length = ID_SUFFIX_LENGTH

        # --- suffix: drawn until unused (L8) ---
        new_item_id = ""
        for _draw_number in range(ID_DRAW_LIMIT):
            # Each byte picks one character; 256 is a multiple of 32, so
            # every character is equally likely (as for device ids).
            suffix = "".join(
                DEVICE_ID_ALPHABET[random_byte % len(DEVICE_ID_ALPHABET)] for random_byte in random_bytes(suffix_length)
            )
            candidate_item_id = f"{id_stem}-{suffix}"
            if candidate_item_id not in taken_item_ids:
                new_item_id = candidate_item_id
                break
        assert new_item_id != "", f"no unused id after {ID_DRAW_LIMIT} draws: the random source is broken"
        assert ITEM_ID_PATTERN.match(new_item_id) is not None, f"generated id is malformed: {new_item_id!r}"
        taken_item_ids.add(new_item_id)
        stamped_item_ids.append(new_item_id)

        # --- where: the start of the line after the question ---
        question_end_index = source_item["question_end_line"] - 1
        if question_end_index == len(raw_lines) - 1:
            # The question is the file's last line and has no line ending:
            # the ending goes before the id, so the question's own characters
            # are untouched (L6).
            insertions.append((len(text), f"{file_line_ending}id: {new_item_id}"))
        else:
            # The inserted line ends the way its neighbor above does, so a
            # CRLF file stays CRLF and nvim sees no mixed endings.
            line_ending = "\r\n" if raw_lines[question_end_index].endswith("\r") else "\n"
            insertions.append((line_start_offsets[question_end_index + 1], f"id: {new_item_id}{line_ending}"))

    # Insert from the end so earlier offsets stay valid.
    stamped_text = text
    for insertion_offset, inserted_text in reversed(insertions):
        stamped_text = stamped_text[:insertion_offset] + inserted_text + stamped_text[insertion_offset:]

    # L5 and L7 by construction: reparsing finds the same items, all with an
    # id, and no error, so a second stamp has nothing to do.
    stamped_source_items = parse_library_text(stamped_text)
    assert len(stamped_source_items) == len(source_items), "stamping changed the number of items"
    assert all("id" in source_item["fields"] for source_item in stamped_source_items), "an item is still without an id"
    assert not any(
        problem["severity"] == "error" for source_item in stamped_source_items for problem in source_item["problems"]
    ), "stamping introduced a parse error"
    return {"text": stamped_text, "stamped_item_ids": stamped_item_ids, "problems": []}
