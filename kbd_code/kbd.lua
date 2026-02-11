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
  error("kbd: telescope.builtin unavailable; install nvim-telescope/telescope.nvim")
end

local uv = vim.uv or vim.loop
if not uv then
  error("kbd: vim.uv or vim.loop required but unavailable")
end



-- vim.notify("kbd.lua: loading started", vim.log.levels.INFO)

-- === CONFIGURATION ===

local kbd_local_dir = os.getenv("KBD_LOCAL_DIR")
if kbd_local_dir == nil then
    kbd_local_dir = string.format("%s/personal_repos/kbd", os.getenv("HOME"))
end

-- Normalize to an absolute path with no trailing slash.
kbd_local_dir = vim.fn.fnamemodify(kbd_local_dir, ":p"):gsub("/$", "")

local kbd_mount_point = os.getenv("KBD_MOUNT_POINT")
local bib_path = kbd_mount_point
    and string.format("%s/zotero_library.bib", kbd_mount_point)
    or string.format("%s/zotero_library.bib", kbd_local_dir)

-- Citation key extraction pattern for grep.
-- BetterBibTeX format: @type{citekey, -> extract citekey
local BIB_GREP_PATTERN = "@[^{]+\\{\\K[^,]+"

-- Directories to ignore (relative to KBD_LOCAL_DIR)
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
local tasks_path = string.format("%s/tasks.txt", kbd_local_dir)

-- === FUNCTIONS ===

local function prepend_date_header()
    local api = vim.api
    local bufnr = 0

    -- Don't touch the buffer if we can't modify it.
    if not api.nvim_buf_get_option(bufnr, "modifiable") then
        return
    end
  --
    -- Guard: only run in journal.txt
    local bufname = vim.api.nvim_buf_get_name(bufnr)
    if not bufname:match("journal%.txt$") then
        vim.notify("kbd: date header only in journal.txt", vim.log.levels.WARN)
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

local function prepend_note_section()
    -- GUARDS
    local api = vim.api
    local bufnr = 0

    -- Don't touch the buffer if we can't modify it.
    if not api.nvim_buf_get_option(bufnr, "modifiable") then
        return
    end

    -- Guard: only run in notes.txt
    local bufname = api.nvim_buf_get_name(bufnr)
    if not bufname:match("notes%.txt$") then
        vim.notify("kbd: note section only in notes.txt", vim.log.levels.WARN)
        return
    end

    -- Bib guards (mirror insert_citation_from_bib)
    if not bib_path then
        vim.notify("kbd: bib_path not configured", vim.log.levels.ERROR)
        return
    end

    local bib_exists = vim.fn.filereadable(bib_path) == 1
    if not bib_exists then
        vim.notify(string.format("kbd: bib not found: %s", bib_path), vim.log.levels.ERROR)
        return
    end

    -- PREPROCESSING
    local scan_limit = 500
    local line_count = api.nvim_buf_line_count(bufnr)
    local actual_limit = math.min(scan_limit, line_count)
    local lines = api.nvim_buf_get_lines(bufnr, 0, actual_limit, false)

    -- Extract citation keys via grep. -o outputs only matches, -P enables Perl regex.
    local grep_command = string.format("grep -oP '%s' %s", BIB_GREP_PATTERN, bib_path)
    local raw_output = vim.fn.system(grep_command)

    local grep_failed = vim.v.shell_error ~= 0
    if grep_failed then
        vim.notify("kbd: grep failed on bib file", vim.log.levels.ERROR)
        return
    end

    local citation_list = vim.split(raw_output, "\n", { trimempty = true })

    local no_citations = #citation_list == 0
    if no_citations then
        vim.notify("kbd: no citations found in bib", vim.log.levels.WARN)
        return
    end

    -- MAIN LOGIC
    -- Telescope-backed UI (via vim.ui.select) will let you search-as-you-type.
    local select_opts = {
        prompt = "Select citation for notes section:",
        format_item = function(item)
            return "@" .. item
        end,
    }

    local on_selection = function(choice)
        if not choice then
            vim.notify("kbd: no citation selected", vim.log.levels.INFO)
            return
        end

        local citation_key = choice
        local header = string.format("## @%s", citation_key)

        -- Escape pattern magic chars in citation key for robust matching.
        local header_pattern = string.format("^## @%s$", vim.pesc(citation_key))

        local existing_row = nil
        for i = 1, #lines do
            local line = lines[i]
            if line:sub(1, 4) == "## @" and line:match(header_pattern) then
                existing_row = i
                break
            end
        end

        if existing_row then
            vim.notify(string.format("kbd: @%s exists, jumping", citation_key), vim.log.levels.INFO)
            api.nvim_win_set_cursor(0, { existing_row + 1, 0 })
            return
        end

        if line_count > scan_limit then
            vim.notify(
                string.format("kbd: scanned %d/%d lines", scan_limit, line_count),
                vim.log.levels.WARN
            )
        end

        local insertion_block = { header, "" }
        api.nvim_buf_set_lines(bufnr, 0, 0, false, insertion_block)
        api.nvim_win_set_cursor(0, { 2, 0 })
        vim.notify(string.format("kbd: added @%s", citation_key), vim.log.levels.INFO)
    end

    vim.ui.select(citation_list, select_opts, on_selection)
end

local function insert_citation_from_bib()
    -- GUARDS
    if not bib_path then
        vim.notify("kbd: bib_path not configured", vim.log.levels.ERROR)
        return
    end

    local bib_exists = vim.fn.filereadable(bib_path) == 1
    if not bib_exists then
        vim.notify(string.format("kbd: bib not found: %s", bib_path), vim.log.levels.ERROR)
        return
    end

    -- PREPROCESSING
    -- Extract citation keys via grep. -o outputs only matches, -P enables Perl regex.
    local grep_command = string.format("grep -oP '%s' %s", BIB_GREP_PATTERN, bib_path)
    local raw_output = vim.fn.system(grep_command)

    local grep_failed = vim.v.shell_error ~= 0
    if grep_failed then
        vim.notify("kbd: grep failed on bib file", vim.log.levels.ERROR)
        return
    end

    local citation_list = vim.split(raw_output, "\n", { trimempty = true })

    local no_citations = #citation_list == 0
    if no_citations then
        vim.notify("kbd: no citations found in bib", vim.log.levels.WARN)
        return
    end

    -- MAIN LOGIC
    -- vim.ui.select integrates with telescope if configured.
    local select_opts = {
        prompt = "Select citation:",
        format_item = function(item)
            return "@" .. item
        end,
    }

    local on_selection = function(choice)
        if not choice then
            vim.notify("kbd: no citation selected", vim.log.levels.INFO)
            return
        end

        local formatted_citation = "@" .. choice
        local insert_mode = 'c'      -- character-wise
        local insert_after = true
        local move_cursor = true
        vim.api.nvim_put({formatted_citation}, insert_mode, insert_after, move_cursor)
    end

    vim.ui.select(citation_list, select_opts, on_selection)
end

local function kvim_all_telescope()
  local kbd_local_dir = os.getenv("KBD_LOCAL_DIR")
  if kbd_local_dir == nil or kbd_local_dir == "" then
    kbd_local_dir = string.format("%s/personal_repos/kbd", os.getenv("HOME") or "")
  end

  local st = uv.fs_stat(kbd_local_dir)
  if not st or st.type ~= "directory" then
    vim.notify(string.format("kbd: directory does not exist: %s", kbd_local_dir), vim.log.levels.ERROR)
    return
  end

  local file_ignore_patterns = {}
  for i = 1, #KBD_EXCLUDE_DIRS do
    local dir = KBD_EXCLUDE_DIRS[i]
    -- Escape Lua pattern magic so ".git" matches literally.
    local escaped = dir:gsub("([^%w])", "%%%1")
    file_ignore_patterns[#file_ignore_patterns + 1] = string.format("^%s/", escaped)
  end

  telescope_builtin.find_files({
    prompt_title = string.format("KBD (%s)", kbd_local_dir),
    cwd = kbd_local_dir,
    hidden = true,
    follow = true,
    file_ignore_patterns = file_ignore_patterns,
  })
end

local function open_journal()
    local command = string.format("edit %s", journal_path)
    vim.cmd(command)
end

local function open_notes()
    local command = string.format("edit %s", notes_path)
    vim.cmd(command)
end

local function open_tasks()
    local command = string.format("edit %s", tasks_path)
    vim.cmd(command)
end

-- === KEYBINDINGS ===

local mode_normal = 'n'
local leader_k = '<leader>k'

vim.keymap.set(
    mode_normal,
    string.format("%s%s", leader_k, "h"),
    prepend_date_header,
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
    prepend_note_section,
    { desc = "kbd: add citation section to notes" }
)

vim.keymap.set(
    mode_normal,
    string.format("%s%s", leader_k, "t"),
    open_tasks,
    { desc = "kbd: open tasks.txt" }
)

vim.keymap.set(
    mode_normal,
    string.format("%s%s", leader_k, "i"),
    insert_citation_from_bib,
    { desc = "kbd: insert citation at cursor" }
)

vim.keymap.set(
  mode_normal,
  string.format("%s%s", leader_k, "f"),
  kvim_all_telescope,
  { desc = "kbd: find files (telescope, rooted at KBD_LOCAL_DIR)" }
)
-- vim.notify("kbd.lua: loading complete", vim.log.levels.INFO)
