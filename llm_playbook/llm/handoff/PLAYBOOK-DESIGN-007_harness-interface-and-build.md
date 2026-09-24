DESIGN RECORD PLAYBOOK-DESIGN-007_harness-interface-and-build
=============================================================
date:     2026-09
type:     design
baseline: playbook 58ca75d04e04af5c433b385bcf81a21aeb955d63  same repo
scope:    the findings of the harness, interface and grammar-boundary
          branches of PLAYBOOK-DESIGN-007, merged into one record. What
          the thing being built is, what the field already ships, and
          the two open questions the next thread must close. Does NOT
          restate the preference work; see the close artifact.

  MERGED FROM TWO BRANCH RECORDS, both of this thread, written in
  parallel conversation branches and never committed:
  findings-harness-interface-grammar.md and
  branch-record-harness-and-build.md. They overlapped on six findings
  and disagreed on one point (the interface seed presumed a TREE while
  the build record left the graph shape open). Every finding in either
  source is below; where both stated one, the fuller text was kept.
  The pre-merge bytes are in the close artifact's DISCREPANCIES
  checksums, not here.

  Companion: PLAYBOOK-DESIGN-007_interface-sketch-seed.md, the editor
  design starting point, kept separate so it can be attached alone.


FINDINGS (LOCKED -- reopen by reading the entry first)

1  FIELD MAP, AND WHERE THIS WORK SITS
   The 2026 context-engineering field splits into four layers:
   orchestration (LangGraph, CrewAI, OpenAI Agents SDK), retrieval
   (LlamaIndex, vector stores), memory (Mem0, Zep, Letta), and
   observability/governance (Langfuse, LangSmith). No single platform
   covers all four; production systems compose across them.

   This playbook is none of those. It is a fifth thing the field
   mostly does not ship: a methodology encoded as a prompt -- review
   disciplines, flat-procedural code philosophy, verification-honesty
   rules, the workflow prompts -- applied by the model to its own
   reasoning, with no external state machine, retrieval or
   persistence. Nearest shipped analogues: NeMo Guardrails' Colang
   (rails triggered by name, which mirrors pasting a prompt by name)
   and the procedural-knowledge-in-context pattern.

   Consequence: the CONTENT is not reinvention; it is taste, and
   nobody ships taste. A self-built orchestrator WOULD reinvent the
   orchestration layer (the state-graph pattern). Keep the
   disciplines; be deliberate about any orchestrator.

2  IN-CONTEXT SELF-ORCHESTRATION BEATS EXTERNAL ORCHESTRATION, FOR ONE
   MODEL ON A DEFINED PROCEDURE
   Evidence: Dennis et al., "In-Context Prompting Obsoletes Agent
   Orchestration for Procedural Tasks", arXiv 2604.27891 (v2, May
   2026). Same model on both sides (Claude Sonnet 4.5), three
   conversational domains (14, 14 and 55 nodes), 200 conversations per
   condition. The whole procedure in the system prompt, self-routed,
   against a LangGraph orchestrator injecting a per-node prompt and
   routing with an extra model call.

   STATED PRECISELY, because both source records overstated it:
     Claude judge: in-context won all 15 comparisons (4.53-5.00
       against 4.17-4.84).
     GPT-4.1 judge: 11 of 15 significant for in-context, none for
       orchestration. The naturalness gap mostly vanished; graceful
       handling was not significant in two domains, with LangGraph
       trending slightly higher there.
     ROBUST across both judges: task success, information accuracy,
       consistency.
     Failure rates: orchestrated 9-24 percent, in-context 0.5-11.5.
     Cost: orchestration made 1.2-1.7x more model calls, yet in-context
       cost 1.3-1.4x MORE per conversation, because the procedure rides
       in every call.
   The "every metric" claim in both source records was true under one
   judge only. Corrected here.

   Diagnosed cause: per-node orchestration fragments the model's
   reasoning into local generations; it sees one node at a time and
   loses the global arc, degrading coherence and adaptability.

   Carve-outs the paper itself names, where orchestration may still
   earn its place: multi-model pipelines, tool use with external
   state, non-procedural open-ended work, and weaker models that need
   the guardrails.

   DESIGN CONSEQUENCE, the whole lesson in one line: orchestrate the
   ENVIRONMENT (which buffer, file, tool, branch); never fragment the
   model's train of thought by swapping prompts mid-reasoning. The
   playbook's prompts already live in context and are self-selected --
   the good side of this finding, kept by instinct.

3  THE OBJECT OF STUDY IS CONTEXT ASSEMBLY, NOT THE MODEL
   The model is stateless. Nothing persists between turns except text
   re-injected into context. A mode, a rule, a discipline -- none
   exists on turn 40 unless it is in the payload on turn 40. The
   payload is the only lever. Every preference and prompt in this
   playbook is payload discipline, and its reliability is exactly the
   reliability of the channel that injects it. Everything below is a
   consequence of this finding.

4  OUTPUT IS ONE STREAM UNDER MANY GRAMMARS: TAGGED SPANS, NOT A
   METALANGUAGE
   Realized as text, a model's output is one token stream with regions
   under different grammars: code in several languages, config
   formats, prose, more than one human language. The naive reach is a
   higher-order language describing arbitrary composition of
   sublanguages -- a grammar of grammars, a large open problem.

   The fitted structure is smaller: a sequence of typed spans with
   boundary markers, each span carrying the grammar that governs it
   (this span is Python and must parse as Python; this is prose and
   must not be parsed as code; this is config with its own escaping).
   Conceded: a metalanguage is still a language, so the distinction is
   not language versus not-language. What survives is that the fitted
   structure IS the language, it is small, and it need not be designed
   up front. Name it later if wanted.

   Shipped partial precedents: MCP typed content blocks (the
   naive-but-working baseline to study first), Markdown fences, shell
   heredocs.

5  THE HARNESS IS A REAL OBJECT ONLY IN THE CARVE-OUTS
   "The harness is the real issue" is true for a multi-model,
   tool-using, external-state system, and a trap for the single-model
   chat case in use today, because finding 2 shows the harness
   degrades that case.

   Building an orchestrator from scratch rather than adopting a
   framework stands on three grounds, none needing the paper's
   permission: (a) it must follow this playbook's conventions and flat
   procedural code, which the frameworks' abstraction stacks fight --
   one cited figure: 80 percent of surveyed developers struggle to
   choose among them, and a single LangChain change can mean
   "traversing seven layers of code" (Wang et al. 2026, as cited by
   Dennis et al.; UNVERIFIED at source); (b) from scratch builds only
   what is needed; (c) a terminal preference for building certain
   things, which is not a claim to defend. Ground (a) makes from
   scratch MORE consistent with the style contract than adoption
   would be. The discipline that remains: name when a use sits inside
   the paper's danger zone (one model, a defined procedure,
   self-orchestratable) and never build the fragmenting per-node
   controller for that case.

6  THE PAIN POINTS ARE NAVIGATION AND I/O, NOT MODEL QUALITY
   Every standing complaint about current chat interfaces is an
   interface and context-assembly problem: cannot branch or navigate
   the conversation, cannot cheaply transform text before sending,
   cannot pull in repository and local files even with sandbox
   features. None is about what the model produces.

   In use today: mostly browser chat; one exploratory project uses an
   nvim buffer as the interface. Envisioned: html/css/js frontend,
   python backend, served to a browser launched from the terminal,
   reaching the WSL and Windows workspaces, driven by a modal,
   vimium-style keyboard model. The nvim reach is the tell: reaching
   for a modal editor means the real object is a structured document
   that is edited, not a chat that is typed into.

7  THE BUILD IS A MODAL EDITOR OVER A CONVERSATION GRAPH, NOT A
   DASHBOARD
   Every pain in finding 6 is YOU-ACTIVE (acting on the structure). A
   dashboard is read-mostly and MODEL-ACTIVE (watching a process you do
   not steer). It would optimize the thing not being complained about.
   The fitted shape: a modal editor whose primary object is a
   navigable, editable conversation graph, where model calls are
   operations invoked on regions of it, the way a substitute or a
   macro operates on a range. Modal interaction is the core grammar;
   everything else is a verb in it.

   Ranked: modal editor over a conversation graph (recommended) >
   IDE-for-conversations (the right long-term shape, overbuilt to
   start) > notebook (steals well for transform and re-run, weak at
   branching, which is the top pain) > dashboard (right only under a
   pivot to watching many concurrent agents).

8  A DASHBOARD FACE LATER, ON THE SAME GRAPH
   Not one thing: an editor now that grows a watching surface later.
   The conversation graph is the shared object. Today the user edits
   it. In a multi-agent future several model calls mutate it
   concurrently and a watching face is wanted -- added when concurrent
   agents are the actual call site, not before. The second-call-site
   rule, applied to the product.

9  VIM SOLVES THE TEXT LAYER; THE NEW WORK IS THE GRAPH AND MODEL LAYER
   Text editing is solved: motions, operators, registers, macros and
   modes transfer free. Embed the solved editor; do not rebuild one.
   The genuinely new work is branch navigation, attaching model-call
   results as spans, pulling files in as typed regions, and watching
   concurrent calls -- which vim lacks because it edits text, not
   conversation graphs. The framing is "vim as the text layer, with a
   graph-and-model layer its grammar extends over", NOT "vim plus
   missing features". That distinction is what prevents reinventing
   editing.

10 THE LOAD-BEARING SEAM IS THE CONVERSATION GRAPH'S REPRESENTATION
   The stated skeleton -- frontend, python backend, browser, modal
   control -- is sound. The representation everything hinges on is the
   conversation graph, so it is chosen FIRST and shaped by how the
   user navigates and branches, never by what renders or serializes
   easily. The frontend renders it and the backend attaches spans to
   it; neither dictates its shape.

11 THE NVIM-BUFFER PROJECT IS THE PROBE
   It already has the solved half (a modal editor over text) and lacks
   only the graph and the file-yank and model-call verbs. If editing
   conversations as buffers already beats browser chat despite having
   no branches, that is evidence the editor framing is right and worth
   the larger build. If not, check before spending on
   frontend and backend.

12 BUILD ORDER (TOPOLOGICAL, NOT PRIORITY)
   Two separable projects share a backend and must not be folded
   together:
     1. The context-assembly and navigation interface -- the editor
        over the conversation graph, file and repository splicing, text
        transformation, branching. Frontend plus local I/O. Needs no
        orchestration and delivers value without it.
     2. The harness / tool-calling / agent layer (finding 5). Needs 1
        first, or agent loops get debugged inside an interface already
        disliked.
   1 unblocks 2 unblocks a deferred 3: multi-model orchestration, only
   if a real workload demands it.


OPEN QUESTIONS (blocked on a workflow dump, done in a clean thread)

A  GRAPH SHAPE: TREE, DAG, OR CYCLIC
   The representation decision the editor rests on. Pin it from one
   concrete branching instance -- what was being attempted when a
   linear chat blocked it -- never by guessing. Branches abandoned and
   returned to imply a tree; branches later merged imply a DAG;
   branches that feed each other imply cycles.
   NOTE: this thread itself is evidence. It ran parallel branches whose
   records were later MERGED into this file. That is a DAG shape, one
   instance. One instance is a lead, not a ruling.

B  WHICH FUTURE: SINGLE-MODEL OR MULTI-MODEL AND CONCURRENT
   Decides whether the harness is the object or the trap. Single
   model, methodology in the prompt: context assembly is the whole
   object, and "higher-order language" is span tagging. Multi-model,
   concurrent, external state, or cheaper-model subtasks: the harness
   becomes the object and the grammar-boundary problem hardens,
   because spans then cross CALL boundaries and not only turn
   boundaries. Evidence lives in the dump: any habit of running a
   prompt several times and picking, or handing work to a cheaper
   model, points to the second.

WHAT THE WORKFLOW DUMP MUST PROVIDE
  - one concrete branching instance, detailed enough to read the graph
    shape off it (closes A);
  - any pattern of multiple runs with selection, or delegation to a
    cheaper model (decides B);
  - one real session end to end, so the editor's verbs are derived
    from use rather than imagined.


THE MERGE SEAM, NOW EXECUTED
  The branch records asked to merge into the thread holding the
  preference work. They are merged here. The frame they handed up
  stands: the methodology layer and the build layer are two faces of
  one object. Payload discipline -- preferences, prompts, verification
  rules -- is what runs INSIDE each node of the conversation graph; the
  graph is the structure the editor navigates.
