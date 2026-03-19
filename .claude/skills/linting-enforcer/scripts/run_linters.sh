#!/bin/bash
# Run linters on specified paths and return JSON results

TARGET="${1:-.}"
SCOPE="${2:-all}"  # all, backend, frontend

results=()
total_errors=0
total_fixed=0

# Run Ruff on Python files
run_ruff() {
    local path="$1"

    if [ -f "pyproject.toml" ]; then
        # Run ruff check
        ruff_output=$(uv run ruff check "$path" --output-format=json 2>/dev/null)
        ruff_exit=$?

        if [ $ruff_exit -eq 0 ]; then
            results+=("{\"linter\":\"ruff\",\"status\":\"clean\",\"path\":\"$path\"}")
        else
            error_count=$(echo "$ruff_output" | grep -c '"code"' || echo "0")
            total_errors=$((total_errors + error_count))

            # Try to fix
            uv run ruff check "$path" --fix &>/dev/null
            uv run ruff format "$path" &>/dev/null

            # Re-check
            ruff_recheck=$(uv run ruff check "$path" 2>&1)
            if [ $? -eq 0 ]; then
                total_fixed=$((total_fixed + error_count))
                results+=("{\"linter\":\"ruff\",\"status\":\"fixed\",\"path\":\"$path\",\"fixed_count\":$error_count}")
            else
                remaining=$(echo "$ruff_recheck" | grep -c "error" || echo "0")
                results+=("{\"linter\":\"ruff\",\"status\":\"errors\",\"path\":\"$path\",\"error_count\":$remaining}")
            fi
        fi
    fi
}

# Run ESLint on TypeScript/JavaScript files
run_eslint() {
    local path="$1"

    if [ -d "frontend" ] && [ -f "frontend/package.json" ]; then
        # Run eslint
        cd frontend
        eslint_output=$(npm run lint 2>&1)
        eslint_exit=$?
        cd ..

        if [ $eslint_exit -eq 0 ]; then
            results+=("{\"linter\":\"eslint\",\"status\":\"clean\",\"path\":\"$path\"}")
        else
            error_count=$(echo "$eslint_output" | grep -c "error" || echo "0")
            total_errors=$((total_errors + error_count))

            # Try to fix
            cd frontend
            npm run lint -- --fix &>/dev/null
            eslint_recheck=$(npm run lint 2>&1)
            cd ..

            if [ $? -eq 0 ]; then
                total_fixed=$((total_fixed + error_count))
                results+=("{\"linter\":\"eslint\",\"status\":\"fixed\",\"path\":\"frontend\",\"fixed_count\":$error_count}")
            else
                remaining=$(echo "$eslint_recheck" | grep -c "error" || echo "0")
                results+=("{\"linter\":\"eslint\",\"status\":\"errors\",\"path\":\"frontend\",\"error_count\":$remaining}")
            fi
        fi
    fi
}

# Run based on scope
case "$SCOPE" in
    backend)
        run_ruff "$TARGET"
        ;;
    frontend)
        run_eslint "$TARGET"
        ;;
    all|*)
        run_ruff "backend/"
        run_eslint "frontend/"
        ;;
esac

# Output JSON
echo "{"
echo "  \"target\": \"$TARGET\","
echo "  \"scope\": \"$SCOPE\","
echo "  \"total_errors\": $total_errors,"
echo "  \"total_fixed\": $total_fixed,"
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
