# sm2

Spaced repetition study tool. See B.17 for full documentation.

    uv run sm2.py
    uv run sm2.py --validate

## format
@@@ id: <domain>-<topic>-<hint>
[after: <comma-separated prerequisite ids>]
[tags: <comma-separated tags>]
<content -- free text, may be multi-line>
criteria: <one line defining correct performance>
