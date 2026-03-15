---
name: implementer
description: Implement changes to the codebase thoughtfully - solving the actual problem without creating future work. Use when user asks to implement, change, update, modify, add, or make any codebase change that isn't explicitly a bug fix or brand new feature.
---

# Implementer Skill

---

## Philosophy

**Solve the problem, not the symptom.** Understand what's actually needed before writing code.

**Don't create future work.** Every line of code is a liability. Don't leave landmines, gotchas, or "I'll fix this later" situations.

**Minimum viable change.** The best implementation is often the smallest one that fully solves the problem. Complexity is not sophistication.

**Fit in, don't stand out.** Code should look like it was always there. Follow existing patterns. Don't introduce new conventions unless there's a compelling reason.

**Appropriate effort.** Match implementation effort to problem importance. Don't over-engineer small changes. Don't under-engineer critical ones.

---

## Process

### 1. Understand the Problem
Before touching code:

**Ask clarifying questions**:
- What's the actual goal?
- Why is this needed?
- Who/what is affected?
- What does success look like?
- Are there constraints I should know about?

**Identify the root problem**:
- Is what they're asking for the actual solution, or a symptom?
- Would solving a different problem eliminate this one?
- Is this a one-off or will it recur?

### 2. Analyze the Context
Run context analysis before implementing:

```bash
# Find relevant files (customize script path for your project)
uv run .claude/skills/implementer/scripts/analyze_context.py "description"
```

**Understand**:
- Where does this change belong?
- What existing code does this interact with?
- What patterns are used in this area?
- What utilities already exist that I can reuse?
- What tests cover this area?

### 3. Plan the Change
Before writing code:

**Scope the change**:
- What files need modification?
- What files need creation (if any)?
- What's the blast radius?

**Identify risks**:
- What could break?
- What assumptions am I making?
- What edge cases exist?

**Choose the approach**:
- What's the simplest way to do this?
- Does this fit existing patterns?
- Am I introducing unnecessary complexity?

### 4. Implement with Care

**Follow the codebase**:
- Use existing utilities, don't recreate them
- Match naming conventions exactly
- Follow established patterns
- Put code where similar code lives

**Keep it simple**:
- No premature abstraction
- No "just in case" code
- No clever tricks when straightforward works
- No comments that explain *what* (code should be clear); only *why* if non-obvious

**No hidden gotchas**:
- No magic numbers without explanation
- No implicit dependencies
- No assumptions that aren't validated
- No "this works but I don't know why"

### 5. Test Appropriately

**Match test effort to risk**:
- High-risk change -> comprehensive tests
- Low-risk change -> basic coverage
- Trivial change -> may not need new tests

**Test the right things**:
- Test behavior, not implementation
- Test edge cases that matter
- Don't test framework code
- Don't test obvious getters/setters

**Use existing test patterns**:
- Follow test file organization
- Use existing fixtures/helpers
- Match test naming conventions

### 6. Verify the Implementation

**Does it actually work?**
- Run the tests
- Try it manually
- Check edge cases

**Does it fit in?**
- Does it follow existing patterns?
- Would someone reading this code be surprised?
- Does it look like it was always there?

**Did I create future work?**
- Any TODOs or FIXMEs added?
- Any technical debt introduced?
- Any "temporary" solutions?
- Any undocumented behavior?

### 7. Clean Up

**Remove the scaffolding**:
- Delete debug code
- Remove commented-out code
- Remove unused imports
- Run linters

**Final check**:
- Would I be happy to maintain this code?
- Would I be proud to show this to a senior engineer?
- Does this make the codebase better or worse overall?

---

## CRITICAL: Git Operations Policy

**NEVER automatically commit, push, or perform any git operations.**

This skill ONLY implements code changes and runs verification. Git operations are ONLY performed when:
- User explicitly requests "commit these changes"
- User explicitly requests "push to remote"
- User explicitly requests "create PR"

Do NOT:
- Auto-commit after implementation
- Auto-push after tests pass
- Auto-create PRs
- Run any CI/CD pipelines automatically

If the user wants git operations, they will ask explicitly.

---

## Anti-Patterns to Avoid

### Over-Engineering
```python
# BAD: Abstract factory for a one-off case
class DataProcessorFactory:
    @staticmethod
    def create_processor(type: str) -> DataProcessor:
        ...

# GOOD: Just do the thing
def process_data(data):
    ...
```

### Under-Engineering
```python
# BAD: Hardcoded values that will definitely change
def get_api_url():
    return "http://localhost:8000"  # TODO: make configurable

# GOOD: Use existing config patterns
def get_api_url():
    return settings.API_URL
```

### Leaving Landmines
```python
# BAD: Silent failure that will confuse future devs
def get_user(id):
    try:
        return db.query(User).get(id)
    except:
        return None  # Swallows ALL errors

# GOOD: Fail explicitly or handle specifically
def get_user(id):
    return db.query(User).get(id)  # Let it raise if user not found
```

### Reinventing the Wheel
```python
# BAD: Writing your own utility
def format_date(date):
    return f"{date.year}-{date.month:02d}-{date.day:02d}"

# GOOD: Use existing utilities or standard library
from datetime import date
date.isoformat()
```

### Adding "Just in Case" Code
```python
# BAD: Handling cases that can't happen
def process_item(item):
    if item is None:  # Can't be None - required field
        return None
    if item.type not in ["a", "b"]:  # DB constraint ensures valid
        raise ValueError("Invalid type")
    ...

# GOOD: Trust the system, validate at boundaries
def process_item(item):
    # item is validated at API level, trust it here
    ...
```

### Creating Future Mysteries
```python
# BAD: Magic that requires archaeology to understand
result = data[::2][::-1][1::3]

# GOOD: Clear intent
every_other = data[::2]
reversed_data = every_other[::-1]
result = reversed_data[1::3]  # Take every 3rd starting from index 1
```

---

## Decision Framework

### When to Create a New File
- The functionality is distinct and reusable
- Existing files would become too large (>500 lines is a smell)
- The change doesn't fit any existing file's responsibility

### When to Modify an Existing File
- The change fits the file's existing responsibility
- Similar code already lives there
- Creating a new file would fragment related logic

### When to Create a New Utility
- You're about to duplicate code
- The logic is genuinely reusable
- It doesn't already exist somewhere

### When to Inline Code
- The "abstraction" is used exactly once
- The abstraction makes code harder to follow
- The abstraction provides no meaningful name

### When to Add Tests
- The change affects business logic
- The change touches error handling
- The change modifies data transformations
- You're not confident it works

### When Tests Are Optional
- Pure config changes
- Documentation updates
- Obvious one-liner changes
- Changes already covered by existing tests

---

## Invocation

```
/implementer <description of change>
```

**Examples**:
```
/implementer Add pagination to the user list API
/implementer Update the search to include type filtering
/implementer Change the date format in the export CSV
/implementer Refactor the context builder to support streaming
```

---

## Output

**Before implementing**:
- Summary of understood problem
- Files to be modified/created
- Approach chosen with rationale
- Risks identified

**After implementing**:
- What was changed
- Why this approach was chosen
- Any trade-offs made
- How to verify it works

---

## Integration with Other Skills

- **test-runner**: Run tests after implementation
- **linting-enforcer**: Clean up code after changes
- **bug-fixer**: If the change reveals a bug
- **feature-generator**: If the change is specifically a new feature

---

## Notes

- Always understand before implementing
- The best code is code you don't write
- Match effort to importance
- If it feels hacky, it probably is
- When in doubt, keep it simple
- Your future self will thank you
