# tsk - Session Notes: Phase 1 Implementation
DATE: 2026-06-04
SOURCE: Phase-1 implementation thread (commits 17f, 18, 19, 20, 21, 23, 22)
PURPOSE: Context recovery document for future implementation threads.

---

## 1. Coding Guidelines: Stated, Observed, Conflicts

### Stated rules that held without friction
- **Function extraction rule (2+ callers or dispatch target).** Applied cleanly. print_command_help extracted in commit 21 with exactly 2 callers (handle_help, handle_add error path). _sort_key_for_record and _format_list_line in commit 19 were the only marginal cases.
- **Domain vocabulary in variable names.** No generic key/value/item/data names appeared. record_summary, type_prefix_filter, archived_event_ids, etc.
- **Intermediate variables over direct returns.** Followed throughout. No bare expressions inside function calls.
- **No classes, no OOP.** ENTITY_CONFIG is a plain dict-of-dicts, not a class hierarchy.
- **Atomic writes via temp file + rename.** All write_file calls go through the existing atomic path. New write sites in commit 20 (--cleanup-events) use the same pattern.
- **Standard ASCII only.** No unicode in code, comments, or output.

### Stated rules that needed judgment calls
- **Higher-order function exception for genuine comparison sorting.** Used in commits 19 and 22 for sorted() with runtime-determined keys. _sort_key_for_record was extracted as a named function rather than inline lambda because the key logic is a 3-branch conditional - too unwieldy for a lambda. Marked with [ASSUME] in the commit. The style doc's exception clause ("genuine comparison-based sorting on data where the order is not already known") covers this, but the extraction of the key function into a named def (single caller) is a style-rule tension. Resolution: prefixed with _ to signal internal, documented the justification.
- **_format_list_line extraction (commit 19).** Single caller in a strict sense, but called inside a nested loop (group x record). The 15-line formatting block would make the loop body hard to read. Marked with [ASSUME]. If this pattern recurs, establish a "readability within nested iteration" exception to the extraction rule.

### Observed patterns not in the style doc
- **Config-driven dispatch within a handler.** ENTITY_CONFIG in commit 18 is a pattern not covered by the style doc: a data structure that drives control flow within a single handler. It's not a class, not a higher-order function, but it is an abstraction layer. It worked well here because the four entity types share 80% of their logic. The pattern: a dict mapping type names to dicts of {prefix, file, defaults, validations, required, usage}. The handler reads the config and branches only where types genuinely differ (time parsing for events, label vs type field).
- **Manual flag check before argument parsing.** Commit 20's `if arguments[0] == "--cleanup-events"` is a hand-rolled subcommand pattern. It works because there's exactly one flag-like argument that changes the handler's entire behavior. If more flag-like subcommands appear on done, this pattern won't scale - would need a secondary dispatch or a flag-aware branch. For now, one is fine.
- **Comment-at-decision-point pattern.** The review document specified 5 locations requiring code comments. All were placed. The pattern: when a design decision creates behavior that would surprise a reader of the code alone (e.g., "all flags accepted" when you'd expect per-type rejection), a comment at the decision point explains the rationale. This is distinct from docstrings (which describe what a function does) and inline comments (which explain tricky code). These are *policy comments* - they explain why the code doesn't do the obvious thing.

### Conflicts identified
- **Descriptions dict duplicated.** handle_help and print_command_help both contain a descriptions dict. The overview dict (handle_help) includes deferred commands; the per-command dict (print_command_help) only includes implemented commands. This is a latent maintenance burden - adding a command requires updating both. Candidate for a module-level constant in phase 2, but currently only 2 sites so inline is defensible.
- **Event display logic duplicated.** handle_today, handle_week, and _format_list_line all format event records slightly differently. today and week share the time + summary + type + location pattern; list uses a one-line format. Not yet worth extracting (3 sites with meaningful differences), but watch for a fourth.

---

## 2. Workflow Patterns

### Commit sequencing that worked
**Bugfix first, then refactor.** 17f (ID reuse fix) landed in all four handlers before 18 (consolidation) collapsed them to one. This gave a working checkpoint: if consolidation introduced bugs, the fix was already verified independently. The "fix then refactor" order also made the consolidation diff cleaner - the fix was already present, so 18 only had to collapse call sites, not also fix the bug.

**Exemplar before dependents.** Commit 18 (creation consolidation) established ENTITY_CONFIG and the unified handle_add. Commits 19-23 could reference its patterns without re-explaining them. The review document's exemplar strategy (mutation command as reference) carried forward from phase 0.

**Stretch goal last.** Commit 22 (week view) depended on 19 and 20 but had no dependents. Placing it last meant all required work was done before the optional work started. If the thread had run out of context, nothing critical would be missing.

### Commit block structure that worked
**Stating invariants before implementation.** The revised workflow rhythm (invariants before code) meant the implementation was written against explicit constraints. This prevented drift: when writing handle_add in commit 18, the invariant "tsk add event without --date exits with error" caught a path that might otherwise have been forgotten.

**Verification commands with expected output.** Concrete shell commands with expected output made review fast. The developer can run each command and compare. Edge cases (summary starting with entity type name, whitespace-only summary, old commands removed) were caught by verification, not by reading code.

### Commit sizing
- **17f (haiku, ~12 lines changed across 4 sites):** Right size. Mechanical substitution, no judgment.
- **18 (sonnet, ~150 lines new code):** At the upper bound of sonnet. The ENTITY_CONFIG design, flag unification, dispatch cleanup, and compound logging were all interrelated - splitting would have created intermediate broken states. Correct to keep as one commit.
- **19 (sonnet, ~100 lines new code):** Right size. Grouped output, new sort logic, prefix-based type filter - all part of one coherent change.
- **20 (haiku, ~40 lines new code):** Right size. Single new code path at the top of an existing handler.
- **21 (haiku, ~50 lines new code):** Right size. Extract + two call sites + annotation dict.
- **23 (haiku, ~2 lines changed):** Minimal. Guard already existed; this was verification + comment cleanup. Could have been folded into 18 but the spec update justifies a separate commit.
- **22 (sonnet, ~60 lines new code):** Right size. Self-contained view command.

---

## 3. Interaction Patterns

### Instructions that produced good output
- **"Continue with the next commit"** - unambiguous, no context lost. The thread maintained state across commits without re-prompting.
- **Pasting the full codebase + spec + workflow docs in the opening prompt.** Gave enough context for all 7 commits without mid-thread document requests.
- **Review document with final decisions.** Sections 5-6 of the review document eliminated design deliberation during implementation. Every decision was pre-made; the LLM's job was execution, not design. This is the ideal split: design in a refinement thread, execute in an implementation thread.

### Patterns that would need adjustment for future threads
- **Edge case discovery during implementation.** The `tsk add "goal setting workshop"` edge case (commit 18) was noticed during implementation, not during design. The design doc mentioned it abstractly ("--type flag works as fallback") but didn't spell out the shell quoting interaction. Future design threads should include a "shell interaction" section for commands with positional subcommands.
- **Verification commands assume specific record state.** The verification sections reference records created in earlier verification steps. In practice, the developer's data files have real data from usage. Verification commands should use unique, obviously-test summaries (e.g., "VERIFY-18-task") to avoid collision with real records, or should note "output will vary based on existing data."
- **Commit 18 was dense.** A single "continue" produced ~200 lines of implementation instructions. For a commit this size, the developer might prefer two exchanges: one for the design/structure review, one for the full implementation. Consider asking "ready for the full implementation?" after the design summary for sonnet-level commits.

---

## 4. Project-Specific Decisions

### Decided in this session

| Decision | Chosen | Rejected | Commit | Why |
|----------|--------|----------|--------|-----|
| Positional subcommand for entity type | First positional arg checked against {task,goal,habit,event} | --type flag only | 18 | Natural CLI syntax; matches user's mental model from friction log |
| Old commands removed entirely | No aliases, no deprecation | Deprecation warnings, aliases | 18 | Clean break; solo user, no backward compat needed |
| --label/-y for event subtype | Renamed from --type/-y | Keep --type/-y with disambiguation logic | 18 | Avoids collision with entity type concept; maps to type field in record |
| All flags accepted for all types | Field-agnostic | Per-type flag rejection | 18 | Consistent with parser philosophy; --date required is sole exception |
| --type list filter by ID prefix | Prefix match (T/G/H/E) | Type field value match | 19 | Aligns with "entity type = ID prefix" convention |
| Grouped list output | GOALS, TASKS, HABITS, EVENTS sections | Flat sorted list | 19 | Better orientation; mirrors today's section structure |
| Batch event archival only | --cleanup-events flag on done | Per-ID event done | 20 | Events are batch lifecycle; individual completion is semantic mismatch |
| Full help on error | print_command_help with annotations | Bare usage line | 21 | Eliminates helpcommandhelp round-trip from usage data |
| Week shows 7 days forward | today+0 through today+6 | Configurable range, --offset flag | 22 | Simple; no usage data yet to justify complexity |
| Empty days show placeholder | `"  --"` under day header | Skip empty days | 22 | Preserves calendar rhythm; user sees the gap |

### Decisions from phase 0 that were validated by usage
- **list and today as separate commands.** Usage data confirmed: list 18 vs today 4. Different mental models, both valuable.
- **Per-command help.** 6 of 18 help calls targeted specific commands. The pattern works.
- **Atomic writes.** No data corruption incidents despite USB sync friction.

### Decisions from phase 0 that were challenged by usage
- **Event lifecycle ("events pass, archiving deferred").** Broke within 5 days of real use. Fixed in this phase.
- **generate_id scope (single file).** ID reuse bug surfaced on day 3. Fixed in 17f.

---

## 5. Issues and Frictions

### During implementation
- **ENTITY_CONFIG defaults vs flag overrides.** Habit frequency has a default ("daily") in ENTITY_CONFIG but can be overridden by --frequency flag. The override logic (`if entity_type == "habit" and "frequency" in flags`) is a special case that breaks the otherwise uniform config-driven flow. A cleaner pattern would be: apply defaults first, then let flags overwrite. But the current field-application logic adds flags only when the field isn't already in the record (`if field_name not in new_record`), which means defaults win over flags. The habit frequency override is a patch for this ordering issue. If more defaulted-but-overridable fields appear, refactor to: build record with required fields  apply flag values  apply defaults for missing fields.
- **Compound logging duplicates type detection.** The dispatch-level logging peeks at arguments to build "add:goal" etc., mirroring the entity type detection in handle_add. This is documented with a comment but is a maintenance risk - if entity type detection logic changes in handle_add, the dispatch logging must change too. No better alternative without handler cooperation (which would break the dispatch-level logging pattern).
- **print_command_help descriptions dict.** Duplicated from handle_help. See Conflicts section above.

### Latent issues not yet surfaced
- **Event display logic repetition.** Three sites format events. Not yet a problem but will be when week and today diverge further (e.g., prep fields in tomorrow view).
- **parse_flags doesn't handle --flag=value.** Documented in scope boundaries. Will surface when a user types `--date=2026-06-10` and gets a confusing error.
- **Habit feature entirely untested by real use.** Zero invocations in 70. Streak calculation, frequency filtering, and dashboard section are running on assumptions.

---

## 6. Future Work

### Immediate (before next implementation thread)
- **Apply retire fix from other branch.** Retire was broken (accessing non-existent field, didn't work on calendar events). Merge that fix.
- **Verify all 7 commits against actual codebase.** This thread produced commit blocks; they need to be applied and tested against the real data files.
- **Run end-of-phase analysis on phase 1.** Same six checks as phase 0 end-of-phase.

### Medium-term (phase 2 candidates)
- **Refactor default/flag ordering in handle_add.** Current pattern: defaults applied, then flags skip existing fields, with a special case for habit frequency. Better: required fields  flags  defaults for missing. Small refactor, high clarity gain.
- **Module-level descriptions constant.** Eliminate the duplicated descriptions dicts in handle_help and print_command_help.
- **Event formatting helper.** If a fourth site appears (tomorrow view), extract the time + summary + type + location formatting.
- **--flag=value syntax in parse_flags.** Low priority but will prevent user confusion.
- **Habit real-use validation.** Use habits for a week, then review streak calculation and dashboard display.
- **nvim integration (spec phase 2, commit 24).** Keybindings for quick capture.

### Structural observations
- **The config-driven handler pattern scales.** ENTITY_CONFIG could be extended with display formatters, archive rules, and lifecycle definitions. Don't do this preemptively - wait for the second use case that would benefit.
- **The positional subcommand pattern is fragile at the shell boundary.** `tsk add "goal setting workshop"` creates a goal, not a task. This is documented but will surprise users. The `tsk add task "goal setting workshop"` workaround is adequate but not discoverable. Consider: if summary's first word matches an entity type AND the user didn't quote the entire summary, print a confirmation: "creating goal: setting workshop. Did you mean task? Use: tsk add task \"goal setting workshop\"". Deferred - no complaints yet.
- **Usage logging is the most valuable diagnostic tool.** Every design decision in this phase traced back to the usage log. Compound logging (add:goal) will make phase 2 analysis even better. Consider adding a `tsk stats` command that reads usage_log.txt and prints frequency distributions.

---

## 7. Veteran Notes

### What went well
- **Pre-made design decisions eliminated deliberation during implementation.** The review document with "all decisions final" was the single biggest quality factor. The LLM produced code, not design exploration. Every commit was focused.
- **Usage data drove every feature.** Not one commit was speculative. list improvements came from list being 26% of commands. Help refinement came from the helpcommandhelp round-trip. Event lifecycle came from the done-on-event failure. This is the right development rhythm: use  friction  targeted fix.
- **The haiku/sonnet classification kept commits right-sized.** No commit felt too large or too small. The "no opus" rule forced decomposition before implementation.

### What to watch for
- **Config-driven abstraction creep.** ENTITY_CONFIG is useful now. Resist the urge to put display logic, archive rules, or lifecycle state machines in it. Each addition makes the config harder to read and the handler harder to follow. The config should hold *data* (prefix, file, defaults), not *behavior* (formatting, validation logic beyond simple lambdas).
- **Verification commands are promises.** Every verification command in a commit block is a promise that the code works this way. If the developer runs them and gets different output, trust is lost. Be conservative: only promise output you're certain of. Use "output will include" rather than exact output when record state varies.
- **The scratchpad protocol in user preferences adds overhead.** For this project, the commit block format serves the same purpose as the scratchpad (constraints before code, explicit assumptions). The two systems are redundant. In implementation threads, the commit block IS the reasoning artifact - no separate scratchpad needed. In design/refinement threads, the scratchpad adds value for exploring trade-offs.

### Blind spots
- **No testing beyond manual verification.** The --verify-parser flag tests the parser round-trip, but no automated tests exist for command behavior. A `tsk --self-test` that creates a temp data dir, runs commands, and checks output would catch regressions. Not urgent for a solo tool, but would increase confidence in refactors.
- **No error recovery guidance.** If a write fails mid-operation (e.g., disk full during done --cleanup-events), the user sees a traceback. The atomic write pattern prevents data loss, but the user doesn't know that. A top-level try/except at dispatch that prints "error: write failed, your data is safe (atomic writes)" would improve the experience.
- **Calendar.txt growth is unbounded until --cleanup-events is run.** There's no reminder or warning when calendar.txt has many past events. A line in today's dashboard ("N past events in calendar - run tsk done --cleanup-events") would prompt the user.
