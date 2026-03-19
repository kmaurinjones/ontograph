---
name: audit-skills
description: Audit Claude Code skills to detect drift, validate structure, and ensure alignment with codebase. Use when user mentions audit skills, check skills, validate skills, or during regular maintenance reviews.
---

# Audit Skills Skill

---

## Configuration (CUSTOMIZE FOR YOUR PROJECT)

```yaml
# Example configuration - update for your project
audit_skills:
  skills_directory: ".claude/skills"        # Where skills live
  project_structure:
    source_dirs:
      - "src/"                              # Your source directories
      - "lib/"
    test_dirs:
      - "tests/"                            # Your test directories
      - "__tests__/"
  package_managers:
    python: "uv"                            # or "pip", "poetry"
    javascript: "npm"                       # or "yarn", "pnpm"
  linters:
    python: "ruff"                          # or "flake8", "pylint"
    javascript: "eslint"                    # or "biome"
  test_runners:
    python: "pytest"                        # or "unittest"
    javascript: "vitest"                    # or "jest", "mocha"
```

---

## Process

### 1. Discover Skills
Find all skills:

```bash
find .claude/skills -type f -name "SKILL.md"
```

### 2. Validate Structure
For each skill, check:

**Required files**:
- SKILL.md must exist
- Must contain required sections:
  - Purpose
  - Use when
  - Process
  - Invocation

**Optional files**:
- PROCESS.md (for complex workflows)
- scripts/ directory
- templates/ directory
- assets/ directory

### 3. Check Trigger Phrases
Validate "Use when" section:
- Contains 3-5 trigger phrases
- Triggers are specific and action-oriented
- No generic triggers ("help", "do something")

### 4. Verify Stack Alignment
Check if skill references match current stack:

**Detect your project's stack**:
```bash
# Python project?
[ -f "pyproject.toml" ] && echo "Python project detected"
[ -f "setup.py" ] && echo "Python project detected"

# JavaScript project?
[ -f "package.json" ] && echo "JavaScript project detected"

# Go project?
[ -f "go.mod" ] && echo "Go project detected"

# Rust project?
[ -f "Cargo.toml" ] && echo "Rust project detected"
```

**Check alignment**:
- Commands reference correct package manager
- File paths match actual structure
- Test framework matches project
- Linter matches project

### 5. Detect Drift
Compare skill content with codebase reality:

**File structure drift**:
- Skill references `backend/app/` but actual code in `src/`
- Skill references paths that don't exist

**Convention drift**:
- Skill says snake_case but codebase uses camelCase
- Skill references wrong test runner

**Dependency drift**:
- Skill references tools not in package manifest

### 6. Report Findings
Generate audit report:

**Clean skill**:
```
✓ test-runner
  - Structure: Valid
  - Triggers: 4 triggers (specific)
  - Stack alignment: Correct
  - No drift detected
```

**Drifted skill**:
```
⚠ feature-generator
  - Structure: Valid
  - Triggers: 5 triggers (specific)
  - Stack alignment: Mostly correct
  - Drift detected:
    * References `pip install` but project uses `uv`
    * References `src/api/` but actual structure is `app/api/`
```

**Invalid skill**:
```
✗ broken-skill
  - Structure: Invalid (missing SKILL.md)
  - Cannot validate
```

### 7. Suggest Fixes
For each drift/issue:
- Explain what's wrong
- Show expected vs actual
- Offer to fix automatically

---

## Invocation

```
/audit-skills
```

---

## Output Format

**Summary**:
```
Skill Audit Report
==================

Total skills: 8
  ✓ Clean: 5
  ⚠ Drift detected: 2
  ✗ Invalid: 1

Clean skills:
  - workflow-designer
  - skill-generator
  - test-runner
  - bug-fixer
  - linting-enforcer

Drifted skills:
  - feature-generator (2 issues)
  - deprecated-skill (3 issues)

Invalid skills:
  - broken-skill (missing SKILL.md)
```

**Detailed findings**:
```
feature-generator drift:
  1. Package manager mismatch
     - Skill: pip install pandas
     - Expected: uv add pandas
     - Fix: Update all pip commands to uv

  2. Directory structure mismatch
     - Skill: backend/src/api/
     - Actual: src/api/
     - Fix: Update all file path references
```

---

## Audit Categories

### Structure Validation
- SKILL.md exists and is readable
- Required sections present
- Markdown formatting valid

### Content Validation
- Trigger phrases present and specific
- Process section has clear steps
- Examples included

### Stack Alignment
- Commands match installed tools
- File paths match project structure
- Dependencies match package manifest

### Convention Alignment
- Naming conventions match codebase
- Code style matches project standards
- Architecture patterns align

### Drift Detection
- Referenced files/directories exist
- Commands are executable
- Tools are installed
- Paths are current

---

## Auto-Fix Capabilities

Can automatically fix:
- Package manager commands (pip → uv, npm → yarn)
- Simple path updates
- Formatting issues in SKILL.md

Requires manual fix:
- Conceptual drift (skill outdated entirely)
- Major restructuring needed
- Trigger phrase redesign

---

## Integration with Other Skills

**workflow-designer**: Use audit findings to redesign outdated skills
**skill-generator**: Regenerate drifted skills from scratch

---

## CRITICAL: Git Operations Policy

**NEVER automatically commit, push, or perform any git operations.**

This skill ONLY audits skill files and reports drift. Git operations are ONLY performed when:
- User explicitly requests "commit these fixes"
- User explicitly requests "push to remote"
- User explicitly requests "create PR"

This is primarily a READ-ONLY diagnostic skill.

---

## Notes

- Run audit monthly or after major refactoring
- Prioritize fixing invalid skills first
- Address drift before it compounds
- Keep skills in sync with codebase evolution
