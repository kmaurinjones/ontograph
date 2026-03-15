#!/usr/bin/env python3
"""
Analyze existing skills to extract common patterns and conventions.
Useful when creating new skills to follow established patterns.
"""
import json
import re
from pathlib import Path


def analyze_skill_patterns(skills_dir=".claude/skills"):
    """Analyze patterns across all skills."""
    skills_path = Path(skills_dir)

    if not skills_path.exists():
        return {"error": "Skills directory not found"}

    patterns = {
        "trigger_phrases": [],
        "section_headings": {},
        "script_languages": {"python": 0, "bash": 0},
        "common_words_in_purpose": {},
        "invocation_styles": []
    }

    for skill_dir in skills_path.iterdir():
        if not skill_dir.is_dir():
            continue

        skill_md = skill_dir / "SKILL.md"
        if not skill_md.exists():
            continue

        content = skill_md.read_text()

        # Extract trigger phrases from "Use when" section
        use_when_match = re.search(r'\*\*Use when\*\*:\s*([^\n]+)', content)
        if use_when_match:
            triggers = use_when_match.group(1).split(",")
            for trigger in triggers:
                trigger = trigger.strip().strip(".")
                if trigger:
                    patterns["trigger_phrases"].append({
                        "skill": skill_dir.name,
                        "trigger": trigger
                    })

        # Extract section headings (## and ###)
        headings = re.findall(r'^(#{2,3})\s+(.+)$', content, re.MULTILINE)
        for level, heading in headings:
            heading = heading.strip()
            if heading not in patterns["section_headings"]:
                patterns["section_headings"][heading] = 0
            patterns["section_headings"][heading] += 1

        # Extract invocation style
        invocation_match = re.search(r'/([a-z-]+)', content)
        if invocation_match:
            patterns["invocation_styles"].append({
                "skill": skill_dir.name,
                "command": invocation_match.group(1)
            })

        # Count script languages
        scripts_dir = skill_dir / "scripts"
        if scripts_dir.exists():
            for script in scripts_dir.iterdir():
                if script.suffix == ".py":
                    patterns["script_languages"]["python"] += 1
                elif script.suffix == ".sh":
                    patterns["script_languages"]["bash"] += 1

    # Find most common section headings
    sorted_headings = sorted(
        patterns["section_headings"].items(),
        key=lambda x: x[1],
        reverse=True
    )
    patterns["common_sections"] = [h[0] for h in sorted_headings[:10]]

    # Summary
    patterns["summary"] = {
        "total_skills_analyzed": len([d for d in skills_path.iterdir() if d.is_dir()]),
        "total_triggers": len(patterns["trigger_phrases"]),
        "python_scripts": patterns["script_languages"]["python"],
        "bash_scripts": patterns["script_languages"]["bash"]
    }

    return patterns


if __name__ == "__main__":
    result = analyze_skill_patterns()
    print(json.dumps(result, indent=2))
