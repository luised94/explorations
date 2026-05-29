
# Thread Meta-Reflector
VERSION: 1
UPDATED: 2026-05-27

Meta-prompt. Reviews the current thread and recommends refinements
to source documents, prompts, instructions, and thinking patterns.
Surfaces process improvements from lived experience.

---

## When to use

- End of a thread where you corrected the LLM multiple times
- After noticing a recurring friction in how threads go
- Periodic review of prompt library health (monthly or quarterly)
- After a thread that went particularly well - capture why

## Prompt (end-of-thread reflection)

```
Reflect on this thread as a process observer. Review how the
conversation went - what worked, what didn't, where friction
occurred, where I had to correct or redirect you.

Produce recommendations in these categories:

1. PROMPT UPDATES - specific changes to existing prompt files
   that would prevent issues seen in this thread. For each:
   which file, what to add/change/remove, and why.

2. NEW PROMPTS - thinking patterns, tasks, or conventions that
   emerged in this thread and should be captured as reusable
   prompt files. For each: what it does, when to use it, draft
   the compact form.

3. DEVELOPER PROFILE UPDATES - new tendencies, preferences, or
   corrections observed in how I work or make decisions. For
   each: what to add or revise in developer_profile.md.

4. INTERACTION MODE UPDATES - communication patterns that worked
   or failed. Anti-patterns to add, calibrations to adjust.

5. PROCESS IMPROVEMENTS - changes to workflow_rhythm.md,
   thread lifecycle, or the overall development process.

Be specific. "Improve the design prompt" is not actionable.
"Add to interaction_modes.md under anti-patterns: 'Do not list
more than 3 alternatives without stating which one wins'" is
actionable.

Only recommend changes supported by evidence from this thread.
Do not suggest hypothetical improvements.
```

## Prompt (periodic library review)

Attach: all prompt files from prompts/

```
Review my prompt library for consistency, gaps, contradictions,
and staleness. The files are attached.

For each issue found:
- Which file(s) are affected
- What the issue is (contradiction, gap, redundancy, drift)
- Specific recommended fix

Also identify:
- Prompts that reference conventions not captured elsewhere
- Conventions captured in multiple places (redundancy risk)
- Missing prompts implied by the existing library but not
  yet written
- Prompts that may have drifted from actual practice based on
  their version/update dates

Prioritize by impact on daily workflow.
```

## Compact form (end of thread)

```
Thread meta-reflection: what worked, what didn't, what prompts
or documents should be updated based on this thread's evidence.
Specific recommendations only.
```

## Conventions

- Every recommendation must cite a specific moment or pattern
  from the thread (or a specific inconsistency in the files
  for library review)
- Recommendations are changes to existing files, not new
  philosophy. Save new philosophy for developer_profile.md
  updates.
- The reflector does not execute changes - it recommends them.
  The user reviews and applies.
- If the reflector finds that the prompt library is working well
  and no changes are needed, it should say so. No changes for
  the sake of appearing useful.
