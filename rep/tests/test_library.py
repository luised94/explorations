"""The library parser at its contract: line kinds, item boundaries, problems, round trip."""

import unicodedata

from hypothesis import given, settings
from hypothesis import strategies as strategies

from rep.library import Field, SourceItem, parse_library_text, render_library_items

CONVENTIONS_EXAMPLE = """\
## @Lehninger2021

### Q: What does Km measure?
id: km-measure-7q2m
A: The substrate concentration at which velocity is half of Vmax.

### Q: How does the proton gradient drive ATP synthesis?
id: proton-gradient-drive-k3xa
source: @Lehninger2021:p712
tags: #atp #chemiosmosis
attempt: typed
criteria:
    > the electron transport chain builds the H+ gradient
    > H+ flows back through Fo, turning the rotor
    > rotation drives F1 to phosphorylate ADP
?: is the c-ring stoichiometry worth its own item?
"""


def test_conventions_example_parses_to_the_records_it_describes() -> None:
    items = parse_library_text(CONVENTIONS_EXAMPLE)
    assert len(items) == 2
    first_item, second_item = items
    assert first_item == {
        "line": 3,
        "section_heading": "@Lehninger2021",
        "question": "What does Km measure?",
        "question_is_block": False,
        "fields": {
            "id": {"key": "id", "value": "km-measure-7q2m", "is_block": False, "line": 4},
            "A": {
                "key": "A",
                "value": "The substrate concentration at which velocity is half of Vmax.",
                "is_block": False,
                "line": 5,
            },
        },
        "open_questions": [],
        "problems": [],
    }
    assert second_item["line"] == 7
    assert list(second_item["fields"]) == ["id", "source", "tags", "attempt", "criteria"]
    assert second_item["fields"]["criteria"] == {
        "key": "criteria",
        "value": (
            "the electron transport chain builds the H+ gradient\n"
            "H+ flows back through Fo, turning the rotor\n"
            "rotation drives F1 to phosphorylate ADP"
        ),
        "is_block": True,
        "line": 12,
    }
    assert second_item["open_questions"] == [
        {"key": "?", "value": "is the c-ring stoichiometry worth its own item?", "is_block": False, "line": 16}
    ]
    assert second_item["problems"] == []


def test_block_question_and_paragraph_break() -> None:
    items = parse_library_text("### Q:\n    > Prove that\n    >\n    >   x > 0\nA: done\n")
    assert items[0]["question"] == "Prove that\n\n  x > 0"
    assert items[0]["question_is_block"] is True
    assert items[0]["fields"]["A"]["value"] == "done"
    assert items[0]["problems"] == []


def test_items_end_at_headings_and_blank_lines_do_not_end_them() -> None:
    text = (
        "free notes before the first item\n"
        "> a kbd excerpt\n"
        "### Q: one\n"
        "\n"
        "\n"
        "A: first\n"
        "### Q: two\n"
        "A: second\n"
        "## A topic\n"
        "text under a topic heading is notes\n"
        "### Notes\n"
        "text under a non-item heading is notes: not an error\n"
        "### Q: three\n"
        "A: third\n"
    )
    items = parse_library_text(text)
    assert [item["question"] for item in items] == ["one", "two", "three"]
    assert [item["fields"]["A"]["value"] for item in items] == ["first", "second", "third"]
    assert [item["section_heading"] for item in items] == [None, None, "A topic"]
    assert all(item["problems"] == [] for item in items)


def test_crlf_and_byte_order_mark_read_the_same_as_plain_lf() -> None:
    windows_text = "\ufeff" + CONVENTIONS_EXAMPLE.replace("\n", "\r\n")
    assert parse_library_text(windows_text) == parse_library_text(CONVENTIONS_EXAMPLE)


def test_only_newline_splits_lines() -> None:
    # U+2028 and form feed are line breaks to str.splitlines but not to nvim:
    # the value keeps them and the next item's line number is unchanged (L4).
    items = parse_library_text("### Q: a\u2028b\x0cc\nA: x\n### Q: next\nA: y\n")
    assert items[0]["question"] == "a\u2028b\x0cc"
    assert items[1]["line"] == 3


def test_content_is_normalized_to_nfc() -> None:
    decomposed_question = unicodedata.normalize("NFD", "caf\u00e9 \u00fcber")
    assert decomposed_question != "caf\u00e9 \u00fcber"
    items = parse_library_text(f"### Q: {decomposed_question}\nA: x\n")
    assert items[0]["question"] == "caf\u00e9 \u00fcber"


def test_syntax_problems_are_reported_on_their_item_and_line() -> None:
    text = (
        "### Q: fine\n"  # 1
        "A: x\n"  # 2
        "### Q:\n"  # 3  empty question: no block follows
        "A: y\n"  # 4
        "A: again\n"  # 5  duplicate field
        "criteria:\n"  # 6  marker with no block
        "\n"  # 7
        "    > cut off from its marker\n"  # 8
        "this line has no marker\n"  # 9
        "  A: indented field\n"  # 10
        "B:no space after colon\n"  # 11
        "?:\n"  # 12 empty open question (warning)
    )
    items = parse_library_text(text)
    assert items[0]["problems"] == []
    reported = [(problem["line"], problem["severity"]) for problem in items[1]["problems"]]
    assert reported == [
        (3, "error"),
        (5, "error"),
        (6, "error"),
        (8, "error"),
        (9, "error"),
        (10, "error"),
        (11, "error"),
        (12, "warning"),
    ]
    # The first of a duplicated field is kept.
    assert items[1]["fields"]["A"]["value"] == "y"
    assert "line 4" in items[1]["problems"][1]["message"]


def test_a_block_at_the_end_of_the_file_is_closed() -> None:
    items = parse_library_text("### Q: q\ncriteria:\n    > one\n    > two")
    assert items[0]["fields"]["criteria"]["value"] == "one\ntwo"
    assert items[0]["problems"] == []


# --- properties -------------------------------------------------------------

# A targeted alphabet, not uniform Unicode: uniform text almost never forms
# the grammar's markers ("### Q:", "    >", "key:") or puts a combining mark
# after one, so it rarely reaches the classification and NFC paths where the
# parser can be wrong. The edge characters: whitespace that str.strip removes but "\n" split
# does not see (U+3000, U+0085), line breaks only str.splitlines knows
# (U+2028, form feed, vertical tab), a combining acute that NFC composes with
# "e", a combining long solidus that NFC composes with ">" and "=", sharp s,
# an astral character, a byte-order mark, NUL.
GRAMMAR_CHARACTERS = "#Q:>?Aaz0_-@ \t"
UNICODE_EDGE_CHARACTERS = "e\u00e9\u0301\u0338=\u00df\u3000\u0085\u2028\x0c\x0b\U0001f600\ufeff\x00"
line_characters = strategies.sampled_from(GRAMMAR_CHARACTERS + UNICODE_EDGE_CHARACTERS)
nfc_line_text = strategies.text(alphabet=line_characters, max_size=12).map(
    lambda text: unicodedata.normalize("NFC", text)
)
inline_text = nfc_line_text.map(str.strip).filter(lambda text: text != "")
block_text = strategies.lists(nfc_line_text.map(str.rstrip), min_size=1, max_size=4).map("\n".join)
# The language of FIELD_PATTERN's key, [A-Za-z][A-Za-z0-9_]*, built from two
# sampled alphabets: from_regex builds Hypothesis's character table on first
# use (1.75 s measured), the cause of the too_slow failure on a fresh checkout.
ASCII_LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz"
field_key = strategies.tuples(
    strategies.sampled_from(ASCII_LETTERS),
    strategies.text(alphabet=strategies.sampled_from(ASCII_LETTERS + "0123456789_"), max_size=5),
).map("".join)


@strategies.composite
def source_items(draw: strategies.DrawFn) -> list[SourceItem]:
    item_count = draw(strategies.integers(min_value=0, max_value=4))
    items: list[SourceItem] = []
    section_heading: str | None = None
    for _item_number in range(item_count):
        # A file can enter a section or change it, never leave it.
        if draw(strategies.booleans()):
            section_heading = draw(nfc_line_text.map(str.strip))
        question_is_block = draw(strategies.booleans())
        question = draw(block_text if question_is_block else inline_text)
        fields: dict[str, Field] = {}
        for key in draw(strategies.lists(field_key, max_size=4, unique=True)):
            is_block = draw(strategies.booleans())
            fields[key] = {
                "key": key,
                "value": draw(block_text if is_block else inline_text),
                "is_block": is_block,
                "line": 0,
            }
        open_question_values = draw(strategies.lists(inline_text, max_size=2))
        item: SourceItem = {
            "line": 0,
            "section_heading": section_heading,
            "question": question,
            "question_is_block": question_is_block,
            "fields": fields,
            "open_questions": [
                {"key": "?", "value": value, "is_block": False, "line": 0} for value in open_question_values
            ],
            "problems": [],
        }
        items.append(item)
    return items


@settings(max_examples=300)
@given(source_items())
def test_parse_of_render_is_identity_apart_from_line_numbers(items: list[SourceItem]) -> None:
    parsed_items = parse_library_text(render_library_items(items))
    assert all(item["problems"] == [] for item in parsed_items), [item["problems"] for item in parsed_items]
    for parsed_item in parsed_items:
        parsed_item["line"] = 0
        for field in parsed_item["fields"].values():
            field["line"] = 0
        for open_question in parsed_item["open_questions"]:
            open_question["line"] = 0
    assert parsed_items == items


@settings(max_examples=500)
@given(
    strategies.lists(
        strategies.sampled_from(["### Q:", "## ", "###", "    >", "\t>", "A:", "?:", "\n", "\r\n", ""]).flatmap(
            lambda prefix: strategies.text(alphabet=line_characters, max_size=6).map(lambda rest: prefix + rest)
        ),
        max_size=12,
    ).map("".join)
)
def test_parser_is_total_and_problem_lines_exist(text: str) -> None:
    line_count = unicodedata.normalize("NFC", text).count("\n") + 1
    for item in parse_library_text(text):
        assert 1 <= item["line"] <= line_count
        for problem in item["problems"]:
            assert 1 <= problem["line"] <= line_count
