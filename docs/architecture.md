# ontograph — Architecture

## Overview

ontograph is an LLM-powered knowledge graph engine. It ingests unstructured text,
extracts entities and relationships via LLM, resolves duplicates using a four-signal
composite score, and provides hybrid semantic-graph retrieval.

## Module Map

```
src/ontograph/
├── __init__.py          Public API exports
├── onto.py              OntoDB class — unified user-facing API
├── db.py                GraphDB — SQLite schema + all CRUD operations
├── models.py            Domain models (Entity, Relationship, Alias, Schema, OrbitEntry, Document)
├── llm.py               LLM client (OpenAI Responses API + Google Gemini + embeddings)
├── ingest.py            Ingestion pipeline: text → LLM extraction → resolution → graph
├── resolve.py           Entity resolution (phonetic, spelling, semantic, orbit composite)
├── orbit.py             Orbit proximity tracking with time decay
├── search.py            Hybrid search (semantic + keyword + graph traversal)
├── config.py            YAML-based config with 5-layer precedence
├── schema_registry.py   Pre-built schemas (EXPANDED_SCHEMA)
└── temporal.py          Temporal normalization (relative dates → ISO)
```

## Data Flow

### Ingestion Pipeline (`ingest.py`)

```
Raw text
  → Store as Document (with embedding of first 8k chars)
  → LLM extraction (schema-constrained if schema provided)
    → Extracts: entities (name, type, attributes) + relationships (source, target, type)
    → Enriched attributes: status, confidence, temporal, source_project
  → Entity resolution per extracted entity
    → Phonetic match (Metaphone)
    → Spelling match (Jaro-Winkler)
    → Semantic match (embedding cosine)
    → Orbit match (interaction frequency)
    → If composite score > threshold: resolve to existing entity
    → Else: create new entity with embedding
  → Relationship creation (skip if already exists)
  → Provenance stamping (if session_id provided):
    → entity.attributes.source_session_id, extracted_at
    → relationship.attributes.source_session_id, extracted_at
  → Orbit tracking (if observer_id provided)
```

### Search Pipeline (`search.py`)

```
Query
  → Embed query
  → Semantic search (cosine similarity against entity embeddings)
  → FTS5 keyword search
  → Merge + deduplicate results
  → Graph traversal (expand to neighbors within depth)
  → Return ranked results
  → (ask/ask_with_sources): LLM synthesizes answer from graph context
```

### Entity Resolution (`resolve.py`)

```
Input name + optional type + optional observer
  → Check exact name match (case-insensitive)
  → Check alias match
  → Compute composite score across all candidates:
    - phonetic_score (Metaphone similarity)
    - spelling_score (Jaro-Winkler)
    - semantic_score (embedding cosine)
    - orbit_score (proximity to observer)
  → If best composite > RESOLUTION_THRESHOLD (0.72):
    - Return existing entity + score
    - Log resolution
  → Else:
    - Return None + best score
```

## Storage

### SQLite Schema (8 tables)

| Table | Purpose |
|---|---|
| `entities` | Graph nodes with name, type, attributes, file_refs, embedding blob |
| `entity_aliases` | Alternate names per entity (transcription errors, nicknames) |
| `relationships` | Directed/bidirectional edges with attributes |
| `orbit` | Interaction frequency per observer-entity pair |
| `documents` | Ingested source text with embedding |
| `schemas` | Ontology schema definitions (entity types, relationship types) |
| `resolution_log` | Audit trail for entity resolution (feedback loop) |
| `entities_fts` | FTS5 virtual table auto-synced via triggers |

Embeddings: float32 numpy arrays stored as byte blobs.
IDs: 12-char truncated hex UUIDs.
Timestamps: UTC ISO format.

## Configuration (`config.py`)

5-layer precedence (highest wins):
1. Runtime overrides (`set_llm_provider()`, `set_llm_model()`, etc.)
2. Environment variables (`ONTOGRAPH_LLM_PROVIDER`, `ONTOGRAPH_LLM_MODEL`, etc.)
3. Project config (`.ontograph/config.yaml` in cwd)
4. User config (`~/.ontograph/config.yaml`)
5. Hardcoded defaults

LLM providers: `openai` (default, gpt-4o-mini), `google` (gemini-2.5-flash-lite).
Embeddings: always OpenAI `text-embedding-3-small` (256-dim).

## Expanded Schema (`schema_registry.py`)

Pre-built `EXPANDED_SCHEMA` for rich knowledge extraction:

**Entity types (10):** person, project, organization, topic, event, location,
decision, goal, insight, session

**Relationship types (12):** works_on, belongs_to, collaborates_with, located_in,
mentioned_in, decided_during, originated_in, updated_status, relates_to, blocks,
blocked_by, supports

All new relationship types are directed.

## Temporal Normalization (`temporal.py`)

Converts relative time expressions to ISO date strings:

| Input | Output | Notes |
|---|---|---|
| `2026-07-15` | `2026-07-15` | ISO passthrough |
| `Q3 2026` / `2026-Q3` | `2026-07-01` | First day of quarter |
| `by July 2026` | `2026-07-31` | Last day of month |
| `July 2026` | `2026-07-01` | First day of month |
| `next quarter` | varies | Relative to reference_date |
| `this week` | varies | Monday of current week |
| `next month` | varies | First day of next month |
| unparseable | original string | Returned unchanged |
