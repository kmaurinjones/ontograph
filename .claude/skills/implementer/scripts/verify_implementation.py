#!/usr/bin/env python3
"""
Verify implementation quality by checking for common issues.
Run after making changes to ensure nothing was missed.
"""
import json
import re
import subprocess
from pathlib import Path


def get_modified_files():
    """Get files modified in current working state."""
    try:
        result = subprocess.run(
            ["git", "diff", "--name-only", "HEAD"],
            capture_output=True,
            text=True
        )
        return [f for f in result.stdout.strip().split("\n") if f]
    except Exception:
        return []


def check_for_todos(files):
    """Check for TODO/FIXME comments that might indicate incomplete work."""
    issues = []

    for file in files:
        path = Path(file)
        if not path.exists():
            continue

        try:
            content = path.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                if re.search(r'\b(TODO|FIXME|HACK|XXX)\b', line, re.IGNORECASE):
                    issues.append({
                        "file": file,
                        "line": i,
                        "type": "todo",
                        "content": line.strip()[:100]
                    })
        except Exception:
            pass

    return issues


def check_for_debug_code(files):
    """Check for debug code that should be removed."""
    issues = []
    debug_patterns = [
        (r'console\.log\(', "console.log statement"),
        (r'print\([^)]*\)(?!\s*#)', "print statement"),
        (r'debugger\b', "debugger statement"),
        (r'import pdb', "pdb import"),
        (r'pdb\.set_trace', "pdb breakpoint"),
        (r'breakpoint\(\)', "breakpoint()"),
    ]

    for file in files:
        path = Path(file)
        if not path.exists():
            continue

        try:
            content = path.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                for pattern, desc in debug_patterns:
                    if re.search(pattern, line):
                        issues.append({
                            "file": file,
                            "line": i,
                            "type": "debug_code",
                            "description": desc,
                            "content": line.strip()[:100]
                        })
        except Exception:
            pass

    return issues


def check_for_commented_code(files):
    """Check for large blocks of commented-out code."""
    issues = []

    for file in files:
        path = Path(file)
        if not path.exists() or path.suffix not in [".py", ".ts", ".tsx", ".js"]:
            continue

        try:
            content = path.read_text()
            lines = content.split("\n")

            # Look for consecutive comment lines that look like code
            comment_block_start = None
            comment_block_count = 0

            for i, line in enumerate(lines, 1):
                stripped = line.strip()

                # Check if line is a comment that looks like code
                is_code_comment = False
                if path.suffix == ".py":
                    if stripped.startswith("#") and re.search(r'[=\(\)\[\]{}:]', stripped):
                        is_code_comment = True
                else:
                    if stripped.startswith("//") and re.search(r'[=\(\)\[\]{}:;]', stripped):
                        is_code_comment = True

                if is_code_comment:
                    if comment_block_start is None:
                        comment_block_start = i
                    comment_block_count += 1
                else:
                    if comment_block_count >= 5:
                        issues.append({
                            "file": file,
                            "line": comment_block_start,
                            "type": "commented_code",
                            "description": f"{comment_block_count} lines of commented code"
                        })
                    comment_block_start = None
                    comment_block_count = 0

        except Exception:
            pass

    return issues


def check_for_hardcoded_values(files):
    """Check for potentially problematic hardcoded values."""
    issues = []
    suspicious_patterns = [
        (r'localhost:\d+', "hardcoded localhost URL"),
        (r'127\.0\.0\.1:\d+', "hardcoded localhost IP"),
        (r'"http://[^"]+:\d+', "hardcoded HTTP URL with port"),
        (r'password\s*=\s*["\'][^"\']+["\']', "hardcoded password"),
        (r'api_key\s*=\s*["\'][^"\']+["\']', "hardcoded API key"),
        (r'secret\s*=\s*["\'][^"\']+["\']', "hardcoded secret"),
    ]

    for file in files:
        path = Path(file)
        if not path.exists():
            continue

        # Skip test files
        if "test" in file.lower():
            continue

        try:
            content = path.read_text()
            lines = content.split("\n")

            for i, line in enumerate(lines, 1):
                for pattern, desc in suspicious_patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        issues.append({
                            "file": file,
                            "line": i,
                            "type": "hardcoded_value",
                            "description": desc
                        })
        except Exception:
            pass

    return issues


def check_test_coverage(files):
    """Check if modified implementation files have corresponding tests."""
    untested = []

    for file in files:
        path = Path(file)

        # Skip test files themselves
        if "test" in file.lower():
            continue

        # Skip non-code files
        if path.suffix not in [".py", ".ts", ".tsx", ".js", ".jsx"]:
            continue

        # Skip config files
        if any(x in file for x in ["config", "settings", "__init__", "migrations"]):
            continue

        # Check for corresponding test file
        has_test = False

        if path.suffix == ".py" and "backend" in file:
            test_path = Path("backend/tests") / f"test_{path.stem}.py"
            has_test = test_path.exists()

        elif path.suffix in [".tsx", ".ts"]:
            test_path1 = path.parent / f"{path.stem}.test{path.suffix}"
            test_path2 = Path("frontend/__tests__") / f"{path.stem}.test{path.suffix}"
            has_test = test_path1.exists() or test_path2.exists()

        if not has_test:
            untested.append({
                "file": file,
                "type": "missing_test"
            })

    return untested


def verify_implementation():
    """Run all verification checks."""
    modified_files = get_modified_files()

    if not modified_files:
        return {
            "status": "no_changes",
            "message": "No modified files detected"
        }

    todos = check_for_todos(modified_files)
    debug_code = check_for_debug_code(modified_files)
    commented_code = check_for_commented_code(modified_files)
    hardcoded = check_for_hardcoded_values(modified_files)
    untested = check_test_coverage(modified_files)

    all_issues = todos + debug_code + commented_code + hardcoded

    return {
        "status": "checked",
        "modified_files": modified_files,
        "file_count": len(modified_files),
        "issues": {
            "todos": todos,
            "debug_code": debug_code,
            "commented_code": commented_code,
            "hardcoded_values": hardcoded,
            "missing_tests": untested
        },
        "summary": {
            "total_issues": len(all_issues),
            "todos_found": len(todos),
            "debug_code_found": len(debug_code),
            "commented_code_blocks": len(commented_code),
            "hardcoded_values_found": len(hardcoded),
            "files_without_tests": len(untested)
        },
        "clean": len(all_issues) == 0
    }


if __name__ == "__main__":
    result = verify_implementation()
    print(json.dumps(result, indent=2))
