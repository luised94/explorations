REPAIR NOTE REQUEST

A bug was identified and fixed. Produce a repair note with the following
structure. Save it to llm/repair/<short-descriptive-name>.md in the
project repository.

Required sections:
  Title: "Repair Note: <what broke>"
  Date, Scope (which files), Constraint (if a new constraint was introduced)

  For each bug:
    BUG N: <short name>
      Symptom:   What the user observed. The visible wrong behavior.
      Cause:     The root cause. Name the exact mechanism, language boundary,
                 or assumption that failed.
      Wrong:     The incorrect code (minimal excerpt).
      Correct:   The fixed code (minimal excerpt).
      Key distinction: If the bug involved a language/context boundary
                 (lua vs vimscript, regex dialects, eval context), include
                 a table showing both sides.

  DIAGNOSTIC COMMANDS:
    List the vim/bash commands that would have caught this faster.
    Include the exact incantations, not descriptions.

  GENERAL RULES:
    Numbered list of rules that prevent this class of bug in the future.
    Each rule: one sentence, imperative voice, names the boundary.

  VERIFICATION:
    A command or test that confirms the fix. Must be runnable.

Constraints on the note itself:
  - ASCII only.
  - No prose padding. Every sentence carries information.
  - Code excerpts are minimal: the wrong line and the right line, not
    the whole function.
  - The note must be understandable by someone reading it cold, without
    the surrounding conversation.
