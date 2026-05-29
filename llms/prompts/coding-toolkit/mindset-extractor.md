# Mindset Extractor
VERSION: 1
UPDATED: 2026-05-27

Task module. Invoke at the end of a significant design or
implementation thread to capture accumulated domain knowledge,
strategies, and contextual judgment as a reusable document.

---

## When to invoke

- End of a design thread that produced a spec or major decisions
- End of an implementation phase with lessons learned
- Anytime a thread developed substantial domain understanding
  that would be lost if the thread were archived
- When you find yourself thinking "I don't want to re-explain
  all of this in the next thread"

## Prompt

```
Extract a thread mindset document from this conversation. Capture
the accumulated domain knowledge, strategies, heuristics, and
contextual judgment that developed over the course of this thread.

Structure as follows:

1. DOMAIN MODEL UNDERSTANDING - what the system/problem is about
   at a level deeper than the spec. The mental model, not the
   data model. Relationships, tensions, and insights that shaped
   the design.

2. DECISION HEURISTICS - rules of thumb that emerged for making
   choices in this domain. Format: "name" followed by explanation
   and when to apply. These should be transferable to future
   decisions in the same project.

3. ARCHITECTURE PATTERNS - structural choices that are locked in
   and should not be revisited without strong reason. For each:
   what it is, why it was chosen, what it prevents.

4. CODING CHOICES AND REASONS - implementation-level decisions
   with their rationale. Not just "what" but "why this and not
   that."

5. RISKS AND FAILURE MODES - identified threats to the project's
   success. For each: what the risk is, how it was mitigated (or
   left unmitigated), and what to watch for.

6. STRATEGIES THAT WORKED - interaction patterns, analysis
   approaches, or design methods that produced good results in
   this thread. Worth reusing in similar future threads.

Keep it under 100 lines. Favor density over completeness - capture
the high-signal insights, not a summary of everything discussed.
Title the file: "thread_mindset_[project].md"
```

## Compact form

```
Extract thread mindset: domain understanding, decision heuristics,
locked-in patterns, coding rationale, risks, and strategies that
worked. Under 100 lines. High signal only.
```

## Conventions

- The mindset document is project-specific, not general wisdom
- It should contain things a new LLM thread couldn't infer from
  the spec alone - the judgment layer above the specification
- Update it at the end of each subsequent significant thread on
  the same project (bump version, add/revise sections)
- If a heuristic or pattern turns out to be universal (appears
  in 3+ project mindsets), migrate it to developer_profile.md
  or coding_style.md
