#!/bin/bash

# --- Validate location ---
EXPECTED_DIR_NAME="explorations"
CWD=$(basename "$PWD")

if [ "$CWD" != "$EXPECTED_DIR_NAME" ]; then
  echo "Error: Script must be run from the '$EXPECTED_DIR_NAME' directory (repo root)."
  exit 1
fi

if ! git rev-parse --is-inside-work-tree &>/dev/null; then
  echo "Error: Not inside a Git worktree."
  exit 1
fi

# --- Pull all ---
git worktree list --porcelain | awk '/worktree /{print $2}' | while read worktree; do
  echo "Pulling $worktree"
  (
    cd "$worktree" || exit
    branch=$(git rev-parse --abbrev-ref HEAD)
    echo "On branch $branch"
    git pull origin "$branch"
  )
done
