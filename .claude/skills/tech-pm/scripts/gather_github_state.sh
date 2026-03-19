#!/usr/bin/env bash
# gather_github_state.sh — Collects GitHub project state as JSON via gh CLI
# Outputs: JSON object with issues, milestones, PRs, project boards, labels, activity
set -euo pipefail

# Check gh CLI is available
if ! command -v gh &>/dev/null; then
    echo '{"error": "gh_not_installed", "message": "GitHub CLI (gh) is not installed. Install with: brew install gh"}'
    exit 0
fi

# Check authentication
if ! gh auth status &>/dev/null 2>&1; then
    echo '{"error": "gh_not_authenticated", "message": "GitHub CLI is not authenticated. Run: gh auth login"}'
    exit 0
fi

# Detect repo — try git remote first, fall back to args
REPO=""
if git remote get-url origin &>/dev/null 2>&1; then
    REMOTE_URL=$(git remote get-url origin)
    # Extract owner/repo from SSH or HTTPS URL
    REPO=$(echo "$REMOTE_URL" | sed -E 's#.*[:/]([^/]+/[^/.]+)(\.git)?$#\1#')
fi

if [ -z "$REPO" ]; then
    echo '{"error": "no_remote", "message": "No git remote found. Set up remote with: gh repo create"}'
    exit 0
fi

# Gather all data in parallel using subshells
TMPDIR_WORK=$(mktemp -d)
trap "rm -rf $TMPDIR_WORK" EXIT

# Issues (open, sorted by updated)
gh issue list --repo "$REPO" --state open --limit 50 --json number,title,labels,milestone,assignees,createdAt,updatedAt,state,url 2>/dev/null > "$TMPDIR_WORK/issues_open.json" &

# Issues (recently closed, last 10)
gh issue list --repo "$REPO" --state closed --limit 10 --json number,title,labels,milestone,closedAt,url 2>/dev/null > "$TMPDIR_WORK/issues_closed.json" &

# Pull requests (open)
gh pr list --repo "$REPO" --state open --limit 20 --json number,title,labels,milestone,author,createdAt,updatedAt,state,url,isDraft,reviewDecision 2>/dev/null > "$TMPDIR_WORK/prs_open.json" &

# Pull requests (recently merged, last 10)
gh pr list --repo "$REPO" --state merged --limit 10 --json number,title,mergedAt,url 2>/dev/null > "$TMPDIR_WORK/prs_merged.json" &

# Milestones
gh api "repos/$REPO/milestones?state=all&sort=due_on&direction=asc" 2>/dev/null > "$TMPDIR_WORK/milestones.json" &

# Labels
gh label list --repo "$REPO" --limit 100 --json name,description,color 2>/dev/null > "$TMPDIR_WORK/labels.json" &

# Repo metadata
gh repo view "$REPO" --json name,description,defaultBranchRef,isPrivate,url,stargazerCount,forkCount 2>/dev/null > "$TMPDIR_WORK/repo.json" &

# Wait for all background jobs
wait

# GitHub Projects (v2) — these require separate API calls
# List projects linked to this repo
PROJECTS_JSON="[]"
OWNER=$(echo "$REPO" | cut -d'/' -f1)
PROJECTS_RAW=$(gh project list --owner "$OWNER" --format json 2>/dev/null || echo '{"projects":[]}')
PROJECTS_JSON=$(echo "$PROJECTS_RAW" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    projects = data.get('projects', [])
    print(json.dumps(projects))
except:
    print('[]')
" 2>/dev/null || echo "[]")

# For each project, try to get items (limited to first project found)
PROJECT_ITEMS="[]"
FIRST_PROJECT_NUMBER=$(echo "$PROJECTS_JSON" | python3 -c "
import json, sys
try:
    projects = json.load(sys.stdin)
    if projects:
        print(projects[0].get('number', ''))
    else:
        print('')
except:
    print('')
" 2>/dev/null || echo "")

if [ -n "$FIRST_PROJECT_NUMBER" ]; then
    PROJECT_ITEMS_RAW=$(gh project item-list "$FIRST_PROJECT_NUMBER" --owner "$OWNER" --format json --limit 100 2>/dev/null || echo '{"items":[]}')
    PROJECT_ITEMS=$(echo "$PROJECT_ITEMS_RAW" | python3 -c "
import json, sys
try:
    data = json.load(sys.stdin)
    items = data.get('items', [])
    print(json.dumps(items))
except:
    print('[]')
" 2>/dev/null || echo "[]")
fi

# Assemble final JSON
python3 -c "
import json, sys, os

def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return []

tmpdir = '$TMPDIR_WORK'
repo = '$REPO'

result = {
    'repo': repo,
    'repo_metadata': load_json(os.path.join(tmpdir, 'repo.json')),
    'issues_open': load_json(os.path.join(tmpdir, 'issues_open.json')),
    'issues_recently_closed': load_json(os.path.join(tmpdir, 'issues_closed.json')),
    'prs_open': load_json(os.path.join(tmpdir, 'prs_open.json')),
    'prs_recently_merged': load_json(os.path.join(tmpdir, 'prs_merged.json')),
    'milestones': load_json(os.path.join(tmpdir, 'milestones.json')),
    'labels': load_json(os.path.join(tmpdir, 'labels.json')),
    'projects': json.loads('''$(echo "$PROJECTS_JSON" | sed "s/'/\\\\'/g")'''),
    'project_items': json.loads('''$(echo "$PROJECT_ITEMS" | sed "s/'/\\\\'/g")'''),
    'counts': {
        'open_issues': len(load_json(os.path.join(tmpdir, 'issues_open.json'))),
        'open_prs': len(load_json(os.path.join(tmpdir, 'prs_open.json'))),
        'milestones': len(load_json(os.path.join(tmpdir, 'milestones.json'))),
        'projects': len(json.loads('''$(echo "$PROJECTS_JSON" | sed "s/'/\\\\'/g")''')),
    }
}

print(json.dumps(result, indent=2))
"
