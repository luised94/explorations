# conv.lua - Repair Notes (v0.1.1)

Date: 2026-07-29
Session: test-run prototype validation

---

## BUG 1: Folds not created

**Symptom:** File opens fully unfolded. `:set foldmethod?` shows `expr` but no
folds appear. All blocks visible as flat text.

**Cause:** `foldexpr` is evaluated as **vimscript**, regardless of whether you
set it from lua via `vim.opt_local.foldexpr`. The original expression used lua
method syntax (`:match()`), which does not exist in vimscript. The expression
silently errors, vim treats the result as `0` (no fold), and nothing folds.

**Wrong (lua syntax in a vimscript context):**
```lua
vim.opt_local.foldexpr = "getline(v:lnum):match('^%-%-%- b') and '>1' or '='"
```

**Correct (vimscript syntax):**
```lua
vim.opt_local.foldexpr = "getline(v:lnum)=~#'^---\\ b'?'>1':'='"
```

**Key distinctions:**
| Context | Regex match | Digits | One-or-more | Ternary |
|---------|-------------|--------|-------------|---------|
| Lua pattern | `str:match('^%-%-%- b')` | `%d` | `+` | `x and a or b` |
| Vimscript | `str =~# '^--- b'` | `\d` | `\+` | `x ? a : b` |
| vim.fn.search() | vim regex | `\d` | `\+` | n/a |

**Rule:** If the string will be evaluated by vim's expression engine (foldexpr,
statusline expressions, etc.), write vimscript. If it's in a lua `function()`
callback, write lua. The *setter* language doesn't matter; the *evaluator* does.

---

## BUG 2: `<leader>cx` never finds children

**Symptom:** "no children" notification even when children exist.

**Cause:** `vim.fn.search()` takes a **vim regex** pattern. The original code
passed lua pattern syntax (`%d+`), which vim interprets as literal characters
`%`, `d`, `+`. No line ever matches.

**Wrong:**
```lua
vim.fn.search("^--- b%d+ | " .. id .. " | ", "nw")
```

**Correct:**
```lua
vim.fn.search("^--- b\\d\\+ | " .. id .. " | ", "nw")
```

In the lua string, `\\d` becomes `\d` and `\\+` becomes `\+` in the actual
vim regex passed to search().

---

## BUG 3: `<leader>cb` requires fzf-lua

**Symptom:** Keymap does nothing (silent fail via pcall).

**Cause:** Original code called `require("fzf-lua")`. User has telescope.
The `pcall` swallowed the error silently.

**Correct:** Use telescope's picker API:
```lua
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
      -- ... navigate to block ...
    end)
    return true
  end,
}):find()
```

---

## BUG 4: foldlevel resets to 0

**Symptom:** `:set foldlevel?` shows 0 even though lua sets it to 1.

**Cause:** Likely a global setting in init.lua or a plugin (e.g., a session
restore, or `vim.opt.foldlevel = 0` set globally) overriding the buffer-local
value after the ftplugin/luafile runs.

**Workarounds (pick one):**
```lua
-- Option A: autocmd that fires after buffer is fully loaded
vim.api.nvim_create_autocmd("BufReadPost", {
  pattern = "*.conv",
  callback = function()
    vim.opt_local.foldlevel = 1
  end,
})

-- Option B: manual, per-session
:set foldlevel=1
```

---

## DIAGNOSTIC COMMANDS (for future debugging)

```vim
" Check what vim actually sees:
:set foldmethod? foldexpr? foldlevel?

" Test foldexpr on a specific line (vimscript):
:echo eval(substitute(&foldexpr, 'v:lnum', '3', 'g'))

" Check a line's content:
:echo getline(3)

" Check character codes (verify ASCII dashes, char 45):
:echo char2nr(getline(3)[0])

" Test regex match in vimscript:
:echo getline(3) =~# '^--- b'

" Test regex match in lua:
:lua print(vim.fn.getline(3):match('^%-%-%- b'))

" List buffer-local keymaps:
:verbose map ]m
:verbose map <leader>cb

" Check if filetype triggered:
:set filetype?

" Source the lua file with error output:
:luafile ./conv.lua
" If silent failure, wrap in:
:lua local ok, err = pcall(dofile, './conv.lua'); if not ok then print(err) end
```

---

## GENERAL RULES

1. **foldexpr, statusline, tabline**  vimscript syntax inside the string.
2. **vim.fn.search(), vim.fn.substitute(), vim.fn.match()**  vim regex.
3. **lua callbacks, string.match(), string.find()**  lua patterns.
4. **Escaping across the boundary:** lua `"\\d"`  vim `\d`. Lua `"\\+"`  vim `\+`.
5. **pcall swallows errors.** During development, use `local ok, err = pcall(...)`
   and `print(err)` on failure. Don't silent-fail in prototypes.
6. **foldlevel is global-friendly.** Plugins and configs often set it globally.
   Buffer-local can be overridden. Autocmd or manual `:set` is the reliable path.
```

Save it wherever you keep the project files. `~/conversations/REPAIR-NOTES.md` or next to `conv.lua`.

Now-whenever you're ready, the Q1-Q10 answers. Even partial. Even "Q1 fine, Q9 folds." That's the data I need for v0.2.
