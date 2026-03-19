---
name: test-guard
description: Enforce 1:1 test coverage for ALL code changes. Every implementation change MUST be accompanied by both unit tests and Playwright E2E tests before it is considered complete. This is a hard gate — no exceptions. Invoked automatically before any code change is marked done.
---

# Skill: Test Guard

## Purpose

Enforce 1:1 test coverage for ALL code changes. Every implementation change MUST
be accompanied by both unit tests and Playwright E2E tests before it is
considered complete. This is a hard gate — no exceptions.

This skill defines the mandatory development loop that every code change must
follow. It applies to features, bug fixes, refactors, UI changes, API changes,
and any other modification that touches application code.

---

## The Development Loop (MANDATORY — follow in exact order)

Every code change follows this loop. Do not skip steps. Do not reorder.

```
1. IMPLEMENT  →  Write the code change
2. UNIT TEST  →  Write unit tests covering the change
3. E2E TEST   →  Write/update Playwright tests covering the change
4. RUN UNITS  →  Execute unit tests (must pass)
5. RUN E2E    →  Execute Playwright tests HEADED (must pass)
6. ITERATE    →  If any test fails: fix implementation or test, return to step 4
7. DONE       →  All tests green → change is complete
```

**The loop is non-negotiable.** A change without passing tests at both levels
is an incomplete change, period. "I'll add tests later" is not acceptable.

---

## Configuration (CUSTOMIZE FOR YOUR PROJECT)

Replace the placeholder commands and paths below with your project's actual
test tooling. The loop structure is fixed; the tools are project-specific.

```yaml
test_guard:
  unit:
    frontend:
      framework: "vitest"                    # vitest | jest | mocha
      command: "npx vitest run"              # Single-run command
      verbose: "npx vitest run --reporter=verbose"
      single_file: "npx vitest run {file}"
      test_pattern: "**/*.test.{ts,tsx}"     # Co-located with source
    backend:
      framework: "pytest"                    # pytest | go test | cargo test
      command: "cd backend && uv run pytest -v"
      single_file: "cd backend && uv run pytest -v {file}"
      test_dir: "backend/tests/"
      test_prefix: "test_"
  e2e:
    framework: "playwright"
    command: "npx playwright test --headed"  # MUST be headed
    single_file: "npx playwright test --headed {file}"
    grep: "npx playwright test --headed -g \"{pattern}\""
    test_dir: "tests/e2e/"
    requires_services: true
    start_services: "./run.sh"               # Command to start the full stack
```

---

## Step 1: Implement

Write the code change. Normal development — no special rules beyond what
CLAUDE.md already requires.

---

## Step 2: Write Unit Tests

Unit tests validate individual functions, components, hooks, and API logic
in isolation.

### Frontend unit tests

**Location:** Co-located with source files as `<filename>.test.ts(x)`

```
src/components/Button.tsx      → src/components/Button.test.tsx
src/lib/api/hooks.ts           → src/lib/api/hooks.test.ts
src/lib/utils.ts               → src/lib/utils.test.ts
src/hooks/use-theme.ts         → src/hooks/use-theme.test.ts
app/login/page.tsx             → app/login/page.test.tsx
```

**What to test:**
- Component rendering (does it mount without crashing?)
- User interactions (click, type, submit → correct state changes)
- Conditional rendering (loading, error, empty states)
- Form validation (valid/invalid inputs, error messages)
- Hook behavior (state transitions, side effects)
- Utility functions (pure logic, edge cases)

**What NOT to unit test (leave for E2E):**
- Full page navigation flows
- Multi-page user journeys
- Real API integration
- Browser-specific behavior (localStorage, cookies)

### Backend unit tests

**Location:** Mirror the source structure under a `tests/` directory.

```
backend/app/api/v1/endpoints/auth.py  → backend/tests/api/v1/test_auth.py
backend/app/core/security.py          → backend/tests/core/test_security.py
backend/app/models/user.py            → backend/tests/models/test_user.py
```

**What to test:**
- Endpoint request/response (status codes, response shapes)
- Auth flows (login, register, token validation, unauthorized access)
- Database operations (CRUD, constraints, edge cases)
- Business logic (validation rules, state machines)
- Error handling (invalid input, missing resources, permission denied)

---

## Step 3: Write/Update Playwright E2E Tests

E2E tests validate complete user journeys through the running application.

**Location:** `tests/e2e/*.spec.ts` — one spec file per feature area.

**Structure:**
- Tests run serially in shared browser sessions (one context per `describe` block)
- Each block shares a single `BrowserContext` and `Page` via `beforeAll`/`afterAll`
- Screenshots captured to `tests/artifacts/{timestamp}/` for visual verification

**What to test:**
- Full user flows (login → navigate → perform action → verify result)
- Page renders correctly after navigation
- Form submissions produce correct outcomes
- Error states display to the user
- Access control (authorized vs unauthorized users)
- New UI elements are visible and interactive

**Key patterns:**
```typescript
// Always use exact matches for buttons that might conflict with framework UI
page.getByRole("button", { name: "Submit", exact: true })

// Use role scoping to avoid strict mode violations
page.getByRole("main").getByText("Welcome")

// Wait for content hydration on API-dependent pages
await page.waitForLoadState("networkidle");

// Use waitForURL after navigation actions
await page.waitForURL("**/dashboard");
```

**CRITICAL: Playwright tests MUST run headed.** Never use headless mode.
The `--headed` flag is mandatory on every invocation.

---

## Step 4: Run Unit Tests

```bash
# Frontend (customize command per config)
npx vitest run

# Backend (customize command per config)
cd backend && uv run pytest -v
```

Both must pass. If either fails, go to Step 6.

---

## Step 5: Run Playwright E2E Tests (HEADED)

```bash
npx playwright test --headed
```

**Prerequisites:**
- Full stack must be running (use the configured `start_services` command)
- Database must be seeded if tests depend on seed data

All tests must pass. If any fail, go to Step 6.

---

## Step 6: Iterate

When tests fail:

1. **Read the failure output.** Understand what failed and why.
2. **Determine if it's a test bug or an implementation bug.**
   - Test bug: selector wrong, timing issue, wrong assertion → fix the test
   - Implementation bug: component crashes, wrong behavior, missing element → fix the code
3. **Fix and re-run from Step 4.** Do not skip re-running the full suite.
4. **Repeat until all tests pass at both levels.**

Common Playwright issues:
- Strict mode violations → scope selectors with `getByRole("main")` or `{ exact: true }`
- Timing issues → use `waitForLoadState("networkidle")` or `waitForURL()`
- React hooks violations → ensure hooks are called before conditional returns

---

## Step 7: Done

All unit tests and all Playwright tests pass. The change is complete.

---

## Coverage Rules

### When to write NEW tests (mandatory):
- New component or page → unit test for rendering + interactions
- New API endpoint → backend unit test for all response paths
- New user-facing feature → Playwright test for the happy path + key error paths
- New form → unit test for validation, Playwright test for submission flow
- New utility function → unit test for all branches

### When to UPDATE existing tests (mandatory):
- Changed component behavior → update unit test assertions
- Changed API response shape → update backend tests + any E2E tests that assert on content
- Changed navigation flow → update Playwright navigation tests
- Removed feature → remove corresponding tests (dead tests are bugs)
- Renamed element → update selectors in both unit and E2E tests

### When tests are NOT required (rare exceptions):
- Pure CSS/styling changes with no behavioral impact (but if the change adds/removes
  an element, that IS behavioral)
- Config file changes (tsconfig, tailwind, eslint) — unless they change build behavior
- Documentation-only changes (README, comments)
- Dependency version bumps — unless they change API surface

---

## Test Infrastructure Setup

### Frontend: Vitest + React Testing Library

```bash
npm install -D vitest @vitejs/plugin-react jsdom @testing-library/react @testing-library/jest-dom @testing-library/user-event
```

Create `vitest.config.ts` at repo root:
```typescript
import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    include: ["**/*.test.{ts,tsx}"],
    exclude: ["node_modules", "tests/e2e"],
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
});
```

Create `tests/setup.ts`:
```typescript
import "@testing-library/jest-dom/vitest";
```

### Backend: pytest (Python)

```bash
cd backend && uv add --dev pytest pytest-asyncio httpx
```

### Playwright

```bash
npm install -D @playwright/test
npx playwright install chromium
```

---

## Enforcement

This skill is invoked automatically by the agent before marking ANY code change
as complete. The agent MUST NOT:

- Declare a feature "done" without running both test levels
- Skip unit tests because "the E2E covers it" (they test different things)
- Skip E2E tests because "the unit tests cover it" (they test different things)
- Run Playwright in headless mode (must be `--headed`)
- Leave failing tests with a "TODO: fix later" comment
- Write tests that pass trivially (e.g., `expect(true).toBe(true)`)

If time pressure is invoked as a reason to skip tests: the answer is still no.
Tests are not optional. They are part of the implementation, not a separate task.
