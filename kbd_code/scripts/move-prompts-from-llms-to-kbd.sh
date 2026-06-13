#!/usr/bin/env bash
# ==============================================================================
# Script: move_prompts_to_review.sh
# Purpose: Relocate prompt files from ~/personal_repos/explorations/llms/prompts
#          to $KBD_DIR/prompts/for_review with git-aware batch commits
# ==============================================================================

set -o nounset
set -o pipefail

# ------------------------------------------------------------------------------
# PHASE 1: CONFIGURATION
# ------------------------------------------------------------------------------

readonly SCRIPT_NAME="move_prompts_to_review.sh"
readonly SOURCE_DIR="${HOME}/personal_repos/explorations/llms/prompts"
readonly TARGET_PARENT_DIR="${KBD_DIR}/prompts/for_review"
readonly BATCH_SIZE=25
readonly GIT_COMMIT_MESSAGE_PREFIX="chore: relocate prompts batch"

# Toggle for dry-run mode (true = simulate only, false = execute)
readonly DRY_RUN=true

# Dynamic path holders (filled in Phase 3)
SOURCE_RESOLVED=""
TARGET_RESOLVED=""

# ------------------------------------------------------------------------------
# PHASE 2: PREFLIGHT CHECKS
# ------------------------------------------------------------------------------

if ! command -v git >/dev/null 2>&1; then
    printf "[FATAL] git binary not found in PATH\n" >&2
    exit 1
fi

if [[ -z "${KBD_DIR:-}" ]]; then
    printf "[FATAL] KBD_DIR environment variable is not set\n" >&2
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

# Resolve paths
SOURCE_RESOLVED=$(eval echo "${SOURCE_DIR}")
TARGET_RESOLVED=$(eval echo "${TARGET_PARENT_DIR}")

if [[ ! -d "${SOURCE_RESOLVED}" ]]; then
    printf "[FATAL] Resolved source path does not exist: %s\n" "${SOURCE_RESOLVED}" >&2
    exit 2
fi

printf "[INFO] Source resolved: %s\n" "${SOURCE_RESOLVED}"
printf "[INFO] Target resolved: %s\n" "${TARGET_RESOLVED}"

# Create target directory (dry-run: only log, don't create)
if [[ "${DRY_RUN}" == "true" ]]; then
    printf "[DRY-RUN] Would create target directory: %s\n" "${TARGET_RESOLVED}"
else
    if [[ ! -d "${TARGET_RESOLVED}" ]]; then
        mkdir -p "${TARGET_RESOLVED}" 2>/dev/null
        if [[ $? -ne 0 ]]; then
            printf "[FATAL] Failed to create target directory: %s\n" "${TARGET_RESOLVED}" >&2
            exit 2
        fi
        printf "[INFO] Created target directory: %s\n" "${TARGET_RESOLVED}"
    fi
fi

# ------------------------------------------------------------------------------
# PHASE 4: ASSERTIONS AND ERROR HANDLING (Data Gathering)
# ------------------------------------------------------------------------------

declare -a PROMPT_FILES=()
declare -i FILE_COUNT=0

# Gather files using null-terminated find
temp_file=$(mktemp) || {
    printf "[FATAL] Cannot create temporary file for file listing\n" >&2
    exit 3
}

find "${SOURCE_RESOLVED}" -maxdepth 1 -type f -print0 > "${temp_file}" 2>/dev/null
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
    printf "[FATAL] No prompt files found in source directory: %s\n" "${SOURCE_RESOLVED}" >&2
    exit 4
fi

printf "[INFO] Discovered %d prompt files to migrate\n" "${FILE_COUNT}"

# ------------------------------------------------------------------------------
# PHASE 5: MAIN LOGIC (Processing Phase)
# ------------------------------------------------------------------------------

declare -i SUCCESS_COUNT=0
declare -i FAIL_COUNT=0
declare -i BATCH_NUMBER=0
declare -a CURRENT_BATCH=()
declare -i BATCH_ITEM_COUNT=0

# Early check: target is a git repo (unless dry-run)
if [[ "${DRY_RUN}" != "true" ]]; then
    cd "${TARGET_RESOLVED}" || { printf "[FATAL] Cannot change to target directory\n" >&2; exit 5; }
    if ! git rev-parse --git-dir >/dev/null 2>&1; then
        printf "[ERROR] Target directory is not a git repository. Aborting.\n" >&2
        exit 6
    fi
    repo_root=$(git rev-parse --show-toplevel 2>/dev/null)
    printf "[INFO] Git repository root: %s\n" "${repo_root}"
fi

# Helper for batch commit (embedded as a small inline procedure, but flat)
perform_batch_commit() {
    if [[ ${BATCH_ITEM_COUNT} -eq 0 ]]; then
        return
    fi

    BATCH_NUMBER+=1
    local commit_msg="${GIT_COMMIT_MESSAGE_PREFIX} ${BATCH_NUMBER} (${BATCH_ITEM_COUNT} files)"

    if [[ "${DRY_RUN}" == "true" ]]; then
        printf "[DRY-RUN] Would stage and commit batch %d: '%s'\n" "${BATCH_NUMBER}" "${commit_msg}"
        SUCCESS_COUNT+=BATCH_ITEM_COUNT   # simulate success
        CURRENT_BATCH=()
        BATCH_ITEM_COUNT=0
        return
    fi

    cd "${TARGET_RESOLVED}" || { printf "[ERROR] Cannot enter target dir\n" >&2; FAIL_COUNT+=BATCH_ITEM_COUNT; CURRENT_BATCH=(); BATCH_ITEM_COUNT=0; return; }

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

# Main move loop (flat, iterates over array)
cd "${SOURCE_RESOLVED}" || { printf "[FATAL] Cannot change to source directory\n" >&2; exit 5; }

for file_path in "${PROMPT_FILES[@]}"; do
    filename=$(basename "${file_path}")
    target_path="${TARGET_RESOLVED}/${filename}"

    # Conflict check
    if [[ -e "${target_path}" ]]; then
        printf "[WARN] Target file already exists: %s\n" "${filename}" >&2
        FAIL_COUNT+=1
        continue
    fi

    if [[ "${DRY_RUN}" == "true" ]]; then
        printf "[DRY-RUN] Would move: %s -> %s\n" "${filename}" "${target_path}"
        CURRENT_BATCH+=("${filename}")
        BATCH_ITEM_COUNT+=1
        if [[ ${BATCH_ITEM_COUNT} -ge ${BATCH_SIZE} ]]; then
            perform_batch_commit
        fi
    else
        mv "${file_path}" "${target_path}" 2>/dev/null
        if [[ $? -ne 0 ]]; then
            printf "[ERROR] Failed to move: %s\n" "${filename}" >&2
            FAIL_COUNT+=1
        else
            CURRENT_BATCH+=("${filename}")
            BATCH_ITEM_COUNT+=1
            if [[ ${BATCH_ITEM_COUNT} -ge ${BATCH_SIZE} ]]; then
                perform_batch_commit
            fi
        fi
    fi
done

# Final partial batch
perform_batch_commit

# ------------------------------------------------------------------------------
# PHASE 6: SUMMARY / FINAL ASSERTIONS / ERROR HANDLING
# ------------------------------------------------------------------------------

printf "\n[INFO] Running post-migration validation...\n"

if [[ "${DRY_RUN}" == "true" ]]; then
    printf "[DRY-RUN] Skipping real filesystem checks.\n"
    remaining_count="N/A"
    target_count="N/A"
else
    remaining_count=$(find "${SOURCE_RESOLVED}" -maxdepth 1 -type f 2>/dev/null | wc -l)
    target_count=$(find "${TARGET_RESOLVED}" -maxdepth 1 -type f 2>/dev/null | wc -l)
    printf "[INFO] Files remaining in source: %d\n" "${remaining_count}"
    printf "[INFO] Files now in target: %d\n" "${target_count}"
fi

separator="================================================"
total_processed=$((SUCCESS_COUNT + FAIL_COUNT))

printf "\n%s\n" "${separator}"
printf "MIGRATION SUMMARY\n"
printf "%s\n" "${separator}"
printf "Total files discovered:  %d\n" "${FILE_COUNT}"
printf "Successfully moved:      %d\n" "${SUCCESS_COUNT}"
printf "Failed / Skipped:        %d\n" "${FAIL_COUNT}"
printf "Total batches committed: %d\n" "${BATCH_NUMBER}"
printf "%s\n" "${separator}"

# Final assertion and exit code
if [[ "${DRY_RUN}" != "true" ]]; then
    if [[ ${FAIL_COUNT} -gt 0 ]] || [[ ${SUCCESS_COUNT} -eq 0 ]]; then
        printf "[FATAL] Migration incomplete or failed. Review errors above.\n" >&2
        exit 7
    fi
else
    printf "[DRY-RUN] Simulation complete. No actual changes made.\n"
fi

printf "[END] Script completed successfully.\n"
