-- conv.lua - minimal navigation for .conv files
-- Assumes: treesitter not required for v0.1, regex syntax is enough.
-- Dependencies: fzf-lua or telescope (whichever you have) for block picker.

vim.opt_local.foldmethod = "expr"
vim.opt_local.foldexpr = "getline(v:lnum)=~'^---\\s' ? '>1' : '='"
vim.opt_local.foldlevel = 1  -- all blocks folded on open, headers visible
vim.opt_local.commentstring = "# %s"

-- Syntax: highlight the header line, dim the body
vim.cmd [[
  syn match convHeader /^--- b\d\+ | .*/ contains=convId,convSpeaker
  syn match convId /b\d\+/ contained
  syn match convSpeaker /| \(user\|asst\) |/ contained
  hi def convHeader ctermfg=245 guifg=#888888
  hi def convId ctermfg=214 guifg=#ffaf00
  hi def convSpeaker ctermfg=114 guifg=#87d787
]]

-- ]m / [m : jump between block headers
vim.keymap.set("n", "]m", function()
  vim.fn.search("^--- b", "W")
end, { buffer = true, desc = "next block" })

vim.keymap.set("n", "[m", function()
  vim.fn.search("^--- b", "bW")
end, { buffer = true, desc = "prev block" })

-- <leader>cb : open fzf picker of all blocks in this file
vim.keymap.set("n", "<leader>cb", function()
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local blocks = {}
  for i, line in ipairs(lines) do
    local id, parent, speaker = line:match("^%-%-%- (b%d+) | (%S+) | (%S+)")
    if id then
      -- grab first line of body as preview
      local preview = lines[i + 1] or ""
      table.insert(blocks, string.format("%s [%s%s] %s", id, parent, speaker, preview))
    end
  end
  -- if you have fzf-lua:
  if pcall(require, "fzf-lua") then
    require("fzf-lua").fzf_exec(blocks, {
      prompt = "blocks> ",
      actions = {
        default = function(selected)
          local target = selected[1]:match("^(b%d+)")
          local lnum = vim.fn.search("^--- " .. target, "nw")
          if lnum > 0 then
            vim.api.nvim_win_set_cursor(0, { lnum, 0 })
            vim.cmd("normal! zv")  -- unfold
          end
        end,
      },
    })
  end
end, { buffer = true, desc = "fzf block picker" })

-- <leader>ct : show children of current block (quick tree nav)
vim.keymap.set("n", "<leader>ct", function()
  local line = vim.fn.search("^--- b", "bcnW")
  local header = vim.api.nvim_buf_get_lines(0, line - 1, line, false)[1] or ""
  local id = header:match("b%d+")
  if not id then return end
  -- find all blocks whose parent is this id
  local children = vim.fn.search("^--- b%d+ | " .. id, "nw")
  if children > 0 then
    vim.api.nvim_win_set_cursor(0, { children, 0 })
    vim.cmd("normal! zv")
  else
    vim.notify("no children of " .. id, vim.log.levels.INFO)
  end
end, { buffer = true, desc = "first child of block" })

-- Statusline: show current block id
vim.opt_local.statusline = "%f %=%{v:lua.ConvStatus()} %l:%c"
function ConvStatus()
  local line = vim.fn.search("^--- b", "bcnW")
  if line == 0 then return "" end
  local h = vim.api.nvim_buf_get_lines(0, line - 1, line, false)[1] or ""
  return h:match("(b%d+)") or ""
end
