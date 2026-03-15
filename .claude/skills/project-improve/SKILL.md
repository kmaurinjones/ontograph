---
name: project-improve
description: Encode a durable improvement to the project's agent configuration. Routes improvements to agents/lessons.md, agents/decisions.md, docs/, or skill files based on type — never inline into CLAUDE.md (except non-negotiables). Invoked automatically when a session produces a new convention, architectural decision, or reusable pattern. Also use when any team member says encode this, bake this in, add this as a rule, make this permanent, remember this going forward, or update the instructions.
---

# Skill: Project Improve

## Purpose

Encode an improvement to this project's agent configuration so it persists
across sessions and team members. This skill is the execution arm of the
Self-Improvement Protocol defined in CLAUDE.md — the single most important
mechanism in the entire constitution.

**Why this is P0:** Every session that encounters friction, discovers a better
pattern, or resolves an ambiguity is an opportunity to make the constitution
permanently better. With this skill active, each session's learnings compound —
the next session starts from a higher baseline, hits fewer problems, and
produces more consistent output. Without it, every other rule in CLAUDE.md is a
depreciating asset: accurate the day it was written and increasingly wrong over
time. The default human behavior is to suffer through friction rather than fix
the system. This skill overrides that default by firing automatically.

**Every unencoded improvement is a compounding loss.** The cost is not just the
friction in the current session — it is the same friction in every future
session that hits the same problem. The opportunity cost grows exponentially.

Invoke automatically when trigger conditions are met (see CLAUDE.md), or
manually when a team member says phrases like: "encode this", "bake this in",
"add this as a rule", "make this permanent", "remember this going forward",
"from now on", "always do", "going forward".

---

## Step 0: Determine Invocation Mode

This skill is invoked in one of two ways. Identify which mode applies before
proceeding.

### Mode A: Explicit directive

The user invoked the skill with a specific instruction attached, e.g.:
`/project-improve always use snake_case for database columns` or
`/project-improve add Redis caching convention to coding standards`.

**Action:** The directive is the improvement. Skip to Step 1 and classify it.

### Mode B: Contextual inference (correction or preference expressed mid-session)

The user corrected the agent's behavior or expressed a preference during the
session, then invoked the skill without a specific directive (or with a vague
one like "encode that" / "bake that in"). The improvement must be inferred from
recent conversation context.

**Action — follow these steps exactly:**

1. **Identify the pattern.** Scan the recent conversation for what the agent did
   wrong or what the user wanted done differently. Look for: user corrections,
   "no, do X instead", "don't do Y", "I wanted Z", repeated friction, or
   explicit preference statements.

2. **State the pattern back to the user.** Before encoding anything, confirm
   with the user by presenting:
   - **What happened:** "You corrected me when I did X."
   - **The erroneous pattern:** "The behavior that needs to change is: [specific
     description of what the agent did wrong or suboptimally]."
   - **The proposed rule:** "The rule I'll encode is: [concrete, actionable rule
     that prevents this from recurring]."

3. **Wait for user confirmation.** Do not write anything until the user confirms
   the pattern and proposed rule are correct. The user may refine the wording or
   scope.

4. **After confirmation,** proceed to Step 1 with the confirmed rule.

**Why confirmation is mandatory for Mode B:** Inferred improvements risk encoding
the wrong lesson. The agent might misidentify which part of the interaction was
the problem, or encode a rule that's too broad/narrow. A 10-second confirmation
prevents encoding a rule that then causes friction in every future session.

---

## Step 1: Classify the Improvement

Identify which category the improvement falls into. **Stop at the first match.**

| # | Category | Signal | Target |
|---|---|---|---|
| 1 | **Operational lesson** | Mistake, correction, plan deviation, discovered pattern, friction resolved | `agents/lessons.md` under a searchable category heading |
| 2 | **Architectural decision** | Stack choice, data flow change, integration pattern, database schema decision | `agents/decisions.md` (append-only row) |
| 3 | **Coding convention** | Style rule, naming pattern, file organization, linter config | `agents/lessons.md` > `## Coding Conventions` |
| 4 | **External data source** | New API, database, or service connected | `docs/` or `CLAUDE.md` Architecture section (one-line pointer) |
| 5 | **Process convention** | Workflow, branching, deploy, review process | `agents/lessons.md` > `## Process` or `docs/` |
| 6 | **Non-negotiable rule** | Safety constraint, hard requirement, zero-tolerance policy | `CLAUDE.md` Non-Negotiables section (only place content goes directly into CLAUDE.md) |
| 7 | **API surface change** | Endpoint added, removed, or modified | `docs/architecture-overview.md` + `CLAUDE.md` API Surface table (one-line entry) |
| 8 | **Reusable workflow** | Multi-step procedure needed across sessions | New skill in `.claude/skills/<name>/SKILL.md` |
| 9 | **Existing skill correction** | Bug, drift, or gap in a current skill | Edit `.claude/skills/<name>/SKILL.md` |
| 10 | **Architecture doc update** | Model changed, data flow modified, directory restructured | `docs/architecture-overview.md` |

Customize this table for your project. Add categories that match your CLAUDE.md
sections (e.g., Design System, Testing Strategy, Deploy Pipeline). Remove
categories that don't apply.

If the improvement spans multiple categories (e.g., new data source + coding
convention), handle each target in sequence.

---

## Step 2: Apply the Correct Format

**HARD RULE — CLAUDE.md is a routing document, not an encyclopedia.**
CLAUDE.md entries must be one-line pointers to skills, docs, or other files.
Never add code blocks, multi-line instructions, connection strings, or detailed
procedures to CLAUDE.md. If your content is more than one sentence of context,
it belongs in `agents/`, `docs/`, or a skill file.

### Operational Lesson

Append to `agents/lessons.md` under a searchable category heading (e.g.,
`## Git`, `## Python`, `## Testing`, `## API Design`, `## UI/UX`).
Create the heading if it doesn't exist. Each entry must include: what went wrong
or changed, why, and the rule to follow going forward.

```markdown
## <Category>

- **<Date> — <Brief title>:** <What happened.> <Why.> <Rule going forward.>
```

Create `agents/` directory and `agents/lessons.md` if they don't exist.

### Architectural Decision

Add a row to `agents/decisions.md` (NOT to CLAUDE.md):

```markdown
| <YYYY-MM-DD> | <What was decided> | <Why / context> |
```

Create `agents/` directory and `agents/decisions.md` if they don't exist.
If the decision also changes the Architecture section content in CLAUDE.md
(stack, directory structure), update that pointer too.

### Coding Convention

Append to `agents/lessons.md` > `## Coding Conventions`.
Format: one bullet per rule, imperative voice.

```markdown
- **Rule subject:** Do X. Never do Y. Reason: Z.
```

### External Data Source

Add a one-line pointer in `CLAUDE.md` Architecture section, then put the detail
in `docs/` or `agents/lessons.md`.

### Process Convention

Append to `agents/lessons.md` > `## Process`. One bullet per convention.

### Non-Negotiable Rule

Append to `CLAUDE.md` Non-Negotiables section with a `###` subheading.
This is the **only category** where content goes directly into CLAUDE.md:

```markdown
### <Rule name>
- <Concrete constraint — what to do and what never to do.>
```

### API Surface Change

1. Update `docs/architecture-overview.md` with endpoint details.
2. Update the API Surface table in `CLAUDE.md` if present (one-line entry only).
3. Update `README.md` API Surface list if the endpoint is user-facing.

### New Skill

Before creating, confirm:
1. The workflow is reused across sessions (not one-off).
2. No existing skill covers it (check `.claude/skills/`).
3. Scope is coherent — one skill, one capability.

Use the `skill-generator` skill if available, or create manually:
- Directory: `.claude/skills/<kebab-case-name>/`
- File: `SKILL.md` with frontmatter (`name`, `description`) + step-by-step procedure.

### Existing Skill Update

Read the full SKILL.md first. Make the minimum targeted edit.
Do not restructure or reformat sections not related to the improvement.

### Architecture Doc Update

Update `docs/architecture-overview.md` directly. Keep it current-state only
(no historical commentary). Update the "Last updated" date.

---

## Step 3: Validate

After writing the change, verify all that apply:

- [ ] Target file parses correctly (no broken Markdown tables, no orphaned headers).
- [ ] The improvement is specific — vague rules ("be smarter about X") are not
  durable. Restate as a concrete trigger + concrete action.
- [ ] No existing rule is contradicted without explicit acknowledgment.
- [ ] If CLAUDE.md was changed: heading hierarchy is preserved and no section
  is duplicated.
- [ ] If a Decisions Log entry was added to `agents/decisions.md`: date, decision,
  and context columns are all populated.
- [ ] Content was NOT added inline to CLAUDE.md (except Non-Negotiables).
- [ ] If docs/ was changed: the "Last updated" date reflects today.
- [ ] If a skill was created or modified: the frontmatter `name` and
  `description` fields are present and accurate.

---

## Step 4: Confirm

After making the change, state:

1. **Where** — file path + section name.
2. **What** — the rule or entry in one sentence.
3. **When** — takes effect immediately (this session) or next session start.

Example:
> Encoded in `agents/lessons.md` > ## Coding Conventions:
> "All database queries must use parameterized statements via SQLAlchemy bind params."
> Takes effect immediately.
