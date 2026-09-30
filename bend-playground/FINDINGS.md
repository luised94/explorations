# Findings: getting models to write Bend 2

Closed 2026-09-30. This is the long-term reference: what was learned, what
transfers beyond Bend, what is still open, and what to read next. `report.md`
holds the evidence for the i00 experiment; `rules-card.md` holds the
language rules; `prompts.md` holds every message; `bendlab.py` is the tool.

---

## 0. Decision

**Closed deliberately; Bend continues as an occasional study-session topic.**
None of the personal projects this was weighed against (spaced repetition,
nvim + Zotero, personal finance, PDF/EPUB knowledge views, an LLM interface,
academic OSINT) fits Bend today: they are text, files, web and interfaces,
and Bend's own limitations list names slow strings and no HTTP, JSON or
regex. Most of what transfers from this project is not Bend-specific (section 1).

**What would reopen it:** a shipped web target (the announced WASM + WebGPU
work), JSON or HTTP libraries in Base or on BendHub, or a Bend program you
actually need. Re-test in about twenty minutes with `bendlab.py` (README).

---

## 1. Lessons that transfer beyond Bend

Ranked by how much they would change the next project.

**1. The compiler fixes loud defects; nothing fixes silent ones unless you
ask.** Error-pasting took all five models from failing to passing. Across
roughly twenty rounds it fixed every affinity, termination and parse error,
and not one of: unbalanced forks, figures with dead columns, or laws that
constrain nothing. Law files were byte-identical before and after recovery
in four of five models. A green check means "no loud defect", nothing more.
Anything silent needs its own measurement (figure measurement in
`bendlab.py`) or a question asked on purpose (the `audit` message).

**2. A proof, like a test, is only as strong as the property it states.**
Two of five models passed "All terms check." on law sets in which every law
closes in one reduction step, and medium's last session ended the same way.
Two more described a law that only counted rows as guaranteeing that no row
was dropped or duplicated; an implementation that duplicates every row
satisfies it.
A verified kernel (Bend 2.0.32's `--verdict`) guarantees soundness, not
adequacy. The practice: **the human writes the laws**, and every law names
one wrong implementation it rejects and one it still accepts. The tool idea that follows: mutate the
implementation and see which laws still pass (`upstream-discussion.md`).

**3. Repair messages: ask for every site of the rule, not a fix for the
line.** Medium diagnosed all eight of its i00 errors correctly and still took
eight rounds, because it repaired only the reported line. The four-line
`enumerate` message (name the rule, list every site, fix all, change nothing
else) later took a fresh session from its one error to compiling in a single
round. Escalate to `sweep` when an error class repeats. Use a bare paste only
when measuring unaided recovery.

**4. Self-audits find real defects and invent fake ones; ask for the trace.**
The four audit questions surfaced what compiling could not: dead columns,
unreachable branches, an escape test one step late, retracted overclaims.
One audit also confessed, fluently, to a catastrophic bug that the program's
own output refuted: a "blank" Mandelbrot that printed 619 glyphs. Ask for the
trace, and check each claim against the run before believing it.

**5. Lesson files a model writes for itself speed things up and fossilise
errors.** Medium's 20-note self-written catalog got a fresh session compiling
after one error. It also stated three rules that other models' passing code
refutes, and the session obeyed all three: an unbalanced fork, trivial laws,
and a false bug report about the guide. Grade every carried-forward rule as
VERIFIED, STATED or UNVERIFIED, check it against independent runs, and paste
the `notes-preamble` above it. The catalog's own note 19 proposed exactly
this grading and never applied it to itself.

**6. Verify the verifier.** My own checks were wrong twice. A plain-text
search called a real guide quotation fabricated, because the guide wrote
"checked \*live\*". A later check missed a quote because a comment's `#` sat
mid-phrase at a line break. Normalise markup before matching, and treat a
zero-hit search as a question, not a verdict. The same applies to counting:
I reported five Sonnet errors when there were six.

**7. Materials rot fast; generate them at use time.** Bend went from 2.0.16
to 2.0.32 in about two weeks, with the guide and the error display changing
along the way. Frozen doc copies were stale within days. `bendlab.py prompt`
builds the prompt from the live compiler and stamps it with the version and a
content fingerprint. Keep rules about the language in the docs layer (the
rules card) and task framing in the prompt.

**8. Build contexts by selecting sections, not deleting them.** The section
that looked most skippable, "Under the Hood", holds the rule deciding which
variable occurrences count as uses. The shader guide, which looked relevant,
misled all four models asked about it. Relevance cannot be judged from
section titles.

**9. Experiment design.**
- Separate **iteration** (a frozen materials version) from **attempt** (one
  submission inside a chat). "Round" meant both here, and it confused the
  records.
- **Fixed k, not retry-until-success.** Retrying until a pass keeps the
  success and throws away the denominator.
- Keep a **held-out task** that never informs a materials change, or the
  materials overfit to the task.
- **Attribute changes by error class**, not by pass/fail. Keep a change only
  if the class it targeted disappears.
- **Fresh chats with memory off**, so a "fresh" session doesn't remember
  earlier rounds.
- **Capture files from the copy or download button, not transcripts.** One
  transcript scrape lost all its code to line-number gutters.
- **Never overwrite results; snapshot the source before each run**, so the
  record and the artifact cannot drift apart.

**10. A tool you won't maintain is worth less than a small one you will.**
The first conventions draft had tags, a model registry, eight message
templates and manual fields. It was cut to one command, a fingerprint instead
of tags, and three templates, because friction decides whether the tool gets
used at all.

---

## 2. Harness tactics worth keeping

From the original `run_model_tests.sh`. All of these are carried into
`bendlab.py`.

- An explicit model list, not a glob, so a stray directory is never run as a
  model. (`bendlab.py` runs only `work/` subdirectories that contain all three
  files, and reports the rest as skipped.)
- Run from the model's directory so relative imports resolve against that
  model's files.
- stdin from `/dev/null`, so a program that reads input cannot hang the run.
- A timeout, with a timeout recorded as its own outcome and never mistaken
  for a compiler error. (The script named exit codes 124 and 137; Python's
  `subprocess` timeout covers both.)
- `NO_COLOR=1`, to keep terminal escapes out of recorded output.
- No `set -e`: one failing model is a result to record, not a reason to stop.
- Record the compiler version, since results only compare within one version.

Added in `bendlab.py`: snapshot before run; attempt numbering keyed to file
content (reruns never invent attempts); error classes read from the
"observed" parenthetical; figure measurement with marker lines; paths resolved
from the script (the v1 script hardcoded a home path, so it would have run
against the main checkout from a git worktree); version-mismatch warnings; an
opt-in installer.

---

## 3. Bend knowledge

### The unit of thought

A **def over a shrinking argument**. One recursion shape is used three times:
as the loop (termination needs the shrinking argument first), as the proof
(induction on that argument; the recursive call is the hypothesis), and as the
fork tree (halve that argument). Every nontrivial proof here was induction on
exactly the argument its def recursed on, and every structural failure broke
that shape. Two further axes: **ownership** (each value's quantity, `+` or
affine) and the **live/dead wall** (code that runs versus types and proofs).
Before writing a def, ask: what shrinks, who owns this, is it live?

### Rules

In `rules-card.md`, graded by evidence. The ones that cost the most rounds:
affinity counts every occurrence (4 of 5 models); the shrinking parameter goes
first; match parameters in signature order; define before use; no unary minus.

### Where Bend fits

Good fits: round-trip codecs with `read(show(x)) == x` laws (structural,
inductive, meaningful); quadtree image work (`Image` is a quadtree, so the
fork tree is the image); balanced-tree data structures with invariants;
bit-level arithmetic over `Word`; small games through `App`.

Poor fits today: laws about floats (F32 is axiomatic), text-heavy output
(strings are linked lists, and joins are serial), IO glue, unbalanced search on
the GPU.

### State of the project, from the announcements of 2026-09-30

Shipped in 2.0.32: `--verdict` (files compile to BendTT, a minimal proof
kernel verified in Lean, with a $10k bounty for a proof of `Empty`;
axiomatic F32 and some templates are not covered yet); templates as theorems
(a law can take `~` parameters); errors underline the exact code; a 2.3x faster
JS backend; BendHub with named, versioned packages; a sha256-pinned installer;
`-o f.mjs` ES modules.

Announced, not shipped: kernel and compiler rewritten in Bend; WASM + WebGPU
HTML apps; AMD GPUs; clustering; networking, crypto and database libraries; a
game engine; an AI framework. The author also says the compiler is "still
uncomfortably AI-sloppy". About 400 distinct non-cloud IP addresses run
`bend` each day.

---

## 4. Open questions

Each is settleable with a file of a few lines.

1. **What makes Base's law-forward-declared mutual recursion legal?** A user
   file with the same shape got "an unfilled law is a dead claim". Test two
   laws, shrinking parameter first versus third, around the same helper cycle.
2. **Does `+` on a law's `for` clause carry to a filling def in another
   file?** Sonnet worked around it and never isolated the cause.
3. **Does `x : T = v` parse inside a `do` block?** The guide says yes;
   medium reported a failure it never isolated.
4. **What caused medium's `Sierpinski.row` resolution error in i00?** Most
   likely a forward reference; dotted names themselves work (rules card R12).
5. **Do these PROOF.bend files pass `--verdict`?** The laws avoid F32, but
   playground.bend uses it throughout, and `--verdict` does not yet cover
   axiomatic F32.

Resolved since the report: the checker does reduce U32 literals through
`Word` (large's ten ground laws passed).

---

## 5. What to read, in order

1. **Base, eight definitions** (line numbers as of 2.0.16):
   - `Image.free` (around 2760): fork k levels, then one flat loop; `+k` reused
     four times; 4^7 is the GPU lane cube.
   - The `Word.adc` / `Word.adc.con` cycle (1166-1179): mutual recursion
     through a `law`.
   - `String.trim_start` (1958), `U32.show.go` (2049), `Map.put` (2367): the
     other three cycles.
   - `U32.add_comm` and `Word.add_comm.arm`: proof idioms (`Equal.cong`,
     `Equal.trans`, erased arguments).
   - `List.append`, `List.length`: the shapes most length laws induct over.
2. **The checker, navigated by error strings.** In a read-only clone kept
   outside `explorations`, grep for `consumed more than once`, `a decreasing
   self-call`, `an unfilled law is a dead claim`, `a defined name`, `consumed
   binder`. Each open question above maps to one of these sites.
3. **Demos:** `pure_par_sum` (the balanced fork), `app_ray_tracer_3d`
   (`Fly.march`, the early-exit loop), `app_pong_game_2d`, and the game with
   its proof.
4. **Papers:** BendTT (recently rewritten; the live/dead wall and the kernel
   `--verdict` uses), then BendRT (why a task never moves between cores, and
   so why balance matters).
5. **Guide sections to reread:** Quantities, then Under the Hood, together.

---

## 6. Per-model notes (one run each; indicative, not rankings)

- **claude-opus-5:** the only one-shot pass; two real inductions; strongest
  honesty, and it retracted its own overclaim unprompted. Its files are the
  reference solution in this directory.
- **claude-sonnet-5:** six errors, four of them affinity. Deepest language
  reasoning: it re-derived the live/dead rule from error messages. Its
  self-audit found a genuinely unreachable branch.
- **gpt5.6-terra:** two errors. The only centred, correctly re-derived
  Sierpinski geometry; laws all single-step; accurate self-classification.
- **open-source-large:** three errors, and the best breadth of repair. It
  killed a mutual recursion no error had pointed at, but shipped a half-blank
  Sierpinski and certified it correct.
- **open-source-medium:** eight errors in i00, each diagnosed correctly and
  repaired only at the reported line; fixed by the sweep message. Across later
  sessions: a self-written catalog, one-round compiles with `enumerate`, three
  false rules obeyed, and code blocks no longer labelled `python`.

---

## 7. For study sessions

Exercises that fit Bend and exercise the ideas above:

1. **A round-trip codec** (for example, a tiny run-length encoding) with a
   `decode(encode(x)) == x` law proved by induction. Before proving it, write
   down a wrong implementation the law would reject.
2. **Sierpinski as a quadtree.** An `Image` with one empty quadrant per level,
   and a law about its depth or leaf count. Compare it to the ASCII version:
   the fork tree becomes the data structure.
3. **Mutation-test your own laws by hand.** Break one line of the reference
   solution here (reuse `first_row_index` in the lower branch) and confirm
   `bend PROOF.bend` still says "All terms check." Then write a law that
   catches the break.
4. **Close one open question** from section 4 with a file of a few lines.
