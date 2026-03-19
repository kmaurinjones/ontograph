#!/usr/bin/env python3
"""
Scan and validate Claude Code skills structure.
Outputs JSON for Claude to parse.
"""
import json
import sys
from pathlib import Path


def scan_skills(skills_dir=".claude/skills"):
    """Scan all skills and return validation results."""
    skills_path = Path(skills_dir)

    if not skills_path.exists():
        return {"error": "Skills directory not found", "path": str(skills_path)}

    results = []

    for skill_dir in skills_path.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_info = {
            "name": skill_dir.name,
            "path": str(skill_dir),
            "skill_md_exists": (skill_dir / "SKILL.md").exists(),
            "process_md_exists": (skill_dir / "PROCESS.md").exists(),
            "scripts_dir_exists": (skill_dir / "scripts").exists(),
            "templates_dir_exists": (skill_dir / "templates").exists(),
            "assets_dir_exists": (skill_dir / "assets").exists(),
            "issues": []
        }

        # Validate SKILL.md structure
        if skill_info["skill_md_exists"]:
            skill_md_path = skill_dir / "SKILL.md"
            content = skill_md_path.read_text()

            required_sections = ["Purpose", "Use when", "Process", "Invocation"]
            for section in required_sections:
                if f"**{section}**" not in content and f"## {section}" not in content:
                    skill_info["issues"].append(f"Missing section: {section}")
        else:
            skill_info["issues"].append("SKILL.md not found")

        # Check if scripts directory has executable files
        if skill_info["scripts_dir_exists"]:
            scripts_dir = skill_dir / "scripts"
            script_files = list(scripts_dir.glob("*"))
            skill_info["script_count"] = len([f for f in script_files if f.is_file()])
        else:
            skill_info["script_count"] = 0

        results.append(skill_info)

    return {
        "total_skills": len(results),
        "skills": results
    }


if __name__ == "__main__":
    # Get skills directory from args or use default
    skills_dir = sys.argv[1] if len(sys.argv) > 1 else ".claude/skills"

    results = scan_skills(skills_dir)
    print(json.dumps(results, indent=2))
