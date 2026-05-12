CODE STYLE REQUIREMENT: Simple Procedural

Write code in linear, procedural style without functions or abstractions:

**Do:**
- Inline all logic in execution order (top to bottom)
- Repeat code blocks if logic appears multiple times
- Use descriptive names: `user_config_before_update` not `cfg1`
- Add comments to mark sections, not function docstrings

**Don't:**
- Create helper functions (`log_message`, `validate_input`, `process_data`)
- Abstract repetitive code into utilities
- Use DRY principles that reduce immediate readability

Rationale: Code should be immediately understandable without jumping between function definitions. Repetition is acceptable when it improves clarity.
