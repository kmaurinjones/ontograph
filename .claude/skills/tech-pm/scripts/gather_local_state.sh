#!/usr/bin/env bash
# gather_local_state.sh — Collects local git repo state as JSON
# Outputs: JSON object with branch, changes, recent commits, stash, ahead/behind
set -euo pipefail

# Check if we're in a git repo
if ! git rev-parse --is-inside-work-tree &>/dev/null; then
    echo '{"error": "not_a_git_repo", "message": "Current directory is not a git repository. Initialize with: git init && gh repo create"}'
    exit 0
fi

# Current branch
BRANCH=$(git branch --show-current 2>/dev/null || echo "detached")

# Uncommitted changes (staged + unstaged + untracked)
STAGED=$(git diff --cached --stat 2>/dev/null | tail -1 || echo "")
UNSTAGED=$(git diff --stat 2>/dev/null | tail -1 || echo "")
UNTRACKED_COUNT=$(git ls-files --others --exclude-standard 2>/dev/null | wc -l | tr -d ' ')

# Detailed file-level changes
STAGED_FILES=$(git diff --cached --name-status 2>/dev/null | head -30 || echo "")
UNSTAGED_FILES=$(git diff --name-status 2>/dev/null | head -30 || echo "")
UNTRACKED_FILES=$(git ls-files --others --exclude-standard 2>/dev/null | head -30 || echo "")

# Recent commits (last 15)
RECENT_COMMITS=$(git log --oneline --no-decorate -15 2>/dev/null || echo "")

# Stash list
STASH_LIST=$(git stash list 2>/dev/null || echo "")
STASH_COUNT=$(echo "$STASH_LIST" | grep -c "stash@" 2>/dev/null || echo "0")

# Ahead/behind remote
AHEAD_BEHIND=""
TRACKING=$(git rev-parse --abbrev-ref --symbolic-full-name @{u} 2>/dev/null || echo "")
if [ -n "$TRACKING" ]; then
    AHEAD=$(git rev-list --count @{u}..HEAD 2>/dev/null || echo "0")
    BEHIND=$(git rev-list --count HEAD..@{u} 2>/dev/null || echo "0")
    AHEAD_BEHIND="${AHEAD} ahead, ${BEHIND} behind ${TRACKING}"
else
    AHEAD_BEHIND="no upstream tracking branch"
fi

# Total commit count
TOTAL_COMMITS=$(git rev-list --count HEAD 2>/dev/null || echo "0")

# Last commit timestamp
LAST_COMMIT_DATE=$(git log -1 --format="%ci" 2>/dev/null || echo "no commits")

# Active branches (local)
LOCAL_BRANCHES=$(git branch --format='%(refname:short)' 2>/dev/null | head -20 || echo "")

# Tags
RECENT_TAGS=$(git tag --sort=-creatordate 2>/dev/null | head -5 || echo "")

# Build JSON output using heredoc + jq-free approach (portable)
python3 -c "
import json, sys

data = {
    'branch': '''$BRANCH''',
    'tracking': '''$AHEAD_BEHIND''',
    'total_commits': int('''$TOTAL_COMMITS''' or '0'),
    'last_commit_date': '''$LAST_COMMIT_DATE''',
    'staged_summary': '''$STAGED'''.strip(),
    'unstaged_summary': '''$UNSTAGED'''.strip(),
    'untracked_count': int('''$UNTRACKED_COUNT''' or '0'),
    'staged_files': [l for l in '''$STAGED_FILES'''.strip().splitlines() if l],
    'unstaged_files': [l for l in '''$UNSTAGED_FILES'''.strip().splitlines() if l],
    'untracked_files': [l for l in '''$UNTRACKED_FILES'''.strip().splitlines() if l],
    'recent_commits': [l for l in '''$RECENT_COMMITS'''.strip().splitlines() if l],
    'stash_count': int('''$STASH_COUNT''' or '0'),
    'stash_entries': [l for l in '''$STASH_LIST'''.strip().splitlines() if l],
    'local_branches': [l for l in '''$LOCAL_BRANCHES'''.strip().splitlines() if l],
    'recent_tags': [l for l in '''$RECENT_TAGS'''.strip().splitlines() if l],
}
print(json.dumps(data, indent=2))
"
