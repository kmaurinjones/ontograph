#!/usr/bin/env python3
"""
Validate hook scripts and configuration.
Outputs JSON for Claude to parse.
"""
import json
import stat
import sys
from pathlib import Path


def check_hook_script(hook_path):
    """Validate a single hook script."""
    hook = Path(hook_path)

    if not hook.exists():
        return {"error": "Hook file not found", "path": str(hook)}

    issues = []
    info = {
        "name": hook.name,
        "path": str(hook),
        "exists": True,
        "issues": issues
    }

    # Check if executable
    st = hook.stat()
    is_executable = bool(st.st_mode & stat.S_IXUSR)
    info["executable"] = is_executable

    if not is_executable:
        issues.append("Not executable (need chmod +x)")

    # Check shebang
    try:
        first_line = hook.read_text().split('\n')[0]
        info["has_shebang"] = first_line.startswith("#!")
        info["shebang"] = first_line if info["has_shebang"] else None

        if not info["has_shebang"]:
            issues.append("Missing shebang line")
    except Exception as e:
        issues.append(f"Could not read file: {e}")

    # Check for proper exit codes
    content = hook.read_text() if hook.exists() else ""
    has_exit_0 = "exit 0" in content
    has_exit_2 = "exit 2" in content

    info["has_exit_codes"] = has_exit_0 or has_exit_2

    if not info["has_exit_codes"]:
        issues.append("Missing proper exit codes (should have 'exit 0' or 'exit 2')")

    return info


def validate_hooks_config(settings_path=".claude/settings.json"):
    """Validate hooks configuration in settings.json."""
    settings = Path(settings_path)

    if not settings.exists():
        return {"error": "settings.json not found", "path": str(settings)}

    try:
        config = json.loads(settings.read_text())
    except json.JSONDecodeError as e:
        return {"error": f"Invalid JSON: {e}"}

    hooks_config = config.get("hooks", {})
    issues = []

    # Check for PreToolUse and PostToolUse
    pre_hooks = hooks_config.get("PreToolUse", [])
    post_hooks = hooks_config.get("PostToolUse", [])

    result = {
        "has_hooks": bool(hooks_config),
        "pre_hook_count": len(pre_hooks),
        "post_hook_count": len(post_hooks),
        "registered_hooks": [],
        "issues": issues
    }

    # Validate each registered hook
    for hook_type, hook_list in [("PreToolUse", pre_hooks), ("PostToolUse", post_hooks)]:
        for hook_entry in hook_list:
            matcher = hook_entry.get("matcher", "")
            hooks = hook_entry.get("hooks", [])

            for hook in hooks:
                command = hook.get("command", "")
                # Extract script path from command
                script_path = command.split()[0] if command else ""

                result["registered_hooks"].append({
                    "type": hook_type,
                    "matcher": matcher,
                    "script": script_path,
                    "command": command
                })

                # Check if script exists
                if script_path and not Path(script_path).exists():
                    issues.append(f"Hook script not found: {script_path}")

    return result


def validate_all_hooks(hooks_dir=".claude/hooks", settings_path=".claude/settings.json"):
    """Validate all hooks."""
    hooks_path = Path(hooks_dir)

    # Validate config first
    config_result = validate_hooks_config(settings_path)

    # Scan hook scripts
    hook_scripts = []
    if hooks_path.exists():
        for hook_file in hooks_path.glob("*.sh"):
            hook_info = check_hook_script(hook_file)
            hook_scripts.append(hook_info)

    return {
        "config": config_result,
        "hook_scripts": hook_scripts,
        "total_scripts": len(hook_scripts),
        "total_issues": sum(len(h.get("issues", [])) for h in hook_scripts) + len(config_result.get("issues", []))
    }


if __name__ == "__main__":
    hooks_dir = sys.argv[1] if len(sys.argv) > 1 else ".claude/hooks"
    settings_path = sys.argv[2] if len(sys.argv) > 2 else ".claude/settings.json"

    results = validate_all_hooks(hooks_dir, settings_path)
    print(json.dumps(results, indent=2))
