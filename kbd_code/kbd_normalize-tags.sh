#!/bin/bash
# kbd-normalize-tags - detect and fix tag inconsistencies in kbd
# Usage: kbd-normalize-tags [--fix]
# Without --fix: report only. With --fix: apply canonical forms.
set -u

# -- Configuration --
KBD_DIR="${KBD_LOCAL_DIR:-$HOME/personal_repos/kbd}"

# Acronyms preserved as uppercase (add to this list as needed)
ACRONYM_WHITELIST="ORC MCM CRE ARS APC CDK DDK MCM10 RFC PCNA TRC"

# -- Argument parsing --
fix_mode=false
if [[ "${1:-}" == "--fix" ]]; then
    fix_mode=true
fi

# -- File collection --
content_files=()
while IFS= read -r -d '' found_file; do
    content_files+=("$found_file")
done < <(find "$KBD_DIR" \
    \( -name "source-notes.txt" \
    -o -name "journal.txt" \
    -o -path "*/projects/*.txt" \
    -o -path "*/recall/*.md" \
    -o -path "*/daily_log/*.txt" \) \
    -print0 2>/dev/null)

if [[ ${#content_files[@]} -eq 0 ]]; then
    echo "kbd-normalize-tags[ERROR]: no content files found in $KBD_DIR" >&2
    exit 1
fi

echo "Scanning ${#content_files[@]} file(s) in $KBD_DIR"
echo "---"

# -- Extract all tags --
# Pattern: # preceded by start-of-line or whitespace, followed by word chars
all_tags_raw=$(grep -ohP '(?:^|\s)#\K\w+' "${content_files[@]}" 2>/dev/null | sort)

if [[ -z "$all_tags_raw" ]]; then
    echo "No tags found."
    exit 0
fi

# Unique tags with counts
all_tags_counted=$(echo "$all_tags_raw" | uniq -c | sort -rn)
unique_tags=$(echo "$all_tags_raw" | sort -u)
total_unique=$(echo "$unique_tags" | wc -l)
total_occurrences=$(echo "$all_tags_raw" | wc -l)

echo "Tags: $total_unique unique, $total_occurrences total occurrences"
echo ""

# -- Check: is tag an acronym? --
is_acronym() {
    local tag_to_check="$1"
    local acronym_entry
    for acronym_entry in $ACRONYM_WHITELIST; do
        if [[ "${tag_to_check^^}" == "${acronym_entry^^}" ]]; then
            return 0
        fi
    done
    # Heuristic: all uppercase and 2+ chars
    if [[ "$tag_to_check" =~ ^[A-Z][A-Z0-9]+$ ]]; then
        return 0
    fi
    return 1
}

# -- Detect case variants --
echo "=== Case Variants ==="
declare -A lowercase_groups
while IFS= read -r tag_name; do
    lower_form="${tag_name,,}"
    if [[ -n "${lowercase_groups[$lower_form]:-}" ]]; then
        lowercase_groups[$lower_form]="${lowercase_groups[$lower_form]} $tag_name"
    else
        lowercase_groups[$lower_form]="$tag_name"
    fi
done <<< "$unique_tags"

case_variant_count=0
for lower_form in "${!lowercase_groups[@]}"; do
    group_members="${lowercase_groups[$lower_form]}"
    member_count=$(echo "$group_members" | wc -w)
    if [[ $member_count -gt 1 ]]; then
        if is_acronym "$lower_form"; then
            echo "  [acronym] $group_members -> keep as-is"
        else
            echo "  [variant] $group_members -> canonical: #$lower_form"
            case_variant_count=$((case_variant_count + 1))
        fi
    fi
done

if [[ $case_variant_count -eq 0 ]]; then
    echo "  (none found)"
fi
echo ""

# -- Detect plural/singular pairs --
echo "=== Plural/Singular Pairs ==="
plural_pair_count=0
while IFS= read -r tag_name; do
    # Check if tag ends in 's' and the singular form also exists
    if [[ "$tag_name" =~ s$ ]]; then
        singular_form="${tag_name%s}"
        if echo "$unique_tags" | grep -qx "$singular_form"; then
            echo "  [plural] #$tag_name / #$singular_form -> canonical: #$singular_form"
            plural_pair_count=$((plural_pair_count + 1))
        fi
    fi
done <<< "$unique_tags"

if [[ $plural_pair_count -eq 0 ]]; then
    echo "  (none found)"
fi
echo ""

# -- Summary --
total_issues=$((case_variant_count + plural_pair_count))
echo "=== Summary ==="
echo "Issues found: $total_issues (case: $case_variant_count, plural: $plural_pair_count)"

if [[ $total_issues -eq 0 ]]; then
    echo "All tags are consistent."
    exit 0
fi

# -- Fix mode --
if [[ "$fix_mode" != true ]]; then
    echo ""
    echo "Run with --fix to apply canonical forms."
    exit 0
fi

echo ""
echo "=== Applying Fixes ==="

fix_count=0

# Fix case variants (non-acronym)
for lower_form in "${!lowercase_groups[@]}"; do
    group_members="${lowercase_groups[$lower_form]}"
    member_count=$(echo "$group_members" | wc -w)
    if [[ $member_count -gt 1 ]]; then
        if is_acronym "$lower_form"; then
            continue
        fi
        for variant in $group_members; do
            if [[ "$variant" == "$lower_form" ]]; then
                continue
            fi
            echo "  #$variant -> #$lower_form"
            perl -i -pe "s/(?:(?<=\\s)|(?<=^))#${variant}(?=\\s|\$)/#${lower_form}/g" "${content_files[@]}"
            fix_count=$((fix_count + 1))
        done
    fi
done

# Fix plurals
while IFS= read -r tag_name; do
    if [[ "$tag_name" =~ s$ ]]; then
        singular_form="${tag_name%s}"
        if echo "$unique_tags" | grep -qx "$singular_form"; then
            echo "  #$tag_name -> #$singular_form"
            perl -i -pe "s/(?:(?<=\\s)|(?<=^))#${tag_name}(?=\\s|\$)/#${singular_form}/g" "${content_files[@]}"
            fix_count=$((fix_count + 1))
        fi
    fi
done <<< "$unique_tags"

echo ""
echo "Applied $fix_count fix(es). Review with: cd $KBD_DIR && git diff"
