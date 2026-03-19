#!/usr/bin/env python3
"""
Detect drift in skills (references that don't match current project structure).
Outputs JSON for Claude to parse.
"""
import json
import re
import sys
from pathlib import Path


def detect_drift(skill_path, project_root="."):
    """Detect drift in a single skill."""
    skill_md = Path(skill_path) / "SKILL.md"

    if not skill_md.exists():
        return {"error": "SKILL.md not found", "path": str(skill_md)}

    content = skill_md.read_text()
    project_root = Path(project_root)
    drift_issues = []

    # Check for pip references (should be uv)
    pip_matches = re.findall(r'pip install|pip\s+\w+', content)
    if pip_matches:
        drift_issues.append({
            "type": "package_manager",
            "issue": "References 'pip' but project uses 'uv'",
            "matches": pip_matches,
            "fix": "Replace 'pip install X' with 'uv add X'"
        })

    # Check for file path references
    path_pattern = r'`(backend/[a-zA-Z/_\.]+|frontend/[a-zA-Z/_\.]+)`'
    path_matches = re.findall(path_pattern, content)

    for path in path_matches:
        full_path = project_root / path
        if not full_path.exists() and not path.endswith('.py') and not path.endswith('.tsx'):
            # Only flag if it's a directory reference or complete file reference
            if '/' in path and not any(ext in path for ext in ['.py', '.tsx', '.ts', '.js']):
                drift_issues.append({
                    "type": "file_path",
                    "issue": f"Referenced path does not exist: {path}",
                    "path": path
                })

    # Check for unittest references (should be pytest)
    if 'unittest' in content and (project_root / "pyproject.toml").exists():
        drift_issues.append({
            "type": "test_framework",
            "issue": "References 'unittest' but project uses 'pytest'",
            "fix": "Update test examples to use pytest"
        })

    return {
        "skill": Path(skill_path).name,
        "drift_count": len(drift_issues),
        "drift_issues": drift_issues
    }


def detect_all_drift(skills_dir=".claude/skills", project_root="."):
    """Detect drift in all skills."""
    skills_path = Path(skills_dir)

    if not skills_path.exists():
        return {"error": "Skills directory not found"}

    results = []
    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir():
            result = detect_drift(skill_dir, project_root)
            results.append(result)

    total_drift = sum(r.get("drift_count", 0) for r in results)

    return {
        "total_skills": len(results),
        "total_drift_issues": total_drift,
        "skills": results
    }


if __name__ == "__main__":
    skills_dir = sys.argv[1] if len(sys.argv) > 1 else ".claude/skills"
    project_root = sys.argv[2] if len(sys.argv) > 2 else "."

    results = detect_all_drift(skills_dir, project_root)
    print(json.dumps(results, indent=2))
