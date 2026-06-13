#!/usr/bin/env bash
# ==============================================================================
# Script: move_prompts_to_review.sh
# Purpose: Recursively relocate prompt files from
#          ~/personal_repos/explorations/llms/prompts
#          to $KBD_DIR/prompts/for_review while preserving subdirectory
#          structure, auto-renaming on collisions, with git-aware batch commits.
# ==============================================================================

set -o nounset
set -o pipefail

# ------------------------------------------------------------------------------
# PHASE 1: CONFIGURATION
# ------------------------------------------------------------------------------

readonly SCRIPT_NAME="move_prompts_to_review.sh"
readonly SOURCE_DIR="${HOME}/personal_repos/explorations/llms/prompts"
readonly BATCH_SIZE=25
readonly GIT_COMMIT_MESSAGE_PREFIX="chore: relocate prompts batch"

# Dry-run flag, overridable via --execute
DRY_RUN=true
for arg in "$@"; do
    case "$arg" in
        --execute) DRY_RUN=false ;;
        *)
            printf "[FATAL] Unknown argument: %s\n" "$arg" >&2
            printf "Usage: %s [--execute]\n" "${SCRIPT_NAME}" >&2
            exit 1
            ;;
    esac
done
readonly DRY_RUN

# Target directory depends on KBD_DIR - will be set after preflight
TARGET_PARENT_DIR=""

# ------------------------------------------------------------------------------
# PHASE 2: PREFLIGHT CHECKS
# ------------------------------------------------------------------------------

if [[ -z "${KBD_DIR:-}" ]]; then
    printf "[FATAL] KBD_DIR is not set or not exported.\n" >&2
    printf "Please export it before running this script:\n" >&2
    printf "    export KBD_DIR=/home/lius/personal_repos/kbd\n" >&2
    exit 1
fi
readonly KBD_DIR

if ! command -v git >/dev/null 2>&1; then
    printf "[FATAL] git binary not found in PATH\n" >&2
    exit 1
fi

if [[ ! -d "${SOURCE_DIR}" ]]; then
    printf "[FATAL] Source directory does not exist: %s\n" "${SOURCE_DIR}" >&2
    exit 1
fi

if [[ ! -r "${SOURCE_DIR}" ]]; then
    printf "[FATAL] Source directory not readable: %s\n" "${SOURCE_DIR}" >&2
    exit 1
fi

printf "[INFO] Preflight checks passed\n"

# ------------------------------------------------------------------------------
# PHASE 3: PREPROCESSING / DERIVED VALUES
# ------------------------------------------------------------------------------

TARGET_PARENT_DIR="${KBD_DIR}/prompts/for_review"
readonly TARGET_PARENT_DIR

SOURCE_RESOLVED=$(eval echo "${SOURCE_DIR}")
TARGET_RESOLVED=$(eval echo "${TARGET_PARENT_DIR}")

if [[ ! -d "${SOURCE_RESOLVED}" ]]; then
    printf "[FATAL] Resolved source path does not exist: %s\n" "${SOURCE_RESOLVED}" >&2
    exit 2
fi

printf "[INFO] Source root: %s\n" "${SOURCE_RESOLVED}"
printf "[INFO] Target root: %s\n" "${TARGET_RESOLVED}"

# ------------------------------------------------------------------------------
# PHASE 4: ASSERTIONS AND ERROR HANDLING (Data Gathering)
# ------------------------------------------------------------------------------

declare -a PROMPT_FILES=()
declare -i FILE_COUNT=0

temp_file=$(mktemp) || {
    printf "[FATAL] Cannot create temporary file for file listing\n" >&2
    exit 3
}

find "${SOURCE_RESOLVED}" -type f -print0 > "${temp_file}" 2>/dev/null
if [[ $? -ne 0 ]]; then
    rm -f "${temp_file}"
    printf "[FATAL] find command failed on source directory\n" >&2
    exit 3
fi

while IFS= read -r -d '' file_path; do
    PROMPT_FILES+=("${file_path}")
    FILE_COUNT+=1
done < "${temp_file}"
rm -f "${temp_file}"

if [[ ${FILE_COUNT} -eq 0 ]]; then
    printf "[FATAL] No prompt files found in source tree: %s\n" "${SOURCE_RESOLVED}" >&2
    exit 4
fi

printf "[INFO] Discovered %d prompt files (recursively)\n" "${FILE_COUNT}"

# ------------------------------------------------------------------------------
# PHASE 5: MAIN LOGIC (Processing Phase)
# ------------------------------------------------------------------------------

declare -i SUCCESS_COUNT=0
declare -i FAIL_COUNT=0
declare -i BATCH_NUMBER=0
declare -a CURRENT_BATCH=()
declare -i BATCH_ITEM_COUNT=0

# Early check: target is inside a git repository (unless dry-run)
if [[ "${DRY_RUN}" != "true" ]]; then
    if [[ ! -d "${TARGET_RESOLVED}" ]]; then
        mkdir -p "${TARGET_RESOLVED}" 2>/dev/null
        if [[ $? -ne 0 ]]; then
            printf "[FATAL] Failed to create target root directory: %s\n" "${TARGET_RESOLVED}" >&2
            exit 5
        fi
        printf "[INFO] Created target root directory: %s\n" "${TARGET_RESOLVED}"
    fi
    cd "${TARGET_RESOLVED}" || { printf "[FATAL] Cannot change to target root\n" >&2; exit 5; }
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        printf "[ERROR] Target directory is not inside a git repository. Aborting.\n" >&2
        exit 6
    fi
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
    printf "[INFO] Git repository root: %s\n" "${repo_root}"
fi

# Inline batch commit helper
perform_batch_commit() {
    if [[ ${BATCH_ITEM_COUNT} -eq 0 ]]; then
        return
    fi

    BATCH_NUMBER+=1
    local commit_msg="${GIT_COMMIT_MESSAGE_PREFIX} ${BATCH_NUMBER} (${BATCH_ITEM_COUNT} files)"

    if [[ "${DRY_RUN}" == "true" ]]; then
        printf "[DRY-RUN] Would stage and commit batch %d: '%s'\n" "${BATCH_NUMBER}" "${commit_msg}"
        SUCCESS_COUNT+=BATCH_ITEM_COUNT
        CURRENT_BATCH=()
        BATCH_ITEM_COUNT=0
        return
    fi

    cd "${TARGET_RESOLVED}" || {
        printf "[ERROR] Cannot enter target root for git operations\n" >&2
        FAIL_COUNT+=BATCH_ITEM_COUNT
        CURRENT_BATCH=()
        BATCH_ITEM_COUNT=0
        return
    }

    git add . 2>&1
    if [[ $? -ne 0 ]]; then
        printf "[ERROR] Git stage failed for batch %d\n" "${BATCH_NUMBER}" >&2
        FAIL_COUNT+=BATCH_ITEM_COUNT
    else
        git commit -m "${commit_msg}" 2>&1
        if [[ $? -ne 0 ]]; then
            printf "[ERROR] Git commit failed for batch %d\n" "${BATCH_NUMBER}" >&2
            FAIL_COUNT+=BATCH_ITEM_COUNT
        else
            SUCCESS_COUNT+=BATCH_ITEM_COUNT
            printf "[INFO] Committed batch %d: %s\n" "${BATCH_NUMBER}" "${commit_msg}"
        fi
    fi

    CURRENT_BATCH=()
    BATCH_ITEM_COUNT=0
}

# Helper: generate a non-colliding name by appending _1, _2, . before extension
generate_unique_name() {
    local base_target="$1"      # full path originally desired
    local dir=$(dirname "$base_target")
    local fname=$(basename "$base_target")

    # If no extension, treat whole name as stem
    local stem="${fname%.*}"
    local ext=""
    if [[ "$fname" == *.* ]]; then
        ext=".${fname##*.}"
    fi

    local candidate="$base_target"
    local counter=1
    while [[ -e "$candidate" ]]; do
        candidate="${dir}/${stem}_${counter}${ext}"
        ((counter++))
    done
    echo "$candidate"
}

# Move files while preserving subdirectory structure, auto-renaming on collision
cd "${SOURCE_RESOLVED}" || { printf "[FATAL] Cannot change to source root\n" >&2; exit 5; }

for file_path in "${PROMPT_FILES[@]}"; do
    rel_path="${file_path#${SOURCE_RESOLVED}/}"
    desired_target="${TARGET_RESOLVED}/${rel_path}"
    target_dir=$(dirname "${desired_target}")

    # Ensure target subdirectory exists (real run only)
    if [[ "${DRY_RUN}" != "true" ]]; then
        if [[ ! -d "${target_dir}" ]]; then
            mkdir -p "${target_dir}" 2>/dev/null
            if [[ $? -ne 0 ]]; then
                printf "[ERROR] Failed to create target subdirectory: %s\n" "${target_dir}" >&2
                FAIL_COUNT+=1
                continue
            fi
        fi
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
        # Simulate rename if needed: we can't check -e, so just show what we'd do
        # For simplicity, we'll pretend no collision in dry-run to keep output clean,
        # but if we want exact simulation we'd need to track dry-run moves ourselves.
        # Since dry-run doesn't alter filesystem, we'll just display the desired target.
        final_target="$desired_target"
        printf "[DRY-RUN] Would move: %s -> %s\n" "${rel_path}" "${final_target}"
        CURRENT_BATCH+=("${rel_path}")
        BATCH_ITEM_COUNT+=1
        if [[ ${BATCH_ITEM_COUNT} -ge ${BATCH_SIZE} ]]; then
            perform_batch_commit
        fi
    else
        # Real move: find unique name if conflict exists
        final_target=$(generate_unique_name "$desired_target")
        mv "${file_path}" "${final_target}" 2>/dev/null
        if [[ $? -ne 0 ]]; then
            printf "[ERROR] Failed to move: %s\n" "${rel_path}" >&2
            FAIL_COUNT+=1
        else
            if [[ "$final_target" != "$desired_target" ]]; then
                printf "[INFO] Renamed to avoid collision: %s -> %s\n" "${rel_path}" "$(basename "$final_target")"
            fi
            CURRENT_BATCH+=("$(basename "$final_target")")
            BATCH_ITEM_COUNT+=1
            if [[ ${BATCH_ITEM_COUNT} -ge ${BATCH_SIZE} ]]; then
                perform_batch_commit
            fi
        fi
    fi
done

# Commit final partial batch
perform_batch_commit

# ------------------------------------------------------------------------------
# PHASE 6: SUMMARY / FINAL ASSERTIONS / ERROR HANDLING
# ------------------------------------------------------------------------------

printf "\n[INFO] Running post-migration validation...\n"

if [[ "${DRY_RUN}" == "true" ]]; then
    printf "[DRY-RUN] Skipping real filesystem checks.\n"
else
    remaining_count=$(find "${SOURCE_RESOLVED}" -type f 2>/dev/null | wc -l)
    target_count=$(find "${TARGET_RESOLVED}" -type f 2>/dev/null | wc -l)
    printf "[INFO] Files remaining in source: %d\n" "${remaining_count}"
    printf "[INFO] Files now in target (including any renames): %d\n" "${target_count}"
fi

separator="================================================"

printf "\n%s\n" "${separator}"
printf "MIGRATION SUMMARY\n"
printf "%s\n" "${separator}"
printf "Total files discovered:  %d\n" "${FILE_COUNT}"
printf "Successfully moved:      %d\n" "${SUCCESS_COUNT}"
printf "Failed:                  %d\n" "${FAIL_COUNT}"
printf "Total batches committed: %d\n" "${BATCH_NUMBER}"
printf "%s\n" "${separator}"

if [[ "${DRY_RUN}" != "true" ]]; then
    if [[ ${FAIL_COUNT} -gt 0 ]] || [[ ${SUCCESS_COUNT} -eq 0 ]]; then
        printf "[FATAL] Migration incomplete or failed. Review errors above.\n" >&2
        exit 7
    fi
else
    printf "[DRY-RUN] Simulation complete. No actual changes made.\n"
fi

printf "[END] Script completed successfully.\n"
