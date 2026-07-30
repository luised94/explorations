-- conv.lua v0.1.1 - telescope, fixed folds, fixed search

-- Folds: fold on header lines
vim.opt_local.foldmethod = "expr"
vim.opt_local.foldexpr = "getline(v:lnum)=~#'^---\\ b'?'>1':'='"
vim.opt_local.foldlevel = 1
vim.opt_local.commentstring = "# %s"
vim.opt_local.wrap = true
vim.opt_local.linebreak = true

-- Syntax
vim.cmd [[
  syn match convHeader /^--- b\d\+ | .*/
  syn match convId /b\d\+/ contained containedin=convHeader
  syn match convSpeaker /| \(user\|asst\) |/ contained containedin=convHeader
  hi def convHeader guifg=#666666 ctermfg=242
  hi def convId guifg=#ffaf00 ctermfg=214 gui=bold
  hi def convSpeaker guifg=#87d787 ctermfg=114
]]

-- ]m / [m : jump between blocks
vim.keymap.set("n", "]m", function()
  vim.fn.search("^--- b", "W")
end, { buffer = true, desc = "next block" })

vim.keymap.set("n", "[m", function()
  vim.fn.search("^--- b", "bW")
end, { buffer = true, desc = "prev block" })

-- <leader>cb : telescope block picker
vim.keymap.set("n", "<leader>cb", function()
  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local blocks = {}
  for i, line in ipairs(lines) do
    local id, parent, speaker = line:match("^%-%-%- (b%d+) | (%S+) | (%S+)")
    if id then
      local preview = (lines[i + 1] or ""):sub(1, 72)
      table.insert(blocks, string.format("%s  [%s > %s]  %s", id, parent, speaker, preview))
    end
  end
  if #blocks == 0 then
    vim.notify("no blocks found", vim.log.levels.WARN)
    return
  end

  local pickers = require("telescope.pickers")
  local finders = require("telescope.finders")
  local conf = require("telescope.config").values
  local actions = require("telescope.actions")
  local action_state = require("telescope.actions.state")

  pickers.new({}, {
    prompt_title = "Blocks",
    finder = finders.new_table({
      results = blocks,
      entry_maker = function(entry)
        return { value = entry, display = entry, ordinal = entry }
      end,
    }),
    sorter = conf.generic_sorter({}),
    attach_mappings = function(prompt_bufnr, _)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local sel = action_state.get_selected_entry()
        if not sel then return end
        local target = sel.value:match("^(b%d+)")
        if target then
          local lnum = vim.fn.search("^--- " .. target, "nw")
          if lnum > 0 then
            vim.api.nvim_win_set_cursor(0, { lnum, 0 })
            vim.cmd("normal! zv")
          end
        end
      end)
      return true
    end,
  }):find()
end, { buffer = true, desc = "telescope block picker" })

-- <leader>cx : jump to first child of current block
vim.keymap.set("n", "<leader>cx", function()
  local line = vim.fn.search("^--- b", "bcnW")
  if line == 0 then return end
  local h = vim.api.nvim_buf_get_lines(0, line - 1, line, false)[1] or ""
  local id = h:match("(b%d+)")
  if not id then return end
  -- vim regex: \d\+ not %d+
  local child_line = vim.fn.search("^--- b\\d\\+ | " .. id .. " | ", "nw")
  if child_line > 0 then
    vim.api.nvim_win_set_cursor(0, { child_line, 0 })
    vim.cmd("normal! zv")
  else
    vim.notify(id .. ": no children", vim.log.levels.INFO)
  end
end, { buffer = true, desc = "first child of block" })

-- <leader>cX : list ALL children of current block in telescope
vim.keymap.set("n", "<leader>cX", function()
  local line = vim.fn.search("^--- b", "bcnW")
  if line == 0 then return end
  local h = vim.api.nvim_buf_get_lines(0, line - 1, line, false)[1] or ""
  local id = h:match("(b%d+)")
  if not id then return end

  local lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
  local children = {}
  for i, l in ipairs(lines) do
    local cid, parent, speaker = l:match("^%-%-%- (b%d+) | (%S+) | (%S+)")
    if cid and parent == id then
      local preview = (lines[i + 1] or ""):sub(1, 72)
      table.insert(children, string.format("%s  [%s]  %s", cid, speaker, preview))
    end
  end
  if #children == 0 then
    vim.notify(id .. ": no children", vim.log.levels.INFO)
    return
  end

  local pickers = require("telescope.pickers")
  local finders = require("telescope.finders")
  local conf = require("telescope.config").values
  local actions = require("telescope.actions")
  local action_state = require("telescope.actions.state")

  pickers.new({}, {
    prompt_title = "Children of " .. id,
    finder = finders.new_table({
      results = children,
      entry_maker = function(entry)
        return { value = entry, display = entry, ordinal = entry }
      end,
    }),
    sorter = conf.generic_sorter({}),
    attach_mappings = function(prompt_bufnr, _)
      actions.select_default:replace(function()
        actions.close(prompt_bufnr)
        local sel = action_state.get_selected_entry()
        if not sel then return end
        local target = sel.value:match("^(b%d+)")
        if target then
          local lnum = vim.fn.search("^--- " .. target, "nw")
          if lnum > 0 then
            vim.api.nvim_win_set_cursor(0, { lnum, 0 })
            vim.cmd("normal! zv")
          end
        end
      end)
      return true
    end,
  }):find()
end, { buffer = true, desc = "all children of block" })
