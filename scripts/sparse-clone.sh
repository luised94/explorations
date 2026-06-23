#!/usr/bin/env bash
# Sparse shallow clone helper
# Fetches ONLY the named subdirectory of a public repo (no blobs for the rest).
#
# Usage:
#   ./sparse-clone.sh <repo-url> <subdir> [dest] [branch]
#
# Examples:
#   ./sparse-clone.sh https://github.com/luised94/explorations.git drill
#   ./sparse-clone.sh https://github.com/luised94/explorations.git drill /tmp/repo main
#
# Args:
#   repo-url  (required)  HTTPS URL of the public repo
#   subdir    (required)  directory inside the repo to materialize
#   dest      (optional)  local path to clone into (default: /tmp/repo)
#   branch    (optional)  branch to clone (default: remote default)

set -euo pipefail

REPO_URL="${1:?need a repo URL}"
SUBDIR="${2:?need a subdirectory to check out}"
DEST="${3:-/tmp/repo}"
BRANCH="${4:-}"

BRANCH_ARG=()
[ -n "$BRANCH" ] && BRANCH_ARG=(--branch "$BRANCH")

# 1. sparse shallow clone (no file blobs yet)
git clone --depth 1 --filter=blob:none --sparse "${BRANCH_ARG[@]}" "$REPO_URL" "$DEST"
cd "$DEST"

# 2. materialize only the requested subdir
git sparse-checkout set "$SUBDIR"

# 3. report what landed
echo "=== top level ==="
ls -la
echo "=== $SUBDIR contents ==="
ls -laR "$SUBDIR" | head -60

# 4. show the commit (compare against your local HEAD)
echo "=== HEAD commit ==="
git log -1 --oneline --decorate
git rev-parse HEAD
