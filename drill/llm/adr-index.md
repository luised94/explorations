# ADR Index

A navigable index of the Architecture Decision Records in `decisions.md`:
id -> one-line subject -> status. Built for roadmap #20 (the last outstanding
piece of the docstring / status-drift cleanup).

STATUS.md remains the single source of truth for LIVE project status (ADR-048);
this index is a static map into `decisions.md`, not a status dashboard. When an
ADR is added or its disposition changes in `decisions.md`, update the matching
row here.

## Scope note -- what counts as an ADR

The formal `ADR-NNN` numbering was adopted at the T2 (schema/migrations) thread
and runs contiguously from ADR-021 through ADR-054. It is NOT gap-free from one:
there are no formal records numbered below 021. Decisions made before the
convention existed live inside their commit sections (`## C-NNN` blocks) in
`decisions.md`, and a few are referred to retroactively by number (e.g.
"ADR-005", "ADR-007") in later prose. Those two are listed at the end as
retro-references so a reader chasing the citation can find the real home, but
they are not standalone ADR entries.

Statuses use each ADR's own in-body marker (`[DECIDED]`, `[REJECTED]`,
`[DEFERRED]`, `[OPEN]`, `[CLOSED]`, `[RECONSIDER WHEN]`). Where an ADR carries
several markers, the row reflects its overall disposition.

## Index (ADR-021 .. ADR-054)

| ADR | Subject | Status |
|-----|---------|--------|
| ADR-021 | Version mechanism: keep the schema_version table; do not switch to PRAGMA user_version | DECIDED |
| ADR-022 | init_db reconciliation: init_db stays the v1 baseline, the runner layers migrations on top (option B) | DECIDED |
| ADR-023 | Transaction discipline: the runner drives BEGIN/COMMIT/ROLLBACK explicitly (do not "simplify" away) | DECIDED |
| ADR-024 | Which table gets metadata: questions.metadata (not banks); surfaced at reader level, not in the client payload | DECIDED |
| ADR-025 | grading_kind column: deferred to adaptive selection / SM2 (roadmap #7, Phase 4); not added in D1 | DEFERRED |
| ADR-026 | init_db stamps a FIXED baseline (BASELINE_SCHEMA_VERSION = 1), not the moving SCHEMA_VERSION | DECIDED |
| ADR-027 | Operator definition is one record per operator (OPERATOR_DEFINITIONS) | DECIDED |
| ADR-028 | Modulo and exponent operand strategies: per-operator operand generation, not a generic override | DECIDED |
| ADR-029 | Deferred operators and the "easy operator" gate | DECIDED |
| ADR-030 | Full per-operand-range generalization deferred to #2; node stays a plain dict, no dataclass | DEFERRED |
| ADR-031 | Provisional #4 defaults that #2 supersedes (uniform operator sample, exponent handling) | DECIDED (superseded on the rung path) |
| ADR-032 | Bottom-up construction and the composable / leaf-only split | DECIDED |
| ADR-033 | Precedence and associativity represented on the operator record; the renderer reads them | DECIDED |
| ADR-034 | Depth is the knob, as a module constant, and is structural not difficulty (until #2) | DECIDED |
| ADR-035 | Optional global result ceiling, shipped dark (default OFF) as a sanity guard | DECIDED |
| ADR-036 | Bounded retry / fail-loud generation; nondeterministic with no seed | DECIDED |
| ADR-037 | Deferred doors for #2 (convenience-not-principle); disposition tracked as #2 opens each | DEFERRED (doors dispositioned under #2) |
| ADR-038 | Difficulty model shape: scalar rung expanding to a per-operator config (shape C) | DECIDED |
| ADR-039 | Q2xQ3 feasible-region resolution: per-operator range scaling plus a difficulty-scaled ceiling, jointly satisfiable | DECIDED |
| ADR-040 | Storage: responses.difficulty AND responses.leaf_count (mutable label plus non-drifting fact) | DECIDED |
| ADR-041 | The per-difficulty stats breakdown as the real Q5 consumer; grouping via a swappable pure key seam | DECIDED |
| ADR-042 | The generator difficulty seam is four plain-data parameters threaded through one path | DECIDED |
| ADR-043 | Per-rung range overlay is pure and copy-on-write (_apply_rung_ranges) | DECIDED |
| ADR-044 | The result ceiling is enforced locally and proven jointly satisfiable | DECIDED |
| ADR-045 | HTTP validates difficulty inbound, records it trusted-but-typed | DECIDED |
| ADR-046 | The breakdown grouping mechanism is the pure breakdown_by seam with the S11 key as a callable | DECIDED |
| ADR-047 | Difficulty rung UI control (was OPEN/handed off; the selector shipped in C-2U-a..d) | CLOSED |
| ADR-048 | Single-source status in STATUS.md; adopt CODING_CONVENTIONS.md | DECIDED |
| ADR-049 | Frontend tests import modules directly (option b), not via jsdom page execution | DECIDED |
| ADR-050 | Layering guards are data-driven (the module dependency / ownership model) | DECIDED |
| ADR-051 | Ownership guard design (the DOM-node owner model the E10 guard enforces) | DECIDED |
| ADR-052 | Frontend cutover sequencing: the inline script keeps its own copy until the E10 cutover (R1) | DECIDED |
| ADR-053 | Accept the drill<->session bidirectional import cycle (option A), spike-verified | DECIDED |
| ADR-054 | Post-modularization roadmap reassessment (2026-07): rescore and resequence the remaining threads | DECIDED |

## Retro-references (pre-convention decisions cited by number)

These are not standalone ADR entries; the decision lives in the noted commit
section of `decisions.md`.

| Cited as | Real home | Subject |
|----------|-----------|---------|
| ADR-005 | `## C-005` Operator scalar config | Bank question selection / operator scalar config decisions |
| ADR-007 | `## C-006` Operator table + generator | Operand-range and forbidden-identity constraints the generator reads |
