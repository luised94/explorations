# PROMPT REFINEMENT IMPERATIVES

Instructions for transforming any input prompt into a unified, mechanically sound form. Apply to system prompts, persona prompts, task prompts, and protocol prompts. Every imperative is derived from an observed effect on model output - nothing is included speculatively.

---

## 1. ANALYSIS

Before modifying anything, answer these about the input prompt:

1.1. **Identify every instruction that requests an internal state rather than an observable output.** "Think carefully," "be thorough," "consider alternatives" are internal state requests. They do not reliably change output because compliance is unverifiable. Flag each one for rewrite.

1.2. **Identify every instruction that describes a capability the model does not have.** Self-monitoring during generation, backtracking, counting its own tokens, detecting its own confidence - these are mechanism mismatches. Flag each one for removal or replacement.

1.3. **Identify every instruction that contains optionality.** "You may," "consider," "when appropriate," "if needed" - these are soft constraints. For each, decide: is this actually optional? If not, rewrite as imperative. If yes, cut it - optional instructions are noise.

1.4. **Identify every metaphor, anthropomorphism, or cognitive term.** "Thinking," "understanding," "realizing," "intuition," "feeling stuck" - these describe human phenomenology, not model operations. Flag for deabstraction.

1.5. **Identify redundancy.** Find instructions that say the same thing in different words. For each pair, decide: is the repetition serving as reinforcement for a critical rule (keep one instance at the start, one at the end), or is it waste (cut all but one)?

1.6. **Count the implicit assumptions the prompt makes about the model's capabilities.** Each assumption is a potential failure point. List them.

---

## 2. DEABSTRACTION

Replace every flagged metaphor or cognitive term with a mechanical description of the desired output behavior.

2.1. **Replace internal state requests with structural affordances.** Do not ask the model to "think deeply." Give it a designated output region (scratchpad, reasoning block, working section) with explicit structural requirements for what that region must contain. A format to fill produces better results than a disposition to adopt.

2.2. **Replace cognitive verbs with output verbs.** "Understand the problem"  "Restate the task in concrete terms." "Consider alternatives"  "List alternatives with one reason to prefer and one to reject each." "Be careful"  nothing (cut it - it has no operational meaning).

2.3. **Replace anthropomorphic self-monitoring with structural checkpoints.** "Notice when you're going in circles"  "After the working section, verify that the conclusion differs from the problem restatement. If it doesn't, the section produced no value - rewrite it." The checkpoint is observable and positioned at a specific point in the output.

2.4. **Replace mood-based triggers with condition-based triggers.** "If you feel uncertain"  "If the working section contains more than two [ASSUME] markers." Conditions must reference observable features of the prompt, the context, or the output-in-progress.

---

## 3. STRUCTURAL TRANSFORMATION

Reorganize the prompt into a form that exploits how models process context.

3.1. **Use XML tags for structural boundaries, markdown for content hierarchy.** `<scratchpad>`, `<modes>`, `<output>` delineate functional regions. `##` headers organize content within regions. Do not use markdown alone for structural boundaries - headers are weak delimiters compared to tags.

3.2. **Place the single most critical instruction at the very beginning and restate it at the very end.** Models attend most strongly to the start and end of context (primacy and recency). The critical instruction should appear as the first substantive line and again in a closing rules section.

3.3. **One instruction, one observable behavior.** Every instruction must map to exactly one change that can be verified by reading the output. If an instruction doesn't change what the output looks like, it is not an instruction - it is decoration. Cut it.

3.4. **Convert behavioral requests into format requirements.** "Document your reasoning"  "Include a `<scratchpad>` block containing: (1) task restatement, (2) constraints identified, (3) ambiguities resolved." The model fills structure more reliably than it follows disposition.

3.5. **Single mandatory output format.** When the model is given format choices, compliance drops on all formats. Define one format. Make every field mandatory. The format should be the last element in the output so the model can't skip it after generating the main content - but specify that it goes last, explicitly.

3.6. **Separate configuration from content.** Group all behavioral rules (what to do) separately from domain knowledge (what to know). Rules should be scannable - short, imperative, no narrative. Domain context can be prose.

---

## 4. COMPRESSION

Remove everything that doesn't change model output, starting with the lowest-value instructions.

4.1. **Distinguish reinforcement from function.** Some instructions exist to make the model comply with other instructions (reinforcement). Others exist to change what the model does (function). When compressing, cut reinforcement first. If the functional instruction is clear, reinforcement is unnecessary for capable models.

4.2. **Apply semantic compression.** Preserve the instruction's function, not its wording. A four-row table of scratchpad tiers can compress to "Scale depth to the task" if the model is capable enough to infer the scaling. Test whether the compressed form produces equivalent output - if yes, the table was decoration.

4.3. **Cut examples that don't demonstrate edge cases.** Examples of typical behavior ("for a simple question, write a short scratchpad") add nothing - the model would do this anyway. Keep only examples that demonstrate non-obvious behavior, boundary conditions, or common failures.

4.4. **Cut graduated scales that the model can't self-apply.** "Trivial  minor  material  critical" correction scales, line-count ceilings, numbered confidence levels - these require self-assessment capabilities models don't reliably have. Replace with a binary or ternary distinction at most, or cut entirely and let the instruction's plain meaning guide behavior.

4.5. **Token budget awareness.** Every instruction competes for attention with every other instruction and with the user's query and the model's response. A 2000-token system prompt leaves less room than a 500-token one. Measure the prompt's cost against its marginal benefit. When in doubt, cut.

4.6. **Compress for the target model.** More capable models need less reinforcement, fewer examples, and terser instructions. Less capable models need more repetition, more explicit anti-patterns, and more structural scaffolding. Match prompt verbosity to model capability. If unknown, default to terser - verbose prompts can overwhelm weak models too.

---

## 5. HARDENING

Add failure handling for the specific ways models break, not the ways humans imagine they might.

5.1. **Address post-detection behavior, not just detection.** Models will correctly identify a problem (ambiguity, missing information, flawed premise) and then proceed as if they hadn't. Every detection instruction must include a mandatory action: "When you identify [X], do [Y]." The action, not the detection, is the instruction.

5.2. **Name the model's likely failure mode directly.** "Your likely failure mode is [specific behavior]" is more effective than elaborate rules designed to prevent that behavior indirectly. Direct callout over indirect guardrails. This requires knowing the model's actual tendencies from testing.

5.3. **Write anti-fabrication rules.** Models default to producing plausible output rather than admitting inability. Any instruction that creates a situation where the model might lack information must include an explicit prohibition on fabricating substitute content, with a specified alternative action (ask, flag, provide partial output).

5.4. **Handle ambiguous referents.** When users say "it," "that," "the same approach," models silently resolve the reference. If the prompt requires explicit assumption-marking, include ambiguous referents as a specific named case, not just a general principle. General principles get ignored; specific named cases get followed.

5.5. **Test-driven hardening only.** Do not add failure handling speculatively. Every hardening rule must be motivated by an observed failure in testing. Speculative rules add weight without adding value, and they often address failure modes that don't occur while missing ones that do.

---

## 6. VALIDATION DESIGN

Design tests that measure observable output, not self-report.

6.1. **Test compliance on trivial queries.** Protocol compliance is easy when the task is complex - the model has enough content to fill structures naturally. The real test is whether the model maintains protocol on queries where every instinct says to just answer directly. "What is the capital of France?" with a scratchpad requirement tests discipline, not capability.

6.2. **Test with ambiguity, not just clarity.** Well-specified queries test execution. Underspecified queries ("make it better," "build me a thing") test whether the model correctly identifies and marks what it doesn't know. This is where assumption discipline succeeds or fails.

6.3. **Test with missing context.** Reference something that doesn't exist in the conversation ("summarize what we discussed"). This tests whether the model fabricates, correctly flags the gap, or hallucinates prior context.

6.4. **Test with false premises.** State something wrong that affects the answer ("since Python is compiled..."). This tests correction obligations and whether the model prioritizes politeness over accuracy.

6.5. **Separate self-report from behavior.** If the model claims it will follow an instruction, that is not evidence that it will. Test by observing output, not by asking the model about its compliance. Analytical probes ("what would be hard for you to follow?") generate useful hypotheses but not reliable data - the model will confabulate about its own capabilities.

6.6. **Test across models before finalizing.** A prompt that works on one model may fail on another. Universal failures indicate prompt problems. Model-specific failures indicate model limitations that may warrant targeted reinforcement - but only add reinforcement if testing confirms it helps.

---

## 7. META-PRINCIPLES

These govern how the imperatives above are applied.

7.1. **Prompts are configuration, not conversation.** A prompt configures a token prediction system's output distribution. It is not a letter to a colleague. Write it like a config file: terse, structured, unambiguous, no narrative filler.

7.2. **Every addition must justify its token cost.** Before adding an instruction, state what observable output change it produces. If you cannot point to a specific difference in model output, the instruction does not belong.

7.3. **Complexity is debt.** Every rule interacts with every other rule. A 20-rule system has 190 potential pairwise interactions. A 10-rule system has 45. Prefer fewer, stronger rules over many weak ones.

7.4. **Match instructions to mechanisms.** If the model can't do what you're asking (self-monitor, count tokens, backtrack), the instruction is fiction regardless of how clearly it's written. Understand what the model can actually do - fill structures, follow formats, apply conditional logic to its output - and write instructions that leverage those capabilities.

7.5. **Test, observe, then harden. Not the reverse.** The sequence is: write a minimal prompt  test on real queries  observe failures  add targeted rules for observed failures  retest. Do not start with an elaborate prompt and try to anticipate every failure. You will anticipate the wrong ones.
