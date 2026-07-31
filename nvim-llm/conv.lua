-- conv.lua -- v0.2 conversation buffer navigation, tree rendering, yank, fork
-- Source: :luafile ./conv.lua  (from the nvim-llm directory)
-- Or install to: ~/.config/nvim/after/ftplugin/conv.lua
-- Requires: telescope (for block picker). No other plugin dependencies.
-- ASCII only. No Unicode characters in this file.
-- Coding guidelines: full names, no abbreviations, imperative top-level,
--   pure helper functions, side effects isolated to command handlers.

-- -- Configuration -----------------------------------------------------------

local BLOCK_HEADER_LUA_PATTERN = "^%-%-%- b%d+"
local BLOCK_HEADER_VIM_REGEX = "^--- b\\d\\+"
local BLOCK_ID_LUA_PATTERN = "(b%d+)"
local FOLD_LEVEL_ON_OPEN = 1
local TREE_SPLIT_WIDTH = 44
local TREE_BRANCH_PREFIX = "|-- "
local TREE_LAST_CHILD_PREFIX = "`-- "
local TREE_VERTICAL_CONTINUE = "|   "
local TREE_SPACE_CONTINUE = "    "

-- -- Pure transformations ----------------------------------------------------
-- These functions compute. They do not modify buffers or files.

local function parse_all_blocks_from_buffer(buffer_number)
  local all_lines = vim.api.nvim_buf_get_lines(buffer_number, 0, -1, false)
  local blocks = {}
  for line_index, line_content in ipairs(all_lines) do
    local identifier, parent_identifier, speaker, timestamp =
      line_content:match("^%-%-%- (b%d+) | (%S+) | (%S+) | (%S+)")
    if identifier then
      local body_preview = (all_lines[line_index + 1] or ""):sub(1, 56)
      table.insert(blocks, {
        identifier = identifier,
        parent_identifier = parent_identifier,
        speaker = speaker,
        timestamp = timestamp,
        body_preview = body_preview,
        line_number = line_index,
      })
    end
  end
  return blocks
end

local function build_children_map(blocks)
  local children_map = {}
  for _, block in ipairs(blocks) do
    local parent_key = block.parent_identifier
    if not children_map[parent_key] then
      children_map[parent_key] = {}
    end
    table.insert(children_map[parent_key], block)
  end
  return children_map
end

local function render_tree_lines(blocks)
  -- Returns: two parallel lists: rendered display strings, block identifiers
  local children_map = build_children_map(blocks)
  local rendered_lines = {}
  local rendered_identifiers = {}

  local function render_subtree(block, prefix, is_last_child)
    local connector = is_last_child and TREE_LAST_CHILD_PREFIX or TREE_BRANCH_PREFIX
    local display_line = string.format("%s%s%s [%s] %s",
      prefix, connector, block.identifier, block.speaker, block.body_preview)
    table.insert(rendered_lines, display_line)
    table.insert(rendered_identifiers, block.identifier)

    local children = children_map[block.identifier] or {}
    local child_prefix = prefix .. (is_last_child and TREE_SPACE_CONTINUE or TREE_VERTICAL_CONTINUE)
    for child_index, child_block in ipairs(children) do
      render_subtree(child_block, child_prefix, child_index == #children)
    end
  end

  local roots = children_map["root"] or {}
  for root_index, root_block in ipairs(roots) do
    local root_display = string.format("%s [%s] %s",
      root_block.identifier, root_block.speaker, root_block.body_preview)
    table.insert(rendered_lines, root_display)
    table.insert(rendered_identifiers, root_block.identifier)

    local children = children_map[root_block.identifier] or {}
    for child_index, child_block in ipairs(children) do
      render_subtree(child_block, "", child_index == #children)
    end

    if root_index < #roots then
      table.insert(rendered_lines, "")
      table.insert(rendered_identifiers, "")
    end
  end

  return rendered_lines, rendered_identifiers
end

-- -- Side effects (isolated to command handlers) -----------------------------

local function open_tree_sidebar()
  local current_buffer = vim.api.nvim_get_current_buf()
  local blocks = parse_all_blocks_from_buffer(current_buffer)
  if #blocks == 0 then
    vim.notify("no blocks found in buffer", vim.log.levels.WARN)
    return
  end

  local tree_lines, tree_identifiers = render_tree_lines(blocks)

  -- Create scratch buffer for the tree
  local tree_buffer_name = "conv-tree://" .. vim.fn.bufname(current_buffer)
  local existing_tree_buffer = vim.fn.bufnr(tree_buffer_name)
  if existing_tree_buffer ~= -1 then
    vim.api.nvim_buf_delete(existing_tree_buffer, { force = true })
  end

  -- Vertical split, left side
  vim.cmd("topleft " .. TREE_SPLIT_WIDTH .. "vsplit")
  local tree_buffer = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_buf_set_name(tree_buffer, tree_buffer_name)
  vim.api.nvim_win_set_buf(0, tree_buffer)
  vim.api.nvim_buf_set_lines(tree_buffer, 0, -1, false, tree_lines)

  -- Read-only scratch buffer settings
  vim.opt_local.modifiable = false
  vim.opt_local.readonly = true
  vim.opt_local.buftype = "nofile"
  vim.opt_local.bufhidden = "wipe"
  vim.opt_local.wrap = false
  vim.opt_local.cursorline = true
  vim.opt_local.number = false
  vim.opt_local.signcolumn = "no"

  -- Syntax highlighting for tree buffer (ASCII only)
  vim.cmd [[
    syn match convTreeId /b\d\+/
    syn match convTreeSpeakerUser /\[user\]/
    syn match convTreeSpeakerAsst /\[asst\]/
    syn match convTreeConnector /[|`-]/
    hi def convTreeId guifg=#ffaf00 gui=bold
    hi def convTreeSpeakerUser guifg=#87d787
    hi def convTreeSpeakerAsst guifg=#87afd7
    hi def convTreeConnector guifg=#555555
  ]]

  log_interaction_metric("tree_open", nil, #blocks .. " blocks")

  -- Enter: jump to block in conversation buffer
  vim.keymap.set("n", "<CR>", function()
    local cursor_line = vim.api.nvim_win_get_cursor(0)[1]
    local target_identifier = tree_identifiers[cursor_line]
    if not target_identifier or target_identifier == "" then return end

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

    vim.api.nvim_set_current_win(conversation_window)
    local target_line = vim.fn.search("^--- " .. target_identifier .. " ", "nw")
    if target_line > 0 then
      vim.api.nvim_win_set_cursor(conversation_window, { target_line, 0 })
      vim.cmd("normal! zv")
    end
  end, { buffer = tree_buffer, desc = "jump to block" })

  -- q: close tree sidebar
  vim.keymap.set("n", "q", function()
    vim.api.nvim_win_close(0, true)
  end, { buffer = tree_buffer, desc = "close tree" })
end

local function yank_current_block(register_name)
  local current_buffer = vim.api.nvim_get_current_buf()
  local all_lines = vim.api.nvim_buf_get_lines(current_buffer, 0, -1, false)
  local cursor_line = vim.api.nvim_win_get_cursor(0)[1]

  -- Walk up to find block header
  local block_start_line = cursor_line
  while block_start_line > 0
    and not all_lines[block_start_line]:match(BLOCK_HEADER_LUA_PATTERN) do
    block_start_line = block_start_line - 1
  end
  if block_start_line == 0 then
    vim.notify("no block header found above cursor", vim.log.levels.WARN)
    return
  end

  -- Walk down to find next header or EOF
  local block_end_line = block_start_line + 1
  while block_end_line <= #all_lines
    and not all_lines[block_end_line]:match(BLOCK_HEADER_LUA_PATTERN) do
    block_end_line = block_end_line + 1
  end
  block_end_line = block_end_line - 1

  -- Yank
  local block_lines = vim.api.nvim_buf_get_lines(
    current_buffer, block_start_line - 1, block_end_line, false)
  local yank_text = table.concat(block_lines, "\n")
  local target_register = register_name or '"'
  vim.fn.setreg(target_register, yank_text)

  log_interaction_metric("yank", block_identifier, #block_lines .. " lines")

  local block_identifier = all_lines[block_start_line]:match(BLOCK_ID_LUA_PATTERN)
  vim.notify(string.format("yanked %s (%d lines) to register %s",
    block_identifier, #block_lines, target_register), vim.log.levels.INFO)
end

local function compute_ancestry_path(blocks, target_identifier)
  -- Pure. Returns ordered list of blocks from root to target_identifier.
  local block_by_identifier = {}
  for _, block in ipairs(blocks) do
    block_by_identifier[block.identifier] = block
  end

  local path = {}
  local current_identifier = target_identifier
  while current_identifier and current_identifier ~= "root" do
    local current_block = block_by_identifier[current_identifier]
    if not current_block then break end
    table.insert(path, 1, current_block)  -- prepend
    current_identifier = current_block.parent_identifier
  end
  return path
end

local function preview_ancestry_in_scratch_buffer(ancestry_path)
  -- Side effect: opens a scratch buffer showing what will be forked.
  -- Returns nothing. User reads, then runs :ConvFork to confirm.
  local preview_lines = {
    "# FORK PREVIEW - ancestry path to be copied:",
    "# (run :ConvFork <name> to create the new session)",
    "",
  }
  for path_index, block in ipairs(ancestry_path) do
    local prefix = (path_index < #ancestry_path) and "|  " or "   "
    table.insert(preview_lines, string.format("%s%s [%s] %s",
      prefix, block.identifier, block.speaker, block.body_preview))
  end
  table.insert(preview_lines, "")
  table.insert(preview_lines, "# " .. #ancestry_path .. " blocks will be copied.")

  -- Open in a horizontal split, read-only
  vim.cmd("botright 12split")
  local preview_buffer = vim.api.nvim_create_buf(false, true)
  vim.api.nvim_win_set_buf(0, preview_buffer)
  vim.api.nvim_buf_set_lines(preview_buffer, 0, -1, false, preview_lines)
  vim.opt_local.modifiable = false
  vim.opt_local.readonly = true
  vim.opt_local.buftype = "nofile"
  vim.opt_local.bufhidden = "wipe"
  vim.opt_local.filetype = "conv-fork-preview"
end

local function fork_ancestry_to_new_session(session_name)
  -- Side effect: writes a new .conv file containing the ancestry path.
  local current_buffer = vim.api.nvim_get_current_buf()
  local all_blocks = parse_all_blocks_from_buffer(current_buffer)
  if #all_blocks == 0 then
    vim.notify("no blocks in buffer", vim.log.levels.WARN)
    return
  end

  -- Find the block at or above cursor
  local cursor_line = vim.api.nvim_win_get_cursor(0)[1]
  local target_block = nil
  for _, block in ipairs(all_blocks) do
    if block.line_number <= cursor_line then
      target_block = block
    end
  end
  if not target_block then
    vim.notify("no block at or above cursor", vim.log.levels.WARN)
    return
  end

  local ancestry_path = compute_ancestry_path(all_blocks, target_block.identifier)
  if #ancestry_path == 0 then
    vim.notify("could not compute ancestry for " .. target_block.identifier, vim.log.levels.ERROR)
    return
  end

  -- Build the new file content
  local source_file_name = vim.fn.fnamemodify(vim.fn.bufname(current_buffer), ":t")
  local original_identifiers = {}
  for _, block in ipairs(ancestry_path) do
    table.insert(original_identifiers, block.identifier)
  end

  local new_file_lines = {
    "# session: " .. os.date("%Y-%m-%d") .. " " .. session_name,
    "# forked from: " .. source_file_name,
    "# ancestry: " .. table.concat(original_identifiers, " -> "),
    "# fork point: " .. target_block.identifier,
  }

  -- Renumber blocks sequentially, preserve parent chain
  local identifier_remap = {}
  for path_index, block in ipairs(ancestry_path) do
    local new_identifier = string.format("b%03d", path_index)
    identifier_remap[block.identifier] = new_identifier
  end

  for path_index, block in ipairs(ancestry_path) do
    local new_identifier = string.format("b%03d", path_index)
    local new_parent = "root"
    if path_index > 1 then
      new_parent = string.format("b%03d", path_index - 1)
    end
    table.insert(new_file_lines, "")
    table.insert(new_file_lines, string.format("--- %s | %s | %s | %s",
      new_identifier, new_parent, block.speaker, block.timestamp))
    -- Copy body lines from original buffer
    local body_start = block.line_number  -- line after header
    local body_end = body_start
    local all_buffer_lines = vim.api.nvim_buf_get_lines(current_buffer, 0, -1, false)
    while body_end < #all_buffer_lines
      and not all_buffer_lines[body_end + 1]:match(BLOCK_HEADER_PATTERN) do
      body_end = body_end + 1
    end
    for body_line_index = body_start, body_end do
      table.insert(new_file_lines, all_buffer_lines[body_line_index])
    end
  end

  -- Write the file
  local conversation_directory = os.getenv("CONVERSATION_DIRECTORY")
    or (os.getenv("HOME") .. "/conversations")
  local new_file_path = conversation_directory .. "/"
    .. os.date("%Y-%m-%d") .. "-" .. session_name .. ".conv"
  vim.fn.writefile(new_file_lines, new_file_path)
  log_interaction_metric("fork", target_block.identifier, #ancestry_path .. " blocks -> " .. session_name)
  vim.notify("forked " .. #ancestry_path .. " blocks -> " .. new_file_path, vim.log.levels.INFO)
  vim.cmd("edit " .. new_file_path)
end

-- -- Buffer setup (runs on source) -------------------------------------------

vim.opt_local.foldmethod = "expr"
vim.opt_local.foldexpr = "getline(v:lnum)=~#'^---\\\\ b'?'>1':'='"
vim.opt_local.foldlevel = FOLD_LEVEL_ON_OPEN
vim.opt_local.commentstring = "# %s"
vim.opt_local.wrap = true
vim.opt_local.linebreak = true

-- Syntax highlighting for .conv files (ASCII only)
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

-- -- Keymaps -----------------------------------------------------------------

vim.keymap.set("n", "]m", function()
  log_interaction_metric("navigate", nil, "next")   -- or "prev"
  vim.fn.search(BLOCK_HEADER_VIM_REGEX, "W")
end, { buffer = true, desc = "next block" })

vim.keymap.set("n", "[m", function()
  log_interaction_metric("navigate", nil, "next")   -- or "prev"
  vim.fn.search(BLOCK_HEADER_VIM_REGEX, "bW")
end, { buffer = true, desc = "prev block" })

vim.keymap.set("n", "<leader>ct", open_tree_sidebar,
  { buffer = true, desc = "open tree sidebar" })

vim.keymap.set("n", "<leader>cy", function()
  yank_current_block(nil)
end, { buffer = true, desc = "yank current block" })

vim.keymap.set("n", "<leader>cf", function()
  vim.ui.input({ prompt = "fork session name: " }, function(session_name)
    if session_name and session_name ~= "" then
      fork_current_block_to_new_session(session_name)
    end
  end)
end, { buffer = true, desc = "fork block to new session" })

-- Telescope block picker
vim.keymap.set("n", "<leader>cb", function()
  local blocks = parse_all_blocks_from_buffer(vim.api.nvim_get_current_buf())
  if #blocks == 0 then
    vim.notify("no blocks", vim.log.levels.WARN)
    return
  end

  local display_entries = {}
  for _, block in ipairs(blocks) do
    table.insert(display_entries, string.format("%s  [%s -> %s]  %s",
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
          local target_line = vim.fn.search("^--- " .. target_identifier .. " ", "nw")
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

-- -- Commands ----------------------------------------------------------------

vim.api.nvim_create_user_command("ConvTree", open_tree_sidebar,
  { desc = "Open conversation tree sidebar" })

vim.api.nvim_create_user_command("ConvYank", function()
  yank_current_block(nil)
end, { desc = "Yank current block to default register" })

-- Replace the old ConvFork command:
vim.api.nvim_create_user_command("ConvForkPreview", function()
  local current_buffer = vim.api.nvim_get_current_buf()
  local all_blocks = parse_all_blocks_from_buffer(current_buffer)
  local cursor_line = vim.api.nvim_win_get_cursor(0)[1]
  local target_block = nil
  for _, block in ipairs(all_blocks) do
    if block.line_number <= cursor_line then target_block = block end
  end
  if not target_block then
    vim.notify("no block at cursor", vim.log.levels.WARN)
    return
  end
  local ancestry_path = compute_ancestry_path(all_blocks, target_block.identifier)
  preview_ancestry_in_scratch_buffer(ancestry_path)
end, { desc = "Preview what :ConvFork will copy" })

vim.api.nvim_create_user_command("ConvFork", function(opts)
  local session_name = opts.args ~= "" and opts.args or "fork"
  fork_ancestry_to_new_session(session_name)
end, { nargs = "?", desc = "Fork ancestry path to new session" })

-- Keymaps
vim.keymap.set("n", "<leader>cf", function()
  vim.ui.input({ prompt = "fork session name: " }, function(session_name)
    if session_name and session_name ~= "" then
      fork_ancestry_to_new_session(session_name)
    end
  end)
end, { buffer = true, desc = "fork ancestry to new session" })

vim.keymap.set("n", "<leader>cp", function()
  vim.cmd("ConvForkPreview")
end, { buffer = true, desc = "preview fork ancestry" })

---- Metrics (observational side effects) ----------------------------

local METRICS_LOG_PATH = (os.getenv("CONVERSATION_DIRECTORY")
  or (os.getenv("HOME") .. "/conversations")) .. "/interaction-metrics.log"

local function log_interaction_metric(action_name, block_identifier, detail)
  -- Side effect: appends one line to the metrics log.
  local timestamp = os.date("%Y-%m-%dT%H:%M:%S")
  local source_file = vim.fn.fnamemodify(vim.fn.bufname(0), ":t")
  local line = string.format("%s\t%s\t%s\t%s\t%s",
    timestamp, action_name, block_identifier or "-", source_file, detail or "-")
  local file_handle = io.open(METRICS_LOG_PATH, "a")
  if file_handle then
    file_handle:write(line .. "\n")
    file_handle:close()
  end
end

--[[ I had to add this to the init.lua to make sure it loads. Need to update this to the plugin standard I use and then symlink into the mc_extensions directory.
vim.filetype.add({ extension = { conv = "conv" } })
vim.api.nvim_create_autocmd("Filetype", {
  pattern = "conv",
  callback = function()
    dofile(vim.fn.expand("~/personal_repos/explorations--nvim-llm/nvim-llm/conv.lua"))
  end,
})
--]]
