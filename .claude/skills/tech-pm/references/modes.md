# Tech PM — Mode Reference

Detailed specifications for each operating mode. Loaded on demand when the SKILL.md needs deeper guidance.

---

## Standup Mode — Deep Dive

### Priority Ranking Algorithm

When synthesizing priorities, use this mental model (ordered by weight):

1. **Blockers first** — Anything blocking other issues or teammates gets top priority. Look for:
   - Issues with `blocker` or `critical` labels
   - PRs with requested changes that block merges
   - Infrastructure issues preventing development

2. **Current sprint commitments** — Issues in the active sprint/milestone that are started but not done:
   - Partially implemented features (check branch names vs issue numbers)
   - Items in "In Progress" column on project board
   - Issues assigned to the user

3. **High-priority unstarted work** — Look for:
   - Issues with `priority:high`, `P0`, `P1` labels
   - Issues in current milestone not yet started
   - Issues with approaching deadlines

4. **Dependencies and sequencing** — Some issues enable others:
   - Infrastructure/setup issues that unblock feature work
   - Database migrations before API endpoints
   - API endpoints before frontend features

5. **Quick wins** — Small issues that clear the board:
   - Issues with `good-first-issue` or `small` labels
   - Bug fixes that take < 30 min
   - Documentation gaps

6. **Backlog grooming** — If nothing urgent:
   - Review and refine upcoming milestone issues
   - Break down large issues into smaller ones
   - Update stale issues

### Detecting WIP Context

When the user starts a session, check for signals of previous work:

- **Branch name**: If on a feature branch, they were working on something
- **Uncommitted changes**: Active WIP — ask if they want to continue or stash
- **Recent commits**: Shows what they were doing last session
- **Stash entries**: Forgotten context — remind them
- **Open PRs by user**: May need review responses or merge

### Output Calibration

- **Busy project (10+ open issues)**: Top 5 priorities, grouped by theme
- **Quiet project (< 5 open issues)**: All items, with suggestion to seed backlog
- **New project (0 issues)**: Suggest Ingest mode to create initial backlog from README/spec

---

## Ingest Mode — Deep Dive

### Issue Quality Standards

Every issue created should include:

```markdown
## Context
[Why this matters, what problem it solves, background info]

## Acceptance Criteria
- [ ] [Specific, testable criterion 1]
- [ ] [Specific, testable criterion 2]
- [ ] [Specific, testable criterion 3]

## Technical Notes
[Implementation hints, relevant files, dependencies, edge cases]

## Out of Scope
[Explicitly list what this issue does NOT cover to prevent scope creep]
```

### Duplicate Detection

Before creating a new issue:

1. Search open issues by title keywords
2. Search open issues by label overlap
3. Check recently closed issues (might be reopenable)
4. If potential duplicate found, show both to user and ask:
   - Create new issue anyway?
   - Add context to existing issue?
   - Close existing and create new (supersede)?

### Label Taxonomy

Respect existing labels. If the project has none, suggest this starter set:

| Label | Color | Purpose |
|-------|-------|---------|
| `bug` | `#d73a4a` | Something isn't working |
| `enhancement` | `#a2eeef` | New feature or request |
| `chore` | `#e4e669` | Maintenance, refactoring, tooling |
| `documentation` | `#0075ca` | Documentation improvements |
| `architecture` | `#7057ff` | Architectural decisions |
| `priority:critical` | `#b60205` | Must fix immediately |
| `priority:high` | `#d93f0b` | Important, do soon |
| `priority:medium` | `#fbca04` | Normal priority |
| `priority:low` | `#0e8a16` | Nice to have |
| `blocked` | `#000000` | Waiting on something |
| `size:small` | `#c5def5` | < 2 hours |
| `size:medium` | `#bfd4f2` | 2-8 hours |
| `size:large` | `#85bbf0` | 1-3 days |

### Milestone Assignment Logic

- If the issue is a bug in existing functionality → current milestone
- If the issue is a new feature → next milestone (unless user overrides)
- If the issue is infrastructure/tooling → current milestone (enables other work)
- If the issue is speculative/research → no milestone (backlog)

---

## Status Mode — Deep Dive

### Health Metrics

Calculate these from the GitHub data:

1. **Velocity** (issues closed per week):
   - Look at `closedAt` dates for recent issues
   - Trend: increasing, stable, or declining?

2. **Scope Creep Index**:
   - Issues opened in last 7 days vs issues closed
   - Ratio > 1.5 = flag as scope creep risk

3. **Staleness**:
   - Issues with no comments or updates in > 14 days
   - PRs open > 7 days without review

4. **Milestone Health**:
   - % complete vs % of time elapsed
   - If milestone is 50% through time but only 20% done = red flag

5. **Distribution**:
   - Issues by label (too many bugs? not enough features?)
   - Issues by assignee (balanced or overloaded?)

### Visualization Hints

When presenting status, use text-based visual aids:

```
Progress: ████████░░░░░░░░ 47% (7/15 issues)
Velocity: ▁▂▃▅▇ trending up (3/wk average)
```

---

## Sprint Plan Mode — Deep Dive

### Sprint Scoping Questions

Ask the user (via AskUserQuestion):

1. **Sprint duration**: How long is this sprint? (1 week / 2 weeks / custom)
2. **Capacity**: How many hours/issues can you take on?
3. **Focus**: Any particular area to prioritize? (backend, frontend, infra, bugs)
4. **Carryover**: Any items from last sprint that need to continue?

### Sprint Composition Guidelines

A healthy sprint includes:
- **60-70% feature work** — Moving the product forward
- **20-30% bugs/chores** — Keeping quality high
- **10% buffer** — Things always take longer

### Creating Sprint Milestones

If the project doesn't have sprint milestones:

```bash
# Create milestone for current sprint
gh api repos/OWNER/REPO/milestones --method POST \
  -f title="Sprint N — YYYY-MM-DD to YYYY-MM-DD" \
  -f due_on="YYYY-MM-DDT23:59:59Z" \
  -f description="Focus: [areas]. Capacity: [N] issues."
```

Then assign selected issues to the milestone:
```bash
gh issue edit ISSUE_NUMBER --milestone "Sprint N — ..."
```

---

## Cross-Mode Behaviors

### Always Do

- Check `gather_local_state.sh` output for the `error` field before proceeding
- Check `gather_github_state.sh` output for the `error` field before proceeding
- Reference actual issue numbers and URLs (don't make them up)
- Use the user's existing conventions for labels, milestones, naming

### Never Do

- Invent issue numbers that don't exist
- Assume milestone due dates — read them from the API
- Create issues without user confirmation
- Change issue labels/milestones without asking
- Guess at project board column names — read them from the API
