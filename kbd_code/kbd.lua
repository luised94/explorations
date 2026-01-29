-- kbd.lua
-- Neovim keybindings for kbd (knowledge base desk)
-- Loaded by extension loader after lazy.nvim setup
-- === GUARDS ===

if vim == nil then
    print("kbd.lua: not running in neovim, exiting")
    return
end

if vim.keymap == nil then
    vim.notify("kbd.lua: vim.keymap not available (neovim < 0.7?), exiting", vim.log.levels.ERROR)
    return
end

if vim.api == nil then
    vim.notify("kbd.lua: vim.api not available, exiting", vim.log.levels.ERROR)
    return
end

-- vim.notify("kbd.lua: loading started", vim.log.levels.INFO)

-- === CONFIGURATION ===

local kbd_local_dir = os.getenv("KBD_LOCAL_DIR")
if kbd_local_dir == nil then
    kbd_local_dir = string.format("%s/personal_repos/kbd", os.getenv("HOME"))
end

local journal_path = string.format("%s/journal.txt", kbd_local_dir)
local notes_path = string.format("%s/notes.txt", kbd_local_dir)

-- === ACTIONS ===

local function insert_date_header()
    local date_string = os.date("## %Y-%m-%d")

    -- Get all lines in buffer
    local line_count = vim.api.nvim_buf_line_count(0)
    local all_lines = vim.api.nvim_buf_get_lines(0, 0, line_count, false)

    -- Check if today's header already exists
    -- NOTE: This scans entire buffer. For very large files (10k+ lines),
    -- could optimize by: searching backwards from end, only checking ## lines,
    -- or using vim.fn.search(). Premature for now - journal would need
    -- years of daily entries before this matters.
    for _, line in ipairs(all_lines) do
        if line == date_string then
            vim.notify("kbd: today's date header already exists", vim.log.levels.INFO)
            -- Optional: jump to it instead of duplicating
            vim.cmd(string.format("/%s", date_string))
            return
        end
    end

    -- Go to end of file
    vim.cmd("normal! G")

    -- Add blank line if file doesn't end with one
    local last_line = vim.api.nvim_buf_get_lines(0, -2, -1, false)[1] or ""
    local lines_to_insert = {}

    if last_line ~= "" then
        table.insert(lines_to_insert, "")
    end

    table.insert(lines_to_insert, date_string)
    table.insert(lines_to_insert, "")

    -- Insert after last line
    vim.api.nvim_buf_set_lines(0, -1, -1, false, lines_to_insert)

    -- Move cursor to the blank line after header (ready to type)
    local new_line_count = vim.api.nvim_buf_line_count(0)
    vim.api.nvim_win_set_cursor(0, {new_line_count, 0})
end

local function open_journal()
    local command = string.format("edit %s", journal_path)
    vim.cmd(command)
end

local function open_notes()
    local command = string.format("edit %s", notes_path)
    vim.cmd(command)
end

-- === KEYBINDINGS ===

local mode_normal = 'n'
local leader_k = '<leader>k'

vim.keymap.set(
    mode_normal,
    string.format("%s%s", leader_k, "d"),
    insert_date_header,
    { desc = "kbd: insert date header" }
)

vim.keymap.set(
    mode_normal,
    string.format("%s%s", leader_k, "j"),
    open_journal,
    { desc = "kbd: open journal" }
)

vim.keymap.set(
    mode_normal,
    string.format("%s%s", leader_k, "n"),
    open_notes,
    { desc = "kbd: open notes" }
)

-- vim.notify("kbd.lua: loading complete", vim.log.levels.INFO)
