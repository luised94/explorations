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
