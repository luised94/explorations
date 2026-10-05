-- The questions-only view of a FAQ.md (meta/README.md): every "## "
-- entry folds to its heading, so the file reads as a list of questions,
-- and j and k move one question at a time. Loaded only by the shell's
-- `faq` as `nvim --cmd "luafile <this file>"`, so the person's config is
-- untouched; the settings are window-local and only for FAQ.md buffers.
vim.api.nvim_create_autocmd({ "BufReadPost", "BufNewFile" }, {
  pattern = "*/FAQ.md",
  callback = function()
    vim.wo.foldmethod = "expr"
    -- A heading starts a fold; every other line keeps the level above it,
    -- so the file's own header (before the first entry) stays open.
    vim.wo.foldexpr = "getline(v:lnum)=~#'^## '?'>1':'='"
    -- The heading alone, without the default "+-- N lines:" prefix.
    vim.wo.foldtext = "getline(v:foldstart)"
    vim.opt_local.fillchars:append({ fold = " " })
    vim.wo.foldlevel = 0
  end,
})
