#!/usr/bin/env python3
"""
Find recent git commits and changed files.
Useful for identifying potential sources of bugs.
"""
import json
import subprocess
import sys


def run_git_command(args):
    """Run a git command and return output."""
    try:
        result = subprocess.run(
            ["git"] + args,
            capture_output=True,
            text=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"


def get_recent_commits(limit=10):
    """Get recent commits with metadata."""
    # Get commit info: hash, author, date, message
    log_output = run_git_command([
        "log",
        f"-{limit}",
        "--format=%H|%an|%ai|%s"
    ])

    commits = []
    for line in log_output.split("\n"):
        if "|" in line:
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                })

    return commits


def get_files_changed_in_commit(commit_hash):
    """Get files changed in a specific commit."""
    output = run_git_command(["show", "--name-only", "--format=", commit_hash])
    return [f for f in output.split("\n") if f.strip()]


def get_recent_changes(limit=10, include_files=False):
    """Get recent changes with optional file details."""
    commits = get_recent_commits(limit)

    if include_files:
        for commit in commits:
            commit["files"] = get_files_changed_in_commit(commit["hash"])

    # Get overall stats
    diff_stat = run_git_command(["diff", "--stat", f"HEAD~{limit}..HEAD"])

    return {
        "commits": commits,
        "total_commits": len(commits),
        "diff_summary": diff_stat.split("\n")[-1] if diff_stat else "No changes"
    }


def find_commits_touching_file(filepath, limit=5):
    """Find recent commits that modified a specific file."""
    log_output = run_git_command([
        "log",
        f"-{limit}",
        "--format=%H|%an|%ai|%s",
        "--",
        filepath
    ])

    commits = []
    for line in log_output.split("\n"):
        if "|" in line:
            parts = line.split("|")
            if len(parts) >= 4:
                commits.append({
                    "hash": parts[0][:8],
                    "author": parts[1],
                    "date": parts[2],
                    "message": parts[3]
                })

    return {
        "file": filepath,
        "commits": commits,
        "total": len(commits)
    }


if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "--file":
        # Find commits for specific file
        if len(sys.argv) > 2:
            result = find_commits_touching_file(sys.argv[2])
        else:
            result = {"error": "No file specified"}
    else:
        # Get recent changes
        limit = int(sys.argv[1]) if len(sys.argv) > 1 else 10
        include_files = "--files" in sys.argv
        result = get_recent_changes(limit, include_files)

    print(json.dumps(result, indent=2))
