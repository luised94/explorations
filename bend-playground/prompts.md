# Prompt kit

Every message a model receives, as fixed text. `bendlab.py` reads the blocks
between `<!-- template: NAME -->` and `<!-- end -->` verbatim, so two attempts
produced by the same strategy always received the same words. Edit the text
here, never in a chat window; an edit here changes the materials fingerprint
of the next `prompt` build, which is how a result stays attributable.

The prose outside the blocks is for you: when to send each one, and why it
exists. None of it is sent.

Order of use in one chat:

1. `task` (built into `prompt.md` by `uv run bendlab.py prompt`), fresh chat,
   memory off or a temporary chat.
2. The model replies with a plan. Send `confirm`, unchanged.
3. The model sends files. Save them into `work/<model_id>/`, run
   `uv run bendlab.py run`, and paste the generated `paste.md`. It holds
   `enumerate`, `sweep` or `audit`, chosen by the rules below.
4. Optional, after `audit`: `diagnose`.

---

## task

Replaces the original i00 prompt. Changes, each tied to an i00 finding:

- The documents are generated from the installed compiler and stamped with its
  version, instead of being frozen copies (they went stale in days).
- Marker lines before each figure, so figure checks are exact.
- A law-strength floor: at least one law needing induction, and every law
  names one wrong implementation it rejects and one it would still accept.
  Two of five i00 models passed the checker with laws that each close in one
  reduction step.
- Grid dimensions stated with a reason. Two of five shipped a Sierpinski
  figure whose cell test could not reach half its own columns.
- The four audit questions are part of the deliverable, answered with the
  trace rather than only the conclusion.

<!-- template: task -->
The reference material above is the verbatim output of `bend guide` and
`bend base` from the compiler named in its header, followed by a rules card
that grades each rule by its evidence. Treat that material as the only
authority on the language. Where the rules card and the guide disagree, the
card says why; where the card marks a rule UNVERIFIED, treat it as a
hypothesis.

Do not web search. Search results for "Bend" are dominated by Bend 1 /
HVM2, which is a different language: `bend x = init:` loops, `fork()`,
`def f(): return x`, `cargo install bend-lang`, `bend run`. None of that
is valid here. If you find yourself reaching for a construct that is not
in the material above, stop and say so instead of guessing.

TASK
Three files in one directory:
  playground.bend  - prints an ASCII Mandelbrot set, then an ASCII
                     Sierpinski triangle, to stdout via IO.print
  LAWS.bend        - laws over playground.bend
  PROOF.bend       - discharges every law

Print the line `== mandelbrot ==` immediately before the Mandelbrot figure
and the line `== sierpinski ==` immediately before the Sierpinski figure,
each on its own line.

`bend PROOF.bend` must print "All terms check." and `bend playground.bend`
must render. Both must hold. A law you cannot discharge is a failed
deliverable, not a stretch goal - so choose laws you can actually prove,
and say why you chose those.

At least one law must require induction to discharge. A law that closes in a
single reduction step - unfolding one def and selecting one match branch - is
allowed alongside, but a law set made entirely of those does not meet the
deliverable, whatever the checker prints. For every law, name in its comment
one wrong implementation the law rejects and one it would still accept. If you
cannot name one it rejects, the law constrains nothing: replace it.

CONSTRAINTS
- Full descriptive names, no abbreviations, no single-letter names,
  pattern binders included.
- Comments state why: the constraint, the failure prevented, the
  alternative rejected. Not what the line does.
- ASCII only.
- Flat and procedural where the language allows it. Bend overrides this:
  where a rule of the language forces a helper def - a match on a
  computed value, for instance - write the helper and say in a comment
  which rule forced it. Do not fight the language to satisfy this bullet.
- The program is meant to exercise parallelism. Say what shape your
  recursion gives the fork tree and why.
- State the row count and column count you chose for each figure, and why
  those numbers and not others.

PROCESS
Before writing any code, reply with: what you understand the task to be,
your strategy, and open questions. No code in that turn. Wait for me.

Once I confirm, run an adversarial pass over your own plan - what have
you not considered, what would make this go wrong - then write the files.

I will run the compiler; you cannot. So:
- Do not claim anything checks, runs, or is proven. State what you have
  verified by reading and what you are inferring.
- End with a ranked list of what you expect to fail and why, most likely
  first. I will paste the errors verbatim.
- Then, separately from that list, answer four questions about the finished
  files. A program that compiles and runs can still be wrong.
    a. For each figure, give its row count and column count, and show which
       cell positions its own cell test can fill and which it can never fill
       at any row or column. If any position can never be filled, say so.
    b. Describe your fork tree: levels, leaves, and the work on each side of
       the first split. If any parallel call's two sides differ in work, name
       which finishes first.
    c. For each law, say whether it needed induction or closed in one step.
    d. Anything that will compile, run, and still produce a result you would
       not defend.
  For (a) and (c), show the trace you followed, not only the conclusion. I
  will check your arithmetic against what the program actually prints, and a
  conclusion I cannot retrace is one I will discard.
<!-- end -->

---

## confirm

Sent after the model's plan turn, unchanged. In i00 this message was never
recorded and varied between chats, which made the chats less comparable
than they looked.

<!-- template: confirm -->
Confirmed. Proceed.
<!-- end -->

---

## enumerate (default repair)

The default reply to a compiler error. Evidence: open-source-medium took eight
rounds in i00 because it repaired only the reported line each time; in a
later fresh session this exact message got it from its one error to a
compiling program in a single round. Naming the rule forces the
generalisation the model was skipping. "Change nothing that isn't on the list"
limits churn, such as the rename-every-def guess medium once made.

<!-- template: enumerate -->
{compiler_output}

Name the rule the error enforces.
List every site in all three files that breaks that rule, each with a one-line repair note.
Fix them all in one pass.
Change nothing that isn't on the list, or say why.
<!-- end -->

---

## sweep (escalation)

`bendlab.py` suggests this when the same error class appears in two
consecutive attempts: the model is fixing sites one at a time. It asks for
the whole list before any edit.

<!-- template: sweep -->
{compiler_output}

Stop before editing. The same rule has now broken in more than one attempt
(error classes so far: {error_history}). Each fix was correct for the line
reported, and the next run found the rule broken somewhere else.

State the rule behind this error in one sentence. Then go through all three
files, every def, and list every place that rule is violated, with line
numbers, before fixing any of them. Then fix all of them in one pass,
together with the error above.

If the list contains only the reported error, say so, and say how you
checked.

You still cannot run bend. Do not claim the result checks.
<!-- end -->

---

## bare (measurement only)

The compiler output and nothing else. Use it only when the thing being
measured is unaided recovery; it is the control condition, not a good
repair message.

<!-- template: bare -->
{compiler_output}
<!-- end -->

---

## audit (after it compiles)

The only step that reached the silent defects in i00: dead figure columns,
unbalanced forks, vacuous laws, an off-by-one escape test. Its yield is high
and its error rate is not zero: one i00 audit invented a catastrophic bug
that the program's own output refuted. So it asks for traces, and every
claim in the answer gets checked against the run before it is believed.

<!-- template: audit -->
Both commands pass now, so the deliverable is met. Before I close this out I
want one more pass, and I want it done by reading, not by guessing at what I
might say next.

A program that compiles and runs can still be wrong. Answer these four:

1. State the row count and the column count of each of the two figures, as
   your code actually produces them. Then, for the figure's own cell test,
   show which cell positions in that grid can be filled and which can never
   be, whatever the row and column. If any position can never be filled, say
   so and say why.

2. Describe the shape of your fork tree as a tree: how many levels, how many
   leaves, and how much work sits on each side of the first split. If the two
   sides of any parallel call do different amounts of work, name which one
   finishes first.

3. For each law you stated: did discharging it require induction, or does it
   close in a single reduction step? For the single-step ones, say what a
   reader learns from the law that they could not already read off the
   function's type signature.

4. Anything else in the three files that will compile, run, and still produce
   a result you would not defend.

Show the trace behind each answer, not only the conclusion. I will check it
against what the program prints. You still cannot run bend. Do not fix
anything yet - answer first, then I will tell you what to change.
<!-- end -->

---

## diagnose (feedback on the materials)

Asks the model to classify each error it hit against the documents. The
forced classification is the point: asked only "what was missing", a model
files its own mistakes as documentation gaps. Every quotation in the answer
must be checked against the documents, with markdown emphasis stripped
before searching (a plain-text search once missed a real quotation written
as "checked \*live\*").

<!-- template: diagnose -->
Separate question, about the materials rather than your code.

Go back through every compiler error you hit in this session, including the
first one, and classify each into exactly one of:

  STATED  - the rule was in the material you were given and you missed or
            misread it. Quote the sentence exactly. Say what made it easy to
            miss.
  ABSENT  - the rule was in none of the material. Write the sentence you
            would add, and say which document and section it belongs in.
  WRONG   - the material says something misleading or false as written.
            Quote it exactly and say what it should say instead.

Be strict about STATED: if the rule is in the text at all, even as one
clause with no example, it is STATED, and the "easy to miss" note is where
that goes. I will check every quotation against the documents.

Then:
1. Which parts of the material did you actually use while writing the code,
   and which did you read once and never return to?
2. Name something you believed about Bend while writing the first version
   that turned out to be false, and say what in the material led you to it.

This is for revising the material, not for grading you.
<!-- end -->

---

## notes-preamble (carrying a model's own notes forward)

Put this above any notes a previous session wrote for itself before pasting
them into a new session. Evidence: open-source-medium's 20-note self-written
catalog got a fresh session compiling after one error, and also stated three
rules that other models' passing code refutes. The session obeyed all three,
and they locked in its unbalanced fork, its trivial laws and a false bug
report about the guide. Grading the notes is what the catalog's own note 19
proposed and never applied to itself.

<!-- template: notes-preamble -->
Below are notes that a previous session wrote for itself. They are not
documentation, and some of them may be wrong. Each rule is marked VERIFIED (a
compiler run confirmed it), STATED (it is in the guide or Base) or UNVERIFIED
(inferred from one session). Treat UNVERIFIED rules as hypotheses: when one
of them blocks a design you want, say so and check it against the guide and
Base instead of obeying it.
<!-- end -->
