# Setup
## Introduction
Quick summary of how the repo was setup. Does use functionality from luised94/my_config repo.
I started the repo under the explorations repo. I start under explorations before shifting to self-contained repo.

## Dependencies
- luised94/my_config
- uv
- python
- jq
- sqlite3

See pyproject.toml for python libraries.

## Bash commands

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh
uv --version # Check uv is working.

git checkout -b proj/llms
git push -u origin proj/llms
git switch main
new_worktree proj/llms # new_worktree is from the my_config repo. Use git worktree add <options>

cd ../explorations-proj-llms
git status; git pull # check if you want
mkdir llms/ # Holds code for llms project
cd llms/
uv init --python 3.12

# Install jq and sqlite3
apt install jq sqlite3

# Test
jq --help
sqlite3 --help

# Document
touch setup.md # This document.
nvim setup.md # Write the things.
```



