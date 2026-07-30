-- conv.lua - v0.2 conversation buffer navigation, tree rendering, yank, fork
-- Source: :luafile ./conv.lua
-- Requires: telescope (for block picker). No other plugin dependencies.
-- Coding guidelines: full names, no abbreviations, imperative top-level,
--   pure helper functions, side effects isolated to command handlers.

-- 컴 Configuration 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴

local BLOCK_HEADER_PATTERN = "^%-%-%- b%d+"          -- lua pattern for header lines
local BLOCK_HEADER_VIM_REGEX = "^--- b\\d\\+"         -- vim regex equivalent
local BLOCK_ID_LUA_PATTERN = "(b%d+)"                 -- extract ID in lua
local BLOCK_ID_VIM_REGEX = "b\\d\\+"                  -- extract ID in vim regex
local FOLD_LEVEL_ON_OPEN = 1                          -- 0=all folded, 1=headers visible
local TREE_SPLIT_WIDTH = 40                           -- columns for tree sidebar
local TREE_INDENT_UNIT = "    "                       -- 4 spaces per depth level
local TREE_BRANCH_CHAR = "쳐� "
local TREE_LAST_CHILD_CHAR = "읕� "
local TREE_VERTICAL_CHAR = "�   "
local TREE_SPACE_CHAR = "    "

-- 컴 Pure transformations 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴�
-- These functions compute. They do not modify buffers or files.

local function parse_all_blocks_from_buffer(buffer_number)
  -- Returns: list of {identifier, parent_identifier, speaker, timestamp, body_first_line, line_number}
  local all_lines = vim.api.nvim_buf_get_lines(buffer_number, 0, -1, false)
  local blocks = {}
  for line_index, line_content in ipairs(all_lines) do
    local identifier, parent_identifier, speaker, timestamp =
      line_content:match("^%-%-%- (b%d+) | (%S+) | (%S+) | (%S+)")
    if identifier then
      local body_first_line = (all_lines[line_index + 1] or ""):sub(1, 60)
      table.insert(blocks, {
        identifier = identifier,
        parent_identifier = parent_identifier,
        speaker = speaker,
        timestamp = timestamp,
        body_preview = body_first_line,
        line_number = line_index,
      })
    end
  end
  return blocks
end

local function build_children_map(blocks)
  -- Returns: map of parent_identifier -> list of child blocks (in file order)
  local children_map = {}
  for _, block in ipairs(blocks) do
    local parent = block.parent_identifier
    if not children_map[parent] then
      children_map[parent] = {}
    end
    table.insert(children_map[parent], block)
  end
  return children_map
end

local function render_tree_lines(blocks)
  -- Returns: list of strings (the rendered tree) and a parallel list of block identifiers
  local children_map = build_children_map(blocks)
  local rendered_lines = {}
  local rendered_identifiers = {}

  local function render_subtree(block, prefix, is_last_child)
    local connector = is_last_child and TREE_LAST_CHILD_CHAR or TREE_BRANCH_CHAR
    local label = string.format("%s%s [%s] %s",
      prefix, block.identifier, block.speaker, block.body_preview)
    table.insert(rendered_lines, prefix .. connector .. label:sub(#prefix + 1))
    -- correction: build the line cleanly
    rendered_lines[#rendered_lines] = string.format("%s%s%s [%s] %s",
      prefix, connector, block.identifier, block.speaker, block.body_preview)
    table.insert(rendered_identifiers, block.identifier)

    local children = children_map[block.identifier] or {}
    local child_prefix = prefix .. (is_last_child and TREE_SPACE_CHAR or TREE_VERTICAL_CHAR)
    for child_index, child_block in ipairs(children) do
      render_subtree(child_block, child_prefix, child_index == #children)
    end
  end

  -- Roots: blocks whose parent is "root"
  local roots = children_map["root"] or {}
  for root_index, root_block in ipairs(roots) do
    -- Render root without connector
    table.insert(rendered_lines, string.format("%s [%s] %s",
      root_block.identifier, root_block.speaker, root_block.body_preview))
    table.insert(rendered_identifiers, root_block.identifier)
    local children = children_map[root_block.identifier] or {}
    for child_index, child_block in ipairs(children) do
      render_subtree(child_block, "", child_index == #children)
    end
    -- Blank line between roots
    if root_index < #roots then
      table.insert(rendered_lines, "")
      table.insert(rendered_identifiers, "")
    end
  end

  return rendered_lines, rendered_identifiers
end

-- 컴 Side effects (isolated to command handlers) 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴

local function open_tree_sidebar()
  local current_buffer = vim.api.nvim_get_current_buf()
  local blocks = parse_all_blocks_from_buffer(current_buffer)
  if #blocks == 0 then
    vim.notify("no blocks found in buffer", vim.log.levels.WARN)
    return
  end

  local tree_lines, tree_identifiers = render_tree_lines(blocks)

  -- Create or reuse the tree sidebar window
  local tree_buffer_name = "conv-tree://" .. vim.fn.bufname(current_buffer)
  local existing_tree_buffer = vim.fn.bufnr(tree_buffer_name)
  if existing_tree_buffer ~= -1 then
    vim.api.nvim_buf_delete(existing_tree_buffer, { force = true })
  end

  -- Split: vertical, left side, fixed width
  vim.cmd("topleft " .. TREE_SPLIT_WIDTH .. "vsplit")
  local tree_buffer = vim.api.nvim_create_buf(false, true)  -- scratch, no file
  vim.api.nvim_buf_set_name(tree_buffer, tree_buffer_name)
  vim.api.nvim_win_set_buf(0, tree_buffer)

  -- Write the rendered tree
  vim.api.nvim_buf_set_lines(tree_buffer, 0, -1, false, tree_lines)

  -- Make it read-only and non-modifiable
  vim.opt_local.modifiable = false
  vim.opt_local.readonly = true
  vim.opt_local.buftype = "nofile"
  vim.opt_local.bufhidden = "wipe"
  vim.opt_local.wrap = false
  vim.opt_local.cursorline = true
  vim.opt_local.number = false
  vim.opt_local.signcolumn = "no"

  -- Syntax for the tree buffer
  vim.cmd [[
    syn match convTreeId /b\d\+/
    syn match convTreeSpeaker /\[user\]/
    syn match convTreeSpeakerAsst /\[asst\]/
    syn match convTreeConnector /[쳄냐]/
    hi def convTreeId guifg=#ffaf00 gui=bold
    hi def convTreeSpeaker guifg=#87d787
    hi def convTreeSpeakerAsst guifg=#87afd7
    hi def convTreeConnector guifg=#555555
  ]]

  -- Enter on a line: jump to that block in the conversation buffer
  vim.keymap.set("n", "<CR>", function()
    local cursor_line = vim.api.nvim_win_get_cursor(0)[1]
    local target_identifier = tree_identifiers[cursor_line]
    if not target_identifier or target_identifier == "" then return end

    -- Find the conversation window (the other window)
    local conversation_window = nil
    for _, window in ipairs(vim.api.nvim_list_wins()) do
      if vim.api.nvim_win_get_buf(window) == current_buffer then
        conversation_window = window
        break
      end
    end
    if not conversation_window then
      vim.notify("conversation buffer not visible", vim.log.levels.WARN)
      return
    end

    -- Jump
    vim.api.nvim_set_current_win(conversation_window)
    local target_line = vim.fn.search(BLOCK_HEADER_VIM_REGEX:gsub("b\\d\\+", target_identifier), "nw")
    if target_line > 0 then
      vim.api.nvim_win_set_cursor(conversation_window, { target_line, 0 })
      vim.cmd("normal! zv")
    end
  end, { buffer = tree_buffer, desc = "jump to block" })

  -- q closes the tree sidebar
  vim.keymap.set("n", "q", function()
    vim.api.nvim_win_close(0, true)
  end, { buffer = tree_buffer, desc = "close tree" })
end

local function yank_current_block(register)
  -- Yank from current block header to just before the next header (or EOF)
  local current_buffer = vim.api.nvim_get_current_buf()
  local all_lines = vim.api.nvim_buf_get_lines(current_buffer, 0, -1, false)
  local cursor_line = vim.api.nvim_win_get_cursor(0)[1]

  -- Find the header at or above cursor
  local block_start_line = cursor_line
  while block_start_line > 0 and not all_lines[block_start_line]:match(BLOCK_HEADER_PATTERN) do
    block_start_line = block_start_line - 1
  end
  if block_start_line == 0 then
    vim.notify("no block header found above cursor", vim.log.levels.WARN)
    return
  end

  -- Find the next header (or EOF)
  local block_end_line = block_start_line + 1
  while block_end_line <= #all_lines and not all_lines[block_end_line]:match(BLOCK_HEADER_PATTERN) do
    block_end_line = block_end_line + 1
  end
  block_end_line = block_end_line - 1  -- back up to last body line

  -- Extract and yank
  local block_lines = vim.api.nvim_buf_get_lines(current_buffer, block_start_line - 1, block_end_line, false)
  local yank_text = table.concat(block_lines, "\n")
  vim.fn.setreg(register or '"', yank_text)
  local block_identifier = all_lines[block_start_line]:match(BLOCK_ID_LUA_PATTERN)
  vim.notify("yanked " .. block_identifier .. " (" .. #block_lines .. " lines) to register " .. (register or '"'),
    vim.log.levels.INFO)
end

local function fork_current_block_to_new_session(session_name)
  -- Create a new .conv file with the current block as b001/root
  local current_buffer = vim.api.nvim_get_current_buf()
  local all_lines = vim.api.nvim_buf_get_lines(current_buffer, 0, -1, false)
  local cursor_line = vim.api.nvim_win_get_cursor(0)[1]

  -- Find block boundaries (same logic as yank)
  local block_start_line = cursor_line
  while block_start_line > 0 and not all_lines[block_start_line]:match(BLOCK_HEADER_PATTERN) do
    block_start_line = block_start_line - 1
  end
  if block_start_line == 0 then
    vim.notify("no block header found above cursor", vim.log.levels.WARN)
    return
  end
  local block_end_line = block_start_line + 1
  while block_end_line <= #all_lines and not all_lines[block_end_line]:match(BLOCK_HEADER_PATTERN) do
    block_end_line = block_end_line + 1
  end
  block_end_line = block_end_line - 1

  -- Extract body (skip the original header)
  local body_lines = vim.api.nvim_buf_get_lines(current_buffer, block_start_line, block_end_line, false)
  local original_identifier = all_lines[block_start_line]:match(BLOCK_ID_LUA_PATTERN)

  -- Build new file
  local conversation_directory = vim.fn.expand("$CONVERSATION_DIRECTORY")
  if conversation_directory == "" then
    conversation_directory = vim.fn.expand("$HOME/conversations")
  end
  local new_file_path = conversation_directory .. "/" .. os.date("%Y-%m-%d") .. "-" .. session_name .. ".conv"

  local new_file_lines = {
    "# session: " .. os.date("%Y-%m-%d") .. " " .. session_name,
    "# forked from: " .. vim.fn.bufname(current_buffer) .. " block " .. original_identifier,
    "",
    "--- b001 | root | user | " .. os.date("%H:%M"),
  }
  for _, body_line in ipairs(body_lines) do
    table.insert(new_file_lines, body_line)
  end

  vim.fn.writefile(new_file_lines, new_file_path)
  vim.notify("forked " .. original_identifier .. "  " .. new_file_path, vim.log.levels.INFO)
  -- Open the new file
  vim.cmd("edit " .. new_file_path)
end

-- 컴 Buffer setup (runs on source) 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴�

vim.opt_local.foldmethod = "expr"
vim.opt_local.foldexpr = "getline(v:lnum)=~#'^---\\\\ b'?'>1':'='"
vim.opt_local.foldlevel = FOLD_LEVEL_ON_OPEN
vim.opt_local.commentstring = "# %s"
vim.opt_local.wrap = true
vim.opt_local.linebreak = true

-- Syntax highlighting for .conv files
vim.cmd [[
  syn match convHeader /^--- b\d\+ | .*/
  syn match convId /b\d\+/ contained containedin=convHeader
  syn match convSpeaker /| \(user\|asst\) |/ contained containedin=convHeader
  syn match convTimestamp /| \d\+:\d\+$/ contained containedin=convHeader
  hi def convHeader guifg=#666666 ctermfg=242
  hi def convId guifg=#ffaf00 ctermfg=214 gui=bold
  hi def convSpeaker guifg=#87d787 ctermfg=114
  hi def convTimestamp guifg=#555555 ctermfg=240
]]

-- 컴 Keymaps 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴

vim.keymap.set("n", "]m", function()
  vim.fn.search(BLOCK_HEADER_VIM_REGEX, "W")
end, { buffer = true, desc = "next block" })

vim.keymap.set("n", "[m", function()
  vim.fn.search(BLOCK_HEADER_VIM_REGEX, "bW")
end, { buffer = true, desc = "prev block" })

vim.keymap.set("n", "<leader>ct", open_tree_sidebar,
  { buffer = true, desc = "open tree sidebar" })

vim.keymap.set("n", "<leader>cy", function()
  yank_current_block(nil)  -- default register
end, { buffer = true, desc = "yank current block" })

vim.keymap.set("n", "<leader>cf", function()
  vim.ui.input({ prompt = "fork session name: " }, function(session_name)
    if session_name and session_name ~= "" then
      fork_current_block_to_new_session(session_name)
    end
  end)
end, { buffer = true, desc = "fork block to new session" })

-- Telescope block picker (if available)
vim.keymap.set("n", "<leader>cb", function()
  local blocks = parse_all_blocks_from_buffer(vim.api.nvim_get_current_buf())
  if #blocks == 0 then
    vim.notify("no blocks", vim.log.levels.WARN)
    return
  end

  local display_entries = {}
  for _, block in ipairs(blocks) do
    table.insert(display_entries, string.format("%s  [%s  %s]  %s",
      block.identifier, block.parent_identifier, block.speaker, block.body_preview))
  end

  local telescope_ok, telescope_pickers = pcall(require, "telescope.pickers")
  if not telescope_ok then
    vim.notify("telescope not available", vim.log.levels.WARN)
    return
  end
  local telescope_finders = require("telescope.finders")
  local telescope_config = require("telescope.config").values
  local telescope_actions = require("telescope.actions")
  local telescope_action_state = require("telescope.actions.state")

  telescope_pickers.new({}, {
    prompt_title = "Conversation Blocks",
    finder = telescope_finders.new_table({
      results = display_entries,
      entry_maker = function(entry)
        return { value = entry, display = entry, ordinal = entry }
      end,
    }),
    sorter = telescope_config.generic_sorter({}),
    attach_mappings = function(prompt_buffer_number, _)
      telescope_actions.select_default:replace(function()
        telescope_actions.close(prompt_buffer_number)
        local selected_entry = telescope_action_state.get_selected_entry()
        if not selected_entry then return end
        local target_identifier = selected_entry.value:match("(b%d+)")
        if target_identifier then
          local target_line = vim.fn.search("^--- " .. target_identifier, "nw")
          if target_line > 0 then
            vim.api.nvim_win_set_cursor(0, { target_line, 0 })
            vim.cmd("normal! zv")
          end
        end
      end)
      return true
    end,
  }):find()
end, { buffer = true, desc = "telescope block picker" })

-- 컴 Commands 컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴컴�

vim.api.nvim_create_user_command("ConvTree", open_tree_sidebar,
  { desc = "Open conversation tree sidebar" })

vim.api.nvim_create_user_command("ConvYank", function()
  yank_current_block(nil)
end, { desc = "Yank current block to default register" })

vim.api.nvim_create_user_command("ConvFork", function(opts)
  local session_name = opts.args ~= "" and opts.args or "fork"
  fork_current_block_to_new_session(session_name)
end, { nargs = "?", desc = "Fork current block to new session" })
