# kbd_code

Shell and neovim tooling for the kbd (knowledge base desk) system.

## File Inventory

| File | Purpose |
|------|---------|
| kbd.sh | Shell aliases, functions, USB operations (sourced into bash) |
| kbd.lua | Neovim keybindings and commands (loaded as extension) |
| kbd_audit.sh | Content audit: orphan tags, missing headers, structure checks |
| kbd-normalize-tags | Tag consistency checker and fixer |

## Content Repo

The kbd content (journal.txt, source-notes.txt, projects/, etc.) lives at
`~/personal_repos/kbd/`. See that repo's README.md for file conventions.

## Dependencies

- bash 4+
- neovim 0.9+
- git
- perl (for tag normalization --fix mode)
- grep with -P (PCRE) support
- USB drive (for sync; optional for local-only use)
- WSL (Windows Subsystem for Linux)
- luised94/usb-sh repo (USB mount/sync infrastructure)

## Integration

Loaded as an extension via the my_config repo's bash chain and nvim
extension loader. Not sourced directly.

Shell: infrastructure loads `kbd.sh` after `usb.sh` in the bash chain.
Neovim: extension loader picks up `kbd.lua` after lazy.nvim setup.

## USB Setup (Reference)

First-time USB bare repo creation (from PowerShell):
```powershell
cd D:\
mkdir personal_repos
cd personal_repos
git init --bare kbd.git
```

WSL mount (required before any USB operation):
```bash
sudo mkdir -p /mnt/d
sudo mount -t drvfs D: /mnt/d -o metadata
```

If WSL reports ownership warnings:
```bash
git config --global --add safe.directory /mnt/d/personal_repos/kbd.git
```

Clone to local working directory:
```bash
git clone /mnt/d/personal_repos/kbd.git ~/personal_repos/kbd
```

After initial setup, USB operations control commit, push and pull for the kbd git repo.

---
