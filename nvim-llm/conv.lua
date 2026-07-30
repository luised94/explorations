-- conv.lua - v0.1 navigation for .conv files

vim.opt_local.foldmethod = "expr"
vim.opt_local.foldexpr = "getline(v:lnum):match('^%-%-%- %s') and '>1' or '='"
vim.opt_local.foldlevel = 1
vim.opt_local.commentstring = "# %s"
vim.opt_local.wrap = true
vim.opt_local.linebreak = true

-- Syntax
vim.cmd [[
  syn match convHeader /^--- b\d\+ | .*/
  syn match convId /b\d\+/ contained containedin=convHeader
  syn match convSpeaker /| \(user\|asst\) |/ contained containedin=convHeader
  syn match convTime /| \d\+:\d\+$/ contained containedin=convHeader
  hi def convHeader guifg=#666666 ctermfg=242
  hi def convId guifg=#ffaf00 ctermfg=214 gui=bold
  hi def convSpeaker guifg=#87d787 ctermfg=114
  hi def convTime guifg=#555555 ctermfg=240
]]

-- Jump between blocks
vim.keymap.set("n", "]m", function()
  vim.fn.search("^--- b", "W")
end, { buffer = true, desc = "next block" })

vim.keymap.set("n", "[m", function()
  vim.fn.search("^--- b", "bW")
end, { buffer = true, desc = "prev block" })

-- fzf block picker
vim.keymap.set("n", "<leader>cb", function()
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local blocks = {}
  for i, line in ipairs(lines) do
    local id, parent, speaker = line:match("^%-%-%- (b%d+) | (%S+) | (%S+)")
    if id then
      local preview = (lines[i + 1] or ""):sub(1, 72)
      table.insert(blocks, string.format("%s  [%s  %s]  %s", id, parent, speaker, preview))
    end
  end
  if #blocks == 0 then
    vim.notify("no blocks found", vim.log.levels.WARN)
    return
  end
  local ok, fzf = pcall(require, "fzf-lua")
  if ok then
    fzf.fzf_exec(blocks, {
      prompt = "blocks> ",
      actions = {
        default = function(selected)
          if not selected or not selected[1] then return end
          local target = selected[1]:match("^(b%d+)")
          if target then
            local lnum = vim.fn.search("^--- " .. target, "nw")
            if lnum > 0 then
              vim.api.nvim_win_set_cursor(0, { lnum, 0 })
              vim.cmd("normal! zv")
            end
          end
        end,
      },
    })
  else
    -- fallback: telescope
    local ok2, telescope = pcall(require, "telescope.builtin")
    if ok2 then
      -- just use grep_string as fallback
      vim.notify("fzf-lua not found, use :vimgrep", vim.log.levels.INFO)
    end
  end
end, { buffer = true, desc = "fzf block picker" })

-- Show children of current block
vim.keymap.set("n", "<leader>cx", function()
  local line = vim.fn.search("^--- b", "bcnW")
  if line == 0 then return end
  local header = vim.api.nvim_buf_get_lines(0, line - 1, line, false)[1] or ""
  local id = header:match("(b%d+)")
  if not id then return end
  local child_line = vim.fn.search("^--- b%d+ | " .. id .. " ", "nw")
  if child_line > 0 then
    vim.api.nvim_win_set_cursor(0, { child_line, 0 })
    vim.cmd("normal! zv")
  else
    vim.notify(id .. " has no children", vim.log.levels.INFO)
  end
end, { buffer = true, desc = "first child" })

-- Statusline: current block id
vim.opt_local.statusline = "%f  %=%{v:lua.ConvBlockId()}  %l:%c"
function _G.ConvBlockId()
  local line = vim.fn.search("^--- b", "bcnW")
  if line == 0 then return "" end
  local h = vim.api.nvim_buf_get_lines(0, line - 1, line, false)[1] or ""
  return h:match("(b%d+)") or ""
end

vim.filetype.add({ extension = { conv = "conv" } })
vim.opt.runtimepath:append("~/conv")
