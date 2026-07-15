# tsk -- next steps: feedback, metrics, experiments, backlog

Written 2026-07-15, after the capture-ergonomics pass (add --edit,
command registry, done-path audit, nvim integration). This is the plan
for the observation window before the next build pass. Nothing here is
committed work; it is what to watch and what to consider.

## Feedback and metrics phase

Run a two-week observation window, then review. Instruments: usage_log.txt
(the tool's own record) plus the user's CLI-based friction notes. Every
section-3 metric from the implementation plan now has a concrete hook.

- Edit-capture adoption. `grep -c 'add:task '` vs `grep -c 'add:task:edit'`
  (and per other entity) gives the --edit ratio. If --edit clears ~50% of
  adds after two weeks, promote editor capture to the default and add a
  --quick/--no-edit skip.
- Field richness. Sample active.txt for fields-per-record on newly created
  records. Did editor capture increase field use, or are records still
  bare summaries? Bare is a fine answer -- it settles whether the flags
  were ever needed.
- Command frequency. `awk '{print $2}' usage_log.txt | sort | uniq -c |
  sort -rn`. Built-but-unused commands are removal candidates, not neglect
  candidates.
- Error rate by command. The log's ok/error column is a free metric not in
  the original plan: which commands fail most, and does the add:*:edit
  error rate fall after the 04b recovery-echo change.
- Gap days. Days with zero invocations distinguish tool friction from
  weeks the user was busy elsewhere.
- edit-to-add ratio. Whether speed-2 capture (edit an existing record) is
  actually in use.

## Experiments to run deliberately in the window

- Capture ~10 real events through --edit and check the template field
  lists. Any blank always deleted -> drop it from CAPTURE_TEMPLATE_FIELDS;
  any field repeatedly added by hand -> add it. One-line changes each.
- One full week of --edit-only capture (entity + summary, no other flags).
  Does the tmux `tsk help add` reference pane stay closed? That is the
  original friction's direct test.
- Trigger a recovery echo under real conditions (terminal scrollback, not
  a clean test) and confirm the typed buffer is actually reconstructable
  from stderr. If it is ever garbled by editor screen-restore, switch the
  echo to a temp file the message points at (see bugs below).
- Year-rollover ID check (cheap, do it once): confirm no long-lived goal
  or habit ID collides with a same-day-next-year prefix. Prefix resolution
  searches only active + calendar, so this is believed harmless; add one
  spec line documenting the behavior either way.

## Suspected bugs and fragilities (ranked by suspicion)

1. Recovery echo vs. editor screen-restore. The 04b echo goes to stderr;
   in some terminals that can interleave with the editor's screen restore
   and scroll away. If observed, make discards write the buffer to a temp
   file and print its path instead.
2. Duplicate-ID-across-files sync edge. Documented in the done-path audit,
   unfixed: if external sync recreates the same ID in both active.txt and
   done.txt, `tsk done` stamps the active copy and the next commit writes
   two copies to done.txt. Precondition is external file corruption; watch
   for recurrence after commit 03.
3. parse_records continuation glue. A line with no `=` and no leading
   whitespace is treated as a continuation of the previous field. A stray
   line typed in the capture editor silently appends to the field above
   rather than erroring -- a plausible future "why is this text in my
   notes field" report.
4. Habit "yesterday grace" vs. midnight reset. Carried open from the
   feedback log; correct in practice or off by a day?
5. $EDITOR must be a bare executable. run_editor_session passes $EDITOR as
   a single argv element; a value with arguments ("code -w") raises
   OSError. A README line or a shlex-style split would fix it.

## Feature backlog (in the order to consider)

First: nothing -- let the window run. Then, driven by data:

- key:value token capture (todo.txt style: p:home due:07-20 +tag) IF the
  help pane stays open despite --edit. The deferred parser is a split on
  the first colon; cheap.
- `stale` IF active.txt accumulates untouched items. Already stubbed; the
  `updated` field makes it a filter plus a sort.
- Recovery echo ported to `tsk edit`, which shares the discard-loses-buffer
  property at lower stakes (the record still exists).
- Batch capture. Currently one record per invocation. Rather than
  multi-summary argv (quoting hell), extend the capture sandwich: an
  --edit buffer that accepts multiple blank-line-separated records
  (parse_records already returns a list). Build only if shell-loop
  workarounds show up repeatedly in friction notes.
- `tsk plan` (send today/week to an editable file, archive it) ONLY if the
  `:r !tsk week` planning loop happens naturally.

## Decomplection pass (its own future plan, post-window)

The user's standing sense of residual indirection has three concrete
targets, worth addressing together once usage data says which commands
survive:

- Write the CLI grammar as a grammar: one page, every token form and what
  consumes it. --edit is the only boolean flag; --cleanup-events hides
  inside `done`; --time is flag-only syntax with no matching record field;
  single-letter mnemonics are arbitrary (-r priority, -y label, -g parent).
  The document makes the irregularities undeniable.
- Audit the Effects shape. effects now optionally carries an "editor" key
  whose dict carries an "apply" FUNCTION -- a function travelling through
  data, the same "cannot tell from the call site" property as globals.
  Principled (mirrors the registry) but it is a second hidden mode in
  main's transform branch.
- render_command_help is documented "Pure" but reads the COMMANDS global;
  either take the registry as a defaulted parameter or drop the claim.
- The keymap positional-tuple loader seam (see nvim-integration-strategy.md)
  is the same class of smell in the nvim config, not tsk itself, but worth
  fixing in the same spirit.

Do this AFTER the window: no point regularizing grammar for commands the
frequency data says to delete.
