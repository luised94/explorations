MANIFEST
========

The sole authoritative grouping of playbook documents into load
classes, with per-role ordered required-read lists and token
budgets. Directory placement carries no semantics.

Every committed document is indexed below. An entry that is not here
is a finding, not an omission: check.sh's own accept criterion is that
MANIFEST covers every committed doc.

MACHINE-READABLE BLOCK FORMAT (parsed by scripts/check.sh)
  Required-read lists are declared one per line, anywhere in this
  file, in the form:

    REQREAD <ROLE> <token_budget>: <path> <path> ...

  Paths are relative to the repository root. Token estimate is
  total characters divided by 4. Roles and budgets:
  DESIGN 10000, IMPL 6000, CAPTURE 6000.

REQUIRED-READ LISTS
  Every list opens with the load-always set plus the kickoff template,
  then adds the method documents that role reaches for. One line per
  role; a line is not wrapped, because check.sh reads it whole.

REQREAD DESIGN 10000: llm_playbook/protocol/naming.md llm_playbook/protocol/precedence.md llm_playbook/protocol/thread-protocol.md llm_playbook/protocol/kickoff.md llm_playbook/protocol/prompts/adversarial-review.md llm_playbook/protocol/prompts/plan-review.md llm_playbook/protocol/prompts/spike-and-verify.md
REQREAD IMPL 6000: llm_playbook/protocol/naming.md llm_playbook/protocol/precedence.md llm_playbook/protocol/thread-protocol.md llm_playbook/protocol/kickoff.md llm_playbook/protocol/prompts/commit-planning.md llm_playbook/protocol/prompts/clone-and-verify.md llm_playbook/protocol/prompts/runtime-verification.md
REQREAD CAPTURE 6000: llm_playbook/protocol/naming.md llm_playbook/protocol/precedence.md llm_playbook/protocol/thread-protocol.md llm_playbook/protocol/kickoff.md

  CAPTURE'S LIST IS PROVISIONAL. The role is named in five documents
  and DEFINED in none: entry/ENTRY.md was to carry the three role
  sections and does not exist yet (T-014). Its list is therefore the
  common set and nothing role-specific, because there is no basis for
  choosing anything role-specific. Filling it by analogy would be
  inventing the role.

  ALL THREE BUDGETS ARE EXCEEDED, measured here for the first time:

    load-always alone                      4877 tokens
    load-always + kickoff.md               6501 tokens
    DESIGN   10768 vs budget 10000   over by   768
    IMPL      9932 vs budget  6000   over by  3932
    CAPTURE   6501 vs budget  6000   over by   501

  The lists are NOT trimmed to fit. The budgets were hand-set without
  measurement (ADR-028) and warn rather than gate; trimming a correct
  required-read list to satisfy an uncalibrated number would be fitting
  the work to the guess. CAPTURE is over on the common set alone, with
  nothing role-specific in it at all, which is the clearest evidence
  the figures are wrong rather than the lists.

  naming.md is 3013 tokens by itself -- half the IMPL budget -- having
  grown from 104 to 241 lines in this thread. If any single change
  would bring these numbers back into range it is splitting that file,
  which is recorded as open and not done here.

LOAD CLASSES
  load-always | load-per-role | on-demand

DOCUMENT TABLE
  Every committed file, with its declared type and load class.
  Load class is a JUDGMENT and is not derivable from the file:
    load-always    the grammar and protocol every thread is bound
                   by, whatever its role
    load-per-role  method documents a role reaches for
    on-demand      records, thread artifacts, and preference
                   SOURCES -- a source reaches a thread through
                   the render, not by being loaded directly
                   (CONVENTION-004)
  Paths are atoms and are not wrapped; some rows run long.

  LOAD-ALWAYS
    protocol/naming.md  toolkit-rules
    protocol/precedence.md  toolkit-rules
    protocol/thread-protocol.md  toolkit-rules

  LOAD-PER-ROLE
    preferences/render.md  toolkit-rules
    preferences/transport.md  toolkit-rules
    protocol/kickoff.md  toolkit-rules
    protocol/prompts/adversarial-review.md  prompt
    protocol/prompts/clone-and-verify.md  prompt
    protocol/prompts/commit-planning.md  prompt
    protocol/prompts/plan-review.md  prompt
    protocol/prompts/runtime-verification.md  prompt
    protocol/prompts/spike-and-verify.md  prompt

  ON-DEMAND
    MANIFEST.md  sentinel
    README.md  sentinel
    VERSION  sentinel
    decisions/era-2026-q3.md  decisions
    llm/close/PLAYBOOK-DESIGN-002_render-placement-and-transport-decisions.md  close
    llm/close/PLAYBOOK-DESIGN-004_kickoff-binding-and-prompt-promotion.md  close
    llm/close/PLAYBOOK-IMPL-003_g1a-transport-pass-render-fail.md  close
    llm/handoff/PLAYBOOK-DESIGN-002-to-IMPL-003_stage-b-g1a-gate.md  kickoff
    llm/handoff/PLAYBOOK-DESIGN-004-to-IMPL_g1-render-effect-retest.md  handoff
    llm/handoff/PLAYBOOK-IMPL-003-to-DESIGN-004_protocol-gap-and-doc-consolidation.md  handoff
    llm/plan/PLAYBOOK-DESIGN-002_r3-plan-locate-replace-edits.md  plan
    llm/plan/PLAYBOOK-DESIGN-002_stage-a-landing-and-stage-b-start.md  plan
    llm/plan/implementation-plan.md  plan
    llm/refinements.md  refinements
    preferences/layers.md  preference-source
    preferences/platform-settings-block.md  render
    preferences/style-contract.md  preference-source
    scripts/check.sh  script
    scripts/pack-repo.sh  script

RAW URLS
  (empty; populated at tag time, T-016)
