CODING GUIDELINES (paste into any prompt that will produce code)

Data-oriented. These are heuristics, not laws, but default to following them:

Structure:
  - Imperative core, functional shell. The top-level dispatch is a flat
    case/if sequence. Transformations are pure functions. Side effects
    (file I/O, API calls, mutations) are isolated to clearly marked
    edge functions.
  - No premature abstraction. No helper functions that wrap one line.
    No indirection layers added "for flexibility." No nesting deeper
    than three levels.
  - Read/write/mutation boundaries are explicit. A function either
    computes a value OR performs a side effect. Never both. Comment
    the boundary: "-- Pure transformations" and "-- Side effects".

Naming:
  - Full descriptive names with domain information and units where
    applicable. "conversation_directory" not "dir". "block_identifier"
    not "id". "timestamp_hours_minutes" not "ts" if ambiguity exists.
  - No abbreviations unless the abbreviated form functions as a noun
    in the domain (e.g., "id" is acceptable as a noun; "cfg" is not).
  - Extract magic numbers and literal expressions into named variables
    at the top of the scope. The name assigns semantic value.
    "BLOCK_IDENTIFIER_WIDTH=3" not "printf %03d".

Interface:
  - Centralize argument processing. Assign names to positional
    arguments immediately. The case/dispatch block should read as
    named variables, not $1 $2 $3.
  - Include a help message. Print it on "help", "--help", "-h",
    and unknown commands.

Quality:
  - Readability, maintainability, consistency, and professionalism
    are not deferred. Write the code once, cleanly. Do not prototype
    sloppily and "clean up later."
  - ASCII only in all code and locally saved content.
