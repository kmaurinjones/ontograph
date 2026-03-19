#!/bin/bash
# Test hook execution with sample inputs
# Outputs JSON for Claude to parse

HOOKS_DIR="${1:-.claude/hooks}"

# Initialize results array
results=()

# Test each hook script
for hook_script in "$HOOKS_DIR"/*.sh; do
    if [ -f "$hook_script" ]; then
        hook_name=$(basename "$hook_script")

        # Determine appropriate test inputs based on hook name
        if [[ "$hook_name" == *"python"* ]]; then
            test_file="backend/app/test.py"
        elif [[ "$hook_name" == *"typescript"* ]] || [[ "$hook_name" == *"tsx"* ]]; then
            test_file="frontend/src/Component.tsx"
        else
            test_file="test_file.txt"
        fi

        # Run the hook script
        output=$("$hook_script" "$test_file" "Edit" 2>&1)
        exit_code=$?

        # Build result object
        result="{\"hook\":\"$hook_name\",\"exit_code\":$exit_code,\"test_file\":\"$test_file\""

        if [ $exit_code -eq 0 ]; then
            result="$result,\"status\":\"pass\""
        elif [ $exit_code -eq 2 ]; then
            result="$result,\"status\":\"blocked\""
        else
            result="$result,\"status\":\"error\""
        fi

        # Add output if non-empty
        if [ -n "$output" ]; then
            # Escape quotes in output
            escaped_output=$(echo "$output" | sed 's/"/\\"/g' | tr '\n' ' ')
            result="$result,\"output\":\"$escaped_output\""
        fi

        result="$result}"
        results+=("$result")
    fi
done

# Build JSON output
echo "{"
echo "  \"hooks_dir\": \"$HOOKS_DIR\","
echo "  \"total_hooks\": ${#results[@]},"
echo "  \"results\": ["

# Print results with proper comma separation
for i in "${!results[@]}"; do
    echo "    ${results[$i]}"
    if [ $i -lt $((${#results[@]} - 1)) ]; then
        echo "    ,"
    fi
done

echo "  ]"
echo "}"
