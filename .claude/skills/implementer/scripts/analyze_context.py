#!/usr/bin/env python3
"""
Analyze codebase context for a given change description.
Finds relevant files, patterns, and existing utilities.
"""
import json
import re
import subprocess
import sys
from pathlib import Path


def search_codebase(query, file_types=None):
    """Search codebase for relevant files using ripgrep."""
    args = ["rg", "-l", "-i", query]

    if file_types:
        for ft in file_types:
            args.extend(["--type", ft])

    try:
        result = subprocess.run(args, capture_output=True, text=True)
        return result.stdout.strip().split("\n") if result.stdout.strip() else []
    except FileNotFoundError:
        return []


def find_related_files(keywords):
    """Find files related to given keywords."""
    related = set()

    for keyword in keywords:
        # Search in Python files
        py_files = search_codebase(keyword, ["py"])
        related.update(py_files)

        # Search in TypeScript files
        ts_files = search_codebase(keyword, ["ts"])
        related.update(ts_files)

    return sorted([f for f in related if f])


def extract_keywords(description):
    """Extract meaningful keywords from description."""
    # Remove common words
    stop_words = {
        "the", "a", "an", "to", "for", "in", "on", "of", "and", "or", "is",
        "it", "this", "that", "with", "be", "as", "at", "by", "from",
        "add", "update", "change", "modify", "implement", "create", "make",
        "new", "should", "would", "could", "need", "want"
    }

    # Extract words
    words = re.findall(r'\b[a-zA-Z_][a-zA-Z0-9_]*\b', description.lower())

    # Filter and return meaningful keywords
    keywords = [w for w in words if w not in stop_words and len(w) > 2]

    return list(set(keywords))


def find_existing_utilities(keywords):
    """Find existing utilities that might be reusable."""
    utils = []

    # Check common utility locations
    util_paths = [
        "backend/app/utils",
        "backend/app/core",
        "frontend/src/lib",
        "frontend/src/hooks",
        "frontend/src/utils"
    ]

    for util_path in util_paths:
        path = Path(util_path)
        if path.exists():
            for file in path.rglob("*.py"):
                utils.append({"path": str(file), "type": "python"})
            for file in path.rglob("*.ts"):
                utils.append({"path": str(file), "type": "typescript"})

    return utils


def find_test_files(files):
    """Find test files corresponding to implementation files."""
    test_mapping = []

    for f in files:
        f_path = Path(f)

        if f_path.suffix == ".py" and "backend" in f:
            # Python: backend/app/X.py -> backend/tests/test_X.py
            test_name = f"test_{f_path.stem}.py"
            test_path = Path("backend/tests") / test_name
            test_mapping.append({
                "impl": f,
                "test": str(test_path),
                "test_exists": test_path.exists()
            })

        elif f_path.suffix in [".tsx", ".ts"] and "frontend" in f:
            # TypeScript: X.tsx -> X.test.tsx
            test_name = f"{f_path.stem}.test{f_path.suffix}"
            test_path = f_path.parent / test_name
            alt_test_path = Path("frontend/__tests__") / f_path.relative_to("frontend/src").parent / test_name

            test_mapping.append({
                "impl": f,
                "test": str(test_path),
                "alt_test": str(alt_test_path),
                "test_exists": test_path.exists() or alt_test_path.exists()
            })

    return test_mapping


def analyze_context(description):
    """Main analysis function."""
    keywords = extract_keywords(description)

    # Find related files
    related_files = find_related_files(keywords)

    # Categorize files
    backend_files = [f for f in related_files if f.startswith("backend/")]
    frontend_files = [f for f in related_files if f.startswith("frontend/")]

    # Find utilities
    utilities = find_existing_utilities(keywords)

    # Find test files
    test_mapping = find_test_files(related_files[:10])  # Limit to top 10

    # Determine likely scope
    scope = []
    if backend_files:
        scope.append("backend")
    if frontend_files:
        scope.append("frontend")

    return {
        "description": description,
        "extracted_keywords": keywords,
        "scope": scope,
        "related_files": {
            "backend": backend_files[:15],
            "frontend": frontend_files[:15],
            "total_found": len(related_files)
        },
        "existing_utilities": utilities[:10],
        "test_coverage": test_mapping,
        "recommendations": generate_recommendations(backend_files, frontend_files, test_mapping)
    }


def generate_recommendations(backend_files, frontend_files, test_mapping):
    """Generate implementation recommendations."""
    recs = []

    if backend_files and frontend_files:
        recs.append("Change spans backend and frontend - consider API contract first")

    if backend_files:
        recs.append("Backend changes detected - ensure API schema stays consistent")

    if frontend_files:
        recs.append("Frontend changes detected - check component reusability")

    untested = [t for t in test_mapping if not t.get("test_exists")]
    if untested:
        recs.append(f"{len(untested)} related files lack test coverage - consider adding tests")

    return recs


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(json.dumps({"error": "No description provided"}))
        sys.exit(1)

    description = " ".join(sys.argv[1:])
    result = analyze_context(description)
    print(json.dumps(result, indent=2))
