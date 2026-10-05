# Threads: the kinds, and how to start each one

date: 2026-10-05
Written at the close of rep's thread 3, from three threads of practice.
A thread is one chat. Its kind decides its role, its opening line, what
it is given, and how it ends. The files carry everything between threads:
what one chat knew and the files do not say is lost.

## 1. Before any thread

- The working defaults live in the claude.ai Preferences field and load
  into every chat. Modes are switched by the literal phrases "design
  mode" and "implement mode". No mode named means design mode.
- Check whether the chat can run code (a sandbox: it can unpack a tar
  and run tests). Without one, it cannot verify anything: it must give
  the exact commands, the expected output and checksums instead, and you
  run them (the "make verifiable" rule in the defaults).
- Method prompts (llm_playbook/prompts/) act only when pasted. Paste the
  one a thread's kind calls for (section 2) into its first message.
- Length bounds a thread, not the work: start a new chat at a commit
  boundary after about six commits, or as soon as the chat feels long.
  A long chat forgets its early instructions.

## 2. The kinds

| kind | purpose | role and mode | paste |
|---|---|---|---|
| build | a milestone, from plan to commits | DESIGN until a plan is locked, then IMPL | find-the-isomorph, survey-the-space, adversarial-review at plan lock |
| continuation | the same work, in a fresh chat | as the old chat was, usually implement mode | nothing new |
| rolling | fixes while using what was built | IMPL, fixes only | runtime-verification when a fix is subtle |
| strategy | read the data of a period, decide continue or pivot | DESIGN | survey-the-space, adversarial-review |
| spike | one risky question, the cheapest experiment | DESIGN, then a throwaway | spike-and-verify |
| review | a fresh reader attacks a series or a plan | DESIGN, reports only | adversarial-review or plan-review |

- build: ends with the series committed and verified, the project's
  docs updated, and a KICKOFF.md for whatever comes next.
- continuation: the old chat's last response and its commands' output
  are attached; the new chat verifies the pack and carries on. It does
  not reopen decisions.
- rolling: a fix is a bug or a friction whose remedy changes no
  decision. Anything that would change one is written down (the
  project's KICKOFF or notes) for the strategy thread, not done. One
  commit per fix, each with a test that fails without it.
- strategy: reads the period's reports before forming views; ends with
  a decision recorded (continue, adjust, or pivot, with the options
  scored) and the kickoff for the next build thread.
- spike: ends with a finding written down (rep keeps FINDINGS.md) and
  the experiment thrown away or kept as a test.
- review: has not seen the work being made, so the work does not grade
  itself. It reports findings ranked; the build thread fixes them.

## 3. Starting a thread in the browser

1. In the old chat: the last commit is applied, tested and committed on
   your machine, and its output pasted back.
2. Pack the repository's directories at HEAD, each under its own name
   (one name for all makes each archive overwrite the last):

       D="$(wslpath "$(cmd.exe /c 'echo %USERPROFILE%' 2>/dev/null | tr -d '\r')")/Downloads"
       cd ~/personal_repos/explorations
       H=$(git rev-parse --short HEAD)
       for part in rep pyutils meta; do git archive --format=tar.gz -o "$D/pack-$H-$part.tar.gz" HEAD "$part/"; done
       ls -l "$D"/pack-"$H"-*.tar.gz
       # expect: three files, rep, pyutils and meta

3. Open a new chat on claude.ai. Attach the packs, plus what the kind
   needs (section 2): for a continuation or rolling thread, the old
   chat's last response and the output of its commands; for a strategy
   thread, the reports.
4. First message: the opening line from the project's KICKOFF.md, then
   the ad hoc block (section 4), then any method prompt to paste.
5. The new thread's first job is clone-and-verify (rep/BUILDING.md
   section 1): it checks the packs' commit id against the HEAD you
   report, and the test counts file by file against STATUS.md. Do not
   let it change anything before that matches.

## 4. The ad hoc block

What you know that the files do not. Short is fine; leave lines out
rather than guess.

    Opening: <the line from KICKOFF.md, with its mode phrase>
    HEAD: <git log --oneline -1>
    Today: <date>, day <N> of the period
    Since the last thread: <what you did, what happened>
    Context: <anything the files cannot know: deadlines, energy, time available>
    Asks: <what you want from this thread, in order>
    Not now: <what to leave alone>

## 5. When something goes wrong

| what | do |
|---|---|
| the chat got long mid-series | finish the commit in hand, pack, open a continuation |
| the pack's commit id is not your HEAD | re-pack; never let a thread build on the wrong base |
| the chat cannot run code | it switches to making things verifiable; you run every command |
| a fix in a rolling thread turns into a design question | write it down for the strategy thread; stop that fix |
| a thread contradicts a recorded decision | point it at the decision; it argues for a change or follows it |
| you are away for days | nothing is lost: the files and the packs hold the state |
