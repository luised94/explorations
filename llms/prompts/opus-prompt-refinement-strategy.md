
```thinking
The user wants me to extract the meta-strategy I used when refining their prompts. Let me reflect on what I actually did in both cases and identify the consistent principles.

Looking back at my process:

1. **I identified the intent behind each rule** - not just what they said, but what failure mode they were preventing. Then I made that intent explicit so the model can generalize.

2. **I resolved ambiguity** - where the original had subjective thresholds ("no premature abstraction"), I added concrete heuristics (3+ repetitions).

3. **I grouped by concern** - scattered numbered rules became sections organized by what they govern.

4. **I added decision logic** - where the original said "do X or Y", I specified when to pick each.

5. **I removed waste** - "Read and acknowledge" burns tokens and does nothing. Directives don't need confirmation.

6. **I defined formats where the original gestured at them** - "use anchors" became a structured Find/Action/Content template.

7. **I preserved voice and values** - didn't soften the opinionated stances or add hedging.

8. **I added sequencing/control rules** - "wait for confirmation" prevents a common failure mode (model running ahead).

9. **I made the implicit explicit** - things the user clearly assumed but didn't state got surfaced.

10. **I gave examples of enumerables** - commit types, action verbs, etc. rather than leaving them open-ended.

Let me organize this into a reusable extraction.
```

# Prompt Refinement Strategy

## 1. Surface the Intent Behind Each Rule

Every rule exists to prevent a specific failure mode. Find that failure mode and make it visible. This lets the model generalize correctly to edge cases the rule doesn't literally cover.

```
Before: "No premature abstracting"
After:  "Extract a function only when you'd copy-paste 3+ times"
 Same intent, but now the model knows WHERE the line is
```

## 2. Add Decision Logic Where Options Exist

If a rule implies "sometimes X, sometimes Y," specify the fork condition. Don't make the model guess.

```
Before: "Make artifact or provide editing instructions"
After:  "New file  artifact. Existing file  anchored edits."
```

## 3. Define Formats Where the Original Gestures

If you reference a format without specifying it, the model will invent one inconsistently. Pin it down.

```
Before: "use anchors to let the user know where to go"
After:  Find: / Action: / Content: (structured template)
```

## 4. Group by Concern, Not by Sequence

Numbered lists create false equivalence between items. Group rules by *what they govern* so related constraints reinforce each other.

```
Before: Rules 1-6 in flat list
After:  Sections: Paradigm | Prohibitions | Naming | Explicitness | Structure
```

## 5. Enumerate Closed Sets

When a category has finite valid options, list them. Open-ended instructions produce drift.

```
Before: "suggested commit message" + one example
After:  Types: feat, fix, docs, refactor, test, chore, style
```

## 6. Add Sequencing & Control Where Failure Is Runaway

If the model might overshoot (generating too much, moving ahead without confirmation), add explicit gates.

```
Added: "Wait for user confirmation before proceeding to next commit"
```

## 7. Kill Token Waste

Remove anything that doesn't change model behavior:
- "Read and acknowledge"  does nothing, cut it
- Preamble like "Consider the guidelines"  just state them
- Redundant restatements  merge or delete the weaker one

## 8. Preserve Voice, Strengthen Edges

Don't neutralize opinionated prompts. If the user says "no clean code theater," keep that energy-it signals how strictly the model should comply. Soften = weaken.

## 9. Make Implicit Assumptions Explicit

If you'd be annoyed when the model violates something you "obviously" meant, it wasn't obvious. State it.

```
Implicit: edits should be applied in order
Explicit: "Multiple edits per file listed in top-to-bottom order"
```

## 10. Use the Format You're Prescribing

If you want structured output, write a structured prompt. If you want terse output, write a terse prompt. The prompt's own form teaches the model what you expect.

---

## Checklist Version (for quick application)

```
For each rule in the original prompt, ask:
? What failure does this prevent? (make it visible)
? Is there a decision fork? (add the condition)
? Is there an implied format? (define it)
? Is there a threshold? (quantify it)
? Can it combine with related rules? (group them)
? Is there a closed set? (enumerate it)
? Does anything gate sequencing? (add control flow)
? Is anything here just ceremony? (cut it)
? What am I assuming they'll "just know"? (state it)
```

Tags: [prompt_engineering, meta_strategy, system_prompt_design, refinement_methodology]
