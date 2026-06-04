# tsk - Registry Manifest
VERSION: 1
UPDATED: 2026-06-04
PURPOSE: Maps every data structure that encodes tsk's data model,
control flow, transformation rules, or presentation logic. Consult
before every commit to identify co-update targets.

---

## Data Model

### ENTITY_CONFIG
  Category: data_model
  Controls: per-entity-type behavior in handle_add - prefix, target
    file, type field value, defaults, validations, required fields,
    usage string
  Location: tasks.py, CREATION section
  Update when: adding an entity type, changing an entity's defaults
    or validations, changing which fields are required, changing
    which file an entity writes to
  Co-update: ENTITY_TYPES, TYPE_PREFIX_MAP, FIELD_ORDER (if new
    fields), CREATION_FLAGS (if new flags), FLAG_TYPE_ANNOTATIONS
    (if type-specific)
  Format: dict[str, dict] where key = entity type name ("task",
    "goal", "habit", "event"), value = {prefix: str, file: Path,
    type_field: str|None, defaults: dict, validations: dict,
    required: set, usage: str}

### ENTITY_TYPES
  Category: data_model
  Controls: set of recognized entity type names for positional
    subcommand parsing in handle_add
  Location: tasks.py, CREATION section
  Update when: adding or removing an entity type
  Co-update: ENTITY_CONFIG (always), TYPE_PREFIX_MAP
  Format: set[str] - {"task", "goal", "habit", "event"}

### FIELD_ORDER
  Category: data_model
  Controls: field serialization order in format_record - determines
    the top-to-bottom layout of written records
  Location: tasks.py, WRITER section
  Update when: adding a new record field that should appear in a
    specific position (unknown fields append alphabetically)
  Co-update: none required, but FIELD_HELP should document new fields
  Format: list[str] - field names in display order, multi-line fields
    (notes, prep) last

### DATA_FILES
  Category: data_model
  Controls: which files ensure_data_files creates on init
  Location: tasks.py, CONFIGURATION section
  Update when: adding a new data file
  Co-update: ensure_data_files (implicitly), relevant handlers
  Format: list[Path]

### TYPE_PREFIX_MAP
  Category: data_model
  Controls: --type filter in handle_list - maps entity type names
    to ID prefixes for prefix-based filtering
  Location: tasks.py, before handle_list
  Update when: adding an entity type
  Co-update: ENTITY_TYPES, ENTITY_CONFIG
  Format: dict[str, str] - {"task": "T", "goal": "G", ...}

---

## Transformation

### CREATION_FLAGS
  Category: transformation
  Controls: which CLI flags handle_add accepts and how they map
    to record field names
  Location: tasks.py, CREATION section
  Update when: adding a new creation flag
  Co-update: FIELD_HELP (description for new field),
    FLAG_TYPE_ANNOTATIONS (if type-specific), ENTITY_CONFIG
    validations (if validated)
  Format: dict[str, str] - {"--flag": "field_name", "-x": "field_name"}

### LIST_FLAGS
  Category: transformation
  Controls: which CLI flags handle_list accepts
  Location: tasks.py, before handle_list
  Update when: adding a new list filter or sort option
  Co-update: FIELD_HELP (description), COMMAND_FLAG_SETS (already
    references LIST_FLAGS by identity)
  Format: dict[str, str] - same shape as CREATION_FLAGS

### VALIDATION_ERRORS
  Category: transformation
  Controls: error messages printed when a flag value fails validation
  Location: tasks.py, CREATION section
  Update when: adding a validated field to ENTITY_CONFIG
  Co-update: ENTITY_CONFIG validations (must have matching entry)
  Format: dict[str, str] - {field_name: error_message}

### SORT_FIELDS
  Category: transformation
  Controls: accepted values for --sort flag in handle_list
  Location: tasks.py, before handle_list
  Update when: adding a new sort mode
  Co-update: _sort_key_for_record (must handle new mode),
    FIELD_HELP "sort" entry (update description)
  Format: set[str] - {"date", "project", "priority"}

---

## Flow

### COMMANDS
  Category: flow
  Controls: top-level dispatch table - maps command names to handler
    functions
  Location: tasks.py, DISPATCH section
  Update when: adding or removing a command
  Co-update: COMMAND_USAGE (always), handle_help descriptions dict
    (always), print_command_help descriptions dict (if implemented
    command)
  Format: dict[str, Callable] - {"name": handler_function}
  Note: not-implemented commands use lambda wrappers to
    handle_not_implemented

### DEFAULT_COMMAND
  Category: flow
  Controls: which command runs when tsk is invoked with no arguments
  Location: tasks.py, DISPATCH section
  Update when: changing the default behavior of bare `tsk`
  Co-update: none
  Format: str - currently "today"

### BOOTSTRAP_COMMANDS
  Category: flow
  Controls: which commands skip the data-directory gate (allowed to
    run before tsk init)
  Location: tasks.py, PREFLIGHT CHECKS section
  Update when: adding a command that must work without DATA_DIR
  Co-update: none
  Format: tuple[str] - currently ("init",)

---

## Presentation

### COMMAND_USAGE
  Category: presentation
  Controls: usage strings shown by tsk help <command> and error paths
  Location: tasks.py, HELP REGISTRIES section
  Update when: adding a command or changing a command's syntax
  Co-update: COMMANDS (must have matching entry)
  Format: dict[str, str] - {"command": "tsk command <args> [flags]"}

### COMMAND_FLAG_SETS
  Category: presentation
  Controls: which flag dict tsk help <command> reads to display flags
  Location: tasks.py, HELP REGISTRIES section
  Update when: adding a command with flags
  Co-update: COMMAND_USAGE (must have matching entry)
  Format: dict[str, dict] - {"command": flag_dict_reference}
  Note: values are references to flag dicts (CREATION_FLAGS,
    LIST_FLAGS), not copies. Single source of truth for flag names.

### FIELD_HELP
  Category: presentation
  Controls: human-readable descriptions for flags in help output
  Location: tasks.py, HELP REGISTRIES section
  Update when: adding a new flag to any flag dict
  Co-update: the flag dict itself (CREATION_FLAGS or LIST_FLAGS)
  Format: dict[str, str] - {field_name: description_string}

### FLAG_TYPE_ANNOTATIONS
  Category: presentation
  Controls: "(event only)", "(goal)" annotations appended to flag
    descriptions in help output
  Location: tasks.py, before print_command_help
  Update when: adding a flag that applies primarily to one or two
    entity types
  Co-update: FIELD_HELP (must have base description for same field)
  Format: dict[str, str] - {field_name: "type annotation"}

---

## Co-update Graph (quick reference)

Reading: "A -> B" means "changing A requires checking B."

```
ENTITY_CONFIG -> ENTITY_TYPES, TYPE_PREFIX_MAP, CREATION_FLAGS,
                 FLAG_TYPE_ANNOTATIONS, FIELD_ORDER, VALIDATION_ERRORS
ENTITY_TYPES -> ENTITY_CONFIG, TYPE_PREFIX_MAP
CREATION_FLAGS -> FIELD_HELP, FLAG_TYPE_ANNOTATIONS, ENTITY_CONFIG
LIST_FLAGS -> FIELD_HELP, COMMAND_FLAG_SETS
COMMANDS -> COMMAND_USAGE, handle_help descriptions,
            print_command_help descriptions
COMMAND_USAGE -> COMMANDS
SORT_FIELDS -> _sort_key_for_record, FIELD_HELP
VALIDATION_ERRORS -> ENTITY_CONFIG validations
```

Most common co-update sets (by trigger):

| Trigger | Registries to update |
|---------|---------------------|
| Add entity type | ENTITY_TYPES, ENTITY_CONFIG, TYPE_PREFIX_MAP, COMMANDS (if new top-level cmd) |
| Add creation flag | CREATION_FLAGS, FIELD_HELP, FLAG_TYPE_ANNOTATIONS (if type-specific), ENTITY_CONFIG validations (if validated), VALIDATION_ERRORS (if validated) |
| Add list flag | LIST_FLAGS, FIELD_HELP, SORT_FIELDS (if sort mode), _sort_key_for_record (if sort mode) |
| Add command | COMMANDS, COMMAND_USAGE, handle_help descriptions, print_command_help descriptions, COMMAND_FLAG_SETS (if has flags) |
| Add record field | FIELD_ORDER (for position), FIELD_HELP (for description) |
