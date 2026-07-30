METRICS AND EXPERIMENT DESIGN (paste into prompts that involve testing or iteration)

Quantitative:
  - Introduce lightweight metrics hooks for any operation that has a
    cost (API calls, file operations, time). Log to a plain-text file.
    One line per event. Fields: timestamp, operation, relevant measure.
  - Provide the shell commands to query the log (totals, per-category
    breakdowns, rates). Do not build a dashboard. grep and awk are
    the dashboard.

Qualitative:
  - Design explicit test sequences for format and workflow changes.
    Each test: a numbered list of actions the user performs, with
    OBSERVE notes stating what to watch for.
  - After each test, provide a structured debrief: numbered questions,
    one per line, each answerable in one sentence. The user pastes
    answers back.
  - Tests should isolate one variable. Do not test format changes and
    navigation changes in the same session.

Distinction:
  - Mechanics tests: does it store, retrieve, render, navigate correctly?
    Use free/cheap models. Quality of content is irrelevant.
  - Semantics tests: does the granularity, structure, and representation
    match the user's thinking? Use capable models. Content quality matters.
  - State which kind of test is being designed. Do not conflate them.
