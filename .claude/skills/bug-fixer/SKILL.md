---
name: bug-fixer
description: Investigate bugs, identify root cause, implement fix with test coverage, verify resolution. Use when user mentions fix bug, resolve bug, debug issue, something's broken, or reports unexpected behavior.
---

# Bug Fixer Skill

---

## Process

### 1. Bug Report Clarification
Gather information:
- **Symptom**: What's the observed behavior?
- **Expected**: What should happen instead?
- **Reproduction**: Steps to reproduce
- **Scope**: Where in the codebase?
- **Recent changes**: Was it working before? What changed?

If insufficient detail, ask clarifying questions.

### 2. Reproduction Verification
Attempt to reproduce:

**API/Backend bug**:
```bash
# Try to trigger via API
curl -X POST http://localhost:8000/api/endpoint -d '{...}'

# Or via test
pytest tests/test_X.py -k "failing_test"
```

**Frontend bug**:
```bash
# Run dev server, navigate to affected page
npm run dev

# Or via test
npm test -- ComponentName.test.tsx
```

**CLI bug**:
```bash
# Run the command that fails
./my-cli --flag value
```

If can't reproduce:
- Request more details
- Check environment differences
- Review logs

### 3. Root Cause Investigation
Systematic investigation:

**Check logs**:
```bash
# Application logs
tail -f logs/app.log

# System logs (if applicable)
journalctl -f -u myservice
```

**Check error traces**:
- Stack trace analysis
- Identify failing line/function
- Trace back to original cause

**Check recent changes**:
```bash
# What changed recently?
git log --oneline -10
git diff HEAD~5..HEAD -- path/to/file
```

**Check related code**:
```bash
# Find all usages of failing function
rg "function_name" src/

# Find similar patterns
rg "similar_pattern" .
```

**Hypothesis formation**:
- What could cause this symptom?
- What assumptions might be violated?
- What edge case wasn't handled?

### 4. Hypothesis Testing
Test theories:

**Add debug logging**:
```python
# Temporary debug code
print(f"DEBUG: variable_value = {variable_value}")
```

**Check assumptions**:
```python
# Add assertions
assert value is not None, "Value unexpectedly None"
assert isinstance(value, int), f"Expected int, got {type(value)}"
```

**Isolate variables**:
- Test with minimal input
- Test with known-good data
- Binary search through code path

### 5. Fix Implementation (TDD)
Once root cause identified:

**Write regression test** (bug should fail test):
```python
# tests/test_bug_fix.py
def test_bug_reproduction():
    """Regression test for bug #123."""
    # Setup that triggers bug
    result = buggy_function(edge_case_input)

    # Assert expected behavior (this should fail initially)
    assert result == expected_value
```

Run test -> Verify it fails as expected.

**Implement fix**:
```python
# Fix the root cause
def buggy_function(input):
    # Add missing edge case handling
    if input is None:
        raise ValueError("Input cannot be None")

    # Original logic with fix
    return process(input)
```

**Run test again** -> Verify it passes.

### 6. Comprehensive Verification
Ensure fix doesn't break anything:

**Run affected tests**:
```bash
# Tests for modified file
pytest tests/test_X.py -v
```

**Run full test suite**:
```bash
# All tests
pytest

# Or for frontend
npm test
```

**Manual verification**:
- Reproduce original bug scenario
- Verify bug no longer occurs
- Check related functionality still works

### 7. Regression Prevention
Prevent bug from recurring:

**Test coverage**:
- Ensure edge case has test coverage
- Add additional tests for similar edge cases

**Code review**:
- Check for similar patterns elsewhere
- Fix similar issues proactively

**Documentation**:
- Add comments explaining non-obvious edge case handling
- Update documentation if behavior was misunderstood

### 8. Cleanup
Remove debug code:
- Remove print statements
- Remove temporary assertions
- Clean up test code

Run linters:
```bash
# Whatever linter your project uses
ruff check src/ --fix
eslint src/ --fix
```

---

## CRITICAL: Git Operations Policy

**NEVER automatically commit, push, or perform any git operations.**

This skill ONLY investigates bugs, implements fixes, and runs verification. Git operations are ONLY performed when:
- User explicitly requests "commit this fix"
- User explicitly requests "push to remote"
- User explicitly requests "create PR"

Do NOT:
- Auto-commit after fix is verified
- Auto-push after tests pass
- Auto-create PRs
- Run any CI/CD pipelines automatically

If the user wants git operations, they will ask explicitly.

---

## Invocation

```
/bug-fixer <description>
```

**Examples**:
```
/bug-fixer Search returns no results for valid queries
/bug-fixer PDF viewer not loading documents
/bug-fixer API returning 500 on valid request
/bug-fixer Login fails intermittently
```

---

## Output

**Investigation report**:
```
Bug: Search returns no results for valid queries

Reproduction: Confirmed
  curl -X GET 'http://localhost:8000/api/search?q=test'
  Response: {"results": [], "count": 0}

Root cause: Index not loaded on server startup
  File: src/server.py:45
  Issue: startup handler missing load_index() call

Fix: Add index loading to startup event
  Modified: src/server.py
  Added: await load_index() to startup handler

Regression test: Added test_search_with_valid_query()
  File: tests/test_search.py:87

Verification: All tests passing
  tests/test_search.py: 15 passed
  Full suite: 127 passed
```

**Files modified**:
- Implementation file with fix
- Test file with regression test

**Verification proof**:
- Test output showing regression test passes
- Full test suite passing
- Manual verification steps completed

---

## Common Bug Categories

### Backend Bugs

**Database issues**:
- Missing async/await
- Connection pool exhaustion
- Transaction rollback failures
- N+1 query problems

**API issues**:
- Missing input validation
- Incorrect response models
- Auth/permission failures
- CORS configuration

**Data processing**:
- Edge case handling (None, empty, malformed)
- Off-by-one errors
- Type mismatches
- Encoding issues

### Frontend Bugs

**React/Component issues**:
- Stale closure in useEffect
- Missing dependency in hook deps array
- Key prop issues in lists
- State update race conditions

**API integration**:
- Missing error handling
- Incorrect request format
- Response parsing failures
- Auth token not sent

**UI issues**:
- CSS specificity conflicts
- Responsive design breakpoints
- Accessibility violations
- Browser compatibility

### Full-Stack Bugs

**Contract mismatches**:
- Backend schema != Frontend types
- API endpoint URL mismatch
- Request/response format differences

**Timing issues**:
- Race conditions
- Async operation ordering
- Polling interval too aggressive

---

## Anti-Patterns to Avoid

**Fixing without reproducing**:
```
# BAD: Assume bug exists, apply fix blindly
# GOOD: Reproduce first, understand root cause, then fix
```

**Fixing without test**:
```
# BAD: Apply fix, manually verify, call it done
# GOOD: Write regression test, apply fix, verify test passes
```

**Fixing symptoms, not root cause**:
```python
# BAD (symptom fix)
if result is None:
    result = []  # Hide the real problem

# GOOD (root cause fix)
# Fix why result is None in the first place
```

**Leaving debug code**:
```python
# BAD
print("DEBUG: got here")  # Left in production

# GOOD
# Remove all debug prints before completing
```

---

## Integration with Other Skills

**test-runner**: Run tests after fix to verify
**linting-enforcer**: Run linters to clean up code
**feature-generator**: If bug reveals missing feature

---

## Notes

- Always reproduce before fixing
- Always add regression test
- Root cause > symptom fix
- Verify no other regressions introduced
- Clean up debug code before completing
