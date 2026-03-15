#!/usr/bin/env bash
# Auto-discover relevant files for documentation scope

set -euo pipefail

SCOPE="${1:-}"

if [ -z "$SCOPE" ]; then
    echo "Error: No scope provided"
    echo "Usage: discover_files.sh <path|pattern>"
    exit 1
fi

# Output array for discovered files
declare -a FILES=()

# Function to check if file is a source file (not test)
is_source_file() {
    local file="$1"

    # Skip test files unless explicitly in scope
    if [[ "$file" == *"test"* ]] || [[ "$file" == *"spec"* ]]; then
        if [[ "$SCOPE" != *"test"* ]]; then
            return 1
        fi
    fi

    # Only include source code files
    case "$file" in
        *.py|*.ts|*.tsx|*.js|*.jsx)
            return 0
            ;;
        *)
            return 1
            ;;
    esac
}

# If scope is a file, just return it
if [ -f "$SCOPE" ]; then
    if is_source_file "$SCOPE"; then
        echo "$PWD/$SCOPE"
    fi
    exit 0
fi

# If scope is a directory, find all source files
if [ -d "$SCOPE" ]; then
    while IFS= read -r -d '' file; do
        if is_source_file "$file"; then
            FILES+=("$file")
        fi
    done < <(find "$SCOPE" -type f -print0)

    # Print discovered files
    for file in "${FILES[@]}"; do
        echo "$file"
    done

    exit 0
fi

# If scope is a pattern or concept, search for matching files
# Use ripgrep to find files containing the scope term
if command -v rg &> /dev/null; then
    while IFS= read -r file; do
        if is_source_file "$file"; then
            FILES+=("$file")
        fi
    done < <(rg -l "$SCOPE" --type-add 'source:*.{py,ts,tsx,js,jsx}' -tsource 2>/dev/null || true)

    # Deduplicate
    FILES=($(printf "%s\n" "${FILES[@]}" | sort -u))

    for file in "${FILES[@]}"; do
        echo "$PWD/$file"
    done

    exit 0
fi

# Fallback: no files found
echo "No files found matching scope: $SCOPE" >&2
exit 1
