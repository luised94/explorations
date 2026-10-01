"""The library unit at its contract: parser, writer, checks and stamp."""

import decimal
import hashlib
import random
import re
import unicodedata
from collections.abc import Callable
from decimal import Decimal

from hypothesis import given, settings
from hypothesis import strategies as strategies

import pytest

from rep.library import (
    ITEM_ID_PATTERN,
    Field,
    Item,
    SourceItem,
    check_source_item,
    grade_typed_answer,
    item_fingerprint,
    parse_library_text,
    plan_library_append,
    render_library_items,
    stamp_library_text,
)
from rep.machine import DEVICE_ID_ALPHABET

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
        "question_end_line": 3,
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
    assert items[0]["question_end_line"] == 4
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
            "question_end_line": 0,
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
        parsed_item["question_end_line"] = 0
        for field in parsed_item["fields"].values():
            field["line"] = 0
        for open_question in parsed_item["open_questions"]:
            open_question["line"] = 0
    assert parsed_items == items


@settings(max_examples=500)
@given(
    strategies.lists(
        strategies.sampled_from(
            ["### Q:", "## @", "## ", "###", "    >", "\t>", "A: ", "?:", "\n", "\r\n", "",
             "check: numeric", "check: exact", "attempt: recall", "id: ", "source: @", "tags: #", "criteria:"]
        ).flatmap(
            lambda prefix: strategies.text(alphabet=line_characters, max_size=6).map(lambda rest: prefix + rest)
        ),
        max_size=12,
    ).map("".join)
)
def test_parser_is_total_and_problem_lines_exist(text: str) -> None:
    line_count = unicodedata.normalize("NFC", text).count("\n") + 1
    for source_item in parse_library_text(text):
        assert 1 <= source_item["line"] <= line_count
        # Checking is total too, and an Item exists exactly when no error does.
        item, problems = check_source_item(source_item)
        for problem in problems:
            assert 1 <= problem["line"] <= line_count
        has_error = any(problem["severity"] == "error" for problem in problems)
        assert (item is None) == has_error


# --- checks -----------------------------------------------------------------

VALID_ITEM = "### Q: What does Km measure?\nid: km-measure-7q2m\nA: half of Vmax\n"


def test_conventions_example_checks_into_session_items() -> None:
    first_source_item, second_source_item = parse_library_text(CONVENTIONS_EXAMPLE)
    first_item, first_problems = check_source_item(first_source_item)
    assert first_problems == []
    assert first_item == {
        "id": "km-measure-7q2m",
        "line": 3,
        "question": "What does Km measure?",
        "answer": "The substrate concentration at which velocity is half of Vmax.",
        "criteria": None,
        "check": "self",
        "attempt": "recall",
        "numeric_key": None,
        "citekey": "Lehninger2021",
        "citekey_is_unverified": False,
        "location": None,
        "tags": [],
        "by": None,
        "open_questions": [],
    }
    second_item, second_problems = check_source_item(second_source_item)
    assert second_problems == []
    assert second_item is not None
    assert second_item["criteria"] == [
        "the electron transport chain builds the H+ gradient",
        "H+ flows back through Fo, turning the rotor",
        "rotation drives F1 to phosphorylate ADP",
    ]
    assert (second_item["citekey"], second_item["location"]) == ("Lehninger2021", "p712")
    assert second_item["tags"] == ["#atp", "#chemiosmosis"]
    assert second_item["attempt"] == "typed"
    assert second_item["open_questions"] == ["is the c-ring stoichiometry worth its own item?"]


def test_parser_problems_pass_through_and_exclude_the_item() -> None:
    (source_item,) = parse_library_text(VALID_ITEM + "stray line\n")
    item, problems = check_source_item(source_item)
    assert item is None
    assert [(problem["line"], problem["severity"]) for problem in problems] == [(4, "error")]


# Each case appends lines to VALID_ITEM (or replaces it) and names the one
# problem expected: its line, its severity and a fragment of its message.
@pytest.mark.parametrize(
    ("item_text", "expected_line", "expected_severity", "message_fragment"),
    [
        ("### Q: q\nA: a\n", 1, "error", "no id"),
        ("### Q: q\nid:\n    > km-7q2m\nA: a\n", 2, "error", "one word of printable ASCII"),
        ("### Q: q\nid: two words\nA: a\n", 2, "error", "one word of printable ASCII"),
        ("### Q: q\nid: caf\u00e9-7q2m\nA: a\n", 2, "error", "one word of printable ASCII"),
        ("### Q: q\nid: km-measure-7q2i\nA: a\n", 2, "warning", "not in the form rep writes"),
        ("### Q: q\nid: a-b-c-d-7q2m\nA: a\n", 2, "warning", "not in the form rep writes"),
        ("### Q: q\nid: km-7q2m\n", 1, "error", "no answer"),
        ("### Q: q\nid: km-7q2m\ncriteria:\n    >\n", 3, "error", "no elements"),
        (VALID_ITEM + "check: fuzzy\n", 4, "error", "check must be"),
        (VALID_ITEM + "attempt: spoken\n", 4, "error", "attempt must be"),
        (VALID_ITEM + "check: exact\nattempt: recall\n", 5, "error", "remove 'attempt: recall'"),
        ("### Q: q\nid: km-7q2m\ncriteria: c\ncheck: exact\n", 1, "error", "needs a one-line 'A:'"),
        ("### Q: q\nid: km-7q2m\nA:\n    > 9.81\ncheck: numeric\n", 3, "error", "needs a one-line 'A:'"),
        ("### Q: q\nid: km-7q2m\nA: 9.81 m/s^2\ncheck: numeric\n", 3, "error", "not a numeric key"),
        (VALID_ITEM + "a: lowercase answer\n", 4, "warning", "did you mean 'A:'"),
        (VALID_ITEM + "colour: blue\n", 4, "warning", "unknown field 'colour'"),
        (VALID_ITEM + "source: Lehninger2021\n", 4, "warning", "source must be"),
        (VALID_ITEM + "source: @Key two\n", 4, "warning", "source must be"),
        ("## @Key with words\n\n" + VALID_ITEM, 3, "warning", "is not a citekey"),
        (VALID_ITEM + "tags: #Genome_stability\n", 4, "warning", "not kbd form"),
        (VALID_ITEM + "tags: atp\n", 4, "warning", "not kbd form"),
    ],
)
def test_each_injected_violation_is_reported_once(
    item_text: str, expected_line: int, expected_severity: str, message_fragment: str
) -> None:
    (source_item,) = parse_library_text(item_text)
    item, problems = check_source_item(source_item)
    assert len(problems) == 1, problems
    (problem,) = problems
    assert (problem["line"], problem["severity"]) == (expected_line, expected_severity)
    assert message_fragment in problem["message"]
    # SEVERITY: errors exclude the item, warnings never do.
    assert (item is None) == (expected_severity == "error")


@pytest.mark.parametrize(
    ("answer_text", "expected_key"),
    [
        ("9.81", {"value": "9.81", "tolerance": None, "tolerance_is_percent": False}),
        ("-9.81 +- 0.01", {"value": "-9.81", "tolerance": "0.01", "tolerance_is_percent": False}),
        ("6.022e23 +- 0.1%", {"value": "6.022e23", "tolerance": "0.1", "tolerance_is_percent": True}),
        ("+.5+-1E-3", {"value": "+.5", "tolerance": "1E-3", "tolerance_is_percent": False}),
        ("1000", {"value": "1000", "tolerance": None, "tolerance_is_percent": False}),
    ],
)
def test_numeric_keys_in_d20_syntax_are_read(answer_text: str, expected_key: dict[str, object]) -> None:
    (source_item,) = parse_library_text(f"### Q: q\nid: km-7q2m\nA: {answer_text}\ncheck: numeric\n")
    item, problems = check_source_item(source_item)
    assert problems == []
    assert item is not None and item["numeric_key"] == expected_key
    assert item["attempt"] == "typed"


@pytest.mark.parametrize(
    "answer_text",
    ["1,000", "3,14", "1/3", "Infinity", "NaN", "inf", "9.81 +- -0.01", "9.81 +-", "\u0663", "0x1F", "9.81 +- 1 %", ""],
)
def test_numeric_keys_outside_d20_syntax_are_errors(answer_text: str) -> None:
    (source_item,) = parse_library_text(f"### Q: q\nid: km-7q2m\nA: {answer_text}\ncheck: numeric\n")
    item, problems = check_source_item(source_item)
    assert item is None
    assert any(problem["severity"] == "error" for problem in problems)


def test_sources_citekeys_and_locations() -> None:
    text = (
        "## @St.AthanasiusOrthodoxAcademy2008orthodox\n"
        "### Q: a\nid: a-7q2m\nA: x\n"
        "### Q: b\nid: b-7q2m\nA: x\nsource: @osb:John.3.16\n"
        "### Q: c\nid: c-7q2m\nA: x\nsource: @Matsui1980??:p12\n"
        "## @Matsui1980??\n"
        "### Q: d\nid: d-7q2m\nA: x\n"
        "## A topic\n"
        "### Q: e\nid: e-7q2m\nA: x\n"
    )
    checked = [check_source_item(source_item) for source_item in parse_library_text(text)]
    assert all(problems == [] for _item, problems in checked)
    sources = [
        (item["citekey"], item["citekey_is_unverified"], item["location"]) for item, _problems in checked if item is not None
    ]
    assert sources == [
        ("St.AthanasiusOrthodoxAcademy2008orthodox", False, None),
        ("osb", False, "John.3.16"),
        ("Matsui1980", True, "p12"),
        ("Matsui1980", True, None),
        (None, False, None),
    ]


def test_q_form_and_one_word_ids_are_rep_form() -> None:
    for item_id in ("q-7q2m3x", "km-7q2m", "a-b-c-7q2m"):
        (source_item,) = parse_library_text(f"### Q: q\nid: {item_id}\nA: a\n")
        assert check_source_item(source_item)[1] == [], item_id


# --- stamp ------------------------------------------------------------------


def fixed_suffix_source(suffixes: list[str]) -> Callable[[int], bytes]:
    # Returns bytes that DEVICE_ID_ALPHABET maps to each suffix in turn, so a
    # test can name the exact ids it expects, including forced collisions.
    remaining_suffixes = list(suffixes)

    def next_bytes(count: int) -> bytes:
        suffix = remaining_suffixes.pop(0)
        assert len(suffix) == count
        return bytes(DEVICE_ID_ALPHABET.index(character) for character in suffix)

    return next_bytes


def test_stamp_inserts_ids_after_each_question_and_nothing_else() -> None:
    text = (
        "## @Lehninger2021\n"
        "\n"
        "### Q: What does Km measure?\n"
        "A: half of Vmax\n"
        "\n"
        "### Q:\n"
        "    > How does the proton gradient\n"
        "    > drive ATP synthesis?\n"
        "criteria: rotor turns\n"
        "### Q: already stamped\n"
        "id: kept-as-written\n"
        "A: x\n"
    )
    result = stamp_library_text(text, set(), fixed_suffix_source(["7q2m", "k3xa"]))
    assert result["problems"] == []
    assert result["stamped_item_ids"] == ["km-measure-7q2m", "proton-gradient-drive-k3xa"]
    assert result["text"] == (
        "## @Lehninger2021\n"
        "\n"
        "### Q: What does Km measure?\n"
        "id: km-measure-7q2m\n"
        "A: half of Vmax\n"
        "\n"
        "### Q:\n"
        "    > How does the proton gradient\n"
        "    > drive ATP synthesis?\n"
        "id: proton-gradient-drive-k3xa\n"
        "criteria: rotor turns\n"
        "### Q: already stamped\n"
        "id: kept-as-written\n"
        "A: x\n"
    )


@pytest.mark.parametrize(
    ("question", "expected_item_id"),
    [
        # Accents are stripped; letters NFKD cannot decompose (sharp s) drop.
        ("\u00bfQu\u00e9 significa Stra\u00dfe?", "que-significa-strae-7q2m"),
        # Full-width and ligature forms become ASCII under NFKD.
        ("\uff21\uff34\uff30 \ufb01xation", "atp-fixation-7q2m"),
        ("What is 2 + 2 in base 3?", "2-2-base-7q2m"),
        ("2 + 2 = ?", "q-7q2m3x"),
        ("What is it?", "q-7q2m3x"),
        ("\u03bb\u03cc\u03b3\u03bf\u03c2", "q-7q2m3x"),
    ],
)
def test_id_stems(question: str, expected_item_id: str) -> None:
    suffix = "7q2m" if not expected_item_id.startswith("q-") else "7q2m3x"
    result = stamp_library_text(f"### Q: {question}\nA: x\n", set(), fixed_suffix_source([suffix]))
    assert result["stamped_item_ids"] == [expected_item_id]


def test_stamp_redraws_a_suffix_taken_anywhere_in_the_library() -> None:
    text = "### Q: Km?\nid: km-aaaa\nA: x\n### Q: Km?\nA: y\n### Q: Km?\nA: z\n"
    result = stamp_library_text(
        text, {"km-bbbb"}, fixed_suffix_source(["aaaa", "bbbb", "cccc", "cccc", "dddd"])
    )
    # aaaa is in this file, bbbb elsewhere in the library, cccc was just used.
    assert result["stamped_item_ids"] == ["km-cccc", "km-dddd"]


def test_stamp_keeps_crlf_bom_nfd_and_a_missing_final_newline() -> None:
    decomposed_question = unicodedata.normalize("NFD", "caf\u00e9 cr\u00e8me")
    text = f"\ufeff### Q: {decomposed_question}\r\nA: x\r\n### Q: last\r\nA: y\r\n### Q: final"
    result = stamp_library_text(text, set(), fixed_suffix_source(["aaaa", "bbbb", "cccc"]))
    assert result["text"] == (
        f"\ufeff### Q: {decomposed_question}\r\nid: cafe-creme-aaaa\r\nA: x\r\n"
        "### Q: last\r\nid: last-bbbb\r\nA: y\r\n"
        "### Q: final\r\nid: final-cccc"
    )


def test_stamp_refuses_any_parse_error_and_returns_the_input() -> None:
    text = "### Q: fine\nA: x\n### Q: broken\nA: y\nstray line\n"
    result = stamp_library_text(text, set(), fixed_suffix_source([]))
    assert result["text"] == text
    assert result["stamped_item_ids"] == []
    assert [problem["line"] for problem in result["problems"]] == [5]


def test_stamp_ignores_warnings_and_check_errors() -> None:
    # An empty ?: is a parse warning; a missing answer is a check error. The
    # capture template stamps before the answer is written, so neither may
    # block an id.
    result = stamp_library_text("### Q: What is Km?\n?:\n", set(), fixed_suffix_source(["aaaa"]))
    assert result["problems"] == []
    assert result["stamped_item_ids"] == ["km-aaaa"]
    assert result["text"] == "### Q: What is Km?\nid: km-aaaa\n?:\n"


stampable_text = strategies.one_of(
    source_items().map(render_library_items),
    source_items().map(render_library_items).map(lambda text: text.replace("\n", "\r\n")),
    source_items().map(render_library_items).map(lambda text: text.rstrip("\n")),
)


@settings(max_examples=300)
@given(stampable_text, strategies.integers(min_value=0, max_value=2**32))
def test_stamp_only_inserts_id_lines_and_is_idempotent(text: str, seed: int) -> None:
    result = stamp_library_text(text, set(), random.Random(seed).randbytes)
    assert result["problems"] == []
    stamped_text = result["text"]
    # L6: removing each inserted line, with the line ending inserted with it,
    # gives back the input exactly.
    unstamped_text = stamped_text
    for new_item_id in result["stamped_item_ids"]:
        assert ITEM_ID_PATTERN.match(new_item_id) is not None
        inserted_line_match = re.search(rf"(?m)^id: {re.escape(new_item_id)}(\r?\n)?", unstamped_text)
        assert inserted_line_match is not None
        start, end = inserted_line_match.span()
        if inserted_line_match.group(1) is None:
            # Inserted after a final line that had no ending: the ending was
            # inserted before the id line instead.
            start -= 2 if unstamped_text[:start].endswith("\r\n") else 1
        unstamped_text = unstamped_text[:start] + unstamped_text[end:]
    assert unstamped_text == text
    # L8: ids unique; L5: a second stamp inserts nothing.
    assert len(set(result["stamped_item_ids"])) == len(result["stamped_item_ids"])
    second_result = stamp_library_text(stamped_text, set(), random.Random(seed + 1).randbytes)
    assert second_result == {"text": stamped_text, "stamped_item_ids": [], "problems": []}


# --- append planning ----------------------------------------------------------

ADDED_ITEM = "### Q: What does Km measure?\nid: km-measure-7q2m\nsource: @Lehninger2021:p80\nA: half of Vmax\n"


@pytest.mark.parametrize(
    ("existing_text", "expected_separator"),
    [
        (None, ""),
        ("", ""),
        ("## @Lehninger2021\n\n### Q: a\nid: a-7q2m\nA: x", "\n\n"),
        ("## @Lehninger2021\n\n### Q: a\nid: a-7q2m\nA: x\n", "\n"),
        ("## @Lehninger2021\n\n### Q: a\nid: a-7q2m\nA: x\n\n", ""),
    ],
)
def test_append_is_separated_by_one_blank_line(existing_text: str | None, expected_separator: str) -> None:
    text_to_append, problems = plan_library_append(existing_text, ADDED_ITEM.rstrip("\n"), "lehninger.md")
    assert problems == []
    assert text_to_append == expected_separator + ADDED_ITEM


def test_append_takes_the_line_endings_of_the_file() -> None:
    existing_text = "### Q: a\r\nid: a-7q2m\r\nA: x\r\n"
    text_to_append, problems = plan_library_append(existing_text, ADDED_ITEM, "lehninger.md")
    assert problems == []
    assert text_to_append == "\r\n" + ADDED_ITEM.replace("\n", "\r\n")
    # A new file keeps the endings it was written with.
    assert plan_library_append(None, ADDED_ITEM.replace("\n", "\r\n"), "new.md")[0] == ADDED_ITEM.replace("\n", "\r\n")


def test_append_that_would_join_the_last_item_is_refused() -> None:
    existing_text = "### Q: a\nid: a-7q2m\nA: x\n"
    text_to_append, problems = plan_library_append(existing_text, "tags: #stray\n" + ADDED_ITEM, "lehninger.md")
    assert text_to_append == ""
    assert len(problems) == 1 and "would change the items already in lehninger.md" in problems[0]


def test_append_that_would_change_a_source_is_refused() -> None:
    existing_text = "## @OtherKey\n\n### Q: a\nid: a-7q2m\nA: x\n"
    without_source = "### Q: Km?\nid: km-7q2m\nA: x\n"
    text_to_append, problems = plan_library_append(existing_text, without_source, "other.md")
    assert text_to_append == ""
    assert len(problems) == 1 and "'## @OtherKey'" in problems[0]
    # An explicit source, or a heading of its own, keeps the meaning.
    assert plan_library_append(existing_text, ADDED_ITEM, "other.md")[1] == []
    assert plan_library_append(existing_text, "## @Lehninger2021\n\n" + without_source, "other.md")[1] == []


# --- fingerprint (PLAN.md D33, library.py L9) ---------------------------------


def checked_item(item_text: str) -> Item:
    """The one item in item_text, checked; the text must check with no error."""
    (source_item,) = parse_library_text(item_text)
    item, problems = check_source_item(source_item)
    assert item is not None, f"test item does not check: {problems}"
    return item


FINGERPRINT_BASE_ITEM = "### Q: What does Km measure?\nid: km-measure-7q2m\nA: Half of Vmax.\n"


def test_fingerprint_is_the_d33_definition_written_out() -> None:
    # The JSON is spelled out by hand here, not produced by the code under
    # test, so a change to the definition cannot pass by agreeing with itself.
    hand_written_json = '["What does Km measure?","Half of Vmax.",null,"self","recall"]'
    expected = "f1:" + hashlib.sha256(hand_written_json.encode("utf-8")).hexdigest()[:16]
    assert item_fingerprint(checked_item(FINGERPRINT_BASE_ITEM)) == expected
    # ensure_ascii=False: non-ASCII text is hashed as UTF-8, not as \u escapes.
    accented_json = '["Caf\u00e9?","Half of Vmax.",null,"self","recall"]'
    accented_item = checked_item(FINGERPRINT_BASE_ITEM.replace("What does Km measure?", "Caf\u00e9?"))
    assert item_fingerprint(accented_item) == "f1:" + hashlib.sha256(accented_json.encode("utf-8")).hexdigest()[:16]


@pytest.mark.parametrize(
    "changed_item_text",
    [
        FINGERPRINT_BASE_ITEM.replace("What does Km measure?", "What does Km measure here?"),
        FINGERPRINT_BASE_ITEM.replace("Half of Vmax.", "Half of Vmax"),
        FINGERPRINT_BASE_ITEM + "criteria:\n    > half\n",
        FINGERPRINT_BASE_ITEM + "check: exact\n",
        FINGERPRINT_BASE_ITEM + "attempt: typed\n",
    ],
)
def test_fingerprint_changes_with_each_field_that_says_what_is_asked(changed_item_text: str) -> None:
    assert item_fingerprint(checked_item(changed_item_text)) != item_fingerprint(checked_item(FINGERPRINT_BASE_ITEM))


@pytest.mark.parametrize(
    "unchanged_item_text",
    [
        FINGERPRINT_BASE_ITEM.replace("km-measure-7q2m", "km-other-7q2m"),
        "## @Lehninger2021\n\n" + FINGERPRINT_BASE_ITEM,
        FINGERPRINT_BASE_ITEM + "source: @Lehninger2021:p712\ntags: #enzymes\nby: model:x llm/a.md\n?: worth splitting?\n",
        "\n\n\n" + FINGERPRINT_BASE_ITEM,
        "### Q:\n    > What does Km measure?\nid: km-measure-7q2m\nA:\n    > Half of Vmax.\n",
    ],
)
def test_fingerprint_ignores_identity_place_and_metadata(unchanged_item_text: str) -> None:
    assert item_fingerprint(checked_item(unchanged_item_text)) == item_fingerprint(checked_item(FINGERPRINT_BASE_ITEM))


def test_fingerprint_uses_the_effective_attempt() -> None:
    # check: exact implies typed (D20), so writing it out asks nothing new.
    exact_item_text = FINGERPRINT_BASE_ITEM + "check: exact\n"
    assert item_fingerprint(checked_item(exact_item_text)) == item_fingerprint(
        checked_item(exact_item_text + "attempt: typed\n")
    )


# --- grading typed answers (PLAN.md D20, D34, library.py L10) -----------------


@pytest.mark.parametrize(
    ("key_text", "typed_answer", "expected_pass"),
    [
        ("Paris", "Paris", True),
        ("Paris", "  Paris \t", True),
        ("Saint Paul", "Saint \t  Paul", True),
        ("Saint  Paul", "Saint Paul", True),
        ("Paris", "paris", False),
        ("Paris", "Paris.", False),
        ("Haus", "haus", False),
        ("s\u00ed", "si", False),
        ("s\u00ed", "si\u0301", True),
        ("Stra\u00dfe", "Strasse", False),
        ("Paris", "", False),
    ],
)
def test_exact_grading_follows_d20(key_text: str, typed_answer: str, expected_pass: bool) -> None:
    item = checked_item(f"### Q: q\nid: km-7q2m\nA: {key_text}\ncheck: exact\n")
    assert grade_typed_answer(item, typed_answer) is expected_pass


@pytest.mark.parametrize(
    ("key_text", "typed_answer", "expected_pass"),
    [
        ("9.81", "9.81", True),
        ("9.81", "9.810", True),
        ("9.81", " 9.81 ", True),
        ("1000", "1e3", True),
        ("1000", "1E+3", True),
        ("0.5", ".5", True),
        ("5", "+5", True),
        ("9.81", "9.8", False),
        ("1", "1.0000000000000000000000000000001", False),
        ("0.1 +- 0.3", "0.4", True),
        ("0.1 +- 0.3", "-0.2", True),
        ("0.1 +- 0.3", "0.4000000000000000000000000000001", False),
        ("6.022e23 +- 1%", "6.08222e23", True),
        ("6.022e23 +- 1%", "6.0822200000001e23", False),
        ("-50 +- 10%", "-45", True),
        ("0 +- 1e30", "1000000000000000000000000000000.00001", False),
        ("1e30000", "1e30000", True),
        ("1 +- 1", "1e99999999", False),
        ("9.81", "9,81", False),
        ("1000", "1,000", False),
        ("0.5", "1/2", False),
        ("1", "Infinity", False),
        ("1", "NaN", False),
        ("1", "inf", False),
        ("1000", "1_000", False),
        ("3", "\u0663", False),
        ("9.81", "9.81 m/s^2", False),
        ("9.81", "", False),
    ],
)
def test_numeric_grading_follows_d20_exactly(key_text: str, typed_answer: str, expected_pass: bool) -> None:
    item = checked_item(f"### Q: q\nid: km-7q2m\nA: {key_text}\ncheck: numeric\n")
    assert grade_typed_answer(item, typed_answer) is expected_pass


@settings(max_examples=300)
@given(
    key_units=strategies.integers(min_value=-(10**40), max_value=10**40),
    key_exponent=strategies.integers(min_value=-40, max_value=40),
    tolerance_units=strategies.integers(min_value=0, max_value=10**40),
    tolerance_exponent=strategies.integers(min_value=-40, max_value=40),
    tolerance_is_percent=strategies.booleans(),
)
def test_numeric_tolerance_boundary_passes_and_one_unit_past_it_fails(
    key_units: int, key_exponent: int, tolerance_units: int, tolerance_exponent: int, tolerance_is_percent: bool
) -> None:
    # D20: the boundary passes. Built from integers so the expected values
    # are exact by construction, whatever the test's own arithmetic does.
    key_value = Decimal(key_units).scaleb(key_exponent)
    tolerance_value = Decimal(tolerance_units).scaleb(tolerance_exponent)
    key_text = f"{key_value} +- {tolerance_value}{'%' if tolerance_is_percent else ''}"
    item = checked_item(f"### Q: q\nid: km-7q2m\nA: {key_text}\ncheck: numeric\n")
    with decimal.localcontext() as exact_context:
        exact_context.prec = decimal.MAX_PREC
        exact_context.traps[decimal.Inexact] = True
        allowed_distance = abs(key_value) * tolerance_value / 100 if tolerance_is_percent else tolerance_value
        upper_boundary_value = key_value + allowed_distance
        lower_boundary_value = key_value - allowed_distance
        one_unit_past = upper_boundary_value + Decimal(1).scaleb(min(key_exponent, tolerance_exponent) - 3)
    # Every value above is computed inside the exact context: outside it,
    # 1 - 1E+29 rounds to 28 digits (the first version of this test did
    # that, and the property caught it).
    assert grade_typed_answer(item, str(upper_boundary_value)) is True
    assert grade_typed_answer(item, str(lower_boundary_value)) is True
    assert grade_typed_answer(item, str(one_unit_past)) is False
