"""Spike: editor-buffer authoring format for drill questions.

Design intent (Steenberg-style thin consistent API):
    author_parse(text)      -> list[dict]   pure; text -> canonical dicts
    author_render(records)  -> str          pure; inverse of parse
    author_template(n)      -> str          pure; commented starter buffer
    author_session(...)                     impure shell; $EDITOR loop

The format is deliberately smaller than sm2's @@@ format because it is a
TRANSIENT INBOX, not a canonical store: no ids (drill assigns integers),
no source tracking, no cross-file policy. Blocks separated by blank
lines; 'key: value' lines; '|' separates array values (drill's existing
CSV cell convention); '#' lines are comments. Keys mirror the canonical
dict; short aliases q/a for the two required fields.

Everything funnels through drill's _normalize_question_dict, so this
adds a projection, not a second validation authority. Output is the
exact dict parse_jsonl produces -> trivially json.dumps-able.
"""

from logic import ImportParseError, _normalize_question_dict

KEY_ALIASES = {"q": "question", "a": "answer", "alt": "alternatives",
               "type": "qtype", "hint": "hints"}
ARRAY_FIELDS = ("alternatives", "distractors", "hints", "tags")
KNOWN_KEYS = ("question", "answer", "qtype", "alternatives", "distractors",
              "hints", "tags", "media_url", "difficulty")
ARRAY_SEPARATOR = "|"


def author_parse(text: str) -> list[dict]:
    """Parse an editor buffer into canonical question dicts. Pure.

    Raises ImportParseError naming the block and line on any problem, so
    the editor loop can reopen the buffer with the error shown.
    """
    records: list[dict] = []
    block: dict = {}
    block_start_line = 0

    def close_block(line_number: int) -> None:
        if not block:
            return
        try:
            records.append(_normalize_question_dict(block))
        except ImportParseError as error:
            raise ImportParseError(
                "block starting at line %d: %s" % (block_start_line, error)
            )
        block.clear()

    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.rstrip()
        if line.lstrip().startswith("#"):
            continue
        if line.strip() == "":
            close_block(line_number)
            continue
        if ":" not in line:
            raise ImportParseError(
                "line %d: expected 'key: value', got %r" % (line_number, line)
            )
        key, _, value = line.partition(":")
        key = KEY_ALIASES.get(key.strip(), key.strip())
        value = value.strip()
        if key not in KNOWN_KEYS:
            raise ImportParseError(
                "line %d: unknown key %r (known: %s)"
                % (line_number, key, ", ".join(KNOWN_KEYS))
            )
        if not block:
            block_start_line = line_number
        if key in block:
            raise ImportParseError(
                "line %d: duplicate key %r in one block" % (line_number, key)
            )
        if key in ARRAY_FIELDS:
            block[key] = [piece.strip() for piece in value.split(ARRAY_SEPARATOR)
                          if piece.strip() != ""]
        else:
            block[key] = value
    close_block(-1)
    return records


def author_render(records: list[dict]) -> str:
    """Render canonical dicts back into the buffer format. Pure.

    Inverse of author_parse for every representable record; omits
    empty/default fields so round-trips stay minimal.
    """
    blocks: list[str] = []
    for record in records:
        lines = ["q: " + record["question"], "a: " + record["answer"]]
        if record.get("qtype") and record["qtype"] != "free_response":
            lines.append("type: " + record["qtype"])
        for field in ARRAY_FIELDS:
            values = record.get(field) or []
            if values:
                lines.append(field + ": " + (" " + ARRAY_SEPARATOR + " ").join(values))
        if record.get("media_url"):
            lines.append("media_url: " + record["media_url"])
        if record.get("difficulty") is not None:
            lines.append("difficulty: " + str(record["difficulty"]))
        blocks.append("\n".join(lines))
    return "\n\n".join(blocks) + "\n"


def author_template(count: int = 1) -> str:
    """Starter buffer with the format documented in comments. Pure."""
    header = (
        "# One question per block; blank line between blocks.\n"
        "# Required: q, a. Optional: type (free_response|multiple_choice|\n"
        "# translate|identify|arithmetic), alt, distractors, hint, tags,\n"
        "# media_url, difficulty (1-5). Arrays use ' | '.\n"
        "# Lines starting with '#' are ignored. Empty buffer aborts.\n\n"
    )
    return header + "\n\n".join("q: \na: " for _ in range(count)) + "\n"
