# Patch series -- drill/llm consolidation (drill side)

Baseline: e3aabfbbe2732efc75466e4b2c6f27cec440d8d0
Baseline tree checksum (all .md, sorted): 4296b13bf21a46146589d785635db02c

Per-file md5 at baseline, for the files this series touches:
  501d1c03c21bc0a71d889a62d421e534  decisions.md
  e6cdc8e9071ee4b198e3aea83c20bb76  spec.md
  6c265f22894d1b051301c39ed19b49af  adr-index.md
  567659fd421c15023f9f64eb21f9486a  STATUS.md
  93c0752ea7f38e5ec086f33a8d96bfee  CODING_CONVENTIONS.md
  2405205c41f9d6b69b159499dd9b2113  feature-backlog-2026-07.md

Verified: all 8 patches apply cleanly onto a fresh clone at the baseline,
and the resulting tree is byte-identical to drill-final/.

  git checkout e3aabfb
  git am patches/*.patch

## The series

  1  archive/ + non-authority README
  2  absorb the ADR scope note; remove adr-index.md
  3  spec cedes ADR-001..009 to decisions.md
  4  STATUS.md collapsed to a single current baseline
  5  decisions.md: insert 7 missing section headings
  6  backlog pointers (REVERSES a call made in the PLAN)
  7  spikes moved to drill/tests/spikes/
  8  archive 14 provably superseded documents

## Result

  live set        50 -> 35 documents
  archived              15 (incl. the archive README)
  dangling ADR refs      0
  decisions.md largest section  645 -> 240 lines (no content moved)
  STATUS.md       256 -> 198 lines, one baseline instead of five

## NOT done -- carried to the llm_playbook pass

The WORKFLOW CONTRACT / DELIVERY DISCIPLINE sections. ELEVEN documents carry
one. The consolidation PLAN said four; that was an undercount from diffing
only the modularization chain. Divergence is rigorously verified for those
four (the deliberately-red-commit allowance is present in one copy and
absent in the next, under a heading reading "standing; unchanged"). The
other seven are confirmed carriers but not yet diffed.

All eleven are HELD in the live set. Archiving them before the contract has
a home in llm_playbook would orphan the rule -- the exact failure this
consolidation exists to fix.

Reconciled contract, per your decision: take the 3-to-E10-cutover.md version
as current, and a deliberately-red commit IS permitted, because it confirms
a test actually catches what it claims to catch.

Also carried: the HOLD set (SM-2 four-document cluster, design-A,
design-handoffs-BCDE, and the remaining guides), and the NEXT section of
STATUS.md, which still contains completed-thread narrative.
