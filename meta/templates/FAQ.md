# FAQ: PROJECT

> Questions asked about this project, each answered by the rule behind it
> and the command that shows the data the rule acts on. One entry each:
>
>   ## How many items does a session hold, and why that many?
>   asked: Why only 8 due?                 the words it was asked in; repeat
>   answer: The rule, in prose. Lines below it, up to a blank line, are
>     part of it.
>   see: rep status                        a command that shows the numbers now
>   rule: PLAN.md D36; src/rep/session.py  where the rule is written (gF opens)
>   date: 2026-10-05                       when the answer was last checked
>
> Write the heading one level above the question as asked: not "why 8?"
> but "how many, and why that many?". The asked: lines keep the words it
> came in, so a search for them still finds it. An entry without an
> answer is an open question.
> In nvim (`faq`): each question is one folded line; j and k move between
> them, zo opens one, zc closes it, zR opens all, / searches everything.
> From the shell: faq WORDS, faq --questions, faq --open,
> faq --add "QUESTION", faq --check. meta/README.md has the rest.
