"""Spike: the impure shell around author_parse -- the git-commit pattern.

author_session(initial_text, editor, ...) -> list[dict] | None
    Write buffer to a temp file, spawn $EDITOR on it, parse on exit.
    On parse error: reinsert the error as comment lines at the top and
    reopen, so the author fixes in place (nvim stays smooth: one buffer,
    no flags, errors arrive where the eyes already are). Unchanged or
    emptied buffer aborts (returns None), exactly like git commit.

This is the ONLY impure piece; everything it calls is pure. In drill it
would live beside MAIN (a small cli entry), never in logic.
"""

import os
import subprocess
import tempfile

from author import author_parse
from logic import ImportParseError

MAX_ATTEMPTS = 5


def _strip_error_banner(text: str) -> str:
    lines = [ln for ln in text.splitlines() if not ln.startswith("#! ")]
    return "\n".join(lines)


def author_session(initial_text: str, editor: list[str],
                   max_attempts: int = MAX_ATTEMPTS) -> list[dict] | None:
    buffer_text = initial_text
    for _ in range(max_attempts):
        with tempfile.NamedTemporaryFile(
            "w", suffix=".drill", delete=False, encoding="utf-8"
        ) as handle:
            handle.write(buffer_text)
            path = handle.name
        try:
            subprocess.run(editor + [path], check=True)
            with open(path, "r", encoding="utf-8") as handle:
                edited = handle.read()
        finally:
            os.unlink(path)
        cleaned = _strip_error_banner(edited)
        if cleaned.strip() == "" or cleaned == _strip_error_banner(buffer_text):
            return None  # abort: emptied or untouched, the git-commit contract
        try:
            return author_parse(cleaned)
        except ImportParseError as error:
            buffer_text = "#! ERROR: %s\n#! fix and save again; empty to abort\n%s" % (
                error, cleaned
            )
    return None


if __name__ == "__main__":
    # Headless demonstration: EDITOR is a script. Pass 1 writes a broken
    # buffer (bad qtype); pass 2 sees the reinserted error banner and fixes
    # it. Proves the loop without a tty.
    fake_editor = os.path.join(tempfile.gettempdir(), "fake_editor.py")
    with open(fake_editor, "w", encoding="utf-8") as handle:
        handle.write(
            "import sys\n"
            "path = sys.argv[1]\n"
            "text = open(path).read()\n"
            "if '#! ERROR' not in text:\n"
            "    out = 'q: Capital of France?\\na: Paris\\ntype: essay\\n'\n"
            "else:\n"
            "    assert 'qtype' in text, 'error banner missing'\n"
            "    out = text.replace('type: essay', 'type: free_response')\n"
            "open(path, 'w').write(out)\n"
        )
    result = author_session("q: \na: \n", ["python3", fake_editor])
    assert result is not None and result[0]["answer"] == "Paris" \
        and result[0]["qtype"] == "free_response", result
    print("PASS  editor loop: error banner shown, fixed in place, parsed")
    untouched = author_session("q: \na: \n", ["python3", "-c", "pass"])
    assert untouched is None
    print("PASS  untouched buffer aborts cleanly")
