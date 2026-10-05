# Tools for any project in this repository (meta/README.md). Source this
# file, or symlink it into the directory your bashrc sources. Defining
# these changes nothing until one is called. `function name {` rather than
# `name() {`: an alias of the same name cannot break the definition.

META_DIRECTORY="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"

# faq: the project's questions and their answers (meta/templates/FAQ.md
# has the format). Which files: every FAQ.md from the current directory up
# to the repository root, nearest first, so inside rep/ both rep's and the
# repository's are in scope. The project, for --add when none exists yet:
# the directory directly under the repository root that holds the current
# directory (the root itself when standing there).
#
#   faq                    the nearest FAQ.md in nvim, one folded line per question
#   faq WORDS...           every entry containing all the words, printed
#   faq --questions        each question with its path:line; open ones marked
#   faq --open             only the questions without an answer
#   faq --add "QUESTION"   append an entry to the nearest FAQ.md, open it there
#   faq --check            duplicates, and answers with no see: or rule:
function faq {
  local repository_root current_directory faq_paths=() mode="${1:-}"
  repository_root="$(git rev-parse --show-toplevel 2>/dev/null)" || repository_root="$PWD"
  current_directory="$PWD"
  while true; do
    [ -f "$current_directory/FAQ.md" ] && faq_paths+=("$current_directory/FAQ.md")
    if [ "$current_directory" = "$repository_root" ] || [ "$current_directory" = "/" ]; then
      break
    fi
    current_directory="$(dirname "$current_directory")"
  done

  if [ "$mode" = "--help" ]; then
    sed -n '/^# faq:/,/^function faq/p' "$META_DIRECTORY/shell/meta.sh" | sed '$d; s/^# \{0,1\}//'
    return 0
  fi

  if [ "$mode" = "--add" ]; then
    local question="${2:-}" target_path project_directory relative_directory entry_line
    if [ -z "$question" ]; then
      echo 'faq: --add needs the question, quoted: faq --add "Why is X?"' >&2
      return 2
    fi
    if [ "${#faq_paths[@]}" -gt 0 ]; then
      target_path="${faq_paths[0]}"
    else
      relative_directory="${PWD#"$repository_root"}"
      relative_directory="${relative_directory#/}"
      project_directory="$repository_root${relative_directory:+/${relative_directory%%/*}}"
      target_path="$project_directory/FAQ.md"
      sed "s/^# FAQ: PROJECT$/# FAQ: $(basename "$project_directory")/" "$META_DIRECTORY/templates/FAQ.md" > "$target_path"
      echo "faq: started $target_path" >&2
    fi
    printf '\n## %s\nasked: %s\nanswer: \nsee: \nrule: \ndate: %s\n' "$question" "$question" "$(date +%F)" >> "$target_path"
    # The answer line of the entry just written: four lines above the end.
    entry_line=$(( $(wc -l < "$target_path") - 3 ))
    nvim --cmd "luafile $META_DIRECTORY/nvim/faq.lua" "+$entry_line" "+normal! zv\$" "$target_path"
    return
  fi

  if [ "${#faq_paths[@]}" -eq 0 ]; then
    echo "faq: no FAQ.md from $PWD up to $repository_root; faq --add \"QUESTION\" starts one" >&2
    return 1
  fi

  if [ -z "$mode" ]; then
    nvim --cmd "luafile $META_DIRECTORY/nvim/faq.lua" "${faq_paths[0]}"
    return
  fi

  local awk_mode search_words=""
  case "$mode" in
    --questions) awk_mode="questions" ;;
    --open) awk_mode="open" ;;
    --check) awk_mode="check" ;;
    --*) echo "faq: unknown option $mode (faq --help)" >&2; return 2 ;;
    *) awk_mode="search"; search_words="$*" ;;
  esac
  # One pass over the files, entry by entry. An entry runs from its "## "
  # heading to the next heading or the end of its file. Its answer is the
  # text after "answer:" and the lines after it up to a key line ("word:")
  # or a blank line.
  awk -v mode="$awk_mode" -v search_words="$search_words" '
    BEGIN {
      word_count = split(tolower(search_words), wanted_words, /[ \t]+/)
      problem_count = 0
      match_count = 0
    }
    function finish_entry(    word_index, is_match, trimmed_body) {
      if (question == "") return
      if (mode == "questions") {
        printf "%s:%d  %s%s\n", entry_path, question_line, question, (answered ? "" : "   (open)")
      } else if (mode == "open") {
        if (!answered) printf "%s:%d  %s\n", entry_path, question_line, question
      } else if (mode == "check") {
        question_key = tolower(question)
        if (question_key in first_seen_at) {
          printf "%s:%d: the same question as %s\n", entry_path, question_line, first_seen_at[question_key]
          problem_count++
        } else {
          first_seen_at[question_key] = entry_path ":" question_line
        }
        if (answered && !has_pointer) {
          printf "%s:%d: answered, but no see: or rule: line says where to check it\n", entry_path, question_line
          problem_count++
        }
      } else {
        is_match = 1
        for (word_index = 1; word_index <= word_count; word_index++) {
          if (wanted_words[word_index] != "" && index(tolower(question body), wanted_words[word_index]) == 0) is_match = 0
        }
        if (is_match) {
          trimmed_body = body
          sub(/[ \t\n]+$/, "", trimmed_body)
          printf "%s%s:%d: ## %s%s\n", (match_count > 0 ? "\n" : ""), entry_path, question_line, question, trimmed_body
          match_count++
        }
      }
      question = ""
    }
    FNR == 1 { finish_entry() }
    /^## / {
      finish_entry()
      question = substr($0, 4)
      question_line = FNR
      entry_path = FILENAME
      body = ""
      answered = 0
      has_pointer = 0
      in_answer = 0
      next
    }
    question != "" {
      body = body "\n" $0
      if ($0 ~ /^answer:/) {
        answer_text = $0
        sub(/^answer:[ \t]*/, "", answer_text)
        if (answer_text != "") answered = 1
        in_answer = 1
      } else if ($0 ~ /^[a-z]+:/) {
        in_answer = 0
        if ($0 ~ /^(see|rule):[ \t]*[^ \t]/) has_pointer = 1
      } else if ($0 !~ /[^ \t]/) {
        in_answer = 0
      } else if (in_answer) {
        answered = 1
      }
    }
    END {
      finish_entry()
      if (mode == "search" && match_count == 0) { print "faq: no entry has all of: " search_words > "/dev/stderr"; exit 1 }
      if (mode == "check") { if (problem_count > 0) exit 1; print "faq: no problems" }
    }
  ' "${faq_paths[@]}"
}
