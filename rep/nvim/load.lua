-- Turns on rep's plugin (stamp on save, :RepCapture) in this nvim session,
-- without touching your config: `nvim --cmd "luafile <this file>"`, or
-- `:luafile <this file>` inside nvim, or the shell's `rep-nvim`
-- (rep/shell/rep.sh). Until the plugin is loaded by lazy.nvim (README.md).
local plugin_directory = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":p:h")
vim.opt.runtimepath:prepend(plugin_directory)
require("rep").setup({})
