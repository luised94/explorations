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
local has_telescope, telescope_builtin = pcall(require, "telescope.builtin")
if not has_telescope then
    vim.notify("[kbd] telescope.builtin unavailable; install nvim-telescope/telescope.nvim", vim.log.levels.WARN)
    return nil
end
local uv = vim.uv or vim.loop
if uv == nil then
    vim.notify("[kbd] vim.uv or vim.loop required but unavailable", vim.log.levels.WARN)
    return nil
end

-- === CONFIGURATION ===
local api    = vim.api
local fn     = vim.fn
local keymap = vim.keymap

local kbd_local_dir = fn.fnamemodify(
    os.getenv("KBD_LOCAL_DIR") or string.format("%s/personal_repos/kbd", os.getenv("HOME") or ""),
    ":p"
):gsub("/$", "")

local kbd_mount_point = os.getenv("KBD_MOUNT_POINT")
local bib_path
if kbd_mount_point ~= nil then
    bib_path = string.format("%s/zotero_library.bib", kbd_mount_point)
else
    bib_path = string.format("%s/zotero_library.bib", kbd_local_dir)
end

local journal_path = string.format("%s/journal.txt", kbd_local_dir)
local notes_path   = string.format("%s/notes.txt",   kbd_local_dir)
local tasks_path   = string.format("%s/tasks.txt",   kbd_local_dir)

-- === CONSTANTS ===
---@type string
local BIB_GREP_PATTERN = "@[^{]+\\{\\K[^,]+"

---@type string[]
local KBD_EXCLUDE_DIRS = {
    ".git",
    "node_modules",
    "__pycache__",
    ".venv",
    "venv",
    "env",
    "build",
    "dist",
    "target",
    "out",
    ".cache",
    "tmp",
    "temp",
    "coverage",
}

---@type string
local MANUAL_ENTRY_LABEL = "Manual entry."

---@class FileSpec
---@field key  string
---@field path string
---@field desc string

---@type FileSpec[]
local FILES = {
    { key = "j", path = journal_path, desc = "open journal" },
    { key = "n", path = notes_path,   desc = "open notes"   },
    { key = "t", path = tasks_path,   desc = "open tasks"   },
}

---@type string
local MODE_NORMAL = "n"

---@type string
local LEADER_K = "<leader>k"

-- === FUNCTIONS ===

---@param path string
---@return function
local function make_open_fn(path)
    return function()
        vim.cmd(string.format("edit %s", path))
    end
end

---@return nil
local function prepend_date_header()
    local bufnr = 0
    if not api.nvim_buf_get_option(bufnr, "modifiable") then
        return
    end
    local bufname = api.nvim_buf_get_name(bufnr)
    if bufname:match("journal%.txt$") == nil then
        vim.notify("[kbd] date header only in journal.txt", vim.log.levels.WARN)
        return
    end
    local date_string = os.date("## %Y-%m-%d")
    local header_region_limit = 50
    local lines = api.nvim_buf_get_lines(bufnr, 0, header_region_limit, false)
    local existing_row = nil
    for i = 1, #lines do
        local line = lines[i]
        if line == date_string then
            existing_row = i
            break
        end
        if line:sub(1, 3) ~= "## " then
            break
        end
    end
    if existing_row ~= nil then
        vim.notify("[kbd] today's header exists", vim.log.levels.INFO)
        api.nvim_win_set_cursor(0, { existing_row + 1, 0 })
        return
    end
    api.nvim_buf_set_lines(bufnr, 0, 0, false, { date_string, "" })
    api.nvim_win_set_cursor(0, { 2, 0 })
end

---@return nil
local function prepend_note_section()
    local bufnr = 0
    if not api.nvim_buf_get_option(bufnr, "modifiable") then
        return
    end
    local bufname = api.nvim_buf_get_name(bufnr)
    if bufname:match("notes%.txt$") == nil then
        vim.notify("[kbd] note section only in notes.txt", vim.log.levels.WARN)
        return
    end
    if bib_path == nil then
        vim.notify("[kbd] bib_path not configured", vim.log.levels.ERROR)
        return
    end
    if fn.filereadable(bib_path) ~= 1 then
        vim.notify(string.format("[kbd] bib not found: %s", bib_path), vim.log.levels.ERROR)
        return
    end
    local scan_limit  = 500
    local line_count  = api.nvim_buf_line_count(bufnr)
    local actual_limit = math.min(scan_limit, line_count)
    local lines = api.nvim_buf_get_lines(bufnr, 0, actual_limit, false)
    local grep_command = string.format("grep -oP '%s' %s", BIB_GREP_PATTERN, bib_path)
    local raw_output = fn.system(grep_command)
    if vim.v.shell_error ~= 0 then
        vim.notify("[kbd] grep failed on bib file", vim.log.levels.ERROR)
        return
    end
    local citation_list = vim.split(raw_output, "\n", { trimempty = true })
    if #citation_list == 0 then
        vim.notify("[kbd] no citations found in bib", vim.log.levels.WARN)
        return
    end
    table.insert(citation_list, 1, MANUAL_ENTRY_LABEL)
    ---@param item string
    ---@return string
    local function format_item(item)
        if item == MANUAL_ENTRY_LABEL then
            return item
        end
        return "@" .. item
    end
    local select_opts = {
        prompt      = "Select citation for notes section:",
        format_item = format_item,
    }
    ---@param choice string|nil
    ---@return nil
    local function on_selection(choice)
        if choice == nil then
            vim.notify("[kbd] no citation selected", vim.log.levels.INFO)
            return
        end
        local citation_key = choice
        if choice == MANUAL_ENTRY_LABEL then
            local manual = fn.input("Citation key (manual): @")
            if manual == nil or manual == "" then
                vim.notify("[kbd] cancelled", vim.log.levels.INFO)
                return
            end
            if manual:match("%s") ~= nil then
                vim.notify("[kbd] citation key cannot contain spaces", vim.log.levels.ERROR)
                return
            end
            if manual:match("[#%[%]%(%){}<>\"'`|\\]") ~= nil then
                vim.notify("[kbd] citation key contains unsupported characters", vim.log.levels.ERROR)
                return
            end
            citation_key = manual
        end
        local header         = string.format("## @%s", citation_key)
        local header_pattern = string.format("^## @%s$", vim.pesc(citation_key))
        local existing_row   = nil
        for i = 1, #lines do
            local line = lines[i]
            if line:sub(1, 4) == "## @" and line:match(header_pattern) ~= nil then
                existing_row = i
                break
            end
        end
        if existing_row ~= nil then
            vim.notify(string.format("[kbd] @%s exists, jumping", citation_key), vim.log.levels.INFO)
            api.nvim_win_set_cursor(0, { existing_row + 1, 0 })
            return
        end
        if line_count > scan_limit then
            vim.notify(
                string.format("[kbd] scanned %d/%d lines", scan_limit, line_count),
                vim.log.levels.WARN
            )
        end
        api.nvim_buf_set_lines(bufnr, 0, 0, false, { header, "" })
        api.nvim_win_set_cursor(0, { 2, 0 })
        vim.notify(string.format("[kbd] added @%s", citation_key), vim.log.levels.INFO)
    end
    vim.ui.select(citation_list, select_opts, on_selection)
end

---@return nil
local function insert_citation_from_bib()
    if bib_path == nil then
        vim.notify("[kbd] bib_path not configured", vim.log.levels.ERROR)
        return
    end
    if fn.filereadable(bib_path) ~= 1 then
        vim.notify(string.format("[kbd] bib not found: %s", bib_path), vim.log.levels.ERROR)
        return
    end
    local grep_command = string.format("grep -oP '%s' %s", BIB_GREP_PATTERN, bib_path)
    local raw_output = fn.system(grep_command)
    if vim.v.shell_error ~= 0 then
        vim.notify("[kbd] grep failed on bib file", vim.log.levels.ERROR)
        return
    end
    local citation_list = vim.split(raw_output, "\n", { trimempty = true })
    if #citation_list == 0 then
        vim.notify("[kbd] no citations found in bib", vim.log.levels.WARN)
        return
    end
    ---@param item string
    ---@return string
    local function format_item(item)
        return "@" .. item
    end
    local select_opts = {
        prompt      = "Select citation:",
        format_item = format_item,
    }
    ---@param choice string|nil
    ---@return nil
    local function on_selection(choice)
        if choice == nil then
            vim.notify("[kbd] no citation selected", vim.log.levels.INFO)
            return
        end
        api.nvim_put({ "@" .. choice }, "c", true, true)
    end
    vim.ui.select(citation_list, select_opts, on_selection)
end

---@return nil
local function kvim_all_telescope()
    local st = uv.fs_stat(kbd_local_dir)
    if st == nil or st.type ~= "directory" then
        vim.notify(
            string.format("[kbd] directory does not exist: %s", kbd_local_dir),
            vim.log.levels.ERROR
        )
        return
    end
    local file_ignore_patterns = {}
    for i = 1, #KBD_EXCLUDE_DIRS do
        local dir     = KBD_EXCLUDE_DIRS[i]
        local escaped = dir:gsub("([^%w])", "%%%1")
        file_ignore_patterns[#file_ignore_patterns + 1] = string.format("^%s/", escaped)
    end
    telescope_builtin.find_files({
        prompt_title        = string.format("KBD (%s)", kbd_local_dir),
        cwd                 = kbd_local_dir,
        hidden              = true,
        follow              = true,
        file_ignore_patterns = file_ignore_patterns,
    })
end

-- === DECLARATIONS ===
api.nvim_create_user_command("ShowDigraphs", function()
    vim.cmd("help digraph-table")
end, {})

local txt_markdown_augroup = api.nvim_create_augroup("kbd_txt_markdown", { clear = true })
api.nvim_create_autocmd({ "BufRead", "BufNewFile" }, {
    group    = txt_markdown_augroup,
    pattern  = "*.txt",
    callback = function(args)
        local file = api.nvim_buf_get_name(args.buf)
        if file == "" then return end
        if vim.startswith(file, kbd_local_dir .. "/") then
            vim.bo[args.buf].filetype = "markdown"
        end
    end,
})

for _, f in ipairs(FILES) do
    keymap.set(MODE_NORMAL, LEADER_K .. f.key, make_open_fn(f.path), { desc = "kbd: " .. f.desc })
end

keymap.set(MODE_NORMAL, LEADER_K .. "h", prepend_date_header,     { desc = "kbd: insert date header"              })
keymap.set(MODE_NORMAL, LEADER_K .. "c", prepend_note_section,    { desc = "kbd: add citation section to notes"   })
keymap.set(MODE_NORMAL, LEADER_K .. "i", insert_citation_from_bib, { desc = "kbd: insert citation at cursor"      })
keymap.set(MODE_NORMAL, LEADER_K .. "f", kvim_all_telescope,       { desc = "kbd: find files (telescope, KBD_LOCAL_DIR)" })
