HANDOFF PLAYBOOK-DESIGN-007_data-model-and-tooling
==================================================
date:     2026-09
type:     handoff
baseline: playbook 58ca75d04e04af5c433b385bcf81a21aeb955d63 plus this
          thread's series 0001-0004 (0005-0006 gated); same repo
model:    written on claude-opus-5-5
scope:    what the next DESIGN thread inherits. Its job: decide the
          data model for threads and their artifacts, and the smallest
          tooling that makes it cheap to keep -- then, and only then,
          whether the interface work starts. Leans are labelled as
          leans; nothing here binds a kickoff.


WHAT THE NEXT THREAD INHERITS

  The author's aim, in his words: a holistic system usable from his
  preferred space -- nvim in WSL, or a browser interface launched from
  the terminal and connected to both the WSL and Windows workspaces --
  consolidating his LLM-related ideas and code, and making final
  decisions on the system. He likes tailored tools, suspects current
  approaches are off in ways he cannot yet state, and is undecided on
  how much rule accretion and compression loss matter.

  Transport today, and working: attach or paste where a model has no
  sandbox; pack-repo.sh to collect files, directories or repositories
  whole. Neither is in question.


VERIFIED GROUND TRUTH (verify-first: checked against 58ca75d0 in a
sandbox, not against the author's live tree)

  The data model already exists, implicitly, as filenames, frontmatter
  and git. It is not written down as a model anywhere:
    THREAD      id PROJ-ROLE-NNN_descriptive, one counter per project
                across roles, so ids totally order threads
                (protocol.md IDENTITY AND NAMING). The id is pasted
                into the chat title: THE TITLE IS THE JOIN KEY between
                a conversation and the repository.
    ARTIFACT    llm/<kickoff|handoff|close|plan>/<writer-id>_<subject>.md,
                classified by its type: frontmatter, not by its
                directory, because the path does not survive transport.
    EDGE        a kickoff's from: names the sending thread. That is
                the only edge field. One sender per kickoff.
    PREFERENCE  LAYER-NNN items in layers.md; S-numbered clauses in
                style-contract.md; stable ids, cited from renders.
    REFINEMENT  RF-PROJ-NNN, citing the items it targets.
    PROVENANCE  git: every command in README RECOVERING WITH GIT.
  Queried today by ls of llm/ and git log --grep.

  What that model CANNOT express, each observed in PLAYBOOK-DESIGN-007:
    - a thread with more than one parent, or parallel branches later
      merged. from: holds one sender; this thread merged two branch
      records (DAG, one instance -- design record question A);
    - which model did the work (RF-PLAYBOOK-013);
    - where an artifact lived before it reached the repository. This
      thread's files lived in a chat and were nearly lost
      (RF-PLAYBOOK-015);
    - more than one project at once: drill's llm/ and the playbook's
      llm/ are separate listings with no joint view.


SETTLED -- DO NOT REOPEN WITHOUT READING THE ENTRY

  In settled.md: rendering and packing are separate; a project carries
  deltas, never a copy; the author is the committer; modes are the
  in-thread form of roles; a thread's output is triaged against the
  tree; prompts keep their reasoning.
  In the design record (llm/handoff/PLAYBOOK-DESIGN-007_harness-
  interface-and-build.md): in-context methodology over an external
  orchestrator for one model; tagged spans, not a metalanguage; an
  editor over a conversation graph, not a dashboard; the editor before
  the harness.


OPEN QUESTIONS, EACH WITH THIS THREAD'S LEAN

  1  THE DATA MODEL.
     LEAN: do not build a new store. Git plus frontmatter is already a
     single-source, diffable, packable database, and CRITERIA-005 asks
     first whether a feature is a projection of structure already
     present. It mostly is. Extend the model by exactly what was
     observed missing: from: admits several senders (a DAG edge); a
     model: line beside baseline:; and nothing else until a second
     observation. The graph is then COMPUTED from frontmatter across
     repositories, never stored beside it -- a stored copy is the
     drift CRITERIA-009 warns against.
     Keep TWO GRANULARITIES apart. The THREAD graph (threads and
     artifacts, coarse) is this question. The CONVERSATION graph
     (turns, messages, payload snapshots, fine) is the editor's node
     model, the interface seed's question 1. Conflating them designs
     the editor before its data exists.

  2  THE WORKFLOW DUMP. Still unrun, still the input to design record
     questions A (graph shape) and B (one model or several). LEAN: do
     it FIRST in the next thread, before any modelling, from real
     sessions -- including this one, which is already one DAG instance.

  3  THE SMALLEST TOOLING. LEAN, in dependency order:
       a. artifact-out, the missing half of pack-repo.sh: land files a
          chat delivered into llm/ under the thread's id, verifying the
          checksums the chat printed. It enforces RF-PLAYBOOK-015's fix
          instead of asking for it (CONVENTION-010), and it is the
          promotion that entry is waiting for.
       b. a thread lister: read frontmatter across one or more
          repositories and print threads, edges and artifacts. This is
          the "tracking threads across projects" problem, answered as a
          query over structure that already exists.
       c. only then the editor, probed first with the existing
          nvim-buffer project (design record finding 11).
     Rejected in advance, as a lean: a database, a daemon, or an index
     file. Each duplicates git, which is how the pre-reset tree grew.

  4  THE PREFERENCES FIELD AS A SECOND AUTHORITY (settled.md OPEN).
     LEAN: make working-defaults.md the base every project render sits
     on, so a render carries only what supersedes it -- one
     composition, one authority. It also answers "the playbook has no
     render of its own". Needs the precedence section of protocol.md,
     not a new rule.

  5  WHOLE REWRITE OR ITEMIZED DELTA (settled.md OPEN, rule TWO). LEAN:
     split by document kind rather than choosing one mechanism. Always-
     loaded text and preference items evolve by itemized delta, where
     collapse is the danger and ids already exist. Narrative documents
     -- README, protocol.md, settled.md -- keep whole rewrites, where
     contradiction is the danger. The instruction-density finding
     argues for keeping the always-loaded text SHORT, and ordered by
     importance, since earlier instructions are followed better.

  6  THE ENVIRONMENT. CONSTRAINT-008 says no agentic environment is in
     use; this thread ran in a session with a sandbox, a shell and file
     tools, and built and verified its own patch series. The author
     deferred this here. LEAN: a kickoff states which environment the
     thread has -- chat only, sandbox, or linked to his machine --
     because R12, CONSTRAINT-014 and the no-sandbox rule all turn on
     it. That is a kickoff field, not a rule.

  7  ONE THREAD AT A TIME (settled.md, observed not holding). Revisit
     its three mechanisms as a set, with question 1: parallel threads
     are the same fact as a multi-parent edge.


SUGGESTED SEQUENCE (topological)

  dump (2) -> data model (1) -> artifact-out (3a) -> thread lister
  (3b) -> precedence and environment (4, 6), which touch protocol.md
  -> editor probe (3c). Questions 5 and 7 ride along with 1.


NEXT THREAD
  title    PLAYBOOK-DESIGN-008_thread-data-model (verify the counter)
  pack     ./llm_playbook/scripts/pack-repo.sh llm_playbook/README.md
           llm_playbook/protocol.md llm_playbook/settled.md
           llm_playbook/refinements.md llm_playbook/preferences
           llm_playbook/prompts llm_playbook/scripts
           llm_playbook/llm/close/PLAYBOOK-DESIGN-007_preferences-split-and-harness.md
           llm_playbook/llm/handoff/PLAYBOOK-DESIGN-007_data-model-and-tooling.md
           llm_playbook/llm/handoff/PLAYBOOK-DESIGN-007_harness-interface-and-build.md
  attach   this file travels in the pack; write the kickoff from it
  say      "unpack, skim the tree, read the kickoff"
