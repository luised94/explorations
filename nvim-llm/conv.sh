#!/usr/bin/env bash
set -euo pipefail

# conv - append blocks to a conversation file, optionally query an LLM
# usage:
#   conv new <session-name>          create a new session file
#   conv say "text"                  append a user block
#   conv ask "text"                  append user block + call LLM + append response
#   conv branch <parent-id> "text"   append a block branching from parent
#   conv tree                        print the block tree (indent by depth)

CONV_DIR="${CONV_DIR:-$HOME/conversations}"
API_URL="${LLM_API_URL:-http://localhost:11434/v1/chat/completions}"  # ollama default
API_KEY="${LLM_API_KEY:-}"
MODEL="${LLM_MODEL:-qwen3}"

session_file() { echo "$CONV_DIR/$1.conv"; }

next_id() {
  local f="$1"
  local last
  last=$(grep -oP '(?<=^--- )b\d+' "$f" | tail -1 | grep -oP '\d+')
  printf "b%03d" $(( ${last:-0} + 1 ))
}

append_block() {
  local file="$1" id="$2" parent="$3" speaker="$4"
  local ts
  ts=$(date +%H:%M)
  printf '\n--- %s | %s | %s | %s\n' "$id" "$parent" "$speaker" "$ts" >> "$file"
  cat >> "$file"  # stdin is the block body
}

call_llm() {
  local prompt="$1"
  # Minimal OpenAI-compatible call. Adjust for your endpoint.
  local auth_header=""
  [[ -n "$API_KEY" ]] && auth_header="Authorization: Bearer $API_KEY"
  curl -s "$API_URL" \
    -H "Content-Type: application/json" \
    ${auth_header:+-H "$auth_header"} \
    -d "$(jq -n --arg m "$MODEL" --arg p "$prompt" \
      '{model:$m, messages:[{role:"user",content:$p}], stream:false}')" \
    | jq -r '.choices[0].message.content'
}

cmd="${1:-help}"
case "$cmd" in
  new)
    mkdir -p "$CONV_DIR"
    f=$(session_file "$2")
    echo "# session: $(date +%Y-%m-%d) $2" > "$f"
    echo "created $f"
    ;;
  say)
    f=$(ls -t "$CONV_DIR"/*.conv 2>/dev/null | head -1)
    [[ -z "$f" ]] && { echo "no active session"; exit 1; }
    id=$(next_id "$f")
    parent=$(grep -oP '(?<=^--- )b\d+' "$f" | tail -1)
    parent="${parent:-root}"
    echo "$2" | append_block "$f" "$id" "$parent" "user"
    echo "$id"
    ;;
  ask)
    f=$(ls -t "$CONV_DIR"/*.conv 2>/dev/null | head -1)
    [[ -z "$f" ]] && { echo "no active session"; exit 1; }
    # user block
    uid=$(next_id "$f")
    parent=$(grep -oP '(?<=^--- )b\d+' "$f" | tail -1)
    parent="${parent:-root}"
    echo "$2" | append_block "$f" "$uid" "$parent" "user"
    # llm response block
    response=$(call_llm "$2")
    aid=$(next_id "$f")
    echo "$response" | append_block "$f" "$aid" "$uid" "asst"
    echo "$uid -> $aid"
    ;;
  branch)
    f=$(ls -t "$CONV_DIR"/*.conv 2>/dev/null | head -1)
    id=$(next_id "$f")
    echo "$3" | append_block "$f" "$id" "$2" "user"
    echo "$id (branched from $2)"
    ;;
  tree)
    f=$(ls -t "$CONV_DIR"/*.conv 2>/dev/null | head -1)
    # crude tree: grep headers, you navigate in nvim
    grep -P '^--- b' "$f" | sed 's/^--- //'
    ;;
  *)
    echo "usage: conv {new|say|ask|branch|tree}"
    ;;
esac
