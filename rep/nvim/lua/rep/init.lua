-- rep's nvim plugin (PLAN.md D43): ids stamped on save in library files,
-- and :RepCapture to start an item from what you are reading.
--
-- REPRESENTATION
--   library_directory   the real path of <data root>/library, asked of
--                       `rep where --data-root` on first use, then kept for
--                       the nvim session; false once asking has failed, so a
--                       missing `rep` is reported once, not on every save.
--   rep_command         the executable to run, "rep" unless setup() says.
--
-- INVARIANTS
--   N1  Only files directly in the library directory are stamped (rep reads
--       only those, storage.py).
--   N2  Stamp only inserts id lines (PLAN.md I9), so its output is applied as
--       insertions: the cursor, marks, folds and undo history of every other
--       line are kept. Output that changes a line is not applied at all.
--   N3  A refused stamp leaves the buffer as it was; the save goes ahead, and
--       the problems are in the quickfix list at their lines.
--   N4  Capture never writes: it opens the library file with an item to fill,
--       and the ordinary save stamps it (one write path, so capture problems
--       show at the real file's lines).

local rep_module = {}

local rep_command = "rep"
local library_directory = nil

local function find_library_directory()
  if library_directory == nil then
    local started, process = pcall(vim.system, { rep_command, "where", "--data-root" }, { text = true })
    local result = started and process:wait() or nil
    if result == nil or result.code ~= 0 then
      library_directory = false
      vim.notify(
        "rep: `" .. rep_command .. " where --data-root` failed; stamp on save and :RepCapture are off this session. "
          .. (result and result.stderr or tostring(process)),
        vim.log.levels.ERROR
      )
    else
      local data_root = vim.trim(result.stdout)
      -- Real paths on both sides, so a symlinked data root still matches.
      library_directory = (vim.uv.fs_realpath(data_root) or data_root) .. "/library"
    end
  end
  return library_directory or nil
end

function rep_module.setup(options)
  rep_command = (options and options.command) or "rep"
  local augroup = vim.api.nvim_create_augroup("rep", { clear = true })

  vim.api.nvim_create_autocmd("BufWritePre", {
    group = augroup,
    pattern = "*.md",
    callback = function(event)
      local buffer_name = vim.api.nvim_buf_get_name(event.buf)
      -- The directory's real path, not the file's: a captured file may not
      -- exist yet. N1.
      local buffer_directory = vim.uv.fs_realpath(vim.fs.dirname(buffer_name))
      if buffer_directory == nil or buffer_directory ~= find_library_directory() then
        return
      end
      local old_text = table.concat(vim.api.nvim_buf_get_lines(event.buf, 0, -1, false), "\n") .. "\n"
      local result = vim.system({ rep_command, "stamp", "--path", buffer_name }, { stdin = old_text, text = true }):wait()

      if result.code == 1 then
        -- N3. Lines are path:line:col: severity: message (PLAN.md D30).
        vim.fn.setqflist({}, " ", {
          title = "rep stamp",
          lines = vim.split(vim.trim(result.stderr), "\n", { plain = true }),
          efm = "%f:%l:%c: %t%*[a-z]: %m",
        })
        vim.notify("rep: nothing stamped; the problems are in the quickfix list (:copen)", vim.log.levels.WARN)
        return
      elseif result.code ~= 0 then
        vim.notify(vim.trim(result.stderr), vim.log.levels.ERROR)
        return
      end

      local new_lines = vim.split(result.stdout, "\n", { plain = true })
      if new_lines[#new_lines] == "" then
        table.remove(new_lines)
      end
      local hunks = vim.diff(old_text, result.stdout, { result_type = "indices" })
      -- N2: check every hunk before applying any. stamp has already recorded
      -- its item_stamped events, so the message says what that leaves.
      for _, hunk in ipairs(hunks) do
        if hunk[2] ~= 0 then
          vim.notify(
            "rep: stamp changed a line instead of inserting one (PLAN.md I9); the buffer is left as it was, "
              .. "and the ids it recorded are in no file: report this",
            vim.log.levels.ERROR
          )
          return
        end
      end
      -- From the last hunk up, so each insertion leaves the earlier line
      -- numbers valid. An insertion after old line N is at 0-based index N.
      for hunk_index = #hunks, 1, -1 do
        local old_start, _, new_start, new_count = unpack(hunks[hunk_index])
        vim.api.nvim_buf_set_lines(
          event.buf, old_start, old_start, false, vim.list_slice(new_lines, new_start, new_start + new_count - 1)
        )
      end
    end,
  })

  vim.api.nvim_create_user_command("RepCapture", function(command_arguments)
    local target_library_directory = find_library_directory()
    if target_library_directory == nil then
      return
    end
    -- The source is the nearest `## @citekey` above the cursor, the
    -- grammar's source section (CONVENTIONS.md), so a kbd reading note
    -- needs no other marking. Searched before the split changes buffers.
    local heading_line_number = vim.fn.search([[^## @\S\+]], "bnW")
    local citekey = heading_line_number > 0 and vim.fn.getline(heading_line_number):match("^## @(%S+)") or nil
    -- The kbd "??" marks an unverified citekey: kept in the source, not in
    -- the file name.
    local file_name = command_arguments.args ~= "" and command_arguments.args
      or (citekey and citekey:gsub("%?%?$", ""))
    if file_name == nil or file_name == "" then
      vim.notify("rep: no `## @citekey` above the cursor; name the file: :RepCapture <name>", vim.log.levels.ERROR)
      return
    end
    file_name = file_name:gsub("%.md$", "")
    if file_name:find("/") or file_name:sub(1, 1) == "." then
      vim.notify("rep: '" .. file_name .. "' cannot be a library file name (no '/', no leading '.')", vim.log.levels.ERROR)
      return
    end

    vim.cmd("split " .. vim.fn.fnameescape(target_library_directory .. "/" .. file_name .. ".md"))
    local item_template = { "### Q: ", "A: " }
    if citekey ~= nil then
      table.insert(item_template, "source: @" .. citekey)
    end
    local existing_lines = vim.api.nvim_buf_get_lines(0, 0, -1, false)
    local question_line_number
    if #existing_lines == 1 and existing_lines[1] == "" then
      -- A new file: the template is the whole buffer.
      vim.api.nvim_buf_set_lines(0, 0, -1, false, item_template)
      question_line_number = 1
    else
      table.insert(item_template, 1, "")
      vim.api.nvim_buf_set_lines(0, -1, -1, false, item_template)
      question_line_number = #existing_lines + 2
    end
    vim.api.nvim_win_set_cursor(0, { question_line_number, #"### Q: " })
    vim.cmd("startinsert!")
  end, { nargs = "?", desc = "rep: start an item in the library file of the source above the cursor" })
end

return rep_module
