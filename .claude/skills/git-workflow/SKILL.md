---
name: git-workflow
description: End-to-end Git workflow for feature development, conflict resolution, and promotion across branches. Covers branch naming, commit conventions, PR creation, lock file handling, migration coordination, and agent session safety. Use when starting any code change, resolving merge conflicts, promoting code between environments, or when user mentions branching, PR, merge, conflict, deploy, or release.
---

# Git Workflow

Standard operating procedure for all code changes. Every developer and every
agent session follows this workflow without exception.

**CUSTOMIZE:** Replace `PROJ-XX` with your project's ticket prefix (e.g.,
`MATLAS-XX`, `GUARD-XX`). Replace branch names if your project uses different
environment branches. Update commands to match your project's tooling.

---

## Branch Architecture

```
release ─── production (deployed, protected, PO sign-off to merge)
  ↑
stage ───── staging (deployed, semi-protected, any engineer can promote from main)
  ↑
main ────── integration trunk (where PRs land, squash merge only)
  ↑
feature/ ── short-lived, one per ticket
```

### Branch naming (mandatory)

| Type | Pattern | Example |
|---|---|---|
| Feature | `feature/PROJ-{ticket}-{2-4-word-slug}` | `feature/PROJ-20-npi-data-model` |
| Bug fix | `bugfix/PROJ-{ticket}-{slug}` | `bugfix/PROJ-45-upload-null-check` |
| Hotfix (prod) | `hotfix/PROJ-{ticket}-{slug}` | `hotfix/PROJ-50-csv-encoding` |
| Chore (no ticket) | `chore/{slug}` | `chore/update-deps` |

Rules:
- Slugs are lowercase, hyphens only, max 4 words.
- One ticket per branch. One branch per ticket.
- Never reuse a branch name after it's been merged and deleted.

---

## Feature Lifecycle (Step by Step)

### 1. Pre-flight checks

Before starting any work:

```bash
git checkout main
git pull --rebase origin main
git status                        # Must be clean. If dirty, stash or commit first.
```

If the working tree has uncommitted changes from another session:
- If they're yours and intentional: `git stash` or commit on a branch.
- If they're unknown: investigate before discarding. Never `git checkout .`
  without understanding what's there.

### 2. Create feature branch and update ticket

```bash
git checkout -b feature/PROJ-XX-short-description
```

Never work directly on `main`, `stage`, or `release`.

If the project uses a ticket tracker (Jira, GitHub Issues, etc.), transition
the ticket to **In Progress** using available tools (MCP, CLI, API).

### 3. Work and commit

Make changes. Commit early and often with conventional commit messages.

**Commit message format:**

```
<type>(<scope>): <description>

[optional body with context]

Refs: PROJ-XX
```

**Types:** `feat`, `fix`, `refactor`, `test`, `docs`, `chore`, `style`, `perf`

**Scopes:** Customize per project (e.g., `upload`, `auth`, `models`, `api`, `ui`, `infra`, `deps`)

Rules:
- First line: imperative mood, max 72 characters, no period.
- Body: explain *why*, not *what* (the diff shows what).
- Always include `Refs: PROJ-XX` when a ticket exists.
- No `WIP` commits on shared branches. Squash before PR.

### 4. Rebase before PR

Before creating a PR, rebase your branch on latest main:

```bash
git fetch origin
git rebase origin/main
```

If conflicts arise, resolve them (see Conflict Resolution below), then:

```bash
git rebase --continue
```

Never merge main into your feature branch. Always rebase.

### 5. Push and create PR

```bash
git push -u origin feature/PROJ-XX-short-description
```

Create PR with:

```bash
gh pr create --base main --title "PROJ-XX: Short description" --body "$(cat <<'EOF'
## Summary
- What this PR does and why

## Changes
- File-by-file summary of what changed

## How to test
1. Step-by-step verification instructions

## Ticket
[PROJ-XX](<link to ticket>)
EOF
)"
```

PR rules:
- Title format: `PROJ-XX: Short imperative description`
- One ticket per PR. If a PR touches multiple tickets, split it.
- Keep PRs under 400 lines changed. Larger PRs get split into stacked PRs.
- Always fill in "How to test" — reviewers must be able to verify.

After creating the PR, transition the ticket to **In Review**.

### 6. Review and merge

- Squash merge into `main`. This keeps history clean — one commit per feature.
- Delete the feature branch after merge.
- If CI exists, all checks must pass before merge.
- After merge, transition the ticket to **Done**.

### 7. Post-merge

After your PR is merged:

```bash
git checkout main
git pull --rebase origin main
git branch -d feature/PROJ-XX-short-description   # delete local branch
```

---

## Conflict Resolution

### Decision tree (follow in order)

#### Lock files (`package-lock.json`, `uv.lock`, `yarn.lock`, `pnpm-lock.yaml`)

**Never manually resolve.** Always regenerate:

```bash
# For package-lock.json:
git checkout origin/main -- package-lock.json
npm install

# For uv.lock:
git checkout origin/main -- uv.lock
cd backend && uv sync    # adjust path for your project
```

Then `git add` the regenerated lock file and continue the rebase/merge.

#### Auto-generated files (build output, type declarations, etc.)

Delete the conflicting file, regenerate it with the appropriate build command,
then `git add` and continue.

#### Database migrations (Alembic, Prisma, Django, etc.)

Migration files are sequential and order-dependent. Two branches creating
migrations = broken migration history.

Protocol:
1. **Only one branch creates migrations at a time.** Before creating a migration,
   check with the team to confirm no other branch has an in-flight migration.
2. If you discover a conflict: your branch rebases, deletes its migration,
   and re-generates it on top of the merged migration.
3. Never manually edit migration revision pointers. Always regenerate.

#### Code conflicts

1. Read both sides of the conflict. Understand the intent of each change.
2. Prefer the newer intent (the one being rebased onto) as the base, then
   integrate your changes on top.
3. After resolving, verify the file is syntactically valid and logically correct.
4. Run linters and tests after resolution.

#### If unsure

Stop. Do not guess. Ask the team or flag for the other developer to resolve jointly.

---

## Promotion Gates

### main → stage (staging deployment)

**Who can trigger:** Any engineer on the team.

**Requirements:**
- All CI checks pass on `main` (when CI exists)
- No known broken tests
- Full lint + test suite passes locally

**How:**
```bash
git checkout stage
git pull origin stage
git merge origin/main
git push origin stage
```

### stage → release (production deployment)

**Who can trigger:** Product Owner sign-off required.

**Requirements:**
- QA pass on staging environment
- PO explicitly approves
- No open P0 bugs

**How:**
```bash
git checkout release
git pull origin release
git merge origin/stage
git push origin release
```

**Never skip staging.** Code goes main → stage → release. No exceptions unless
it's a hotfix (see below).

### Hotfix flow (production emergency)

When prod is broken and can't wait for the normal flow:

```bash
git checkout release
git pull origin release
git checkout -b hotfix/PROJ-XX-description
# ... make the fix ...
git push -u origin hotfix/PROJ-XX-description
gh pr create --base release --title "HOTFIX PROJ-XX: description"
```

After the hotfix PR is merged to `release` and deployed:

```bash
# Cherry-pick the fix back into main and stage
git checkout main && git pull origin main
git cherry-pick <hotfix-commit-sha>
git push origin main

git checkout stage && git pull origin stage
git cherry-pick <hotfix-commit-sha>
git push origin stage
```

Never leave hotfixes only on `release`. They must propagate back.

---

## Agent Session Safety

Every agent session (Claude Code, Codex, or any automated tool) MUST follow
these rules to avoid stomping on concurrent work.

### Pre-flight (mandatory, every session)

```bash
git status          # Working tree must be clean
git checkout main
git pull --rebase origin main
```

If the working tree is dirty:
- Identify what the uncommitted changes are and why they exist.
- If they belong to another in-progress feature: stash them.
- If they're abandoned: confirm with the user before discarding.
- Never blindly discard uncommitted changes.

### During work

- Always work on a feature branch. Never commit to `main` directly.
- Commit frequently so progress isn't lost if the session is interrupted.
- If the session is long-running, periodically rebase on `main` to avoid
  accumulating large conflict surfaces.

### Session handoff

If a session ends with work-in-progress:
- Push the feature branch to remote so the next session can pick it up.
- Leave a clear commit message: `wip: <what's done, what's left>`
- The next session pulls the branch and continues.

### Parallel session awareness

Multiple agent sessions may be running on different feature branches simultaneously.
Each session:
- Works only on its own feature branch.
- Never modifies another session's branch.
- Never force pushes to any shared branch.
- Merges to `main` only via PR (never direct push).

---

## Monolith File Strategy

When multiple features touch the same files, merge conflicts become frequent.

**Strategy:** When a file exceeds ~500 lines or causes repeated conflicts, split
it into domain-specific modules as a standalone `chore/` PR. Never mix structural
refactoring with feature work in the same PR.

**Common high-conflict files to watch:**
- Backend entry point (all endpoints in one file)
- ORM models (all models in one file)
- Schema definitions (all schemas in one file)
- Global CSS / design tokens
- Shared type definitions

---

## .env Contract

`.env.example` is the contract for required environment variables.

Rules:
- Any new env var MUST be added to `.env.example` in the same PR that introduces it.
- `.env.example` contains placeholder values only (never real credentials).
- If a var is optional, comment it out with a note: `# Optional: ...`

---

## CRITICAL RULES

1. **Never push directly to `main`, `stage`, or `release`.** Always use PRs.
2. **Never force push to shared branches.** Only force push your own feature branches.
3. **Never manually resolve lock file conflicts.** Always regenerate.
4. **Never skip staging.** main → stage → release. Hotfixes are the only exception.
5. **Never merge main into a feature branch.** Always rebase.
6. **One ticket per branch, one branch per PR.** No dump-truck PRs.
7. **Clean working tree before starting.** `git status` must be clean.
8. **Delete feature branches after merge.** No stale branches.

---

## Invocation

```
/git-workflow
```

Or triggered by: "start a feature", "create a branch", "merge conflict",
"promote to staging", "deploy to prod", "hotfix", "how do I branch"
