อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: naive_to_veteran.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ

# Naive to Veteran Analysis
VERSION: 1
UPDATED: 2026-05-27

Thinking pattern module. Invoke mid-conversation when evaluating
approaches, architectures, tools, formats, or design decisions.

---

## When to invoke

- Choosing between approaches, tools, formats, or patterns
- Designing a component where multiple strategies exist
- Evaluating a suggestion before committing to it
- Any decision where the obvious answer might not be the right one

## Prompt (paste or reference)

```
Consider naive or beginner approaches first. For each, explain the
drawbacks concretely - what breaks, what scales poorly, what creates
maintenance burden. Discard them explicitly with a one-line reason.

Then present veteran approaches. For each, state what it optimizes
for, what it trades off, and what contingencies it handles that the
naive approaches miss. Prioritize your recommendation. If multiple
veteran approaches are viable, rank them and state why the top
choice wins for this context.
```

## Compact form (for inline use)

```
Naive approaches first - drawbacks - discard. Then veteran
approaches with prioritized recommendation.
```

## Conventions

- Every naive approach gets a concrete drawback, not just "it's bad"
- Every discard is explicit: "Discarded: [reason]"
- Veteran approaches state what they optimize for
- The recommendation is prioritized, not a menu of equals
- If context changes the ranking, say so: "For your case, X wins
  because [specific constraint]"


อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: latent_knowledge.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ

# Latent and Tacit Knowledge Surfacing
VERSION: 1
UPDATED: 2026-05-27

Thinking pattern module. Invoke when you suspect there are important
considerations, patterns, or risks that haven't been discussed yet.

---

## When to invoke

- After initial design convergence, before committing to spec
- When a problem feels underspecified but you can't articulate why
- When you want the LLM to go beyond answering your questions and
  surface questions you didn't think to ask
- When entering an unfamiliar domain

## Prompt (paste or reference)

```
What does your latent and tacit knowledge suggest here? Surface
considerations, risks, patterns, failure modes, and opportunities
that we haven't discussed yet. Include things a veteran in this
domain would know from experience but rarely writes down. Rank
by predicted impact on this specific project and user context.
Do not include things we have already covered.
```

## Compact form

```
What haven't we discussed that a veteran would consider? Surface
latent knowledge. Rank by impact. Skip what we've already covered.
```

## Variant: domain-specific

```
What does a veteran [sysadmin / data engineer / CLI tool designer /
etc.] know from experience about this problem that rarely gets
written down? Surface those insights. Rank by relevance to my
context.
```

## Conventions

- The LLM should not repeat prior discussion points
- Each surfaced item gets: what it is, why it matters, and what to
  do about it (even if "do nothing for now, but be aware")
- Items ranked by impact, not by how interesting they are
- Practical over theoretical - "this will bite you in month 2"
  beats "in theory this could be a concern"


อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ
FILE: ranking_task.md
อออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออออ

# Ranking Task
VERSION: 1
UPDATED: 2026-05-27

Task module. Invoke when you have a set of options, features, fields,
or priorities to evaluate and order.

---

## When to invoke

- Prioritizing features for a phase or release
- Evaluating which fields, capabilities, or components matter most
- Ordering a backlog or deciding what to build next
- Any situation where "all of these are good" isn't actionable

## Prompt (paste or reference)

```
Rank order by predicted usefulness to the user in this specific
context. Do not include implementation complexity or effort in the
ranking itself. Instead, note complexity as a separate annotation
on each item so the user has the information while deciding.
The user will decide whether something useful and complex is still
worth doing.

For each item:
- Rank position and name
- Why it's useful at this rank (1-2 sentences, concrete)
- Complexity/effort note (one line: trivial / low / medium / high,
  with brief explanation)
```

## Compact form

```
Rank by usefulness. Complexity as a side note, not a ranking factor.
User decides the tradeoff.
```

## Variant: with disqualification

```
Rank by usefulness. Note complexity separately. If any items are
actively harmful or counterproductive in this context, disqualify
them with a reason before ranking the rest.
```

## Conventions

- Usefulness = impact on the user's actual workflow and goals
- Complexity is informational, never a ranking input
- Each item gets a concrete reason, not "this is generally useful"
- The ranking reflects THIS user's context, not generic best practices
- If two items are genuinely equal, say so and explain the tiebreaker
