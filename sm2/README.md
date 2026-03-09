
# sm2

A command-line spaced repetition tool. Parses flashcard items from Markdown
files, schedules reviews via the SM-2 algorithm, and stores all state in
SQLite. Single source file. No external dependencies.


## Requirements

- Python 3.10 or later, managed via uv
- SQLite 3.36 or later (bundled with Python on most platforms)


## Running

    uv run sm2.py

On first run the database is created at data/sm2.db. Items in exercises/ are
parsed and inserted with a due date of today. The session begins immediately.


## Item Format

Flashcard items live in Markdown files inside exercises/. Any number of .md
files are supported. Each item begins with a delimiter line at column zero:

    @@@ id: <domain>-<topic>-<hint>

Optional metadata lines follow the delimiter, before the content body:

    after: <comma-separated prerequisite item ids>
    tags:  <comma-separated tags>

The content body is all remaining lines until the next delimiter or end of
file. An optional criteria line may appear anywhere in the body:

    criteria: <one line describing the success condition>

The criteria line is shown to the user before grading. It is omitted from
display if absent.

The item id must be unique across all files. The first segment before the
first hyphen is the domain (e.g. "drive", "c", "bio"). Domain is derived
at runtime by splitting on "-" and taking the first part.

Example item:

    @@@ id: c-ptr-deref
    tags: pointers
    Given:
        int x = 42;
        int *p = &x;
        *p = 99;
    What is the value of x after the third line?
    criteria: x is 99. Writing through *p modifies the object p points to.

Content files are read-only. The tool never writes to exercises/.


## Grading

After reading a card, enter one of three grades:

    0  Failed -- could not recall or answered incorrectly
    1  Passed with effort -- recalled but with difficulty
    2  Easy, fluent -- recalled immediately without hesitation

Grade 0 prompts for an optional error note. The note is stored in the
review log for later inspection but does not affect scheduling.

Grades map to SM-2 quality scores internally:

    User grade  SM-2 q  Effect on easiness factor
    ----------  ------  -------------------------
    0           1       -0.54
    1           3       -0.14
    2           5       +0.10

Easiness factor is clamped to the range [1.3, 3.0] and is never reset on
failure. Lapsed items recover on shorter intervals due to the lowered factor.


## Throttle Policy

Each session applies three constraints to the review queue:

    total_new_max    9     hard cap on new items introduced per session
    min_per_domain   1     at least one new item per domain if any are due
    max_reviews      100   hard cap on total items reviewed per session

New item = repetition_count == 0 in the database (never had a successful
review). The floor guarantee (min_per_domain) ensures no domain is starved
when the new item budget is nearly exhausted. Already-reviewed items
(repetition_count > 0) are always included up to max_reviews.


## CLI Flags

    --new-max N          override total_new_max for this session (default 9)
    --min-per-domain N   override min_per_domain for this session (default 1)
    --max-reviews N      override max_reviews for this session (default 100)
    --dry-run            print the review queue and exit without reviewing
    --validate           run the internal validation suite and exit

Examples:

    uv run sm2.py --dry-run
    uv run sm2.py --new-max 3
    uv run sm2.py --validate


## Analytics

Reference SQL queries are in docs/analytics.sql. Run them directly against
the database:

    sqlite3 data/sm2.db < docs/analytics.sql

Or open an interactive session:

    sqlite3 data/sm2.db

Queries provided:

    7-day retention rate per domain     target: >= 85% pass rate
    Easiness factor distribution        target: median EF above 2.2
    Daily review load (14-day window)   target: no single day above 50
    Leech detection (lapse_count >= 3)  target: zero leeches
    New item rate per domain (30 days)  target: consistent 3-9 per day

Dates are stored as Python ordinal integers. The queries convert to the
current ordinal using a SQLite CTE:

    cast(julianday('now', 'localtime') - 1721424.5 AS INTEGER)


## Scratch Directory

A scratch/ directory at the project root is gitignored and reserved for
ad-hoc test files. To test a new item format before adding it to exercises/:

    mkdir -p scratch
    # write scratch/test.md with @@@ id: ... items
    # open a Python REPL:
    uv run python
    from sm2 import parse_exercises
    items = parse_exercises("scratch/")
    for item in items:
        print(item)

Scratch files never affect the database or the exercises/ corpus.


## Validation

The internal validation suite runs a full pipeline against an in-memory
database with 15 synthetic items. No filesystem access. No side effects.

    uv run sm2.py --validate

Expected output on a healthy build:

    validation passed: all checks ok

The suite asserts: 15 items inserted, 9 queued after throttle, 9 review log
rows written, correct easiness factor and interval per grade bucket (0/1/2),
correct lapse count increments, correct due dates.
