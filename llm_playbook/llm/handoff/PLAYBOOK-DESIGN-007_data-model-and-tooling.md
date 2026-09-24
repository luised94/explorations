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

  FOUND AFTER THIS THREAD CLOSED, verified by the author on 2026-09-24
  in his repository:
    - DRILL-IMPL-002 CLOSED in July 2026, after PLAYBOOK-DESIGN-006.
      Its close lists eleven commits landed and defers, among others,
      C-101 (re-render drill/llm/CONTEXT.md) and C-113 (drill's
      refinements.md, so four RF-DRILL entries sit unfiled in the
      close). The GATE in this thread's close was therefore moot, and
      0005-0006 are applied.
    - Its close names a handoff TO THE PLAYBOOK,
      drill/llm/handoff/DRILL-IMPL-002-to-playbook.md, "FINDINGS FOR
      THE PLAYBOOK ... carried in the handoff, not fixed here". No
      playbook thread has read it: DESIGN-006 closed before it was
      written, and this thread never saw it. READ IT FIRST.
    - drill/llm/CONTEXT.md is now stale three ways: stamped in the
      pre-reset format, asserting drill has no PROJECT.md instance
      rules (false, per that close), and carrying the CONSTRAINT-005
      text 0006 replaced. Re-rendering it is drill's IMPL work, not
      this thread's.
    - Two small leads from that close for question 1: its terminal
      state is prose, not one of R9's four words; and its handoff name
      follows the superseded <FROM>-to-<TO> grammar (settled.md).
    - An original verbalized-sampling existed. git log --all matches
      it in three commits adding prompts under llms/ and in ad1004f
      "Move prompts out of llms"; git grep finds nothing outside
      llm_playbook at HEAD. --all searches every branch, so locate it
      with git show --stat ad1004f and read it by path from that
      commit or its parent, before the draft is ever promoted. The
      four menu entries removed in 0005 may have bodies there too.
    - The author's LLM material OUTSIDE the repository, observed the
      same day while searching for the DRILL-IMPL-002 conversation.
      Input to the dump (question 2), not a ruling:
        clipboard-page-captures: each captured thread is a PAIR,
          page-NNN.md (the scraped transcript) and page-NNN.zip (that
          thread's artifacts, downloaded in bulk, likely out of date,
          kept on purpose). The pair is keyed by a capture page
          number, not a thread id, so the chat-title join key never
          reached the capture step. Zip entries keep sandbox paths
          (mnt/user-data/outputs/c020a/...) with no link to the commit
          that landed them: RF-PLAYBOOK-015 at corpus scale.
        One capture tree existed twice, on the E: drive and as a
          Desktop copy; diff -rq confirmed them identical.
        Documents/llm_thread holds 106 .json files, one per chat title.
        The DRILL-IMPL-002 conversation is in none of these: its
          sandbox commit e3aabfb matches nowhere. It likely survives
          only in the claude.ai history, which offers an account data
          export (Settings, Privacy, Export data).


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
     Write it against a READ-ONLY census of where the material lives
     (the section above lists what is known), and do not move LLM
     material in the author's workspace reorganization until question
     1 decides where it goes: moving it first is organizing a spoke
     before the hub exists, and it would be moved twice.

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

  read DRILL-IMPL-002-to-playbook.md -> dump (2) -> data model (1)
  -> artifact-out (3a) -> thread lister (3b) -> precedence and
  environment (4, 6), which touch protocol.md -> editor probe (3c).
  Questions 5 and 7 ride along with 1. Its findings are triaged
  against the tree before anything else, the way this thread's own
  output was.


NEXT THREAD
  title    PLAYBOOK-DESIGN-008_thread-data-model (verify the counter)
  pack     ./llm_playbook/scripts/pack-repo.sh llm_playbook/README.md
           llm_playbook/protocol.md llm_playbook/settled.md
           llm_playbook/refinements.md llm_playbook/preferences
           llm_playbook/prompts llm_playbook/scripts
           llm_playbook/llm/close/PLAYBOOK-DESIGN-007_preferences-split-and-harness.md
           llm_playbook/llm/handoff/PLAYBOOK-DESIGN-007_data-model-and-tooling.md
           llm_playbook/llm/handoff/PLAYBOOK-DESIGN-007_harness-interface-and-build.md
           drill/llm/handoff/DRILL-IMPL-002-to-playbook.md
           <drill's IMPL-002 close: git ls-files drill/llm | grep -i close>
  attach   this file travels in the pack; write the kickoff from it
  say      "unpack, skim the tree, read the kickoff"
