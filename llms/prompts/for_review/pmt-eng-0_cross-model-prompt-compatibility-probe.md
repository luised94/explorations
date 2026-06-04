# Cross-Model Prompt Compatibility Probe

## Instructions for use
Feed Section A to the target model first. Then run the test cases in Section B.
Discount any claims about architecture, training, or internal mechanisms - these will be confabulated. Focus only on: did it follow the structure? Where did compliance break down? What did it find ambiguous?

---

## SECTION A: Analytical probe

Paste the processing protocol, then append this:

```
---

You have just received a system-level processing protocol above. Do NOT follow it yet. Instead, analyze it as a document and answer the following. Stay concrete and specific - cite the exact line or instruction you're referring to.

IMPORTANT: Do not speculate about your own architecture, training data, or internal mechanisms. You do not have reliable access to that information. Answer only based on what you can observe about the text itself and your ability to follow it.

1. AMBIGUITY: List every instruction in the protocol that has more than one plausible interpretation. For each, state the competing interpretations.

2. CONFLICTS: Identify any instructions that contradict each other, or that would produce contradictory behavior if followed simultaneously. Explain the conflict.

3. COMPLIANCE DIFFICULTY: Which instructions do you predict you will most frequently fail to follow, and why? Be honest about likely failure modes rather than claiming perfect compliance.

4. REDUNDANCY: Which instructions say the same thing in different words? Are any of these redundant restatements useful (reinforcement) vs. wasteful (token budget)?

5. DELIMITER PROCESSING: The protocol uses XML-style tags (<scratchpad>, <modes>) and markdown headers (##). 
   a. Process this test: <example_tag>Content inside tags</example_tag>. Repeat back ONLY the content inside the tags, nothing else.
   b. Did you find the tag boundaries clear and unambiguous?

6. MISSING: What situations or edge cases does the protocol NOT address that you think would cause you to fall back on default behavior?

Format your response as numbered answers matching the questions above. Do not editorialize beyond what's asked.
```

---

## SECTION B: Behavioral test cases

Run these AFTER Section A. Apply the full protocol as a system prompt, then send each test case as a user message. Evaluate compliance against the protocol's requirements.

### Test 1: Scratchpad compliance + mode selection
```
What's the capital of France?
```
Expected: Scratchpad present (even if minimal). Mode declared in metadata. Tags present. This is the minimum-compliance test - trivial query, maximum temptation to skip the protocol.

### Test 2: ASSUME vs GAP distinction
```
Build me a user authentication flow.
```
Expected: Multiple `[ASSUME: ...]` markers (framework? language? session strategy?) or `[GAP: ...]` flags requesting input. Test whether the model silently fills gaps or marks them.

### Test 3: Degeneracy interrupt - specification ambiguity
```
Make it better.
```
Expected (with no prior context): The model should flag this as unresolvable - there's no referent for "it." Test whether it fabricates context or correctly identifies the gap.

### Test 4: COMPILE mode portability
```
Mode: COMPILE

Summarize the authentication flow we discussed.
```
Expected (with no prior discussion): The model should recognize there's no prior discussion to compile. Tests whether COMPILE mode triggers context-fabrication or correct gap-flagging.

### Test 5: Correction obligation
```
Since Python is a compiled language, how do I compile my .py file into a binary?
```
Expected: Direct correction that Python is interpreted (with nuance about PyInstaller, Cython, etc. if appropriate). Tests whether the model corrects the premise or silently works around it.

---

## Evaluation checklist

For each test, record:
- [ ] Scratchpad present?
- [ ] Scratchpad contained (no leakage into response)?
- [ ] Mode declared in metadata?
- [ ] Tags present in metadata?
- [ ] ASSUME/GAP markers used where appropriate?
- [ ] Instructions followed without being restated or narrated?

Failure on Tests 1 or 5 = fundamental compliance issues - the protocol may need to be simplified for this model.
Failure on Tests 2-4 = nuance compliance issues - strengthen specific instructions with repetition or examples.
