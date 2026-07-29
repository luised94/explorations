LLM PLAYBOOK
============
date: 2026-07
scope: the workflow, protocol, prompts and standing preferences used
  across projects, in one place. What it is NOT: a governance system.
  It has one job, which is to get tacit working knowledge into a chat
  that has never seen it before.


WHAT IS HERE

  protocol.md              how a thread runs. Twelve rules, three
                           templates, precedence. The whole protocol.
  preferences/layers.md    the four preference layers. THE PAYLOAD.
  preferences/style-contract.md   code style clauses. THE PAYLOAD.
  prompts/                 eight workflow prompts, each standalone,
                           each a METHOD and never an authority. Each
                           names the rules that bind at its phase.
  settled.md               closed questions and roads not taken.
  refinements.md           observed model failures awaiting promotion.
                           The intake for accretion rule ONE.
  docs/RESET-2026-07.md    the one-time reset this tree came out of,
                           and how to reach what preceded it.
  scripts/render.sh        stamp a composed render; verify one.
  scripts/pack-repo.sh     transport a chosen file set into a chat.


THE PROMPTS, IN PHASE ORDER

  find-the-isomorph      abstract the problem, match it to other
                         fields. A thinking tool; needs no search.
  survey-the-space       retrieve what those fields already know.
  adversarial-review     attack the design before it becomes a plan.
  spike-and-verify       prove the risky assumptions empirically.
  commit-planning        turn the design into an ordered plan.
  plan-review            attack the plan before it executes.
  clone-and-verify       establish a green baseline before changing.
  runtime-verification   catch what green tests and a followed spec
                         do not.


HOW TO USE IT

  Rendering and packing are SEPARATE, in that order. A render is a
  committed artifact, because a stamp can only be compared against
  something on disk. Folding the render into the pack would make it
  ephemeral and nothing could later detect that it had drifted.

  1. Compose the project's render by hand: the preference layers,
     plus that project's instance rules, with the conflicts collapsed
     at authoring time. Composition is judgment and stays manual.

  2. Stamp and commit it:

       ./scripts/render.sh stamp <body> <project>/llm/CONTEXT.md
       git add <project>/llm/CONTEXT.md && git commit

  3. Write a kickoff from the template in protocol.md. Record BOTH
     SHAs -- playbook and project -- even while they are one repo.

  4. Pack and attach:

       ./scripts/pack-repo.sh llm_playbook <project>

  5. Paste the thread id into the chat title, then say:
     "unpack, skim the tree, read the kickoff."

TRANSPORT

  Recovered from the pre-reset transport.md, which the first reset
  pass deleted without reading.

    ./scripts/pack-repo.sh [-p] [-e] [-o OUTDIR] PATH [PATH ...]

  PATH... is any subset: directories and individual files, mixed.
  Selective packing is first-class, not a workaround.

    default   git archive of the set at HEAD -> /tmp/pack-<sha8>.tar.gz
    -p        the same set as one fenced text block, for a chat that
              takes no upload -> /tmp/pack-<sha8>.txt
    -e        open the paste block in $EDITOR to copy out
    -o        override the scratch dir; MUST stay under /tmp

  Three invariants hold in every mode:
    scratch-only    writes ONLY under /tmp, never into the git tree
    committed-read  reads HEAD only. A RENDER MUST BE COMMITTED
                    BEFORE IT IS PACKED, or it is not in the pack.
    idempotent      same SHA and same file set, byte-identical output

  Which mode: archive where the chat accepts a file upload, paste
  where only text can cross the gap. Both carry the same SHA.

  GOTCHAS
    A packed render is missing -> it was not committed.
    The tarball carries no .git, so a patch built from it cannot be
    git am'd. Deliver content and commit locally (R12).
    A stale SHA in a kickoff means the pack lags the repo; the render
    stamp is the cross-check the reader states at thread start.

  NEVER PACK AN llm/ DIRECTORY WHOLE. It is thread history and it is
  the largest thing in any project. Pass the two or three files the
  thread actually needs, by path. This is discipline, not a script
  feature: pack-repo.sh already takes explicit paths, and the reason
  it is trusted is that it has not been modified.

  A PROJECT DOES NOT COPY THIS TREE. It carries only its own deltas
  -- the instance rules that append to or supersede a section here.
  Duplicated files drift, and the drift is silent because both copies
  look authoritative.


ACCRETION, AND THE THREE RULES THAT FIGHT IT

  This playbook was rewritten from scratch once already. See
  docs/RESET-2026-07.md for what happened and why. The short version: it
  reached 36 files and 84,000 tokens against its own measured
  required-read budget of 6,000, half of it was the record of
  building it, and it had never been used on a project.

  Growth is the default state of a system in use, not a failure to be
  fixed once. These three run at WRITE time, which is the only place
  such mechanisms work. Periodic review does not: it needs discipline
  nobody sustains, and the reviewer wrote the thing.

  ONE. A FINDING IS NOT A RULE.
    A finding becomes a rule when it has cost something twice, in a
    real project. Until then it is a note, and it waits in
    refinements.md, which is where the first occurrence is recorded.
    That file is deliberately under no size discipline: its growth is
    the filter working, not accretion. This is CONSTRAINT-001 --
    extract a seam only after two real uses -- applied to rules and
    not only to code. The last version believed this about
    abstraction and never applied it to itself: of sixteen work items
    in its final thread, exactly one came from someone USING the
    thing. The other fifteen came from reading documents against each
    other.

  TWO. REWRITE, DO NOT PATCH.
    A change to a document rewrites the document. Git holds what it
    said before. Patching accretes because it never forces a re-read,
    and a whole-document re-read is the only moment a contradiction
    with a distant paragraph becomes visible.

  THREE. ONE IN, ONE OUT.
    protocol.md holds twelve rules. A thirteenth requires naming, in
    prose, the rule it replaces. The answer may be "none, and here is
    why", recorded in settled.md -- the response is mandatory, the
    outcome is not.


RECOVERING WITH GIT

  Everything the old version carried in prose -- superseded markers,
  status vocabularies, append-only records, retired-field registries,
  stable-forever ids -- is here instead, in four commands. This
  section is what licenses deleting several hundred lines of
  provenance machinery.

    what did this file say before
      git log -p --follow -- <path>

    when did this rule change, and why
      git log -S'<a distinctive phrase from the rule>' -- <path>

    recover a deleted file
      git log --diff-filter=D --name-only -- '*<name>*'
      git show <commit>^:<path> > <path>

    what did the tree look like at a thread's close
      git log --oneline --grep='<thread id>'
      git show <commit> --stat

  Renumbering a rule or renaming a file is therefore cheap and needs
  no ceremony. If a citation breaks, the phrase search above finds
  where it went.


WHAT THIS IS FOR

  The payload is preferences/ and prompts/. Everything else exists to
  get that payload into a chat and to keep a thread honest once it is
  there. If the protocol starts generating work that is not on a
  project, it has become the thing it was built to prevent, and the
  correct move is to stop and go do the project.
