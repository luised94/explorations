#!/bin/bash
# Render all of the qmd files.

# Configuration
CV_FILENAME="luis_martinez_cv.qmd"
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

# --- Render all ---
git worktree list --porcelain | awk '/worktree /{print $2}' | while read wt; do
  CV_PATH="$wt/cv_in_quarto/${CV_FILENAME}"
  if [ -f "$CV_PATH" ]; then
    echo "Rendering CV in: $wt"
    echo "PATH: ${CV_PATH}"
    #quarto render "$CV_PATH"
  else
    echo "Skipped: No CV found in $wt"
  fi
done
