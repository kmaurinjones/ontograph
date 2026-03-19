---
name: commit-review
description: Automatic post-commit code review + fix loop via Claude Opus. Reviews every commit, fixes all findings, reviews again (3 rounds). Writes to code-reviews/YYYY/MM/DD/HHMMSS-{sha}-review.md. Customize via REVIEW.md at repo root.
---

# Commit Review + Fix Loop

## Purpose

Automatic code review that fires after every git commit. A backgrounded Claude
Opus session runs a 3-round review-fix loop: review the commit, fix all
findings, review the fix, fix again, then a final review for documentation.
Non-blocking — runs entirely in the background.

## How It Works

1. Global `post-commit` hook at `~/.claude/git-hooks/post-commit` fires
2. Gathers: commit SHA, changed files, commit message, timestamps
3. Filters out noise (lock files, binaries, build output, images)
4. Writes a progress placeholder to the review file
5. Backgrounds a `claude -p --model opus --dangerously-skip-permissions` session
6. The session runs the 3-round loop:

### Round 1
- Reviews the original commit diff + full file contents
- Writes review to `code-reviews/YYYY/MM/DD/HHMMSS-{sha}-review.md`
- If LGTM: stops. If findings: fixes all issues, commits with `review-fix:` prefix

### Round 2
- Reviews the fix commit diff + full file contents
- Writes new review file for the fix commit
- If LGTM: stops. If findings: fixes all issues, commits with `review-fix:` prefix

### Round 3 (final — documentation only)
- Reviews the second fix commit
- Writes final review file
- Stops. Does NOT fix anything — this review is documentation only.

## Recursion Guard

Fix commits use the message prefix `review-fix:`. The hook detects this and
skips, preventing infinite loops.

## Installation

The hook is global — it applies to all repos automatically:

```bash
git config --global core.hooksPath ~/.claude/git-hooks
```

Per-repo hooks (husky, pre-commit, etc.) are preserved — the global hook
chains to `.git/hooks/post-commit` if it exists.

## Skipped Automatically

- Initial commits (no parent to diff against)
- Rebases, merges, cherry-picks (rapid-fire commits)
- Commits with only noise files (lock files, binaries, images, build output)
- Repos where `claude` CLI is not installed
- Commits with `review-fix:` prefix (recursion guard)

## Progress Tracking

While the loop is running, the initial review file contains a placeholder:

```markdown
# Code Review: abc1234

**Status:** In progress (started 2026-03-10 21:15:00)
...
Review + fix loop is running in the background (3 review rounds).
```

## Customization — REVIEW.md

Create a `REVIEW.md` at repo root to define project-specific review
instructions. The reviewer reads it automatically before each round.

Example:

```markdown
# Review Instructions

## Focus Areas
- All database queries must use parameterized statements
- Auth middleware must be applied to every route in /api/v1/
- React components must not call hooks conditionally

## Ignore
- Files in /scripts/ are one-off utilities, don't review for production quality

## Conventions
- Error responses use the AppError class from lib/errors.ts
- All async route handlers are wrapped in asyncHandler()
```

## Review Output Format

Each review is written to `code-reviews/YYYY/MM/DD/HHMMSS-{short-sha}-review.md`:

```markdown
# Code Review: abc1234

**Verdict:** 2 findings (1 CRITICAL, 1 MEDIUM)
**Commit:** `abc1234567890...`
**Message:** feat: add user authentication
**Review started:** 2026-03-10 19:45:00
**Review completed:** 2026-03-10 19:47:32
**Review duration:** 2m 32s
**Files:** 5 changed
**Model:** claude-opus-4-6
**Round:** 1 of 3

## Summary

Added JWT-based auth with login/register endpoints. Implementation is solid
but has one critical issue with token validation.

## Findings

### [CRITICAL] JWT secret loaded from env without validation
**File:** `src/auth/jwt.ts` L12
**Code:**
​```typescript
const JWT_SECRET = process.env.JWT_SECRET;
const token = jwt.sign(payload, JWT_SECRET);
​```
**Issue:** JWT_SECRET is read from process.env without checking if it exists.
If unset, tokens are signed with `undefined` as the secret.
**Fix:**
​```typescript
const JWT_SECRET = process.env["JWT_SECRET"];
if (!JWT_SECRET) throw new Error("JWT_SECRET environment variable is required");
​```
```

## Typical Output

A single commit may produce up to 4 files:
- `214500-abc1234-review.md` — Round 1 review of original commit
- `214732-def5678-review.md` — Round 2 review of fix commit
- `214915-ghi9012-review.md` — Round 3 final review (documentation)
- `214500-abc1234-review.log` — Stderr log (deleted if empty)

## Error Diagnostics

If a review fails, check `code-reviews/YYYY/MM/DD/HHMMSS-{sha}-review.log` for stderr.
Empty log files are automatically cleaned up on successful runs.

## Review Scope

The reviewer checks with emphasis on code quality given codebase context:
- **Bugs:** logic errors, off-by-ones, null/undefined access, race conditions
- **Security:** injection, XSS, auth bypass, secrets exposure, OWASP top 10
- **Edge cases:** missing error handling, contract violations, type mismatches
- **Style:** naming, consistency with project conventions, readability
- **Architecture:** coupling, abstraction quality, separation of concerns
- **Performance:** unnecessary allocations, N+1 patterns, missing indexes

## File Filter

These patterns are excluded from review (noise reduction):

```
*.lock, *.min.*, *.map, *.generated.*, .DS_Store,
node_modules/, dist/, build/, __pycache__/, *.pyc,
*.png, *.jpg, *.jpeg, *.gif, *.ico, *.woff, *.ttf,
*.eot, *.mp4, *.mp3, *.pdf, *.pen
```

## Constraints

- Fix commits are local only — NEVER pushes to any remote.
- Fix commits only modify files flagged in the review.
- Every fix commit message starts with `review-fix:` (recursion guard).
- Every finding includes: file, line number, code snippet, description, concrete fix.
