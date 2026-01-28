# kbd

Personal knowledge base desk. Text files, git-backed, USB-synced.

## Structure

```
kbd/
  journal.txt    # dated entries, personal thinking
  notes.txt      # reading notes by citation key
  context.txt    # project context
  .gitignore
```

## File Formats

### journal.txt

```markdown
## 2024-01-15

Today's thoughts...

## 2024-01-14

Yesterday's entry...
```

Append new entries at bottom. 
::notAdded
Date headers inserted via `<space>kd` in nvim.
::end

### notes.txt
One section per source.
Citation key from BetterBibTeX (`auth.fold + year + title.lower.skipwords().select(1,1)`). 
Revisiting a paper? Append to existing section with date marker: `[2024-01-20] New thoughts...`

```markdown
## @smith2024emergence

Notes on this source...

## @jones2022method

Notes on another source...
```

## Workflow

::notAdded
```bash
kpull          # pull from USB
j              # open journal
n              # open notes
ksync          # commit and push to USB
```
::end

## Sync

Bare repo lives on USB. Mount required in WSL before sync:

```bash
sudo mount -t drvfs D: /mnt/d -o metadata
```

After initial setup, './kbd_setup.sh' should take care of this. If you insert the usb before './kbd_setup.sh' runs, source '/.kbd_setup.sh' manually.

## Tooling

- Shell aliases and nvim keybindings live in separate tooling repo. See: `explorations-proj-kbd_code` branch (to be extracted to own repo later).
- Works with my_config repo as an extension to the repo.
