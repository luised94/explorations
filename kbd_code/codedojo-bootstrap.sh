#!/usr/bin/env bash
set -euo pipefail

CODE_DOJO_DIR="$HOME/code-dojo"

script_directory="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
manifest_file="$script_directory/codedojo_manifest.txt"

# -- parse arguments -------------------------------------------------------

force_mode=false
force_project_filter=""

if [[ $# -ge 1 ]] && [[ "$1" == "--force" ]]; then
    force_mode=true
    if [[ $# -ge 2 ]]; then
        force_project_filter="$2"
    fi
fi

# -- validate manifest ------------------------------------------------------

if [[ ! -f "$manifest_file" ]]; then
    echo "error: manifest not found at $manifest_file" >&2
    exit 1
fi

# -- prepare target directory -----------------------------------------------

if [[ ! -d "$CODE_DOJO_DIR" ]]; then
    mkdir -p "$CODE_DOJO_DIR"
    echo "created $CODE_DOJO_DIR"
fi

# -- clone from manifest ----------------------------------------------------

clone_count=0
skip_count=0
fail_count=0
matched_filter=false

while IFS= read -r manifest_line || [[ -n "$manifest_line" ]]; do
    if [[ -z "$manifest_line" ]]; then
        continue
    fi
    if [[ "$manifest_line" =~ ^# ]]; then
        continue
    fi

    project_name="${manifest_line%%|*}"
    remainder="${manifest_line#*|}"
    git_url="${remainder%%|*}"
    git_ref="${remainder#*|}"

    if [[ -n "$force_project_filter" ]]; then
        if [[ "$project_name" != "$force_project_filter" ]]; then
            continue
        fi
        matched_filter=true
    fi

    project_directory="$CODE_DOJO_DIR/$project_name"

    if [[ -d "$project_directory" ]]; then
        if [[ "$force_mode" == true ]]; then
            echo "removing $project_directory"
            rm -rf "$project_directory"
        else
            echo "skip: $project_name already exists at $project_directory"
            skip_count=$((skip_count + 1))
            continue
        fi
    fi

    echo "cloning $project_name ($git_ref) ..."
    if git clone --branch "$git_ref" "$git_url" "$project_directory"; then
        clone_count=$((clone_count + 1))
    else
        echo "error: failed to clone $project_name" >&2
        fail_count=$((fail_count + 1))
    fi

done < "$manifest_file"

# -- warn if filter matched nothing -----------------------------------------

if [[ -n "$force_project_filter" ]] && [[ "$matched_filter" == false ]]; then
    valid_project_names=""
    while IFS= read -r check_line || [[ -n "$check_line" ]]; do
        if [[ -z "$check_line" ]] || [[ "$check_line" =~ ^# ]]; then
            continue
        fi
        valid_project_names="$valid_project_names ${check_line%%|*}"
    done < "$manifest_file"
    echo "error: '$force_project_filter' not found in manifest" >&2
    echo "valid project names:$valid_project_names" >&2
    exit 1
fi

# -- summary -----------------------------------------------------------------

echo ""
echo "done: $clone_count cloned, $skip_count skipped, $fail_count failed"
