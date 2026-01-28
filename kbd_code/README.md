# kbd_code

## Introduction
Shell and nvim tooling for my "knowledge base desk" system. Record notes on readings and random thoughts.

## Notes
Currently works via simple usb syncing.
Part of explorations repo while the repo stabilizes into something useful.

## Dependencies
- nvim
- bash
- git
- USB drive
- wsl/windows
- (optional) luised94/my_config repo: Add as extension.

## Setup
```bash
git clone https://github.com/luised94/explorations.git
```

## Usage

```bash
source ./kbd_setup.sh
```

```nvim
source ./kbd_setup.lua
luafile ./kbd_setup.lua
```

Alternatively, add code to bashrc or init.lua.

## kbd content directory
To setup the kbd content directory, see './setup_issues.md'.
After initial setup, './kbd_setup.sh' should work if the usb is installed.
