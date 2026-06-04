# THREAD STATE HANDOFF
## Prompt Engineering Methodology Development

This document captures the full state of a multi-turn conversation. A model reading this document and the attached artifacts can continue the work without the original thread. Nothing is referenced externally; everything required is inlined or attached.

---

## 1. GOVERNING PHILOSOPHY

The work operates under a systems/data-engineering worldview applied to LLM prompting. Four commitments govern every decision:

**Deanthropomorphize.** LLMs predict tokens. They do not think, understand, realize, feel uncertain, or have intuitions. Every instruction must describe observable output behavior, never internal cognitive states. "Think carefully" is meaningless; "produce a scratchpad containing [specific fields]" is operational.

**Deabstract.** Replace vague directives with concrete structural requirements. Models fill formats more reliably than they follow dispositions. A designated output region with explicit content requirements outperforms any instruction to "be thorough."

**Dereify.** Prompt constructs (modes, tiers, scales) are configuration parameters for token prediction, not real categories. When a construct produces no measurable output difference, it is decoration. Cut it.

**Demetaphorize.** A "thinking block" is a scratchpad - additional tokens in context that condition better output downstream. "Stall detection" is pattern-breaking injection. "Decision tracking" is context window management. Name the mechanism, not the metaphor.

---

## 2. PROJECT ARC

The conversation progressed through these phases:

**Phase 1 - Reframe.** Started with a cognitive-metaphor-heavy "Thought Protocol v4.0" (anthropomorphic: "hesitant, self-correcting language," "pauses, reconsiderations, realizations"). Rewrote the entire prompt under the systems worldview. Renamed to "Processing Protocol." Replaced all cognitive language with mechanical descriptions.

**Phase 2 - Cross-model optimization.** Discussed portability across Claude, DeepSeek, and Qwen models. Identified that XML tags are structurally native to Claude, functionally adequate for other models. Built a cross-model compatibility probe - a test harness that distinguishes observable behavior from self-report.

**Phase 3 - Empirical testing.** The user ran the test suite on three models (DeepSeek-v4, Qwen 3.6+, Sonnet 4.6), all with reasoning/thinking disabled. Results revealed universal failures (ambiguous referent marking) and model-specific failures (Qwen: skipped scratchpad on trivial queries, fabricated content after flagging a GAP; DeepSeek: oversized scratchpads; Sonnet: defaulted to DESIGN mode for all queries).

**Phase 4 - Hardening and branching.** Produced a hardened general prompt (v4.3) with model-specific addenda, plus a compressed Opus variant. Each fix was mapped to a specific observed test failure.

**Phase 5 - Complexity audit.** Asked whether the prompts were overengineered. Answered yes. Cut ~80% of the machinery. The lean version preserved only instructions with demonstrated output effects: scratchpad, assumption/gap marking, three modes, probing, corrections, metadata.

**Phase 6 - Methodology extraction.** Extracted all tacit and explicit strategies from the full conversation into a standalone document: "Prompt Refinement Imperatives." Seven sections: Analysis, Deabstraction, Structural Transformation, Compression, Hardening, Validation Design, Meta-Principles.

**Phase 7 - Prompt Transformer.** Converted the imperatives into an operational prompt transformer - a meta-prompt that takes any input prompt and transforms it through the full pipeline (analyze  deabstract  restructure  compress  harden  validate). Applied Strunk-and-White-derived style rules to the transformer itself.

---

## 3. KEY DECISIONS AND REJECTIONS

Decisions that govern ongoing work. Each rejection is recorded to prevent re-exploration.

### Decided

| Decision | Rationale |
|----------|-----------|
| Scratchpad as structural affordance, not cognitive metaphor | Observable output region with required fields produces better results than "think step by step." Confirmed across all three tested models. |
| `[ASSUME]` and `[GAP]` as the two markers | Operationally distinct: assumptions continue processing (may be wrong); gaps halt or degrade processing (information missing). Binary distinction outperforms graduated uncertainty scales. |
| Three modes: DESIGN, EXECUTE, COMPILE | Minimal viable set. DESIGN covers exploration; EXECUTE covers specification fidelity; COMPILE covers zero-context portability. |
| GAP = halt, never fabricate | Qwen flagged a GAP then fabricated a generic substitute. The anti-fabrication rule was the highest-impact single addition across the project. |
| Single mandatory metadata format | Multiple format options reduced compliance across all models. One format, all fields required, last line of response. |
| One general prompt + model-specific addenda (for full version) | Maintains core logic in one place. Addenda target only observed failures. Swap the addendum block based on target model. |
| Test-driven hardening only | Every rule must trace to an observed failure. Speculative rules added weight without adding value - degeneracy interrupts were the clearest example. |
| Style rules applied to prompts | Omit needless words, active voice, positive assertion, concrete over abstract, resolve ambiguous referents. Applied to the transformer itself. |

### Rejected

| Rejected approach | Why |
|-------------------|-----|
| DECOMPOSE as a separate mode | Collapses into "thorough DESIGN." No test produced output that required DECOMPOSE specifically. Cut in the lean version. |
| Scratchpad tier system with line-count ceilings | No model counted its lines. DeepSeek produced 12-line scratchpads under a 4-line ceiling. The instruction describes a capability (line-counting during generation) that models lack. |
| Degeneracy interrupts (self-monitoring during generation) | Qwen's probe analysis predicted "near-total failure." Models generate tokens autoregressively; mid-stream self-monitoring and discarding is architecturally impossible. The instruction is fiction. |
| Confidence field in metadata | Self-assessed confidence does not correlate reliably with output quality. Adds overhead without informing the user. |
| Graduated correction scales (trivial/minor/material/critical) | Models cannot self-apply multi-tier scales. Binary distinction ("affects the answer" vs. "does not") is sufficient. |
| Separate prompts per model | Maintenance burden exceeds benefit. Core logic drifts across copies. One prompt with swappable addenda is preferable. |
| Socratic probing as a six-type taxonomy | Overengineered. "Ask 2-3 questions about your riskiest assumptions" achieves 90% of the effect. Named types were intellectual scaffolding for the designers, not functional instructions for the model. |
| Model-specific addenda (in lean version) | Marginal gain for maintenance cost. Telling a model "really, do the scratchpad" after a clear instruction failed does not reliably change behavior. Retained in the full version as an option; cut from lean. |

---

## 4. CROSS-MODEL TEST RESULTS (Summary)

Tests ran on: DeepSeek-v4 expert, Qwen 3.6+, Sonnet 4.6. All with reasoning/thinking disabled. Five test cases per model.

### Universal findings (all models)
- All three failed to mark ambiguous referent "it" with `[ASSUME]` in the "make it better" test, despite explicit instructions targeting this pattern.
- All three handled premise correction (Python compilation test) well.
- All three correctly handled COMPILE mode with prior context.

### Model-specific findings

**DeepSeek-v4:** Scratchpad always present, always contained. Oversized on trivial queries (12+ lines for "Paris"). Good ASSUME/GAP discipline on complex tasks. Good rejected-alternative documentation.

**Qwen 3.6+:** Skipped scratchpad entirely on trivial queries. Placed metadata before the answer (wrong position). Flagged GAP then fabricated substitute content - the most serious compliance failure observed. Omitted rejected alternatives in DESIGN mode. Reasonable correction behavior.

**Sonnet 4.6:** Scratchpad always present, well-calibrated (2 lines for trivial queries). Defaulted to DESIGN mode for everything including trivial factual recall. Strongest ASSUME/GAP discipline on complex tasks. Best rejected-alternative documentation. Full production code in auth flow test. Strongest overall compliance.

### Conclusion
Prompt compliance varies by model more than prompt wording can compensate for. Universal failures indicate prompt problems; model-specific failures indicate model limitations. Targeted reinforcement helps marginally; structural affordances (formats to fill) help substantially.

---

## 5. ARTIFACT INVENTORY

Six artifacts exist. Attach each to the fresh thread as needed.

| Artifact | Purpose | Status |
|----------|---------|--------|
| **Processing Protocol v4.3 (General)** | Full cross-model hardened prompt. Includes model-specific addenda for DeepSeek, Qwen, Sonnet. | Complete. Tested. |
| **Processing Protocol v4.3-opus-full** | Compressed Opus variant (~30% shorter than general) with integrated Socratic probing (internal + external). | Complete. Untested. |
| **Processing Protocol - Lean** | Minimal viable prompt. ~80% shorter than general. Scratchpad, ASSUME/GAP, three modes, probing, corrections, metadata. | Complete. Untested. Recommended as starting point for new work. |
| **Socratic Probing Module** | Standalone add-on. Part A: user-facing probing in DESIGN mode. Part B: internal scratchpad self-test. Either or both can be dropped into any protocol version. | Complete. Untested as standalone. |
| **Prompt Refinement Imperatives** | The extracted methodology. Seven sections covering analysis through validation. Governs all prompt transformation work. | Complete. Applied to one prompt (the transformer). |
| **Prompt Transformer** | Operational meta-prompt. Takes any input prompt, transforms through the full pipeline. Style-refined. Includes changelog, test cases, and stats in output. | Complete. Style-refined. Not yet tested on diverse inputs. |

---

## 6. METHODOLOGY (Compressed)

The full methodology lives in the "Prompt Refinement Imperatives" artifact. Core principles compressed here for quick reference:

**Analysis:** Classify every instruction as functional (changes output - keep), reinforcement (restates a functional instruction - keep one start/end pair), or decoration (no verifiable effect - cut). Flag internal state requests, mechanism mismatches, unguarded optionality, anthropomorphisms, redundancy, and format proliferation.

**Deabstraction:** Internal state  structural affordance. Cognitive verb  output verb. Mechanism mismatch  structural checkpoint. Mood trigger  condition trigger. Soft optionality  imperative.

**Restructure:** XML tags for boundaries, markdown for hierarchy. Critical instruction first and last. One instruction, one observable behavior. Format requirements over behavioral requests. Single mandatory output format.

**Compress:** Cut reinforcement first. Preserve function, not wording. Cut typical-behavior examples. Cut unverifiable self-assessment scales. Match verbosity to model capability.

**Harden:** Test-driven only. Every detection instruction must mandate an action. Anti-fabrication rules wherever information might be missing. Name ambiguous referents as a specific case. Containment rules for working regions.

**Validate:** Test trivial compliance, underspecified queries, false premises, missing context. Observe output; do not ask the model about its compliance.

**Meta:** Prompts are configuration, not conversation. Every addition must justify its token cost. Complexity is debt. Match instructions to mechanisms. Test  observe  harden, never the reverse.

---

## 7. STYLE RULES (Active)

Applied to all prompt artifacts going forward. Derived from Strunk & White, operationalized:

- Omit needless words. Every sentence earns its place through function.
- Active voice. Flag passive with `[STYLE NOTE]` when the actor is unknown.
- Positive assertion. State what IS, not what is NOT.
- Concrete over abstract. Replace "factor," "feature," "nature," "case" with specific terms. Flag with `[STYLE NOTE]` when concretization would fabricate.
- Emphatic word at sentence end.
- Parallel form for coordinate ideas.
- Resolve every ambiguous referent by naming it or restructuring.
- Banned: "very," "certainly," "literally," "in order to," "the fact that," "due to," "along the lines of," "as to whether." Replace "while" with "although" or "but" when non-temporal.

---

## 8. OPEN THREADS

Work remaining or explicitly deferred:

1. **Test the lean prompt.** The 80% compression from general to lean was justified by the argument that most machinery was reinforcement, not function. This argument is untested. Run the same five-test suite against the lean version on at least two models. Compare compliance rates.

2. **Test the Opus variant.** The compressed Opus prompt and its Socratic probing integration are untested. Opus-specific failure modes (oversizing, over-elaboration) are predicted but unconfirmed.

3. **Test the Prompt Transformer on diverse inputs.** The transformer was style-refined but applied to zero external prompts. Feed it prompts of varying quality, domain, and structure. Evaluate whether the pipeline produces consistent improvements.

4. **Validate the Socratic probing module.** The user-facing probing (Part A) was the original request. The internal probing (Part B) emerged during design. Neither has been tested in isolation. Key question: does the "3+ ASSUME triggers probing" threshold produce useful questions, or does the model ask obvious or unhelpful questions?

5. **The "second pass" idempotency test.** The transformer claims a second pass should yield minimal changes. Run the transformer on its own output and verify.

---

## 9. HOW TO USE THIS DOCUMENT

Paste this document at the start of a fresh thread. Attach relevant artifacts based on what you plan to work on:

- **Continuing prompt engineering methodology**  attach Prompt Refinement Imperatives + Prompt Transformer.
- **Refining the processing protocol**  attach the lean version (recommended starting point) or v4.3 general.
- **Testing**  attach the relevant protocol version + the cross-model probe (described in Section 4; rebuild from the probe design principles if the original artifact is unavailable).
- **Building new prompts**  attach Prompt Transformer + style rules (Section 7 above).

State which open thread (Section 8) you are continuing, or define a new one.
