#!/usr/bin/env bash
# Runs PROOF.bend and playground.bend for every model directory, records the
# output of each run, snapshots the files that produced it, and measures the
# rendered figures.
#
# Changes from v1, and why each one exists:
#   - Results are written per round instead of truncating one file. v1 opened
#     results.txt with ">", so re-running after a repair round destroyed the
#     previous round's evidence.
#   - Each round's three .bend files are copied into the round directory before
#     the run. Without this the artifact and the result drift apart as soon as a
#     model hands back files with the same three names.
#   - Each round is committed to git when the tree is a repo. The diff between
#     rounds is the only record of what a model actually changed in response to
#     an error; transcripts are a lossy substitute and browser scrapes lose code.
#   - The error class is extracted into a per-round summary. A histogram of
#     classes across rounds is what distinguishes a model converging from one
#     repairing the reported line and breaking the same rule elsewhere.
#   - Rendered figures are measured: rows, columns, and columns that are blank
#     in every row. A Sierpinski figure whose cell test cannot reach its own
#     right half raises no compiler error and is invisible in a pass/fail log.

# ---- configuration ---------------------------------------------------------

MODEL_TESTS_ROOT="/home/luis/personal_repos/explorations/bend-playground/model_tests"

# Explicit list rather than a */ glob so a stray directory (for example a
# results/ or rounds/ folder) is never run as a model, and the order is fixed.
MODEL_DIRECTORY_NAMES=(
  "claude-opus-5"
  "claude-sonnet-5"
  "gpt5.6-terra"
  "open-source-large"
  "open-source-medium"
)

# LAWS.bend is not run on its own: PROOF.bend imports it. Note that this only
# checks the laws when playground.bend already elaborates -- a playground error
# preempts PROOF.bend entirely, and both runs then report the same failure.
BEND_FILE_NAMES=(
  "PROOF.bend"
  "playground.bend"
)

TIMEOUT_SECONDS=60

# Round number. Pass it in: ROUND=2 ./run_model_tests.sh
ROUND_NUMBER="${ROUND:-1}"

ROUND_DIRECTORY="$MODEL_TESTS_ROOT/rounds/round_${ROUND_NUMBER}"
RESULTS_FILE="$ROUND_DIRECTORY/results.txt"
SUMMARY_FILE="$ROUND_DIRECTORY/summary.txt"

mkdir -p "$ROUND_DIRECTORY"

# ---- run -------------------------------------------------------------------

# No `set -e`: a failing or timed-out model is a result to record, not a reason
# to stop before the remaining models run.

# Best effort to keep ANSI color escapes out of the text file; harmless if bend
# ignores it.
export NO_COLOR=1

{
  echo "Model test run: $(date '+%Y-%m-%d %H:%M:%S %Z')"
  echo "Round: $ROUND_NUMBER"
  # Recorded because results are only comparable across runs on the same
  # compiler version.
  echo "Bend version: $(bend --version 2>&1)"
  echo "Timeout per run: ${TIMEOUT_SECONDS}s"
  echo
} > "$RESULTS_FILE"

for MODEL_DIRECTORY_NAME in "${MODEL_DIRECTORY_NAMES[@]}"; do
  MODEL_DIRECTORY_PATH="$MODEL_TESTS_ROOT/$MODEL_DIRECTORY_NAME"
  MODEL_SNAPSHOT_PATH="$ROUND_DIRECTORY/$MODEL_DIRECTORY_NAME"

  # Snapshot before running, so the recorded result always has the exact source
  # that produced it sitting beside it.
  mkdir -p "$MODEL_SNAPSHOT_PATH"
  cp "$MODEL_DIRECTORY_PATH"/*.bend "$MODEL_SNAPSHOT_PATH"/ 2>/dev/null

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
    # stdin from /dev/null: a main that reads input would otherwise block until
    # the timeout. --kill-after: a bend that ignores SIGTERM still dies.
    timeout --kill-after=5 "$TIMEOUT_SECONDS" bend "$BEND_FILE_NAME" < /dev/null >> "$RESULTS_FILE" 2>&1
    BEND_EXIT_CODE=$?
    RUN_END_NANOSECONDS=$(date +%s%N)
    RUN_ELAPSED_MILLISECONDS=$(( (RUN_END_NANOSECONDS - RUN_START_NANOSECONDS) / 1000000 ))

    # timeout(1) reports 124 on SIGTERM and 137 when --kill-after had to send
    # SIGKILL; name those so they are not mistaken for bend errors.
    if [ "$BEND_EXIT_CODE" -eq 124 ] || [ "$BEND_EXIT_CODE" -eq 137 ]; then
      echo "--- TIMEOUT after ${TIMEOUT_SECONDS}s (exit code $BEND_EXIT_CODE)" >> "$RESULTS_FILE"
    else
      echo "--- exit code $BEND_EXIT_CODE, ${RUN_ELAPSED_MILLISECONDS} ms" >> "$RESULTS_FILE"
    fi
    echo >> "$RESULTS_FILE"
  done
done

cd "$MODEL_TESTS_ROOT" || exit 1

# ---- summarise -------------------------------------------------------------

# Two things the raw log does not give you: the error class per model, and the
# shape of what was actually drawn. Both are read straight out of results.txt so
# there is one source of truth.
python3 - "$RESULTS_FILE" "$SUMMARY_FILE" <<'PYTHON_SUMMARY'
import re
import sys

results_path, summary_path = sys.argv[1], sys.argv[2]
results_text = open(results_path).read()
blocks = re.split(r'^===== ', results_text, flags=re.M)[1:]

per_model = {}
for block in blocks:
    header, _, body = block.partition('=====\n')
    model_name, _, file_name = header.strip().partition(' / ')
    body = body.split('bend 2.0')[0]
    per_model.setdefault(model_name, {})[file_name.strip()] = body

summary_lines = []
for model_name, files in per_model.items():
    summary_lines.append('#### ' + model_name)

    # Error class. The first "expected :" or "message :" line is the class; the
    # variable name in it is the site. Class without site is what you histogram
    # across rounds, because the same rule broken at a new site is not progress.
    render_had_error = False
    for file_name, body in files.items():
        # Prefer the "observed" line when it carries a parenthetical: that is
        # where the rule lives ("x (consumed more than once)"), while "expected"
        # holds only the offending name, which differs at every site and would
        # make two breaches of one rule look like two different problems.
        observed_match = re.search(r'^- observed\s*:\s*\S+ \((.+)\)\s*$', body, re.M)
        error_match = re.search(r'^- (?:expected|message)\s*:\s*(.+)$', body, re.M)
        if observed_match or error_match:
            if file_name == 'playground.bend':
                render_had_error = True
            error_class = (observed_match or error_match).group(1).strip()
            summary_lines.append(f'  {file_name}: ERROR [{error_class}]')
        elif 'All terms check' in body:
            summary_lines.append(f'  {file_name}: All terms check.')
        else:
            summary_lines.append(f'  {file_name}: rendered')

    # Figure measurement. Group the rendered output into blocks of consecutive
    # non-empty lines and report each one's extent. A column blank in every row
    # of a figure is either a bounded set (fine, Mandelbrot) or a cell test that
    # cannot reach its own grid (a defect, Sierpinski) -- the number is reported
    # either way and read in context.
    # Skip measurement when the render failed: the "figure" would be the error
    # text, and a measurement of an error message is worse than none.
    render_body = '' if render_had_error else files.get('playground.bend', '')
    figures, current = [], []
    for line in render_body.split('\n'):
        if line.strip() == '' or re.fullmatch(r'[A-Za-z ]+', line.strip() or ' '):
            if len(current) >= 8:
                figures.append(current)
            current = []
        else:
            current.append(line)
    if len(current) >= 8:
        figures.append(current)

    for figure_index, figure_lines in enumerate(figures, start=1):
        width = max(len(line) for line in figure_lines)
        padded = [line.ljust(width) for line in figure_lines]
        dead_columns = [c for c in range(width)
                        if all(row[c] == ' ' for row in padded)]
        trailing_dead = 0
        for column in range(width - 1, -1, -1):
            if column in dead_columns:
                trailing_dead += 1
            else:
                break
        summary_lines.append(
            f'  figure {figure_index}: {len(figure_lines)} rows x {width} cols, '
            f'{len(dead_columns)} never-filled columns, '
            f'{trailing_dead} blank on the right')
    summary_lines.append('')

open(summary_path, 'w').write('\n'.join(summary_lines) + '\n')
print('\n'.join(summary_lines))
PYTHON_SUMMARY

# ---- commit ----------------------------------------------------------------

# Only if this tree is already a repo. The diff between two rounds is the record
# of what a model changed in response to an error, which no transcript reliably
# preserves.
if git -C "$MODEL_TESTS_ROOT" rev-parse --git-dir > /dev/null 2>&1; then
  git -C "$MODEL_TESTS_ROOT" add -A
  git -C "$MODEL_TESTS_ROOT" commit -q -m "round ${ROUND_NUMBER}: model files and results" \
    && git -C "$MODEL_TESTS_ROOT" tag -f "round-${ROUND_NUMBER}" > /dev/null \
    && echo "committed and tagged round-${ROUND_NUMBER}"
else
  echo "not a git repo: skipping commit (git init here to get per-round diffs)"
fi

echo "results written to $RESULTS_FILE"
echo "summary written to $SUMMARY_FILE"
