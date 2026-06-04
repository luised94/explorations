Generate a state handoff document for the current conversation. The document enables a fresh thread to continue this work without the original conversation history. A model reading only the handoff document and attached artifacts must be able to proceed as if it had full context.

Capture necessary and sufficient state. This is not a transcript, not a summary, and not a recap. It is the minimum information required to continue - and nothing more.

<structure>

## 1. GOVERNING CONSTRAINTS
State the foundational commitments, worldview, or principles that governed decisions throughout the conversation. These prevent a fresh model from reverting to defaults that contradict established direction. Include only principles that were actively applied - not aspirational rules that were stated but never enforced.

## 2. PROJECT ARC
Compress the conversation's progression into named phases. Each phase: one sentence stating what was done and one stating what it produced. Preserve sequence - which phase led to which - because causation matters. Discard the conversational back-and-forth within each phase.

## 3. DECISIONS AND REJECTIONS
Two tables.

**Decisions table:** What was decided and why. Include only decisions that constrain future work. Omit decisions that were intermediate and later superseded.

**Rejections table:** What was considered and rejected, with rationale. This is the highest-value section. A fresh model given only the artifacts will naturally find good paths; without the rejection log, that same model will re-explore dead paths. Every entry must state the rejected approach AND the specific reason it failed, so the fresh model can evaluate whether the reason still applies under changed circumstances.

## 4. EMPIRICAL RESULTS
Summarize any tests, experiments, or observations that produced findings. State the finding and its implication for the work. Exclude raw data - compress to conclusions. If the raw data is needed, note that it should be attached separately.

## 5. ARTIFACT INVENTORY
Table: artifact name, purpose, status (complete/draft/untested/superseded). Do not inline artifact content - the user attaches artifacts separately. The handoff document captures why each artifact exists, what state it is in, and how artifacts relate to each other.

## 6. ACTIVE METHODOLOGY
If the conversation developed or adopted a methodology, compress it to its operative principles. One line per principle. The full methodology lives in its own artifact if one exists; this section is a quick-reference index, not a reproduction.

## 7. ACTIVE STYLE OR FORMAT RULES
If style or formatting rules were established, list them. These are easy to lose across threads and expensive to re-derive.

## 8. OPEN THREADS
List unfinished work, untested claims, and explicitly deferred decisions. Each entry: what remains, why it matters, and what would constitute completion. These give the user a menu for the fresh thread - "continue from thread N" orients the entire conversation with one line.

## 9. USAGE INSTRUCTIONS
State how to use the handoff document. Map combinations of attached artifacts to types of continued work. Make the document self-documenting - the receiving model should not need the user to explain what the handoff document is or how to use the attachments.

</structure>

<principles>

**Necessary and sufficient.** Include decision rationale; exclude the deliberation process that produced decisions. Include what was rejected; exclude the exploratory discussion that preceded rejection. Include findings; exclude the raw data unless noting it should be attached.

**Anti-re-exploration.** Rejections with rationale outweigh decisions in handoff value. A fresh model will find good paths through the artifacts themselves. Without the rejection log, that model will spend tokens rediscovering paths already proven dead.

**Temporal compression.** Preserve phase sequence (what led to what). Discard turn-by-turn conversation structure. Sequence encodes causation; turn structure encodes only chronology.

**Exclusion is content.** State what was excluded from the handoff and why. A receiving model that detects missing information will either hallucinate it or ask for it. Stating the exclusion and its rationale prevents both failure modes.

**Self-documenting.** The handoff document explains its own structure and usage. The receiving model reads the document cold; no external instructions should be required.

**Actionable orientation.** Open threads are phrased as completable tasks, not vague observations. "Test the lean prompt on two models using the five-case suite" - not "further testing may be warranted."

</principles>

<rules>

- Write for a model with zero prior context. Every term, acronym, and reference must be defined or self-evident on first use.
- Apply COMPILE mode: inline all definitions and context. Reference nothing external to the document except artifacts noted in the inventory.
- Apply active style rules from the conversation (Section 7) to the handoff document itself.
- Omit needless words. Every section earns its inclusion through function. If a section would be empty, omit the section.
- Do not reproduce artifact content. State purpose, status, and relationships. The user attaches artifacts separately.
- Flag any section where the handoff compresses away information the fresh model might plausibly need: `[COMPRESSED: what was omitted and where to find it if needed]`.

</rules>
