#!/usr/bin/env bash
# Runs PROOF.bend and playground.bend for every model directory and collects
# the output of each run, labeled by model and file, into one results file.

# ---- configuration ---------------------------------------------------------

MODEL_TESTS_ROOT="/home/luis/personal_repos/explorations/bend-playground/model_tests"

# Explicit list rather than a */ glob so a stray directory (for example a
# future results/ folder) is never run as a model, and the order is fixed.
MODEL_DIRECTORY_NAMES=(
  #"claude-opus-5"
  "claude-sonnet-5"
  #"gpt5.6-terra"
  #"open-source-large"
  "open-source-medium"
)

# LAWS.bend is not run on its own: PROOF.bend imports it, so checking
# PROOF.bend already checks every law.
BEND_FILE_NAMES=(
  "PROOF.bend"
  "playground.bend"
)

TIMEOUT_SECONDS=60
RESULTS_FILE="$MODEL_TESTS_ROOT/results.txt"

# ---- run -------------------------------------------------------------------

# No `set -e`: a failing or timed-out model is a result to record, not a
# reason to stop before the remaining models run.

# Best effort to keep ANSI color escapes out of the text file; harmless if
# bend ignores it.
export NO_COLOR=1

{
  echo "Model test run: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  # Recorded because results are only comparable across runs on the same
  # compiler version.
  echo "Bend version: $(bend --version 2>&1)"
  echo "Timeout per run: ${TIMEOUT_SECONDS}s"
  echo
} > "$RESULTS_FILE"

for MODEL_DIRECTORY_NAME in "${MODEL_DIRECTORY_NAMES[@]}"; do
  MODEL_DIRECTORY_PATH="$MODEL_TESTS_ROOT/$MODEL_DIRECTORY_NAME"

  for BEND_FILE_NAME in "${BEND_FILE_NAMES[@]}"; do
    echo "===== $MODEL_DIRECTORY_NAME / $BEND_FILE_NAME =====" >> "$RESULTS_FILE"
    echo "running $MODEL_DIRECTORY_NAME / $BEND_FILE_NAME"

    if [ ! -f "$MODEL_DIRECTORY_PATH/$BEND_FILE_NAME" ]; then
      echo "MISSING: $MODEL_DIRECTORY_PATH/$BEND_FILE_NAME" >> "$RESULTS_FILE"
      echo >> "$RESULTS_FILE"
      continue
    fi

    # Run from the model directory so relative imports (./LAWS.bend) resolve
    # against that model's files, not the script's location.
    cd "$MODEL_DIRECTORY_PATH" || continue

    RUN_START_NANOSECONDS=$(date +%s%N)
    # stdin from /dev/null: a main that reads input would otherwise block
    # until the timeout. --kill-after: a bend that ignores SIGTERM still dies.
    timeout --kill-after=5 "$TIMEOUT_SECONDS" bend "$BEND_FILE_NAME" < /dev/null >> "$RESULTS_FILE" 2>&1
    BEND_EXIT_CODE=$?
    RUN_END_NANOSECONDS=$(date +%s%N)
    RUN_ELAPSED_MILLISECONDS=$(( (RUN_END_NANOSECONDS - RUN_START_NANOSECONDS) / 1000000 ))

    # timeout(1) reports 124 on SIGTERM and 137 when --kill-after had to
    # send SIGKILL; name those so they are not mistaken for bend errors.
    if [ "$BEND_EXIT_CODE" -eq 124 ] || [ "$BEND_EXIT_CODE" -eq 137 ]; then
      echo "--- TIMEOUT after ${TIMEOUT_SECONDS}s (exit code $BEND_EXIT_CODE)" >> "$RESULTS_FILE"
    else
      echo "--- exit code $BEND_EXIT_CODE, ${RUN_ELAPSED_MILLISECONDS} ms" >> "$RESULTS_FILE"
    fi
    echo >> "$RESULTS_FILE"
  done
done

echo "results written to $RESULTS_FILE"
