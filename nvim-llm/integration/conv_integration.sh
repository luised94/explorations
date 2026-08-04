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

readonly CONV_SCRIPT_PATH="$HOME/personal_repos/explorations/nvim-llm/conv.sh"

if [[ -x "$CONV_SCRIPT_PATH" ]]; then
  alias conv="$CONV_SCRIPT_PATH"
else
  echo "conv-aliases: $CONV_SCRIPT_PATH not found or not executable" >&2
fi
