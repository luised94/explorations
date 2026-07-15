-- tsk.lua -- nvim integration for the tsk CLI, plugin-free.
--
-- WHY THIS FILE EXISTS
--   `tsk` is a bash *function* (integrations/tsk.sh, sourced from your
--   interactive shell config). nvim's `:!` spawns a NON-interactive shell,
--   which does not source that config, so `:!tsk ...` fails with
--   "command not found" / exit 127. This module sidesteps the shell
--   entirely, invoking the script the way the function does:
--       uv run --no-project <TSK_SCRIPT> <args...>
--   through vim.system (no shell -> no quoting hazards, no .bashrc need).
--
-- LOADER CONTRACT (matches the mc_extensions for-loop)
--   Returns { keymaps, autocmds, commands, setup }.
--   keymaps: list of POSITIONAL 4-tuples { mode, lhs, rhs, opts } passed
--            straight to vim.keymap.set (rhs may be a string or a function;
--            this module uses functions).
--   commands: list of { name, fn, opts } for nvim_create_user_command.
--   autocmds: list of { event, opts }; none here.
--   setup: function or nil; nil here (loader runs it only if a function).
--   The named-spec-plus-build-loop below mirrors the house pattern
--   (cf. lw.lua) so the readable specs stay separate from the terse tuples
--   the loader consumes. See docs/nvim-integration-strategy.md.
--
-- SELF-CONTAINED: no ambient globals assumed. Mode and leader are defined
-- locally so this file drops into any loader without external definitions.

local MODE_NORMAL = "n"
local LEADER_T = "<leader>t"

-- Resolve the script path once. Prefer $TSK_SCRIPT (exported by tsk.sh when
-- a login shell launched nvim); fall back to the known repo path so the
-- module still works when nvim started without that environment.
local tsk_script = vim.env.TSK_SCRIPT
  or (vim.env.HOME .. "/personal_repos/explorations/tasks/tasks.py")

-- Run tsk with an argv list (no shell). Each element is passed literally:
-- a summary with spaces is ONE element, no word-splitting or globbing.
local function run_tsk(argv)
  local cmd = { "uv", "run", "--no-project", tsk_script }
  for _, a in ipairs(argv) do
    cmd[#cmd + 1] = a
  end
  local result = vim.system(cmd, { text = true }):wait()
  return result.stdout or "", result.stderr or "", result.code
end

-- Surface tsk output. Exit codes (0 ok, 1 validation, 3 data dir missing)
-- drive the level. On a discarded --edit capture, stderr carries the
-- recovery echo of the typed buffer, so it must reach the user, not vanish.
local function report(stdout, stderr, code)
  if stdout ~= "" then
    vim.notify(vim.trim(stdout), vim.log.levels.INFO)
  end
  if code ~= 0 and stderr ~= "" then
    vim.notify(vim.trim(stderr), vim.log.levels.WARN)
  end
end

-- :Tsk <args>  -- any subcommand: :Tsk today, :Tsk add task "call plumber".
-- fargs is pre-split by nvim, so a quoted summary stays one argument.
local function cmd_tsk(opts)
  report(run_tsk(opts.fargs))
end

-- :TskRead [args]  -- read tsk output into the buffer at the cursor
-- (the planning workflow), defaulting to `week`.
local function cmd_tsk_read(opts)
  local argv = opts.fargs
  if #argv == 0 then
    argv = { "week" }
  end
  local stdout, stderr, code = run_tsk(argv)
  if code ~= 0 then
    report(stdout, stderr, code)
    return
  end
  local lines = vim.split(vim.trim(stdout), "\n", { plain = true })
  vim.api.nvim_put(lines, "l", true, false)
end

-- --edit note: :Tsk add ... --edit launches $EDITOR as a child of
-- vim.system with no controlling TTY -- it will NOT work as an interactive
-- editor. Use a :terminal split for editor-capture (see README).

local commands = {
  { name = "Tsk",     fn = cmd_tsk,      opts = { nargs = "*", desc = "run a tsk subcommand, echo output" } },
  { name = "TskRead", fn = cmd_tsk_read, opts = { nargs = "*", desc = "read tsk output into buffer (default: week)" } },
}

-- Readable specs -> positional tuples, the same bridge lw.lua uses. A
-- string rhs would also work; functions keep the maps independent of the
-- :Tsk command being registered.
local KEYMAP_SPECS = {
  { key = "a", fn = function() vim.api.nvim_feedkeys(':Tsk add task ""' .. vim.api.nvim_replace_termcodes("<Left>", true, false, true), "n", false) end, desc = "add task (type summary, Enter to create)" },
  { key = "d", fn = function() report(run_tsk({ "today" })) end, desc = "today dashboard" },
  { key = "w", fn = cmd_tsk_read, desc = "read week view into buffer" },
}

local keymaps = {}
for _, spec in ipairs(KEYMAP_SPECS) do
  keymaps[#keymaps + 1] = {
    MODE_NORMAL,
    LEADER_T .. spec.key,
    spec.fn,
    { desc = "tsk: " .. spec.desc },
  }
end

return {
  keymaps  = keymaps,
  autocmds = {},
  commands = commands,
  setup    = nil,
}
