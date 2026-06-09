# code-dojo

Personal infrastructure for studying the source code of tools I use daily.

## What This Is

This project has two parts:

**~/code-dojo/** is a plain directory (not a git repository) containing full
git clones of upstream projects. These clones are study material -- for reading,
navigating, and analyzing source code. They are not forks, not vendored
dependencies, and not contribution checkouts.

**~/personal_repos/explorations/dojo-code/** (this repository) contains the
tooling that operates on those clones: a bootstrap script that clones from a
manifest, utility functions for opening files during study sessions, and
documentation.

## Study Targets

| Project | Why Study It |
|---------|-------------|
| Neovim | Daily editor. Understand the event loop, Lua runtime embedding, and plugin architecture to write better plugins and debug configuration issues. |
| tmux | Daily terminal multiplexer. Understand the client-server model, window/pane lifecycle, and input handling to debug session issues and customize behavior. |
| SQLite | Used in many tools and pipelines. Understand the virtual machine, B-tree storage engine, and query planner as a reference for how production C is structured. |
| Git | Daily version control. Understand the object model, packfile format, and merge machinery to debug confidently and extend workflows. |

## Quick Start

Clone this repository and run the bootstrap script:

    cd ~/personal_repos/explorations/dojo-code
    chmod +x bootstrap.sh
    ./bootstrap.sh

This reads manifest.txt and clones each project into ~/code-dojo/. Existing
directories are skipped.

## Usage

### bootstrap.sh

Clone all projects (skip any that already exist):

    ./bootstrap.sh

Nuke and reclone all projects:

    ./bootstrap.sh --force

Nuke and reclone a single project:

    ./bootstrap.sh --force neovim

### Adding a new project

Add a line to manifest.txt in the format `project_name|git_url|git_ref`, then
run `./bootstrap.sh`. Only the new project will be cloned.

### Updating a project version

Edit the git_ref field in manifest.txt, then run `./bootstrap.sh --force <name>`
to reclone at the new tag.

## Study Utilities

Source the functions file to make study commands available in your shell:

    source scripts/dojo_functions.sh

### dojo_open_most_edited_files

Open the most frequently edited files in a project's git history. Useful for
finding the core files where most development happens.

    dojo_open_most_edited_files neovim       # top 20 files (default)
    dojo_open_most_edited_files sqlite 10    # top 10 files

Files that no longer exist in the working tree are filtered out. Nvim opens
with the working directory set to the project root, so Telescope works
immediately.

### dojo_open_random_source_file

Open a random source file from a project. Useful for serendipitous exploration
of unfamiliar areas of a codebase.

    dojo_open_random_source_file tmux

Matches files with these extensions: .c, .h, .lua, .py, .sh, .md, .rb, .rs,
.go. The .git directory is excluded.

### Shell aliases

Add to your .bashrc or .zshrc for shorter invocations:

    source ~/personal_repos/explorations/dojo-code/scripts/dojo_functions.sh
    alias dme='dojo_open_most_edited_files'
    alias drf='dojo_open_random_source_file'

## Zotero BibTeX Entries

These use the <Author><Year><FirstWord> citation key format and the "Computer
Program" item type in Zotero.

    @software{Neovim2026Vim,
      title   = {Neovim: Vim-Fork Focused on Extensibility and Usability},
      author  = {{Neovim Contributors}},
      year    = {2026},
      url     = {https://github.com/neovim/neovim},
      version = {0.12.2}
    }

    @software{Marriott2026tmux,
      title   = {tmux: Terminal Multiplexer},
      author  = {Marriott, Nicholas},
      year    = {2026},
      url     = {https://github.com/tmux/tmux},
      version = {3.6b}
    }

    @software{Hipp2026SQLite,
      title   = {SQLite},
      author  = {Hipp, D. Richard},
      year    = {2026},
      url     = {https://github.com/sqlite/sqlite},
      version = {3.53.2}
    }

    @software{Torvalds2026Git,
      title   = {Git},
      author  = {Torvalds, Linus and Hamano, Junio C.},
      year    = {2026},
      url     = {https://github.com/git/git},
      version = {2.54.0}
    }
