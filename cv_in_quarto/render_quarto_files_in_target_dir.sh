#!/bin/bash

# ==============================================================================
# 1. CONFIGURATION
# ==============================================================================
# Absolute path expansion safely handles the tilde '~'
readonly TARGET_DIR=$(eval echo "~/personal_repos/explorations/cv_in_quarto")
readonly LOG_FILE="${TARGET_DIR}/render_process.log"
readonly EXPECTED_EXTENSION="pdf" # Change to 'html' or 'docx' if your Quarto default differs

# ==============================================================================
# 2. PREFLIGHT CHECKS
# ==============================================================================
# Ensure required binary dependency exists
if ! command -v quarto &>/dev/null; then
    echo "CRITICAL ERROR: 'quarto' CLI is not installed or available in PATH." >&2
    exit 1
fi

# ==============================================================================
# 3. PREPROCESSING / DERIVED VALUES
# ==============================================================================
declare -a QMD_FILES=()
declare -i TOTAL_FILES=0
declare -i SUCCESS_COUNT=0
declare -i FAILURE_COUNT=0
declare -i STRUCTURAL_DEFECTS=0

# Ensure target directory structure exists before writing logs
mkdir -p "$TARGET_DIR"
: > "$LOG_FILE"

# ==============================================================================
# 4. ASSERTIONS AND ERROR HANDLING (Data Gathering)
# ==============================================================================
if [ ! -d "$TARGET_DIR" ]; then
    echo "CRITICAL ERROR: Target directory '$TARGET_DIR' could not be found or created." >&2
    exit 1
fi

# Populate data array using null-terminated stream
while IFS= read -r -d '' file; do
    QMD_FILES+=("$file")
done < <(find "$TARGET_DIR" -type f -name "*.qmd" -print0 2>/dev/null)

TOTAL_FILES=${#QMD_FILES[@]}

if [ "$TOTAL_FILES" -eq 0 ]; then
    echo "WARNING: No .qmd files found in '$TARGET_DIR'. Nothing to process."
    exit 0
fi

# ==============================================================================
# 5. MAIN LOGIC (Processing Phase)
# ==============================================================================
echo "Starting batch render pipeline of $TOTAL_FILES file(s)..."
echo "Target: $TARGET_DIR"
echo "------------------------------------------------------------"

for qmd_file in "${QMD_FILES[@]}"; do
    echo "Processing: $(basename "$qmd_file")"
    
    # Execute Quarto compilation, redirecting outputs cleanly to log file
    if quarto render "$qmd_file" >> "$LOG_FILE" 2>&1; then
        echo "--> RENDER SUCCESS"
        ((SUCCESS_COUNT++))
    else
        echo "--> RENDER FAILED (See log for details)" >&2
        ((FAILURE_COUNT++))
    fi
done

# ==============================================================================
# 6. SUMMARY / FINAL ASSERTIONS / ERROR HANDLING (Validation Phase)
# ==============================================================================
echo "------------------------------------------------------------"
echo "Validating compiled structural outputs..."

# Post-Execution Assertions: Verify 1:1 map between inputs and compiled artifacts
for qmd_file in "${QMD_FILES[@]}"; do
    # Strip .qmd and append expected output extension
    expected_output="${qmd_file%.qmd}.${EXPECTED_EXTENSION}"
    
    if [ ! -f "$expected_output" ]; then
        echo "CRITICAL STRUCTURAL DEFECT: Missing compiled asset -> $expected_output" >&2
        ((STRUCTURAL_DEFECTS++))
    fi
done

echo "------------------------------------------------------------"
echo "Pipeline Execution Summary:"
echo "  Total QMD inputs discovered: $TOTAL_FILES"
echo "  Quarto successful renders  : $SUCCESS_COUNT"
echo "  Quarto failed renders      : $FAILURE_COUNT"
echo "  Missing output artifacts   : $STRUCTURAL_DEFECTS"

# Determine final exit state based on technical defects
if [ "$FAILURE_COUNT" -gt 0 ] || [ "$STRUCTURAL_DEFECTS" -gt 0 ]; then
    echo "Pipeline completed with errors. Data state integrity compromised." >&2
    exit 2
else
    echo "Pipeline completed successfully with zero defects. All outputs verified."
    exit 0
fi
