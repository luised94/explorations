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
  7. DEPENDENCY QUARANTINE -- (Eskil) every dependency you do NOT control (DOM,
                           fetch, clock, storage, a library) should be reachable
                           through ONE thin seam you DO control, so call sites
                           speak your vocabulary and the thing is swappable/
                           fixable in one place. Is any external capability
                           SMEARED across modules instead of quarantined behind a
                           wrapper (the fetch/speechSynthesis pattern)? A thin
                           seam adds consistency, not behavior -- if the wrapper
                           grows logic, it is an abstraction, flag it.
  8. INSPECTABILITY / GAP -- (Victor) can you SEE the relevant state at any
                           moment, with no edit-run-hunt gap between a change and
                           observing its effect? Is state a single inspectable
                           thing, or scattered (e.g. stashed in the DOM and read
                           back)? A design you cannot observe live is a design
                           you cannot debug.
  9. ENFORCED CONSTRAINT -- (Sutherland) is each invariant MACHINE-ENFORCED where
                           it is introduced, or merely intended? An invariant not
                           yet guarded is a comment, not a constraint. Prefer
                           constraints expressed as DATA a generic checker reads
                           (a policy table, a registry) over rules humans
                           remember. Single master, instances follow (state is
                           the master; the DOM renders from it, never the reverse).
  10. AFFORDANCE TRUTH -- (Gibson; UI-facing) does the PERCEIVED affordance match
                           the REAL one? A thing that looks interactive must be
                           interactive; a thing shown hidden must not still respond
                           (the [hidden] guard: perceived state = real state).
                           Semantic elements so the affordance is readable from
                           the tag.

Two heuristics folded into the lenses above (invoke by name when useful):
  - COMPLECTION (Hickey; sharpens SIMPLICITY/STATE #2): A is complected with B
    iff a change to one forces a change to the other (a cycle, a shared mutable,
    a helper serving two meanings). "Simplest thing" means fewest such braids,
    not fewest lines. Splitting a file can MANUFACTURE complection (scattered is
    worse than long) -- a good cut adds only an import, never new indirection.
  - LOCALITY OF BEHAVIOR (Gross; sharpens STRUCTURE/INTENT #5): can you understand
    what a thing does by reading the thing, or must you chase behavior across
    distant files? Prefer behavior locatable from where it lives.

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
