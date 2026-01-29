-- kbd.lua
-- Neovim keybindings for kbd (knowledge base desk)
-- Loaded by extension loader after lazy.nvim setup
vim.notify("kbd.lua: loading started", vim.log.levels.INFO)

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
    local lines_to_insert = { date_string, "" }
    local insert_type = "l"      -- "l" = linewise
    local insert_after = true    -- insert after cursor line
    local move_cursor = true     -- move cursor to end of inserted text
    vim.api.nvim_put(lines_to_insert, insert_type, insert_after, move_cursor)
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

vim.notify("kbd.lua: loading complete", vim.log.levels.INFO)
