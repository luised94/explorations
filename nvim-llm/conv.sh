#!/usr/bin/env bash
set -euo pipefail

CONV_DIR="${CONV_DIR:-$HOME/conversations}"
API_URL="https://openrouter.ai/api/v1/chat/completions"
API_KEY="${OPEN_ROUTER_API_KEY}"
MODEL="inclusionai/ling-3.0-flash:free"

active_file() {
  ls -t "$CONV_DIR"/*.conv 2>/dev/null | head -1
}

next_id() {
  local f="$1"
  local last
  last=$(grep -oP '(?<=^--- )b\d+' "$f" 2>/dev/null | tail -1 | grep -oP '\d+' || echo 0)
  printf "b%03d" $(( last + 1 ))
}

append_block() {
  local file="$1" id="$2" parent="$3" speaker="$4"
  local ts
  ts=$(date +%H:%M)
  printf '\n--- %s | %s | %s | %s\n' "$id" "$parent" "$speaker" "$ts" >> "$file"
  cat >> "$file"
}

call_llm() {
  local prompt="$1"
  curl -s "$API_URL" \
    -H "Content-Type: application/json" \
    -H "Authorization: Bearer $API_KEY" \
    -d "$(jq -n --arg m "$MODEL" --arg p "$prompt" \
      '{model:$m, messages:[{role:"user",content:$p}], stream:false}')" \
    | jq -r '.choices[0].message.content // "ERROR: " + tostring'
}

cmd="${1:-help}"
case "$cmd" in
  new)
    mkdir -p "$CONV_DIR"
    f="$CONV_DIR/$(date +%Y-%m-%d)-${2:-session}.conv"
    echo "# session: $(date +%Y-%m-%d) ${2:-session}" > "$f"
    echo "created $f"
    ;;
  say)
    f=$(active_file)
    [[ -z "$f" ]] && { echo "no active session. run: conv new <name>"; exit 1; }
    id=$(next_id "$f")
    parent=$(grep -oP '(?<=^--- )b\d+' "$f" | tail -1 || echo "root")
    echo "${2}" | append_block "$f" "$id" "$parent" "user"
    echo "appended $id (parent: $parent)"
    ;;
  ask)
    f=$(active_file)
    [[ -z "$f" ]] && { echo "no active session"; exit 1; }
    uid=$(next_id "$f")
    parent=$(grep -oP '(?<=^--- )b\d+' "$f" | tail -1 || echo "root")
    echo "${2}" | append_block "$f" "$uid" "$parent" "user"
    echo "user block: $uid - calling LLM..."
    response=$(call_llm "$2")
    aid=$(next_id "$f")
    echo "$response" | append_block "$f" "$aid" "$uid" "asst"
    echo "asst block: $aid (parent: $uid)"
    ;;
  branch)
    f=$(active_file)
    [[ -z "$f" ]] && { echo "no active session"; exit 1; }
    id=$(next_id "$f")
    echo "${3}" | append_block "$f" "$id" "$2" "user"
    echo "appended $id (branched from $2)"
    ;;
  tree)
    f=$(active_file)
    [[ -z "$f" ]] && { echo "no active session"; exit 1; }
    grep -P '^--- b' "$f" | sed 's/^--- //' | column -t -s'|'
    ;;
  *)
    echo "usage: conv {new|say|ask|branch|tree}"
    ;;
esac
