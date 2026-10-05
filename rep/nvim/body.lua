-- The body form (rep/PLAN.md section 9): a new day's file starts from
-- rep/templates/body.md, cursor at the end of "bed: ". Loaded only by the
-- shell's `body` (rep/shell/body.sh) as `nvim --cmd "luafile <this file>"`,
-- so it changes nothing in your config. The template is found beside this
-- file, so it is versioned with rep and nothing has to be installed.
local template_path = vim.fn.fnamemodify(debug.getinfo(1, "S").source:sub(2), ":p:h:h") .. "/templates/body.md"
vim.api.nvim_create_autocmd("BufNewFile", {
  pattern = "*/body/*.md",
  callback = function()
    vim.cmd("0read " .. vim.fn.fnameescape(template_path) .. " | $delete _")
    vim.fn.search("^bed: ")
    vim.cmd("normal! $")
  end,
})
