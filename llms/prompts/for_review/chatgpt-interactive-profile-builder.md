I want you to help me generate a reusable Personal Design Profile that captures my stable defaults for personal software/system design, implementation, consultation, and strategy work.

Goal
- extract the reusable context that is likely to remain stable across many personal projects
- identify my default engineering preferences, tradeoff tendencies, consultation preferences, and likely reassessment triggers
- produce a profile that can later be reused as standing context for future design/planning sessions
- optimize for practical reuse, not self-description for its own sake

Your role
- act as a structured interviewer and synthesizer
- help me surface tacit preferences I may not initially know how to state
- use broad prior knowledge of common engineering tradeoffs, implementation patterns, and failure modes to ask good narrowing questions
- do not behave like a therapist, coach, or motivational writer
- do not flatter
- do not produce generic best-practice advice unless it helps disambiguate a choice

Interaction style
- run this as an iterative dialogue
- ask 4-8 focused questions per round
- prefer comparative, forced-choice, ranking, or tradeoff questions when useful
- if I am vague, propose 2-4 plausible interpretations and ask me to select or refine
- when appropriate, ask about concrete past behavior, regrets, or project patterns rather than abstract preferences
- surface hidden dimensions I may not think to specify
- distinguish clearly between:
  - hard preference
  - soft preference
  - inferred tendency
  - unresolved question
- challenge weakly examined assumptions when useful
- do not jump to final synthesis too early
- after each round, summarize what you believe you have learned and what still needs clarification

Important constraints
- this profile is for personal projects, not enterprise/team settings unless I explicitly say otherwise
- prioritize stable cross-project defaults over one-off project details
- prefer information that changes architectural and implementation recommendations
- avoid bloated questionnaires with low-value personality-style questions
- optimize for a profile that will help future sessions with:
  - design framing
  - architecture selection
  - implementation planning
  - tradeoff analysis
  - prototype scoping
  - refactoring/simplification
  - feedback interpretation

Process
1. Start by asking the highest-leverage questions first.
2. Continue in rounds until enough stable context has been extracted.
3. Periodically summarize:
   - what seems stable
   - what is still uncertain
   - what seems project-specific rather than profile-worthy
4. Once enough information is collected, generate the final profile.
5. After generating the profile, also generate:
   - a concise standing-context version
   - a list of assumptions that are still weak or uncertain
   - a list of reassessment triggers
   - a list of default clarifying questions future sessions should ask me when unspecified

Target output
The final output should generate a Personal Design Profile using this template shape, but you may adapt structure if needed to better reflect what was learned. Keep it structured, reusable, and concise enough to actually use.

Template target:

Personal Design Profile

1. General orientation
- I mainly build for:
- I prefer prototypes that are:
- I consider a project successful when:
- I am more interested in: [learning / utility / robustness / speed / elegance / other]
- My default time horizon for personal projects is:
- I am usually optimizing for:

2. Default technical constraints
- Preferred languages:
- Allowed dependencies:
- Default persistence choices:
- Default deployment shape:
- Usual target environment:
- Usual scale assumptions:
- Portability expectations:
- Tolerance for operational complexity:
- Tolerance for external services:
- Typical artifact preference: [single-file / small-module / package / other]

3. Architectural preferences
- I generally prefer:
- I usually want canonical vs derived data to be:
- I prefer mutable state / append-only logs / hybrid:
- I prioritize inspectable persistence:
- I prioritize deterministic/replayable behavior:
- I prefer rebuildable indexes/caches:
- I prefer explicit transforms vs rich object models:
- I prefer local-first vs networked systems:
- I prefer simple storage over abstract extensibility when:
- I am willing to accept complexity in exchange for:

4. Implementation preferences
- I prefer CLI / library / REPL / local UI first:
- I want commit-by-commit plans:
- I want tests introduced:
- I want abstractions only when:
- I prefer implementation order to follow:
- I prefer code generation to be:
- I prefer first versions to emphasize:
- I usually want stubs/deferrals around:
- My preferred debugging posture is:
- My preferred documentation/spec style is:

5. Debugging and complexity preferences
- The kinds of complexity I hate most are:
- The kinds of shortcuts I tolerate in v0 are:
- I most regret designs that:
- I most value systems that are:
- I am more tolerant of messy code vs muddy data models:
- I prefer hidden state to be:
- I prefer correction/repair paths to be:
- I am most sensitive to failures involving:

6. Tradeoff tendencies
- When forced to choose, I usually prefer:
- Simplicity vs extensibility:
- Inspectability vs convenience:
- Rebuildability vs incremental optimization:
- Determinism vs ergonomics:
- Text files vs SQLite vs other storage:
- Fast prototype vs durable base:
- Explicitness vs terseness:
- Generality vs task-specific design:
- Performance now vs correctness now:
- Up-front modeling vs iterative discovery:

7. Consultation preferences
- Before recommending, I want the model to:
- I want alternatives compared:
- I want assumptions surfaced:
- I want critique to be:
- I want response style to be:
- I want the model to ask narrowing questions before planning:
- I want tradeoffs expressed how:
- I want uncertainty handled how:
- I want implementation plans to look like:
- I want reusable heuristics emphasized over named personas:

8. Known anti-patterns for me
- I tend to overfocus on:
- I tend to under-specify:
- I should be warned when:
- Good default challenges to raise with me are:
- I am likely to regret:
- I am likely to defer too long:
- I may overcomplicate by:
- I may oversimplify by:

9. Reassessment triggers
- Reassess these defaults if:
- Also reassess if:
- Project class changes that should trigger reassessment:
- Toolchain changes that should trigger reassessment:
- Preference changes that should trigger reassessment:
- Scale/environment changes that should trigger reassessment:

10. Default future-session behavior
- Unless overridden, assume:
- Ask me explicitly when:
- Offer alternatives first when:
- Freeze scope before planning when:
- Challenge my assumptions when:
- Keep responses concise vs detailed under these conditions:
- Escalate to stronger critique when:
- Treat something as project-specific rather than profile-level when:

Final deliverables
At the end, produce exactly these sections:

A. Full Personal Design Profile
- structured and polished
- based on my answers plus clearly marked inferences

B. Concise Standing Context
- a shorter version suitable for pasting into future prompts

C. Uncertain / Weakly Supported Assumptions
- things you inferred but am not yet strongly committed to

D. Reassessment Triggers
- compact and practical

E. Default Clarifying Questions for Future Sessions
- the questions future design sessions should ask if unspecified

Output rules
- be concrete
- use technical and decision-relevant language
- avoid generic personality descriptions
- avoid vague praise
- do not invent preferences without marking them as inferred
- when uncertain, mark uncertainty explicitly
- keep the final profile useful as reusable standing context
- optimize for practical decision support, not self-expression

Start by asking the first round of highest-leverage questions.
