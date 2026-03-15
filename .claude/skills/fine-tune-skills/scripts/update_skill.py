#!/usr/bin/env python3
"""
Apply updates to a skill file based on analysis results.
Can perform dry-run or actual updates.
"""
import json
import re
import shutil
from datetime import datetime
from pathlib import Path


def backup_skill(skill_path: Path) -> Path:
    """Create a backup of the skill before modification."""
    backup_dir = skill_path.parent.parent / "_backups"
    backup_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    backup_name = f"{skill_path.parent.name}_{timestamp}"
    backup_path = backup_dir / backup_name

    shutil.copytree(skill_path.parent, backup_path)
    return backup_path


def apply_command_fix(content: str, issue: dict) -> tuple[str, bool]:
    """Apply a command fix to content. Returns (new_content, was_changed)."""
    current = issue.get("current", "")
    fix = issue.get("fix", "")

    if not current or not fix:
        return content, False

    # Escape special regex characters in current command
    escaped_current = re.escape(current)

    # Try to match in code blocks and inline code
    patterns = [
        # In code blocks
        (rf'(`{escaped_current}`)', f'`{fix}`'),
        # Plain text (less common but handle it)
        (rf'\b{escaped_current}\b', fix),
    ]

    new_content = content
    changed = False

    for pattern, replacement in patterns:
        if re.search(pattern, new_content):
            new_content = re.sub(pattern, replacement, new_content)
            changed = True
            break

    return new_content, changed


def apply_path_fix(content: str, issue: dict) -> tuple[str, bool]:
    """Apply a path fix to content. Returns (new_content, was_changed)."""
    current = issue.get("current", "")
    fix = issue.get("fix")

    if not current or not fix:
        return content, False

    # Escape special regex characters
    escaped_current = re.escape(current)

    # Match paths in various contexts
    patterns = [
        # In backticks
        (rf'`{escaped_current}`', f'`{fix}`'),
        # In quotes
        (rf'"{escaped_current}"', f'"{fix}"'),
        # In single quotes
        (rf"'{escaped_current}'", f"'{fix}'"),
    ]

    new_content = content
    changed = False

    for pattern, replacement in patterns:
        if re.search(pattern, new_content):
            new_content = re.sub(pattern, replacement, new_content)
            changed = True

    return new_content, changed


def apply_fixes(skill_md_path: Path, issues: list, dry_run: bool = False) -> dict:
    """Apply all auto-fixable issues to a skill file."""
    content = skill_md_path.read_text()
    original_content = content

    applied = []
    skipped = []

    for issue in issues:
        fix = issue.get("fix")
        if not fix:
            skipped.append({
                "issue": issue,
                "reason": "No fix available"
            })
            continue

        issue_type = issue.get("type", "unknown")

        if issue_type in ("package_manager", "python_runner", "test_runner"):
            content, changed = apply_command_fix(content, issue)
        elif issue_type == "path":
            content, changed = apply_path_fix(content, issue)
        else:
            skipped.append({
                "issue": issue,
                "reason": f"Unknown issue type: {issue_type}"
            })
            continue

        if changed:
            applied.append(issue)
        else:
            skipped.append({
                "issue": issue,
                "reason": "Pattern not found in content"
            })

    result = {
        "skill": skill_md_path.parent.name,
        "path": str(skill_md_path),
        "applied_count": len(applied),
        "skipped_count": len(skipped),
        "applied": applied,
        "skipped": skipped,
        "dry_run": dry_run,
        "content_changed": content != original_content
    }

    if not dry_run and content != original_content:
        # Create backup first
        backup_path = backup_skill(skill_md_path)
        result["backup_path"] = str(backup_path)

        # Write updated content
        skill_md_path.write_text(content)
        result["written"] = True
    else:
        result["written"] = False

    return result


def update_skill(skill_name: str, skills_dir: str = ".claude/skills",
                 analysis_file: str | None = None, dry_run: bool = False) -> dict:
    """Update a single skill based on analysis."""
    skill_path = Path(skills_dir) / skill_name
    skill_md = skill_path / "SKILL.md"

    if not skill_md.exists():
        return {"error": f"Skill not found: {skill_name}"}

    # Load analysis if provided
    issues = []
    if analysis_file and Path(analysis_file).exists():
        analysis = json.loads(Path(analysis_file).read_text())
        for skill_data in analysis.get("skills", []):
            if skill_data.get("skill") == skill_name:
                issues = skill_data.get("issues", [])
                break

    if not issues:
        return {
            "skill": skill_name,
            "status": "no_issues",
            "message": "No issues to fix"
        }

    # Filter to only auto-fixable issues
    fixable = [i for i in issues if i.get("fix")]

    if not fixable:
        return {
            "skill": skill_name,
            "status": "no_auto_fixes",
            "total_issues": len(issues),
            "message": "No auto-fixable issues"
        }

    return apply_fixes(skill_md, fixable, dry_run)


def update_all_skills(skills_dir: str = ".claude/skills",
                      analysis_file: str | None = None, dry_run: bool = False) -> dict:
    """Update all skills that have auto-fixable issues."""
    skills_path = Path(skills_dir)

    if not skills_path.exists():
        return {"error": "Skills directory not found"}

    # Load analysis
    if not analysis_file or not Path(analysis_file).exists():
        return {"error": "Analysis file required for batch updates"}

    analysis = json.loads(Path(analysis_file).read_text())

    results = []
    for skill_data in analysis.get("skills", []):
        if skill_data.get("auto_fixable", 0) > 0:
            result = update_skill(
                skill_data["skill"],
                skills_dir,
                analysis_file,
                dry_run
            )
            results.append(result)

    total_applied = sum(r.get("applied_count", 0) for r in results)
    total_skipped = sum(r.get("skipped_count", 0) for r in results)

    return {
        "summary": {
            "skills_updated": len([r for r in results if r.get("content_changed")]),
            "total_fixes_applied": total_applied,
            "total_fixes_skipped": total_skipped,
            "dry_run": dry_run
        },
        "results": results
    }


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Update skills based on analysis")
    parser.add_argument("--skill", help="Specific skill to update (omit for all)")
    parser.add_argument("--skills-dir", default=".claude/skills", help="Skills directory")
    parser.add_argument("--analysis", help="Path to analysis JSON file")
    parser.add_argument("--dry-run", action="store_true", help="Preview changes without applying")

    args = parser.parse_args()

    if args.skill:
        result = update_skill(args.skill, args.skills_dir, args.analysis, args.dry_run)
    else:
        result = update_all_skills(args.skills_dir, args.analysis, args.dry_run)

    print(json.dumps(result, indent=2))
