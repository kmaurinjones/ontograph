---
name: fine-tune-skills
description: Update all skills in .claude/skills/ to stay aligned with the current project codebase structure, conventions, and demands. Use when user mentions fine-tune skills, update skills, sync skills, refresh skills, or during periodic maintenance to keep skills current with evolving codebase.
---

# Fine-Tune Skills Skill

---

## Philosophy

**Skills are living documentation.** As the codebase evolves, skills must evolve with it. Outdated skills are worse than no skills - they actively mislead.

**Surgical updates over rewrites.** Update only what's drifted. If a skill is 90% correct, fix the 10%, don't regenerate from scratch.

**Preserve intent, update implementation.** The skill's purpose and triggers usually stay valid; it's the file paths, commands, and conventions that drift.

**Stack-agnostic.** This skill detects what YOUR project uses and aligns skills to match. No assumptions about "correct" tools - pip, uv, poetry, npm, yarn, pnpm, bun are all valid depending on your project.

---

## Configuration (AUTO-DETECTED)

The skill auto-detects your project's tooling from lockfiles and config:

```yaml
# Example of what gets detected - yours may differ
fine_tune_skills:
  skills_directory: ".claude/skills"
  detected_tooling:
    package_managers:
      python: "poetry"       # Detected from poetry.lock
      javascript: "pnpm"     # Detected from pnpm-lock.yaml
    linters:
      python: "ruff"         # Detected from ruff.toml
      javascript: "eslint"   # Detected from .eslintrc
    test_runners:
      python: "pytest"       # Detected from pytest.ini
      javascript: "jest"     # Detected from jest.config.js
    directory_structure:
      source_dirs: ["src/", "lib/"]
      test_dirs: ["tests/"]
```

---

## Process

### 1. Analyze Current Project State
Gather project context before analyzing skills:

```bash
# Detect project structure and conventions (use your project's Python runner)
python .claude/skills/fine-tune-skills/scripts/analyze_project.py
```

**Captures**:
- Directory structure (where code actually lives)
- Package manager in use (from lockfiles and config)
- Linter configuration
- Test framework and patterns
- Import patterns
- File organization patterns

### 2. Scan All Skills
For each skill in `.claude/skills/`:

```bash
# Analyze skill alignment with project
python .claude/skills/fine-tune-skills/scripts/analyze_skills.py
```

**Evaluates**:
- File path references (do they exist?)
- Command references (do they match project tools?)
- Convention alignment (naming, structure)
- Process steps (are they still valid?)
- Examples (do they reflect current patterns?)

### 3. Categorize Update Needs

**No Update Needed**:
- Skill is fully aligned with project
- All paths, commands, and conventions match
- Examples are current

**Minor Update Needed** (Auto-fixable):
- Package manager command mismatches
- File path updates
- Test runner command updates
- Simple convention fixes

**Major Update Needed** (Requires review):
- Process steps no longer valid
- Core functionality has changed
- Architecture has evolved significantly
- Skill may need redesign

**Deprecated** (Consider removal):
- Skill references removed functionality
- Skill purpose no longer relevant
- Superseded by another skill

### 4. Generate Update Plan
Create a concrete update plan:

```
Fine-Tune Skills Analysis
=========================

Project uses: poetry (Python), pnpm (JS), pytest, jest

Skills Status:
  - No update needed: 4
  - Minor updates: 3
  - Major updates: 1
  - Deprecated: 1

Minor Updates (will auto-apply):
  feature-generator:
    * Line 42: pip install -> poetry add (project uses poetry)
    * Line 67: backend/api/ -> src/api/
    * Line 89: npm run test -> pnpm test

  test-runner:
    * Line 23: tests/unit/ -> tests/

  doc-creator:
    * Line 15: uv run python -> poetry run python

Major Updates (require review):
  workflow-designer:
    * Process section references old deployment pipeline
    * Recommendation: Manual review and update

Deprecated (recommend removal):
  legacy-migrator:
    * References migration system no longer in use
    * Recommendation: Archive or remove
```

### 5. Apply Minor Updates Automatically
For skills needing minor updates:

```bash
# Apply automated fixes
python .claude/skills/fine-tune-skills/scripts/update_skill.py --skill=<skill-name>
```

**Auto-fix capabilities**:
- Package manager command substitution (any direction: pip↔uv↔poetry↔pipenv)
- JS package manager substitution (npm↔yarn↔pnpm↔bun)
- File path updates (when target exists)
- Test runner command updates (pytest↔unittest, jest↔vitest↔mocha)

### 6. Flag Major Updates for Review
For skills needing major updates:
- Document what's changed in the project
- Highlight which skill sections are affected
- Provide suggested changes
- Wait for user approval before applying

### 7. Handle Deprecated Skills
For deprecated skills:
- Explain why skill appears deprecated
- Offer options:
  - Archive to `.claude/skills/_archived/`
  - Remove entirely
  - Update if still relevant
- Never auto-remove; always confirm with user

### 8. Generate Update Report
After all updates:

```
Fine-Tune Complete
==================

Applied Updates:
  feature-generator: 3 changes
  test-runner: 1 change
  doc-creator: 1 change

Pending Review:
  workflow-designer: Major update needed (see details above)

Deprecated:
  legacy-migrator: Awaiting user decision

Skills now in sync: 7/9
```

---

## Invocation

```
/fine-tune-skills
```

**With options**:
```
/fine-tune-skills --dry-run          # Preview changes without applying
/fine-tune-skills --skill=test-runner # Update only specific skill
/fine-tune-skills --force            # Apply all auto-fixable changes
/fine-tune-skills --verbose          # Show detailed analysis
```

---

## Update Categories

### Path Updates
```diff
- Find tests: `backend/tests/unit/`
+ Find tests: `tests/`
```

### Command Updates (Bidirectional - matches YOUR project)

If project uses `poetry` but skill uses `pip`:
```diff
- pip install pandas numpy
+ poetry add pandas numpy
```

If project uses `pip` but skill uses `uv`:
```diff
- uv add requests
+ pip install requests
```

If project uses `yarn` but skill uses `npm`:
```diff
- npm run build
+ yarn build
```

If project uses `vitest` but skill uses `jest`:
```diff
- jest --coverage
+ vitest --coverage
```

### Process Updates (Manual Review Required)
```
OLD: Deploy using `kubectl apply -f deployment.yaml`
NEW: Project now uses Helm charts

Suggested update:
  - Replace kubectl deployment instructions
  - Add Helm chart references
  - Update rollback procedures
```

---

## Safety Rules

### Never Auto-Apply
- Conceptual changes to skill purpose
- Trigger phrase modifications
- Process flow restructuring
- Removal of entire sections

### Always Preserve
- Skill's core purpose and intent
- User-customized content (if detectable)
- Working examples (only update broken ones)
- Critical safety rules sections

### Always Backup
Before any modification:
```bash
cp -r .claude/skills .claude/skills.backup.$(date +%Y%m%d-%H%M%S)
```

---

## CRITICAL: Git Operations Policy

**NEVER automatically commit, push, or perform any git operations.**

This skill ONLY modifies skill files in `.claude/skills/`. Git operations are ONLY performed when:
- User explicitly requests "commit these changes"
- User explicitly requests "push to remote"
- User explicitly requests "create PR"

All changes are local until user explicitly requests git operations.

---

## Output Format

**Analysis Phase**:
```
Analyzing project structure...
  Source: src/
  Tests: tests/
  Package manager (Python): poetry
  Package manager (JS): pnpm
  Linter: ruff
  Test runner: pytest

Scanning skills...
  Found 9 skills in .claude/skills/

Comparing against project...
```

**Update Phase**:
```
Updating feature-generator...
  [1/3] pip install -> poetry add (line 42)
  [2/3] backend/api/ -> src/api/ (line 67)
  [3/3] npm run test -> pnpm test (line 89)
  Done.

Updating test-runner...
  [1/1] tests/unit/ -> tests/ (line 23)
  Done.
```

**Summary**:
```
Fine-Tune Complete
==================
Updated: 3 skills (5 total changes)
Pending: 1 skill (major update needed)
Deprecated: 1 skill (awaiting decision)
Up-to-date: 4 skills
```

---

## Integration with Other Skills

- **audit-skills**: Run audit first to understand drift before fine-tuning
- **skill-generator**: Regenerate skills that need major updates
- **workflow-designer**: Redesign skills with outdated workflows
- **linting-enforcer**: Run after updates to ensure SKILL.md formatting

---

## Difference from audit-skills

| audit-skills | fine-tune-skills |
|--------------|------------------|
| Read-only | Writes updates |
| Reports drift | Fixes drift |
| One-time snapshot | Iterative updates |
| Diagnostic | Corrective |

Use `audit-skills` to understand the problem. Use `fine-tune-skills` to fix it.

---

## Notes

- Run after major codebase refactoring
- Run after changing core tooling (package manager, linter, test framework)
- Run periodically (monthly) for maintenance
- Always review major updates before applying
- Keep skills lean; if updates are too complex, consider regenerating
- This skill is stack-agnostic: it adapts to YOUR project's tooling, not the other way around
