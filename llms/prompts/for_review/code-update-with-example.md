Update my count_string function to follow the updated organization strategy:

count_string() {

ÿ ÿ# Usage function

ÿ ÿusage() {

ÿ ÿ ÿ ÿcat << EOF

Usage: count_string [OPTIONS] <search_string> [directory]

Search for string occurrences in files with detailed reporting.

Options:

ÿ ÿ-h, --help ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ Show this help message

ÿ ÿ-e, --exclude-dir DIR ÿ ÿ ÿAdditional directory to exclude (can be used multiple times)

ÿ ÿ-f, --exclude-file FILE ÿ ÿAdditional file pattern to exclude (can be used multiple times)

ÿ ÿ-v, --verbose ÿ ÿ ÿ ÿ ÿ ÿ Enable verbose output

ÿ ÿ-q, --quiet ÿ ÿ ÿ ÿ ÿ ÿ ÿ Suppress all output except final counts

ÿ ÿ--no-default-excludes ÿ ÿ Don't use default exclusion patterns

ÿ ÿ--max-depth N ÿ ÿ ÿ ÿ ÿ ÿ Maximum directory depth to search

Examples:

ÿ ÿcount_string "TODO" ./src

ÿ ÿcount_string -e "tests" -e "docs" "FIXME" .

ÿ ÿcount_string -q "deprecated" ./project

EOF

ÿ ÿ}

ÿ ÿ# Default configuration

ÿ ÿlocal default_exclude_dirs=(".git" "node_modules" "build" "dist" "renv" ".venv")

ÿ ÿlocal default_exclude_files=("\*.md" "\*.txt" "\*init.sh" "\*renv.lock" "\*.log" "\*.tmp" "\*.bak" "\*.swp" "\*.gitignore" "\*.Rprofile")

ÿ ÿlocal additional_exclude_dirs=()

ÿ ÿlocal additional_exclude_files=()

ÿ ÿlocal verbose=0

ÿ ÿlocal quiet=0

ÿ ÿlocal use_default_excludes=1

ÿ ÿlocal max_depth=""

ÿ ÿlocal search_string=""

ÿ ÿlocal search_dir="."

ÿ ÿ# Parse options

ÿ ÿwhile [[ $# -gt 0 ]]; do

ÿ ÿ ÿ ÿcase $1 in

ÿ ÿ ÿ ÿ ÿ ÿ-h|--help)

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿusage

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿreturn 0

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ;;

ÿ ÿ ÿ ÿ ÿ ÿ-e|--exclude-dir)

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿif [[ -z "$2" ]]; then

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿecho "Error: --exclude-dir requires a directory argument" >&2

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿreturn 1

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿfi

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿadditional_exclude_dirs+=("$2")

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿshift 2

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ;;

ÿ ÿ ÿ ÿ ÿ ÿ-f|--exclude-file)

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿif [[ -z "$2" ]]; then

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿecho "Error: --exclude-file requires a file pattern argument" >&2

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿreturn 1

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿfi

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿadditional_exclude_files+=("$2")

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿshift 2

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ;;

ÿ ÿ ÿ ÿ ÿ ÿ-v|--verbose)

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿverbose=1

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿshift

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ;;

ÿ ÿ ÿ ÿ ÿ ÿ-q|--quiet)

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿquiet=1

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿshift

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ;;

ÿ ÿ ÿ ÿ ÿ ÿ--no-default-excludes)

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿuse_default_excludes=0

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿshift

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ;;

ÿ ÿ ÿ ÿ ÿ ÿ--max-depth)

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿif [[ -z "$2" ]] || ! [[ "$2" =~ ^[0-9]+$ ]]; then

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿecho "Error: --max-depth requires a numeric argument" >&2

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿreturn 1

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿfi

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿmax_depth="-maxdepth $2"

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿshift 2

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ;;

ÿ ÿ ÿ ÿ ÿ ÿ-\*)

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿecho "Error: Unknown option: $1" >&2

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿusage

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿreturn 1

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ;;

ÿ ÿ ÿ ÿ ÿ ÿ\*)

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿif [[ -z "$search_string" ]]; then

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿsearch_string="$1"

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿelse

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿsearch_dir="$1"

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿfi

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿshift

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿ;;

ÿ ÿ ÿ ÿesac

ÿ ÿdone

ÿ ÿ# Validate required arguments

ÿ ÿif [[ -z "$search_string" ]]; then

ÿ ÿ ÿ ÿecho "Error: Search string is required" >&2

ÿ ÿ ÿ ÿusage

ÿ ÿ ÿ ÿreturn 1

ÿ ÿfi

ÿ ÿ# Validate directory

ÿ ÿif [[ ! -d "$search_dir" ]]; then

ÿ ÿ ÿ ÿecho "Error: Directory '$search_dir' does not exist" >&2

ÿ ÿ ÿ ÿreturn 1

ÿ ÿfi

ÿ ÿ# Build exclude arguments

ÿ ÿlocal exclude_args=()

ÿ ÿif ((use_default_excludes)); then

ÿ ÿ ÿ ÿfor dir in "${default_exclude_dirs[@]}"; do

ÿ ÿ ÿ ÿ ÿ ÿexclude_args+=(-not -path "\*/${dir}/\*")

ÿ ÿ ÿ ÿdone

ÿ ÿ ÿ ÿfor file in "${default_exclude_files[@]}"; do

ÿ ÿ ÿ ÿ ÿ ÿexclude_args+=(-not -name "${file}")

ÿ ÿ ÿ ÿdone

ÿ ÿfi

ÿ ÿfor dir in "${additional_exclude_dirs[@]}"; do

ÿ ÿ ÿ ÿexclude_args+=(-not -path "\*/${dir}/\*")

ÿ ÿdone

ÿ ÿfor file in "${additional_exclude_files[@]}"; do

ÿ ÿ ÿ ÿexclude_args+=(-not -name "${file}")

ÿ ÿdone

ÿ ÿ# Temporary files for results

ÿ ÿlocal tmp_dir=$(mktemp -d)

ÿ ÿlocal files_with="$tmp_dir/with.txt"

ÿ ÿlocal files_without="$tmp_dir/without.txt"

ÿ ÿtrap 'rm -rf "$tmp_dir"' EXIT

ÿ ÿ# Execute find command with proper error handling

ÿ ÿif ((verbose)); then

ÿ ÿ ÿ ÿecho "Executing find command..."

ÿ ÿ ÿ ÿecho "find $search_dir $max_depth -type f ${exclude_args[@]}"

ÿ ÿfi

ÿ ÿ# Find and categorize files

ÿ ÿfind "$search_dir" $max_depth -type f "${exclude_args[@]}" -print0 2>/dev/null | \

ÿ ÿ ÿ ÿwhile IFS= read -r -d $'\0' file; do

ÿ ÿ ÿ ÿ ÿ ÿif grep -q "$search_string" "$file" 2>/dev/null; then

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿecho "$file" >> "$files_with"

ÿ ÿ ÿ ÿ ÿ ÿelse

ÿ ÿ ÿ ÿ ÿ ÿ ÿ ÿecho "$file" >> "$files_without"

ÿ ÿ ÿ ÿ ÿ ÿfi

ÿ ÿ ÿ ÿdone

ÿ ÿ# Count results

ÿ ÿlocal count_with=$(wc -l < "$files_with" || echo 0)

ÿ ÿlocal count_without=$(wc -l < "$files_without" || echo 0)

ÿ ÿlocal total=$((count_with + count_without))

ÿ ÿ# Output results

ÿ ÿif ((! quiet)); then

ÿ ÿ ÿ ÿecho "Searching for: '$search_string' in $search_dir"

ÿ ÿ ÿ ÿecho "----------------------------------------"

ÿ ÿ ÿ ÿecho -e "\nFiles containing the string:"

ÿ ÿ ÿ ÿif [[ -s "$files_with" ]]; then

ÿ ÿ ÿ ÿ ÿ ÿsed 's/^/ ÿ/' "$files_with"

ÿ ÿ ÿ ÿelse

ÿ ÿ ÿ ÿ ÿ ÿecho " ÿNone found"

ÿ ÿ ÿ ÿfi

ÿ ÿ ÿ ÿecho -e "\nFiles missing the string:"

ÿ ÿ ÿ ÿif [[ -s "$files_without" ]]; then

ÿ ÿ ÿ ÿ ÿ ÿsed 's/^/ ÿ/' "$files_without"

ÿ ÿ ÿ ÿelse

ÿ ÿ ÿ ÿ ÿ ÿecho " ÿNone found"

ÿ ÿ ÿ ÿfi

ÿ ÿ ÿ ÿecho -e "\nSummary:"

ÿ ÿ ÿ ÿecho " ÿFiles containing string: $count_with"

ÿ ÿ ÿ ÿecho " ÿFiles missing string: $count_without"

ÿ ÿ ÿ ÿecho " ÿTotal files checked: $total"

ÿ ÿelse

ÿ ÿ ÿ ÿecho "$count_with"

ÿ ÿfi

ÿ ÿreturn 0

}
