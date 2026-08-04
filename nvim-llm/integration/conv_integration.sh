#!/usr/bin/env bash
# integrations/conv-aliases.bash
# Aliases for the nvim-llm conversation buffer tool.
# Symlink this file into your bashrc loading directory.
#
# Setup:
#   ln -sf ~/personal_repos/explorations/nvim-llm/integrations/conv-aliases.bash \
#          ~/.bashrc.d/conv-aliases.bash
#
# After setup, the following commands are available in any shell:
#   conv new <name>    create a new conversation session
#   conv help          print usage
#
# Note: daily conversation work happens inside nvim (<leader>cs, <leader>ca).
# The conv command is for session creation and scripting only.

_conv_file="${BASH_SOURCE[0]}"
_conv_dir="$(cd -- "$(dirname -- "$_conv_file")" && pwd -P)"
_conv_script="${CONV_SCRIPT_PATH:-$(cd -- "$_conv_dir/.." && pwd -P)/conv.sh}"

if [[ -x "$_conv_script" ]]; then
  alias conv="$_conv_script"
else
  printf 'conv-aliases: %s not found or not executable\n' \
    "$_conv_script" >&2
fi

unset _conv_file _conv_dir _conv_script
