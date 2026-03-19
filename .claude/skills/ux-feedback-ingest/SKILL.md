---
name: ux-feedback-ingest
description: Ingest UX feedback from GitHub issues labeled AGENT-FEEDBACK, deduplicate findings, prioritize by impact, and produce an actionable backlog. Use when user says ingest ux feedback, process ux issues, triage ux feedback, or review ux test results.
---

# UX Feedback Ingest Skill

Pulls all `AGENT-FEEDBACK` issues from the current project's GitHub repo, deduplicates and clusters findings across sessions, scores by impact, and produces a prioritized backlog of UX improvements.

---

## Execution

### Step 1: Detect repo context

Get the GitHub remote:
```bash
git remote -v
```
Extract `owner/repo`. If no remote exists, check for local reports in `ux-testing/reports/` instead and process those.

### Step 2: Fetch all UX feedback issues

```bash
gh issue list \
  --repo <owner/repo> \
  --label "AGENT-FEEDBACK" \
  --state all \
  --json number,title,body,state,createdAt,closedAt \
  --limit 100
```

If no issues exist (and no local reports), tell the user and suggest running `/ux-tester` first.

For local reports (no GitHub remote):
```bash
ls ux-testing/reports/*.md
```
Read each file and process identically.

### Step 3: Parse and extract findings

For each issue/report, extract structured data from the report sections:

| Section | Extract |
|---|---|
| Task Outcome | Pass/partial/blocked + what was missing |
| Friction Log | Each friction point as a discrete finding |
| Bugs & Errors | Each bug as a discrete finding with error message |
| Missing Features | Each missing affordance as a discrete finding |
| What Worked Well | Each positive as a discrete finding (for "keep" list) |
| Trust & Confidence | Trust blockers as discrete findings |
| Value Perception | Pricing/value gaps as discrete findings |
| Top 5 Recommendations | Each recommendation as a discrete finding |

Tag each finding with:
- **source_issue**: GitHub issue number (or local filename)
- **category**: `bug` | `friction` | `missing-feature` | `trust` | `value` | `positive`
- **severity**: `critical` (blocks task completion) | `major` (significant degradation) | `minor` (annoyance) | `cosmetic`
- **ui_location**: which page/component/flow is affected

### Step 4: Deduplicate and cluster

Group findings that describe the same underlying issue:

1. **Exact duplicates**: Same UI element + same problem = merge, increment `seen_count`.
2. **Related findings**: Same UI area + related problems = cluster under a theme.
3. **Contradictions**: One session says something works well, another says it's broken = flag for manual review.

### Step 5: Score and prioritize

| Factor | Weight | Scale |
|---|---|---|
| Severity | 40% | critical=4, major=3, minor=2, cosmetic=1 |
| Frequency | 30% | seen_count / total_sessions |
| User journey position | 20% | early_funnel=4 (landing, signup, first action), mid_funnel=3 (core features), late_funnel=2 (sharing, export, settings), edge_case=1 |
| Fix complexity estimate | 10% | trivial=4 (copy change), small=3 (component tweak), medium=2 (new feature), large=1 (architecture change) |

**Priority score** = weighted sum. Rank descending.

### Step 6: Generate the backlog

Write output to `ux-testing/ux-backlog.md`:

```markdown
# UX Feedback Backlog

Generated: YYYY-MM-DD
Sources: N issues (M open, K closed)
Total findings: X (Y unique after dedup)

## Critical / Blocking

| # | Finding | Category | UI Location | Seen | Score | Source Issues |
|---|---------|----------|-------------|------|-------|---------------|
| 1 | ... | bug | ... | 3/5 | 9.2 | #1, #4, #7 |

## High Priority

(same table format)

## Medium Priority

(same table format)

## Low Priority / Cosmetic

(same table format)

## What's Working Well (Keep List)

Positive findings across sessions — do not regress these.

| Finding | Seen | Source Issues |
|---------|------|---------------|
| ... |

## Contradictions (Needs Manual Review)

| Finding A | Finding B | Source Issues |
|-----------|-----------|---------------|
| ... |

## Session Coverage

| Issue | Date | Goal | Outcome |
|-------|------|------|---------|
| #1 | 2026-02-20 | <goal summary> | Partial |
```

### Step 7: Optionally create GitHub issues for top findings

If the user asks to "create tickets" or "file issues", create individual issues for the top N findings (default: top 5).

**CRITICAL: Every agent-generated issue MUST have the `[AGENT-FEEDBACK]` title prefix, proper labels, AND a proper issue type.** This is how agent-generated content is distinguished from human-generated content. All three are required -- no exceptions.

**Step 7a: Discover existing labels and issue types.**

Fetch the repo's current labels and issue types in parallel:

```bash
# Labels
gh label list --repo <owner/repo> --json name,description,color --limit 200

# Issue types (only available via GraphQL)
gh api graphql -f query='{ repository(owner:"<owner>", name:"<repo>") { id issueTypes(first:20) { nodes { id name description } } } }'
```

Parse both outputs. Map each finding to the best-fit existing labels AND the best-fit issue type (e.g., Bug type for broken behavior, Feature type for missing functionality, Task type for improvements/friction).

**Only create a new label if no existing label adequately covers the category.** When creating, match the repo's existing naming conventions. The only label that is always created if missing is `AGENT-FEEDBACK` (source tracking).

```bash
# Only if AGENT-FEEDBACK label doesn't exist yet:
gh label create "AGENT-FEEDBACK" --repo <owner/repo> --color "7057FF" --description "Agent-generated content" 2>/dev/null
```

**Step 7b: File issues.**

Every issue gets:
1. **`AGENT-FEEDBACK` label** (source tracking)
2. **At least one category label** from the repo's existing set
3. **A severity label** if the repo has them and the finding warrants it
4. **An issue type** (separate field from labels)

Create via REST first, then set the type via GraphQL:

```bash
# Step 1: Create (REST)
ISSUE_URL=$(gh issue create \
  --repo <owner/repo> \
  --title "[AGENT-FEEDBACK] <category>: <finding summary>" \
  --label "AGENT-FEEDBACK" \
  --label "<best-fit existing category label>" \
  --label "<best-fit existing severity label if applicable>" \
  --body "$(cat <<'EOF'
**Category:** <category>
**Severity:** <severity>
**UI Location:** <location>
**Seen in:** <N>/<total> test sessions
**Source feedback:** <issue numbers>

## Description
<finding detail>

## Reproduction
<steps from friction log / bug report>

## Suggested Fix
<recommendation if available>
EOF
)")

# Step 2: Get node ID
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -o '[0-9]*$')
ISSUE_NODE_ID=$(gh api graphql -f query="{ repository(owner:\"<owner>\", name:\"<repo>\") { issue(number: $ISSUE_NUM) { id } } }" --jq '.data.repository.issue.id')

# Step 3: Set issue type
gh api graphql -f query="mutation { updateIssue(input: { id: \"$ISSUE_NODE_ID\", issueTypeId: \"<type_id>\" }) { issue { id } } }"
```

**Both the label AND the type MUST be set.** If GraphQL type assignment fails, report the error but still return the created issue URL.

### Step 8: Present triage results and get implementation approval

Print the triage summary:
- Total issues/reports ingested
- Total findings extracted
- Unique findings after dedup
- Prioritized list with score, category, severity, and UI location for each
- Path to backlog file
- Any contradictions flagged for manual review

**Present the ordered backlog to the user and ask which findings to implement.** The user may approve all, select a subset, reorder, or defer. Do not proceed to implementation without explicit user approval of the implementation list.

### Step 9: Implement fixes (TDD)

For each approved finding, in priority order:

**Step 9a: Write failing tests first.**

Before changing any application code, write tests that capture the expected behavior after the fix. Use the project's existing test framework and patterns (check AGENTS.md/CLAUDE.md for test commands).

- For bugs: write a test that reproduces the broken behavior and asserts the correct behavior.
- For UX friction: write a test that asserts the improved flow (e.g., correct component rendering, expected API response shape, proper error messages).
- For missing features: write tests that define the feature's expected behavior.

Run the tests and confirm they fail for the right reason:
```bash
# Use the project's test command from AGENTS.md/CLAUDE.md
```

**Step 9b: Implement the fix.**

Write the minimum code change that makes the failing tests pass. Follow existing codebase patterns, conventions, and architecture. Read the relevant files before modifying them. Use existing utilities - do not reinvent.

**Step 9c: Run tests and confirm green.**

Run the full test suite (not just the new tests) to confirm the fix doesn't break anything:
```bash
# Use the project's test command from AGENTS.md/CLAUDE.md
```

If tests fail, fix the implementation. Do not skip or disable existing tests.

**Step 9d: Run linters.**

```bash
# Use the project's lint command from AGENTS.md/CLAUDE.md
```

Auto-fix where safe. Report any remaining issues.

**Step 9e: Move to next finding.**

Repeat 9a-9d for each approved finding in order. If a finding depends on a previous fix, implement them sequentially. If findings are independent, note that to the user but still implement sequentially for reviewability.

### Step 10: Full retest and report

After all approved findings are implemented:

**Step 10a: Run the complete test suite.**

```bash
# Full test suite
```

All tests (pre-existing + newly written) must pass. If any fail, diagnose and fix before proceeding.

**Step 10b: Run all linters and formatters.**

```bash
# Full lint
```

**Step 10c: Run a verification UX test.**

If browser automation is available, re-run the original test goals from the ingested feedback sessions against the updated app. This confirms the fixes actually resolve the reported issues from a user perspective, not just from a test perspective.

**Step 10d: Report to user.**

Print:
- Findings implemented (count + list)
- Tests written (count + file locations)
- Tests passing (total count, all green)
- Lint status (clean)
- Verification UX test results (if run)
- Files modified (list)

**Do NOT commit, push, or create PRs.** All changes are local and uncommitted. The user decides when to commit and what to include. If the user asks to commit/push/PR, follow the project's git workflow conventions.

---

## Arguments

- `/ux-feedback-ingest` — full ingest, backlog generation, present triage for approval, then implement approved fixes
- `/ux-feedback-ingest triage-only` — full ingest + backlog generation only, no implementation
- `/ux-feedback-ingest create-tickets` — full ingest + create GitHub issues for top 5 (no implementation)
- `/ux-feedback-ingest create-tickets 10` — full ingest + create issues for top 10 (no implementation)

---

## Notes

- `ux-testing/ux-backlog.md` is regenerated from scratch on every run (derived state, not append-only).
- Closed `AGENT-FEEDBACK` issues are still included (they represent completed sessions, not resolved findings).
- This skill pairs with `ux-tester`: run N test sessions first, then ingest to surface patterns.
- The default mode is triage + implement. Use `triage-only` or `create-tickets` to stop before implementation.
- All code changes are local and uncommitted until the user explicitly requests git operations.
