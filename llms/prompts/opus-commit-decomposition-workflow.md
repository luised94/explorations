<thinking>
The user is asking me to write the actual prompt(s) that would be used to classify a commit/task based on the framework we just developed. They want to know how I would prompt myself (as a language model) to do this classification.

Let me think about this carefully. The goal is: given a description of a task/commit, classify it along the four dimensions and derive the execution strategy.

But wait-there's a subtlety. The prompt needs to work in practice, which means:

1. It needs to be concise enough to actually use repeatedly
2. It needs to surface tacit assumptions (Layer 0)
3. It needs to classify along the four dimensions
4. It needs to derive the execution strategy

Should this be one prompt or multiple? Let me think...

In practice, you might want:
- A single classification prompt that does all of this in one shot
- Or a two-stage: first surface assumptions, then classify

Actually, the user said "irreducible prompt set" earlier. So what's the minimum set of prompts needed?

I think there might be two modes:
1. **Pre-commit classification** - "I need to do X"  classify  determine strategy
2. **Batch classification** - Looking at a set of planned changes and triaging them

Let me think about how I'd actually want to be prompted...

The key insight is that the prompt should force the model to STOP and think about the dimensions before jumping to action. Most people (including when prompting LLMs) go straight to "do the thing" without classifying what kind of thing it is.

Let me draft this...

Actually, I should think about what the user's workflow looks like:
- They have a task/change in mind
- They need to decide: do I use a command? Do I ask an LLM? Which tier? Do I do it manually?
- They want a prompt that helps make this decision

So the prompt is essentially a triage/routing prompt. It takes a task description and outputs a classification + recommended approach.

Let me think about the minimal effective prompt...

One approach: a single system prompt that acts as a classifier. You feed it the task, it gives you the classification and recommended action.

Another approach: the prompt is actually for the USER to fill out-a template that forces them to think through the dimensions, and the classification falls out naturally.

Or both-a self-interrogation prompt that the model uses to ask clarifying questions, then classifies.

I think the most practical version is:

**One prompt** that:
1. Takes a task description
2. Surfaces what's implicit
3. Classifies on the four dimensions
4. Outputs the execution strategy

Let me write this. I want it to be tight-no bloat.

Hmm, but there's another consideration. The user mentioned they use haiku/sonnet/opus tiers. So this classification prompt itself should probably be run on a small/fast model since it's a routing decision. It shouldn't require Opus to decide whether you need Opus.

Let me also think about the output format. It should be scannable, actionable. Not a wall of text.

Let me draft:

---

Given a task, classify it and determine execution strategy.

First, surface what's implicit:
- What files/areas are affected?
- What must be true for this change to be correct?
- What could go wrong?

Then classify:
- Scope: site | function | file | multi-file | codebase
- Complexity: mechanical | contextual | design
- Complection: isolated | coupled | entangled
- Determinism: one correct output | constrained choices | open-ended

Then derive:
- Action: command | editor op | snippet | full file | guidance
- Agent: human | shell/editor | modelhuman
- Model tier: none | small | medium | large

---

Actually wait. I want to think about whether this should be even more compressed. The user appreciates the haiku/sonnet/opus compression precisely because it's fast. A 4-dimensional classification might be too heavy for every commit.

Maybe the irreducible set is actually TWO prompts:

1. **Quick triage** - Fast, one-shot, for the common case where the mapping is obvious
2. **Deep classification** - For when the quick triage is ambiguous or the stakes are high

That mirrors the system itself-simple things should be simple, complex things should be thorough.

Or... maybe it's one prompt with a built-in short-circuit. If the task is obviously simple, don't go through all four dimensions. If it's ambiguous, expand.

Let me think about what format works best...

I think the cleanest approach is:

1. A **classification prompt** (system-level) that the model uses
2. The user just describes the task naturally
3. The model outputs a structured classification + recommended action

And the prompt should be designed so that trivial tasks get trivial classification (don't overthink a sed rename) while complex tasks get thorough analysis.

Let me write the actual prompt now. I'll make it how I'd genuinely want to be prompted.

Actually-the user asked "how would you prompt yourself?" This is a fascinating question because it's asking me to be meta about my own optimal input format.

What do I actually need to classify well?
- Clear description of the change
- Context about the codebase (or enough to infer)
- What the user's environment is (shell, editor, model access)

What makes me misclassify?
- When scope is ambiguous because the user hasn't thought about blast radius
- When something sounds simple but is actually complected
- When I don't know the codebase structure

So the prompt should force those to be addressed.

Let me write the final version.

I think there should be:
1. A system prompt for the classifier role
2. Optionally, a template the user fills in (but shouldn't be required-natural language should work)

Let me also think about whether this should produce the COMMIT itself or just classify. I think classify only-the classification then routes to the appropriate execution method. Separation of concerns.

OK here's my attempt:

---

System prompt (the classifier):

```
You are a commit classifier. Given a task description, determine the optimal execution strategy.

STEP 1 - SURFACE IMPLICIT
Before classifying, state:
- What is actually changing? (be specific)
- What are the preconditions for correctness?
- What is the blast radius if wrong?

STEP 2 - CLASSIFY
Rate each dimension:

Scope:        site | function | file | multi-file | codebase
Complexity:   mechanical | contextual | design  
Complection:  isolated | coupled | systemic
Determinism:  deterministic | constrained | open

STEP 3 - DERIVE
From the classification:

Action:     command | editor_op | snippet | full_file | rewrite | guidance
Agent:      shell | editor | modelhuman | human
Model tier: none | small | medium | large

STEP 4 - PRESCRIBE
State the specific recommended action in one line.
If action is 'command', provide the command.
If action is 'editor_op', provide the nvim command.
If action requires a model, state what to ask for.
```

---

Hmm, that's decent but maybe too rigid. Let me think about whether steps 2 and 3 should be more fluid...

Actually, I think the rigidity is a feature here. The whole point is to force systematic classification rather than jumping to action. The structure IS the value.

But I should add a short-circuit: if something is obviously a command, don't make it go through 4 steps. Let me add that.

Also, I realize the user might want multiple prompts for different stages of their workflow. Let me think about the full prompt set:

1. **Classify** - What kind of task is this? (the one above)
2. **Execute** - Now do it (this is where you'd use the appropriate tier/action)

The classification prompt routes to the execution prompt. The execution prompt is different depending on the classification.

For execution, the "prompts" might be:
- For `none/command`: just run the command, no prompt needed
- For `small/snippet`: "Generate [specific thing] for [specific context]"
- For `medium/full_file`: "Given [file context], generate [complete file] that [specific change]"
- For `large/rewrite`: "Given [broader context], design and implement [change] considering [concerns]"

So the irreducible prompt SET is really:
1. Classification prompt
2. Execution prompt templates per tier

Let me write this up cleanly.

One more thought: the user said "how would you prompt yourself?" - I should be honest about what actually helps me perform well. What helps:
- Specificity over generality
- Constraints stated explicitly
- Context provided, not assumed
- Clear success criteria
- One job per prompt

That should inform the design.
</thinking>

# The Prompt Set

## Prompt 0: The Classifier

This is the routing prompt. Runs on any tier-it's lightweight by design.

```
Given a task, classify then prescribe.

Surface:
- What specifically changes?
- What must hold for correctness?
- Blast radius if wrong?

Classify:
  Scope:        site | function | file | multi-file | codebase
  Complexity:   mechanical | contextual | design
  Complection:  isolated | coupled | systemic
  Determinism:  deterministic | constrained | open

Derive:
  Action: command | editor_op | snippet | full_file | rewrite | guidance
  Agent:  shell | editor(nvim) | modelhuman | human
  Tier:   none | small | medium | large

Prescribe the specific next action in one line.
If command: give the command.
If editor_op: give the nvim keystrokes/ex command.
If model: state exactly what to request and at what tier.

Short-circuit: if deterministic + isolated, skip to prescription.
```

That's the whole classifier. Now here's what I actually want to say about it:

---

## Why this shape

**The short-circuit is critical.** Most commits are simple. A rename, a version bump, a deleted file. The prompt wastes your time if it forces four-dimensional analysis on `sed -i 's/foo/bar/g' **/*.py`. The short-circuit says: *if the answer is obvious, just give the answer.*

**"Surface" is doing the real work.** The classification dimensions are almost mechanical once you've answered those three questions honestly. "What specifically changes?" kills vagueness. "What must hold?" forces you to think about invariants. "Blast radius?" is the risk check that prevents you from treating a systemic change as isolated.

**The prescription must be concrete.** Not "use a medium-tier model to help." Instead: "Ask Sonnet to generate the updated `parse.rs` with the new error variant threaded through match arms, providing the current file and the type definition as context." That's actionable. The vague version is useless.

---

## Prompt 1-N: The Execution Templates

The classifier *routes* to these. Each is a different prompt shape optimized for its tier.

### Tier: None (Shell/Editor)

No prompt. You got a command from the classifier. Run it.

```bash
# The classifier already gave you this:
find . -name '*.rs' -exec sed -i 's/OldName/NewName/g' {} +
```

### Tier: Small - Mechanical Generation

```
Generate [specific output] given [specific input].

Context:
[paste the minimal relevant code/file]

Change:
[exact description of what to produce]

Output the result only. No explanation.
```

The key property: **minimal context, maximal specificity.** You're not asking it to understand-you're asking it to transform. Like a slightly smarter sed.

### Tier: Medium - Contextual Generation

```
Given this file and its role in the system, produce the updated version.

File: [filename]
Role: [one sentence on what it does and what depends on it]
Change: [what needs to change and why]
Constraints: [what must not break]

[paste file]

Output the complete updated file.
```

The key property: **you supply the judgment, it supplies the labor.** You've already decided *what* to do. It needs enough context to do it *correctly* across the whole file without breaking contracts.

### Tier: Large - Design-Level

```
I need to [goal].

Current state:
[relevant architecture/structure/files]

Constraints:
[what's fixed, what's flexible]

Concerns:
[what I think is hard about this, where I'm uncertain]

Think through the approach, surface anything I've missed,
then provide the implementation.
```

The key property: **you're sharing the judgment.** You don't fully know the right answer. You need the model to reason about tradeoffs, notice things you haven't, and *then* generate. This is the only tier where explanation before code is valuable.

---

## The Meta-Observation

The prompt set is really **one classifier + a gradient of context/autonomy:**

```
none   zero context,  zero autonomy  (you run a command)
small  minimal context, zero autonomy  (transform this  that)
medium  file context,   low autonomy   (you decided, it executes)
large  system context,  shared autonomy (you collaborate on the decision)
```

What scales across the tiers isn't just model capability-it's **how much of your judgment you're encoding in the prompt vs. delegating to the model.** The classifier's real job is deciding that boundary.

---

## How I'd actually prompt myself

Honestly? If I were routing my own work:

```
What kind of problem is this? Be specific about what changes, then tell me
the simplest thing that could work-command, editor operation, or generation
at what tier-and why not simpler.
```

That last clause-**"and why not simpler"**-is the one that does the most work. It forces justification for escalation. The default should always be the lowest tier that works. You go up only when you can articulate why the tier below fails.

---

Category: prompt_engineering
Keywords: [commit_classification, task_routing, execution_strategy, model_tiering, prompt_design]
