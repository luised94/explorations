# THREAD CLOSE-OUT - Locate, Copy, and Reorganize Reusable Content

You are given a full conversation transcript. Read every turn. Produce a structured output containing only content that meets the criteria below. The test for inclusion: could the content be applied in a different conversation or project without modification, or with only input-substitution? If not, exclude it.

A second inclusion test: could this content be reproduced by sending only the first user message to a new LLM instance? If yes, exclude it - it is a product of the topic, not of this conversation's specific trajectory. Only include content that required the sequence of turns, corrections, and refinements that occurred.

---

## 1. CONVERSATION DESCRIPTION

Write 3-5 sentences. State: (a) what the opening input was, (b) what sequence of operations the conversation performed on it (e.g., "the user requested a rewrite, then asked for measurement criteria, then shifted domain to pedagogy"), and (c) what the final state of the output is - what exists at the end that didn't exist at the start. Write for someone scanning a list of saved conversations who needs to decide in 10 seconds whether this one contains what they're looking for.

## 2. PROCEDURES AND DECISION RULES

Scan each turn for any content that has the structure: "given input X, perform steps 1-N, producing output Y." This includes named methods, pipelines, rubrics, evaluation criteria, and conditional rules (if A, then do B).

For each one found:

- **Label**: A short noun phrase describing the function (e.g., "three-stage abstraction pipeline," "vacuity detection via failed concretization").
- **Input**: What goes in. Specify the format (text passage, code, dataset, etc.).
- **Steps**: Numbered list. Each step describes one operation: what it takes as input, what transformation it performs, and what it outputs. No metaphors - describe the operation on the data, not a figurative version of it.
- **Output**: What comes out. Specify the format.
- **Turn of origin**: Which conversation turn this appeared or reached its final form in. If it was revised across turns, note the initial and final turns.
- **Was it executed in-conversation?**: Yes (it was applied to actual input and produced actual output) or No (it was described but not demonstrated). Flag which.

## 3. STANDALONE INSTRUCTION BLOCKS

For the three most generally applicable procedures from Section 2, write a self-contained instruction block that could be pasted into a new conversation with no additional context. Each block must:

- Begin with a one-sentence description of what it does
- Contain all steps needed to execute it
- Include a clearly marked input placeholder: `[PASTE INPUT HERE]`
- Specify what form the output should take
- Contain no references to this conversation, its participants, or its context

## 4. USER MOVES THAT ALTERED TRAJECTORY

Read the user's messages in sequence. Identify each point where the user's input caused the assistant's subsequent output to differ substantially from what a default continuation would have produced. "Default continuation" means: if the user had said "continue," "tell me more," or asked a surface-level follow-up, the output would have gone in direction A; instead, the user's actual input sent it in direction B.

For each such point:

- **What the user wrote**: Quote or closely paraphrase the relevant portion of the user's message.
- **What changed**: Describe the difference between the likely default continuation and what actually resulted.
- **The generalizable move**: Restate the user's action as a one-sentence instruction that someone could apply in a different conversation. Format: "When [condition], do [action], which produces [effect]."

Exclude trivial redirections (e.g., "now do it for a different example"). Only include moves where the conversation's direction, depth, or quality changed.

## 5. CLAIMS THAT CHALLENGE DEFAULTS

Locate statements in the conversation (from either participant) that contradict a commonly held assumption or a standard practice. For each:

- **The claim**: State it in one sentence, plainly.
- **What it contradicts**: Name the default assumption or common practice it opposes.
- **What support exists in-conversation**: Was it argued for, demonstrated, tested, or merely asserted? State which.

Maximum 7 entries. If fewer than 3 qualify, state that the conversation did not produce strongly non-obvious claims.

## 6. UNFINISHED PATHS

Identify any topic, question, or direction that was raised in the conversation but not followed to completion. For each:

- **What was raised**: One sentence.
- **Where it was dropped**: Which turn.
- **What following it would involve**: A concrete next step - not "explore further" but a specific question to ask, artifact to build, or test to run.

## 7. INDEX BLOCK

```
title: [Noun phrase summarizing what was built, not what was discussed]
date: [Conversation date]
domains: [1-3 fields this applies to]
keywords: [5-10 terms, lowercase_underscored, optimized for search: 
           include both the specific topic and the general category]
prior_threads: [IDs or titles of earlier conversations this extends, 
               or "none"]
next_steps: [1-2 concrete actions this conversation points toward]
maturity: [asserted | demonstrated_on_example | tested_against_external_frameworks]
```

---

## EXECUTION CONSTRAINTS

- Every item in Sections 2-6 must be traceable to a specific turn in the conversation. If you cannot point to where it appeared, do not include it.
- Do not introduce content from outside the conversation. If a relevant framework or reference was not mentioned in the thread, it does not belong in the archive.
- If a procedure or claim was revised during the conversation (the user pushed back, the assistant corrected), include only the final version in Sections 2-3. In Section 4, describe the revision trajectory - what changed and what user move caused the change.
- If the conversation was routine - no novel procedures, no trajectory-altering moves, no non-obvious claims - produce only Sections 1 and 7, and state in Section 1 that the thread contained no content meeting the extraction criteria. Do not pad.
---
# THREAD ARCHIVE - Extract & Preserve

You are closing out a conversation thread. Your job is to harvest everything reusable, novel, or worth preserving before this thread goes cold. Be ruthless about signal - skip anything generic, obvious, or reproducible from the opening message alone. Prioritize what *only exists because this specific conversation happened*.

---

## 1. THREAD SUMMARY (3-5 sentences max)

What was this conversation about, what was built, and why does it matter? Write this for someone skimming an archive six months from now. Front-load the novel contribution - not the topic, but what was *produced* that's new.

## 2. CORE ARTIFACTS

Extract every method, framework, pipeline, taxonomy, or structured idea that emerged. For each:

- **Name**: Short, descriptive, searchable.
- **What it does**: 1-2 sentences.
- **The procedure**: Numbered steps. Concrete enough that someone who wasn't in this conversation can execute it.
- **Came from turn(s)**: Where in the conversation it appeared or matured.

Only include artifacts that were *demonstrated or stress-tested* in the conversation, not just mentioned in passing.

## 3. REUSABLE PROMPTS

Extract or generate standalone, copy-pasteable prompts for the most valuable operations that emerged. Each prompt should:
- Work without any context from this conversation
- Include clear input placeholders
- Specify the expected output format
- Be immediately usable by pasting into a new thread

Label each with a short functional name (e.g., "Vacuity Test," "Perspective Stress Test").

## 4. STRATEGIES THAT WORKED

Identify the user's most effective conversational moves - things they did that changed the trajectory, depth, or quality of the conversation. For each:

- **The move**: What they did (quote or paraphrase).
- **Why it worked**: What it produced that a default interaction wouldn't have.
- **Reusable as**: A one-line instruction someone could apply in future conversations.

Skip generic strategies ("asked a follow-up question"). Only include moves that were *specific, non-obvious, and demonstrably effective* in this thread.

## 5. KEY INSIGHTS

List the sharpest, most non-obvious ideas that emerged - things you'd want to remember or cite later. For each:

- **The insight**: One sentence, plainly stated.
- **Why it's non-obvious**: What conventional assumption it challenges or what it makes visible that's normally hidden.

Cap at 5-7. If you're padding, you have too many.

## 6. OPEN THREADS

What was left unfinished, gestured at but not developed, or surfaced as a promising direction that the conversation didn't pursue? These are starting points for future threads.

## 7. ARCHIVE TAGS

```
Title: [Descriptive title for retrieval]
Date: [Date of conversation]
Domain: [Primary domain(s)]
Keywords: [5-10 searchable terms, lowercase, underscored]
Builds on: [Any prior threads this extends, or "none"]
Could feed into: [Topics or projects this connects to]
Confidence: [How stress-tested are the core artifacts? 
             raw_idea | demonstrated | tested_against_frameworks]
```

---

## EXECUTION RULES

- Extract from the *conversation*, not from background knowledge. If it wasn't said, built, or demonstrated in this thread, it doesn't go in the archive.
- Trace evolution. If an idea was refined across turns (user pushed back, assistant revised), extract the *mature version* - but note what changed and why, because the trajectory is often as valuable as the endpoint.
- Distinguish between what the *user* contributed and what the *assistant* contributed. The user's framings, challenges, and redirections are often the most valuable and least obvious elements.
- Be concise. This is an archive entry, not a paper. Someone should be able to scan it in 2 minutes and find what they need.
- If the conversation was mid-quality - routine Q&A, no novel artifacts, no interesting strategies - say so in the summary and keep the archive minimal. Not every thread deserves a full extraction.
