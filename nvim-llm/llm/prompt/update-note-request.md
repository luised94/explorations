UPDATE NOTE REQUEST

A development branch is complete. Produce an update note summarizing
what changed, for reinjection into an earlier conversation turn.
Save it to llm/updates/<date>-<short-name>.md in the project repository.

Required sections:
  Title: "Update: <what was done>"
  Date, Branch/Phase, Prior State (one sentence)

  WHAT CHANGED:
    Bullet list. Each bullet: one concrete change. Name the file, the
    function, the behavior. No vague summaries.

  WHY:
    One to three sentences. What problem or constraint motivated this
    branch. Reference the user's stated requirements by name if applicable.

  CURRENT PROJECT STATE:
    Repository location, file listing (ls -R output or equivalent),
    what works, what is known-broken, what is deferred.

  CONSTRAINTS IN FORCE:
    List all active constraints (ASCII only, coding guidelines, format
    decisions, etc.) as a bullet list. Each constraint: one sentence.

  NEXT STEP:
    One sentence. The single next action, named concretely.

  DO NOT:
    - Re-output full file contents. Reference filenames only.
    - Summarize the conversation narratively. State facts.
    - Include code unless a specific snippet is needed to document a
      format decision (e.g., "block headers use this pattern: ---").

Constraints on the note itself:
  - ASCII only.
  - Self-contained: readable without the surrounding conversation.
  - Under 80 lines.
