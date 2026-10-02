# rep: findings about neighbouring code

date: 2026-10-01
scope: code rep depends on or sits beside but does not own: the person's
nvim config (my_config/nvim: init.lua, lua/plugins.lua), the nvim
extensions (kbd.lua), and the explorations repository. rep never fixes
these (PLAN.md D16: kbd is read, never written); this file carries what a
build thread found, so the person can take it to the nvim config rework.
Each finding has an id (F<n>) for citing, a severity, where, what, the
evidence, and a fix.

Severity:
  critical       silently wrong data or behavior
  bug            wrong behavior that shows itself
  inconsistency  two places disagree about one fact
  deprecated     works on nvim 0.11, warned about, scheduled to go
  suggestion     data flow, boundaries, interfaces for the rework

Sources of evidence: the files as uploaded in thread 3 (2026-10-01); nvim
0.11.4 runtime docs and headless runs in the build sandbox (the person runs
0.11.6); mason-lspconfig.nvim at b329899 and nvim-lspconfig at 3e8d598
(GitHub, 2026-09-27 and 2026-09-30).

--------------------------------------------------------------------------------
## explorations repository
--------------------------------------------------------------------------------

F1  inconsistency  explorations/.gitignore line 20: `uv.lock`
  What: every Python project under explorations has its lock ignored. rep
  re-includes its own with `!uv.lock` in rep/.gitignore (57559e3), so rep
  is unaffected; any other uv project there runs without a pinned
  toolchain in git.
  Evidence: `git check-ignore -v rep/uv.lock` printed
  `.gitignore:20:uv.lock` on the person's machine.
  Fix: remove the root rule, and let each project decide (an application
  tracks its lock; uv's documentation recommends it). rep's negation then
  becomes redundant and harmless.

--------------------------------------------------------------------------------
## nvim: init.lua
--------------------------------------------------------------------------------

F2  critical  init.lua, CLIPBOARD (copy = clip.exe)
  What: yanks to the + register pipe raw UTF-8 into clip.exe, which reads
  it in the console code page; accented and other non-ASCII text pastes
  into Windows garbled.
  Evidence: measured for rep (PLAN.md section 3): `cafe-with-acute lambda`
  through clip.exe produced CP437 mojibake; UTF-16LE with a byte-order
  mark pasted intact.
  Fix: copy through a command that converts first, for example
  `copy = { ["+"] = { "sh", "-c", "{ printf '\\377\\376'; iconv -f utf-8 -t utf-16le; } | clip.exe" }, ... }`
  (the route measured), or use win32yank.exe for both copy and paste,
  which also replaces the powershell.exe paste (F9). The command above
  was checked in the sandbox with od in place of clip.exe: it emits
  ff fe and then UTF-16LE; clip.exe itself was not run there.

F3  bug  init.lua, EXTENSIONS (the `return` when the directory is missing)
  What: when ~/.config/mc_extensions does not exist, the top-level
  `return` ends init.lua, so the nvim-llm `conv` filetype and autocmd
  below it are never set up.
  Evidence: Lua semantics: `return` in a chunk ends the chunk; the conv
  block is the last thing in the file.
  Fix: wrap the loader in its own block or function and skip it instead of
  returning; or, with the move to lazy.nvim (F16), delete the loader.

F4  bug  init.lua, EXTENSIONS (spec.setup(), keymap.set, nvim_create_autocmd)
  What: each file is loaded under pcall, but its setup() and the
  registration calls are not, so one extension that errors there stops
  every extension after it and the rest of init.lua.
  Evidence: only `chunk` is called through pcall; an error raised by
  spec.setup() propagates out of the top-level chunk.
  Fix: pcall each registration per extension and report the file name;
  or move to lazy.nvim (F16), which isolates each plugin's config.

F5  bug  init.lua <leader>r (runner) with the LSP's buffer-local <leader>rn
  What: in any buffer with an LSP attached, <Space>r waits timeoutlen
  (1000 ms) before running the current file, because <Space>rn (rename,
  plugins.lua on_lsp_attach) makes it ambiguous.
  Evidence: headless nvim, timeoutlen 1000: a global <Space>r ran after
  0 ms alone and after 1001 ms with a buffer-local <Space>rn present.
  `:h map-ambiguous`, `:h map-nowait`.
  Fix: move one of them (rename to <leader>cr next to <leader>ca, or the
  runner elsewhere). A single prefix table (F17) prevents the next one.

F6  bug  init.lua RUNNER_SPECS (command strings with %s)
  What: file paths are pasted into shell commands unquoted, so a path
  with a space or shell characters breaks or runs something else.
  Fix: fn.shellescape(filepath) and the same for the C output name.

F7  inconsistency  init.lua KEYMAPS <leader>q
  What: described as "open quickfix list"; it calls
  vim.diagnostic.setloclist, which fills the location list.
  Fix: correct the description, or call setqflist if quickfix is meant.

F8  deprecated  init.lua
  vim.diagnostic.goto_prev and goto_next: use vim.diagnostic.jump with
  {count = -1} or {count = 1} (and float = true to keep the float).
  vim.highlight.on_yank: renamed vim.hl.on_yank.
  Evidence: nvim 0.11 runtime doc/deprecated.txt.

F9  suggestion  init.lua clipboard paste
  What: every paste starts powershell.exe (cache_enabled = 0), which
  takes a noticeable fraction of a second per paste.
  Fix: win32yank.exe -o --lf for paste (and F2's copy).

F10 suggestion  init.lua, nvim-llm conv autocmd
  What: dofile() runs conv.lua again on every FileType conv event, and the
  autocmd has no group, so re-sourcing init.lua adds duplicates. The path
  is hard-coded.
  Fix: a lazy.nvim spec with dir = the nvim-llm path and ft = "conv"
  (F16).

--------------------------------------------------------------------------------
## nvim: lua/plugins.lua
--------------------------------------------------------------------------------

F11 critical  plugins.lua, LSP (mason_lspconfig.setup({ handlers = ... }))
  What: mason-lspconfig 2.x removed the `handlers` setting. The spec is
  unpinned, so lazy.nvim installs 2.x, which enables every installed
  server with its default configuration; setup_lsp_server never runs, so
  LSP_SERVERS' settings (lua_ls globals and library, marksman's root_dir,
  the shared capabilities) are silently not applied.
  Evidence: mason-lspconfig CHANGELOG, 2.0.0, "Removed Features": "Remove
  the `handlers` setting and `.setup_handlers()` function. It has been
  replaced by the new native vim.lsp.config() API and a new
  automatic_enable setting." The code at b329899 has no handlers.
  Unless lazy-lock.json pins a 1.x commit (check with :Lazy).
  Fix: call vim.lsp.config(name, server) for each entry of LSP_SERVERS
  directly, before mason_lspconfig.setup({ ensure_installed = ... });
  automatic_enable then enables them with those settings. Confirm with
  :checkhealth vim.lsp in a Lua buffer.

F12 inconsistency  plugins.lua BIBTEX_CONFIG global_files
  What: telescope-bibtex searches ~/mylibrary.bib; kbd.lua and rep read
  the kbd export (zotero_library.bib). Unless ~/mylibrary.bib links to
  it, the bibtex picker offers a different (or empty) set of keys.
  Fix: point it at the same file; see F17 for one source of the path.

F13 deprecated  plugins.lua
  vim.lsp.with (hover and signature borders): deprecated in 0.11; set
  vim.o.winborder = "rounded" instead. lspconfig.util.find_git_ancestor
  (r_ls_root_dir): marked deprecated in nvim-lspconfig; use
  vim.fs.root(fname, ".git").

F14 suggestion  plugins.lua get_quarto_resource_path()
  What: io.popen("quarto --paths") runs synchronously each time the LSP
  config runs, on every start.
  Fix: load the LSP spec on an event (BufReadPre), or cache the path.

--------------------------------------------------------------------------------
## nvim: kbd.lua (the D16 list, with fixes, and two more)
--------------------------------------------------------------------------------

F15 bug and inconsistency  kbd.lua
  a. prepend_note_section scans only the first 500 lines for an existing
     `## @key` section, so a section further down is not found and a
     duplicate header is inserted at the top. Fix: scan the whole buffer
     (it is in memory already).
  b. The bib path is pasted unquoted into the grep command. Fix:
     fn.shellescape(bib_path), or vim.system with an argument list.
  c. The telescope guard returns nil, so a missing telescope removes
     every kbd key, including the ones that do not use it. Fix: under
     lazy.nvim, declare telescope as a dependency and drop the guard.
  d. kbd_isolate copies a section into a nofile buffer with
     bufhidden=wipe: edits made there are silently lost. Fix: make it
     read-only (modifiable = false), or write back on demand.
  e. api.nvim_buf_get_option is deprecated in 0.11; use
     vim.bo[bufnr].modifiable.
  f. BIB_GREP_PATTERN `@[^{]+\{\K[^,]+` is not anchored to the line
     start and does not exclude @comment, @string or @preamble, so the
     pickers can offer string macro names and text from inside fields.
     rep reads keys with an anchored pattern that excludes those three
     (PLAN.md D25). Fix: `^@(?!comment|string|preamble)[A-Za-z]+\{\K[^,]+`
     with grep -oP -i. Evidence: on a six-line sample bib, today's
     pattern returned `jbc = "J Biol Chem"}` (a @string), `jabref-meta: x`
     (a @Comment) and `x}` (from inside an abstract) besides the two keys;
     the fixed pattern returned only the two keys.
  g. kbd_questions takes any line containing "?:", anywhere in the line;
     the kbd and rep convention is a line that starts with "?:"
     (CONVENTIONS.md), so prose such as "why?: because" is listed. Fix:
     match "^%?:".

--------------------------------------------------------------------------------
## pyutils: terminal_output.py (read 2026-10-02, sha256 efd098c4...)
--------------------------------------------------------------------------------

rep's session draws through this module from M3 (PLAN.md D46), so these
matter to rep as well as to the person's other tools.

F18 bug  terminal_output.py, _layout_max_width (default 80)
  What: until set_layout() is called, content width is 80 whatever the
  terminal's width, so separators and cards wider than a narrow terminal
  wrap into broken borders. The clamp to the terminal happens only inside
  set_layout.
  Evidence: with the terminal width at 60, format_separator() and
  format_card() were 80 columns wide; after set_layout(), 60.
  Fix: clamp in _get_max_width (min of the setting and the terminal width
  minus 4), so the default is safe without a call. rep calls set_layout.
  Fixed (thread 3, pyutils commit): the same clamp applies to the default;
  unchanged when set_layout() was called or there is no terminal.

F19 inconsistency  terminal_output.py, STDERR_IS_TERMINAL
  What: computed once at import and not refreshed by set_color(None),
  while styles follow set_color; clear_screen() decides by the stale
  value. A caller that redirects stderr after import (tests, embedding)
  gets escape codes in a non-terminal stream.
  Fix: let clear_screen() call sys.stderr.isatty() when it runs, or have
  set_color(None) refresh it.
  Fixed (thread 3, pyutils commit): set_color(None) refreshes it; the
  attribute stays, so tests that set it keep working.

F20 suggestion  terminal_output.py under pyright strict
  What: strict mode reports errors that trace to one line,
  `_ANSI_PATTERN: re.Pattern` (line 167, no type argument), which makes
  every match on it partially unknown, and to VERBOSITY being reassigned
  while its uppercase name marks it a constant (line 160). rep checks only
  its own files and the functions it calls return annotated types, so rep
  is unaffected.
  Fix: `re.Pattern[str]`; rename the mutable setting (verbosity_level).
  Partly fixed (thread 3, pyutils commit): `re.Pattern[str]` and an
  annotated list in wrap_text take strict errors from 13 to 3. Left by
  choice: VERBOSITY and STDERR_IS_TERMINAL are module settings with
  constant-style names that other code may read (renaming them is the
  person's call), and sys._getframe serves the trace level.

--------------------------------------------------------------------------------
## Suggestions for the rework: data flow, boundaries, interfaces
--------------------------------------------------------------------------------

F16 suggestion  move the extensions onto lazy.nvim's data model
  The extension loader's spec maps onto lazy.nvim fields one to one, so
  the loader can be archived instead of maintained:
    keymaps   -> keys      (also lazy-loads the plugin on first use)
    commands  -> cmd
    autocmds  -> config (or init when they must exist before loading),
                 or event to load the plugin on that event
    setup     -> config / opts
    the guards (telescope present, nvim version) -> dependencies and
                 lazy's own checks
  Each extension becomes a directory on the runtime path,
  lua/<name>/init.lua returning its functions and setup(), with a spec in
  plugins.lua: { dir = "~/personal_repos/.../kbd/nvim", keys = {...},
  cmd = {...}, dependencies = { "nvim-telescope/telescope.nvim" } }.
  rep's plugin is built this way from M3 (PLAN.md D43), so it can serve
  as the first example.
  Boundary: the functions change with the tool they drive (kbd, rep), so
  they live in that tool's repository; the keys change with the person's
  taste, so they live in the config.

F17 suggestion  one home for facts that several tools read
  a. The bib path is configured three times: kbd.lua (KBD_LOCAL_DIR or
     KBD_MOUNT_POINT), telescope-bibtex (global_files, F12) and rep
     (bib_path in ~/.config/rep/local.toml). Ranked:
     (8) one environment variable set in the shell profile (for example
         KBD_BIB), read by kbd.lua and the bibtex spec; rep's local.toml
         names the same file once per machine (rep reads local.toml,
         PLAN.md D3, not the environment, by design);
     (6) kbd.lua as the only source, others asking it (couples nvim
         plugins to kbd.lua's load order);
     (4) keep three copies (they already disagree, F12).
  b. Key prefixes are spread over init.lua, plugins.lua and each
     extension (k kbd, l lw, t tsk, s telescope, r runner, q and e
     diagnostics). One table of prefixes in the config, also feeding
     which-key's group names, makes collisions such as F5 visible in one
     place. `<leader>p` was free on 2026-10-01 and is suggested for rep.
