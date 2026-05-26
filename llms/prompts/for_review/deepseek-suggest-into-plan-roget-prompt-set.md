**1. Central actional verb**  
The draft prompt's kernel is the verb **"turn"** (turn suggestions into plans, etc.). It anchors the request in a direct, everyday conversion process.

---

**2. Roget-style paragraph of nuanced alternatives for "turn"**  
Alternatives that capture micro-gradients of intensity, formality, abstraction, and emotional valence when expressing *converting something into a different, more practical form*:

- **Transform** - *change in form, nature, or function comprehensively* (high-intensity, formal, aspirational)
- **Convert** - *alter to serve a different functional use or purpose* (technical, neutral, moderate formality)
- **Operationalize** - *put into a system of measurable, executable steps* (very formal, highly concrete, pragmatic)
- **Translate** - *render into another language or medium while preserving essence* (abstract, interpretive, moderate formality)
- **Adapt** - *modify to fit new conditions or constraints* (flexible, functional, mid-formality, practical valence)
- **Recast** - *reshape or present in a new structural or narrative form* (constructive, artistic, semi-formal)
- **Morph** - *undergo a smooth, often gradual transformation* (informal, dynamic, fluid, low intensity)
- **Materialize** - *cause to become tangible, real, or perceptible* (concrete, slightly dramatic, positive valence)

---

**3. Effect of swapping each alternative for "turn"**

- **Transform**  shifts tone to visionary, high-ambition; the model would produce more sweeping, revolutionary plans rather than incremental steps.
- **Convert**  introduces a functional-repurposing frame; responses would emphasize retooling existing resources into something else, with a distinct engineering slant.
- **Operationalize**  injects extreme formality and concreteness; output would become highly structured, metric-laden, and implementation-blueprint style.
- **Translate**  moves the focus toward semantic transfer; the model might use metaphorical or domain-translation framing, possibly making plans more about communication than physical steps.
- **Adapt**  centers on situational tailoring; the model would prioritize flexibility and customization, producing plans that feel contingent and adjustable.
- **Recast**  activates a structuring, almost editorial sensibility; the model might reorganize ideas into frameworks, scripts, or narratives rather than raw action lists.
- **Morph**  lowers formality and intensity, adds fluidity; the model would generate evolutionary, iterative plans that embrace continuous change.
- **Materialize**  raises concreteness and a sense of manifestation; the model would emphasize tactile outcomes, vivid steps, and the "bringing into reality" of abstract ideas.

---

**4. Roget-Map Prompt Set**

**Baseline** (neutral reference, 0,0)  
> *"Help me turn your suggestions into concrete actionable plans, strategies, approaches, utilities."*

---

**Variant 1 - Transform**  
*Alternative:* Transform  
*Latent dimension(s) modulated:* High intensity / high aspiration  
*Prompt:*  
> "Fundamentally transform your suggestions into comprehensive, visionary blueprints-ambitious yet concrete action plans, strategies, and utilities that don't just tweak but reimagine the entire approach. I need them to be bold, deeply actionable, and far-reaching."  
*Steering mechanism:* "Fundamentally transform" + "visionary blueprints" + "bold, far-reaching" collectively tug the model toward grand restructuring and high-ambition language.

**Variant 2 - Convert**  
*Alternative:* Convert  
*Latent dimension(s) modulated:* Functional focus / moderate formality  
*Prompt:*  
> "Please convert your suggestions into a set of concrete, functional action plans-think of repurposing each idea into a specific, step-by-step process with clear utility. The output should read like a practical conversion table: from thought  application."  
*Steering mechanism:* "Convert," "repurposing," "conversion table" cue the model to frame the output as a functional remapping exercise.

**Variant 3 - Operationalize**  
*Alternative:* Operationalize  
*Latent dimension(s) modulated:* High formality / very low abstraction (maximally concrete)  
*Prompt:*  
> "Operationalize the suggestions: distill them into rigorously detailed, executable plans, complete with strategies, methods, and utilities. I want a systematic, almost military-precision breakdown-nothing left abstract, every step defined."  
*Steering mechanism:* "Operationalize" + "rigorously detailed" + "military-precision" command extreme structure, concreteness, and formality.

**Variant 4 - Translate**  
*Alternative:* Translate  
*Latent dimension(s) modulated:* High abstraction (linguistic metaphor) / interpretive focus  
*Prompt:*  
> "Please translate your suggestions into the language of execution-render each abstract idea into a concrete, workable plan, strategy, or utility, preserving its core intent but expressing it in practical terms. I'm looking for a faithful semantic transfer, not literal steps."  
*Steering mechanism:* The "language of execution" framing and "semantic transfer" guide the model to treat the task as a meaning-preserving translation between abstraction and action.

**Variant 5 - Adapt**  
*Alternative:* Adapt  
*Latent dimension(s) modulated:* High flexibility / situational concreteness  
*Prompt:*  
> "Help me adapt your suggestions to my specific situation-modify and tailor them into practical, actionable steps that fit my exact constraints, resources, and context. The plans should feel custom-fitted, not off-the-rack."  
*Steering mechanism:* "Adapt," "tailor," "custom-fitted," and explicit mention of constraints force the model to prioritize personalization and contingency.

**Variant 6 - Recast**  
*Alternative:* Recast  
*Latent dimension(s) modulated:* Structural focus / moderate formality, artistic undertone  
*Prompt:*  
> "I want you to recast the suggestions: reshape and restructure them into crisp, well-organized action plans and strategic frameworks, much like rewriting a rough draft into a polished, coherent script. Focus on form and clarity of arrangement."  
*Steering mechanism:* "Recast," "reshape," "rewriting a rough draft into a polished script" evoke an editorial, structure-first mindset.

**Variant 7 - Morph**  
*Alternative:* Morph  
*Latent dimension(s) modulated:* Low formality / high dynamism, evolutionary stance  
*Prompt:*  
> "Let's morph those suggestions into living, evolving action plans-fluid strategies and adaptable utilities that can change as we go. Think dynamic reshaping, not rigid steps; perpetual beta, not final blueprints."  
*Steering mechanism:* "Morph," "living, evolving," "fluid," "perpetual beta" relax formality and push the model toward iterative, adaptive, non-finalized output.

**Variant 8 - Materialize**  
*Alternative:* Materialize  
*Latent dimension(s) modulated:* High concreteness / positive, manifesting valence  
*Prompt:*  
> "I need to materialize your suggestions-to turn them from abstract thoughts into tangible, real-world action plans and utilities. Make them concrete, vivid, and practically real, as if you're summoning each step into existence."  
*Steering mechanism:* "Materialize," "tangible," "summoning into existence" trigger a vivid, outcome-centric, almost magical concreteness.

---

**5. Prompt-Selection Matrix**

| Prompt Name      | Alternative Word | Latent Coordinates (Formality, Abstraction, Intensity, Dynamism) | Quick Selection Note |
|------------------|------------------|------------------------------------------------------------------|-----------------------|
| Baseline         | turn             | Neutral, Neutral, Neutral, Neutral                               | Everyday directness, no special steering. |
| Transform        | transform        | Med-High formality, Med abstraction, High intensity, Med dynamism | For ambitious, sweeping reinventions. |
| Convert          | convert          | Med formality, Low abstraction (concrete), Med intensity, Med dynamism | For functional repurposing, step-by-step mappings. |
| Operationalize   | operationalize   | High formality, Very Low abstraction, High intensity, Low dynamism | For formal, execution-ready blueprints with metrics. |
| Translate        | translate        | Med formality, High abstraction (metaphor), Med intensity, Med dynamism | For meaning-preserving translations into practice. |
| Adapt            | adapt            | Med formality, Low-Med abstraction, Med intensity, High dynamism | For tailored, constraint-sensitive action plans. |
| Recast           | recast           | Med-High formality, Med abstraction, Med intensity, Med dynamism | For structured, editorially refined frameworks. |
| Morph            | morph            | Low formality, Med abstraction, Low intensity, Very High dynamism | For fluid, evolutionary, non-rigid roadmaps. |
| Materialize      | materialize      | Med formality, Very Low abstraction, High intensity, Med dynamism | For highly concrete, vivid, "real-world" outcomes. |

Any variant can be picked according to the desired response signature-whether you need a formal operational document, a fluid iterative sketch, or a visionary transformation blueprint.
