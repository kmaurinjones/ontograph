#!/usr/bin/env python3
"""
Analyze current project structure, conventions, and tooling.
Outputs JSON for Claude to use when fine-tuning skills.
"""
import json
import sys
from pathlib import Path


def detect_package_manager(project_root: Path) -> dict:
    """Detect which package managers are in use."""
    managers = {}

    # Python package managers (check lockfiles first for definitive detection)
    if (project_root / "uv.lock").exists():
        managers["python"] = "uv"
    elif (project_root / "poetry.lock").exists():
        managers["python"] = "poetry"
    elif (project_root / "Pipfile.lock").exists():
        managers["python"] = "pipenv"
    elif (project_root / "requirements.txt").exists() or (project_root / "setup.py").exists():
        managers["python"] = "pip"
    elif (project_root / "pyproject.toml").exists():
        # Check pyproject.toml for build system
        content = (project_root / "pyproject.toml").read_text()
        if "[tool.uv]" in content:
            managers["python"] = "uv"
        elif "[tool.poetry]" in content or "poetry-core" in content:
            managers["python"] = "poetry"
        else:
            # pyproject.toml without specific tool config - default to pip
            managers["python"] = "pip"

    # JavaScript package managers
    if (project_root / "bun.lockb").exists():
        managers["javascript"] = "bun"
    elif (project_root / "pnpm-lock.yaml").exists():
        managers["javascript"] = "pnpm"
    elif (project_root / "yarn.lock").exists():
        managers["javascript"] = "yarn"
    elif (project_root / "package-lock.json").exists():
        managers["javascript"] = "npm"
    elif (project_root / "package.json").exists():
        managers["javascript"] = "npm"  # Default

    # Rust
    if (project_root / "Cargo.toml").exists():
        managers["rust"] = "cargo"

    # Go
    if (project_root / "go.mod").exists():
        managers["go"] = "go"

    return managers


def detect_linters(project_root: Path) -> dict:
    """Detect which linters are configured."""
    linters = {}

    # Python linters
    if (project_root / "ruff.toml").exists() or (project_root / ".ruff.toml").exists():
        linters["python"] = "ruff"
    elif (project_root / "pyproject.toml").exists():
        content = (project_root / "pyproject.toml").read_text()
        if "[tool.ruff]" in content:
            linters["python"] = "ruff"
        elif "[tool.flake8]" in content:
            linters["python"] = "flake8"
        elif "[tool.pylint]" in content:
            linters["python"] = "pylint"
    if "python" not in linters and (project_root / ".flake8").exists():
        linters["python"] = "flake8"
    if "python" not in linters and (project_root / ".pylintrc").exists():
        linters["python"] = "pylint"

    # JavaScript/TypeScript linters
    eslint_configs = [
        ".eslintrc", ".eslintrc.js", ".eslintrc.json", ".eslintrc.yml",
        "eslint.config.js", "eslint.config.mjs"
    ]
    biome_configs = ["biome.json", "biome.jsonc"]

    for config in biome_configs:
        if (project_root / config).exists():
            linters["javascript"] = "biome"
            break

    if "javascript" not in linters:
        for config in eslint_configs:
            if (project_root / config).exists():
                linters["javascript"] = "eslint"
                break

    return linters


def detect_test_runners(project_root: Path) -> dict:
    """Detect which test frameworks are in use."""
    runners = {}

    # Python test runners
    if (project_root / "pytest.ini").exists() or (project_root / "conftest.py").exists():
        runners["python"] = "pytest"
    elif (project_root / "pyproject.toml").exists():
        content = (project_root / "pyproject.toml").read_text()
        if "[tool.pytest" in content or "pytest" in content:
            runners["python"] = "pytest"

    # JavaScript test runners
    if (project_root / "vitest.config.ts").exists() or (project_root / "vitest.config.js").exists():
        runners["javascript"] = "vitest"
    elif (project_root / "jest.config.js").exists() or (project_root / "jest.config.ts").exists():
        runners["javascript"] = "jest"
    elif (project_root / "package.json").exists():
        content = (project_root / "package.json").read_text()
        if "vitest" in content:
            runners["javascript"] = "vitest"
        elif "jest" in content:
            runners["javascript"] = "jest"
        elif "mocha" in content:
            runners["javascript"] = "mocha"

    return runners


def detect_directory_structure(project_root: Path) -> dict:
    """Detect key directories in the project."""
    structure = {
        "source_dirs": [],
        "test_dirs": [],
        "config_dirs": [],
        "docs_dirs": []
    }

    # Common source directories
    source_candidates = ["src", "app", "lib", "backend", "frontend", "api", "core", "pkg"]
    for candidate in source_candidates:
        path = project_root / candidate
        if path.exists() and path.is_dir():
            structure["source_dirs"].append(candidate + "/")

    # Common test directories
    test_candidates = ["tests", "test", "__tests__", "spec", "specs"]
    for candidate in test_candidates:
        path = project_root / candidate
        if path.exists() and path.is_dir():
            structure["test_dirs"].append(candidate + "/")

    # Config directories
    config_candidates = ["config", "configs", ".config", "settings"]
    for candidate in config_candidates:
        path = project_root / candidate
        if path.exists() and path.is_dir():
            structure["config_dirs"].append(candidate + "/")

    # Docs directories
    docs_candidates = ["docs", "doc", "documentation"]
    for candidate in docs_candidates:
        path = project_root / candidate
        if path.exists() and path.is_dir():
            structure["docs_dirs"].append(candidate + "/")

    return structure


def detect_languages(project_root: Path) -> list:
    """Detect primary languages used in the project."""
    languages = []

    if (project_root / "pyproject.toml").exists() or (project_root / "setup.py").exists():
        languages.append("python")
    if (project_root / "package.json").exists():
        # Check if TypeScript
        if (project_root / "tsconfig.json").exists():
            languages.append("typescript")
        languages.append("javascript")
    if (project_root / "Cargo.toml").exists():
        languages.append("rust")
    if (project_root / "go.mod").exists():
        languages.append("go")

    return languages


def sample_naming_conventions(_project_root: Path, languages: list) -> dict:
    """Sample code files to detect naming conventions.

    Note: Currently returns standard conventions per language.
    _project_root reserved for future dynamic sampling from actual code files.
    """
    conventions = {}

    if "python" in languages:
        # Python uses snake_case by convention
        conventions["python"] = {
            "functions": "snake_case",
            "classes": "PascalCase",
            "variables": "snake_case",
            "constants": "UPPER_SNAKE_CASE"
        }

    if "typescript" in languages or "javascript" in languages:
        conventions["javascript"] = {
            "functions": "camelCase",
            "classes": "PascalCase",
            "variables": "camelCase",
            "constants": "UPPER_SNAKE_CASE",
            "components": "PascalCase"
        }

    if "rust" in languages:
        conventions["rust"] = {
            "functions": "snake_case",
            "structs": "PascalCase",
            "variables": "snake_case",
            "constants": "UPPER_SNAKE_CASE"
        }

    if "go" in languages:
        conventions["go"] = {
            "functions": "camelCase",  # or PascalCase for exported
            "structs": "PascalCase",
            "variables": "camelCase",
            "constants": "PascalCase"
        }

    return conventions


def analyze_project(project_root: str = ".") -> dict:
    """Analyze the project and return comprehensive context."""
    root = Path(project_root).resolve()

    languages = detect_languages(root)

    return {
        "project_root": str(root),
        "languages": languages,
        "package_managers": detect_package_manager(root),
        "linters": detect_linters(root),
        "test_runners": detect_test_runners(root),
        "directory_structure": detect_directory_structure(root),
        "naming_conventions": sample_naming_conventions(root, languages)
    }


if __name__ == "__main__":
    project_root = sys.argv[1] if len(sys.argv) > 1 else "."
    result = analyze_project(project_root)
    print(json.dumps(result, indent=2))
