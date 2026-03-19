---
name: skill-generator
description: Create production-ready Claude Code skills from workflow designs or ad-hoc requirements. Use when user mentions new skill, create skill, generate skill, or after completing workflow-designer phase.
---

# Skill Generator Skill

---

## Skill Architecture

A skill is a directory with structured content:

```
.claude/skills/{skill-name}/
├── SKILL.md        # Required: Entry point (target <500 lines)
├── PROCESS.md      # Optional: Detailed flow for complex processes
├── scripts/        # Optional: Executable code
│   └── *.py|sh     # Scripts output JSON, not prose
├── templates/      # Optional: Scaffolding templates
│   └── *.template  # Mustache/Jinja templates for code generation
└── assets/         # Optional: Binary resources
    └── *.png|pdf   # Images, docs, references
```

---

## SKILL.md Requirements

**Must include**:
1. **Purpose**: One-line description of what it does
2. **Use when**: Trigger-rich description (3-5 trigger phrases)
3. **Process**: Step-by-step execution flow
4. **Invocation**: How to call it (slash command or context)
5. **Output format**: What it produces
6. **Examples**: At least one complete example

**Tone**: Direct, imperative, no fluff. Staff engineer explaining to another engineer.

**Token target**: <500 lines for simple skills, use PROCESS.md for detailed flows

---

## Trigger Phrase Strategy

**Good triggers** (specific, action-oriented):
- "new feature", "add feature", "implement feature"
- "fix bug", "resolve bug", "debug issue"
- "create test", "generate test", "add test coverage"

**Bad triggers** (too generic):
- "help"
- "do something"
- "improve code"

**Best practice**: Include 3-5 triggers covering synonyms + user phrasing variations.

---

## Script Guidelines

When skills need executable logic:

**Input**: Scripts receive arguments via command line or environment variables
**Output**: Scripts MUST output JSON to stdout
**Errors**: Scripts output error JSON: `{"error": "message", "details": {}}`

**Why JSON?**: Claude sees script output, not source. JSON is parseable, prose is not.

**Example Python script**:
```python
#!/usr/bin/env python3
import json
import sys

def analyze_codebase(directory):
    # Analysis logic here
    results = {"files": 42, "patterns": ["components", "routes"]}
    return results

if __name__ == "__main__":
    directory = sys.argv[1] if len(sys.argv) > 1 else "."
    results = analyze_codebase(directory)
    print(json.dumps(results, indent=2))
```

**Example shell script**:
```bash
#!/bin/bash
# Outputs JSON

echo "{"
echo "  \"files_found\": $(find . -name "*.py" | wc -l),"
echo "  \"status\": \"success\""
echo "}"
```

---

## Template Guidelines

When skills scaffold code:

**Format**: Use Mustache (simple) or Jinja2 (complex) templating
**Variables**: Clearly document all template variables
**Testing**: Include example variable values in template comments

**Example React component template**:
```typescript
// templates/component.template.tsx
// Variables: {{componentName}}, {{propsInterface}}

import React from 'react';

interface {{propsInterface}} {
  // Props here
}

export const {{componentName}}: React.FC<{{propsInterface}}> = (props) => {
  return (
    <div>
      {/* Component implementation */}
    </div>
  );
};
```

**Example Python module template**:
```python
# templates/module.template.py
# Variables: {{module_name}}, {{class_name}}

"""{{module_name}} - Generated module."""


class {{class_name}}:
    """{{class_name}} implementation."""

    def __init__(self):
        pass
```

---

## Generation Process

### Step 1: Requirements Gathering
Ask user:
- What does this skill do?
- When should it activate?
- What inputs does it need?
- What outputs does it produce?
- Does it need scripts or templates?

### Step 2: Skill Structure Planning
Decide:
- Simple (SKILL.md only) or complex (SKILL.md + PROCESS.md)?
- Need scripts? What language? What do they analyze/generate?
- Need templates? What code patterns do they scaffold?
- Need assets? Documentation? Diagrams?

### Step 3: Content Generation
Generate:
- SKILL.md with all required sections
- PROCESS.md if complex workflow
- Scripts with JSON output
- Templates with variable documentation
- Assets as needed

### Step 4: Validation
Check:
- Triggers are specific and action-oriented
- Process is clear and executable
- Scripts output valid JSON
- Templates are well-documented
- Examples are complete and realistic

### Step 5: Testing Strategy
Define:
- How to test the skill manually
- What edge cases to consider
- How to verify output correctness

---

## Stack-Aware Generation

Skills adapt to project stack. Before generating, analyze:

**Backend detection**:
- Python → Check for FastAPI/Flask/Django patterns
- JavaScript → Check for Express/Nest.js patterns
- Go → Check for Gin/Echo patterns
- Rust → Check for Axum/Actix patterns

**Frontend detection**:
- React → Check for class/functional components, hooks
- Next.js → Check for App Router/Pages Router
- Vue/Angular/Svelte → Check for component conventions

**Testing detection**:
- Python → pytest vs unittest
- JavaScript → Jest vs Vitest vs Mocha
- Go → testing package patterns

**Linting detection**:
- Python → Ruff vs Black vs flake8
- JavaScript → ESLint + Prettier
- Go → golangci-lint

Skills should use the EXISTING tooling, not introduce new tools.

---

## Example Skill: Data Exporter

**Input**: User request "I want a skill that exports data to CSV"

**Generated SKILL.md**:

```markdown
# Data Exporter Skill

**Purpose**: Export application data to CSV format with customizable columns.

**Use when**: User mentions "export data", "export to CSV", "download CSV", "generate report".

## Process

1. **Identify data source**: Ask user what data to export
2. **Determine columns**: List available fields, let user select
3. **Generate export**: Create CSV with selected columns
4. **Verify output**: Check file was created correctly

## Invocation

/data-exporter <data_source>

## Output

- CSV file at specified location
- Summary of rows exported

## Examples

**Request**: "Export users to CSV"

**Generated**:
- `exports/users_20260113.csv`
- Summary: "Exported 150 users with columns: id, name, email, created_at"

**Verification**:
- File exists and is readable
- CSV has correct headers
- Row count matches source
```

---

## Naming Conventions

**Skill names**:
- Use kebab-case: `feature-generator`, `test-runner`, `bug-fixer`
- Be descriptive but concise
- NO product/project names (portable infrastructure)

**File names**:
- SKILL.md (uppercase, required)
- PROCESS.md (uppercase, optional)
- scripts/ (lowercase)
- templates/ (lowercase)
- assets/ (lowercase)

---

## Integration with Workflow Designer

This skill works best AFTER workflow-designer:

1. User describes goal
2. Workflow-designer produces design (6 phases)
3. Skill-generator creates skill from design
4. User tests and iterates

Can also work standalone for simple skills:

1. User describes skill need
2. Skill-generator asks clarifying questions
3. Generates skill directly
4. User tests and iterates

---

## Self-Extension

This skill can improve itself:

```
User: "Generate a skill-generator skill that's better than the current one"
Assistant: [Runs workflow-designer to design improved version, then generates new skill]
```

This is meta-programming: the system extends itself using its own tools.

---

## CRITICAL: Git Operations Policy

**NEVER automatically commit, push, or perform any git operations.**

This skill ONLY generates skill files and documentation. Git operations are ONLY performed when:
- User explicitly requests "commit this skill"
- User explicitly requests "push to remote"
- User explicitly requests "create PR"

Do NOT:
- Auto-commit after skill generation
- Auto-push after validation
- Auto-create PRs
- Run any CI/CD pipelines automatically

If the user wants git operations, they will ask explicitly.

---

## Notes

- Always include trigger phrases - they're critical for activation
- Scripts are optional but powerful for complex analysis/generation
- Templates are essential for consistent code scaffolding
- Keep SKILL.md focused - detailed flows go in PROCESS.md
- Test manually before declaring success
