---
name: audit-hooks
description: Verify hook scripts and configuration, detect execution issues, validate exit codes. Use when user mentions audit hooks, check hooks, validate hooks, or during regular maintenance reviews.
---

# Audit Hooks Skill

---

## Configuration (CUSTOMIZE FOR YOUR PROJECT)

```yaml
# Example configuration - update for your project
audit_hooks:
  hooks_directory: ".claude/hooks"          # Where hooks live
  settings_file: ".claude/settings.json"    # Hook registration file
  test_files:                               # Sample files for testing
    python: "src/example.py"
    javascript: "src/example.ts"
    go: "pkg/example.go"
```

---

## Process

### 1. Discover Hooks
Find all hook scripts:

```bash
# Find shell scripts
find .claude/hooks -type f -name "*.sh" 2>/dev/null

# Find Python scripts
find .claude/hooks -type f -name "*.py" 2>/dev/null

# List all hooks
ls -la .claude/hooks/
```

### 2. Validate Hook Scripts

**File checks**:
- Script file exists and is readable
- Script is executable (`chmod +x`)
- Has shebang line (`#!/bin/bash` or `#!/usr/bin/env python3`)

**Structure checks**:
- Accepts required arguments (`$FILE_PATH`, `$TOOL_NAME`)
- Has exit code handling (exit 0, exit 2)
- Has error messaging for failures

**Logic checks**:
- Pre-tool-use hooks: Block on exit 2
- Post-tool-use hooks: Report error on exit 2
- Non-blocking hooks: Always exit 0

### 3. Validate Configuration
Check `.claude/settings.json`:

**Hook registration**:
- Hooks are registered under correct event types
- Matcher patterns are correct (Edit, Write, Read)
- Command paths are correct
- Required variables are passed ($FILE_PATH, $TOOL_NAME)

**Schema validation**:
- JSON is well-formed
- Follows Claude Code hooks schema
- No syntax errors

### 4. Test Execution
Run hooks in test mode:

**Pre-tool-use hooks**:
```bash
# Test with valid file (should exit 0)
.claude/hooks/your_check_hook.sh "src/valid_file.py" "Edit"

# Test with invalid file (should exit 2 with message)
.claude/hooks/your_check_hook.sh "src/InvalidFile.py" "Edit"
```

**Post-tool-use hooks**:
```bash
# Test linting hook
.claude/hooks/your_lint_hook.sh "src/some_file.py" "Edit"
# Expected: exit 0 or exit 2 with error details
```

### 5. Check Dependencies
Verify hook dependencies exist:

**For linting hooks**:
- Check if linter is installed (`which ruff`, `which eslint`, etc.)
- Check if config file exists
- Check package manager is available

**For test hooks**:
- Check if test runner is installed
- Check if test config exists

### 6. Report Findings

**Healthy hook**:
```
✓ lint_on_save.sh
  - File: Exists, executable, proper shebang
  - Structure: Valid (accepts args, proper exits)
  - Configuration: Registered correctly in settings.json
  - Execution: Test passed
  - Dependencies: All present
```

**Broken hook**:
```
✗ run_tests.sh
  - File: Exists, executable, proper shebang
  - Structure: Valid
  - Configuration: Registered correctly
  - Execution: Test failed (exit 1)
    Error: pytest: command not found
  - Dependencies: Missing pytest
```

### 7. Suggest Fixes
For each issue:
- Explain what's wrong
- Show fix steps
- Offer to apply fix if possible

---

## Invocation

```
/audit-hooks
```

---

## Output Format

**Summary**:
```
Hook Audit Report
=================

Total hooks: 5
  ✓ Healthy: 4
  ✗ Broken: 1

Healthy hooks:
  - check_naming_convention.sh
  - lint_on_save.sh
  - format_code.sh
  - validate_imports.sh

Broken hooks:
  - run_tests.sh (1 issue)
```

**Detailed findings**:
```
run_tests.sh issues:
  1. Dependency missing: pytest command not found
     - Cause: pytest not installed or not in PATH
     - Fix: Install pytest via your package manager
     - Impact: Test hook will fail

  Suggested action: Install missing dependency and re-test
```

---

## Common Issues

### Execution Issues

**Permission denied**:
```
✗ Hook not executable
  Fix: chmod +x .claude/hooks/script.sh
```

**Command not found**:
```
✗ Dependency missing
  Fix: Install required tool (linter, test runner, etc.)
```

**Wrong exit code**:
```
✗ Hook exits 1 instead of 0 or 2
  Fix: Update script to use exit 0 (pass) or exit 2 (block/error)
```

### Configuration Issues

**Hook not registered**:
```
✗ Hook script exists but not in settings.json
  Fix: Add hook registration to PreToolUse or PostToolUse
```

**Wrong matcher**:
```
✗ Hook registered for "Read" but should be "Edit"
  Fix: Update matcher in settings.json
```

**Missing arguments**:
```
✗ Hook command doesn't pass $FILE_PATH
  Fix: Update command to include "$FILE_PATH" "$TOOL_NAME"
```

### Logic Issues

**Pre-tool-use not blocking**:
```
✗ Hook exits 0 on invalid input (should exit 2)
  Fix: Update exit code for blocking behavior
```

**Post-tool-use blocking incorrectly**:
```
✗ Hook exits 1 instead of 2 (non-standard exit code)
  Fix: Use exit 2 for errors in post-tool-use hooks
```

---

## Auto-Fix Capabilities

Can automatically fix:
- Permission issues (chmod +x)
- Simple configuration errors
- Missing hook registrations

Requires manual fix:
- Missing dependencies (requires installation)
- Logic errors in hook scripts
- Complex configuration issues

---

## CRITICAL: Git Operations Policy

**NEVER automatically commit, push, or perform any git operations.**

This skill ONLY audits hook scripts and configuration files. Git operations are ONLY performed when:
- User explicitly requests "commit these fixes"
- User explicitly requests "push to remote"
- User explicitly requests "create PR"

This is primarily a READ-ONLY diagnostic skill.

---

## Notes

- Test hooks in isolated environment to avoid side effects
- Hooks should be idempotent (safe to run multiple times)
- Hooks should be fast (<5 seconds for most operations)
- Hooks should provide clear error messages
- Run audit after adding/modifying hooks
