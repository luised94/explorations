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

-- Normalize to an absolute path with no trailing slash.
kbd_local_dir = vim.fn.fnamemodify(kbd_local_dir, ":p"):gsub("/$", "")

-- === Usercommands ===
-- Open the digraph help (includes the digraph table you can search with /).
vim.api.nvim_create_user_command("ShowDigraphs", function()
  vim.cmd("help digraph-table")
end, {})

-- === Autocommands ===
local aug = vim.api.nvim_create_augroup("kbd_txt_markdown", { clear = true })

-- Add highlighting to txt files as if they are markdown.
vim.api.nvim_create_autocmd({ "BufRead", "BufNewFile" }, {
  group = aug,
  pattern = "*.txt",
  callback = function(args)
    local file = vim.api.nvim_buf_get_name(args.buf) -- full path (or "" for [No Name]) [web:19]
    if file == "" then return end
    if vim.startswith(file, kbd_local_dir .. "/") then
      vim.bo[args.buf].filetype = "markdown"
    end
  end,
})

local journal_path = string.format("%s/journal.txt", kbd_local_dir)
local notes_path = string.format("%s/notes.txt", kbd_local_dir)

-- === FUNCTIONS ===

local function insert_date_header()
    local api = vim.api
    local bufnr = 0

    -- Don't touch the buffer if we can't modify it.
    if not api.nvim_buf_get_option(bufnr, "modifiable") then
        return
    end

    -- Fixed-width format "## YYYY-MM-DD" (13 chars).
    local date_string = os.date("## %Y-%m-%d")

    -- Only touch hot data (header region). Scan until we leave the prefix.
    -- Assumption: All headers are contiguous at line 0..N with no gaps.
    local header_region_limit = 50
    local lines = api.nvim_buf_get_lines(bufnr, 0, header_region_limit, false)

    local existing_row = nil

    --Use numeric index to avoid iterator overhead (ipairs allocates closure).
    for i = 1, #lines do
        local line = lines[i]

        if line == date_string then
            existing_row = i
            break
        end

        -- Early termination. Cold data starts after header block ends.
        -- If not a header pattern, we passed the contiguous header region.
        if line:sub(1, 3) ~= "## " then
            break
        end
    end

    if existing_row then
        -- Minimal side effects on duplicate. Just move cursor.
        vim.notify("kbd: today's header exists", vim.log.levels.INFO)
        api.nvim_win_set_cursor(0, {existing_row + 1, 0})
        return
    end

    -- Defer allocation until insertion is confirmed necessary.
    -- (Duplicate path is now allocation-free).
    local insertion_block = {date_string, ""}
    api.nvim_buf_set_lines(bufnr, 0, 0, false, insertion_block)

    -- Cursor to blank line (row 2)
    api.nvim_win_set_cursor(0, {2, 0})
end

local function add_note_section()
    -- Prompt for citation key
    local citation_key = vim.fn.input("Citation key: @")

    -- User cancelled or empty input
    if citation_key == nil or citation_key == "" then
        vim.notify("kbd: cancelled", vim.log.levels.INFO)
        return
    end

    local header = string.format("## @%s", citation_key)

    -- Get all lines in buffer
    local line_count = vim.api.nvim_buf_line_count(0)
    local all_lines = vim.api.nvim_buf_get_lines(0, 0, line_count, false)

    -- Check if this citation key already exists
    for line_number, line in ipairs(all_lines) do
        if line == header then
            vim.notify(string.format("kbd: @%s already exists, jumping to it", citation_key), vim.log.levels.INFO)
            vim.api.nvim_win_set_cursor(0, {line_number, 0})
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

    table.insert(lines_to_insert, header)
    table.insert(lines_to_insert, "")

    -- Insert after last line
    vim.api.nvim_buf_set_lines(0, -1, -1, false, lines_to_insert)

    -- Move cursor to the blank line after header (ready to type)
    local new_line_count = vim.api.nvim_buf_line_count(0)
    vim.api.nvim_win_set_cursor(0, {new_line_count, 0})

    vim.notify(string.format("kbd: added @%s", citation_key), vim.log.levels.INFO)
end
--}


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
    string.format("%s%s", leader_k, "h"),
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

vim.keymap.set(
    mode_normal,
    string.format("%s%s", leader_k, "c"),
    add_note_section,
    { desc = "kbd: add citation section to notes" }
)
-- vim.notify("kbd.lua: loading complete", vim.log.levels.INFO)
