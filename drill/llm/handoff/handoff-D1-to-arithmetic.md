# Handoff: D1 complete -> next thread (arithmetic operators, #4)

Forward-looking and prescriptive. What the next thread needs so it does not
re-derive anything. For the reasoning behind these (the "why"), see
llm/review-D1.md; for the reusable critique/planning tools, see llm/prompts/.

================================================================================
1. CURRENT STATE
================================================================================
- D1 is COMPLETE. Suite green at 177 (backend 102, frontend 75: 6/21/19/23/6).
- Local repo: last code commit (C-D1d) + the C-D1e docs patch applied on top =
  the full D1 end-state. Confirm with `bash tests/run.sh` -> ALL GREEN.
  NOTE: the user manages the exact SHA / pin themselves (the repo may host more
  than one project). The next thread should be told the SHA by the user, or
  read it from the user's setup brief -- do not assume or hard-code it here.
- What D1 shipped: the v2 migration adds questions.metadata (additive, NOT NULL
  DEFAULT '{}'), surfaced through the readers (get_question/list_questions), and
  fixed a latent init_db defect (now stamps BASELINE_SCHEMA_VERSION=1, not the
  moving SCHEMA_VERSION). grading_kind from the original brief was DEFERRED to
  #7/Phase 4. See ADR-024/025/026 in decisions.md.
- Commits in D1: C-D1a (migration+bump+consistency-test), C-D1b (harden T2 loop
  tests), C-D1c (real-migration test), C-D1d (init_db baseline fix + temp_db/
  current_db split + reader surfacing), C-D1e (docs).

================================================================================
2. WORKFLOW CONTRACT (standing; adopted at end of D1)
================================================================================
At EACH commit boundary, Claude (in its sandbox) will: make edits, run the
suite, COMMIT with the agreed message, then deliver a fixed TRIPLE:
  (a) a SUMMARY ending with an explicit "files modified" list;
  (b) a PATCH file cut as `git diff <prev_sha> HEAD --relative`, presented as a
      downloadable file (so paths match wherever the user runs git);
  (c) the COMMIT MESSAGE (scope(project/section): imperative; bullets; final
      line = identifier, e.g. C-D2a).
The user reviews the diff (e.g. in nvim), `git apply`s the patch, and commits
with the provided message -- no hand-transcription of file contents.

Why: Claude's sandbox repo and the user's repo are SEPARATE; nothing syncs
automatically. Patches replace error-prone manual copying, especially for large
files (this bit us repeatedly on decisions.md in D1). Claude must actually
COMMIT in-sandbox so patches map one-to-one onto the user's commits.

`git apply` gotcha: cut patches with `--relative` from the drill/ dir so paths
start with `llm/...`, `tests/...` (matching the user's cwd inside drill/). A
patch with a `drill/` prefix will not apply from inside drill/. If `git apply
--check` reports "already applied" on some files, the user's local state is
ahead on those -- cut a narrower patch of only the missing files.================================================================================
3. STRATEGIES TO CARRY OVER (as RULES WITH TRIGGERS -- not a mandatory pipeline)
================================================================================
OVER-APPLICATION IS THE RISK. Each tool has a trigger; if it does not fire,
skip the tool. Applying these to a one-line change is theater.

  - ADVERSARIAL DESIGN REVIEW (llm/prompts/adversarial-review.md)
    Trigger: a costly or irreversible design choice (schema, persisted column,
    public contract, abstraction with dependents, gating sequencing). The bar:
    "could one sharp objection change WHAT I build?" In D1 only 2 of 6 lenses
    overturned anything; that is normal -- it earns its cost on the rare flip.

  - COMMIT PLANNING: decompose + sort + predict downstream
    (llm/prompts/commit-planning.md)
    Trigger: >3 interdependent commits, OR any change to a shared assumption /
    widely-used helper. The PREDICT-DOWNSTREAM step (grep every consumer, ask
    what each assumes, map the whole blast radius BEFORE editing) is the single
    highest-leverage habit from D1.

  - LET IT GO RED (deliberate): land a change that reddens a test on purpose
    when the red CONFIRMS a coupling hypothesis, then fix. Only when the red is
    informative.

JUDGMENT (not procedure -- do not proceduralize, just expect):
  - Read the actual code before asserting anything about it. Re-grep; do not
    trust memory of the file.
  - Frame fixes as UPHOLDING prior ADRs where true (ADR-026 upheld ADR-022),
    so the decision log stays coherent rather than contradictory.
  - Distinguish "scope reduction by correction" (cutting grading_kind) from
    "scope creep" (the init_db fix); name which, do not let scope drift silently.
  - When the brief's prose is "untested" (a handoff procedure, a docstring
    claim like "the evaluator already recurses"), treat it as a HYPOTHESIS to
    verify empirically, not a fact.

================================================================================
4. NEXT THREAD: arithmetic operators (#4), then trees (#5), then difficulty (#2)
================================================================================
Per roadmap Phase 1. Operators (#4) is the correct next step: a near-zero-risk
warm-up (add dict entries to the data-driven OPERATORS table) that rebuilds
content momentum after an infrastructure-heavy thread. The chain is three
interdependent threads -- so COMMIT PLANNING matters more here than adversarial
review; getting #5's tree representation wrong makes #2 rework.

PREDICTIONS / FLAGS (grounded in drill.py as of D1):
  - OPERATORS is already data-driven (OPERATORS = _build_operator_table(); each
    entry carries generate_operands + eval/render callables). Adding an operator
    SHOULD be a dict entry, not control flow -- IF nothing special-cases the
    existing four by symbol. FLAG: audit ?operators= validation, the renderer,
    and any difficulty heuristic for symbol-specific assumptions.
  - INVARIANT: evaluate_expression is typed -> int. A new operator that yields a
    non-integer (true division) or out-of-bounds negative could violate that
    contract. The operand-generation seam (_generate_operands_division exists
    separately) is where such an invariant must be enforced. Decide explicitly.
  - TREES (#5, the meaty one): generate_expression already returns a tree node
    and the docstring CLAIMS the evaluator/renderer recurse and support nesting
    "without changing" them. Treat that as UNTESTED PROSE (cf. the D1 handoff
    example that was wrong). First move in #5: build a nested node by hand, run
    it through evaluate_expression and render_expression, confirm before relying
    on it. Renderer PARENTHESIZATION is the subtlety: precedence-aware parens
    (2 + 3 * 4 vs (2 + 3) * 4); a naive recursive renderer over/under-parens.
  - NO SCHEMA CHANGE for #4 -- D1's migration apparatus is dormant; another
    reason it is a clean warm-up. DIFFICULTY (#2) is the first real candidate
    for persisted per-question state: at #2, decide whether difficulty lives in
    questions.metadata (cheap/experimental, the D1 hatch) or earns its own
    column (committed) -- the same cheap-vs-committed call we made for
    grading_kind, now WITH a real consumer. Run the adversarial review there.

================================================================================
5. SETUP FOR THE NEXT THREAD
================================================================================
Same as D1: sparse-clone drill/, verify the SHA, `uv sync --group test`,
`npm install jsdom --no-save`, `bash tests/run.sh` -> expect 177 ALL GREEN as
the baseline. If not 177 green on a clean clone at the verified SHA, STOP and
report. The user supplies the exact SHA to verify against (they manage the pin);
do not guess it. Note the SHA that was D1's launch-prompt commit is NOT the
D1 end-state -- the end-state is later, after the D1 commits landed.
