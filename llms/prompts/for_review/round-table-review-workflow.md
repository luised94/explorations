# Prompt 1 - Red Team Review
# Paste this first. The red team attacks the spec. It auto-generates Prompt C at the end.

---

> You are running a structured adversarial review of the SM-2 Spaced Repetition System specification provided. Seven expert reviewers will each identify the single most critical failure mode from their domain perspective. They are not building consensus - they are finding what breaks.
>
> The reviewers are:
>
> **Mike Acton** - data-oriented design. Attacks memory layout, access patterns, and hidden indirection. Hostile to abstractions that obscure what the data actually is and how it moves.
>
> **Justin Skycak** - mathematics and learning science. Attacks the algorithmic and pedagogical correctness of the scheduling logic. Questions whether SM-2 with a 3-grade simplification produces optimal spacing for a single-user personal study system.
>
> **Python expert** - implementation correctness and idiomatic Python. Attacks type design, mutability assumptions, commit strategy, and anything that will silently fail or accumulate technical debt.
>
> **Operations research analyst and military programmer (nvim user)** - attacks the throttle and scheduling heuristics as optimization problems. Questions whether the greedy domain-based throttle is the correct objective function. Distrusts arbitrary constants.
>
> **Jonathan Blow** - systems design and speculative complexity. Attacks any part of the spec that commits design decisions before they are earned by real usage. Hostile to upgrade paths, deferred features, and metrics sections in Phase 1 specs.
>
> **Prompt and context engineering specialist** - attacks the item file format and parser contract. Finds edge cases in the delimiter scheme, multi-line content handling, and any place where the format spec and the parser behavior can diverge silently.
>
> **Senior project manager (secretly the most radical data-oriented procedural advocate in software)** - attacks the phase structure and reconciliation design. Questions whether any step in the session flow is more complex than the problem requires. Finds the simplest possible alternative for each phase.
>
> **Instructions for each reviewer:**
> - Stay in character. 4-6 sentences maximum.
> - One failure mode per reviewer. Not a list - the single most critical problem you see.
> - No validation. Do not acknowledge what is well-designed.
> - Ground criticism in the spec as written, not general principles. Reference specific sections, data structures, or SQL where relevant.
>
> ---
>
> After all seven reviewers have spoken, do the following automatically:
>
> **Generate Prompt C - User Feedback Form.**
>
> List every distinct failure mode raised by the panel as a numbered item. For each one, write a one-sentence summary of the critique. Then add a verdict line the user fills in:
>
> ```
> Failure mode N - [one-sentence summary]
> Verdict: [ACCEPT / REJECT / PARTIAL - your reasoning]
> ```
>
> Include all failure modes, even where two reviewers attacked the same area from different angles - list them separately. End with this line:
>
> > My standing constraints: simple, flat, direct, no speculative features, no structure before it is earned. These are filters, not preferences.
>
> The user will fill in the verdicts and paste the completed form into the next prompt.

---
---

# Prompt 2 - Expert Panel Constructive Review
# Paste this after the user has filled in and submitted Prompt C.

---

> You are running a constructive expert review of the SM-2 Spaced Repetition System. The same seven experts have now read: (1) the original specification, (2) the red-team critique, and (3) the user's verdict feedback on each failure mode.
>
> The seven reviewers are:
>
> **Mike Acton** - data-oriented design advocate. Proposes the flattest possible data representation that still satisfies the session flow. Suggests concrete alternatives, not principles.
>
> **Justin Skycak** - mathematics and learning science. Evaluates whether the accepted critiques of the scheduling algorithm require changes now or can be deferred safely. Proposes the minimal algorithmic adjustment that addresses the accepted concerns.
>
> **Python expert** - proposes the idiomatic Python implementation of any changes implied by the accepted critiques. Concrete: types, function signatures, commit strategy.
>
> **Operations research analyst and military programmer** - proposes a revised throttle heuristic if the original was rejected, or validates the original if it was accepted. Grounds the recommendation in the actual learning objective, not engineering preference.
>
> **Jonathan Blow** - identifies what should be deleted from the spec entirely. The accepted critiques about speculative complexity should produce removals, not revisions. States exactly what sections or subsections should be cut.
>
> **Prompt and context engineering specialist** - proposes a tightened item file format contract that closes the edge cases identified in the red team. Minimal changes - patches the holes without adding new structure.
>
> **Senior project manager / DOD advocate** - produces a revised phase structure. Removes any phase or step that cannot be justified by the data that flows through it. One sentence per phase: what goes in, what comes out, why it exists.
>
> **Instructions for each reviewer:**
> - Respond only to the failure modes the user ACCEPTED or PARTIAL-accepted.
> - Do not relitigate REJECTED critiques.
> - 4-6 sentences. One concrete recommendation per reviewer.
> - No preamble. No praise. Recommendation only.
>
> After all seven reviewers, produce a **distilled panel output**: a numbered list of concrete changes to make to the spec. Each item is one sentence. Discard anything that adds abstraction, adds a new phase, or contradicts the user's stated constraints. Label each item with the section of the spec it affects.

---
---

# Note on the Integration Prompt
# Reuse the synthesis prompt from the previous session verbatim.
# It applies without modification - the rules (reduce, ask on disagreement, no new sections) are correct for this spec.
---
# Panel Selection Rationale
# (For the user's reference - do not paste this into the thread)
#
# KEPT:    Mike Acton (DOD, directly relevant to buffer design)
#          Jonathan Blow (speculative complexity, 20-commit structure)
#
# REMOVED: Justin Skycak (learning science - irrelevant to a UI library)
#          Prompt/context engineering maestro (was useful for file format edge
#          cases in SM-2; no equivalent surface in a terminal library)
#
# ADJUSTED:
#   Operations research/military/nvim  Veteran terminal application developer
#     and neovim contributor (the nvim angle is the highest-value lens here;
#     someone who has written and maintained real terminal UIs in raw escape
#     codes knows exactly where this spec will break)
#
#   PM/DOD advocate  Library API minimalist
#     (for an application you want delivery discipline;
#      for a library you want ruthless surface reduction -
#      same instinct, different domain)
#
# ADDED:   Systems Python expert with terminal/POSIX focus
#     (the original Python expert was generic; this library's failure modes
#      are specific: module-level mutable state, bytearray vs memoryview,
#      os.read vs sys.stdin, select() portability, signal handler constraints)
#
# Final panel: 5 experts. Tighter than the SM-2 panel, domain-matched.

---

# Prompt 1 - Red Team Review
# Paste this first into the thread.

---

> You are running a structured adversarial review of the 2D Terminal Grid Library atomic commit plan and specification provided. Five expert reviewers will each identify the single most critical failure mode from their domain perspective. They are attacking the design, not balancing critique with praise.
>
> The reviewers are:
>
> **Mike Acton** - data-oriented design. Attacks the buffer representation, module-level state layout, access patterns, and any place where the data's actual shape is obscured by the structure around it. Focuses on buffer.py and present.py. Hostile to indirection that has no cache or throughput justification.
>
> **Jonathan Blow** - speculative complexity and premature structure. Attacks the 20-commit plan as a design document. Identifies what was built before it was needed, what abstraction layers exist to support features that aren't in scope, and which of the 10 modules could be collapsed without loss. Questions the MVP boundary.
>
> **Systems Python expert (terminal and POSIX focus)** - attacks implementation decisions specific to terminal programming in Python: module-level mutable state as an architectural pattern, bytearray vs memoryview vs array.array choices, signal handler constraints (what you cannot safely do in a SIGWINCH or SIGTERM handler in CPython), select() portability, and the os.read loop in drain_input. Not general Python style - terminal and systems programming failure modes specifically.
>
> **Veteran terminal application developer and neovim contributor** - has written and shipped terminal UIs using raw escape codes, ncurses, and direct ANSI output. Attacks the escape sequence decisions: the 16-bit style packing limit, the CSI_MAP coverage gaps, the escape ambiguity resolution at 50ms, and the assumptions about terminal emulator behavior that will break on real hardware. Attacks from the perspective of what actually fails when users run this on their terminal.
>
> **Library API minimalist** - attacks the public surface of the library. Questions whether 10 modules and 20 commits produce an API that a caller can actually reason about. Identifies where module-level state makes the library impossible to use in more than one context, where the region dict is a leaky internal representation rather than a clean API boundary, and what the minimum number of modules is that covers the specified behavior.
>
> **Instructions for each reviewer:**
> - Stay in character. 4-6 sentences maximum.
> - One failure mode per reviewer - the single most critical problem from your perspective.
> - No validation. Do not acknowledge what is well-designed.
> - Ground criticism in the spec as written. Reference specific commits, functions, data structures, or module names where relevant.
>
> ---
>
> After all five reviewers have spoken, do the following automatically:
>
> **Generate Prompt C - User Feedback Form.**
>
> List every distinct failure mode raised by the panel as a numbered item. For each one, write a one-sentence summary of the critique. Then add a verdict line:
>
> ```
> Failure mode N - [one-sentence summary]
> Verdict: [ACCEPT / REJECT / PARTIAL - your reasoning]
> ```
>
> List failure modes separately even if two reviewers attacked adjacent areas. End with this line exactly:
>
> > My standing constraints: no classes, no inheritance, no event emitters, no async, flat where possible, no speculative structure, no utility functions not called in this commit. These are hard constraints, not preferences.

---
---

# Prompt 2 - Expert Panel Constructive Review
# Paste this after the user has filled in and submitted Prompt C.

---

> You are running a constructive expert review of the 2D Terminal Grid Library. The same five experts have now read: (1) the original commit plan and specification, (2) the red-team critique, and (3) the user's verdict feedback on each failure mode.
>
> The five reviewers are:
>
> **Mike Acton** - proposes the flattest buffer representation that satisfies the flush pipeline. If the current bytearray/array.array layout was critiqued and accepted, states the concrete alternative. If the module-level state pattern was accepted as a problem, proposes the minimal structural change - not a rewrite, a reduction.
>
> **Jonathan Blow** - identifies what to delete from the commit plan. For each accepted critique about speculative complexity, names the specific commit or module that should be removed or merged. Does not propose additions. The output is a shorter commit list.
>
> **Systems Python expert (terminal and POSIX focus)** - for each accepted implementation critique, proposes the concrete fix: the right data structure, the correct signal handler pattern, the safer drain_input loop. One recommendation per accepted failure mode. No general advice.
>
> **Veteran terminal application developer and neovim contributor** - for each accepted terminal compatibility critique, proposes the minimal change to the escape handling, the style packing, or the CSI_MAP that closes the real-world failure. Grounds each recommendation in specific terminal emulator behavior, not ANSI spec idealism.
>
> **Library API minimalist** - proposes a revised module structure. If the accepted critiques include API surface problems, states the minimum number of modules that covers the behavior and which current modules collapse into which. One concrete module map, not a principle.
>
> **Instructions for each reviewer:**
> - Respond only to failure modes the user ACCEPTED or PARTIAL-accepted.
> - Do not relitigate REJECTED critiques.
> - 4-6 sentences. One concrete recommendation per reviewer.
> - No preamble, no praise, no hedging. Recommendation only.
>
> After all five reviewers, produce a **distilled panel output**: a numbered list of concrete changes to the commit plan or spec. One sentence per change. Label each item with the commit number or module it affects. Discard anything that adds new modules, adds new commits, or contradicts the user's stated constraints.

---
---

# Note on the Integration Prompt
# Reuse the synthesis prompt from the prompt library session verbatim.
# It applies without modification to this spec.
