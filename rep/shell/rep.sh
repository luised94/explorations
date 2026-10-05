# rep's shell helpers (rep/PLAN.md D56). Source this file, or symlink it into
# the directory your bashrc sources. Defining these changes nothing until one
# is called. `function name {` rather than `name() {`: an alias of the same
# name cannot break the definition (it broke `body() {` once).

REP_REPOSITORY="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Today's section of the week's notes (templates/notes.md has the format),
# in nvim at the end of the file. The day rolls over at 04:00, as in rep.
function rep-notes {
  local data_root notes_path today
  data_root="$(rep where --data-root)" || return
  notes_path="$data_root/notes.md"
  today="$(date -d '4 hours ago' +%F)"
  [ -f "$notes_path" ] || cp "$REP_REPOSITORY/templates/notes.md" "$notes_path"
  grep -qx "## $today" "$notes_path" || printf '\n## %s\n- \n' "$today" >> "$notes_path"
  nvim + "$notes_path"
}

# The current tmux pane, scrollback included, saved to a file to attach
# instead of copying from the screen. Prints the file's path. The whole
# scrollback can hold anything typed or shown in that pane, so it says to
# read the file before sharing it (the person raised the risk of a
# leak); the files stay in the data root, never synced.
function rep-screen {
  local screens_directory screen_path
  screens_directory="$(rep where --data-root)/screens" || return
  mkdir -p "$screens_directory"
  screen_path="$screens_directory/$(date +%F-%H%M%S).txt"
  tmux capture-pane -p -J -S - > "$screen_path" || return
  echo "$screen_path"
  echo "rep-screen: $(wc -l < "$screen_path") lines, the whole scrollback; read it before attaching." >&2
}

# nvim with rep's plugin on (stamp on save, :RepCapture), config untouched.
function rep-nvim {
  nvim --cmd "luafile $REP_REPOSITORY/nvim/load.lua" "$@"
}

# The end of the week: statistics and a form of questions, in one report
# for the next thread, opened in nvim to answer (tools/week_report.py).
# Before the week's last day it says which day it is; --partial reports
# the days so far.
function rep-week {
  local report_path
  report_path="$(cd "$REP_REPOSITORY" && uv run python tools/week_report.py "$@")" && nvim "$report_path"
}

# A guided tour of rep's code, written as a form, opened in nvim: answer
# under each stop (tools/code_tour.py). The file lands beside the reports.
function rep-tour {
  local tour_path
  tour_path="$(rep where --data-root)/reports/code-tour-$(date +%F).md" || return
  (cd "$REP_REPOSITORY" && uv run python tools/code_tour.py --repository "$REP_REPOSITORY" \
    --sources "src/rep/*.py" --whole-file nvim/lua/rep/init.lua --output "$tour_path" "$@") && nvim "$tour_path"
}
