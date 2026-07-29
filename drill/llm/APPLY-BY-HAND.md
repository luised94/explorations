# Applying the drill consolidation by hand

You cannot download the patches, so this reproduces the same eight-commit
series using local commands plus the ten .md files presented alongside this
document.

Baseline you should be at before starting:
  tree checksum of all .md under drill/llm, sorted:
    4296b13bf21a46146589d785635db02c

Check it first:

    cd drill/llm
    find . -name '*.md' | sort | xargs md5sum | md5sum

If that does not match, your working tree has moved since the pack was made.
Stop and tell me; the file replacements below assume the pack's content.

--------------------------------------------------------------------------------
## Step 1 -- pure file operations (run these; no editing needed)

All of this is moves and one delete. Run from the repo root.

    # 1. archive skeleton
    mkdir -p drill/llm/archive/handoffs

    # 2. retire the 14 provably-superseded documents
    cd drill/llm
    git mv 260626_roadmap-rec-after-D2.md            archive/
    git mv g1-findings.md                            archive/
    git mv handoff-qol-recall-thread.md              archive/
    git mv phase0.md                                 archive/
    git mv readme-tests.md                           archive/
    git mv review-D1.md                              archive/
    git mv roadmap-1-modularization-commit-plan.md   archive/
    git mv roadmap-1-modularization-findings.md      archive/
    git mv setup.md                                  archive/
    git mv thread-migrate-T2-wave0.md                archive/
    git mv thread-model-D1-wave1.md                  archive/
    git mv handoffs/handoff-2-implementation-to-ui.md      archive/handoffs/
    git mv handoffs/handoff-2-to-implementation.md         archive/handoffs/
    git mv handoffs/handoff-kickoff-2-difficulty-design.md archive/handoffs/

    # 3. remove the drifted ADR index (its scope note is now in decisions.md)
    git rm adr-index.md

    # 4. move the spikes out of the docs tree
    cd ..                      # now at drill/
    mkdir -p tests/spikes
    git mv llm/spike/*.py tests/spikes/
    rmdir llm/spike

--------------------------------------------------------------------------------
## Step 2 -- file replacements

Replace these ELEVEN files wholesale with the versions presented alongside
this document. Every one is plain markdown; none needs merging.

    drill/llm/STATUS.md                     REWRITTEN  (256 -> 198 lines)
    drill/llm/decisions.md                  headings + ADR block + scope note
    drill/llm/spec.md                       section 3 becomes a pointer
    drill/llm/roadmap.md                    3 citation fixes
    drill/llm/feature-backlog-2026-07.md    pointer block added
    drill/llm/design-handoffs-BCDE.md       1 citation fix
    drill/llm/consolidation-findings.md     spike-location note
    drill/llm/implementation-plan.md        spike-location note
    drill/llm/refinements-and-wiring.md     spike-location note
    drill/llm/v1-completion-guide.md        spike-location note
    drill/llm/archive/README.md             NEW FILE

The last four differ from the pack by exactly one inserted paragraph each, so
if you would rather not replace them, insert this near the top of each
instead:

    SPIKE FILE LOCATION. The spike files cited below as executable evidence
    (scheduler_port.py, author.py, author_shell.py, and the test_*.py named
    per section) live in drill/tests/spikes/. They were moved there from
    llm/spike/ in the 2026-07 consolidation so that executable evidence sits
    with the code it proves rather than in the documentation tree. Citations
    in this document are by bare filename, matching the convention used for
    the real suite.

--------------------------------------------------------------------------------
## Step 3 -- verify

    cd drill/llm

    # no ADR id is referenced but undefined
    grep -oE 'ADR-[0-9]{3}' decisions.md | sort -u > /tmp/defined.txt
    grep -rhoE 'ADR-[0-9]{3}' --include='*.md' . | sort -u > /tmp/referenced.txt
    comm -13 /tmp/defined.txt /tmp/referenced.txt        # expect: empty

    # counts
    ls *.md handoffs/*.md | wc -l                        # expect: 35
    ls archive/*.md archive/handoffs/*.md | wc -l         # expect: 15
    ls ../tests/spikes/*.py | wc -l                       # expect: 8
    ls spike 2>/dev/null | wc -l                          # expect: 0

    # STATUS.md asserts one current baseline
    grep -nE '[0-9]{3} green' STATUS.md
    # expect 4 hits: three are prose describing the OLD drift, one is the
    # live figure "668 green". No other number is claimed as current.

--------------------------------------------------------------------------------
## Step 4 -- commit

If you want the series shape, commit in this order, one concern each. If you
do not care about the history here, one commit is fine -- the reasoning is in
the documents themselves.

    1  archive/ + non-authority README
    2  absorb the ADR scope note; remove adr-index.md
    3  spec cedes ADR-001..009 to decisions.md
    4  STATUS.md collapsed to a single current baseline
    5  decisions.md: insert 7 missing section headings
    6  backlog pointers
    7  spikes moved to drill/tests/spikes/
    8  archive the 14 superseded documents

Full commit messages, with the reasoning for each, are in
SERIES-README.md and in the PLAN document.

--------------------------------------------------------------------------------
## One thing to check before you commit

The STATUS.md rewrite records the suite as 668 green and explicitly says the
COMPOSITION is not recorded anywhere in the corpus -- only the total ever was.
If you can run the suite, capture the backend/frontend split now and put it in
the BASELINE block. That closes the last hole this consolidation could not fill
from the documents alone.
