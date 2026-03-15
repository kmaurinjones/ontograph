# ontograph — Agent Constitution

## Identity
LLM-powered knowledge graph engine with ontological entity resolution, orbit-based proximity scoring, and hybrid semantic-graph retrieval. Created 2026-03-15.

## Symlinked Sources of Truth (MANDATORY)
- `AGENTS.md` → `CLAUDE.md`. **CLAUDE.md is the ground truth.** Edit `CLAUDE.md` only.
- `.codex/skills/` → `.claude/skills/`. **`.claude/skills/` is the ground truth.** Edit files in `.claude/skills/` only.

## How to Run
```bash
uv run python -c "from ontograph import OntoDB; db = OntoDB('test.db'); print(db.stats())"
```

## How to Test
```bash
uv run ruff check src/ tests/ && uv run pytest
```

## Architecture

### Stack
- Python 3.14, uv-managed
- SQLite (single-file embedded DB — graph modeled as entity/relationship tables)
- OpenAI API: `text-embedding-3-small` (256-dim embeddings), `gpt-4o-mini` (LLM), Responses API
- jellyfish (phonetic + string similarity for entity resolution)
- numpy (embedding vector ops)
- pydantic (validation)

### Directory Structure
```
ontograph/
├── src/ontograph/          # Package source
│   ├── __init__.py         # Public API exports (OntoDB, Entity, Relationship, Schema, etc.)
│   ├── onto.py             # OntoDB class — main entry point, unified API
│   ├── db.py               # SQLite schema, GraphDB class, all CRUD ops
│   ├── models.py           # Domain models: Entity, Relationship, Alias, Schema, OrbitEntry, Document
│   ├── llm.py              # OpenAI client (Responses API + embeddings)
│   ├── ingest.py           # Ingestion pipeline: text → entities + relationships
│   ├── resolve.py          # Entity resolution (phonetic, spelling, semantic, orbit composite)
│   ├── orbit.py            # Orbit proximity tracking with time decay
│   ├── search.py           # Hybrid search (semantic + keyword + graph traversal)
│   └── config.py           # Configuration (API key, model names, thresholds)
├── tests/                  # pytest test suite
├── pyproject.toml          # Project config + deps
└── README.md               # Usage docs
```

### Key Design Decisions
- **SQLite over graph-native DB**: Same engineering criteria (embedded, zero-config, single-file) with superior ecosystem. Graph modeled via entity/relationship tables with recursive CTEs for traversal.
- **Composite entity resolution**: Four-signal scoring (phonetic, spelling, semantic, orbit) to handle transcription errors and name ambiguity.
- **Orbit as first-class concept**: Interaction frequency tracking enables context-aware resolution (the "Sam vs Sal" problem).
- **Schema-constrained extraction**: Ontology schemas limit LLM extraction to valid types, reducing hallucinated entities.
- **Resolution audit log**: Every resolution logged for self-improving feedback loop.

## Non-Negotiables (P0)

### UV only for Python
Always use `uv` for Python package management. Never `pip`.

### No silent fallbacks
Never use `.get()` with defaults that hide bugs. Prefer explicit key access and hard failures.

### Do not modify model names
`EMBEDDING_MODEL`, `LLM_MODEL` in `config.py` are sacred. Fix the real cause of API errors.

### Justify everything — zero unjustified output
Every artifact must be justifiable. "Why does this exist?" must have a concrete answer.

### Linters are mandatory
After editing code: `uv run ruff check --fix src/ tests/`

## Coding Conventions
- Flat module structure under `src/ontograph/` — no nested sub-packages
- OOP for domain models (Entity, Relationship, etc.), functions for operations (ingest, resolve, search)
- All models have `to_row()` / `from_row()` for DB serialization
- Embeddings stored as float32 numpy byte blobs in SQLite
- UTC timestamps in ISO format everywhere
- UUIDs truncated to 12 hex chars for readability

## Process Conventions

### Git workflow
- Branch naming: `feature/<name>`, `fix/<name>`, `chore/<name>`
- Commit format: conventional commits (`feat:`, `fix:`, `chore:`, `docs:`)
- PRs: squash merge, descriptive titles

### Task completion workflow
1. Restate the requested changes
2. Create a task list
3. Execute against the task list
4. Verify each change works before marking complete

## Accumulated Knowledge (pointers — DO NOT inline content here)
- **Lessons learned:** `agents/lessons.md`
- **Decisions log:** `agents/decisions.md`
- **Skills:** `.claude/skills/`

## Self-Improvement Protocol (MANDATORY — P0)

**Trigger conditions:**
- New convention established, user corrects behavior, friction point resolved
- User says "from now on", "always do", "bake this in"

**Routing table:**
| Category | Target |
|---|---|
| Operational lessons | `agents/lessons.md` |
| Architectural decisions | `agents/decisions.md` |
| Process conventions | This file (Process Conventions section) |
| Non-negotiable rules | This file (Non-Negotiables section) |
| Reusable workflows | `.claude/skills/` |

See `.claude/skills/project-improve/SKILL.md` for full procedure.

## Decisions Log
| Date | Decision | Context |
|---|---|---|
| 2026-03-15 | Project created | KG engine with ontological entity resolution, orbit scoring, hybrid search |
| 2026-03-15 | SQLite over graph-native DB | Embedded, zero-config, single-file; graph modeled via tables + recursive CTEs |
| 2026-03-15 | OpenAI text-embedding-3-small (256-dim) | Cost-efficient for high-volume operations |
| 2026-03-15 | gpt-4o-mini as default LLM | High-volume ingestion/extraction needs low cost per call |
| 2026-03-15 | jellyfish for phonetic/string similarity | Lightweight, no NLTK dependency, Metaphone + Jaro-Winkler |
| 2026-03-15 | Responses API over Chat Completions | OpenAI's recommended path forward, cleaner interface |
