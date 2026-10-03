# rep for nvim

What it does (PLAN.md D43):

- Saving a file in `<data root>/library/` runs `rep stamp` on it and inserts
  the `id:` lines it adds, nothing else; the cursor, marks and folds stay.
  If stamp refuses, the file saves as written and the problems go to the
  quickfix list (`:copen`). Save again after fixing them.
- `:RepCapture` opens, in a split, the library file of the nearest
  `## @citekey` heading above the cursor (`library/<citekey>.md`), with a new
  item at the end:

      ### Q: |
      A:
      source: @<citekey>

  Write the question and answer, then `:w`: that save stamps the id.
  `:RepCapture <name>` picks the file by name instead (needed where no
  `## @citekey` heading is above the cursor). To drop an item you started,
  delete its lines, or `:q!` before saving.

The data root comes from `rep where --data-root`, asked once per nvim
session on the first save of a `.md` file or the first `:RepCapture`.
`rep` must be on PATH (`uv tool install --editable .` in rep/).

## lazy.nvim spec

```lua
{
  dir = "~/personal_repos/explorations/rep/nvim",
  name = "rep",
  lazy = false, -- stamp on save must be set up before the first save; setup() only registers an autocmd and a command
  opts = {},    -- or { command = "/path/to/rep" }
  keys = {
    { "<leader>pc", "<cmd>RepCapture<cr>", desc = "rep: capture an item" },
  },
},
```

## Lint into quickfix

No plugin code: nvim's `:make` does it. In a library file:

```vim
:setlocal makeprg=rep\ lint errorformat=%f:%l:%c:\ %t%*[a-z]:\ %m
:make
```

Or set both for library files, anywhere in your config:

```lua
vim.api.nvim_create_autocmd("BufEnter", {
  pattern = vim.fn.expand("~/learning") .. "/library/*.md",
  callback = function()
    vim.opt_local.makeprg = "rep lint"
    vim.opt_local.errorformat = "%f:%l:%c: %t%*[a-z]: %m"
  end,
})
```
