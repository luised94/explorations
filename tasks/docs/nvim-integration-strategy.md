# nvim integration strategy

How tsk is driven from nvim, why the module is shaped the way it is, and
the alternative strategies worth weighing when the nvim setup itself is
the subject rather than tsk. This is a design record, not a how-to; the
how-to lives in the README "Using tsk from nvim" section.

## The core constraint

`tsk` is a bash function (integrations/tsk.sh), sourced from interactive
shell config. nvim `:!` runs a non-interactive shell, which does not
source that config, so `:!tsk` fails with exit 127. Every strategy below
is a way around that one fact. The cleanest workaround exists because the
tool is argv in / files + stdout out: anything that can spawn
`uv run --no-project tasks.py <args>` gets full tsk behavior without the
shell function. The integration does not wrap tsk; it re-enters it.

## Where the integration files live

Decision: both entry points sit under `tasks/integrations/`, flat --
`tsk.sh` (shell) and `tsk.lua` (nvim) side by side. Alternatives weighed:

- Repo root (both files in tasks/). Simplest, but clutters root and
  frames integration glue as core artifacts.
- Per-technology split (integrations/shell/, integrations/nvim/).
  Correct at scale; over-built for two files, and it separates two files
  that share one purpose.
- Role directory, flat (chosen: integrations/{tsk.sh,tsk.lua}). The name
  says what the files ARE -- ways in from other environments -- not what
  technology each uses. A future tsk.fish, tsk.el, or systemd unit lands
  here with no new decision. Promotes to per-tech subdirs cleanly if
  integrations ever multiply.
- integrations/nvim/tsk.lua (role + per-tech). Adopt only when the count
  justifies it.

## Why tsk.lua is built the way it is

- vim.system with an argv list, not `:!` or io.popen: no shell means no
  quoting hazards and no dependency on interactive config. A summary with
  spaces is one list element.
- Self-contained: MODE_NORMAL and LEADER_T are defined locally, so the
  module drops into any loader without assuming ambient globals. (The
  house loader does expose some; not depending on them keeps the file
  portable and greppable in isolation.)
- Named specs -> positional tuples: the loader consumes keymaps as bare
  4-tuples {mode, lhs, rhs, opts}. The module keeps readable named specs
  (key/fn/desc) and builds the tuples in a loop, the same bridge lw.lua
  uses. This is the seam to watch (see below).
- Function rhs, not string: keeps the maps working even if the :Tsk
  command is not registered, and matches the other modules' style.
- --edit is deliberately unsupported from :Tsk: vim.system has no
  controlling TTY, so an interactive $EDITOR cannot run. Editor-capture
  is documented as a :terminal-split task instead.

## The positional-tuple seam (the thing to make more explicit)

The loader reads `keymap.set(km[1], km[2], km[3], km[4])` -- purely
positional. A producer that used named fields (mode=, lhs=, ...) would
pass four nils silently. Today every module bridges this internally, so
the fragility is contained but undeclared: nothing at the loader or the
producer states the tuple shape, and a wrong order fails quietly. This is
the same class of hidden-contract smell as functions reading module
globals -- you cannot tell the shape from the call site.

## Veteran alternative strategies (for nvim-setup threads)

These change the loader or the module contract; they are out of scope for
tsk commits and belong in a deliberate pass on the extensions system.

1. Loader accepts named keymap fields. Have the loader read
   `km.mode or km[1]`, `km.lhs or km[2]`, etc., so a named-field entry
   works and a malformed one surfaces a real error. Trade-off: more
   forgiving and self-documenting vs. a looser, less uniform contract.
   Migrate modules incrementally; both forms coexist during transition.

2. Loader validates the returned spec shape. Before wiring, assert
   keymaps is a list of 4-element entries with a string/function rhs;
   notify with the offending module and entry on mismatch. Turns silent
   nil-argument failures into named errors at source time. Cheap; high
   value once modules multiply.

3. Keymap-only modules, no user commands. lw registers zero commands;
   tsk.lua adds :Tsk/:TskRead. Decide house policy: commands give
   discoverability (:Tsk<Tab>) and args; maps give speed. A module could
   expose only maps and keep command surface out of the global namespace.

4. Lazy loading. The loader eagerly evaluates every module at startup.
   For heavier integrations, defer: register a stub command/map that,
   on first use, loads the real module. Not worth it for tsk (the module
   is tiny and does no work until invoked), but the pattern matters as
   the extension set grows.

5. A shared helper module. run_tsk/report-style wrappers are generic
   (spawn a script, surface stdout/stderr by exit code). If several
   tool integrations appear, factor a common integrations/_util.lua
   rather than copy the wrapper. Extraction rule applies: do it at the
   second call site, not the first.

6. BASH_ENV escape hatch (documented, not recommended as default).
   Setting `let $BASH_ENV = expand('~/.config/mc_extensions/tsk.sh')`
   in nvim config makes non-interactive bash source that file, so bare
   `:!tsk` works. It fixes the 127 but points nvim at shell internals
   and reintroduces the coupling the module avoids. Keep as a fallback
   note, prefer the module.
