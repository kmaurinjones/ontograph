#!/bin/bash
# Scaffold a new skill directory structure
# Usage: scaffold_skill.sh <skill-name> [--with-scripts] [--with-templates]

SKILL_NAME="$1"
WITH_SCRIPTS=false
WITH_TEMPLATES=false

# Parse flags
for arg in "$@"; do
    case $arg in
        --with-scripts)
            WITH_SCRIPTS=true
            ;;
        --with-templates)
            WITH_TEMPLATES=true
            ;;
    esac
done

if [ -z "$SKILL_NAME" ]; then
    echo '{"error": "No skill name provided", "usage": "scaffold_skill.sh <skill-name> [--with-scripts] [--with-templates]"}'
    exit 1
fi

SKILL_DIR=".claude/skills/$SKILL_NAME"

# Check if skill already exists
if [ -d "$SKILL_DIR" ]; then
    echo "{\"error\": \"Skill already exists\", \"path\": \"$SKILL_DIR\"}"
    exit 1
fi

# Create directories
mkdir -p "$SKILL_DIR"

if [ "$WITH_SCRIPTS" = true ]; then
    mkdir -p "$SKILL_DIR/scripts"
fi

if [ "$WITH_TEMPLATES" = true ]; then
    mkdir -p "$SKILL_DIR/templates"
fi

# Create basic SKILL.md
cat > "$SKILL_DIR/SKILL.md" << 'SKILLMD'
# {{SKILL_NAME}} Skill

**Purpose**: [Describe what this skill does in one line]

**Use when**: [trigger phrase 1], [trigger phrase 2], [trigger phrase 3].

---

## Process

### 1. [First Step]
[Description of what happens in this step]

### 2. [Second Step]
[Description of what happens in this step]

---

## Invocation

```
/{{SKILL_NAME}}
```

---

## Output Format

[Describe what this skill produces]

---

## Notes

- [Important note 1]
- [Important note 2]
SKILLMD

# Replace placeholder
sed -i '' "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$SKILL_DIR/SKILL.md" 2>/dev/null || \
sed -i "s/{{SKILL_NAME}}/$SKILL_NAME/g" "$SKILL_DIR/SKILL.md"

# Output result
echo "{"
echo "  \"status\": \"created\","
echo "  \"skill_name\": \"$SKILL_NAME\","
echo "  \"path\": \"$SKILL_DIR\","
echo "  \"created\": {"
echo "    \"skill_md\": true,"
echo "    \"scripts_dir\": $WITH_SCRIPTS,"
echo "    \"templates_dir\": $WITH_TEMPLATES"
echo "  }"
echo "}"
