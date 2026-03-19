#!/bin/bash
# Search for error patterns in logs and code
# Outputs JSON with locations of potential issues

LOG_DIR="${1:-logs}"
CODE_DIR="${2:-.}"

results=()

# Search log files for errors
if [ -d "$LOG_DIR" ]; then
    while IFS= read -r line; do
        if [ -n "$line" ]; then
            file=$(echo "$line" | cut -d: -f1)
            linenum=$(echo "$line" | cut -d: -f2)
            content=$(echo "$line" | cut -d: -f3-)
            # Escape quotes
            content=$(echo "$content" | sed 's/"/\\"/g')
            results+=("{\"type\":\"log\",\"file\":\"$file\",\"line\":$linenum,\"content\":\"$content\"}")
        fi
    done < <(grep -rn -i "error\|exception\|failed\|traceback" "$LOG_DIR" 2>/dev/null | head -20)
fi

# Search for unhandled exceptions in Python code
while IFS= read -r line; do
    if [ -n "$line" ]; then
        file=$(echo "$line" | cut -d: -f1)
        linenum=$(echo "$line" | cut -d: -f2)
        results+=("{\"type\":\"bare_except\",\"file\":\"$file\",\"line\":$linenum,\"issue\":\"Bare except clause\"}")
    fi
done < <(grep -rn "except:" backend/ 2>/dev/null | grep -v "except:$" | head -10)

# Search for TODO/FIXME comments that might indicate known issues
while IFS= read -r line; do
    if [ -n "$line" ]; then
        file=$(echo "$line" | cut -d: -f1)
        linenum=$(echo "$line" | cut -d: -f2)
        content=$(echo "$line" | cut -d: -f3- | sed 's/"/\\"/g')
        results+=("{\"type\":\"todo\",\"file\":\"$file\",\"line\":$linenum,\"content\":\"$content\"}")
    fi
done < <(grep -rn "TODO\|FIXME\|BUG\|HACK" backend/ frontend/src/ 2>/dev/null | head -20)

# Output JSON
echo "{"
echo "  \"log_dir\": \"$LOG_DIR\","
echo "  \"total_results\": ${#results[@]},"
echo "  \"results\": ["

for i in "${!results[@]}"; do
    echo -n "    ${results[$i]}"
    if [ $i -lt $((${#results[@]} - 1)) ]; then
        echo ","
    else
        echo ""
    fi
done

echo "  ]"
echo "}"
