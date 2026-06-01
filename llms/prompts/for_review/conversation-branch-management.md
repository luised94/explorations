# Conversation Branch Management
# Analogical heuristic: borrows git's vocabulary and operations to
# organize reasoning about conversation synthesis. It does not
# implement git formally. There are no real diffs, no deterministic
# merges, no preserved history. Operations are structured
# approximations - they organize judgment, not compute results.

---

## OPERATION 1 - Branch Summary (git log / PR description)
# Run at the END of a branch thread before switching back to trunk.
# Produces the portable artifact that all other operations consume.

---

> Summarize this conversation branch for integration into another thread.
>
> Produce a structured branch summary:
>
> **Branch type** - classify as one of:
> - *Fix*: resolved a specific problem
> - *Direction*: explored and developed a line of thinking worth pursuing
> - *Exploration*: went deep on a topic, conclusions tentative
> - *Idea*: generated possibilities, no commitment made
>
> **What this branch produced** - flat list, one line each:
> - Decisions reached (things that would hold up under review)
> - Artifacts created (specs, prompts, code, documents)
> - Insights gained (things that change how the problem should be approached)
> - Approaches rejected (and why - one line rationale)
>
> **What this branch changed** - compared to where it started, what is now different or known that was not before.
>
> **Merge recommendation** - one of:
> - *Full merge*: branch substantially advances the trunk, integrate most of it
> - *Cherry-pick*: specific items worth extracting, rest is scaffolding
> - *Hold*: valuable but conflicts with trunk decisions - needs conflict resolution first
> - *Close*: exploration complete, nothing to carry forward
>
> **Items to cherry-pick** (if applicable) - the specific decisions, artifacts, or insights to extract. Numbered list.
>
> Format as a single code block for clean copying.

---
---

## OPERATION 2 - Conflict Detection (git diff / merge conflict scan)
# Run in the TRUNK thread after pasting a branch summary.
# Run BEFORE integration to surface contradictions explicitly.

---

> A branch summary has been provided. Before integrating it, perform a conflict scan.
>
> Compare the branch summary against the current state of this thread and identify:
>
> **Direct conflicts** - where the branch reached a conclusion that contradicts a decision already made in this thread. For each:
> - State the trunk decision.
> - State the branch conclusion.
> - Label as: *supersedes trunk* / *trunk supersedes branch* / *requires human resolution*.
>
> **Additive changes** - branch content that does not conflict with anything in the trunk. Safe to integrate directly.
>
> **Scope gaps** - branch content that addresses something the trunk has not considered. Neither a conflict nor a direct addition - a new dimension.
>
> **Verdict** - one of:
> - *Clean merge*: no conflicts, proceed to integration
> - *Conflicts present*: resolve marked conflicts before integrating
> - *Partial merge safe*: additive changes can integrate now, conflicts deferred
>
> Do not integrate anything yet. This is a scan only.

---
---

## OPERATION 3 - Cherry-Pick (git cherry-pick)
# Use when you want a specific insight, artifact, or decision from a branch
# without pulling in the full branch context.

---

> Extract the following from this conversation: [DESCRIBE WHAT YOU WANT]
>
> Produce only the extracted item, formatted for direct use in another thread.
> Strip all scaffolding, intermediate reasoning, and context specific to this branch.
> The output should be self-contained - readable without access to this conversation.
>
> If the item depends on context that would be lost in extraction, note the dependency
> in a single line at the top: "Depends on: [what the recipient thread needs to know]"

---
---

## OPERATION 4 - Integration (git merge)
# Run in the TARGET thread (trunk or another branch) after conflict detection.
# Receives the branch summary and integrates clean items into the working context.

---

> Integrate the following branch summary into the current working context of this thread.
>
> [PASTE BRANCH SUMMARY HERE]
>
> Rules:
> - Integrate additive changes and scope gaps directly into the relevant sections of our current state.
> - Do not re-litigate items marked as *trunk supersedes branch* in the conflict scan.
> - For items marked *supersedes trunk*: apply the update and note what changed.
> - For items marked *requires human resolution*: list them at the end as open conflicts - do not resolve them.
>
> After integration, produce an updated state summary:
> - What changed from the branch integration (flat list)
> - Open conflicts requiring human resolution (flat list, or "None")
> - Current working state (the trunk's context as it now stands, dense)
>
> This updated state summary becomes the new working context for this thread.

---
---

## Branch Type  Merge Strategy

```
BRANCH TYPE     TYPICAL OPERATION       NOTES
-----------     -----------------       -----
Fix             Cherry-pick or          If fix contradicts trunk design,
                Full merge              run conflict detection first

Direction       Conflict detection      Direction branches often change
                 Full merge            decisions - scan before merging

Exploration     Cherry-pick             Extract insights, discard the
                                        path that produced them

Idea            Cherry-pick or          Most tentative - low merge
                Close                   priority, high close rate
```

---

## Workflow Slot

```
Branch running in parallel
         ³
         
  Branch Summary          run at end of branch
         ³
         
  Conflict Detection      run in target thread
         ³
    ÚÄÄÄÄÁÄÄÄÄ¿
    ³         ³
 Clean    Conflicts
  merge    present
    ³         ³
             
Integration  Human       resolve, then integrate
             resolution
         ³
         
  Updated working context
  (handoff document updated if crossing sessions)
```
