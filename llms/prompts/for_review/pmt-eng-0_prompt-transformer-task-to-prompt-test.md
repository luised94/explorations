```thinking
The user wants to know what kind of task to use for testing the generator. Let me think about what would stress-test the most dimensions of the generator.

The generator has these processing steps:
1. Extract (objective, constraints, inputs, steps)
2. Assess persona
3. Build system prompt
4. Build prompt set
5. Write usage note

What dimensions need testing:
- Vague vs. specific input handling
- Single-step vs. multi-step decomposition
- Persona inclusion vs. exclusion
- [DEFAULT] marking when inferring
- [PASTE] insertion points
- Format specification vs. freeform
- The actual quality of generated prompts (do they produce good output?)

Different task types stress different things:

**Coding task:**
- Good for: multi-step decomposition, concrete deliverables, format specification
- Weak for: persona assessment (rarely needed), vague input handling (coding tasks tend to be specific)
- Risk: the model is already good at coding prompts, so it won't reveal weaknesses

**Learning task:**
- Good for: persona assessment (tutor persona might help), multi-step sequencing, vague inputs ("teach me X")
- Weak for: concrete deliverables (learning is a process, not an artifact)
- Risk: hard to evaluate output quality objectively

**Writing task:**
- Good for: persona assessment, tone/audience constraints, vague inputs
- Weak for: multi-step decomposition (often single-step), format specification

**Research/analysis task:**
- Good for: multi-step decomposition, input handling ([PASTE] documents), format specification
- Moderate for: persona (analyst persona might help)

**Workflow/process task:**
- Good for: multi-step, dependencies, chain patterns
- Good for: revealing whether the generator handles complex sequencing

Actually, the best approach isn't to pick ONE task type - it's to pick a small battery that covers the dimensions. But the user asked for a recommendation, and they probably don't want to run 10 tests.

The ideal single test task would:
1. Be vague enough to test default-inference
2. Decompose into multiple steps
3. Have a domain where persona might or might not help (tests the assessment)
4. Require user inputs ([PASTE] points)
5. Mix structured and freeform output
6. Produce output whose quality is evaluable

Something like: "I want to analyze my codebase for security vulnerabilities and produce a report for my team lead."

This hits:
- Vague (what codebase? what language? what kind of vulnerabilities?)
- Multi-step (scan, analyze, prioritize, report)
- Persona assessment (security auditor persona genuinely helps here)
- Inputs (user pastes code)
- Mixed output (structured vulnerability list + freeform executive summary)
- Evaluable (did the prompts produce useful security analysis?)

But actually, I think the user is asking me more broadly - what CATEGORY of task, and maybe they want my reasoning on which reveals the most about the generator's gaps.

Let me also think about what a coding task reveals vs. what a learning task reveals:

Coding: the generator will likely do well because coding tasks are highly structured. It won't reveal weaknesses in ambiguity handling, persona assessment, or freeform output.

Learning: reveals more. "Teach me distributed systems" is vague, multi-faceted, benefits from persona (experienced teacher), requires sequencing (what order?), and the quality of the prompts directly affects the learning experience. It also tests whether the generator can produce prompts that adapt to different levels of understanding.

A real-world compound task might be best - something that crosses domains and requires the generator to make non-obvious decomposition choices.

I think I should recommend a specific battery of 3-4 tasks, each targeting different dimensions, rather than picking one. But lead with the single best diagnostic task.

Actually, the user's phrasing "coding task, learning task, or something else" suggests they want me to pick or suggest. Let me be direct with a recommendation and reasoning.
</thinking>

Neither alone. A coding task won't reveal much - coding is already well-structured, personas rarely matter, and inputs are concrete. The generator will look good without being tested. A learning task is better but hard to evaluate objectively ("did I learn?" is subjective).

The best diagnostic is a task that forces every processing step to do real work. Here's a battery of three, ordered by what each reveals:

**Test 1: The vague compound task** (stresses extraction, decomposition, persona assessment, defaults)

> "I want to improve my team's code review process."

This is deliberately underspecified. No tech stack, no team size, no current process, no definition of "improve." The generator must infer an objective, decide whether persona helps (it should - process consultant or engineering manager framing changes the output), decompose into steps (audit current state  identify gaps  design new process  produce artifacts), and mark defaults. This test reveals whether the generator produces something useful from ambiguity or collapses into either interrogation or generic advice.

**Evaluate:** Did the generator produce prompts you could actually use? Are the defaults reasonable? Would the prompts produce different output than just asking the model "how do I improve code reviews?" If the generated prompts produce roughly the same output as the raw question, the generator added no value.

**Test 2: The input-heavy analytical task** (stresses PASTE points, multi-step sequencing, format specification)

> "I have server access logs from the past week. I need to figure out what caused the outage on Tuesday and write a postmortem for stakeholders."

This requires the user to supply data, decomposes into distinct phases (parse logs  identify anomalies  correlate with timeline  draft postmortem), mixes structured output (log analysis) with freeform output (postmortem narrative), and involves two audiences (the engineer doing analysis, the stakeholders reading the postmortem). The generator must place `[PASTE]` points and handle the audience shift.

**Evaluate:** Are the PASTE points in the right places? Does the prompt sequence carry information forward correctly between steps? Does the postmortem prompt produce a different kind of output than the analysis prompt (audience-aware)?

**Test 3: The deceptively simple task** (stresses the "don't over-engineer" instinct)

> "Write a good README for my project."

This should produce a short, single-step prompt - maybe with a system prompt, maybe without. The test reveals whether the generator resists the urge to decompose a fundamentally single-step task into artificial phases. If the generator produces four steps and a complex system prompt for a README, the decomposition logic has no floor.

**Evaluate:** Is the output proportional to the task? One prompt, maybe two? Does the generated prompt produce a better README than just asking "write a README for my project"? The delta between raw ask and generated prompt is the generator's value-add. Measure the delta.

**What to look for across all three:**

| Dimension | Test 1 | Test 2 | Test 3 |
|-----------|--------|--------|--------|
| Default inference from vague input | Primary | Secondary | Secondary |
| Multi-step decomposition | Primary | Primary | Should resist |
| Persona assessment | Primary | Secondary | Edge case |
| PASTE insertion points | - | Primary | Depends |
| Format specification | Secondary | Primary | Light |
| Proportionality (not over-engineering) | - | - | Primary |
| Prompt quality delta vs. raw ask | All three | All three | All three |

The last row is the most important metric overall. Run each generated prompt AND the raw task against the same model. Compare outputs. If the generated prompt produces meaningfully better output, the generator works. If the outputs are indistinguishable, the generator is adding ceremony without value - and the processing steps need to produce prompts that are structurally different from what a naive user would write, not just cleaner versions of the same thing.

That comparison - generated prompt vs. raw ask - is the single most honest test. Everything else is proxy measurement.

Category: [prompt_engineering] | Keywords: [testing_strategy, diagnostic_tasks, prompt_evaluation, value_delta, proportionality]
