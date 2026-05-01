# finances.sh

Shell module for personal plain text accounting with hledger.

## Location

- Source: `~/personal_repos/explorations/finances_code/finances.sh`
- Symlink: `~/.config/mc_extensions/finances.sh`
- Load chain: `~/.bashrc`  `bash/99_extensions.sh`  `mc_extensions/finances.sh`

## Dependencies

- hledger 1.40+ in PATH (`~/.local/bin/`)
- usb.sh loaded by bash/ infrastructure (bash/06_usb.sh) before this module
- Neovim ftplugin: `~/.config/nvim/ftplugin/hledger.lua`

## Related

- Journal files and project README: `~/personal_repos/finances/`
- USB project conf: `.usb-projects/finances.conf` on USB
