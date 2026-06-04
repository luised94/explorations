## Registry Manifest

A registry manifest is a project-specific document that maps every
data structure in the codebase that encodes the project's data model,
control flow, or configuration. It serves three purposes:

1. **Co-update safety.** Registries that must change together are
   linked. The manifest answers: "I added a flag - what else do I
   need to touch?" before the developer or LLM forgets a site.

2. **Anchoring.** The LLM uses the manifest to locate insertion
   points, verify completeness, and avoid stale references. When
   a commit block says "add entry to CREATION_FLAGS," the manifest
   tells the LLM exactly what that dict controls, where it lives,
   and what co-updates are required.

3. **Compression.** Instead of re-explaining the codebase structure
   in every commit block, the commit references the manifest entry.
   "Update per manifest: COMMANDS, COMMAND_USAGE" replaces paragraphs
   of location/format description.

### Registry categories

| Category | What it captures | Examples |
|----------|-----------------|----------|
| Data model | Entity types, field definitions, ID schemes | ENTITY_CONFIG, FIELD_ORDER, TYPE_PREFIX_MAP |
| Transformation | How input becomes records, how records become output | CREATION_FLAGS, LIST_FLAGS, VALIDATION_ERRORS |
| Flow | Dispatch, command routing, lifecycle transitions | COMMANDS, DEFAULT_COMMAND |
| Presentation | Display formatting, help text, annotations | FIELD_HELP, FLAG_TYPE_ANNOTATIONS, COMMAND_USAGE |

### Manifest format

Each entry in the manifest follows this structure:

```
REGISTRY_NAME
  Category: data_model | transformation | flow | presentation
  Controls: one-line description of what this registry governs
  Location: file and section header where it lives
  Update when: triggering conditions (adding a command, new flag, etc.)
  Co-update: other registries that MUST change in the same commit
  Format: shape of entries (dict, list, set - with key/value types)
```

Co-update links are directional where relevant. "A co-updates B"
means changing A requires checking B. If bidirectional, state both.

### Commit block integration

Every IMPLEMENTATION section must include a **Registry impact** line
before code changes:

```
REGISTRY IMPACT
  COMMANDS: ADD week = handle_week
  COMMAND_USAGE: ADD "week": "tsk week"
  (per manifest co-update: COMMANDS -> COMMAND_USAGE)
  No other registries affected.
```

If the commit touches no registries: "REGISTRY IMPACT: none."

### Hardening checklist addition

Add to the existing hardening checklist:

- [ ] Registry manifest consulted; all co-update targets identified
      and included in this commit
- [ ] No registry entry added without its co-update partners
- [ ] Manifest itself updated if a new registry was introduced

### Maintenance

The manifest lives alongside the spec and is version-controlled.
When a commit introduces a new module-level dict, constant, or
configuration structure that other code reads to determine behavior,
add it to the manifest in the same commit. The trigger: if a future
developer adding a feature would need to know about this structure
to avoid a bug, it belongs in the manifest.
