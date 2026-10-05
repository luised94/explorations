# The body form (rep/PLAN.md section 9). Source this file, or symlink it into
# the directory your bashrc sources. `function body {`, not `body() {`: an
# alias named body cannot break this definition.

REP_REPOSITORY="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# Today's form in nvim: a new day starts from templates/body.md. The day
# rolls over at 04:00, as in rep, so after midnight this is still yesterday.
function body {
  local body_directory
  body_directory="$(rep where --data-root)/body" || return
  mkdir -p "$body_directory"
  nvim --cmd "luafile $REP_REPOSITORY/nvim/body.lua" "$body_directory/$(date -d '4 hours ago' +%F).md"
}
