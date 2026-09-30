# Draft discussion post: when models write the laws, they write laws that pass

Status: DRAFT, not posted. For GitHub Discussions (or a reply thread), kept
separate from the documentation issue on purpose. Re-read the "bug-free
code" sentence in the current `bend guide` before posting; it may have
changed.

---

## Title

A small test of "AI guarded by LAWS": the kernel proves what the law says, and models pick laws that say little

## Body

Bend's thesis, as stated in the recent update, is AI inference guarded by
Bend's LAWS. I ran a small test of exactly that, and the result bears on it,
so I'm sharing it.

**Setup.** Five models (three proprietary, two open-weight) got the same task
on bend 2.0.16: write `playground.bend` (an ASCII Mandelbrot and Sierpinski
renderer), `LAWS.bend` (laws over it) and `PROOF.bend` (discharging every
law), such that `bend PROOF.bend` prints "All terms check." Their only
reference was `bend guide` and `bend base`. They could not run the compiler;
I pasted errors back. The prompt said: "A law you cannot discharge is a
failed deliverable, not a stretch goal - so choose laws you can actually
prove."

**Result.** All five reached "All terms check." The laws they chose:

| Model | Laws | Needing induction |
|---|---|---|
| A | 6 | 2, plus a proved append-length lemma |
| B | 2 | 2 |
| C | 5 | 3 |
| D | 5 | 0: each is one match branch, e.g. `glyph(False{}) == "#"` |
| E | 10 | 0: ground instances such as `cell(2, 1) == False{}` |

Two of five passed on laws that constrain almost nothing, and "All terms
check." looks identical for them and for the model that proved two
inductions over its fork tree.

The inductive laws were weaker than their authors claimed. Models A and B
each proved that the fork tree returns the expected *number* of rows, and
described it in a comment as more than that: "nothing dropped or duplicated
by the split" (A), "no row is lost or doubled by the parallel split" (B).
When asked, both retracted independently: an implementation that returns the
same row 32 times satisfies both laws.

**Why this matters for the thesis.** 2.0.32's `--verdict` and the bounty
make a discharged law a trustworthy proof of *what the law says*. That is
soundness. Nothing makes the law say what the human meant; that is adequacy,
a separate property that a verified kernel cannot provide. When the same
model writes the implementation, the laws and the proofs, and a law it
cannot prove counts as failure, the easiest path is the weakest law that
checks. The models took it.

The guide's framing invites the conflation:

> Models are then guaranteed to respond with bug-free code, since Bend will demand that they provide an actual proof.

**Suggestions**, offered tentatively:

1. **Reword that sentence** along the lines of: "Bend guarantees that the
   code satisfies the laws as written, exactly and no more. A law weaker
   than intended is discharged as easily as a strong one, so what is
   guaranteed is only as strong as what the human states."
2. **Make human-authored laws the documented workflow for AI use.** The
   guide's own picture is that humans state laws and AI implements them.
   Saying so explicitly next to the laws section would steer users away from
   letting the model write both sides.
3. **A law-adequacy check by mutation.** Mutate the implementation (swap two
   match branches, duplicate or drop a list element, shift a constant by one)
   and report every law that still checks. A law that survives the mutation
   "duplicate every row" is not constraining row identity. This is mutation
   testing applied to laws. Checking was about 80 ms per file here, so
   running many mutants is cheap.
4. **A warning when every law in a file closes in one reduction step**,
   meaning none needed induction and each is a restatement of one def's own
   branch.

**Caveats.** One run per model, one task. The task was float-heavy, and
F32 is axiomatic, so some weakness was forced: nothing about the Mandelbrot
values could be proven at all. But models A, B and C found inductive
structural laws under the same constraint. Models D and E considered them and
chose ground instances instead, one of them explicitly because an induction
over `Word` looked too fragile to promise.

Happy to share the files, the compiler output at every attempt, and the
written report.
