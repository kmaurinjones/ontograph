#!/usr/bin/env python3
"""
Analyze skills against project context to determine update needs.
Outputs JSON with categorized update requirements.

Stack-agnostic: Compares skill references against detected project tooling,
regardless of what tools are used. No assumptions about "correct" tools.
"""
import json
import re
import sys
from pathlib import Path


# Package manager command patterns for detection
PYTHON_PKG_MANAGERS = {
    "uv": {
        "install_pattern": r'\buv\s+add\b',
        "run_pattern": r'\buv\s+run\b',
        "install_cmd": "uv add",
        "run_cmd": "uv run",
    },
    "pip": {
        "install_pattern": r'\bpip\s+install\b',
        "run_pattern": r'^python\s+',  # Direct python invocation
        "install_cmd": "pip install",
        "run_cmd": "python",
    },
    "poetry": {
        "install_pattern": r'\bpoetry\s+add\b',
        "run_pattern": r'\bpoetry\s+run\b',
        "install_cmd": "poetry add",
        "run_cmd": "poetry run",
    },
    "pipenv": {
        "install_pattern": r'\bpipenv\s+install\b',
        "run_pattern": r'\bpipenv\s+run\b',
        "install_cmd": "pipenv install",
        "run_cmd": "pipenv run",
    },
}

JS_PKG_MANAGERS = {
    "npm": {"pattern": r'\bnpm\s+', "cmd": "npm"},
    "yarn": {"pattern": r'\byarn\s+', "cmd": "yarn"},
    "pnpm": {"pattern": r'\bpnpm\s+', "cmd": "pnpm"},
    "bun": {"pattern": r'\bbun\s+', "cmd": "bun"},
}

PYTHON_TEST_RUNNERS = {
    "pytest": {"pattern": r'\bpytest\b', "cmd": "pytest"},
    "unittest": {"pattern": r'\bunittest\b', "cmd": "python -m unittest"},
}

JS_TEST_RUNNERS = {
    "vitest": {"pattern": r'\bvitest\b', "cmd": "vitest"},
    "jest": {"pattern": r'\bjest\b', "cmd": "jest"},
    "mocha": {"pattern": r'\bmocha\b', "cmd": "mocha"},
}


def load_project_context(project_context_file: str | None = None) -> dict:
    """Load project context from file or return empty dict."""
    if project_context_file and Path(project_context_file).exists():
        return json.loads(Path(project_context_file).read_text())
    return {}


def extract_commands(content: str) -> list:
    """Extract shell commands from markdown code blocks."""
    commands = []

    # Match bash/shell code blocks
    code_block_pattern = r'```(?:bash|shell|sh)?\n(.*?)```'
    matches = re.findall(code_block_pattern, content, re.DOTALL)

    for match in matches:
        for line in match.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('#'):
                commands.append(line)

    # Also match inline code that looks like commands
    cmd_tools = '|'.join([
        'pip', 'npm', 'yarn', 'pnpm', 'bun', 'uv', 'poetry', 'pipenv',
        'python', 'pytest', 'vitest', 'jest', 'mocha', 'ruff', 'eslint',
        'flake8', 'pylint', 'biome'
    ])
    inline_pattern = rf'`((?:{cmd_tools})\s+[^`]+)`'
    inline_matches = re.findall(inline_pattern, content)
    commands.extend(inline_matches)

    return commands


def extract_paths(content: str) -> list:
    """Extract file/directory paths from skill content."""
    paths = []

    # Match paths in backticks
    backtick_pattern = r'`([a-zA-Z0-9_\-./]+(?:/[a-zA-Z0-9_\-./]+)+)`'
    paths.extend(re.findall(backtick_pattern, content))

    # Match paths in quotes
    quote_pattern = r'"([a-zA-Z0-9_\-./]+(?:/[a-zA-Z0-9_\-./]+)+)"'
    paths.extend(re.findall(quote_pattern, content))

    return list(set(paths))


def detect_skill_python_pkg_manager(commands: list) -> str | None:
    """Detect which Python package manager the skill references."""
    for cmd in commands:
        for name, patterns in PYTHON_PKG_MANAGERS.items():
            if re.search(patterns["install_pattern"], cmd):
                return name
    return None


def detect_skill_js_pkg_manager(commands: list) -> str | None:
    """Detect which JS package manager the skill references."""
    for cmd in commands:
        for name, patterns in JS_PKG_MANAGERS.items():
            if re.search(patterns["pattern"], cmd):
                return name
    return None


def detect_skill_python_test_runner(commands: list) -> str | None:
    """Detect which Python test runner the skill references."""
    for cmd in commands:
        for name, patterns in PYTHON_TEST_RUNNERS.items():
            if re.search(patterns["pattern"], cmd):
                return name
    return None


def detect_skill_js_test_runner(commands: list) -> str | None:
    """Detect which JS test runner the skill references."""
    for cmd in commands:
        for name, patterns in JS_TEST_RUNNERS.items():
            if re.search(patterns["pattern"], cmd):
                return name
    return None


def generate_command_fix(cmd: str, from_tool: str, to_tool: str, tool_type: str) -> str | None:
    """Generate a fixed command by substituting one tool for another."""
    if tool_type == "python_pkg":
        from_patterns = PYTHON_PKG_MANAGERS.get(from_tool, {})
        to_patterns = PYTHON_PKG_MANAGERS.get(to_tool, {})

        # Handle install commands
        if re.search(from_patterns.get("install_pattern", ""), cmd):
            # Extract packages being installed
            if from_tool == "pip":
                match = re.search(r'pip\s+install\s+(.+)', cmd)
            elif from_tool == "uv":
                match = re.search(r'uv\s+add\s+(.+)', cmd)
            elif from_tool == "poetry":
                match = re.search(r'poetry\s+add\s+(.+)', cmd)
            elif from_tool == "pipenv":
                match = re.search(r'pipenv\s+install\s+(.+)', cmd)
            else:
                match = None

            if match:
                packages = match.group(1)
                return f"{to_patterns['install_cmd']} {packages}"

        # Handle run commands
        if from_tool == "pip" and to_tool in ("uv", "poetry", "pipenv"):
            # python script.py -> <tool> run python script.py
            if re.match(r'^python\s+', cmd):
                return re.sub(r'^python\s+', f"{to_patterns['run_cmd']} python ", cmd)

        if from_tool in ("uv", "poetry", "pipenv") and to_tool == "pip":
            # <tool> run python script.py -> python script.py
            run_pattern = from_patterns.get("run_pattern", "")
            if run_pattern and re.search(run_pattern, cmd):
                return re.sub(rf'{from_tool}\s+run\s+', '', cmd)

    elif tool_type == "js_pkg":
        from_cmd = JS_PKG_MANAGERS.get(from_tool, {}).get("cmd", "")
        to_cmd = JS_PKG_MANAGERS.get(to_tool, {}).get("cmd", "")
        if from_cmd and to_cmd:
            return re.sub(rf'\b{from_cmd}\s+', f'{to_cmd} ', cmd)

    elif tool_type == "python_test":
        from_patterns = PYTHON_TEST_RUNNERS.get(from_tool, {})
        to_patterns = PYTHON_TEST_RUNNERS.get(to_tool, {})
        if from_patterns and to_patterns:
            return re.sub(from_patterns["pattern"], to_patterns["cmd"], cmd)

    elif tool_type == "js_test":
        from_patterns = JS_TEST_RUNNERS.get(from_tool, {})
        to_patterns = JS_TEST_RUNNERS.get(to_tool, {})
        if from_patterns and to_patterns:
            return re.sub(from_patterns["pattern"], to_patterns["cmd"], cmd)

    return None


def check_command_alignment(commands: list, project_context: dict) -> list:
    """Check if commands align with project tooling (bidirectional comparison)."""
    issues = []
    pkg_managers = project_context.get("package_managers", {})
    test_runners = project_context.get("test_runners", {})

    # Detect what the skill uses
    skill_py_pkg = detect_skill_python_pkg_manager(commands)
    skill_js_pkg = detect_skill_js_pkg_manager(commands)
    skill_py_test = detect_skill_python_test_runner(commands)
    skill_js_test = detect_skill_js_test_runner(commands)

    # Compare against project
    project_py_pkg = pkg_managers.get("python")
    project_js_pkg = pkg_managers.get("javascript")
    project_py_test = test_runners.get("python")
    project_js_test = test_runners.get("javascript")

    # Check Python package manager mismatch (bidirectional)
    if skill_py_pkg and project_py_pkg and skill_py_pkg != project_py_pkg:
        for cmd in commands:
            patterns = PYTHON_PKG_MANAGERS.get(skill_py_pkg, {})
            if (re.search(patterns.get("install_pattern", ""), cmd) or
                (skill_py_pkg == "pip" and re.match(r'^python\s+', cmd))):
                fix = generate_command_fix(cmd, skill_py_pkg, project_py_pkg, "python_pkg")
                issues.append({
                    "type": "package_manager",
                    "severity": "minor",
                    "current": cmd,
                    "skill_uses": skill_py_pkg,
                    "project_uses": project_py_pkg,
                    "fix": fix
                })

    # Check JS package manager mismatch (bidirectional)
    if skill_js_pkg and project_js_pkg and skill_js_pkg != project_js_pkg:
        for cmd in commands:
            pattern = JS_PKG_MANAGERS.get(skill_js_pkg, {}).get("pattern", "")
            if pattern and re.search(pattern, cmd):
                fix = generate_command_fix(cmd, skill_js_pkg, project_js_pkg, "js_pkg")
                issues.append({
                    "type": "package_manager",
                    "severity": "minor",
                    "current": cmd,
                    "skill_uses": skill_js_pkg,
                    "project_uses": project_js_pkg,
                    "fix": fix
                })

    # Check Python test runner mismatch (bidirectional)
    if skill_py_test and project_py_test and skill_py_test != project_py_test:
        for cmd in commands:
            pattern = PYTHON_TEST_RUNNERS.get(skill_py_test, {}).get("pattern", "")
            if pattern and re.search(pattern, cmd):
                fix = generate_command_fix(cmd, skill_py_test, project_py_test, "python_test")
                issues.append({
                    "type": "test_runner",
                    "severity": "minor",
                    "current": cmd,
                    "skill_uses": skill_py_test,
                    "project_uses": project_py_test,
                    "fix": fix
                })

    # Check JS test runner mismatch (bidirectional)
    if skill_js_test and project_js_test and skill_js_test != project_js_test:
        for cmd in commands:
            pattern = JS_TEST_RUNNERS.get(skill_js_test, {}).get("pattern", "")
            if pattern and re.search(pattern, cmd):
                fix = generate_command_fix(cmd, skill_js_test, project_js_test, "js_test")
                issues.append({
                    "type": "test_runner",
                    "severity": "minor",
                    "current": cmd,
                    "skill_uses": skill_js_test,
                    "project_uses": project_js_test,
                    "fix": fix
                })

    return issues


def check_path_alignment(paths: list, project_context: dict, project_root: Path) -> list:
    """Check if referenced paths exist in project."""
    issues = []
    structure = project_context.get("directory_structure", {})
    source_dirs = structure.get("source_dirs", [])

    for path in paths:
        # Skip obvious non-path strings
        if path.startswith("http") or path.startswith("@"):
            continue

        full_path = project_root / path
        path_dir = path.split('/')[0] + '/' if '/' in path else path

        # Check if path exists
        if not full_path.exists():
            suggested_fix = None

            # Common path migrations (generic, not assuming any particular structure)
            path_migrations = {
                "backend/": "src/",
                "frontend/": "src/",
                "backend/src/": "src/",
                "src/": "app/",
                "app/": "src/",
                "lib/": "src/",
                "tests/unit/": "tests/",
                "tests/integration/": "tests/",
                "test/": "tests/",
                "__tests__/": "tests/",
            }

            for old, new in path_migrations.items():
                if path.startswith(old):
                    new_path = path.replace(old, new, 1)
                    if (project_root / new_path).exists():
                        suggested_fix = new_path
                        break

            if not suggested_fix:
                # Check if any detected source dir provides a match
                for src_dir in source_dirs:
                    if src_dir != path_dir:
                        potential = path.replace(path_dir, src_dir, 1) if path_dir else src_dir + path
                        if (project_root / potential).exists():
                            suggested_fix = potential
                            break

            issues.append({
                "type": "path",
                "severity": "minor" if suggested_fix else "major",
                "current": path,
                "exists": False,
                "fix": suggested_fix
            })

    return issues


def analyze_skill(skill_path: Path, project_context: dict, project_root: Path) -> dict:
    """Analyze a single skill for update needs."""
    skill_md = skill_path / "SKILL.md"

    if not skill_md.exists():
        return {
            "skill": skill_path.name,
            "status": "invalid",
            "reason": "SKILL.md not found",
            "issues": []
        }

    content = skill_md.read_text()

    # Extract commands and paths
    commands = extract_commands(content)
    paths = extract_paths(content)

    # Check alignment
    command_issues = check_command_alignment(commands, project_context)
    path_issues = check_path_alignment(paths, project_context, project_root)

    all_issues = command_issues + path_issues

    # Categorize by severity
    minor_issues = [i for i in all_issues if i.get("severity") == "minor"]
    major_issues = [i for i in all_issues if i.get("severity") == "major"]

    # Determine status
    if not all_issues:
        status = "up_to_date"
    elif major_issues:
        status = "major_update_needed"
    else:
        status = "minor_update_needed"

    return {
        "skill": skill_path.name,
        "path": str(skill_md),
        "status": status,
        "issues": all_issues,
        "minor_count": len(minor_issues),
        "major_count": len(major_issues),
        "auto_fixable": len([i for i in all_issues if i.get("fix")])
    }


def analyze_all_skills(skills_dir: str, project_context: dict, project_root: str = ".") -> dict:
    """Analyze all skills and return comprehensive report."""
    skills_path = Path(skills_dir)
    root = Path(project_root)

    if not skills_path.exists():
        return {"error": "Skills directory not found", "path": str(skills_path)}

    results = []
    for skill_dir in skills_path.iterdir():
        if skill_dir.is_dir() and not skill_dir.name.startswith('.'):
            result = analyze_skill(skill_dir, project_context, root)
            results.append(result)

    # Categorize results
    up_to_date = [r for r in results if r["status"] == "up_to_date"]
    minor_updates = [r for r in results if r["status"] == "minor_update_needed"]
    major_updates = [r for r in results if r["status"] == "major_update_needed"]
    invalid = [r for r in results if r["status"] == "invalid"]

    return {
        "summary": {
            "total_skills": len(results),
            "up_to_date": len(up_to_date),
            "minor_updates_needed": len(minor_updates),
            "major_updates_needed": len(major_updates),
            "invalid": len(invalid)
        },
        "skills": results,
        "by_status": {
            "up_to_date": [r["skill"] for r in up_to_date],
            "minor_update_needed": [r["skill"] for r in minor_updates],
            "major_update_needed": [r["skill"] for r in major_updates],
            "invalid": [r["skill"] for r in invalid]
        }
    }


if __name__ == "__main__":
    skills_dir = sys.argv[1] if len(sys.argv) > 1 else ".claude/skills"
    project_context_file = sys.argv[2] if len(sys.argv) > 2 else None
    project_root = sys.argv[3] if len(sys.argv) > 3 else "."

    project_context = load_project_context(project_context_file)
    results = analyze_all_skills(skills_dir, project_context, project_root)
    print(json.dumps(results, indent=2))
