# tsk -- Decisions & Feedback Log
VERSION: 1
STARTED: 2026-05-29
PURPOSE: Running record of decisions made during implementation, open questions, and things to watch once the tool is in daily use. Append, don't rewrite. Date entries.
Decisions made during implementation (commits 09-17c)
These extend Appendix C of the spec. Fold into the spec's reconciled-decisions table at the next spec revision.
Blueprint applicability (CLI vs batch processor). The standard phase blueprint is written for batch processors. Sections 1-3 (CONFIGURATION, PREFLIGHT, DERIVED) were applied to tasks.py as explicit ASCII-headed sections. Sections 5-6 (main-loop success/failure counters, post-run 1:1 artifact assertion, metrics report) were judged N/A for a dispatcher and are not applied: a CLI runs one handler per invocation, the per-command confirmation print serves as the "summary," and the dispatch-level usage log serves as the "metrics" layer. A comment in tasks.py records this so it doesn't read as an omission.
Atomic writes. write_file now writes a .tmp sibling then Path.replaces the target (atomic on the same filesystem). Rationale: single-writer + USB sync means a yanked drive or killed process mid-write could otherwise truncate active.txt. Highest-value robustness change in the tool; ~3 lines.
Preflight exit codes. 2 = unsupported Python, 3 = data dir missing, 4 = data dir not writable, 127 = (shell) uv/script missing. Command-level validation stays at exit 1. The Python-version gate sits above all defs so it fires before the 3.10+ union annotations are evaluated.
updated refreshed on done/retire. Spec lifecycle text listed only status+completed, but the Appendix B retired-record example shows updated matching completed. Resolved by refreshing updated = today on both done and retire. [resolved from ASSUME]
Habit unrecognized-flag fall-through. --due/--priority/--parent on tsk habit fall through to positional and visibly pollute the summary rather than being rejected. No rejection logic added (no second caller, marginal benefit on a solo tool). [resolved from ASSUME -- accept fall-through]
Per-file prefix-ambiguity check in edit. Spec mentioned "combined matches > 1" across active+calendar, but T/G/H IDs (active) and E IDs (calendar) are prefix-disjoint, so cross-file collision can't occur. edit searches active first, falls to calendar on zero matches, checks ambiguity per file. [resolved from ASSUME]
tsk done on a habit exits 0 on duplicate. Logging the same habit twice in a day is idempotent, not an error, so it exits 0 and the usage log records ok.
uv --no-project. The shell function runs uv run --no-project so that running tsk from inside another repo with a pyproject.toml doesn't make uv adopt that project's environment.
Open questions / things to verify

uv flag semantics across versions. Confirm uv run --no-project isolates as intended on the installed uv version; --script is the fallback if not. (Verify by running tsk help from inside another project dir.)
os.access on the USB mount. W_OK can misreport on some filesystems. Reliable on ext4/exFAT; worth a sanity check on the actual sync target.
Exit-code collisions. Confirm 2/3/4 don't clash with anything a wrapper script or the shell interprets specially.
ID exhaustion. generate_id returns None after 26 records of one type per day; handlers exit with "too many records created today." Almost certainly never hit, but the ceiling is real.

Watch during daily use (feeds end-of-phase / phase-1 priorities)

Stale-task accumulation. The graveyard metric. If active.txt fills with untouched items, tsk stale (deferred) moves up in priority.
Is edit (speed-2 capture) actually used? Edit-to-add ratio from the usage log answers this.
Which commands go unused. Command-frequency distribution from usage_log.txt. Built-but-unused commands are candidates for removal, not just neglect.
done.txt growth. Unbounded by design; when it gets unwieldy, tsk archive (phase 3) is the answer.
Habit streak correctness. Verify the "yesterday grace" (an unlogged-yet-today habit keeps its streak) feels right in practice vs. resetting at midnight.

### Deferred (already catalogued, here for visibility)
Recurrence logic (events), goal-hierarchy view, weekly review workflow, full-text search, tomorrow/prep view, nvim integration, Samsung Notes import, color output, metrics-analysis script, and the Appendix A deferred fields (blocked_by, estimate, buffer, alert, etc.). The field-agnostic parser already accepts the deferred fields if added by hand.

### On the tags guard - honest answer: no, and it's deliberate
We don't guard against --tags #health #home, and I'd argue we shouldn't try to. The obvious guard would be "warn if a leftover positional token starts with #" - but # is legitimate in a summary (tsk add "fix login bug #42"), so that heuristic would false-positive on real summaries and create noise. There's no reliable way to distinguish "stray tag the user forgot to quote" from "a # that belongs in the summary." So the correct fix is documentation (now in the README) plus the per-command help, not a fragile runtime check. This is the same class as the habit unrecognized-flag fall-through: visible, self-correcting, not silently destructive. If you ever do want a guard, a --tags-specific post-parse check is the narrowest version, but I'd leave it off.

### Symlinker - plan and the git reality
The git interaction is the deciding factor, and it argues against symlinks for your setup. Here's the mechanics: git stores a symlink as the link text (the target path), not the target's contents. So if you symlink an external file into docs/{id}/, the synced repo carries a pointer to an absolute path that won't exist on another machine or after the USB moves - you get dangling links. Symlinks only survive sync if the target lives inside the synced tree and the path is identical everywhere, which defeats the point of linking to a file elsewhere.

So the robust pattern for a USB-synced, single-writer-multi-machine repo is the repo holds the real file - bring the document in, don't point out. Two shapes:

The simplest is tsk link <id> <path> that copies the file into docs/{id}/ (creating the dir), with an optional --move to relocate the original into the repo. Content is then tracked, diffable, and portable - everything symlinks aren't. If you still want a convenience pointer at the original location, that's a local, uncommitted symlink you recreate per machine - the repo stays the source of truth, the pointer is ephemeral.

On your file-vs-directory question: the spec's convention is docs/{id}/ (a directory per task), which handles the common case of multiple documents per task. A single linked file just lands as docs/{id}/filename.ext inside that directory - you don't need to choose; the directory convention already accommodates one file or many. I'd keep the directory model and not special-case single files.

This slots naturally into phase 2 next to the already-deferred tsk docs <id> command (the spec lists it there). tsk link populates docs/{id}/; tsk docs <id> lists/opens it. I'd plan them as a pair. Nothing to build now - just flag in the feedback log that the chosen mechanism is copy/move-into-repo, symlinks rejected for sync-portability, so the decision is captured before phase 2 starts.

### Help patch
Quick read on the design question first: don't add --help to every command. That means a --help check duplicated in every handler, and since parse_flags would treat --help as an unknown token and sweep it into the positional summary, each handler would need explicit pre-handling - exactly the per-site boilerplate the style rules push against. The clean fit for this dispatcher is tsk help <command>: one place (handle_help), no handler changes, naturally discoverable.
The efficiency win is that the flag names come straight from the existing *_FLAGS dicts - no second copy of "which flags exist," so they can't drift. The only new text is a small FIELD_HELP map of human descriptions and a usage line per command.

### On the data-dir bootstrap
Your read is right - the message conflates two cases, and because tsk.sh does : "${TASKS_LOCAL_DIR:=...}"; export, the variable is always set by the time Python runs (via the wrapper). So "set TASKS_LOCAL_DIR" is almost always the wrong hint. The unset case only happens if someone runs tasks.py directly.
Let me take your three cases:
Case 3 (dir exists, no files) is already handled - the DERIVED touch loop creates any missing data files on every run, so a freshly emptied directory self-heals. Not an error path.
Case 1 vs 2 need distinguishing in the message, which means tracking whether DATA_DIR came from the env var or the default.
Should the script auto-create the directory? My recommendation: no, not on normal runs - add an explicit tsk init command instead. The reasoning is specific to your USB workflow: if the drive isn't mounted, the mount point's parent often still exists, so an auto-mkdir would silently create a local directory shadowing the real synced one, and you'd start writing tasks to the wrong place with no warning - the data-divergence failure that's worst in a sync setup. A typo'd TASKS_LOCAL_DIR has the same hazard. Auto-create trades a one-time setup step for a silent-corruption risk; bad trade for a sync-based tool.
tsk init gives you deliberate, idempotent creation (dir + files + docs), prints the path it created so you can eye-check it's the mount and not a local shadow, and keeps normal runs fail-fast with an accurate message. I'd make it a command, not a --flag, to match the dispatch style (flags here are value-carrying via parse_flags; a bare bootstrap action reads better as tsk init).
Rejected alternatives: auto-create on every run (the shadow-dir hazard above); manual-only with no helper (needless friction when init is three lines). init is the middle path that stays safe.

### 2026-07-14: done-path write guarantee (field report 2026-06-01, closed)
Field report: a task marked done remained in active.txt. Audited
transform_done and commit(): every success path on the task/goal branch
sets status=done and returns the store; commit() repartitions every
record by partition_file() on every write, so the tool cannot itself
leave a done-stamped record in active.txt. Excluded code cause;
attributed to pre-fix USB sync rewriting active.txt between commits.
Note the persistence mechanism: read-only commands (today, list, week)
return store=None and never commit, so a sync-created inconsistency
survives until the next writing command runs and self-heals it.
Related edge, observed not fixed: if sync duplicates the same ID into
both active.txt and done.txt, tsk done stamps the active copy and the
next commit writes two copies to done.txt. Requires external file
corruption as a precondition; no code change. A verify_store round-trip
case (transform_done -> commit -> load_store against a temp dir) now
pins the guarantee: absent from active, present exactly once in done
with status/completed/updated stamped.

### 2026-07-15: add --edit field reports (day one) and carried observations
Field session surfaced four items minutes after the feature landed.
Fixed in the follow-up commit: (1) required fields (event date) blocked
--edit at the shell, contradicting the feature's premise; now deferred
to a blank template line and enforced by apply_add_capture after
editing. (2) A validation failure after editing discarded the whole
typed buffer -- the most expensive failure a capture tool can have;
discards now echo the edited text to stderr under "your text, for
recovery:", and the time error names the field and offending value
(time_start/time_end each take a single HH:MM, not a range).
Open question, revisit with usage data: should summary also be
deferrable under --edit (tsk add task --edit -> blank summary line)?
Arguments both ways; if the log shows --edit becoming the default
capture mode, defer it for consistency with date.
Related pre-existing property, observed not fixed: tsk edit has the
same discard-loses-buffer behavior; lower stakes (the record still
exists) but the same recovery echo would fit there.
Carried code observations for a future pass: render_command_help is
documented Pure but reads the COMMANDS global -- either take the
registry as a defaulted parameter or drop the claim; run_editor_session
requires $EDITOR to be a bare executable (no arguments) -- a command
string like "code -w" raises OSError; worth a README line or shlex
split someday.

### 2026-07-15: nvim docs first use surfaced the function-vs-argv seam
The bare `:!tsk ...` examples from the first nvim docs draft failed with
exit 127 in real use: tsk is a bash function sourced from interactive
shell config, and nvim's `:!` runs a non-interactive shell that never
sources it. Notably this is the tool's central design seam biting
exactly where function and executable diverge -- and the fix was to
call the argv interface directly (uv run --no-project tasks.py ...),
which just worked. Evidence FOR the decomplected design, not against:
because the tool is argv in / files + stdout out, an integration that
cannot see the shell function reaches the same behavior with zero extra
machinery. Resolved by rewriting the README into three tiers (terminal
split / direct-script :! / the tsk.lua module) and adding
integrations/tsk.lua. The shell and nvim entry points now live together
under integrations/, which names them for what they are: ways in from
other environments, not core artifacts.
