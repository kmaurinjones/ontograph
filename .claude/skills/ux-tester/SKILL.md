---
name: ux-tester
description: Run an automated UX test on the current project using browser automation. Simulates a first-time user with a real goal, navigates the full app, and produces a structured feedback report filed as a GitHub issue. Use when user says ux test, test the ux, run a ux test, or browser test.
---

# UX Tester Skill

Automated first-time-user UX testing via browser automation (Claude in Chrome or Chrome DevTools MCP).

---

## Prerequisites

Before running a UX test:

1. **App must be running locally.** Confirm the local dev server is live (typically `http://localhost:3000` or whatever the project uses). If not, start it using the project's dev command from AGENTS.md / CLAUDE.md.

2. **Test account must be available.** Check the project's AGENTS.md or CLAUDE.md for demo/test credentials. If none exist, either create a test account through the signup flow or note that signup itself is part of the test.

3. **Browser automation must be available.** Requires either `mcp__claude-in-chrome__*` or `mcp__chrome-devtools__*` tools.

4. **GitHub remote must exist** (for issue filing). Check with `git remote -v`. If no remote, save the report locally instead.

---

## Execution

### Step 1: Gather project context

Before testing, read:
- `AGENTS.md` or `CLAUDE.md` at repo root for: dev server URL, demo credentials, app description
- `ux-testing/testing-prompts/ux-testing-prompts.md` if it exists (project-specific test library)
- `docs/frontend/ui-ux-guidelines.md` or similar if it exists (to understand intended design)

Identify:
- **App URL** (e.g., `http://localhost:3000`)
- **Login credentials** (if any)
- **What the app does** (one sentence, for persona grounding)

### Step 2: Pick or receive a test goal

If the user provides a specific goal, use it verbatim.

If the user says "run a ux test" without specifying a goal, check for a test prompt library at `ux-testing/testing-prompts/ux-testing-prompts.md`. If it exists, pick a prompt (prefer ones not yet tested — check `ux-testing/artifacts/` for prior sessions). If no library exists, ask the user for a goal.

### Step 3: Open the app in a fresh browser tab

Navigate to the app URL in a new tab. Do NOT reuse an existing tab — the test must simulate a cold start.

Take a screenshot of the landing page before doing anything.

### Step 4: Execute the test as a first-time user

**Persona:** You are a first-time user. You have never seen this app before. You do not know the UI, terminology, or navigation. Approach with your goal and zero prior knowledge.

**Behavioral rules:**
- Read every page before clicking. Note what's clear and what's confusing.
- Do not skip steps. If the app requires login, log in. If it requires form input, fill it out.
- Use demo/test credentials when authentication is needed.
- Do not assume things work. Click, wait, observe.
- If something breaks or errors, document it exactly and try to continue.
- Take screenshots at every significant state change (page load, form submission, results, errors).

**Attention dimensions — actively track these throughout:**

| Dimension | What to observe |
|---|---|
| Friction | Where you got stuck, confused, or slowed down |
| Errors | Anything that broke, errored, or behaved unexpectedly |
| Clarity | Whether UI copy, labels, and terminology were clear |
| Missing affordances | Things you wanted to do but couldn't |
| Flow | Whether the step sequence felt logical or required backtracking |
| Delight | Anything surprisingly good, fast, or well-designed |
| Trust | Whether you trusted the outputs and had enough context to believe results |
| Value perception | Whether you'd pay for this and at what tier |

### Step 5: Produce the structured report

When the task is complete (or you've hit a dead end), write the report:

```markdown
## Task Outcome
Did you accomplish the goal? If partially, what was missing?

## Step-by-Step Walkthrough
Every action taken, in order. What was clicked, what happened, reaction.

## Friction Log
Every moment of confusion, hesitation, or frustration — with specific UI elements.

## Bugs & Errors
Anything that broke or produced unexpected behavior. Include exact error messages.

## Missing Features / Affordances
Things expected to exist but didn't. Capabilities that would have helped.

## What Worked Well
Anything intuitive, fast, or well-designed.

## Trust & Confidence Assessment
How much do you trust the output? What would increase confidence?

## Value Perception
Would you pay? What tier feels right? What's missing before swiping the card?

## Top 5 Recommendations
Highest-impact improvements, ranked by first-time-user experience impact.
```

### Step 6: File the GitHub issue

Detect the GitHub remote from `git remote -v` and extract the `owner/repo`.

**CRITICAL: Every agent-generated issue MUST have the `[AGENT-FEEDBACK]` title prefix, proper labels, AND a proper issue type.** This is how agent-generated content is distinguished from human-generated content in the repo. All three are required -- no exceptions.

**Step 6a: Discover existing labels and issue types.**

Fetch the repo's current labels and issue types in parallel:

```bash
# Labels
gh label list --repo <owner/repo> --json name,description,color --limit 200

# Issue types (only available via GraphQL)
gh api graphql -f query='{ repository(owner:"<owner>", name:"<repo>") { id issueTypes(first:20) { nodes { id name description } } } }'
```

Parse both outputs. Map each finding to:
1. The best-fit existing **labels** based on label names and descriptions (bug/defect, enhancement/feature, UX/usability, cosmetic/visual, severity levels, project-specific labels).
2. The best-fit existing **issue type** based on the finding category (e.g., Bug type for broken behavior, Feature type for missing functionality, Task type for improvements/friction).

**Step 6b: Determine labels and type for this issue.**

Every issue gets:
1. **`AGENT-FEEDBACK` label** (source tracking - create if it doesn't exist). This label marks all agent-generated issues.
2. **At least one category label** from the repo's existing label set that best matches the finding (bug, enhancement, ux, etc.)
3. **A severity label** if the repo has severity/priority labels and the finding warrants it
4. **An issue type** (Bug, Feature, Task, or whatever types the repo defines). This is a separate field from labels.

**Only create a new label if no existing label adequately covers the category.** When creating, match the repo's existing naming conventions.

```bash
# Only if AGENT-FEEDBACK label doesn't exist yet:
gh label create "AGENT-FEEDBACK" --repo <owner/repo> --color "7057FF" --description "Agent-generated content" 2>/dev/null
```

**Step 6c: File the issue.**

**Issue title format:** `[AGENT-FEEDBACK] <category>: <concise description>`
- Examples: `[AGENT-FEEDBACK] bug: Upload form crashes on CSV files >10MB`
- Examples: `[AGENT-FEEDBACK] ux: No feedback after clicking "Compare" button`
- Examples: `[AGENT-FEEDBACK] enhancement: Missing bulk export for comparison results`

Create the issue via REST first (to get the issue URL), then set the type via GraphQL:

```bash
# Step 1: Create the issue (REST -- no --type flag available)
ISSUE_URL=$(gh issue create \
  --repo <owner/repo> \
  --title "[AGENT-FEEDBACK] <category>: <short description of finding>" \
  --label "AGENT-FEEDBACK" \
  --label "<best-fit existing category label>" \
  --label "<best-fit existing severity label if applicable>" \
  --body "$(cat <<'EOF'
<full report here>
EOF
)")

# Step 2: Extract issue number from URL and get node ID
ISSUE_NUM=$(echo "$ISSUE_URL" | grep -o '[0-9]*$')
ISSUE_NODE_ID=$(gh api graphql -f query="{ repository(owner:\"<owner>\", name:\"<repo>\") { issue(number: $ISSUE_NUM) { id } } }" --jq '.data.repository.issue.id')

# Step 3: Set the issue type via GraphQL
gh api graphql -f query="mutation { updateIssue(input: { id: \"$ISSUE_NODE_ID\", issueTypeId: \"<type_id_from_step_6a>\" }) { issue { id } } }"
```

**Both the label AND the type MUST be set.** If GraphQL type assignment fails, report the error but still return the created issue URL -- the label and title prefix are already set.

If no GitHub remote exists, save the report to `ux-testing/reports/YYYY-MM-DD--HH-MM-SS-<goal-slug>.md` instead and tell the user.

### Step 7: Save artifacts

Create `ux-testing/artifacts/` if it doesn't exist. Save all screenshots:
```
ux-testing/artifacts/ux-tester-session<N>-<brief-description>.png
```
Number sessions sequentially based on existing files.

### Step 8: Report to user

Print:
- Goal tested
- Outcome (pass/partial/blocked)
- Top 3 issues found
- GitHub issue URL (or local report path)
- Number of screenshots saved

---

## Arguments

The skill accepts an optional argument: the test goal as a free-text string.

- `/ux-tester` — picks a goal from the library (or asks for one)
- `/ux-tester I want to create an account and do the main thing this app does` — uses the provided goal
- `/ux-tester 3` — uses prompt #3 from the project's test library

---

## Bootstrapping a Test Prompt Library

If the project doesn't have `ux-testing/testing-prompts/ux-testing-prompts.md` yet, offer to create one. Ask the user:
1. What does this app do? (one sentence)
2. Who are the target users?
3. What are the 3-5 core workflows?

Then generate 10-15 test prompts covering:
- Core workflow happy paths (one per workflow)
- First-time user onboarding / signup
- Error recovery scenarios
- Edge cases (empty states, long inputs, rapid actions)
- Mobile / responsive testing goals
- Sharing / collaboration features (if applicable)
- Payment / upgrade flows (if applicable)
