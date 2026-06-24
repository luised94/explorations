# Prompt: adversarial design review

A reusable design-critique pass. Born in D1 (the questions.metadata thread),
where it flipped one real decision (defer grading_kind) and confirmed the rest.

--------------------------------------------------------------------------------
USE THIS WHEN
--------------------------------------------------------------------------------
Run it before committing to a design that is COSTLY or HARD TO REVERSE:
  - a schema change (forward-only migrations: a wrong guess is unrollable)
  - a new persisted column / table / public contract
  - an abstraction or interface other code will depend on
  - a sequencing choice that gates later threads

SKIP IT WHEN
  - the change is mechanical (add a dict entry, rename, fix a typo)
  - it is trivially reversible (internal, no persistence, no callers yet)
  - you already have a real consumer dictating the shape (then just build it)

The bar is: "could a single sharp objection change WHAT I build?" If no, skip.
Running this on a one-line change is theater and trains bad instincts.

--------------------------------------------------------------------------------
HOW TO RUN
--------------------------------------------------------------------------------
Critique the current plan through each LENS below. The lenses matter; the
named personas are optional scaffolding to help generate the objection -- do
not fill them in mechanically. One genuine objection that overturns the plan is
worth more than six paragraphs of agreement. State each as an operational
heuristic, not a platitude. Ground every objection in the ACTUAL code (read it
first), not in the abstract.

LENSES (axis -- the question it forces):
  1. DATA / TRANSFORM   -- what is the real data and its shape at N, not N=1?
                           Where there is one, there are many. Is the test/transform
                           proving the bulk case or a single element?
  2. SIMPLICITY / STATE -- simplest thing that works? Can you reason about every
                           path? Is this one change or several coupled by convenience?
  3. REAL vs SPECULATIVE -- what problem does this solve NOW? Is the consumer real
                           or imagined? Architecture for a guessed future is debt.
  4. USAGE BEFORE INTERFACE -- write the calling code first; let it dictate the
                           abstraction. An interface designed before its caller
                           is usually wrong. (Did the code already tell you so?)
  5. STRUCTURE / INTENT -- does this flatten or sever a meaningful link (e.g.
                           denormalizing a derived fact)? Preserve "this deviates"
                           vs "this inherits".
  6. DOMAIN CORRECTNESS -- (project-specific; for drill: learning-science /
                           mastery framing) does the atom you are defining stay
                           unambiguous for the features that will build on it?

OUTPUT
  - For each lens: the sharpest objection, or "confirms" with one line of why.
  - A CONSENSUS ATTACK if several lenses converge (this is the signal to change
    the plan).
  - A revised plan, or an explicit "plan stands because ...".

--------------------------------------------------------------------------------
PROJECT GUARDRAILS (drill-specific; restate when porting elsewhere)
--------------------------------------------------------------------------------
  - Forward-only migrations, no down-migrations. The .db file is the user's
    ONLY copy: additive, NOT NULL DEFAULT, no data loss.
  - stdlib + Bottle only; no new runtime deps (ADR-001).
  - "Nothing too clever." Data-first, explicit declarations over magic numbers.
  - Do not fork validate_answer's qtype dispatch; columns FEED it, not fork it.
