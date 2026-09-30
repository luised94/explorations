# rep conventions

date: 2026-09
status: locked for M2 (the parser implements exactly this; changes go
through PLAN.md decision D4 and a note in the changelog at the bottom)

This is the whole grammar of a library file. You write a question and an
answer. Everything else is optional or written by the tool.

## Example

```
## @Lehninger2021

### Q: What does Km measure?
id: km-measure-7q2m
A: The substrate concentration at which velocity is half of Vmax.

### Q: How does the proton gradient drive ATP synthesis?
id: proton-gradient-drive-k3xa
source: @Lehninger2021:p712
tags: #atp #chemiosmosis
attempt: typed
criteria:
    > the electron transport chain builds the H+ gradient
    > H+ flows back through Fo, turning the rotor
    > rotation drives F1 to phosphorylate ADP
?: is the c-ring stoichiometry worth its own item?
```

## Files

- Library files live in `<data root>/library/` and end in `.md`.
- One file per source by default: `library/<citekey>.md`. Topic files for
  your own synthesis are allowed: `library/<topic>.md`. The parser reads
  every file the same way; the file name carries no meaning.
- Order inside a file is the default order in which new items are
  introduced, so a file written while reading keeps the reading order.
- Text before the first item that is not a `## ` heading is free notes and is
  ignored.

## Line kinds

A line is classified by its first characters. Nothing else is structure.

| Line                          | Meaning                                                       |
|-------------------------------|---------------------------------------------------------------|
| `## @citekey`                 | source section; sets the default source for items below it    |
| `## any other text`           | topic section; clears the default source                      |
| `### Q: text`                 | starts an item; the text is the question                      |
| `### Q:` (nothing after)      | starts an item; the question is the `>` block that follows    |
| `key: value`                  | a field of the current item (keys below)                      |
| `key:` (nothing after)        | a field whose value is the `>` block that follows             |
| `    > text`                  | block content under the preceding marker (kbd convention)     |
| `?: text`                     | open question (kbd meaning); kept, listed by lint             |
| blank line                    | ignored                                                       |

An item ends at the next `### ` or `## ` heading, or at the end of the file.
Blank lines inside an item do not end it.

Block content: each line is indented and starts with `>`. A line containing
only the indent and `>` is a paragraph break inside the block. The block ends
at the first line that is not block content.

## Fields

| Field                        | Required        | Default                  | Written by                         |
|------------------------------|-----------------|--------------------------|------------------------------------|
| question (`### Q:`)          | yes             | -                        | you                                |
| `A:` answer                  | `A:` or `criteria:` | -                    | you                                |
| `criteria:` checklist        | `A:` or `criteria:` | -                    | you                                |
| `id:`                        | yes             | -                        | the tool, never you (see IDs)      |
| `source: @citekey:location`  | no              | the `## @citekey` above  | you, or the capture key            |
| `tags: #tag #tag`            | no              | none                     | you                                |
| `check:` self, exact, numeric| no              | `self`                   | you                                |
| `attempt:` recall, typed     | no              | `recall`                 | you                                |
| `by: model:<name> <llm file>`| no              | you                      | `rep accept`                       |

- `criteria:` is a checklist. In a session you answer `y` only if every
  element is present. When both `A:` and `criteria:` exist, `A:` is shown at
  reveal and `criteria:` is what you grade against.
- `check: exact` and `check: numeric` imply `attempt: typed`, and need a
  one-line `A:` (a block answer cannot be typed on one line). Writing
  `attempt: recall` with either is an error. Reasons: PLAN.md D20.
- `check: exact` passes when your typed answer equals `A:` after trimming the
  ends and turning each run of spaces into one space. Case, accents and
  punctuation count: `Paris` is not `paris`.
- `check: numeric`: `A:` is a number, optionally with `+-` and a tolerance,
  absolute or in percent of the answer:

  ```
  A: 9.81
  A: 9.81 +- 0.01
  A: 6.022e23 +- 0.1%
  ```

  A number is an optional sign, digits with an optional decimal point, and
  an optional exponent (`1.5e-3`). No thousands separators, decimal commas,
  fractions or units: put the unit and the expected form in the question
  ("in m/s^2, to two decimals"). Without a tolerance your answer must equal
  `A:` as a number (`9.810` equals `9.81`); with one, the edge passes.
- `attempt: recall` means: think of the answer, press a key to commit, then
  see it. `attempt: typed` means: type the answer, then see it. Both commit
  before reveal.
- Locations follow the kbd location specifiers: `p42`, `pp42-45`, `ch3`,
  `S2.1`, `fig3`, `t12m34s`. A citekey not in the bib is written with the kbd
  `??` suffix, for example `@Matsui1980??`.
- Tags follow kbd: lowercase, underscore-separated, acronyms uppercase.
- An unknown field is kept and reported by lint as a warning, so a future
  field needs no migration.

Not in v1, on purpose: `requires:` (its meaning moves to the concept layer in
M5), variant pools (arrive with generated problems), cloze deletions,
`status:` (suspension is an event, recorded by the tool).

## IDs

- Written by the tool: on save in nvim (`rep stamp`), by `rep add`, and by
  `rep accept`. You never type one.
- Form: up to three words from the question, lowercase ASCII with accents
  stripped and common words dropped, then a hyphen and four characters from
  the lowercase Crockford base32 alphabet (`0-9 a-z` without `i l o u`).
  Example: `km-measure-7q2m`. A question with no ASCII letters gets `q-`
  followed by six such characters.
- An ID never changes after the item's first review, even if you reword the
  question. The ID is an identity, not a title.
- A change of meaning is a new item: delete the old block (its history is kept
  in the events and reported as orphaned) and write a new one.

## Item rules

- One fact or one skill per item (minimum information). A question that asks
  three things fails as a whole when you miss one, and the grade can no longer
  say what you forgot. Split facts; keep an explanation as one item with a
  `criteria:` checklist.
- Each language direction is its own item: recognizing and producing a word
  are different memories.
- Content is UTF-8 and is normalized to NFC when read. IDs, field names and
  markers are ASCII.

## Changelog

```
2026-09-30  First version, locked with PLAN.md.
2026-09-30  M2: exact-match rule and numeric answer syntax fixed (PLAN.md D20).
```
