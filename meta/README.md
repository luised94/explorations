# meta: tools for any project in this repository

date: 2026-10-05
Started at the close of rep's thread 3. A tool belongs here when it knows
nothing about one project: it works the same in rep/, pyutils/ or any
directory added later. A tool that knows a project's data stays in that
project (rep's `rep-week`, for example).

## Contents

| path | what |
|---|---|
| shell/meta.sh | shell functions; today only `faq` |
| nvim/faq.lua | the folded, questions-only view `faq` opens |
| templates/FAQ.md | a new FAQ.md starts from this; its header is the format |
| tests/test_faq.sh | `bash meta/tests/test_faq.sh` prints "ok: N checks" |

Load the functions as rep's are loaded: source the file, or symlink it
into the directory your bashrc sources.

    source ~/personal_repos/explorations/meta/shell/meta.sh

## The project convention

A tool finds its context from the current directory, never from a
setting:
- the repository root: `git rev-parse --show-toplevel`;
- the project: the directory directly under the root that holds the
  current directory (the root itself when standing there);
- files a tool reads are looked for from the current directory up to the
  root, nearest first, so a project's file and the repository's are
  both found from anywhere inside the project.

## faq: questions and their answers

Questions asked while using or building a project, answered where they
can be found again, and kept out of the code's comments and the design
documents: a comment explains a line, a decision record explains a
choice, an FAQ entry answers a person's question about behaviour.

Each entry answers the question one level up from how it was asked:
"why only 8 due?" becomes "how many items does a session hold, and why
that many?". The answer states the rule; `see:` gives a command that
shows the data the rule is acting on right now; `rule:` says where the
rule is written. A number changes every day; the rule and the way to
check it do not. The words it was asked in stay on `asked:` lines, so
a search for them still finds it.

    faq                    the nearest FAQ.md in nvim, one folded line per question
    faq WORDS...           every entry containing all the words, printed
    faq --questions        each question with its path:line; open ones marked
    faq --open             questions without an answer yet
    faq --add "QUESTION"   append an entry to the nearest FAQ.md, open it there
    faq --check            duplicates, and answers with no see: or rule:
    faq --help             this list

In nvim: j and k move a question at a time (each is one closed fold), zo
opens one, zc closes it, zR opens all, zM closes all, / searches inside
folds, gF on a `rule:` path opens the file. An entry added with --add is
an open question until its answer line has text: the FAQ is also the log
of what has been asked and not yet answered.

## Candidates to move here (rep's thread 4b decides)

- rep-screen (rep/shell/rep.sh): nothing in it is rep's but the folder
  it writes to.
- the code tour (rep/tools/code_tour.py): already standalone; it needs
  the project convention above instead of rep's defaults.
