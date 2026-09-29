# Return contract

End your reply with exactly one return block: plain `key: value` lines between
the two tags, one key per line. Every key appears; an empty slot says none.
For each command the human must run, give a run line followed by its expect
line; repeat the pair for more commands.

<return>
status: done | partial | failed | design
changed: files changed or produced, or none
verified: the command you ran and its result, or "not run: <why>"
failure: the observed failure, or none
next: the next unit of work, or none
need: files the human must attach next time, or none
decide: the decision required from the human, or none
lesson: one lesson worth keeping for later tasks, or none
run: exact command for the human, or none
expect: the output that means it worked, or none
</return>
