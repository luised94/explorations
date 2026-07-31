#!/usr/bin/env bash
# conv.sh -- conversation block manager
# Appends, branches, queries, and renders conversation blocks in flat .conv files.
# Part of the nvim-llm conversation buffer tool.
# ASCII only. No Unicode characters in this file.
set -euo pipefail

# -- Configuration -----------------------------------------------------------
readonly CONVERSATION_DIRECTORY="${CONVERSATION_DIRECTORY:-$HOME/conversations}"
readonly OPEN_ROUTER_API_KEY="https://openrouter.ai/api/v1/chat/completions"
readonly OPEN_ROUTER_MODEL="inclusionai/ling-3.0-flash:free"
readonly BLOCK_IDENTIFIER_WIDTH=3          # zero-padding: b001, b002, ...
readonly BLOCK_HEADER_DELIMITER="%%%"
readonly API_CALL_LOG_FILE="$CONVERSATION_DIRECTORY/api-calls.log"

# -- Help --------------------------------------------------------------------
print_help() {
  cat << 'HELP'
conv.sh -- conversation block manager

USAGE
  ./conv.sh <command> [arguments]

COMMANDS
  new <session-name>
      Create a new .conv session file in $CONVERSATION_DIRECTORY.

  say <text>
      Append a user block to the active (most recent) session.
      Parent is the last block in the file (linear append).

  ask <text>
      Append a user block, call the LLM, append the response as an asst block.
      The LLM receives ONLY <text>, no prior context. (v0.1 limitation.)

  branch <parent-block-id> <text>
      Append a user block whose parent is <parent-block-id>, not the last block.
      Creates a branch in the conversation tree.

  tree
      Print the block headers of the active session as a flat table.
      (Full tree rendering is in nvim via :ConvTree.)

  help
      Print this message.

ENVIRONMENT
  CONVERSATION_DIRECTORY   Where .conv files live. Default: ~/conversations
  OPENROUTER_API_KEY       Required for 'ask'. Must be exported in current shell.

FILES
  $CONVERSATION_DIRECTORY/*.conv        Session files (flat text, git-tracked)
  $CONVERSATION_DIRECTORY/api-calls.log Timestamped log of LLM API calls

FORMAT
  Each block:
    --- <block-id> | <parent-id> | <speaker> | <HH:MM>
    <body text, one or more lines>

  Block IDs: b001, b002, ... (sequential, zero-padded to 3 digits)
  Parent: 'root' for the first block, otherwise a block ID.
  Speaker: 'user' or 'asst'.

EXAMPLES
  ./conv.sh new constraint-engineering
  ./conv.sh say "First thought: constraint systems are isomorphic."
  ./conv.sh branch b001 "Alternate thread: temporal constraints?"
  ./conv.sh ask "Define constraint system in two sentences."
  ./conv.sh tree
HELP
}

# -- Pure transformations ----------------------------------------------------
# These functions compute values. They do not write files or call APIs.

find_active_conversation_file() {
  ls -t "$CONVERSATION_DIRECTORY"/*.conv 2>/dev/null | head -1
}

compute_next_block_identifier() {
  local conversation_file="$1"
  local last_numeric_suffix
  last_numeric_suffix=$(
    grep -oP "(?<=^$BLOCK_HEADER_DELIMITER )b\d+" "$conversation_file" 2>/dev/null \
    | tail -1 \
    | grep -oP '\d+' \
    || echo 0
  )
  printf "b%0${BLOCK_IDENTIFIER_WIDTH}d" $(( last_numeric_suffix + 1 ))
}

find_last_block_identifier() {
  local conversation_file="$1"
  grep -oP "(?<=^$BLOCK_HEADER_DELIMITER )b\d+" "$conversation_file" 2>/dev/null \
    | tail -1 \
    || echo "root"
}

format_block_header() {
  local block_identifier="$1"
  local parent_block_identifier="$2"
  local speaker="$3"
  local timestamp="$4"
  printf '%s %s | %s | %s | %s' \
    "$BLOCK_HEADER_DELIMITER" \
    "$block_identifier" \
    "$parent_block_identifier" \
    "$speaker" \
    "$timestamp"
}

# -- Side effects (isolated) -------------------------------------------------
# These are the ONLY functions that write to disk or call external services.

write_block_to_file() {
  local conversation_file="$1"
  local block_identifier="$2"
  local parent_block_identifier="$3"
  local speaker="$4"
  local timestamp
  timestamp=$(date +%H:%M)
  printf '\n%s\n' "$(format_block_header \
    "$block_identifier" "$parent_block_identifier" "$speaker" "$timestamp")" \
    >> "$conversation_file"
  cat >> "$conversation_file"   # body from stdin
}

call_openrouter_api() {
  local prompt_text="$1"
  local request_payload
  request_payload=$(jq -n \
    --arg model "$OPEN_ROUTER_MODEL" \
    --arg prompt "$prompt_text" \
    '{model: $model, messages: [{role: "user", content: $prompt}], stream: false}')

  # Log the call (observational side effect, not structural)
  printf '%s  %s  %s bytes\n' \
    "$(date +%Y-%m-%dT%H:%M:%S)" \
    "$OPEN_ROUTER_MODEL" \
    "$(echo "$prompt_text" | wc -c)" \
    >> "$API_CALL_LOG_FILE"

  curl -s "$OPEN_ROUTER_API_KEY" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \
    -d "$request_payload" \
    | jq -r '.choices[0].message.content // "ERROR: " + (.error.message // "unknown")'
}

# -- Imperative core: argument processing and dispatch -----------------------

main() {
  local command="${1:-help}"
  shift 2>/dev/null || true

  case "$command" in
    new)
      local session_name="${1:?usage: ./conv.sh new <session-name>}"
      mkdir -p "$CONVERSATION_DIRECTORY"
      local conversation_file="$CONVERSATION_DIRECTORY/$(date +%Y-%m-%d)-${session_name}.conv"
      echo "# session: $(date +%Y-%m-%d) ${session_name}" > "$conversation_file"
      echo "created $conversation_file"
      ;;

    say)
      local user_text="${1:?usage: ./conv.sh say <text>}"
      local conversation_file
      conversation_file=$(find_active_conversation_file)
      [[ -z "$conversation_file" ]] && { echo "no active session. run: ./conv.sh new <name>"; exit 1; }
      local block_identifier
      block_identifier=$(compute_next_block_identifier "$conversation_file")
      local parent_block_identifier
      parent_block_identifier=$(find_last_block_identifier "$conversation_file")
      echo "$user_text" | write_block_to_file \
        "$conversation_file" "$block_identifier" "$parent_block_identifier" "user"
      echo "appended $block_identifier (parent: $parent_block_identifier)"
      ;;

    ask)
      local user_text="${1:?usage: ./conv.sh ask <text>}"
      local conversation_file
      conversation_file=$(find_active_conversation_file)
      [[ -z "$conversation_file" ]] && { echo "no active session"; exit 1; }
      local user_block_identifier
      user_block_identifier=$(compute_next_block_identifier "$conversation_file")
      local parent_block_identifier
      parent_block_identifier=$(find_last_block_identifier "$conversation_file")
      echo "$user_text" | write_block_to_file \
        "$conversation_file" "$user_block_identifier" "$parent_block_identifier" "user"
      echo "user block: $user_block_identifier -- calling LLM..."
      local assistant_response_text
      assistant_response_text=$(call_openrouter_api "$user_text")
      local assistant_block_identifier
      assistant_block_identifier=$(compute_next_block_identifier "$conversation_file")
      echo "$assistant_response_text" | write_block_to_file \
        "$conversation_file" "$assistant_block_identifier" "$user_block_identifier" "asst"
      echo "asst block: $assistant_block_identifier (parent: $user_block_identifier)"
      ;;

    branch)
      local parent_block_identifier="${1:?usage: ./conv.sh branch <parent-id> <text>}"
      local user_text="${2:?usage: ./conv.sh branch <parent-id> <text>}"
      local conversation_file
      conversation_file=$(find_active_conversation_file)
      [[ -z "$conversation_file" ]] && { echo "no active session"; exit 1; }
      local block_identifier
      block_identifier=$(compute_next_block_identifier "$conversation_file")
      echo "$user_text" | write_block_to_file \
        "$conversation_file" "$block_identifier" "$parent_block_identifier" "user"
      echo "appended $block_identifier (branched from $parent_block_identifier)"
      ;;

    tree)
      local conversation_file
      conversation_file=$(find_active_conversation_file)
      [[ -z "$conversation_file" ]] && { echo "no active session"; exit 1; }
      grep -P "^$BLOCK_HEADER_DELIMITER b" "$conversation_file" \
        | sed "s/^$BLOCK_HEADER_DELIMITER //" \
        | column -t -s'|'
      ;;

    help|--help|-h)
      print_help
      ;;

    *)
      echo "unknown command: $command" >&2
      echo "run './conv.sh help' for usage" >&2
      exit 1
      ;;
  esac
}

main "$@"
