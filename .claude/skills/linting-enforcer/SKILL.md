---
name: linting-enforcer
description: Run linters and formatters after code changes, auto-fix issues, report unfixable errors. Use when user mentions lint, format, or automatically after Edit/Write operations on code files.
---

# Linting Enforcer Skill

---

## Configuration (CUSTOMIZE FOR YOUR PROJECT)

Configure linters based on your stack:

```yaml
# Example configuration
linting:
  python:
    linter: "ruff"                        # or "flake8", "pylint"
    formatter: "ruff format"              # or "black", "autopep8"
    check_command: "ruff check {path}"
    fix_command: "ruff check {path} --fix && ruff format {path}"
  javascript:
    linter: "eslint"                      # or "biome"
    formatter: "prettier"                 # or "eslint --fix"
    check_command: "eslint {path}"
    fix_command: "eslint {path} --fix"
  go:
    linter: "golangci-lint"
    formatter: "gofmt"
    check_command: "golangci-lint run {path}"
    fix_command: "gofmt -w {path}"
  rust:
    linter: "clippy"
    formatter: "rustfmt"
    check_command: "cargo clippy"
    fix_command: "cargo fmt"
```

---

## Process

### 1. Scope Detection
Determine what to lint:
- **Explicit scope**: User says "lint backend" -> lint backend/
- **Explicit scope**: User says "lint frontend" -> lint frontend/
- **Implicit scope**: Detect from file extension
  - `.py` files -> Python linter
  - `.ts`, `.tsx`, `.js`, `.jsx` files -> JavaScript linter
  - `.go` files -> Go linter
  - `.rs` files -> Rust linter
- **Full project**: No scope specified -> lint all supported languages

### 2. Linter Detection
Auto-detect installed linters:

```bash
# Python
which ruff && echo "ruff"
which black && echo "black"
which flake8 && echo "flake8"

# JavaScript
which eslint && echo "eslint"
which biome && echo "biome"

# Go
which golangci-lint && echo "golangci-lint"

# Rust
which rustfmt && echo "rustfmt"
```

Use the bundled detection script:
```bash
uv run .claude/skills/linting-enforcer/scripts/detect_linters.py
```

### 3. Linter Execution

**Python (Ruff example)**:
```bash
# Check + auto-fix
ruff check src/ --fix
ruff format src/
```

**Python (Black + flake8 example)**:
```bash
flake8 src/
black src/
```

**JavaScript (ESLint example)**:
```bash
eslint src/ --fix
prettier --write src/
```

**Go (golangci-lint example)**:
```bash
golangci-lint run ./...
gofmt -w .
```

**Rust (clippy + rustfmt example)**:
```bash
cargo clippy --fix
cargo fmt
```

### 4. Result Interpretation

**All clean**:
```
No linting issues
  Python (Ruff): 0 errors, 0 warnings
  JavaScript (ESLint): 0 errors, 0 warnings
```

**Auto-fixed**:
```
Auto-fixed 5 issues
  Python (Ruff): Fixed 3 issues (unused imports, line length)
  JavaScript (ESLint): Fixed 2 issues (missing semicolons, trailing comma)
```

**Unfixable errors**:
```
2 unfixable errors
  src/foo.py:42:10: F821 Undefined name 'unknown_variable'
  src/components/Bar.tsx:15:5: @typescript-eslint/no-explicit-any
```

### 5. Error Reporting
For unfixable errors:
- Show file, line, column
- Show error code and description
- Suggest fix if clear
- Offer to apply fix if user confirms

### 6. Post-Fix Verification
After fixes applied:
- Re-run linter to verify clean
- Run tests to ensure no breakage
- Report final status

---

## Invocation

```
/linting-enforcer               # Lint all code
/linting-enforcer backend       # Lint backend only
/linting-enforcer frontend      # Lint frontend only
/linting-enforcer src/foo.py    # Lint specific file
```

Or automatically via hooks after Edit/Write operations.

---

## Output Format

**Success (all clean)**:
```
Linting complete: No issues found
  Backend: Clean
  Frontend: Clean
```

**Success (auto-fixed)**:
```
Linting complete: 5 issues auto-fixed
  Backend:
    Fixed: Removed 2 unused imports
    Fixed: Wrapped 1 long line
  Frontend:
    Fixed: Added 2 missing semicolons
```

**Failure (unfixable errors)**:
```
Linting failed: 2 unfixable errors

Backend:
  src/foo.py:42:10: F821 Undefined name 'unknown_var'
    -> Did you mean 'known_var'?

Frontend:
  src/components/Bar.tsx:15:5: @typescript-eslint/no-explicit-any
    -> Replace 'any' with specific type

Fix these errors and re-run linting.
```

---

## Stack Examples

### Python + Ruff
```toml
# pyproject.toml
[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "N", "W"]
ignore = ["E501"]  # Line too long (handled by formatter)

[tool.ruff.lint.isort]
known-first-party = ["myproject"]
```

Commands:
```bash
ruff check src/ --fix    # Check + auto-fix
ruff format src/         # Format code
ruff check src/          # Check only (no fix)
```

### JavaScript + ESLint
```json
// .eslintrc.json
{
  "extends": [
    "eslint:recommended",
    "plugin:@typescript-eslint/recommended"
  ],
  "rules": {
    "@typescript-eslint/no-explicit-any": "error",
    "@typescript-eslint/no-unused-vars": "error"
  }
}
```

Commands:
```bash
eslint src/             # Check only
eslint src/ --fix       # Check + auto-fix
prettier --write src/   # Format
```

### Go + golangci-lint
```yaml
# .golangci.yml
linters:
  enable:
    - errcheck
    - govet
    - staticcheck
    - unused
```

Commands:
```bash
golangci-lint run ./...     # Check
gofmt -w .                  # Format
go vet ./...                # Additional checks
```

### Rust + clippy
```toml
# Cargo.toml or clippy.toml
[lints.clippy]
unwrap_used = "deny"
expect_used = "warn"
```

Commands:
```bash
cargo clippy            # Check
cargo clippy --fix      # Auto-fix
cargo fmt               # Format
```

---

## Integration with Hooks

This skill is triggered automatically by post-tool-use hooks:

**Hook: `lint_python.sh`**
- Triggers: After Edit/Write on `.py` files
- Action: Run Python linter + formatter
- Behavior: BLOCKING on unfixable errors

**Hook: `lint_javascript.sh`**
- Triggers: After Edit/Write on `.ts`, `.tsx`, `.js`, `.jsx` files
- Action: Run JavaScript linter + formatter
- Behavior: BLOCKING on unfixable errors

---

## Common Issues and Fixes

### Unused Imports
```python
# Before
import sys
import json  # Unused

# After (auto-fixed)
import sys
```

### Import Sorting
```python
# Before
from myproject.models import User
import sys
from fastapi import APIRouter

# After (auto-fixed)
import sys

from fastapi import APIRouter

from myproject.models import User
```

### Missing Types
```typescript
// Before
function process(data: any) { ... }

// After (fix required)
interface Data { ... }
function process(data: Data) { ... }
```

---

## Anti-Patterns to Avoid

**Disabling linter errors without fixing**:
```python
# BAD
# noqa: F821
undefined_variable  # Error hidden, not fixed

# GOOD
# Fix the actual error
```

**Committing without linting**:
```bash
# BAD
git add . && git commit -m "Quick fix"  # No linting

# GOOD
# Run linting first, then commit
```

**Using global disable**:
```typescript
// BAD
/* eslint-disable */  // Disables all checks

// GOOD
// Fix the issues or disable specific rule with justification
/* eslint-disable-next-line @typescript-eslint/no-explicit-any -- Legacy API */
```

---

## CRITICAL: Git Operations Policy

**NEVER automatically commit, push, or perform any git operations.**

This skill ONLY runs linters and auto-fixes code style issues. Git operations are ONLY performed when:
- User explicitly requests "commit these changes"
- User explicitly requests "push to remote"
- User explicitly requests "create PR"

Do NOT:
- Auto-commit after linting passes
- Auto-push after auto-fixes applied
- Auto-create PRs
- Run any CI/CD pipelines automatically

If the user wants git operations, they will ask explicitly.

---

## Notes

- Linting is mandatory before commits (enforced by hooks)
- Auto-fix whenever possible
- Unfixable errors must be resolved manually
- Run linting after every code change
- Linter config should match project conventions
