#!/usr/bin/env python3
"""
Detect what linters are configured in the project.
Returns configuration details and commands to run them.
"""
import json
from pathlib import Path


def detect_python_linter():
    """Detect Python linting configuration."""
    result = {
        "language": "python",
        "linter": None,
        "config_file": None,
        "command": None
    }

    # Check for Ruff
    pyproject = Path("pyproject.toml")
    if pyproject.exists():
        content = pyproject.read_text()
        if "[tool.ruff]" in content:
            result["linter"] = "ruff"
            result["config_file"] = "pyproject.toml"
            result["command"] = "uv run ruff check {path} --fix && uv run ruff format {path}"
            return result

    # Check for ruff.toml
    if Path("ruff.toml").exists():
        result["linter"] = "ruff"
        result["config_file"] = "ruff.toml"
        result["command"] = "uv run ruff check {path} --fix && uv run ruff format {path}"
        return result

    # Check for Black
    if pyproject.exists():
        content = pyproject.read_text()
        if "[tool.black]" in content:
            result["linter"] = "black"
            result["config_file"] = "pyproject.toml"
            result["command"] = "uv run black {path}"
            return result

    # Check for flake8
    if Path(".flake8").exists() or Path("setup.cfg").exists():
        result["linter"] = "flake8"
        result["config_file"] = ".flake8 or setup.cfg"
        result["command"] = "uv run flake8 {path}"
        return result

    return result


def detect_javascript_linter():
    """Detect JavaScript/TypeScript linting configuration."""
    result = {
        "language": "javascript/typescript",
        "linter": None,
        "config_file": None,
        "command": None
    }

    frontend_dir = Path("frontend")

    # Check for ESLint
    eslint_configs = [
        frontend_dir / ".eslintrc.json",
        frontend_dir / ".eslintrc.js",
        frontend_dir / ".eslintrc.cjs",
        frontend_dir / "eslint.config.js",
        frontend_dir / "eslint.config.mjs"
    ]

    for config in eslint_configs:
        if config.exists():
            result["linter"] = "eslint"
            result["config_file"] = str(config)
            result["command"] = "cd frontend && npm run lint -- --fix"
            return result

    # Check package.json for eslint
    package_json = frontend_dir / "package.json"
    if package_json.exists():
        content = package_json.read_text()
        if "eslint" in content:
            result["linter"] = "eslint"
            result["config_file"] = "frontend/package.json (inferred)"
            result["command"] = "cd frontend && npm run lint -- --fix"
            return result

    return result


def detect_all_linters():
    """Detect all configured linters."""
    python = detect_python_linter()
    javascript = detect_javascript_linter()

    return {
        "detected_linters": [
            l for l in [python, javascript] if l["linter"]
        ],
        "python": python,
        "javascript": javascript,
        "summary": {
            "python_linter": python["linter"],
            "js_linter": javascript["linter"]
        }
    }


if __name__ == "__main__":
    result = detect_all_linters()
    print(json.dumps(result, indent=2))
